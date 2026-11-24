import base64
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "k8s/preflight-traefik.py"


class TraefikPreflightTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        cert, key = self.root / "cert", self.root / "key"
        subprocess.run(["openssl", "req", "-x509", "-nodes", "-newkey", "rsa:2048",
                        "-days", "1", "-subj", "/CN=test", "-keyout", str(key),
                        "-out", str(cert)], check=True, stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL)
        self.objects = {
            "nita-traefik-config": {"data": {"traefik.yaml": "config", "routes.yaml": "routes"}},
            "nita-traefik-bodylimit": {"data": {".traefik.yml": "plugin", "go.mod": "module", "bodylimit.go": "code"}},
            "nita-traefik-identityguard": {"data": {".traefik.yml": "plugin", "go.mod": "module", "identityguard.go": "code"}},
            "nita-traefik-tls": {"type": "kubernetes.io/tls", "data": {
                "tls.crt": base64.b64encode(cert.read_bytes()).decode(),
                "tls.key": base64.b64encode(key.read_bytes()).decode(),
            }},
        }
        kubectl = self.root / "kubectl"
        kubectl.write_text(
            "#!/usr/bin/env python3\nimport json, os, sys\n"
            "print(json.dumps(json.loads(os.environ['OBJECTS'])[sys.argv[3]]))\n"
        )
        kubectl.chmod(0o755)

    def run_preflight(self):
        return subprocess.run(
            ["python3", str(SCRIPT)],
            env={**os.environ, "PATH": f"{self.root}:{os.environ['PATH']}", "OBJECTS": json.dumps(self.objects)},
            capture_output=True, text=True,
        )

    def test_valid_resources_pass(self):
        result = self.run_preflight()
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_missing_plugin_source_fails(self):
        del self.objects["nita-traefik-bodylimit"]["data"]["bodylimit.go"]
        result = self.run_preflight()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing required configuration", result.stderr)

    def test_invalid_key_fails(self):
        self.objects["nita-traefik-tls"]["data"]["tls.key"] = base64.b64encode(b"invalid").decode()
        result = self.run_preflight()
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("invalid", result.stderr)


if __name__ == "__main__":
    unittest.main()
