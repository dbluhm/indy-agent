""" Message receiver handlers. """

from aiohttp import web
import asyncio

class PostDuplexMessageHandler():
    def __init__(self, in_q, out_q):
        self.in_q = in_q
        self.out_q = out_q

    async def handle_message(self, request):
        """ Put to message queue and wait for outbound queue to populate
        """
        if not request.app['agent'].initialized:
            raise web.HTTPUnauthorized()

        msg = await request.read()
        await self.in_q.put(msg)
        return web.Response(text=(await self.out_q.get()))
