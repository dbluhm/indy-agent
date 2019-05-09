""" Message receiver handlers. """

# pylint: disable=import-error
from asyncio import Event
from aiohttp import web


class PostMessageHandler:
    """ Simple message queue interface for receiving messages.
    """
    def __init__(self, transport):
        self.transport = transport

    async def handle_message(self, request):
        """ Put to message queue and return 202 to client.
        """
        if not request.app['agent'].initialized:
            raise web.HTTPUnauthorized()

        msg = await request.read()

        return_msg = None
        message_event = Event()
        async def all_dispatch(new_msg_gen):
            return_msg = await next(new_msg_gen, None)
            message_event.set()

        await message_event.wait()

        if return_msg:
            return web.Response(text=return_msg)

        raise web.HTTPAccepted()
