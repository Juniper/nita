"""Rollback snapshots must be reusable and contain their mounted resources."""

import importlib.util
import json
import stat
from pathlib import Path
from unittest.mock import patch

import pytest


path = Path(__file__).resolve().parents[1] / "k8s/backup-proxy.py"
spec = importlib.util.spec_from_file_location("backup_proxy", path)
backup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(backup)


def deployment(name, volumes=()):
    return {
        "kind": "Deployment", "metadata": {"name": name},
        "spec": {"template": {"spec": {"volumes": list(volumes)}}},
    }


def test_snapshot_is_private_and_contains_proxy_and_optional_mcp(tmp_path):
    resources = {
        ("deployment", "proxy"): deployment(
            "proxy", [{"configMap": {"name": "proxy-config-cm"}}]
        ),
        ("deployment", "webapp"): deployment("webapp"),
        ("configmap", "proxy-config-cm"): {"kind": "ConfigMap", "metadata": {"name": "proxy-config-cm"}},
        ("deployment", "junos-mcp"): deployment(
            "junos-mcp", [{"secret": {"secretName": "junos-mcp-auth"}}]
        ),
        ("secret", "junos-mcp-auth"): {"kind": "Secret", "metadata": {"name": "junos-mcp-auth"}},
    }
    def fake_resource(kind, name, required=False):
        value = resources.get((kind, name))
        if required and value is None:
            raise ValueError(f"missing {kind}/{name}")
        return value

    directory = tmp_path / "snapshot"
    with patch.object(backup, "resource", side_effect=fake_resource), patch.object(backup.os, "umask"):
        backup.main(directory)
    assert stat.S_IMODE(directory.stat().st_mode) == 0o700
    assert [item["metadata"]["name"] for item in json.loads(
        (directory / "proxy-and-webapp.json").read_text())["items"]] == [
            "proxy-config-cm", "webapp", "proxy"
        ]
    assert [item["metadata"]["name"] for item in json.loads(
        (directory / "mcp.json").read_text())["items"]] == ["junos-mcp-auth", "junos-mcp"]


def test_snapshot_rejects_unbacked_volume():
    proxy = deployment("proxy", [{"secret": {"secretName": "custom-certificate"}}])
    with pytest.raises(ValueError, match="custom-certificate"):
        backup.ensure_config_sources(proxy, [])


@pytest.mark.parametrize("pod", [
    {"volumes": [{"projected": {"sources": [{"secret": {"name": "custom"}}]}}]},
    {"containers": [{"envFrom": [{"configMapRef": {"name": "custom"}}]}]},
    {"initContainers": [{"env": [{"name": "TOKEN", "valueFrom": {"secretKeyRef": {"name": "custom", "key": "token"}}}]}]},
])
def test_snapshot_rejects_unbacked_projected_and_environment_sources(pod):
    proxy = deployment("proxy")
    proxy["spec"]["template"]["spec"] = pod
    with pytest.raises(ValueError, match="custom"):
        backup.ensure_config_sources(proxy, [])


def test_snapshot_strips_server_managed_metadata():
    result = {
        "kind": "Secret",
        "metadata": {"name": "test", "resourceVersion": "123", "uid": "abc",
                     "annotations": {"kubectl.kubernetes.io/last-applied-configuration": "old"}},
        "status": {"irrelevant": True}, "data": {"key": "dmFsdWU="},
    }
    with patch.object(backup.subprocess, "run") as run:
        run.return_value.stdout = json.dumps(result)
        saved = backup.resource("secret", "test", required=True)
    assert saved == {"kind": "Secret", "metadata": {"name": "test", "annotations": {}},
                     "data": {"key": "dmFsdWU="}}
