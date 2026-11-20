## Context

The JTAF tooling already knows how to convert YANG definitions into generated Ansible role assets via `jtaf-yang2ansible` and `jtaf-ansible`. Those generated assets include a role with a hierarchical var merge model, a Jinja XML template, and required filter plugins. The missing piece is a reproducible project lifecycle: the role should be generated into a project, the project manifest should include it, and the build job should apply it without manual editing.

This proposal extends the nitaprj project model so a project can be created from a JTAF profile and then enriched with a generated role before the normal build packaging step.

## Goals / Non-Goals

**Goals:**
- Add a `generate-role` workflow to the NITA project builder.
- Generate a project-local Ansible role from YANG/XML inputs in a repeatable, idempotent way.
- Keep the generated role compatible with the existing `jtaf_effective` merge model and Jinja template rendering flow.
- Ensure the generated role is reflected in the project manifest and action metadata.

**Non-Goals:**
- Replacing the existing generic project template flow.
- Modifying the logic of the existing `build` step beyond including generated role assets.
- Adding device-specific vendor behavior outside the generated JTAF role contract.

## Decisions

### Decision 1: Treat JTAF as a project profile, not a separate build system

**Choice:** Add a `jtaf-ansible` profile alongside the existing generic nitaprj profiles and invoke generation from the project directory.

**Rationale:** This keeps profile creation and role generation aligned with the existing project packaging model and avoids creating a separate build pipeline for JTAF-specific projects.

**Alternatives considered:**
- Generate the role outside the project and later copy files manually: brittle and hard to repeat.
- Add custom logic directly to each project: not reusable across NITA deployments.

### Decision 2: Follow an idempotent `generate-role` contract

**Choice:** `nitaprj.sh generate-role <project>` overwrites the role files for the same device type and updates generated project metadata when rerun.

**Rationale:** Project schemas and XML inputs can change during validation; rerunning generation should refresh the role without manual cleanup.

**Alternatives considered:**
- Failing if the generated role already exists: makes iteration slower and more error-prone.
- Creating a new directory on every run: leaves stale files behind.

### Decision 3: Keep the generated role layout consistent with the upstream JTAF output

**Choice:** The generated project directory mirrors the upstream structure:
- `roles/<type>_role/tasks/main.yml`
- `templates/template.j2`
- `filter_plugins/jtaf_filters.py`
- `group_vars/` and `host_vars/`
- `configs/`
- `jtaf-playbook.yml`
- `trimmed_schema.json`

**Rationale:** This preserves compatibility with the current JTAF runtime contract and simplifies debugging when generated output is inspected or compared against upstream artifacts.

### Decision 4: Merge generation into the existing project manifest and action flow

**Choice:** The `generate-role` command updates the project manifest to include `roles/<type>_role`, `filter_plugins`, and the generated configuration output, and appends the role entry to the project playbook skeleton.

**Rationale:** Without this, the generated role would exist on disk but not be included in the packaged project or the build job execution path.

**Alternatives considered:**
- Leave the project manifest unchanged: the generated role is dropped from archive packaging.
- Manually maintain role references in each project: not scalable or repeatable.

## Risks / Trade-offs

- **Schema drift**: rerunning generation can overwrite project-local customizations if the same role name is regenerated without review.
- **Role lifecycle complexity**: the generated project needs a clear ownership boundary between generated files and hand-authored device configuration.
- **Operational dependency**: generation requires JTAF tooling to be installed and on `PATH`.

## Migration Plan

1. Add the new `generate-role` command to `nitaprj.sh` and validate invocation with a sample project.
2. Add the `jtaf-ansible` profile that includes the expected project skeleton and action metadata.
3. Generate a sample JTAF role into a sandbox project and confirm the role, manifest, and playbook updates are correct.
4. Package the project and verify the build path still works for the generic non-JTAF flow.
