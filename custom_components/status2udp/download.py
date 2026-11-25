"""HTTP view that serves the Loxone import template (VIU_*.xml)."""

from __future__ import annotations

from datetime import timedelta
from http import HTTPStatus

from aiohttp import web

from homeassistant.components.http import KEY_HASS, HomeAssistantView
from homeassistant.components.http.auth import async_sign_path
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_UNIT_OF_MEASUREMENT, CONF_NAME, CONF_PORT
from homeassistant.core import HomeAssistant, callback

from .const import (
    CONF_ENTITIES,
    CONF_PREFIX,
    DEFAULT_NAME,
    DEFAULT_PORT,
    DEFAULT_PREFIX,
    DOMAIN,
    TEMPLATE_URL,
)
from .loxone import TemplateItem, build_viu_xml, template_filename
from .values import is_digital


@callback
def build_template_for_entry(hass: HomeAssistant, entry: ConfigEntry) -> tuple[str, bytes]:
    """Return (filename, xml) for a config entry."""
    options = entry.options
    title = options.get(CONF_NAME) or entry.title or DEFAULT_NAME
    items: list[TemplateItem] = []
    for entity_id in options.get(CONF_ENTITIES, []):
        state = hass.states.get(entity_id)
        name = state.name if state is not None else entity_id
        unit = state.attributes.get(ATTR_UNIT_OF_MEASUREMENT) if state is not None else None
        items.append(
            TemplateItem(
                entity_id=entity_id,
                name=str(name),
                digital=is_digital(entity_id, state.state if state else None),
                unit=str(unit) if unit else None,
            )
        )
    xml = build_viu_xml(
        title=title,
        port=int(options.get(CONF_PORT, DEFAULT_PORT)),
        prefix=options.get(CONF_PREFIX, DEFAULT_PREFIX),
        items=items,
    )
    return template_filename(title), xml


@callback
def async_signed_template_url(hass: HomeAssistant, entry_id: str) -> str:
    """Return a temporary, pre-authenticated download path."""
    return async_sign_path(
        hass, TEMPLATE_URL.format(entry_id=entry_id), timedelta(minutes=30)
    )


class LoxoneTemplateView(HomeAssistantView):
    """Download of the Loxone 'Virtueller UDP Eingang' template."""

    url = "/api/status2udp/{entry_id}/loxone_template.xml"
    name = "api:status2udp:loxone_template"
    requires_auth = True

    async def get(self, request: web.Request, entry_id: str) -> web.Response:
        """Return the XML as file download."""
        hass = request.app[KEY_HASS]
        entry = hass.config_entries.async_get_entry(entry_id)
        if entry is None or entry.domain != DOMAIN:
            return self.json_message("Config entry not found", HTTPStatus.NOT_FOUND)
        filename, xml = build_template_for_entry(hass, entry)
        return web.Response(
            body=xml,
            content_type="application/xml",
            charset="utf-8",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
