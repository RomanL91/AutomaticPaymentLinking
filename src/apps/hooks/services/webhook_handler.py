"""Обработчик webhook событий для автоматической привязки платежей."""

import logging
import re

from ...customerorder.exceptions import CustomerOrderNotFoundError
from ...customerorder.services.customerorder_service import CustomerOrderService
from ...paymentin.exceptions import PaymentInNotFoundError
from ...paymentin.services.paymentin_service import PaymentInService
from ..models import WebhookSubscription
from ..schemas import DocumentType, LinkType

logger = logging.getLogger(__name__)


class WebhookHandler:
    """Обработчик webhook событий для автоматической привязки платежей."""
    
    def __init__(
        self,
        paymentin_service: PaymentInService,
        customerorder_service: CustomerOrderService,
    ):
        self.paymentin_service = paymentin_service
        self.customerorder_service = customerorder_service
    
    async def handle_paymentin_create(
        self, event_href: str, subscription: WebhookSubscription
    ) -> dict:
        """Обработать событие создания входящего платежа."""
        try:
            # 1. Получить данные платежа
            payment = await self.paymentin_service.get_by_href(event_href)
            logger.info(
                "Обработка платежа: id=%s, sum=%s, agent=%s",
                payment.id, payment.sum, payment.agent_id
            )
            
            # 2. Проверить тип документа (пока только customerorder)
            if subscription.document_type != DocumentType.customerorder:
                return {
                    "success": False,
                    "message": f"Тип документа {subscription.document_type} пока не поддерживается",
                }
            
            # 3. Найти подходящий заказ
            order = await self._find_order_for_payment(payment, subscription.link_type)
            
            if not order:
                logger.warning(
                    "Не найден заказ для платежа %s (agent=%s, sum=%s, strategy=%s)",
                    payment.id, payment.agent_id, payment.sum, subscription.link_type
                )
                return {
                    "success": False,
                    "message": "Не найден подходящий заказ для привязки",
                }
            
            # 4. Привязать платеж к заказу
            await self.paymentin_service.link_to_document(
                payment_id=payment.id,
                document_meta_href=order.meta_href,
                linked_sum=payment.sum,
            )
            
            logger.info(
                "✓ Платеж %s привязан к заказу %s (сумма: %s)",
                payment.id, order.name, payment.sum
            )
            
            return {
                "success": True,
                "message": f"Платеж привязан к заказу {order.name}",
                "payment_id": payment.id,
                "order_id": order.id,
            }
        
        except Exception as e:
            logger.exception("Ошибка при обработке платежа: %s", str(e))
            return {
                "success": False,
                "message": f"Ошибка: {str(e)}",
            }
    
    async def _find_order_for_payment(self, payment, link_type: LinkType):
        """Найти подходящий заказ в зависимости от стратегии."""
        
        if link_type == LinkType.sum_and_counterparty:
            # По сумме И контрагенту
            orders = await self.customerorder_service.find_for_payment(
                agent_id=payment.agent_id,
                payment_sum=payment.sum,
                search_by_sum=True,
            )
            return orders[0] if orders else None
        
        elif link_type == LinkType.counterparty:
            # Только по контрагенту (FIFO)
            orders = await self.customerorder_service.find_for_payment(
                agent_id=payment.agent_id,
                payment_sum=payment.sum,
                search_by_sum=False,
            )
            return orders[0] if orders else None
        
        elif link_type == LinkType.payment_purpose_mask:
            # По маске в назначении платежа
            return await self._find_order_by_purpose_mask(payment)
        
        return None
    
    async def _find_order_by_purpose_mask(self, payment):
        """Найти заказ по номеру из назначения платежа."""
        if not payment.payment_purpose:
            return None
        
        # Паттерны для извлечения номера
        patterns = [
            r"(?:заказ|order|№)\s*(\d+)",  # "заказ 123"
            r"\b(\d{5,})\b",                # 5+ цифр
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