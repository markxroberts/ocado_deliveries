# Changelog

## 0.2.1

- Added local Home Assistant `brand/` assets using Ocado Retail's official logo artwork, including light/dark and 1x/2x variants.
- Corrected the Next delivery entity icon to the valid `mdi:truck-delivery-outline` icon.
- Added an explicit icon fallback on the Next delivery timestamp sensor for frontends that do not apply `icons.json` there.

## 0.2.0

- Remains strictly read-only; no Ocado mutation endpoints are implemented.
- Added `calendar.ocado_edit_deadlines`.
- Added Home Assistant config-entry diagnostics with aggressive privacy filtering.
- Added a Reconfigure flow to refresh the imported browser session proactively.
- Retained automatic Home Assistant reauthentication when Ocado rejects an expired session.
- Marked the Ocado account device as a Home Assistant service device and added a direct configuration URL.
- Added entity translation keys and `icons.json` rather than storing static entity icons in state.
- Improved delivery/edit calendar descriptions and ETA presentation.
- Added more tracking fields to the next-delivery sensor attributes.
- Stopped including arbitrary Ocado HTTP response bodies in error messages/logs.
- Corrected all setup/reauth wording to use Chrome **Copy as cURL (bash)**.

## 0.1.1

- Added support for Chrome cURL `-b` / `--cookie` cookie syntax.

## 0.1.0

- Initial test release.
