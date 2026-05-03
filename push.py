"""
Push confirmed HubSpot companies into HubSpot CRM.

Strategy:
  - Search CRM for an existing company by domain.
  - If found  → update hubspot_user = "true" on the existing record.
  - If not found → create a new Company record with domain + hubspot_user = "true".

Uses update_company_property() from the existing hubspot_api module for updates.
Create and search calls are added here to keep hubspot_api.py unchanged.
"""

import requests

from hubspot_api import update_company_property

API_BASE = "https://api.hubapi.com"
HUBSPOT_USER_PROP = "hubspot_user"


def _headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


def _find_company_id(domain: str, token: str) -> str | None:
    """Return the CRM company ID for *domain*, or None if not found."""
    try:
        resp = requests.post(
            f"{API_BASE}/crm/v3/objects/companies/search",
            headers=_headers(token),
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
            results = resp.json().get("results", [])
            if results:
                return results[0]["id"]
    except requests.RequestException:
        pass
    return None


def _create_company(domain: str, token: str) -> str | None:
    """Create a new Company record and return its ID, or None on failure."""
    try:
        resp = requests.post(
            f"{API_BASE}/crm/v3/objects/companies",
            headers=_headers(token),
            json={
                "properties": {
                    "domain": domain,
                    "name": domain,
                    HUBSPOT_USER_PROP: "true",
                }
            },
            timeout=10,
        )
        if resp.status_code in (200, 201):
            return resp.json().get("id")
    except requests.RequestException:
        pass
    return None


def push_company(domain: str, token: str) -> bool:
    """
    Ensure *domain* exists in HubSpot CRM with hubspot_user = true.
    Returns True if the operation succeeded.
    """
    company_id = _find_company_id(domain, token)

    if company_id:
        # Company already in CRM — just update the property
        return update_company_property(token, company_id, HUBSPOT_USER_PROP, "true")

    # Not in CRM — create a fresh record (hubspot_user set at creation time)
    created_id = _create_company(domain, token)
    return created_id is not None
