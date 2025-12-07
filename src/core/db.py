from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import declarative_base

from .config import settings

# Async engine
engine = create_async_engine(
    settings.database_url,
    echo=False,   # можно True, если хочешь видеть SQL
    future=True,
)

# Session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    expire_on_commit=False,
    class_=AsyncSession,
)

# Базовый класс моделей
Base = declarative_base()


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency для FastAPI: даёт AsyncSession и закрывает его после запроса.
    """
    async with AsyncSessionLocal() as session:
        yield session


async def init_db() -> None:
    """
    Инициализация БД: создаём таблицы для всех моделей.
    Для этого нужно импортировать модели перед create_all.
    """
    # Импортируем модели, чтобы они зарегистрировались в Base.metadata
    import src.apps.hooks.models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
