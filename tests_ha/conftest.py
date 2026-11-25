"""Fixtures for Home Assistant based tests."""

from pathlib import Path

import pytest

import custom_components  # the plugin's testing_config package, already imported

# Let the HA loader also find this repository's integrations.
_REPO_CC = str(Path(__file__).resolve().parents[1] / "custom_components")
if _REPO_CC not in custom_components.__path__:
    custom_components.__path__.append(_REPO_CC)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations, socket_enabled):
    """Enable loading custom_components/ and allow real (UDP) sockets."""
    yield
