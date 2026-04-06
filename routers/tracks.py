import pyodbc
from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from db import CONN_STR, engine, fetch_all
from error_utils import raise_http_error


router = APIRouter()


@router.get("/api/track-profile")
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
        raise_http_error("Failed to load track profile.", e)


@router.get("/api/track-classes")
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


@router.get("/api/race-header")
def get_race_header(raceid: int):
    query = """
    DECLARE @RaceID INT = ?;

    SELECT
        rt.TrackID AS TrackID,
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
