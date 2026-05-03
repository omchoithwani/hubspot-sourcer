"""
Runs main.run() every 5 minutes using the `schedule` library.
Executes one run immediately on startup, then ticks every 30 s to check the schedule.
"""

import logging
import time

import schedule

from main import run

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)


def _job() -> None:
    try:
        run()
    except Exception as exc:
        log.error("Run failed: %s", exc, exc_info=True)


schedule.every(5).minutes.do(_job)
log.info("Scheduler started — running every 5 minutes.")

_job()  # Run immediately on startup

while True:
    schedule.run_pending()
    time.sleep(30)
