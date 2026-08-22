"""Constants for the Ocado Deliveries integration."""

from datetime import timedelta

DOMAIN = "ocado_deliveries"
CONF_COOKIE = "cookie"
CONF_BROWSER_HEADERS = "browser_headers"

BASE_URL = "https://www.ocado.com"
GRAPHQL_URL = f"{BASE_URL}/graphql"
UPDATE_INTERVAL = timedelta(minutes=30)

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
