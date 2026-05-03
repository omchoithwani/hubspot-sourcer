"""
Domain liveness checker.
Concurrent HEAD requests to verify each domain has an active web server
before spending time on full HubSpot detection.
"""

import concurrent.futures

import requests

TIMEOUT = 5
MAX_WORKERS = 10

# Any of these status codes means a real server answered — consider it live.
# 403/405/406 are included because legitimate sites often block scrapers
# but are clearly up.
_LIVE_CODES = set(range(200, 400)) | {403, 405, 406}

_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; HubSpotSourcer/1.0)"}


def _is_live(domain: str) -> bool:
    for scheme in ("https", "http"):
        try:
            resp = requests.head(
                f"{scheme}://{domain}",
                headers=_HEADERS,
                timeout=TIMEOUT,
                allow_redirects=True,
            )
            if resp.status_code in _LIVE_CODES:
                return True
        except requests.RequestException:
            continue
    return False


def filter_live_domains(domains: list) -> list:
    """Return only the domains that respond to HTTP — dead/parked domains removed."""
    if not domains:
        return []
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        results = list(executor.map(_is_live, domains))
    return [d for d, alive in zip(domains, results) if alive]
