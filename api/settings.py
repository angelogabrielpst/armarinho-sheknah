from server import connect
from vercel_api import APIHandler, ensure_database


class handler(APIHandler):
    def do_GET(self):
        try:
            ensure_database()
            with connect() as db:
                row = db.execute("SELECT value FROM settings WHERE `key` = 'whatsapp'").fetchone()
            self.send_json(200, {"whatsapp": row["value"] if row else "5531989319971"})
        except Exception:
            self.internal_error()
