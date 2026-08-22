"""Data models for Ocado Deliveries."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


def parse_datetime(value: str | None) -> datetime | None:
    """Parse an Ocado ISO timestamp."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


@dataclass(frozen=True, slots=True)
class OcadoOrder:
    """An upcoming Ocado order."""

    order_id: str
    status: str | None
    start: datetime
    end: datetime
    time_zone: str | None
    total_amount: float | None
    currency: str | None
    is_editable: bool
    edit_deadline: datetime | None
    delivery_method: str | None
    destination_name: str | None
    recurring_name: str | None
    tracking_status: str | None
    eta_status: str | None
    eta_time: datetime | None
    eta_from: datetime | None
    eta_to: datetime | None
