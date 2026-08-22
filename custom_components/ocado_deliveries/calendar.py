"""Calendar platform for Ocado Deliveries."""

from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from . import OcadoConfigEntry
from .entity import OcadoEntity
from .models import OcadoOrder

_DEADLINE_EVENT_DURATION = timedelta(minutes=1)


def _format_currency(amount: float | None, currency: str | None) -> str | None:
    if amount is None:
        return None
    if currency == "GBP":
        return f"£{amount:.2f}"
    return f"{amount:.2f} {currency}" if currency else f"{amount:.2f}"


def _format_datetime(value: datetime, time_zone: str | None) -> str:
    """Format a timestamp in the delivery time zone where possible."""
    display = value
    if time_zone:
        try:
            display = value.astimezone(ZoneInfo(time_zone))
        except ZoneInfoNotFoundError:
            pass
    return display.strftime("%a %d %b %Y, %H:%M")


def _format_slot(order: OcadoOrder) -> str:
    start = _format_datetime(order.start, order.time_zone)
    end = order.end
    if order.time_zone:
        try:
            end = order.end.astimezone(ZoneInfo(order.time_zone))
        except ZoneInfoNotFoundError:
            pass
    return f"{start}–{end.strftime('%H:%M')}"


def _delivery_event_from_order(order: OcadoOrder) -> CalendarEvent:
    lines: list[str] = []
    if order.status:
        lines.append(f"Status: {order.status}")
    total = _format_currency(order.total_amount, order.currency)
    if total:
        lines.append(f"Order total: {total}")
    if order.edit_deadline:
        lines.append(
            "Edit deadline: "
            + _format_datetime(order.edit_deadline, order.time_zone)
        )
    if order.recurring_name:
        lines.append(f"Recurring order: {order.recurring_name}")
    if order.tracking_status:
        lines.append(f"Tracking: {order.tracking_status}")
    if order.eta_time:
        lines.append(f"ETA: {_format_datetime(order.eta_time, order.time_zone)}")
    elif order.eta_from and order.eta_to:
        eta_from = _format_datetime(order.eta_from, order.time_zone)
        eta_to = order.eta_to
        if order.time_zone:
            try:
                eta_to = order.eta_to.astimezone(ZoneInfo(order.time_zone))
            except ZoneInfoNotFoundError:
                pass
        lines.append(f"ETA window: {eta_from}–{eta_to.strftime('%H:%M')}")

    return CalendarEvent(
        start=order.start,
        end=order.end,
        summary="Ocado delivery",
        description="\n".join(lines) or None,
        location=order.destination_name,
        uid=f"ocado-delivery-{order.order_id}" if order.order_id else None,
    )


def _edit_deadline_event_from_order(order: OcadoOrder) -> CalendarEvent | None:
    deadline = order.edit_deadline
    if deadline is None:
        return None

    lines = [f"Delivery: {_format_slot(order)}"]
    if order.status:
        lines.append(f"Status: {order.status}")
    total = _format_currency(order.total_amount, order.currency)
    if total:
        lines.append(f"Order total: {total}")

    return CalendarEvent(
        start=deadline,
        end=deadline + _DEADLINE_EVENT_DURATION,
        summary="Ocado edit deadline",
        description="\n".join(lines),
        uid=f"ocado-edit-deadline-{order.order_id}" if order.order_id else None,
    )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: OcadoConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Ocado calendars."""
    async_add_entities(
        [
            OcadoDeliveryCalendar(entry),
            OcadoEditDeadlineCalendar(entry),
        ]
    )


class OcadoDeliveryCalendar(OcadoEntity, CalendarEntity):
    """Calendar of upcoming Ocado delivery slots."""

    _attr_translation_key = "deliveries"

    def __init__(self, entry: OcadoConfigEntry) -> None:
        super().__init__(entry)
        self._attr_unique_id = f"{entry.entry_id}_deliveries"

    @property
    def event(self) -> CalendarEvent | None:
        """Return the current or next upcoming delivery."""
        now = dt_util.now()
        for order in self.coordinator.data or []:
            if order.end >= now:
                return _delivery_event_from_order(order)
        return None

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: datetime,
        end_date: datetime,
    ) -> list[CalendarEvent]:
        """Return delivery events overlapping the requested range."""
        return [
            _delivery_event_from_order(order)
            for order in self.coordinator.data or []
            if order.end > start_date and order.start < end_date
        ]


class OcadoEditDeadlineCalendar(OcadoEntity, CalendarEntity):
    """Calendar of upcoming Ocado order edit deadlines."""

    _attr_translation_key = "edit_deadlines"

    def __init__(self, entry: OcadoConfigEntry) -> None:
        super().__init__(entry)
        self._attr_unique_id = f"{entry.entry_id}_edit_deadlines"

    @property
    def event(self) -> CalendarEvent | None:
        """Return the current or next edit deadline."""
        now = dt_util.now()
        deadlines = sorted(
            (
                order
                for order in self.coordinator.data or []
                if order.edit_deadline is not None
                and order.edit_deadline + _DEADLINE_EVENT_DURATION >= now
            ),
            key=lambda order: order.edit_deadline,
        )
        if not deadlines:
            return None
        return _edit_deadline_event_from_order(deadlines[0])

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: datetime,
        end_date: datetime,
    ) -> list[CalendarEvent]:
        """Return edit-deadline events in the requested range."""
        events: list[CalendarEvent] = []
        orders = sorted(
            (order for order in self.coordinator.data or [] if order.edit_deadline),
            key=lambda order: order.edit_deadline,
        )
        for order in orders:
            deadline = order.edit_deadline
            if deadline is None:
                continue
            event_end = deadline + _DEADLINE_EVENT_DURATION
            if event_end <= start_date or deadline >= end_date:
                continue
            event = _edit_deadline_event_from_order(order)
            if event is not None:
                events.append(event)
        return events
