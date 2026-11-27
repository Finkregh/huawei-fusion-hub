"""Units, device classes and state classes, checked against Home Assistant itself.

The mapping decides what every hub entity looks like to the recorder, the Energy
dashboard and the frontend, and Home Assistant has its own tables for which unit
belongs to which device class and which state class a device class permits. A
typo here does not crash anything - the entity simply stops producing usable
statistics or renders as a string - so the tables are asserted rather than
reviewed.

The triples themselves are the audit result: power in W (HA's base unit, not
kW), energy in kWh, duration in minutes (allowed, and the value users read),
reactive energy in varh with `total_increasing`, signal strength in dBm, and
`energy_storage` carrying `measurement` because that is the only state class HA
permits for it.
"""
import os
import sys

sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "custom_components")
)

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.components.sensor.const import (
    DEVICE_CLASS_STATE_CLASSES,
    DEVICE_CLASS_UNITS,
)
from huawei_fusion_hub.mapping import SENSOR_DEFS

# kind -> (device_class, state_class, unit) after the audit
EXPECTED_KINDS = {
    "power": (SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT, "W"),
    "energy": (SensorDeviceClass.ENERGY, SensorStateClass.TOTAL_INCREASING, "kWh"),
    "energy_total": (SensorDeviceClass.ENERGY, SensorStateClass.TOTAL, "kWh"),
    "energy_storage": (
        SensorDeviceClass.ENERGY_STORAGE,
        SensorStateClass.MEASUREMENT,
        "kWh",
    ),
    "reactive_energy": (
        SensorDeviceClass.REACTIVE_ENERGY,
        SensorStateClass.TOTAL_INCREASING,
        "varh",
    ),
    "signal": (SensorDeviceClass.SIGNAL_STRENGTH, SensorStateClass.MEASUREMENT, "dBm"),
    "voltage": (SensorDeviceClass.VOLTAGE, SensorStateClass.MEASUREMENT, "V"),
    "current": (SensorDeviceClass.CURRENT, SensorStateClass.MEASUREMENT, "A"),
    "percent": (None, SensorStateClass.MEASUREMENT, "%"),
    "battery": (SensorDeviceClass.BATTERY, SensorStateClass.MEASUREMENT, "%"),
    "temp": (SensorDeviceClass.TEMPERATURE, SensorStateClass.MEASUREMENT, "°C"),
    "freq": (SensorDeviceClass.FREQUENCY, SensorStateClass.MEASUREMENT, "Hz"),
    "pf": (SensorDeviceClass.POWER_FACTOR, SensorStateClass.MEASUREMENT, None),
    "reactive": (SensorDeviceClass.REACTIVE_POWER, SensorStateClass.MEASUREMENT, "var"),
    "resistance": (None, SensorStateClass.MEASUREMENT, "MΩ"),
    "minutes": (SensorDeviceClass.DURATION, SensorStateClass.MEASUREMENT, "min"),
    "text": (None, None, None),
}


def _triple(entity_def):
    return (entity_def.device_class, entity_def.state_class, entity_def.unit)


def test_every_entity_uses_a_home_assistant_approved_unit():
    invalid = []
    for entity_def in SENSOR_DEFS:
        if entity_def.unit is None or entity_def.device_class is None:
            continue
        allowed = DEVICE_CLASS_UNITS.get(entity_def.device_class)
        if allowed is not None and entity_def.unit not in allowed:
            invalid.append(
                f"{entity_def.key}: {entity_def.unit!r} not in {sorted(allowed)}"
            )
    assert invalid == []


def test_every_entity_uses_a_state_class_its_device_class_allows():
    invalid = []
    for entity_def in SENSOR_DEFS:
        if entity_def.state_class is None or entity_def.device_class is None:
            continue
        allowed = DEVICE_CLASS_STATE_CLASSES.get(entity_def.device_class)
        if allowed is not None and entity_def.state_class not in allowed:
            invalid.append(
                f"{entity_def.key}: {entity_def.state_class!s} not in {sorted(allowed)}"
            )
    assert invalid == []


def test_energy_storage_entities_are_measurements():
    """HA permits only `measurement` for `energy_storage`; `None` silently did that."""
    for entity_def in SENSOR_DEFS:
        if entity_def.device_class is SensorDeviceClass.ENERGY_STORAGE:
            assert entity_def.state_class is SensorStateClass.MEASUREMENT, entity_def.key


def test_the_audited_triples_are_what_the_mapping_produces():
    seen = {_triple(entity_def) for entity_def in SENSOR_DEFS}
    expected = set(EXPECTED_KINDS.values())
    assert seen == expected, (
        f"unexpected triples: {sorted(map(str, seen - expected))}; "
        f"missing: {sorted(map(str, expected - seen))}"
    )


def test_numeric_values_are_not_published_as_text_sensors():
    """The three keys that used to be `text` carry numbers, not statuses."""
    by_key = {entity_def.key: entity_def for entity_def in SENSOR_DEFS}
    for key, device_class in (
        ("meter_reactive_energy", SensorDeviceClass.REACTIVE_ENERGY),
        ("meter_wifi_signal_strength", SensorDeviceClass.SIGNAL_STRENGTH),
        ("meter_signal_strength", SensorDeviceClass.SIGNAL_STRENGTH),
    ):
        assert by_key[key].device_class is device_class, key
        assert by_key[key].unit is not None, key
        assert by_key[key].state_class is not None, key


if __name__ == "__main__":
    import traceback

    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"PASS {t.__name__}")
        except Exception:
            print(f"FAIL {t.__name__}")
            traceback.print_exc()
            failed += 1
    sys.exit(1 if failed else 0)
