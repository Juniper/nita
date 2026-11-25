# Proposal

## Why

The NITA Kind end-to-end test pulled a mutable published webapp image, so it
could test a stale or incompatible release instead of the current companion
source. Pinning a fixed commit has the same problem in reverse: CI keeps
testing old webapp code after `main` moves on. Build the webapp image from the
latest commit on the companion repository's `main` branch on every run, and
record the exact commit that was tested.

## What Changes

- Make the Kind end-to-end workflow check out, build and load the webapp image
  from the tip of the companion repository's `main` branch by default.
- Record the resolved webapp commit SHA in the job log and step summary so
  every run is traceable.
- Allow repository variables and manual workflow inputs to select another
  companion repository or branch/tag/commit, and fail clearly for malformed
  values.
- Remove the registry-pull fallback for the webapp image in the E2E job.
- Document the default and overrides, and distinguish this source-build
  integration check from published-image release validation.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `kubernetes`: Define the source contract for the webapp image used by NITA's
  Kind integration CI.

## Impact

The NITA CI workflow, Kubernetes integration validation specification, README
and installer regression tests are affected. The workflow checks out the public
companion source and builds it locally; it does not publish an image.
