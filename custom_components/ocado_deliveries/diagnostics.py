"""Diagnostics support for Ocado Deliveries."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from . import OcadoConfigEntry
from .const import CONF_COOKIE

_TO_REDACT = {CONF_COOKIE}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: OcadoConfigEntry
) -> dict[str, Any]:
    """Return privacy-safe diagnostics for an Ocado config entry."""
    coordinator = entry.runtime_data.coordinator
    orders = coordinator.data or []

    # Deliberately omit order identifiers, amounts, addresses/destinations,
    # dates/times, recurring-order names and all authentication material.
    safe_orders = [
        {
            "status": order.status,
            "delivery_method": order.delivery_method,
            "is_editable": order.is_editable,
            "has_edit_deadline": order.edit_deadline is not None,
            "has_tracking": order.tracking_status is not None,
            "has_eta": any((order.eta_time, order.eta_from, order.eta_to)),
            "is_recurring": order.recurring_name is not None,
        }
        for order in orders
    ]

    return {
        "entry": {
            "title": entry.title,
            "data": async_redact_data(dict(entry.data), _TO_REDACT),
        },
        "coordinator": {
            "last_update_success": coordinator.last_update_success,
            "order_count": len(orders),
            "orders": safe_orders,
        },
    }
