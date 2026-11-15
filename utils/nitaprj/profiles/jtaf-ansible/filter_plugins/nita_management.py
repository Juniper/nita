"""Reconcile existing management DHCP with generated static IPv4 addressing."""

from ipaddress import IPv4Interface
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


def _generated_management_inets(configuration, interface_name, unit_name):
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
    return [
        inet for scope in scopes
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


class FilterModule:
    def filters(self):
        return {
            "nita_management_addressing": nita_management_addressing,
            "nita_reconcile_management_dhcp": nita_reconcile_management_dhcp,
        }
