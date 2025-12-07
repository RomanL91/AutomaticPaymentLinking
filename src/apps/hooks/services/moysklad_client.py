"""Клиент для взаимодействия с API МойСклад."""

import logging
from typing import Any, Dict, Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from ...ms_auth.services.auth_service import MySkladAuthService
from ..exceptions import MoySkladAPIError

logger = logging.getLogger(__name__)


class MoySkladClient:
    """
    Клиент для работы с API МойСклад.
    
    Инкапсулирует логику HTTP-запросов к API.
    """
    
    def __init__(self, auth_service: MySkladAuthService) -> None:
        """
        Инициализировать клиент МойСклад.
        
        Args:
            auth_service: Сервис аутентификации
        """
        self._auth_service = auth_service
        self._timeout = 30.0
    
    def _get_base_url(self) -> str:
        """
        Получить базовый URL API.
        
        Returns:
            Базовый URL
            
        Raises:
            MoySkladAPIError: Если credentials не настроены
        """
        creds = self._auth_service.get_raw_credentials()
        if not creds:
            raise MoySkladAPIError("МойСклад credentials не настроены")
        return str(creds.base_url).rstrip("/")
    
    def _get_headers(self) -> Dict[str, str]:
        """
        Получить заголовки для запросов.
        
        Returns:
            Словарь заголовков
            
        Raises:
            MoySkladAPIError: Если не удается построить заголовок авторизации
        """
        auth_header = self._auth_service.get_basic_auth_header()
        if not auth_header:
            raise MoySkladAPIError("Невозможно построить Authorization header")
        
        return {
            **auth_header,
            "Content-Type": "application/json",
            "Accept-Encoding": "gzip",
        }
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def list_webhooks(self, limit: int = 100) -> list[Dict[str, Any]]:
        """
        Получить список вебхуков.
        
        Args:
            limit: Максимальное количество записей
            
        Returns:
            Список вебхуков
            
        Raises:
            MoySkladAPIError: При ошибке запроса
        """
        try:
            base_url = self._get_base_url()
            headers = self._get_headers()
            
            async with httpx.AsyncClient(headers=headers, timeout=self._timeout) as client:
                url = f"{base_url}/entity/webhook"
                logger.debug("Запрос списка вебхуков: %s", url)
                
                resp = await client.get(url, params={"limit": limit})
                resp.raise_for_status()
                data = resp.json()
                
                rows = data.get("rows", [])
                logger.debug("Получено вебхуков: %d", len(rows))
                return rows
        except httpx.HTTPStatusError as exc:
            raise MoySkladAPIError(
                "Ошибка HTTP при получении списка вебхуков",
                details={"status_code": exc.response.status_code, "error": str(exc)},
            ) from exc
        except Exception as exc:
            raise MoySkladAPIError(
                "Ошибка при получении списка вебхуков",
                details={"error": str(exc)},
            ) from exc
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def create_webhook(
        self,
        entity_type: str,
        action: str,
        url: str,
    ) -> Dict[str, Any]:
        """
        Создать новый вебхук.
        
        Args:
            entity_type: Тип сущности
            action: Действие (CREATE, UPDATE, DELETE)
            url: URL для вебхука
            
        Returns:
            Данные созданного вебхука
            
        Raises:
            MoySkladAPIError: При ошибке создания
        """
        try:
            base_url = self._get_base_url()
            headers = self._get_headers()
            
            payload = {
                "url": url,
                "action": action,
                "entityType": entity_type,
            }
            
            async with httpx.AsyncClient(headers=headers, timeout=self._timeout) as client:
                create_url = f"{base_url}/entity/webhook"
                logger.info("Создание вебхука: %s", payload)
                
                resp = await client.post(create_url, json=payload)
                resp.raise_for_status()
                result = resp.json()
                
                logger.info("Вебхук создан: id=%s", result.get("id"))
                return result
        except httpx.HTTPStatusError as exc:
            raise MoySkladAPIError(
                "Ошибка HTTP при создании вебхука",
                details={"status_code": exc.response.status_code, "error": str(exc)},
            ) from exc
        except Exception as exc:
            raise MoySkladAPIError(
                "Ошибка при создании вебхука",
                details={"error": str(exc)},
            ) from exc
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def update_webhook_enabled(
        self,
        webhook_data: Dict[str, Any],
        enabled: bool,
    ) -> Dict[str, Any]:
        """
        Обновить статус вебхука (включен/выключен).
        
        Args:
            webhook_data: Данные вебхука с meta.href
            enabled: Новый статус
            
        Returns:
            Обновленные данные вебхука
            
        Raises:
            MoySkladAPIError: При ошибке обновления
        """
        try:
            headers = self._get_headers()
            meta = webhook_data.get("meta") or {}
            href = meta.get("href")
            
            if not href:
                webhook_id = webhook_data.get("id")
                raise MoySkladAPIError(
                    f"Отсутствует meta.href для вебхука {webhook_id}"
                )
            
            webhook_id = webhook_data.get("id")
            logger.info("Обновление вебхука %s: enabled=%s", webhook_id, enabled)
            
            async with httpx.AsyncClient(headers=headers, timeout=self._timeout) as client:
                resp = await client.put(href, json={"enabled": enabled})
                resp.raise_for_status()
                result = resp.json()
                
                logger.info("Вебхук обновлен: id=%s, enabled=%s", result.get("id"), enabled)
                return result
        except httpx.HTTPStatusError as exc:
            raise MoySkladAPIError(
                "Ошибка HTTP при обновлении вебхука",
                details={"status_code": exc.response.status_code, "error": str(exc)},
            ) from exc
        except Exception as exc:
            raise MoySkladAPIError(
                "Ошибка при обновлении вебхука",
                details={"error": str(exc)},
            ) from exc
    
    async def find_webhook(
        self,
        entity_type: str,
        action: str,
        url: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Найти вебхук по параметрам.
        
        Args:
            entity_type: Тип сущности
            action: Действие
            url: URL вебхука
            
        Returns:
            Данные вебхука или None
        """
        webhooks = await self.list_webhooks()
        
        for webhook in webhooks:
            if (
                webhook.get("entityType") == entity_type
                and webhook.get("action") == action
                and webhook.get("url") == url
            ):
                logger.debug("Найден существующий вебхук: %s", webhook.get("id"))
                return webhook
        
        return None