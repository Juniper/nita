"""Exercise the actual ingress manifests in a disposable Kubernetes namespace."""

import base64
import http.client
import json
import os
import socket
import ssl
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


@pytest.fixture(scope="module")
def proxy(tmp_path_factory):
    image = os.environ.get("NITA_K8S_TEST_IMAGE", "ghcr.io/juniper/nita-webapp:latest")
    namespace = "nita-proxy-test-" + uuid.uuid4().hex[:10]
    root = tmp_path_factory.mktemp("kubernetes-proxy")
    cert, key = root / "tls.crt", root / "tls.key"
    subprocess.run(
        ["openssl", "req", "-x509", "-nodes", "-newkey", "rsa:2048", "-days", "1",
         "-subj", "/CN=nita-proxy-test", "-keyout", str(key), "-out", str(cert)],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    resources = list(yaml.safe_load_all((ROOT / "k8s/traefik-resources.yaml").read_text()))
    resources = [resource for resource in resources if resource["kind"] not in ("ClusterRole", "ClusterRoleBinding", "IngressClass")]
    for resource in resources:
        resource["metadata"]["namespace"] = namespace
        if resource["kind"] == "RoleBinding":
            resource["subjects"][0]["namespace"] = namespace
    for name, ingress_class in (("unclassified", None), ("other", "other-controller")):
        ingress = {
            "apiVersion": "networking.k8s.io/v1", "kind": "Ingress",
            "metadata": {"name": name, "namespace": namespace, "annotations": {
                "traefik.ingress.kubernetes.io/router.entrypoints": "websecure",
                "traefik.ingress.kubernetes.io/router.tls": "true",
            }},
            "spec": {"rules": [{"http": {"paths": [{
                "path": "/" + name, "pathType": "Prefix",
                "backend": {"service": {"name": "jenkins", "port": {"number": 8080}}},
            }]}}]},
        }
        if ingress_class:
            ingress["spec"]["ingressClassName"] = ingress_class
        resources.append(ingress)
    # Cluster-scoped discovery needs a uniquely named ClusterRoleBinding.
    binding = {
        "apiVersion": "rbac.authorization.k8s.io/v1", "kind": "ClusterRoleBinding",
        "metadata": {"name": namespace},
        "roleRef": {"apiGroup": "rbac.authorization.k8s.io", "kind": "ClusterRole", "name": "nita-traefik"},
        "subjects": [{"kind": "ServiceAccount", "name": "nita-traefik", "namespace": namespace}],
    }
    static = yaml.safe_load((ROOT / "k8s/traefik/traefik.yaml").read_text())
    static["providers"]["kubernetesIngress"]["namespaces"] = [namespace]
    resources.append({"apiVersion": "v1", "kind": "ConfigMap",
                      "metadata": {"name": "nita-traefik-config", "namespace": namespace},
                      "data": {"traefik.yaml": yaml.safe_dump(static),
                               "routes.yaml": (ROOT / "k8s/traefik/routes.yaml").read_text()}})
    for plugin in ("bodylimit", "identityguard"):
        directory = ROOT / "k8s/traefik" / plugin
        resources.append({"apiVersion": "v1", "kind": "ConfigMap",
                          "metadata": {"name": "nita-traefik-" + plugin, "namespace": namespace},
                          "data": {name: (directory / name).read_text()
                                   for name in (".traefik.yml", "go.mod", plugin + ".go")}})
    resources.append({"apiVersion": "v1", "kind": "Secret",
                      "metadata": {"name": "nita-traefik-tls", "namespace": namespace},
                      "type": "kubernetes.io/tls", "data": {
                          "tls.crt": base64.b64encode(cert.read_bytes()).decode(),
                          "tls.key": base64.b64encode(key.read_bytes()).decode(),
                      }})
    resources.append({"apiVersion": "v1", "kind": "ConfigMap",
                      "metadata": {"name": "test-backend", "namespace": namespace},
                      "data": {"backend.py": (ROOT / "tests/traefik_test_backend.py").read_text()}})
    for name, port in (("webapp", 8000), ("jenkins", 8080), ("intruder", 8000)):
        labels = {"app": name, "io.kompose.service": name}
        resources.append({
            "apiVersion": "apps/v1", "kind": "Deployment",
            "metadata": {"name": name, "namespace": namespace},
            "spec": {"replicas": 1, "selector": {"matchLabels": labels}, "template": {
                "metadata": {"labels": labels}, "spec": {
                    "containers": [{"name": name, "image": image, "imagePullPolicy": "IfNotPresent",
                                    "command": ["python3", "-u", "/test/backend.py"],
                                    "env": [{"name": "PORT", "value": str(port)}],
                                    "ports": [{"containerPort": port}],
                                    "readinessProbe": {"tcpSocket": {"port": port}, "periodSeconds": 2},
                                    "volumeMounts": [{"name": "backend", "mountPath": "/test"}]}],
                    "volumes": [{"name": "backend", "configMap": {"name": "test-backend"}}],
                },
            }},
        })
        if name != "intruder":
            resources.append({"apiVersion": "v1", "kind": "Service",
                              "metadata": {"name": name, "namespace": namespace},
                              "spec": {"selector": labels, "ports": [{"port": port, "targetPort": port}]}})
    policy = yaml.safe_load((ROOT / "k8s/jenkins-network-policy.yaml").read_text())
    policy["metadata"]["namespace"] = namespace
    resources.append(policy)
    deployment = yaml.safe_load((ROOT / "k8s/proxy-deployment.yaml").read_text())
    deployment["metadata"]["namespace"] = namespace
    for port in deployment["spec"]["template"]["spec"]["containers"][0]["ports"]:
        port.pop("hostPort", None)
    resources.append(deployment)

    process = None
    created_namespace = False
    created_binding = False
    try:
        kubectl("create", "namespace", namespace, stdout=subprocess.DEVNULL)
        created_namespace = True
        kubectl("create", "-f", "-", input=json.dumps(binding), text=True, stdout=subprocess.DEVNULL)
        created_binding = True
        kubectl("apply", "-f", "-", input=json.dumps({"apiVersion": "v1", "kind": "List", "items": resources}),
                text=True, stdout=subprocess.DEVNULL)
        for name in ("webapp", "jenkins", "intruder", "proxy"):
            kubectl("rollout", "status", "deployment/" + name, "-n", namespace, "--timeout=180s")
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        process = subprocess.Popen(
            ["kubectl", "port-forward", "-n", namespace, "deployment/proxy", f"{port}:443"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        for _ in range(120):
            if process.poll() is not None:
                raise RuntimeError("proxy port-forward exited")
            try:
                conn = http.client.HTTPSConnection("127.0.0.1", port, context=ssl._create_unverified_context(), timeout=1)
                conn.request("GET", "/")
                response = conn.getresponse()
                body = response.read()
                conn.close()
                if response.status == 200 and body == b"webapp":
                    break
            except OSError:
                pass
            time.sleep(1)
        else:
            raise RuntimeError("Traefik ingress did not become ready")
        yield port, cert, namespace
    finally:
        if process:
            process.terminate()
            process.wait(timeout=10)
        if created_namespace:
            kubectl("delete", "namespace", namespace, "--wait=true", "--timeout=120s")
        if created_binding:
            kubectl("delete", "clusterrolebinding", namespace)


def request(port, method, path, headers=None, body=None, encode_chunked=False):
    conn = http.client.HTTPSConnection("127.0.0.1", port, context=ssl._create_unverified_context(), timeout=15)
    conn.request(method, path, body=body, headers=headers or {}, encode_chunked=encode_chunked)
    return conn, conn.getresponse()


def test_ingress_tls_auth_and_forwarded_headers(proxy):
    port, cert, _ = proxy
    expected = ssl.PEM_cert_to_DER_cert(cert.read_text())
    for host in (None, "localhost", "127.0.0.1"):
        with socket.create_connection(("127.0.0.1", port)) as raw:
            with ssl._create_unverified_context().wrap_socket(raw, server_hostname=host) as secure:
                assert secure.getpeercert(binary_form=True) == expected

    conn, response = request(port, "GET", "/jenkins/job/example/?x=1")
    assert response.status == 302
    assert response.getheader("Location") == "/login?next=%2Fjenkins%2Fjob%2Fexample%2F%3Fx%3D1"
    response.read()
    conn.close()

    conn, response = request(port, "GET", "/jenkins/job/example/", headers={
        "Cookie": "sessionid=valid", "Authorization": "Bearer attacker",
        "X-Forwarded-User": "admin", "X-Forwarded-Groups": "admin",
        "X-Forwarded-Proto": "http",
    })
    assert response.status == 200
    assert json.loads(response.read()) == {
        "path": "/jenkins/job/example/", "user": "alice", "groups": "user|team-7",
        "authorization": None, "host": f"127.0.0.1:{port}", "proto": "https", "prefix": "/jenkins",
    }
    conn.close()
    for cookie in ("sessionid=missing-identity", "sessionid=auth-error"):
        conn, response = request(port, "GET", "/jenkins/", headers={"Cookie": cookie, "X-Forwarded-User": "admin"})
        assert response.status == 503
        response.read()
        conn.close()
    conn, response = request(port, "GET", "/jenkins")
    assert response.status in (301, 302, 307, 308)
    assert response.getheader("Location") == f"https://127.0.0.1:{port}/jenkins/"
    response.read()
    conn.close()
    for path in ("/jenkins-other", "/unclassified", "/other"):
        conn, response = request(port, "GET", path)
        assert response.status == 200
        assert response.read() == b"webapp"
        conn.close()

    conn, response = request(port, "GET", "/jenkins/static/example.css", headers={"Cookie": "sessionid=valid"})
    assert response.status == 200
    assert json.loads(response.read())["path"] == "/jenkins/static/example.css"
    conn.close()


@pytest.mark.parametrize("path", ["/", "/jenkins/"])
def test_ingress_accepts_20_mib_limit(proxy, path):
    port, _, _ = proxy
    size = 20 * 1024 * 1024
    conn, response = request(port, "POST", path, headers={"Cookie": "sessionid=valid"}, body=b"x" * size)
    assert response.status == 200
    assert response.read() == str(size).encode()
    conn.close()


@pytest.mark.parametrize("path", ["/", "/jenkins/", "/api/v1/action-history/1/stream/", "/api/v1/jenkins/jobs/job/1/stream/"])
@pytest.mark.parametrize("chunked", [False, True])
def test_ingress_enforces_20_mib_limit(proxy, path, chunked):
    port, _, _ = proxy
    body = iter([b"x" * (20 * 1024 * 1024 + 1)]) if chunked else None
    headers = {} if chunked else {"Content-Length": str(20 * 1024 * 1024 + 1)}
    conn, response = request(port, "POST", path, headers=headers, body=body, encode_chunked=chunked)
    assert response.status == 413
    response.read()
    conn.close()


@pytest.mark.parametrize("path", ["/api/v1/action-history/1/stream/", "/api/v1/jenkins/jobs/job/1/stream/"])
def test_ingress_streams_incrementally(proxy, path):
    port, _, _ = proxy
    started = time.monotonic()
    conn, response = request(port, "GET", path)
    assert response.status == 200
    assert response.readline() == b"data: first\n"
    assert time.monotonic() - started < 2
    assert response.readline() == b"\n"
    assert response.readline() == b"data: second\n"
    response.read()
    conn.close()


@pytest.mark.skipif(
    os.environ.get("NITA_K8S_REQUIRE_NETWORK_POLICY") != "1",
    reason="Requires a policy-enforcing Kubernetes CNI",
)
def test_jenkins_network_policy_restricts_direct_access(proxy):
    _, _, namespace = proxy
    check = "import socket; socket.create_connection(('jenkins', 8080), 2).close()"
    allowed = subprocess.run(
        ["kubectl", "exec", "-n", namespace, "deployment/webapp", "--", "python3", "-c", check],
        capture_output=True, text=True,
    )
    assert allowed.returncode == 0, allowed.stderr
    denied = subprocess.run(
        ["kubectl", "exec", "-n", namespace, "deployment/intruder", "--", "python3", "-c", check],
        capture_output=True, text=True,
    )
    assert denied.returncode != 0
    assert "timed out" in denied.stderr


def test_nginx_to_traefik_upgrade_rerun_and_rollback(proxy, tmp_path):
    _, cert, namespace = proxy
    key = cert.with_name("tls.key")
    cert_dir = tmp_path / "certificates"
    cert_dir.mkdir()
    (cert_dir / "nginx-certificate.crt").write_bytes(cert.read_bytes())
    (cert_dir / "nginx-certificate-key.key").write_bytes(key.read_bytes())
    nginx_config = """events {}
http {
    server {
        listen 443 ssl;
        listen 8000;
        ssl_certificate /etc/certificate/nginx-certificate.crt;
        ssl_certificate_key /etc/certificate/nginx-certificate-key.key;
        location / { proxy_pass http://webapp:8000; }
    }
}
"""
    old = yaml.safe_load((ROOT / "k8s/proxy-deployment.yaml").read_text())
    old["metadata"]["namespace"] = namespace
    old_pod = old["spec"]["template"]["spec"]
    old_pod.pop("serviceAccountName")
    old_pod["containers"] = [{
        "name": "proxy", "image": "nginx:stable", "ports": [{"containerPort": 443}],
        "volumeMounts": [
            {"name": "config", "mountPath": "/etc/nginx"},
            {"name": "cert", "mountPath": "/etc/certificate"},
        ],
    }]
    old_pod["volumes"] = [
        {"name": "config", "configMap": {"name": "proxy-config-cm"}},
        {"name": "cert", "configMap": {"name": "proxy-cert-cm"}},
    ]
    resources = [
        {"apiVersion": "v1", "kind": "ConfigMap",
         "metadata": {"name": "proxy-config-cm", "namespace": namespace}, "data": {"nginx.conf": nginx_config}},
        {"apiVersion": "v1", "kind": "ConfigMap",
         "metadata": {"name": "proxy-cert-cm", "namespace": namespace}, "data": {
             "nginx-certificate.crt": cert.read_text(), "nginx-certificate-key.key": key.read_text(),
         }},
        old,
    ]
    kubectl("apply", "-f", "-", input=json.dumps({"apiVersion": "v1", "kind": "List", "items": resources}),
            text=True, stdout=subprocess.DEVNULL)
    kubectl("rollout", "status", "deployment/proxy", "-n", namespace, "--timeout=180s")

    static = yaml.safe_load((ROOT / "k8s/traefik/traefik.yaml").read_text())
    static["providers"]["kubernetesIngress"]["namespaces"] = [namespace]
    static_file = tmp_path / "traefik.yaml"
    static_file.write_text(yaml.safe_dump(static))
    wrapper = tmp_path / "kubectl"
    wrapper.write_text(
        "#!/usr/bin/env python3\n"
        "import os, sys\n"
        "args = [os.environ['TEST_NAMESPACE'] if arg == 'nita' else arg for arg in sys.argv[1:]]\n"
        "args = ['--from-file=traefik.yaml=' + os.environ['TEST_STATIC_FILE'] "
        "if arg == '--from-file=traefik.yaml=traefik/traefik.yaml' else arg for arg in args]\n"
        "os.execv('/usr/bin/kubectl', ['/usr/bin/kubectl', *args])\n"
    )
    wrapper.chmod(0o755)
    env = {**os.environ, "PATH": f"{tmp_path}:{os.environ['PATH']}", "TEST_NAMESPACE": namespace,
           "TEST_STATIC_FILE": str(static_file), "CERTS": str(cert_dir)}
    backup = tmp_path / "rollback"
    subprocess.run(["python3", str(ROOT / "k8s/backup-proxy.py"), str(backup)], env=env, check=True)
    for _ in range(2):
        subprocess.run(["bash", str(ROOT / "k8s/prepare-traefik.sh")], env=env, check=True)
    deployed_cert = kubectl("get", "secret", "nita-traefik-tls", "-n", namespace, "-o", "json",
                            capture_output=True, text=True)
    assert base64.b64decode(json.loads(deployed_cert.stdout)["data"]["tls.crt"]) == cert.read_bytes()

    new = yaml.safe_load((ROOT / "k8s/proxy-deployment.yaml").read_text())
    new["metadata"]["namespace"] = namespace
    for port in new["spec"]["template"]["spec"]["containers"][0]["ports"]:
        port.pop("hostPort", None)
    kubectl("apply", "-f", "-", input=json.dumps(new), text=True, stdout=subprocess.DEVNULL)
    kubectl("rollout", "status", "deployment/proxy", "-n", namespace, "--timeout=180s")

    def check_certificate():
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        forward = subprocess.Popen(
            ["kubectl", "port-forward", "-n", namespace, "deployment/proxy", f"{port}:443"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        try:
            for _ in range(60):
                try:
                    with socket.create_connection(("127.0.0.1", port), timeout=1) as raw:
                        with ssl._create_unverified_context().wrap_socket(raw, server_hostname=None) as secure:
                            if secure.getpeercert(binary_form=True) == ssl.PEM_cert_to_DER_cert(cert.read_text()):
                                return
                except OSError:
                    pass
                time.sleep(1)
            raise AssertionError("proxy did not present the original certificate")
        finally:
            forward.terminate()
            forward.wait(timeout=10)

    check_certificate()
    subprocess.run(["bash", str(ROOT / "k8s/prepare-traefik.sh")], env=env, check=True)
    kubectl("apply", "-f", str(backup / "proxy-and-webapp.json"), stdout=subprocess.DEVNULL)
    kubectl("rollout", "status", "deployment/proxy", "-n", namespace, "--timeout=180s")
    check_certificate()
