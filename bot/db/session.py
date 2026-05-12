from typing import Optional
"""Async-движок и фабрика сессий SQLAlchemy."""

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine, AsyncSession

from bot.config import settings


engine = create_async_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=5,
    echo=False,
)

async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_session() -> AsyncSession:
    """Получить сессию (использовать с async with)."""
    async with async_session_maker() as session:
        yield session
