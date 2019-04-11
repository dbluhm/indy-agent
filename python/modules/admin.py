import aiohttp_jinja2
import jinja2
import json
import socket
from indy import did, wallet, non_secrets, pairwise
from indy_sdk_utils import get_wallet_records

from router.simple_router import SimpleRouter
from agent import Agent
from message import Message
from . import Module

class Admin(Module):
    FAMILY_NAME = "admin"
    VERSION = "1.0"
    FAMILY = "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/" + FAMILY_NAME + "/" + VERSION + "/"

    STATE = FAMILY + "state"
    STATE_REQUEST = FAMILY + "state_request"

    def __init__(self, agent):
        self.agent = agent
        self.router = SimpleRouter()
        self.router.register(self.STATE_REQUEST, self.state_request)

    async def route(self, msg: Message) -> Message:
        return await self.router.route(msg)

    async def state_request(self, _) -> Message:
        if self.agent.initialized:
            invitations = await get_wallet_records(self.agent.wallet_handle, "invitations")

            # load up pairwise connections
            pairwise_records = []
            agent_pairwises_list_str = await pairwise.list_pairwise(self.agent.wallet_handle)
            agent_pairwises_list = json.loads(agent_pairwises_list_str)
            for agent_pairwise_str in agent_pairwises_list:
                pairwise_record = json.loads(agent_pairwise_str)
                pairwise_record['metadata'] = json.loads(pairwise_record['metadata'])
                pairwise_records.append(pairwise_record)

            await self.agent.send_admin_message(
                Message({
                    '@type': self.STATE,
                    'content': {
                        'initialized': self.agent.initialized,
                        'agent_name': self.agent.owner,
                        'invitations': invitations,
                        'pairwise_connections': pairwise_records,
                    }
                })
            )
        else:
            await self.agent.send_admin_message(
                Message({
                    '@type': self.STATE,
                    'content': {
                        'initialized': self.agent.initialized,
                        }
                    })
            )


@aiohttp_jinja2.template('index.html')
async def root(request):
    agent = request.app['agent']
    local_ip = socket.gethostbyname(socket.gethostname())
    agent.endpoint = request.url.scheme + '://' + local_ip
    if request.url.port is not None:
        agent.endpoint += ':' + str(request.url.port) + '/indy'
    else:
        agent.endpoint += '/indy'
    print('Agent Endpoint : "{}"'.format(agent.endpoint))
    return {'agent_admin_key': agent.agent_admin_key}
