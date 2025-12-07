from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy import (
    Index,
    Integer,
    String,
)
from sqlalchemy.sql import func

from src.core.db import Base

from .schemas import PaymentType


class WebhookSubscription(Base):
    __tablename__ = "webhook_subscription"

    id = Column(Integer, primary_key=True, index=True)

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

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
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