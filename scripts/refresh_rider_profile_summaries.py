"""Refresh rider profile summary tables from raw SX/MX results data.

Run this after race imports, or on a scheduled cadence such as Saturday night:
    python scripts/refresh_rider_profile_summaries.py
"""

from pathlib import Path
import sys

import pyodbc

BASE_DIR = Path(__file__).resolve().parent.parent
SQL_PATH = BASE_DIR / "sql" / "refresh_rider_profile_summaries.sql"
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from db import CONN_STR


def _split_batches(sql_text: str):
    batches = []
    current = []

    for line in sql_text.splitlines():
        if line.strip().upper() == "GO":
            batch = "\n".join(current).strip()
            if batch:
                batches.append(batch)
            current = []
            continue
        current.append(line)

    final_batch = "\n".join(current).strip()
    if final_batch:
        batches.append(final_batch)

    return batches


def refresh_rider_profile_summaries():
    sql_text = SQL_PATH.read_text(encoding="utf-8")
    batches = _split_batches(sql_text)

    with pyodbc.connect(CONN_STR) as conn:
        conn.autocommit = False
        cursor = conn.cursor()

        for index, batch in enumerate(batches, start=1):
            print(f"Running batch {index}/{len(batches)}...")
            cursor.execute(batch)

            while cursor.nextset():
                pass

        conn.commit()

    print("Rider profile summary refresh complete.")


if __name__ == "__main__":
    refresh_rider_profile_summaries()
