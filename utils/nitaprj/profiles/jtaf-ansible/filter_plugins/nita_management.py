"""Reconcile management DHCP and conflicting empty physical-interface units."""

from ipaddress import IPv4Interface
import re
import xml.etree.ElementTree as ET


def _configuration(xml, description):
    try:
        root = ET.fromstring(xml)
    except ET.ParseError as exc:
        raise ValueError(f"Invalid {description} XML: {exc}") from exc
    if root.tag.split("}")[-1] == "configuration":
        return root
    configurations = root.findall(".//{*}configuration")
    if len(configurations) != 1:
        raise ValueError(f"{description} XML must contain one configuration")
    return configurations[0]


def _child(parent, name):
    if parent is None:
        return None
    children = parent.findall(f"./{{*}}{name}")
    if len(children) > 1:
        raise ValueError(f"Ambiguous management configuration: multiple {name} elements")
    return children[0] if children else None


def _named_child(parent, tag, name):
    if parent is None:
        return None
    children = [
        child for child in parent.findall(f"./{{*}}{tag}")
        if child.findtext("./{*}name", "").strip() == name
    ]
    if len(children) > 1:
        raise ValueError(f"Ambiguous management configuration: multiple {tag} entries for {name}")
    return children[0] if children else None


def _enabled(element):
    return element is not None and not (
        "inactive" in element.attrib
        or "delete" in element.attrib
        or element.get("operation") in ("delete", "remove")
        or element.get("{urn:ietf:params:xml:ns:netconf:base:1.0}operation")
        in ("delete", "remove")
    )


def _management_inet(configuration, interface_name, unit_name):
    interfaces = _child(configuration, "interfaces")
    interface = _named_child(interfaces, "interface", interface_name)
    unit = _named_child(interface, "unit", unit_name)
    family = _child(unit, "family")
    inet = _child(family, "inet")
    if not all(_enabled(element) for element in (interfaces, interface, unit, family, inet)):
        return None
    return inet


def _generated_scopes(configuration):
    scopes = [configuration]
    excluded = {
        (element.text or "").strip()
        for element in configuration.findall("./{*}apply-groups-except")
        if _enabled(element)
    }
    applied = set()
    for element in configuration.findall("./{*}apply-groups"):
        if not _enabled(element):
            continue
        name = (element.text or "").strip()
        if not name:
            raise ValueError("Generated apply-groups must name a configuration group")
        if name in excluded or name in applied:
            continue
        applied.add(name)
        group = _named_child(configuration, "groups", name)
        if _enabled(group):
            scopes.append(group)
    return scopes


def _generated_management_inets(configuration, interface_name, unit_name):
    return [
        inet for scope in _generated_scopes(configuration)
        if (inet := _management_inet(scope, interface_name, unit_name)) is not None
    ]


def _ensure_child(parent, name):
    child = _child(parent, name)
    if child is None:
        namespace = parent.tag.rpartition("}")[0] + "}" if "}" in parent.tag else ""
        child = ET.SubElement(parent, namespace + name)
    return child


def _ensure_named_child(parent, tag, name):
    child = _named_child(parent, tag, name)
    if child is None:
        namespace = parent.tag.rpartition("}")[0] + "}" if "}" in parent.tag else ""
        child = ET.SubElement(parent, namespace + tag)
        ET.SubElement(child, namespace + "name").text = name
    return child


def nita_management_addressing(xml, management_interface):
    if not isinstance(management_interface, str) or not management_interface:
        raise ValueError("Management interface must be a name, for example em0 or em0.0")
    if "." in management_interface:
        interface_name, unit_name = management_interface.rsplit(".", 1)
    else:
        interface_name, unit_name = management_interface, "0"
    if not interface_name or not unit_name.isdecimal():
        raise ValueError("Management interface must include a numeric unit")
    configuration = _configuration(xml, "generated")
    inets = _generated_management_inets(configuration, interface_name, unit_name)
    addresses = []
    for inet in inets:
        for address in inet.findall("./{*}address"):
            if _enabled(address):
                name = address.findtext("./{*}name")
                try:
                    addresses.append(str(IPv4Interface(name)))
                except (ValueError, TypeError) as exc:
                    raise ValueError(f"Invalid static IPv4 address on {management_interface}") from exc
    if addresses and any(_enabled(_child(inet, "dhcp")) for inet in inets):
        raise ValueError(
            f"Generated {management_interface} enables both DHCP and static IPv4; "
            "remove DHCP from the project variables"
        )

    query = ET.Element("configuration")
    interface = ET.SubElement(ET.SubElement(query, "interfaces"), "interface")
    ET.SubElement(interface, "name").text = interface_name
    unit = ET.SubElement(interface, "unit")
    ET.SubElement(unit, "name").text = unit_name
    ET.SubElement(ET.SubElement(ET.SubElement(unit, "family"), "inet"), "dhcp")
    return {
        "has_static_ipv4": bool(addresses),
        "interface": interface_name,
        "unit": unit_name,
        "filter": ET.tostring(query, encoding="unicode"),
    }


def nita_reconcile_management_dhcp(xml, current_xml, management_interface):
    addressing = nita_management_addressing(xml, management_interface)
    if not addressing["has_static_ipv4"]:
        return xml
    current = _configuration(current_xml, "retrieved")
    current_inet = _management_inet(current, addressing["interface"], addressing["unit"])
    if not _enabled(_child(current_inet, "dhcp")):
        return xml
    generated = _configuration(xml, "generated")
    inet = _management_inet(generated, addressing["interface"], addressing["unit"])
    if _child(inet, "dhcp") is not None:
        return xml
    if inet is None:
        interfaces = _ensure_child(generated, "interfaces")
        interface = _ensure_named_child(interfaces, "interface", addressing["interface"])
        unit = _ensure_named_child(interface, "unit", addressing["unit"])
        inet = _ensure_child(_ensure_child(unit, "family"), "inet")
    namespace = inet.tag.rpartition("}")[0] + "}" if "}" in inet.tag else ""
    ET.SubElement(inet, namespace + "dhcp", {"delete": "delete"})
    return ET.tostring(generated, encoding="unicode")


def _has_vlan_id(unit):
    vlan_id = _child(unit, "vlan-id")
    vlan_tags = _child(unit, "vlan-tags")
    return (
        _enabled(vlan_id) and bool((vlan_id.text or "").strip())
        or _enabled(vlan_tags) and bool(len(vlan_tags))
    )


def _physical_unit_targets(configuration):
    ports = {}
    for scope in _generated_scopes(configuration):
        interfaces = _child(scope, "interfaces")
        if not _enabled(interfaces):
            continue
        for interface in interfaces.findall("./{*}interface"):
            if not _enabled(interface):
                continue
            name = interface.findtext("./{*}name", "").strip()
            aggregate = any(
                _enabled(options) and _enabled(_child(options, "ieee-802.3ad"))
                for options in (_child(interface, "ether-options"), _child(interface, "gigether-options"))
            )
            tagged = any(_enabled(_child(interface, tag))
                         for tag in ("vlan-tagging", "flexible-vlan-tagging"))
            if not re.fullmatch(r"(?:xe|ge|et)-\d+/\d+/\d+(?::\d+)?", name):
                if name.startswith(("xe-", "ge-", "et-")) and (aggregate or tagged):
                    raise ValueError(f"Interface cleanup requires an explicit physical port: {name}")
                continue
            port = ports.setdefault(name, {
                "aggregate": False, "tagged": False, "units": set(), "tagged_units": set(),
            })
            port["aggregate"] |= aggregate
            port["tagged"] |= tagged
            for unit in interface.findall("./{*}unit"):
                if not _enabled(unit):
                    continue
                unit_name = unit.findtext("./{*}name", "").strip()
                if not unit_name.isdecimal():
                    raise ValueError(f"Invalid generated logical unit on {name}")
                port["units"].add(unit_name)
                if _has_vlan_id(unit):
                    port["tagged_units"].add(unit_name)
    targets = {}
    for name, port in ports.items():
        if port["aggregate"] and (port["units"] or port["tagged"]):
            raise ValueError(f"Generated aggregate member {name} must not have logical units or VLAN tagging")
        if port["tagged"] and port["units"] - port["tagged_units"]:
            raise ValueError(f"Generated tagged interface {name} has a logical unit without a VLAN ID")
        if port["aggregate"] or port["tagged"]:
            targets[name] = port
    return targets


def nita_interface_unit_cleanup(xml):
    targets = _physical_unit_targets(_configuration(xml, "generated"))
    query = ET.Element("configuration")
    interfaces = ET.SubElement(query, "interfaces")
    for name in targets:
        interface = ET.SubElement(interfaces, "interface")
        ET.SubElement(interface, "name").text = name
        ET.SubElement(interface, "unit")
    return {"has_targets": bool(targets), "filter": ET.tostring(query, encoding="unicode")}


def nita_reconcile_empty_interface_units(xml, current_xml):
    generated = _configuration(xml, "generated")
    targets = _physical_unit_targets(generated)
    if not targets:
        return xml
    current = _configuration(current_xml, "retrieved")
    current_interfaces = _child(current, "interfaces")
    if not _enabled(current_interfaces):
        return xml
    changed = False
    for name, port in targets.items():
        current_interface = _named_child(current_interfaces, "interface", name)
        if not _enabled(current_interface):
            continue
        for unit in current_interface.findall("./{*}unit"):
            if not _enabled(unit):
                continue
            unit_name = unit.findtext("./{*}name", "").strip()
            if not unit_name.isdecimal():
                raise ValueError(f"Invalid retrieved logical unit on {name}")
            _named_child(current_interface, "unit", unit_name)
            if not port["aggregate"] and (unit_name in port["units"] or _has_vlan_id(unit)):
                continue
            if unit.attrib or len(unit) != 1 or _child(unit, "name") is None:
                raise ValueError(f"Refusing to delete non-empty {name} unit {unit_name}; review it manually")
            interface = _ensure_named_child(_ensure_child(generated, "interfaces"), "interface", name)
            existing = _named_child(interface, "unit", unit_name)
            if existing is not None:
                if "delete" in existing.attrib or existing.get("operation") in ("delete", "remove"):
                    continue
                raise ValueError(f"Generated {name} unit {unit_name} conflicts with empty-unit cleanup")
            namespace = interface.tag.rpartition("}")[0] + "}" if "}" in interface.tag else ""
            deletion = ET.SubElement(interface, namespace + "unit", {"delete": "delete"})
            ET.SubElement(deletion, namespace + "name").text = unit_name
            changed = True
    return ET.tostring(generated, encoding="unicode") if changed else xml


class FilterModule:
    def filters(self):
        return {
            "nita_management_addressing": nita_management_addressing,
            "nita_reconcile_management_dhcp": nita_reconcile_management_dhcp,
            "nita_interface_unit_cleanup": nita_interface_unit_cleanup,
            "nita_reconcile_empty_interface_units": nita_reconcile_empty_interface_units,
        }
