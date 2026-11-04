# Software inventory

NITA publishes a **pre-build inventory of declared direct dependencies** for this
repository. It covers the NITA component references, nginx/MariaDB, host package
requirements, Kubernetes/Calico, optional tools, and the generic project
builder's Python imports.

The inventory is a pilot for [issue #81](https://github.com/Juniper/nita/issues/81).
It is not an inventory of the packages installed on a particular machine or
inside a container. It does not include transitive dependencies, standalone
examples/demo environments, or development/test dependencies. It does not
establish CRA applicability or conformity. A required SOPD template has not been
specified; these outputs use an open format pending any such requirement.

## Download evidence

Open a successful **Software Inventory** run on the repository's **Actions**
page and download `nita-source-inventory-<run-id>-<attempt>`. Downloads require
GitHub sign-in and are retained for 90 days.

New published releases in `Juniper/nita` also receive these individual assets,
retained with the release:

| File | Purpose |
| --- | --- |
| `nita-source.cdx.json` | CycloneDX 1.7 pre-build SBOM, direct dependency relationships, source evidence, and incomplete-coverage declaration |
| `nita-components.md` | Readable component, condition, version, and license-source inventory |
| `SHA256SUMS` | SHA-256 checksums of both documents |

Release generation uses the exact tag commit. If uploading fails, rerun the
failed workflow. Identical existing assets are skipped; conflicting contents
fail before any missing assets are uploaded. No existing files are replaced,
no releases are created, and historical releases are not backfilled.
Maintainers must review a conflict instead of deleting evidence automatically.
GitHub platform or repository policy can limit artifact retention.

## Generate locally

Use Python 3.12 or later from the repository root:

```shell
python3 -m venv .venv-inventory
.venv-inventory/bin/python -m pip install -r requirements-inventory.txt
.venv-inventory/bin/python tools/inventory.py --output dist/inventory
```

Installing the pinned validation tools needs package-registry access. Generation
itself is offline: it does not install NITA, run product code, pull containers,
resolve registry tags, or fetch package/license metadata. Official CycloneDX
schemas are included in the repository with their license and provenance.

For release-equivalent validation, check out a clean commit with its tag available:

```shell
.venv-inventory/bin/python tools/inventory.py \
  --release-tag 26.10-1 --output dist/inventory
```

Replace the example tag with the tag at your checkout. Both lightweight and
annotated tags are supported. A missing/mismatched tag or dirty tracked checkout
fails; the example does not imply that historical releases contain this tooling.

The generator records HEAD, source commit time, and a hash of the catalog,
product input files, generator, version file, and root license. Local uncommitted
edits change that input hash; HEAD identifies the base commit in that case.
Identical inputs, HEAD, and release tag produce byte-identical files.
`--root PATH` selects a different checkout; `--output PATH` selects the destination.

## Maintain the catalog

`compliance/components.json` is the reviewed source of component metadata.
Inspect declarations before editing it:

```shell
.venv-inventory/bin/python tools/inventory.py --discover
```

Every discovered `(kind, value)` reference must belong to exactly one component.
Each component must own at least one live reference. The generator checks both
directions, reporting missing declarations and stale catalog entries with their
locations. Evidence locations in the output are derived from current source files.

Catalog fields:

| Field | Meaning |
| --- | --- |
| `id`, `name` | Stable unique identifier and readable component name |
| `category` | `component`, `host-prerequisite`, `optional-tool`, or `library` |
| `source` | Canonical HTTPS project/source URL |
| `version_status`, `version`, `reference` | `exact`, `mutable`, `constraint`, or `unknown`; only exact versions populate `version` |
| `conditions`, `optional` | Installation/use conditions and whether this is an optional feature |
| `license`, `license_sources` | Verified SPDX identifier or `null`, plus HTTPS sources for review |
| `references` | Owned declarations: `package`, `image`, `repository`, `resource`, `python`, `python-install`, or `tool` |

For example, `nginx:stable` is a mutable image reference, `v1.28` is a Kubernetes
package channel, and `openjdk-21-jre-headless` does not specify the installed
patch version. These are not exact component versions. An unknown license is
omitted from the SBOM's license assertions and marked unknown in its properties.
Project license assertions do not cover bundled third-party dependencies.
Existing `LICENSE.txt` and `NOTICES.txt` remain separate legal notices.

Discovery is deliberately specific to NITA's declaration styles. It reads
`install.sh`, product scripts under `cli_scripts`, shell/YAML/Python files under
`k8s` and `utils`, image defaults/literals, repository lists, external
artifact/configuration URLs, explicit `which` prerequisites, pip install
declarations, and non-standard-library Python imports. Package installs through
`${INSTALLER}` are parsed without shell evaluation; unsupported expressions,
direct apt/dnf/yum install commands, or unresolved YAML image variables fail
and require an extractor update.

This is not a general shell dependency analyzer. New ecosystems, indirect shell
construction, or a new product directory need an explicit extractor change and
a test. Maintainers must review conditions, source/license links, and component
grouping whenever installation logic changes: reference coverage cannot infer
those semantics. Literal package repository/key URLs are evidence for the
corresponding host component; they are not separate software products.

## Validate changes

```shell
.venv-inventory/bin/python -m unittest \
  tests.test_software_inventory tests.test_installer_regression -v
openspec validate add-repository-sbom --strict --no-interactive
actionlint .github/workflows/software-inventory.yaml
```

Tests cover declaration additions/removals, schema and graph integrity,
optionality, version/license uncertainty, deterministic output, exact release
identity, fork restrictions, and simulated asset upload/retry/conflict behavior.
No test creates a release or publishes files.

The workflow validates pushes, pull requests, manual dispatches, and published
releases. Validation uses read-only repository permissions. Only the separate
published-release job in `Juniper/nita` receives `contents: write`; PRs and forks
never publish. Actions are pinned to commits and publisher jobs for a release
are serialized.

## Relationship to container SBOMs and CRA

The existing Junos MCP BuildKit SBOM/provenance describes container builds.
This source inventory complements those attestations and leaves them unchanged.
Separate component-repository work is needed for container contents and
transitive dependencies, and an installed-system inventory is needed for actual
host package versions and user overrides.

CRA Annex I, Part II(1) addresses component documentation and machine-readable
SBOMs covering at least top-level dependencies for products in scope. This
pilot's unknown versions and incomplete runtime coverage must not be presented
as complete compliance evidence. The project's legal role, support obligations,
and any Juniper/HPE SOPD format remain separate decisions.

- [CRA legal text](https://eur-lex.europa.eu/eli/reg/2024/2847/oj)
- [European Commission: CRA and open source](https://digital-strategy.ec.europa.eu/en/policies/cra-open-source)
- [CycloneDX 1.7 specification](https://cyclonedx.org/docs/1.7/json/)
