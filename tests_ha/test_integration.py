"""End-to-end tests: config flow, UDP sending, options, template download."""

import asyncio
import xml.etree.ElementTree as ET

import pytest

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.setup import async_setup_component

DOMAIN = "status2udp"


class Receiver(asyncio.DatagramProtocol):
    def __init__(self):
        self.queue: asyncio.Queue[bytes] = asyncio.Queue()

    def datagram_received(self, data, addr):
        self.queue.put_nowait(data)


@pytest.fixture
async def receiver():
    loop = asyncio.get_running_loop()
    transport, proto = await loop.create_datagram_endpoint(
        Receiver, local_addr=("127.0.0.1", 0)
    )
    proto.port = transport.get_extra_info("sockname")[1]
    yield proto
    transport.close()


async def _drain(proto, timeout=0.5):
    out = []
    try:
        while True:
            out.append(await asyncio.wait_for(proto.queue.get(), timeout))
    except TimeoutError:
        return out


async def _setup(hass: HomeAssistant, port: int):
    hass.states.async_set("sensor.temp", "21.5", {"unit_of_measurement": "°C", "friendly_name": "Temp"})
    hass.states.async_set("binary_sensor.door", "off", {"friendly_name": "Tür"})
    assert await async_setup_component(hass, "http", {})

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM and result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"entities": []}
    )
    assert result["errors"] == {"entities": "no_entities"}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"entities": ["sensor.temp", "binary_sensor.door"]}
    )
    assert result["step_id"] == "miniserver"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"name": "Mein HA", "host": "127.0.0.1", "port": port, "prefix": "ha/", "refresh_interval": 0},
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY, result
    await hass.async_block_till_done()
    return result["result"]


async def test_flow_and_sending(hass: HomeAssistant, receiver) -> None:
    entry = await _setup(hass, receiver.port)
    assert entry.state is config_entries.ConfigEntryState.LOADED
    assert entry.title == "Mein HA"

    initial = await _drain(receiver)
    assert sorted(initial) == [b"ha/binary_sensor.door=0", b"ha/sensor.temp=21.5"]

    hass.states.async_set("binary_sensor.door", "on")
    hass.states.async_set("sensor.temp", "21.5", {"unit_of_measurement": "°C", "x": 1})  # attr only
    hass.states.async_set("sensor.temp", "unavailable")
    hass.states.async_set("sensor.temp", "22")
    hass.states.async_set("sensor.other", "5")  # not selected
    await hass.async_block_till_done()
    assert await _drain(receiver) == [b"ha/binary_sensor.door=1", b"ha/sensor.temp=22"]


async def test_duplicate_aborts_with_error(hass: HomeAssistant, receiver) -> None:
    await _setup(hass, receiver.port)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"entities": ["sensor.temp"]}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"name": "x", "host": "127.0.0.1", "port": receiver.port, "prefix": "", "refresh_interval": 0},
    )
    assert result["errors"] == {"base": "already_configured"}


async def test_options_entities(hass: HomeAssistant, receiver) -> None:
    entry = await _setup(hass, receiver.port)
    await _drain(receiver)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.MENU
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "entities"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"entities": ["sensor.temp"]}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert entry.options["entities"] == ["sensor.temp"]
    assert entry.options["host"] == "127.0.0.1"

    await _drain(receiver)  # resend after reload
    hass.states.async_set("binary_sensor.door", "on")
    hass.states.async_set("sensor.temp", "23")
    await hass.async_block_till_done()
    assert await _drain(receiver) == [b"ha/sensor.temp=23"]


async def test_template_download(hass: HomeAssistant, hass_client_no_auth, receiver) -> None:
    entry = await _setup(hass, receiver.port)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "loxone_template"}
    )
    assert result["step_id"] == "loxone_template"
    url = result["description_placeholders"]["url"]
    assert "authSig=" in url

    client = await hass_client_no_auth()
    unsigned = await client.get(url.split("?")[0])
    assert unsigned.status == 401

    resp = await client.get(url)
    assert resp.status == 200
    assert 'filename="VIU_Mein_HA.xml"' in resp.headers["Content-Disposition"]
    root = ET.fromstring(await resp.read())
    assert root.get("Title") == "Mein HA"
    assert root.get("Port") == str(receiver.port)
    checks = {c.get("Check"): c.get("Analog") for c in root}
    assert checks == {r"ha/sensor.temp=\v": "true", r"ha/binary_sensor.door=\v": "false"}

    result = await hass.config_entries.options.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.CREATE_ENTRY
