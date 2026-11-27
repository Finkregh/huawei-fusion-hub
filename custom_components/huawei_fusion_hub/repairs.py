"""Repair flow: enable the source entities the hub cannot read.

The issue exists because a registry entry that is disabled never gets a state, so
the hub discovers it as a candidate and can never resolve a value from it. Telling
the user is only half of a fix, so the issue is fixable: this flow enables the
entities through the entity registry, the same way the UI switch does. Enabling is
a registry write with the user's explicit confirmation, not a side effect.
"""

from __future__ import annotations

import voluptuous as vol
from homeassistant import data_entry_flow
from homeassistant.components.repairs import ConfirmRepairFlow, RepairsFlow
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .const import ISSUE_DISABLED_SOURCE_ENTITIES

MODE_ALL = "all"
MODE_CRITICAL = "critical"


class EnableDisabledEntitiesFlow(RepairsFlow):
    """Enable the disabled source entities, all of them or only the critical ones."""

    def __init__(self, data: dict[str, str]) -> None:
        self._all = _split(data.get("entities"))
        self._critical = _split(data.get("critical_entities"))
        self._selected: list[str] = []

    async def async_step_init(
        self, user_input: dict[str, str] | None = None
    ) -> data_entry_flow.FlowResult:
        """Ask which set to enable."""
        if user_input is not None:
            mode = user_input.get("mode", MODE_CRITICAL)
            self._selected = self._critical if mode == MODE_CRITICAL else self._all
            return await self.async_step_confirm()

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required("mode", default=MODE_CRITICAL): SelectSelector(
                        SelectSelectorConfig(
                            options=[MODE_CRITICAL, MODE_ALL],
                            translation_key="mode",
                            mode=SelectSelectorMode.LIST,
                        )
                    )
                }
            ),
            description_placeholders={
                "count": str(len(self._all)),
                "critical": str(len(self._critical)),
            },
        )

    async def async_step_confirm(
        self, user_input: dict[str, str] | None = None
    ) -> data_entry_flow.FlowResult:
        """Enable the selected entities."""
        if user_input is not None:
            registry = er.async_get(self.hass)
            for entity_id in self._selected:
                entry = registry.async_get(entity_id)
                if entry is not None and entry.disabled_by is not None:
                    registry.async_update_entity(entity_id, disabled_by=None)
            return self.async_create_entry(data={})

        return self.async_show_form(
            step_id="confirm",
            data_schema=vol.Schema({}),
            description_placeholders={
                "count": str(len(self._selected)),
                "entities": "\n".join(
                    f"- `{entity_id}`" for entity_id in self._selected
                ),
            },
        )


def _split(value: str | None) -> list[str]:
    if not value:
        return []
    return [line.strip() for line in value.splitlines() if line.strip()]


async def async_create_fix_flow(
    hass: HomeAssistant,
    issue_id: str,
    data: dict[str, str | int | float | None] | None,
) -> RepairsFlow:
    """Return the flow for an issue of this integration."""
    if issue_id == ISSUE_DISABLED_SOURCE_ENTITIES:
        return EnableDisabledEntitiesFlow(
            {key: str(value) for key, value in (data or {}).items()}
        )
    return ConfirmRepairFlow()
