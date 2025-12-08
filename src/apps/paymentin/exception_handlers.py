"""Обработчики исключений для paymentin."""

import logging

from fastapi import Request, status
from fastapi.responses import JSONResponse

from .exceptions import (
    PaymentInAPIError,
    PaymentInBaseException,
    PaymentInNotFoundError,
)

logger = logging.getLogger(__name__)


async def paymentin_not_found_handler(
    request: Request,
    exc: PaymentInNotFoundError,
) -> JSONResponse:
    """Обработчик для PaymentInNotFoundError."""
    logger.warning("PaymentInNotFoundError: %s", exc.message)
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            "detail": exc.message,
            "error_type": "PaymentInNotFoundError",
            "details": exc.details,
        },
    )


async def paymentin_api_error_handler(
    request: Request,
    exc: PaymentInAPIError,
) -> JSONResponse:
    """Обработчик для PaymentInAPIError."""
    logger.error("PaymentInAPIError: %s, details=%s", exc.message, exc.details)
    return JSONResponse(
        status_code=status.HTTP_502_BAD_GATEWAY,
        content={
            "detail": f"Ошибка API МойСклад: {exc.message}",
            "error_type": "PaymentInAPIError",
            "details": exc.details,
        },
    )


async def paymentin_base_exception_handler(
    request: Request,
    exc: PaymentInBaseException,
) -> JSONResponse:
    """Обработчик для PaymentInBaseException."""
    logger.error(
        "PaymentInBaseException: %s, details=%s",
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
    PaymentInNotFoundError: paymentin_not_found_handler,
    PaymentInAPIError: paymentin_api_error_handler,
    PaymentInBaseException: paymentin_base_exception_handler,
}