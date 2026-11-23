## MODIFIED Requirements

### Requirement: Proxy Restart
The system SHALL provide `nita-cmd proxy restart` to restart the Traefik proxy
deployment.

#### Scenario: Proxy restart
- **GIVEN** the proxy pod is running
- **WHEN** `nita-cmd proxy restart` is run
- **THEN** the proxy pod is restarted and returns to Running state
