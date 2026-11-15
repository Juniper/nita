# NITA Project Utility (`nitaprj.sh`)

This utility script helps you create, build, and manage NITA-based network automation projects using predefined profiles.

## Features

- **Project Creation:**  
  Create a new project directory from a profile template (default: `generic`).

- **Project Build:**  
  Package your project files into a zip archive and generate an Excel summary of variables, with sensitive environment variables scrubbed.

- **Version Display:**  
  Show the script version.

## Usage

You can run the script in two ways, depending on your current directory:

### 1. From Outside the Project Directory

Call the script as `nitaprj.sh` and specify the project name as an argument:

```sh
./nitaprj.sh build <projectname>
```

### 2. From Inside the Project Directory

Call the script as `nitaprj` (the script creates a symlink with this name in each project). The script automatically detects it is running inside a project by the name it is called:

```sh
./nitaprj build
```

### Commands

- `create <projectname> [profilename]`  
  Create a new project directory using the specified profile (default: `generic`).  
  **Note:** The `create` command can only be run from outside the project directory.

- `build <projectname>`  
  Build the specified project (creates a zip archive and an xlsx file).

- `version`  
  Display the script version.

### Example

```sh
# Create a new project called myproject (from outside any project directory)
./nitaprj.sh create myproject

# Build the project from outside the project directory
./nitaprj.sh build myproject

# Or, build the project from inside the project directory
cd myproject
./nitaprj build
```

## Notes

### JTAF Ansible builds

The `jtaf-ansible` profile renders generated roles before deploying their XML with
`juniper.device.config` using `load: merge`. It does not use the legacy
`junos_commit_config` role, which assembles text `.cfg` fragments.

Before deployment, the profile inspects the generated IPv4 configuration for the
management unit (`management_interface.int`, default `em0.0`; bare names such as
the enrichment helper's `em0` refer to unit `0`). If that unit has
an active static address, it retrieves its committed DHCP configuration without
loading or committing changes. Existing active DHCP is marked for deletion in a
separate, private copy of the generated XML. The DHCP deletion and static address
are then loaded and committed together; there is no separate DHCP-removal commit.
Other interfaces, DHCP-only management units, and IPv6 configuration are unchanged.
If DHCP is already absent, no deletion is emitted. Invalid XML, ambiguous management
entries, conflicting generated DHCP/static settings, and retrieval errors stop
deployment. Inherited DHCP or unrelated pending candidate changes require separate
review; this workflow does not alter configuration groups or discard candidates.

Existing projects must copy both `build/commit.yaml` and
`filter_plugins/nita_management.py` from `profiles/jtaf-ansible` before using this
behavior. Updating the profile alone does not update an uploaded project archive.
The filter is automatically packaged through the existing `filter_plugins`
manifest entry. Management changes can affect connectivity; validate the intended
static address and access path before deployment.

Runtime paths live in `build/runtime.yaml`, outside workbook-managed
`group_vars` and `host_vars`. Generated roles load this file and write separate
XML files for each device under `/var/tmp/build/<host>/xml`. Do not put runtime
defaults only in `group_vars/all.yaml`: workbook generation replaces that file.

New `jtaf-ansible` projects include `enrich_variables.py` in their archives.
After each workbook update, `run_build.sh` uses it to restore
`management_interface` from the IPv4 address on `em0.0` before creating the
Ansible Job. Missing or ambiguous addresses stop the launcher. Hostname
preparation uses this address when `ansible_host` is the inventory name, while
preserving explicit `ansible_host` overrides.

Enrichment also restores presence flags that workbook conversion turned into
text. YANG `empty` leaves become boolean `true`; `false` omits the statement.
Ordinary string fields are unchanged. `generate-role` records empty leaf
elements observed in the input XML in `configs/empty_leaf_paths.json`, including
presence flags modeled as strings by the schema. The hint file is included in
the project archive with `configs`.

For an existing project, copy the updated enrichment helper and record these
hints using the original XML inputs before the next build:

```sh
python3 enrich_variables.py . --record-empty-leaves /path/to/device1.xml /path/to/device2.xml
```

For existing projects, copy `enrich_variables.py` from this utility directory,
add it to the project manifest, and update `run_build.sh` and
`make_etc_hosts.yaml` from the profile. A non-default management interface can
be specified in `variable_metadata.yaml` as supported by the enrichment helper.

The device username (from `ANSIBLE_NET_USERNAME`, falling back to `jcluser`) and
NETCONF port (`830`) also live in
`build/runtime.yaml` so workbook updates cannot remove them. Edit that file for
your environment; these play-level values override inventory values, while
Ansible extra variables can override them per invocation.
Supply password authentication through `netconf_passwd` or the Juniper module's
`ANSIBLE_NET_PASSWORD` environment variable, or configure SSH key authentication.
Optional
`group_vars/env.yaml` supplies the job's environment; do not package credentials
in the project archive.

For Secret-based authentication, provision a Kubernetes Secret containing keys
`ANSIBLE_NET_USERNAME` and `ANSIBLE_NET_PASSWORD` in the job's namespace. Then
configure the Jenkins shell environment (or your interactive shell):

```sh
export NITA_NETCONF_SECRET=my-fabric-netconf-credentials
export NITA_NAMESPACE=nita
bash ./run_build.sh
```

`NITA_NAMESPACE` defaults to `nita` and is used by both the generated Job and
every launcher Kubernetes operation. `NITA_NETCONF_SECRET` is optional: when set,
both credential variables use required `secretKeyRef` entries, replacing any
same-named plaintext entries from `group_vars/env.yaml`. Unrelated environment
variables remain unchanged. A missing Secret or key prevents the pod from
starting; there is no plaintext fallback. When unset, existing environment-file
and SSH-key workflows remain supported. Jenkins environment credentials are
not automatically forwarded to the job. Provision Secret values outside the
repository; never commit them.

Jenkins runs `bash ./run_build.sh`, which checks Kubernetes Job completion after
streaming logs. Rendering or deployment failures now fail the build. A previous
`build` Job must have been removed (normally by its 120-second TTL) before a new
build can start; an existing Job causes an explicit error instead of reusing its
result.

Both shell entry points resolve paths relative to their own project directory.
Before rendering, `build.sh` syntax-checks the deployment playbook to catch
missing collections without deploying. Deployment uses `ansible_host`, then
`management_interface.ip`, then the inventory hostname, stripping any CIDR suffix.

The rendering playbook first imports `make_etc_hosts.yaml` to populate device
hostname resolution inside the Ansible container. Each device requires
`ansible_host` or `management_interface.ip`. The task uses Ansible's built-in
`lineinfile` module rather than the generic profile's shell/sudo helper, serializes
updates, and permits in-place writes for container-mounted `/etc/hosts`.
The container user must have write access to that file.

To validate rendering without contacting devices (but updating the container's
`/etc/hosts`), run inside the Ansible image:

```sh
ansible-playbook -i hosts build/sites.yaml
```

`bash build.sh [output-directory]` renders and then deploys configuration.

- The script will prompt to install `yaml2xls.py` if not found, which is required for generating the Excel file.
- Sensitive environment variables in `group_vars/env.yaml` are scrubbed before packaging.
- The script expects a `manifest` file in the project directory to determine which files to include in the archive.
- The script distinguishes between being run from inside or outside a project directory by checking the name it is called with (`nitaprj.sh` vs `nitaprj`).

## Directory Structure

- `profiles/` - Contains project templates (profiles).
- `group_vars/` and `host_vars/` - Ansible variable files.
- `manifest` - List of files/directories to include in the build archive.

## License

See individual files for license information.  
Default profile and scripts are licensed under the Apache 2.0 License.

---