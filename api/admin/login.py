from server import ADMIN_PASSWORD, create_admin_token
from vercel_api import APIHandler


class handler(APIHandler):
    def do_POST(self):
        try:
            data = self.read_json()
            if not ADMIN_PASSWORD or data.get("password") != ADMIN_PASSWORD:
                return self.send_json(401, {"error": "Senha incorreta."})
            self.send_json(200, {"token": create_admin_token()})
        except Exception:
            self.internal_error()
