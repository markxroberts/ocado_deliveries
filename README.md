# Ocado Deliveries for Home Assistant

Home Assistant 2026.3+ displays bundled Ocado Retail branding in the integration UI, with light and dark mode assets.

Read-only Home Assistant custom integration for upcoming Ocado deliveries.

## Entities

- `calendar.ocado_deliveries` — delivery windows for upcoming orders.
- `calendar.ocado_edit_deadlines` — one-minute calendar markers at Ocado's guaranteed edit deadlines.
- `sensor.ocado_next_delivery` — timestamp of the next delivery, with useful order/tracking attributes.
- `sensor.ocado_next_edit_deadline` — next future edit deadline.
- `sensor.ocado_upcoming_deliveries` — number of upcoming deliveries.

Entity IDs can be adjusted by Home Assistant if names already exist.

## Read-only guarantee

The integration contains only the `GetUpcomingOrders` GraphQL **query**. It contains no GraphQL mutations and no code for basket changes, checkout, delivery-slot booking, order editing or cancellation. The calendar entities do not advertise create/update/delete features.

## Installation / upgrade

Copy `custom_components/ocado_deliveries` into Home Assistant's `/config/custom_components/` directory and restart Home Assistant.

For an upgrade, replace the existing `ocado_deliveries` directory with the new one and restart. Existing v0.1.x config entries do not need to be removed or recreated.

Then go to **Settings > Devices & services**. To add it for the first time choose **Add integration > Ocado Deliveries**.

## Authentication

Ocado can require two-factor authentication for a new browser login, so this integration deliberately does not automate username/password login or 2FA.

1. Sign in to `ocado.com` in Chrome and complete 2FA if requested.
2. Open **Developer Tools > Network**.
3. Load **Your orders**.
4. Select any successful Ocado `/graphql` request (the completed-orders request is fine).
5. Right-click the request row and choose **Copy > Copy as cURL (bash)**.
6. Paste the complete cURL command into the Home Assistant setup form.

The integration extracts and stores only the Ocado Cookie value. It does **not** store the copied CSRF token or other request headers. Before each GraphQL session it obtains a current CSRF token from authenticated Ocado page HTML.

When the browser session expires, Home Assistant automatically starts a reauthentication flow. v0.2.0 and later also provide **Reconfigure** on the integration entry so the browser session can be refreshed proactively.

## Polling

Upcoming deliveries are polled every 30 minutes.

## Diagnostics and privacy

Home Assistant diagnostics are supported. Diagnostics redact the saved cookie and deliberately omit order IDs, prices, delivery destinations, delivery/edit times and recurring-order names.

The normal Home Assistant entities do expose the order information needed for automations and display, including the next order's ID, total, edit deadline and tracking information.

## Limitations

This uses Ocado's private website API rather than a published public API. Ocado can change its website schema, authentication or anti-bot behaviour without notice. A browser-session refresh may occasionally be required.

## Version

0.2.1
