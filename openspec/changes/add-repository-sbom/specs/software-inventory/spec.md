## ADDED Requirements

### Requirement: Reviewed direct dependency inventory
The repository SHALL maintain one catalog of direct product components, host prerequisites, and optional tools, with source references, installation conditions, version status, and license sources. CI SHALL fail on missing, stale, or multiply owned discovered references, duplicate component IDs, and invalid dependency references.

#### Scenario: Installer adds a dependency
- **WHEN** an installer package, container image, repository, external resource, explicit prerequisite, or product Python import changes without matching catalog coverage
- **THEN** inventory validation fails with the affected reference and source location

#### Scenario: Optional and distribution-specific components
- **WHEN** evidence is generated for the repository
- **THEN** optional tools and distribution conditions remain visible and are not represented as installed on every system

### Requirement: Honest deterministic evidence
The generator SHALL produce a schema-valid CycloneDX 1.7 pre-build SBOM, a readable component/license manifest, and SHA-256 checksums from local files and Git metadata. Output SHALL identify the full source commit, input digest, and any verified release tag, distinguish unknown values from exact versions, and disclose incomplete transitive coverage.

#### Scenario: Repeated generation
- **WHEN** the same source files, commit, and optional release tag are processed twice
- **THEN** all three output files are byte-identical

#### Scenario: Mutable or unknown metadata
- **WHEN** a dependency uses a mutable tag, version constraint, or unverified license
- **THEN** the evidence retains that reference or uncertainty without inventing an installed version or license assertion

#### Scenario: Release identity is invalid
- **WHEN** a release tag does not resolve to the checked-out commit or tracked source inputs are dirty
- **THEN** release generation fails before publishing evidence

### Requirement: Validated CI downloads
The workflow SHALL validate inventory, official schemas, and tests before exposing successful evidence artifacts for pushes, pull requests, manual dispatches, and published releases. CI artifacts SHALL request 90-day retention. Pull requests and forks SHALL NOT receive release-writing permissions or publish release assets.

#### Scenario: Fork pull request
- **WHEN** a fork pull request runs the inventory workflow
- **THEN** it validates and uploads review artifacts without a write token or registry login

### Requirement: Non-destructive upstream release evidence
Only the published-release job in Juniper/nita SHALL upload the three fixed evidence files to its existing release, using the exact release commit. The publisher SHALL preflight existing files and fail on different content without overwriting any asset, skip identical files, and upload missing files only.

#### Scenario: First publication
- **WHEN** a new upstream release passes inventory checks
- **THEN** its SBOM, manifest, and checksums become downloadable release assets

#### Scenario: Interrupted publication is retried
- **WHEN** some identical assets already exist
- **THEN** only missing assets are uploaded

#### Scenario: Existing evidence differs
- **WHEN** any existing evidence asset has different bytes
- **THEN** publication fails without overwriting assets or uploading other missing files

### Requirement: Documented boundaries
The documentation SHALL explain local generation, catalog maintenance, CI/release downloads, and the distinction between repository inventory, container attestations, installed-system inventory, and CRA conformity. It SHALL state that SOPD format requirements remain unspecified.

#### Scenario: Maintainer reviews the pilot
- **WHEN** a maintainer reads the guide and generated manifest
- **THEN** coverage, unresolved values, and excluded transitive/container contents are clearly identified
