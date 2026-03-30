from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

# Async engine — connection pool to PostgreSQL via asyncpg
engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
)

# Session factory — each call produces a new AsyncSession
async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@asynccontextmanager
async def task_session():
    """Create a disposable engine + session for Celery tasks.

    Each asyncio.run() in a Celery worker creates a new event loop.
    The module-level engine holds pooled connections bound to a previous
    (now-closed) loop, causing 'Future attached to a different loop' errors.
    This helper creates a fresh engine per task invocation and disposes it
    on exit, so connections never leak across loops.
    """
    task_engine = create_async_engine(
        settings.database_url,
        echo=False,
        pool_size=5,
        max_overflow=5,
        pool_pre_ping=True,
    )
    task_session_factory = async_sessionmaker(
        task_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with task_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()
    await task_engine.dispose()


# Base class for all ORM models
class Base(DeclarativeBase):
    pass


# FastAPI dependency — injects a DB session into route handlers
async def get_db():
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
