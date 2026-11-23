import argparse
import ipaddress
import json
from pathlib import Path
from xml.etree import ElementTree

import yaml


def load_mapping(path):
    with path.open(encoding="utf-8") as source:
        value = yaml.safe_load(source)
    if not isinstance(value, dict):
        raise ValueError(f"Expected a YAML mapping in {path}")
    return value


def schema_leaves(project):
    path = project / "configs" / "trimmed_schema.json"
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as source:
        schema = json.load(source)
    leaves = {}

    def visit(node):
        if node.get("type") in {"leaf", "leaf-list"}:
            path = "/".join(filter(None, (node.get("path", ""), node["name"])))
            leaves[path.replace("-", "_").replace(".", "_")] = node
        for child in node.get("children", []):
            visit(child)

    visit(schema["root"])
    return leaves


def record_empty_leaves(project, xml_files):
    leaves = schema_leaves(project)
    if not leaves:
        raise ValueError("A trimmed schema is required to record XML presence flags")
    paths = set()
    hints_path = project / "configs" / "empty_leaf_paths.json"
    if hints_path.exists():
        paths.update(json.loads(hints_path.read_text(encoding="utf-8")))

    def visit(element, path=""):
        path = "/".join(filter(None, (path, element.tag)))
        normalized = path.replace("-", "_").replace(".", "_")
        if normalized in leaves and len(element) == 0 and not (element.text or "").strip():
            paths.add(normalized)
        for child in element:
            visit(child, path)

    for filename in xml_files:
        root = ElementTree.parse(filename).getroot()
        configuration = root if root.tag == "configuration" else root.find(".//configuration")
        if configuration is None:
            raise ValueError(f"No configuration element found in {filename}")
        for child in configuration:
            visit(child)
    hints_path.write_text(json.dumps(sorted(paths), indent=2) + "\n", encoding="utf-8")


def restore_presence_flags(payload, paths, location):
    def visit(value, path=""):
        if isinstance(value, list):
            return [visit(item, path) for item in value]
        if not isinstance(value, dict):
            return value
        restored = {}
        for key, child in value.items():
            child_path = "/".join(filter(None, (path, key)))
            if child_path in paths:
                if child is True or (isinstance(child, str) and child.strip().lower() in {"true", ""}):
                    restored[key] = True
                elif child is False or (isinstance(child, str) and child.strip().lower() == "false"):
                    continue
                else:
                    raise ValueError(f"{location}: invalid presence flag at {child_path}")
            else:
                restored[key] = visit(child, child_path)
        return restored

    return visit(payload)


def primary_loopback(payload):
    addresses = []
    for interface in payload.get("interfaces", {}).get("interface", []):
        if interface.get("name") != "lo0":
            continue
        for unit in interface.get("unit", []):
            if str(unit.get("name")) == "0":
                addresses.extend(
                    address["name"]
                    for address in unit.get("family", {}).get("inet", {}).get("address", [])
                )
    if len(addresses) > 1:
        raise ValueError("Multiple IPv4 addresses on lo0.0; set loopback_ip explicitly")
    if not addresses:
        return None
    address = ipaddress.ip_interface(addresses[0])
    if address.version != 4:
        raise ValueError("Expected an IPv4 address on lo0.0")
    return str(address.ip)


def management_interface(payload, interface_name):
    addresses = []
    for interface in payload.get("interfaces", {}).get("interface", []):
        if interface.get("name") != interface_name:
            continue
        for unit in interface.get("unit", []):
            if str(unit.get("name")) == "0":
                addresses.extend(
                    address["name"]
                    for address in unit.get("family", {}).get("inet", {}).get("address", [])
                )
    if not addresses:
        return None
    if len(addresses) != 1:
        raise ValueError(f"Expected exactly one IPv4 address on {interface_name}.0")
    if not isinstance(addresses[0], str) or "/" not in addresses[0]:
        raise ValueError(f"Expected an IPv4 CIDR address on {interface_name}.0")
    address = ipaddress.ip_interface(addresses[0])
    if address.version != 4:
        raise ValueError(f"Expected an IPv4 address on {interface_name}.0")
    return {"int": interface_name, "ip": str(address.ip), "mask": address.network.prefixlen}


def enrich_variables(project):
    metadata_path = project / "variable_metadata.yaml"
    metadata = load_mapping(metadata_path) if metadata_path.exists() else None
    shared_path = project / "group_vars" / "all.yaml"
    shared = load_mapping(shared_path)
    leaves = schema_leaves(project)
    presence_paths = {
        path for path, node in leaves.items()
        if node.get("leaf-type") == "empty" or node.get("base-type") == "empty"
    }
    hints_path = project / "configs" / "empty_leaf_paths.json"
    if hints_path.exists():
        hints = json.loads(hints_path.read_text(encoding="utf-8"))
        if not isinstance(hints, list) or any(not isinstance(path, str) or path not in leaves for path in hints):
            raise ValueError("Invalid XML presence flag paths")
        presence_paths.update(hints)
    variable_paths = sorted(
        path for directory in ("group_vars", "host_vars")
        for path in (project / directory).rglob("*")
        if path.is_file() and path.suffix in {".yaml", ".yml"}
        and path.name not in {"registry.yaml", "env.yaml"}
    )
    updates = {
        path: restore_presence_flags(load_mapping(path), presence_paths, str(path))
        for path in variable_paths
    }
    shared = updates[shared_path]
    if metadata is not None:
        connection = metadata["connection"]
        required = {"netconf_user", "netconf_passwd", "netconf_port"}
        if set(connection) != required:
            raise ValueError(f"connection must contain exactly {sorted(required)}")
        port = connection["netconf_port"]
        if type(port) is not int or not 1 <= port <= 65535:
            raise ValueError("netconf_port must be an integer between 1 and 65535")
        if not all(isinstance(connection[key], str) for key in ("netconf_user", "netconf_passwd")):
            raise ValueError("netconf_user and netconf_passwd must be strings")
        updates[shared_path] = {**shared, **connection}

    host_paths = sorted(
        path for path in (project / "host_vars").iterdir()
        if path.is_file() and path.suffix in {".yaml", ".yml"}
    )
    for path in host_paths:
        host = updates[path]
        host_metadata = metadata["hosts"].get(path.stem, {}) if metadata is not None else {}
        summary = {}
        if metadata is not None:
            summary = {
                "OS_version": host_metadata.get("OS_version") or host.get("version") or shared.get("version"),
                "leaf_type": host_metadata.get("leaf_type"),
                "loopback_ip": host_metadata.get("loopback_ip") or primary_loopback(host) or primary_loopback(shared),
            }
            if any(value is None or value == "" for value in summary.values()):
                raise ValueError(f"Missing host summary values for {path.stem}: {summary}")
        try:
            interface_name = host_metadata.get("management_interface", {}).get("int", "em0")
            if not isinstance(interface_name, str) or not interface_name:
                raise ValueError("management_interface.int must be a nonempty string")
            management = management_interface(host, interface_name)
            if management is None:
                management = management_interface(shared, interface_name)
            if management is None:
                raise ValueError(f"Missing IPv4 management address on {interface_name}.0")
        except ValueError as error:
            raise ValueError(f"{path.stem}: {error}") from error
        summary["management_interface"] = management
        updates[path] = {**host, **summary}

    for path, payload in updates.items():
        if payload != load_mapping(path):
            path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Restore project metadata after JTAF variable generation")
    parser.add_argument("project", type=Path)
    parser.add_argument("--record-empty-leaves", nargs="+", metavar="XML")
    args = parser.parse_args()
    try:
        if args.record_empty_leaves:
            record_empty_leaves(args.project, args.record_empty_leaves)
        else:
            enrich_variables(args.project)
    except (KeyError, ValueError, OSError, yaml.YAMLError, ElementTree.ParseError) as error:
        parser.exit(1, f"Variable enrichment failed: {error}\n")


if __name__ == "__main__":
    main()