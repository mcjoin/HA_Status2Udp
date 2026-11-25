"""Config and options flow for Status2UDP (Loxone)."""

from __future__ import annotations

import html
import socket
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import selector

from .const import (
    CONF_ENTITIES,
    CONF_PREFIX,
    CONF_REFRESH_INTERVAL,
    DEFAULT_NAME,
    DEFAULT_PORT,
    DEFAULT_PREFIX,
    DEFAULT_REFRESH_INTERVAL,
    DOMAIN,
)
from .download import async_signed_template_url
from .loxone import template_filename


def _entities_schema(default: list[str]) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_ENTITIES, default=default): selector.EntitySelector(
                selector.EntitySelectorConfig(multiple=True)
            )
        }
    )


def _miniserver_schema(defaults: dict[str, Any]) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(
                CONF_NAME, default=defaults.get(CONF_NAME, DEFAULT_NAME)
            ): selector.TextSelector(),
            vol.Required(CONF_HOST, default=defaults.get(CONF_HOST, "")): selector.TextSelector(),
            vol.Required(
                CONF_PORT, default=defaults.get(CONF_PORT, DEFAULT_PORT)
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=1, max=65535, step=1, mode=selector.NumberSelectorMode.BOX
                )
            ),
            vol.Optional(
                CONF_PREFIX, default=defaults.get(CONF_PREFIX, DEFAULT_PREFIX)
            ): selector.TextSelector(),
            vol.Required(
                CONF_REFRESH_INTERVAL,
                default=defaults.get(CONF_REFRESH_INTERVAL, DEFAULT_REFRESH_INTERVAL),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0,
                    max=86400,
                    step=1,
                    unit_of_measurement="s",
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
        }
    )


async def _async_validate_miniserver(
    hass: HomeAssistant,
    user_input: dict[str, Any],
    current_entry_id: str | None,
) -> tuple[dict[str, Any], dict[str, str]]:
    """Normalize Miniserver input; return (cleaned data, errors)."""
    errors: dict[str, str] = {}
    data = {
        CONF_NAME: str(user_input[CONF_NAME]).strip() or DEFAULT_NAME,
        CONF_HOST: str(user_input[CONF_HOST]).strip(),
        CONF_PORT: int(user_input[CONF_PORT]),
        CONF_PREFIX: str(user_input.get(CONF_PREFIX) or ""),
        CONF_REFRESH_INTERVAL: int(user_input[CONF_REFRESH_INTERVAL]),
    }

    if "\\" in data[CONF_PREFIX] or "=" in data[CONF_PREFIX]:
        errors[CONF_PREFIX] = "invalid_prefix"

    try:
        await hass.async_add_executor_job(
            socket.getaddrinfo, data[CONF_HOST], data[CONF_PORT], 0, socket.SOCK_DGRAM
        )
    except (OSError, UnicodeError):
        errors[CONF_HOST] = "cannot_resolve"

    for entry in hass.config_entries.async_entries(DOMAIN):
        if entry.entry_id == current_entry_id:
            continue
        if (
            entry.options.get(CONF_HOST) == data[CONF_HOST]
            and int(entry.options.get(CONF_PORT, DEFAULT_PORT)) == data[CONF_PORT]
        ):
            errors["base"] = "already_configured"

    return data, errors


class Status2UdpConfigFlow(ConfigFlow, domain=DOMAIN):
    """Initial setup: 1. entities, 2. Miniserver."""

    VERSION = 1

    def __init__(self) -> None:
        self._entities: list[str] = []

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 1: select entities."""
        errors: dict[str, str] = {}
        if user_input is not None:
            self._entities = list(user_input.get(CONF_ENTITIES) or [])
            if self._entities:
                return await self.async_step_miniserver()
            errors[CONF_ENTITIES] = "no_entities"
        return self.async_show_form(
            step_id="user", data_schema=_entities_schema(self._entities), errors=errors
        )

    async def async_step_miniserver(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 2: Loxone Miniserver settings."""
        errors: dict[str, str] = {}
        defaults: dict[str, Any] = {}
        if user_input is not None:
            data, errors = await _async_validate_miniserver(self.hass, user_input, None)
            if not errors:
                return self.async_create_entry(
                    title=data[CONF_NAME],
                    data={},
                    options={**data, CONF_ENTITIES: self._entities},
                )
            defaults = user_input
        return self.async_show_form(
            step_id="miniserver", data_schema=_miniserver_schema(defaults), errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Return the options flow."""
        return Status2UdpOptionsFlow()


class Status2UdpOptionsFlow(OptionsFlow):
    """Change entities / Miniserver later and download the Loxone template."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Menu."""
        return self.async_show_menu(
            step_id="init", menu_options=["entities", "miniserver", "loxone_template"]
        )

    async def async_step_entities(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Change the selected entities."""
        errors: dict[str, str] = {}
        current = list(self.config_entry.options.get(CONF_ENTITIES, []))
        if user_input is not None:
            entities = list(user_input.get(CONF_ENTITIES) or [])
            if entities:
                return self.async_create_entry(
                    data={**self.config_entry.options, CONF_ENTITIES: entities}
                )
            errors[CONF_ENTITIES] = "no_entities"
        return self.async_show_form(
            step_id="entities", data_schema=_entities_schema(current), errors=errors
        )

    async def async_step_miniserver(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Change the Miniserver settings."""
        errors: dict[str, str] = {}
        defaults: dict[str, Any] = dict(self.config_entry.options)
        if user_input is not None:
            data, errors = await _async_validate_miniserver(
                self.hass, user_input, self.config_entry.entry_id
            )
            if not errors:
                if data[CONF_NAME] != self.config_entry.title:
                    self.hass.config_entries.async_update_entry(
                        self.config_entry, title=data[CONF_NAME]
                    )
                return self.async_create_entry(data={**self.config_entry.options, **data})
            defaults = user_input
        return self.async_show_form(
            step_id="miniserver", data_schema=_miniserver_schema(defaults), errors=errors
        )

    async def async_step_loxone_template(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show a download link for the Loxone import template."""
        if user_input is not None:
            # Nothing changed -> no reload.
            return self.async_create_entry(data=dict(self.config_entry.options))
        options = self.config_entry.options
        url = async_signed_template_url(self.hass, self.config_entry.entry_id)
        filename = template_filename(options.get(CONF_NAME) or self.config_entry.title)
        # Plain HTML instead of a markdown link: the HA frontend routes clicks on
        # same-origin links inside the app (-> dashboard). Links with a target or
        # download attribute are left to the browser.
        link = f'<a href="{html.escape(url)}" target="_blank" download="{html.escape(filename)}">{html.escape(filename)}</a>'
        return self.async_show_form(
            step_id="loxone_template",
            data_schema=vol.Schema({}),
            description_placeholders={
                "url": url,
                "link": link,
                "count": str(len(options.get(CONF_ENTITIES, []))),
                "port": str(options.get(CONF_PORT, DEFAULT_PORT)),
            },
        )
