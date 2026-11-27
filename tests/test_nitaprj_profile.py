import os
import importlib.util
import json
import shutil
import subprocess
import tempfile
import unittest
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
NITAPRJ_DIR = ROOT / "utils" / "nitaprj"
NITAPRJ_SCRIPT = NITAPRJ_DIR / "nitaprj.sh"
JTAF_PROFILE = NITAPRJ_DIR / "profiles" / "jtaf-ansible"
ENRICH_SPEC = importlib.util.spec_from_file_location(
    "enrich_variables", NITAPRJ_DIR / "enrich_variables.py"
)
ENRICH = importlib.util.module_from_spec(ENRICH_SPEC)
ENRICH_SPEC.loader.exec_module(ENRICH)
MANAGEMENT_SPEC = importlib.util.spec_from_file_location(
    "nita_management", JTAF_PROFILE / "filter_plugins" / "nita_management.py"
)
MANAGEMENT = importlib.util.module_from_spec(MANAGEMENT_SPEC)
MANAGEMENT_SPEC.loader.exec_module(MANAGEMENT)


class NitaprjProfileTests(unittest.TestCase):
    def test_empty_units_cleanup_for_aggregate_members_preserves_group_and_dhcp(self):
        generated = (
            '<configuration xmlns="urn:example:junos"><groups><name> JTAF_ANSIBLE </name>'
            "<interfaces><interface><name>xe-0/0/2</name><ether-options><ieee-802.3ad>"
            "<bundle>ae0</bundle></ieee-802.3ad></ether-options></interface></interfaces>"
            "</groups><apply-groups> JTAF_ANSIBLE </apply-groups><interfaces><interface>"
            '<name>em0</name><unit><name>0</name><family><inet><dhcp delete="delete"/>'
            "</inet></family></unit></interface></interfaces></configuration>"
        )
        current = (
            "<configuration><interfaces><interface><name>xe-0/0/2</name><unit><name>0</name>"
            "</unit></interface></interfaces></configuration>"
        )
        summary = MANAGEMENT.nita_interface_unit_cleanup(generated)
        self.assertTrue(summary["has_targets"])
        self.assertEqual(
            ET.fromstring(summary["filter"]).findtext("./interfaces/interface/name"), "xe-0/0/2"
        )
        prepared = MANAGEMENT.nita_reconcile_empty_interface_units(generated, current)
        root = ET.fromstring(prepared)
        physical = next(node for node in root.findall("./{*}interfaces/{*}interface")
                        if node.findtext("{*}name") == "xe-0/0/2")
        self.assertEqual(physical.find("{*}unit").attrib, {"delete": "delete"})
        self.assertEqual(physical.findtext("./{*}unit/{*}name"), "0")
        self.assertEqual(
            root.find("./{*}interfaces/{*}interface/{*}unit/{*}family/{*}inet/{*}dhcp").attrib,
            {"delete": "delete"},
        )
        self.assertEqual(
            ET.tostring(root.find("{*}groups")),
            ET.tostring(ET.fromstring(generated).find("{*}groups")),
        )
        self.assertEqual(
            MANAGEMENT.nita_reconcile_empty_interface_units(prepared, current), prepared
        )
        self.assertNotIn('<unit delete="delete">', generated)

    def test_empty_units_cleanup_for_tagged_ports_keeps_desired_and_valid_units(self):
        generated = (
            "<configuration><groups><name>fabric</name><interfaces><interface><name>xe-0/0/1</name>"
            "<vlan-tagging/><unit><name>1</name><vlan-id>1</vlan-id><family><inet><address>"
            "<name>192.0.2.1/24</name></address></inet></family></unit></interface></interfaces>"
            "</groups><apply-groups>fabric</apply-groups></configuration>"
        )
        current = (
            "<configuration><interfaces><interface><name>xe-0/0/1</name><unit><name>0</name>"
            "</unit><unit><name>1</name><description>existing</description></unit>"
            "<unit><name>9</name><vlan-id>9</vlan-id><family><inet/></family></unit>"
            "</interface><interface><name>xe-0/0/2</name><unit><name>0</name></unit>"
            "</interface></interfaces></configuration>"
        )
        prepared = ET.fromstring(MANAGEMENT.nita_reconcile_empty_interface_units(generated, current))
        self.assertEqual(
            [node.findtext("name") for node in prepared.findall("./interfaces/interface/unit")],
            ["0"],
        )
        self.assertEqual(prepared.find("./interfaces/interface/unit").attrib, {"delete": "delete"})
        self.assertEqual(prepared.findtext("./groups/interfaces/interface/unit/vlan-id"), "1")
        self.assertIsNone(prepared.find("./interfaces/interface/unit/description"))
        self.assertEqual(
            MANAGEMENT.nita_reconcile_empty_interface_units(generated, "<configuration/>"),
            generated,
        )

    def test_empty_units_cleanup_refuses_meaningful_unit_configuration(self):
        for mode in (
            "<ether-options><ieee-802.3ad><bundle>ae0</bundle></ieee-802.3ad></ether-options>",
            "<vlan-tagging/><unit><name>1</name><vlan-id>1</vlan-id></unit>",
        ):
            generated = (
                "<configuration><interfaces><interface><name>xe-0/0/2</name>"
                f"{mode}</interface></interfaces></configuration>"
            )
            for content in (
                "<description>keep me</description>",
                "<family><inet><address><name>192.0.2.1/24</name></address></inet></family>",
            ):
                current = (
                    "<configuration><interfaces><interface><name>xe-0/0/2</name><unit>"
                    f"<name>0</name>{content}</unit></interface></interfaces></configuration>"
                )
                with self.subTest(mode=mode, content=content), self.assertRaisesRegex(
                    ValueError, "Refusing to delete non-empty"
                ):
                    MANAGEMENT.nita_reconcile_empty_interface_units(generated, current)

    def test_empty_units_cleanup_ignores_unused_modes_and_inactive_units(self):
        mode = "<ether-options><ieee-802.3ad><bundle>ae0</bundle></ieee-802.3ad></ether-options>"
        for generated in (
            f"<configuration><groups><name>unused</name><interfaces><interface>"
            f"<name>xe-0/0/2</name>{mode}</interface></interfaces></groups></configuration>",
            f'<configuration><interfaces><interface inactive="inactive"><name>xe-0/0/2</name>'
            f"{mode}</interface></interfaces></configuration>",
            "<configuration><interfaces><interface><name>xe-0/0/2</name><unit><name>0</name>"
            "<family><inet/></family></unit></interface></interfaces></configuration>",
            "<configuration><interfaces><interface><name>ae0</name><vlan-tagging/>"
            "<unit><name>1</name><vlan-id>1</vlan-id></unit></interface></interfaces></configuration>",
        ):
            self.assertFalse(MANAGEMENT.nita_interface_unit_cleanup(generated)["has_targets"])
            self.assertEqual(
                MANAGEMENT.nita_reconcile_empty_interface_units(generated, "<configuration/>"),
                generated,
            )
        generated = (
            f"<configuration><interfaces><interface><name>xe-0/0/2</name>{mode}"
            "</interface></interfaces></configuration>"
        )
        current = (
            '<configuration><interfaces><interface><name>xe-0/0/2</name><unit inactive="inactive">'
            "<name>0</name></unit></interface></interfaces></configuration>"
        )
        self.assertEqual(MANAGEMENT.nita_reconcile_empty_interface_units(generated, current), generated)

    def test_empty_units_cleanup_rejects_invalid_generated_modes(self):
        for mode, message in (
            ("<ether-options><ieee-802.3ad><bundle>ae0</bundle></ieee-802.3ad></ether-options>"
             "<unit><name>0</name></unit>", "Generated aggregate member"),
            ("<vlan-tagging/><unit><name>0</name></unit>", "Generated tagged interface"),
        ):
            generated = (
                "<configuration><interfaces><interface><name>xe-0/0/2</name>"
                f"{mode}</interface></interfaces></configuration>"
            )
            with self.subTest(mode=mode), self.assertRaisesRegex(ValueError, message):
                MANAGEMENT.nita_interface_unit_cleanup(generated)

    def test_applied_management_group_deletes_direct_dhcp_without_changing_group(self):
        generated = (
            '<configuration xmlns="urn:example:junos"><groups><name> JTAF_ANSIBLE </name>'
            "<interfaces><interface><name>fxp0</name><unit><name>7</name><family><inet>"
            "<address><name>192.0.2.5/24</name></address></inet><inet6><dhcpv6-client/>"
            "</inet6></family></unit></interface></interfaces></groups>"
            "<apply-groups> JTAF_ANSIBLE </apply-groups></configuration>"
        )
        current = (
            "<configuration><interfaces><interface><name>fxp0</name><unit><name>7</name>"
            "<family><inet><dhcp/></inet></family></unit></interface></interfaces></configuration>"
        )
        summary = MANAGEMENT.nita_management_addressing(generated, "fxp0.7")
        self.assertTrue(summary["has_static_ipv4"])
        self.assertEqual(
            ET.fromstring(summary["filter"]).findtext("./interfaces/interface/unit/name"), "7"
        )
        prepared = MANAGEMENT.nita_reconcile_management_dhcp(generated, current, "fxp0.7")
        root = ET.fromstring(prepared)
        inet = root.find("./{*}interfaces/{*}interface/{*}unit/{*}family/{*}inet")
        self.assertEqual(inet.find("{*}dhcp").attrib, {"delete": "delete"})
        self.assertEqual(root.findtext("./{*}interfaces/{*}interface/{*}name"), "fxp0")
        self.assertEqual(root.findtext("./{*}interfaces/{*}interface/{*}unit/{*}name"), "7")
        self.assertIsNone(inet.find("{*}address"))
        self.assertEqual(
            ET.tostring(root.find("{*}groups")),
            ET.tostring(ET.fromstring(generated).find("{*}groups")),
        )
        self.assertEqual(root.findtext("{*}apply-groups"), " JTAF_ANSIBLE ")
        self.assertEqual(
            MANAGEMENT.nita_reconcile_management_dhcp(prepared, current, "fxp0.7"), prepared
        )
        self.assertEqual(
            MANAGEMENT.nita_reconcile_management_dhcp(generated, "<configuration/>", "fxp0.7"),
            generated,
        )

    def test_grouped_management_ignores_unapplied_inactive_and_excluded_groups(self):
        for attributes, application, address in (
            ("", "", "<address><name>192.0.2.5/24</name></address>"),
            (' inactive="inactive"', "<apply-groups>example</apply-groups>",
             "<address><name>192.0.2.5/24</name></address>"),
            ("", '<apply-groups inactive="inactive">example</apply-groups>',
             "<address><name>192.0.2.5/24</name></address>"),
            ("", "<apply-groups>example</apply-groups><apply-groups-except>example</apply-groups-except>",
             "<address><name>192.0.2.5/24</name></address>"),
            ("", "<apply-groups>example</apply-groups>",
             '<address inactive="inactive"><name>192.0.2.5/24</name></address>'),
        ):
            with self.subTest(attributes=attributes, application=application, address=address):
                generated = (
                    f"<configuration><groups{attributes}><name>example</name><interfaces>"
                    f"<interface><name>em0</name><unit><name>0</name><family><inet>{address}"
                    "</inet></family></unit></interface></interfaces></groups>"
                    f"{application}</configuration>"
                )
                self.assertFalse(
                    MANAGEMENT.nita_management_addressing(generated, "em0")["has_static_ipv4"]
                )
                self.assertEqual(
                    MANAGEMENT.nita_reconcile_management_dhcp(generated, "<configuration/>", "em0"),
                    generated,
                )
        generated = (
            "<configuration><groups><name>example</name><interfaces inactive=\"inactive\">"
            "<interface><name>em0</name><unit><name>0</name><family><inet><address>"
            "<name>192.0.2.5/24</name></address></inet></family></unit></interface>"
            "</interfaces></groups><apply-groups>example</apply-groups></configuration>"
        )
        self.assertFalse(
            MANAGEMENT.nita_management_addressing(generated, "em0")["has_static_ipv4"]
        )

    def test_grouped_management_rejects_invalid_addresses_and_cross_scope_dhcp(self):
        static = (
            "<groups><name>static</name><interfaces><interface><name>em0</name>"
            "<unit><name>0</name><family><inet><address><name>192.0.2.5/24</name></address>"
            "</inet></family></unit></interface></interfaces></groups><apply-groups>static</apply-groups>"
        )
        dhcp = (
            "<interfaces><interface><name>em0</name><unit><name>0</name><family><inet>"
            "<dhcp/></inet></family></unit></interface></interfaces>"
        )
        for scope in (dhcp, f"<groups><name>dhcp</name>{dhcp}</groups><apply-groups>dhcp</apply-groups>"):
            with self.subTest(scope=scope), self.assertRaisesRegex(
                ValueError, "enables both DHCP and static"
            ):
                MANAGEMENT.nita_management_addressing(
                    f"<configuration>{static}{scope}</configuration>", "em0"
                )
        with self.assertRaisesRegex(ValueError, "Invalid static IPv4"):
            MANAGEMENT.nita_management_addressing(
                f"<configuration>{static}</configuration>".replace("192.0.2.5/24", "invalid"),
                "em0",
            )

    def test_management_dhcp_deletion_preserves_static_address_and_other_interfaces(self):
        generated = (
            "<configuration><interfaces><interface><name>em0</name><unit><name>0</name>"
            "<family><inet><address><name>192.0.2.5/24</name></address></inet>"
            "<inet6><dhcpv6-client/></inet6></family></unit></interface>"
            "<interface><name>em1</name><unit><name>0</name><family><inet><dhcp/>"
            "</inet></family></unit></interface></interfaces></configuration>"
        )
        current = (
            "<rpc-reply><configuration><interfaces><interface><name>em0</name>"
            "<unit><name>0</name><family><inet><dhcp><client-identifier>"
            "<user-id>example</user-id></client-identifier></dhcp></inet></family>"
            "</unit></interface></interfaces></configuration></rpc-reply>"
        )
        result = MANAGEMENT.nita_reconcile_management_dhcp(generated, current, "em0.0")
        root = ET.fromstring(result)
        interfaces = root.findall("./interfaces/interface")
        inet = interfaces[0].find("./unit/family/inet")
        self.assertEqual(inet.findtext("./address/name"), "192.0.2.5/24")
        self.assertEqual(inet.find("dhcp").attrib, {"delete": "delete"})
        self.assertEqual(len(inet.find("dhcp")), 0)
        self.assertIsNotNone(interfaces[0].find("./unit/family/inet6/dhcpv6-client"))
        self.assertEqual(interfaces[1].find("./unit/family/inet/dhcp").attrib, {})
        self.assertNotIn('delete="delete"', generated)
        metadata = ENRICH.management_interface({
            "interfaces": {"interface": [{
                "name": "em0", "unit": [{
                    "name": "0", "family": {"inet": {"address": [{"name": "192.0.2.5/24"}]}},
                }],
            }]},
        }, "em0")
        self.assertEqual(
            MANAGEMENT.nita_reconcile_management_dhcp(generated, current, metadata["int"]),
            result,
        )

    def test_management_dhcp_reconciliation_is_idempotent_and_unit_specific(self):
        generated = (
            "<configuration><interfaces><interface><name>fxp0</name><unit><name>7</name>"
            "<family><inet><address><name>192.0.2.5/24</name></address></inet></family>"
            "</unit></interface></interfaces></configuration>"
        )
        current = (
            '<configuration xmlns="urn:example:junos"><interfaces><interface>'
            "<name>fxp0</name><unit><name>0</name><family><inet><dhcp/></inet></family>"
            "</unit><unit><name>7</name><family><inet><dhcp inactive=\"inactive\"/>"
            "</inet></family></unit></interface></interfaces></configuration>"
        )
        self.assertEqual(
            MANAGEMENT.nita_reconcile_management_dhcp(generated, current, "fxp0.7"),
            generated,
        )
        current = current.replace(' inactive="inactive"', "")
        prepared = MANAGEMENT.nita_reconcile_management_dhcp(generated, current, "fxp0.7")
        self.assertEqual(ET.fromstring(prepared).find("./interfaces/interface/unit/family/inet/dhcp").attrib,
                         {"delete": "delete"})
        self.assertEqual(
            MANAGEMENT.nita_reconcile_management_dhcp(generated, "<configuration/>", "fxp0.7"),
            generated,
        )

    def test_management_without_active_static_ipv4_is_unchanged(self):
        for inet in (
            "<dhcp/>",
            '<address inactive="inactive"><name>192.0.2.5/24</name></address>',
            '<address delete="delete"><name>192.0.2.5/24</name></address>',
            "",
        ):
            generated = (
                "<configuration><interfaces><interface><name>em0</name><unit><name>0</name>"
                f"<family><inet>{inet}</inet></family></unit></interface></interfaces>"
                "</configuration>"
            )
            summary = MANAGEMENT.nita_management_addressing(generated, "em0.0")
            self.assertFalse(summary["has_static_ipv4"])
            self.assertEqual(
                MANAGEMENT.nita_reconcile_management_dhcp(generated, "<configuration/>", "em0.0"),
                generated,
            )

    def test_management_xml_errors_stop_reconciliation(self):
        generated = (
            "<configuration><interfaces><interface><name>em0</name><unit><name>0</name>"
            "<family><inet><address><name>192.0.2.5/24</name></address></inet></family>"
            "</unit></interface></interfaces></configuration>"
        )
        with self.assertRaisesRegex(ValueError, "enables both DHCP and static"):
            MANAGEMENT.nita_management_addressing(
                generated.replace("</inet>", "<dhcp/></inet>"), "em0.0"
            )
        with self.assertRaisesRegex(ValueError, "Invalid static IPv4"):
            MANAGEMENT.nita_management_addressing(generated.replace("192.0.2.5/24", "invalid"), "em0.0")
        with self.assertRaisesRegex(ValueError, "Invalid retrieved XML"):
            MANAGEMENT.nita_reconcile_management_dhcp(generated, "<configuration>", "em0.0")
        with self.assertRaisesRegex(ValueError, "must contain one configuration"):
            MANAGEMENT.nita_reconcile_management_dhcp(generated, "<rpc-reply/>", "em0.0")
        with self.assertRaisesRegex(ValueError, "must include a numeric unit"):
            MANAGEMENT.nita_management_addressing(generated, "em0.invalid")
        with self.assertRaisesRegex(ValueError, "Ambiguous"):
            MANAGEMENT.nita_management_addressing(
                generated.replace(
                    "</interfaces>", "<interface><name>em0</name></interface></interfaces>"
                ),
                "em0.0",
            )

    def test_presence_restoration_preserves_strings_and_handles_list_flags(self):
        payload = {"interfaces": {"interface": [{
            "name": "true", "description": "false",
            "active": "TRUE", "disabled": "false",
        }]}}
        restored = ENRICH.restore_presence_flags(payload, {
            "interfaces/interface/active", "interfaces/interface/disabled",
        }, "test")
        self.assertEqual(restored, {"interfaces": {"interface": [{
            "name": "true", "description": "false", "active": True,
        }]}})
        self.assertEqual(payload["interfaces"]["interface"][0]["active"], "TRUE")
        with self.assertRaisesRegex(ValueError, "invalid presence flag"):
            ENRICH.restore_presence_flags({"flag": "not-a-boolean"}, {"flag"}, "test")

    def test_original_xml_records_only_schema_leaf_presence_flags(self):
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            (project / "configs").mkdir()
            schema = {"root": {"children": [{
                "name": "then", "path": "", "type": "container",
                "children": [
                    {"name": "accept", "path": "then", "type": "leaf", "leaf-type": "empty"},
                    {"name": "add", "path": "then", "type": "leaf", "leaf-type": "string"},
                    {"name": "description", "path": "then", "type": "leaf", "leaf-type": "string"},
                ],
            }]}}
            (project / "configs/trimmed_schema.json").write_text(json.dumps(schema))
            xml = project / "source.xml"
            xml.write_text(
                "<rpc-reply><configuration><then><accept/><add/>"
                "<description>true</description><unknown/></then>"
                "</configuration></rpc-reply>"
            )
            ENRICH.record_empty_leaves(project, [xml])
            hints = json.loads((project / "configs/empty_leaf_paths.json").read_text())
            self.assertEqual(hints, ["then/accept", "then/add"])

    def test_invalid_presence_flag_does_not_partially_update_project(self):
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            for name in ("configs", "group_vars", "host_vars"):
                (project / name).mkdir()
            schema = {"root": {"children": [{
                "name": "accept", "path": "", "type": "leaf", "leaf-type": "empty",
            }]}}
            (project / "configs/trimmed_schema.json").write_text(json.dumps(schema))
            shared = project / "group_vars/all.yaml"
            shared.write_text("accept: 'true'\n")
            host = project / "host_vars/device.yaml"
            host.write_text("accept: invalid\n")
            with self.assertRaisesRegex(ValueError, "invalid presence flag"):
                ENRICH.enrich_variables(project)
            self.assertEqual(shared.read_text(), "accept: 'true'\n")

    def test_hosts_preparation_uses_serialized_container_safe_updates(self):
        hosts = yaml.safe_load((JTAF_PROFILE / "make_etc_hosts.yaml").read_text())
        self.assertFalse(hosts[0]["gather_facts"])
        task = hosts[0]["tasks"][0]
        self.assertEqual(task["throttle"], 1)
        settings = task["ansible.builtin.lineinfile"]
        self.assertEqual(settings["path"], "/etc/hosts")
        self.assertTrue(settings["unsafe_writes"])
        self.assertIn("inventory_hostname | regex_escape", settings["regexp"])
        self.assertIn("management_interface.ip", settings["line"])
        self.assertIn("split('/') | first", settings["line"])

    def test_deployment_address_supports_management_ip_and_cidr(self):
        commit = yaml.safe_load((JTAF_PROFILE / "build/commit.yaml").read_text())
        defaults = commit[0]["module_defaults"]["juniper.device.config"]
        self.assertEqual(
            defaults["host"],
            "{{ (ansible_host | default(management_interface.ip | "
            "default(inventory_hostname))) | split('/') | first }}",
        )
        tasks = commit[0]["tasks"]
        retrieval = next(t["juniper.device.config"] for t in tasks
                         if t.get("juniper.device.config", {}).get("retrieve"))
        self.assertFalse(retrieval["commit"])
        self.assertFalse(retrieval["check"])
        deployment = next(t["juniper.device.config"] for t in tasks
                          if t.get("juniper.device.config", {}).get("load"))
        self.assertEqual(deployment["load"], "merge")
        self.assertIn(".static-management.xml", deployment["src"])

    def test_connection_settings_survive_workbook_variable_replacement(self):
        runtime = yaml.safe_load((JTAF_PROFILE / "build/runtime.yaml").read_text())
        commit = yaml.safe_load((JTAF_PROFILE / "build/commit.yaml").read_text())
        self.assertIn("runtime.yaml", commit[0]["vars_files"])
        self.assertIn("ANSIBLE_NET_USERNAME", runtime["netconf_user"])
        self.assertIn("default('jcluser', true)", runtime["netconf_user"])
        self.assertEqual(runtime["netconf_port"], 830)
        self.assertIn("ANSIBLE_NET_PASSWORD", runtime["netconf_passwd"])
        self.assertIn("default('Juniper!1', true)", runtime["netconf_passwd"])
        workbook_variables = {"system": {"host_name": "example"}, "netconf_passwd": "workbook"}
        effective = {**workbook_variables, **runtime}
        self.assertEqual(effective["netconf_user"], runtime["netconf_user"])
        self.assertEqual(effective["netconf_passwd"], runtime["netconf_passwd"])
        self.assertEqual(effective["netconf_port"], 830)

    def test_create_profile_selection(self):
        for profile_args, expected_profile in (([], "jtaf-ansible"), (["generic"], "generic")):
            with self.subTest(profile=expected_profile):
                project_name = f"nitaprj-test-{uuid.uuid4().hex}"
                project_dir = NITAPRJ_DIR / project_name
                try:
                    result = subprocess.run(
                        ["bash", str(NITAPRJ_SCRIPT), "create", project_name, *profile_args],
                        cwd=NITAPRJ_DIR,
                        input="n\n",
                        text=True,
                        capture_output=True,
                        check=False,
                    )

                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertIn(f"using profile '{expected_profile}'", result.stdout)
                    self.assertEqual(
                        (project_dir / "build.sh").read_bytes(),
                        (NITAPRJ_DIR / "profiles" / expected_profile / "build.sh").read_bytes(),
                    )
                    self.assertEqual(
                        (project_dir / "enrich_variables.py").exists(),
                        expected_profile == "jtaf-ansible",
                    )
                finally:
                    shutil.rmtree(project_dir, ignore_errors=True)

    def test_jtaf_ansible_create_renders_and_packages_project_yaml(self):
        project_name = f"nitaprj-test-{uuid.uuid4().hex}"
        project_dir = NITAPRJ_DIR / project_name

        try:
            result = subprocess.run(
                ["bash", str(NITAPRJ_SCRIPT), "create", project_name, "jtaf-ansible"],
                cwd=NITAPRJ_DIR,
                input="n\n",
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            project_yaml = (project_dir / "project.yaml").read_text(encoding="utf-8")
            manifest = (project_dir / "manifest").read_text(encoding="utf-8")
            self.assertIn(f"name: {project_name}", project_yaml)
            self.assertNotIn("__PROJECT_NAME__", project_yaml)
            self.assertIn("project.yaml", manifest.splitlines())
            self.assertEqual(project_yaml.count("jenkins_url:"), 4)
            self.assertIn("shell_command: bash ./run_build.sh", project_yaml)
            self.assertTrue((project_dir / "build/runtime.yaml").is_file())
            self.assertTrue((project_dir / "build/commit.yaml").is_file())
            self.assertEqual(
                (project_dir / "filter_plugins/nita_management.py").read_bytes(),
                (JTAF_PROFILE / "filter_plugins/nita_management.py").read_bytes(),
            )
            self.assertIn("make_etc_hosts.yaml", manifest.splitlines())
            self.assertIn("enrich_variables.py", manifest.splitlines())
            self.assertEqual(
                (project_dir / "enrich_variables.py").read_bytes(),
                (NITAPRJ_DIR / "enrich_variables.py").read_bytes(),
            )
            sites = yaml.safe_load((project_dir / "build/sites.yaml").read_text())
            self.assertEqual(sites[0]["import_playbook"], "../make_etc_hosts.yaml")
            self.assertNotIn(
                "junos_commit_config",
                (project_dir / "build/sites.yaml").read_text(),
            )
            for entry in manifest.splitlines():
                entry = entry.strip()
                if entry and not entry.startswith("#"):
                    self.assertTrue((project_dir / entry).exists(), entry)
        finally:
            shutil.rmtree(project_dir, ignore_errors=True)

    def test_generated_roles_load_runtime_paths_outside_workbook(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            project = root / "project"
            shutil.copytree(JTAF_PROFILE, project)
            tools = root / "bin"
            tools.mkdir()
            generator = tools / "jtaf-yang2ansible"
            generator.write_text(
                "#!/bin/bash\n"
                "mkdir -p ansible-provider-junos-qfx/roles/qfx_role/tasks "
                "ansible-provider-junos-qfx/filter_plugins\n"
                "echo '[]' > ansible-provider-junos-qfx/roles/qfx_role/tasks/main.yml\n"
                "cat > ansible-provider-junos-qfx/trimmed_schema.json <<'JSON'\n"
                '{"root":{"children":[{"name":"accept","path":"","type":"leaf",'
                '"leaf-type":"empty"}]}}\nJSON\n'
            )
            converter = tools / "jtaf-xml2yaml"
            converter.write_text("#!/bin/bash\nexit 0\n")
            generator.chmod(0o755)
            converter.chmod(0o755)
            xml = root / "config.xml"
            xml.write_text("<configuration><accept/></configuration>")
            env = dict(os.environ, PATH=f"{tools}:{os.environ['PATH']}")
            command = [
                "bash", str(NITAPRJ_SCRIPT), "generate-role", str(project),
                "-p", "schema.yang", "-x", str(xml), "-t", "qfx",
            ]
            for _ in range(2):
                result = subprocess.run(
                    command, cwd=NITAPRJ_DIR, env=env, text=True, capture_output=True,
                )
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            sites = (project / "build/sites.yaml").read_text()
            self.assertEqual(sites.count("role: qfx_role"), 1)
            self.assertIn("  vars_files:\n    - runtime.yaml", sites)
            self.assertNotIn('tmp_dir: "configs"', sites)
            runtime = (project / "build/runtime.yaml").read_text()
            self.assertIn("{{ inventory_hostname }}/xml", runtime)
            self.assertEqual(
                json.loads((project / "configs/empty_leaf_paths.json").read_text()),
                ["accept"],
            )
            self.assertIn(
                "enrich_variables.py", (project / "manifest").read_text().splitlines()
            )

    def test_build_stops_on_render_failure_and_preserves_exit_code(self):
        self._run_build_with_stub(render_status=2, commit_status=0, expected=2)

    def test_build_propagates_commit_failure(self):
        self._run_build_with_stub(render_status=0, commit_status=3, expected=3)

    def test_build_renders_before_commit_and_creates_log(self):
        self._run_build_with_stub(render_status=0, commit_status=0, expected=0)

    def test_build_stops_on_deployment_preflight_failure(self):
        self._run_build_with_stub(0, 0, 1, preflight_status=4)

    def _run_build_with_stub(self, render_status, commit_status, expected, preflight_status=0):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            tools = root / "bin"
            tools.mkdir()
            ansible = tools / "ansible-playbook"
            calls = root / "calls"
            ansible.write_text(
                "#!/bin/bash\n"
                'echo "$3${4:+ $4}" >> "$CALLS"\n'
                'test -f build/runtime.yaml || exit 99\n'
                'echo "Ansible output"\n'
                f'if [ "$4" = --syntax-check ]; then exit {preflight_status}; fi\n'
                f'if [ "$3" = build/sites.yaml ]; then exit {render_status}; fi\n'
                f"exit {commit_status}\n"
            )
            ansible.chmod(0o755)
            env = dict(
                os.environ, PATH=f"{tools}:{os.environ['PATH']}",
                HOME=str(root), CALLS=str(calls),
            )
            output = root / "output"
            result = subprocess.run(
                ["bash", str(JTAF_PROFILE / "build.sh"), str(output)],
                cwd=root, env=env, text=True, capture_output=True,
            )
            self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
            expected_calls = ["build/commit.yaml --syntax-check"]
            if preflight_status == 0:
                expected_calls.append("build/sites.yaml --extra-vars")
            if preflight_status == 0 and render_status == 0:
                expected_calls.append("build/commit.yaml --extra-vars")
            self.assertEqual(calls.read_text().splitlines(), expected_calls)
            self.assertIn("Ansible output", (output / "ansible-run.log").read_text())

    def test_jenkins_runner_checks_job_result_not_log_exit_code(self):
        for failed in (False, True):
            with self.subTest(failed=failed), tempfile.TemporaryDirectory() as temp_dir:
                root = Path(temp_dir)
                project = root / "project"
                shutil.copytree(JTAF_PROFILE, project)
                shutil.copy2(NITAPRJ_DIR / "enrich_variables.py", project)
                for name, body in {
                    "write_yaml_files.py": "exit 0",
                    "python3": (
                        'test -f "$1" || exit 99\n'
                        'test "$PWD" = "$PROJECT_DIR" || exit 98\n'
                        "exit 0"
                    ),
                    "kubectl": (
                        'echo "$*" >> "$CALLS"\n'
                        'if [ "$1" = get ]; then echo pod/build-test; fi\n'
                        'if [ "$1" = wait ] && [ "$2" = --for=condition=complete ]; then\n'
                        f"  exit {1 if failed else 0}\n"
                        "fi\nexit 0"
                    ),
                }.items():
                    tool = root / name
                    tool.write_text(f"#!/bin/bash\n{body}\n")
                    tool.chmod(0o755)
                calls = root / "calls"
                result = subprocess.run(
                    ["bash", str(project / "run_build.sh")], cwd=root,
                    env=dict(os.environ, PATH=f"{root}:{os.environ['PATH']}",
                             CALLS=str(calls), PROJECT_DIR=str(project),
                             NITA_NAMESPACE="test-fabric"),
                    text=True, capture_output=True,
                )
                self.assertEqual(result.returncode, 1 if failed else 0)
                self.assertIn("wait --for=condition=complete", calls.read_text())
                self.assertNotIn(".status.ready", calls.read_text())
                self.assertTrue(all(
                    "-n test-fabric" in line
                    for line in calls.read_text().splitlines()
                ))
                if failed:
                    self.assertIn("did not complete successfully", result.stderr)

    def test_runner_restores_management_after_workbook_and_stops_on_invalid_addresses(self):
        for addresses in (["192.0.2.5/24"], [], ["192.0.2.5/24", "192.0.2.6/24"]):
            with self.subTest(addresses=addresses), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                project = root / "project"
                shutil.copytree(JTAF_PROFILE, project)
                shutil.copy2(NITAPRJ_DIR / "enrich_variables.py", project)
                (project / "group_vars/all.yaml").write_text("{}\n")
                (project / "host_vars/device.yaml").write_text(
                    "management_interface:\n  ip: 192.0.2.99\n"
                )
                workbook_host = {
                    "interfaces": {"interface": [{
                        "name": "em0", "unit": [{
                            "name": "0", "family": {"inet": {
                                "address": [{"name": address} for address in addresses]
                            }}
                        }]
                    }]}
                }
                tools = root / "bin"
                tools.mkdir()
                writer = tools / "write_yaml_files.py"
                writer.write_text(
                    "#!/bin/bash\n"
                    "cat > host_vars/device.yaml <<'YAML'\n"
                    + yaml.safe_dump(workbook_host)
                    + "YAML\n"
                )
                writer.chmod(0o755)
                kubectl = tools / "kubectl"
                calls = root / "calls"
                kubectl.write_text(
                    "#!/bin/bash\n"
                    'echo "$*" >> "$CALLS"\n'
                    'if [ "$1" = get ]; then echo pod/build-test; fi\n'
                )
                kubectl.chmod(0o755)
                result = subprocess.run(
                    ["bash", str(project / "run_build.sh")],
                    cwd=root,
                    env=dict(os.environ, PATH=f"{tools}:{os.environ['PATH']}",
                             CALLS=str(calls), NITA_NETCONF_SECRET=""),
                    text=True, capture_output=True,
                )
                if len(addresses) == 1:
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    host = yaml.safe_load((project / "host_vars/device.yaml").read_text())
                    self.assertEqual(host["management_interface"], {
                        "int": "em0", "ip": "192.0.2.5", "mask": 24,
                    })
                    self.assertTrue(calls.exists())
                else:
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn("Variable enrichment failed:", result.stderr)
                    self.assertFalse(calls.exists())
                    self.assertFalse((project / "build.yaml").exists())

    def test_job_generator_passes_build_directory_without_shell_interpolation(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            output_dir = "/tmp/build directory;not-a-command"
            result = subprocess.run(
                ["python3", str(JTAF_PROFILE / "create_ansible_job_k8s.py"), "build"],
                cwd=root,
                env=dict(os.environ, build_dir=output_dir,
                         NITA_NETCONF_SECRET="", NITA_NAMESPACE="nita"),
                text=True, capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            job = yaml.safe_load((root / "build.yaml").read_text())
            container = job["spec"]["template"]["spec"]["containers"][0]
            self.assertEqual(container["command"], ["/bin/bash"])
            self.assertEqual(container["args"], ["build.sh", output_dir])
            self.assertEqual(container["env"], [])
            self.assertEqual(job["spec"]["backoffLimit"], 0)
            self.assertEqual(job["metadata"]["namespace"], "nita")

    def test_job_generator_secret_replaces_only_netconf_credentials(self):
        for secret in ("fabric-credentials", ""):
            with self.subTest(secret=secret), tempfile.TemporaryDirectory() as temp_dir:
                root = Path(temp_dir)
                (root / "group_vars").mkdir()
                variables = {
                    "ANSIBLE_NET_USERNAME": "test-user",
                    "ANSIBLE_NET_PASSWORD": "test-placeholder",
                    "UNRELATED_SETTING": 42,
                }
                (root / "group_vars/env.yaml").write_text(
                    yaml.safe_dump({"env": variables})
                )
                result = subprocess.run(
                    ["python3", str(JTAF_PROFILE / "create_ansible_job_k8s.py"), "build"],
                    cwd=root,
                    env=dict(os.environ, NITA_NETCONF_SECRET=secret,
                             NITA_NAMESPACE="test-fabric"),
                    text=True, capture_output=True,
                )
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                job = yaml.safe_load((root / "build.yaml").read_text())
                self.assertEqual(job["metadata"]["namespace"], "test-fabric")
                entries = job["spec"]["template"]["spec"]["containers"][0]["env"]
                self.assertEqual(len(entries), 3)
                environment = {entry["name"]: entry for entry in entries}
                self.assertEqual(environment["UNRELATED_SETTING"]["value"], "42")
                for name in ("ANSIBLE_NET_USERNAME", "ANSIBLE_NET_PASSWORD"):
                    if secret:
                        self.assertEqual(environment[name], {
                            "name": name,
                            "valueFrom": {
                                "secretKeyRef": {"name": secret, "key": name}
                            },
                        })
                    else:
                        self.assertEqual(environment[name]["value"], variables[name])


if __name__ == "__main__":
    unittest.main()