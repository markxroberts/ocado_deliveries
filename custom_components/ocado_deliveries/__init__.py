"""Ocado Deliveries integration."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import OcadoApi
from .const import CONF_COOKIE
from .coordinator import OcadoCoordinator

PLATFORMS: list[Platform] = [Platform.CALENDAR, Platform.SENSOR]


@dataclass(slots=True)
class OcadoRuntimeData:
    """Runtime data for an Ocado config entry."""

    api: OcadoApi
    coordinator: OcadoCoordinator


OcadoConfigEntry = ConfigEntry[OcadoRuntimeData]


async def async_setup_entry(hass: HomeAssistant, entry: OcadoConfigEntry) -> bool:
    """Set up Ocado Deliveries from a config entry."""
    api = OcadoApi(async_get_clientsession(hass), entry.data[CONF_COOKIE])
    coordinator = OcadoCoordinator(hass, entry, api)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = OcadoRuntimeData(api=api, coordinator=coordinator)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: OcadoConfigEntry) -> bool:
    """Unload an Ocado Deliveries config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
