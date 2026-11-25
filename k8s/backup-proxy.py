#!/usr/bin/env python3
"""Save apply-ready proxy resources for a coordinated rollback."""

import json
import os
import subprocess
import sys
from pathlib import Path


def resource(kind, name, required=False):
    result = subprocess.run(
        ["kubectl", "get", kind, name, "-n", "nita", "--ignore-not-found", "-o", "json"],
        text=True, capture_output=True, check=True,
    )
    if not result.stdout.strip():
        if required:
            raise ValueError(f"required {kind}/{name} does not exist")
        return None
    value = json.loads(result.stdout)
    metadata = value["metadata"]
    for key in ("resourceVersion", "uid", "generation", "creationTimestamp",
                "managedFields", "deletionTimestamp", "deletionGracePeriodSeconds"):
        metadata.pop(key, None)
    metadata.get("annotations", {}).pop("kubectl.kubernetes.io/last-applied-configuration", None)
    value.pop("status", None)
    return value


def save(path, values):
    with path.open("x", encoding="utf-8") as target:
        json.dump({"apiVersion": "v1", "kind": "List", "items": values}, target, indent=2)
        target.write("\n")


def ensure_config_sources(deployment, resources):
    pod = deployment["spec"]["template"]["spec"]
    sources = {
        (kind, volume[kind]["name"] if kind == "configMap" else volume[kind]["secretName"])
        for volume in pod.get("volumes", [])
        for kind in ("configMap", "secret") if kind in volume
    }
    for volume in pod.get("volumes", []):
        for source in volume.get("projected", {}).get("sources", []):
            for kind in ("configMap", "secret"):
                if kind in source:
                    sources.add((kind, source[kind]["name"]))
    for container in pod.get("initContainers", []) + pod.get("containers", []):
        for source in container.get("envFrom", []):
            for field, kind in (("configMapRef", "configMap"), ("secretRef", "secret")):
                if field in source:
                    sources.add((kind, source[field]["name"]))
        for variable in container.get("env", []):
            source = variable.get("valueFrom", {})
            for field, kind in (("configMapKeyRef", "configMap"), ("secretKeyRef", "secret")):
                if field in source:
                    sources.add((kind, source[field]["name"]))
    saved_sources = {
        ("configMap" if item["kind"] == "ConfigMap" else "secret", item["metadata"]["name"])
        for item in resources
    }
    if not sources.issubset(saved_sources):
        raise ValueError(f"{deployment['metadata']['name']} references resources not included in the backup: {sources - saved_sources}")


def main(directory):
    os.umask(0o077)
    directory.mkdir(mode=0o700, parents=True, exist_ok=False)
    proxy = resource("deployment", "proxy", required=True)
    webapp = resource("deployment", "webapp", required=True)
    main_resources = []
    for kind, name in (
        ("configmap", "proxy-config-cm"), ("configmap", "proxy-cert-cm"),
        ("configmap", "nita-traefik-config"), ("configmap", "nita-traefik-bodylimit"),
        ("configmap", "nita-traefik-identityguard"), ("secret", "nita-traefik-tls"),
    ):
        value = resource(kind, name)
        if value:
            main_resources.append(value)
    ensure_config_sources(proxy, main_resources)
    main_resources.extend([webapp, proxy])
    save(directory / "proxy-and-webapp.json", main_resources)
    mcp = resource("deployment", "junos-mcp")
    if mcp:
        mcp_resources = []
        for kind, name in (
            ("configmap", "junos-mcp-devices-cm"), ("configmap", "junos-mcp-proxy-cm"),
            ("secret", "junos-mcp-auth"), ("secret", "junos-mcp-traefik-auth"),
        ):
            value = resource(kind, name)
            if value:
                mcp_resources.append(value)
        ensure_config_sources(mcp, mcp_resources)
        mcp_resources.append(mcp)
        save(directory / "mcp.json", mcp_resources)
    print(f"Proxy backup saved in {directory}; restrict access because it contains secrets.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} NEW_BACKUP_DIRECTORY", file=sys.stderr)
        sys.exit(2)
    try:
        main(Path(sys.argv[1]))
    except subprocess.CalledProcessError as error:
        print(f"Error backing up proxy resources: {error}: {error.stderr.strip()}", file=sys.stderr)
        sys.exit(1)
    except (OSError, ValueError, KeyError) as error:
        print(f"Error backing up proxy resources: {error}", file=sys.stderr)
        sys.exit(1)
