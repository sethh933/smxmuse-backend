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


def normalize_brand(value):
    if not value:
        return None

    brand = str(value).strip().upper()
    if brand.startswith("HON"):
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
        "GERMANY": "DE",
        "SPAIN": "ES",
        "FRANCE": "FR",
        "GREAT BRITAIN": "GB",
        "UNITED KINGDOM": "GB",
        "JAPAN": "JP",
        "NEW ZEALAND": "NZ",
    }
    return country_map.get(country, country[:2])


def rider_key(row, class_id):
    rider_coast_id = row.get("RiderCoastID")
    suffix = rider_coast_id if rider_coast_id is not None else class_id
    return f"{row['RiderID']}-{suffix}"


def build_title(year, class_id, rider_coast_id):
    if class_id == 1:
        return f"{year} 450SX Laps Led"

    coast = "West" if rider_coast_id == 1 else "East" if rider_coast_id == 2 else "250SX"
    return f"{year} 250SX {coast} Laps Led"


def fetch_leader_laps(year, class_id, rider_coast_id):
    coast_filter = ""
    if rider_coast_id is not None:
        coast_filter = """
          AND COALESCE(sms.ridercoastid, sm.RiderCoastID, cp.RiderCoastID) = :rider_coast_id
        """

    query = text(f"""
        WITH LeaderRows AS (
            SELECT
                rt.[Year],
                rt.SportID,
                rt.[Round],
                rt.RaceDate,
                sms.raceid AS RaceID,
                sms.classid AS ClassID,
                COALESCE(sms.ridercoastid, sm.RiderCoastID, cp.RiderCoastID) AS RiderCoastID,
                sms.TCmain AS TCMain,
                sms.LAP AS Lap,
                sms.riderid AS RiderID,
                MAX(sms.FullName) AS FullName,
                MAX(rl.Country) AS Country,
                MAX(rl.ImageURL) AS ImageURL,
                COALESCE(
                    NULLIF(MAX(sms.Bike), ''),
                    NULLIF(MAX(sm.Brand), '')
                ) AS Brand
            FROM dbo.SX_MAIN_SEGMENTS sms
            JOIN dbo.Race_Table rt
                ON rt.RaceID = sms.raceid
            LEFT JOIN dbo.SX_MAINS sm
                ON sm.RaceID = sms.raceid
               AND sm.ClassID = sms.classid
               AND sm.RiderID = sms.riderid
            LEFT JOIN dbo.CoastPool cp
                ON cp.RiderID = sms.riderid
               AND cp.[Year] = rt.[Year]
            LEFT JOIN dbo.Rider_List rl
                ON rl.RiderID = sms.riderid
            WHERE rt.[Year] = :year
              AND rt.SportID = 1
              AND sms.sportid = 1
              AND sms.classid = :class_id
              AND sms.position = 1
              {coast_filter}
            GROUP BY
                rt.[Year],
                rt.SportID,
                rt.[Round],
                rt.RaceDate,
                sms.raceid,
                sms.classid,
                COALESCE(sms.ridercoastid, sm.RiderCoastID, cp.RiderCoastID),
                sms.TCmain,
                sms.LAP,
                sms.riderid
        )
        SELECT *
        FROM LeaderRows
        ORDER BY [Round], RaceDate, RaceID, COALESCE(TCMain, 1), Lap, RiderID
    """)

    params = {
        "year": year,
        "class_id": class_id,
        "rider_coast_id": rider_coast_id,
    }

    with engine.begin() as conn:
        return [dict(row._mapping) for row in conn.execute(query, params)]


def build_payload(rows, year, class_id, rider_coast_id):
    riders = {}
    cumulative = {}
    frames = []

    for index, row in enumerate(rows, start=1):
        key = rider_key(row, class_id)
        brand = normalize_brand(row.get("Brand"))

        riders[key] = {
            "riderId": row["RiderID"],
            "riderKey": key,
            "name": row["FullName"],
            "countryCode": normalize_country(row.get("Country")),
            "manufacturerLogo": brand,
            "image": row.get("ImageURL"),
            "color": BRAND_COLORS.get(brand, "#8b95a7"),
        }

        cumulative[key] = cumulative.get(key, 0) + 1
        standings = [
            {"riderKey": rider_key_value, "lapsLed": laps_led}
            for rider_key_value, laps_led in sorted(
                cumulative.items(),
                key=lambda item: (-item[1], riders[item[0]]["name"], item[0]),
            )
        ]

        frames.append({
            "sequence": index,
            "round": row["Round"],
            "raceId": row["RaceID"],
            "raceDate": row["RaceDate"].isoformat() if row.get("RaceDate") else None,
            "tcMain": row.get("TCMain"),
            "lap": row["Lap"],
            "leaderKey": key,
            "leaderName": row["FullName"],
            "totalLapsLed": index,
            "standings": standings,
        })

    ordered_riders = sorted(
        riders.values(),
        key=lambda rider: (-cumulative.get(rider["riderKey"], 0), rider["name"]),
    )

    return {
        "title": build_title(year, class_id, rider_coast_id),
        "subtitle": "Cumulative lap leaders by lap in chronological season order",
        "season": year,
        "sportId": 1,
        "classId": class_id,
        "riderCoastId": rider_coast_id,
        "source": "SX_MAIN_SEGMENTS position = 1 joined to Race_Table round order",
        "frames": frames,
        "riders": ordered_riders,
    }


def main():
    parser = argparse.ArgumentParser(description="Export SX lap-leader progression for Remotion.")
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--class-id", type=int, required=True)
    parser.add_argument("--rider-coast-id", type=int, default=None)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    rows = fetch_leader_laps(args.year, args.class_id, args.rider_coast_id)
    payload = build_payload(rows, args.year, args.class_id, args.rider_coast_id)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {len(payload['frames'])} lap snapshots to {args.out}")


if __name__ == "__main__":
    main()
