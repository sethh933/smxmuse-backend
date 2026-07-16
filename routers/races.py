import pyodbc
from fastapi import APIRouter

from db import CONN_STR, fetch_all
from error_utils import raise_http_error


router = APIRouter()


def _lap_time_to_seconds(lap_time):
    if lap_time is None:
        return None

    value = str(lap_time).strip()
    if not value:
        return None

    try:
        if ":" in value:
            minutes, seconds = value.split(":", 1)
            return (int(minutes) * 60) + float(seconds)

        return float(value)
    except (TypeError, ValueError):
        return None


def _seconds_to_lap_time(seconds):
    if seconds is None:
        return None

    if seconds >= 60:
        minutes = int(seconds // 60)
        remainder = seconds - (minutes * 60)
        return f"{minutes}:{remainder:06.3f}"

    return f"{seconds:.3f}"


def _standard_deviation(values):
    if not values:
        return None

    average = sum(values) / len(values)
    variance = sum((value - average) ** 2 for value in values) / len(values)
    return variance ** 0.5


def _consistency_percentage(values):
    if not values:
        return None

    average = sum(values) / len(values)
    if average == 0:
        return None

    standard_deviation = _standard_deviation(values)
    return 100 - ((standard_deviation / average) * 100)


def _build_lap_segment_detail(rows, rank_rows, riderid: int):
    lap_ranks = {}
    lap_times_by_lap = {}
    rider_lap_seconds = {}
    rider_segment_bests = {}
    rider_segment_seconds = {}
    average_consistency_rank_eligible = {}

    for row in rank_rows:
        rank_riderid = row.get("riderid")
        race_status = row.get("race_status")
        average_consistency_rank_eligible[rank_riderid] = (
            not isinstance(race_status, str)
            or race_status.strip().upper() != "DNF"
        )
        seconds = _lap_time_to_seconds(row.get("laptime"))

        if seconds is not None:
            lap_times_by_lap.setdefault(row.get("lap"), []).append({
                "riderid": row.get("riderid"),
                "seconds": seconds,
            })

            if row.get("lap") != 1:
                rider_lap_seconds.setdefault(row.get("riderid"), []).append(seconds)

        for segment_number in range(1, 11):
            key = f"seg_{segment_number}"
            segment_time = row.get(key)
            if segment_time is None:
                continue

            segment_key = (segment_number, row.get("riderid"))
            previous_best = rider_segment_bests.get(segment_key)
            if previous_best is None or segment_time < previous_best:
                rider_segment_bests[segment_key] = segment_time

            rider_segment_seconds.setdefault(segment_key, []).append(segment_time)

    for lap, lap_times in lap_times_by_lap.items():
        previous_seconds = None
        current_rank = 0

        for index, lap_time in enumerate(
            sorted(lap_times, key=lambda item: item["seconds"]),
            start=1,
        ):
            if previous_seconds is None or lap_time["seconds"] != previous_seconds:
                current_rank = index

            lap_ranks[(lap, lap_time["riderid"])] = current_rank
            previous_seconds = lap_time["seconds"]

    average_lap_ranks = {}
    consistency_ranks = {}
    best_lap_ranks = {}
    rider_averages = [
        {
            "riderid": rank_riderid,
            "seconds": sum(rank_lap_seconds) / len(rank_lap_seconds),
        }
        for rank_riderid, rank_lap_seconds in rider_lap_seconds.items()
        if rank_lap_seconds
        and average_consistency_rank_eligible.get(rank_riderid, True)
    ]
    previous_average_seconds = None
    current_average_rank = 0

    for index, rider_average in enumerate(
        sorted(rider_averages, key=lambda item: item["seconds"]),
        start=1,
    ):
        if previous_average_seconds is None or rider_average["seconds"] != previous_average_seconds:
            current_average_rank = index

        average_lap_ranks[rider_average["riderid"]] = current_average_rank
        previous_average_seconds = rider_average["seconds"]

    rider_consistency_scores = [
        {
            "riderid": rank_riderid,
            "seconds": _standard_deviation(rank_lap_seconds),
        }
        for rank_riderid, rank_lap_seconds in rider_lap_seconds.items()
        if rank_lap_seconds
        and average_consistency_rank_eligible.get(rank_riderid, True)
    ]
    previous_consistency_seconds = None
    current_consistency_rank = 0

    for index, rider_consistency in enumerate(
        sorted(rider_consistency_scores, key=lambda item: item["seconds"]),
        start=1,
    ):
        if (
            previous_consistency_seconds is None
            or rider_consistency["seconds"] != previous_consistency_seconds
        ):
            current_consistency_rank = index

        consistency_ranks[rider_consistency["riderid"]] = current_consistency_rank
        previous_consistency_seconds = rider_consistency["seconds"]

    rider_best_laps = [
        {
            "riderid": rank_riderid,
            "seconds": min(rank_lap_seconds),
        }
        for rank_riderid, rank_lap_seconds in rider_lap_seconds.items()
        if rank_lap_seconds
    ]
    previous_best_lap_seconds = None
    current_best_lap_rank = 0

    for index, rider_best_lap in enumerate(
        sorted(rider_best_laps, key=lambda item: item["seconds"]),
        start=1,
    ):
        if previous_best_lap_seconds is None or rider_best_lap["seconds"] != previous_best_lap_seconds:
            current_best_lap_rank = index

        best_lap_ranks[rider_best_lap["riderid"]] = current_best_lap_rank
        previous_best_lap_seconds = rider_best_lap["seconds"]

    segment_best_ranks = {}
    segment_average_ranks = {}
    for segment_number in range(1, 11):
        segment_bests_for_rank = [
            {
                "riderid": segment_riderid,
                "seconds": segment_time,
            }
            for (rank_segment, segment_riderid), segment_time in rider_segment_bests.items()
            if rank_segment == segment_number
        ]
        previous_segment_seconds = None
        current_segment_rank = 0

        for index, segment_best in enumerate(
            sorted(segment_bests_for_rank, key=lambda item: item["seconds"]),
            start=1,
        ):
            if previous_segment_seconds is None or segment_best["seconds"] != previous_segment_seconds:
                current_segment_rank = index

            segment_best_ranks[(segment_number, segment_best["riderid"])] = current_segment_rank
            previous_segment_seconds = segment_best["seconds"]

        segment_averages_for_rank = [
            {
                "riderid": segment_riderid,
                "seconds": sum(segment_seconds) / len(segment_seconds),
            }
            for (rank_segment, segment_riderid), segment_seconds in rider_segment_seconds.items()
            if rank_segment == segment_number and segment_seconds
        ]
        previous_segment_average_seconds = None
        current_segment_average_rank = 0

        for index, segment_average in enumerate(
            sorted(segment_averages_for_rank, key=lambda item: item["seconds"]),
            start=1,
        ):
            if (
                previous_segment_average_seconds is None
                or segment_average["seconds"] != previous_segment_average_seconds
            ):
                current_segment_average_rank = index

            segment_average_ranks[(segment_number, segment_average["riderid"])] = current_segment_average_rank
            previous_segment_average_seconds = segment_average["seconds"]

    lap_seconds = [
        seconds
        for seconds in (
            _lap_time_to_seconds(row.get("laptime"))
            for row in rows
            if row.get("lap") != 1
        )
        if seconds is not None
    ]
    average_seconds = sum(lap_seconds) / len(lap_seconds) if lap_seconds else None
    consistency_percentage = _consistency_percentage(lap_seconds)
    best_lap_seconds = min(lap_seconds) if lap_seconds else None

    segment_bests = []
    segment_averages = []
    for segment_number in range(1, 11):
        key = f"seg_{segment_number}"
        best_row = None
        best_time = None
        segment_times = []

        for row in rows:
            segment_time = row.get(key)
            if segment_time is None:
                continue

            segment_times.append(segment_time)

            if best_time is None or segment_time < best_time:
                best_time = segment_time
                best_row = row

        if best_row is not None:
            segment_bests.append({
                "segment": segment_number,
                "time": round(best_time, 3),
                "lap": best_row.get("lap"),
                "rank": segment_best_ranks.get((segment_number, riderid)),
            })

        if segment_times:
            average_segment_time = sum(segment_times) / len(segment_times)
            segment_averages.append({
                "segment": segment_number,
                "time": round(average_segment_time, 3),
                "rank": segment_average_ranks.get((segment_number, riderid)),
            })

    return {
        "average_lap_time": _seconds_to_lap_time(average_seconds),
        "average_lap_rank": average_lap_ranks.get(riderid),
        "best_lap_time": _seconds_to_lap_time(best_lap_seconds),
        "best_lap_rank": best_lap_ranks.get(riderid),
        "consistency_score": (
            f"{consistency_percentage:.3f}%"
            if consistency_percentage is not None
            else None
        ),
        "consistency_rank": consistency_ranks.get(riderid),
        "laps": [
            {
                "lap": row.get("lap"),
                "laptime": row.get("laptime"),
                "position": row.get("position"),
                "laptime_rank": lap_ranks.get((row.get("lap"), row.get("riderid"))),
            }
            for row in rows
        ],
        "segment_bests": segment_bests,
        "segment_averages": segment_averages,
    }


def _rank_values(items):
    ranks = {}
    previous_value = None
    current_rank = 0

    for index, item in enumerate(
        sorted(items, key=lambda rank_item: rank_item["value"]),
        start=1,
    ):
        if previous_value is None or item["value"] != previous_value:
            current_rank = index

        ranks[item["key"]] = current_rank
        previous_value = item["value"]

    return ranks


def _build_qualifying_session_detail(rows, rank_rows, riderid: int):
    session_laps = {}
    session_segment_bests = {}

    for row in rank_rows:
        session_key = (row.get("group"), row.get("session"))
        seconds = _lap_time_to_seconds(row.get("laptime"))

        if seconds is not None and row.get("lap") != 1:
            session_laps.setdefault(session_key, {}).setdefault(row.get("riderid"), []).append({
                "seconds": seconds,
                "laptime": row.get("laptime"),
                "lap": row.get("lap"),
            })

        for segment_number in range(1, 11):
            key = f"seg_{segment_number}"
            segment_time = row.get(key)
            if segment_time is None:
                continue

            segment_key = (session_key, segment_number, row.get("riderid"))
            previous_best = session_segment_bests.get(segment_key)
            if previous_best is None or segment_time < previous_best["time"]:
                session_segment_bests[segment_key] = {
                    "time": segment_time,
                    "lap": row.get("lap"),
                }

    fastest_ranks = {}
    second_fastest_ranks = {}
    segment_ranks = {}

    for session_key, laps_by_rider in session_laps.items():
        fastest_items = []
        second_fastest_items = []

        for rank_riderid, laps in laps_by_rider.items():
            sorted_laps = sorted(laps, key=lambda lap: lap["seconds"])
            if sorted_laps:
                fastest_items.append({
                    "key": (session_key, rank_riderid),
                    "value": sorted_laps[0]["seconds"],
                })
            if len(sorted_laps) > 1:
                second_fastest_items.append({
                    "key": (session_key, rank_riderid),
                    "value": sorted_laps[1]["seconds"],
                })

        fastest_ranks.update(_rank_values(fastest_items))
        second_fastest_ranks.update(_rank_values(second_fastest_items))

        for segment_number in range(1, 11):
            segment_items = [
                {
                    "key": (session_key, segment_number, segment_riderid),
                    "value": segment_best["time"],
                }
                for (
                    rank_session_key,
                    rank_segment_number,
                    segment_riderid,
                ), segment_best in session_segment_bests.items()
                if rank_session_key == session_key and rank_segment_number == segment_number
            ]
            segment_ranks.update(_rank_values(segment_items))

    rider_sessions = {}

    for row in rows:
        session_key = (row.get("group"), row.get("session"))
        rider_sessions.setdefault(session_key, []).append(row)

    sessions = []

    for session_key, session_rows in sorted(
        rider_sessions.items(),
        key=lambda item: (str(item[0][0] or ""), item[0][1] or 0),
    ):
        session_group, session_number = session_key
        timed_laps = [
            {
                "seconds": seconds,
                "laptime": row.get("laptime"),
                "lap": row.get("lap"),
            }
            for row in session_rows
            for seconds in [_lap_time_to_seconds(row.get("laptime"))]
            if seconds is not None and row.get("lap") != 1
        ]
        sorted_timed_laps = sorted(timed_laps, key=lambda lap: lap["seconds"])
        fastest_lap = sorted_timed_laps[0] if sorted_timed_laps else None
        second_fastest_lap = sorted_timed_laps[1] if len(sorted_timed_laps) > 1 else None

        segment_bests = []
        for segment_number in range(1, 11):
            segment_key = (session_key, segment_number, riderid)
            segment_best = session_segment_bests.get(segment_key)
            if segment_best is None:
                continue

            segment_bests.append({
                "segment": segment_number,
                "time": round(float(segment_best["time"]), 3),
                "lap": segment_best["lap"],
                "rank": segment_ranks.get(segment_key),
            })

        sessions.append({
            "group": session_group,
            "session": session_number,
            "fastest_lap_time": fastest_lap["laptime"] if fastest_lap else None,
            "fastest_lap": fastest_lap["lap"] if fastest_lap else None,
            "fastest_lap_rank": fastest_ranks.get((session_key, riderid)),
            "second_fastest_lap_time": (
                second_fastest_lap["laptime"] if second_fastest_lap else None
            ),
            "second_fastest_lap": second_fastest_lap["lap"] if second_fastest_lap else None,
            "second_fastest_lap_rank": second_fastest_ranks.get((session_key, riderid)),
            "segment_bests": segment_bests,
        })

    return {"sessions": sessions}


@router.get("/api/race/overalls")
def get_mx_overalls(raceid: int, classid: int, sport_id: int = 2):
    with pyodbc.connect(CONN_STR) as conn:
        cursor = conn.cursor()

        overall_table = "SMX_OVERALLS" if sport_id == 3 else "MX_OVERALLS"
        sport_column = "sport_id" if sport_id == 3 else "Sport_ID"

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
                rl.ImageURL,
                rl.Country
            FROM {overall_table} mo
            LEFT JOIN Rider_List rl
                ON rl.RiderID = mo.RiderID
            WHERE mo.raceid = ?
            AND mo.classid = ?
            AND mo.{sport_column} = ?
            ORDER BY CASE WHEN mo.Result IS NULL THEN 1 ELSE 0 END, mo.Result
        """.format(overall_table=overall_table, sport_column=sport_column), raceid, classid, sport_id)

        columns = [column[0].lower() for column in cursor.description]

        results = [
            dict(zip(columns, row))
            for row in cursor.fetchall()
        ]

    return results


@router.get("/api/race/smx-motos")
def get_smx_motos(raceid: int, classid: int, moto: int):
    with pyodbc.connect(CONN_STR) as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                sm.Result AS Result,
                sm.riderid AS riderid,
                COALESCE(rl.FullName, sm.FullName) AS FullName,
                sm.Brand AS Brand,
                sm.Interval AS Interval,
                sm.BestLap AS BestLap,
                sm.Start AS Start,
                sm.Holeshot AS Holeshot,
                sm.RaceStatus AS RaceStatus,
                rl.ImageURL AS ImageURL,
                rl.Country AS Country
            FROM SMX_MOTOS sm
            LEFT JOIN Rider_List rl
                ON rl.RiderID = sm.RiderID
            WHERE sm.raceid = ?
              AND sm.classid = ?
              AND sm.Moto = ?
              AND sm.sportid = 3
            ORDER BY CASE WHEN sm.Result IS NULL THEN 1 ELSE 0 END, sm.Result
        """, raceid, classid, moto)

        columns = [column[0].lower() for column in cursor.description]

        return [
            dict(zip(columns, row))
            for row in cursor.fetchall()
        ]


@router.get("/api/race/mx-motos")
def get_mx_motos(raceid: int, classid: int, moto: int):
    with pyodbc.connect(CONN_STR) as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                mm.Result AS Result,
                mm.riderid AS riderid,
                COALESCE(rl.FullName, mm.FullName) AS FullName,
                mm.Brand AS Brand,
                mm.Interval AS Interval,
                mm.BestLap AS BestLap,
                mm.Start AS Start,
                mm.Holeshot AS Holeshot,
                mm.RaceStatus AS RaceStatus,
                rl.ImageURL AS ImageURL,
                rl.Country AS Country
            FROM MX_MOTOS mm
            LEFT JOIN Rider_List rl
                ON rl.RiderID = mm.RiderID
            WHERE mm.raceid = ?
              AND mm.classid = ?
              AND mm.Moto = ?
              AND mm.sportid = 2
            ORDER BY CASE WHEN mm.Result IS NULL THEN 1 ELSE 0 END, mm.Result
        """, raceid, classid, moto)

        columns = [column[0].lower() for column in cursor.description]

        return [
            dict(zip(columns, row))
            for row in cursor.fetchall()
        ]


@router.get("/api/race/mx-moto-rider-details")
def get_mx_moto_rider_details(raceid: int, classid: int, moto: int, riderid: int):
    params = {
        "raceid": raceid,
        "classid": classid,
        "moto": moto,
        "riderid": riderid,
    }
    rows = fetch_all("""
        SELECT
            mms.LAP      AS lap,
            mms.riderid  AS riderid,
            mms.LAPTIME  AS laptime,
            mms.position AS position,
            mms.SEG_1    AS seg_1,
            mms.SEG_2    AS seg_2,
            mms.SEG_3    AS seg_3,
            mms.SEG_4    AS seg_4,
            mms.SEG_5    AS seg_5,
            mms.SEG_6    AS seg_6,
            mms.SEG_7    AS seg_7,
            mms.SEG_8    AS seg_8,
            mms.SEG_9    AS seg_9,
            mms.SEG_10   AS seg_10
        FROM dbo.MX_MOTO_SEGMENTS mms
        WHERE mms.raceid = :raceid
          AND mms.classid = :classid
          AND mms.Moto = :moto
          AND mms.riderid = :riderid
          AND mms.sportid = 2
        ORDER BY mms.LAP
    """, params)
    rank_rows = fetch_all("""
        SELECT
            mms.LAP     AS lap,
            mms.riderid AS riderid,
            mms.LAPTIME AS laptime,
            mm.RaceStatus AS race_status,
            mms.SEG_1   AS seg_1,
            mms.SEG_2   AS seg_2,
            mms.SEG_3   AS seg_3,
            mms.SEG_4   AS seg_4,
            mms.SEG_5   AS seg_5,
            mms.SEG_6   AS seg_6,
            mms.SEG_7   AS seg_7,
            mms.SEG_8   AS seg_8,
            mms.SEG_9   AS seg_9,
            mms.SEG_10  AS seg_10
        FROM dbo.MX_MOTO_SEGMENTS mms
        LEFT JOIN dbo.MX_MOTOS mm
          ON mm.raceid = mms.raceid
         AND mm.classid = mms.classid
         AND mm.Moto = mms.Moto
         AND mm.riderid = mms.riderid
         AND mm.sportid = mms.sportid
        WHERE mms.raceid = :raceid
          AND mms.classid = :classid
          AND mms.Moto = :moto
          AND mms.sportid = 2
    """, params)

    return _build_lap_segment_detail(rows, rank_rows, riderid)


@router.get("/api/race/consi")
def get_mx_consi(raceid: int, classid: int):
    with pyodbc.connect(CONN_STR) as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                mc.Result AS Result,
                mc.riderid AS riderid,
                COALESCE(rl.FullName, mc.FullName) AS FullName,
                mc.Brand AS Brand,
                rl.ImageURL AS ImageURL,
                rl.Country AS Country
            FROM MX_CONSIS mc
            LEFT JOIN Rider_List rl
                ON rl.RiderID = mc.RiderID
            WHERE mc.raceid = ?
            AND mc.classid = ?
            ORDER BY CASE WHEN mc.Result IS NULL THEN 1 ELSE 0 END, mc.Result
        """, raceid, classid)

        columns = [column[0].lower() for column in cursor.description]

        results = [
            dict(zip(columns, row))
            for row in cursor.fetchall()
        ]

    return results


@router.get("/api/race/legacy-mx-sessions")
def get_legacy_mx_sessions(raceid: int):
    """Return 2004-2008 MX qualifying and consi sessions in race-page order."""
    rows = fetch_all(
        """
        WITH LegacySessions AS (
            SELECT
                CASE
                    WHEN q.ClassID = 1 AND q.qualtype = 'prequal' AND q.qual = 1 THEN 1
                    WHEN q.ClassID = 1 AND q.qualtype = 'prequal' AND q.qual = 2 THEN 2
                    WHEN q.ClassID = 2 AND q.qualtype = 'prequal' AND q.qual = 1 THEN 3
                    WHEN q.ClassID = 2 AND q.qualtype = 'prequal' AND q.qual = 2 THEN 4
                    WHEN q.ClassID = 1 AND q.qualtype = 'qual' AND q.qual = 1 THEN 7
                    WHEN q.ClassID = 1 AND q.qualtype = 'qual' AND q.qual = 2 THEN 8
                    WHEN q.ClassID = 2 AND q.qualtype = 'qual' AND q.qual = 1 THEN 9
                    WHEN q.ClassID = 2 AND q.qualtype = 'qual' AND q.qual = 2 THEN 10
                END AS SessionOrder,
                q.ClassID,
                CASE WHEN q.qualtype = 'prequal' THEN 'Saturday Pre Qualifier'
                     ELSE 'Sunday Qualifier' END AS SessionName,
                q.qual AS SessionNumber,
                q.Result,
                q.RiderID,
                COALESCE(rl.FullName, q.FullName) AS FullName,
                q.Brand,
                q.Interval,
                rl.ImageURL,
                rl.Country
            FROM MX_QUAL_RACES q
            LEFT JOIN Rider_List rl ON rl.RiderID = q.RiderID
            WHERE q.RaceID = :raceid
              AND q.ClassID IN (1, 2)
              AND q.qualtype IN ('prequal', 'qual')
              AND q.qual IN (1, 2)

            UNION ALL

            SELECT
                CASE
                    WHEN c.ClassID = 1 AND c.consitype = 'prequal' THEN 5
                    WHEN c.ClassID = 2 AND c.consitype = 'prequal' THEN 6
                    WHEN c.ClassID = 1 AND c.consitype = 'qual' THEN 11
                    WHEN c.ClassID = 2 AND c.consitype = 'qual' THEN 12
                END,
                c.ClassID,
                CASE WHEN c.consitype = 'prequal' THEN 'Saturday Consi'
                     ELSE 'Sunday Consi' END,
                NULL,
                c.Result,
                c.RiderID,
                COALESCE(rl.FullName, c.FullName),
                c.Brand,
                c.Interval,
                rl.ImageURL,
                rl.Country
            FROM MX_CONSIS_OLD_FORMAT c
            LEFT JOIN Rider_List rl ON rl.RiderID = c.RiderID
            WHERE c.RaceID = :raceid
              AND c.ClassID IN (1, 2)
              AND c.consitype IN ('prequal', 'qual')

            UNION ALL

            SELECT
                CASE
                    WHEN q.ClassID = 1 AND q.[Day] = 'Saturday' THEN 1
                    WHEN q.ClassID = 1 AND q.[Day] = 'Sunday' THEN 3
                    WHEN q.ClassID = 2 AND q.[Day] = 'Saturday' THEN 4
                    WHEN q.ClassID = 2 AND q.[Day] = 'Sunday' THEN 6
                END,
                q.ClassID,
                CASE WHEN q.[Day] = 'Saturday' THEN 'Saturday Timed Qualifying'
                     ELSE 'Sunday Timed Qualifying' END,
                NULL,
                q.Result,
                q.RiderID,
                COALESCE(rl.FullName, q.FullName),
                q.Brand,
                q.BestLap,
                rl.ImageURL,
                rl.Country
            FROM MX_QUAL_OLD_FORMAT q
            LEFT JOIN Rider_List rl ON rl.RiderID = q.RiderID
            WHERE q.RaceID = :raceid
              AND q.ClassID IN (1, 2)
              AND q.[Day] IN ('Saturday', 'Sunday')

            UNION ALL

            SELECT
                CASE WHEN c.ClassID = 1 THEN 2 ELSE 5 END,
                c.ClassID,
                'Consolation Race',
                NULL,
                c.Result,
                c.RiderID,
                COALESCE(rl.FullName, c.FullName),
                c.Brand,
                c.Interval,
                rl.ImageURL,
                rl.Country
            FROM MX_CONSIS_OLD_FORMAT c
            LEFT JOIN Rider_List rl ON rl.RiderID = c.RiderID
            WHERE c.RaceID = :raceid
              AND c.ClassID IN (1, 2)
              AND c.consitype = 'timedqual'
        )
        SELECT SessionOrder, ClassID, SessionName, SessionNumber,
               Result, RiderID, FullName, Brand, Interval, ImageURL, Country
        FROM LegacySessions
        WHERE SessionOrder IS NOT NULL
        ORDER BY SessionOrder, CASE WHEN Result IS NULL THEN 1 ELSE 0 END, Result
        """,
        {"raceid": raceid},
    )

    sessions = []
    for row in rows:
        if not sessions or sessions[-1]["session_order"] != row["SessionOrder"]:
            class_name = "450" if row["ClassID"] == 1 else "250"
            number = f" {row['SessionNumber']}" if row["SessionNumber"] is not None else ""
            sessions.append({
                "session_order": row["SessionOrder"],
                "title": f"{class_name} {row['SessionName']}{number}",
                "results": [],
            })

        sessions[-1]["results"].append({
            "result": row["Result"],
            "riderid": row["RiderID"],
            "fullname": row["FullName"],
            "brand": row["Brand"],
            "interval": row["Interval"],
            "imageurl": row["ImageURL"],
            "country": row["Country"],
        })

    return sessions


@router.get("/api/race/smx-wildcard")
def get_smx_wildcard(raceid: int, classid: int):
    with pyodbc.connect(CONN_STR) as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                sl.Result AS Result,
                sl.riderid AS riderid,
                COALESCE(rl.FullName, sl.FullName) AS FullName,
                sl.Brand AS Brand,
                rl.ImageURL AS ImageURL,
                rl.Country AS Country
            FROM SMX_LCQS sl
            LEFT JOIN Rider_List rl
                ON rl.RiderID = sl.RiderID
            WHERE sl.raceid = ?
              AND sl.classid = ?
              AND sl.sportid = 3
            ORDER BY CASE WHEN sl.Result IS NULL THEN 1 ELSE 0 END, sl.Result
        """, raceid, classid)

        columns = [column[0].lower() for column in cursor.description]

        return [
            dict(zip(columns, row))
            for row in cursor.fetchall()
        ]


@router.get("/api/race/lcqs")
def get_supercross_lcqs(raceid: int, classid: int):
    query = """
        SELECT
            sxl.Result      AS result,
            sxl.riderid     AS riderid,
            COALESCE(rl.FullName, sxl.FullName) AS fullname,
            sxl.Brand       AS brand,
            sxl.RiderCoastID AS ridercoastid,
            rl.ImageURL AS imageurl,
            rl.Country AS country
        FROM SX_LCQS sxl
        LEFT JOIN Rider_List rl
            ON rl.RiderID = sxl.RiderID
        WHERE sxl.RaceID = :raceid
          AND sxl.ClassID = :classid
        ORDER BY CASE WHEN sxl.Result IS NULL THEN 1 ELSE 0 END, sxl.Result
    """

    return fetch_all(query, {"raceid": raceid, "classid": classid})


@router.get("/api/race/qualifying")
def get_qualifying(raceid: int, classid: int, sport_id: int):
    try:
        if sport_id == 1:
            query = """
                SELECT
                    sxq.Result      AS result,
                    sxq.riderid     AS riderid,
                    COALESCE(rl.FullName, sxq.FullName) AS fullname,
                    sxq.Brand       AS brand,
                    sxq.Best_Lap    AS best_lap,
                    sxq.RiderCoastID AS ridercoastid,
                    sxq.coastid     AS coastid,
                    rl.ImageURL     AS imageurl,
                    rl.Country      AS country
                FROM SX_QUAL sxq
                LEFT JOIN Rider_List rl
                    ON rl.RiderID = sxq.RiderID
                WHERE sxq.RaceID = :raceid
                  AND sxq.ClassID = :classid
                ORDER BY CASE WHEN sxq.Result IS NULL THEN 1 ELSE 0 END, sxq.Result
            """

            return fetch_all(query, {
                "raceid": raceid,
                "classid": classid
            })

        with pyodbc.connect(CONN_STR) as conn:
            cursor = conn.cursor()

            qual_table = "SMX_QUAL" if sport_id == 3 else "MX_QUAL"
            sport_column = "SportId" if sport_id == 3 else "SportID"

            cursor.execute("""
                SELECT
                    mq.Result AS Result,
                    mq.riderid AS riderid,
                    COALESCE(rl.FullName, mq.FullName) AS FullName,
                    mq.Brand AS Brand,
                    mq.Best_Lap AS Best_Lap,
                    rl.ImageURL AS ImageURL,
                    rl.Country AS Country
                FROM {qual_table} mq
                LEFT JOIN Rider_List rl
                    ON rl.RiderID = mq.RiderID
                WHERE mq.raceid = ?
                  AND mq.classid = ?
                  AND mq.{sport_column} = ?
                ORDER BY CASE WHEN mq.Result IS NULL THEN 1 ELSE 0 END, mq.Result
            """.format(qual_table=qual_table, sport_column=sport_column), raceid, classid, sport_id)

            columns = [column[0].lower() for column in cursor.description]

            return [
                dict(zip(columns, row))
                for row in cursor.fetchall()
            ]

    except Exception as e:
        raise_http_error("Failed to load race qualifying results.", e)


@router.get("/api/race/mx-qualifying-rider-details")
def get_mx_qualifying_rider_details(raceid: int, classid: int, riderid: int):
    params = {
        "raceid": raceid,
        "classid": classid,
        "riderid": riderid,
    }
    query_columns = """
        mqs.[Group]  AS [group],
        mqs.[Session] AS session,
        mqs.Lap      AS lap,
        mqs.riderid  AS riderid,
        mqs.Laptime  AS laptime,
        mqs.SEG_1    AS seg_1,
        mqs.SEG_2    AS seg_2,
        mqs.SEG_3    AS seg_3,
        mqs.SEG_4    AS seg_4,
        mqs.SEG_5    AS seg_5,
        mqs.SEG_6    AS seg_6,
        mqs.SEG_7    AS seg_7,
        mqs.SEG_8    AS seg_8,
        mqs.SEG_9    AS seg_9,
        mqs.SEG_10   AS seg_10
    """

    rows = fetch_all(f"""
        SELECT
            {query_columns}
        FROM dbo.MX_QUAL_SESSIONS mqs
        WHERE mqs.raceid = :raceid
          AND mqs.classid = :classid
          AND mqs.riderid = :riderid
          AND mqs.sportid = 2
        ORDER BY mqs.[Group], mqs.[Session], mqs.Lap
    """, params)

    rank_rows = fetch_all(f"""
        SELECT
            {query_columns}
        FROM dbo.MX_QUAL_SESSIONS mqs
        WHERE mqs.raceid = :raceid
          AND mqs.classid = :classid
          AND mqs.sportid = 2
    """, params)

    return _build_qualifying_session_detail(rows, rank_rows, riderid)


@router.get("/api/race/sx-qualifying-rider-details")
def get_sx_qualifying_rider_details(raceid: int, classid: int, riderid: int):
    params = {
        "raceid": raceid,
        "classid": classid,
        "riderid": riderid,
    }
    query_columns = """
        sqs.[Group]  AS [group],
        sqs.[Session] AS session,
        sqs.Lap      AS lap,
        sqs.riderid  AS riderid,
        sqs.Laptime  AS laptime,
        sqs.SEG_1    AS seg_1,
        sqs.SEG_2    AS seg_2,
        sqs.SEG_3    AS seg_3,
        sqs.SEG_4    AS seg_4,
        sqs.SEG_5    AS seg_5,
        sqs.SEG_6    AS seg_6,
        sqs.SEG_7    AS seg_7,
        sqs.SEG_8    AS seg_8,
        sqs.SEG_9    AS seg_9,
        sqs.SEG_10   AS seg_10
    """

    rows = fetch_all(f"""
        SELECT
            {query_columns}
        FROM dbo.SX_QUAL_SESSIONS sqs
        WHERE sqs.raceid = :raceid
          AND sqs.classid = :classid
          AND sqs.riderid = :riderid
          AND sqs.sportid = 1
        ORDER BY sqs.[Group], sqs.[Session], sqs.Lap
    """, params)

    rank_rows = fetch_all(f"""
        SELECT
            {query_columns}
        FROM dbo.SX_QUAL_SESSIONS sqs
        WHERE sqs.raceid = :raceid
          AND sqs.classid = :classid
          AND sqs.sportid = 1
    """, params)

    return _build_qualifying_session_detail(rows, rank_rows, riderid)


@router.get("/api/race/main-event")
def get_supercross_main_event(raceid: int):
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
            rl.ImageURL            AS imageurl,
            rl.Country             AS country
        FROM SX_MAINS sx
        LEFT JOIN Rider_List rl
            ON rl.RiderID = sx.RiderID
        WHERE sx.RaceID = :raceid
        ORDER BY ClassID, CASE WHEN sx.Result IS NULL THEN 1 ELSE 0 END, sx.Result
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


@router.get("/api/race/triple-crown-mains")
def get_supercross_triple_crown_mains(raceid: int):
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
            rl.ImageURL            AS imageurl,
            rl.Country             AS country
        FROM TC_MAINS tc
        LEFT JOIN Rider_List rl
            ON rl.RiderID = tc.RiderID
        WHERE tc.raceid = :raceid
        ORDER BY tc.classid, tc.main, CASE WHEN tc.Result IS NULL THEN 1 ELSE 0 END, tc.Result
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


@router.get("/api/race/main-event-rider-details")
def get_supercross_main_event_rider_details(
    raceid: int,
    classid: int,
    riderid: int,
    tcmain: int | None = None,
):
    tcmain_filter = "AND sms.TCmain = :tcmain" if tcmain is not None else "AND sms.TCmain IS NULL"
    query = f"""
        SELECT
            sms.LAP      AS lap,
            sms.riderid  AS riderid,
            sms.LAPTIME  AS laptime,
            sms.position AS position,
            sms.SEG_1    AS seg_1,
            sms.SEG_2    AS seg_2,
            sms.SEG_3    AS seg_3,
            sms.SEG_4    AS seg_4,
            sms.SEG_5    AS seg_5,
            sms.SEG_6    AS seg_6,
            sms.SEG_7    AS seg_7,
            sms.SEG_8    AS seg_8,
            sms.SEG_9    AS seg_9,
            sms.SEG_10   AS seg_10
        FROM dbo.SX_MAIN_SEGMENTS sms
        WHERE sms.raceid = :raceid
          AND sms.classid = :classid
          AND sms.riderid = :riderid
          AND sms.sportid = 1
          {tcmain_filter}
        ORDER BY sms.LAP
    """

    params = {
        "raceid": raceid,
        "classid": classid,
        "riderid": riderid,
    }
    if tcmain is not None:
        params["tcmain"] = tcmain

    rows = fetch_all(query, params)
    rank_rows = fetch_all(f"""
        SELECT
            sms.LAP     AS lap,
            sms.riderid AS riderid,
            sms.LAPTIME AS laptime,
            sms.SEG_1   AS seg_1,
            sms.SEG_2   AS seg_2,
            sms.SEG_3   AS seg_3,
            sms.SEG_4   AS seg_4,
            sms.SEG_5   AS seg_5,
            sms.SEG_6   AS seg_6,
            sms.SEG_7   AS seg_7,
            sms.SEG_8   AS seg_8,
            sms.SEG_9   AS seg_9,
            sms.SEG_10  AS seg_10
        FROM dbo.SX_MAIN_SEGMENTS sms
        WHERE sms.raceid = :raceid
          AND sms.classid = :classid
          AND sms.sportid = 1
          {tcmain_filter}
    """, params)

    return _build_lap_segment_detail(rows, rank_rows, riderid)


@router.get("/api/race/heats")
def get_supercross_heats(raceid: int, classid: int):
    query = """
        SELECT
            sxh.Heat        AS Heat,
            sxh.Result      AS result,
            sxh.riderid     AS riderid,
            COALESCE(rl.FullName, sxh.FullName) AS fullname,
            sxh.Brand       AS brand,
            sxh.RiderCoastID AS ridercoastid,
            sxh.coastid     AS coastid,
            rl.ImageURL     AS imageurl,
            rl.Country      AS country
        FROM SX_HEATS sxh
        LEFT JOIN Rider_List rl
            ON rl.RiderID = sxh.RiderID
        WHERE sxh.RaceID = :raceid
          AND sxh.ClassID = :classid
        ORDER BY sxh.Heat, CASE WHEN sxh.Result IS NULL THEN 1 ELSE 0 END, sxh.Result
    """

    rows = fetch_all(query, {"raceid": raceid, "classid": classid})

    heats = {}

    for row in rows:
        heat_num = row["Heat"]
        heats.setdefault(heat_num, []).append(row)

    return heats


@router.get("/api/race/mx-classes")
def get_mx_classes(raceid: int, sport_id: int = 2):
    result_table = "SMX_OVERALLS" if sport_id == 3 else "MX_OVERALLS"
    query = f"""
        SELECT DISTINCT ClassID
        FROM {result_table}
        WHERE RaceID = :raceid
        ORDER BY ClassID
    """

    return fetch_all(query, {"raceid": raceid})
