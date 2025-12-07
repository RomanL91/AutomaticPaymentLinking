import logging
from typing import Any, Dict, Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from src.apps.ms_auth.service import MySkladAuthService
from src.core.config import settings

from .schemas import PaymentType

logger = logging.getLogger(__name__)


PAYMENT_TYPE_TO_ENTITY_TYPE: Dict[PaymentType, str] = {
    PaymentType.incoming_payment: "paymentin",
    PaymentType.incoming_order: "cashin",
    PaymentType.outgoing_payment: "paymentout",
    PaymentType.outgoing_order: "cashout",
}

WEBHOOK_ACTION = "CREATE"


class WebhookServiceError(Exception):
    """Базовое исключение для ошибок сервиса вебхуков"""
    pass


class WebhookService:
    def __init__(self, auth_service: MySkladAuthService) -> None:
        self._auth_service = auth_service

    async def sync_webhook_for_toggle(
        self,
        payment_type: PaymentType,
        enabled: bool,
    ) -> Dict[str, Any]:
        entity_type = PAYMENT_TYPE_TO_ENTITY_TYPE[payment_type]

        # Читаем webhook URL из конфига (динамически)
        webhook_url = settings.ms_webhook_url
        
        if not webhook_url:
            logger.warning(
                "MS_WEBHOOK_URL не задан. Установите APL_MS_WEBHOOK_URL в .env и перезапустите сервер"
            )
            return {
                "operation": "skipped_no_webhook_url",
                "reason": (
                    "Webhook URL не настроен. Запустите ngrok (DEV_docs/start_ngrok.ps1) "
                    "и перезапустите сервер"
                ),
            }

        creds = self._auth_service.get_raw_credentials()
        if not creds:
            logger.warning("МойСклад credentials не настроены")
            return {
                "operation": "skipped_no_credentials",
                "reason": "MoySklad credentials are not configured",
            }

        auth_header = self._auth_service.get_basic_auth_header()
        if not auth_header:
            logger.warning("Невозможно построить Authorization header")
            return {
                "operation": "skipped_no_credentials",
                "reason": "Cannot build Basic Auth header",
            }

        base_url = str(creds.base_url).rstrip("/")

        async with httpx.AsyncClient(
            headers={
                **auth_header,
                "Content-Type": "application/json",
                "Accept-Encoding": "gzip",
            },
            timeout=30.0,
        ) as client:
            try:
                existing = await self._find_existing_webhook(
                    client=client,
                    base_url=base_url,
                    entity_type=entity_type,
                    action=WEBHOOK_ACTION,
                    url=webhook_url,
                )
            except Exception as exc:
                logger.exception("Ошибка при получении списка вебхуков")
                return {"operation": "error_fetching", "error": str(exc)}

            if enabled:
                return await self._handle_enable(client, base_url, entity_type, existing, webhook_url)
            else:
                return await self._handle_disable(client, existing)

    async def _handle_enable(
        self,
        client: httpx.AsyncClient,
        base_url: str,
        entity_type: str,
        existing: Optional[Dict[str, Any]],
        webhook_url: str,
    ) -> Dict[str, Any]:
        if not existing:
            try:
                created = await self._create_webhook(
                    client=client,
                    base_url=base_url,
                    entity_type=entity_type,
                    action=WEBHOOK_ACTION,
                    url=webhook_url,
                )
                logger.info("Создан новый вебхук: %s", created.get("id"))
                return {"operation": "created_and_enabled", "webhook": created}
            except Exception as exc:
                logger.exception("Ошибка при создании вебхука")
                return {"operation": "error_creating", "error": str(exc)}

        if existing.get("enabled") is True:
            return {"operation": "already_enabled", "webhook": existing}

        try:
            updated = await self._update_webhook_enabled(
                client=client,
                webhook=existing,
                enabled=True,
            )
            logger.info("Вебхук включен: %s", existing.get("id"))
            return {"operation": "enabled", "webhook": updated}
        except Exception as exc:
            logger.exception("Ошибка при включении вебхука")
            return {"operation": "error_enabling", "error": str(exc)}

    async def _handle_disable(
        self,
        client: httpx.AsyncClient,
        existing: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        if not existing:
            return {"operation": "not_found_to_disable", "webhook": None}

        if existing.get("enabled") is False:
            return {"operation": "already_disabled", "webhook": existing}

        try:
            updated = await self._update_webhook_enabled(
                client=client,
                webhook=existing,
                enabled=False,
            )
            logger.info("Вебхук выключен: %s", existing.get("id"))
            return {"operation": "disabled", "webhook": updated}
        except Exception as exc:
            logger.exception("Ошибка при выключении вебхука")
            return {"operation": "error_disabling", "error": str(exc)}

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def _find_existing_webhook(
        self,
        client: httpx.AsyncClient,
        base_url: str,
        entity_type: str,
        action: str,
        url: str,
    ) -> Optional[Dict[str, Any]]:
        list_url = f"{base_url}/entity/webhook"
        logger.debug("Получение списка вебхуков: %s", list_url)
        
        resp = await client.get(list_url, params={"limit": 100})
        resp.raise_for_status()
        data = resp.json()

        logger.debug("Получено вебхуков: %d", len(data.get("rows", [])))

        for row in data.get("rows", []):
            if (
                row.get("entityType") == entity_type
                and row.get("action") == action
                and row.get("url") == url
            ):
                logger.debug("Найден существующий вебхук: %s", row.get("id"))
                return row
        return None

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def _create_webhook(
        self,
        client: httpx.AsyncClient,
        base_url: str,
        entity_type: str,
        action: str,
        url: str,
    ) -> Dict[str, Any]:
        create_url = f"{base_url}/entity/webhook"
        payload = {
            "url": url,
            "action": action,
            "entityType": entity_type,
        }
        logger.info("Создание вебхука: %s", payload)
        
        resp = await client.post(create_url, json=payload)
        resp.raise_for_status()
        result = resp.json()
        
        logger.info("Вебхук создан: id=%s", result.get("id"))
        return result

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def _update_webhook_enabled(
        self,
        client: httpx.AsyncClient,
        webhook: Dict[str, Any],
        enabled: bool,
    ) -> Dict[str, Any]:
        meta = webhook.get("meta") or {}
        href = meta.get("href")
        
        if not href:
            webhook_id = webhook.get("id")
            raise WebhookServiceError(
                f"Отсутствует meta.href для вебхука {webhook_id}"
            )

        logger.info("Обновление вебхука %s: enabled=%s", webhook.get("id"), enabled)
        
        resp = await client.put(href, json={"enabled": enabled})
        resp.raise_for_status()
        result = resp.json()
        
        logger.info("Вебхук обновлен: id=%s, enabled=%s", result.get("id"), enabled)
        return result