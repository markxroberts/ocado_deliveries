"""Config flow for Ocado Deliveries."""

from __future__ import annotations

import asyncio
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import TextSelector, TextSelectorConfig

from .api import OcadoApi, OcadoApiError, OcadoAuthError, extract_cookie
from .const import CONF_BROWSER_HEADERS, CONF_COOKIE, DOMAIN


class OcadoDeliveriesConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle an Ocado Deliveries config flow."""

    VERSION = 1

    async def _async_validate(self, browser_headers: str) -> str:
        """Validate imported browser session data and return its cookie."""
        cookie = extract_cookie(browser_headers)
        api = OcadoApi(async_get_clientsession(self.hass), cookie)
        await api.async_get_upcoming_orders()
        return cookie

    async def _async_session_form(
        self,
        *,
        step_id: str,
        user_input: dict[str, Any] | None,
    ) -> tuple[str | None, dict[str, str]]:
        """Validate the common browser-session form."""
        errors: dict[str, str] = {}
        if user_input is None:
            return None, errors

        try:
            cookie = await self._async_validate(user_input[CONF_BROWSER_HEADERS])
        except ValueError:
            errors["base"] = "cookie_not_found"
        except OcadoAuthError:
            errors["base"] = "invalid_auth"
        except (aiohttp.ClientError, asyncio.TimeoutError, TimeoutError):
            errors["base"] = "cannot_connect"
        except OcadoApiError:
            errors["base"] = "api_error"
        except Exception:  # noqa: BLE001
            errors["base"] = "unknown"
        else:
            return cookie, errors

        return None, errors

    def _show_session_form(
        self,
        *,
        step_id: str,
        errors: dict[str, str],
    ) -> config_entries.ConfigFlowResult:
        return self.async_show_form(
            step_id=step_id,
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_BROWSER_HEADERS): TextSelector(
                        TextSelectorConfig(multiline=True)
                    )
                }
            ),
            errors=errors,
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle initial setup."""
        cookie, errors = await self._async_session_form(
            step_id="user", user_input=user_input
        )
        if cookie is not None:
            await self.async_set_unique_id(DOMAIN)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title="Ocado",
                data={CONF_COOKIE: cookie},
            )
        return self._show_session_form(step_id="user", errors=errors)

    async def async_step_reauth(
        self, entry_data: dict[str, Any]
    ) -> config_entries.ConfigFlowResult:
        """Start reauthentication."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Import a fresh browser session after authentication expires."""
        entry = self._get_reauth_entry()
        cookie, errors = await self._async_session_form(
            step_id="reauth_confirm", user_input=user_input
        )
        if cookie is not None:
            return self.async_update_reload_and_abort(
                entry,
                data={**entry.data, CONF_COOKIE: cookie},
            )
        return self._show_session_form(step_id="reauth_confirm", errors=errors)

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Allow the saved browser session to be refreshed proactively."""
        entry = self._get_reconfigure_entry()
        cookie, errors = await self._async_session_form(
            step_id="reconfigure", user_input=user_input
        )
        if cookie is not None:
            return self.async_update_reload_and_abort(
                entry,
                data={**entry.data, CONF_COOKIE: cookie},
            )
        return self._show_session_form(step_id="reconfigure", errors=errors)
