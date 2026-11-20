## 1. Project generator command

- [x] 1.1 Add `generate-role` to `nitaprj.sh` with validation for project existence and required JTAF tooling.
- [x] 1.2 Implement CLI parsing for `-p`, `-x`, `-t`, and optional `-v` arguments.
- [x] 1.3 Run the upstream JTAF generator and capture output into a project-local role directory.

## 2. Profile and project skeleton

- [x] 2.1 Add `profiles/jtaf-ansible/` with `project.yaml`, `ansible.cfg`, `hosts`, and `manifest`.
- [x] 2.2 Include a base `build/sites.yaml` skeleton and `group_vars` placeholders for the generated role.
- [x] 2.3 Ensure the generated project includes `filter_plugins` and `configs` directories.

## 3. Project lifecycle integration

- [x] 3.1 Copy the generated role into the project and refresh project-local files on rerun.
- [x] 3.2 Copy `jtaf_filters.py` into `filter_plugins/` and update the manifest.
- [x] 3.3 Append the generated role to the build playbook and keep the change idempotent.
- [x] 3.4 Include the trimmed schema and generated config output in the project artifact set.

## 4. Verification

- [x] 4.1 Validate `nitaprj.sh create ... jtaf-ansible` creates a project skeleton correctly.
- [x] 4.2 Run `nitaprj.sh generate-role <project>` against a sample YANG/XML input and confirm files are generated.
- [x] 4.3 Verify the generated project builds and packages without breaking the existing generic flow.
