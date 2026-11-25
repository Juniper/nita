# Design

## Context

The Kind job used the published webapp image (`latest`) unless a manual source
override was given, so ordinary CI never exercised current webapp source. The
forward-auth integration depends on current webapp behavior. See proposal.md
and the Kubernetes spec delta.

## Goals / Non-Goals

**Goals:**
- Every Kind integration run builds the webapp from the latest commit on the
  companion repository's `main` branch.
- Make the tested webapp commit visible in each run.
- Allow overriding the repository and ref for coordinated testing.
- Fail before cluster deployment if the selection is malformed.

**Non-Goals:**
- Publish the validation image.
- Replace release validation of the published webapp image.
- Change the webapp authentication contract or weaken the installer check.

## Decisions

- Resolve the source as: manual input → repository variable → default.
  Repository: `webapp_repository` → `NITA_WEBAPP_SOURCE_REPOSITORY` →
  `<workflow repository owner>/nita-webapp`. Ref: `webapp_ref` →
  `NITA_WEBAPP_SOURCE_REF` → `main`. The owner-derived repository keeps fork CI
  aligned with the matching companion fork; upstream uses `Juniper/nita-webapp`.
- Inputs are independent: a run can override only the repository (still
  building its `main`) or only the ref.
- Validate the repository as `owner/repo` and the ref as a safe git ref name
  (letters, digits, `.`, `_`, `/`, `-`, not starting with `-`) before checkout.
- After checkout, run `git rev-parse HEAD`, print the resolved SHA and append
  it to `$GITHUB_STEP_SUMMARY`.
- Always build the checked-out source and load that local tag into Kind. No
  registry fallback: if checkout or build fails, the job fails.

## Risks / Trade-offs

- NITA CI results can change when webapp `main` changes without a NITA commit
  → intended; the step summary records the tested webapp SHA for triage, and a
  manual run with `webapp_ref=<sha>` reproduces an earlier run.
- A breaking webapp change on `main` will fail NITA CI → this is the desired
  early signal of incompatibility.
- Building the webapp adds time to each Kind run → accepted.
