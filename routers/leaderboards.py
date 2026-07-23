from typing import List

import pyodbc
from fastapi import APIRouter, Query

from db import CONN_STR
from error_utils import raise_http_error


router = APIRouter()


@router.get("/leaderboard1")
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

    smx_query = f"""
        SELECT
    m.RiderID AS riderid,
    rl.FullName AS fullname,
    COUNT(*) AS wins
FROM SMX_OVERALLS m
JOIN Rider_List rl
    ON rl.RiderID = m.RiderID
WHERE m.Result = 1
  AND m.ClassID IN ({placeholders})
GROUP BY
    m.RiderID,
    rl.FullName
ORDER BY wins DESC;
    """

    wmx_query = """
        SELECT
            w.riderid AS riderid,
            rl.FullName AS fullname,
            COUNT(*) AS wins
        FROM WMX_OVERALLS w
        JOIN Rider_List rl ON rl.RiderID = w.riderid
        WHERE w.Result = 1
        GROUP BY w.riderid, rl.FullName
        ORDER BY wins DESC, rl.FullName;
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

            cursor.execute(smx_query, class_ids)
            smx = [
                {"riderid": row.riderid, "fullname": row.fullname, "wins": row.wins}
                for row in cursor.fetchall()
            ]

            cursor.execute(wmx_query)
            wmx = [
                {"riderid": row.riderid, "fullname": row.fullname, "wins": row.wins}
                for row in cursor.fetchall()
            ]

        return {"supercross": supercross, "motocross": motocross, "smx": smx, "wmx": wmx}

    except Exception as e:
        raise_http_error("Failed to load wins leaderboard.", e)


@router.get("/leaderboard2")
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

    smx_query = f"""
        SELECT
    m.RiderID AS riderid,
    rl.FullName AS fullname,
    COUNT(*) AS podiums
FROM SMX_OVERALLS m
JOIN Rider_List rl
    ON rl.RiderID = m.RiderID
WHERE m.Result <= 3
  AND m.ClassID IN ({placeholders})
GROUP BY
    m.RiderID,
    rl.FullName
ORDER BY podiums DESC;
    """

    wmx_query = """
        SELECT
            w.riderid AS riderid,
            rl.FullName AS fullname,
            COUNT(*) AS podiums
        FROM WMX_OVERALLS w
        JOIN Rider_List rl ON rl.RiderID = w.riderid
        WHERE w.Result <= 3
        GROUP BY w.riderid, rl.FullName
        ORDER BY podiums DESC, rl.FullName;
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

            cursor.execute(smx_query, class_ids)
            smx = [
                {"riderid": row.riderid, "fullname": row.fullname, "podiums": row.podiums}
                for row in cursor.fetchall()
            ]

            cursor.execute(wmx_query)
            wmx = [
                {"riderid": row.riderid, "fullname": row.fullname, "podiums": row.podiums}
                for row in cursor.fetchall()
            ]

        return {"supercross": supercross, "motocross": motocross, "smx": smx, "wmx": wmx}

    except Exception as e:
        raise_http_error("Failed to load podiums leaderboard.", e)


@router.get("/leaderboard3")
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

    smx_query = f"""
        SELECT
    m.RiderID AS riderid,
    rl.FullName AS fullname,
    COUNT(*) AS starts
FROM SMX_OVERALLS m
JOIN Rider_List rl
    ON rl.RiderID = m.RiderID
WHERE m.ClassID IN ({placeholders})
GROUP BY
    m.RiderID,
    rl.FullName
ORDER BY starts DESC;
    """

    wmx_query = """
        SELECT
            w.riderid AS riderid,
            rl.FullName AS fullname,
            COUNT(*) AS starts
        FROM WMX_OVERALLS w
        JOIN Rider_List rl ON rl.RiderID = w.riderid
        GROUP BY w.riderid, rl.FullName
        ORDER BY starts DESC, rl.FullName;
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

            cursor.execute(smx_query, class_ids)
            smx = [
                {"riderid": row.riderid, "fullname": row.fullname, "starts": row.starts}
                for row in cursor.fetchall()
            ]

            cursor.execute(wmx_query)
            wmx = [
                {"riderid": row.riderid, "fullname": row.fullname, "starts": row.starts}
                for row in cursor.fetchall()
            ]

        return {"supercross": supercross, "motocross": motocross, "smx": smx, "wmx": wmx}

    except Exception as e:
        raise_http_error("Failed to load starts leaderboard.", e)


@router.get("/leaderboard4")
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

    smx_query = f"""
        SELECT
    m.RiderID AS riderid,
    rl.FullName AS fullname,
    COUNT(*) AS moto_wins
FROM SMX_MOTOS m
JOIN Rider_List rl
    ON rl.RiderID = m.RiderID
WHERE m.Result = 1
  AND m.ClassID IN ({placeholders})
GROUP BY
    m.RiderID,
    rl.FullName
ORDER BY moto_wins DESC;
    """

    wmx_query = """
        SELECT
            c.[Year] AS [year],
            c.RiderID AS riderid,
            COALESCE(rl.FullName, c.FullName) AS fullname
        FROM Champions c
        LEFT JOIN Rider_List rl ON rl.RiderID = c.RiderID
        WHERE c.SportID = 4
        ORDER BY c.[Year] DESC, fullname;
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

            cursor.execute(smx_query, class_ids)
            smx = [
                {"riderid": row.riderid, "fullname": row.fullname, "moto_wins": row.moto_wins}
                for row in cursor.fetchall()
            ]

            cursor.execute(wmx_query)
            wmx = [
                {"year": row.year, "riderid": row.riderid, "fullname": row.fullname}
                for row in cursor.fetchall()
            ]

        return {"supercross": supercross, "motocross": motocross, "smx": smx, "wmx": wmx}

    except Exception as e:
        raise_http_error("Failed to load heat and moto wins leaderboard.", e)
