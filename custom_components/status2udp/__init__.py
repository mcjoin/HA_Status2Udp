"""Status2UDP: send Home Assistant states via UDP to a Loxone Miniserver."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .bridge import Status2UdpBridge
from .const import DOMAIN
from .download import LoxoneTemplateView

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

type Status2UdpConfigEntry = ConfigEntry[Status2UdpBridge]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register the template download view once."""
    hass.http.register_view(LoxoneTemplateView())
    return True


async def async_setup_entry(hass: HomeAssistant, entry: Status2UdpConfigEntry) -> bool:
    """Set up a Miniserver connection from a config entry."""
    bridge = Status2UdpBridge(hass, dict(entry.options))
    try:
        await bridge.async_start()
    except OSError as err:
        await bridge.async_stop()
        raise ConfigEntryNotReady(
            f"Cannot open UDP socket to {bridge.host}:{bridge.port}: {err}"
        ) from err

    entry.runtime_data = bridge
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: Status2UdpConfigEntry) -> bool:
    """Unload a config entry."""
    await entry.runtime_data.async_stop()
    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload when options (entities / Miniserver settings) change."""
    await hass.config_entries.async_reload(entry.entry_id)
