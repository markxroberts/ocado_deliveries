"""Data update coordinator for Ocado Deliveries."""

from __future__ import annotations

import logging

import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import OcadoApi, OcadoApiError, OcadoAuthError
from .const import DOMAIN, UPDATE_INTERVAL
from .models import OcadoOrder

_LOGGER = logging.getLogger(__name__)


class OcadoCoordinator(DataUpdateCoordinator[list[OcadoOrder]]):
    """Coordinate polling of Ocado upcoming orders."""

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        api: OcadoApi,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=config_entry,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
            always_update=False,
        )
        self.api = api

    async def _async_update_data(self) -> list[OcadoOrder]:
        try:
            return await self.api.async_get_upcoming_orders()
        except OcadoAuthError as err:
            raise ConfigEntryAuthFailed(
                "The Ocado browser session has expired; import a fresh browser session"
            ) from err
        except OcadoApiError as err:
            raise UpdateFailed(str(err)) from err
        except (aiohttp.ClientError, TimeoutError) as err:
            raise UpdateFailed(f"Error communicating with Ocado: {err}") from err
