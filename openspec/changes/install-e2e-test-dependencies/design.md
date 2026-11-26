# Design

## Context

`tests/test_software_inventory.py` was added to the Kind job's
migration-prerequisite pytest step, but its `jsonschema` dependency lives in
`requirements-inventory.txt`, which only the Software Inventory workflow
installed. Earlier Kind runs never reached this step because they failed at
the webapp forward-auth check.

## Goals / Non-Goals

**Goals:**
- Make the Kind job's pytest steps importable with the dependencies it installs.
- Catch future mismatches in the fast regression suite rather than in Kind.

**Non-Goals:**
- Change which tests run in the Kind job.
- Change the Software Inventory workflow or the pinned inventory versions.

## Decisions

- Install `requirements-inventory.txt` in the existing "Install integration-test
  dependencies" step instead of copying `jsonschema` into
  `requirements-integration-test.txt`, so the inventory pins stay in one file.
  Both files resolve together (`PyYAML==6.0.3` satisfies `PyYAML>=6.0.0`).
- Keep `test_software_inventory.py` in the Kind job; dropping it would hide the
  failure rather than fix it.
- The regression test parses the Kind job: it reads `-r` files from the install
  step, collects test files named in `pytest` steps and the `testpaths` of any
  `pytest -c <file>.ini`, then checks every top-level import that is neither
  standard library nor repository-local against the installed requirement
  names. `yaml` maps to `PyYAML`; `urllib3` is accepted as a dependency of
  `requests`.

## Risks / Trade-offs

- The import check needs `sys.stdlib_module_names` (Python 3.10+) → it skips on
  older interpreters; CI uses Python 3.12.
- New indirect imports without an explicit mapping will fail the test → add the
  requirement or the mapping deliberately.
