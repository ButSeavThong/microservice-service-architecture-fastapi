# app/db/session.py

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)


# ── Engine ────────────────────────────────────────────────────────────────────

engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_timeout=settings.DATABASE_POOL_TIMEOUT,
    pool_pre_ping=True,   # ← CRITICAL for production
    echo=settings.DATABASE_ECHO,
)

"""
WHY pool_pre_ping=True?

Without it: A connection sitting idle in the pool for >8 hours
gets killed by PostgreSQL's TCP keepalive timeout. When your
service tries to reuse it, it fails with a cryptic error.

With pool_pre_ping=True: SQLAlchemy sends a cheap "SELECT 1"
before handing out a connection. If it's dead, it's discarded
and a fresh one is used. Zero downtime.

This is non-negotiable in production.

WHY pool_size + max_overflow?
pool_size=10: Keep 10 connections always open and ready.
max_overflow=20: Allow burst up to 30 total under load.
After burst subsides, extras are closed.

In production, tune these based on:
- PostgreSQL max_connections setting (usually 100-200)
- Number of service replicas (3 replicas × 30 = 90 connections)
- Never exhaust DB connection limits!
"""

# ── Session Factory ───────────────────────────────────────────────────────────

AsyncSessionFactory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

"""
WHY expire_on_commit=False?

Default SQLAlchemy behavior: after commit(), all ORM object attributes
are "expired" — meaning the next access triggers a lazy DB reload.

In an async context, that lazy reload would fire an async query
OUTSIDE a session context = crash.

expire_on_commit=False: Objects retain their values after commit.
Safe to return them from service methods, serialize them to JSON.

WHY autoflush=False?
With autoflush=True (default), SQLAlchemy might issue a flush
(write to DB buffer) at unexpected moments — like when you do
a query in the middle of building multiple objects.

explicit > implicit. We control when flushes happen.
"""


# ── Dependency-Injection Provider ─────────────────────────────────────────────

async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that provides a request-scoped database session.

    LIFECYCLE per request:
    1. FastAPI calls this generator before your route handler.
    2. A new AsyncSession is created from the factory.
    3. Your route handler runs with this session.
    4. On success: session closes, connection returns to pool.
    5. On exception: session closes (no commit), connection returns to pool.

    Spring Boot equivalent:
    This is your @Transactional method scope — each request gets
    its own unit of work. The connection is borrowed from HikariCP
    (your pool_size equivalent) and returned after the request.

    WHY NOT a global session?
    A global session in async code is a concurrency disaster.
    Session state (pending objects, identity map) would bleed
    across concurrent requests. Each request MUST have isolation.
    """
    async with AsyncSessionFactory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ── Service-layer / non-request contexts ──────────────────────────────────────

@asynccontextmanager
async def get_session_context() -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager for obtaining a session OUTSIDE of FastAPI
    dependency injection — e.g., Kafka consumers, background tasks,
    startup scripts.

    Usage:
        async with get_session_context() as session:
            await profile_repo.create(session, profile_data)

    WHY separate from get_db_session()?
    get_db_session() is a FastAPI-specific async generator designed
    for Depends(). Kafka consumers don't go through FastAPI's DI
    system — they need a standalone context manager.
    """
    async with AsyncSessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()