#!/usr/bin/env python3
import base64
import json
import subprocess
import sys
import tempfile
from pathlib import Path


def main():
    required = {
        "nita-traefik-config": {"traefik.yaml", "routes.yaml"},
        "nita-traefik-bodylimit": {".traefik.yml", "go.mod", "bodylimit.go"},
        "nita-traefik-identityguard": {".traefik.yml", "go.mod", "identityguard.go"},
    }
    for name, keys in required.items():
        result = subprocess.run(
            ["kubectl", "get", "configmap", name, "-n", "nita", "-o", "json"],
            check=True, capture_output=True, text=True,
        )
        data = json.loads(result.stdout).get("data", {})
        if not all(data.get(key) for key in keys):
            raise ValueError(f"ConfigMap {name} is missing required configuration")
    result = subprocess.run(
        ["kubectl", "get", "secret", "nita-traefik-tls", "-n", "nita", "-o", "json"],
        check=True, capture_output=True, text=True,
    )
    secret = json.loads(result.stdout)
    if secret.get("type") != "kubernetes.io/tls":
        raise ValueError("nita-traefik-tls is not a TLS Secret")
    cert = base64.b64decode(secret["data"]["tls.crt"], validate=True)
    key = base64.b64decode(secret["data"]["tls.key"], validate=True)
    with tempfile.TemporaryDirectory(prefix="nita-tls-check-") as directory:
        cert_file = Path(directory) / "tls.crt"
        key_file = Path(directory) / "tls.key"
        cert_file.write_bytes(cert)
        key_file.write_bytes(key)
        subprocess.run(["openssl", "x509", "-in", str(cert_file), "-checkend", "0", "-noout"],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        cert_public = subprocess.run(
            ["openssl", "x509", "-in", str(cert_file), "-pubkey", "-noout"],
            check=True, capture_output=True,
        ).stdout
        key_public = subprocess.run(
            ["openssl", "pkey", "-in", str(key_file), "-pubout"],
            check=True, capture_output=True,
        ).stdout
        if cert_public != key_public:
            raise ValueError("Traefik certificate and private key do not match")
    print("Traefik configuration and TLS prerequisites are valid.")


if __name__ == "__main__":
    try:
        main()
    except (OSError, KeyError, ValueError, subprocess.CalledProcessError) as error:
        print(f"Error validating Traefik prerequisites: {error}", file=sys.stderr)
        sys.exit(1)
