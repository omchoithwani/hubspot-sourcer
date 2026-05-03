"""
Auth helper — loads the HubSpot private app token from .env.
Swap get_token() for an OAuth flow here when ready; nothing else changes.
"""

import os
from dotenv import load_dotenv

load_dotenv()


def get_token() -> str:
    token = os.getenv("HUBSPOT_TOKEN", "").strip()
    if not token:
        raise ValueError("HUBSPOT_TOKEN is not set in .env")
    return token
