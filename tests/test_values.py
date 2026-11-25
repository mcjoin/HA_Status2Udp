import pytest

from status2udp_pure.values import build_message, is_digital, state_to_value


@pytest.mark.parametrize(
    ("state", "expected"),
    [
        ("on", "1"),
        ("off", "0"),
        ("ON", "1"),
        ("home", "1"),
        ("not_home", "0"),
        ("open", "1"),
        ("closed", "0"),
        ("21.5", "21.5"),
        ("21.50", "21.5"),
        ("100", "100"),
        ("100.0", "100"),
        ("-3.25", "-3.25"),
        ("-0.0", "0"),
        ("1234567.5", "1234567.5"),
        ("0.0000001", "0"),
        ("unavailable", None),
        ("unknown", None),
        ("heat", None),
        ("nan", None),
        ("inf", None),
        ("2026-11-25T10:00:00+00:00", None),
        (None, None),
    ],
)
def test_state_to_value(state, expected):
    assert state_to_value(state) == expected


def test_is_digital():
    assert is_digital("sensor.x", "on")
    assert not is_digital("sensor.x", "21.5")
    assert is_digital("binary_sensor.x", "unavailable")
    assert not is_digital("sensor.x", None)


def test_build_message():
    assert build_message("ha/", "sensor.t", "21.5") == b"ha/sensor.t=21.5"
