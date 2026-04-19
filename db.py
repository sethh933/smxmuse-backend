from datetime import datetime, timezone
from pathlib import Path
import os

import pyodbc
from dotenv import load_dotenv
from sqlalchemy import create_engine, text


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env.local")

DEFAULT_FRONTEND_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://smxmuse.com",
    "https://www.smxmuse.com",
]

configured_frontend_origins = [
    origin.strip()
    for origin in os.getenv("FRONTEND_ORIGINS", "").split(",")
    if origin.strip()
]

FRONTEND_ORIGINS = list(
    dict.fromkeys([*DEFAULT_FRONTEND_ORIGINS, *configured_frontend_origins])
)

ADMIN_REFRESH_TOKEN = os.getenv("ADMIN_REFRESH_TOKEN")
GRID_CACHE_REFRESH_URL = os.getenv("GRID_CACHE_REFRESH_URL")
SMXMUSE_ADMIN_REFRESH_URL = os.getenv("SMXMUSE_ADMIN_REFRESH_URL")

SQL_DRIVER = os.getenv("SQL_DRIVER", "ODBC Driver 18 for SQL Server")
SQL_SERVER = os.getenv("SQL_SERVER")
SQL_DATABASE = os.getenv("SQL_DATABASE")
SQL_USERNAME = os.getenv("SQL_USERNAME")
SQL_PASSWORD = os.getenv("SQL_PASSWORD")
SQL_ENCRYPT = os.getenv("SQL_ENCRYPT", "yes")
SQL_TRUST_SERVER_CERT = os.getenv("SQL_TRUST_SERVER_CERT", "no")
SQL_MARS = os.getenv("SQL_MARS_CONNECTION", "yes")

missing_db_settings = [
    key
    for key, value in {
        "SQL_SERVER": SQL_SERVER,
        "SQL_DATABASE": SQL_DATABASE,
        "SQL_USERNAME": SQL_USERNAME,
        "SQL_PASSWORD": SQL_PASSWORD,
    }.items()
    if not value
]

if missing_db_settings:
    raise RuntimeError(
        "Missing required database settings in .env.local: "
        + ", ".join(missing_db_settings)
    )

CONN_STR = (
    f"DRIVER={{{SQL_DRIVER}}};"
    f"SERVER={SQL_SERVER};"
    f"DATABASE={SQL_DATABASE};"
    f"UID={SQL_USERNAME};"
    f"PWD={SQL_PASSWORD};"
    f"Encrypt={SQL_ENCRYPT};"
    f"TrustServerCertificate={SQL_TRUST_SERVER_CERT};"
    f"MARS_Connection={SQL_MARS};"
)

engine = create_engine(
    "mssql+pyodbc://",
    creator=lambda: pyodbc.connect(CONN_STR),
    pool_pre_ping=True,
)

FEATURED_RIDERS_CACHE = {
    "date": None,
    "data": []
}

RIDER_OF_THE_DAY_CACHE = {
    "date": None,
    "data": None
}

ROTD_TABLE_READY = False


def fetch_all(query: str, params: dict):
    with engine.begin() as conn:
        result = conn.execute(text(query), params)
        return [dict(row._mapping) for row in result]


def ensure_rotd_table():
    global ROTD_TABLE_READY

    if ROTD_TABLE_READY:
        return

    with engine.begin() as conn:
        conn.execute(text("""
            IF OBJECT_ID('dbo.ROTD', 'U') IS NULL
            BEGIN
                CREATE TABLE dbo.ROTD (
                    ROTDID INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
                    ROTDDate DATE NOT NULL,
                    RiderID INT NOT NULL,
                    FullName NVARCHAR(255) NULL,
                    Country NVARCHAR(100) NULL,
                    ImageURL NVARCHAR(1000) NULL,
                    SelectedAt DATETIME2(0) NOT NULL
                        CONSTRAINT DF_ROTD_SelectedAt DEFAULT SYSUTCDATETIME()
                );
            END;

            IF NOT EXISTS (
                SELECT 1
                FROM sys.indexes
                WHERE name = 'UX_ROTD_ROTDDate'
                  AND object_id = OBJECT_ID('dbo.ROTD')
            )
            BEGIN
                CREATE UNIQUE INDEX UX_ROTD_ROTDDate
                    ON dbo.ROTD (ROTDDate);
            END;
        """))

    ROTD_TABLE_READY = True


def compute_featured_riders():
    with engine.connect() as conn:
        result = conn.execute(text("""
            WITH RiderDirectory AS (
                SELECT
                    rl.RiderID,
                    rl.FullName,
                    rl.Country,
                    rl.ImageURL,
                    LOWER(LTRIM(RTRIM(rl.FullName))) AS NormalizedFullName,
                    ROW_NUMBER() OVER (
                        PARTITION BY LOWER(LTRIM(RTRIM(rl.FullName)))
                        ORDER BY rl.RiderID
                    ) AS NameRank
                FROM Rider_List rl
                WHERE rl.FullName IS NOT NULL
            ),
            RecentGuessLeaders AS (
                SELECT TOP 8
                    rd.RiderID,
                    rd.FullName,
                    rd.Country,
                    COALESCE(
                        NULLIF(MAX(ug.ImageURL), ''),
                        NULLIF(rd.ImageURL, ''),
                        MAX(ug.ImageURL)
                    ) AS ImageURL,
                    COUNT(DISTINCT ug.UserID) AS UniqueUsers,
                    COUNT(*) AS TotalGuesses
                FROM dbo.UserGuesses ug
                JOIN RiderDirectory rd
                    ON rd.NormalizedFullName = LOWER(LTRIM(RTRIM(ug.FullName)))
                   AND rd.NameRank = 1
                WHERE ug.IsCorrect = 1
                  AND ug.FullName IS NOT NULL
                  AND ug.GuessedAt >= DATEADD(DAY, -7, GETUTCDATE())
                GROUP BY
                    rd.RiderID,
                    rd.FullName,
                    rd.Country,
                    rd.ImageURL
                ORDER BY
                    COUNT(DISTINCT ug.UserID) DESC,
                    COUNT(*) DESC,
                    rd.FullName ASC
            ),
            RiderStarts AS (
                SELECT RiderID, COUNT(*) AS Starts
                FROM SX_MAINS
                GROUP BY RiderID

                UNION ALL

                SELECT RiderID, COUNT(*) AS Starts
                FROM MX_OVERALLS
                GROUP BY RiderID
            ),
            CombinedStarts AS (
                SELECT RiderID, SUM(Starts) AS TotalStarts
                FROM RiderStarts
                GROUP BY RiderID
            ),
            FallbackRiders AS (
                SELECT TOP 8
                    rd.RiderID,
                    rd.FullName,
                    rd.Country,
                    rd.ImageURL,
                    cs.TotalStarts
                FROM CombinedStarts cs
                JOIN RiderDirectory rd
                    ON rd.RiderID = cs.RiderID
                WHERE rd.ImageURL IS NOT NULL
                  AND LTRIM(RTRIM(rd.ImageURL)) <> ''
                  AND rd.RiderID NOT IN (
                      SELECT RiderID
                      FROM RecentGuessLeaders
                  )
                ORDER BY
                    cs.TotalStarts DESC,
                    rd.FullName ASC
            )
            SELECT TOP 8
                featured.RiderID,
                featured.FullName,
                featured.Country,
                featured.ImageURL
            FROM (
                SELECT
                    rgl.RiderID,
                    rgl.FullName,
                    rgl.Country,
                    rgl.ImageURL,
                    0 AS SourceRank,
                    rgl.UniqueUsers AS PrimaryScore,
                    rgl.TotalGuesses AS SecondaryScore
                FROM RecentGuessLeaders rgl

                UNION ALL

                SELECT
                    fr.RiderID,
                    fr.FullName,
                    fr.Country,
                    fr.ImageURL,
                    1 AS SourceRank,
                    fr.TotalStarts AS PrimaryScore,
                    0 AS SecondaryScore
                FROM FallbackRiders fr
            ) featured
            ORDER BY
                featured.SourceRank ASC,
                featured.PrimaryScore DESC,
                featured.SecondaryScore DESC,
                featured.FullName ASC
        """)).fetchall()

        return [dict(row._mapping) for row in result]


def compute_rider_of_the_day(for_date=None):
    target_date = for_date or datetime.now(timezone.utc).date()
    ensure_rotd_table()

    with engine.begin() as conn:
        existing_row = conn.execute(text("""
            SELECT TOP 1
                RiderID,
                FullName,
                Country,
                ImageURL
            FROM dbo.ROTD
            WHERE ROTDDate = :target_date
        """), {"target_date": target_date}).fetchone()

        if existing_row:
            return dict(existing_row._mapping)

        selected_row = conn.execute(text("""
            SELECT TOP 1
                RiderID,
                FullName,
                Country,
                ImageURL
            FROM Rider_List
            WHERE FullName IS NOT NULL
              AND ImageURL IS NOT NULL
              AND LTRIM(RTRIM(ImageURL)) <> ''
            ORDER BY NEWID()
        """)).fetchone()

        if not selected_row:
            return None

        selected_rider = dict(selected_row._mapping)

        conn.execute(text("""
            INSERT INTO dbo.ROTD (
                ROTDDate,
                RiderID,
                FullName,
                Country,
                ImageURL
            )
            VALUES (
                :target_date,
                :rider_id,
                :full_name,
                :country,
                :image_url
            )
        """), {
            "target_date": target_date,
            "rider_id": selected_rider["RiderID"],
            "full_name": selected_rider["FullName"],
            "country": selected_rider["Country"],
            "image_url": selected_rider["ImageURL"],
        })

        return selected_rider
