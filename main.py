from fastapi import FastAPI, HTTPException, Query, Response
from typing import List, Optional
from datetime import datetime, timezone
import pyodbc
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy import create_engine
from urllib.parse import urlparse
from urllib.request import Request, urlopen


app = FastAPI()

# ✅ CORS for local dev or frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # You can restrict to your frontend domain later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Azure SQL Connection
CONN_STR = (
    "DRIVER={ODBC Driver 18 for SQL Server};"
    "SERVER=tcp:smxmuse.database.windows.net;"
    "DATABASE=smxmuse;"
    "UID=smxmuseadmin;"
    "PWD=Anaheim12025!;"
    "Encrypt=yes;TrustServerCertificate=no;"
    "MARS_Connection=yes;"
)

engine = create_engine(
    "mssql+pyodbc://",
    creator=lambda: pyodbc.connect(CONN_STR)
)

FEATURED_RIDERS_CACHE = {
    "date": None,
    "data": []
}

RIDER_OF_THE_DAY_CACHE = {
    "date": None,
    "data": None
}

def fetch_all(query: str, params: dict):
    with engine.begin() as conn:
        result = conn.execute(text(query), params)
        return [dict(row._mapping) for row in result]

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

def compute_rider_of_the_day():
    with engine.connect() as conn:
        row = conn.execute(text("""
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

        return dict(row._mapping) if row else None

@app.get("/")
def home():
    return {"message": "SMX Muse Leaderboard API is running."}

@app.get("/api/season/main-stats")
def get_season_main_stats(
    year: int,
    sportid: int,
    classid: int,
    ridercoastid: int = None
):
    query = """
        WITH CoastPoolResolved AS (
            SELECT
                RiderID,
                [Year],
                MIN(RiderCoastID) AS RiderCoastID
            FROM CoastPool
            GROUP BY RiderID, [Year]
        ),
        MainStatsRaw AS (
            SELECT DISTINCT *
            FROM dbo.vw_SeasonMainEventStats
            WHERE Year = :year
              AND SportID = :sportid
              AND ClassID = :classid
        ),
        MainStats AS (
            SELECT *
            FROM (
                SELECT
                    msr.*,
                    ROW_NUMBER() OVER (
                        PARTITION BY msr.RiderID
                        ORDER BY
                            CASE WHEN msr.RiderCoastID IS NULL THEN 0 ELSE 1 END,
                            msr.Wins DESC,
                            msr.AvgFinish ASC,
                            msr.Points DESC
                    ) AS rn
                FROM MainStatsRaw msr
            ) ranked
            WHERE rn = 1
        ),
        BrandAgg AS (
            SELECT
                rt.Year,
                1 AS SportID,
                sm.ClassID,
                sm.RiderID,
                MAX(sm.Brand) AS Brand,
                COALESCE(sm.RiderCoastID, cp.RiderCoastID) AS RiderCoastID
            FROM SX_MAINS sm
            JOIN Race_Table rt
                ON rt.RaceID = sm.RaceID
            LEFT JOIN CoastPoolResolved cp
                ON cp.RiderID = sm.RiderID
               AND cp.[Year] = rt.[Year]
            WHERE rt.Year = :year
              AND rt.SportID = :sportid
              AND sm.ClassID = :classid
              AND (:ridercoastid IS NULL OR COALESCE(sm.RiderCoastID, cp.RiderCoastID) = :ridercoastid)
            GROUP BY
                rt.Year,
                sm.ClassID,
                sm.RiderID,
                COALESCE(sm.RiderCoastID, cp.RiderCoastID)
        )
        SELECT
            ms.*,
            COALESCE(rl.FullName, ms.FullName) AS DisplayFullName,
            ba.Brand
        FROM MainStats ms
        LEFT JOIN Rider_List rl
            ON rl.RiderID = ms.RiderID
        LEFT JOIN BrandAgg ba
            ON ba.Year = ms.Year
           AND ba.SportID = ms.SportID
           AND ba.ClassID = ms.ClassID
           AND ba.RiderID = ms.RiderID
           AND (
                (ba.RiderCoastID = ms.RiderCoastID)
                OR (ba.RiderCoastID IS NULL AND ms.RiderCoastID IS NULL)
           )
    """

    if ridercoastid is not None:
        query += " WHERE ms.RiderCoastID = :ridercoastid"

    query += " ORDER BY ms.Wins DESC, ms.AvgFinish ASC"

    return fetch_all(query, locals())

@app.get("/api/season/start-stats")
def get_season_start_stats(
    year: int,
    sportid: int,
    classid: int,
    ridercoastid: int = None
):
    if sportid == 1:
        query = """
            WITH CoastPoolResolved AS (
                SELECT
                    RiderID,
                    [Year],
                    MIN(RiderCoastID) AS RiderCoastID
                FROM CoastPool
                GROUP BY RiderID, [Year]
            ),
            Base AS (
                SELECT
                    rt.Year,
                    1 AS SportID,
                    q.ClassID,
                    q.RiderID,
                    COALESCE(rl.FullName, q.FullName) AS FullName,
                    COALESCE(q.RiderCoastID, cp.RiderCoastID) AS RiderCoastID,
                    'QUAL' AS SessionType,
                    q.Result
                FROM SX_QUAL q
                JOIN Race_Table rt
                    ON rt.RaceID = q.RaceID
                LEFT JOIN Rider_List rl
                    ON rl.RiderID = q.RiderID
                LEFT JOIN CoastPoolResolved cp
                    ON cp.RiderID = q.RiderID
                   AND cp.[Year] = rt.[Year]
                WHERE rt.Year = :year
                  AND rt.SportID = :sportid
                  AND q.ClassID = :classid
                  AND (:ridercoastid IS NULL OR COALESCE(q.RiderCoastID, cp.RiderCoastID) = :ridercoastid)

                UNION ALL

                SELECT
                    rt.Year,
                    1 AS SportID,
                    h.ClassID,
                    h.RiderID,
                    COALESCE(rl.FullName, h.FullName) AS FullName,
                    COALESCE(h.RiderCoastID, cp.RiderCoastID) AS RiderCoastID,
                    'HEAT' AS SessionType,
                    h.Result
                FROM SX_HEATS h
                JOIN Race_Table rt
                    ON rt.RaceID = h.RaceID
                LEFT JOIN Rider_List rl
                    ON rl.RiderID = h.RiderID
                LEFT JOIN CoastPoolResolved cp
                    ON cp.RiderID = h.RiderID
                   AND cp.[Year] = rt.[Year]
                WHERE rt.Year = :year
                  AND rt.SportID = :sportid
                  AND h.ClassID = :classid
                  AND (:ridercoastid IS NULL OR COALESCE(h.RiderCoastID, cp.RiderCoastID) = :ridercoastid)

                UNION ALL

                SELECT
                    rt.Year,
                    1 AS SportID,
                    l.ClassID,
                    l.RiderID,
                    COALESCE(rl.FullName, l.FullName) AS FullName,
                    COALESCE(l.RiderCoastID, cp.RiderCoastID) AS RiderCoastID,
                    'LCQ' AS SessionType,
                    l.Result
                FROM SX_LCQS l
                JOIN Race_Table rt
                    ON rt.RaceID = l.RaceID
                LEFT JOIN Rider_List rl
                    ON rl.RiderID = l.RiderID
                LEFT JOIN CoastPoolResolved cp
                    ON cp.RiderID = l.RiderID
                   AND cp.[Year] = rt.[Year]
                WHERE rt.Year = :year
                  AND rt.SportID = :sportid
                  AND l.ClassID = :classid
                  AND (:ridercoastid IS NULL OR COALESCE(l.RiderCoastID, cp.RiderCoastID) = :ridercoastid)
            )
            SELECT
                Year,
                SportID,
                ClassID,
                RiderID,
                MAX(FullName) AS FullName,
                MAX(FullName) AS DisplayFullName,
                MAX(RiderCoastID) AS RiderCoastID,
                SUM(CASE WHEN SessionType = 'QUAL' THEN 1 ELSE 0 END) AS QualStarts,
                SUM(CASE WHEN SessionType = 'QUAL' AND Result = 1 THEN 1 ELSE 0 END) AS Poles,
                MIN(CASE WHEN SessionType = 'QUAL' THEN Result END) AS BestQual,
                CAST(ROUND(AVG(CASE WHEN SessionType = 'QUAL' THEN CAST(Result AS DECIMAL(10,2)) END), 2) AS DECIMAL(10,2)) AS AvgQualFinish,
                SUM(CASE WHEN SessionType = 'HEAT' THEN 1 ELSE 0 END) AS HeatStarts,
                SUM(CASE WHEN SessionType = 'HEAT' AND Result = 1 THEN 1 ELSE 0 END) AS HeatWins,
                MIN(CASE WHEN SessionType = 'HEAT' THEN Result END) AS BestHeat,
                SUM(CASE WHEN SessionType = 'LCQ' THEN 1 ELSE 0 END) AS LCQStarts,
                SUM(CASE WHEN SessionType = 'LCQ' AND Result = 1 THEN 1 ELSE 0 END) AS LCQWins,
                MIN(CASE WHEN SessionType = 'LCQ' THEN Result END) AS BestLCQ
            FROM Base
            GROUP BY
                Year,
                SportID,
                ClassID,
                RiderID
        """

        return fetch_all(query, locals())

    query = """
        SELECT *
        FROM dbo.vw_SeasonStartStats
        WHERE Year = :year
          AND SportID = :sportid
          AND ClassID = :classid
    """

    if ridercoastid is not None:
        query += " AND RiderCoastID = :ridercoastid"

    return fetch_all(query, locals())

@app.get("/api/season/laps-led")
def get_season_laps_led(
    year: int,
    sportid: int,
    classid: int,
    ridercoastid: int = None
):
    query = """
        WITH LapStats AS (
            SELECT *
            FROM dbo.vw_SeasonLapStats
            WHERE Year = :year
              AND SportID = :sportid
              AND ClassID = :classid
        ),
        BrandAgg AS (
            SELECT
                rt.Year,
                1 AS SportID,
                sm.ClassID,
                sm.RiderID,
                MAX(sm.Brand) AS Brand,
                COALESCE(sm.RiderCoastID, cp.RiderCoastID) AS RiderCoastID
            FROM SX_MAINS sm
            JOIN Race_Table rt
                ON rt.RaceID = sm.RaceID
            LEFT JOIN CoastPool cp
                ON cp.RiderID = sm.RiderID
               AND cp.[Year] = rt.[Year]
            WHERE rt.Year = :year
              AND rt.SportID = :sportid
              AND sm.ClassID = :classid
            GROUP BY
                rt.Year,
                sm.ClassID,
                sm.RiderID,
                COALESCE(sm.RiderCoastID, cp.RiderCoastID)
        )
        SELECT
            ls.*,
            ba.Brand
        FROM LapStats ls
        LEFT JOIN BrandAgg ba
            ON ba.Year = ls.Year
           AND ba.SportID = ls.SportID
           AND ba.ClassID = ls.ClassID
           AND ba.RiderID = ls.RiderID
           AND (
                (ba.RiderCoastID = ls.RiderCoastID)
                OR (ba.RiderCoastID IS NULL AND ls.RiderCoastID IS NULL)
           )
    """

    if ridercoastid is not None:
        query += " WHERE ls.RiderCoastID = :ridercoastid"

    query += " ORDER BY ls.LapsLed DESC"

    return fetch_all(query, locals())

@app.get("/api/season/points-progression")
def get_season_points_progression(
    year: int,
    sportid: int,
    classid: int,
    ridercoastid: int = None
):
    query = """
        SELECT *
        FROM dbo.vw_SeasonPointsProgression
        WHERE Year = :year
          AND SportID = :sportid
          AND ClassID = :classid
    """

    if ridercoastid is not None:
        query += " AND RiderCoastID = :ridercoastid"

    query += " ORDER BY Round"

    return fetch_all(query, locals())

@app.get("/leaderboard1")
def leaderboard1(class_ids: List[int] = Query(default=[1, 2, 3])):
    placeholders = ",".join("?" for _ in class_ids)

    sx_query = f"""
        SELECT
    m.RiderID AS riderid,
    rl.FullName AS fullname,
    COUNT(*) AS wins
FROM SX_MAINS m
JOIN Rider_List rl
    ON rl.RiderID = m.RiderID
WHERE Result = 1
  AND ClassID IN ({placeholders})
GROUP BY
    m.RiderID,
    rl.FullName
ORDER BY wins DESC;
    """

    mx_query = f"""
        SELECT
    m.RiderID AS riderid,
    rl.FullName AS fullname,
    COUNT(*) AS wins
FROM MX_OVERALLS m
JOIN Rider_List rl
    ON rl.RiderID = m.RiderID
WHERE m.Result = 1
  AND m.ClassID IN ({placeholders})
GROUP BY
    m.RiderID,
    rl.FullName
ORDER BY wins DESC;
    """

    try:
        with pyodbc.connect(CONN_STR) as conn:
            cursor = conn.cursor()

            cursor.execute(sx_query, class_ids)
            supercross = [
                {"riderid": row.riderid, "fullname": row.fullname, "wins": row.wins}
                for row in cursor.fetchall()
            ]

            cursor.execute(mx_query, class_ids)
            motocross = [
                {"riderid": row.riderid, "fullname": row.fullname, "wins": row.wins}
                for row in cursor.fetchall()
            ]

        return {"supercross": supercross, "motocross": motocross}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching wins leaderboard: {str(e)}")

@app.get("/leaderboard2")
def leaderboard2(class_ids: List[int] = Query(default=[1, 2, 3])):
    placeholders = ",".join("?" for _ in class_ids)

    sx_query = f"""
        SELECT
    m.RiderID AS riderid,
    rl.FullName AS fullname,
    COUNT(*) AS podiums
FROM SX_MAINS m
JOIN Rider_List rl
    ON rl.RiderID = m.RiderID
WHERE m.Result <= 3
  AND m.ClassID IN ({placeholders})
GROUP BY
    m.RiderID,
    rl.FullName
ORDER BY podiums DESC;
    """

    mx_query = f"""
        SELECT
    m.RiderID AS riderid,
    rl.FullName AS fullname,
    COUNT(*) AS podiums
FROM MX_OVERALLS m
JOIN Rider_List rl
    ON rl.RiderID = m.RiderID
WHERE m.Result <= 3
  AND m.ClassID IN ({placeholders})
GROUP BY
    m.RiderID,
    rl.FullName
ORDER BY podiums DESC;
    """

    try:
        with pyodbc.connect(CONN_STR) as conn:
            cursor = conn.cursor()

            cursor.execute(sx_query, class_ids)
            supercross = [
                {"riderid": row.riderid, "fullname": row.fullname, "podiums": row.podiums}
                for row in cursor.fetchall()
            ]

            cursor.execute(mx_query, class_ids)
            motocross = [
                {"riderid": row.riderid, "fullname": row.fullname, "podiums": row.podiums}
                for row in cursor.fetchall()
            ]

        return {"supercross": supercross, "motocross": motocross}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching podiums leaderboard: {str(e)}")
    
@app.get("/leaderboard4")
def leaderboard4(class_ids: List[int] = Query(default=[1, 2, 3])):
    placeholders = ",".join("?" for _ in class_ids)

    sx_query = f"""
        SELECT
    h.RiderID AS riderid,
    rl.FullName AS fullname,
    COUNT(*) AS heat_wins
FROM SX_HEATS h
JOIN Rider_List rl
    ON rl.RiderID = h.RiderID
WHERE h.Result = 1
  AND h.ClassID IN ({placeholders})
GROUP BY
    h.RiderID,
    rl.FullName
ORDER BY heat_wins DESC;
    """

    mx_query = f"""
        SELECT
    m.RiderID AS riderid,
    rl.FullName AS fullname,
    SUM(
        CASE WHEN m.Moto1 = 1 THEN 1 ELSE 0 END +
        CASE WHEN m.Moto2 = 1 THEN 1 ELSE 0 END
    ) AS moto_wins
FROM MX_OVERALLS m
JOIN Rider_List rl
    ON rl.RiderID = m.RiderID
WHERE m.ClassID IN ({placeholders})
GROUP BY
    m.RiderID,
    rl.FullName
HAVING SUM(
    CASE WHEN m.Moto1 = 1 THEN 1 ELSE 0 END +
    CASE WHEN m.Moto2 = 1 THEN 1 ELSE 0 END
) > 0
ORDER BY moto_wins DESC;
    """

    try:
        with pyodbc.connect(CONN_STR) as conn:
            cursor = conn.cursor()

            cursor.execute(sx_query, class_ids)
            supercross = [
                {"riderid": row.riderid, "fullname": row.fullname, "heat_wins": row.heat_wins}
                for row in cursor.fetchall()
            ]

            cursor.execute(mx_query, class_ids)
            motocross = [
                {"riderid": row.riderid, "fullname": row.fullname, "moto_wins": row.moto_wins}
                for row in cursor.fetchall()
            ]

        return {"supercross": supercross, "motocross": motocross}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching heat/moto wins leaderboard: {str(e)}")

@app.get("/api/race/overalls")
def get_mx_overalls(raceid: int, classid: int):

    with pyodbc.connect(CONN_STR) as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                mo.Result,
                COALESCE(rl.FullName, mo.FullName) AS FullName,
                mo.riderid,
                mo.Brand,
                mo.Moto1,
                mo.Moto2,
                mo.LapsLed,
                mo.Holeshot,
                mo.M1_Start,
                mo.M2_Start,
                rl.ImageURL
            FROM MX_OVERALLS mo
            LEFT JOIN Rider_List rl
                ON rl.RiderID = mo.RiderID
            WHERE mo.raceid = ?
            AND mo.classid = ?
            ORDER BY Result
        """, raceid, classid)

        columns = [column[0].lower() for column in cursor.description]

        results = [
            dict(zip(columns, row))
            for row in cursor.fetchall()
        ]

    return results

@app.get("/api/race/consi")
def get_mx_consi(raceid: int, classid: int):

    with pyodbc.connect(CONN_STR) as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                mc.Result AS Result,
                mc.riderid AS riderid,
                COALESCE(rl.FullName, mc.FullName) AS FullName,
                mc.Brand AS Brand
            FROM MX_CONSIS mc
            LEFT JOIN Rider_List rl
                ON rl.RiderID = mc.RiderID
            WHERE mc.raceid = ?
            AND mc.classid = ?
            ORDER BY mc.Result
        """, raceid, classid)

        columns = [column[0].lower() for column in cursor.description]

        results = [
            dict(zip(columns, row))
            for row in cursor.fetchall()
        ]

    return results

@app.get("/api/race/lcqs")
def get_supercross_lcqs(
    raceid: int,
    classid: int
):
    """
    Returns LCQ results for a race
    """

    query = """
        SELECT
            sxl.Result      AS result,
            sxl.riderid     AS riderid,
            COALESCE(rl.FullName, sxl.FullName) AS fullname,
            sxl.Brand       AS brand,
            sxl.RiderCoastID AS ridercoastid
        FROM SX_LCQS sxl
        LEFT JOIN Rider_List rl
            ON rl.RiderID = sxl.RiderID
        WHERE sxl.RaceID = :raceid
          AND sxl.ClassID = :classid
        ORDER BY sxl.Result
    """

    rows = fetch_all(query, {"raceid": raceid, "classid": classid})

    return rows


@app.get("/api/race/qualifying")
def get_qualifying(raceid: int, classid: int, sport_id: int):

    try:
        # 🔥 Supercross
        if sport_id == 1:
            query = """
                SELECT
                    sxq.Result      AS result,
                    sxq.riderid     AS riderid,
                    COALESCE(rl.FullName, sxq.FullName) AS fullname,
                    sxq.Brand       AS brand,
                    sxq.Best_Lap    AS best_lap,
                    sxq.RiderCoastID AS ridercoastid,
                    sxq.coastid     AS coastid
                FROM SX_QUAL sxq
                LEFT JOIN Rider_List rl
                    ON rl.RiderID = sxq.RiderID
                WHERE sxq.RaceID = :raceid
                  AND sxq.ClassID = :classid
                ORDER BY sxq.Result
            """

            return fetch_all(query, {
                "raceid": raceid,
                "classid": classid
            })

        # 🔥 Motocross
        else:
            with pyodbc.connect(CONN_STR) as conn:
                cursor = conn.cursor()

                cursor.execute("""
                    SELECT
                        mq.Result AS Result,
                        mq.riderid AS riderid,
                        COALESCE(rl.FullName, mq.FullName) AS FullName,
                        mq.Brand AS Brand,
                        mq.Best_Lap AS Best_Lap
                    FROM MX_QUAL mq
                    LEFT JOIN Rider_List rl
                        ON rl.RiderID = mq.RiderID
                    WHERE mq.raceid = ?
                      AND mq.classid = ?
                    ORDER BY mq.Result
                """, raceid, classid)

                columns = [column[0].lower() for column in cursor.description]

                return [
                    dict(zip(columns, row))
                    for row in cursor.fetchall()
                ]

    except Exception as e:
        return {"error": str(e)}


@app.get("/rider/{rider_id}/profile")
def get_rider_profile(rider_id: int, sport: str = "SX"):
    try:
        with pyodbc.connect(CONN_STR) as conn:
            cursor = conn.cursor()

            # -----------------------------
            # Rider identity
            # -----------------------------
            cursor.execute("""
                SELECT RiderID, FullName, Country, DOB, ImageURL
                FROM Rider_List
                WHERE RiderID = ?
            """, rider_id)

            rider = cursor.fetchone()
            if not rider:
                raise HTTPException(status_code=404, detail="Rider not found")

            rider_data = {
                "rider_id": rider.RiderID,
                "full_name": rider.FullName,
                "country": rider.Country,
                "dob": rider.DOB,
                "image_url": rider.ImageURL
            }

            # -----------------------------
            # SPORT AVAILABILITY
            # -----------------------------
            cursor.execute("""
SELECT
    CASE WHEN EXISTS (
        SELECT 1 FROM (
            SELECT RiderID FROM SX_MAINS
            UNION
            SELECT RiderID FROM SX_HEATS
            UNION
            SELECT RiderID FROM SX_LCQS
            UNION
            SELECT RiderID FROM SX_QUAL
        ) x
        WHERE RiderID = ?
    ) THEN 1 ELSE 0 END AS HasSX,

    CASE WHEN EXISTS (
        SELECT 1 FROM (
            SELECT RiderID FROM MX_OVERALLS
            UNION
            SELECT RiderID FROM MX_CONSIS
            UNION
            SELECT RiderID FROM MX_QUAL
        ) x
        WHERE RiderID = ?
    ) THEN 1 ELSE 0 END AS HasMX
""", rider_id, rider_id)

            availability = cursor.fetchone()

            has_sx = availability.HasSX == 1
            has_mx = availability.HasMX == 1

            # -----------------------------
            # SX MAIN STATS
            # -----------------------------
            cursor.execute("""
                WITH base AS (
                    SELECT
                        r.[Year],
                        m.ClassID,
                        COALESCE(m.RiderCoastID, cp.RiderCoastID) AS RiderCoastID,
                        m.Result,
                        m.Points,
                        m.LapsLed,
                        m.[Start],
                        m.Holeshot,
                        m.Brand
                    FROM SX_MAINS m
                    JOIN Race_Table r
                        ON r.RaceID = m.RaceID
                    LEFT JOIN CoastPool cp
                        ON cp.RiderID = m.RiderID
                       AND cp.[Year] = r.[Year]
                    WHERE m.RiderID = ?
                ),

                year_stats AS (
                    SELECT
                        [Year],
                        ClassID,
                        CASE 
                            WHEN ClassID = 1 THEN '450'
                            WHEN ClassID = 2 AND RiderCoastID = 1 THEN '250W'
                            WHEN ClassID = 2 AND RiderCoastID = 2 THEN '250E'
                            WHEN ClassID = 2 THEN '250'
                            WHEN ClassID = 3 THEN '500'
                        END AS Class,
                        Brand,

                        COUNT(*) AS Starts,
                        MIN(Result) AS Best,
                        CAST(ROUND(AVG(CAST(Result AS DECIMAL(10,2))), 2) AS DECIMAL(10,2)) AS AvgMainResult,

                        SUM(CASE WHEN Result <= 10 THEN 1 ELSE 0 END) AS Top10Count,
                        CAST(ROUND(100.0 * SUM(CASE WHEN Result <= 10 THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 2) AS DECIMAL(10,2)) AS Top10Pct,

                        SUM(CASE WHEN Result <= 5 THEN 1 ELSE 0 END) AS Top5Count,
                        CAST(ROUND(100.0 * SUM(CASE WHEN Result <= 5 THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 2) AS DECIMAL(10,2)) AS Top5Pct,

                        SUM(CASE WHEN Result <= 3 THEN 1 ELSE 0 END) AS Podiums,
                        CAST(ROUND(100.0 * SUM(CASE WHEN Result <= 3 THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 2) AS DECIMAL(10,2)) AS PodiumPct,

                        SUM(CASE WHEN Result = 1 THEN 1 ELSE 0 END) AS Wins,
                        CAST(ROUND(100.0 * SUM(CASE WHEN Result = 1 THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 2) AS DECIMAL(10,2)) AS WinPct,

                        SUM(COALESCE(LapsLed, 0)) AS LapsLed,

                        (
                            SELECT CAST(ROUND(AVG(CAST(s.[Start] AS DECIMAL(10,2))), 2) AS DECIMAL(10,2))
                            FROM (
                                SELECT m.[Start]
                                FROM SX_MAINS m
                                JOIN Race_Table r2
                                    ON r2.RaceID = m.RaceID
                                LEFT JOIN CoastPool cp2
                                    ON cp2.RiderID = m.RiderID
                                   AND cp2.[Year] = r2.[Year]
                                WHERE m.RiderID = ?
                                  AND m.ClassID = base.ClassID
                                  AND r2.[Year] = base.[Year]
                                  AND (
                                      base.ClassID <> 2
                                      OR COALESCE(m.RiderCoastID, cp2.RiderCoastID) = base.RiderCoastID
                                  )

                                UNION ALL

                                SELECT t.[Start]
                                FROM TC_MAINS t
                                JOIN Race_Table r3
                                    ON r3.RaceID = t.RaceID
                                LEFT JOIN CoastPool cp3
                                    ON cp3.RiderID = t.RiderID
                                   AND cp3.[Year] = r3.[Year]
                                WHERE t.RiderID = ?
                                  AND t.ClassID = base.ClassID
                                  AND r3.[Year] = base.[Year]
                                  AND (
                                      base.ClassID <> 2
                                      OR COALESCE(t.RiderCoastID, cp3.RiderCoastID) = base.RiderCoastID
                                  )
                            ) s
                        ) AS AvgStart,

                        SUM(CASE WHEN Holeshot = 1 THEN 1 ELSE 0 END) AS Holeshots,
                        SUM(COALESCE(Points, 0)) AS TotalPoints
                    FROM base
                    GROUP BY [Year], ClassID, RiderCoastID, Brand
                ),

                career_stats AS (

                    -- Per-class career rows (UNCHANGED: no coast split)
                    SELECT
                        NULL AS [Year],
                        ClassID,
                        CASE 
                            WHEN ClassID = 1 THEN '450'
                            WHEN ClassID = 2 THEN '250'
                            WHEN ClassID = 3 THEN '500'
                        END AS Class,
                        NULL AS Brand,

                        COUNT(*) AS Starts,
                        MIN(Result) AS Best,
                        CAST(ROUND(AVG(CAST(Result AS DECIMAL(10,2))), 2) AS DECIMAL(10,2)) AS AvgMainResult,

                        SUM(CASE WHEN Result <= 10 THEN 1 ELSE 0 END) AS Top10Count,
                        CAST(ROUND(100.0 * SUM(CASE WHEN Result <= 10 THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 2) AS DECIMAL(10,2)) AS Top10Pct,

                        SUM(CASE WHEN Result <= 5 THEN 1 ELSE 0 END) AS Top5Count,
                        CAST(ROUND(100.0 * SUM(CASE WHEN Result <= 5 THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 2) AS DECIMAL(10,2)) AS Top5Pct,

                        SUM(CASE WHEN Result <= 3 THEN 1 ELSE 0 END) AS Podiums,
                        CAST(ROUND(100.0 * SUM(CASE WHEN Result <= 3 THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 2) AS DECIMAL(10,2)) AS PodiumPct,

                        SUM(CASE WHEN Result = 1 THEN 1 ELSE 0 END) AS Wins,
                        CAST(ROUND(100.0 * SUM(CASE WHEN Result = 1 THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 2) AS DECIMAL(10,2)) AS WinPct,

                        SUM(COALESCE(LapsLed, 0)) AS LapsLed,

                        (
                            SELECT CAST(ROUND(AVG(CAST(s.[Start] AS DECIMAL(10,2))), 2) AS DECIMAL(10,2))
                            FROM (
                                SELECT m.[Start]
                                FROM SX_MAINS m
                                WHERE m.RiderID = ?
                                  AND m.ClassID = base.ClassID

                                UNION ALL

                                SELECT t.[Start]
                                FROM TC_MAINS t
                                WHERE t.RiderID = ?
                                  AND t.ClassID = base.ClassID
                            ) s
                        ) AS AvgStart,

                        SUM(CASE WHEN Holeshot = 1 THEN 1 ELSE 0 END) AS Holeshots,
                        SUM(COALESCE(Points, 0)) AS TotalPoints

                    FROM base
                    GROUP BY ClassID

                    UNION ALL

                    -- All classes combined row
                    SELECT
                        NULL AS [Year],
                        0 AS ClassID,
                        NULL AS Class,
                        NULL AS Brand,

                        COUNT(*) AS Starts,
                        MIN(Result) AS Best,
                        CAST(ROUND(AVG(CAST(Result AS DECIMAL(10,2))), 2) AS DECIMAL(10,2)) AS AvgMainResult,

                        SUM(CASE WHEN Result <= 10 THEN 1 ELSE 0 END) AS Top10Count,
                        CAST(ROUND(100.0 * SUM(CASE WHEN Result <= 10 THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 2) AS DECIMAL(10,2)) AS Top10Pct,

                        SUM(CASE WHEN Result <= 5 THEN 1 ELSE 0 END) AS Top5Count,
                        CAST(ROUND(100.0 * SUM(CASE WHEN Result <= 5 THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 2) AS DECIMAL(10,2)) AS Top5Pct,

                        SUM(CASE WHEN Result <= 3 THEN 1 ELSE 0 END) AS Podiums,
                        CAST(ROUND(100.0 * SUM(CASE WHEN Result <= 3 THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 2) AS DECIMAL(10,2)) AS PodiumPct,

                        SUM(CASE WHEN Result = 1 THEN 1 ELSE 0 END) AS Wins,
                        CAST(ROUND(100.0 * SUM(CASE WHEN Result = 1 THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 2) AS DECIMAL(10,2)) AS WinPct,

                        SUM(COALESCE(LapsLed, 0)) AS LapsLed,

                        (
                            SELECT CAST(ROUND(AVG(CAST(s.[Start] AS DECIMAL(10,2))), 2) AS DECIMAL(10,2))
                            FROM (
                                SELECT m.[Start]
                                FROM SX_MAINS m
                                WHERE m.RiderID = ?

                                UNION ALL

                                SELECT t.[Start]
                                FROM TC_MAINS t
                                WHERE t.RiderID = ?
                            ) s
                        ) AS AvgStart,

                        SUM(CASE WHEN Holeshot = 1 THEN 1 ELSE 0 END) AS Holeshots,
                        SUM(COALESCE(Points, 0)) AS TotalPoints

                    FROM base
                )

                SELECT *
                FROM (
                    SELECT * FROM year_stats
                    UNION ALL
                    SELECT * FROM career_stats
                ) x
                ORDER BY
                    CASE WHEN [Year] IS NULL THEN 1 ELSE 0 END,
                    [Year],
                    CASE
                        WHEN [Year] IS NULL THEN
                            CASE
                                WHEN ClassID = 2 THEN 1
                                WHEN ClassID = 1 THEN 2
                                WHEN ClassID = 0 THEN 3
                                ELSE 9
                            END
                        ELSE ClassID
                    END,
                    Brand;
            """, rider_id, rider_id, rider_id, rider_id, rider_id, rider_id, rider_id)

            columns = [col[0] for col in cursor.description]
            stats = [dict(zip(columns, row)) for row in cursor.fetchall()]

            # -----------------------------
            # SX QUAL / HEAT / LCQ STATS
            # -----------------------------
            cursor.execute("""
                WITH base AS (

                    SELECT
                        r.[Year],
                        q.ClassID,
                        COALESCE(q.RiderCoastID, cp.RiderCoastID) AS RiderCoastID,
                        q.Brand,
                        'QUAL' AS SessionType,
                        q.Result,
                        CAST(NULL AS INT) AS IsLcqTransfer
                    FROM SX_QUAL q
                    JOIN Race_Table r
                        ON r.RaceID = q.RaceID
                    LEFT JOIN CoastPool cp
                        ON cp.RiderID = q.RiderID
                       AND cp.[Year] = r.[Year]
                    WHERE q.RiderID = ?

                    UNION ALL

                    SELECT
                        r.[Year],
                        h.ClassID,
                        COALESCE(h.RiderCoastID, cp.RiderCoastID) AS RiderCoastID,
                        h.Brand,
                        'HEAT',
                        h.Result,
                        CAST(NULL AS INT)
                    FROM SX_HEATS h
                    JOIN Race_Table r
                        ON r.RaceID = h.RaceID
                    LEFT JOIN CoastPool cp
                        ON cp.RiderID = h.RiderID
                       AND cp.[Year] = r.[Year]
                    WHERE h.RiderID = ?

                    UNION ALL

                    SELECT
                        r.[Year],
                        l.ClassID,
                        COALESCE(l.RiderCoastID, cp.RiderCoastID) AS RiderCoastID,
                        l.Brand,
                        'LCQ',
                        l.Result,
                        CASE
                            WHEN EXISTS (
                                SELECT 1
                                FROM SX_MAINS m
                                WHERE m.RaceID = l.RaceID
                                  AND m.ClassID = l.ClassID
                                  AND m.RiderID = ?
                            )
                            THEN 1 ELSE 0
                        END
                    FROM SX_LCQS l
                    JOIN Race_Table r
                        ON r.RaceID = l.RaceID
                    LEFT JOIN CoastPool cp
                        ON cp.RiderID = l.RiderID
                       AND cp.[Year] = r.[Year]
                    WHERE l.RiderID = ?
                ),

                year_stats AS (
                    SELECT
                        [Year],
                        ClassID,
                        CASE
                            WHEN ClassID = 1 THEN '450'
                            WHEN ClassID = 2 AND RiderCoastID = 1 THEN '250W'
                            WHEN ClassID = 2 AND RiderCoastID = 2 THEN '250E'
                            WHEN ClassID = 2 THEN '250'
                            WHEN ClassID = 3 THEN '500'
                        END AS Class,
                        Brand,

                        SUM(CASE WHEN SessionType = 'QUAL' THEN 1 ELSE 0 END) AS QualStarts,
SUM(CASE WHEN SessionType = 'QUAL' AND Result = 1 THEN 1 ELSE 0 END) AS Poles,
MIN(CASE WHEN SessionType = 'QUAL' THEN Result END) AS BestQual,
CAST(ROUND(AVG(CASE WHEN SessionType = 'QUAL' THEN CAST(Result AS DECIMAL(10,2)) END), 2) AS DECIMAL(10,2)) AS AvgQualResult,

                        SUM(CASE WHEN SessionType = 'HEAT' THEN 1 ELSE 0 END) AS HeatStarts,
MIN(CASE WHEN SessionType = 'HEAT' THEN Result END) AS BestHeat,
SUM(CASE WHEN SessionType = 'HEAT' AND Result = 1 THEN 1 ELSE 0 END) AS HeatWins,
CAST(ROUND(AVG(CASE WHEN SessionType = 'HEAT' THEN CAST(Result AS DECIMAL(10,2)) END), 2) AS DECIMAL(10,2)) AS AvgHeatResult,

                        SUM(CASE WHEN SessionType = 'LCQ' THEN 1 ELSE 0 END) AS LcqStarts,
MIN(CASE WHEN SessionType = 'LCQ' THEN Result END) AS BestLcq,
SUM(CASE WHEN SessionType = 'LCQ' AND IsLcqTransfer = 1 THEN 1 ELSE 0 END) AS LcqTransfers,
                        CAST(ROUND(
                            100.0 * SUM(CASE WHEN SessionType = 'LCQ' AND IsLcqTransfer = 1 THEN 1 ELSE 0 END)
                            / NULLIF(SUM(CASE WHEN SessionType = 'LCQ' THEN 1 ELSE 0 END), 0),
                            2
                        ) AS DECIMAL(10,2)) AS LcqTransferPct,
                        SUM(CASE WHEN SessionType = 'LCQ' AND Result = 1 THEN 1 ELSE 0 END) AS LcqWins,
                        CAST(ROUND(AVG(CASE WHEN SessionType = 'LCQ' THEN CAST(Result AS DECIMAL(10,2)) END), 2) AS DECIMAL(10,2)) AS AvgLcqResult

                    FROM base
                    GROUP BY [Year], ClassID, RiderCoastID, Brand
                ),

                career_stats AS (

                    -- Per-class career rows (UNCHANGED: no coast split)
                    SELECT
                        NULL AS [Year],
                        ClassID,
                        CASE
                            WHEN ClassID = 1 THEN '450'
                            WHEN ClassID = 2 THEN '250'
                            WHEN ClassID = 3 THEN '500'
                        END AS Class,
                        NULL AS Brand,

                        SUM(CASE WHEN SessionType = 'QUAL' THEN 1 ELSE 0 END) AS QualStarts,
                        SUM(CASE WHEN SessionType = 'QUAL' AND Result = 1 THEN 1 ELSE 0 END) AS Poles,
                        MIN(CASE WHEN SessionType = 'QUAL' THEN Result END) AS BestQual,
                        CAST(ROUND(AVG(CASE WHEN SessionType = 'QUAL' THEN CAST(Result AS DECIMAL(10,2)) END), 2) AS DECIMAL(10,2)) AS AvgQualResult,

                        SUM(CASE WHEN SessionType = 'HEAT' THEN 1 ELSE 0 END) AS HeatStarts,
                        MIN(CASE WHEN SessionType = 'HEAT' THEN Result END) AS BestHeat,
                        SUM(CASE WHEN SessionType = 'HEAT' AND Result = 1 THEN 1 ELSE 0 END) AS HeatWins,
                        CAST(ROUND(AVG(CASE WHEN SessionType = 'HEAT' THEN CAST(Result AS DECIMAL(10,2)) END), 2) AS DECIMAL(10,2)) AS AvgHeatResult,

                        SUM(CASE WHEN SessionType = 'LCQ' THEN 1 ELSE 0 END) AS LcqStarts,
                        MIN(CASE WHEN SessionType = 'LCQ' THEN Result END) AS BestLcq,
                        SUM(CASE WHEN SessionType = 'LCQ' AND IsLcqTransfer = 1 THEN 1 ELSE 0 END) AS LcqTransfers,
                        CAST(ROUND(
                            100.0 * SUM(CASE WHEN SessionType = 'LCQ' AND IsLcqTransfer = 1 THEN 1 ELSE 0 END)
                            / NULLIF(SUM(CASE WHEN SessionType = 'LCQ' THEN 1 ELSE 0 END), 0),
                            2
                        ) AS DECIMAL(10,2)) AS LcqTransferPct,
                        SUM(CASE WHEN SessionType = 'LCQ' AND Result = 1 THEN 1 ELSE 0 END) AS LcqWins,
                        CAST(ROUND(AVG(CASE WHEN SessionType = 'LCQ' THEN CAST(Result AS DECIMAL(10,2)) END), 2) AS DECIMAL(10,2)) AS AvgLcqResult

                    FROM base
                    GROUP BY ClassID

                    UNION ALL

                    -- Combined career row
-- Combined career row
SELECT
    NULL AS [Year],
    0 AS ClassID,
    NULL AS Class,
    NULL AS Brand,

    -- QUAL
    SUM(CASE WHEN SessionType = 'QUAL' THEN 1 ELSE 0 END),
    SUM(CASE WHEN SessionType = 'QUAL' AND Result = 1 THEN 1 ELSE 0 END),
    MIN(CASE WHEN SessionType = 'QUAL' THEN Result END) AS BestQual,
    CAST(ROUND(AVG(CASE WHEN SessionType = 'QUAL' THEN CAST(Result AS DECIMAL(10,2)) END), 2) AS DECIMAL(10,2)),

    -- HEAT
    SUM(CASE WHEN SessionType = 'HEAT' THEN 1 ELSE 0 END),
    MIN(CASE WHEN SessionType = 'HEAT' THEN Result END) AS BestHeat,
    SUM(CASE WHEN SessionType = 'HEAT' AND Result = 1 THEN 1 ELSE 0 END),
    CAST(ROUND(AVG(CASE WHEN SessionType = 'HEAT' THEN CAST(Result AS DECIMAL(10,2)) END), 2) AS DECIMAL(10,2)),

    -- LCQ
    SUM(CASE WHEN SessionType = 'LCQ' THEN 1 ELSE 0 END),
    MIN(CASE WHEN SessionType = 'LCQ' THEN Result END) AS BestLcq,
    SUM(CASE WHEN SessionType = 'LCQ' AND IsLcqTransfer = 1 THEN 1 ELSE 0 END),
    CAST(ROUND(
        100.0 * SUM(CASE WHEN SessionType = 'LCQ' AND IsLcqTransfer = 1 THEN 1 ELSE 0 END)
        / NULLIF(SUM(CASE WHEN SessionType = 'LCQ' THEN 1 ELSE 0 END), 0),
        2
    ) AS DECIMAL(10,2)),
    SUM(CASE WHEN SessionType = 'LCQ' AND Result = 1 THEN 1 ELSE 0 END),
    CAST(ROUND(AVG(CASE WHEN SessionType = 'LCQ' THEN CAST(Result AS DECIMAL(10,2)) END), 2) AS DECIMAL(10,2))

FROM base
                )

                SELECT *
                FROM (
                    SELECT * FROM year_stats
                    UNION ALL
                    SELECT * FROM career_stats
                ) x
                ORDER BY
                    CASE WHEN [Year] IS NULL THEN 1 ELSE 0 END,
                    [Year],
                    CASE
                        WHEN [Year] IS NULL THEN
                            CASE
                                WHEN ClassID = 2 THEN 1
                                WHEN ClassID = 1 THEN 2
                                WHEN ClassID = 0 THEN 3
                                ELSE 9
                            END
                        ELSE ClassID
                    END;
            """, rider_id, rider_id, rider_id, rider_id)

            columns = [col[0] for col in cursor.description]
            qual_stats = [dict(zip(columns, row)) for row in cursor.fetchall()]

            # -----------------------------
            # RETURN SX DATA
            # -----------------------------
            if sport.upper() != "MX":
                return {
                    "rider": rider_data,
                    "stats": stats,
                    "qual_stats": qual_stats,
                    "hasSX": has_sx,
                    "hasMX": has_mx
                }


                        # -----------------------------
            # MOTOCROSS STATS
            # -----------------------------
            cursor.execute("""
WITH
/* =========================================================
   1) OVERALLS (moto appearances) — brand-aware
   ========================================================= */
overall_year_brand AS (
    SELECT
        r.[Year],
        o.ClassID,
        CASE 
            WHEN o.ClassID = 1 THEN '450'
            WHEN o.ClassID = 2 THEN '250'
            WHEN o.ClassID = 3 THEN '500'
        END AS Class,
        o.Brand,
        
        COUNT(*) AS Starts,
        MIN(o.Result) AS BestOverall,

MIN(
    CASE
        WHEN o.Moto1 IS NULL THEN o.Moto2
        WHEN o.Moto2 IS NULL THEN o.Moto1
        WHEN o.Moto1 < o.Moto2 THEN o.Moto1
        ELSE o.Moto2
    END
) AS BestMoto,                   

        CAST(ROUND(AVG(CAST(o.Result AS DECIMAL(10,2))), 2) AS DECIMAL(10,2)) AS AvgOverallFinish,

        CAST(ROUND(
            ( SUM(CAST(o.Moto1 AS DECIMAL(10,2)))
            + SUM(CAST(o.Moto2 AS DECIMAL(10,2))) )
            / NULLIF(
                SUM(CASE WHEN o.Moto1 IS NOT NULL THEN 1 ELSE 0 END)
              + SUM(CASE WHEN o.Moto2 IS NOT NULL THEN 1 ELSE 0 END),
              0
            ), 2) AS DECIMAL(10,2)) AS AvgMotoFinish,

        CAST(ROUND(AVG(CAST(o.Moto1 AS DECIMAL(10,2))), 2) AS DECIMAL(10,2)) AS AvgMoto1Finish,
        CAST(ROUND(AVG(CAST(o.Moto2 AS DECIMAL(10,2))), 2) AS DECIMAL(10,2)) AS AvgMoto2Finish,

        SUM(CASE WHEN o.Result <= 10 THEN 1 ELSE 0 END) AS Top10s,
        CAST(ROUND(100.0 * SUM(CASE WHEN o.Result <= 10 THEN 1 ELSE 0 END) / NULLIF(COUNT(*),0),2) AS DECIMAL(10,2)) AS Top10Pct,

        SUM(CASE WHEN o.Result <= 5 THEN 1 ELSE 0 END) AS Top5s,
        CAST(ROUND(100.0 * SUM(CASE WHEN o.Result <= 5 THEN 1 ELSE 0 END) / NULLIF(COUNT(*),0),2) AS DECIMAL(10,2)) AS Top5Pct,

        SUM(CASE WHEN o.Result <= 3 THEN 1 ELSE 0 END) AS Podiums,
        CAST(ROUND(100.0 * SUM(CASE WHEN o.Result <= 3 THEN 1 ELSE 0 END) / NULLIF(COUNT(*),0),2) AS DECIMAL(10,2)) AS PodiumPct,

        SUM(CASE WHEN o.Result = 1 THEN 1 ELSE 0 END) AS Wins,
        CAST(ROUND(100.0 * SUM(CASE WHEN o.Result = 1 THEN 1 ELSE 0 END) / NULLIF(COUNT(*),0),2) AS DECIMAL(10,2)) AS WinPct,

        SUM(
            CASE
                WHEN o.LapsLed IS NOT NULL THEN CAST(o.LapsLed AS INT)
                ELSE CAST(COALESCE(o.M1_Laps_Led,0) + COALESCE(o.M2_Laps_Led,0) AS INT)
            END
        ) AS LapsLed,

        SUM(COALESCE(o.Holeshot, 0)) AS Holeshots,

        CAST(ROUND(
            ( SUM(CASE WHEN o.M1_Start IS NOT NULL THEN CAST(o.M1_Start AS DECIMAL(10,2)) ELSE 0 END)
            + SUM(CASE WHEN o.M2_Start IS NOT NULL THEN CAST(o.M2_Start AS DECIMAL(10,2)) ELSE 0 END) )
            / NULLIF(
                SUM(CASE WHEN o.M1_Start IS NOT NULL THEN 1 ELSE 0 END)
              + SUM(CASE WHEN o.M2_Start IS NOT NULL THEN 1 ELSE 0 END),
              0
            ), 2) AS DECIMAL(10,2)) AS AvgStart,

        SUM(COALESCE(o.Points,0)) AS TotalPoints

    FROM MX_OVERALLS o
    JOIN Race_Table r
        ON r.RaceID = o.RaceID
    WHERE o.RiderID = ?
      AND o.Sport_ID = 2
    GROUP BY
        r.[Year],
        o.ClassID,
        CASE 
            WHEN o.ClassID = 1 THEN '450'
            WHEN o.ClassID = 2 THEN '250'
            WHEN o.ClassID = 3 THEN '500'
        END,
        o.Brand
),

/* =========================================================
   3) Union of (Year, ClassID, Brand) from both tables
      - ensures brands that ONLY appear in qualifying still show
   ========================================================= */
brand_union AS (
    SELECT [Year], ClassID, Brand FROM overall_year_brand
),

/* =========================================================
   4) Year + Brand rows (full outer by using brand_union)
   ========================================================= */
year_rows AS (
    SELECT
        b.[Year],
        b.ClassID,
        CASE 
            WHEN b.ClassID = 1 THEN '450'
            WHEN b.ClassID = 2 THEN '250'
            WHEN b.ClassID = 3 THEN '500'
        END AS Class,
        b.Brand,
        COALESCE(o.Starts, 0) AS Starts,
        o.BestOverall,
        o.BestMoto,
        o.AvgOverallFinish,
        o.AvgMotoFinish,
        o.AvgMoto1Finish,
        o.AvgMoto2Finish,
        o.Top10s,
        o.Top10Pct,
        o.Top5s,
        o.Top5Pct,
        o.Podiums,
        o.PodiumPct,
        o.Wins,
        o.WinPct,
        o.LapsLed,
        o.Holeshots,
        o.AvgStart,
        o.TotalPoints
    FROM brand_union b
    LEFT JOIN overall_year_brand o
        ON o.[Year] = b.[Year]
       AND o.ClassID = b.ClassID
       AND ( (o.Brand = b.Brand) OR (o.Brand IS NULL AND b.Brand IS NULL) )
),

/* =========================================================
   5) Career rows per class (Brand NULL)
   ========================================================= */
overall_career_class AS (
    SELECT
        o.ClassID,
        CASE 
            WHEN o.ClassID = 1 THEN '450'
            WHEN o.ClassID = 2 THEN '250'
            WHEN o.ClassID = 3 THEN '500'
        END AS Class,

        COUNT(*) AS Starts,
        MIN(o.Result) AS BestOverall,

MIN(
    CASE
        WHEN o.Moto1 IS NULL THEN o.Moto2
        WHEN o.Moto2 IS NULL THEN o.Moto1
        WHEN o.Moto1 < o.Moto2 THEN o.Moto1
        ELSE o.Moto2
    END
) AS BestMoto,
        CAST(ROUND(AVG(CAST(o.Result AS DECIMAL(10,2))), 2) AS DECIMAL(10,2)) AS AvgOverallFinish,

        CAST(ROUND(
            ( SUM(CAST(o.Moto1 AS DECIMAL(10,2)))
            + SUM(CAST(o.Moto2 AS DECIMAL(10,2))) )
            / NULLIF(
                SUM(CASE WHEN o.Moto1 IS NOT NULL THEN 1 ELSE 0 END)
              + SUM(CASE WHEN o.Moto2 IS NOT NULL THEN 1 ELSE 0 END),
              0
            ), 2) AS DECIMAL(10,2)) AS AvgMotoFinish,

        CAST(ROUND(AVG(CAST(o.Moto1 AS DECIMAL(10,2))), 2) AS DECIMAL(10,2)) AS AvgMoto1Finish,
        CAST(ROUND(AVG(CAST(o.Moto2 AS DECIMAL(10,2))), 2) AS DECIMAL(10,2)) AS AvgMoto2Finish,

        SUM(CASE WHEN o.Result <= 10 THEN 1 ELSE 0 END) AS Top10s,
        CAST(ROUND(100.0 * SUM(CASE WHEN o.Result <= 10 THEN 1 ELSE 0 END) / NULLIF(COUNT(*),0),2) AS DECIMAL(10,2)) AS Top10Pct,

        SUM(CASE WHEN o.Result <= 5 THEN 1 ELSE 0 END) AS Top5s,
        CAST(ROUND(100.0 * SUM(CASE WHEN o.Result <= 5 THEN 1 ELSE 0 END) / NULLIF(COUNT(*),0),2) AS DECIMAL(10,2)) AS Top5Pct,

        SUM(CASE WHEN o.Result <= 3 THEN 1 ELSE 0 END) AS Podiums,
        CAST(ROUND(100.0 * SUM(CASE WHEN o.Result <= 3 THEN 1 ELSE 0 END) / NULLIF(COUNT(*),0),2) AS DECIMAL(10,2)) AS PodiumPct,

        SUM(CASE WHEN o.Result = 1 THEN 1 ELSE 0 END) AS Wins,
        CAST(ROUND(100.0 * SUM(CASE WHEN o.Result = 1 THEN 1 ELSE 0 END) / NULLIF(COUNT(*),0),2) AS DECIMAL(10,2)) AS WinPct,

        SUM(
            CASE
                WHEN o.LapsLed IS NOT NULL THEN CAST(o.LapsLed AS INT)
                ELSE CAST(COALESCE(o.M1_Laps_Led,0) + COALESCE(o.M2_Laps_Led,0) AS INT)
            END
        ) AS LapsLed,
                           
        SUM(COALESCE(o.Holeshot, 0)) AS Holeshots,


        CAST(ROUND(
            ( SUM(CASE WHEN o.M1_Start IS NOT NULL THEN CAST(o.M1_Start AS DECIMAL(10,2)) ELSE 0 END)
            + SUM(CASE WHEN o.M2_Start IS NOT NULL THEN CAST(o.M2_Start AS DECIMAL(10,2)) ELSE 0 END) )
            / NULLIF(
                SUM(CASE WHEN o.M1_Start IS NOT NULL THEN 1 ELSE 0 END)
              + SUM(CASE WHEN o.M2_Start IS NOT NULL THEN 1 ELSE 0 END),
              0
            ), 2) AS DECIMAL(10,2)) AS AvgStart,

        SUM(COALESCE(o.Points,0)) AS TotalPoints
    FROM MX_OVERALLS o
    WHERE o.RiderID = ?
      AND o.Sport_ID = 2
    GROUP BY
        o.ClassID,
        CASE 
            WHEN o.ClassID = 1 THEN '450'
            WHEN o.ClassID = 2 THEN '250'
            WHEN o.ClassID = 3 THEN '500'
        END
),

career_class_rows AS (
    SELECT
        NULL AS [Year],
        o.ClassID,
        CASE 
    WHEN ClassID = 1 THEN '450'
    WHEN ClassID = 2 THEN '250'
END AS Class,
        NULL AS Brand,
        o.Starts,
        o.BestOverall,
        o.BestMoto,
        o.AvgOverallFinish,
        o.AvgMotoFinish,
        o.AvgMoto1Finish,
        o.AvgMoto2Finish,
        o.Top10s,
        o.Top10Pct,
        o.Top5s,
        o.Top5Pct,
        o.Podiums,
        o.PodiumPct,
        o.Wins,
        o.WinPct,
        o.LapsLed,
        o.Holeshots,
        o.AvgStart,
        o.TotalPoints
    FROM overall_career_class o
),

/* =========================================================
   6) Combined career row (Class NULL, Brand NULL)
   ========================================================= */
overall_career_combined AS (
    SELECT
        COUNT(*) AS Starts,
        MIN(o.Result) AS BestOverall,

MIN(
    CASE
        WHEN o.Moto1 IS NULL THEN o.Moto2
        WHEN o.Moto2 IS NULL THEN o.Moto1
        WHEN o.Moto1 < o.Moto2 THEN o.Moto1
        ELSE o.Moto2
    END
) AS BestMoto,

        CAST(ROUND(AVG(CAST(o.Result AS DECIMAL(10,2))), 2) AS DECIMAL(10,2)) AS AvgOverallFinish,

        CAST(ROUND(
            ( SUM(CAST(o.Moto1 AS DECIMAL(10,2)))
            + SUM(CAST(o.Moto2 AS DECIMAL(10,2))) )
            / NULLIF(
                SUM(CASE WHEN o.Moto1 IS NOT NULL THEN 1 ELSE 0 END)
              + SUM(CASE WHEN o.Moto2 IS NOT NULL THEN 1 ELSE 0 END),
              0
            ), 2) AS DECIMAL(10,2)) AS AvgMotoFinish,

        CAST(ROUND(AVG(CAST(o.Moto1 AS DECIMAL(10,2))), 2) AS DECIMAL(10,2)) AS AvgMoto1Finish,
        CAST(ROUND(AVG(CAST(o.Moto2 AS DECIMAL(10,2))), 2) AS DECIMAL(10,2)) AS AvgMoto2Finish,

        SUM(CASE WHEN o.Result <= 10 THEN 1 ELSE 0 END) AS Top10s,
        CAST(ROUND(100.0 * SUM(CASE WHEN o.Result <= 10 THEN 1 ELSE 0 END) / NULLIF(COUNT(*),0),2) AS DECIMAL(10,2)) AS Top10Pct,

        SUM(CASE WHEN o.Result <= 5 THEN 1 ELSE 0 END) AS Top5s,
        CAST(ROUND(100.0 * SUM(CASE WHEN o.Result <= 5 THEN 1 ELSE 0 END) / NULLIF(COUNT(*),0),2) AS DECIMAL(10,2)) AS Top5Pct,

        SUM(CASE WHEN o.Result <= 3 THEN 1 ELSE 0 END) AS Podiums,
        CAST(ROUND(100.0 * SUM(CASE WHEN o.Result <= 3 THEN 1 ELSE 0 END) / NULLIF(COUNT(*),0),2) AS DECIMAL(10,2)) AS PodiumPct,

        SUM(CASE WHEN o.Result = 1 THEN 1 ELSE 0 END) AS Wins,
        CAST(ROUND(100.0 * SUM(CASE WHEN o.Result = 1 THEN 1 ELSE 0 END) / NULLIF(COUNT(*),0),2) AS DECIMAL(10,2)) AS WinPct,

        SUM(
            CASE
                WHEN o.LapsLed IS NOT NULL THEN CAST(o.LapsLed AS INT)
                ELSE CAST(COALESCE(o.M1_Laps_Led,0) + COALESCE(o.M2_Laps_Led,0) AS INT)
            END
        ) AS LapsLed,

        SUM(COALESCE(o.Holeshot, 0)) AS Holeshots,

        CAST(ROUND(
            ( SUM(CASE WHEN o.M1_Start IS NOT NULL THEN CAST(o.M1_Start AS DECIMAL(10,2)) ELSE 0 END)
            + SUM(CASE WHEN o.M2_Start IS NOT NULL THEN CAST(o.M2_Start AS DECIMAL(10,2)) ELSE 0 END) )
            / NULLIF(
                SUM(CASE WHEN o.M1_Start IS NOT NULL THEN 1 ELSE 0 END)
              + SUM(CASE WHEN o.M2_Start IS NOT NULL THEN 1 ELSE 0 END),
              0
            ), 2) AS DECIMAL(10,2)) AS AvgStart,

        SUM(COALESCE(o.Points,0)) AS TotalPoints
    FROM MX_OVERALLS o
    WHERE o.RiderID = ?
      AND o.Sport_ID = 2
),


career_combined_row AS (
    SELECT
        NULL AS [Year],
        0 AS ClassID,
        NULL AS Class,
        NULL AS Brand,
        o.Starts,
        o.BestOverall,
        o.BestMoto,
        o.AvgOverallFinish,
        o.AvgMotoFinish,
        o.AvgMoto1Finish,
        o.AvgMoto2Finish,
        o.Top10s,
        o.Top10Pct,
        o.Top5s,
        o.Top5Pct,
        o.Podiums,
        o.PodiumPct,
        o.Wins,
        o.WinPct,
        o.LapsLed,
        o.Holeshots,
        o.AvgStart,
        o.TotalPoints
    FROM overall_career_combined o
),

/* =========================================================
   7) Final union
   ========================================================= */
final_rows AS (
    SELECT * FROM year_rows
    UNION ALL
    SELECT * FROM career_class_rows
    UNION ALL
    SELECT * FROM career_combined_row
)

SELECT
    [Year],
    Class,
    Brand,
    Starts,
    BestOverall,
    BestMoto,
    AvgOverallFinish,
    AvgMotoFinish,
    AvgMoto1Finish,
    AvgMoto2Finish,
    Top10s,
    Top10Pct,
    Top5s,
    Top5Pct,
    Podiums,
    PodiumPct,
    Wins,
    WinPct,
    LapsLed,
    Holeshots,
    AvgStart,
    TotalPoints
FROM final_rows
ORDER BY
    CASE WHEN [Year] IS NULL THEN 1 ELSE 0 END,
    [Year],
    CASE
        WHEN [Year] IS NULL THEN
            CASE
                WHEN ClassID = 2 THEN 1
                WHEN ClassID = 1 THEN 2
                WHEN ClassID = 3 THEN 3
                WHEN ClassID = 0 THEN 3
                ELSE 9
            END
        ELSE ClassID
    END,
    Brand;
""",
rider_id,
rider_id,
rider_id
)

            columns = [col[0] for col in cursor.description]
            mx_stats = [dict(zip(columns, row)) for row in cursor.fetchall()]

            # -----------------------------
# MX QUAL / CONSI STATS
# -----------------------------
            cursor.execute("""
WITH QualYearly AS (
    SELECT
        r.Year,
        q.ClassID,
        q.Brand,
        COUNT(DISTINCT q.RaceID) AS QualAppearances,
        CAST(ROUND(AVG(CAST(q.Result AS FLOAT)), 2) AS DECIMAL(10,2)) AS AvgQual,
        MIN(q.Result) AS BestQual,
        SUM(CASE WHEN q.Result = 1 THEN 1 ELSE 0 END) AS Poles
    FROM MX_QUAL q
    JOIN Race_Table r
        ON r.RaceID = q.RaceID
    WHERE q.RiderID = ?
    GROUP BY
        r.Year,
        q.ClassID,
        q.Brand
),

ConsiYearly AS (
    SELECT
        r.Year,
        c.ClassID,
        c.Brand,
        COUNT(DISTINCT c.RaceID) AS ConsiAppearances,
        CAST(ROUND(AVG(CAST(c.Result AS FLOAT)), 2) AS DECIMAL(10,2)) AS AvgConsi,
        MIN(c.Result) AS BestConsi,
        SUM(CASE WHEN c.Result = 1 THEN 1 ELSE 0 END) AS ConsiWins
    FROM MX_CONSIS c
    JOIN Race_Table r
        ON r.RaceID = c.RaceID
    WHERE c.RiderID = ?
    GROUP BY
        r.Year,
        c.ClassID,
        c.Brand
),

BrandUnion AS (
    SELECT Year, ClassID, Brand FROM QualYearly
    UNION
    SELECT Year, ClassID, Brand FROM ConsiYearly
),

Yearly AS (
    SELECT
        bu.Year,
        bu.ClassID,
        bu.Brand,

        ISNULL(q.QualAppearances, 0) AS QualAppearances,
        q.AvgQual,
        q.BestQual,
        ISNULL(q.Poles, 0) AS Poles,

        ISNULL(c.ConsiAppearances, 0) AS ConsiAppearances,
        c.AvgConsi,
        c.BestConsi,
        ISNULL(c.ConsiWins, 0) AS ConsiWins
    FROM BrandUnion bu
    LEFT JOIN QualYearly q
        ON bu.Year = q.Year
        AND bu.ClassID = q.ClassID
        AND (
            (bu.Brand = q.Brand)
            OR (bu.Brand IS NULL AND q.Brand IS NULL)
        )
    LEFT JOIN ConsiYearly c
        ON bu.Year = c.Year
        AND bu.ClassID = c.ClassID
        AND (
            (bu.Brand = c.Brand)
            OR (bu.Brand IS NULL AND c.Brand IS NULL)
        )
),

Career AS (
    SELECT
        NULL AS Year,
        ClassID,
        NULL AS Brand,

        COUNT(DISTINCT CASE WHEN Source = 'Qual' THEN RaceID END) AS QualAppearances,
        CAST(ROUND(AVG(CASE WHEN Source = 'Qual' THEN CAST(Result AS FLOAT) END), 2) AS DECIMAL(10,2)) AS AvgQual,
        MIN(CASE WHEN Source = 'Qual' THEN Result END) AS BestQual,
        SUM(CASE WHEN Source = 'Qual' AND Result = 1 THEN 1 ELSE 0 END) AS Poles,

        COUNT(DISTINCT CASE WHEN Source = 'Consi' THEN RaceID END) AS ConsiAppearances,
        CAST(ROUND(AVG(CASE WHEN Source = 'Consi' THEN CAST(Result AS FLOAT) END), 2) AS DECIMAL(10,2)) AS AvgConsi,
        MIN(CASE WHEN Source = 'Consi' THEN Result END) AS BestConsi,
        SUM(CASE WHEN Source = 'Consi' AND Result = 1 THEN 1 ELSE 0 END) AS ConsiWins
    FROM (
        SELECT ClassID, RaceID, Result, 'Qual' AS Source FROM MX_QUAL WHERE RiderID = ?
        UNION ALL
        SELECT ClassID, RaceID, Result, 'Consi' AS Source FROM MX_CONSIS WHERE RiderID = ?
    ) x
    GROUP BY ClassID

    UNION ALL

    SELECT
        NULL AS Year,
        0 AS ClassID,
        NULL AS Brand,

        COUNT(DISTINCT CASE WHEN Source = 'Qual' THEN RaceID END) AS QualAppearances,
        CAST(ROUND(AVG(CASE WHEN Source = 'Qual' THEN CAST(Result AS FLOAT) END), 2) AS DECIMAL(10,2)) AS AvgQual,
        MIN(CASE WHEN Source = 'Qual' THEN Result END) AS BestQual,
        SUM(CASE WHEN Source = 'Qual' AND Result = 1 THEN 1 ELSE 0 END) AS Poles,

        COUNT(DISTINCT CASE WHEN Source = 'Consi' THEN RaceID END) AS ConsiAppearances,
        CAST(ROUND(AVG(CASE WHEN Source = 'Consi' THEN CAST(Result AS FLOAT) END), 2) AS DECIMAL(10,2)) AS AvgConsi,
        MIN(CASE WHEN Source = 'Consi' THEN Result END) AS BestConsi,
        SUM(CASE WHEN Source = 'Consi' AND Result = 1 THEN 1 ELSE 0 END) AS ConsiWins
    FROM (
        SELECT RaceID, Result, 'Qual' AS Source FROM MX_QUAL WHERE RiderID = ?
        UNION ALL
        SELECT RaceID, Result, 'Consi' AS Source FROM MX_CONSIS WHERE RiderID = ?
    ) x
)

SELECT
    Year,
    CASE
        WHEN ClassID = 1 THEN '450'
        WHEN ClassID = 2 THEN '250'
        WHEN ClassID = 3 THEN '500'
        WHEN ClassID = 0 THEN NULL
    END AS Class,
    Brand,
    QualAppearances,
    AvgQual,
    BestQual,
    Poles,
    ConsiAppearances,
    AvgConsi,
    BestConsi,
    ConsiWins
FROM (
    SELECT * FROM Yearly
    UNION ALL
    SELECT * FROM Career
) final
ORDER BY
    CASE WHEN Year IS NULL THEN 1 ELSE 0 END,
    Year,
    CASE
        WHEN Year IS NULL THEN
            CASE
                WHEN ClassID = 2 THEN 1
                WHEN ClassID = 1 THEN 2
                WHEN ClassID = 3 THEN 3
                WHEN ClassID = 0 THEN 4
            END
        ELSE ClassID
    END,
    Brand;
""", rider_id, rider_id, rider_id, rider_id, rider_id, rider_id)

            columns = [col[0] for col in cursor.description]
            mx_qual_stats = [dict(zip(columns, row)) for row in cursor.fetchall()]

            return {
    "rider": rider_data,
    "mx_stats": mx_stats,
    "mx_qual_stats": mx_qual_stats,
    "hasSX": has_sx,
    "hasMX": has_mx
}
        

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

@app.get("/api/race/main-event")
def get_supercross_main_event(
    raceid: int
):
    """
    Returns Main Event results for a single Supercross race,
    split into Premier (450) and Lites (250) classes.
    """

    query = """
        SELECT
            sx.ClassID,
            sx.Result              AS result,
            sx.riderid             AS riderid,
            COALESCE(rl.FullName, sx.FullName) AS fullname,
            sx.Brand               AS brand,
            sx.Interval            AS interval,
            sx.BestLap             AS bestlap,
            sx.LapsLed             AS lapsled,
            sx.Holeshot            AS holeshot,
            sx.HoleshotPos         AS holeshotpos,
            sx.[Start]             AS Lap1Pos,
            sx.TC1                 AS tc1,
            sx.TC2                 AS tc2,
            sx.TC3                 AS tc3,
            sx.RiderCoastID        AS ridercoastid,
            sx.coastid             AS coastid,
            rl.ImageURL            AS imageurl
        FROM SX_MAINS sx
        LEFT JOIN Rider_List rl
            ON rl.RiderID = sx.RiderID
        WHERE sx.RaceID = :raceid
        ORDER BY ClassID, Result
    """

    rows = fetch_all(query, {"raceid": raceid})

    class450 = []
    class250 = []

    for row in rows:
        if row["ClassID"] == 1:
            class450.append(row)
        elif row["ClassID"] == 2:
            class250.append(row)

    return {
        "class450": class450,
        "class250": class250
    }

@app.get("/api/race/triple-crown-mains")
def get_supercross_triple_crown_mains(raceid: int):
    """
    Returns individual Triple Crown mains for a single Supercross race,
    split by class (450 / 250) and main number (1 / 2 / 3).
    """

    query = """
        SELECT
            tc.classid             AS classid,
            tc.main                AS main,
            tc.Result              AS result,
            tc.riderid             AS riderid,
            COALESCE(rl.FullName, tc.FullName) AS fullname,
            tc.Brand               AS brand,
            tc.Interval            AS interval,
            tc.BestLap             AS bestlap,
            tc.LapsLed             AS lapsled,
            tc.Holeshot            AS holeshot,
            tc.HoleshotPos         AS holeshotpos,
            tc.[Start]             AS Lap1Pos,
            tc.RiderCoastID        AS ridercoastid,
            tc.coastid             AS coastid,
            rl.ImageURL            AS imageurl
        FROM TC_MAINS tc
        LEFT JOIN Rider_List rl
            ON rl.RiderID = tc.RiderID
        WHERE tc.raceid = :raceid
        ORDER BY tc.classid, tc.main, tc.Result
    """

    rows = fetch_all(query, {"raceid": raceid})

    response = {
        "class450_main1": [],
        "class450_main2": [],
        "class450_main3": [],
        "class250_main1": [],
        "class250_main2": [],
        "class250_main3": [],
    }

    for row in rows:
        classid = row.get("classid")
        main = row.get("main")
        if classid == 1 and main in (1, 2, 3):
            response[f"class450_main{main}"].append(row)
        elif classid == 2 and main in (1, 2, 3):
            response[f"class250_main{main}"].append(row)

    return response

@app.get("/api/race/heats")
def get_supercross_heats(
    raceid: int,
    classid: int
):
    """
    Returns heat race results grouped by Heat number
    """

    query = """
        SELECT
            sxh.Heat        AS Heat,
            sxh.Result      AS result,
            sxh.riderid     AS riderid,
            COALESCE(rl.FullName, sxh.FullName) AS fullname,
            sxh.Brand       AS brand,
            sxh.RiderCoastID AS ridercoastid,
            sxh.coastid     AS coastid
        FROM SX_HEATS sxh
        LEFT JOIN Rider_List rl
            ON rl.RiderID = sxh.RiderID
        WHERE sxh.RaceID = :raceid
          AND sxh.ClassID = :classid
        ORDER BY sxh.Heat, sxh.Result
    """

    rows = fetch_all(query, {"raceid": raceid, "classid": classid})

    heats = {}

    for row in rows:
        heat_num = row["Heat"]
        heats.setdefault(heat_num, []).append(row)

    return heats

@app.get("/rider/{rider_id}/race-results")
def get_rider_race_results(rider_id: int):
    try:
        with pyodbc.connect(CONN_STR) as conn:
            cursor = conn.cursor()

            # 🔹 Get rider header info FIRST
            cursor.execute("""
    SELECT FullName, Country, ImageURL
    FROM Rider_List
    WHERE RiderID = ?
""", rider_id)

            rider = cursor.fetchone()

            rider_data = {
    "full_name": rider.FullName,
    "country": rider.Country,
    "image_url": rider.ImageURL
}

            cursor.execute("""
DECLARE @RiderID INT = ?;

/* ===============================
   SUPERCROSS RESULTS
=============================== */

WITH RiderRaceClasses AS (
    SELECT DISTINCT RaceID, ClassID
    FROM (
        SELECT RaceID, ClassID FROM SX_MAINS WHERE RiderID = @RiderID
        UNION ALL
        SELECT RaceID, ClassID FROM SX_HEATS WHERE RiderID = @RiderID
        UNION ALL
        SELECT RaceID, ClassID FROM SX_LCQS WHERE RiderID = @RiderID
        UNION ALL
        SELECT RaceID, ClassID FROM SX_QUAL WHERE RiderID = @RiderID
    ) x
),

MainResults AS (
    SELECT RaceID, Result, Brand, ClassID
    FROM SX_MAINS
    WHERE RiderID = @RiderID
),

HeatResults AS (
    SELECT RaceID,
           ClassID,
           MIN(Result) AS HeatResult,
           MAX(Brand) AS Brand
    FROM SX_HEATS
    WHERE RiderID = @RiderID
    GROUP BY RaceID, ClassID
),

LCQResults AS (
    SELECT 
        RaceID,
        MIN(Result) AS LCQResult,
        ClassID,
        MAX(Brand) AS Brand
    FROM SX_LCQS
    WHERE RiderID = @RiderID
    GROUP BY RaceID, ClassID
),

QualResults AS (
    SELECT RaceID,
           ClassID,
           MIN(Result) AS QualResult,
           MAX(Brand) AS Brand
    FROM SX_QUAL
    WHERE RiderID = @RiderID
    GROUP BY RaceID, ClassID
),

SXResults AS (

SELECT
    COALESCE(CAST(m.Result AS VARCHAR), '-') AS Result,
    rt.RaceID,
    rt.TrackID,
    rt.TrackName,
    rt.RaceDate,

    CASE 
    WHEN rc.ClassID = 1 THEN '450SX'
    WHEN rc.ClassID = 2 THEN '250SX'
    ELSE '-'
END AS Class,

    COALESCE(q.Brand, h.Brand, l.Brand, m.Brand, '-') AS Brand,
    COALESCE(CAST(q.QualResult AS VARCHAR), '-') AS QualResult,
    COALESCE(CAST(h.HeatResult AS VARCHAR), '-') AS HeatResult,
    COALESCE(CAST(l.LCQResult AS VARCHAR), '-') AS LCQResult,

    'SX' AS Discipline

FROM RiderRaceClasses rc
JOIN Race_Table rt ON rt.RaceID = rc.RaceID
LEFT JOIN MainResults m 
    ON m.RaceID = rc.RaceID
   AND m.ClassID = rc.ClassID

LEFT JOIN HeatResults h 
    ON h.RaceID = rc.RaceID 
   AND h.ClassID = rc.ClassID

LEFT JOIN LCQResults l 
    ON l.RaceID = rc.RaceID 
   AND l.ClassID = rc.ClassID

LEFT JOIN QualResults q 
    ON q.RaceID = rc.RaceID 
   AND q.ClassID = rc.ClassID

WHERE rt.SportID = 1
),

/* ===============================
   MOTOCROSS RESULTS
=============================== */

MX_RiderRaces AS (
    SELECT DISTINCT RaceID
    FROM (
        SELECT RaceID FROM MX_OVERALLS WHERE RiderID = @RiderID
        UNION ALL
        SELECT RaceID FROM MX_CONSIS WHERE RiderID = @RiderID
        UNION ALL
        SELECT RaceID FROM MX_QUAL WHERE RiderID = @RiderID
    ) x
),

MXResults AS (

SELECT
    COALESCE(CAST(mo.Result AS VARCHAR), '-') AS Result,
    rt.RaceID,
    rt.TrackID,
    rt.TrackName,
    rt.RaceDate,

    CASE 
        WHEN COALESCE(mo.ClassID, mq.ClassID, mc.ClassID) = 1 THEN '450MX'
        WHEN COALESCE(mo.ClassID, mq.ClassID, mc.ClassID) = 2 THEN '250MX'
        WHEN COALESCE(mo.ClassID, mq.ClassID, mc.ClassID) = 3 THEN '500MX'
        ELSE '-'
    END AS Class,

    COALESCE(mo.Brand, mq.Brand, mc.Brand, '-') AS Brand,

    COALESCE(CAST(mq.Result AS VARCHAR), '-') AS QualResult,

    '-' AS HeatResult,

    COALESCE(CAST(mc.Result AS VARCHAR), '-') AS LCQResult,

    'MX' AS Discipline

FROM MX_RiderRaces rr
JOIN Race_Table rt ON rt.RaceID = rr.RaceID

LEFT JOIN MX_OVERALLS mo
    ON mo.RaceID = rr.RaceID
    AND mo.RiderID = @RiderID

LEFT JOIN MX_QUAL mq
    ON mq.RaceID = rr.RaceID
    AND mq.RiderID = @RiderID

LEFT JOIN MX_CONSIS mc
    ON mc.RaceID = rr.RaceID
    AND mc.RiderID = @RiderID

WHERE rt.SportID = 2
)

/* ===============================
   FINAL OUTPUT
=============================== */

SELECT *
FROM (
    SELECT * FROM SXResults
    UNION ALL
    SELECT * FROM MXResults
) x

ORDER BY RaceDate DESC
""", rider_id)

            columns = [column[0] for column in cursor.description]

            results = [
                dict(zip(columns, row))
                for row in cursor.fetchall()
            ]

            return {
    "rider": rider_data,
    "results": results
}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/leaderboard3")
def leaderboard3(class_ids: List[int] = Query(default=[1, 2, 3])):
    placeholders = ",".join("?" for _ in class_ids)

    sx_query = f"""
        SELECT
    m.RiderID AS riderid,
    rl.FullName AS fullname,
    COUNT(*) AS starts
FROM SX_MAINS m
JOIN Rider_List rl
    ON rl.RiderID = m.RiderID
WHERE m.ClassID IN ({placeholders})
GROUP BY
    m.RiderID,
    rl.FullName
ORDER BY starts DESC;
    """

    mx_query = f"""
        SELECT
    m.RiderID AS riderid,
    rl.FullName AS fullname,
    COUNT(*) AS starts
FROM MX_OVERALLS m
JOIN Rider_List rl
    ON rl.RiderID = m.RiderID
WHERE m.ClassID IN ({placeholders})
GROUP BY
    m.RiderID,
    rl.FullName
ORDER BY starts DESC;
    """

    try:
        with pyodbc.connect(CONN_STR) as conn:
            cursor = conn.cursor()

            cursor.execute(sx_query, class_ids)
            supercross = [
                {"riderid": row.riderid, "fullname": row.fullname, "starts": row.starts}
                for row in cursor.fetchall()
            ]

            cursor.execute(mx_query, class_ids)
            motocross = [
                {"riderid": row.riderid, "fullname": row.fullname, "starts": row.starts}
                for row in cursor.fetchall()
            ]

        return {"supercross": supercross, "motocross": motocross}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching starts leaderboard: {str(e)}")



@app.get("/compare")
def compare_riders(
    rider1: int,
    rider2: int,
    sport: str,
    classid: Optional[int] = Query(default=None)
):

    with engine.connect() as conn:

        # ======================
        # SX LOGIC
        # ======================
        if sport == "sx":

            main_query = text("""
                SELECT
                    RiderID,
                    COUNT(*) AS Starts,
                    ROUND(AVG(CAST(Result AS FLOAT)), 2) AS AvgFinish,
                    SUM(CASE WHEN Result = 1 THEN 1 ELSE 0 END) AS Wins,
                    ROUND(100.0 * SUM(CASE WHEN Result = 1 THEN 1 ELSE 0 END) / NULLIF(COUNT(*),0),1) AS WinPct,
                    SUM(CASE WHEN Result <= 3 THEN 1 ELSE 0 END) AS Podiums,
                    ROUND(100.0 * SUM(CASE WHEN Result <= 3 THEN 1 ELSE 0 END) / NULLIF(COUNT(*),0),1) AS PodiumPct,
                    ROUND(100.0 * SUM(CASE WHEN Result <= 5 THEN 1 ELSE 0 END) / NULLIF(COUNT(*),0),1) AS Top5Pct,
                    ROUND(100.0 * SUM(CASE WHEN Result <= 10 THEN 1 ELSE 0 END) / NULLIF(COUNT(*),0),1) AS Top10Pct,
                    SUM(ISNULL(LapsLed,0)) AS LapsLed
                FROM SX_MAINS
                WHERE RiderID IN (:r1, :r2)
                AND (:classid IS NULL OR ClassID = :classid)
                GROUP BY RiderID
            """)

            heat_query = text("""
    SELECT
        r.RiderID,
        ROUND(AVG(CAST(h.Result AS FLOAT)), 2) AS HeatAvg,
        SUM(CASE WHEN h.Result = 1 THEN 1 ELSE 0 END) AS HeatWins
    FROM (
        SELECT :r1 AS RiderID
        UNION
        SELECT :r2
    ) r
    LEFT JOIN SX_HEATS h
        ON h.RiderID = r.RiderID
       AND (:classid IS NULL OR h.ClassID = :classid)
    GROUP BY r.RiderID
""")

            qual_query = text("""
    SELECT
        r.RiderID,
        ROUND(AVG(CAST(q.Result AS FLOAT)), 2) AS QualAvg,
        SUM(CASE WHEN q.Result = 1 THEN 1 ELSE 0 END) AS Poles
    FROM (
        SELECT :r1 AS RiderID
        UNION
        SELECT :r2
    ) r
    LEFT JOIN SX_QUAL q
        ON q.RiderID = r.RiderID
       AND (:classid IS NULL OR q.ClassID = :classid)
    GROUP BY r.RiderID
""")

            sport_id = 1

        # ======================
        # MX LOGIC
        # ======================
        else:

            main_query = text("""
                SELECT
                    RiderID,
                    COUNT(*) AS Starts,
                    ROUND(AVG(CAST(Result AS FLOAT)), 2) AS AvgFinish,
                    SUM(CASE WHEN Result = 1 THEN 1 ELSE 0 END) AS Wins,
                    ROUND(
                        100.0 * SUM(CASE WHEN Result = 1 THEN 1 ELSE 0 END)
                        / NULLIF(COUNT(*), 0), 1
                    ) AS WinPct,
                    SUM(CASE WHEN Moto1 = 1 THEN 1 ELSE 0 END)
                    + SUM(CASE WHEN Moto2 = 1 THEN 1 ELSE 0 END)
                    + SUM(CASE WHEN Moto3 = 1 THEN 1 ELSE 0 END) AS MotoWins,
                    SUM(CASE WHEN Result <= 3 THEN 1 ELSE 0 END) AS Podiums,
                    ROUND(
                        100.0 * SUM(CASE WHEN Result <= 3 THEN 1 ELSE 0 END)
                        / NULLIF(COUNT(*), 0), 1
                    ) AS PodiumPct,
                    ROUND(
                        100.0 * SUM(CASE WHEN Result <= 5 THEN 1 ELSE 0 END)
                        / NULLIF(COUNT(*), 0), 1
                    ) AS Top5Pct,
                    ROUND(
                        100.0 * SUM(CASE WHEN Result <= 10 THEN 1 ELSE 0 END)
                        / NULLIF(COUNT(*), 0), 1
                    ) AS Top10Pct,
                    SUM(ISNULL(LapsLed, 0)) AS LapsLed
                FROM MX_OVERALLS
                WHERE RiderID IN (:r1, :r2)
                  AND (:classid IS NULL OR ClassID = :classid)
                GROUP BY RiderID
            """)

            heat_query = None

            qual_query = text("""
                SELECT
                    RiderID,
                    ROUND(AVG(CAST(Result AS FLOAT)), 2) AS QualAvg,
                    SUM(CASE WHEN Result = 1 THEN 1 ELSE 0 END) AS Poles
                FROM MX_QUAL
                WHERE RiderID IN (:r1, :r2)
                  AND (:classid IS NULL OR ClassID = :classid)
                GROUP BY RiderID
            """)

            sport_id = 2

        params = {"r1": rider1, "r2": rider2, "classid": classid}

        main_rows = conn.execute(main_query, params).mappings().all()

        heat_rows = (
            conn.execute(heat_query, params).mappings().all()
            if heat_query is not None else []
)
        qual_rows = (
            conn.execute(qual_query, params).mappings().all()
            if qual_query is not None else []
)
        champ_query = text("""
            SELECT RiderID, ClassID, COUNT(*) AS Titles
            FROM Champions
            WHERE RiderID IN (:r1, :r2)
            AND SportID = :sportid
            GROUP BY RiderID, ClassID
        """)

        champ_rows = conn.execute(champ_query, {
            "r1": rider1,
            "r2": rider2,
            "sportid": sport_id
        }).mappings().all()

        rider_query = """
SELECT RiderID, FullName, ImageURL
FROM Rider_List
WHERE RiderID IN (:r1, :r2)
"""
        riders = fetch_all(rider_query, {"r1": rider1, "r2": rider2})

        return {
            "main": main_rows,
            "heats": heat_rows,
            "qual": qual_rows,
            "championships": champ_rows,
            "riders": riders   # 👈 NEW
        }
    
    
@app.get("/api/riders/search")
def search_riders(q: str = Query(..., min_length=2)):
    query = """
        SELECT TOP 20
            RiderID,
            FullName,
            country AS Country,
            ImageURL
        FROM Rider_List
        WHERE 
            LOWER(FullName) LIKE LOWER(:search)
        ORDER BY 
            CASE 
                WHEN LOWER(FullName) LIKE LOWER(:starts) THEN 0
                ELSE 1
            END,
            FullName
    """

    rows = fetch_all(query, {
    "search": f"%{q}%",
    "starts": f"{q}%"
})

    return [
    {
        "RiderID": row["RiderID"],
        "FullName": row["FullName"],
        "Country": row["Country"],   # 👈 THIS FIXES IT
        "ImageURL": row["ImageURL"]
    }
        for row in rows
]

from fastapi import APIRouter, HTTPException
from sqlalchemy import create_engine

router = APIRouter()

@app.get("/api/track-profile")
def get_track_profile(track_id: int, sport_id: int, class_id: int):

    if sport_id == 1:
        query = """
        DECLARE @TrackID INT = ?;
        DECLARE @ClassID INT = ?;

        IF OBJECT_ID('tempdb..#FilteredMains') IS NOT NULL
            DROP TABLE #FilteredMains;

        SELECT
            sm.RiderID,
            sm.FullName,
            sm.Result,
            sm.RaceID,
            sm.Brand
        INTO #FilteredMains
        FROM SX_MAINS sm
        JOIN Race_Table rt
            ON rt.RaceID = sm.RaceID
        WHERE rt.TrackID = @TrackID
          AND rt.SportID = 1
          AND sm.ClassID = @ClassID;

        SELECT
            rt.TrackName,
            rt.RaceID,
            rt.RaceDate,
            fm.FullName AS Winner,
            fm.Brand
        FROM #FilteredMains fm
        JOIN Race_Table rt
            ON rt.RaceID = fm.RaceID
        WHERE fm.Result = 1
        ORDER BY rt.RaceDate DESC, rt.RaceID DESC;

        SELECT
            ROW_NUMBER() OVER (ORDER BY COUNT(*) DESC, fm.FullName ASC) AS Rank,
            fm.RiderID,
            fm.FullName,
            COUNT(*) AS Wins
        FROM #FilteredMains fm
        WHERE fm.Result = 1
        GROUP BY fm.RiderID, fm.FullName
        ORDER BY Wins DESC, fm.FullName ASC;

        SELECT
            ROW_NUMBER() OVER (ORDER BY COUNT(*) DESC, fm.FullName ASC) AS Rank,
            fm.RiderID,
            fm.FullName,
            COUNT(*) AS Podiums
        FROM #FilteredMains fm
        WHERE fm.Result <= 3
        GROUP BY fm.RiderID, fm.FullName
        ORDER BY Podiums DESC, fm.FullName ASC;

        SELECT
            ROW_NUMBER() OVER (ORDER BY COUNT(*) DESC, fm.FullName ASC) AS Rank,
            fm.RiderID,
            fm.FullName,
            COUNT(*) AS Starts
        FROM #FilteredMains fm
        GROUP BY fm.RiderID, fm.FullName
        ORDER BY Starts DESC, fm.FullName ASC;
        """
    elif sport_id == 2:
        query = """
        DECLARE @TrackID INT = ?;
        DECLARE @ClassID INT = ?;

        IF OBJECT_ID('tempdb..#FilteredMains') IS NOT NULL
            DROP TABLE #FilteredMains;

        SELECT
            mo.RiderID,
            mo.FullName,
            mo.Result,
            mo.RaceID,
            mo.Brand
        INTO #FilteredMains
        FROM MX_OVERALLS mo
        JOIN Race_Table rt
            ON rt.RaceID = mo.RaceID
        WHERE rt.TrackID = @TrackID
          AND rt.SportID = 2
          AND mo.ClassID = @ClassID;

        SELECT
            rt.TrackName,
            rt.RaceID,
            rt.RaceDate,
            fm.FullName AS Winner,
            fm.Brand
        FROM #FilteredMains fm
        JOIN Race_Table rt
            ON rt.RaceID = fm.RaceID
        WHERE fm.Result = 1
        ORDER BY rt.RaceDate DESC, rt.RaceID DESC;

        SELECT
            ROW_NUMBER() OVER (ORDER BY COUNT(*) DESC, fm.FullName ASC) AS Rank,
            fm.RiderID,
            fm.FullName,
            COUNT(*) AS Wins
        FROM #FilteredMains fm
        WHERE fm.Result = 1
        GROUP BY fm.RiderID, fm.FullName
        ORDER BY Wins DESC, fm.FullName ASC;

        SELECT
            ROW_NUMBER() OVER (ORDER BY COUNT(*) DESC, fm.FullName ASC) AS Rank,
            fm.RiderID,
            fm.FullName,
            COUNT(*) AS Podiums
        FROM #FilteredMains fm
        WHERE fm.Result <= 3
        GROUP BY fm.RiderID, fm.FullName
        ORDER BY Podiums DESC, fm.FullName ASC;

        SELECT
            ROW_NUMBER() OVER (ORDER BY COUNT(*) DESC, fm.FullName ASC) AS Rank,
            fm.RiderID,
            fm.FullName,
            COUNT(*) AS Starts
        FROM #FilteredMains fm
        GROUP BY fm.RiderID, fm.FullName
        ORDER BY Starts DESC, fm.FullName ASC;
        """
    else:
        raise HTTPException(status_code=400, detail="Invalid sport_id")

    try:
        with pyodbc.connect(CONN_STR) as conn:
            cursor = conn.cursor()
            cursor.execute(query, track_id, class_id)

            def fetch_with_columns(cur):
    # Move forward until we hit a real result set
                while cur.description is None:
                    if not cur.nextset():
                        return []

                columns = [col[0] for col in cur.description]
                rows = cur.fetchall()
                return [dict(zip(columns, row)) for row in rows]

            race_winners = fetch_with_columns(cursor)
            cursor.nextset()

            wins = fetch_with_columns(cursor)
            cursor.nextset()

            podiums = fetch_with_columns(cursor)
            cursor.nextset()

            starts = fetch_with_columns(cursor)

            return {
                "race_winners": race_winners,
                "wins": wins,
                "podiums": podiums,
                "starts": starts
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/countries")
def get_countries():
    with engine.connect() as conn:
        result = conn.execute(text("""
            WITH NormalizedCountries AS (
                SELECT
                    CASE
                        WHEN Country IN ('United Kingdom', 'England', 'Wales', 'Scotland')
                            THEN 'United Kingdom'
                        ELSE Country
                    END AS Country
                FROM Rider_List
                WHERE Country IS NOT NULL
            )
            SELECT Country
            FROM NormalizedCountries
            GROUP BY Country
            ORDER BY
                CASE WHEN Country = 'United States' THEN 0 ELSE 1 END,
                Country
        """))

        return [row.Country for row in result]

@app.get("/api/riders/index")
def get_riders_index():
    with engine.connect() as conn:
        riders = conn.execute(text("""
            SELECT RiderID, FullName, Last, First, Country, ImageURL
            FROM Rider_List
            WHERE FullName IS NOT NULL
            ORDER BY Last, First, FullName
        """)).fetchall()

        count = conn.execute(text("""
            SELECT COUNT(*) AS RiderCount
            FROM Rider_List
            WHERE FullName IS NOT NULL
        """)).scalar()

        return {
            "riderCount": count,
            "riders": [dict(row._mapping) for row in riders]
        }

@app.get("/api/riders/featured")
def get_featured_riders():
    today_utc = datetime.now(timezone.utc).date()

    if FEATURED_RIDERS_CACHE["date"] != today_utc:
        FEATURED_RIDERS_CACHE["data"] = compute_featured_riders()
        FEATURED_RIDERS_CACHE["date"] = today_utc

    return FEATURED_RIDERS_CACHE["data"]

@app.get("/api/riders/rider-of-the-day")
def get_rider_of_the_day():
    today_utc = datetime.now(timezone.utc).date()

    if RIDER_OF_THE_DAY_CACHE["date"] != today_utc:
        RIDER_OF_THE_DAY_CACHE["data"] = compute_rider_of_the_day()
        RIDER_OF_THE_DAY_CACHE["date"] = today_utc

    return RIDER_OF_THE_DAY_CACHE["data"]

@app.get("/api/image-proxy")
def image_proxy(url: str):
    parsed = urlparse(url)

    if parsed.scheme not in {"http", "https"}:
        raise HTTPException(status_code=400, detail="Invalid image URL")

    try:
        request = Request(
            url,
            headers={"User-Agent": "SMXmuse/1.0"}
        )

        with urlopen(request, timeout=10) as remote:
            content_type = remote.headers.get_content_type() or "image/jpeg"
            body = remote.read()

        return Response(content=body, media_type=content_type)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Failed to fetch image: {exc}")

@app.get("/countries/{country}")
def get_country(country: str):
    with engine.connect() as conn:
        country_group = ['United Kingdom', 'England', 'Wales', 'Scotland']
        normalized_country = "United Kingdom" if country in country_group else country

        if normalized_country == "United Kingdom":
            riders_query = text("""
                SELECT RiderID, FullName, Last, First, ImageURL
                FROM Rider_List
                WHERE LTRIM(RTRIM(LOWER(Country))) IN (
                    'united kingdom',
                    'england',
                    'wales',
                    'scotland'
                )
                ORDER BY Last, First
            """)
            count_query = text("""
                SELECT COUNT(*) AS RiderCount
                FROM Rider_List
                WHERE LTRIM(RTRIM(LOWER(Country))) IN (
                    'united kingdom',
                    'england',
                    'wales',
                    'scotland'
                )
            """)
            riders = conn.execute(riders_query).fetchall()
            count = conn.execute(count_query).scalar()
        else:
            riders = conn.execute(text("""
                SELECT RiderID, FullName, Last, First, ImageURL
                FROM Rider_List
                WHERE LTRIM(RTRIM(LOWER(Country))) = LTRIM(RTRIM(LOWER(:country)))
                ORDER BY Last, First
            """), {"country": country}).fetchall()

            count = conn.execute(text("""
                SELECT COUNT(*) AS RiderCount
                FROM Rider_List
                WHERE LTRIM(RTRIM(LOWER(Country))) = LTRIM(RTRIM(LOWER(:country)))
            """), {"country": country}).scalar()

        return {
            "country": normalized_country,
            "riderCount": count,
            "riders": [dict(row._mapping) for row in riders]
        }

@app.get("/api/mx/season/overall")
def get_mx_season_overall(year: int, classid: int):

    query = """
    WITH Base AS (
    SELECT
        mo.RiderID,
        mo.FullName,
        mo.Brand,
        mo.Result,
        mo.Holeshot,
        mo.M1_Start,
        mo.M2_Start,

        ps.Points AS StandingPoints

    FROM MX_OVERALLS mo
    JOIN Race_Table rt
        ON rt.RaceID = mo.RaceID

    LEFT JOIN MX_POINTS_STANDINGS ps
        ON ps.RiderID = mo.RiderID
       AND ps.Year = rt.Year
       AND ps.ClassID = mo.ClassID

    WHERE rt.Year = :year
      AND mo.ClassID = :classid
),

StartsCalc AS (
    SELECT *,
        CASE 
            WHEN M1_Start IS NOT NULL AND M2_Start IS NOT NULL 
                THEN (M1_Start + M2_Start) / 2.0
            WHEN M1_Start IS NOT NULL THEN M1_Start
            WHEN M2_Start IS NOT NULL THEN M2_Start
        END AS AvgStartRace
    FROM Base
)

SELECT
    RiderID,
    FullName,
    MAX(Brand) AS Brand,

    COUNT(*) AS Starts,

    SUM(CASE WHEN Result = 1 THEN 1 ELSE 0 END) AS Wins,
    SUM(CASE WHEN Result <= 3 THEN 1 ELSE 0 END) AS Podiums,
    SUM(CASE WHEN Result <= 5 THEN 1 ELSE 0 END) AS Top5,
    SUM(CASE WHEN Result <= 10 THEN 1 ELSE 0 END) AS Top10,

    MIN(Result) AS BestOverall,
    CAST(AVG(CAST(Result AS FLOAT)) AS DECIMAL(10,2)) AS AvgOverall,

    SUM(Holeshot) AS Holeshots,
    CAST(AVG(AvgStartRace) AS DECIMAL(10,2)) AS AvgStart,

    -- 🔥 UPDATED
    MAX(StandingPoints) AS Points

FROM StartsCalc
GROUP BY RiderID, FullName
ORDER BY Points DESC
    """

    return fetch_all(query, locals())

@app.get("/api/mx/season/moto-qual")
def get_mx_season_moto_qual(year: int, classid: int):

    query = """
    WITH HasQual AS (
    SELECT COUNT(*) AS Cnt
    FROM MX_QUAL mq
    JOIN Race_Table rt
        ON rt.RaceID = mq.RaceID
    WHERE rt.Year = :year
      AND mq.ClassID = :classid
),

RiderBase AS (
    -- Always include OVERALLS riders
    SELECT DISTINCT mo.RiderID, mo.FullName
    FROM MX_OVERALLS mo
    JOIN Race_Table rt
        ON rt.RaceID = mo.RaceID
    WHERE rt.Year = :year
      AND mo.ClassID = :classid

    UNION

    -- ONLY include QUAL riders if qual exists that year
    SELECT DISTINCT mq.RiderID, mq.FullName
    FROM MX_QUAL mq
    JOIN Race_Table rt
        ON rt.RaceID = mq.RaceID
    WHERE rt.Year = :year
      AND mq.ClassID = :classid
      AND (SELECT Cnt FROM HasQual) > 0
),

Base AS (
    SELECT
        mo.RiderID,
        mo.FullName,
        mo.Moto1,
        mo.Moto2
    FROM MX_OVERALLS mo
    JOIN Race_Table rt
        ON rt.RaceID = mo.RaceID
    WHERE rt.Year = :year
      AND mo.ClassID = :classid
),

MotoStats AS (
    SELECT
        RiderID,
        FullName,

        SUM(CASE WHEN Moto = 1 THEN 1 ELSE 0 END) AS MotoWins,
        SUM(CASE WHEN Moto <= 3 THEN 1 ELSE 0 END) AS MotoPodiums,
        MIN(Moto) AS BestMoto,
        CAST(AVG(CAST(Moto AS FLOAT)) AS DECIMAL(10,2)) AS AvgMoto

    FROM (
        SELECT RiderID, FullName, Moto1 AS Moto FROM Base WHERE Moto1 IS NOT NULL
        UNION ALL
        SELECT RiderID, FullName, Moto2 AS Moto FROM Base WHERE Moto2 IS NOT NULL
    ) x

    GROUP BY RiderID, FullName
),

QualStats AS (
    SELECT
        mq.RiderID,
        COUNT(*) AS QualStarts,
        SUM(CASE WHEN mq.Result = 1 THEN 1 ELSE 0 END) AS Poles,
        CAST(AVG(CAST(mq.Result AS FLOAT)) AS DECIMAL(10,2)) AS AvgQual
    FROM MX_QUAL mq
    JOIN Race_Table rt
        ON rt.RaceID = mq.RaceID
    WHERE rt.Year = :year
      AND mq.ClassID = :classid
    GROUP BY mq.RiderID
),

ConsiStats AS (
    SELECT
        mc.RiderID,
        SUM(CASE WHEN mc.Result = 1 THEN 1 ELSE 0 END) AS ConsiWins
    FROM MX_CONSIS mc
    JOIN Race_Table rt
        ON rt.RaceID = mc.RaceID
    WHERE rt.Year = :year
      AND mc.ClassID = :classid
    GROUP BY mc.RiderID
)

SELECT
    r.RiderID,
    r.FullName,

    ISNULL(m.MotoWins, 0) AS MotoWins,
    ISNULL(m.MotoPodiums, 0) AS MotoPodiums,
    m.BestMoto,
    m.AvgMoto,

    ISNULL(q.Poles, 0) AS Poles,
    ISNULL(q.QualStarts, 0) AS QualStarts,
    ISNULL(q.AvgQual, 0) AS AvgQual,

    ISNULL(c.ConsiWins, 0) AS ConsiWins

FROM RiderBase r
LEFT JOIN MotoStats m ON r.RiderID = m.RiderID
LEFT JOIN QualStats q ON r.RiderID = q.RiderID
LEFT JOIN ConsiStats c ON r.RiderID = c.RiderID

ORDER BY
    CASE WHEN m.AvgMoto IS NULL THEN 1 ELSE 0 END,
    m.AvgMoto ASC,
    q.AvgQual DESC
    """

    return fetch_all(query, locals())

@app.get("/api/mx/season/laps-led")
def get_mx_season_laps_led(
    year: int,
    classid: int
):
    query = """
    WITH RiderLaps AS (
        SELECT
            rt.Year,
            mo.ClassID,
            mo.RiderID,
            mo.FullName,
            MAX(mo.Brand) AS Brand,
            SUM(COALESCE(mo.LapsLed, 0)) AS LapsLed
        FROM MX_OVERALLS mo
        JOIN Race_Table rt
            ON rt.RaceID = mo.RaceID
        WHERE rt.Year = :year
          AND mo.ClassID = :classid
        GROUP BY
            rt.Year,
            mo.ClassID,
            mo.RiderID,
            mo.FullName
    ),

    TotalLaps AS (
        SELECT SUM(LapsLed) AS Total FROM RiderLaps
    )

    SELECT
        r.Year,
        2 AS SportID,
        r.ClassID,
        r.RiderID,
        r.FullName,
        r.Brand,
        r.LapsLed,
        CASE 
            WHEN t.Total = 0 THEN 0
            ELSE r.LapsLed * 1.0 / t.Total
        END AS PctLapsLed
    FROM RiderLaps r
    CROSS JOIN TotalLaps t
    ORDER BY r.LapsLed DESC
    """

    return fetch_all(query, locals())

@app.get("/api/mx/season/points-progression")
def get_mx_season_points_progression(
    year: int,
    classid: int
):
    query = """
    WITH Base AS (
        SELECT
            rt.Year,
            rt.Round,
            mo.ClassID,
            mo.RiderID,
            mo.FullName,
            mo.Points
        FROM MX_OVERALLS mo
        JOIN Race_Table rt
            ON rt.RaceID = mo.RaceID
        WHERE rt.Year = :year
          AND mo.ClassID = :classid
    ),

    RunningTotals AS (
        SELECT
            Year,
            Round,
            ClassID,
            RiderID,
            FullName,
            SUM(Points) OVER (
                PARTITION BY RiderID
                ORDER BY Round
                ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
            ) AS CumulativePoints
        FROM Base
    )

    SELECT
        Year,
        2 AS SportID,
        ClassID,
        Round,
        RiderID,
        FullName,
        CumulativePoints
    FROM RunningTotals
    ORDER BY Round, CumulativePoints DESC
    """

    return fetch_all(query, locals())

@app.get("/api/search")
def search(q: str):
    like = f"%{q}%"
    starts = f"{q}%"

    riders = engine.execute("""
        SELECT TOP 8 RiderID, FullName, Country
        FROM Rider_List
        WHERE FullName LIKE ?
        ORDER BY
            CASE WHEN FullName LIKE ? THEN 0 ELSE 1 END,
            FullName
    """, (like, starts)).fetchall()

    tracks = engine.execute("""
    SELECT TOP 8
        rt.TrackID,
        rt.TrackName,
        tt.State,
        rt.SportID
    FROM Race_Table rt
    JOIN TrackTable tt 
        ON rt.TrackID = tt.TrackID
    WHERE rt.TrackName LIKE ?
      AND rt.SportID IN (1, 2)   -- 🔥 ADD THIS LINE
    GROUP BY 
        rt.TrackID, 
        rt.TrackName, 
        tt.State, 
        rt.SportID
    ORDER BY
        CASE WHEN rt.TrackName LIKE ? THEN 0 ELSE 1 END,
        rt.TrackName
""", (like, starts)).fetchall()

    return {
        "riders": [dict(r._mapping) for r in riders],
        "tracks": [dict(t._mapping) for t in tracks],
    }

@app.get("/api/race-header")
def get_race_header(raceid: int):
    query = """
    DECLARE @RaceID INT = ?;

    SELECT 
        rt.TrackID AS TrackID,   -- 👈 THIS IS THE FIX
        rt.Round,
        rt.Year,
        rt.TrackName,
        rt.SportID,
        rt.CoastID,
        rt.TripleCrownID,
        maxRounds.MaxRound
    FROM Race_Table rt
    CROSS APPLY (
        SELECT MAX(Round) AS MaxRound
        FROM Race_Table
        WHERE Year = rt.Year
          AND SportID = rt.SportID
    ) maxRounds
    WHERE rt.RaceID = @RaceID
    """

    with engine.connect() as conn:
        row = conn.exec_driver_sql(query, (raceid,)).mappings().first()

    return dict(row)

@app.get("/api/track-classes")
def get_track_classes(track_id: int, sport_id: int):
    query = """
    SELECT DISTINCT ClassID
    FROM Race_Table rt
    JOIN (
        SELECT RaceID, ClassID FROM SX_MAINS
        UNION
        SELECT RaceID, ClassID FROM MX_OVERALLS
    ) x ON x.RaceID = rt.RaceID
    WHERE rt.TrackID = :track_id
      AND rt.SportID = :sport_id
    """

    return fetch_all(query, locals())

@app.get("/api/years")
def get_years(sport_id: int):
    try:
        with pyodbc.connect(CONN_STR) as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT DISTINCT Year
                FROM Race_Table
                WHERE SportID = ?
                ORDER BY Year DESC
            """, sport_id)

            rows = cursor.fetchall()

            return [row.Year for row in rows]

    except Exception as e:
        return {"error": str(e)}

@app.get("/api/races")
def get_races(sport_id: int, year: int):
    with pyodbc.connect(CONN_STR) as conn:
        cursor = conn.cursor()

        cursor.execute("""
    SELECT
        rt.RaceID,
        rt.Round,
        rt.TrackName,
        rt.RaceDate,
        tt.City,
        tt.State
    FROM Race_Table rt
    JOIN TrackTable tt ON rt.TrackID = tt.TrackID
    WHERE rt.SportID = ?
      AND rt.Year = ?
    ORDER BY rt.Round
""", sport_id, year)

        rows = cursor.fetchall()

        return [
    {
        "race_id": row.RaceID,
        "round": row.Round,
        "track_name": row.TrackName,
        "race_date": row.RaceDate.strftime("%Y-%m-%d"),
        "city": row.City,
        "state": row.State
    }
    for row in rows
]

@app.get("/api/season-champions")
def get_season_champions(sport_id: int, year: int):
    with pyodbc.connect(CONN_STR) as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                c.RiderID,
                c.ClassID,
                c.CoastID,
                rl.FullName,
                rl.ImageURL,
                rl.Country
            FROM Champions c
            LEFT JOIN Rider_List rl
                ON rl.RiderID = c.RiderID
            WHERE c.SportID = ?
              AND c.Year = ?
            ORDER BY
                CASE
                    WHEN c.ClassID = 1 THEN 1
                    WHEN c.ClassID = 2 AND c.CoastID = 1 THEN 2
                    WHEN c.ClassID = 2 AND c.CoastID = 2 THEN 3
                    WHEN c.ClassID = 3 THEN 4
                    ELSE 5
                END
        """, sport_id, year)

        rows = cursor.fetchall()

        return [
            {
                "riderid": row.RiderID,
                "classid": row.ClassID,
                "coastid": row.CoastID,
                "fullname": row.FullName,
                "imageurl": row.ImageURL,
                "country": row.Country
            }
            for row in rows
        ]
     
@app.get("/api/race/mx-classes")
def get_mx_classes(raceid: int):
    query = """
        SELECT DISTINCT ClassID
        FROM MX_OVERALLS
        WHERE RaceID = :raceid
        ORDER BY ClassID
    """

    return fetch_all(query, {"raceid": raceid})

@app.get("/rider/{rider_id}/points")
def get_rider_points_standings(rider_id: int):
    try:
        with pyodbc.connect(CONN_STR) as conn:
            cursor = conn.cursor()

            cursor.execute("""
DECLARE @RiderID INT = ?;

-- =========================
-- SX WITH TIES
-- =========================
WITH SX_WithTies AS (
    SELECT
        Year,
        RiderID,
        Points,
        ClassID,
        RiderCoastID,
        CASE 
            WHEN COUNT(*) OVER (
                PARTITION BY Year, ClassID, RiderCoastID, Result
            ) > 1
                THEN 'T-' + CAST(Result AS VARCHAR)
            ELSE CAST(Result AS VARCHAR)
        END AS ResultDisplay
    FROM SX_POINTS_STANDINGS
),

-- =========================
-- MX WITH TIES
-- =========================
MX_WithTies AS (
    SELECT
        Year,
        RiderID,
        Points,
        ClassID,
        CASE 
            WHEN COUNT(*) OVER (
                PARTITION BY Year, ClassID, Result
            ) > 1
                THEN 'T-' + CAST(Result AS VARCHAR)
            ELSE CAST(Result AS VARCHAR)
        END AS ResultDisplay
    FROM MX_POINTS_STANDINGS
),

-- =========================
-- BRAND AGG (FIXED WITH SPORTID)
-- =========================
Brands AS (
    SELECT
        RiderID,
        Year,
        ClassID,
        SportID,
        STRING_AGG(Brand, ', ') AS Brand
    FROM (
        SELECT DISTINCT
            RiderID,
            Year,
            ClassID,
            SportID,
            Brand
        FROM RiderBrandListYear
    ) x
    GROUP BY
        RiderID,
        Year,
        ClassID,
        SportID
)

-- =========================
-- FINAL OUTPUT
-- =========================
SELECT *
FROM (
    SELECT
        s.Year,
        s.ResultDisplay AS Result,
        s.Points,
        CASE 
            WHEN s.ClassID = 1 THEN '450SX'
            WHEN s.ClassID = 2 AND s.RiderCoastID = 1 THEN '250SX W'
            WHEN s.ClassID = 2 AND s.RiderCoastID = 2 THEN '250SX E'
        END AS Class,
        b.Brand,
        1 AS SortOrder
    FROM SX_WithTies s
    LEFT JOIN Brands b
        ON b.RiderID = s.RiderID
       AND b.Year = s.Year
       AND b.ClassID = s.ClassID
       AND b.SportID = 1
    WHERE s.RiderID = @RiderID

    UNION ALL

    SELECT
        m.Year,
        m.ResultDisplay,
        m.Points,
        CASE 
            WHEN m.ClassID = 1 THEN '450MX'
            WHEN m.ClassID = 2 THEN '250MX'
            WHEN m.ClassID = 3 THEN '500MX'
        END,
        b.Brand,
        0 AS SortOrder
    FROM MX_WithTies m
    LEFT JOIN Brands b
        ON b.RiderID = m.RiderID
       AND b.Year = m.Year
       AND b.ClassID = m.ClassID
       AND b.SportID = 2
    WHERE m.RiderID = @RiderID
) x

ORDER BY 
    Year DESC,
    SortOrder,
    Class;
            """, (rider_id,))

            columns = [column[0] for column in cursor.description]

            results = [
                dict(zip(columns, row))
                for row in cursor.fetchall()
            ]

            return results

    except Exception as e:
        return {"error": str(e)}
    
@app.get("/season/current")
def get_current_season():
    try:
        with pyodbc.connect(CONN_STR) as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT TOP 1
                    SportID,
                    Year
                FROM Race_Table
                WHERE RaceDate <= GETDATE()
                ORDER BY RaceDate DESC
            """)

            row = cursor.fetchone()

            if not row:
                return {"error": "No races found"}

            sport = "sx" if row.SportID == 1 else "mx"

            return {
                "sport": sport,
                "year": row.Year,
                "classId": "450"
            }

    except Exception as e:
        return {"error": str(e)}
    
@app.get("/api/available-classes")
def get_available_classes(sport_id: int, year: int):

    if sport_id == 1:
        query = """
            SELECT DISTINCT m.ClassID
            FROM SX_MAINS m
            JOIN Race_Table rt
                ON rt.RaceID = m.RaceID
            WHERE rt.Year = :year
              AND rt.SportID = 1
        """
    else:
        query = """
            SELECT DISTINCT mo.ClassID
            FROM MX_OVERALLS mo
            JOIN Race_Table rt
                ON rt.RaceID = mo.RaceID
            WHERE rt.Year = :year
              AND rt.SportID = 2
        """

    return fetch_all(query, {"year": year})
