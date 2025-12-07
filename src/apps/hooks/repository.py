from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import WebhookSubscription
from .schemas import PaymentType


async def get_webhook_status(session: AsyncSession) -> dict[str, bool]:
    """
    Получить статус всех вебхуков.
    Возвращает словарь {payment_type: enabled}.
    """
    stmt = select(WebhookSubscription)
    result = await session.execute(stmt)
    webhooks = result.scalars().all()

    status_dict = {}
    for webhook in webhooks:
        # Используем строковое значение enum
        status_dict[webhook.payment_type.value] = webhook.enabled

    return status_dict


async def upsert_webhook_subscription(
    session: AsyncSession,
    payment_type: PaymentType,
    webhook_data: dict,
) -> WebhookSubscription:
    """
    Создаёт или обновляет запись о вебхуке по его id из МойСклад.
    """
    ms_webhook_id = webhook_data.get("id")
    entity_type = webhook_data.get("entityType")
    action = webhook_data.get("action")
    url = webhook_data.get("url")
    enabled = bool(webhook_data.get("enabled", True))
    account_id = webhook_data.get("accountId")
    meta = webhook_data.get("meta") or {}
    href = meta.get("href")

    stmt = select(WebhookSubscription).where(
        WebhookSubscription.ms_webhook_id == ms_webhook_id
    )
    result = await session.execute(stmt)
    instance = result.scalar_one_or_none()

    if instance is None:
        instance = WebhookSubscription(
            payment_type=payment_type,
            entity_type=entity_type,
            action=action,
            url=url,
            ms_webhook_id=ms_webhook_id,
            ms_href=href,
            ms_account_id=account_id,
            enabled=enabled,
        )
        session.add(instance)
    else:
        instance.payment_type = payment_type
        instance.entity_type = entity_type
        instance.action = action
        instance.url = url
        instance.ms_href = href
        instance.ms_account_id = account_id
        instance.enabled = enabled

    await session.commit()
    await session.refresh(instance)
    return instance