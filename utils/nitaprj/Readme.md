# NITA Project Utility (`nitaprj.sh`)

Use `nitaprj.sh` to create a project from a profile and package it for NITA.
The default profile is `jtaf-ansible`; select `generic` explicitly when you
want the generic template.

The following is an illustrative laptop session. Replace the paths, project
name, devices, and configuration values with those for your environment.
Directory timestamps in the listings are synchronized for this example.

## Prerequisites

- Bash, Python 3.9 or later, Git, `zip`, and either `wget` or `curl`.
- SSH access to the GitHub repositories used in this example.
- A NITA installation to upload and run the resulting project.

## JTAF Ansible profile

This workflow generates an Ansible role from Junos YANG models and device XML
configurations, then packages the role and project variables for NITA.

### 1. Clone the NITA repository

From a working directory, clone NITA and check that the directory was created:

```
vishalc@vishalc-mbp new_jtaf % git clone git@github.com:Juniper/nita.git

vishalc@vishalc-mbp new_jtaf % ls -ltr
drwxr-xr-x  24 vishalc  staff    768 Nov 26 11:10 nita
```

### 2. Clone the junos-terraform repository

Clone junos-terraform alongside NITA. It provides the YANG models and sample
data center XML configurations used to generate the JTAF Ansible role:

```
vishalc@vishalc-mbp new_jtaf % git clone git@github.com:Juniper/junos-terraform.git

vishalc@vishalc-mbp new_jtaf % ls -ltr
drwxr-xr-x  24 vishalc  staff    768 Nov 26 11:10 nita
drwxr-xr-x  30 vishalc  staff    960 Nov 26 11:12 junos-terraform
```

### 3. Create a virtual environment

Create and activate a Python virtual environment, then install the JTAF
generator and YAML-to-Excel utility. Keep the environment active for the
remaining commands:

```
vishalc@vishalc-mbp new_jtaf % python3 -m venv venv

vishalc@vishalc-mbp new_jtaf % source venv/bin/activate

(venv) vishalc@vishalc-mbp new_jtaf % pip install git+ssh://git@github.com/Juniper/junos-terraform.git

(venv) vishalc@vishalc-mbp new_jtaf % pip install git+ssh://git@github.com/Juniper/nita-yaml-to-excel.git
```


### 4. Create the project

Change to NITA's `utils/nitaprj` directory and create `my-fabric`. The default
profile is `jtaf-ansible`; this example answers `y` to initialize a Git
repository, but you can answer `n` instead:

```
(venv) vishalc@vishalc-mbp new_jtaf % cd nita/utils/nitaprj
(venv) vishalc@vishalc-mbp nitaprj % ./nitaprj.sh create my-fabric
Creating project 'my-fabric' using profile 'jtaf-ansible'
Do you want to create a git repository? [y/n]: y
hint: Using 'master' as the name for the initial branch. This default branch name
hint: will change to "main" in Git 3.0. To configure the initial branch name
hint: to use in all of your new repositories, which will suppress this warning,
hint: call:
hint:
hint: 	git config --global init.defaultBranch <name>
hint:
hint: Names commonly chosen instead of 'master' are 'main', 'trunk' and
hint: 'development'. The just-created branch can be renamed via this command:
hint:
hint: 	git branch -m <name>
hint:
hint: Disable this message with "git config set advice.defaultBranchName false"
Initialized empty Git repository in /Users/vishalc/new_jtaf/nita/utils/nitaprj/my-fabric/.git/
Empty project 'my-fabric' created
You can now edit the files in 'my-fabric'
You can run './nitaprj build' to build or test the project inside the project directory
Or
You can run './nitaprj.sh build my-fabric to build or test the project from current directory
```


### 5. Generate the role and variables

From `utils/nitaprj`, generate the role using the bundled JTAF 18.2R3 QFX
models and EVPN-VXLAN XML configurations. Run the command in Bash and check
that the paths and wildcard patterns match the models and devices you intend
to use:

```
(venv) vishalc@vishalc-mbp nitaprj % ./nitaprj.sh generate-role my-fabric \
  -p ../../../junos-terraform/examples/yang/18.2/18.2R3/common \
     ../../../junos-terraform/examples/yang/18.2/18.2R3/junos-qfx/conf/*.yang \
  -x ../../../junos-terraform/examples/evpn-vxlan-dc/dc1/*{spine,leaf}*.xml ../../../junos-terraform/examples/evpn-vxlan-dc/dc2/*spine*.xml \
  -t vqfx \
  -v 18.2R3
```

#### `generate-role` arguments

```text
./nitaprj.sh generate-role <projectname> \
  -p <yang-paths-and-files> -x <xml-config-files> -t <device-type> \
  [-v <yang-version>]
```

| Argument | Meaning |
|---|---|
| `<projectname>` | Existing project directory created by `nitaprj.sh create`. |
| `-p` | Required. One or more YANG search paths and model files. The example supplies the common model directory and QFX configuration models. All arguments up to the next option are passed to `jtaf-yang2ansible`. |
| `-x` | Required. One or more device XML configuration files. They identify the configuration used to filter the schema and are also used to generate inventory and variables. Supply XML for the same device type. |
| `-t` | Required. Device type or role identifier, such as `vqfx`. The role is placed in `roles/<device-type>_role`. It must not contain `/` or `..`. |
| `-v` | Optional. A YANG version label, such as `18.2R3`, printed by the wrapper. It is not passed to the generator and does not select or validate the YANG models; choose the appropriate paths with `-p`. |

The wrapper runs `jtaf-yang2ansible`, copies the generated role and filter
plugins into the project, and adds the role to `build/sites.yaml` and the
manifest. When the expected uncompressed schema is present, it also runs
`jtaf-xml2yaml` to populate `hosts`, `group_vars`, and `host_vars`. Running the
command again for the same device type replaces that generated role directory;
review your project and generated data after each run.

### 6. Review the project and build it

1. Review `my-fabric/hosts`, `group_vars/`, and `host_vars/` for the expected
   devices, management addresses, and configuration values.
2. Review `my-fabric/build/sites.yaml`, the generated role, and `project.yaml`.
   Check `build/runtime.yaml` for the NETCONF connection settings required by
   your environment. The profile contains lab credential defaults; supply
   appropriate credentials securely rather than committing them to the project.

3. Check `my-fabric/manifest` and add any additional files or directories that
   your project needs in its archive.
4. Build the project from `utils/nitaprj`. The following example shows the
   archive entries and the paths of the resulting files:

```
(venv) vishalc@vishalc-mbp nitaprj % ./nitaprj.sh build my-fabric
Building project 'my-fabric'
Building
Current directory is /Users/vishalc/new_jtaf/nita/utils/nitaprj/my-fabric
	zip warning: name not matched: # Files and directories to include in the NITA project archive.
	zip warning: name not matched: # Directories are included recursively.
  adding: ansible.cfg (deflated 32%)
  adding: build/ (stored 0%)
  adding: build/runtime.yaml (deflated 46%)
  adding: build/sites.yaml (deflated 50%)
  adding: build/commit.yaml (deflated 72%)
  adding: build.sh (deflated 57%)
  adding: configs/ (stored 0%)
  adding: configs/.gitkeep (deflated 2%)
  adding: create_ansible_job_k8s.py (deflated 62%)
  adding: enrich_variables.py (deflated 72%)
  adding: filter_plugins/ (stored 0%)
  adding: filter_plugins/.gitkeep (stored 0%)
  adding: filter_plugins/nita_management.py (deflated 76%)
  adding: filter_plugins/jtaf_filters.py (deflated 73%)
  adding: group_vars/ (stored 0%)
  adding: group_vars/all.yaml (stored 0%)
  adding: hosts (deflated 11%)
  adding: host_vars/ (stored 0%)
  adding: host_vars/.gitkeep (stored 0%)
  adding: manifest (deflated 36%)
  adding: make_etc_hosts.yaml (deflated 44%)
  adding: project.yaml (deflated 72%)
  adding: run_build.sh (deflated 51%)
  adding: roles/ (stored 0%)
  adding: roles/vqfx_role/ (stored 0%)
  adding: roles/vqfx_role/tasks/ (stored 0%)
  adding: roles/vqfx_role/tasks/main.yml (deflated 66%)
  adding: roles/vqfx_role/defaults/main.yml (deflated 44%)
  adding: roles/vqfx_role/templates/ (stored 0%)
  adding: roles/.gitkeep (stored 0%)
  adding: roles/vqfx_role/defaults/ (stored 0%)
  adding: roles/vqfx_role/templates/template.j2 (deflated 91%)
Build completed. Project file is /Users/vishalc/new_jtaf/nita/utils/nitaprj/my-fabric/my-fabric.zip
           Variable xlsx file is /Users/vishalc/new_jtaf/nita/utils/nitaprj/my-fabric/my-fabric.xlsx

```

The command produces `my-fabric/my-fabric.zip` and
`my-fabric/my-fabric.xlsx`. It packages the manifest entries and generates the
workbook from YAML files under `group_vars` and `host_vars`, excluding
`registry.yaml`. Existing output files are moved to `.bak` files.

### 7. Use the project in NITA

1. In the NITA web application, add the ZIP as a network type.
2. Add a network using that network type and the project's `hosts` file.
3. Import the generated XLSX workbook into the network configuration. Review
   the configuration and device connectivity before triggering a build.
4. Run the appropriate project action in NITA. Packaging with `nitaprj.sh build`
   does not itself deploy configuration to devices.

For the NITA interface workflow, see [NITA examples](../../docs/nita-examples.md).

## Generic profile

Use this profile when you want to prepare the inventory, playbooks, roles, and
variables yourself rather than generating a JTAF role. The following sample
continues from the laptop setup above, with the virtual environment active and
`yaml2xls.py` installed.

### 1. Create a generic project

From the NITA `utils/nitaprj` directory, create a project with the `generic`
profile. This example answers `n` when prompted to initialize a Git repository:

```
(venv) vishalc@vishalc-mbp nitaprj % ./nitaprj.sh create my-generic-project generic
Creating project 'my-generic-project' using profile 'generic'
Do you want to create a git repository? [y/n]: n
Empty project 'my-generic-project' created
You can now edit the files in 'my-generic-project'
You can run './nitaprj build' to build or test the project inside the project directory
Or
You can run './nitaprj.sh build my-generic-project to build or test the project from current directory
```

The final `generic` argument is required to select this profile.

### 2. Configure the project

1. Edit `my-generic-project/hosts` for your devices and inventory groups.
2. Update the YAML files in `group_vars/` and `host_vars/` with your own
   configuration and connection details. Review the template's lab defaults
   and avoid committing credentials.
3. Customize `build/sites.yaml`, the referenced roles and templates, and
   `project.yaml` for your network. Add any role or template files needed by
   your playbooks; the profile is a starting point, not a complete project for
   every network.
4. Update `manifest` to include the files and directories needed in the ZIP.
   For background on project structure, see [Projects](../../docs/projects.md).

### 3. Build and use the project

After configuring the project, build it from `utils/nitaprj`. This illustrative
output is abbreviated; archive entries and warnings depend on the files in
your project:

```
(venv) vishalc@vishalc-mbp nitaprj % ./nitaprj.sh build my-generic-project
Building project 'my-generic-project'
Building
Current directory is /Users/vishalc/new_jtaf/nita/utils/nitaprj/my-generic-project
	zip warning: name not matched: #list of files to include into package archive
	zip warning: name not matched: #directories are included recursively
  ...
  adding: ansible.cfg (deflated 50%)
  adding: build/ (stored 0%)
  adding: build/sites.yaml (deflated 64%)
  adding: build.sh (deflated 50%)
  adding: create_ansible_job_k8s.py (deflated 52%)
  adding: group_vars/ (stored 0%)
  adding: hosts (deflated 23%)
  adding: host_vars/ (stored 0%)
  ...
Build completed. Project file is /Users/vishalc/new_jtaf/nita/utils/nitaprj/my-generic-project/my-generic-project.zip
           Variable xlsx file is /Users/vishalc/new_jtaf/nita/utils/nitaprj/my-generic-project/my-generic-project.xlsx
```

This creates `my-generic-project/my-generic-project.zip` and
`my-generic-project/my-generic-project.xlsx`. As with the JTAF profile, upload
the ZIP as a network type, create a network with the `hosts` file, import the
workbook, and review the configuration before running a project action.

## Commands from inside a project

Each created project contains a `nitaprj` symlink. From inside the project,
omit the project name when generating a role or building:

```bash
cd /path/to/nita/utils/nitaprj/my-fabric
./nitaprj generate-role -p <yang-paths-and-files> -x <xml-config-files> -t <device-type>
./nitaprj build
```

Replace the placeholders with actual arguments. Paths passed to `generate-role`
are resolved from the current directory. The `create` command is available only
outside a project; use `./nitaprj.sh version` to display the utility version.

## License

See individual files for license information. The default profile and scripts
are licensed under the Apache 2.0 License.
