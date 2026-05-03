"""
CLI entry point — runs one sourcing cycle using the next query from the bank.
For the web UI, run app.py instead.
"""

import logging

from queries import active_filter_summary, increment_run_index, next_query
from runner import run_search

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)


def run() -> None:
    query, run_idx = next_query()
    log.info("Run #%d — query: %s", run_idx, query)
    log.info("Active filters: %s", active_filter_summary())
    run_search(query)
    increment_run_index()


if __name__ == "__main__":
    run()
