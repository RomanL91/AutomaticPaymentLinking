"""Сервис для работы с входящими платежами."""

import logging

from ...ms_auth.services.auth_service import MySkladAuthService
from ..domain.entities import PaymentInEntity
from .paymentin_client import PaymentInClient

logger = logging.getLogger(__name__)


class PaymentInService:
    """Сервис для работы с входящими платежами."""
    
    def __init__(self, auth_service: MySkladAuthService) -> None:
        self._auth_service = auth_service
        self._client = PaymentInClient(auth_service)
    
    async def get_by_href(self, href: str) -> PaymentInEntity:
        """Получить платеж по href."""
        data = await self._client.get_by_href(href)
        return self._to_entity(data)
    
    async def link_to_document(
        self, payment_id: str, document_meta_href: str, linked_sum: float
    ) -> PaymentInEntity:
        """Привязать платеж к документу."""
        # Сначала получаем текущий платеж
        payment_data = await self._client.get_by_href(
            f"{self._client._get_base_url()}/entity/paymentin/{payment_id}"
        )
        payment = self._to_entity(payment_data)
        
        # Собираем существующие связи
        operations = [
            {"meta": op["meta"], "linkedSum": op.get("linkedSum", 0)}
            for op in payment.linked_operations
        ]
        
        # Добавляем новую связь
        operations.append({
            "meta": {
                "href": document_meta_href,
                "type": self._extract_type_from_href(document_meta_href),
                "mediaType": "application/json",
            },
            "linkedSum": linked_sum,
        })
        
        # Обновляем платеж
        updated_data = await self._client.update_operations(payment_id, operations)
        return self._to_entity(updated_data)
    
    @staticmethod
    def _to_entity(data: dict) -> PaymentInEntity:
        """Преобразовать данные API в доменную сущность."""
        agent_meta = data.get("agent", {}).get("meta", {})
        agent_href = agent_meta.get("href", "")
        agent_id = agent_href.split("/")[-1] if agent_href else ""
        
        org_meta = data.get("organization", {}).get("meta", {})
        org_href = org_meta.get("href", "")
        org_id = org_href.split("/")[-1] if org_href else ""
        
        linked_ops = [
            {
                "meta": {
                    "href": op.get("meta", {}).get("href", ""),
                    "type": op.get("meta", {}).get("type", ""),
                },
                "linkedSum": op.get("linkedSum", 0),
            }
            for op in data.get("operations", [])
        ]
        
        return PaymentInEntity(
            id=data["id"],
            account_id=data["accountId"],
            name=data["name"],
            moment=data["moment"],
            applicable=data["applicable"],
            sum=data["sum"],
            agent_id=agent_id,
            organization_id=org_id,
            payment_purpose=data.get("paymentPurpose"),
            linked_operations=linked_ops,
            meta_href=data["meta"]["href"],
        )
    
    @staticmethod
    def _extract_type_from_href(href: str) -> str:
        """Извлечь тип документа из href."""
        parts = href.split("/")
        return parts[-2] if len(parts) >= 2 else "unknown"