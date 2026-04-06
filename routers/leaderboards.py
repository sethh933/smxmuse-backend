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
        raise_http_error("Failed to load heat and moto wins leaderboard.", e)
