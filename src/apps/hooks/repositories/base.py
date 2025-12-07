"""Базовый абстрактный репозиторий."""

from abc import ABC, abstractmethod
from typing import Generic, List, Optional, TypeVar

from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar("T")


class AbstractRepository(ABC, Generic[T]):
    """Абстрактный базовый репозиторий."""
    
    def __init__(self, session: AsyncSession) -> None:
        """
        Инициализировать репозиторий.
        
        Args:
            session: Асинхронная сессия SQLAlchemy
        """
        self._session = session
    
    @abstractmethod
    async def get_by_id(self, entity_id: int) -> Optional[T]:
        """
        Получить сущность по ID.
        
        Args:
            entity_id: ID сущности
            
        Returns:
            Сущность или None
        """
        raise NotImplementedError
    
    @abstractmethod
    async def get_all(self) -> List[T]:
        """
        Получить все сущности.
        
        Returns:
            Список сущностей
        """
        raise NotImplementedError
    
    @abstractmethod
    async def add(self, entity: T) -> T:
        """
        Добавить новую сущность.
        
        Args:
            entity: Сущность для добавления
            
        Returns:
            Добавленная сущность
        """
        raise NotImplementedError
    
    @abstractmethod
    async def update(self, entity: T) -> T:
        """
        Обновить существующую сущность.
        
        Args:
            entity: Сущность для обновления
            
        Returns:
            Обновленная сущность
        """
        raise NotImplementedError
    
    @abstractmethod
    async def delete(self, entity_id: int) -> None:
        """
        Удалить сущность по ID.
        
        Args:
            entity_id: ID сущности
        """
        raise NotImplementedError