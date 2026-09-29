"""Loopback-only UI fixture preview. No business DB, credentials or AI provider.

Uses the real assistant template with a minimal shell and explicit sample responses.
Run: python scripts/preview_assistant_modes.py
"""
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from django.conf import settings
settings.configure(DEBUG=True, STATIC_URL="/static/", USE_I18N=False)
import django
django.setup()
from django.template import Engine, Context

engine = Engine(loaders=[
    ("django.template.loaders.locmem.Loader", {"base.html": '''<!doctype html>
<html lang="vi"><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<link rel="stylesheet" href="/static/css/style.css">
<body><p>KIỂM THỬ GIAO DIỆN — dữ liệu mẫu, không kết nối database/API AI.</p>
{% block content %}{% endblock %}</body></html>'''}),
    ("django.template.loaders.filesystem.Loader", [str(ROOT / "templates")]),
])
page = engine.get_template("ai/assistant.html").render(Context({"active_workspace": {"name": "Preview fixture"}, "sessions": []})).encode()


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            content, kind = page, "text/html; charset=utf-8"
        elif self.path == "/static/css/style.css":
            content, kind = (ROOT / "static/css/style.css").read_bytes(), "text/css"
        else:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Type", kind)
        self.end_headers()
        self.wfile.write(content)

    def do_POST(self):
        if self.path != "/api/v1/ai/chat/":
            self.send_error(404)
            return
        self.rfile.read(min(int(self.headers.get("Content-Length", "0")), 10000))
        payload = {"success": True, "data": {"session_id": 1,
            "answer": "Dữ liệu mẫu kiểm thử: tổng doanh thu 100 VND từ 1 đơn hàng.",
            "sources": [], "tools_used": [], "generation_metadata": {"mode": "DETERMINISTIC"}}}
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(json.dumps(payload, ensure_ascii=False).encode())


if __name__ == "__main__":
    print("Fixture preview: http://127.0.0.1:8012/", flush=True)
    HTTPServer(("127.0.0.1", 8012), Handler).serve_forever()
