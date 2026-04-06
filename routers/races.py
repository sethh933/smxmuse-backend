import pyodbc
from fastapi import APIRouter

from db import CONN_STR, fetch_all
from error_utils import raise_http_error


router = APIRouter()


@router.get("/api/race/overalls")
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


@router.get("/api/race/consi")
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


@router.get("/api/race/lcqs")
def get_supercross_lcqs(raceid: int, classid: int):
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
        raise_http_error("Failed to load race qualifying results.", e)


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


@router.get("/api/race/mx-classes")
def get_mx_classes(raceid: int):
    query = """
        SELECT DISTINCT ClassID
        FROM MX_OVERALLS
        WHERE RaceID = :raceid
        ORDER BY ClassID
    """

    return fetch_all(query, {"raceid": raceid})
