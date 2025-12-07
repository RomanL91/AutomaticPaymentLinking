from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel


class PaymentType(str, Enum):
    incoming_payment = "incoming_payment"   # Входящий платеж
    incoming_order = "incoming_order"       # Приходный ордер
    outgoing_payment = "outgoing_payment"   # Исходящий платеж
    outgoing_order = "outgoing_order"       # Расходный ордер


class AutoLinkTogglePayload(BaseModel):
    payment_type: PaymentType
    enabled: bool


# ===== Схемы для входящих вебхуков МойСклад =====


class MetaRef(BaseModel):
    """
    Универсальные meta, которые МС кладёт в auditContext.meta и event.meta.
    Остальные поля (metadataHref и прочие) Pydantic примет, даже если мы их не описали.
    """
    href: str
    type: str

    class Config:
        extra = "allow"  # не падать, если придут лишние поля


class AuditContext(BaseModel):
    meta: MetaRef
    moment: datetime
    uid: str


class WebhookEvent(BaseModel):
    meta: MetaRef
    action: str  # CREATE / UPDATE / DELETE / PROCESSED
    accountId: str
    updatedFields: Optional[List[str]] = None


class MySkladWebhookPayload(BaseModel):
    """
    Общая структура вебхука:
    {
      "auditContext": {...},
      "events": [ {...}, {...} ]
    }
    """
    auditContext: AuditContext
    events: List[WebhookEvent]
