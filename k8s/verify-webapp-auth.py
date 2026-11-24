#!/usr/bin/env python3
import http.client
import socket
import subprocess
import sys
import time
from urllib.parse import urlsplit


def main():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    process = subprocess.Popen(
        ["kubectl", "port-forward", "-n", "nita", "svc/webapp", f"{port}:8000"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        for _ in range(60):
            if process.poll() is not None:
                raise RuntimeError("webapp port-forward exited")
            try:
                connection = http.client.HTTPConnection("127.0.0.1", port, timeout=2)
                connection.request("GET", "/api/v1/auth/forward/", headers={"X-Forwarded-Uri": "/jenkins/"})
                response = connection.getresponse()
                status = response.status
                location = response.getheader("Location", "")
                response.read()
                connection.close()
                if status in (301, 302, 303, 307, 308) and urlsplit(location).path == "/login":
                    print("Verified the webapp Traefik forward-auth contract.")
                    return
                if status < 500:
                    raise RuntimeError(f"webapp forward-auth returned incompatible HTTP {status}")
            except (OSError, http.client.HTTPException):
                pass
            time.sleep(1)
        raise RuntimeError("webapp forward-auth did not become available")
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
    except (OSError, RuntimeError, http.client.HTTPException) as error:
        print(f"Error checking webapp authentication: {error}", file=sys.stderr)
        sys.exit(1)
