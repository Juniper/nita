## ADDED Requirements

### Requirement: JTAF project role generation
The system SHALL support creating a project-local JTAF Ansible role from one or more YANG source paths and a device XML configuration, and SHALL include that role in the project archive and build playbook.

#### Scenario: Role generation creates valid project assets
- **GIVEN** a project created from the `jtaf-ansible` profile
- **WHEN** `nitaprj.sh generate-role <project> -p <yang-path> -x <xml-config> -t <device-type>` is run
- **THEN** a `roles/<type>_role/` directory is created under the project
- **AND** the generated role contains `tasks/main.yml`, `templates/template.j2`, and a valid JTAF filter plugin contract
- **AND** the project manifest includes the generated role and filter plugin paths

#### Scenario: Role generation is idempotent
- **GIVEN** a project that already contains a generated JTAF role for a device type
- **WHEN** the same `generate-role` command is run again
- **THEN** the generated files are replaced in place
- **AND** no stale role fragments remain in the project tree

#### Scenario: Generated project remains buildable
- **GIVEN** a project generated from JTAF inputs
- **WHEN** the project archive is built
- **THEN** the project's `build/sites.yaml` references the generated role and the role's files are included in the package
- **AND** the project can be uploaded and used by the NITA webapp as a valid network-type package

### Requirement: JTAF profile contract
A `jtaf-ansible` project profile SHALL define the default project skeleton needed for role generation and build execution, including `project.yaml`, `ansible.cfg`, inventory, group variables, and build directory structure.

#### Scenario: New profile is available to project creation
- **GIVEN** a NITA operator creates a new project with the `jtaf-ansible` profile
- **WHEN** the project directory is created
- **THEN** the skeleton includes a role-ready layout with `roles/`, `filter_plugins/`, `configs/`, and `build/`
- **AND** project actions are present for generate, build, dump, and test steps
