"""Database connection and session management."""
import logging
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel, create_engine
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import sessionmaker

from config import settings

logger = logging.getLogger(__name__)

# Async engine for application use
async_engine = create_async_engine(
    settings.database_url,
    echo=settings.log_level == "DEBUG",
    future=True,
    pool_pre_ping=True,
)

# Sync engine for Alembic migrations
sync_engine = create_engine(
    settings.database_sync_url,
    echo=settings.log_level == "DEBUG",
    future=True,
    pool_pre_ping=True,
)

# Async session factory
async_session_maker = sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def init_db():
    """Initialize database tables."""
    async with async_engine.begin() as conn:
        # Create pgvector extension
        await conn.execute(SQLModel.metadata.create_all(bind=conn))
        logger.info("Database tables created successfully")


async def close_db():
    """Close database connections."""
    await async_engine.dispose()
    logger.info("Database connections closed")


@asynccontextmanager
async def get_session() -> AsyncSession:
    """Get async database session."""
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
