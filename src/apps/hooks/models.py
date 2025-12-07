from sqlalchemy import Boolean, Column
from sqlalchemy import Enum as SAEnum
from sqlalchemy import Index, String

from src.core.models import Base

from .schemas import DocumentType, LinkType, PaymentType


class WebhookSubscription(Base):

    payment_type = Column(
        SAEnum(PaymentType, name="payment_type_enum"),
        nullable=False,
        index=True,
    )

    entity_type = Column(String(255), nullable=False)
    action = Column(String(32), nullable=False)
    url = Column(String(255), nullable=False)

    ms_webhook_id = Column(String(64), unique=True, nullable=False, index=True)
    ms_href = Column(String(512), nullable=True)
    ms_account_id = Column(String(64), nullable=True)

    enabled = Column(Boolean, nullable=False, default=True, index=True)

    document_type = Column(
        SAEnum(DocumentType, name="document_type_enum"),
        nullable=False,
        default=DocumentType.customerorder,
        server_default="customerorder",
    )

    link_type = Column(
        SAEnum(LinkType, name="link_type_enum"),
        nullable=False,
        default=LinkType.sum_and_counterparty,
        server_default="sum_and_counterparty",
    )

    __table_args__ = (
        Index(
            "ix_webhook_payment_enabled",
            "payment_type",
            "enabled",
        ),
        Index(
            "ix_webhook_entity_action_url",
            "entity_type",
            "action",
            "url",
        ),
    )