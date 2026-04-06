from datetime import datetime, timezone

import pyodbc
from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import text

from db import (
    CONN_STR,
    FEATURED_RIDERS_CACHE,
    RIDER_OF_THE_DAY_CACHE,
    compute_featured_riders,
    compute_rider_of_the_day,
    engine,
    fetch_all,
)
from error_utils import raise_http_error


router = APIRouter()


def _get_rider_identity_and_availability(cursor, rider_id: int):
    cursor.execute(
        """
        SELECT RiderID, FullName, Country, DOB, ImageURL
        FROM Rider_List
        WHERE RiderID = ?
        """,
        rider_id,
    )

    rider = cursor.fetchone()
    if not rider:
        raise HTTPException(status_code=404, detail="Rider not found")

    rider_data = {
        "rider_id": rider.RiderID,
        "full_name": rider.FullName,
        "country": rider.Country,
        "dob": rider.DOB,
        "image_url": rider.ImageURL,
    }

    try:
        cursor.execute(
            """
            SELECT HasSX, HasMX
            FROM RiderProfileAvailabilitySummary
            WHERE RiderID = ?
            """,
            rider_id,
        )
        availability = cursor.fetchone()
        if availability:
            return rider_data, availability.HasSX == 1, availability.HasMX == 1
    except pyodbc.Error:
        pass

    cursor.execute(
        """
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
        """,
        rider_id,
        rider_id,
    )

    availability = cursor.fetchone()
    return rider_data, availability.HasSX == 1, availability.HasMX == 1


def _get_sx_profile_payload_from_summary(cursor, rider_id: int):
    try:
        cursor.execute(
            """
            SELECT
                [Year],
                Class,
                Brand,
                Starts,
                Best,
                AvgMainResult,
                Top10Count,
                Top10Pct,
                Top5Count,
                Top5Pct,
                Podiums,
                PodiumPct,
                Wins,
                WinPct,
                LapsLed,
                AvgStart,
                Holeshots,
                TotalPoints
            FROM RiderProfileSXStatsSummary
            WHERE RiderID = ?
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
                Brand
            """,
            rider_id,
        )
        columns = [col[0] for col in cursor.description]
        stats = [dict(zip(columns, row)) for row in cursor.fetchall()]

        cursor.execute(
            """
            SELECT
                [Year],
                Class,
                Brand,
                QualStarts,
                Poles,
                BestQual,
                AvgQualResult,
                HeatStarts,
                BestHeat,
                HeatWins,
                AvgHeatResult,
                LcqStarts,
                BestLcq,
                LcqTransfers,
                LcqTransferPct,
                LcqWins,
                AvgLcqResult
            FROM RiderProfileSXQualSummary
            WHERE RiderID = ?
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
                END
            """,
            rider_id,
        )
        columns = [col[0] for col in cursor.description]
        qual_stats = [dict(zip(columns, row)) for row in cursor.fetchall()]
    except pyodbc.Error:
        return None

    if not stats and not qual_stats:
        return None

    return {"stats": stats, "qual_stats": qual_stats}


def _get_mx_profile_payload_from_summary(cursor, rider_id: int):
    try:
        cursor.execute(
            """
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
            FROM RiderProfileMXStatsSummary
            WHERE RiderID = ?
            ORDER BY
                CASE WHEN [Year] IS NULL THEN 1 ELSE 0 END,
                [Year],
                CASE
                    WHEN [Year] IS NULL THEN
                        CASE
                            WHEN ClassID = 2 THEN 1
                            WHEN ClassID = 1 THEN 2
                            WHEN ClassID = 3 THEN 3
                            WHEN ClassID = 0 THEN 4
                            ELSE 9
                        END
                    ELSE ClassID
                END,
                Brand
            """,
            rider_id,
        )
        columns = [col[0] for col in cursor.description]
        mx_stats = [dict(zip(columns, row)) for row in cursor.fetchall()]

        cursor.execute(
            """
            SELECT
                [Year],
                Class,
                Brand,
                QualAppearances,
                AvgQual,
                BestQual,
                Poles,
                ConsiAppearances,
                AvgConsi,
                BestConsi,
                ConsiWins
            FROM RiderProfileMXQualSummary
            WHERE RiderID = ?
            ORDER BY
                CASE WHEN [Year] IS NULL THEN 1 ELSE 0 END,
                [Year],
                CASE
                    WHEN [Year] IS NULL THEN
                        CASE
                            WHEN ClassID = 2 THEN 1
                            WHEN ClassID = 1 THEN 2
                            WHEN ClassID = 3 THEN 3
                            WHEN ClassID = 0 THEN 4
                        END
                    ELSE ClassID
                END,
                Brand
            """,
            rider_id,
        )
        columns = [col[0] for col in cursor.description]
        mx_qual_stats = [dict(zip(columns, row)) for row in cursor.fetchall()]
    except pyodbc.Error:
        return None

    if not mx_stats and not mx_qual_stats:
        return None

    return {"mx_stats": mx_stats, "mx_qual_stats": mx_qual_stats}


def _get_sx_profile_payload(cursor, rider_id: int):
    cursor.execute(
        """
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
                        JOIN Race_Table r2 ON r2.RaceID = m.RaceID
                        LEFT JOIN CoastPool cp2 ON cp2.RiderID = m.RiderID AND cp2.[Year] = r2.[Year]
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
                        JOIN Race_Table r3 ON r3.RaceID = t.RaceID
                        LEFT JOIN CoastPool cp3 ON cp3.RiderID = t.RiderID AND cp3.[Year] = r3.[Year]
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
                        SELECT m.[Start] FROM SX_MAINS m WHERE m.RiderID = ? AND m.ClassID = base.ClassID
                        UNION ALL
                        SELECT t.[Start] FROM TC_MAINS t WHERE t.RiderID = ? AND t.ClassID = base.ClassID
                    ) s
                ) AS AvgStart,
                SUM(CASE WHEN Holeshot = 1 THEN 1 ELSE 0 END) AS Holeshots,
                SUM(COALESCE(Points, 0)) AS TotalPoints
            FROM base
            GROUP BY ClassID
            UNION ALL
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
                        SELECT m.[Start] FROM SX_MAINS m WHERE m.RiderID = ?
                        UNION ALL
                        SELECT t.[Start] FROM TC_MAINS t WHERE t.RiderID = ?
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
        """,
        rider_id,
        rider_id,
        rider_id,
        rider_id,
        rider_id,
        rider_id,
        rider_id,
    )
    columns = [col[0] for col in cursor.description]
    stats = [dict(zip(columns, row)) for row in cursor.fetchall()]

    cursor.execute(
        """
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
            JOIN Race_Table r ON r.RaceID = q.RaceID
            LEFT JOIN CoastPool cp ON cp.RiderID = q.RiderID AND cp.[Year] = r.[Year]
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
            JOIN Race_Table r ON r.RaceID = h.RaceID
            LEFT JOIN CoastPool cp ON cp.RiderID = h.RiderID AND cp.[Year] = r.[Year]
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
            JOIN Race_Table r ON r.RaceID = l.RaceID
            LEFT JOIN CoastPool cp ON cp.RiderID = l.RiderID AND cp.[Year] = r.[Year]
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
            SELECT
                NULL AS [Year],
                0 AS ClassID,
                NULL AS Class,
                NULL AS Brand,
                SUM(CASE WHEN SessionType = 'QUAL' THEN 1 ELSE 0 END),
                SUM(CASE WHEN SessionType = 'QUAL' AND Result = 1 THEN 1 ELSE 0 END),
                MIN(CASE WHEN SessionType = 'QUAL' THEN Result END) AS BestQual,
                CAST(ROUND(AVG(CASE WHEN SessionType = 'QUAL' THEN CAST(Result AS DECIMAL(10,2)) END), 2) AS DECIMAL(10,2)),
                SUM(CASE WHEN SessionType = 'HEAT' THEN 1 ELSE 0 END),
                MIN(CASE WHEN SessionType = 'HEAT' THEN Result END) AS BestHeat,
                SUM(CASE WHEN SessionType = 'HEAT' AND Result = 1 THEN 1 ELSE 0 END),
                CAST(ROUND(AVG(CASE WHEN SessionType = 'HEAT' THEN CAST(Result AS DECIMAL(10,2)) END), 2) AS DECIMAL(10,2)),
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
        """,
        rider_id,
        rider_id,
        rider_id,
        rider_id,
    )
    columns = [col[0] for col in cursor.description]
    qual_stats = [dict(zip(columns, row)) for row in cursor.fetchall()]
    return {"stats": stats, "qual_stats": qual_stats}


def _get_mx_profile_payload(cursor, rider_id: int):
    cursor.execute(
        """
WITH
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
            ( SUM(CAST(o.Moto1 AS DECIMAL(10,2))) + SUM(CAST(o.Moto2 AS DECIMAL(10,2))) )
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
    JOIN Race_Table r ON r.RaceID = o.RaceID
    WHERE o.RiderID = ?
      AND o.Sport_ID = 2
    GROUP BY r.[Year], o.ClassID, CASE WHEN o.ClassID = 1 THEN '450' WHEN o.ClassID = 2 THEN '250' WHEN o.ClassID = 3 THEN '500' END, o.Brand
),
brand_union AS (
    SELECT [Year], ClassID, Brand FROM overall_year_brand
),
year_rows AS (
    SELECT
        b.[Year],
        b.ClassID,
        CASE WHEN b.ClassID = 1 THEN '450' WHEN b.ClassID = 2 THEN '250' WHEN b.ClassID = 3 THEN '500' END AS Class,
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
       AND ((o.Brand = b.Brand) OR (o.Brand IS NULL AND b.Brand IS NULL))
),
overall_career_class AS (
    SELECT
        o.ClassID,
        CASE WHEN o.ClassID = 1 THEN '450' WHEN o.ClassID = 2 THEN '250' WHEN o.ClassID = 3 THEN '500' END AS Class,
        COUNT(*) AS Starts,
        MIN(o.Result) AS BestOverall,
        MIN(CASE WHEN o.Moto1 IS NULL THEN o.Moto2 WHEN o.Moto2 IS NULL THEN o.Moto1 WHEN o.Moto1 < o.Moto2 THEN o.Moto1 ELSE o.Moto2 END) AS BestMoto,
        CAST(ROUND(AVG(CAST(o.Result AS DECIMAL(10,2))), 2) AS DECIMAL(10,2)) AS AvgOverallFinish,
        CAST(ROUND(
            ( SUM(CAST(o.Moto1 AS DECIMAL(10,2))) + SUM(CAST(o.Moto2 AS DECIMAL(10,2))) )
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
        SUM(CASE WHEN o.LapsLed IS NOT NULL THEN CAST(o.LapsLed AS INT) ELSE CAST(COALESCE(o.M1_Laps_Led,0) + COALESCE(o.M2_Laps_Led,0) AS INT) END) AS LapsLed,
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
    GROUP BY o.ClassID, CASE WHEN o.ClassID = 1 THEN '450' WHEN o.ClassID = 2 THEN '250' WHEN o.ClassID = 3 THEN '500' END
),
career_class_rows AS (
    SELECT NULL AS [Year], o.ClassID, CASE WHEN ClassID = 1 THEN '450' WHEN ClassID = 2 THEN '250' WHEN ClassID = 3 THEN '500' END AS Class, NULL AS Brand,
        o.Starts, o.BestOverall, o.BestMoto, o.AvgOverallFinish, o.AvgMotoFinish, o.AvgMoto1Finish, o.AvgMoto2Finish,
        o.Top10s, o.Top10Pct, o.Top5s, o.Top5Pct, o.Podiums, o.PodiumPct, o.Wins, o.WinPct, o.LapsLed, o.Holeshots, o.AvgStart, o.TotalPoints
    FROM overall_career_class o
),
overall_career_combined AS (
    SELECT
        COUNT(*) AS Starts,
        MIN(o.Result) AS BestOverall,
        MIN(CASE WHEN o.Moto1 IS NULL THEN o.Moto2 WHEN o.Moto2 IS NULL THEN o.Moto1 WHEN o.Moto1 < o.Moto2 THEN o.Moto1 ELSE o.Moto2 END) AS BestMoto,
        CAST(ROUND(AVG(CAST(o.Result AS DECIMAL(10,2))), 2) AS DECIMAL(10,2)) AS AvgOverallFinish,
        CAST(ROUND(
            ( SUM(CAST(o.Moto1 AS DECIMAL(10,2))) + SUM(CAST(o.Moto2 AS DECIMAL(10,2))) )
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
        SUM(CASE WHEN o.LapsLed IS NOT NULL THEN CAST(o.LapsLed AS INT) ELSE CAST(COALESCE(o.M1_Laps_Led,0) + COALESCE(o.M2_Laps_Led,0) AS INT) END) AS LapsLed,
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
    SELECT NULL AS [Year], 0 AS ClassID, NULL AS Class, NULL AS Brand,
        o.Starts, o.BestOverall, o.BestMoto, o.AvgOverallFinish, o.AvgMotoFinish, o.AvgMoto1Finish, o.AvgMoto2Finish,
        o.Top10s, o.Top10Pct, o.Top5s, o.Top5Pct, o.Podiums, o.PodiumPct, o.Wins, o.WinPct, o.LapsLed, o.Holeshots, o.AvgStart, o.TotalPoints
    FROM overall_career_combined o
),
final_rows AS (
    SELECT * FROM year_rows
    UNION ALL
    SELECT * FROM career_class_rows
    UNION ALL
    SELECT * FROM career_combined_row
)
SELECT [Year], Class, Brand, Starts, BestOverall, BestMoto, AvgOverallFinish, AvgMotoFinish, AvgMoto1Finish, AvgMoto2Finish,
       Top10s, Top10Pct, Top5s, Top5Pct, Podiums, PodiumPct, Wins, WinPct, LapsLed, Holeshots, AvgStart, TotalPoints
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
                WHEN ClassID = 0 THEN 4
                ELSE 9
            END
        ELSE ClassID
    END,
    Brand;
""",
        rider_id,
        rider_id,
        rider_id,
    )
    columns = [col[0] for col in cursor.description]
    mx_stats = [dict(zip(columns, row)) for row in cursor.fetchall()]

    cursor.execute(
        """
WITH QualYearly AS (
    SELECT r.Year, q.ClassID, q.Brand,
           COUNT(DISTINCT q.RaceID) AS QualAppearances,
           CAST(ROUND(AVG(CAST(q.Result AS FLOAT)), 2) AS DECIMAL(10,2)) AS AvgQual,
           MIN(q.Result) AS BestQual,
           SUM(CASE WHEN q.Result = 1 THEN 1 ELSE 0 END) AS Poles
    FROM MX_QUAL q
    JOIN Race_Table r ON r.RaceID = q.RaceID
    WHERE q.RiderID = ?
    GROUP BY r.Year, q.ClassID, q.Brand
),
ConsiYearly AS (
    SELECT r.Year, c.ClassID, c.Brand,
           COUNT(DISTINCT c.RaceID) AS ConsiAppearances,
           CAST(ROUND(AVG(CAST(c.Result AS FLOAT)), 2) AS DECIMAL(10,2)) AS AvgConsi,
           MIN(c.Result) AS BestConsi,
           SUM(CASE WHEN c.Result = 1 THEN 1 ELSE 0 END) AS ConsiWins
    FROM MX_CONSIS c
    JOIN Race_Table r ON r.RaceID = c.RaceID
    WHERE c.RiderID = ?
    GROUP BY r.Year, c.ClassID, c.Brand
),
BrandUnion AS (
    SELECT Year, ClassID, Brand FROM QualYearly
    UNION
    SELECT Year, ClassID, Brand FROM ConsiYearly
),
Yearly AS (
    SELECT
        bu.Year, bu.ClassID, bu.Brand,
        ISNULL(q.QualAppearances, 0) AS QualAppearances, q.AvgQual, q.BestQual, ISNULL(q.Poles, 0) AS Poles,
        ISNULL(c.ConsiAppearances, 0) AS ConsiAppearances, c.AvgConsi, c.BestConsi, ISNULL(c.ConsiWins, 0) AS ConsiWins
    FROM BrandUnion bu
    LEFT JOIN QualYearly q
        ON bu.Year = q.Year AND bu.ClassID = q.ClassID
       AND ((bu.Brand = q.Brand) OR (bu.Brand IS NULL AND q.Brand IS NULL))
    LEFT JOIN ConsiYearly c
        ON bu.Year = c.Year AND bu.ClassID = c.ClassID
       AND ((bu.Brand = c.Brand) OR (bu.Brand IS NULL AND c.Brand IS NULL))
),
Career AS (
    SELECT
        NULL AS Year, ClassID, NULL AS Brand,
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
        NULL AS Year, 0 AS ClassID, NULL AS Brand,
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
""",
        rider_id,
        rider_id,
        rider_id,
        rider_id,
        rider_id,
        rider_id,
    )
    columns = [col[0] for col in cursor.description]
    mx_qual_stats = [dict(zip(columns, row)) for row in cursor.fetchall()]
    return {"mx_stats": mx_stats, "mx_qual_stats": mx_qual_stats}


@router.get("/rider/{rider_id}/profile")
def get_rider_profile(rider_id: int, sport: str = "SX"):
    try:
        with pyodbc.connect(CONN_STR) as conn:
            cursor = conn.cursor()
            rider_data, has_sx, has_mx = _get_rider_identity_and_availability(cursor, rider_id)

            if sport.upper() == "MX":
                payload = _get_mx_profile_payload_from_summary(cursor, rider_id)
                if payload is None and has_mx:
                    payload = _get_mx_profile_payload(cursor, rider_id)
                if payload is None:
                    payload = {"mx_stats": [], "mx_qual_stats": []}
            else:
                payload = _get_sx_profile_payload_from_summary(cursor, rider_id)
                if payload is None and has_sx:
                    payload = _get_sx_profile_payload(cursor, rider_id)
                if payload is None:
                    payload = {"stats": [], "qual_stats": []}

            return {
                "rider": rider_data,
                "hasSX": has_sx,
                "hasMX": has_mx,
                **payload,
            }
    except Exception as e:
        raise_http_error("Failed to load rider profile.", e)


@router.get("/api/riders/search")
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

    rows = fetch_all(
        query,
        {
            "search": f"%{q}%",
            "starts": f"{q}%",
        },
    )

    return [
        {
            "RiderID": row["RiderID"],
            "FullName": row["FullName"],
            "Country": row["Country"],
            "ImageURL": row["ImageURL"],
        }
        for row in rows
    ]


@router.get("/countries")
def get_countries():
    with engine.connect() as conn:
        result = conn.execute(
            text(
                """
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
            """
            )
        )

        return [row.Country for row in result]


@router.get("/api/riders/index")
def get_riders_index():
    with engine.connect() as conn:
        riders = conn.execute(
            text(
                """
            SELECT RiderID, FullName, Last, First, Country, ImageURL
            FROM Rider_List
            WHERE FullName IS NOT NULL
            ORDER BY Last, First, FullName
            """
            )
        ).fetchall()

        count = conn.execute(
            text(
                """
            SELECT COUNT(*) AS RiderCount
            FROM Rider_List
            WHERE FullName IS NOT NULL
            """
            )
        ).scalar()

        return {
            "riderCount": count,
            "riders": [dict(row._mapping) for row in riders],
        }


@router.get("/api/riders/featured")
def get_featured_riders():
    today_utc = datetime.now(timezone.utc).date()

    if FEATURED_RIDERS_CACHE["date"] != today_utc:
        FEATURED_RIDERS_CACHE["data"] = compute_featured_riders()
        FEATURED_RIDERS_CACHE["date"] = today_utc

    return FEATURED_RIDERS_CACHE["data"]


@router.get("/api/riders/rider-of-the-day")
def get_rider_of_the_day():
    today_utc = datetime.now(timezone.utc).date()

    if RIDER_OF_THE_DAY_CACHE["date"] != today_utc:
        RIDER_OF_THE_DAY_CACHE["data"] = compute_rider_of_the_day()
        RIDER_OF_THE_DAY_CACHE["date"] = today_utc

    return RIDER_OF_THE_DAY_CACHE["data"]


@router.get("/countries/{country}")
def get_country(country: str):
    with engine.connect() as conn:
        country_group = ["United Kingdom", "England", "Wales", "Scotland"]
        normalized_country = "United Kingdom" if country in country_group else country

        if normalized_country == "United Kingdom":
            riders_query = text(
                """
                SELECT RiderID, FullName, Last, First, ImageURL
                FROM Rider_List
                WHERE LTRIM(RTRIM(LOWER(Country))) IN (
                    'united kingdom',
                    'england',
                    'wales',
                    'scotland'
                )
                ORDER BY Last, First
                """
            )
            count_query = text(
                """
                SELECT COUNT(*) AS RiderCount
                FROM Rider_List
                WHERE LTRIM(RTRIM(LOWER(Country))) IN (
                    'united kingdom',
                    'england',
                    'wales',
                    'scotland'
                )
                """
            )
            riders = conn.execute(riders_query).fetchall()
            count = conn.execute(count_query).scalar()
        else:
            riders = conn.execute(
                text(
                    """
                SELECT RiderID, FullName, Last, First, ImageURL
                FROM Rider_List
                WHERE LTRIM(RTRIM(LOWER(Country))) = LTRIM(RTRIM(LOWER(:country)))
                ORDER BY Last, First
                """
                ),
                {"country": country},
            ).fetchall()

            count = conn.execute(
                text(
                    """
                SELECT COUNT(*) AS RiderCount
                FROM Rider_List
                WHERE LTRIM(RTRIM(LOWER(Country))) = LTRIM(RTRIM(LOWER(:country)))
                """
                ),
                {"country": country},
            ).scalar()

        return {
            "country": normalized_country,
            "riderCount": count,
            "riders": [dict(row._mapping) for row in riders],
        }


@router.get("/rider/{rider_id}/points")
def get_rider_points_standings(rider_id: int):
    try:
        with pyodbc.connect(CONN_STR) as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
DECLARE @RiderID INT = ?;

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
                """,
                (rider_id,),
            )

            columns = [column[0] for column in cursor.description]
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]
            return results

    except Exception as e:
        raise_http_error("Failed to load rider points standings.", e)


@router.get("/rider/{rider_id}/race-results")
def get_rider_race_results(rider_id: int):
    try:
        with pyodbc.connect(CONN_STR) as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT FullName, Country, ImageURL
                FROM Rider_List
                WHERE RiderID = ?
                """,
                rider_id,
            )

            rider = cursor.fetchone()

            rider_data = {
                "full_name": rider.FullName,
                "country": rider.Country,
                "image_url": rider.ImageURL,
            }

            cursor.execute(
                """
DECLARE @RiderID INT = ?;

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
    SELECT RaceID, ClassID, MIN(Result) AS HeatResult, MAX(Brand) AS Brand
    FROM SX_HEATS
    WHERE RiderID = @RiderID
    GROUP BY RaceID, ClassID
),
LCQResults AS (
    SELECT RaceID, MIN(Result) AS LCQResult, ClassID, MAX(Brand) AS Brand
    FROM SX_LCQS
    WHERE RiderID = @RiderID
    GROUP BY RaceID, ClassID
),
QualResults AS (
    SELECT RaceID, ClassID, MIN(Result) AS QualResult, MAX(Brand) AS Brand
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
SELECT *
FROM (
    SELECT * FROM SXResults
    UNION ALL
    SELECT * FROM MXResults
) x
ORDER BY RaceDate DESC
                """,
                rider_id,
            )

            columns = [column[0] for column in cursor.description]
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]

            return {"rider": rider_data, "results": results}

    except Exception as e:
        raise_http_error("Failed to load rider race results.", e)
