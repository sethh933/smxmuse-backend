"""Career totals shared by the live rider profile and static HTML build."""
import re
import unicodedata

from sqlalchemy import text

SPORTS = (("SX", "Supercross"), ("MX", "Motocross"),
          ("SMX", "SuperMotocross"), ("WMX", "Women's Motocross"))


def career_overviews(conn, rider_id=None):
    # Select the existing combined career rows, never sum season/class subtotals.
    queries = []
    for code, _ in SPORTS:
        average = "AvgMainResult" if code == "SX" else "AvgOverallFinish"
        total = "SportID = 4" if code == "WMX" else "ClassID = 0"
        queries.append(f"""
            SELECT RiderID, '{code}' AS Sport, Starts, Wins, Podiums,
                   {average} AS AverageFinish
            FROM dbo.RiderProfile{code}StatsSummary
            WHERE [Year] IS NULL AND {total}
            {"AND RiderID = :rider_id" if rider_id is not None else ""}
        """)
    rows = conn.execute(text(" UNION ALL ".join(queries)),
                        {"rider_id": rider_id} if rider_id is not None else {}).mappings()
    grouped = {}
    for row in rows:
        if not row["Starts"]:
            continue
        grouped.setdefault(int(row["RiderID"]), []).append({
            "code": row["Sport"], "label": dict(SPORTS)[row["Sport"]],
            "starts": int(row["Starts"]), "wins": int(row["Wins"]),
            "podiums": int(row["Podiums"]),
            "averageFinish": float(row["AverageFinish"]) if row["AverageFinish"] is not None else None,
        })
    order = {code: index for index, (code, _) in enumerate(SPORTS)}
    for overview in grouped.values():
        overview.sort(key=lambda row: order[row["code"]])
    return grouped


def profile_metadata(rider_id, name, country, image, overview):
    name = name.strip()
    normalized = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
    slug = re.sub(r"[^a-z0-9]+", "-", normalized.replace("&", " and ")).strip("-")
    path = f"/rider/{slug}-{rider_id}" if slug else f"/rider/{rider_id}"
    disciplines = ", ".join(row["label"] for row in overview)
    description = (f"Explore {name}'s {disciplines + ' ' if disciplines else ''}career stats, "
                   "race results, wins, podiums, average finishes, and points standings on smxmuse.")
    person = {"@context": "https://schema.org", "@type": "Person", "name": name,
              "url": f"https://smxmuse.com{path}"}
    if country and country.strip():
        person["nationality"] = country.strip()
    if image and image.strip():
        person["image"] = image.strip()
    return {"title": f"{name} Career Stats and Race Results", "description": description,
            "path": path, "jsonLd": person}
