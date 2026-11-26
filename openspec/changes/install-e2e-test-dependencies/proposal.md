# Proposal

## Why

Now that the Kind job builds the webapp from source and passes the install-time
auth check, it reaches the "Test migration prerequisites and rollback
snapshots" step for the first time. That step runs
`tests/test_software_inventory.py`, which imports `jsonschema`, but the job
installs only `requirements-integration-test.txt`. Collection fails with
`ModuleNotFoundError: No module named 'jsonschema'` and the remaining
integration steps are skipped (run 45687769804).

## What Changes

- Install the pinned `requirements-inventory.txt` alongside
  `requirements-integration-test.txt` in the Kind job's Python dependency step.
- Add a regression test that checks every third-party module imported by the
  test files that the Kind job runs with pytest is provided by the requirement
  files installed in that job.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `kubernetes`: Kind integration CI must install the dependencies of every
  test module it runs.

## Impact

`.github/workflows/nita-ci.yaml` and `tests/test_installer_regression.py`.
No product, manifest or installer behavior changes.
