"""Conversion of Home Assistant states into values Loxone understands.

This module has no Home Assistant imports so it can be unit tested on its own.
"""

from __future__ import annotations

import math

# States that are sent as 1 / 0 (digital inputs in Loxone).
TRUE_STATES = frozenset(
    {"on", "true", "home", "open", "locked", "detected", "playing", "active"}
)
FALSE_STATES = frozenset(
    {"off", "false", "not_home", "closed", "unlocked", "clear", "idle", "paused", "inactive"}
)

# States that are never sent (Loxone keeps the last value).
SKIP_STATES = frozenset({"unavailable", "unknown", "none", ""})

# Domains whose entities are digital (on/off) in Loxone.
DIGITAL_DOMAINS = frozenset(
    {
        "binary_sensor",
        "device_tracker",
        "fan",
        "input_boolean",
        "light",
        "lock",
        "person",
        "schedule",
        "siren",
        "switch",
    }
)


def format_number(value: float) -> str:
    """Format a number with a dot as decimal separator, without exponent."""
    if value.is_integer() and abs(value) < 1e15:
        return str(int(value))
    text = f"{value:.6f}".rstrip("0").rstrip(".")
    return "0" if text in ("-0", "") else text


def state_to_value(state: str | None) -> str | None:
    """Convert a HA state string to the value sent via UDP, or None to skip it."""
    if state is None:
        return None
    normalized = state.strip().lower()
    if normalized in SKIP_STATES:
        return None
    if normalized in TRUE_STATES:
        return "1"
    if normalized in FALSE_STATES:
        return "0"
    try:
        number = float(normalized)
    except ValueError:
        return None
    if not math.isfinite(number):
        return None
    return format_number(number)


def is_digital(entity_id: str, state: str | None) -> bool:
    """Decide whether an entity becomes a digital or analog input in Loxone."""
    if state is not None:
        normalized = state.strip().lower()
        if normalized in TRUE_STATES or normalized in FALSE_STATES:
            return True
        if normalized not in SKIP_STATES:
            return False
    return entity_id.split(".", 1)[0] in DIGITAL_DOMAINS


def build_message(prefix: str, entity_id: str, value: str) -> bytes:
    """Build the UDP payload, e.g. b'ha/sensor.temperature=21.5'."""
    return f"{prefix}{entity_id}={value}".encode()


def build_command_recognition(prefix: str, entity_id: str) -> str:
    """Loxone 'Befehlserkennung' matching build_message()."""
    return f"{prefix}{entity_id}=\\v"
