## ADDED Requirements

### Requirement: Kubernetes Certificate Renewal Command
The system SHALL provide `nita-cmd kube renew-certs` as a dedicated
sub-command for Kubernetes certificate renewal operations.

#### Scenario: Command is discoverable via help
- **GIVEN** the CLI scripts are installed
- **WHEN** `nita-cmd kube help` is run
- **THEN** an entry for `nita-cmd kube renew-certs` is listed with a one-line
  description

#### Scenario: Renewal command executes on supported environments
- **GIVEN** a host where `kubeadm` is available and the user has required
  privileges
- **WHEN** `nita-cmd kube renew-certs` is run
- **THEN** the command executes `kubeadm certs renew all`
- **AND** exits with code 0 when renewal succeeds

#### Scenario: Clear failure on unsupported environments
- **GIVEN** a host where `kubeadm` is not available
- **WHEN** `nita-cmd kube renew-certs` is run
- **THEN** the command prints an actionable unsupported-environment message
- **AND** exits with a non-zero status

#### Scenario: Debug output shows wrapped command
- **GIVEN** `_CLI_RUNNER_DEBUG=1` is set
- **WHEN** `nita-cmd kube renew-certs` is run
- **THEN** the underlying shell command is printed to stderr before execution
