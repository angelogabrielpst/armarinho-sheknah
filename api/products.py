import json
import secrets

from server import connect
from vercel_api import APIHandler, ensure_database, store_product_image


class handler(APIHandler):
    def do_GET(self):
        try:
            ensure_database()
            with connect() as db:
                products = [dict(row) for row in db.execute("SELECT * FROM products ORDER BY created_at DESC").fetchall()]
            self.send_json(200, products)
        except Exception:
            self.internal_error()

    def do_POST(self):
        if not self.is_admin():
            return self.send_json(401, {"error": "Não autorizado."})
        try:
            ensure_database()
            data = self.read_json()
            name = str(data.get("name", "")).strip()
            category = str(data.get("category", "")).strip()
            try:
                price = float(data.get("price"))
            except (TypeError, ValueError):
                return self.send_json(400, {"error": "Preço inválido."})
            if not name or not category or price <= 0:
                return self.send_json(400, {"error": "Nome, categoria e preço são obrigatórios."})

            image = data.get("image", "")
            if image:
                image = store_product_image(image)
            product_id = str(data.get("id") or f"product-{secrets.token_hex(8)}")
            with connect() as db:
                db.execute(
                    "INSERT INTO products (id, name, category, price, description, image, symbol) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (product_id, name, category, price, str(data.get("description", "")).strip(), image, "✳"),
                )
            self.send_json(201, {"id": product_id})
        except ValueError as error:
            self.send_json(400, {"error": str(error)})
        except Exception:
            self.internal_error()
