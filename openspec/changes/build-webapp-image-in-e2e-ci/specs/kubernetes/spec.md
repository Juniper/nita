# Spec Delta

## MODIFIED Requirements

### Requirement: Architecture-parity integration validation
Upstream NITA CI SHALL deploy the same rendered manifests on x86 and, only when the `NITA_ARM_CI_ENABLED` repository variable is `true`, experimental ARM Kind hosts after canonical component images are multi-platform, verify Ansible and Robot smoke workloads, and run the existing stack integration checks.

#### Scenario: x86 fork CI uses public packages
- **WHEN** NITA CI runs in a personal fork
- **THEN** the x86 Kind deployment pulls canonical public Juniper images for the non-webapp components rather than deriving package names from the fork owner, and uses a source-built webapp image

#### Scenario: Upstream ARM stack validation
- **WHEN** CI runs in the Juniper NITA repository with multi-platform canonical packages available and `NITA_ARM_CI_ENABLED=true`
- **THEN** the ARM Kind job verifies rollout, database, HTTP, Jenkins RBAC, Ansible, Robot, and API integration behavior

#### Scenario: Canonical packages are not yet ARM-ready
- **WHEN** `NITA_ARM_CI_ENABLED` is absent or is not `true`
- **THEN** CI schedules only the x86 Kind job, even in the Juniper NITA repository

## ADDED Requirements

### Requirement: Kind CI builds the webapp from latest main
NITA Kind integration CI SHALL build the webapp image from the latest commit on the companion repository's `main` branch by default, SHALL record the resolved webapp commit SHA, and SHALL NOT pull the webapp image from a registry.

#### Scenario: Default CI builds latest webapp main
- **WHEN** NITA CI runs without webapp source overrides
- **THEN** it checks out the current tip of `main` in `<repository owner>/nita-webapp`, builds and loads that local webapp image into Kind, and reports the resolved webapp commit SHA in the job summary

#### Scenario: Override webapp source
- **WHEN** repository variables or a manual NITA CI run supply a valid webapp repository and/or ref (branch, tag or commit SHA)
- **THEN** the workflow builds and tests that source locally, using defaults for any value not supplied

#### Scenario: Invalid webapp source selection
- **WHEN** the selected webapp repository is not `owner/repo` or the ref is not a safe git ref name
- **THEN** the workflow fails before deploying the stack and reports the required format
