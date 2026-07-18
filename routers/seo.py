import re
import unicodedata
from datetime import date, datetime
from urllib.parse import quote
from xml.etree import ElementTree as ET

from fastapi import APIRouter
from fastapi.responses import Response
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
