"""Forwards state changes of selected entities via UDP to a Loxone Miniserver."""

from __future__ import annotations

import asyncio
from datetime import timedelta
import logging
from typing import Any

from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import Event, EventStateChangedData, HomeAssistant, callback
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_time_interval,
)
from homeassistant.helpers.start import async_at_started

from .const import (
    BULK_SEND_DELAY,
    CONF_ENTITIES,
    CONF_PREFIX,
    CONF_REFRESH_INTERVAL,
    DEFAULT_PORT,
    DEFAULT_PREFIX,
    DEFAULT_REFRESH_INTERVAL,
)
from .values import build_message, state_to_value

_LOGGER = logging.getLogger(__name__)


class _UdpProtocol(asyncio.DatagramProtocol):
    """Send-only protocol; only logs errors (e.g. ICMP port unreachable)."""

    def error_received(self, exc: Exception) -> None:
        _LOGGER.debug("UDP error: %s", exc)


class Status2UdpBridge:
    """Listens for state changes and sends them as UDP packets."""

    def __init__(self, hass: HomeAssistant, options: dict[str, Any]) -> None:
        self.hass = hass
        self.host: str = options[CONF_HOST]
        self.port: int = int(options.get(CONF_PORT, DEFAULT_PORT))
        self.prefix: str = options.get(CONF_PREFIX, DEFAULT_PREFIX)
        self.entities: list[str] = list(options.get(CONF_ENTITIES, []))
        self.refresh_interval = int(
            options.get(CONF_REFRESH_INTERVAL, DEFAULT_REFRESH_INTERVAL)
        )
        self._transport: asyncio.DatagramTransport | None = None
        self._unsubs: list[Any] = []

    async def async_start(self) -> None:
        """Open the socket and start listening. Raises OSError if host is invalid."""
        loop = asyncio.get_running_loop()
        self._transport, _ = await loop.create_datagram_endpoint(
            _UdpProtocol, remote_addr=(self.host, self.port)
        )

        if self.entities:
            self._unsubs.append(
                async_track_state_change_event(
                    self.hass, self.entities, self._async_state_changed
                )
            )
        if self.refresh_interval > 0:
            self._unsubs.append(
                async_track_time_interval(
                    self.hass,
                    self._async_send_all,
                    timedelta(seconds=self.refresh_interval),
                    name="status2udp refresh",
                )
            )
        # Send all current values once HA is up (immediately on reload).
        self._unsubs.append(async_at_started(self.hass, self._async_send_all))

    async def async_stop(self) -> None:
        """Stop listening and close the socket."""
        while self._unsubs:
            self._unsubs.pop()()
        if self._transport is not None:
            self._transport.close()
            self._transport = None

    @callback
    def _async_state_changed(self, event: Event[EventStateChangedData]) -> None:
        new_state = event.data["new_state"]
        if new_state is None:
            return
        value = state_to_value(new_state.state)
        if value is None:
            return
        old_state = event.data["old_state"]
        if old_state is not None and state_to_value(old_state.state) == value:
            return  # attribute-only change
        self._send(new_state.entity_id, value)

    async def _async_send_all(self, *_: Any) -> None:
        """Send the current value of every selected entity."""
        for entity_id in self.entities:
            state = self.hass.states.get(entity_id)
            if state is None:
                continue
            value = state_to_value(state.state)
            if value is None:
                continue
            self._send(entity_id, value)
            await asyncio.sleep(BULK_SEND_DELAY)

    @callback
    def _send(self, entity_id: str, value: str) -> None:
        if self._transport is None:
            return
        payload = build_message(self.prefix, entity_id, value)
        try:
            self._transport.sendto(payload)
        except OSError as err:
            _LOGGER.warning("Sending to %s:%s failed: %s", self.host, self.port, err)
            return
        _LOGGER.debug("Sent %s to %s:%s", payload, self.host, self.port)
