import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.apps.ms_auth.service import MySkladAuthService, get_ms_auth_service
from src.core.db import get_session

from .repository import get_webhook_status, upsert_webhook_subscription
from .schemas import AutoLinkTogglePayload, MySkladWebhookPayload, WebhookStatusResponse
from .service import WebhookService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/webhooks/status", response_model=WebhookStatusResponse)
async def get_webhooks_status(
    session: AsyncSession = Depends(get_session),
):
    """
    Получить текущее состояние всех вебхуков (включено/выключено).
    """
    status_dict = await get_webhook_status(session)
    logger.debug("Webhook status retrieved: %s", status_dict)
    return WebhookStatusResponse(webhooks=status_dict)


@router.post("/auto-link-toggle")
async def auto_link_toggle(
    payload: AutoLinkTogglePayload,
    auth_service: MySkladAuthService = Depends(get_ms_auth_service),
    session: AsyncSession = Depends(get_session),
):
    logger.info(
        "UI toggle: payment_type=%s, enabled=%s",
        payload.payment_type,
        payload.enabled,
    )

    service = WebhookService(auth_service=auth_service)

    try:
        result = await service.sync_webhook_for_toggle(
            payment_type=payload.payment_type,
            enabled=payload.enabled,
        )
    except Exception as exc:
        logger.exception("Ошибка при синхронизации вебхука")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка синхронизации вебхука: {str(exc)}",
        )

    logger.debug("Результат синхронизации: %s", result)

    operation = result.get("operation")
    webhook_data = result.get("webhook")
    db_record = None

    # Операции пропуска (не ошибки) - возвращаем 200 с пояснением
    if operation in ("skipped_no_webhook_url", "skipped_no_credentials"):
        return {
            "status": "warning",
            "payment_type": payload.payment_type,
            "enabled": payload.enabled,
            "operation": operation,
            "message": result.get("reason", "Операция пропущена"),
        }

    # Реальные ошибки - возвращаем 500
    if operation in ("error_fetching", "error_creating", "error_enabling", "error_disabling"):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.get("error", "Unknown error"),
        )

    if webhook_data:
        try:
            db_record = await upsert_webhook_subscription(
                session=session,
                payment_type=payload.payment_type,
                webhook_data=webhook_data,
            )
            logger.info(
                "Webhook subscription сохранен: id=%s, ms_webhook_id=%s, enabled=%s",
                db_record.id,
                db_record.ms_webhook_id,
                db_record.enabled,
            )
        except Exception as exc:
            logger.exception("Ошибка при сохранении вебхука в БД")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Ошибка сохранения в БД: {str(exc)}",
            )
    else:
        logger.info(
            "Нет данных вебхука для сохранения: operation=%s",
            operation,
        )

    return {
        "status": "ok",
        "payment_type": payload.payment_type,
        "enabled": payload.enabled,
        "operation": operation,
        "db_record_id": getattr(db_record, "id", None),
    }


@router.post("/moysklad/webhook", status_code=204)
async def receive_moysklad_webhook(
    payload: MySkladWebhookPayload,
    request_id: str | None = Query(default=None, alias="requestId"),
):
    if not request_id:
        logger.warning("Получен вебхук без requestId")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="requestId обязателен",
        )

    logger.info(
        "Получен вебхук МойСклад: requestId=%s, events=%d, uid=%s, moment=%s",
        request_id,
        len(payload.events),
        payload.auditContext.uid,
        payload.auditContext.moment,
    )

    for event in payload.events:
        logger.info(
            "Событие вебхука: type=%s, action=%s, href=%s, accountId=%s, updatedFields=%s",
            event.meta.type,
            event.action,
            event.meta.href,
            event.accountId,
            event.updatedFields,
        )

    # TODO: Реализовать обработку событий (поиск и привязка документов)

    return Response(status_code=204)