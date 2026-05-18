# CLI Specification

## Purpose
`nita-cmd` is the primary command-line interface for controlling NITA. It is a
bash-based dispatcher that maps hierarchical sub-commands to named scripts
stored in `/usr/local/bin`.

## Requirements

### Requirement: Interactive Mode
The system SHALL enter an interactive shell when `nita-cmd` is invoked with no
arguments.

#### Scenario: Enter and exit interactive mode
- GIVEN a user runs `nita-cmd` with no arguments
- WHEN the interactive prompt appears
- THEN typing `help` lists all available commands
- AND typing `exit` returns to the parent shell

### Requirement: Help Output
The system SHALL display usage instructions when called with the `help` argument
or when a sub-command is followed by `help`.

#### Scenario: Top-level help
- GIVEN a user runs `nita-cmd help`
- WHEN the command executes
- THEN all top-level sub-commands are listed with one-line descriptions

#### Scenario: Sub-command help
- GIVEN a user runs `nita-cmd kube help`
- WHEN the command executes
- THEN all `kube` sub-commands are listed with their descriptions

### Requirement: Kubernetes Cluster Commands
The system SHALL provide `nita-cmd kube` sub-commands for inspecting the
Kubernetes cluster.

#### Scenario: List pods
- GIVEN NITA is deployed and running
- WHEN `nita-cmd kube pods` is run
- THEN the NAME, READY, STATUS, RESTARTS and AGE of each pod in the nita
  namespace are displayed

#### Scenario: List nodes
- GIVEN a user runs `nita-cmd kube nodes`
- WHEN the command executes
- THEN all Kubernetes nodes are listed with their status

#### Scenario: List config-maps
- GIVEN a user runs `nita-cmd kube cm`
- WHEN the command executes
- THEN all config-maps in the nita namespace are listed

#### Scenario: List namespaces
- GIVEN a user runs `nita-cmd kube ns all`
- WHEN the command executes
- THEN all configured Kubernetes namespaces are listed

### Requirement: Database Restart
The system SHALL provide `nita-cmd db restart` to restart the MariaDB pod.

#### Scenario: Database restart
- GIVEN the MariaDB pod is running
- WHEN `nita-cmd db restart` is run
- THEN the db pod is restarted and returns to Running state

### Requirement: Proxy Restart
The system SHALL provide `nita-cmd proxy restart` to restart the nginx proxy pod.

#### Scenario: Proxy restart
- GIVEN the proxy pod is running
- WHEN `nita-cmd proxy restart` is run
- THEN the proxy pod is restarted and returns to Running state

### Requirement: Extensibility
The system SHALL allow additional commands to be added by placing executable
scripts prefixed with `nita-cmd_` in `/usr/local/bin`.

#### Scenario: Custom command registration
- GIVEN a script named `nita-cmd_hello` exists in `/usr/local/bin` and is executable
- WHEN a user runs `nita-cmd hello`
- THEN the script executes and its output is shown

#### Scenario: Custom command help
- GIVEN a script named `nita-cmd_hello_help` exists in `/usr/local/bin`
- WHEN a user runs `nita-cmd hello help`
- THEN the help script executes and its output is shown

### Requirement: Debug Output
The system SHALL emit the underlying shell commands to stderr when the
`_CLI_RUNNER_DEBUG` environment variable is set to 1.

#### Scenario: Debug mode
- GIVEN `export _CLI_RUNNER_DEBUG=1` has been run
- WHEN any `nita-cmd` sub-command is invoked
- THEN the underlying command is printed to stderr before execution
