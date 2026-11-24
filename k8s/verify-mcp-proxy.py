#!/usr/bin/env python3
import http.client
import socket
import subprocess
import sys
import time


def main():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    process = subprocess.Popen(
        ["kubectl", "port-forward", "-n", "nita", "deployment/junos-mcp", f"{port}:8090"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        for _ in range(60):
            if process.poll() is not None:
                raise RuntimeError("MCP port-forward exited")
            try:
                connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
                connection.request("GET", "/mcp/", headers={"Accept": "application/json, text/event-stream"})
                response = connection.getresponse()
                status = response.status
                connection.close()
                if status in (200, 400, 405, 406):
                    print("Verified the MCP proxy can reach its authenticated backend.")
                    return
                if status < 500 and status != 404:
                    raise RuntimeError(f"MCP backend returned HTTP {status}")
            except (OSError, http.client.HTTPException):
                pass
            time.sleep(1)
        raise RuntimeError("MCP proxy did not reach its backend")
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
        print(f"Error verifying MCP Traefik proxy: {error}", file=sys.stderr)
        sys.exit(1)
