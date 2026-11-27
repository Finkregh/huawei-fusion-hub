"""Per-source availability binary sensors."""
from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DEVICE_HUB, DEVICE_NAMES, DOMAIN, ENTITY_PREFIX
from .coordinator import HuaweiFusionHubConfigEntry, HubCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: HuaweiFusionHubConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        SourceAvailabilitySensor(coordinator, source)
        for source in coordinator.priority
    )


class SourceAvailabilitySensor(CoordinatorEntity[HubCoordinator], BinarySensorEntity):
    _attr_has_entity_name = True
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: HubCoordinator, source: str) -> None:
        super().__init__(coordinator)
        self._source = source
        uid = f"{ENTITY_PREFIX}_{source}_available"
        self._attr_unique_id = uid
        self.entity_id = f"binary_sensor.{uid}"
        self._attr_translation_key = uid
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, DEVICE_HUB)},
            name=DEVICE_NAMES[DEVICE_HUB],
            manufacturer="giorgioparri",
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def is_on(self) -> bool | None:
        return self.coordinator.source_available.get(self._source)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "tracked_entities": sorted(
                self.coordinator.source_entities.get(self._source, [])
            )
        }
