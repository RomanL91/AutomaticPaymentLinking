"""Обработчик webhook событий для автоматической привязки платежей."""

import logging
import re

from ...customerorder.exceptions import CustomerOrderNotFoundError
from ...customerorder.services.customerorder_service import CustomerOrderService
from ...demand.exceptions import DemandNotFoundError
from ...demand.services.demand_service import DemandService
from ...invoiceout.exceptions import InvoiceOutNotFoundError
from ...invoiceout.services.invoiceout_service import InvoiceOutService
from ...paymentin.exceptions import PaymentInNotFoundError
from ...paymentin.services.paymentin_service import PaymentInService
from ..domain.entities import WebhookEntity
from ..schemas import DocumentPriority, DocumentType, LinkType

logger = logging.getLogger(__name__)


class WebhookHandler:
    """Обработчик webhook событий для автоматической привязки платежей."""

    def __init__(
        self,
        paymentin_service: PaymentInService,
        customerorder_service: CustomerOrderService,
        invoiceout_service: InvoiceOutService,
        demand_service: DemandService,
    ):
        self.paymentin_service = paymentin_service
        self.customerorder_service = customerorder_service
        self.invoiceout_service = invoiceout_service
        self.demand_service = demand_service


    async def handle_paymentin_create(
        self, event_href: str, subscription: WebhookEntity
    ) -> dict:
        """Обработать событие создания входящего платежа."""

        try:
            payment = await self.paymentin_service.get_by_href(event_href)
            logger.info(
                "Обработка платежа: id=%s, sum=%s, agent=%s",
                payment.id,
                payment.sum,
                payment.agent_id,
            )

            if subscription.link_type == LinkType.counterparty:
                document, linked_sum = await self._link_payment_by_counterparty(
                    payment=payment,
                    document_type=subscription.document_type,
                    prioritize_oldest=(
                        subscription.document_priority == DocumentPriority.oldest_first
                    ),
                )
            else:
                document = await self._find_document_for_payment(
                    payment=payment,
                    document_type=subscription.document_type,
                    link_type=subscription.link_type,
                )
                linked_sum = payment.sum if document else 0

            if not document or linked_sum <= 0:
                logger.warning(
                    "Не найден документ для платежа %s (agent=%s, sum=%s, strategy=%s, type=%s)",
                    payment.id,
                    payment.agent_id,
                    payment.sum,
                    subscription.link_type,
                    subscription.document_type,
                )
                return {
                    "success": False,
                    "message": "Не найден подходящий документ для привязки",
                }

            if subscription.link_type != LinkType.counterparty:
                await self.paymentin_service.link_to_document(
                    payment_id=payment.id,
                    document_meta_href=document.meta_href,
                    linked_sum=payment.sum,
                )

            logger.info(
                "✓ Платеж %s привязан к %s %s (сумма: %s)",
                payment.id,
                subscription.document_type.value,
                document.name,
                payment.sum,
            )
            
            response = {
                "success": True,
                "message": (
                    f"Платеж привязан к {subscription.document_type.value} {document.name}"
                ),
                "payment_id": payment.id,
                "document_id": document.id,
                "document_type": subscription.document_type.value,
            }

            if subscription.document_type == DocumentType.customerorder:
                response["order_id"] = document.id

            return response
        
        except PaymentInNotFoundError as exc:
            logger.warning("Платеж по ссылке %s не найден: %s", event_href, exc)
            return {"success": False, "message": "Платеж не найден в МойСклад"}
        except (
            CustomerOrderNotFoundError,
            InvoiceOutNotFoundError,
            DemandNotFoundError,
        ) as exc:
            logger.warning("Документ для платежа %s не найден: %s", event_href, exc)
            return {"success": False, "message": "Документ для привязки не найден"}
        except Exception as exc:  # pragma: no cover - защитный блок
            logger.exception("Ошибка при обработке платежа: %s", str(exc))
            raise

    async def _find_document_for_payment(
        self, payment, document_type: DocumentType, link_type: LinkType
    ):
        """Найти подходящий документ по типу и стратегии."""

        if document_type == DocumentType.customerorder:
            return await self._find_order_for_payment(payment, link_type)

        if document_type == DocumentType.invoiceout:
            return await self._find_invoice_for_payment(payment, link_type)

        if document_type == DocumentType.demand:
            return await self._find_demand_for_payment(payment, link_type)

        return None

    async def _link_payment_by_counterparty(
        self,
        payment,
        document_type: DocumentType,
        prioritize_oldest: bool,
    ):
        """Привязать платеж по контрагенту к нескольким документам по очереди."""

        documents = await self._get_documents_by_counterparty(
            payment=payment,
            document_type=document_type,
            prioritize_oldest=prioritize_oldest,
        )

        if not documents:
            return None, 0

        remaining_sum = payment.sum
        last_linked_document = None

        for document in documents:
            unpaid_amount = document.get_unpaid_amount()
            if unpaid_amount <= 0:
                continue

            linked_sum = min(unpaid_amount, remaining_sum)

            if linked_sum <= 0:
                break

            await self.paymentin_service.link_to_document(
                payment_id=payment.id,
                document_meta_href=document.meta_href,
                linked_sum=linked_sum,
            )

            logger.info(
                "Часть платежа %s привязана к %s %s: linked_sum=%s, unpaid_before=%s, remaining_payment=%s",
                payment.id,
                document_type.value,
                document.name,
                linked_sum,
                unpaid_amount,
                remaining_sum - linked_sum,
            )

            remaining_sum -= linked_sum
            last_linked_document = document

            if remaining_sum <= 0:
                break

        total_linked = payment.sum - remaining_sum
        return last_linked_document, total_linked

    async def _get_documents_by_counterparty(
        self, payment, document_type: DocumentType, prioritize_oldest: bool
    ):
        """Получить список документов для привязки по контрагенту."""

        if document_type == DocumentType.customerorder:
            return await self.customerorder_service.find_for_payment(
                agent_id=payment.agent_id,
                payment_sum=payment.sum,
                search_by_sum=False,
                prioritize_oldest=prioritize_oldest,
            )

        if document_type == DocumentType.invoiceout:
            return await self.invoiceout_service.find_for_payment(
                agent_id=payment.agent_id,
                payment_sum=payment.sum,
                search_by_sum=False,
                prioritize_oldest=prioritize_oldest,
            )

        if document_type == DocumentType.demand:
            return await self.demand_service.find_for_payment(
                agent_id=payment.agent_id,
                payment_sum=payment.sum,
                search_by_sum=False,
                prioritize_oldest=prioritize_oldest,
            )

        return []

    async def _find_order_for_payment(self, payment, link_type: LinkType):
        """Найти подходящий заказ в зависимости от стратегии."""

        if link_type == LinkType.sum_and_counterparty:
            orders = await self.customerorder_service.find_for_payment(
                agent_id=payment.agent_id,
                payment_sum=payment.sum,
                search_by_sum=True,
            )
            return orders[0] if orders else None
        
        elif link_type == LinkType.counterparty:
            orders = await self.customerorder_service.find_for_payment(
                agent_id=payment.agent_id,
                payment_sum=payment.sum,
                search_by_sum=False,
            )
            return orders[0] if orders else None
        
        elif link_type == LinkType.payment_purpose_mask:
            return await self._find_order_by_purpose_mask(payment)

        return None

    async def _find_invoice_for_payment(self, payment, link_type: LinkType):
        """Найти подходящий счет покупателю для платежа."""

        if link_type == LinkType.sum_and_counterparty:
            invoices = await self.invoiceout_service.find_for_payment(
                agent_id=payment.agent_id,
                payment_sum=payment.sum,
                search_by_sum=True,
            )
            return invoices[0] if invoices else None

        if link_type == LinkType.counterparty:
            invoices = await self.invoiceout_service.find_for_payment(
                agent_id=payment.agent_id,
                payment_sum=payment.sum,
                search_by_sum=False,
            )
            return invoices[0] if invoices else None

        return None

    async def _find_demand_for_payment(self, payment, link_type: LinkType):
        """Найти подходящую отгрузку для платежа."""

        if link_type == LinkType.sum_and_counterparty:
            demands = await self.demand_service.find_for_payment(
                agent_id=payment.agent_id,
                payment_sum=payment.sum,
                search_by_sum=True,
            )
            return demands[0] if demands else None

        if link_type == LinkType.counterparty:
            demands = await self.demand_service.find_for_payment(
                agent_id=payment.agent_id,
                payment_sum=payment.sum,
                search_by_sum=False,
            )
            return demands[0] if demands else None

        return None

    async def _find_order_by_purpose_mask(self, payment):
        """Найти заказ по номеру из назначения платежа."""
        if not payment.payment_purpose:
            return None

        patterns = [
            r"(?:заказ|order|№)\s*(\d+)",
            r"\b(\d{5,})\b",
        ]

        order_number = None
        for pattern in patterns:
            match = re.search(pattern, payment.payment_purpose, re.IGNORECASE)
            if match:
                order_number = match.group(1)
                break

        if not order_number:
            logger.warning("Не удалось извлечь номер заказа из: '%s'", payment.payment_purpose)
            return None

        try:
            return await self.customerorder_service.find_by_name_and_agent(
                name=order_number,
                agent_id=payment.agent_id
            )
        except CustomerOrderNotFoundError:
            return None