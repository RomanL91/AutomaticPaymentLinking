from abc import ABC
from typing import Generic, List, Optional, Type, TypeVar

from sqlalchemy import delete, insert, select, update
from sqlalchemy.engine import Result
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeMeta

T = TypeVar("T", bound=DeclarativeMeta)


class SQLAlchemyRepository(ABC, Generic[T]):
    """Базовый репозиторий для работы с SQLAlchemy."""
    
    model: Type[T] = None
    
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
    
    async def create(self, **data) -> T:
        """Создать объект."""
        stmt = insert(self.model).values(**data).returning(self.model)
        result: Result = await self._session.execute(stmt)
        return result.scalar_one()
    
    async def get_all(self, order_by=None) -> List[T]:
        """Получить все объекты."""
        stmt = select(self.model).where(self.model.is_active == True)
        if order_by is not None:
            stmt = stmt.order_by(order_by)
        result: Result = await self._session.execute(stmt)
        return list(result.scalars().all())
    
    async def get_by_id(self, obj_id: str) -> Optional[T]:
        """Получить объект по ID."""
        stmt = select(self.model).where(
            self.model.id == obj_id,
            self.model.is_active == True,
        )
        try:
            result: Result = await self._session.execute(stmt)
            return result.scalar_one()
        except NoResultFound:
            return None
    
    async def get_one(self, **filter_by) -> Optional[T]:
        """Получить один объект по фильтру."""
        stmt = select(self.model).filter_by(**filter_by, is_active=True)
        try:
            result: Result = await self._session.execute(stmt)
            return result.scalar_one()
        except NoResultFound:
            return None
    
    async def update(self, obj_id: str, **data) -> Optional[T]:
        """Обновить объект."""
        stmt = (
            update(self.model)
            .where(self.model.id == obj_id, self.model.is_active == True)
            .values(**data)
            .returning(self.model)
        )
        result: Result = await self._session.execute(stmt)
        updated_obj = result.scalar_one_or_none()
        if updated_obj is None:
            raise ValueError(f"Object with id={obj_id} not found")
        return updated_obj
    
    async def soft_delete(self, obj_id: str) -> None:
        """Мягкое удаление объекта."""
        await self.update(obj_id, is_active=False)
    
    async def hard_delete(self, **filter_by) -> None:
        """Жесткое удаление объекта."""
        stmt = delete(self.model).filter_by(**filter_by)
        result = await self._session.execute(stmt)
        if result.rowcount == 0:
            raise ValueError(f"Object with filters {filter_by} not found")