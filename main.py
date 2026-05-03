"""
Orchestrates one full sourcing run:
  query → scrape → dedup → detect → push → log
"""

import logging

from auth import get_token
from dedup import filter_new_domains, mark_seen
from detect import run_detection
from logger import log_run
from push import push_company
from queries import increment_run_index, next_query
from scraper import scrape_domains

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)


def run() -> None:
    token = get_token()
    query, run_idx = next_query()
    log.info("Run #%d — query: %s", run_idx, query)

    # 1. Scrape
    domains = scrape_domains(query)
    log.info("Scraped %d domain(s)", len(domains))

    # 2. Dedup
    new_domains = filter_new_domains(domains, token)
    log.info("%d new domain(s) after dedup", len(new_domains))

    confirmed: list[str] = []
    pushed_count = 0

    for domain in new_domains:
        # 3. Detect
        result = run_detection(domain)

        # Always mark as seen so we never re-check this domain, regardless of outcome
        mark_seen(domain)

        if not result.uses_hubspot:
            log.info("Not HubSpot: %s", domain)
            continue

        log.info("Confirmed HubSpot: %s [confidence=%s]", domain, result.confidence)
        confirmed.append(domain)

        # 4. Push
        if push_company(domain, token):
            pushed_count += 1
            log.info("Pushed to CRM: %s", domain)
        else:
            log.warning("CRM push failed: %s", domain)

    # 5. Log
    log_run(
        query=query,
        found=len(domains),
        passed_dedup=len(new_domains),
        confirmed=len(confirmed),
        pushed=pushed_count,
    )

    increment_run_index()
    log.info(
        "Run #%d complete — found=%d dedup=%d confirmed=%d pushed=%d",
        run_idx,
        len(domains),
        len(new_domains),
        len(confirmed),
        pushed_count,
    )


if __name__ == "__main__":
    run()
