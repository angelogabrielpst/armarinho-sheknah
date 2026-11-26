from server import connect
from vercel_api import APIHandler, ensure_database


class handler(APIHandler):
    def do_PUT(self):
        if not self.is_admin():
            return self.send_json(401, {"error": "Não autorizado."})
        try:
            ensure_database()
            data = self.read_json()
            phone = "".join(character for character in str(data.get("whatsapp", "")) if character.isdigit())
            if len(phone) < 12 or len(phone) > 13:
                return self.send_json(400, {"error": "WhatsApp inválido."})
            with connect() as db:
                db.execute(
                    "INSERT INTO settings (`key`, value) VALUES (?, ?) "
                    "ON CONFLICT(`key`) DO UPDATE SET value = excluded.value",
                    ("whatsapp", phone),
                )
            self.send_json(200, {"whatsapp": phone})
        except Exception:
            self.internal_error()
