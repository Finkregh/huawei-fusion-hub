"""Disabled source entities: a candidate with no registry state is no candidate.

A registry entry with `disabled_by` set never gets an entity object, so the hub
can discover it by unique_id and resolve it as a candidate forever while never
being able to read a value from it. On a real EMMA install 117 of 172
huawei_solar entities are disabled by the integration itself, and its
`/api/states` holds exactly the 55 enabled ids, so the distinction is not
academic: it decides whether a hub key has a working fallback at all.
"""
import os
import sys

sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "custom_components")
)

from huawei_fusion_hub.const import (
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
