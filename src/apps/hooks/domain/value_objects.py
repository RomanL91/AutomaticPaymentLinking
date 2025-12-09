"""Value Objects для доменной модели."""

from dataclasses import dataclass
from typing import Dict

from ..schemas import PaymentType

PAYMENT_TYPE_TO_ENTITY_TYPE: Dict[PaymentType, str] = {
    PaymentType.incoming_payment: "paymentin",
    PaymentType.incoming_order: "cashin",
    PaymentType.outgoing_payment: "paymentout",
    PaymentType.outgoing_order: "cashout",
}

WEBHOOK_ACTION = "CREATE"


@dataclass(frozen=True)
class WebhookConfiguration:
    """Конфигурация вебхука (Value Object)."""
    
    payment_type: PaymentType
    entity_type: str
    action: str
    url: str
    
    @classmethod
    def from_payment_type(
        cls,
        payment_type: PaymentType,
        webhook_url: str,
    ) -> "WebhookConfiguration":
        """
        Создать конфигурацию вебхука из типа платежа.
        
        Args:
            payment_type: Тип платежа
            webhook_url: URL для вебхука
            
        Returns:
            Конфигурация вебхука
        """
        return cls(
            payment_type=payment_type,
            entity_type=PAYMENT_TYPE_TO_ENTITY_TYPE[payment_type],
            action=WEBHOOK_ACTION,
            url=webhook_url,
        )