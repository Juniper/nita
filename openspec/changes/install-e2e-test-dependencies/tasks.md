# Tasks

## 1. Kind job test dependencies

- [x] 1.1 Install `requirements-inventory.txt` with `requirements-integration-test.txt` in the Kind job; verify the "Test migration prerequisites and rollback snapshots" pytest command passes under Python 3.12 with exactly those requirement files.
- [x] 1.2 Add a regression test that fails when a Kind job pytest module imports a third-party package not provided by the job's installed requirement files; verify it fails without task 1.1 and passes with it.

## 2. Validation

- [x] 2.1 Run the focused regression suite, collect the later Kind pytest steps in the CI-equivalent environment, and run strict OpenSpec validation.
