"""
Orchestrates one full sourcing run:
  query → scrape → validate → dedup → detect → push → log
"""

import logging

from auth import get_token
from dedup import filter_new_domains, mark_seen
from detect import run_detection
from logger import log_run
from push import push_company
from queries import active_filter_summary, increment_run_index, next_query
from scraper import scrape_domains
from validator import filter_live_domains

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)


def run() -> None:
    token = get_token()
    query, run_idx = next_query()
    log.info("Run #%d — query: %s", run_idx, query)
    log.info("Active filters: %s", active_filter_summary())

    # 1. Scrape
    domains = scrape_domains(query)
    log.info("Scraped %d domain(s)", len(domains))

    # 2. Validate — drop dead/parked domains
    live_domains = filter_live_domains(domains)
    log.info("%d live domain(s) after validation", len(live_domains))

    # 3. Dedup — skip already-seen and already-in-CRM domains
    new_domains = filter_new_domains(live_domains, token)
    log.info("%d new domain(s) after dedup", len(new_domains))

    confirmed: list = []
    pushed_count = 0

    for domain in new_domains:
        # 4. Detect
        result = run_detection(domain)

        # Mark seen regardless of outcome — never re-check this domain
        mark_seen(domain)

        if not result.uses_hubspot:
            log.info("Not HubSpot: %s", domain)
            continue

        log.info(
            "Confirmed HubSpot: %s [confidence=%s signals=%d]",
            domain, result.confidence, len(result.signals),
        )
        confirmed.append(domain)

        # 5. Push
        if push_company(domain, token):
            pushed_count += 1
            log.info("Pushed to CRM: %s", domain)
        else:
            log.warning("CRM push failed: %s", domain)

    # 6. Log
    log_run(
        query=query,
        found=len(domains),
        live=len(live_domains),
        passed_dedup=len(new_domains),
        confirmed=len(confirmed),
        pushed=pushed_count,
    )

    increment_run_index()
    log.info(
        "Run #%d complete — found=%d live=%d dedup=%d confirmed=%d pushed=%d",
        run_idx,
        len(domains),
        len(live_domains),
        len(new_domains),
        len(confirmed),
        pushed_count,
    )


if __name__ == "__main__":
    run()
