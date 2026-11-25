## Why

NITA's main Kubernetes entry point depends on an Nginx configuration downloaded
from the webapp repository. Nginx is also used by the optional Junos MCP
sidecar and the webapp's Docker Compose deployment. Moving these proxy usages
to Traefik makes the main Kubernetes routes declarative while retaining their
existing externally visible behavior.

## What Changes

- Replace the main Nginx proxy with a pinned Traefik controller and Ingress
  resources, preserving HTTPS on host port 443, webapp and Jenkins URLs, TLS
  certificates, Jenkins session authentication and identity, and streaming.
- Replace the optional MCP Nginx sidecar with a Traefik sidecar while keeping
  port 8090, the loopback backend, and internal token injection.
- Migrate the webapp's Docker Compose proxy in a coordinated companion change.
- Keep the `proxy` deployment and `nita-cmd proxy restart` interface compatible;
  limit the controller to NITA's Ingress class and necessary permissions.
- Update installation, upgrades, certificate handling, NetworkPolicy, CI,
  inventory, and operator documentation, including rollback instructions.
- Validate traffic through the actual proxy rather than only direct backend
  port-forwards.

## Capabilities

### New Capabilities

- `ingress`: NITA's controller, routes, TLS, streaming, and upgrade behavior.
- `mcp-proxy`: Optional MCP proxy and its authentication boundary.

### Modified Capabilities

- `kubernetes`: Replace the main proxy implementation while retaining the
  existing deployment and service access contracts.
- `installation`: Install and upgrade the controller and its TLS resources.
- `cli`: Retain the proxy restart command with the new implementation.

## Impact

Changes are expected in `k8s/`, `install.sh`, CI setup, integration tests,
software inventory, documentation, and OpenSpec. The companion change in
`nita-webapp` migrates Compose and updates its proxy specifications and tests.
The existing Jenkins session-gate changes in the webapp and Jenkins repositories
must be coordinated so that the proxy swap does not weaken authentication.
The webapp companion change also depends on a separate console-streaming spec
cleanup to resolve its existing strict-validation length warnings.
The webapp forward-auth endpoint will change incompatibly for Traefik, so the
old Nginx proxy and old webapp image must be rolled back together.

Changing Jenkins' listeners or the webapp API is out of scope. This change does
not add automated certificate issuance, a cluster-wide default ingress
controller, or a load balancer.
