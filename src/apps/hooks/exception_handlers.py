import logging

from fastapi import Request, status
from fastapi.responses import JSONResponse

from .exceptions import (
    HooksBaseException,
    MissingRequestIdError,
    MoySkladAPIError,
    RepositoryError,
    WebhookAlreadyExistsError,
    WebhookConfigurationError,
    WebhookNotFoundError,
)

logger = logging.getLogger(__name__)


async def hooks_base_exception_handler(
    request: Request,
    exc: HooksBaseException,
) -> JSONResponse:
    logger.error(
        "HooksBaseException: %s, details=%s",
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


async def webhook_not_found_handler(
    request: Request,
    exc: WebhookNotFoundError,
) -> JSONResponse:
    logger.warning("WebhookNotFoundError: %s", exc.message)
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            "detail": exc.message,
            "error_type": "WebhookNotFoundError",
            "details": exc.details,
        },
    )


async def webhook_already_exists_handler(
    request: Request,
    exc: WebhookAlreadyExistsError,
) -> JSONResponse:
    logger.warning("WebhookAlreadyExistsError: %s", exc.message)
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={
            "detail": exc.message,
            "error_type": "WebhookAlreadyExistsError",
            "details": exc.details,
        },
    )


async def webhook_configuration_error_handler(
    request: Request,
    exc: WebhookConfigurationError,
) -> JSONResponse:
    logger.error("WebhookConfigurationError: %s", exc.message)
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "detail": exc.message,
            "error_type": "WebhookConfigurationError",
            "details": exc.details,
        },
    )


async def moysklad_api_error_handler(
    request: Request,
    exc: MoySkladAPIError,
) -> JSONResponse:
    logger.error("MoySkladAPIError: %s, details=%s", exc.message, exc.details)
    return JSONResponse(
        status_code=status.HTTP_502_BAD_GATEWAY,
        content={
            "detail": f"Ошибка взаимодействия с МойСклад: {exc.message}",
            "error_type": "MoySkladAPIError",
            "details": exc.details,
        },
    )


async def repository_error_handler(
    request: Request,
    exc: RepositoryError,
) -> JSONResponse:
    logger.error("RepositoryError: %s, details=%s", exc.message, exc.details)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": f"Ошибка работы с БД: {exc.message}",
            "error_type": "RepositoryError",
            "details": exc.details,
        },
    )

async def missing_request_id_handler(
    request: Request,
    exc: MissingRequestIdError,
) -> JSONResponse:
    logger.warning("MissingRequestIdError: %s", exc.message)
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "detail": exc.message,
            "error_type": "MissingRequestIdError",
        },
    )


EXCEPTION_HANDLERS = {
    MissingRequestIdError: missing_request_id_handler,
    WebhookNotFoundError: webhook_not_found_handler,
    WebhookAlreadyExistsError: webhook_already_exists_handler,
    WebhookConfigurationError: webhook_configuration_error_handler,
    MoySkladAPIError: moysklad_api_error_handler,
    RepositoryError: repository_error_handler,
    HooksBaseException: hooks_base_exception_handler,
}