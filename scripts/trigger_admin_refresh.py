"""Trigger the deployed SMXmuse refresh endpoint.

This is handy for manual midweek refreshes and for scheduled automations:
    python scripts/trigger_admin_refresh.py
"""

from pathlib import Path
import json
import sys
from urllib.request import Request, urlopen


BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from db import ADMIN_REFRESH_TOKEN, SMXMUSE_ADMIN_REFRESH_URL


def trigger_admin_refresh():
    if not SMXMUSE_ADMIN_REFRESH_URL:
        raise RuntimeError("SMXMUSE_ADMIN_REFRESH_URL is not configured.")

    if not ADMIN_REFRESH_TOKEN:
        raise RuntimeError("ADMIN_REFRESH_TOKEN is not configured.")

    request = Request(
        SMXMUSE_ADMIN_REFRESH_URL,
        method="POST",
        headers={"X-Admin-Token": ADMIN_REFRESH_TOKEN},
    )

    with urlopen(request, timeout=60) as response:
        body = response.read().decode("utf-8", errors="replace")

    try:
        parsed = json.loads(body)
    except json.JSONDecodeError:
        parsed = {"raw": body}

    print(json.dumps(parsed, indent=2))


if __name__ == "__main__":
    trigger_admin_refresh()
