"""
Handlers required by the web operations
"""

import uuid
from yadacoin.basehandlers import BaseHandler
from yadacoin.graphutils import GraphUtils as GU
from yadacoin.blockchainutils import BU


class HomeHandler(BaseHandler):

    async def get(self):
        """
        :return:
        """
        self.render(
            "index.html",
            yadacoin=self.yadacoin_vars,
            username=self.get_secure_cookie("username"),
            rid=self.get_secure_cookie("rid")
        )


class AuthenticatedHandler(BaseHandler):
    async def get(self):
        config = self.config
        rid = self.get_query_argument('rid')
        if not rid:
            return '{"error": "rid not in query params"}', 400

        txn_id = self.get_query_argument('id')
        
        bulletin_secret = self.get_query_argument('bulletin_secret')
        if not bulletin_secret:
            return '{"error": "bulletin_secret not in query params"}', 400

        if not self.get_secure_cookie("siginin_code"):
            self.set_secure_cookie("siginin_code", str(uuid.uuid4()))

        result = GU().verify_message(
            rid,
            self.get_secure_cookie("siginin_code"),
            config.public_key,
            txn_id.replace(' ', '+'))

        if result[1]:
            self.set_secure_cookie("rid", rid)

            username_txns = [x for x in GU().search_rid(rid)]
            self.set_secure_cookie("username", username_txns[0]['relationship']['their_username'])

            return self.render_as_json({
                'authenticated': True
            })
        
        return self.render_as_json({
            'authenticated': False
        })

class LoginHandler(BaseHandler):

    async def get(self):
        if not self.get_secure_cookie("siginin_code"):
            self.set_secure_cookie("siginin_code", str(uuid.uuid4()))

        self.render_as_json({
            'signin_code': self.get_secure_cookie("siginin_code").decode('utf-8')
        })


class LogoutHandler(BaseHandler):

    def get(self):
        if self.get_secure_cookie("siginin_code"):
            self.set_secure_cookie("siginin_code", None)

        if self.get_secure_cookie("rid"):
            self.set_secure_cookie("rid", None)

        if self.get_secure_cookie("username"):
            self.set_secure_cookie("username", None)

        self.render_as_json({
            'authenticated': False
        })

class HashrateAPIHandler(BaseHandler):

    async def get(self):
        max_target = 0xffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff
        config = self.config
        blocks = config.BU.get_blocks()
        total_nonce = 0
        periods = []
        last_time = None
        for block in blocks:
            difficulty = max_target / int(block.get('target'), 16)
            if block.get('index') == 0:
                start_timestamp = block.get('time')
            if last_time:
                if int(block.get('time')) > last_time:
                    periods.append({
                        'hashrate': (((int(block.get('index')) / 144) * difficulty) * 2**32) / 600 / 100,
                        'index': block.get('index'),
                        'elapsed_time': (int(block.get('time')) - last_time)
                    })
            last_time = int(block.get('time'))
            total_nonce += block.get('nonce')
        sorted(periods, key=lambda x: x['index'])
        total_time_elapsed = int(block.get('time')) - int(start_timestamp)
        network_hash_rate =  total_nonce / int(total_time_elapsed)
        self.render_as_json({
            'stats': {
                'network_hash_rate': network_hash_rate,
                'total_time_elapsed': total_time_elapsed,
                'total_nonce': total_nonce,
                'periods': periods
            }
        })


WEB_HANDLERS = [
    (r'/', HomeHandler),
    (r'/authenticated', AuthenticatedHandler),
    (r'/login', LoginHandler),
    (r'/logout', LogoutHandler),
    (r'/api-stats', HashrateAPIHandler),
]
