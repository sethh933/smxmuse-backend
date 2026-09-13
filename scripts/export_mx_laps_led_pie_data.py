import argparse
import json
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
        "USA": "US",
        "UNITED STATES": "US",
        "AUSTRALIA": "AU",
        "BELGIUM": "BE",
        "CANADA": "CA",
        "DENMARK": "DK",
        "FRANCE": "FR",
        "GERMANY": "DE",
        "ITALY": "IT",
        "JAPAN": "JP",
        "NETHERLANDS": "NL",
        "NEW ZEALAND": "NZ",
        "NORWAY": "NO",
        "SPAIN": "ES",
        "SWEDEN": "SE",
        "SWITZERLAND": "CH",
        "VENEZUELA": "VE",
    }
    return country_map.get(country, country[:2])


def class_title(year, class_id):
    class_name = "450MX" if class_id == 1 else "250MX"
    return f"{year} {class_name} Laps Led"


def fetch_leader_laps(year, class_id):
    query = text(
        """
        WITH LeaderRows AS (
            SELECT
                rt.[Year],
                rt.SportID,
                rt.[Round],
                rt.RaceDate,
                mms.raceid AS RaceID,
                mms.classid AS ClassID,
                mms.Moto,
                mms.LAP AS Lap,
                mms.riderid AS RiderID,
                MAX(mms.FullName) AS FullName,
                MAX(rl.Country) AS Country,
                MAX(rl.ImageURL) AS ImageURL,
                NULLIF(MAX(mms.Bike), '') AS Brand
            FROM dbo.MX_MOTO_SEGMENTS mms
            JOIN dbo.Race_Table rt
                ON rt.RaceID = mms.raceid
            LEFT JOIN dbo.Rider_List rl
                ON rl.RiderID = mms.riderid
            WHERE rt.[Year] = :year
              AND rt.SportID = 2
              AND mms.sportid = 2
              AND mms.classid = :class_id
              AND mms.position = 1
            GROUP BY
                rt.[Year],
                rt.SportID,
                rt.[Round],
                rt.RaceDate,
                mms.raceid,
                mms.classid,
                mms.Moto,
                mms.LAP,
                mms.riderid
        )
        SELECT *
        FROM LeaderRows
        ORDER BY RaceDate, [Round], RaceID, Moto, Lap, RiderID
        """
    )

    with engine.begin() as conn:
        return [
            dict(row._mapping)
            for row in conn.execute(query, {"year": year, "class_id": class_id})
        ]


def build_payload(rows, year, class_id):
    riders = {}
    cumulative = {}
    frames = []

    for index, row in enumerate(rows, start=1):
        rider_key = str(row["RiderID"])
        brand = normalize_brand(row.get("Brand"))

        riders[rider_key] = {
            "riderId": row["RiderID"],
            "riderKey": rider_key,
            "name": row["FullName"],
            "country": row.get("Country") or "",
            "countryCode": normalize_country(row.get("Country")),
            "manufacturerLogo": brand,
            "image": clean_url(row.get("ImageURL")),
            "color": BRAND_COLORS.get(brand, "#8b95a7"),
        }

        cumulative[rider_key] = cumulative.get(rider_key, 0) + 1
        standings = [
            {"riderKey": key, "lapsLed": laps_led}
            for key, laps_led in sorted(
                cumulative.items(),
                key=lambda item: (-item[1], riders[item[0]]["name"], item[0]),
            )
        ]

        frames.append(
            {
                "sequence": index,
                "round": row["Round"],
                "raceId": row["RaceID"],
                "raceDate": row["RaceDate"].isoformat() if row.get("RaceDate") else None,
                "moto": row["Moto"],
                "lap": row["Lap"],
                "leaderKey": rider_key,
                "leaderName": row["FullName"],
                "totalLapsLed": index,
                "standings": standings,
            }
        )

    ordered_riders = sorted(
        riders.values(),
        key=lambda rider: (-cumulative.get(rider["riderKey"], 0), rider["name"]),
    )

    return {
        "title": class_title(year, class_id),
        "subtitle": "Cumulative lap leaders by lap in chronological season order",
        "season": year,
        "sportId": 2,
        "classId": class_id,
        "source": "MX_MOTO_SEGMENTS position = 1 ordered by Race_Table date, moto, and lap",
        "frames": frames,
        "riders": ordered_riders,
    }


def main():
    parser = argparse.ArgumentParser(description="Export MX lap-leader progression for Remotion.")
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--class-id", type=int, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    rows = fetch_leader_laps(args.year, args.class_id)
    payload = build_payload(rows, args.year, args.class_id)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {len(payload['frames'])} lap snapshots to {args.out}")


if __name__ == "__main__":
    main()
