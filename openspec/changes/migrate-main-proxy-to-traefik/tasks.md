## 1. Controller and routing

- [ ] 1.1 Select and pin a supported multi-architecture Traefik release; vendor and document its minimal controller, class, RBAC and any required CRD resources.
- [ ] 1.2 Replace the main `proxy` Deployment with Traefik while preserving its selector, label, restart interface, host port, readiness and internal HTTP listener.
- [ ] 1.3 Define dedicated-class routes, Jenkins session forward-auth, identity/header spoof protection and login redirect, TLS selection, request-size limits and stream-safe timeout settings.
- [ ] 1.4 Verify Jenkins NetworkPolicy permits the proxy without broadening other access; ensure the deployment workflow applies it.

## 2. Installation and migration

- [ ] 2.1 Update fresh installation, resource preflight and apply ordering for controller configuration and TLS Secrets; preserve existing path overrides.
- [ ] 2.2 Implement and document an idempotent existing-install migration that retains certificate identity, reports failures and supports rollback.
- [ ] 2.3 Replace the MCP Nginx sidecar, preserving the loopback backend, port 8090, `/mcp` normalization, secret-backed token injection and 3600-second streaming timeout.
- [ ] 2.4 Implement and document optional MCP upgrade, token rotation, error handling and rollback; update NITA documentation and software inventory for all affected images.
- [ ] 2.5 Coordinate the companion `nita-webapp` change for Compose, proxy specifications and tests; coordinate Jenkins session-gate changes across repositories.

## 3. Verification

- [ ] 3.1 Update installer regression and manifest validation tests; check RBAC, Ingress class isolation, image pinning and certificate prerequisite failures.
- [ ] 3.2 Extend Kind CI to exercise the proxy over HTTPS, including certificate identity, webapp and Jenkins routes, forwarded headers, slash redirects, request-size limits, login redirects, session-based identity and spoofed-header rejection.
- [ ] 3.3 Test both SSE routes for incremental delivery and the full 1850-second idle threshold; verify Jenkins NetworkPolicy with a policy-enforcing cluster.
- [ ] 3.4 Exercise fresh install, upgrade, rerun and rollback, preserving an existing certificate; verify optional MCP access, client Authorization replacement, token rotation, streaming and absence when declined.
- [ ] 3.5 Run relevant tests and strict OpenSpec validation; verify amd64 and the existing gated arm64 integration path.
- [ ] 3.6 Validate MCP's 3600-second idle threshold with a controllable backend; verify secrets and tokens are not exposed in logs or client responses.
