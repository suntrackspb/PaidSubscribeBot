"""
Конфигурация базы данных для PaidSubscribeBot.
Поддерживает SQLite для разработки и PostgreSQL для продакшена.
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import StaticPool
from typing import AsyncGenerator

from app.config.settings import get_settings


settings = get_settings()

# Базовый класс для моделей ORM
Base = declarative_base()


def get_database_url(async_mode: bool = True) -> str:
    """
    Получение URL для подключения к базе данных.
    
    Args:
        async_mode: Если True, возвращает URL для асинхронного подключения
        
    Returns:
        str: URL для подключения к БД
    """
    url = settings.database_url
    
    if async_mode:
        if url.startswith("sqlite:///"):
            # Для SQLite меняем на aiosqlite
            return url.replace("sqlite:///", "sqlite+aiosqlite:///")
        elif url.startswith("postgresql://"):
            # Для PostgreSQL меняем на asyncpg
            return url.replace("postgresql://", "postgresql+asyncpg://")
    
    return url


# Создание асинхронного движка базы данных
if settings.database_url.startswith("sqlite"):
    # Настройки для SQLite
    async_engine = create_async_engine(
        get_database_url(async_mode=True),
        poolclass=StaticPool,
        connect_args={
            "check_same_thread": False,
        },
        echo=settings.debug,
    )
else:
    # Настройки для PostgreSQL
    async_engine = create_async_engine(
        get_database_url(async_mode=True),
        echo=settings.debug,
        pool_size=10,
        max_overflow=20,
    )

# Создание синхронного движка для миграций
sync_engine = create_engine(
    get_database_url(async_mode=False),
    echo=settings.debug,
)

# Создание фабрики асинхронных сессий
AsyncSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Создание фабрики синхронных сессий
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=sync_engine,
)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Генератор для получения асинхронной сессии базы данных.
    Используется как dependency в FastAPI.
    
    Yields:
        AsyncSession: Асинхронная сессия базы данных
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def get_sync_session():
    """
    Генератор для получения синхронной сессии базы данных.
    Используется для миграций и синхронных операций.
    
    Yields:
        Session: Синхронная сессия базы данных
    """
    session = SessionLocal()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


async def init_database():
    """
    Инициализация базы данных.
    Создает все таблицы если они не существуют.
    """
    async with async_engine.begin() as conn:
        # Импортируем все модели для создания таблиц
        from app.database.models import (
            user, subscription, payment, channel
        )
        
        # Создаем все таблицы
        await conn.run_sync(Base.metadata.create_all)


async def close_database():
    """
    Закрытие соединений с базой данных.
    Вызывается при завершении работы приложения.
    """
    await async_engine.dispose() 