"""Verify the deployed webapp session reaches the real Jenkins security realm."""

import os
import socket
import subprocess
import time

import pytest
import requests
import urllib3


pytestmark = pytest.mark.skipif(
    os.environ.get("NITA_PROXY_SESSION_TEST") != "1",
    reason="Requires an isolated deployed NITA stack",
)


def test_webapp_session_authenticates_jenkins_and_rejects_spoofing():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    forward = subprocess.Popen(
        ["kubectl", "port-forward", "-n", "nita", "deployment/proxy", f"{port}:443"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    session = requests.Session()
    session.trust_env = False
    session.verify = False
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    url = f"https://127.0.0.1:{port}"
    try:
        for _ in range(60):
            if forward.poll() is not None:
                pytest.fail("Proxy port-forward exited")
            try:
                response = session.get(url + "/api/v1/auth/csrf/", timeout=2)
                if response.status_code == 200:
                    break
            except requests.ConnectionError:
                pass
            time.sleep(1)
        else:
            pytest.fail("Proxy did not become ready")

        anonymous = session.get(url + "/jenkins/whoAmI/api/json", allow_redirects=False, timeout=15)
        assert anonymous.status_code in (301, 302, 303, 307, 308)
        assert anonymous.headers["Location"].startswith("/login")

        username = os.environ.get("NITA_USER", "vagrant")
        password = os.environ.get("NITA_PASS", "vagrant123")
        login = session.post(
            url + "/api/v1/auth/login/",
            json={"username": username, "password": password},
            headers={"X-CSRFToken": response.json()["csrfToken"], "Origin": "https://localhost"},
            timeout=15,
        )
        assert login.status_code == 200, f"Webapp login failed: HTTP {login.status_code}"
        identity = session.get(
            url + "/jenkins/whoAmI/api/json",
            headers={"X-Forwarded-User": "spoofed-user", "X-Forwarded-Groups": "spoofed-group",
                     "Authorization": "Basic c3Bvb2Y6c3Bvb2Y="},
            allow_redirects=False, timeout=15,
        )
        assert identity.status_code == 200, f"Jenkins identity request failed: HTTP {identity.status_code}"
        result = identity.json()
        assert result["name"] == username
        assert "spoofed-group" not in result["authorities"]
        assert "admin" in result["authorities"]
    finally:
        session.close()
        forward.terminate()
        forward.wait(timeout=10)
