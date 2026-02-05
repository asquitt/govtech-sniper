"""
RFP Sniper - Database Connection & Session Management
======================================================
Async PostgreSQL connection using SQLModel + SQLAlchemy.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from sqlmodel import SQLModel

from app.config import settings

# =============================================================================
# Async Engine Configuration
# =============================================================================

# Create async engine with connection pooling
# NullPool is used for Celery workers to avoid connection issues
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,  # Log SQL queries in debug mode
    future=True,
    pool_pre_ping=True,  # Verify connections before use
)

# Session factory for dependency injection
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


# =============================================================================
# Database Lifecycle
# =============================================================================

async def init_db() -> None:
    """
    Initialize database tables.
    Called on application startup.
    
    Note: In production, use Alembic migrations instead.
    """
    async with engine.begin() as conn:
        # Import all models to ensure they're registered with SQLModel
        from app.models import (  # noqa: F401
            user,
            rfp,
            proposal,
            knowledge_base,
            opportunity_snapshot,
            audit,
            integration,
            webhook,
            dash,
            capture,
            contract,
            saved_search,
            award,
            contact,
            word_addin,
            graphics,
        )
        
        # Create all tables (dev only - use Alembic in production)
        await conn.run_sync(SQLModel.metadata.create_all)


async def close_db() -> None:
    """
    Close database connections.
    Called on application shutdown.
    """
    await engine.dispose()


# =============================================================================
# Dependency Injection
# =============================================================================

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that provides a database session.
    
    Usage:
        @router.get("/items")
        async def get_items(session: AsyncSession = Depends(get_session)):
            ...
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_session_context() -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager for database sessions outside of FastAPI routes.
    Useful for Celery tasks and scripts.
    
    Usage:
        async with get_session_context() as session:
            result = await session.execute(query)
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# =============================================================================
# Celery-specific Engine (NullPool for worker processes)
# =============================================================================

def get_celery_engine():
    """
    Create a new engine for Celery workers with NullPool.
    This prevents connection sharing issues across forked processes.
    """
    return create_async_engine(
        settings.database_url,
        echo=False,
        poolclass=NullPool,
    )


@asynccontextmanager
async def get_celery_session_context() -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager for Celery tasks using a per-task engine.

    Using NullPool + per-task engine avoids event loop conflicts
    when Celery runs tasks with fresh event loops.
    """
    engine = get_celery_engine()
    session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
            await engine.dispose()
