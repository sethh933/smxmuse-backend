from secrets import compare_digest
from typing import Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from fastapi import APIRouter, Header, HTTPException

from db import ADMIN_REFRESH_TOKEN, GRID_CACHE_REFRESH_URL
from scripts.refresh_rider_profile_summaries import refresh_rider_profile_summaries


router = APIRouter()


def _require_admin_token(x_admin_token: Optional[str]):
    if not ADMIN_REFRESH_TOKEN:
        raise HTTPException(
            status_code=500,
            detail="Admin refresh token is not configured.",
        )

    if not x_admin_token or not compare_digest(x_admin_token, ADMIN_REFRESH_TOKEN):
        raise HTTPException(status_code=401, detail="Invalid admin token.")


def _post_grid_cache_refresh():
    if not GRID_CACHE_REFRESH_URL:
        return {"triggered": False, "message": "GRID_CACHE_REFRESH_URL not configured."}

    request = Request(GRID_CACHE_REFRESH_URL, method="POST")
    with urlopen(request, timeout=30) as response:
        body = response.read().decode("utf-8", errors="replace")

    return {
        "triggered": True,
        "status_code": getattr(response, "status", None),
        "body": body[:500],
    }


@router.post("/admin/refresh-caches")
def refresh_caches(x_admin_token: Optional[str] = Header(default=None)):
    _require_admin_token(x_admin_token)

    try:
        refresh_rider_profile_summaries()
        rider_profile = {"refreshed": True}
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Rider profile summary refresh failed.",
                "error": str(exc),
            },
        ) from exc

    try:
        grid_cache = _post_grid_cache_refresh()
    except (HTTPError, URLError, TimeoutError) as exc:
        raise HTTPException(
            status_code=502,
            detail={
                "message": "Rider profile summary refresh succeeded, but grid cache refresh failed.",
                "rider_profile": rider_profile,
                "grid_cache_error": str(exc),
            },
        ) from exc

    return {
        "message": "Refresh completed successfully.",
        "rider_profile": rider_profile,
        "grid_cache": grid_cache,
    }
