# Projects Specification

## Purpose
A NITA project (network type) packages the Ansible roles, templates, and
configuration needed to build and test a specific network topology. Projects
are uploaded as zip archives and linked to networks via the webapp.

## Requirements

### Requirement: Project Archive Format
A network-type project SHALL be packaged as a zip file containing at minimum a
`project.yaml` manifest and an `ansible.cfg` file at the top level of a named
folder inside the archive.

#### Scenario: Valid project upload
- GIVEN a zip file with structure `<name>/project.yaml` and `<name>/ansible.cfg`
- WHEN the zip is uploaded via POST /api/v1/network-types/upload/
- THEN the network type is registered and its name and id are returned

#### Scenario: Missing project.yaml
- GIVEN a zip file without a project.yaml
- WHEN the zip is uploaded
- THEN a 400 error is returned with a descriptive failure reason

### Requirement: project.yaml Structure
The `project.yaml` file SHALL define the project name, description, and one or
more actions. Each action SHALL specify a name, a Jenkins URL fragment, and an
action category (BUILD or TEST).

#### Scenario: Actions parsed from project.yaml
- GIVEN a project.yaml with four actions (Build, Build base config,
  Dump configuration, Test)
- WHEN the project is uploaded
- THEN GET /api/v1/actions/?campus_type_id=<id> returns all four actions

### Requirement: Ansible Inventory (hosts file)
A NITA network SHALL use an Ansible INI-format inventory file to declare the
device groups and hostnames that Ansible will target.

#### Scenario: hosts file stored on network creation
- GIVEN a valid Ansible inventory string
- WHEN POST /api/v1/networks/ is called with that string as host_file
- THEN the inventory is stored and returned verbatim on GET /api/v1/networks/{id}/

### Requirement: Workbook Data (Excel)
Configuration data for a network SHALL be supplied as an Excel (.xlsx) workbook
where each sheet corresponds to an Ansible variable group.

#### Scenario: Workbook upload populates configuration
- GIVEN a valid .xlsx workbook for the network's topology
- WHEN the workbook is uploaded via POST /api/v1/networks/{id}/workbook/upload/
- THEN the sheet data is stored and retrievable via GET /api/v1/networks/{id}/workbook/

#### Scenario: Workbook download
- GIVEN a network with stored workbook data
- WHEN GET /api/v1/networks/{id}/workbook/download/ is called
- THEN an .xlsx file is returned as a file attachment

### Requirement: Example Projects
The NITA repository SHALL ship with at least the following example projects to
demonstrate platform capability: `evpn_vxlan_erb_dc` (EVPN VXLAN data centre)
and `ebgp_wan` (eBGP WAN topology).

#### Scenario: EVPN example runnable
- GIVEN NITA is installed and the evpn_vxlan_erb_dc project is uploaded
- WHEN the Build action is triggered for a network using that project
- THEN Jenkins executes the build job without error

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
