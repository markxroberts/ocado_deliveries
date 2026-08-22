"""Minimal read-only Ocado web client."""

from __future__ import annotations

import re
import shlex
from typing import Any

import aiohttp

from .const import BASE_URL, GRAPHQL_URL, USER_AGENT
from .models import OcadoOrder, parse_datetime

CSRF_RE = re.compile(r'"csrf":\{"token":"([^"]+)"')

UPCOMING_ORDERS_QUERY = r"""
query GetUpcomingOrders {
  ordersUpcoming {
    orderId
    status
    region {
      regionId
      retailerRegionId
    }
    prices {
      total {
        currency
        amount
      }
    }
    recurringOrderDefinition {
      recurringOrderDefinitionId
      name
    }
    editInfo {
      isEditable
      isUnderEdit
      edited
      guaranteedEditableBy
      restrictions {
        description
      }
    }
    slot {
      slotId
      type
      shippingGroupType
      timeWindow {
        start
        end
        timeZone
      }
    }
    delivery {
      __typename
      deliveryMethod
      ... on HomeDelivery {
        destination {
          name
          deliveryDestinationId
        }
        carrier {
          carrierId
          deliveryTrackingMode
        }
        externalLocker {
          externalLockerId
        }
        tracking {
          status
          eta {
            status
            time
            window {
              from
              to
            }
          }
        }
      }
      ... on CollectionPointDelivery {
        destination {
          name
          deliveryDestinationId
        }
      }
    }
  }
}
""".strip()


class OcadoError(Exception):
    """Base Ocado error."""


class OcadoAuthError(OcadoError):
    """The browser session has expired or is invalid."""


class OcadoApiError(OcadoError):
    """Ocado returned an unexpected response."""


def extract_cookie(value: str) -> str:
    """Extract a Cookie value from raw cookie text, request headers or cURL."""
    text = value.strip()
    if not text:
        raise ValueError("empty input")

    # Raw request headers copied from a browser/network inspector.
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.lower().startswith("cookie:"):
            cookie = stripped.split(":", 1)[1].strip()
            if cookie:
                return cookie

    # Chrome's "Copy as cURL (bash)" commonly serialises the Cookie header as
    # -b/--cookie instead of -H 'cookie: ...'.  shlex also handles Chrome's
    # backslash-newline formatting safely.
    if text.lstrip().lower().startswith("curl "):
        try:
            args = shlex.split(text, posix=True)
        except ValueError:
            args = []

        idx = 0
        while idx < len(args):
            arg = args[idx]
            lower = arg.lower()

            if lower in ("-b", "--cookie") and idx + 1 < len(args):
                cookie = args[idx + 1].strip()
                if cookie:
                    return cookie
                idx += 2
                continue

            if lower.startswith("--cookie="):
                cookie = arg.split("=", 1)[1].strip()
                if cookie:
                    return cookie

            if lower in ("-h", "--header") and idx + 1 < len(args):
                header = args[idx + 1].strip()
                if header.lower().startswith("cookie:"):
                    cookie = header.split(":", 1)[1].strip()
                    if cookie:
                        return cookie
                idx += 2
                continue

            if lower.startswith("--header="):
                header = arg.split("=", 1)[1].strip()
                if header.lower().startswith("cookie:"):
                    cookie = header.split(":", 1)[1].strip()
                    if cookie:
                        return cookie

            idx += 1

    # Fallback for cURL snippets that do not parse cleanly with shlex.
    curl_match = re.search(
        r"(?:-H|--header)\s+[\"']cookie:\s*([^\"']+)[\"']",
        text,
        flags=re.IGNORECASE,
    )
    if curl_match:
        return curl_match.group(1).strip()

    cookie_arg_match = re.search(
        r"(?:-b|--cookie)\s+[\"']([^\"']+)[\"']",
        text,
        flags=re.IGNORECASE,
    )
    if cookie_arg_match:
        return cookie_arg_match.group(1).strip()

    # Allow the raw Cookie header value itself.
    if "=" in text and ";" in text and "\n" not in text and "\r" not in text:
        return text

    raise ValueError("No Cookie header found")


class OcadoApi:
    """Read-only client for the Ocado website APIs."""

    def __init__(self, session: aiohttp.ClientSession, cookie: str) -> None:
        self._session = session
        self._cookie = cookie
        self._csrf_token: str | None = None

    @property
    def cookie(self) -> str:
        """Return the configured cookie header value."""
        return self._cookie

    def set_cookie(self, cookie: str) -> None:
        """Replace the browser session cookie."""
        self._cookie = cookie
        self._csrf_token = None

    def _base_headers(self) -> dict[str, str]:
        return {
            "Cookie": self._cookie,
            "User-Agent": USER_AGENT,
        }

    async def async_get_csrf_token(self, *, force_refresh: bool = False) -> str:
        """Fetch a fresh CSRF token from Ocado page HTML."""
        if self._csrf_token and not force_refresh:
            return self._csrf_token

        headers = self._base_headers()
        headers["Accept"] = "text/html,application/xhtml+xml"

        try:
            async with self._session.get(
                f"{BASE_URL}/",
                headers=headers,
                allow_redirects=True,
                timeout=aiohttp.ClientTimeout(total=20),
            ) as response:
                if response.status in (401, 403):
                    raise OcadoAuthError(f"Ocado rejected the browser session (HTTP {response.status})")
                if response.status >= 400:
                    raise OcadoApiError(f"Ocado home page returned HTTP {response.status}")
                html = await response.text()
                final_url = str(response.url)
        except aiohttp.ClientError:
            raise

        match = CSRF_RE.search(html)
        if not match:
            if "/login" in final_url:
                raise OcadoAuthError("Ocado browser session has expired")
            raise OcadoAuthError(
                "No CSRF token was found in Ocado page HTML; the browser session may have expired"
            )

        self._csrf_token = match.group(1)
        return self._csrf_token

    async def _async_graphql(self, *, retry_csrf: bool = True) -> dict[str, Any]:
        token = await self.async_get_csrf_token()
        headers = self._base_headers()
        headers.update(
            {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "x-csrf-token": token,
                "ecom-request-source": "web",
            }
        )
        payload = {
            "operationName": "GetUpcomingOrders",
            "query": UPCOMING_ORDERS_QUERY,
            "variables": {},
        }

        async with self._session.post(
            GRAPHQL_URL,
            headers=headers,
            json=payload,
            timeout=aiohttp.ClientTimeout(total=20),
        ) as response:
            if response.status == 403 and retry_csrf:
                await response.read()
                await self.async_get_csrf_token(force_refresh=True)
                return await self._async_graphql(retry_csrf=False)
            if response.status in (401, 403):
                raise OcadoAuthError(f"Ocado rejected the browser session (HTTP {response.status})")
            if response.status >= 400:
                await response.read()
                raise OcadoApiError(
                    f"Ocado GraphQL returned HTTP {response.status}"
                )
            try:
                data = await response.json(content_type=None)
            except (ValueError, aiohttp.ContentTypeError) as err:
                raise OcadoApiError("Ocado returned a non-JSON GraphQL response") from err

        errors = data.get("errors")
        if errors:
            messages = "; ".join(str(item.get("message", item)) for item in errors)
            lowered = messages.lower()
            if "auth" in lowered or "forbidden" in lowered or "csrf" in lowered:
                raise OcadoAuthError(messages)
            raise OcadoApiError(f"Ocado GraphQL error: {messages}")

        return data

    async def async_get_upcoming_orders(self) -> list[OcadoOrder]:
        """Return Ocado's upcoming orders."""
        result = await self._async_graphql()
        raw_orders = result.get("data", {}).get("ordersUpcoming")
        if raw_orders is None:
            raise OcadoApiError("Ocado response did not contain ordersUpcoming")
        if not isinstance(raw_orders, list):
            raise OcadoApiError("Ocado returned an invalid ordersUpcoming value")

        orders: list[OcadoOrder] = []
        for raw in raw_orders:
            slot = raw.get("slot") or {}
            time_window = slot.get("timeWindow") or {}
            start = parse_datetime(time_window.get("start"))
            end = parse_datetime(time_window.get("end"))
            if start is None or end is None or end <= start:
                continue

            prices = raw.get("prices") or {}
            total = prices.get("total") or {}
            amount = total.get("amount")
            try:
                total_amount = float(amount) if amount is not None else None
            except (TypeError, ValueError):
                total_amount = None

            edit_info = raw.get("editInfo") or {}
            delivery = raw.get("delivery") or {}
            destination = delivery.get("destination") or {}
            recurring = raw.get("recurringOrderDefinition") or {}
            tracking = delivery.get("tracking") or {}
            eta = tracking.get("eta") or {}
            eta_window = eta.get("window") or {}

            orders.append(
                OcadoOrder(
                    order_id=str(raw.get("orderId", "")),
                    status=raw.get("status"),
                    start=start,
                    end=end,
                    time_zone=time_window.get("timeZone"),
                    total_amount=total_amount,
                    currency=total.get("currency"),
                    is_editable=bool(edit_info.get("isEditable")),
                    edit_deadline=parse_datetime(edit_info.get("guaranteedEditableBy")),
                    delivery_method=delivery.get("deliveryMethod"),
                    destination_name=destination.get("name"),
                    recurring_name=recurring.get("name"),
                    tracking_status=tracking.get("status"),
                    eta_status=eta.get("status"),
                    eta_time=parse_datetime(eta.get("time")),
                    eta_from=parse_datetime(eta_window.get("from")),
                    eta_to=parse_datetime(eta_window.get("to")),
                )
            )

        orders.sort(key=lambda order: order.start)
        return orders
