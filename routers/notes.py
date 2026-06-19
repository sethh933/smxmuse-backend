from datetime import date
import re
from typing import List, Literal, Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text

from db import engine
from routers.admin import _require_admin_token


router = APIRouter()

NOTES_TABLES_READY = False
VALID_CATEGORIES = {"preRace", "raceRecap"}


class NoteSlideInput(BaseModel):
    heading: str = ""
    body: str = ""


class NoteSectionInput(BaseModel):
    heading: str
    slides: List[NoteSlideInput] = Field(default_factory=list)


class NoteInput(BaseModel):
    title: str
    category: Literal["preRace", "raceRecap"]
    sport: str = "Motocross"
    season: int
    race_id: Optional[int] = None
    race: Optional[str] = None
    publish_date: date
    summary: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    instagram_url: Optional[str] = None
    status: Literal["draft", "published"] = "draft"
    sections: List[NoteSectionInput] = Field(default_factory=list)


def _slugify(value: str) -> str:
    slug = []
    previous_dash = False

    for char in value.lower():
        if char.isalnum():
            slug.append(char)
            previous_dash = False
        elif not previous_dash:
            slug.append("-")
            previous_dash = True

    return "".join(slug).strip("-")


def _build_rider_path(rider_id, full_name):
    rider_slug = _slugify(full_name or "")
    return f"/rider/{rider_slug}-{rider_id}" if rider_slug else f"/rider/{rider_id}"


def _build_track_path(sport_id, track_id, track_name):
    sport_code_map = {
        1: "SX",
        2: "MX",
        3: "SMX",
    }
    track_slug = _slugify(track_name or "")
    track_segment = f"{track_slug}-{track_id}" if track_slug else str(track_id)

    return f"/track/{sport_code_map.get(sport_id, sport_id)}/{track_segment}"


def _entity_pattern(name):
    return re.compile(rf"(?<![A-Za-z0-9]){re.escape(name)}(?![A-Za-z0-9])", re.IGNORECASE)


def _get_entity_directory(conn):
    rider_rows = conn.execute(text("""
        WITH RiderDirectory AS (
            SELECT
                RiderID,
                FullName,
                ROW_NUMBER() OVER (
                    PARTITION BY LOWER(LTRIM(RTRIM(FullName)))
                    ORDER BY RiderID
                ) AS NameRank
            FROM Rider_List
            WHERE FullName IS NOT NULL
              AND LEN(LTRIM(RTRIM(FullName))) >= 4
        )
        SELECT RiderID, FullName
        FROM RiderDirectory
        WHERE NameRank = 1
    """)).mappings().all()

    track_rows = conn.execute(text("""
        WITH TrackDirectory AS (
            SELECT
                rt.TrackID,
                rt.TrackName,
                rt.SportID,
                COUNT(*) AS RaceCount,
                ROW_NUMBER() OVER (
                    PARTITION BY LOWER(LTRIM(RTRIM(rt.TrackName))), rt.SportID
                    ORDER BY COUNT(*) DESC, rt.TrackID
                ) AS TrackRank
            FROM Race_Table rt
            WHERE rt.TrackName IS NOT NULL
              AND LEN(LTRIM(RTRIM(rt.TrackName))) >= 4
              AND rt.SportID IN (1, 2, 3)
            GROUP BY
                rt.TrackID,
                rt.TrackName,
                rt.SportID
        )
        SELECT TrackID, TrackName, SportID
        FROM TrackDirectory
        WHERE TrackRank = 1
    """)).mappings().all()

    return {
        "riders": [
            {
                "type": "rider",
                "name": row["FullName"],
                "id": row["RiderID"],
                "path": _build_rider_path(row["RiderID"], row["FullName"]),
            }
            for row in rider_rows
        ],
        "tracks": [
            {
                "type": "track",
                "name": row["TrackName"],
                "id": row["TrackID"],
                "sportId": row["SportID"],
                "path": _build_track_path(row["SportID"], row["TrackID"], row["TrackName"]),
            }
            for row in track_rows
        ],
    }


def _collect_note_input_text(note):
    parts = [
        note.title,
        note.summary,
        note.race,
    ]

    for section in note.sections or []:
        parts.append(section.heading)

        for slide in section.slides or []:
            parts.append(slide.heading)
            parts.append(slide.body)

    return "\n".join(part for part in parts if part)


def _resolve_entities(conn, text_to_match):
    if not text_to_match:
        return {"riders": [], "tracks": []}

    directory = _get_entity_directory(conn)
    matched_riders = []
    matched_tracks = []

    for rider in directory["riders"]:
        if _entity_pattern(rider["name"]).search(text_to_match):
            matched_riders.append(rider)

    seen_track_names = set()

    for track in directory["tracks"]:
        normalized_name = track["name"].strip().lower()

        if normalized_name in seen_track_names:
            continue

        if _entity_pattern(track["name"]).search(text_to_match):
            matched_tracks.append(track)
            seen_track_names.add(normalized_name)

    return {
        "riders": sorted(matched_riders, key=lambda entity: entity["name"]),
        "tracks": sorted(matched_tracks, key=lambda entity: entity["name"]),
    }


def _ensure_notes_tables():
    global NOTES_TABLES_READY

    if NOTES_TABLES_READY:
        return

    with engine.begin() as conn:
        conn.execute(text("""
            IF OBJECT_ID('dbo.ContentNoteSlides', 'U') IS NULL
            BEGIN
                CREATE TABLE dbo.ContentNoteSlides (
                    SlideID INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
                    SectionID INT NOT NULL,
                    Heading NVARCHAR(255) NULL,
                    Body NVARCHAR(MAX) NULL,
                    SortOrder INT NOT NULL,
                    CreatedAt DATETIME2(0) NOT NULL
                        CONSTRAINT DF_ContentNoteSlides_CreatedAt DEFAULT SYSUTCDATETIME()
                );
            END;

            IF OBJECT_ID('dbo.ContentNoteSections', 'U') IS NULL
            BEGIN
                CREATE TABLE dbo.ContentNoteSections (
                    SectionID INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
                    NoteID INT NOT NULL,
                    Heading NVARCHAR(255) NOT NULL,
                    SortOrder INT NOT NULL,
                    CreatedAt DATETIME2(0) NOT NULL
                        CONSTRAINT DF_ContentNoteSections_CreatedAt DEFAULT SYSUTCDATETIME()
                );
            END;

            IF OBJECT_ID('dbo.ContentNotes', 'U') IS NULL
            BEGIN
                CREATE TABLE dbo.ContentNotes (
                    NoteID INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
                    Slug NVARCHAR(255) NOT NULL,
                    Title NVARCHAR(255) NOT NULL,
                    Category NVARCHAR(50) NOT NULL,
                    Sport NVARCHAR(50) NULL,
                    Season INT NULL,
                    RaceID INT NULL,
                    RaceName NVARCHAR(255) NULL,
                    PublishDate DATE NOT NULL,
                    Summary NVARCHAR(MAX) NULL,
                    Tags NVARCHAR(1000) NULL,
                    InstagramUrl NVARCHAR(1000) NULL,
                    Status NVARCHAR(20) NOT NULL
                        CONSTRAINT DF_ContentNotes_Status DEFAULT 'draft',
                    CreatedAt DATETIME2(0) NOT NULL
                        CONSTRAINT DF_ContentNotes_CreatedAt DEFAULT SYSUTCDATETIME(),
                    UpdatedAt DATETIME2(0) NOT NULL
                        CONSTRAINT DF_ContentNotes_UpdatedAt DEFAULT SYSUTCDATETIME()
                );
            END;

            IF OBJECT_ID('dbo.ContentNoteEntityLinks', 'U') IS NULL
            BEGIN
                CREATE TABLE dbo.ContentNoteEntityLinks (
                    EntityLinkID INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
                    NoteID INT NOT NULL,
                    EntityType NVARCHAR(20) NOT NULL,
                    EntityID INT NOT NULL,
                    EntityName NVARCHAR(255) NOT NULL,
                    EntityPath NVARCHAR(500) NOT NULL,
                    SportID INT NULL,
                    CreatedAt DATETIME2(0) NOT NULL
                        CONSTRAINT DF_ContentNoteEntityLinks_CreatedAt DEFAULT SYSUTCDATETIME()
                );
            END;

            IF NOT EXISTS (
                SELECT 1
                FROM sys.indexes
                WHERE name = 'UX_ContentNotes_Slug'
                  AND object_id = OBJECT_ID('dbo.ContentNotes')
            )
            BEGIN
                CREATE UNIQUE INDEX UX_ContentNotes_Slug
                    ON dbo.ContentNotes (Slug);
            END;

            IF NOT EXISTS (
                SELECT 1
                FROM sys.foreign_keys
                WHERE name = 'FK_ContentNoteSections_ContentNotes'
            )
            BEGIN
                ALTER TABLE dbo.ContentNoteSections
                ADD CONSTRAINT FK_ContentNoteSections_ContentNotes
                    FOREIGN KEY (NoteID)
                    REFERENCES dbo.ContentNotes(NoteID)
                    ON DELETE CASCADE;
            END;

            IF NOT EXISTS (
                SELECT 1
                FROM sys.foreign_keys
                WHERE name = 'FK_ContentNoteSlides_ContentNoteSections'
            )
            BEGIN
                ALTER TABLE dbo.ContentNoteSlides
                ADD CONSTRAINT FK_ContentNoteSlides_ContentNoteSections
                    FOREIGN KEY (SectionID)
                    REFERENCES dbo.ContentNoteSections(SectionID)
                    ON DELETE CASCADE;
            END;

            IF NOT EXISTS (
                SELECT 1
                FROM sys.foreign_keys
                WHERE name = 'FK_ContentNoteEntityLinks_ContentNotes'
            )
            BEGIN
                ALTER TABLE dbo.ContentNoteEntityLinks
                ADD CONSTRAINT FK_ContentNoteEntityLinks_ContentNotes
                    FOREIGN KEY (NoteID)
                    REFERENCES dbo.ContentNotes(NoteID)
                    ON DELETE CASCADE;
            END;

            IF NOT EXISTS (
                SELECT 1
                FROM sys.indexes
                WHERE name = 'IX_ContentNoteEntityLinks_NoteID'
                  AND object_id = OBJECT_ID('dbo.ContentNoteEntityLinks')
            )
            BEGIN
                CREATE INDEX IX_ContentNoteEntityLinks_NoteID
                    ON dbo.ContentNoteEntityLinks (NoteID);
            END;
        """))

    NOTES_TABLES_READY = True


def _parse_tags(tags_value):
    if not tags_value:
        return []

    return [tag.strip() for tag in tags_value.split(",") if tag.strip()]


def _serialize_note(row, sections=None):
    note = {
        "id": row["NoteID"],
        "slug": row["Slug"],
        "title": row["Title"],
        "type": row["Category"],
        "sport": row["Sport"],
        "season": row["Season"],
        "raceId": row["RaceID"],
        "race": row["RaceName"],
        "date": row["PublishDate"].isoformat(),
        "summary": row["Summary"],
        "tags": _parse_tags(row["Tags"]),
        "instagramUrl": row["InstagramUrl"],
        "status": row["Status"],
        "body": sections or [],
    }

    return note


def _serialize_note_with_entities(conn, row, include_edit_sections=False):
    sections = _load_sections(conn, row["NoteID"])
    note = _serialize_note(row, sections)

    if include_edit_sections:
        note["sections"] = _load_edit_sections(conn, row["NoteID"])

    note["entities"] = _load_entity_links(conn, row["NoteID"])

    return note


def _load_entity_links(conn, note_id):
    rows = conn.execute(text("""
        SELECT
            EntityType,
            EntityID,
            EntityName,
            EntityPath,
            SportID
        FROM dbo.ContentNoteEntityLinks
        WHERE NoteID = :note_id
        ORDER BY EntityType, EntityName
    """), {"note_id": note_id}).mappings().all()

    entities = {
        "riders": [],
        "tracks": [],
    }

    for row in rows:
        if row["EntityType"] == "rider":
            entities["riders"].append({
                "type": "rider",
                "id": row["EntityID"],
                "name": row["EntityName"],
                "path": row["EntityPath"],
            })
        elif row["EntityType"] == "track":
            entities["tracks"].append({
                "type": "track",
                "id": row["EntityID"],
                "sportId": row["SportID"],
                "name": row["EntityName"],
                "path": row["EntityPath"],
            })

    return entities


def _save_entity_links(conn, note_id, entities):
    conn.execute(text("""
        DELETE FROM dbo.ContentNoteEntityLinks
        WHERE NoteID = :note_id
    """), {"note_id": note_id})

    for rider in entities.get("riders", []):
        conn.execute(text("""
            INSERT INTO dbo.ContentNoteEntityLinks (
                NoteID,
                EntityType,
                EntityID,
                EntityName,
                EntityPath,
                SportID
            )
            VALUES (
                :note_id,
                'rider',
                :entity_id,
                :entity_name,
                :entity_path,
                NULL
            )
        """), {
            "note_id": note_id,
            "entity_id": rider["id"],
            "entity_name": rider["name"],
            "entity_path": rider["path"],
        })

    for track in entities.get("tracks", []):
        conn.execute(text("""
            INSERT INTO dbo.ContentNoteEntityLinks (
                NoteID,
                EntityType,
                EntityID,
                EntityName,
                EntityPath,
                SportID
            )
            VALUES (
                :note_id,
                'track',
                :entity_id,
                :entity_name,
                :entity_path,
                :sport_id
            )
        """), {
            "note_id": note_id,
            "entity_id": track["id"],
            "entity_name": track["name"],
            "entity_path": track["path"],
            "sport_id": track.get("sportId"),
        })


def _rebuild_note_entity_links(conn, note_id):
    row = conn.execute(text("""
        SELECT TOP 1
            NoteID,
            Title,
            RaceName,
            Summary
        FROM dbo.ContentNotes
        WHERE NoteID = :note_id
    """), {"note_id": note_id}).mappings().first()

    if not row:
        return False

    edit_sections = _load_edit_sections(conn, note_id)
    parts = [
        row["Title"],
        row["RaceName"],
        row["Summary"],
    ]

    for section in edit_sections:
        parts.append(section.get("heading"))

        for slide in section.get("slides") or []:
            parts.append(slide.get("heading"))
            parts.append(slide.get("body"))

    entities = _resolve_entities(conn, "\n".join(part for part in parts if part))
    _save_entity_links(conn, note_id, entities)

    return True


def _load_sections(conn, note_id):
    section_rows = conn.execute(text("""
        SELECT SectionID, Heading
        FROM dbo.ContentNoteSections
        WHERE NoteID = :note_id
        ORDER BY SortOrder, SectionID
    """), {"note_id": note_id}).mappings().all()

    sections = []

    for section in section_rows:
        slide_rows = conn.execute(text("""
            SELECT Heading, Body
            FROM dbo.ContentNoteSlides
            WHERE SectionID = :section_id
            ORDER BY SortOrder, SlideID
        """), {"section_id": section["SectionID"]}).mappings().all()

        sections.append({
            "heading": section["Heading"],
            "subsections": [
                {
                    "heading": slide["Heading"],
                    "paragraphs": [
                        paragraph.strip()
                        for paragraph in (slide["Body"] or "").split("\n\n")
                        if paragraph.strip()
                    ],
                }
                for slide in slide_rows
                if (slide["Heading"] or "").strip() or (slide["Body"] or "").strip()
            ],
        })

    return sections


def _load_edit_sections(conn, note_id):
    section_rows = conn.execute(text("""
        SELECT SectionID, Heading
        FROM dbo.ContentNoteSections
        WHERE NoteID = :note_id
        ORDER BY SortOrder, SectionID
    """), {"note_id": note_id}).mappings().all()

    sections = []

    for section in section_rows:
        slide_rows = conn.execute(text("""
            SELECT Heading, Body
            FROM dbo.ContentNoteSlides
            WHERE SectionID = :section_id
            ORDER BY SortOrder, SlideID
        """), {"section_id": section["SectionID"]}).mappings().all()

        sections.append({
            "heading": section["Heading"],
            "slides": [
                {
                    "heading": slide["Heading"] or "",
                    "body": slide["Body"] or "",
                }
                for slide in slide_rows
            ],
        })

    return sections


def _save_note_sections(conn, note_id, sections):
    conn.execute(text("""
        DELETE slides
        FROM dbo.ContentNoteSlides slides
        JOIN dbo.ContentNoteSections sections
            ON sections.SectionID = slides.SectionID
        WHERE sections.NoteID = :note_id
    """), {"note_id": note_id})

    conn.execute(text("""
        DELETE FROM dbo.ContentNoteSections
        WHERE NoteID = :note_id
    """), {"note_id": note_id})

    for section_index, section in enumerate(sections):
        if not section.heading.strip():
            continue

        section_id = conn.execute(text("""
            INSERT INTO dbo.ContentNoteSections (
                NoteID,
                Heading,
                SortOrder
            )
            OUTPUT INSERTED.SectionID
            VALUES (
                :note_id,
                :heading,
                :sort_order
            )
        """), {
            "note_id": note_id,
            "heading": section.heading.strip(),
            "sort_order": section_index,
        }).scalar_one()

        for slide_index, slide in enumerate(section.slides):
            if not slide.heading.strip() and not slide.body.strip():
                continue

            conn.execute(text("""
                INSERT INTO dbo.ContentNoteSlides (
                    SectionID,
                    Heading,
                    Body,
                    SortOrder
                )
                VALUES (
                    :section_id,
                    :heading,
                    :body,
                    :sort_order
                )
            """), {
                "section_id": section_id,
                "heading": slide.heading.strip(),
                "body": slide.body.strip(),
                "sort_order": slide_index,
            })


@router.get("/api/notes")
def list_public_notes(category: Optional[str] = None, race_id: Optional[int] = None):
    _ensure_notes_tables()

    if category and category not in VALID_CATEGORIES:
        return []

    filters = ["Status = 'published'"]
    params = {}

    if category:
        filters.append("Category = :category")
        params["category"] = category

    if race_id:
        filters.append("RaceID = :race_id")
        params["race_id"] = race_id

    with engine.connect() as conn:
        rows = conn.execute(text(f"""
            SELECT
                NoteID,
                Slug,
                Title,
                Category,
                Sport,
                Season,
                RaceID,
                RaceName,
                PublishDate,
                Summary,
                Tags,
                InstagramUrl,
                Status
            FROM dbo.ContentNotes
            WHERE {' AND '.join(filters)}
            ORDER BY PublishDate DESC, NoteID DESC
        """), params).mappings().all()

        return [_serialize_note(row) for row in rows]


@router.get("/api/notes/{slug}")
def get_public_note(slug: str):
    _ensure_notes_tables()

    with engine.connect() as conn:
        row = conn.execute(text("""
            SELECT TOP 1
                NoteID,
                Slug,
                Title,
                Category,
                Sport,
                Season,
                RaceID,
                RaceName,
                PublishDate,
                Summary,
                Tags,
                InstagramUrl,
                Status
            FROM dbo.ContentNotes
            WHERE Slug = :slug
              AND Status = 'published'
        """), {"slug": slug}).mappings().first()

        if not row:
            return None

        return _serialize_note_with_entities(conn, row)


@router.get("/api/admin/notes")
def list_admin_notes(
    status: Optional[Literal["draft", "published"]] = None,
    x_admin_token: Optional[str] = Header(default=None),
):
    _require_admin_token(x_admin_token)
    _ensure_notes_tables()

    filters = []
    params = {}

    if status:
        filters.append("Status = :status")
        params["status"] = status

    where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""

    with engine.connect() as conn:
        rows = conn.execute(text(f"""
            SELECT
                NoteID,
                Slug,
                Title,
                Category,
                Sport,
                Season,
                RaceID,
                RaceName,
                PublishDate,
                Summary,
                Tags,
                InstagramUrl,
                Status
            FROM dbo.ContentNotes
            {where_clause}
            ORDER BY UpdatedAt DESC, NoteID DESC
        """), params).mappings().all()

        return [_serialize_note(row) for row in rows]


@router.get("/api/admin/notes/{slug}")
def get_admin_note(slug: str, x_admin_token: Optional[str] = Header(default=None)):
    _require_admin_token(x_admin_token)
    _ensure_notes_tables()

    with engine.connect() as conn:
        row = conn.execute(text("""
            SELECT TOP 1
                NoteID,
                Slug,
                Title,
                Category,
                Sport,
                Season,
                RaceID,
                RaceName,
                PublishDate,
                Summary,
                Tags,
                InstagramUrl,
                Status
            FROM dbo.ContentNotes
            WHERE Slug = :slug
        """), {"slug": slug}).mappings().first()

        if not row:
            return None

        return _serialize_note_with_entities(conn, row, include_edit_sections=True)


@router.post("/api/admin/notes")
def create_admin_note(note: NoteInput, x_admin_token: Optional[str] = Header(default=None)):
    _require_admin_token(x_admin_token)
    _ensure_notes_tables()

    base_slug = _slugify(f"{note.publish_date.isoformat()} {note.title}")
    tags = ", ".join(tag.strip() for tag in note.tags if tag.strip())

    with engine.begin() as conn:
        existing = conn.execute(text("""
            SELECT COUNT(*) AS ExistingCount
            FROM dbo.ContentNotes
            WHERE Slug = :slug
        """), {"slug": base_slug}).mappings().first()

        slug = base_slug
        if existing and existing["ExistingCount"]:
            slug = f"{base_slug}-{existing['ExistingCount'] + 1}"

        note_id = conn.execute(text("""
            INSERT INTO dbo.ContentNotes (
                Slug,
                Title,
                Category,
                Sport,
                Season,
                RaceID,
                RaceName,
                PublishDate,
                Summary,
                Tags,
                InstagramUrl,
                Status
            )
            OUTPUT INSERTED.NoteID
            VALUES (
                :slug,
                :title,
                :category,
                :sport,
                :season,
                :race_id,
                :race_name,
                :publish_date,
                :summary,
                :tags,
                :instagram_url,
                :status
            )
        """), {
            "slug": slug,
            "title": note.title,
            "category": note.category,
            "sport": note.sport,
            "season": note.season,
            "race_id": note.race_id,
            "race_name": note.race,
            "publish_date": note.publish_date,
            "summary": note.summary,
            "tags": tags,
            "instagram_url": note.instagram_url,
            "status": note.status,
        }).scalar_one()

        _save_note_sections(conn, note_id, note.sections)
        _save_entity_links(conn, note_id, _resolve_entities(conn, _collect_note_input_text(note)))

    return {
        "id": note_id,
        "slug": slug,
        "path": f"/news/{slug}",
        "status": note.status,
    }


@router.put("/api/admin/notes/{slug}")
def update_admin_note(
    slug: str,
    note: NoteInput,
    x_admin_token: Optional[str] = Header(default=None),
):
    _require_admin_token(x_admin_token)
    _ensure_notes_tables()

    tags = ", ".join(tag.strip() for tag in note.tags if tag.strip())

    with engine.begin() as conn:
        existing = conn.execute(text("""
            SELECT TOP 1 NoteID
            FROM dbo.ContentNotes
            WHERE Slug = :slug
        """), {"slug": slug}).mappings().first()

        if not existing:
            raise HTTPException(status_code=404, detail="Draft not found.")

        note_id = existing["NoteID"]

        conn.execute(text("""
            UPDATE dbo.ContentNotes
            SET
                Title = :title,
                Category = :category,
                Sport = :sport,
                Season = :season,
                RaceID = :race_id,
                RaceName = :race_name,
                PublishDate = :publish_date,
                Summary = :summary,
                Tags = :tags,
                InstagramUrl = :instagram_url,
                Status = :status,
                UpdatedAt = SYSUTCDATETIME()
            WHERE NoteID = :note_id
        """), {
            "note_id": note_id,
            "title": note.title,
            "category": note.category,
            "sport": note.sport,
            "season": note.season,
            "race_id": note.race_id,
            "race_name": note.race,
            "publish_date": note.publish_date,
            "summary": note.summary,
            "tags": tags,
            "instagram_url": note.instagram_url,
            "status": note.status,
        })

        _save_note_sections(conn, note_id, note.sections)
        _save_entity_links(conn, note_id, _resolve_entities(conn, _collect_note_input_text(note)))

    return {
        "id": note_id,
        "slug": slug,
        "path": f"/news/{slug}",
        "status": note.status,
    }


@router.delete("/api/admin/notes/{slug}")
def delete_admin_note(slug: str, x_admin_token: Optional[str] = Header(default=None)):
    _require_admin_token(x_admin_token)
    _ensure_notes_tables()

    with engine.begin() as conn:
        existing = conn.execute(text("""
            SELECT TOP 1 NoteID, Status
            FROM dbo.ContentNotes
            WHERE Slug = :slug
        """), {"slug": slug}).mappings().first()

        if not existing:
            return None

        if existing["Status"] != "draft":
            raise HTTPException(status_code=400, detail="Only draft news posts can be deleted.")

        note_id = existing["NoteID"]

        conn.execute(text("""
            DELETE FROM dbo.ContentNoteEntityLinks
            WHERE NoteID = :note_id
        """), {"note_id": note_id})

        conn.execute(text("""
            DELETE slides
            FROM dbo.ContentNoteSlides slides
            JOIN dbo.ContentNoteSections sections
                ON sections.SectionID = slides.SectionID
            WHERE sections.NoteID = :note_id
        """), {"note_id": note_id})

        conn.execute(text("""
            DELETE FROM dbo.ContentNoteSections
            WHERE NoteID = :note_id
        """), {"note_id": note_id})

        conn.execute(text("""
            DELETE FROM dbo.ContentNotes
            WHERE NoteID = :note_id
        """), {"note_id": note_id})

    return {
        "deleted": True,
        "slug": slug,
    }


@router.post("/api/admin/notes/backfill-entity-links")
def backfill_note_entity_links(x_admin_token: Optional[str] = Header(default=None)):
    _require_admin_token(x_admin_token)
    _ensure_notes_tables()

    with engine.begin() as conn:
        rows = conn.execute(text("""
            SELECT NoteID
            FROM dbo.ContentNotes
            ORDER BY NoteID
        """)).mappings().all()

        rebuilt_count = 0

        for row in rows:
            if _rebuild_note_entity_links(conn, row["NoteID"]):
                rebuilt_count += 1

    return {
        "rebuilt": rebuilt_count,
    }
