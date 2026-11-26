import json
from urllib.parse import parse_qs, urlparse

from server import connect, parse_json_value
from vercel_api import APIHandler, ensure_database


class handler(APIHandler):
    def do_GET(self):
        try:
            ensure_database()
            client_id = parse_qs(urlparse(self.path).query).get("client_id", [""])[0]
            if not client_id or len(client_id) > 80:
                return self.send_json(400, {"error": "Identificador da sacola inválido."})
            with connect() as db:
                row = db.execute("SELECT items FROM carts WHERE client_id = ?", (client_id,)).fetchone()
            self.send_json(200, parse_json_value(row["items"]) if row else [])
        except Exception:
            self.internal_error()

    def do_POST(self):
        try:
            ensure_database()
            data = self.read_json()
            client_id = str(data.get("client_id", ""))
            items = data.get("items")
            if not client_id or len(client_id) > 80 or not isinstance(items, list):
                return self.send_json(400, {"error": "Dados da sacola inválidos."})
            normalized_items = []
            with connect() as db:
                for item in items:
                    product_id = str(item.get("id", "")) if isinstance(item, dict) else ""
                    try:
                        quantity = int(item.get("quantity", 0))
                    except (TypeError, ValueError):
                        quantity = 0
                    exists = db.execute("SELECT 1 FROM products WHERE id = ?", (product_id,)).fetchone()
                    if exists and 0 < quantity <= 99:
                        normalized_items.append({"id": product_id, "quantity": quantity})
                db.execute(
                    "INSERT INTO carts (client_id, items, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP) "
                    "ON CONFLICT(client_id) DO UPDATE SET items = excluded.items, updated_at = CURRENT_TIMESTAMP",
                    (client_id, json.dumps(normalized_items)),
                )
            self.send_json(200, normalized_items)
        except Exception:
            self.internal_error()
