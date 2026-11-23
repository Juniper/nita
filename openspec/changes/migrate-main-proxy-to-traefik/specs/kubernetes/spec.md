## MODIFIED Requirements

### Requirement: Core Pod Deployments
The system SHALL deploy and keep running four persistent deployments:
`webapp`, `jenkins`, `proxy`, and `db`. The `proxy` deployment SHALL run the
dedicated Traefik Ingress controller.

#### Scenario: All pods reach Running state
- **GIVEN** the k8s manifests have been applied with `apply-k8s.sh`
- **WHEN** `kubectl get pods -n nita` is run after 2 minutes
- **THEN** webapp, jenkins, proxy and db pods all show STATUS Running

### Requirement: Services and Port Exposure
The system SHALL expose the webapp on port 8000 and Jenkins on port 8443 within
the cluster. The proxy SHALL provide HTTPS on host port 443 and an in-pod HTTP
listener on port 8000, without exposing port 8000 on the host.

#### Scenario: Webapp service reachable
- **GIVEN** the webapp deployment and service are applied
- **WHEN** an in-cluster request is made to the webapp service on port 8000
- **THEN** a valid HTTP response is returned

#### Scenario: Proxy HTTPS reachable
- **GIVEN** the controller is ready and its certificate is configured
- **WHEN** a client connects to the host on port 443
- **THEN** the proxy serves the NITA routes over HTTPS
