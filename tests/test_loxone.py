import xml.etree.ElementTree as ET

from status2udp_pure.loxone import TemplateItem, build_viu_xml, template_filename


def test_template_filename():
    assert template_filename("Home Assistant") == "VIU_Home_Assistant.xml"
    assert template_filename("Ä!") == "VIU_HomeAssistant.xml"


def test_build_viu_xml():
    xml = build_viu_xml(
        "HA",
        7000,
        "ha/",
        [
            TemplateItem("sensor.temp", "Temperatur <Außen>", False, "°C"),
            TemplateItem("binary_sensor.door", "Tür", True),
        ],
    )
    assert xml.startswith(b'<?xml version="1.0" encoding="utf-8"?>')
    root = ET.fromstring(xml)
    assert root.tag == "VirtualInUdp"
    assert root.get("Port") == "7000"
    analog, digital = root.findall("VirtualInUdpCmd")
    assert analog.get("Check") == r"ha/sensor.temp=\v"
    assert analog.get("Analog") == "true"
    assert analog.get("Unit") == "<v.1> °C"
    assert analog.get("Title") == "Temperatur <Außen>"
    assert digital.get("Check") == r"ha/binary_sensor.door=\v"
    assert digital.get("Analog") == "false"
