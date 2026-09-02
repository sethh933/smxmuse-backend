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


def class_title(year, class_id):
    class_name = "450MX" if class_id == 1 else "250MX"
    return f"{year} {class_name} Championship"


def fetch_rows(year, sport_id, class_id):
    standings_query = text(
        """
        SELECT
            s.RiderID,
            s.FullName,
            s.[Year],
            s.ClassID,
            s.ClassRound,
            s.OverallRound,
            s.RaceID,
            s.RaceDate,
            s.RunningPoints,
            s.AdjustmentPoints,
            s.TotalPoints,
            s.ChampionshipPosition,
            rl.Country,
            rl.ImageURL
        FROM dbo.vw_MX_RunningStandings s
        LEFT JOIN dbo.Rider_List rl
            ON rl.RiderID = s.RiderID
        WHERE s.[Year] = :year
          AND s.ClassID = :class_id
        ORDER BY
            s.ClassRound,
            s.ChampionshipPosition,
            s.TotalPoints DESC,
            s.FullName
        """
    )
    brand_query = text(
        """
        SELECT
            RiderID,
            MIN(Brand) AS Brand
        FROM dbo.RiderBrandListYear
        WHERE [Year] = :year
          AND SportID = :sport_id
          AND ClassID = :class_id
        GROUP BY RiderID
        """
    )

    with engine.begin() as conn:
        standings = [dict(row._mapping) for row in conn.execute(
            standings_query,
            {"year": year, "class_id": class_id},
        )]
        brands = [dict(row._mapping) for row in conn.execute(
            brand_query,
            {"year": year, "sport_id": sport_id, "class_id": class_id},
        )]

    return standings, brands


def build_payload(standings, brands, year, sport_id, class_id):
    brand_by_rider = {
        row["RiderID"]: normalize_brand(row["Brand"])
        for row in brands
        if row.get("Brand")
    }
    riders_by_id = {}
    rounds = {}

    for row in standings:
        rider_id = row["RiderID"]
        rider_key = str(rider_id)
        brand = brand_by_rider.get(rider_id, "YAM")

        if rider_id not in riders_by_id:
            riders_by_id[rider_id] = {
                "riderKey": rider_key,
                "riderId": rider_id,
                "name": row["FullName"],
                "manufacturer": brand,
                "manufacturerLogo": brand,
                "image": clean_url(row.get("ImageURL")),
                "country": row.get("Country") or "",
                "color": BRAND_COLORS.get(brand, "#8b95a7"),
                "finalPoints": 0,
            }

        points = int(row["TotalPoints"] or 0)
        riders_by_id[rider_id]["finalPoints"] = max(riders_by_id[rider_id]["finalPoints"], points)

        round_number = int(row["ClassRound"])
        rounds.setdefault(
            round_number,
            {
                "round": round_number,
                "date": row["RaceDate"].isoformat() if row.get("RaceDate") else None,
                "standings": [],
            },
        )
        rounds[round_number]["standings"].append(
            {
                "riderId": rider_id,
                "riderKey": rider_key,
                "points": points,
            }
        )

    return {
        "title": class_title(year, class_id),
        "subtitle": f"{year} ClassID {class_id} / SportID {sport_id} points standings",
        "season": year,
        "sportId": sport_id,
        "classId": class_id,
        "source": "vw_MX_RunningStandings TotalPoints joined to RiderBrandListYear",
        "rounds": [rounds[key] for key in sorted(rounds)],
        "riders": sorted(riders_by_id.values(), key=lambda rider: (-rider["finalPoints"], rider["name"])),
    }


def main():
    parser = argparse.ArgumentParser(description="Export MX running standings for Remotion.")
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--sport-id", type=int, default=2)
    parser.add_argument("--class-id", type=int, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    standings, brands = fetch_rows(args.year, args.sport_id, args.class_id)
    payload = build_payload(standings, brands, args.year, args.sport_id, args.class_id)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {len(payload['rounds'])} rounds and {len(payload['riders'])} riders to {args.out}")


if __name__ == "__main__":
    main()
