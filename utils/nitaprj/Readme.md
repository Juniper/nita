# NITA Project Utility (`nitaprj.sh`)

Use `nitaprj.sh` to create a project from a profile and package it for NITA.
The default profile is `jtaf-ansible`; select `generic` explicitly when you
want the generic template.

## Prerequisites

- Bash, Python 3, `zip`, and either `wget` or `curl`.
- `yaml2xls.py` on `PATH` to build either profile. If it is missing, the script
  offers to download and install it. Declining stops the build.
- A NITA installation to upload and run the resulting project.

Run the commands below from the NITA repository's `utils/nitaprj` directory.
The utility looks for `profiles/` relative to the current directory when
creating a project. Replace example paths, project names, devices, and
configuration values with those for your environment.

## JTAF Ansible profile

This workflow generates an Ansible role from Junos YANG models and device XML
configurations, then packages the role and project variables for NITA.

### 1. Install junos-terraform

Install [junos-terraform](https://github.com/Juniper/junos-terraform) before
generating the role and building the project. Its `jtaf-yang2ansible` and
`jtaf-xml2yaml` commands must be available on `PATH`. Follow the
[JTAF setup instructions](https://github.com/Juniper/junos-terraform#setup)
for prerequisites, including Python 3.9+ and Git. For example, with an existing
clone:

```bash
export NITA_ROOT="/path/to/nita"
export JTAF_ROOT="/path/to/junos-terraform"

cd "$JTAF_ROOT"
python3 -m venv venv
. venv/bin/activate
python -m pip install -e .

command -v jtaf-yang2ansible
command -v jtaf-xml2yaml
```

Keep the virtual environment active for the remaining commands. If either
`command -v` produces no path, resolve the installation or `PATH` before
continuing. The [JTAF Ansible guide](https://github.com/Juniper/junos-terraform/blob/master/README-ansible.md)
describes the generator and the Ansible dependencies needed for deployment.

**Compatibility:** This version of `nitaprj.sh` expects the generator to
produce an uncompressed `trimmed_schema.json` and invokes `jtaf-xml2yaml` with
that file. The referenced junos-terraform checkout generates
`trimmed_schema.json.gz` instead. With that version, the wrapper skips XML
conversion and may report role generation as successful without populating the
inventory and variables. Use a compatible JTAF version that produces the
uncompressed schema, or update the wrapper for the newer format before
continuing. Verify the generated inventory and variables before building.

### 2. Create the project

```bash
cd "$NITA_ROOT/utils/nitaprj"
./nitaprj.sh create my-fabric
```

Because no profile was supplied, this creates `my-fabric` using
`jtaf-ansible`. The equivalent explicit command is
`./nitaprj.sh create my-fabric jtaf-ansible`. The script asks whether to
initialize a Git repository; answer `y` or `n`.

### 3. Generate the role and variables

The following example uses the bundled JTAF 18.2R3 QFX models and EVPN-VXLAN
XML configurations. Adjust the paths and patterns for your checkout and
devices. `$JTAF_ROOT` must identify the checkout containing those files.

```bash
./nitaprj.sh generate-role my-fabric \
  -p "$JTAF_ROOT/examples/yang/18.2/18.2R3/common" \
     "$JTAF_ROOT"/examples/yang/18.2/18.2R3/junos-qfx/conf/*.yang \
  -x "$JTAF_ROOT"/examples/evpn-vxlan-dc/dc1/*{spine,leaf}*.xml \
     "$JTAF_ROOT"/examples/evpn-vxlan-dc/dc2/*spine*.xml \
  -t vqfx \
  -v 18.2R3
```

Run this example in Bash so brace and wildcard expansions select the files.
Confirm that the patterns match the intended XML and YANG files before running
the command. Use models for the target platform and Junos release; the example
uses the JTAF 18.2R3 models rather than selecting a release automatically.

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

### 4. Review the project and build it

1. Review `my-fabric/hosts`, `group_vars/`, and `host_vars/` for the expected
   devices, management addresses, and configuration values.
2. Review `my-fabric/build/sites.yaml`, the generated role, and `project.yaml`.
   Check `build/runtime.yaml` for the NETCONF connection settings required by
   your environment. The profile contains lab credential defaults; supply
   appropriate credentials securely rather than committing them to the project.
   For Kubernetes Secret-based credentials, provision a Secret in the job's
   namespace with `ANSIBLE_NET_USERNAME` and `ANSIBLE_NET_PASSWORD` keys.
   Set `NITA_NETCONF_SECRET` to its name in the Jenkins shell environment and
   set `NITA_NAMESPACE` if the namespace is not `nita`. The generated job reads
   both values from the Secret. Jenkins credential environment variables alone
   are not automatically forwarded to the job.
   The build excludes `group_vars/env.yaml` and `env.yml` from the archive, but
   it does not remove secrets from other project files.
3. Check `my-fabric/manifest` and add any additional files or directories that
   your project needs in its archive.
4. Build the project:

   ```bash
   ./nitaprj.sh build my-fabric
   ```

The command produces `my-fabric/my-fabric.zip` and
`my-fabric/my-fabric.xlsx`. It packages the manifest entries and generates the
workbook from YAML files under `group_vars` and `host_vars`, excluding
`registry.yaml`. Existing output files are moved to `.bak` files.

### 5. Use the project in NITA

1. In the NITA web application, add the ZIP as a network type.
2. Add a network using that network type and the project's `hosts` file.
3. Import the generated XLSX workbook into the network configuration. Review
   the configuration and device connectivity before triggering a build.
4. Run the appropriate project action in NITA. Packaging with `nitaprj.sh build`
   does not itself deploy configuration to devices.

For the NITA interface workflow, see [NITA examples](../../docs/nita-examples.md).

## Generic profile

Use this profile when you want to prepare the inventory, playbooks, roles, and
variables yourself rather than generating a JTAF role.

### 1. Create a generic project

```bash
export NITA_ROOT="/path/to/nita"
cd "$NITA_ROOT/utils/nitaprj"
./nitaprj.sh create my-generic-project generic
```

The final `generic` argument is required to select this profile. Answer `y` or
`n` when prompted to initialize a Git repository.

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

```bash
./nitaprj.sh build my-generic-project
```

This creates `my-generic-project/my-generic-project.zip` and
`my-generic-project/my-generic-project.xlsx`. As with the JTAF profile, upload
the ZIP as a network type, create a network with the `hosts` file, import the
workbook, and review the configuration before running a project action.

## Commands from inside a project

Each created project contains a `nitaprj` symlink. From inside the project,
omit the project name when generating a role or building:

```bash
cd "$NITA_ROOT/utils/nitaprj/my-fabric"
./nitaprj generate-role -p <yang-paths-and-files> -x <xml-config-files> -t <device-type>
./nitaprj build
```

Replace the placeholders with actual arguments. Paths passed to `generate-role`
are resolved from the current directory. The `create` command is available only
outside a project; use `./nitaprj.sh version` to display the utility version.

## License

See individual files for license information. The default profile and scripts
are licensed under the Apache 2.0 License.
