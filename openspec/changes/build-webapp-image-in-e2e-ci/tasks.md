# Tasks

## 1. Source-built E2E image from latest main

- [x] 1.1 Default the Kind workflow webapp source to `<owner>/nita-webapp` at branch `main`, with independent repository-variable and manual-input overrides; validate the repository and ref format, check out and build that source, record the resolved commit SHA in the log and step summary, load the local image into Kind, and verify no registry-pull fallback or fixed default commit remains.
- [x] 1.2 Update README to describe the latest-`main` default, the resolved-SHA summary, the repository variables and manual overrides, and separate published-image release validation; verify all documented names match the workflow.
- [x] 1.3 Update installer regression tests for the `main` default, ref validation, and SHA recording.

## 2. Validation

- [x] 2.1 Run focused NITA installer/workflow tests and strict OpenSpec validation; verify the CI change and its spec delta are valid.
