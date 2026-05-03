"""
User-configurable filters loaded from .env.

FILTER_INDUSTRIES — comma-separated list, e.g. saas,fintech,healthcare
FILTER_LOCATIONS  — comma-separated list, e.g. australia,uk,canada

Leave either blank to include all queries for that dimension.
Valid industry values : saas, fintech, healthcare, ecommerce, real-estate,
                        consulting, agency, technology, enterprise,
                        cybersecurity, logistics, hr
Valid location values : australia, uk, us, canada, germany, netherlands
"""

import os

from dotenv import load_dotenv

load_dotenv()


def _parse_list(env_var: str) -> list:
    raw = os.getenv(env_var, "").strip()
    if not raw:
        return []
    return [item.strip().lower() for item in raw.split(",") if item.strip()]


FILTER_INDUSTRIES = _parse_list("FILTER_INDUSTRIES")
FILTER_LOCATIONS = _parse_list("FILTER_LOCATIONS")
