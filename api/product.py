from urllib.parse import parse_qs, urlparse

from server import connect
from vercel_api import APIHandler, delete_product_image, ensure_database


class handler(APIHandler):
    def do_DELETE(self):
        if not self.is_admin():
            return self.send_json(401, {"error": "Não autorizado."})
        try:
            ensure_database()
            product_id = parse_qs(urlparse(self.path).query).get("id", [""])[0]
            if not product_id:
                return self.send_json(400, {"error": "ID do produto obrigatório."})
            with connect() as db:
                product = db.execute("SELECT image FROM products WHERE id = ?", (product_id,)).fetchone()
                db.execute("DELETE FROM products WHERE id = ?", (product_id,))
            if product:
                delete_product_image(product["image"])
            self.send_json(200, {"deleted": product_id})
        except Exception:
            self.internal_error()
