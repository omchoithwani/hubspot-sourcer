"""
Core search pipeline — callable by both the web app and the CLI.

run_search(query, job) mutates *job* in place so the web app can
poll for live progress. Pass job=None for CLI/fire-and-forget use.
"""

import logging

from auth import get_token
from dedup import filter_new_domains, mark_seen
from detect import run_detection
from logger import log_run
from push import push_company
from scraper import scrape_domains
from validator import filter_live_domains

log = logging.getLogger(__name__)


def _update(job: dict, progress: str) -> None:
    if job is not None:
        job["progress"] = progress
    log.info(progress)


def run_search(query: str, job: dict = None) -> dict:
    """
    Run one full sourcing cycle for *query*.

    *job* is an optional dict that gets mutated with live progress so the
    web frontend can poll it. Returns the same dict (or a new one if None).
    """
    if job is None:
        job = {
            "status": "running",
            "progress": "",
            "stats": {"found": 0, "live": 0, "new": 0, "confirmed": 0, "pushed": 0},
            "results": [],
            "error": None,
        }

    token = get_token()

    # 1. Scrape
    _update(job, f'Searching DuckDuckGo for "{query}"…')
    domains = scrape_domains(query)
    job["stats"]["found"] = len(domains)
    _update(job, f"Found {len(domains)} domain(s) in search results")

    # 2. Validate
    _update(job, "Checking which domains have live websites…")
    live = filter_live_domains(domains)
    job["stats"]["live"] = len(live)
    _update(job, f"{len(live)} live domain(s) after dropping dead/parked sites")

    # 3. Dedup
    _update(job, "Deduplicating against HubSpot CRM…")
    new = filter_new_domains(live, token)
    job["stats"]["new"] = len(new)
    _update(job, f"{len(new)} new domain(s) not yet in CRM")

    if not new:
        _update(job, "No new domains to process — all already seen or in CRM")
        _finalise(job, query)
        return job

    # 4. Detect + push
    for i, domain in enumerate(new, 1):
        _update(job, f"Detecting HubSpot on {domain} ({i}/{len(new)})…")
        result = run_detection(domain)
        mark_seen(domain)

        entry = {
            "domain": domain,
            "confirmed": result.uses_hubspot,
            "confidence": result.confidence,
            "portal_id": result.hubspot_portal_id,
            "signals": result.signals[:6],
            "pushed": False,
            "error": result.error or "",
        }

        if result.uses_hubspot:
            job["stats"]["confirmed"] += 1
            _update(job, f"HubSpot confirmed on {domain} — pushing to CRM…")
            pushed = push_company(domain, token)
            entry["pushed"] = pushed
            if pushed:
                job["stats"]["pushed"] += 1

        job["results"].append(entry)

    _finalise(job, query)
    return job


def _finalise(job: dict, query: str) -> None:
    s = job["stats"]
    log_run(
        query=query,
        found=s["found"],
        live=s["live"],
        passed_dedup=s["new"],
        confirmed=s["confirmed"],
        pushed=s["pushed"],
    )
    job["progress"] = (
        f"Done — {s['confirmed']} HubSpot site(s) found, {s['pushed']} pushed to CRM"
    )
    job["status"] = "done"
