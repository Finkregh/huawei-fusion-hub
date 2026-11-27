"""Disabled source entities: a candidate with no registry state is no candidate.

A registry entry with `disabled_by` set never gets an entity object, so the hub
can discover it by unique_id and resolve it as a candidate forever while never
being able to read a value from it. On a real EMMA install 117 of 172
huawei_solar entities are disabled by the integration itself, and its
`/api/states` holds exactly the 55 enabled ids, so the distinction is not
academic: it decides whether a hub key has a working fallback at all.
"""
import logging
import os
import sys
from types import SimpleNamespace

sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "custom_components")
)

import huawei_fusion_hub.coordinator as coordinator_module
from huawei_fusion_hub.const import (
    DOMAIN,
    ISSUE_DISABLED_SOURCE_ENTITIES,
    SOURCE_FUSION_SOLAR_PLUS,
    SOURCE_HUAWEI_SOLAR,
)
from huawei_fusion_hub.coordinator import disabled_candidate_report


def test_reports_only_the_disabled_candidates():
    candidates = {
        "grid_imported_energy": {
            SOURCE_HUAWEI_SOLAR: "sensor.emma_total_supply_from_grid",
            SOURCE_FUSION_SOLAR_PLUS: "sensor.fsp_ne_forward_active_energy",
        },
        "grid_exported_energy": {
            SOURCE_HUAWEI_SOLAR: "sensor.emma_total_feed_in_to_grid",
            SOURCE_FUSION_SOLAR_PLUS: "sensor.fsp_ne_reverse_active_energy",
        },
    }
    disabled_by = {
        "sensor.emma_total_supply_from_grid": None,
        "sensor.fsp_ne_forward_active_energy": None,
        "sensor.emma_total_feed_in_to_grid": None,
        "sensor.fsp_ne_reverse_active_energy": None,
    }

    assert disabled_candidate_report(candidates, disabled_by) == {}


def test_a_disabled_entity_is_reported_with_its_key_and_source():
    candidates = {
        "battery_rated_capacity": {
            SOURCE_HUAWEI_SOLAR: "sensor.emma_rated_ess_capacity",
        },
        "battery_soc": {SOURCE_HUAWEI_SOLAR: "sensor.emma_state_of_capacity"},
    }
    disabled_by = {
        "sensor.emma_rated_ess_capacity": "integration",
        "sensor.emma_state_of_capacity": None,
    }

    assert disabled_candidate_report(candidates, disabled_by) == {
        "battery_rated_capacity": {
            SOURCE_HUAWEI_SOLAR: "sensor.emma_rated_ess_capacity"
        }
    }


def test_real_emma_install_reports_the_four_disabled_mapping_entities():
    """The EMMA entity set from issue #14, with the four disabled ones.

    Everything else the mapping resolves there is enabled, so a report that
    lists more than these four would be a false alarm on a fresh install.
    """
    candidates = {
        "grid_imported_energy": {
            SOURCE_HUAWEI_SOLAR: "sensor.emma_total_positive_active_energy_2",
        },
        "grid_exported_energy": {
            SOURCE_HUAWEI_SOLAR: "sensor.emma_total_negative_active_energy_2",
        },
        "battery_rated_capacity": {
            SOURCE_HUAWEI_SOLAR: "sensor.emma_rated_ess_capacity",
        },
        "total_consumption": {
            SOURCE_HUAWEI_SOLAR: "sensor.emma_total_energy_consumption",
        },
        "battery_soc": {SOURCE_HUAWEI_SOLAR: "sensor.emma_state_of_capacity"},
        "pv_active_power": {SOURCE_HUAWEI_SOLAR: "sensor.emma_inverter_active_power"},
    }
    disabled_by = {
        "sensor.emma_total_positive_active_energy_2": "integration",
        "sensor.emma_total_negative_active_energy_2": "integration",
        "sensor.emma_rated_ess_capacity": "integration",
        "sensor.emma_total_energy_consumption": "integration",
        "sensor.emma_state_of_capacity": None,
        "sensor.emma_inverter_active_power": None,
    }

    report = disabled_candidate_report(candidates, disabled_by)

    assert set(report) == {
        "grid_imported_energy",
        "grid_exported_energy",
        "battery_rated_capacity",
        "total_consumption",
    }


def test_the_repair_issue_key_is_stable():
    # the translation key in strings.json/translations is keyed by this value
    assert ISSUE_DISABLED_SOURCE_ENTITIES == "disabled_source_entities"


class _RecordingIssueRegistry:
    """Stand-in for homeassistant.helpers.issue_registry."""

    IssueSeverity = SimpleNamespace(WARNING="warning")

    def __init__(self):
        self.created: list[dict] = []
        self.deleted: list[tuple[str, str]] = []

    def async_create_issue(self, hass, domain, issue_id, **kwargs):
        self.created.append(
            {"hass": hass, "domain": domain, "issue_id": issue_id, **kwargs}
        )

    def async_delete_issue(self, hass, domain, issue_id):
        self.deleted.append((domain, issue_id))


def _coordinator_with(disabled_candidates):
    """A coordinator with only what the reporting method touches."""
    coordinator = object.__new__(coordinator_module.HubCoordinator)
    coordinator.hass = SimpleNamespace()
    coordinator.disabled_candidates = disabled_candidates
    return coordinator


def _with_recording_registry(disabled_candidates):
    """Run the report against a recording issue registry, return (issue, records)."""
    original = coordinator_module.ir
    recorder = _RecordingIssueRegistry()
    coordinator_module.ir = recorder
    try:
        _coordinator_with(disabled_candidates)._report_disabled_candidates()
    finally:
        coordinator_module.ir = original
    return recorder


def test_repair_issue_names_each_disabled_entity_and_its_key():
    recorder = _with_recording_registry(
        {
            "battery_rated_capacity": {
                SOURCE_HUAWEI_SOLAR: "sensor.batteries_rated_capacity",
            },
            "total_consumption": {
                SOURCE_HUAWEI_SOLAR: "sensor.emma_total_energy_consumption",
            },
        }
    )

    assert len(recorder.created) == 1
    issue = recorder.created[0]
    assert issue["domain"] == DOMAIN
    assert issue["issue_id"] == ISSUE_DISABLED_SOURCE_ENTITIES
    assert issue["translation_key"] == ISSUE_DISABLED_SOURCE_ENTITIES
    assert issue["is_fixable"] is False
    assert issue["severity"] == "warning"
    assert issue["translation_placeholders"]["count"] == "2"
    body = issue["translation_placeholders"]["entities"]
    for expected in (
        "sensor.batteries_rated_capacity",
        "battery_rated_capacity",
        "sensor.emma_total_energy_consumption",
        "total_consumption",
        "Huawei Solar (Modbus)",
    ):
        assert expected in body, f"{expected!r} missing from the issue body"
    assert issue["learn_more_url"].endswith("#disabled-source-entities")
    assert recorder.deleted == []


def test_repair_issue_is_deleted_once_nothing_is_disabled():
    recorder = _with_recording_registry({})

    assert recorder.created == []
    assert recorder.deleted == [(DOMAIN, ISSUE_DISABLED_SOURCE_ENTITIES)]


def test_the_report_warns_in_the_log_as_well():
    records: list[logging.LogRecord] = []

    class _Capture(logging.Handler):
        def emit(self, record):
            records.append(record)

    handler = _Capture()
    coordinator_module._LOGGER.addHandler(handler)
    try:
        _with_recording_registry(
            {"battery_soc": {SOURCE_HUAWEI_SOLAR: "sensor.bma_state_of_capacity"}}
        )
    finally:
        coordinator_module._LOGGER.removeHandler(handler)

    assert len(records) == 1
    assert records[0].levelno == logging.WARNING
    message = records[0].getMessage()
    assert "sensor.bma_state_of_capacity" in message
    assert "battery_soc" in message


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
