"""Репозиторий для работы с вебхуками."""

from typing import Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..domain.entities import WebhookEntity
from ..exceptions import RepositoryError
from ..models import WebhookSubscription
from ..schemas import PaymentType
from .base import AbstractRepository


class WebhookRepository(AbstractRepository[WebhookEntity]):
    """Репозиторий для управления вебхуками."""
    
    def __init__(self, session: AsyncSession) -> None:
        """
        Инициализировать репозиторий вебхуков.
        
        Args:
            session: Асинхронная сессия SQLAlchemy
        """
        super().__init__(session)
    
    async def get_by_id(self, entity_id: int) -> Optional[WebhookEntity]:
        """
        Получить вебхук по ID.
        
        Args:
            entity_id: ID вебхука
            
        Returns:
            Сущность вебхука или None
        """
        stmt = select(WebhookSubscription).where(WebhookSubscription.id == entity_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        
        return self._to_entity(model) if model else None
    
    async def get_all(self) -> List[WebhookEntity]:
        """
        Получить все вебхуки.
        
        Returns:
            Список сущностей вебхуков
        """
        stmt = select(WebhookSubscription)
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        
        return [self._to_entity(model) for model in models]
    
    async def get_by_ms_webhook_id(self, ms_webhook_id: str) -> Optional[WebhookEntity]:
        """
        Получить вебхук по ID МойСклад.
        
        Args:
            ms_webhook_id: ID вебхука в МойСклад
            
        Returns:
            Сущность вебхука или None
        """
        stmt = select(WebhookSubscription).where(
            WebhookSubscription.ms_webhook_id == ms_webhook_id
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        
        return self._to_entity(model) if model else None
    
    async def get_by_payment_type(self, payment_type: PaymentType) -> Optional[WebhookEntity]:
        """
        Получить вебхук по типу платежа.
        
        Args:
            payment_type: Тип платежа
            
        Returns:
            Сущность вебхука или None
        """
        stmt = select(WebhookSubscription).where(
            WebhookSubscription.payment_type == payment_type
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        
        return self._to_entity(model) if model else None
    
    async def get_status_dict(self) -> Dict[str, bool]:
        """
        Получить словарь статусов всех вебхуков.
        
        Returns:
            Словарь {payment_type: enabled}
        """
        webhooks = await self.get_all()
        return {webhook.payment_type.value: webhook.enabled for webhook in webhooks}
    
    async def add(self, entity: WebhookEntity) -> WebhookEntity:
        """
        Добавить новый вебхук.
        
        Args:
            entity: Сущность вебхука
            
        Returns:
            Добавленная сущность
            
        Raises:
            RepositoryError: При ошибке добавления
        """
        try:
            model = self._to_model(entity)
            self._session.add(model)
            await self._session.flush()
            await self._session.refresh(model)
            return self._to_entity(model)
        except Exception as exc:
            raise RepositoryError(
                "Ошибка при добавлении вебхука",
                details={"error": str(exc)},
            ) from exc
    
    async def update(self, entity: WebhookEntity) -> WebhookEntity:
        """
        Обновить существующий вебхук.
        
        Args:
            entity: Сущность вебхука
            
        Returns:
            Обновленная сущность
            
        Raises:
            RepositoryError: При ошибке обновления
        """
        try:
            stmt = select(WebhookSubscription).where(
                WebhookSubscription.ms_webhook_id == entity.ms_webhook_id
            )
            result = await self._session.execute(stmt)
            model = result.scalar_one_or_none()
            
            if not model:
                raise RepositoryError(
                    f"Вебхук с ms_webhook_id={entity.ms_webhook_id} не найден"
                )
            
            model.payment_type = entity.payment_type
            model.entity_type = entity.entity_type
            model.action = entity.action
            model.url = entity.url
            model.ms_href = entity.ms_href
            model.ms_account_id = entity.ms_account_id
            model.enabled = entity.enabled
            
            await self._session.flush()
            await self._session.refresh(model)
            return self._to_entity(model)
        except RepositoryError:
            raise
        except Exception as exc:
            raise RepositoryError(
                "Ошибка при обновлении вебхука",
                details={"error": str(exc)},
            ) from exc
    
    async def upsert(self, entity: WebhookEntity) -> WebhookEntity:
        """
        Создать или обновить вебхук.
        
        Args:
            entity: Сущность вебхука
            
        Returns:
            Сущность вебхука
        """
        existing = await self.get_by_ms_webhook_id(entity.ms_webhook_id)
        
        if existing:
            entity.id = existing.id
            return await self.update(entity)
        else:
            return await self.add(entity)
    
    async def delete(self, entity_id: int) -> None:
        """
        Удалить вебхук по ID.
        
        Args:
            entity_id: ID вебхука
            
        Raises:
            RepositoryError: При ошибке удаления
        """
        try:
            stmt = select(WebhookSubscription).where(WebhookSubscription.id == entity_id)
            result = await self._session.execute(stmt)
            model = result.scalar_one_or_none()
            
            if model:
                await self._session.delete(model)
                await self._session.flush()
        except Exception as exc:
            raise RepositoryError(
                "Ошибка при удалении вебхука",
                details={"error": str(exc)},
            ) from exc
    
    @staticmethod
    def _to_entity(model: WebhookSubscription) -> WebhookEntity:
        """
        Преобразовать модель БД в доменную сущность.
        
        Args:
            model: Модель SQLAlchemy
            
        Returns:
            Доменная сущность
        """
        return WebhookEntity(
            id=model.id,
            payment_type=model.payment_type,
            entity_type=model.entity_type,
            action=model.action,
            url=model.url,
            ms_webhook_id=model.ms_webhook_id,
            ms_href=model.ms_href,
            ms_account_id=model.ms_account_id,
            enabled=model.enabled,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
    
    @staticmethod
    def _to_model(entity: WebhookEntity) -> WebhookSubscription:
        """
        Преобразовать доменную сущность в модель БД.
        
        Args:
            entity: Доменная сущность
            
        Returns:
            Модель SQLAlchemy
        """
        return WebhookSubscription(
            id=entity.id,
            payment_type=entity.payment_type,
            entity_type=entity.entity_type,
            action=entity.action,
            url=entity.url,
            ms_webhook_id=entity.ms_webhook_id,
            ms_href=entity.ms_href,
            ms_account_id=entity.ms_account_id,
            enabled=entity.enabled,
        )