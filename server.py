"""Tiny stdlib HTTP server: static pages + JSON API. Run: python server.py"""

import json
import mimetypes
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from calendar_service import ApiError, CalendarService

ROOT = Path(__file__).parent.resolve()
PUBLIC = ROOT / "public"
MAX_BODY = 10 * 1024
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "Content-Security-Policy": "default-src 'self'; style-src 'self' 'unsafe-inline'",
}


def make_handler(service):
    class Handler(BaseHTTPRequestHandler):
        def _send(self, status, body, content_type):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            for key, value in SECURITY_HEADERS.items():
                self.send_header(key, value)
            self.end_headers()
            self.wfile.write(body)

        def _json(self, status, payload):
            self._send(status, json.dumps(payload).encode(), "application/json")

        def _token(self):
            header = self.headers.get("Authorization", "")
            return header[7:] if header.startswith("Bearer ") else ""

        def _body(self):
            length = int(self.headers.get("Content-Length") or 0)
            if length > MAX_BODY:
                raise ApiError(413, "That request is too chatty.")
            try:
                data = json.loads(self.rfile.read(length) or b"{}")
            except ValueError:
                raise ApiError(400, "Invalid JSON.")
            if not isinstance(data, dict):
                raise ApiError(400, "Invalid JSON.")
            return data

        def _api(self, action):
            if self.command == "GET" and self.path == "/api/calendar":
                return service.calendar(self._token())
            if self.command != "POST":
                raise ApiError(404, "Not found.")
            body = self._body()
            token = self._token()
            if self.path == "/api/login":
                return service.login(body.get("name"))
            routes = {
                "/api/block": lambda: service.block(token, body.get("items")),
                "/api/unblock": lambda: service.unblock(token, body.get("slot")),
                "/api/book": lambda: service.book(token, body.get("slot"), body.get("kind"), body.get("note")),
                "/api/cancel": lambda: service.cancel(token, body.get("slot")),
            }
            if self.path not in routes:
                raise ApiError(404, "Not found.")
            routes[self.path]()
            return {"ok": True}

        def _handle(self):
            try:
                if self.path.startswith("/api/"):
                    self._json(200, self._api(self.path))
                elif self.command == "GET":
                    self._static()
                else:
                    raise ApiError(405, "Method not allowed.")
            except ApiError as error:
                self._json(error.status, {"error": error.message})
            except Exception:
                self._json(500, {"error": "Nishita's server is overworked too. Try again."})

        def _static(self):
            relative = self.path.split("?", 1)[0].lstrip("/") or "index.html"
            target = (PUBLIC / relative).resolve()
            if PUBLIC not in target.parents or not target.is_file():
                raise ApiError(404, "Page not found. Like Nishita's weekends.")
            content_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
            if content_type.startswith("text/") or content_type.endswith("javascript"):
                content_type += "; charset=utf-8"
            self._send(200, target.read_bytes(), content_type)

        do_GET = do_POST = do_PUT = do_DELETE = _handle

        def log_message(self, fmt, *args):
            return

    return Handler


def main():
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))
    service = CalendarService(os.environ.get("DATA_FILE", str(ROOT / "data.json")))
    server = ThreadingHTTPServer((host, port), make_handler(service))
    print(f"Book Nishita is live at http://{host}:{port}  (Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
