"""Обработчики исключений для customerorder."""

import logging

from fastapi import Request, status
from fastapi.responses import JSONResponse

from .exceptions import (
    CustomerOrderAPIError,
    CustomerOrderBaseException,
    CustomerOrderNotFoundError,
)

logger = logging.getLogger(__name__)


async def customerorder_not_found_handler(
    request: Request,
    exc: CustomerOrderNotFoundError,
) -> JSONResponse:
    """Обработчик для CustomerOrderNotFoundError."""
    logger.warning("CustomerOrderNotFoundError: %s", exc.message)
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            "detail": exc.message,
            "error_type": "CustomerOrderNotFoundError",
            "details": exc.details,
        },
    )


async def customerorder_api_error_handler(
    request: Request,
    exc: CustomerOrderAPIError,
) -> JSONResponse:
    """Обработчик для CustomerOrderAPIError."""
    logger.error("CustomerOrderAPIError: %s, details=%s", exc.message, exc.details)
    return JSONResponse(
        status_code=status.HTTP_502_BAD_GATEWAY,
        content={
            "detail": f"Ошибка API МойСклад: {exc.message}",
            "error_type": "CustomerOrderAPIError",
            "details": exc.details,
        },
    )


async def customerorder_base_exception_handler(
    request: Request,
    exc: CustomerOrderBaseException,
) -> JSONResponse:
    """Обработчик для CustomerOrderBaseException."""
    logger.error(
        "CustomerOrderBaseException: %s, details=%s",
        exc.message,
        exc.details,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": exc.message,
            "error_type": exc.__class__.__name__,
            "details": exc.details,
        },
    )


EXCEPTION_HANDLERS = {
    CustomerOrderNotFoundError: customerorder_not_found_handler,
    CustomerOrderAPIError: customerorder_api_error_handler,
    CustomerOrderBaseException: customerorder_base_exception_handler,
}