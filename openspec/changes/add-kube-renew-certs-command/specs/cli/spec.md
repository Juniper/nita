## ADDED Requirements

### Requirement: Kubernetes Certificate Renewal Command
The system SHALL provide `nita-cmd kube renew-certs` as a dedicated
sub-command that renews kubeadm-managed certificates on the local host.

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

#### Scenario: Renewal reports required follow-up
- **GIVEN** certificate renewal succeeds on a kubeadm control-plane host
- **WHEN** `nita-cmd kube renew-certs` completes
- **THEN** the command reminds the operator to restart the control-plane static
  Pods using the documented procedure
- **AND** the command states that it must be run on every control-plane node in
  a replicated cluster

#### Scenario: Clear failure on unsupported environments
- **GIVEN** a host where `kubeadm` is not available
- **WHEN** `nita-cmd kube renew-certs` is run
- **THEN** the command prints an actionable unsupported-environment message
- **AND** exits with a non-zero status

#### Scenario: Documentation identifies unsupported external CA management
- **GIVEN** a cluster uses certificates managed by an external CA
- **WHEN** an operator consults the certificate renewal documentation
- **THEN** the documentation states that `kubeadm certs renew all` does not
  manage externally signed certificates

#### Scenario: Debug output shows wrapped command
- **GIVEN** `_CLI_RUNNER_DEBUG=1` is set
- **WHEN** `nita-cmd kube renew-certs` is run
- **THEN** the underlying shell command is printed to stderr before execution
