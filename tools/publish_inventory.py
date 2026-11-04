#!/usr/bin/env python3
"""Attach validated inventory to an existing upstream release without overwrites."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
from urllib.parse import quote

from inventory import InventoryError, OUTPUTS, validate_bom


REPOSITORY = "Juniper/nita"


def gh(*args):
    return subprocess.check_output(["gh", *args], stderr=subprocess.PIPE)


def api(path):
    return json.loads(gh("api", path))


def publish(directory, tag, commit, schema_dir):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/-]*", tag):
        raise InventoryError("Invalid release tag")
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise InventoryError("Expected full Git commit")
    if os.environ.get("GITHUB_REPOSITORY") != REPOSITORY:
        raise InventoryError("Release publication is restricted to Juniper/nita")
    if os.environ.get("GITHUB_EVENT_NAME") != "release":
        raise InventoryError("Release publication requires a release event")
    event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text())
    if event.get("action") != "published" or event["release"]["tag_name"] != tag:
        raise InventoryError("Expected the published release event for this tag")
    payloads = {name: (directory / name).read_bytes() for name in OUTPUTS}
    expected_sums = "".join(
        f"{hashlib.sha256(payloads[name]).hexdigest()}  {name}\n" for name in OUTPUTS[:2]
    ).encode()
    if payloads["SHA256SUMS"] != expected_sums:
        raise InventoryError("Inventory checksums do not match")
    bom = json.loads(payloads["nita-source.cdx.json"])
    validate_bom(bom, schema_dir)
    props = {p["name"]: p["value"] for p in bom["metadata"]["component"]["properties"]}
    if props.get("nita:source-commit") != commit or props.get("nita:release-tag") != tag:
        raise InventoryError("Evidence does not match the release commit and tag")
    prefix = f"repos/{REPOSITORY}"
    resolved = api(f"{prefix}/git/ref/tags/{quote(tag, safe='/')}")["object"]
    for _ in range(5):
        if resolved["type"] != "tag":
            break
        resolved = api(f"{prefix}/git/tags/{resolved['sha']}")["object"]
    if resolved["type"] != "commit":
        raise InventoryError("Release tag does not resolve to a commit")
    release = api(f"{prefix}/releases/{event['release']['id']}")
    if resolved["sha"] != commit or release["tag_name"] != tag or release["draft"]:
        raise InventoryError("Published release or tag changed")
    # Paginate: an older release can already contain more than 30 unrelated assets.
    pages = json.loads(gh(
        "api", "--paginate", "--slurp", f"{prefix}/releases/{release['id']}/assets?per_page=100"
    ))
    existing = {}
    for asset in (asset for page in pages for asset in page):
        if asset["name"] in OUTPUTS:
            if asset["name"] in existing:
                raise InventoryError(f"Duplicate release asset: {asset['name']}")
            existing[asset["name"]] = asset
    # Read and compare *every* existing asset before performing the first write.
    for name, asset in existing.items():
        actual = gh(
            "api", "-H", "Accept: application/octet-stream",
            f"{prefix}/releases/assets/{asset['id']}",
        )
        if actual != payloads[name]:
            raise InventoryError(f"Conflicting release asset: {name}; no files uploaded")
    with tempfile.TemporaryDirectory() as temporary:
        for name in OUTPUTS:
            if name in existing:
                print(f"Unchanged: {name}")
                continue
            # Publish to the immutable release ID, not a freshly resolved tag;
            # the API rejects existing names and is never called with --clobber.
            path = Path(temporary) / name
            path.write_bytes(payloads[name])
            result = json.loads(gh(
                "api", "--method", "POST",
                "-H", "Content-Type: application/octet-stream",
                f"https://uploads.github.com/{prefix}/releases/{release['id']}/assets?name={name}",
                "--input", str(path),
            ))
            if result.get("state") != "uploaded":
                raise InventoryError(f"Release asset not uploaded: {name}")
            print(f"Uploaded: {name}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--schemas", type=Path, default=Path("compliance/schemas"))
    args = parser.parse_args()
    try:
        publish(args.directory, args.tag, args.commit, args.schemas)
    except (InventoryError, OSError, KeyError, subprocess.CalledProcessError) as exc:
        parser.exit(1, f"Publication error: {exc}\n")


if __name__ == "__main__":
    main()
