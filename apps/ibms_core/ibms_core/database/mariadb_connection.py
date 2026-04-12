"""
MariaDB Connection Manager (SQLAlchemy Async)
===============================================
Dual-database architecture:
  • MongoDB  → documents, analytics, real-time data, auth
  • MariaDB  → relational ERP data (customers, products, orders, invoices, inventory, employees)
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text

logger = logging.getLogger("ibms.mariadb")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
MARIADB_URI = os.getenv(
    "MARIADB_URI",
    "mysql+aiomysql://ibms_user:ibms_secure_password@localhost:3306/ibms_enterprise",
)

# ---------------------------------------------------------------------------
# Engine & Session Factory
# ---------------------------------------------------------------------------
_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


class Base(DeclarativeBase):
    """Declarative base for all MariaDB ORM models."""
    pass


async def connect_mariadb() -> AsyncEngine:
    """Create the async engine and initialize tables."""
    global _engine, _session_factory

    _engine = create_async_engine(
        MARIADB_URI,
        pool_size=20,
        max_overflow=10,
        pool_recycle=1800,
        pool_pre_ping=True,
        echo=False,
    )
    _session_factory = async_sessionmaker(
        bind=_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    # Verify connection
    async with _engine.begin() as conn:
        await conn.execute(text("SELECT 1"))
    logger.info("MariaDB connected: %s", MARIADB_URI.split("@")[-1])

    # Create all tables
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("MariaDB tables created / verified")

    return _engine


async def close_mariadb():
    """Dispose of the async engine."""
    global _engine, _session_factory
    if _engine:
        await _engine.dispose()
        _engine = None
        _session_factory = None
        logger.info("MariaDB connection closed")


def get_engine() -> AsyncEngine:
    if _engine is None:
        raise RuntimeError("MariaDB not connected. Call connect_mariadb() first.")
    return _engine


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async session with auto-commit/rollback."""
    if _session_factory is None:
        raise RuntimeError("MariaDB not connected. Call connect_mariadb() first.")
    session = _session_factory()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()
