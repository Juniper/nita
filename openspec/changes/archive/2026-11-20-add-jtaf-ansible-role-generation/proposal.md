## Why

The current NITA project workflow can package an Ansible role skeleton, but it does not provide a native path for turning JTAF device schemas and XML config into a project-scoped Ansible role that can be built and applied by the same project tooling. This proposal adds a first-class `generate-role` flow so a project can create, refresh, and ship a JTAF-generated role without manual copy-and-paste steps.

## What Changes

- **New** `nitaprj.sh generate-role` command to generate a JTAF Ansible role from schema and XML input.
- **New** `jtaf-ansible` project profile under the nitaprj profile library.
- **Modified** project creation/build flow to include the generated role, Jinja filters, and project manifest updates.
- **Updated** project actions to support a dedicated generation step before build operations.

## Capabilities

### New Capabilities
- `projects`: Generate a project-local JTAF role from a YANG schema and XML config template.
- `projects`: Support a `jtaf-ansible` profile with the required Ansible role and filter plugin layout.

### Modified Capabilities
- `projects`: Add a role-generation stage to the project lifecycle without breaking the existing build/zip workflow.
- `kubernetes`: Keep the build job and deployment flow aligned with the generated role layout used in the project manifest.

## Impact

- NITA project creation gains a JTAF-aware profile and a new `generate-role` action.
- Generated projects contain `roles/<type>_role`, `filter_plugins/jtaf_filters.py`, and `configs/` output directories ready for build execution.
- The change is additive and backward-compatible with existing non-JTAF profiles.
