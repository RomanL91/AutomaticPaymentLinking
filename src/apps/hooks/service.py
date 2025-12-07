import logging
import os
from typing import Any, Dict, Optional

import httpx

from src.apps.ms_auth.service import MySkladAuthService

from .schemas import PaymentType

logger = logging.getLogger(__name__)

# URL, на который МойСклад будет слать вебхуки.
# На бою это должен быть публичный HTTPS URL твоего сервиса.
# Пока можно оставить заглушку или прописать через переменную окружения.
MS_WEBHOOK_URL = os.environ.get(
    "MS_WEBHOOK_URL",
    "https://ba69ec82eb9a.ngrok-free.app/api/hooks/moysklad/webhook",  # TODO: заменить на реальный URL
)

# Маппинг вкладки (типа платежа) -> entityType в вебхуке
# См. документацию МС: PaymentIn, PaymentOut, CashIn, CashOut.
PAYMENT_TYPE_TO_ENTITY_TYPE: Dict[PaymentType, str] = {
    PaymentType.incoming_payment: "paymentin",     # Входящий платеж
    PaymentType.incoming_order: "cashin",          # Приходный ордер
    PaymentType.outgoing_payment: "paymentout",    # Исходящий платеж
    PaymentType.outgoing_order: "cashout",         # Расходный ордер
}

# Какое событие отслеживаем — при создании документа
WEBHOOK_ACTION = "CREATE"


class WebhookService:
    """
    Логика работы с вебхуками МойСклад:
    - поиск вебхука по entityType + action + url;
    - создание нового;
    - включение/выключение существующего.
    """

    def __init__(self, auth_service: MySkladAuthService) -> None:
        self._auth_service = auth_service

    async def sync_webhook_for_toggle(
        self,
        payment_type: PaymentType,
        enabled: bool,
    ) -> Dict[str, Any]:
        """
        Основной сценарий:
        - по типу платежа определяем entityType;
        - ищем вебхук;
        - если enabled=True -> создать или включить;
        - если enabled=False -> выключить (enabled=false).
        Возвращает словарь с информацией об операции.
        """
        entity_type = PAYMENT_TYPE_TO_ENTITY_TYPE[payment_type]

        creds = self._auth_service.get_raw_credentials()
        if creds is None:
            logger.warning(
                "sync_webhook_for_toggle called, but MoySklad credentials are NOT configured"
            )
            return {
                "operation": "skipped_no_credentials",
                "reason": "MoySklad credentials are not configured",
            }

        auth_header = self._auth_service.get_basic_auth_header()
        if auth_header is None:
            logger.warning("No Authorization header built from credentials")
            return {
                "operation": "skipped_no_credentials",
                "reason": "Cannot build Basic Auth header",
            }

        base_url = str(creds.base_url).rstrip("/")  # типа https://api.moysklad.ru/api/remap/1.2

        async with httpx.AsyncClient(
            headers={
                **auth_header,
                "Content-Type": "application/json",
                "Accept-Encoding": "gzip",
            },
            timeout=10.0,
        ) as client:
            try:
                existing = await self._find_existing_webhook(
                    client=client,
                    base_url=base_url,
                    entity_type=entity_type,
                    action=WEBHOOK_ACTION,
                    url=MS_WEBHOOK_URL,
                )
            except httpx.HTTPError as exc:
                logger.error("Error while fetching webhooks from MoySklad: %s", exc)
                return {
                    "operation": "error_fetching",
                    "error": str(exc),
                }

            if enabled:
                if existing is None:
                    # Создаём новый вебхук
                    try:
                        created = await self._create_webhook(
                            client=client,
                            base_url=base_url,
                            entity_type=entity_type,
                            action=WEBHOOK_ACTION,
                            url=MS_WEBHOOK_URL,
                        )
                    except httpx.HTTPError as exc:
                        logger.error("Error while creating webhook: %s", exc)
                        return {
                            "operation": "error_creating",
                            "error": str(exc),
                        }

                    return {
                        "operation": "created_and_enabled",
                        "webhook": created,
                    }

                # Уже есть вебхук — просто включаем, если он выключен
                if existing.get("enabled") is True:
                    return {
                        "operation": "already_enabled",
                        "webhook": existing,
                    }

                try:
                    updated = await self._update_webhook_enabled(
                        client=client,
                        webhook=existing,
                        enabled=True,
                    )
                except httpx.HTTPError as exc:
                    logger.error("Error while enabling webhook: %s", exc)
                    return {
                        "operation": "error_enabling",
                        "error": str(exc),
                    }

                return {
                    "operation": "enabled",
                    "webhook": updated,
                }

            # enabled == False -> нужно выключить вебхук (если есть)
            if existing is None:
                return {
                    "operation": "not_found_to_disable",
                    "webhook": None,
                }

            if existing.get("enabled") is False:
                return {
                    "operation": "already_disabled",
                    "webhook": existing,
                }

            try:
                updated = await self._update_webhook_enabled(
                    client=client,
                    webhook=existing,
                    enabled=False,
                )
            except httpx.HTTPError as exc:
                logger.error("Error while disabling webhook: %s", exc)
                return {
                    "operation": "error_disabling",
                    "error": str(exc),
                }

            return {
                "operation": "disabled",
                "webhook": updated,
            }

    async def _find_existing_webhook(
        self,
        client: httpx.AsyncClient,
        base_url: str,
        entity_type: str,
        action: str,
        url: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Получаем список вебхуков и ищем тот, который соответствует
        entityType + action + url.
        Для MVP достаточно одной страницы (лимит вебхуков обычно небольшой).
        """
        list_url = f"{base_url}/entity/webhook"
        resp = await client.get(list_url, params={"limit": 100})
        resp.raise_for_status()
        data = resp.json()

        for row in data.get("rows", []):
            if (
                row.get("entityType") == entity_type
                and row.get("action") == action
                and row.get("url") == url
            ):
                return row
        return None

    async def _create_webhook(
        self,
        client: httpx.AsyncClient,
        base_url: str,
        entity_type: str,
        action: str,
        url: str,
    ) -> Dict[str, Any]:
        """
        POST /entity/webhook — создаём новый вебхук.
        """
        create_url = f"{base_url}/entity/webhook"
        payload = {
            "url": url,
            "action": action,
            "entityType": entity_type,
        }
        resp = await client.post(create_url, json=payload)
        resp.raise_for_status()
        return resp.json()

    async def _update_webhook_enabled(
        self,
        client: httpx.AsyncClient,
        webhook: Dict[str, Any],
        enabled: bool,
    ) -> Dict[str, Any]:
        """
        PUT /entity/webhook/{id}  или по meta.href — включаем/выключаем вебхук.
        """
        meta = webhook.get("meta") or {}
        href = meta.get("href")
        if not href:
            # fallback: строим по id
            webhook_id = webhook["id"]
            # href вида: https://online.moysklad.ru/api/remap/1.1/entity/webhook/{id}
            # Можно дернуть напрямую по href, если оно полное, httpx это переварит.
            raise ValueError(f"No meta.href in webhook: {webhook_id}")

        resp = await client.put(href, json={"enabled": enabled})
        resp.raise_for_status()
        return resp.json()
