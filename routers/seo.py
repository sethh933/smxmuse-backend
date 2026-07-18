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
SPORT_CODES = {1: "sx", 2: "mx", 3: "smx"}
TRACK_SPORT_CODES = {1: "SX", 2: "MX", 3: "SMX"}
STATIC_PATHS = (
    "/",
    "/about",
    "/riders",
    "/results",
    "/news",
    "/leaderboards",
    "/compare",
)

SPORT_LABELS = {1: "Supercross", 2: "Motocross", 3: "SMX"}


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


def _page(path, title, description, heading=None, body=None, page_type="website", json_ld=None):
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
    return page


def build_prerender_manifest():
    """Return lightweight, route-specific HTML data for the frontend build."""
    with engine.connect() as conn:
        riders = conn.execute(text("""
            SELECT rl.RiderID, rl.FullName, rl.Country, rl.ImageURL
            FROM dbo.Rider_List rl
            WHERE rl.FullName IS NOT NULL
              AND LTRIM(RTRIM(rl.FullName)) <> ''
              AND EXISTS (
                  SELECT 1
                  FROM dbo.RiderProfileAvailabilitySummary availability
                  WHERE availability.RiderID = rl.RiderID
                    AND (availability.HasSX = 1 OR availability.HasMX = 1 OR availability.HasSMX = 1)
              )
        """)).mappings().all()

        races = conn.execute(text("""
            SELECT rt.RaceID, rt.[Year], rt.Round, rt.TrackName, rt.SportID,
                   rt.RaceDate, tt.City
            FROM dbo.Race_Table rt
            LEFT JOIN dbo.TrackTable tt ON tt.TrackID = rt.TrackID
            WHERE rt.SportID IN (1, 2, 3)
        """)).mappings().all()

        tracks = conn.execute(text("""
            SELECT DISTINCT rt.TrackID, rt.TrackName, rt.SportID, tt.City, tt.State
            FROM dbo.Race_Table rt
            LEFT JOIN dbo.TrackTable tt ON tt.TrackID = rt.TrackID
            WHERE rt.SportID IN (1, 2, 3)
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
            WHERE SportID IN (1, 2, 3)
            GROUP BY SportID, [Year]
        """)).mappings().all()

        season_classes = conn.execute(text("""
            SELECT DISTINCT rt.SportID, rt.[Year], results.ClassID
            FROM dbo.Race_Table rt
            INNER JOIN (
                SELECT RaceID, ClassID FROM dbo.SX_MAINS
                UNION SELECT RaceID, ClassID FROM dbo.MX_OVERALLS
                UNION SELECT RaceID, ClassID FROM dbo.SMX_OVERALLS
            ) results ON results.RaceID = rt.RaceID
            WHERE rt.SportID IN (1, 2, 3)
        """)).mappings().all()

        notes = conn.execute(text("""
            SELECT Slug, Title, Summary, PublishDate, UpdatedAt
            FROM dbo.ContentNotes
            WHERE Status = 'published'
              AND Slug IS NOT NULL AND LTRIM(RTRIM(Slug)) <> ''
        """)).mappings().all()

    pages = [
        _page("/", "Supercross and Motocross Stats, Results, and Rider Profiles",
              "Smxmuse is a Supercross and Motocross stats archive with rider profiles, race results, season dashboards, comparisons, and all-time leaderboards.",
              "Everything in one place, from the latest gate drop to all-time history."),
        _page("/about", "About smxmuse",
              "Learn what smxmuse covers, how the Supercross and Motocross stats archive was built, and where to send feedback or business inquiries."),
        _page("/riders", "Browse Riders",
              "Browse the full smxmuse rider archive by last name or country, including featured riders and country pages.", "Riders"),
        _page("/results", "Race Results Archive - Supercross",
              "Browse Supercross race results by decade and season, then jump into full round-by-round result pages.", "Race Results"),
        _page("/news", "Supercross and Motocross News and Analysis",
              "Read smxmuse Supercross and Motocross race notes, previews, recaps, and data-driven analysis.", "Race Notes and Analysis"),
        _page("/leaderboards", "All-Time Supercross, Motocross, and SMX Leaderboards",
              "Browse all-time smxmuse leaderboards for wins, podiums, starts, and career milestones across Supercross, Motocross, and SMX.", "All Time Leaderboards"),
        _page("/compare", "Compare Supercross and Motocross Riders",
              "Compare Supercross, Motocross, and SMX riders head to head across career wins, podiums, starts, championships, and season statistics.", "Rider Comparison"),
    ]

    for rider in riders:
        name = rider["FullName"].strip()
        slug = _slugify(name)
        path = f"/rider/{slug}-{rider['RiderID']}" if slug else f"/rider/{rider['RiderID']}"
        description = f"Explore {name}'s Supercross and Motocross career stats, results history, qualifying numbers, and points totals on smxmuse."
        person = {"@context": "https://schema.org", "@type": "Person", "name": name, "url": _absolute_url(path)}
        if rider["Country"]:
            person["nationality"] = rider["Country"].strip()
        if rider["ImageURL"]:
            person["image"] = rider["ImageURL"]
        pages.append(_page(path, f"{name} Rider Profile and Career Stats", description, name, page_type="profile", json_ld=person))

    for race in races:
        sport = SPORT_LABELS[int(race["SportID"])]
        display_name = race["City"] if int(race["SportID"]) == 1 and race["City"] else race["TrackName"]
        slug = _slugify(f"{display_name} {race['Year']}")
        path = f"/race/{slug}-{race['RaceID']}" if slug else f"/race/{race['RaceID']}"
        description = f"View round {race['Round']} results, race data, and class breakdowns from {display_name} in the {race['Year']} {sport} season."
        event = {
            "@context": "https://schema.org", "@type": "SportsEvent",
            "name": f"{race['Year']} {display_name} {sport}", "sport": sport,
            "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode", "url": _absolute_url(path),
        }
        if race["RaceDate"]:
            event["startDate"] = _lastmod(race["RaceDate"])
        pages.append(_page(path, f"{race['Year']} {display_name} {sport} Results", description, race["TrackName"], page_type="article", json_ld=event))

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
        pages.append(_page(f"/results/{sport_code}/{year}", f"{year} {sport} Results",
                           f"Browse every round from the {year} {sport} season, plus season champions and the full archive schedule.",
                           f"{year} {sport} Results"))

    for path in sorted(_season_paths(season_classes)):
        _, _, sport_code, year, class_slug = path.split("/")
        sport = SPORT_LABELS[{"sx": 1, "mx": 2, "smx": 3}[sport_code]]
        class_label = {"250W": "250 West", "250E": "250 East"}.get(class_slug, class_slug)
        label = f"{class_label} {sport}"
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

        if class_id == 1:
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
              AND EXISTS (
                  SELECT 1
                  FROM dbo.RiderProfileAvailabilitySummary availability
                  WHERE availability.RiderID = rl.RiderID
                    AND (
                        availability.HasSX = 1
                        OR availability.HasMX = 1
                        OR availability.HasSMX = 1
                    )
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
            WHERE rt.SportID IN (1, 2, 3)
        """)).mappings().all()

        tracks = conn.execute(text("""
            SELECT DISTINCT TrackID, TrackName, SportID
            FROM dbo.Race_Table
            WHERE SportID IN (1, 2, 3)
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
            WHERE SportID IN (1, 2, 3)
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
            ) results ON results.RaceID = rt.RaceID
            WHERE rt.SportID IN (1, 2, 3)
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
