import base64
from datetime import date, datetime
from decimal import Decimal
from importlib import import_module
import hashlib
import hmac
import json
import mimetypes
import os
import secrets
import sqlite3
import sys
import time
import urllib.parse
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "papelaria.db"
UPLOAD_DIR = Path(os.environ.get("UPLOAD_DIR", str(ROOT / "uploads"))).resolve()
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD") or ("admin123" if not os.environ.get("VERCEL") else "")
ADMIN_TOKEN_SECRET = os.environ.get("ADMIN_TOKEN_SECRET") or ADMIN_PASSWORD
MYSQL_HOST = os.environ.get("MYSQL_HOST") or os.environ.get("MYSQLHOST")
MYSQL_PORT = int(os.environ.get("MYSQL_PORT") or os.environ.get("MYSQLPORT") or "3306")
MYSQL_USER = os.environ.get("MYSQL_USER") or os.environ.get("MYSQLUSER") or ""
MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD") or os.environ.get("MYSQLPASSWORD") or ""
MYSQL_DATABASE = os.environ.get("MYSQL_DATABASE") or os.environ.get("MYSQLDATABASE") or ""
MYSQL_SSL_CA = os.environ.get("MYSQL_SSL_CA")
ALLOWED_ORIGINS = {
    origin.strip()
    for origin in os.environ.get(
        "ALLOWED_ORIGINS", "http://localhost:8000,http://127.0.0.1:8000"
    ).split(",")
    if origin.strip()
}
ADMIN_TOKEN_TTL = 8 * 60 * 60

STARTER_PRODUCTS = [
    {"id": "starter-1", "name": "Caderno Meu Lugar", "category": "Cadernos", "price": 42.90, "description": "Um espaço todo seu para ideias, planos e rabiscos.", "image": "", "symbol": "✳"},
    {"id": "starter-2", "name": "Kit Canetas Jardim", "category": "Escrita", "price": 24.90, "description": "Cores bonitas para deixar cada palavra especial.", "image": "", "symbol": "✿"},
    {"id": "starter-3", "name": "Planner da Semana", "category": "Organização", "price": 36.50, "description": "Organize seus dias com leveza e um toque de cor.", "image": "", "symbol": "☼"},
    {"id": "starter-4", "name": "Bloco Boas Ideias", "category": "Criatividade", "price": 18.90, "description": "Para aquela ideia boa que aparece de repente.", "image": "", "symbol": "♡"},
    {"id": "starter-5", "name": "Marca-páginas Flores", "category": "Presentes", "price": 12.50, "description": "Um carinho para acompanhar a próxima leitura.", "image": "", "symbol": "❀"},
    {"id": "starter-6", "name": "Estojo Dia Feliz", "category": "Organização", "price": 32.90, "description": "Seu material favorito sempre por perto.", "image": "", "symbol": "✦"},
    {"id": "starter-7", "name": "Cartões para Presentear", "category": "Presentes", "price": 16.90, "description": "Palavras escritas à mão fazem toda a diferença.", "image": "", "symbol": "♡"},
    {"id": "starter-8", "name": "Aquarela Pequenos Mundos", "category": "Criatividade", "price": 49.90, "description": "Um convite colorido para experimentar e criar.", "image": "", "symbol": "✿"},
]


def create_admin_token():
    expires_at = str(int(time.time()) + ADMIN_TOKEN_TTL)
    signature = hmac.new(ADMIN_TOKEN_SECRET.encode(), expires_at.encode(), hashlib.sha256).hexdigest()
    return f"{expires_at}.{signature}"


def verify_admin_token(token):
    try:
        expires_at, signature = token.split(".", 1)
        if int(expires_at) < int(time.time()):
            return False
        expected = hmac.new(ADMIN_TOKEN_SECRET.encode(), expires_at.encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(signature, expected)
    except (AttributeError, ValueError):
        return False


class MySQLRow(dict):
    def __getitem__(self, key):
        if isinstance(key, int):
            return tuple(self.values())[key]
        return super().__getitem__(key)


class MySQLResult:
    def __init__(self, cursor):
        self.cursor = cursor
        self.lastrowid = cursor.lastrowid
        self.has_rows = cursor.with_rows
        if not self.has_rows:
            self.cursor.close()

    def fetchone(self):
        row = self.cursor.fetchone()
        self.cursor.close()
        return MySQLRow(row) if row is not None else None

    def fetchall(self):
        rows = self.cursor.fetchall()
        self.cursor.close()
        return [MySQLRow(row) for row in rows]


class MySQLDatabase:
    def __init__(self, connection):
        self.connection = connection

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type:
            self.connection.rollback()
        else:
            self.connection.commit()
        self.connection.close()

    @staticmethod
    def prepare(query):
        query = query.replace("INSERT OR IGNORE INTO", "INSERT IGNORE INTO")
        query = query.replace(
            "ON CONFLICT(client_id) DO UPDATE SET items = excluded.items, updated_at = CURRENT_TIMESTAMP",
            "ON DUPLICATE KEY UPDATE items = VALUES(items), updated_at = CURRENT_TIMESTAMP",
        )
        query = query.replace(
            "ON CONFLICT(`key`) DO UPDATE SET value = excluded.value",
            "ON DUPLICATE KEY UPDATE value = VALUES(value)",
        )
        return query.replace("?", "%s")

    def execute(self, query, parameters=()):
        cursor = self.connection.cursor(dictionary=True)
        cursor.execute(self.prepare(query), parameters)
        return MySQLResult(cursor)

    def executemany(self, query, parameters):
        cursor = self.connection.cursor(dictionary=True)
        cursor.executemany(self.prepare(query), parameters)
        return MySQLResult(cursor)


def connect():
    if MYSQL_HOST:
        if not MYSQL_USER or not MYSQL_PASSWORD or not MYSQL_DATABASE:
            raise RuntimeError("MYSQL_USER, MYSQL_PASSWORD e MYSQL_DATABASE precisam estar configurados.")
        try:
            mysql_connector = import_module("mysql.connector")
        except ImportError as error:
            raise RuntimeError("Instale as dependências de requirements.txt para usar MySQL.") from error

        config = {
            "host": MYSQL_HOST,
            "port": MYSQL_PORT,
            "user": MYSQL_USER,
            "password": MYSQL_PASSWORD,
            "database": MYSQL_DATABASE,
            "connection_timeout": 10,
        }
        if MYSQL_SSL_CA:
            config["ssl_ca"] = MYSQL_SSL_CA
        return MySQLDatabase(mysql_connector.connect(**config))

    if os.environ.get("VERCEL"):
        raise RuntimeError("Configure as variáveis MYSQL_* no projeto Vercel; SQLite não é persistente na Vercel.")

    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def json_default(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    raise TypeError(f"Tipo nao serializavel: {type(value).__name__}")


def parse_json_value(value):
    return json.loads(value) if isinstance(value, str) else value


def initialize_database():
    if MYSQL_HOST:
        statements = [
            """CREATE TABLE IF NOT EXISTS products (
                id VARCHAR(100) PRIMARY KEY,
                name VARCHAR(70) NOT NULL,
                category VARCHAR(100) NOT NULL,
                price DECIMAL(10, 2) NOT NULL,
                description TEXT,
                image TEXT,
                symbol VARCHAR(16),
                is_new BOOLEAN NOT NULL DEFAULT FALSE,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
            """CREATE TABLE IF NOT EXISTS settings (
                `key` VARCHAR(80) PRIMARY KEY,
                value TEXT NOT NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
            """CREATE TABLE IF NOT EXISTS orders (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                items JSON NOT NULL,
                subtotal DECIMAL(10, 2) NOT NULL,
                status VARCHAR(32) NOT NULL DEFAULT 'pendente',
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
            """CREATE TABLE IF NOT EXISTS carts (
                client_id VARCHAR(80) PRIMARY KEY,
                items JSON NOT NULL,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
        ]
        with connect() as db:
            for statement in statements:
                db.execute(statement)
    else:
        with connect() as db:
            db.executescript("""
            CREATE TABLE IF NOT EXISTS products (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                price REAL NOT NULL,
                description TEXT,
                image TEXT,
                symbol TEXT,
                is_new INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                items TEXT NOT NULL,
                subtotal REAL NOT NULL,
                status TEXT NOT NULL DEFAULT 'pendente',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS carts (
                client_id TEXT PRIMARY KEY,
                items TEXT NOT NULL,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            """)

    with connect() as db:
        db.executemany(
            "INSERT OR IGNORE INTO products (id, name, category, price, description, image, symbol) VALUES (?, ?, ?, ?, ?, ?, ?)",
            [(p["id"], p["name"], p["category"], p["price"], p["description"], p["image"], p["symbol"]) for p in STARTER_PRODUCTS],
        )
        db.execute("INSERT OR IGNORE INTO settings (`key`, value) VALUES (?, ?)", ("whatsapp", "5531989319971"))


class StoreHandler(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        sys.stdout.write("%s - - [%s] %s\n" % (self.address_string(), self.log_date_time_string(), format % args))

    def end_headers(self):
        origin = self.headers.get("Origin")
        if origin and origin in ALLOWED_ORIGINS:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Admin-Token")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(204)
        self.end_headers()

    def send_json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False, default=json_default).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def read_json(self):
        length = int(self.headers.get("Content-Length", "0"))
        if not length:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def is_admin(self):
        token = self.headers.get("X-Admin-Token", "")
        return verify_admin_token(token)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/api/products":
            with connect() as db:
                rows = db.execute("SELECT * FROM products ORDER BY created_at DESC").fetchall()
                return self.send_json(200, [dict(row) for row in rows])

        if path == "/api/settings":
            with connect() as db:
                row = db.execute("SELECT value FROM settings WHERE `key` = 'whatsapp'").fetchone()
                return self.send_json(200, {"whatsapp": row["value"] if row else "5531989319971"})

        if path == "/api/cart":
            client_id = urllib.parse.parse_qs(parsed.query).get("client_id", [""])[0]
            if not client_id or len(client_id) > 80:
                return self.send_json(400, {"error": "Identificador da sacola invalido"})
            with connect() as db:
                row = db.execute("SELECT items FROM carts WHERE client_id = ?", (client_id,)).fetchone()
            return self.send_json(200, parse_json_value(row["items"]) if row else [])

        if path.startswith("/uploads/"):
            filename = urllib.parse.unquote(path.removeprefix("/uploads/"))
            if not filename or Path(filename).name != filename:
                return self.send_error(404)
            file_path = UPLOAD_DIR / filename
            try:
                content = file_path.read_bytes()
            except FileNotFoundError:
                return self.send_error(404)
            self.send_response(200)
            self.send_header("Content-Type", mimetypes.guess_type(filename)[0] or "application/octet-stream")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
            return

        return super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/api/admin/login":
            data = self.read_json()
            if not ADMIN_PASSWORD or data.get("password") != ADMIN_PASSWORD:
                return self.send_json(401, {"error": "Senha incorreta"})
            return self.send_json(200, {"token": create_admin_token()})

        if path == "/api/orders":
            data = self.read_json()
            items = data.get("items")
            subtotal = data.get("subtotal")
            if not isinstance(items, list) or not items or not isinstance(subtotal, (int, float)):
                return self.send_json(400, {"error": "Pedido invalido"})
            with connect() as db:
                cursor = db.execute(
                    "INSERT INTO orders (items, subtotal) VALUES (?, ?)",
                    (json.dumps(items, ensure_ascii=False), float(subtotal)),
                )
            return self.send_json(201, {"id": cursor.lastrowid, "status": "pendente"})

        if path == "/api/cart":
            data = self.read_json()
            client_id = str(data.get("client_id", ""))
            items = data.get("items")
            if not client_id or len(client_id) > 80 or not isinstance(items, list):
                return self.send_json(400, {"error": "Dados da sacola invalidos"})
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
            return self.send_json(200, normalized_items)

        if path == "/api/products":
            if not self.is_admin():
                return self.send_json(401, {"error": "Nao autorizado"})
            data = self.read_json()
            name = str(data.get("name", "")).strip()
            category = str(data.get("category", "")).strip()
            try:
                price = float(data.get("price"))
            except (TypeError, ValueError):
                return self.send_json(400, {"error": "Preco invalido"})
            if not name or not category or price <= 0:
                return self.send_json(400, {"error": "Nome, categoria e preco sao obrigatorios"})

            image = str(data.get("image", ""))
            if image.startswith("data:image/"):
                try:
                    header, encoded = image.split(",", 1)
                    extension = header.split(";")[0].split("/")[-1].lower()
                    if extension == "jpeg":
                        extension = "jpg"
                    if extension not in ("jpg", "png", "webp"):
                        raise ValueError("Formato nao suportado")
                    filename = f"{secrets.token_hex(12)}.{extension}"
                    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
                    (UPLOAD_DIR / filename).write_bytes(base64.b64decode(encoded))
                    image = f"uploads/{filename}"
                except Exception:
                    return self.send_json(400, {"error": "Imagem invalida"})

            product_id = str(data.get("id") or f"product-{secrets.token_hex(8)}")
            with connect() as db:
                db.execute(
                    "INSERT INTO products (id, name, category, price, description, image, symbol) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (product_id, name, category, price, str(data.get("description", "")).strip(), image, "✳"),
                )
            return self.send_json(201, {"id": product_id})

        return self.send_json(404, {"error": "Rota nao encontrada"})

    def do_PUT(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/settings/whatsapp":
            if not self.is_admin():
                return self.send_json(401, {"error": "Nao autorizado"})
            data = self.read_json()
            phone = "".join(ch for ch in str(data.get("whatsapp", "")) if ch.isdigit())
            if len(phone) < 12 or len(phone) > 13:
                return self.send_json(400, {"error": "WhatsApp invalido"})
            with connect() as db:
                db.execute("UPDATE settings SET value = ? WHERE `key` = 'whatsapp'", (phone,))
            return self.send_json(200, {"whatsapp": phone})
        return self.send_json(404, {"error": "Rota nao encontrada"})

    def do_DELETE(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        if path == "/api/product":
            product_id = urllib.parse.parse_qs(parsed.query).get("id", [""])[0]
        elif path.startswith("/api/products/"):
            product_id = urllib.parse.unquote(path.split("/", 3)[3])
        else:
            return self.send_json(404, {"error": "Rota nao encontrada"})

        if not product_id:
            return self.send_json(400, {"error": "ID do produto obrigatório"})
        if product_id:
            if not self.is_admin():
                return self.send_json(401, {"error": "Nao autorizado"})
            with connect() as db:
                product = db.execute("SELECT image FROM products WHERE id = ?", (product_id,)).fetchone()
                db.execute("DELETE FROM products WHERE id = ?", (product_id,))
            if product and product["image"] and product["image"].startswith("uploads/"):
                file_path = UPLOAD_DIR / Path(product["image"]).name
                if file_path.exists():
                    file_path.unlink()
            return self.send_json(200, {"deleted": product_id})


def run(port=None):
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    initialize_database()
    os.chdir(ROOT)
    port = int(os.environ.get("PORT") or port or 8000)
    server = ThreadingHTTPServer(("0.0.0.0", port), StoreHandler)
    database_name = "MySQL" if MYSQL_HOST else "SQLite"
    print(f"Armarinho SHEK-NAH usando {database_name} na porta {port}")
    server.serve_forever()


if __name__ == "__main__":
    run(int(sys.argv[1]) if len(sys.argv) > 1 else None)
