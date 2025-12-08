import logging
import re

from src.apps.hooks.models import DocumentType, LinkType, WebhookSubscription
from src.apps.paymentin.exceptions import PaymentInNotFoundError
from src.apps.paymentin.services.paymentin_service import PaymentInService

logger = logging.getLogger(__name__)


class WebhookHandler:
    """Обработчик webhook событий для автоматической привязки платежей"""

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
        """
        Обработать событие создания входящего платежа
        
        Returns:
            dict с результатом: {"success": bool, "message": str, "details": dict}
        """
        try:
            # 1. Получить данные платежа
            payment = await self.paymentin_service.get_by_href(event_href)
            logger.info(
                f"Обработка платежа: id={payment.id}, sum={payment.sum}, agent={payment.agent_id}"
            )

            # 2. Проверить тип документа
            if subscription.document_type != DocumentType.CUSTOMERORDER:
                return {
                    "success": False,
                    "message": f"Тип документа {subscription.document_type} пока не поддерживается",
                    "details": {"document_type": subscription.document_type},
                }

            # 3. Найти подходящий заказ в зависимости от стратегии
            order = await self._find_order_for_payment(payment, subscription.link_type)

            if not order:
                logger.warning(
                    f"Не найден подходящий заказ для платежа {payment.id} "
                    f"(agent={payment.agent_id}, sum={payment.sum}, strategy={subscription.link_type})"
                )
                return {
                    "success": False,
                    "message": "Не найден подходящий заказ для привязки",
                    "details": {
                        "payment_id": payment.id,
                        "agent_id": payment.agent_id,
                        "sum": payment.sum,
                        "link_type": subscription.link_type,
                    },
                }

            # 4. Привязать платеж к заказу
            linked_payment = await self.paymentin_service.link_to_document(
                payment_id=payment.id,
                document_meta_href=order.meta_href,
                linked_sum=payment.sum,
            )

            logger.info(
                f"✓ Платеж {payment.id} успешно привязан к заказу {order.id} "
                f"(сумма: {payment.sum})"
            )

            return {
                "success": True,
                "message": f"Платеж успешно привязан к заказу {order.name}",
                "details": {
                    "payment_id": linked_payment.id,
                    "order_id": order.id,
                    "order_name": order.name,
                    "linked_sum": payment.sum,
                    "link_type": subscription.link_type,
                },
            }

        except PaymentInNotFoundError as e:
            logger.error(f"Платеж не найден: {e.message}")
            return {
                "success": False,
                "message": "Платеж не найден в МойСклад",
                "details": {"error": e.message},
            }

        except CustomerOrderNotFoundError as e:
            logger.error(f"Заказ не найден: {e.message}")
            return {
                "success": False,
                "message": "Заказ не найден",
                "details": {"error": e.message},
            }

        except Exception as e:
            logger.exception(f"Неожиданная ошибка при обработке платежа: {str(e)}")
            return {
                "success": False,
                "message": "Внутренняя ошибка сервиса",
                "details": {"error": str(e)},
            }

    async def _find_order_for_payment(self, payment, link_type: LinkType):
        """Найти подходящий заказ в зависимости от стратегии привязки"""

        if link_type == LinkType.SUM_AND_COUNTERPARTY:
            # Поиск по контрагенту и сумме (±1%)
            orders = await self.customerorder_service.find_for_payment(
                agent_id=payment.agent_id,
                payment_sum=payment.sum,
                search_by_sum=True,
            )
            return orders[0] if orders else None

        elif link_type == LinkType.COUNTERPARTY:
            # Поиск всех неоплаченных заказов контрагента (FIFO)
            orders = await self.customerorder_service.find_for_payment(
                agent_id=payment.agent_id,
                payment_sum=payment.sum,
                search_by_sum=False,
            )
            return orders[0] if orders else None

        elif link_type == LinkType.PAYMENT_PURPOSE_MASK:
            # Поиск по маске в назначении платежа
            return await self._find_order_by_purpose_mask(payment)

        return None

    async def _find_order_by_purpose_mask(self, payment):
        """Найти заказ по номеру из назначения платежа"""
        if not payment.payment_purpose:
            logger.warning(
                f"Платеж {payment.id}: отсутствует назначение платежа для поиска по маске"
            )
            return None

        # Паттерны для извлечения номера заказа
        patterns = [
            r"(?:заказ|order|№)\s*(\d+)",  # "заказ 123", "order 456", "№789"
            r"(?:зак|ord)[\.\s]*(\d+)",  # "зак. 123", "ord 456"
            r"\b(\d{5,})\b",  # просто 5+ цифр подряд
        ]

        order_number = None
        for pattern in patterns:
            match = re.search(pattern, payment.payment_purpose, re.IGNORECASE)
            if match:
                order_number = match.group(1)
                break

        if not order_number:
            logger.warning(
                f"Платеж {payment.id}: не удалось извлечь номер заказа из назначения: '{payment.payment_purpose}'"
            )
            return None

        logger.info(
            f"Платеж {payment.id}: извлечен номер заказа '{order_number}' из назначения"
        )

        # Поиск заказа по номеру и контрагенту
        try:
            return await self.customerorder_service.find_by_name_and_agent(
                name=order_number, agent_id=payment.agent_id
            )
        except CustomerOrderNotFoundError:
            logger.warning(
                f"Заказ с номером '{order_number}' для контрагента {payment.agent_id} не найден"
            )
            return None