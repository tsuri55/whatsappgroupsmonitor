"""Database connection and session management."""
import logging
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
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
        # Try to create pgvector extension
        try:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            logger.info("✓ pgvector extension is available")
        except Exception as e:
            logger.error("=" * 80)
            logger.error("CRITICAL ERROR: pgvector extension is not available!")
            logger.error("=" * 80)
            logger.error("The database you're connected to does not have pgvector installed.")
            logger.error("")
            logger.error("In Railway Dashboard:")
            logger.error("1. Delete your current PostgreSQL service")
            logger.error("2. Click 'New' → 'Database' → Select 'PostgreSQL' with pgvector template")
            logger.error("3. Copy the new DATABASE_URL from the pgvector service")
            logger.error("4. Update your shared variables with the new DATABASE_URL")
            logger.error("")
            logger.error(f"Current DATABASE_URL: {settings.database_url[:50]}...")
            logger.error("=" * 80)
            raise RuntimeError(
                "pgvector extension is required but not available. "
                "Please use a PostgreSQL database with pgvector installed. "
                "In Railway, create a new service using the pgvector template."
            ) from e

        # Create all tables using run_sync
        await conn.run_sync(SQLModel.metadata.create_all)
        logger.info("✓ Database tables created successfully")


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
