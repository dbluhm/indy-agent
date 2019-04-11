""" Message receiver handlers. """

import json
import socket

from aiohttp import web

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
        agent = request.app['agent']
        if not agent.endpoint:

            local_ip = socket.gethostbyname(socket.gethostname())
            agent.endpoint = request.url.scheme + '://' + local_ip
            if request.url.port is not None:
                agent.endpoint += ':' + str(request.url.port) + '/indy'
            else:
                agent.endpoint += '/indy'


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
