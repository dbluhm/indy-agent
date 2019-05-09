""" Supporting classes and methods for the Transport Layer. """
import json
import asyncio

from indy import crypto, did, pairwise
import aiohttp

from serializer import json_serializer as Serializer
import indy_sdk_utils as utils

class Clerk:
    """ A 'Mail Clerk' that organizes all outgoing messages. """
    def __init__(self):
        self.queues = {}
        self.dispatchers = {}

    def queue_message(self, identifier, msg):
        """ Queue up a message for a given identifier.

            Parameters
            ----------
            identifier : str
                The identifier to be used to look up queues.
            msg: Message
                Message object; not yet serialized or packaged so transport
                details can be added before dispatch.
        """
        if not identifier in self.queues:
            self.queues[identifier] = asyncio.Queue()

        self.queues[identifier].put_nowait(msg)

    def get_queue(self, identifier):
        """ Return the Queue for a given identifier.

            Parameters
            ----------
            identifier : str
                The identifier to be used to look up queues.
        """
        if not identifier in self.queues:
            return None
        return self.queues[identifier]


    async def get_msg(self, identifier):
        """ Wait for a message on a given queue.

            Parameters
            ----------
            identifier : str
                The identifier to be used to look up the queue.
        """
        if not identifier in self.queues:
            return None
        return await self.queues[identifier].get()

    def get_msg_nowait(self, identifier):
        """ Get message on a given queue without waiting.

            Parameters
            ----------
            identifier : str
                The identifier to be used to look up the queue.
        """
        if not identifier in self.queues:
            return None
        try:
            return self.queues[identifier].get_nowait()
        except asyncio.QueueEmpty:
            return None


    def pending_message_count(self, identifier):
        """ Return the number of pending messages on a queue identified by
            identifier.

            Parameters
            ----------
            identifier : str
                The identifier to be used to look up the queue.
        """
        if not identifier in self.queues:
            return 0

        return self.queues[identifier].qsize()

    def remove_queue(self, identifier):
        """ Remove a queue and any registered dispatcher identified by identifier.

            Parameters
            ----------
            identifier : str
                The identifier to be used to look up the queue.
        """
        if identifier in self.queues:
            del self.queues[identifier]
        if identifier in self.dispatchers:
            del self.dispatchers[identifier]

    def register_dispatcher(self, identifier, dispatcher):
        """ Register a dispatcher for a queue identified by identifier.

            Parameters
            ----------
            identifier : str
                The identifier to be used to look up the queue.
            dispatcher : Coroutine
                Asynchronous coroutine that handles sending the messages through
                the appropriate channel.
        """
        if identifier in self.dispatchers:
            self.dispatchers[identifier].cancel()

        async def dispatcher_wrapper():
            await dispatcher
            if identifier in self.dispatchers:
                del self.dispatchers[identifier]

        dispatcher = asyncio.ensure_future(dispatcher_wrapper())
        self.dispatchers[identifier] = dispatcher


    def cancel_dispatcher(self, identifier):
        """ Cancel a registered dispatcher for a queue identified by
            identifier.

            Parameters
            ----------
            identifier : str
                The identifier to be used to look up the queue.
        """
        if not identifier in self.dispatchers:
            return
        self.dispatchers[identifier].cancel()
        del self.dispatchers[identifier]


class Conductor:
    """ Transport layer interface. """
    def __init__(self, wallet_handle, outbound_mail_clerk, message_processor):
        self.wallet_handle = wallet_handle
        self.outbound_mail_clerk = outbound_mail_clerk
        self.message_processor = message_processor

    async def packed_message_generator(self, for_did, queue):
        while True:
            msg = await queue.get()

            #TODO transport decorator handling

            yield self.prepare_message_for_did(for_did, msg)

    @staticmethod
    async def post_to_endpoint_dispatcher(new_msg_gen, their_endpoint):
        """ Default message dispatcher. """
        headers = {
            'content-type': 'application/ssi-agent-wire'
        }
        async for new_msg in new_msg_gen:
            async with aiohttp.ClientSession() as session:
                async with session.post(their_endpoint, data=new_msg, headers=headers) as resp:
                    if resp.status != 202:
                        print(resp.status)
                        print(await resp.text())


    # TODO give a dispatcher as well?
    async def handle_message(self, msg):
        msg = self.unpack_message(msg)
        await self.message_processor(msg)

    async def unpack_message(self, wire_msg_bytes):
        if isinstance(wire_msg_bytes, str):
            wire_msg_bytes = bytes(wire_msg_bytes, 'utf-8')

        msg = Serializer.unpack(wire_msg_bytes)
        if '@type' in msg:
            #msg not encrypted
            return msg

        unpacked = json.loads(
            await crypto.unpack_message(
                self.wallet_handle,
                wire_msg_bytes
            )
        )

        from_key = None
        from_did = None
        if 'sender_verkey' in unpacked:
            from_key = unpacked['sender_verkey']
            from_did = await utils.did_for_key(self.wallet_handle, unpacked['sender_verkey'])

        to_key = unpacked['recipient_verkey']
        to_did = await utils.did_for_key(self.wallet_handle, unpacked['recipient_verkey'])

        msg = Serializer.unpack(unpacked['message'])

        msg.context = {
            'from_did': from_did,  # Could be None
            'to_did': to_did,  # Could be None
            'from_key': from_key,  # Could be None
            'to_key': to_key
        }
        return msg

    async def prepare_message_for_did(self, their_did, msg):
        pairwise_info = json.loads(await pairwise.get_pairwise(self.wallet_handle, their_did))
        pairwise_meta = json.loads(pairwise_info['metadata'])

        my_did = pairwise_info['my_did']

        my_vk = await did.key_for_local_did(self.wallet_handle, my_did)
        their_vk = await did.key_for_local_did(self.wallet_handle, their_did)

        wire_message = await crypto.pack_message(
            self.wallet_handle,
            Serializer.pack(msg),
            [their_vk],
            my_vk
        )

        return wire_message
