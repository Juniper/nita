#!/usr/bin/env python3
import http.client
import base64
import json
import socket
import ssl
import subprocess
import sys
import time
from urllib.parse import urlsplit


def main():
    secret = subprocess.run(
        ["kubectl", "get", "secret", "nita-traefik-tls", "-n", "nita", "-o", "json"],
        capture_output=True, check=True, text=True,
    )
    certificate = base64.b64decode(json.loads(secret.stdout)["data"]["tls.crt"], validate=True)
    expected = ssl.PEM_cert_to_DER_cert(certificate.decode("utf-8"))
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    process = subprocess.Popen(
        ["kubectl", "port-forward", "-n", "nita", "deployment/proxy", f"{port}:443"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        certificate_mismatch = False
        for _ in range(60):
            if process.poll() is not None:
                raise RuntimeError("proxy port-forward exited")
            try:
                connection = http.client.HTTPSConnection(
                    "127.0.0.1", port, context=ssl._create_unverified_context(), timeout=2
                )
                connection.connect()
                if connection.sock.getpeercert(binary_form=True) != expected:
                    certificate_mismatch = True
                    connection.close()
                    time.sleep(1)
                    continue
                certificate_mismatch = False
                connection.request("GET", "/")
                response = connection.getresponse()
                status = response.status
                response.read()
                connection.close()
                if status in (200, 301, 302, 303, 307, 308, 401, 403):
                    break
            except (OSError, http.client.HTTPException):
                pass
            time.sleep(1)
        else:
            if certificate_mismatch:
                raise RuntimeError("proxy presented a different TLS certificate")
            raise RuntimeError("webapp route did not become available through Traefik")

        connection = http.client.HTTPSConnection(
            "127.0.0.1", port, context=ssl._create_unverified_context(), timeout=5
        )
        connection.request("GET", "/jenkins/")
        response = connection.getresponse()
        location = response.getheader("Location", "")
        status = response.status
        response.read()
        connection.close()
        if status not in (301, 302, 303, 307, 308) or urlsplit(location).path != "/login":
            raise RuntimeError("anonymous Jenkins request did not redirect to the webapp login")
        print("Verified proxy certificate, webapp route and Jenkins session gate.")
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


if __name__ == "__main__":
    try:
        main()
    except (OSError, KeyError, RuntimeError, subprocess.CalledProcessError, http.client.HTTPException, ValueError) as error:
        print(f"Error verifying Traefik: {error}", file=sys.stderr)
        sys.exit(1)
