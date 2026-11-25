"""Constants for the Status2UDP (Loxone) integration."""

from __future__ import annotations

DOMAIN = "status2udp"

CONF_ENTITIES = "entities"
CONF_PREFIX = "prefix"
CONF_REFRESH_INTERVAL = "refresh_interval"

DEFAULT_NAME = "Home Assistant"
DEFAULT_PORT = 7000
DEFAULT_PREFIX = "ha/"
DEFAULT_REFRESH_INTERVAL = 300  # seconds, 0 = disabled

# Pause between packets when sending many values at once (seconds).
BULK_SEND_DELAY = 0.01

TEMPLATE_URL = "/api/status2udp/{entry_id}/loxone_template.xml"
