import logging

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from src.apps.ms_auth.service import MySkladAuthService, get_ms_auth_service
from src.core.db import get_session

from .repository import upsert_webhook_subscription
from .schemas import AutoLinkTogglePayload, MySkladWebhookPayload
from .service import WebhookService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/auto-link-toggle")
async def auto_link_toggle(
    payload: AutoLinkTogglePayload,
    auth_service: MySkladAuthService = Depends(get_ms_auth_service),
    session: AsyncSession = Depends(get_session),
):
    """
    Обработчик чекбокса "Включить привязку к документу".

    - синхронизирует вебхук в МойСклад (создаёт/включает/выключает);
    - сохраняет/обновляет запись о вебхуке в нашей БД.
    """
    logger.info(
        "UI toggle: payment_type=%s, enabled=%s",
        payload.payment_type,
        payload.enabled,
    )

    service = WebhookService(auth_service=auth_service)

    result = await service.sync_webhook_for_toggle(
        payment_type=payload.payment_type,
        enabled=payload.enabled,
    )

    print(f"[result] -->> {result}")

    operation = result.get("operation")
    webhook_data = result.get("webhook")
    db_record = None

    if webhook_data:
        db_record = await upsert_webhook_subscription(
            session=session,
            payment_type=payload.payment_type,
            webhook_data=webhook_data,
        )
        logger.info(
            "Webhook subscription stored: id=%s, ms_webhook_id=%s, enabled=%s",
            db_record.id,
            db_record.ms_webhook_id,
            db_record.enabled,
        )
    else:
        logger.info(
            "No webhook data to store for operation=%s (maybe not found / skipped)",
            operation,
        )

    return {
        "status": "ok",
        "payment_type": payload.payment_type,
        "enabled": payload.enabled,
        "operation": operation,
        "db_record_id": getattr(db_record, "id", None),
    }


# ===== Приём вебхуков от МойСклад =====


@router.post("/moysklad/webhook", status_code=204)
async def receive_moysklad_webhook(
    payload: MySkladWebhookPayload,
    request_id: str | None = Query(default=None, alias="requestId"),
):
    """
    Ручка, которую будет дергать МойСклад при срабатывании вебхука.
    """
    logger.info(
        "Received MoySklad webhook: requestId=%s, events_count=%d, uid=%s, moment=%s",
        request_id,
        len(payload.events),
        payload.auditContext.uid,
        payload.auditContext.moment,
    )

    for event in payload.events:
        logger.info(
            "Webhook event: type=%s, action=%s, href=%s, accountId=%s, updatedFields=%s",
            event.meta.type,
            event.action,
            event.meta.href,
            event.accountId,
            event.updatedFields,
        )

    return Response(status_code=204)
