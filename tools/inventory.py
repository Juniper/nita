#!/usr/bin/env python3
"""Validate and export NITA's declared direct dependencies without installing them."""

import argparse
import ast
import hashlib
import json
from pathlib import Path
import re
import shlex
import subprocess
import sys
import uuid


ROOT = Path(__file__).resolve().parents[1]
CATALOG = "compliance/components.json"
OUTPUTS = ("nita-source.cdx.json", "nita-components.md", "SHA256SUMS")
KINDS = {"package", "image", "repository", "resource", "python", "python-install", "tool"}
CATEGORIES = {"component", "host-prerequisite", "optional-tool", "library"}
LIMITATION = (
    "Pre-build inventory of declared direct dependencies. This is not an "
    "installed-system or container-package inventory, a complete transitive SBOM, "
    "a legal license determination, or a statement of CRA conformity. "
    "SOPD requirements have not been specified."
)


class InventoryError(ValueError):
    """Invalid catalog, source coverage, or release identity."""


def git(root, *args):
    return subprocess.check_output(
        ["git", "-C", str(root), *args], text=True, stderr=subprocess.PIPE
    ).strip()


def product_files(root):
    """Explicit product boundary; examples, demos, tests and CI tools are excluded."""
    paths = {root / "install.sh"}
    for directory in ("cli_scripts", "k8s", "utils"):
        for path in (root / directory).rglob("*"):
            if path.is_file() and (
                path.suffix in {".sh", ".py", ".yaml"}
                or (directory == "cli_scripts" and not path.suffix)
            ):
                paths.add(path)
    return sorted(paths)


def discover(root):
    """Return typed references with all declaration sites, never evaluating shell."""
    found = {}

    def add(kind, value, path, line):
        key = (kind, value)
        site = f"{path.relative_to(root).as_posix()}:{line}"
        found.setdefault(key, set()).add(site)

    files = {path: path.read_text(encoding="utf-8") for path in product_files(root)}
    # Resolve only repository-declared defaults, not the caller's environment.
    variables = {}
    for path, content in files.items():
        for match in re.finditer(r"^(\w+)=\$\{\1:=([^\n]+)\}$", content, re.M):
            name, value = match.groups()
            if name in {"CONTAINER_REGISTRY", "GITHUB_ORG"} or name.endswith("_IMAGE"):
                if name in variables and variables[name] != value:
                    raise InventoryError(f"Conflicting default for {name}: {path}")
                variables[name] = value

    def resolve(value):
        for _ in range(5):
            updated = re.sub(
                r"\$\{(\w+)\}", lambda m: variables.get(m[1], m[0]), value
            )
            if updated == value:
                break
            value = updated
        return value

    for path, content in files.items():
        for number, raw in enumerate(content.splitlines(), 1):
            line = raw.strip()
            if line.startswith("#"):
                continue
            if re.match(r"(?:sudo\s+)?(?:apt(?:-get)?|dnf|yum)\s+.*\binstall\b", line):
                raise InventoryError(f"Unsupported direct package command: {path}:{number}")
            match = re.match(r"(?:pip3?|python3?\s+-m\s+pip)\s+install\s+(.+)", line)
            if match:
                add("python-install", match[1], path, number)
            if "${INSTALLER}" in line:
                match = re.fullmatch(r'eval "\$\{INSTALLER\} ([^"]+)"', line)
                if not match:
                    raise InventoryError(f"Unsupported package declaration: {path}:{number}")
                for token in shlex.split(match[1]):
                    if token.startswith("--"):
                        continue
                    if not re.fullmatch(r"[a-zA-Z0-9.+_-]+", token):
                        raise InventoryError(f"Unresolved package: {path}:{number}: {token}")
                    add("package", token, path, number)
            match = re.match(r'NITA_REPOS="([^"]+)"', line)
            if match:
                for name in match[1].split():
                    if name != "nita":
                        add("repository", f"{variables['GITHUB_ORG']}/{name}", path, number)
            match = re.match(r"(\w+_IMAGE)=\$\{\1:=(.+)\}$", line)
            if match:
                value = resolve(match[2])
                if "$" in value:
                    raise InventoryError(f"Unresolved image default: {path}:{number}")
                add("image", value, path, number)
            if path.suffix == ".yaml":
                match = re.match(r"(?:-\s*)?image:\s*(\S+)", line)
                if match:
                    value = resolve(match[1].strip("'\""))
                    if "$" in value or "{" in value:
                        raise InventoryError(f"Unresolved image: {path}:{number}: {value}")
                    add("image", value, path, number)
            if path.suffix == ".py":
                for value in re.findall(r"""['"](ghcr\.io/[^'"]+)['"]""", line):
                    add("image", value, path, number)
            for tool in re.findall(r"`which ([\w.-]+)`", line):
                add("tool", tool, path, number)
            # Remote artifacts and their repository/key configuration are evidence;
            # generated local service URLs and informational comments are not.
            if re.search(
                r"wget|curl|git clone|kubectl apply|config-manager|baseurl=|gpgkey=|"
                r"echo ['\"]deb |https?://.*(?:\.zip|\.tar\.gz|\.yaml)",
                line,
            ):
                for url in re.findall(r"""https?://[^\s"'`<>\\]+""", line):
                    if "${REPO}" in url:  # represented individually by NITA_REPOS
                        continue
                    add("resource", resolve(url), path, number)
        if path.suffix == ".py":
            for node in ast.walk(ast.parse(content, filename=str(path))):
                names = []
                if isinstance(node, ast.Import):
                    names = [item.name.split(".")[0] for item in node.names]
                elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                    names = [node.module.split(".")[0]]
                for name in names:
                    if name not in sys.stdlib_module_names:
                        add("python", name, path, node.lineno)
    return {key: sorted(sites) for key, sites in sorted(found.items())}


def validate_catalog(catalog, discovered):
    if catalog.get("schema_version") != 1:
        raise InventoryError("Catalog schema_version must be 1")
    components = catalog.get("components")
    if not isinstance(components, list) or not components:
        raise InventoryError("Catalog requires a non-empty components array")
    ids, owned = set(), {}
    for item in components:
        cid = item.get("id", "")
        if not re.fullmatch(r"[a-z0-9][a-z0-9._-]*", cid) or cid in ids or cid == "nita":
            raise InventoryError(f"Invalid or duplicate component ID: {cid}")
        ids.add(cid)
        for field in ("name", "source", "reference", "conditions"):
            if not isinstance(item.get(field), str) or not item[field].strip():
                raise InventoryError(f"{cid}: missing {field}")
        if item.get("category") not in CATEGORIES or type(item.get("optional")) is not bool:
            raise InventoryError(f"{cid}: invalid category or optional flag")
        if item.get("version_status") not in {"exact", "mutable", "constraint", "unknown"}:
            raise InventoryError(f"{cid}: invalid version_status")
        version = item.get("version")
        if item["version_status"] == "exact":
            if not isinstance(version, str) or not version or version in {"latest", "stable", "main"}:
                raise InventoryError(f"{cid}: exact version required")
        elif version is not None:
            raise InventoryError(f"{cid}: unresolved versions must be null")
        if not item["source"].startswith("https://"):
            raise InventoryError(f"{cid}: source must be an HTTPS URL")
        licenses = item.get("license_sources")
        if not isinstance(licenses, list) or not licenses or any(
            not isinstance(url, str) or not url.startswith("https://") for url in licenses
        ):
            raise InventoryError(f"{cid}: HTTPS license source required")
        if item.get("license") is not None and (
            not isinstance(item["license"], str) or not item["license"].strip()
        ):
            raise InventoryError(f"{cid}: license must be an SPDX identifier or null")
        references = item.get("references")
        if not isinstance(references, list) or not references:
            raise InventoryError(f"{cid}: source references required")
        for ref in references:
            key = (ref.get("kind"), ref.get("value"))
            if key[0] not in KINDS or not isinstance(key[1], str):
                raise InventoryError(f"{cid}: invalid reference {ref}")
            if key in owned:
                raise InventoryError(f"Duplicate ownership of {key}: {owned[key]}, {cid}")
            owned[key] = cid
    missing, stale = discovered.keys() - owned.keys(), owned.keys() - discovered.keys()
    if missing or stale:
        details = [f"Missing {key} at {discovered[key]}" for key in sorted(missing)]
        details += [f"Stale {key} in {owned[key]}" for key in sorted(stale)]
        raise InventoryError("\n".join(details))
    return sorted(components, key=lambda item: item["id"])


def validate_bom(bom, schema_dir):
    from jsonschema import FormatChecker
    from jsonschema.validators import validator_for
    from referencing import Registry, Resource

    resources = []
    for path in sorted(schema_dir.glob("*.json")):
        schema = json.loads(path.read_text())
        resource = Resource.from_contents(schema)
        for prefix in ("http://cyclonedx.org/schema/", "https://cyclonedx.org/schema/"):
            resources.append((prefix + path.name, resource))
        if "$id" in schema:
            resources.append((schema["$id"], resource))
    registry = Registry().with_resources(resources)
    schema = json.loads((schema_dir / "bom-1.7.schema.json").read_text())
    validator_for(schema)(schema, registry=registry, format_checker=FormatChecker()).validate(bom)
    # CycloneDX JSON Schema cannot check graph referential integrity.
    refs = [bom["metadata"]["component"]["bom-ref"]]
    refs.extend(item["bom-ref"] for item in bom["components"])
    if len(refs) != len(set(refs)):
        raise InventoryError("Duplicate BOM references")
    for edge in bom["dependencies"]:
        if edge["ref"] not in refs or any(ref not in refs for ref in edge["dependsOn"]):
            raise InventoryError("Unknown dependency reference")


def properties(values):
    return [{"name": f"nita:{key}", "value": str(value)} for key, value in sorted(values.items())]


def build(root, release_tag=None):
    discovered = discover(root)
    catalog_path = root / CATALOG
    components = validate_catalog(json.loads(catalog_path.read_text()), discovered)
    commit = git(root, "rev-parse", "HEAD")
    timestamp = git(root, "show", "-s", "--format=%cI", "HEAD")
    if release_tag is not None:
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/-]*", release_tag):
            raise InventoryError("Invalid release tag")
        tag_commit = git(root, "rev-parse", "--verify", f"refs/tags/{release_tag}^{{commit}}")
        if tag_commit != commit:
            raise InventoryError("Release tag does not resolve to HEAD")
        if git(root, "status", "--porcelain", "--untracked-files=no"):
            raise InventoryError("Release generation requires clean tracked files")
    inputs = sorted(set(product_files(root)) | {
        catalog_path, root / "VERSION.txt", root / "LICENSE.txt",
        root / "tools/inventory.py",
    })
    fingerprint = hashlib.sha256()
    for path in inputs:
        fingerprint.update(path.relative_to(root).as_posix().encode() + b"\0")
        fingerprint.update(path.read_bytes() + b"\0")
    input_digest = fingerprint.hexdigest()
    root_ref = "nita"
    version = release_tag or f"{(root / 'VERSION.txt').read_text().strip()}+git.{commit[:12]}"
    root_properties = {
        "source-commit": commit,
        "input-sha256": input_digest,
        "coverage": "declared direct dependencies; transitive coverage incomplete",
    }
    if release_tag:
        root_properties["release-tag"] = release_tag
    bom = {
        "$schema": "http://cyclonedx.org/schema/bom-1.7.schema.json",
        "bomFormat": "CycloneDX",
        "specVersion": "1.7",
        "serialNumber": "urn:uuid:" + str(uuid.uuid5(
            uuid.NAMESPACE_URL, f"https://github.com/Juniper/nita/{commit}/{input_digest}/{release_tag or ''}"
        )),
        "version": 1,
        "metadata": {
            "timestamp": timestamp,
            "lifecycles": [{"phase": "pre-build"}],
            "component": {
                "bom-ref": root_ref, "type": "application", "name": "NITA",
                "version": version, "description": LIMITATION,
                "licenses": [{"license": {"id": "Apache-2.0"}}],
                "externalReferences": [{
                    "type": "vcs", "url": f"https://github.com/Juniper/nita/tree/{commit}"
                }],
                "properties": properties(root_properties),
            },
        },
        "components": [],
        "dependencies": [{"ref": root_ref, "dependsOn": [item["id"] for item in components]}],
        "compositions": [{"aggregate": "incomplete", "assemblies": [root_ref]}],
    }
    rows = [
        "# NITA source component inventory", "", LIMITATION, "",
        f"- Source commit: `{commit}`", f"- Version: `{version}`",
        f"- Source commit time: `{timestamp}`", f"- Input SHA-256: `{input_digest}`", "",
        "Mutable references and constraints below are declarations, not resolved installed versions.",
        "License links are review sources; `Unknown` means no verified license assertion is made.",
        "This inventory does not replace LICENSE.txt or NOTICES.txt.", "",
        "| Component | Category / optional | Version / reference | Conditions | License |",
        "| --- | --- | --- | --- | --- |",
    ]
    evidence_sections = []

    def md(value):
        return str(value).replace("|", r"\|").replace("\n", " ").replace("<", "&lt;").replace(">", "&gt;")

    for item in components:
        evidence = sorted({
            site for ref in item["references"] for site in discovered[(ref["kind"], ref["value"])]
        })
        component = {
            "bom-ref": item["id"],
            "type": "library" if item["category"] == "library" else "application",
            "name": item["name"],
            "scope": "optional" if item["optional"] else "required",
            "externalReferences": [{"type": "website", "url": item["source"]}]
                + [{"type": "license", "url": url} for url in item["license_sources"]],
            "properties": properties({
                "category": item["category"],
                "conditions": item["conditions"],
                "declared-reference": item["reference"],
                "version-status": item["version_status"],
                "license-status": "declared" if item["license"] else "unknown",
                "source-evidence": "; ".join(evidence),
            }),
        }
        if item["version"] is not None:
            component["version"] = item["version"]
        if item["license"]:
            component["licenses"] = [{"license": {"id": item["license"]}}]
        bom["components"].append(component)
        license_text = item["license"] or "Unknown"
        rows.append("| " + " | ".join(md(value) for value in (
            item["name"], item["category"] + (" / optional" if item["optional"] else ""),
            f"{item['version_status']}: {item['reference']}", item["conditions"], license_text,
        )) + " |")
        evidence_sections.extend([
            "", f"### {item['name']} (`{item['id']}`)", "",
            f"Source: {item['source']}", "",
            "License sources: " + ", ".join(item["license_sources"]), "",
            "Declared references:",
            *[f"- `{ref['kind']}: {ref['value']}`" for ref in item["references"]],
            "", "Evidence: " + ", ".join(f"`{site}`" for site in evidence),
        ])
    validate_bom(bom, root / "compliance/schemas")
    payloads = {
        OUTPUTS[0]: (json.dumps(bom, indent=2, ensure_ascii=False) + "\n").encode(),
        OUTPUTS[1]: ("\n".join(rows + ["", "## Sources and declaration evidence"] + evidence_sections) + "\n").encode(),
    }
    payloads[OUTPUTS[2]] = "".join(
        f"{hashlib.sha256(data).hexdigest()}  {name}\n" for name, data in payloads.items()
    ).encode()
    return payloads


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, default=Path("dist/inventory"))
    parser.add_argument("--release-tag", help="Require a clean checkout at this exact Git tag")
    parser.add_argument("--discover", action="store_true", help="Print discovered references for catalog maintenance")
    args = parser.parse_args()
    try:
        if args.discover:
            print(json.dumps([
                {"kind": kind, "value": value, "evidence": sites}
                for (kind, value), sites in discover(args.root.resolve()).items()
            ], indent=2))
            return
        payloads = build(args.root.resolve(), args.release_tag)
        args.output.mkdir(parents=True, exist_ok=True)
        for name, data in payloads.items():
            (args.output / name).write_bytes(data)
        print(f"Validated inventory written to {args.output}")
    except (InventoryError, OSError, subprocess.CalledProcessError) as exc:
        parser.exit(1, f"Inventory error: {exc}\n")


if __name__ == "__main__":
    main()
