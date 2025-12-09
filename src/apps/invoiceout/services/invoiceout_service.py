"""Сервис для работы со счетами покупателю."""

import logging
from typing import List

from ...ms_auth.services.auth_service import MySkladAuthService
from ..domain.entities import InvoiceOutEntity
from ..exceptions import InvoiceOutNotFoundError
from .invoiceout_client import InvoiceOutClient

logger = logging.getLogger(__name__)


class InvoiceOutService:
    """Сервис для работы со счетами покупателю."""

    def __init__(self, auth_service: MySkladAuthService) -> None:
        self._auth_service = auth_service
        self._client = InvoiceOutClient(auth_service)

    async def find_for_payment(
        self,
        agent_id: str,
        payment_sum: float,
        search_by_sum: bool = True,
    ) -> List[InvoiceOutEntity]:
        """Найти счета для привязки платежа."""
        if search_by_sum:
            invoices_data = await self._client.search_by_agent_and_sum(
                agent_id=agent_id,
                sum_value=payment_sum,
            )
        else:
            invoices_data = await self._client.search_by_agent(
                agent_id=agent_id,
                only_unpaid=True,
            )

        entities = [self._to_entity(data) for data in invoices_data]
        entities = [entity for entity in entities if not entity.is_fully_paid()]

        logger.info(
            "Найдено счетов для привязки: %d (agent=%s, sum=%s, by_sum=%s)",
            len(entities),
            agent_id,
            payment_sum,
            search_by_sum,
        )

        return entities

    @staticmethod
    def _to_entity(data: dict) -> InvoiceOutEntity:
        """Преобразовать данные API в доменную сущность."""
        agent_meta = data.get("agent", {}).get("meta", {})
        agent_href = agent_meta.get("href", "")
        agent_id = agent_href.split("/")[-1] if agent_href else ""

        org_meta = data.get("organization", {}).get("meta", {})
        org_href = org_meta.get("href", "")
        org_id = org_href.split("/")[-1] if org_href else ""

        if not data.get("meta", {}).get("href"):
            raise InvoiceOutNotFoundError("Некорректные данные счета покупателю")

        return InvoiceOutEntity(
            id=data["id"],
            account_id=data["accountId"],
            name=data["name"],
            moment=data["moment"],
            applicable=data.get("applicable", False),
            sum=data["sum"],
            payed_sum=data.get("payedSum", 0),
            agent_id=agent_id,
            organization_id=org_id,
            meta_href=data["meta"]["href"],
        )