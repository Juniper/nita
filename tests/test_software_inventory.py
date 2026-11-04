"""Behavioral tests for declared inventory and non-destructive release evidence."""

import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

import yaml
from jsonschema.exceptions import ValidationError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import inventory
import publish_inventory


class InventoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.discovered = inventory.discover(ROOT)
        cls.catalog = json.loads((ROOT / inventory.CATALOG).read_text())
        cls.payloads = inventory.build(ROOT)

    def test_valid_schema_and_direct_graph(self):
        bom = json.loads(self.payloads[inventory.OUTPUTS[0]])
        inventory.validate_bom(bom, ROOT / "compliance/schemas")
        self.assertEqual(bom["metadata"]["lifecycles"], [{"phase": "pre-build"}])
        self.assertEqual(bom["compositions"][0]["aggregate"], "incomplete")
        self.assertEqual(
            set(bom["dependencies"][0]["dependsOn"]),
            {item["bom-ref"] for item in bom["components"]},
        )

    def test_determinism_and_checksums(self):
        self.assertEqual(self.payloads, inventory.build(ROOT))
        for line in self.payloads["SHA256SUMS"].decode().splitlines():
            digest, name = line.split("  ")
            self.assertEqual(digest, hashlib.sha256(self.payloads[name]).hexdigest())

    def test_source_identity_and_uncertainty(self):
        bom = json.loads(self.payloads[inventory.OUTPUTS[0]])
        props = {p["name"]: p["value"] for p in bom["metadata"]["component"]["properties"]}
        self.assertEqual(props["nita:source-commit"], inventory.git(ROOT, "rev-parse", "HEAD"))
        components = {item["bom-ref"]: item for item in bom["components"]}
        self.assertNotIn("version", components["nginx"])
        self.assertNotIn("licenses", components["docker-ce"])
        self.assertEqual(components["junos-mcp-server"]["scope"], "optional")
        self.assertEqual(components["openjdk-archive"]["version"], "19.0.1")
        self.assertIn("Ubuntu", json.dumps(components["openjdk-21-jre-headless"]))
        self.assertIn("AlmaLinux", json.dumps(components["openjdk-archive"]))

    def test_missing_and_stale_reference(self):
        modified = copy.deepcopy(self.discovered)
        modified[("package", "new-runtime")] = ["install.sh:1"]
        with self.assertRaisesRegex(inventory.InventoryError, "Missing.*new-runtime"):
            inventory.validate_catalog(self.catalog, modified)
        del modified[("package", "new-runtime")]
        del modified[("package", "curl")]
        with self.assertRaisesRegex(inventory.InventoryError, "Stale.*curl"):
            inventory.validate_catalog(self.catalog, modified)

    def test_duplicate_ids_and_ownership(self):
        catalog = copy.deepcopy(self.catalog)
        catalog["components"].append(catalog["components"][0])
        with self.assertRaisesRegex(inventory.InventoryError, "duplicate component ID"):
            inventory.validate_catalog(catalog, self.discovered)
        catalog = copy.deepcopy(self.catalog)
        catalog["components"][1]["references"].append(catalog["components"][0]["references"][0])
        with self.assertRaisesRegex(inventory.InventoryError, "Duplicate ownership"):
            inventory.validate_catalog(catalog, self.discovered)

    def test_invalid_metadata(self):
        for update in [
            {"optional": "false"}, {"license_sources": []},
            {"category": "invented"}, {"version_status": "mutable", "version": "latest"},
            {"version_status": "exact", "version": None},
        ]:
            with self.subTest(update=update):
                catalog = copy.deepcopy(self.catalog)
                catalog["components"][0].update(update)
                with self.assertRaises(inventory.InventoryError):
                    inventory.validate_catalog(catalog, self.discovered)

    def test_invalid_schema_license_and_dependency(self):
        bom = json.loads(self.payloads[inventory.OUTPUTS[0]])
        bom["components"][0]["licenses"] = [{"license": {"id": "Invented-License"}}]
        with self.assertRaises(ValidationError):
            inventory.validate_bom(bom, ROOT / "compliance/schemas")
        bom = json.loads(self.payloads[inventory.OUTPUTS[0]])
        bom["dependencies"][0]["dependsOn"].append("absent")
        with self.assertRaisesRegex(inventory.InventoryError, "Unknown dependency"):
            inventory.validate_bom(bom, ROOT / "compliance/schemas")

    def product_copy(self, target):
        for path in inventory.product_files(ROOT):
            destination = target / path.relative_to(ROOT)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, destination)

    def test_real_source_additions_are_detected(self):
        mutations = [
            ("install.sh", 'eval "${INSTALLER} new-package"\n', "new-package"),
            ("install.sh", 'wget https://example.org/new-tool.tar.gz\n', "new-tool"),
            ("k8s/new-deployment.yaml", "image: redis:7\n", "redis"),
            ("utils/new_tool.py", "import new_library\n", "new_library"),
            ("install.sh", 'NITA_REPOS="nita nita-new"\n', "nita-new"),
            ("utils/new.sh", 'pip3 install new-package\n', "new-package"),
        ]
        for filename, text, expected in mutations:
            with self.subTest(filename=filename), tempfile.TemporaryDirectory() as directory:
                target = Path(directory)
                self.product_copy(target)
                path = target / filename
                path.parent.mkdir(parents=True, exist_ok=True)
                with path.open("a") as stream:
                    stream.write("\n" + text)
                with self.assertRaisesRegex(inventory.InventoryError, expected):
                    inventory.validate_catalog(self.catalog, inventory.discover(target))

    def test_source_removal_and_unsupported_expressions(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            self.product_copy(target)
            path = target / "install.sh"
            path.write_text(path.read_text().replace('eval "${INSTALLER} jq"', 'echo skipped'))
            with self.assertRaisesRegex(inventory.InventoryError, "Stale.*jq"):
                inventory.validate_catalog(self.catalog, inventory.discover(target))
            with path.open("a") as stream:
                stream.write('\neval "${INSTALLER} ${NEW_PACKAGES}"\n')
            with self.assertRaisesRegex(inventory.InventoryError, "Unresolved package"):
                inventory.discover(target)

    def test_unresolved_image_is_not_silently_ignored(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            self.product_copy(target)
            (target / "k8s/new.yaml").write_text("image: ${UNDEFINED_IMAGE}\n")
            with self.assertRaisesRegex(inventory.InventoryError, "Unresolved image"):
                inventory.discover(target)

    def test_direct_package_commands_require_extractor_review(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            self.product_copy(target)
            with (target / "install.sh").open("a") as stream:
                stream.write("\nsudo apt-get install new-package\n")
            with self.assertRaisesRegex(inventory.InventoryError, "Unsupported direct package"):
                inventory.discover(target)

    def test_release_tag_commit_and_clean_input(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            self.product_copy(target)
            for relative in ("compliance", "tools"):
                shutil.copytree(ROOT / relative, target / relative)
            for name in ("VERSION.txt", "LICENSE.txt"):
                shutil.copyfile(ROOT / name, target / name)
            def git(*args):
                return inventory.git(target, *args)
            git("init", "-q")
            git("config", "user.email", "test@example.org")
            git("config", "user.name", "Inventory test")
            git("add", ".")
            git("-c", "commit.gpgsign=false", "commit", "-qm", "Fixture")
            git("tag", "test-release")
            payloads = inventory.build(target, "test-release")
            self.assertEqual(payloads, inventory.build(target, "test-release"))
            bom = json.loads(payloads[inventory.OUTPUTS[0]])
            self.assertEqual(bom["metadata"]["component"]["version"], "test-release")
            with (target / "VERSION.txt").open("a") as stream:
                stream.write("\n")
            with self.assertRaisesRegex(inventory.InventoryError, "clean tracked"):
                inventory.build(target, "test-release")
            git("add", ".")
            git("-c", "commit.gpgsign=false", "commit", "-qm", "New commit")
            with self.assertRaisesRegex(inventory.InventoryError, "does not resolve"):
                inventory.build(target, "test-release")


class PublisherTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.commit = inventory.git(ROOT, "rev-parse", "HEAD")
        self.tag = "test-release"
        self.payloads = inventory.build(ROOT)
        bom = json.loads(self.payloads[inventory.OUTPUTS[0]])
        bom["metadata"]["component"]["properties"].append({"name": "nita:release-tag", "value": self.tag})
        self.payloads[inventory.OUTPUTS[0]] = (json.dumps(bom) + "\n").encode()
        self.payloads["SHA256SUMS"] = "".join(
            f"{hashlib.sha256(self.payloads[name]).hexdigest()}  {name}\n"
            for name in inventory.OUTPUTS[:2]
        ).encode()
        for name, data in self.payloads.items():
            (self.directory / name).write_bytes(data)
        event = self.directory / "event.json"
        event.write_text(json.dumps({"action": "published", "release": {"tag_name": self.tag, "id": 123}}))
        self.environment = patch.dict(os.environ, {
            "GITHUB_REPOSITORY": "Juniper/nita", "GITHUB_EVENT_NAME": "release",
            "GITHUB_EVENT_PATH": str(event),
        })
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.existing, self.uploaded = {}, []
        self.api_commit = self.commit
        self.annotated = False
        self.gh_patch = patch.object(publish_inventory, "gh", side_effect=self.fake_gh)
        self.gh_patch.start()
        self.addCleanup(self.gh_patch.stop)

    def fake_gh(self, *args):
        if "--method" in args:
            self.assertIn("POST", args)
            endpoint = next(arg for arg in args if arg.startswith("https://uploads.github.com/"))
            self.assertIn("/releases/123/assets?name=", endpoint)
            name = endpoint.split("name=")[1]
            self.assertNotIn(name, self.existing)
            path = Path(args[args.index("--input") + 1])
            self.assertEqual(path.read_bytes(), self.payloads[name])
            self.uploaded.append(name)
            return b'{"state": "uploaded"}'
        endpoint = args[-1]
        if "/git/ref/tags/" in endpoint:
            return json.dumps({"object": {
                "sha": "a" * 40 if self.annotated else self.api_commit,
                "type": "tag" if self.annotated else "commit",
            }}).encode()
        if "/git/tags/" in endpoint:
            return json.dumps({"object":{"sha":self.api_commit,"type":"commit"}}).encode()
        if endpoint.endswith("/releases/123"):
            return json.dumps({"id":123,"tag_name":self.tag,"draft":False}).encode()
        if "assets?per_page=" in endpoint:
            # Exercise multi-page preflight, including unrelated assets.
            return json.dumps([
                [{"name":"unrelated.zip","id":999}],
                [{"name":name,"id":index} for index,name in enumerate(self.existing)],
            ]).encode()
        if "/releases/assets/" in endpoint:
            index = int(endpoint.split("/")[-1])
            return list(self.existing.values())[index]
        raise AssertionError(args)

    def publish(self):
        publish_inventory.publish(self.directory, self.tag, self.commit, ROOT / "compliance/schemas")

    def test_first_publication(self):
        self.publish()
        self.assertEqual(self.uploaded, list(inventory.OUTPUTS))

    def test_annotated_tag_is_peeled_to_exact_commit(self):
        self.annotated = True
        self.publish()
        self.assertEqual(self.uploaded, list(inventory.OUTPUTS))

    def test_identical_assets_skipped_and_partial_retry(self):
        self.existing = dict(self.payloads)
        self.publish()
        self.assertFalse(self.uploaded)
        del self.existing["nita-components.md"]
        self.publish()
        self.assertEqual(self.uploaded, ["nita-components.md"])

    def test_conflict_is_checked_before_any_upload(self):
        self.existing = {"SHA256SUMS": b"conflict"}
        with self.assertRaisesRegex(inventory.InventoryError, "Conflicting"):
            self.publish()
        self.assertFalse(self.uploaded)

    def test_checksum_and_identity_mismatch(self):
        (self.directory / "nita-components.md").write_text("tampered")
        with self.assertRaisesRegex(inventory.InventoryError, "checksums"):
            self.publish()
        self.assertFalse(self.uploaded)
        (self.directory / "nita-components.md").write_bytes(self.payloads["nita-components.md"])
        self.api_commit = "f" * 40
        with self.assertRaisesRegex(inventory.InventoryError, "changed"):
            self.publish()
        self.assertFalse(self.uploaded)

    def test_fork_and_non_release_refused(self):
        for key,value in (("GITHUB_REPOSITORY","tbelz/nita"),("GITHUB_EVENT_NAME","pull_request")):
            with self.subTest(key=key), patch.dict(os.environ, {key:value}):
                with self.assertRaises(inventory.InventoryError):
                    self.publish()
        self.assertFalse(self.uploaded)


class WorkflowTests(unittest.TestCase):
    def test_privilege_and_artifact_boundaries(self):
        # BaseLoader preserves YAML's "on" key (PyYAML otherwise uses YAML 1.1).
        workflow = yaml.load((ROOT / ".github/workflows/software-inventory.yaml").read_text(), Loader=yaml.BaseLoader)
        self.assertEqual(set(workflow["on"]), {"push","pull_request","workflow_dispatch","release"})
        self.assertEqual(workflow["permissions"], {"contents":"read"})
        publisher = workflow["jobs"]["publish"]
        self.assertEqual(publisher["needs"], "inventory")
        for guard in ("github.repository == 'Juniper/nita'", "github.event_name == 'release'", "github.event.action == 'published'"):
            self.assertIn(guard, publisher["if"])
        self.assertEqual(publisher["permissions"], {"contents":"write"})
        for job in workflow["jobs"].values():
            for step in job["steps"]:
                if "uses" in step:
                    self.assertRegex(step["uses"], r"@[0-9a-f]{40}$")
                if step.get("uses","").startswith("actions/checkout@"):
                    self.assertEqual(step["with"]["persist-credentials"], "false")
        uploads = [step for step in workflow["jobs"]["inventory"]["steps"] if step.get("uses","").startswith("actions/upload-artifact@")]
        self.assertEqual(uploads[0]["with"]["retention-days"], "90")


if __name__ == "__main__":
    unittest.main()
