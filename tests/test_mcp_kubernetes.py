"""Migrate and roll back MCP in a disposable namespace."""

import base64
import copy
import http.client
import json
import os
import socket
import subprocess
import time
import uuid
from pathlib import Path

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.skipif(
    os.environ.get("NITA_K8S_PROXY_TEST") != "1",
    reason="Set NITA_K8S_PROXY_TEST=1 to create an isolated Kubernetes test namespace",
)


def kubectl(*args, **kwargs):
    return subprocess.run(["kubectl", *args], check=True, **kwargs)


def apply(objects):
    kubectl("apply", "-f", "-", input=json.dumps({"apiVersion": "v1", "kind": "List", "items": objects}),
            text=True, stdout=subprocess.DEVNULL)


def wait(namespace):
    kubectl("rollout", "status", "deployment/junos-mcp", "-n", namespace, "--timeout=180s")


def check(port):
    for path in ("/mcp", "/mcp/"):
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        conn.request("GET", path, headers={"Authorization": "Bearer attacker"})
        response = conn.getresponse()
        assert response.status == 200
        assert json.loads(response.read()) == {"path": "/mcp/", "authenticated": True}
        conn.close()


def test_mcp_upgrade_rotation_and_rollback(tmp_path):
    image = os.environ.get("NITA_K8S_TEST_IMAGE", "ghcr.io/juniper/nita-webapp:latest")
    namespace = "nita-mcp-test-" + uuid.uuid4().hex[:10]
    new = yaml.safe_load((ROOT / "k8s/junos-mcp-deployment.yaml").read_text())
    old = copy.deepcopy(new)
    old_spec = old["spec"]["template"]["spec"]
    old_proxy = old_spec["containers"][1]
    old_proxy["image"] = "nginx:stable"
    old_proxy.pop("args")
    old_proxy.pop("readinessProbe")
    old_proxy["volumeMounts"] = [{
        "name": "proxy-config", "mountPath": "/etc/nginx/conf.d/default.conf", "subPath": "default.conf",
    }]
    for volume in old_spec["volumes"]:
        if volume["name"] == "auth-tokens":
            volume["secret"]["secretName"] = "junos-mcp-auth"
        elif volume["name"] == "proxy-config":
            volume.pop("secret")
            volume["configMap"] = {"name": "junos-mcp-proxy-cm", "items": [
                {"key": "default.conf", "path": "default.conf"},
            ]}
    for deployment in (old, new):
        deployment["metadata"]["namespace"] = namespace
        containers = deployment["spec"]["template"]["spec"]["containers"]
        containers[0]["image"] = image
        containers[0]["imagePullPolicy"] = "IfNotPresent"
        containers[0]["command"] = ["python3", "-u", "/test/mcp_backend.py"]
        containers[0]["args"] = []
        containers[0]["volumeMounts"].append({"name": "backend", "mountPath": "/test"})
        deployment["spec"]["template"]["spec"]["volumes"].append(
            {"name": "backend", "configMap": {"name": "test-backend"}}
        )
        containers[1]["ports"][0].pop("hostPort", None)
    token = "test-internal-token"
    tokens = json.dumps({"nita-lab": {"token": token}})
    nginx = '''server {
        listen 8090;
        location /mcp {
            rewrite ^/mcp$ /mcp/ break;
            proxy_pass http://127.0.0.1:8091;
            proxy_set_header Authorization "Bearer test-internal-token";
        }
    }'''
    resources = [
        {"apiVersion": "v1", "kind": "ConfigMap",
         "metadata": {"name": "test-backend", "namespace": namespace},
         "data": {"mcp_backend.py": (ROOT / "tests/traefik_test_mcp_backend.py").read_text()}},
        {"apiVersion": "v1", "kind": "ConfigMap",
         "metadata": {"name": "junos-mcp-devices-cm", "namespace": namespace},
         "data": {"devices.json": "{}"}},
        {"apiVersion": "v1", "kind": "ConfigMap",
         "metadata": {"name": "junos-mcp-proxy-cm", "namespace": namespace},
         "data": {"default.conf": nginx}},
        {"apiVersion": "v1", "kind": "Secret",
         "metadata": {"name": "junos-mcp-auth", "namespace": namespace},
         "data": {".tokens": base64.b64encode(tokens.encode()).decode()}},
        old,
    ]
    wrapper = tmp_path / "kubectl"
    wrapper.write_text(
        "#!/usr/bin/env python3\n"
        "import os, sys\n"
        "args = [os.environ['TEST_NAMESPACE'] if arg == 'nita' else arg for arg in sys.argv[1:]]\n"
        "os.execv('/usr/bin/kubectl', ['/usr/bin/kubectl', *args])\n"
    )
    wrapper.chmod(0o755)
    env = {**os.environ, "PATH": f"{tmp_path}:{os.environ['PATH']}", "TEST_NAMESPACE": namespace,
           "JUNOS_MCP_TOKEN_ID": "nita-lab", "JUNOS_MCP_TOKEN_VALUE": "", "JUNOS_MCP_ROTATE": "false"}
    process = None
    created = False
    try:
        kubectl("create", "namespace", namespace, stdout=subprocess.DEVNULL)
        created = True
        apply(resources)
        wait(namespace)
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        process = subprocess.Popen(
            ["kubectl", "port-forward", "-n", namespace, "deployment/junos-mcp", f"{port}:8090"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        for _ in range(60):
            try:
                check(port)
                break
            except OSError:
                if process.poll() is not None:
                    raise RuntimeError("MCP port-forward exited")
                time.sleep(1)
        else:
            raise RuntimeError("MCP port-forward did not become ready")
        process.terminate()
        process.wait(timeout=10)
        process = None

        subprocess.run(["python3", str(ROOT / "k8s/prepare-mcp-traefik.py")], env=env, check=True)
        apply([new])
        wait(namespace)
        process = subprocess.Popen(
            ["kubectl", "port-forward", "-n", namespace, "deployment/junos-mcp", f"{port}:8090"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        time.sleep(2)
        check(port)
        secret = kubectl("get", "secret", "junos-mcp-traefik-auth", "-n", namespace, "-o", "json",
                         capture_output=True, text=True)
        data = json.loads(secret.stdout)["data"]
        assert json.loads(base64.b64decode(data[".tokens"]))["nita-lab"]["token"] == token
        assert token not in subprocess.run(
            ["kubectl", "logs", "-n", namespace, "deployment/junos-mcp", "-c", "junos-mcp-proxy"],
            capture_output=True, text=True, check=True,
        ).stdout
        process.terminate()
        process.wait(timeout=10)
        process = None

        subprocess.run(["python3", str(ROOT / "k8s/prepare-mcp-traefik.py")],
                       env={**env, "JUNOS_MCP_TOKEN_VALUE": "rotated-token", "JUNOS_MCP_ROTATE": "true"}, check=True)
        kubectl("rollout", "restart", "deployment/junos-mcp", "-n", namespace)
        wait(namespace)
        process = subprocess.Popen(
            ["kubectl", "port-forward", "-n", namespace, "deployment/junos-mcp", f"{port}:8090"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        time.sleep(2)
        check(port)
        process.terminate()
        process.wait(timeout=10)
        process = None

        apply([old])
        wait(namespace)
        process = subprocess.Popen(
            ["kubectl", "port-forward", "-n", namespace, "deployment/junos-mcp", f"{port}:8090"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        time.sleep(2)
        check(port)
        process.terminate()
        process.wait(timeout=10)
        process = None

        subprocess.run(["python3", str(ROOT / "k8s/prepare-mcp-traefik.py")], env=env, check=True)
        secret = kubectl("get", "secret", "junos-mcp-traefik-auth", "-n", namespace, "-o", "json",
                         capture_output=True, text=True)
        assert json.loads(base64.b64decode(json.loads(secret.stdout)["data"][".tokens"]))["nita-lab"]["token"] == token
        apply([new])
        wait(namespace)
        process = subprocess.Popen(
            ["kubectl", "port-forward", "-n", namespace, "deployment/junos-mcp", f"{port}:8090"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        time.sleep(2)
        check(port)
    finally:
        if process:
            process.terminate()
            process.wait(timeout=10)
        if created:
            kubectl("delete", "namespace", namespace, "--wait=true", "--timeout=120s")
