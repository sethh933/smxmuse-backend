from urllib.parse import urlparse
from urllib.request import Request, urlopen

from fastapi import APIRouter, HTTPException, Response

from db import engine


router = APIRouter()


@router.get("/api/search")
def search(q: str):
    like = f"%{q}%"
    starts = f"{q}%"

    riders_query = """
        SELECT TOP 8 RiderID, FullName, Country
        FROM Rider_List
        WHERE FullName LIKE ?
        ORDER BY
            CASE WHEN FullName LIKE ? THEN 0 ELSE 1 END,
            FullName
    """

    tracks_query = """
    SELECT TOP 8
        rt.TrackID,
        rt.TrackName,
        tt.State,
        rt.SportID
    FROM Race_Table rt
    JOIN TrackTable tt
        ON rt.TrackID = tt.TrackID
    WHERE rt.TrackName LIKE ?
      AND rt.SportID IN (1, 2)
    GROUP BY
        rt.TrackID,
        rt.TrackName,
        tt.State,
        rt.SportID
    ORDER BY
        CASE WHEN rt.TrackName LIKE ? THEN 0 ELSE 1 END,
        rt.TrackName
    """

    with engine.connect() as conn:
        riders = conn.exec_driver_sql(riders_query, (like, starts)).mappings().all()
        tracks = conn.exec_driver_sql(tracks_query, (like, starts)).mappings().all()

    return {
        "riders": [dict(r) for r in riders],
        "tracks": [dict(t) for t in tracks],
    }


@router.get("/api/image-proxy")
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
