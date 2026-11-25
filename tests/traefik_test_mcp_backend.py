import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        with open("/app/.tokens", encoding="utf-8") as source:
            tokens = json.load(source)
        expected = "Bearer " + tokens["nita-lab"]["token"]
        if self.headers.get("Authorization") != expected:
            self.send_response(401)
            self.end_headers()
            return
        body = json.dumps({"path": self.path, "authenticated": True}).encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass


ThreadingHTTPServer(("127.0.0.1", 8091), Handler).serve_forever()
