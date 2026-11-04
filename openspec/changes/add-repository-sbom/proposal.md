## Why

Juniper/nita#81 requests a workflow producing component manifests for CRA preparation, one repository at a time. NITA's existing container attestations do not describe the integration repository's direct dependencies, installation conditions, or unresolved versions.

## What Changes

- Maintain a reviewed catalog of direct product dependencies and their source evidence.
- Generate an offline, deterministic CycloneDX 1.7 pre-build SBOM, readable component/license manifest, and checksums.
- Check catalog coverage against installation declarations and runtime assets.
- Validate and retain CI downloads for 90 days; attach validated evidence to new upstream releases without overwriting different existing files.
- Document limitations and catalog maintenance, including unknown versions and licenses.

## Capabilities

### New Capabilities

- `software-inventory`: Repository inventory coverage, deterministic evidence generation, validation, and controlled release publication.

### Modified Capabilities

None. Existing container attestations and security policies are unchanged.

## Impact

Adds a JSON catalog, Python tooling and tests, pinned validation dependencies/schemas, a GitHub Actions workflow, and English documentation. No application API or installation behavior changes. This pilot references #81 without closing the repository-family request and does not claim CRA compliance or implement an unspecified SOPD format.
