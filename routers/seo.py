import re
import unicodedata
from datetime import date, datetime
from urllib.parse import quote
from xml.etree import ElementTree as ET

from fastapi import APIRouter
from fastapi.responses import JSONResponse, Response
from sqlalchemy import text

from db import engine


router = APIRouter()

SITE_URL = "https://smxmuse.com"
SPORT_CODES = {1: "sx", 2: "mx", 3: "smx", 4: "wmx"}
TRACK_SPORT_CODES = {1: "SX", 2: "MX", 3: "SMX", 4: "WMX"}
STATIC_PATHS = (
    "/",
    "/about",
    "/riders",
    "/results",
    "/news",
    "/leaderboards",
    "/compare",
)

SPORT_LABELS = {1: "Supercross", 2: "Motocross", 3: "SMX", 4: "WMX"}


def _slugify(value):
    normalized = unicodedata.normalize("NFKD", str(value or ""))
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii").lower()
    ascii_value = ascii_value.replace("&", " and ")
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", ascii_value)).strip("-")


def _absolute_url(path):
    return f"{SITE_URL}{quote(path, safe='/:')}"


def _lastmod(value):
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return str(value) if value else None


def _add_url(urlset, path, last_modified=None):
    url = ET.SubElement(urlset, "url")
    ET.SubElement(url, "loc").text = _absolute_url(path)

    normalized_lastmod = _lastmod(last_modified)
    if normalized_lastmod:
        ET.SubElement(url, "lastmod").text = normalized_lastmod


def _page(
    path,
    title,
    description,
    heading=None,
    body=None,
    page_type="website",
    json_ld=None,
    image=None,
    schedule=None,
    result_sections=None,
):
    page = {
        "path": path,
        "title": title,
        "description": description,
        "heading": heading,
        "body": body or description,
        "type": page_type,
    }
    if json_ld:
        page["jsonLd"] = json_ld
    if image:
        page["image"] = image
    if schedule:
        page["schedule"] = schedule
    if result_sections:
        page["resultSections"] = result_sections
    return page


def build_prerender_manifest():
    """Return lightweight, route-specific HTML data for the frontend build."""
    with engine.connect() as conn:
        riders = conn.execute(text("""
            WITH Appearances AS (
                SELECT RiderID, RaceID FROM dbo.SX_MAINS
                UNION ALL SELECT RiderID, RaceID FROM dbo.MX_OVERALLS
                UNION ALL SELECT RiderID, RaceID FROM dbo.SMX_OVERALLS
                UNION ALL SELECT RiderID, RaceID FROM dbo.WMX_OVERALLS
            ),
            RiderActivity AS (
                SELECT appearances.RiderID,
                       COUNT(*) AS AppearanceCount,
                       MAX(races.RaceDate) AS LatestRaceDate
                FROM Appearances appearances
                INNER JOIN dbo.Race_Table races ON races.RaceID = appearances.RaceID
                GROUP BY appearances.RiderID
            ),
            RankedRiders AS (
                SELECT RiderID,
                       ROW_NUMBER() OVER (ORDER BY AppearanceCount DESC, RiderID DESC) AS CareerRank,
                       ROW_NUMBER() OVER (
                           ORDER BY LatestRaceDate DESC, AppearanceCount DESC, RiderID DESC
                       ) AS RecentRank
                FROM RiderActivity
            )
            SELECT rl.RiderID, rl.FullName, rl.Country, rl.ImageURL,
                   ranked.CareerRank, ranked.RecentRank
            FROM dbo.Rider_List rl
            INNER JOIN RankedRiders ranked ON ranked.RiderID = rl.RiderID
            WHERE rl.FullName IS NOT NULL
              AND LTRIM(RTRIM(rl.FullName)) <> ''
              AND (
                  EXISTS (
                      SELECT 1
                      FROM dbo.RiderProfileAvailabilitySummary availability
                      WHERE availability.RiderID = rl.RiderID
                        AND (availability.HasSX = 1 OR availability.HasMX = 1 OR availability.HasSMX = 1)
                  )
                  OR COALESCE(rl.WMX, 0) = 1
              )
        """)).mappings().all()

        races = conn.execute(text("""
            SELECT rt.RaceID, rt.[Year], rt.Round, rt.TrackName, rt.SportID,
                   rt.RaceDate, tt.City, tt.State,
                   ROW_NUMBER() OVER (ORDER BY rt.RaceDate DESC, rt.RaceID DESC) AS PrerenderRank
            FROM dbo.Race_Table rt
            LEFT JOIN dbo.TrackTable tt ON tt.TrackID = rt.TrackID
            WHERE rt.SportID IN (1, 2, 3, 4)
        """)).mappings().all()

        race_results = conn.execute(text("""
            WITH PrerenderRaces AS (
                SELECT RaceID
                FROM (
                    SELECT rt.RaceID,
                           ROW_NUMBER() OVER (
                               ORDER BY rt.RaceDate DESC, rt.RaceID DESC
                           ) AS PrerenderRank
                    FROM dbo.Race_Table rt
                    WHERE rt.SportID IN (1, 2, 3, 4)
                ) ranked
                WHERE ranked.PrerenderRank <= 350
            ), CombinedResults AS (
                SELECT sx.RaceID, 1 AS SportID, sx.ClassID,
                       TRY_CONVERT(int, sx.Result) AS FinishPosition,
                       sx.RiderID, COALESCE(rl.FullName, sx.FullName) AS FullName,
                       sx.Brand, NULL AS Moto1, NULL AS Moto2
                FROM dbo.SX_MAINS sx
                INNER JOIN PrerenderRaces pr ON pr.RaceID = sx.RaceID
                LEFT JOIN dbo.Rider_List rl ON rl.RiderID = sx.RiderID

                UNION ALL

                SELECT mx.RaceID, 2 AS SportID, mx.ClassID,
                       TRY_CONVERT(int, mx.Result) AS FinishPosition,
                       mx.RiderID, COALESCE(rl.FullName, mx.FullName) AS FullName,
                       mx.Brand, TRY_CONVERT(int, mx.Moto1), TRY_CONVERT(int, mx.Moto2)
                FROM dbo.MX_OVERALLS mx
                INNER JOIN PrerenderRaces pr ON pr.RaceID = mx.RaceID
                LEFT JOIN dbo.Rider_List rl ON rl.RiderID = mx.RiderID

                UNION ALL

                SELECT smx.RaceID, 3 AS SportID, smx.ClassID,
                       TRY_CONVERT(int, smx.Result) AS FinishPosition,
                       smx.RiderID, COALESCE(rl.FullName, smx.FullName) AS FullName,
                       smx.Brand, TRY_CONVERT(int, smx.Moto1), TRY_CONVERT(int, smx.Moto2)
                FROM dbo.SMX_OVERALLS smx
                INNER JOIN PrerenderRaces pr ON pr.RaceID = smx.RaceID
                LEFT JOIN dbo.Rider_List rl ON rl.RiderID = smx.RiderID

                UNION ALL

                SELECT wmx.RaceID, 4 AS SportID, 4 AS ClassID,
                       TRY_CONVERT(int, wmx.Result) AS FinishPosition,
                       wmx.RiderID, COALESCE(rl.FullName, wmx.FullName) AS FullName,
                       wmx.Brand, TRY_CONVERT(int, wmx.Moto1), TRY_CONVERT(int, wmx.Moto2)
                FROM dbo.WMX_OVERALLS wmx
                INNER JOIN PrerenderRaces pr ON pr.RaceID = wmx.RaceID
                LEFT JOIN dbo.Rider_List rl ON rl.RiderID = wmx.RiderID
                WHERE wmx.SportID = 4
            )
            SELECT RaceID, SportID, ClassID, FinishPosition, RiderID,
                   FullName, Brand, Moto1, Moto2
            FROM CombinedResults
            WHERE FinishPosition >= 1
              AND FullName IS NOT NULL
              AND LTRIM(RTRIM(FullName)) <> ''
            ORDER BY RaceID, ClassID, FinishPosition
        """)).mappings().all()

        tracks = conn.execute(text("""
            SELECT DISTINCT rt.TrackID, rt.TrackName, rt.SportID, tt.City, tt.State
            FROM dbo.Race_Table rt
            LEFT JOIN dbo.TrackTable tt ON tt.TrackID = rt.TrackID
            WHERE rt.SportID IN (1, 2, 3, 4)
              AND rt.TrackID IS NOT NULL
              AND rt.TrackName IS NOT NULL
              AND LTRIM(RTRIM(rt.TrackName)) <> ''
        """)).mappings().all()

        countries = conn.execute(text("""
            SELECT LTRIM(RTRIM(Country)) AS Country, COUNT(*) AS RiderCount
            FROM dbo.Rider_List
            WHERE Country IS NOT NULL AND LTRIM(RTRIM(Country)) <> ''
            GROUP BY LTRIM(RTRIM(Country))
        """)).mappings().all()

        result_years = conn.execute(text("""
            SELECT SportID, [Year]
            FROM dbo.Race_Table
            WHERE SportID IN (1, 2, 3, 4)
            GROUP BY SportID, [Year]
        """)).mappings().all()

        season_classes = conn.execute(text("""
            SELECT DISTINCT rt.SportID, rt.[Year], results.ClassID
            FROM dbo.Race_Table rt
            INNER JOIN (
                SELECT RaceID, ClassID FROM dbo.SX_MAINS
                UNION SELECT RaceID, ClassID FROM dbo.MX_OVERALLS
                UNION SELECT RaceID, ClassID FROM dbo.SMX_OVERALLS
                UNION SELECT RaceID, 0 AS ClassID FROM dbo.WMX_OVERALLS
            ) results ON results.RaceID = rt.RaceID
            WHERE rt.SportID IN (1, 2, 3, 4)
        """)).mappings().all()

        notes = conn.execute(text("""
            SELECT Slug, Title, Summary, PublishDate, UpdatedAt
            FROM dbo.ContentNotes
            WHERE Status = 'published'
              AND Slug IS NOT NULL AND LTRIM(RTRIM(Slug)) <> ''
        """)).mappings().all()

    pages = [
        _page("/", "Supercross, Motocross, SMX, and WMX Stats and Results",
              "Smxmuse is a Supercross, Motocross, SMX, and WMX stats archive with rider profiles, race results, season dashboards, comparisons, and all-time leaderboards.",
              "Everything in one place, from the latest gate drop to all-time history."),
        _page("/about", "About smxmuse",
              "Learn what smxmuse covers, how the Supercross, Motocross, SMX, and WMX stats archive was built, and where to send feedback or business inquiries."),
        _page("/riders", "Browse Riders",
              "Browse the full smxmuse rider archive by last name or country, including featured riders and country pages.", "Riders"),
        _page("/results", "Supercross, Motocross, SMX, and WMX Race Results Archive",
              "Browse Supercross, Motocross, SMX, and WMX race results by decade and season, then open full round-by-round result pages.", "Race Results"),
        _page("/news", "Supercross and Motocross News and Analysis",
              "Read smxmuse Supercross and Motocross race notes, previews, recaps, and data-driven analysis.", "Race Notes and Analysis"),
        _page("/leaderboards", "All-Time Supercross, Motocross, SMX, and WMX Leaderboards",
              "Browse all-time smxmuse leaderboards for wins, podiums, starts, and career milestones across Supercross, Motocross, SMX, and WMX.", "All Time Leaderboards"),
        _page("/compare", "Compare Supercross, Motocross, SMX, and WMX Riders",
              "Compare Supercross, Motocross, SMX, and WMX riders head to head across career wins, podiums, starts, championships, and season statistics.", "Rider Comparison"),
    ]

    races_by_season = {}
    race_paths = {}
    for race in races:
        sport_id = int(race["SportID"])
        display_name = race["City"] if sport_id == 1 and race["City"] else race["TrackName"]
        slug = _slugify(f"{display_name} {race['Year']}")
        race_path = f"/race/{slug}-{race['RaceID']}" if slug else f"/race/{race['RaceID']}"
        race_paths[int(race["RaceID"])] = race_path
        races_by_season.setdefault((sport_id, int(race["Year"])), []).append({
            "raceId": int(race["RaceID"]),
            "round": race["Round"],
            "track": race["TrackName"],
            "location": ", ".join(value for value in (race["City"], race["State"]) if value),
            "date": _lastmod(race["RaceDate"]),
            "href": race_path,
        })

    results_by_race = {}
    for result in race_results:
        race_id = int(result["RaceID"])
        class_id = int(result["ClassID"])
        rider_name = result["FullName"].strip()
        rider_slug = _slugify(rider_name)
        rider_path = (
            f"/rider/{rider_slug}-{result['RiderID']}"
            if rider_slug else f"/rider/{result['RiderID']}"
        )
        results_by_race.setdefault(race_id, {}).setdefault(class_id, []).append({
            "position": int(result["FinishPosition"]),
            "rider": rider_name,
            "riderHref": rider_path,
            "brand": result["Brand"] or "",
            "moto1": result["Moto1"],
            "moto2": result["Moto2"],
        })

    for season_races in races_by_season.values():
        for race in season_races:
            winners = []
            for class_id, rows in sorted(results_by_race.get(race["raceId"], {}).items()):
                winner = next((row for row in rows if row["position"] == 1), None)
                if winner:
                    winners.append({
                        "class": {1: "450", 2: "250", 3: "500", 4: "WMX"}.get(
                            class_id, f"Class {class_id}"
                        ),
                        "rider": winner["rider"],
                        "riderHref": winner["riderHref"],
                    })
            race["winners"] = winners

    for rider in riders:
        # Azure Static Web Apps currently has unreliable production distribution
        # with large directory counts. Keep both the all-time leaders and the
        # most recently active riders in the static prerender set.
        if int(rider["CareerRank"]) > 600 and int(rider["RecentRank"]) > 350:
            continue
        name = rider["FullName"].strip()
        rider_image = rider["ImageURL"].strip() if rider["ImageURL"] else None
        slug = _slugify(name)
        path = f"/rider/{slug}-{rider['RiderID']}" if slug else f"/rider/{rider['RiderID']}"
        description = (
            f"Explore {name}'s career stats, results history, and championship history "
            "on smxmuse."
        )
        person = {"@context": "https://schema.org", "@type": "Person", "name": name, "url": _absolute_url(path)}
        if rider["Country"]:
            person["nationality"] = rider["Country"].strip()
        if rider_image:
            person["image"] = rider_image
        pages.append(_page(
            path,
            f"{name} Rider Profile and Career Stats",
            description,
            name,
            page_type="profile",
            json_ld=person,
            image=rider_image,
        ))

        # Use the remaining Azure deployment headroom for the most valuable
        # rider detail routes, which target high-intent results and standings
        # searches and otherwise depend on client-side canonical injection.
        if int(rider["CareerRank"]) <= 100 or int(rider["RecentRank"]) <= 50:
            results_path = f"{path}/results"
            results_description = (
                f"Browse {name}'s race-by-race Supercross and Motocross career results, "
                "including track history and filtered event results."
            )
            pages.append(_page(
                results_path,
                f"{name} Career Results",
                results_description,
                name,
                results_description,
                page_type="profile",
                image=rider_image,
            ))

            points_path = f"{path}/points"
            points_description = (
                f"View {name}'s Supercross, Motocross, SMX, and WMX championship "
                "finishes and points standings history on smxmuse."
            )
            pages.append(_page(
                points_path,
                f"{name} Points Standings History",
                points_description,
                name,
                points_description,
                page_type="profile",
                image=rider_image,
            ))

    for race in races:
        if int(race["PrerenderRank"]) > 350:
            continue
        sport = SPORT_LABELS[int(race["SportID"])]
        display_name = race["City"] if int(race["SportID"]) == 1 and race["City"] else race["TrackName"]
        path = race_paths[int(race["RaceID"])]
        description = f"View round {race['Round']} results, race data, and class breakdowns from {display_name} in the {race['Year']} {sport} season."
        event = {
            "@context": "https://schema.org", "@type": "SportsEvent",
            "name": f"{race['Year']} {display_name} {sport}", "sport": sport,
            "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode", "url": _absolute_url(path),
        }
        if race["RaceDate"]:
            event["startDate"] = _lastmod(race["RaceDate"])
        if race["City"] or race["State"]:
            address = {"@type": "PostalAddress"}
            if race["City"]:
                address["addressLocality"] = race["City"]
            if race["State"]:
                address["addressRegion"] = race["State"]
            event["location"] = {
                "@type": "Place",
                "name": race["TrackName"],
                "address": address,
            }
        result_sections = []
        for class_id, rows in sorted(results_by_race.get(int(race["RaceID"]), {}).items()):
            class_label = {1: "450", 2: "250", 3: "500", 4: "WMX"}.get(class_id, f"Class {class_id}")
            session_label = "Main Event Results" if int(race["SportID"]) == 1 else "Overall Results"
            result_sections.append({
                "heading": f"{class_label} {session_label}",
                "rows": rows,
                "showMotos": int(race["SportID"]) != 1,
            })

        if int(race["SportID"]) == 2:
            class_names = [section["heading"].removesuffix(" Overall Results") for section in result_sections]
            class_suffix = f" - {' & '.join(class_names)}" if class_names else ""
            title = f"{race['Year']} {display_name} Pro Motocross Results{class_suffix}"
            heading = f"{race['Year']} {display_name} Pro Motocross Results"
        else:
            title = f"{race['Year']} {display_name} {sport} Results"
            heading = f"{race['Year']} {display_name} {sport} Results"

        pages.append(_page(
            path, title, description, heading,
            page_type="article", json_ld=event, result_sections=result_sections,
        ))

    for track in tracks:
        sport_id = int(track["SportID"])
        sport = SPORT_LABELS[sport_id]
        slug = _slugify(track["TrackName"])
        segment = f"{slug}-{track['TrackID']}" if slug else str(track["TrackID"])
        path = f"/track/{TRACK_SPORT_CODES[sport_id]}/{segment}"
        location = ", ".join(value for value in (track["City"], track["State"]) if value)
        body = f"Explore {track['TrackName']} {sport} winners, starts, podiums, and track history."
        if location:
            body += f" The venue is located in {location}."
        pages.append(_page(path, f"{track['TrackName']} {sport} Track History",
                           f"View {track['TrackName']} winners, starts, podiums, and track history for {sport} on smxmuse.", track["TrackName"], body))

    for country in countries:
        name = country["Country"]
        path = f"/riders/{quote(name, safe='')}"
        pages.append(_page(path, f"{name} Riders",
                           f"Browse rider profiles from {name} in the smxmuse Supercross and Motocross archive.", name,
                           f"Browse {country['RiderCount']} rider profiles from {name}."))

    for row in result_years:
        sport_id = int(row["SportID"])
        sport_code = SPORT_CODES[sport_id]
        sport = SPORT_LABELS[sport_id]
        year = int(row["Year"])
        schedule = sorted(
            races_by_season.get((sport_id, year), []),
            key=lambda item: (item["round"] is None, item["round"] or 0),
        )
        title = f"{year} AMA Pro Motocross Results, Schedule & Winners" if sport_id == 2 else f"{year} {sport} Results"
        heading = f"{year} Pro Motocross Results" if sport_id == 2 else f"{year} {sport} Results"
        pages.append(_page(
            f"/results/{sport_code}/{year}", title,
            f"Browse every round from the {year} {sport} season, plus season champions and the full archive schedule.",
            heading, schedule=schedule,
        ))

    for path in sorted(_season_paths(season_classes)):
        _, _, sport_code, year, class_slug = path.split("/")
        sport = SPORT_LABELS[{"sx": 1, "mx": 2, "smx": 3, "wmx": 4}[sport_code]]
        class_label = {"250W": "250 West", "250E": "250 East", "wmx": ""}.get(class_slug, class_slug)
        label = f"{class_label} {sport}".strip()
        pages.append(_page(path, f"{year} {label} Season Dashboard",
                           f"Explore {year} {label} standings, stats, laps led, and championship progression on smxmuse.",
                           f"{year} {label}"))

    for note in notes:
        path = f"/news/{note['Slug']}"
        description = (note["Summary"] or f"Read {note['Title']} on smxmuse.").strip()
        article = {
            "@context": "https://schema.org", "@type": "BlogPosting", "headline": note["Title"],
            "description": description, "url": _absolute_url(path),
            "author": {"@type": "Organization", "name": "smxmuse"},
        }
        if note["PublishDate"]:
            article["datePublished"] = _lastmod(note["PublishDate"])
        if note["UpdatedAt"]:
            article["dateModified"] = _lastmod(note["UpdatedAt"])
        pages.append(_page(path, note["Title"], description, note["Title"], page_type="article", json_ld=article))

    return pages


def _season_paths(rows):
    paths = set()

    for row in rows:
        sport_id = int(row["SportID"])
        class_id = int(row["ClassID"])
        year = int(row["Year"])
        sport = SPORT_CODES.get(sport_id)

        if not sport:
            continue

        if sport_id == 4:
            class_slugs = ("wmx",)
        elif class_id == 1:
            class_slugs = ("450",)
        elif class_id == 2 and sport_id == 1:
            class_slugs = ("250W", "250E")
        elif class_id == 2:
            class_slugs = ("250",)
        elif class_id == 3:
            class_slugs = ("500",)
        else:
            continue

        for class_slug in class_slugs:
            paths.add(f"/season/{sport}/{year}/{class_slug}")

    return paths


def build_sitemap_xml():
    with engine.connect() as conn:
        riders = conn.execute(text("""
            SELECT rl.RiderID, rl.FullName
            FROM dbo.Rider_List rl
            WHERE rl.FullName IS NOT NULL
              AND LTRIM(RTRIM(rl.FullName)) <> ''
              AND (
                  EXISTS (
                      SELECT 1
                      FROM dbo.RiderProfileAvailabilitySummary availability
                      WHERE availability.RiderID = rl.RiderID
                        AND (
                            availability.HasSX = 1
                            OR availability.HasMX = 1
                            OR availability.HasSMX = 1
                        )
                  )
                  OR COALESCE(rl.WMX, 0) = 1
              )
        """)).mappings().all()

        races = conn.execute(text("""
            SELECT
                rt.RaceID,
                rt.[Year],
                rt.TrackName,
                rt.SportID,
                rt.RaceDate,
                tt.City
            FROM dbo.Race_Table rt
            LEFT JOIN dbo.TrackTable tt ON tt.TrackID = rt.TrackID
            WHERE rt.SportID IN (1, 2, 3, 4)
        """)).mappings().all()

        tracks = conn.execute(text("""
            SELECT DISTINCT TrackID, TrackName, SportID
            FROM dbo.Race_Table
            WHERE SportID IN (1, 2, 3, 4)
              AND TrackID IS NOT NULL
              AND TrackName IS NOT NULL
              AND LTRIM(RTRIM(TrackName)) <> ''
        """)).mappings().all()

        countries = conn.execute(text("""
            SELECT DISTINCT LTRIM(RTRIM(Country)) AS Country
            FROM dbo.Rider_List
            WHERE Country IS NOT NULL
              AND LTRIM(RTRIM(Country)) <> ''
        """)).mappings().all()

        result_years = conn.execute(text("""
            SELECT SportID, [Year], MAX(RaceDate) AS LastRaceDate
            FROM dbo.Race_Table
            WHERE SportID IN (1, 2, 3, 4)
            GROUP BY SportID, [Year]
        """)).mappings().all()

        season_classes = conn.execute(text("""
            SELECT DISTINCT rt.SportID, rt.[Year], results.ClassID
            FROM dbo.Race_Table rt
            INNER JOIN (
                SELECT RaceID, ClassID FROM dbo.SX_MAINS
                UNION
                SELECT RaceID, ClassID FROM dbo.MX_OVERALLS
                UNION
                SELECT RaceID, ClassID FROM dbo.SMX_OVERALLS
                UNION
                SELECT RaceID, 0 AS ClassID FROM dbo.WMX_OVERALLS
            ) results ON results.RaceID = rt.RaceID
            WHERE rt.SportID IN (1, 2, 3, 4)
        """)).mappings().all()

        notes = conn.execute(text("""
            SELECT Slug, PublishDate, UpdatedAt
            FROM dbo.ContentNotes
            WHERE Status = 'published'
              AND Slug IS NOT NULL
              AND LTRIM(RTRIM(Slug)) <> ''
        """)).mappings().all()

    ET.register_namespace("", "http://www.sitemaps.org/schemas/sitemap/0.9")
    urlset = ET.Element("{http://www.sitemaps.org/schemas/sitemap/0.9}urlset")

    for path in STATIC_PATHS:
        _add_url(urlset, path)

    for rider in riders:
        rider_id = rider["RiderID"]
        slug = _slugify(rider["FullName"])
        segment = f"{slug}-{rider_id}" if slug else str(rider_id)
        _add_url(urlset, f"/rider/{segment}")
        _add_url(urlset, f"/rider/{segment}/results")
        _add_url(urlset, f"/rider/{segment}/points")

    for race in races:
        race_id = race["RaceID"]
        label = race["City"] if race["SportID"] == 1 and race["City"] else race["TrackName"]
        slug = _slugify(f"{label} {race['Year']}")
        segment = f"{slug}-{race_id}" if slug else str(race_id)
        _add_url(urlset, f"/race/{segment}", race["RaceDate"])

    for track in tracks:
        sport = TRACK_SPORT_CODES.get(int(track["SportID"]))
        slug = _slugify(track["TrackName"])
        segment = f"{slug}-{track['TrackID']}" if slug else str(track["TrackID"])
        _add_url(urlset, f"/track/{sport}/{segment}")

    for country in countries:
        _add_url(urlset, f"/riders/{country['Country']}")

    for result_year in result_years:
        sport = SPORT_CODES.get(int(result_year["SportID"]))
        if sport:
            _add_url(
                urlset,
                f"/results/{sport}/{result_year['Year']}",
                result_year["LastRaceDate"],
            )

    for path in sorted(_season_paths(season_classes)):
        _add_url(urlset, path)

    for note in notes:
        _add_url(urlset, f"/news/{note['Slug']}", note["UpdatedAt"] or note["PublishDate"])

    return ET.tostring(urlset, encoding="utf-8", xml_declaration=True)


@router.get("/sitemap.xml", include_in_schema=False)
def sitemap():
    return Response(
        content=build_sitemap_xml(),
        media_type="application/xml",
        headers={"Cache-Control": "public, max-age=3600"},
    )


@router.get("/seo/prerender.json", include_in_schema=False)
def prerender_manifest():
    pages = build_prerender_manifest()
    return JSONResponse(
        content={"generatedAt": datetime.utcnow().isoformat() + "Z", "pages": pages},
        headers={"Cache-Control": "public, max-age=3600"},
    )
