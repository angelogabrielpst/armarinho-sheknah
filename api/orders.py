import json

from server import connect
from vercel_api import APIHandler, ensure_database


class handler(APIHandler):
    def do_POST(self):
        try:
            ensure_database()
            data = self.read_json()
            items = data.get("items")
            if not isinstance(items, list) or not items:
                return self.send_json(400, {"error": "Pedido inválido."})

            verified_items = []
            subtotal = 0
            with connect() as db:
                for item in items:
                    if not isinstance(item, dict):
                        return self.send_json(400, {"error": "Item inválido."})
                    product_id = str(item.get("id", ""))
                    try:
                        quantity = int(item.get("quantity", 0))
                    except (TypeError, ValueError):
                        quantity = 0
                    if quantity <= 0 or quantity > 99:
                        return self.send_json(400, {"error": "Quantidade inválida."})
                    product = db.execute(
                        "SELECT id, name, price FROM products WHERE id = ?",
                        (product_id,),
                    ).fetchone()
                    if not product:
                        return self.send_json(400, {"error": "Um produto do pedido não está mais disponível."})
                    price = float(product["price"])
                    subtotal += price * quantity
                    verified_items.append({
                        "id": product["id"],
                        "name": product["name"],
                        "price": price,
                        "quantity": quantity,
                    })
                cursor = db.execute(
                    "INSERT INTO orders (items, subtotal) VALUES (?, ?)",
                    (json.dumps(verified_items, ensure_ascii=False), subtotal),
                )
            self.send_json(201, {"id": cursor.lastrowid, "status": "pendente"})
        except Exception:
            self.internal_error()
