import logging

from fastapi import HTTPException


logger = logging.getLogger("smxmuse.api")


def raise_http_error(message: str, exc: Exception, status_code: int = 500) -> None:
    logger.exception(message, exc_info=exc)
    raise HTTPException(status_code=status_code, detail=message) from exc
