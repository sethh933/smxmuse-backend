import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
import sys

from sqlalchemy import text

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from db import engine


BRAND_COLORS = {
    "HON": "#d71920",
    "HRC": "#d71920",
    "YAM": "#2f6df6",
    "KAW": "#67be23",
    "KTM": "#f27a1a",
    "HUS": "#f2f6fb",
    "GAS": "#c8102e",
    "SUZ": "#f6d928",
    "DUC": "#c21807",
    "TRI": "#2b68b8",
    "CAN": "#f15a24",
    "CZ": "#0f6db5",
    "BUL": "#b21f2d",
}


def clean_url(url):
    if not url:
        return ""

    value = str(url).strip()
    if value.startswith("//"):
        return f"https:{value}"

    return value


def normalize_brand(value):
    if not value:
        return None

    brand = str(value).strip().upper()
    if brand.startswith("HON") or brand == "HRC":
        return "HON"
    if brand.startswith("YAM"):
        return "YAM"
    if brand.startswith("KAW"):
        return "KAW"
    if brand.startswith("KTM"):
        return "KTM"
    if brand.startswith("HUS"):
        return "HUS"
    if brand.startswith("GAS"):
        return "GAS"
    if brand.startswith("SUZ"):
        return "SUZ"
    if brand.startswith("DUC"):
        return "DUC"
    if brand.startswith("TRI"):
        return "TRI"

    return brand[:3]


def normalize_country(value):
    if not value:
        return None

    country = str(value).strip().upper()
    country_map = {
        "ARGENTINA": "ar",
        "AUSTRALIA": "au",
        "AUSTRIA": "at",
        "BELGIUM": "be",
        "BRAZIL": "br",
        "CANADA": "ca",
        "CHILE": "cl",
        "CZECH REPUBLIC": "cz",
        "ECUADOR": "ec",
        "FRANCE": "fr",
        "GERMANY": "de",
        "GREAT BRITAIN": "gb",
        "ITALY": "it",
        "JAPAN": "jp",
        "NETHERLANDS": "nl",
        "NEW ZEALAND": "nz",
        "SCOTLAND": "gb-sct",
        "SOUTH AFRICA": "za",
        "SPAIN": "es",
        "SWEDEN": "se",
        "SWITZERLAND": "ch",
        "UNITED KINGDOM": "gb",
        "UNITED STATES": "us",
        "USA": "us",
    }
    return country_map.get(country)


def fetch_wins(class_id):
    query = text(
        """
        SELECT
            rt.[Year],
            rt.[Round],
            rt.RaceDate,
            rt.RaceID,
            rt.TrackName,
            m.MainID,
            m.RiderID,
            COALESCE(rl.FullName, m.FullName) AS FullName,
            rl.Country,
            rl.ImageURL,
            m.Brand
        FROM dbo.SX_MAINS m
        JOIN dbo.Race_Table rt
            ON rt.RaceID = m.RaceID
        LEFT JOIN dbo.Rider_List rl
            ON rl.RiderID = m.RiderID
        WHERE m.Result = 1
          AND m.SportID = 1
          AND m.ClassID = :class_id
        ORDER BY
            rt.RaceDate,
            rt.[Year],
            rt.[Round],
            rt.RaceID,
            m.MainID
        """
    )

    with engine.begin() as conn:
        return [dict(row._mapping) for row in conn.execute(query, {"class_id": class_id})]


def build_payload(rows, class_id):
    cumulative = defaultdict(int)
    brand_counts = defaultdict(Counter)
    rider_info = {}
    events = []

    for index, row in enumerate(rows, start=1):
        rider_key = str(row["RiderID"])
        brand = normalize_brand(row.get("Brand"))

        cumulative[rider_key] += 1
        if brand:
            brand_counts[rider_key][brand] += 1

        rider_info.setdefault(
            rider_key,
            {
                "riderKey": rider_key,
                "riderId": row["RiderID"],
                "name": row["FullName"],
                "image": clean_url(row.get("ImageURL")),
                "country": row.get("Country") or "",
                "countryCode": normalize_country(row.get("Country")),
            },
        )

        standings = [
            {"riderKey": key, "wins": wins}
            for key, wins in sorted(
                cumulative.items(),
                key=lambda item: (-item[1], rider_info[item[0]]["name"], item[0]),
            )
        ]

        events.append(
            {
                "sequence": index,
                "year": row["Year"],
                "round": row["Round"],
                "raceDate": row["RaceDate"].isoformat() if row.get("RaceDate") else None,
                "raceId": row["RaceID"],
                "trackName": row["TrackName"],
                "winnerKey": rider_key,
                "winnerName": row["FullName"],
                "standings": standings,
            }
        )

    riders = []
    for rider_key, rider in rider_info.items():
        brand, _wins = brand_counts[rider_key].most_common(1)[0]
        riders.append(
            {
                **rider,
                "manufacturer": brand,
                "manufacturerLogo": brand,
                "color": BRAND_COLORS.get(brand, "#8b95a7"),
                "finalWins": cumulative[rider_key],
            }
        )

    return {
        "title": "Most 450SX Wins",
        "subtitle": "Cumulative Supercross ClassID 1 main event wins",
        "sportId": 1,
        "classId": class_id,
        "source": "SX_MAINS Result = 1, SportID = 1, ClassID = 1",
        "events": events,
        "riders": sorted(riders, key=lambda rider: (-rider["finalWins"], rider["name"])),
    }


def main():
    parser = argparse.ArgumentParser(description="Export all-time SX wins progression for Remotion.")
    parser.add_argument("--class-id", type=int, default=1)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    rows = fetch_wins(args.class_id)
    payload = build_payload(rows, args.class_id)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {len(payload['events'])} win events and {len(payload['riders'])} riders to {args.out}")


if __name__ == "__main__":
    main()
