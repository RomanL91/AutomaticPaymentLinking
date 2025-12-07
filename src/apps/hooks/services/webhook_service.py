"""Основной сервис для работы с вебхуками."""

import logging
from typing import Dict

from src.core.config import settings

from ...ms_auth.services.auth_service import MySkladAuthService
from ..domain.entities import WebhookOperationResult
from ..domain.value_objects import WebhookConfiguration
from ..schemas import PaymentType
from ..uow.unit_of_work import UnitOfWork
from .moysklad_client import MoySkladClient
from .webhook_operations import WebhookOperationFactory

logger = logging.getLogger(__name__)


class WebhookService:
    """
    Сервис для управления вебхуками.
    
    Координирует работу между API МойСклад и локальной БД.
    """
    
    def __init__(
        self,
        uow: UnitOfWork,
        auth_service: MySkladAuthService,
    ) -> None:
        """
        Инициализировать сервис вебхуков.
        
        Args:
            uow: Unit of Work для работы с БД
            auth_service: Сервис аутентификации МойСклад
        """
        self._uow = uow
        self._auth_service = auth_service
        self._client = MoySkladClient(auth_service)
    
    async def get_webhooks_status(self) -> Dict[str, bool]:
        """
        Получить статус всех вебхуков.
        
        Returns:
            Словарь {payment_type: enabled}
        """
        status_dict = await self._uow.webhooks.get_status_dict()
        logger.debug("Статус вебхуков: %s", status_dict)
        return status_dict
    
    async def toggle_webhook(
        self,
        payment_type: PaymentType,
        enabled: bool,
    ) -> WebhookOperationResult:
        webhook_url = settings.ms_webhook_url
        
        if not webhook_url:
            logger.warning("MS_WEBHOOK_URL не задан")
            return WebhookOperationResult(
                operation="skipped_no_webhook_url",
                success=False,
                message=(
                    "Webhook URL не настроен. Запустите ngrok (DEV_docs/start_ngrok.ps1) "
                    "и перезапустите сервер"
                ),
            )
        
        creds = self._auth_service.get_raw_credentials()
        if not creds:
            logger.warning("МойСклад credentials не настроены")
            return WebhookOperationResult(
                operation="skipped_no_credentials",
                success=False,
                message="MoySklad credentials are not configured",
            )
        
        # Создание конфигурации вебхука
        config = WebhookConfiguration.from_payment_type(
            payment_type=payment_type,
            webhook_url=webhook_url,
        )
        
        # Выполнение операции через фабрику (Strategy Pattern)
        operation = WebhookOperationFactory.create_operation(
            enabled=enabled,
            client=self._client,
            config=config,
        )
        
        result = await operation.execute()
        
        # Сохранение в БД при успехе
        if result.success and result.webhook_entity:
            result.webhook_entity.payment_type = payment_type
            saved_entity = await self._uow.webhooks.upsert(result.webhook_entity)
            await self._uow.commit()
            
            logger.info(
                "Webhook сохранен в БД: id=%s, ms_webhook_id=%s, enabled=%s",
                saved_entity.id,
                saved_entity.ms_webhook_id,
                saved_entity.enabled,
            )
            
            result.details["db_record_id"] = saved_entity.id
        
        return result