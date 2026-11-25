import base64
import http.client
import importlib.util
import json
import os
import socket
import subprocess
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("mcp_traefik", ROOT / "k8s" / "prepare-mcp-traefik.py")
mcp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mcp)


def encoded(value):
    return base64.b64encode(value.encode()).decode()


class McpTraefikTests(unittest.TestCase):
    def run_prepare(self, objects, environment=None):
        created = {}

        def fake_get(kind, name):
            return objects.get((kind, name))

        def fake_run(args, **kwargs):
            if args[1:4] == ["create", "secret", "generic"]:
                for arg in args:
                    if arg.startswith("--from-file="):
                        key, path = arg[len("--from-file="):].split("=", 1)
                        created[key] = Path(path).read_text()
                return unittest.mock.Mock(stdout=b"secret")
            return unittest.mock.Mock()

        with patch.object(mcp, "kubectl_get", side_effect=fake_get), \
             patch.object(mcp.subprocess, "run", side_effect=fake_run), \
             patch.dict(os.environ, environment or {}, clear=True):
            mcp.main()
        return created

    def test_fresh_secret_contains_matching_tokens(self):
        output = self.run_prepare({})
        tokens = json.loads(output[".tokens"])
        routes = json.loads(output["routes.yaml"])
        token = tokens["nita-lab"]["token"]
        self.assertEqual(routes["http"]["middlewares"]["auth"]["headers"]["customRequestHeaders"]["Authorization"], "Bearer " + token)

    def test_legacy_token_is_preserved(self):
        tokens = {"nita-lab": {"token": "jmcp_existing"}}
        objects = {
            ("secret", "junos-mcp-auth"): {"data": {".tokens": encoded(json.dumps(tokens))}},
            ("configmap", "junos-mcp-proxy-cm"): {"data": {"default.conf": 'proxy_set_header Authorization "Bearer jmcp_existing";'}},
        }
        output = self.run_prepare(objects)
        self.assertEqual(json.loads(output[".tokens"]), tokens)

    def test_rolled_back_legacy_deployment_uses_its_active_token(self):
        legacy_tokens = {"nita-lab": {"token": "legacy"}}
        current_tokens = {"nita-lab": {"token": "rotated"}}
        current_routes = {"http": {"middlewares": {"auth": {"headers": {
            "customRequestHeaders": {"Authorization": "Bearer rotated"}
        }}}}}
        objects = {
            ("secret", "junos-mcp-auth"): {"data": {".tokens": encoded(json.dumps(legacy_tokens))}},
            ("secret", "junos-mcp-traefik-auth"): {"data": {
                ".tokens": encoded(json.dumps(current_tokens)), "routes.yaml": encoded(json.dumps(current_routes))
            }},
            ("configmap", "junos-mcp-proxy-cm"): {"data": {"default.conf": 'proxy_set_header Authorization "Bearer legacy";'}},
            ("deployment", "junos-mcp"): {"spec": {"template": {"spec": {
                "containers": [{"name": "junos-mcp", "volumeMounts": [
                    {"name": "tokens", "mountPath": "/app/.tokens"}
                ]}],
                "volumes": [{"name": "tokens", "secret": {"secretName": "junos-mcp-auth"}}],
            }}}},
        }
        output = self.run_prepare(objects)
        self.assertEqual(json.loads(output[".tokens"]), legacy_tokens)

    def test_mismatched_legacy_tokens_fail(self):
        tokens = {"nita-lab": {"token": "jmcp_existing"}}
        objects = {
            ("secret", "junos-mcp-auth"): {"data": {".tokens": encoded(json.dumps(tokens))}},
            ("configmap", "junos-mcp-proxy-cm"): {"data": {"default.conf": 'proxy_set_header Authorization "Bearer other";'}},
        }
        with self.assertRaisesRegex(ValueError, "do not match"):
            self.run_prepare(objects)

    def test_rotation_updates_both_configs(self):
        tokens = {"nita-lab": {"token": "old"}}
        objects = {
            ("secret", "junos-mcp-auth"): {"data": {".tokens": encoded(json.dumps(tokens))}},
            ("configmap", "junos-mcp-proxy-cm"): {"data": {"default.conf": 'proxy_set_header Authorization "Bearer old";'}},
        }
        output = self.run_prepare(objects, {"JUNOS_MCP_ROTATE": "true", "JUNOS_MCP_TOKEN_VALUE": "new"})
        self.assertEqual(json.loads(output[".tokens"])["nita-lab"]["token"], "new")
        self.assertEqual(json.loads(output["routes.yaml"])["http"]["middlewares"]["auth"]["headers"]["customRequestHeaders"]["Authorization"], "Bearer new")

    def test_existing_deployment_without_secret_fails(self):
        with self.assertRaisesRegex(ValueError, "no authentication secret"):
            self.run_prepare({("deployment", "junos-mcp"): {"metadata": {}}})

    def check_running_sidecar(self, stream_delay=0):
        output = self.run_prepare({}, {"JUNOS_MCP_TOKEN_VALUE": "internal"})
        routes = json.loads(output["routes.yaml"])

        class Backend(BaseHTTPRequestHandler):
            def do_GET(self):
                if stream_delay:
                    self.send_response(200)
                    self.send_header("Content-Type", "text/event-stream")
                    self.send_header("Connection", "close")
                    self.end_headers()
                    self.wfile.write(b"data: first\n\n")
                    self.wfile.flush()
                    time.sleep(stream_delay)
                    self.wfile.write(b"data: second\n\n")
                    self.wfile.flush()
                    return
                body = json.dumps({"path": self.path, "auth": self.headers.get("Authorization")}).encode()
                self.send_response(200)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, format, *args):
                pass

        backend = ThreadingHTTPServer(("127.0.0.1", 0), Backend)
        thread = threading.Thread(target=backend.serve_forever)
        thread.start()
        self.addCleanup(thread.join)
        self.addCleanup(backend.server_close)
        self.addCleanup(backend.shutdown)
        routes["http"]["services"]["backend"]["loadBalancer"]["servers"][0]["url"] = f"http://127.0.0.1:{backend.server_port}"

        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / "routes.yaml"
            config.write_text(json.dumps(routes))
            log = open(Path(directory) / "traefik.log", "w+")
            process = subprocess.Popen(
                [os.environ["TRAEFIK_BINARY"], f"--entrypoints.mcp.address=127.0.0.1:{port}",
                 "--entrypoints.mcp.transport.respondingtimeouts.readtimeout=0s",
                 "--entrypoints.mcp.transport.respondingtimeouts.writetimeout=0s",
                 f"--providers.file.filename={config}"],
                stdout=log, stderr=subprocess.STDOUT,
            )
            try:
                for _ in range(100):
                    if process.poll() is not None:
                        self.fail("Traefik exited before accepting connections")
                    try:
                        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=stream_delay + 30 if stream_delay else 1)
                        conn.request("GET", "/mcp?test=1", headers={"Authorization": "Bearer attacker"})
                        response = conn.getresponse()
                        if stream_delay and response.status == 200:
                            self.assertEqual(response.readline(), b"data: first\n")
                            self.assertEqual(response.readline(), b"\n")
                            started = time.monotonic()
                            self.assertEqual(response.readline(), b"data: second\n")
                            self.assertGreaterEqual(time.monotonic() - started, stream_delay - 1)
                            response.read()
                            conn.close()
                            break
                        data = response.read()
                        conn.close()
                        if response.status == 200:
                            break
                    except OSError:
                        pass
                    time.sleep(0.1)
                else:
                    log.flush()
                    self.fail("Traefik did not route the MCP request: " + Path(log.name).read_text())
                if not stream_delay:
                    self.assertEqual(json.loads(data), {"path": "/mcp/?test=1", "auth": "Bearer internal"})
            finally:
                process.terminate()
                process.wait(timeout=10)
                log.flush()
                self.assertNotIn("internal", Path(log.name).read_text())
                log.close()

    @unittest.skipUnless(os.environ.get("TRAEFIK_BINARY"), "TRAEFIK_BINARY is not set")
    def test_running_sidecar_rewrites_path_and_replaces_client_token(self):
        self.check_running_sidecar()

    @unittest.skipUnless(
        os.environ.get("TRAEFIK_BINARY") and os.environ.get("TRAEFIK_MCP_LONG_STREAM") == "1",
        "Set TRAEFIK_BINARY and TRAEFIK_MCP_LONG_STREAM=1 for the 3600-second idle check",
    )
    def test_mcp_stream_survives_3600_seconds_idle(self):
        self.check_running_sidecar(stream_delay=3600)


if __name__ == "__main__":
    unittest.main()
