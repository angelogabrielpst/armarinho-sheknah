import base64
import json
import os
import secrets
import threading
import traceback
from importlib import import_module
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse

from server import (
    ADMIN_PASSWORD,
    ALLOWED_ORIGINS,
    UPLOAD_DIR,
    connect,
    create_admin_token,
    initialize_database,
    json_default,
    parse_json_value,
    verify_admin_token,
)

_DATABASE_READY = False
_DATABASE_LOCK = threading.Lock()


def ensure_database():
    global _DATABASE_READY
    if _DATABASE_READY:
        return
    with _DATABASE_LOCK:
        if not _DATABASE_READY:
            initialize_database()
            _DATABASE_READY = True


class APIHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        return

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
        if length > 4_000_000:
            raise ValueError("A solicitação excede o limite permitido.")
        if not length:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def is_admin(self):
        return verify_admin_token(self.headers.get("X-Admin-Token", ""))

    def internal_error(self):
        traceback.print_exc()
        self.send_json(500, {"error": "Erro interno ao processar a solicitação."})


def store_product_image(data_url):
    if not isinstance(data_url, str) or not data_url.startswith("data:image/"):
        raise ValueError("Imagem inválida.")
    header, encoded = data_url.split(",", 1)
    media_type = header.split(";")[0].removeprefix("data:").lower()
    extensions = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}
    extension = extensions.get(media_type)
    if not extension:
        raise ValueError("Formato de imagem não suportado.")
    image_bytes = base64.b64decode(encoded, validate=True)
    if not image_bytes or len(image_bytes) > 2 * 1024 * 1024:
        raise ValueError("A imagem deve ter até 2 MB.")

    filename = f"products/{secrets.token_hex(16)}.{extension}"
    if os.environ.get("VERCEL"):
        blob = import_module("vercel.blob.sync")

        uploaded = blob.put_blob(
            filename,
            image_bytes,
            access="public",
            content_type=media_type,
        )
        return uploaded.url

    local_name = Path(filename).name
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    (UPLOAD_DIR / local_name).write_bytes(image_bytes)
    return f"uploads/{local_name}"


def delete_product_image(image):
    if not image:
        return
    parsed = urlparse(image)
    if parsed.hostname and parsed.hostname.endswith("blob.vercel-storage.com"):
        blob = import_module("vercel.blob.sync")

        blob.delete_blob(image)
    elif image.startswith("uploads/"):
        (UPLOAD_DIR / Path(image).name).unlink(missing_ok=True)
