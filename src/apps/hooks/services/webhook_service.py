"""Основной сервис для работы с вебхуками."""

import logging
from typing import Dict

from src.core.config import settings

from ...ms_auth.services.auth_service import MySkladAuthService
from ..domain.entities import WebhookOperationResult
from ..domain.value_objects import WebhookConfiguration
from ..schemas import DocumentType, LinkType, PaymentType, WebhookStatusItem
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
    
    async def get_webhooks_status(self) -> Dict[str, WebhookStatusItem]:
        """
        Получить статус всех вебхуков с настройками.
        
        Returns:
            Словарь {payment_type: WebhookStatusItem}
        """
        full_status = await self._uow.webhooks.get_full_status_dict()
        
        result = {}
        for payment_type, data in full_status.items():
            result[payment_type] = WebhookStatusItem(
                enabled=data["enabled"],
                document_type=DocumentType(data["document_type"]),
                link_type=LinkType(data["link_type"]),
            )
        
        logger.debug("Статус вебхуков: %s", result)
        return result
    
    async def update_link_settings(
        self,
        payment_type: PaymentType,
        document_type: DocumentType,
        link_type: LinkType,
    ) -> Dict[str, str]:
        """
        Обновить настройки привязки БЕЗ обращения к МойСклад API.
        
        Args:
            payment_type: Тип платежа
            document_type: Тип документа
            link_type: Тип привязки
            
        Returns:
            Результат операции
        """
        updated = await self._uow.webhooks.update_link_settings(
            payment_type=payment_type,
            document_type=document_type,
            link_type=link_type,
        )
        
        if not updated:
            logger.warning(
                "Вебхук %s не найден для обновления настроек",
                payment_type.value,
            )
            return {
                "status": "warning",
                "message": f"Вебхук {payment_type.value} не найден. Включите его сначала.",
            }
        
        await self._uow.commit()
        
        logger.info(
            "Настройки привязки обновлены: payment_type=%s, document_type=%s, link_type=%s",
            payment_type.value,
            document_type.value,
            link_type.value,
        )
        
        return {
            "status": "ok",
            "payment_type": payment_type.value,
            "document_type": document_type.value,
            "link_type": link_type.value,
        }
    
    async def toggle_webhook(
        self,
        payment_type: PaymentType,
        enabled: bool,
        document_type: DocumentType = DocumentType.customerorder,
        link_type: LinkType = LinkType.sum_and_counterparty,
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
        
        config = WebhookConfiguration.from_payment_type(
            payment_type=payment_type,
            webhook_url=webhook_url,
        )
        
        operation = WebhookOperationFactory.create_operation(
            enabled=enabled,
            client=self._client,
            config=config,
        )
        
        result = await operation.execute()
        
        if result.success and result.webhook_entity:
            result.webhook_entity.payment_type = payment_type
            result.webhook_entity.document_type = document_type
            result.webhook_entity.link_type = link_type
            saved_entity = await self._uow.webhooks.upsert(result.webhook_entity)
            await self._uow.commit()
            
            logger.info(
                "Webhook сохранен в БД: id=%s, ms_webhook_id=%s, enabled=%s, document_type=%s, link_type=%s",
                saved_entity.id,
                saved_entity.ms_webhook_id,
                saved_entity.enabled,
                saved_entity.document_type.value,
                saved_entity.link_type.value,
            )
            
            result.details["db_record_id"] = saved_entity.id
        
        return result