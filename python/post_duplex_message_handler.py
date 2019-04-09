""" Message receiver handlers. """

from aiohttp import web
import asyncio
import json

class PostDuplexMessageHandler():
    def __init__(self, in_q, out_q):
        self.in_q = in_q
        self.out_q = out_q

    async def handle_options(self, request):
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Allow': 'OPTIONS, POST',
            'Access-Control-Allow-Methods': 'POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type'
        }
        return web.Response(headers=headers)

    async def handle_message(self, request):
        """ Put to message queue and wait for outbound queue to populate
        """
        msg = await request.read()
        print("Agent Received: {}".format(json.dumps(json.loads(msg.decode('utf-8')), indent=4, sort_keys=False)))
        await self.in_q.put(msg)
        out_msg = await self.out_q.get()
        print("Sending to UI: {}".format(json.dumps(json.loads(out_msg), indent=4, sort_keys=False)))
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Allow': 'OPTIONS, POST',
            'Access-Control-Allow-Methods': 'POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type'
        }
        return web.Response(text=out_msg, headers=headers)
