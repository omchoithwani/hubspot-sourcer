"""
Query bank (64 queries) with industry/location tags + filter-aware rotation.

Each entry is (query_string, tag_set).
- Empty tag set  → general query, always included regardless of filters.
- Non-empty tags → only included when at least one tag matches an active filter,
                   OR when no filters are configured at all.

Rotation: daily shuffle (seeded by date) + sequential by run index.
"""

import random
from datetime import date
from pathlib import Path

from config import FILTER_INDUSTRIES, FILTER_LOCATIONS

COUNTER_FILE = Path("run_counter.txt")

# ---------------------------------------------------------------------------
# Query bank
# Format: (query_string, set_of_tags)
# Industry tags : saas, fintech, healthcare, ecommerce, real-estate,
#                 consulting, agency, technology, enterprise, cybersecurity,
#                 logistics, hr
# Location tags : australia, uk, us, canada, germany, netherlands
# ---------------------------------------------------------------------------
_RAW_BANK = [
    # --- General (always included) ------------------------------------------
    ('"js.hs-scripts.com"',                         set()),
    ('"js.hs-analytics.net"',                        set()),
    ('"js.hscollectedforms.net"',                    set()),
    ('"js.hs-banner.com"',                           set()),
    ('"js.hsadspixel.net"',                          set()),
    ('"js.usemessages.com"',                         set()),
    ('"track.hubspot.com"',                          set()),
    ('"_hsq.push"',                                  set()),
    ('"_hsp.push"',                                  set()),
    ('"hs-script-loader"',                           set()),
    ('"hbspt.forms.create"',                         set()),
    ('"forms.hubspot.com"',                          set()),
    ('"js.hsforms.net"',                             set()),
    ('"hbspt.forms.create" inurl:contact',           set()),
    ('"hbspt.forms.create" inurl:demo',              set()),
    ('"hbspt.forms.create" inurl:free-trial',        set()),
    ('"hbspt.forms.create" inurl:get-started',       set()),
    ('"hbspt.forms.create" inurl:request',           set()),
    ('"hbspt.cta.load"',                             set()),
    ('"hs-cta-wrapper"',                             set()),
    ('"hs-cta-node"',                                set()),
    ('"data-hs-cos"',                                set()),
    ('"hs-cos-general"',                             set()),
    ('"data-hsjs-portal"',                           set()),
    ('"hubspot-messages-iframe-container"',          set()),
    ('"hbs-content-id"',                             set()),
    ('inurl:"hs_cos_wrapper"',                       set()),
    ('"hs_cos_wrapper"',                             set()),
    ('"hs-cos-type-module"',                         set()),
    ('"hs-cos-type-rich_text"',                      set()),
    ('"powered by HubSpot"',                         set()),
    ('"Built with HubSpot"',                         set()),
    ('"hubspot.net" inurl:blog',                     set()),
    ('"api.hubspot.com"',                            set()),
    ('"hubspot-messages" site:com',                  set()),
    ('"js.hs-scripts.com" portalId',                 set()),
    ('"hbspt.forms.create" portalId',                set()),
    ('"hbspt.cta.load" portalId',                    set()),
    ('"hs-scripts.com" inurl:about',                 set()),
    ('"hs-scripts.com" inurl:pricing',               set()),
    ('"hs-scripts.com" inurl:services',              set()),
    ('"hs-scripts.com" inurl:solutions',             set()),

    # --- Industry-tagged ----------------------------------------------------
    ('"hbspt.forms.create" "marketing agency"',      {"agency"}),
    ('"powered by HubSpot" "agency"',                {"agency"}),
    ('"hs-scripts.com" "marketing"',                 {"agency"}),
    ('"hbspt.forms.create" "SaaS"',                  {"saas"}),
    ('"hbspt.forms.create" "B2B"',                   {"saas", "technology"}),
    ('"hs-scripts.com" "software company"',          {"saas", "technology"}),
    ('"hbspt.forms.create" "consulting"',            {"consulting"}),
    ('"hbspt.forms.create" "professional services"', {"consulting"}),
    ('"hbspt.forms.create" "fintech"',               {"fintech"}),
    ('"hbspt.forms.create" "healthcare"',            {"healthcare"}),
    ('"hbspt.forms.create" "ecommerce"',             {"ecommerce"}),
    ('"hbspt.forms.create" "real estate"',           {"real-estate"}),
    ('"hbspt.forms.create" "technology"',            {"technology"}),
    ('"hbspt.forms.create" "enterprise software"',   {"enterprise"}),
    ('"hbspt.forms.create" "cybersecurity"',         {"cybersecurity"}),
    ('"hbspt.forms.create" "logistics"',             {"logistics"}),
    ('"hbspt.forms.create" "HR software"',           {"hr"}),

    # --- Location-tagged ----------------------------------------------------
    ('"hbspt.forms.create" "Australia"',             {"australia"}),
    ('"hbspt.forms.create" "United Kingdom"',        {"uk"}),
    ('"hbspt.forms.create" "United States"',         {"us"}),
    ('"hbspt.forms.create" "Canada"',                {"canada"}),
    ('"hbspt.forms.create" "Germany"',               {"germany"}),
    ('"hbspt.forms.create" "Netherlands"',           {"netherlands"}),
]


def _active_filters() -> set:
    return set(FILTER_INDUSTRIES + FILTER_LOCATIONS)


def _filtered_queries() -> list:
    """
    Apply industry/location filters to the query bank.
    - No filters configured → return all queries.
    - Filters configured    → return general (untagged) queries always,
                              plus tagged queries whose tags overlap the active filters.
    """
    active = _active_filters()
    if not active:
        return [q for q, _ in _RAW_BANK]
    return [q for q, tags in _RAW_BANK if not tags or tags & active]


def _daily_order(queries: list) -> list:
    """Shuffle with today's date as seed — stable within a day, fresh each morning."""
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


def next_query() -> tuple:
    """Return (query_string, run_index) for the current run."""
    queries = _daily_order(_filtered_queries())
    idx = get_run_index()
    return queries[idx % len(queries)], idx


def active_filter_summary() -> str:
    """Human-readable description of current filters (for logging)."""
    industries = FILTER_INDUSTRIES
    locations = FILTER_LOCATIONS
    if not industries and not locations:
        return "none (all queries active)"
    parts = []
    if industries:
        parts.append(f"industries={','.join(industries)}")
    if locations:
        parts.append(f"locations={','.join(locations)}")
    pool = _filtered_queries()
    return f"{' | '.join(parts)} → {len(pool)} queries in pool"
