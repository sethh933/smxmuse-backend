"""Read-only integration check against the configured database.

Run from the repo root: python scripts/check_rider_seo.py
Compares new summaries to the existing detailed stats for one-result riders
in every discipline, plus Jett, and checks static/live metadata agreement.
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from db import engine
from rider_seo import career_overviews
from routers.riders import get_rider_profile
from routers.seo import build_prerender_manifest


def check():
    with engine.connect() as conn:
        summaries = career_overviews(conn)
    rider_ids = {1755}
    fields = {"SX": ("stats", "AvgMainResult"),
              "MX": ("mx_stats", "AvgOverallFinish"),
              "SMX": ("smx_stats", "AvgOverallFinish"),
              "WMX": ("wmx_stats", "AvgOverallFinish")}
    for code in fields:
        rider_ids.add(next(rider_id for rider_id, rows in summaries.items()
                          if any(row["code"] == code and row["starts"] == 1 for row in rows)))
    pages = {page["path"]: page for page in build_prerender_manifest()}
    for rider_id in sorted(rider_ids):
        for summary in summaries[rider_id]:
            payload = get_rider_profile(rider_id, summary["code"])
            field, average = fields[summary["code"]]
            total = next(row for row in payload[field] if row["Year"] is None
                         and (row.get("ClassID") == 0 or row["Class"] is None))
            expected = (total["Starts"], total["Wins"], total["Podiums"],
                        float(total[average]) if total[average] is not None else None)
            actual = tuple(summary[key] for key in ("starts", "wins", "podiums", "averageFinish"))
            assert actual == expected, (rider_id, summary["code"], actual, expected)
            metadata = payload["profileSeo"]
            if metadata["path"] in pages:
                page = pages[metadata["path"]]
                assert page["careerOverview"] == payload["careerOverview"]
                assert all(page[key] == metadata[key] for key in ("title", "description", "jsonLd"))
        print(f"PASS: rider {rider_id} career totals and metadata")
    print(f"PASS: {len(pages)} prerender routes")


if __name__ == "__main__":
    check()
