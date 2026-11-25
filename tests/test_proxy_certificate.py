import json
import base64
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "k8s" / "prepare-proxy-certificate.sh"


class ProxyCertificateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.certs = self.root / "certs"
        self.certs.mkdir()
        self.bin = self.root / "bin"
        self.bin.mkdir()
        kubectl = self.bin / "kubectl"
        kubectl.write_text(
            """#!/usr/bin/env python3
import os
import sys

if os.environ.get("KUBECTL_FAIL") == "1":
    sys.exit(1)
if sys.argv[2] == "configmap":
    print(os.environ.get("CONFIGMAP", ""), end="")
elif sys.argv[2] == "secret":
    print(os.environ.get("SECRET", ""), end="")
elif sys.argv[2] == "deployment":
    if sys.argv[-1] == "json":
        print(os.environ.get("DEPLOYMENT_JSON", ""), end="")
    else:
        print(os.environ.get("DEPLOYMENT", ""), end="")
else:
    sys.exit(2)
""",
            encoding="utf-8",
        )
        kubectl.chmod(0o755)
        self.env = {
            **os.environ,
            "PATH": f"{self.bin}:{os.environ['PATH']}",
            "CERTS": str(self.certs),
            "TMPDIR": str(self.root),
        }

    def generate_pair(self, name):
        cert, key = self.root / f"{name}.crt", self.root / f"{name}.key"
        subprocess.run(
            [
                "openssl", "req", "-x509", "-nodes", "-days", "1",
                "-newkey", "rsa:2048", "-keyout", str(key),
                "-out", str(cert), "-subj", "/CN=nita-test",
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return cert.read_text(), key.read_text()

    def run_prepare(self, **env):
        if env.get("DEPLOYMENT") and "DEPLOYMENT_JSON" not in env:
            env["DEPLOYMENT_JSON"] = json.dumps({"spec": {"template": {"spec": {"containers": [
                {"name": "proxy", "image": "nginx:stable"},
            ]}}}})
        return subprocess.run(
            ["bash", str(SCRIPT)],
            env={**self.env, **env},
            input="\n" * 10,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_existing_files_are_preserved(self):
        cert, key = self.generate_pair("existing")
        (self.certs / "nginx-certificate.crt").write_text(cert)
        (self.certs / "nginx-certificate-key.key").write_text(key)

        result = self.run_prepare()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.certs / "nginx-certificate.crt").read_text(), cert)
        self.assertEqual((self.certs / "nginx-certificate-key.key").read_text(), key)

    def test_existing_files_must_match_active_certificate(self):
        cert, key = self.generate_pair("local")
        active_cert, _ = self.generate_pair("active")
        (self.certs / "nginx-certificate.crt").write_text(cert)
        (self.certs / "nginx-certificate-key.key").write_text(key)
        deployment = json.dumps({"spec": {"template": {"spec": {"containers": [
            {"name": "proxy", "image": "nginx:stable"},
        ]}}}})
        configmap = json.dumps({"data": {"nginx-certificate.crt": active_cert}})
        result = self.run_prepare(DEPLOYMENT_JSON=deployment, CONFIGMAP=configmap)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("differs from the active proxy certificate", result.stderr)
        self.assertEqual((self.certs / "nginx-certificate.crt").read_text(), cert)

    def test_existing_configmap_is_restored(self):
        cert, key = self.generate_pair("existing")
        configmap = json.dumps({"data": {
            "nginx-certificate.crt": cert,
            "nginx-certificate-key.key": key,
        }})

        result = self.run_prepare(CONFIGMAP=configmap, DEPLOYMENT="deployment.apps/proxy")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.certs / "nginx-certificate.crt").read_text(), cert)
        self.assertEqual((self.certs / "nginx-certificate-key.key").read_text(), key)
        self.assertEqual((self.certs / "nginx-certificate-key.key").stat().st_mode & 0o777, 0o600)

    def test_existing_deployment_without_certificate_fails(self):
        result = self.run_prepare(DEPLOYMENT="deployment.apps/proxy")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("restore the pair", result.stderr)
        self.assertEqual(list(self.certs.iterdir()), [])

    def test_mismatched_certificate_is_not_replaced(self):
        cert, _ = self.generate_pair("first")
        _, key = self.generate_pair("second")
        cert_path = self.certs / "nginx-certificate.crt"
        key_path = self.certs / "nginx-certificate-key.key"
        cert_path.write_text(cert)
        key_path.write_text(key)

        result = self.run_prepare()

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("do not match", result.stderr)
        self.assertEqual(cert_path.read_text(), cert)
        self.assertEqual(key_path.read_text(), key)

    def test_missing_cluster_access_does_not_generate_certificate(self):
        result = self.run_prepare(KUBECTL_FAIL="1")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unable to inspect", result.stderr)
        self.assertEqual(list(self.certs.iterdir()), [])

    def test_invalid_configmap_does_not_replace_partial_files(self):
        cert, _ = self.generate_pair("existing")
        cert_path = self.certs / "nginx-certificate.crt"
        cert_path.write_text(cert)
        configmap = json.dumps({"data": {"nginx-certificate.crt": cert}})

        result = self.run_prepare(CONFIGMAP=configmap, DEPLOYMENT="deployment.apps/proxy")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("does not contain a usable certificate and key", result.stderr)
        self.assertEqual(cert_path.read_text(), cert)
        self.assertFalse((self.certs / "nginx-certificate-key.key").exists())

    def test_existing_tls_secret_takes_precedence_over_legacy_configmap(self):
        cert, key = self.generate_pair("current")
        secret = json.dumps({"data": {
            "tls.crt": base64.b64encode(cert.encode()).decode(),
            "tls.key": base64.b64encode(key.encode()).decode(),
        }})
        result = self.run_prepare(SECRET=secret, CONFIGMAP="invalid")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.certs / "nginx-certificate.crt").read_text(), cert)

    def test_running_nginx_uses_its_certificate_not_stale_traefik_secret(self):
        cert, key = self.generate_pair("nginx")
        stale_cert, stale_key = self.generate_pair("stale")
        secret = json.dumps({"data": {
            "tls.crt": base64.b64encode(stale_cert.encode()).decode(),
            "tls.key": base64.b64encode(stale_key.encode()).decode(),
        }})
        configmap = json.dumps({"data": {
            "nginx-certificate.crt": cert, "nginx-certificate-key.key": key,
        }})
        result = self.run_prepare(SECRET=secret, CONFIGMAP=configmap, DEPLOYMENT="deployment.apps/proxy")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.certs / "nginx-certificate.crt").read_text(), cert)

    def test_fresh_install_generates_once(self):
        result = self.run_prepare()
        self.assertEqual(result.returncode, 0, result.stderr)
        cert = (self.certs / "nginx-certificate.crt").read_text()

        result = self.run_prepare()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.certs / "nginx-certificate.crt").read_text(), cert)


if __name__ == "__main__":
    unittest.main()
