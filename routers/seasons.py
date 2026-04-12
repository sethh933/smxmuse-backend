import pyodbc
from fastapi import APIRouter

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


@router.get("/api/season/main-stats")
def get_season_main_stats(
    year: int,
    sportid: int,
    classid: int,
    ridercoastid: int = None
):
    if sportid == 1:
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
            ms.Wins,
            ms.Podiums,
            ms.Top5s,
            ms.Top10s,
            ms.BestFinish,
            ms.AvgFinish,
            ms.MainsMade,
            COALESCE(ha.Holeshots, ms.Holeshots) AS Holeshots,
            COALESCE(ssa.AvgStartPosition, ms.AvgStartPosition) AS AvgStartPosition,
            ba.Brand
        FROM MainStats ms
        LEFT JOIN Rider_List rl
            ON rl.RiderID = ms.RiderID
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


@router.get("/api/season/points-progression")
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
        return summary_results

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

    return fetch_all(query, locals())


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

            sport = "sx" if row.SportID == 1 else "mx"

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
