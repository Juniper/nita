## ADDED Requirements

### Requirement: MCP sidecar proxy
The optional Junos MCP deployment SHALL use a Traefik sidecar on host port 8090
to forward MCP requests to the authenticated backend on loopback port 8091.
The proxy SHALL normalize `/mcp` to `/mcp/`, preserve relevant request headers,
and support streamable HTTP without buffering and with at least 3600 seconds of
idle time. The existing unauthenticated external HTTP interface SHALL be
documented as lab/demo-only.

#### Scenario: MCP client request
- **GIVEN** the optional MCP deployment is ready
- **WHEN** a client sends a supported MCP request to `http://<node-ip>:8090/mcp/`
- **THEN** the request reaches the backend and the MCP response is returned

#### Scenario: MCP idle stream
- **WHEN** a healthy stream remains idle for 3600 seconds and then emits an event
- **THEN** the proxy keeps the connection open and delivers the event

### Requirement: Internal MCP token injection
The sidecar SHALL inject a bearer token accepted by the backend, overriding any
client-supplied Authorization header. Token-bearing proxy configuration SHALL
be stored in a Kubernetes Secret, not a ConfigMap, and the token SHALL NOT
appear in proxy responses or logs. Installation and rotation SHALL report
failures rather than silently leaving the proxy and backend with mismatched tokens.

#### Scenario: Client supplies a different token
- **WHEN** a client sends an MCP request with its own Authorization header
- **THEN** the backend receives the configured internal bearer token instead

#### Scenario: Existing optional deployment is upgraded
- **GIVEN** a running MCP deployment and a usable existing internal token
- **WHEN** its proxy is migrated
- **THEN** the existing token remains valid and clients need no token

#### Scenario: Optional deployment was declined
- **WHEN** MCP was not selected for installation
- **THEN** the migration does not create an MCP deployment or token
