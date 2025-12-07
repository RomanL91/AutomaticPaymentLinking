import logging

from fastapi import APIRouter, HTTPException, Query, Response, status

from .dependencies import WebhookSvcDep
from .schemas import (
    AutoLinkTogglePayload,
    MySkladWebhookPayload,
    UpdateLinkSettingsPayload,
    WebhookStatusResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/webhooks/status", response_model=WebhookStatusResponse)
async def get_webhooks_status(service: WebhookSvcDep):
    status_dict = await service.get_webhooks_status()
    return WebhookStatusResponse(webhooks=status_dict)


@router.post("/update-link-settings")
async def update_link_settings(
    payload: UpdateLinkSettingsPayload,
    service: WebhookSvcDep,
):
    logger.info(
        "Обновление настроек привязки: payment_type=%s, document_type=%s, link_type=%s",
        payload.payment_type,
        payload.document_type,
        payload.link_type,
    )
    
    result = await service.update_link_settings(
        payment_type=payload.payment_type,
        document_type=payload.document_type,
        link_type=payload.link_type,
    )
    
    return result


@router.post("/auto-link-toggle")
async def auto_link_toggle(payload: AutoLinkTogglePayload, service: WebhookSvcDep):
    logger.info(
        "UI toggle: payment_type=%s, enabled=%s, document_type=%s, link_type=%s",
        payload.payment_type,
        payload.enabled,
        payload.document_type,
        payload.link_type,
    )

    result = await service.toggle_webhook(
        payment_type=payload.payment_type,
        enabled=payload.enabled,
        document_type=payload.document_type,
        link_type=payload.link_type,
    )
   
    if result.is_skipped():
        return {
            "status": "warning",
            "payment_type": payload.payment_type,
            "enabled": payload.enabled,
            "operation": result.operation,
            "message": result.message or "Операция пропущена",
        }

    return {
        "status": "ok",
        "payment_type": payload.payment_type,
        "enabled": payload.enabled,
        "operation": result.operation,
        "db_record_id": result.details.get("db_record_id"),
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

    return Response(status_code=204)