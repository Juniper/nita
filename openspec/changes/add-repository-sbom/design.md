## Context

NITA integrates separately released components and host prerequisites. Its installer uses mutable image tags, distribution packages, optional downloads, and Python tooling; a package-manager source scan alone would omit much of this inventory. Upstream main already generates Junos MCP container attestations. Issue #81 does not define SOPD or establish legal applicability.

## Goals / Non-Goals

**Goals:** A reviewed catalog with executable drift checks, deterministic offline evidence, schema validation, and safe CI/release delivery.

**Non-Goals:** Installed-system or transitive/container-package inventory, license adjudication, vulnerability remediation, deployment changes, automated legal compliance, other repository implementations, or historical release backfills.

## Decisions

- Use `compliance/components.json` with stable component IDs, category, source, nullable exact version, reference/constraint, conditions, optionality, license sources, and typed source references. A stdlib Python discovery pass inventories package arguments, image defaults/literals, repository declarations, external download/configuration URLs, explicit tool requirements, pip install declarations, and non-stdlib imports in product code. Compare discovered references with catalog ownership in both directions; fail on missing/stale/duplicate ownership. Do not execute installation scripts or query registries. Curated metadata remains subject to maintainer review when installation conditions change.
- Generate CycloneDX 1.7 JSON, Markdown, and SHA-256 sums from one model. Use `pre-build`, an incomplete composition, and explicit properties for category, conditions, mutable references, and unknown values. Direct edges connect the NITA root to catalog components; do not assert that those components have no transitive dependencies. Only verified exact versions enter `version`. Only supported SPDX identifier assertions enter license fields; source links alone are not license assertions.
- Identify source by full Git commit, with optional verified tag. Use commit time and deterministic UUIDs; include a hash of catalog/source evidence so uncommitted input changes are distinguishable. Release mode rejects dirty tracked input and verifies the tag resolves to HEAD. Vendor official schemas and their license at the CycloneDX 1.7 tag commit, validate offline using pinned Python dependencies, and make no application dependency changes.
- Run generation/tests with read-only permissions on pushes, pull requests, dispatch, and published releases. Store artifacts for 90 days. A separate upstream-release-only job downloads validated artifacts from the same run and receives `contents: write`. It executes the publisher from the same verified release checkout, with checkout credentials disabled. Pin third-party actions to commit SHAs; never use `pull_request_target`.
- Publish only the three fixed asset names to the existing published release. Verify release tag commit matches generation evidence. Compare all existing asset bytes before any upload: identical files are skipped and conflicts fail without overwrites. Serialize publication for a release; retrying an interrupted upload adds only missing files. No new releases or package publication.
- Keep the existing NOTICES.txt as historical input; explain that this manifest does not replace legal notices. Use an English maintenance guide and examples produced by the PR workflow instead of committing generated snapshots.

## Risks / Trade-offs

- Static discovery is intentionally limited to this repository's declaration styles → fail on unsupported package expressions and unresolved image variables; test additions/removals and document extractor updates for new ecosystems or shell constructs.
- Package/tag versions remain unresolved → represent uncertainty explicitly and describe the output as pre-build inventory, not an installed product SBOM.
- License sources can describe upstream projects rather than distribution packaging → leave unverified licenses unknown and retain links for review.
- A published release can precede its evidence upload → failed upload is a visible workflow failure and can be rerun without replacing assets.

## Migration Plan

Merge the additive workflow and catalog after reviewing the PR artifacts. Future releases receive attachments automatically; existing releases are unchanged. Disable the new workflow to stop publication while retaining already produced evidence. No application migration is required.

## Open Questions

SOPD requirements and CRA applicability remain external follow-up topics; neither blocks the agreed open-format pilot.
