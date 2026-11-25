"""Generation of Loxone Config import templates (Virtual UDP Input, VIU_*.xml).

This module has no Home Assistant imports so it can be unit tested on its own.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
import xml.etree.ElementTree as ET

from .values import build_command_recognition


@dataclass(frozen=True)
class TemplateItem:
    """One virtual UDP input command."""

    entity_id: str
    name: str
    digital: bool
    unit: str | None = None


def template_filename(title: str) -> str:
    """File name Loxone Config expects for UDP input templates."""
    safe = re.sub(r"[^A-Za-z0-9_-]+", "_", title).strip("_") or "HomeAssistant"
    return f"VIU_{safe}.xml"


def build_viu_xml(title: str, port: int, prefix: str, items: list[TemplateItem]) -> bytes:
    """Build the XML of a Loxone 'Virtueller UDP Eingang' with one command per entity."""
    root = ET.Element(
        "VirtualInUdp",
        {"Title": title, "Comment": "Home Assistant Status2UDP", "Address": "", "Port": str(port)},
    )
    for item in items:
        if item.digital:
            unit = "<v>"
        else:
            unit = f"<v.1> {item.unit}".rstrip() if item.unit else "<v.1>"
        ET.SubElement(
            root,
            "VirtualInUdpCmd",
            {
                "Title": item.name,
                "Comment": item.entity_id,
                "Address": "",
                "Check": build_command_recognition(prefix, item.entity_id),
                "Signed": "true",
                "Analog": "false" if item.digital else "true",
                "SourceValLow": "0",
                "DestValLow": "0",
                "SourceValHigh": "100",
                "DestValHigh": "100",
                "DefVal": "0",
                "MinVal": "-2147483648",
                "MaxVal": "2147483647",
                "Unit": unit,
                "HintText": "",
            },
        )
    ET.indent(root, space="\t")
    body = ET.tostring(root, encoding="unicode")
    return ('<?xml version="1.0" encoding="utf-8"?>\n' + body + "\n").encode("utf-8")
