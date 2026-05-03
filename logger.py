"""
Run logger — appends one CSV row to run_log.csv after every completed run.
Columns: timestamp, query, found, passed_dedup, confirmed, pushed
"""

import csv
from datetime import datetime, timezone
from pathlib import Path

LOG_FILE = Path("run_log.csv")
FIELDNAMES = ["timestamp", "query", "found", "passed_dedup", "confirmed", "pushed"]


def log_run(
    *,
    query: str,
    found: int,
    passed_dedup: int,
    confirmed: int,
    pushed: int,
) -> None:
    """Append one row to run_log.csv. Creates the file with a header if it doesn't exist."""
    write_header = not LOG_FILE.exists()
    with open(LOG_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        if write_header:
            writer.writeheader()
        writer.writerow(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "query": query,
                "found": found,
                "passed_dedup": passed_dedup,
                "confirmed": confirmed,
                "pushed": pushed,
            }
        )
