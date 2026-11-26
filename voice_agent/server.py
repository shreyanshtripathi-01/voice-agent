"""Zero-dependency HTTP API + static file server for the voice agent UI."""

from __future__ import annotations

import json
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from . import crm
from .agent import SalesAgent
from .config import HOST, PORT, ROOT, STATIC_DIR

AGENT = SalesAgent()


class Handler(BaseHTTPRequestHandler):
    server_version = "FortivexVoiceAgent/1.0"

    # --------------------------------------------------------------- helpers
    def _json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def _cors(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")

    def _body(self) -> dict:
        length = int(self.headers.get("Content-Length") or 0)
        if length == 0:
            return {}
        if length > 1_000_000:
            return {}
        try:
            return json.loads(self.rfile.read(length).decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return {}

    def _static(self, relative: str) -> None:
        target = (STATIC_DIR / relative).resolve()
        if STATIC_DIR.resolve() not in target.parents and target != STATIC_DIR.resolve():
            self._json(403, {"error": "Forbidden"})
            return
        if not target.is_file():
            self._json(404, {"error": "Not found"})
            return
        ctype = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        body = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", ctype + ("; charset=utf-8" if ctype.startswith("text/") else ""))
        self.send_header("Content-Length", str(len(body)))
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def _root_file(self, relative: str, ctype: str = "") -> None:
        target = (ROOT / relative).resolve()
        if ROOT.resolve() not in target.parents and target != ROOT.resolve():
            self._json(403, {"error": "Forbidden"})
            return
        if not target.is_file():
            self._json(404, {"error": "Not found"})
            return
        ctype = ctype or mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        body = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", ctype + ("; charset=utf-8" if ctype.startswith(("text/", "image/svg")) else ""))
        self.send_header("Content-Length", str(len(body)))
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args) -> None:
        print(f"[http] {self.address_string()} {fmt % args}")

    # --------------------------------------------------------------- verbs
    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path, query = parsed.path, parse_qs(parsed.query)
        routes = {
            "/": lambda: self._static("index.html"),
            "/report": lambda: self._root_file("REPORT.md", "text/plain"),
            "/readme": lambda: self._root_file("README.md", "text/plain"),
            "/api/health": lambda: self._json(200, {"ok": True, "service": "fortivex-voice-agent",
                                                    "sessions": len(AGENT.sessions)}),
            "/api/leads": lambda: self._json(200, {"ok": True, "leads": crm.list_leads()}),
            "/api/session": lambda: self._json(200, {"ok": True,
                                                     "session": AGENT.get_session(query.get("id", [""])[0])}),
            "/api/knowledge": lambda: self._json(200, {"ok": True,
                                                       "chunks": [{"doc": c["doc"], "section": c["section"]}
                                                                  for c in AGENT.kb.chunks]}),
        }
        if path in routes:
            routes[path]()
        elif path.startswith("/static/"):
            self._static(path[len("/static/"):])
        elif path.startswith("/docs/"):
            self._root_file("docs/" + path[len("/docs/"):])
        else:
            self._json(404, {"error": "Not found"})

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        data = self._body()
        if path == "/api/session":
            self._json(200, AGENT.start_session(data.get("lang", "en-IN")))
        elif path == "/api/message":
            self._json(200, AGENT.handle_message(data.get("session_id", ""),
                                                 data.get("text", ""), data.get("lang", "")))
        elif path == "/api/book":
            self._json(200, AGENT.book(data.get("session_id", ""), data.get("date", ""), data.get("time", "")))
        elif path == "/api/end":
            self._json(200, AGENT.end_call(data.get("session_id", "")))
        elif path == "/api/reset":
            crm.reset_demo_data()
            AGENT.sessions.clear()
            self._json(200, {"ok": True, "message": "Demo data reset."})
        else:
            self._json(404, {"error": "Not found"})


def main() -> None:
    crm.init_db()
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"\n  Fortivex AI — Autonomous Sales Voice Agent")
    print(f"  Open http://{HOST}:{PORT}  in Chrome or Edge\n")
    print("  Press Ctrl+C to stop.\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
