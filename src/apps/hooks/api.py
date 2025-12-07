import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.apps.ms_auth.service import MySkladAuthService, get_ms_auth_service
from src.core.db import get_session

from .schemas import (
    AutoLinkTogglePayload,
    MySkladWebhookPayload,
    WebhookStatusResponse,
)
from .services.webhook_service import WebhookService
from .uow.unit_of_work import UnitOfWork

logger = logging.getLogger(__name__)
 
router = APIRouter()
 
 
async def get_uow(session: AsyncSession = Depends(get_session)) -> UnitOfWork:
    """
    Dependency для получения Unit of Work.
    
    Args:
        session: Асинхронная сессия БД
        
    Returns:
        Экземпляр Unit of Work
    """
    return UnitOfWork(session)


async def get_webhook_service(
    uow: UnitOfWork = Depends(get_uow),
    auth_service: MySkladAuthService = Depends(get_ms_auth_service),
) -> WebhookService:
    """
    Dependency для получения сервиса вебхуков.
    
    Args:
        uow: Unit of Work
        auth_service: Сервис аутентификации МойСклад
        
    Returns:
        Экземпляр сервиса вебхуков
    """
    return WebhookService(uow=uow, auth_service=auth_service)


@router.get("/webhooks/status", response_model=WebhookStatusResponse)
async def get_webhooks_status(service: WebhookService = Depends(get_webhook_service),):
    """
    Получить текущее состояние всех вебхуков.
    
    Returns:
        Статус всех вебхуков
    """
    status_dict = await service.get_webhooks_status()
    return WebhookStatusResponse(webhooks=status_dict)


@router.post("/auto-link-toggle")
async def auto_link_toggle(payload: AutoLinkTogglePayload, service: WebhookService = Depends(get_webhook_service),):
    """
    Переключить автоматическую привязку платежей.
    
    Args:
        payload: Данные для переключения
        service: Сервис вебхуков
        
    Returns:
        Результат операции
        
    Raises:
        HTTPException: При ошибке выполнения
    """
    logger.info(
        "UI toggle: payment_type=%s, enabled=%s",
        payload.payment_type,
        payload.enabled,
    )

    try:
        result = await service.toggle_webhook(
            payment_type=payload.payment_type,
            enabled=payload.enabled,
        )
    except Exception as exc:
        logger.exception("Ошибка при синхронизации вебхука")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при переключении вебхука: {str(exc)}",
        ) from exc
   
    if result.is_skipped():
        return {
            "status": "warning",
            "payment_type": payload.payment_type,
            "enabled": payload.enabled,
            "operation": result.operation,
            "message": result.message or "Операция пропущена",
        }
   
    if result.is_error():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.error or "Unknown error",
        )

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
    """
    Принять входящий вебхук от МойСклад.
    
    Args:
        payload: Данные вебхука
        request_id: ID запроса
        
    Returns:
        204 No Content
        
    Raises:
        HTTPException: Если requestId отсутствует
    """
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
