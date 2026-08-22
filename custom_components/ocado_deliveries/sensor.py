"""Sensor platform for Ocado Deliveries."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from . import OcadoConfigEntry
from .entity import OcadoEntity
from .models import OcadoOrder


def _next_order(orders: list[OcadoOrder]) -> OcadoOrder | None:
    now = dt_util.now()
    return next((order for order in orders if order.end >= now), None)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: OcadoConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Ocado sensors."""
    async_add_entities(
        [
            OcadoNextDeliverySensor(entry),
            OcadoNextEditDeadlineSensor(entry),
            OcadoUpcomingCountSensor(entry),
        ]
    )


class OcadoNextDeliverySensor(OcadoEntity, SensorEntity):
    """Timestamp of the next Ocado delivery."""

    _attr_translation_key = "next_delivery"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    # Explicit fallback for frontends that do not apply icons.json to timestamp sensors.
    _attr_icon = "mdi:truck-delivery-outline"

    def __init__(self, entry: OcadoConfigEntry) -> None:
        super().__init__(entry)
        self._attr_unique_id = f"{entry.entry_id}_next_delivery"

    @property
    def native_value(self) -> datetime | None:
        order = _next_order(self.coordinator.data or [])
        return order.start if order else None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        order = _next_order(self.coordinator.data or [])
        if not order:
            return None
        return {
            "end": order.end.isoformat(),
            "order_id": order.order_id,
            "status": order.status,
            "total": order.total_amount,
            "currency": order.currency,
            "editable": order.is_editable,
            "edit_deadline": order.edit_deadline.isoformat() if order.edit_deadline else None,
            "destination": order.destination_name,
            "delivery_method": order.delivery_method,
            "recurring_order": order.recurring_name,
            "tracking_status": order.tracking_status,
            "eta_status": order.eta_status,
            "eta": order.eta_time.isoformat() if order.eta_time else None,
            "eta_from": order.eta_from.isoformat() if order.eta_from else None,
            "eta_to": order.eta_to.isoformat() if order.eta_to else None,
        }


class OcadoNextEditDeadlineSensor(OcadoEntity, SensorEntity):
    """Next future edit deadline."""

    _attr_translation_key = "next_edit_deadline"
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, entry: OcadoConfigEntry) -> None:
        super().__init__(entry)
        self._attr_unique_id = f"{entry.entry_id}_next_edit_deadline"

    @property
    def native_value(self) -> datetime | None:
        now = dt_util.now()
        deadlines = sorted(
            order.edit_deadline
            for order in self.coordinator.data or []
            if order.edit_deadline is not None and order.edit_deadline >= now
        )
        return deadlines[0] if deadlines else None


class OcadoUpcomingCountSensor(OcadoEntity, SensorEntity):
    """Number of upcoming Ocado deliveries."""

    _attr_translation_key = "upcoming_deliveries"
    _attr_native_unit_of_measurement = "deliveries"

    def __init__(self, entry: OcadoConfigEntry) -> None:
        super().__init__(entry)
        self._attr_unique_id = f"{entry.entry_id}_upcoming_count"

    @property
    def native_value(self) -> int:
        now = dt_util.now()
        return sum(1 for order in self.coordinator.data or [] if order.end >= now)
