#!/usr/bin/env python3
import base64
import datetime
import json
import os
import re
import secrets
import subprocess
import sys
import tempfile
from pathlib import Path


def kubectl_get(kind, name):
    result = subprocess.run(
        ["kubectl", "get", kind, name, "-n", "nita", "--ignore-not-found", "-o", "json"],
        text=True,
        capture_output=True,
        check=True,
    )
    return json.loads(result.stdout) if result.stdout.strip() else None


def secret_value(secret, key):
    return base64.b64decode(secret["data"][key], validate=True).decode("utf-8")


def main():
    legacy = kubectl_get("secret", "junos-mcp-auth")
    current = kubectl_get("secret", "junos-mcp-traefik-auth")
    deployment = kubectl_get("deployment", "junos-mcp")
    source_name = "junos-mcp-traefik-auth" if current else "junos-mcp-auth"
    if deployment:
        if not current and not legacy:
            raise ValueError("the existing MCP deployment has no authentication secret")
        pod = deployment["spec"]["template"]["spec"]
        backend = next((container for container in pod["containers"] if container["name"] == "junos-mcp"), None)
        if not backend:
            raise ValueError("the existing MCP deployment has no backend container")
        token_mount = next((mount for mount in backend.get("volumeMounts", [])
                            if mount["mountPath"] == "/app/.tokens"), None)
        if not token_mount:
            raise ValueError("the existing MCP backend has no token mount")
        token_volume = next((volume for volume in pod.get("volumes", [])
                             if volume["name"] == token_mount["name"]), None)
        if not token_volume or "secret" not in token_volume:
            raise ValueError("the existing MCP token mount does not use a Secret")
        source_name = token_volume["secret"]["secretName"]
        if source_name not in ("junos-mcp-auth", "junos-mcp-traefik-auth"):
            raise ValueError(f"unsupported MCP authentication Secret {source_name}")
    source = current if source_name == "junos-mcp-traefik-auth" else legacy
    if deployment and not source:
        raise ValueError(f"the active MCP authentication Secret {source_name} is missing")
    requested_token = os.environ.get("JUNOS_MCP_TOKEN_VALUE", "")
    token_id = os.environ.get("JUNOS_MCP_TOKEN_ID", "nita-lab")

    if source:
        tokens = json.loads(secret_value(source, ".tokens"))
        if token_id not in tokens or not isinstance(tokens[token_id].get("token"), str):
            raise ValueError("the existing MCP token ID is missing or invalid")
        token = tokens[token_id]["token"]
        if not token:
            raise ValueError("the existing MCP token is empty")
        rotate = os.environ.get("JUNOS_MCP_ROTATE", "false") == "true"
        if requested_token and requested_token != token and not rotate:
            raise ValueError("requested MCP token differs from the existing token; set JUNOS_MCP_ROTATE=true to rotate")
        if source_name == "junos-mcp-traefik-auth":
            routes = json.loads(secret_value(source, "routes.yaml"))
            configured = routes["http"]["middlewares"]["auth"]["headers"]["customRequestHeaders"]["Authorization"]
        else:
            config = kubectl_get("configmap", "junos-mcp-proxy-cm")
            if not config:
                raise ValueError("the existing MCP proxy ConfigMap is missing")
            match = re.search(
                r'^\s*proxy_set_header\s+Authorization\s+"Bearer ([^"]+)"\s*;',
                config["data"]["default.conf"],
                re.MULTILINE,
            )
            if not match:
                raise ValueError("the existing MCP proxy token configuration is invalid")
            configured = "Bearer " + match.group(1)
        if configured != "Bearer " + token:
            raise ValueError("the existing MCP proxy and backend tokens do not match")
        if rotate:
            if not requested_token:
                raise ValueError("JUNOS_MCP_ROTATE requires JUNOS_MCP_TOKEN_VALUE")
            token = requested_token
            tokens[token_id]["token"] = token
    else:
        if deployment:
            raise ValueError("the existing MCP deployment has no authentication secret")
        token = requested_token or "jmcp_" + secrets.token_hex(24)
        tokens = {token_id: {
            "token": token,
            "description": "NITA lab/demo internal token",
            "created": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }}

    routes = {
        "http": {
            "routers": {
                "mcp": {
                    "rule": "Path(`/mcp`) || PathPrefix(`/mcp/`)",
                    "entryPoints": ["mcp"],
                    "service": "backend",
                    "middlewares": ["slash", "auth"],
                }
            },
            "middlewares": {
                "slash": {"replacePathRegex": {"regex": "^/mcp$", "replacement": "/mcp/"}},
                "auth": {"headers": {"customRequestHeaders": {"Authorization": "Bearer " + token}}},
            },
            "services": {"backend": {"loadBalancer": {"servers": [{"url": "http://127.0.0.1:8091"}]}}},
        }
    }
    with tempfile.TemporaryDirectory(prefix="nita-mcp-") as directory:
        token_file = Path(directory) / "tokens.json"
        routes_file = Path(directory) / "routes.yaml"
        token_file.write_text(json.dumps(tokens), encoding="utf-8")
        routes_file.write_text(json.dumps(routes), encoding="utf-8")
        manifest = subprocess.run(
            ["kubectl", "create", "secret", "generic", "junos-mcp-traefik-auth", "-n", "nita",
             f"--from-file=.tokens={token_file}", f"--from-file=routes.yaml={routes_file}",
             "--dry-run=client", "-o", "yaml"],
            check=True, stdout=subprocess.PIPE,
        )
        subprocess.run(["kubectl", "apply", "-f", "-"], input=manifest.stdout, check=True)


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, TypeError, subprocess.CalledProcessError) as error:
        print(f"Error preparing MCP Traefik authentication: {error}", file=sys.stderr)
        sys.exit(1)
