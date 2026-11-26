# Spec Delta

## ADDED Requirements

### Requirement: Kind CI test dependencies
NITA Kind integration CI SHALL install every third-party Python package imported by the test modules it runs with pytest before running them.

#### Scenario: Inventory tests run in the Kind job
- **WHEN** the Kind job runs `tests/test_software_inventory.py`
- **THEN** the pinned inventory dependencies, including `jsonschema`, are installed and the module is collected without import errors

#### Scenario: A Kind pytest module adds an undeclared import
- **WHEN** a test module run by the Kind job imports a third-party package that none of the job's installed requirement files provide
- **THEN** the installer regression suite fails and names the module and import
