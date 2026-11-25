## ADDED Requirements

### Requirement: Ingress installation and upgrade
The installer SHALL provision NITA's Traefik controller and required TLS and
route resources before reporting successful deployment. It SHALL preserve
`PROXY` and `CERTS` path overrides. An upgrade SHALL reuse the existing
certificate and key from the configured files or existing proxy certificate
ConfigMap and SHALL report a missing or invalid pair without replacing the
running proxy. Fresh installs SHALL retain self-signed certificate generation.

#### Scenario: Fresh installation
- **GIVEN** a new NITA installation
- **WHEN** the installer provisions the main proxy
- **THEN** it generates a self-signed certificate and configures Traefik to use it

#### Scenario: Existing installation is upgraded
- **GIVEN** a usable existing certificate and key
- **WHEN** the installer upgrades the proxy
- **THEN** it imports that pair into a TLS Secret and retains certificate identity

#### Scenario: Apply prerequisites are missing
- **WHEN** the deployment script cannot find a required ingress configuration
  or TLS resource
- **THEN** it exits with an explicit diagnostic before applying the proxy workload

### Requirement: Optional MCP proxy migration
The installer SHALL replace the optional MCP Nginx sidecar with Traefik when
the MCP installation or upgrade is selected. It SHALL retain the
existing internal token during migration, configure the proxy using a Secret,
and report unusable or mismatched token configuration without silently deploying
a broken authentication path.

#### Scenario: MCP is not installed
- **GIVEN** MCP is not already installed
- **WHEN** the installer is run and the optional MCP component is declined
- **THEN** no MCP proxy or token is created
