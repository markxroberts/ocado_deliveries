"""Shared entity helpers for Ocado Deliveries."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import OcadoConfigEntry
from .const import BASE_URL, DOMAIN
from .coordinator import OcadoCoordinator


class OcadoEntity(CoordinatorEntity[OcadoCoordinator]):
    """Base Ocado entity."""

    _attr_has_entity_name = True

    def __init__(self, entry: OcadoConfigEntry) -> None:
        super().__init__(entry.runtime_data.coordinator)
        self._entry = entry
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            manufacturer="Ocado Retail",
            model="Ocado.com account",
            name="Ocado",
            entry_type=DeviceEntryType.SERVICE,
            configuration_url=f"{BASE_URL}/orders",
        )
