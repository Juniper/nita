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
