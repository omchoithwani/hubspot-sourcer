"""
Deduplication layer.

Two-stage check:
  1. seen_domains.txt  — O(1) local set lookup, no network cost.
  2. HubSpot CRM search by domain — only reached if domain passes stage 1.

Domains that pass both stages are genuinely new and should be detected + pushed.
"""

from pathlib import Path

import requests

SEEN_FILE = Path("seen_domains.txt")
HUBSPOT_SEARCH_URL = "https://api.hubapi.com/crm/v3/objects/companies/search"


# ---------------------------------------------------------------------------
# Local file store
# ---------------------------------------------------------------------------

def _load_seen() -> set[str]:
    if not SEEN_FILE.exists():
        return set()
    return {line.strip() for line in SEEN_FILE.read_text().splitlines() if line.strip()}


def mark_seen(domain: str) -> None:
    """Append *domain* to seen_domains.txt so it is skipped on future runs."""
    with open(SEEN_FILE, "a") as f:
        f.write(domain + "\n")


# ---------------------------------------------------------------------------
# HubSpot CRM lookup
# ---------------------------------------------------------------------------

def _is_in_hubspot(domain: str, token: str) -> bool:
    """Return True if a company with this domain already exists in HubSpot CRM."""
    try:
        resp = requests.post(
            HUBSPOT_SEARCH_URL,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json={
                "filterGroups": [
                    {
                        "filters": [
                            {
                                "propertyName": "domain",
                                "operator": "EQ",
                                "value": domain,
                            }
                        ]
                    }
                ],
                "properties": ["domain"],
                "limit": 1,
            },
            timeout=10,
        )
        if resp.status_code == 200:
            return resp.json().get("total", 0) > 0
    except requests.RequestException:
        pass
    return False


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def filter_new_domains(domains: list[str], token: str) -> list[str]:
    """
    Return only the domains that are new — not in seen_domains.txt and not
    already present as a company in HubSpot CRM.

    Domains that exist in HubSpot but not locally are added to seen_domains.txt
    so the CRM API is not hit for them again.
    """
    seen = _load_seen()
    new: list[str] = []

    for domain in domains:
        if domain in seen:
            continue
        if _is_in_hubspot(domain, token):
            mark_seen(domain)  # cache locally to avoid future API calls
            continue
        new.append(domain)

    return new
