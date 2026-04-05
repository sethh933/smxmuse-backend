from typing import Optional

from fastapi import APIRouter, Query
from sqlalchemy import text

from db import engine, fetch_all


router = APIRouter()


@router.get("/compare")
def compare_riders(
    rider1: int,
    rider2: int,
    sport: str,
    classid: Optional[int] = Query(default=None)
):
    with engine.connect() as conn:
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
        heat_rows = conn.execute(heat_query, params).mappings().all() if heat_query is not None else []
        qual_rows = conn.execute(qual_query, params).mappings().all() if qual_query is not None else []

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
            "riders": riders
        }
