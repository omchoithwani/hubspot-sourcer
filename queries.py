"""
Query bank (60 queries) + sequential rotation by run index.
Order shuffles daily using the date as a seed so every day feels fresh
but is deterministic within the same day.
"""

import random
from datetime import date
from pathlib import Path

COUNTER_FILE = Path("run_counter.txt")

QUERY_BANK: list[str] = [
    # JS tracking & analytics scripts
    '"js.hs-scripts.com"',
    '"js.hs-analytics.net"',
    '"js.hscollectedforms.net"',
    '"js.hs-banner.com"',
    '"js.hsadspixel.net"',
    '"js.usemessages.com"',
    '"track.hubspot.com"',
    '"_hsq.push"',
    '"_hsp.push"',
    '"hs-script-loader"',

    # HubSpot forms
    '"hbspt.forms.create"',
    '"forms.hubspot.com"',
    '"js.hsforms.net"',
    '"hbspt.forms.create" inurl:contact',
    '"hbspt.forms.create" inurl:demo',
    '"hbspt.forms.create" inurl:free-trial',
    '"hbspt.forms.create" inurl:get-started',
    '"hbspt.forms.create" inurl:request',

    # CTAs
    '"hbspt.cta.load"',
    '"hs-cta-wrapper"',
    '"hs-cta-node"',

    # HubSpot CMS / COS templates
    '"data-hs-cos"',
    '"hs-cos-general"',
    '"data-hsjs-portal"',
    '"hubspot-messages-iframe-container"',
    '"hbs-content-id"',
    'inurl:"hs_cos_wrapper"',
    '"hs_cos_wrapper"',
    '"hs-cos-type-module"',
    '"hs-cos-type-rich_text"',

    # General HubSpot signals
    '"powered by HubSpot"',
    '"Built with HubSpot"',
    '"hubspot.net" inurl:blog',
    '"api.hubspot.com"',
    '"hubspot-messages" site:com',

    # Industry verticals + HubSpot forms
    '"hbspt.forms.create" "marketing agency"',
    '"hbspt.forms.create" "SaaS"',
    '"hbspt.forms.create" "consulting"',
    '"hbspt.forms.create" "fintech"',
    '"hbspt.forms.create" "healthcare"',
    '"hbspt.forms.create" "ecommerce"',
    '"hbspt.forms.create" "real estate"',
    '"hbspt.forms.create" "technology"',
    '"hbspt.forms.create" "enterprise software"',
    '"hbspt.forms.create" "B2B"',
    '"hbspt.forms.create" "professional services"',
    '"hbspt.forms.create" "cybersecurity"',
    '"hbspt.forms.create" "logistics"',
    '"hbspt.forms.create" "HR software"',

    # Geographic + HubSpot
    '"hbspt.forms.create" "Australia"',
    '"hbspt.forms.create" "United Kingdom"',
    '"hbspt.forms.create" "Canada"',
    '"hbspt.forms.create" "Germany"',
    '"hbspt.forms.create" "Netherlands"',
    '"powered by HubSpot" "agency"',

    # hs-scripts by page context
    '"hs-scripts.com" inurl:about',
    '"hs-scripts.com" inurl:pricing',
    '"hs-scripts.com" inurl:services',
    '"hs-scripts.com" inurl:solutions',
    '"hs-scripts.com" "software company"',
    '"hs-scripts.com" "marketing"',

    # Portal ID presence
    '"js.hs-scripts.com" portalId',
    '"hbspt.forms.create" portalId',
    '"hbspt.cta.load" portalId',
]


def _daily_order(queries: list[str]) -> list[str]:
    """Shuffle query list with today's date as seed — stable within a day."""
    seed = int(date.today().strftime("%Y%m%d"))
    rng = random.Random(seed)
    shuffled = queries[:]
    rng.shuffle(shuffled)
    return shuffled


def get_run_index() -> int:
    if COUNTER_FILE.exists():
        raw = COUNTER_FILE.read_text().strip()
        return int(raw) if raw.isdigit() else 0
    return 0


def increment_run_index() -> None:
    COUNTER_FILE.write_text(str(get_run_index() + 1))


def next_query() -> tuple[str, int]:
    """Return (query_string, run_index) for the current run."""
    queries = _daily_order(QUERY_BANK)
    idx = get_run_index()
    return queries[idx % len(queries)], idx
