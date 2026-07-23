import pyodbc
from fastapi import APIRouter, HTTPException

from db import CONN_STR, fetch_all
from error_utils import raise_http_error


router = APIRouter()


def _get_sx_season_main_stats_from_summary(year: int, classid: int, ridercoastid: int = None):
    query = """
        WITH CoastPoolResolved AS (
            SELECT
                RiderID,
                [Year],
                MIN(RiderCoastID) AS RiderCoastID
            FROM CoastPool
            GROUP BY RiderID, [Year]
        ),
        SeasonStartAgg AS (
            SELECT
                starts_union.[Year],
                starts_union.ClassID,
                starts_union.RiderID,
                starts_union.RiderCoastID,
                CAST(ROUND(AVG(CAST(starts_union.[Start] AS DECIMAL(10,2))), 2) AS DECIMAL(10,2)) AS AvgStartPosition
            FROM (
                SELECT
                    rt.[Year],
                    sm.ClassID,
                    sm.RiderID,
                    COALESCE(sm.RiderCoastID, cp.RiderCoastID) AS RiderCoastID,
                    sm.[Start]
                FROM SX_MAINS sm
                JOIN Race_Table rt
                    ON rt.RaceID = sm.RaceID
                LEFT JOIN CoastPoolResolved cp
                    ON cp.RiderID = sm.RiderID
                   AND cp.[Year] = rt.[Year]
                WHERE rt.[Year] = :year
                  AND rt.SportID = 1
                  AND sm.ClassID = :classid
                  AND sm.[Start] IS NOT NULL

                UNION ALL

                SELECT
                    rt.[Year],
                    tc.ClassID,
                    tc.RiderID,
                    COALESCE(tc.RiderCoastID, cp.RiderCoastID) AS RiderCoastID,
                    tc.[Start]
                FROM TC_MAINS tc
                JOIN Race_Table rt
                    ON rt.RaceID = tc.RaceID
                LEFT JOIN CoastPoolResolved cp
                    ON cp.RiderID = tc.RiderID
                   AND cp.[Year] = rt.[Year]
                WHERE rt.[Year] = :year
                  AND rt.SportID = 1
                  AND tc.ClassID = :classid
                  AND tc.[Start] IS NOT NULL
            ) starts_union
            GROUP BY
                starts_union.[Year],
                starts_union.ClassID,
                starts_union.RiderID,
                starts_union.RiderCoastID
        ),
        HoleshotAgg AS (
            SELECT
                rt.[Year],
                sm.ClassID,
                sm.RiderID,
                COALESCE(sm.RiderCoastID, cp.RiderCoastID) AS RiderCoastID,
                SUM(COALESCE(sm.Holeshot, 0)) AS Holeshots
            FROM SX_MAINS sm
            JOIN Race_Table rt
                ON rt.RaceID = sm.RaceID
            LEFT JOIN CoastPoolResolved cp
                ON cp.RiderID = sm.RiderID
               AND cp.[Year] = rt.[Year]
            WHERE rt.[Year] = :year
              AND rt.SportID = 1
              AND sm.ClassID = :classid
            GROUP BY
                rt.[Year],
                sm.ClassID,
                sm.RiderID,
                COALESCE(sm.RiderCoastID, cp.RiderCoastID)
        )
        SELECT
            s.[Year],
            s.SportID,
            s.ClassID,
            s.RiderID,
            s.FullName,
            s.DisplayFullName,
            s.RiderCoastID,
            s.Points,
            s.Wins,
            s.Podiums,
            s.Top5s,
            s.Top10s,
            s.BestFinish,
            s.AvgFinish,
            s.MainsMade,
            COALESCE(ha.Holeshots, s.Holeshots) AS Holeshots,
            COALESCE(ssa.AvgStartPosition, s.AvgStartPosition) AS AvgStartPosition,
            s.Brand
        FROM dbo.SeasonSXMainStatsSummary s
        LEFT JOIN SeasonStartAgg ssa
            ON ssa.[Year] = s.[Year]
           AND ssa.ClassID = s.ClassID
           AND ssa.RiderID = s.RiderID
           AND (
                (ssa.RiderCoastID = s.RiderCoastID)
                OR (ssa.RiderCoastID IS NULL AND s.RiderCoastID IS NULL)
           )
        LEFT JOIN HoleshotAgg ha
            ON ha.[Year] = s.[Year]
           AND ha.ClassID = s.ClassID
           AND ha.RiderID = s.RiderID
           AND (
                (ha.RiderCoastID = s.RiderCoastID)
                OR (ha.RiderCoastID IS NULL AND s.RiderCoastID IS NULL)
           )
        WHERE s.[Year] = :year
          AND s.SportID = 1
          AND s.ClassID = :classid
    """

    if ridercoastid is not None:
        query += " AND s.RiderCoastID = :ridercoastid"

    query += " ORDER BY Wins DESC, AvgFinish ASC"

    return fetch_all(query, locals())


def _get_sx_season_start_stats_from_summary(year: int, classid: int, ridercoastid: int = None):
    query = """
        SELECT
            [Year],
            SportID,
            ClassID,
            RiderID,
            FullName,
            DisplayFullName,
            RiderCoastID,
            QualStarts,
            Poles,
            BestQual,
            AvgQualFinish,
            HeatStarts,
            HeatWins,
            BestHeat,
            LCQStarts,
            LCQWins,
            BestLCQ
        FROM dbo.SeasonSXStartStatsSummary
        WHERE [Year] = :year
          AND SportID = 1
          AND ClassID = :classid
    """

    if ridercoastid is not None:
        query += " AND RiderCoastID = :ridercoastid"

    return fetch_all(query, locals())


def _get_mx_season_overall_from_summary(year: int, classid: int):
    query = """
        SELECT
            RiderID,
            FullName,
            Brand,
            Starts,
            Wins,
            Podiums,
            Top5,
            Top10,
            BestOverall,
            AvgOverall,
            Holeshots,
            AvgStart,
            Points
        FROM dbo.SeasonMXOverallSummary
        WHERE [Year] = :year
          AND ClassID = :classid
        ORDER BY Points DESC
    """

    return fetch_all(query, locals())


def _get_mx_season_moto_qual_from_summary(year: int, classid: int):
    query = """
        SELECT
            RiderID,
            FullName,
            MotoWins,
            MotoPodiums,
            BestMoto,
            AvgMoto,
            Poles,
            QualStarts,
            AvgQual,
            ConsiWins
        FROM dbo.SeasonMXMotoQualSummary
        WHERE [Year] = :year
          AND ClassID = :classid
        ORDER BY
            CASE WHEN AvgMoto IS NULL THEN 1 ELSE 0 END,
            AvgMoto ASC,
            AvgQual DESC
    """

    return fetch_all(query, locals())


def _get_wmx_season_overall_from_summary(year: int):
    return fetch_all(
        """
        SELECT RiderID, FullName, Brand, Starts, Wins, Podiums, Top5, Top10,
               BestOverall, AvgOverall, Holeshots, AvgStart, Points
        FROM dbo.SeasonWMXOverallSummary
        WHERE [Year] = :year AND SportID = 4
        ORDER BY Points DESC, Wins DESC, AvgOverall
        """,
        {"year": year},
    )


def _get_wmx_season_moto_qual_from_summary(year: int):
    return fetch_all(
        """
        SELECT RiderID, FullName, MotoWins, MotoPodiums, BestMoto, AvgMoto,
               Poles, QualStarts, AvgQual, ConsiWins
        FROM dbo.SeasonWMXMotoQualSummary
        WHERE [Year] = :year AND SportID = 4
        ORDER BY CASE WHEN AvgMoto IS NULL THEN 1 ELSE 0 END, AvgMoto, AvgQual
        """,
        {"year": year},
    )


def _add_legacy_mx_qual_starts(results, year: int, classid: int):
    """Add unique 2004-2008 qualifying race appearances to season rows."""
    if not 2004 <= year <= 2008:
        return results

    query = """
        WITH QualAppearances AS (
            SELECT mq.RiderID, mq.FullName, mq.RaceID
            FROM MX_QUAL mq
            JOIN Race_Table rt ON rt.RaceID = mq.RaceID
            WHERE rt.[Year] = :year AND mq.ClassID = :classid

            UNION
            SELECT q.RiderID, q.FullName, q.RaceID
            FROM MX_QUAL_RACES q
            JOIN Race_Table rt ON rt.RaceID = q.RaceID
            WHERE rt.[Year] = :year AND q.ClassID = :classid

            UNION
            SELECT q.RiderID, q.FullName, q.RaceID
            FROM MX_QUAL_OLD_FORMAT q
            JOIN Race_Table rt ON rt.RaceID = q.RaceID
            WHERE rt.[Year] = :year AND q.ClassID = :classid

            UNION
            SELECT c.RiderID, c.FullName, c.RaceID
            FROM MX_CONSIS_OLD_FORMAT c
            JOIN Race_Table rt ON rt.RaceID = c.RaceID
            WHERE rt.[Year] = :year AND c.ClassID = :classid
        )
        SELECT RiderID, MAX(FullName) AS FullName,
               COUNT(DISTINCT RaceID) AS QualStarts
        FROM QualAppearances
        GROUP BY RiderID
    """
    appearances = fetch_all(query, {"year": year, "classid": classid})
    appearances_by_rider = {row["RiderID"]: row for row in appearances}
    merged = []

    for row in results:
        updated = dict(row)
        appearance = appearances_by_rider.pop(row["RiderID"], None)
        if appearance:
            updated["QualStarts"] = appearance["QualStarts"]
        merged.append(updated)

    for appearance in appearances_by_rider.values():
        merged.append({
            "RiderID": appearance["RiderID"],
            "FullName": appearance["FullName"],
            "MotoWins": 0,
            "MotoPodiums": 0,
            "BestMoto": None,
            "AvgMoto": None,
            "Poles": 0,
            "QualStarts": appearance["QualStarts"],
            "AvgQual": None,
            "ConsiWins": 0,
        })

    return merged


def _get_smx_season_overall_from_summary(year: int, classid: int):
    query = """
        SELECT
            RiderID,
            FullName,
            Brand,
            Starts,
            Wins,
            Podiums,
            Top5,
            Top10,
            BestOverall,
            AvgOverall,
            Holeshots,
            AvgStart,
            Points
        FROM dbo.SeasonSMXOverallSummary
        WHERE [Year] = :year
          AND ClassID = :classid
        ORDER BY Points DESC, Wins DESC, AvgOverall ASC
    """

    return fetch_all(query, locals())


def _get_smx_season_moto_qual_from_summary(year: int, classid: int):
    query = """
        SELECT
            RiderID,
            FullName,
            MotoWins,
            MotoPodiums,
            BestMoto,
            AvgMoto,
            Poles,
            QualStarts,
            AvgQual,
            ConsiWins
        FROM dbo.SeasonSMXMotoQualSummary
        WHERE [Year] = :year
          AND ClassID = :classid
        ORDER BY
            CASE WHEN AvgMoto IS NULL THEN 1 ELSE 0 END,
            AvgMoto ASC,
            AvgQual DESC
    """

    return fetch_all(query, locals())


@router.get("/api/season/main-stats")
def get_season_main_stats(
    year: int,
    sportid: int,
    classid: int,
    ridercoastid: int = None
):
    if sportid == 1 and not (classid == 2 and ridercoastid is not None):
        summary_results = _get_sx_season_main_stats_from_summary(year, classid, ridercoastid)
        if summary_results:
            return summary_results

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
                        PARTITION BY
                            msr.RiderID,
                            CASE
                                WHEN :classid = 2 THEN COALESCE(msr.RiderCoastID, -1)
                                ELSE -1
                            END
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
        SeasonStartAgg AS (
            SELECT
                starts_union.[Year],
                starts_union.ClassID,
                starts_union.RiderID,
                starts_union.RiderCoastID,
                CAST(ROUND(AVG(CAST(starts_union.[Start] AS DECIMAL(10,2))), 2) AS DECIMAL(10,2)) AS AvgStartPosition
            FROM (
                SELECT
                    rt.[Year],
                    sm.ClassID,
                    sm.RiderID,
                    COALESCE(sm.RiderCoastID, cp.RiderCoastID) AS RiderCoastID,
                    sm.[Start]
                FROM SX_MAINS sm
                JOIN Race_Table rt
                    ON rt.RaceID = sm.RaceID
                LEFT JOIN CoastPoolResolved cp
                    ON cp.RiderID = sm.RiderID
                   AND cp.[Year] = rt.[Year]
                WHERE rt.[Year] = :year
                  AND rt.SportID = :sportid
                  AND sm.ClassID = :classid
                  AND sm.[Start] IS NOT NULL
                  AND (:ridercoastid IS NULL OR COALESCE(sm.RiderCoastID, cp.RiderCoastID) = :ridercoastid)

                UNION ALL

                SELECT
                    rt.[Year],
                    tc.ClassID,
                    tc.RiderID,
                    COALESCE(tc.RiderCoastID, cp.RiderCoastID) AS RiderCoastID,
                    tc.[Start]
                FROM TC_MAINS tc
                JOIN Race_Table rt
                    ON rt.RaceID = tc.RaceID
                LEFT JOIN CoastPoolResolved cp
                    ON cp.RiderID = tc.RiderID
                   AND cp.[Year] = rt.[Year]
                WHERE rt.[Year] = :year
                  AND rt.SportID = :sportid
                  AND tc.ClassID = :classid
                  AND tc.[Start] IS NOT NULL
                  AND (:ridercoastid IS NULL OR COALESCE(tc.RiderCoastID, cp.RiderCoastID) = :ridercoastid)
            ) starts_union
            GROUP BY
                starts_union.[Year],
                starts_union.ClassID,
                starts_union.RiderID,
                starts_union.RiderCoastID
        ),
        HoleshotAgg AS (
            SELECT
                rt.[Year],
                sm.ClassID,
                sm.RiderID,
                COALESCE(sm.RiderCoastID, cp.RiderCoastID) AS RiderCoastID,
                SUM(COALESCE(sm.Holeshot, 0)) AS Holeshots
            FROM SX_MAINS sm
            JOIN Race_Table rt
                ON rt.RaceID = sm.RaceID
            LEFT JOIN CoastPoolResolved cp
                ON cp.RiderID = sm.RiderID
               AND cp.[Year] = rt.[Year]
            WHERE rt.[Year] = :year
              AND rt.SportID = :sportid
              AND sm.ClassID = :classid
              AND (:ridercoastid IS NULL OR COALESCE(sm.RiderCoastID, cp.RiderCoastID) = :ridercoastid)
            GROUP BY
                rt.[Year],
                sm.ClassID,
                sm.RiderID,
                COALESCE(sm.RiderCoastID, cp.RiderCoastID)
        ),
        MainStartsAgg AS (
            SELECT
                mains_union.[Year],
                mains_union.ClassID,
                mains_union.RiderID,
                mains_union.RiderCoastID,
                COUNT(DISTINCT mains_union.RaceID) AS MainsMade
            FROM (
                SELECT
                    rt.[Year],
                    sm.RaceID,
                    sm.ClassID,
                    sm.RiderID,
                    COALESCE(sm.RiderCoastID, cp.RiderCoastID) AS RiderCoastID,
                    rt.CoastID
                FROM SX_MAINS sm
                JOIN Race_Table rt
                    ON rt.RaceID = sm.RaceID
                LEFT JOIN CoastPoolResolved cp
                    ON cp.RiderID = sm.RiderID
                   AND cp.[Year] = rt.[Year]
                WHERE rt.[Year] = :year
                  AND rt.SportID = :sportid
                  AND sm.ClassID = :classid

                UNION ALL

                SELECT
                    rt.[Year],
                    tc.RaceID,
                    tc.ClassID,
                    tc.RiderID,
                    COALESCE(tc.RiderCoastID, cp.RiderCoastID) AS RiderCoastID,
                    rt.CoastID
                FROM TC_MAINS tc
                JOIN Race_Table rt
                    ON rt.RaceID = tc.RaceID
                LEFT JOIN CoastPoolResolved cp
                    ON cp.RiderID = tc.RiderID
                   AND cp.[Year] = rt.[Year]
                WHERE rt.[Year] = :year
                  AND rt.SportID = :sportid
                  AND tc.ClassID = :classid
            ) mains_union
            WHERE :ridercoastid IS NULL
               OR (
                    :classid = 2
                    AND (
                        mains_union.CoastID = :ridercoastid
                        OR mains_union.CoastID = 3
                    )
               )
               OR (
                    :classid <> 2
                    AND mains_union.RiderCoastID = :ridercoastid
               )
            GROUP BY
                mains_union.[Year],
                mains_union.ClassID,
                mains_union.RiderID,
                mains_union.RiderCoastID
        ),
        MainResultsAgg AS (
            SELECT
                rt.[Year],
                sm.ClassID,
                sm.RiderID,
                COALESCE(sm.RiderCoastID, cp.RiderCoastID) AS RiderCoastID,
                SUM(CASE WHEN sm.Result = 1 THEN 1 ELSE 0 END) AS Wins,
                SUM(CASE WHEN sm.Result <= 3 THEN 1 ELSE 0 END) AS Podiums,
                SUM(CASE WHEN sm.Result <= 5 THEN 1 ELSE 0 END) AS Top5s,
                SUM(CASE WHEN sm.Result <= 10 THEN 1 ELSE 0 END) AS Top10s,
                MIN(sm.Result) AS BestFinish,
                CAST(ROUND(AVG(CAST(sm.Result AS DECIMAL(10,2))), 2) AS DECIMAL(10,2)) AS AvgFinish
            FROM SX_MAINS sm
            JOIN Race_Table rt
                ON rt.RaceID = sm.RaceID
            LEFT JOIN CoastPoolResolved cp
                ON cp.RiderID = sm.RiderID
               AND cp.[Year] = rt.[Year]
            WHERE rt.[Year] = :year
              AND rt.SportID = :sportid
              AND sm.ClassID = :classid
              AND (:ridercoastid IS NULL OR COALESCE(sm.RiderCoastID, cp.RiderCoastID) = :ridercoastid)
            GROUP BY
                rt.[Year],
                sm.ClassID,
                sm.RiderID,
                COALESCE(sm.RiderCoastID, cp.RiderCoastID)
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
            ms.[Year],
            ms.SportID,
            ms.ClassID,
            ms.RiderID,
            ms.FullName,
            COALESCE(rl.FullName, ms.FullName) AS DisplayFullName,
            ms.RiderCoastID,
            ms.Points,
            CASE
                WHEN :sportid = 1 AND :classid = 2 AND :ridercoastid IS NOT NULL
                    THEN COALESCE(mra.Wins, ms.Wins)
                ELSE ms.Wins
            END AS Wins,
            CASE
                WHEN :sportid = 1 AND :classid = 2 AND :ridercoastid IS NOT NULL
                    THEN COALESCE(mra.Podiums, ms.Podiums)
                ELSE ms.Podiums
            END AS Podiums,
            CASE
                WHEN :sportid = 1 AND :classid = 2 AND :ridercoastid IS NOT NULL
                    THEN COALESCE(mra.Top5s, ms.Top5s)
                ELSE ms.Top5s
            END AS Top5s,
            CASE
                WHEN :sportid = 1 AND :classid = 2 AND :ridercoastid IS NOT NULL
                    THEN COALESCE(mra.Top10s, ms.Top10s)
                ELSE ms.Top10s
            END AS Top10s,
            CASE
                WHEN :sportid = 1 AND :classid = 2 AND :ridercoastid IS NOT NULL
                    THEN COALESCE(mra.BestFinish, ms.BestFinish)
                ELSE ms.BestFinish
            END AS BestFinish,
            CASE
                WHEN :sportid = 1 AND :classid = 2 AND :ridercoastid IS NOT NULL
                    THEN COALESCE(mra.AvgFinish, ms.AvgFinish)
                ELSE ms.AvgFinish
            END AS AvgFinish,
            COALESCE(msa.MainsMade, ms.MainsMade) AS MainsMade,
            COALESCE(ha.Holeshots, ms.Holeshots) AS Holeshots,
            COALESCE(ssa.AvgStartPosition, ms.AvgStartPosition) AS AvgStartPosition,
            ba.Brand
        FROM MainStats ms
        LEFT JOIN Rider_List rl
            ON rl.RiderID = ms.RiderID
        LEFT JOIN MainStartsAgg msa
            ON msa.[Year] = ms.[Year]
           AND msa.ClassID = ms.ClassID
           AND msa.RiderID = ms.RiderID
           AND (
                (msa.RiderCoastID = ms.RiderCoastID)
                OR (msa.RiderCoastID IS NULL AND ms.RiderCoastID IS NULL)
           )
        LEFT JOIN MainResultsAgg mra
            ON mra.[Year] = ms.[Year]
           AND mra.ClassID = ms.ClassID
           AND mra.RiderID = ms.RiderID
           AND (
                (mra.RiderCoastID = ms.RiderCoastID)
                OR (mra.RiderCoastID IS NULL AND ms.RiderCoastID IS NULL)
           )
        LEFT JOIN SeasonStartAgg ssa
            ON ssa.[Year] = ms.[Year]
           AND ssa.ClassID = ms.ClassID
           AND ssa.RiderID = ms.RiderID
           AND (
                (ssa.RiderCoastID = ms.RiderCoastID)
                OR (ssa.RiderCoastID IS NULL AND ms.RiderCoastID IS NULL)
           )
        LEFT JOIN HoleshotAgg ha
            ON ha.[Year] = ms.[Year]
           AND ha.ClassID = ms.ClassID
           AND ha.RiderID = ms.RiderID
           AND (
                (ha.RiderCoastID = ms.RiderCoastID)
                OR (ha.RiderCoastID IS NULL AND ms.RiderCoastID IS NULL)
           )
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


@router.get("/api/season/start-stats")
def get_season_start_stats(
    year: int,
    sportid: int,
    classid: int,
    ridercoastid: int = None
):
    if sportid == 1:
        summary_results = _get_sx_season_start_stats_from_summary(year, classid, ridercoastid)
        if summary_results:
            return summary_results

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


@router.get("/api/season/laps-led")
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
        ),
        FilteredLapStats AS (
            SELECT
                ls.Year,
                ls.SportID,
                ls.ClassID,
                ls.RiderID,
                ls.FullName,
                ls.RiderCoastID,
                ls.LapsLed,
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
            WHERE :ridercoastid IS NULL OR ls.RiderCoastID = :ridercoastid
        ),
        TotalLaps AS (
            SELECT SUM(LapsLed) AS Total
            FROM FilteredLapStats
        )
        SELECT
            fls.Year,
            fls.SportID,
            fls.ClassID,
            fls.RiderID,
            fls.FullName,
            fls.RiderCoastID,
            fls.LapsLed,
            CASE
                WHEN COALESCE(t.Total, 0) = 0 THEN 0
                ELSE fls.LapsLed * 1.0 / t.Total
            END AS PctLapsLed,
            fls.Brand
        FROM FilteredLapStats fls
        CROSS JOIN TotalLaps t
    """

    query += " ORDER BY fls.LapsLed DESC"

    return fetch_all(query, locals())


@router.get("/api/season/points-progression")
def get_season_points_progression(
    year: int,
    sportid: int,
    classid: int,
    ridercoastid: int = None
):
    if sportid == 1:
        if classid == 1:
            query = """
                SELECT
                    s.[Year] AS Year,
                    1 AS SportID,
                    1 AS ClassID,
                    s.[Round] AS Round,
                    s.RiderID AS RiderID,
                    s.FullName AS FullName,
                    CAST(NULL AS INT) AS RiderCoastID,
                    s.TotalPoints AS CumulativePoints
                FROM dbo.vw_SX450_RunningStandings s
                WHERE s.[Year] = :year
                  AND s.[Round] <= (
                      SELECT MAX(rt.[Round])
                      FROM Race_Table rt
                      JOIN SX_MAINS sm
                        ON sm.RaceID = rt.RaceID
                      WHERE rt.[Year] = :year
                        AND rt.SportID = 1
                        AND sm.ClassID = 1
                        AND sm.Result IS NOT NULL
                  )
                ORDER BY s.[Round], s.TotalPoints DESC, s.RiderID
            """
            return fetch_all(query, locals())

        if classid == 2:
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
                        rt.[Year] AS Year,
                        rt.[Round] AS Round,
                        sm.RiderID,
                        sm.FullName,
                        COALESCE(sm.RiderCoastID, cp.RiderCoastID) AS RiderCoastID,
                        sm.Points AS Points
                    FROM SX_MAINS sm
                    JOIN Race_Table rt
                        ON rt.RaceID = sm.RaceID
                    LEFT JOIN CoastPoolResolved cp
                        ON cp.RiderID = sm.RiderID
                       AND cp.[Year] = rt.[Year]
                    WHERE rt.[Year] = :year
                      AND rt.SportID = 1
                      AND sm.ClassID = 2
                      AND (
                            :ridercoastid IS NULL
                            OR rt.CoastID = :ridercoastid
                            OR rt.CoastID = 3
                      )
                ),
                EligibleRounds AS (
                    SELECT
                        Year,
                        Round
                    FROM Base
                    GROUP BY
                        Year,
                        Round
                    HAVING SUM(Points) IS NOT NULL
                ),
                RoundPoints AS (
                    SELECT
                        b.Year,
                        b.Round,
                        b.RiderID,
                        b.FullName,
                        b.RiderCoastID,
                        SUM(COALESCE(b.Points, 0)) AS Points
                    FROM Base b
                    JOIN EligibleRounds er
                        ON er.Year = b.Year
                       AND er.Round = b.Round
                    GROUP BY
                        b.Year,
                        b.Round,
                        b.RiderID,
                        b.FullName,
                        b.RiderCoastID
                ),
                RunningTotals AS (
                    SELECT
                        Year,
                        Round,
                        RiderID,
                        FullName,
                        RiderCoastID,
                        SUM(Points) OVER (
                            PARTITION BY RiderID, RiderCoastID
                            ORDER BY Round
                            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                        ) AS CumulativePoints
                    FROM RoundPoints
                )
                SELECT
                    Year,
                    1 AS SportID,
                    2 AS ClassID,
                    Round,
                    RiderID,
                    FullName,
                    RiderCoastID,
                    CumulativePoints
                FROM RunningTotals
                ORDER BY Round, CumulativePoints DESC, RiderID
            """
            return fetch_all(query, locals())

    query = """
        SELECT *
        FROM dbo.vw_SeasonPointsProgression
        WHERE Year = :year
          AND SportID = :sportid
          AND ClassID = :classid
        ORDER BY Round
    """

    return fetch_all(query, locals())


@router.get("/api/mx/season/overall")
def get_mx_season_overall(year: int, classid: int):
    summary_results = _get_mx_season_overall_from_summary(year, classid)
    if summary_results:
        return summary_results

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

    MAX(StandingPoints) AS Points

FROM StartsCalc
GROUP BY RiderID, FullName
ORDER BY Points DESC
    """

    return fetch_all(query, locals())


@router.get("/api/mx/season/moto-qual")
def get_mx_season_moto_qual(year: int, classid: int):
    summary_results = _get_mx_season_moto_qual_from_summary(year, classid)
    if summary_results:
        return _add_legacy_mx_qual_starts(summary_results, year, classid)

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
    SELECT DISTINCT mo.RiderID, mo.FullName
    FROM MX_OVERALLS mo
    JOIN Race_Table rt
        ON rt.RaceID = mo.RaceID
    WHERE rt.Year = :year
      AND mo.ClassID = :classid

    UNION

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


@router.get("/api/mx/season/laps-led")
def get_mx_season_laps_led(year: int, classid: int):
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

    results = fetch_all(query, locals())
    return _add_legacy_mx_qual_starts(results, year, classid)


@router.get("/api/smx/season/overall")
def get_smx_season_overall(year: int, classid: int):
    summary_results = _get_smx_season_overall_from_summary(year, classid)
    if summary_results:
        return summary_results

    query = """
    WITH Base AS (
        SELECT
            so.RiderID,
            so.FullName,
            so.Brand,
            so.Result,
            so.Holeshot,
            so.M1_Start,
            so.M2_Start,
            so.Points
        FROM SMX_OVERALLS so
        JOIN Race_Table rt
            ON rt.RaceID = so.RaceID
        WHERE rt.Year = :year
          AND rt.SportID = 3
          AND so.ClassID = :classid
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
        SUM(COALESCE(Holeshot, 0)) AS Holeshots,
        CAST(AVG(AvgStartRace) AS DECIMAL(10,2)) AS AvgStart,
        SUM(COALESCE(Points, 0)) AS Points
    FROM StartsCalc
    GROUP BY RiderID, FullName
    ORDER BY Points DESC, Wins DESC, AvgOverall ASC
    """

    return fetch_all(query, locals())


@router.get("/api/smx/season/moto-qual")
def get_smx_season_moto_qual(year: int, classid: int):
    summary_results = _get_smx_season_moto_qual_from_summary(year, classid)
    if summary_results:
        return summary_results

    query = """
    WITH HasQual AS (
        SELECT COUNT(*) AS Cnt
        FROM SMX_QUAL sq
        JOIN Race_Table rt
            ON rt.RaceID = sq.RaceID
        WHERE rt.Year = :year
          AND rt.SportID = 3
          AND sq.ClassID = :classid
    ),

    RiderBase AS (
        SELECT DISTINCT so.RiderID, so.FullName
        FROM SMX_OVERALLS so
        JOIN Race_Table rt
            ON rt.RaceID = so.RaceID
        WHERE rt.Year = :year
          AND rt.SportID = 3
          AND so.ClassID = :classid

        UNION

        SELECT DISTINCT sq.RiderID, sq.FullName
        FROM SMX_QUAL sq
        JOIN Race_Table rt
            ON rt.RaceID = sq.RaceID
        WHERE rt.Year = :year
          AND rt.SportID = 3
          AND sq.ClassID = :classid
          AND (SELECT Cnt FROM HasQual) > 0
    ),

    MotoStats AS (
        SELECT
            sm.RiderID,
            MAX(sm.FullName) AS FullName,
            SUM(CASE WHEN sm.Result = 1 THEN 1 ELSE 0 END) AS MotoWins,
            SUM(CASE WHEN sm.Result <= 3 THEN 1 ELSE 0 END) AS MotoPodiums,
            MIN(sm.Result) AS BestMoto,
            CAST(AVG(CAST(sm.Result AS FLOAT)) AS DECIMAL(10,2)) AS AvgMoto
        FROM SMX_MOTOS sm
        JOIN Race_Table rt
            ON rt.RaceID = sm.RaceID
        WHERE rt.Year = :year
          AND rt.SportID = 3
          AND sm.ClassID = :classid
        GROUP BY sm.RiderID
    ),

    QualStats AS (
        SELECT
            sq.RiderID,
            COUNT(*) AS QualStarts,
            SUM(CASE WHEN sq.Result = 1 THEN 1 ELSE 0 END) AS Poles,
            CAST(AVG(CAST(sq.Result AS FLOAT)) AS DECIMAL(10,2)) AS AvgQual
        FROM SMX_QUAL sq
        JOIN Race_Table rt
            ON rt.RaceID = sq.RaceID
        WHERE rt.Year = :year
          AND rt.SportID = 3
          AND sq.ClassID = :classid
        GROUP BY sq.RiderID
    ),

    WildcardStats AS (
        SELECT
            sl.RiderID,
            SUM(CASE WHEN sl.Result = 1 THEN 1 ELSE 0 END) AS ConsiWins
        FROM SMX_LCQS sl
        JOIN Race_Table rt
            ON rt.RaceID = sl.RaceID
        WHERE rt.Year = :year
          AND rt.SportID = 3
          AND sl.ClassID = :classid
        GROUP BY sl.RiderID
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
        ISNULL(w.ConsiWins, 0) AS ConsiWins
    FROM RiderBase r
    LEFT JOIN MotoStats m ON r.RiderID = m.RiderID
    LEFT JOIN QualStats q ON r.RiderID = q.RiderID
    LEFT JOIN WildcardStats w ON r.RiderID = w.RiderID
    ORDER BY
        CASE WHEN m.AvgMoto IS NULL THEN 1 ELSE 0 END,
        m.AvgMoto ASC,
        q.AvgQual DESC
    """

    return fetch_all(query, locals())


@router.get("/api/smx/season/laps-led")
def get_smx_season_laps_led(year: int, classid: int):
    query = """
    WITH RiderLaps AS (
        SELECT
            rt.Year,
            so.ClassID,
            so.RiderID,
            so.FullName,
            MAX(so.Brand) AS Brand,
            SUM(
                CASE
                    WHEN so.LapsLed IS NOT NULL THEN so.LapsLed
                    ELSE COALESCE(so.M1_Laps_Led, 0) + COALESCE(so.M2_Laps_Led, 0)
                END
            ) AS LapsLed
        FROM SMX_OVERALLS so
        JOIN Race_Table rt
            ON rt.RaceID = so.RaceID
        WHERE rt.Year = :year
          AND rt.SportID = 3
          AND so.ClassID = :classid
        GROUP BY
            rt.Year,
            so.ClassID,
            so.RiderID,
            so.FullName
    ),

    TotalLaps AS (
        SELECT SUM(LapsLed) AS Total FROM RiderLaps
    )

    SELECT
        r.Year,
        3 AS SportID,
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


@router.get("/api/wmx/season/overall")
def get_wmx_season_overall(year: int):
    summary_results = _get_wmx_season_overall_from_summary(year)
    if summary_results:
        return summary_results

    query = """
    WITH Base AS (
        SELECT
            wo.raceid AS RaceID,
            wo.riderid AS RiderID,
            wo.FullName,
            wo.Brand,
            wo.Result,
            wo.Points
        FROM WMX_OVERALLS wo
        JOIN Race_Table rt ON rt.RaceID = wo.raceid
        WHERE rt.[Year] = :year
          AND rt.SportID = 4
    ),
    StartHoleshotRows AS (
        SELECT wm.riderid AS RiderID, wm.[Start], wm.Holeshot
        FROM WMX_MOTOS wm
        JOIN Race_Table rt ON rt.RaceID = wm.raceid
        WHERE rt.[Year] = :year AND rt.SportID = 4

        UNION ALL

        SELECT wo.riderid, fallback.[Start], fallback.Holeshot
        FROM WMX_OVERALLS wo
        JOIN Race_Table rt ON rt.RaceID = wo.raceid
        CROSS APPLY (VALUES
            (wo.M1_Start, COALESCE(wo.M1_Holeshot, wo.Holeshot)),
            (wo.M2_Start, wo.M2_Holeshot)
        ) fallback([Start], Holeshot)
        WHERE rt.[Year] = :year AND rt.SportID = 4
          AND NOT EXISTS (
              SELECT 1 FROM WMX_MOTOS wm
              WHERE wm.raceid = wo.raceid AND wm.riderid = wo.riderid
          )
          AND (fallback.[Start] IS NOT NULL OR fallback.Holeshot IS NOT NULL)
    ),
    StartHoleshotStats AS (
        SELECT RiderID,
               SUM(COALESCE(CAST(Holeshot AS INT), 0)) AS Holeshots,
               CAST(AVG(CAST([Start] AS DECIMAL(10,2))) AS DECIMAL(10,2)) AS AvgStart
        FROM StartHoleshotRows
        GROUP BY RiderID
    ),
    OverallStats AS (
        SELECT RiderID, MAX(FullName) AS FullName, MAX(Brand) AS Brand, COUNT(*) AS Starts,
               SUM(CASE WHEN Result = 1 THEN 1 ELSE 0 END) AS Wins,
               SUM(CASE WHEN Result <= 3 THEN 1 ELSE 0 END) AS Podiums,
               SUM(CASE WHEN Result <= 5 THEN 1 ELSE 0 END) AS Top5,
               SUM(CASE WHEN Result <= 10 THEN 1 ELSE 0 END) AS Top10,
               MIN(Result) AS BestOverall,
               CAST(AVG(CAST(Result AS FLOAT)) AS DECIMAL(10,2)) AS AvgOverall,
               SUM(COALESCE(Points, 0)) AS Points
        FROM Base
        GROUP BY RiderID
    )
    SELECT
        overall.RiderID, overall.FullName, overall.Brand, overall.Starts,
        overall.Wins, overall.Podiums, overall.Top5, overall.Top10,
        overall.BestOverall, overall.AvgOverall,
        COALESCE(session_stats.Holeshots, 0) AS Holeshots,
        session_stats.AvgStart,
        overall.Points
    FROM OverallStats overall
    LEFT JOIN StartHoleshotStats session_stats ON session_stats.RiderID = overall.RiderID
    ORDER BY overall.Points DESC, overall.Wins DESC, overall.AvgOverall ASC
    """
    return fetch_all(query, {"year": year})


@router.get("/api/wmx/season/moto-qual")
def get_wmx_season_moto_qual(year: int):
    summary_results = _get_wmx_season_moto_qual_from_summary(year)
    if summary_results:
        return summary_results

    query = """
    WITH RiderBase AS (
        SELECT DISTINCT wo.riderid AS RiderID, wo.FullName
        FROM WMX_OVERALLS wo
        JOIN Race_Table rt ON rt.RaceID = wo.raceid
        WHERE rt.[Year] = :year AND rt.SportID = 4

        UNION

        SELECT DISTINCT wq.riderid AS RiderID, wq.FullName
        FROM WMX_QUAL wq
        JOIN Race_Table rt ON rt.RaceID = wq.raceid
        WHERE rt.[Year] = :year AND rt.SportID = 4
    ),
    MotoStats AS (
        SELECT
            motos.RiderID,
            SUM(CASE WHEN motos.Result = 1 THEN 1 ELSE 0 END) AS MotoWins,
            SUM(CASE WHEN motos.Result <= 3 THEN 1 ELSE 0 END) AS MotoPodiums,
            MIN(motos.Result) AS BestMoto,
            CAST(AVG(CAST(motos.Result AS FLOAT)) AS DECIMAL(10,2)) AS AvgMoto
        FROM (
            SELECT wm.riderid AS RiderID, wm.Result
            FROM WMX_MOTOS wm
            JOIN Race_Table rt ON rt.RaceID = wm.raceid
            WHERE rt.[Year] = :year AND rt.SportID = 4 AND wm.Result IS NOT NULL

            UNION ALL

            SELECT wo.riderid, valueset.Result
            FROM WMX_OVERALLS wo
            JOIN Race_Table rt ON rt.RaceID = wo.raceid
            CROSS APPLY (VALUES (wo.Moto1), (wo.Moto2), (wo.Moto3)) valueset(Result)
            WHERE rt.[Year] = :year AND rt.SportID = 4
              AND valueset.Result IS NOT NULL
              AND NOT EXISTS (
                  SELECT 1 FROM WMX_MOTOS wm
                  WHERE wm.raceid = wo.raceid AND wm.riderid = wo.riderid
              )
        ) motos
        GROUP BY motos.RiderID
    ),
    QualStats AS (
        SELECT
            wq.riderid AS RiderID,
            COUNT(*) AS QualStarts,
            SUM(CASE WHEN wq.Result = 1 THEN 1 ELSE 0 END) AS Poles,
            CAST(AVG(CAST(wq.Result AS FLOAT)) AS DECIMAL(10,2)) AS AvgQual
        FROM WMX_QUAL wq
        JOIN Race_Table rt ON rt.RaceID = wq.raceid
        WHERE rt.[Year] = :year AND rt.SportID = 4
        GROUP BY wq.riderid
    )
    SELECT
        rb.RiderID,
        MAX(rb.FullName) AS FullName,
        COALESCE(m.MotoWins, 0) AS MotoWins,
        COALESCE(m.MotoPodiums, 0) AS MotoPodiums,
        m.BestMoto,
        m.AvgMoto,
        COALESCE(q.Poles, 0) AS Poles,
        COALESCE(q.QualStarts, 0) AS QualStarts,
        q.AvgQual,
        0 AS ConsiWins
    FROM RiderBase rb
    LEFT JOIN MotoStats m ON m.RiderID = rb.RiderID
    LEFT JOIN QualStats q ON q.RiderID = rb.RiderID
    GROUP BY rb.RiderID, m.MotoWins, m.MotoPodiums, m.BestMoto, m.AvgMoto,
             q.Poles, q.QualStarts, q.AvgQual
    ORDER BY CASE WHEN m.AvgMoto IS NULL THEN 1 ELSE 0 END, m.AvgMoto, q.AvgQual
    """
    return fetch_all(query, {"year": year})


@router.get("/api/wmx/season/laps-led")
def get_wmx_season_laps_led(year: int):
    query = """
    WITH RiderLaps AS (
        SELECT
            rt.[Year],
            wo.riderid AS RiderID,
            MAX(wo.FullName) AS FullName,
            MAX(wo.Brand) AS Brand,
            SUM(CASE
                WHEN wo.LapsLed IS NOT NULL THEN CAST(wo.LapsLed AS INT)
                ELSE COALESCE(CAST(wo.M1_Laps_Led AS INT), 0)
                   + COALESCE(CAST(wo.M2_Laps_Led AS INT), 0)
            END) AS LapsLed
        FROM WMX_OVERALLS wo
        JOIN Race_Table rt ON rt.RaceID = wo.raceid
        WHERE rt.[Year] = :year AND rt.SportID = 4
        GROUP BY rt.[Year], wo.riderid
    ),
    TotalLaps AS (
        SELECT SUM(LapsLed) AS Total FROM RiderLaps
    )
    SELECT
        r.[Year],
        4 AS SportID,
        4 AS ClassID,
        r.RiderID,
        r.FullName,
        r.Brand,
        r.LapsLed,
        CASE WHEN t.Total = 0 THEN 0 ELSE r.LapsLed * 1.0 / t.Total END AS PctLapsLed
    FROM RiderLaps r
    CROSS JOIN TotalLaps t
    ORDER BY r.LapsLed DESC
    """
    return fetch_all(query, {"year": year})


@router.get("/api/wmx/season/points-progression")
def get_wmx_season_points_progression(year: int):
    query = """
    SELECT
        [Year],
        SportID,
        CAST(0 AS INT) AS ClassID,
        OverallRound AS Round,
        RiderID,
        FullName,
        CAST(NULL AS INT) AS RiderCoastID,
        TotalPoints AS CumulativePoints
    FROM dbo.vw_WMX_RunningStandings
    WHERE [Year] = :year
    ORDER BY RaceDate, RaceID, TotalPoints DESC, RiderID
    """

    return fetch_all(query, {"year": year})


@router.get("/api/mx/season/points-progression")
def get_mx_season_points_progression(year: int, classid: int):
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


@router.get("/api/smx/season/points-progression")
def get_smx_season_points_progression(year: int, classid: int):
    query = """
    SELECT
        [Year],
        3 AS SportID,
        ClassID,
        ClassRound AS Round,
        RiderID,
        FullName,
        CAST(NULL AS INT) AS RiderCoastID,
        TotalPoints AS CumulativePoints
    FROM dbo.vw_SMX_RunningStandings
    WHERE [Year] = :year
      AND ClassID = :classid
    ORDER BY ClassRound, TotalPoints DESC, RiderID
    """

    return fetch_all(query, locals())


@router.get("/api/years")
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
        raise_http_error("Failed to load available years.", e)


@router.get("/api/races")
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


@router.get("/api/season-champions")
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


@router.get("/season/current")
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

            sport = "sx" if row.SportID == 1 else "mx" if row.SportID == 2 else "smx"

            return {
                "sport": sport,
                "year": row.Year,
                "classId": "450"
            }

    except Exception as e:
        raise_http_error("Failed to load current season.", e)


@router.get("/api/available-classes")
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
    elif sport_id == 2:
        query = """
            SELECT DISTINCT mo.ClassID
            FROM MX_OVERALLS mo
            JOIN Race_Table rt
                ON rt.RaceID = mo.RaceID
            WHERE rt.Year = :year
              AND rt.SportID = 2
        """
    elif sport_id == 3:
        query = """
            SELECT DISTINCT so.ClassID
            FROM SMX_OVERALLS so
            JOIN Race_Table rt
                ON rt.RaceID = so.RaceID
            WHERE rt.Year = :year
              AND rt.SportID = 3
        """
    else:
        raise HTTPException(status_code=400, detail="Invalid sport_id")

    return fetch_all(query, {"year": year})
