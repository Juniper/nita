import json
import os
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import quote


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, format, *args):
        pass

    def respond(self, status, body=b"", headers=None):
        self.send_response(status)
        for key, value in (headers or {}).items():
            self.send_header(key, value)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/api/v1/auth/forward/":
            cookie = self.headers.get("Cookie", "")
            if cookie == "sessionid=valid":
                self.respond(200, headers={
                    "X-Forwarded-User": "alice",
                    "X-Forwarded-Groups": "user|team-7",
                })
            elif cookie == "sessionid=missing-identity":
                self.respond(200)
            elif cookie == "sessionid=auth-error":
                self.respond(503)
            else:
                target = self.headers.get("X-Forwarded-Uri", "/jenkins/")
                self.respond(302, headers={"Location": "/login?next=" + quote(target, safe="")})
        elif self.path.startswith(("/api/v1/action-history/", "/api/v1/jenkins/jobs/")):
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(b"data: first\n\n")
            self.wfile.flush()
            time.sleep(1)
            self.wfile.write(b"data: second\n\n")
            self.wfile.flush()
        elif self.path.startswith("/jenkins") and os.environ["PORT"] == "8080":
            self.respond(200, json.dumps({
                "path": self.path,
                "user": self.headers.get("X-Forwarded-User"),
                "groups": self.headers.get("X-Forwarded-Groups"),
                "authorization": self.headers.get("Authorization"),
                "host": self.headers.get("Host"),
                "proto": self.headers.get("X-Forwarded-Proto"),
                "prefix": self.headers.get("X-Forwarded-Prefix"),
            }).encode())
        else:
            self.respond(200, b"webapp" if os.environ["PORT"] == "8000" else b"jenkins")

    def do_POST(self):
        body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
        self.respond(200, str(len(body)).encode())


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", int(os.environ["PORT"])), Handler).serve_forever()
