"""
MongoDB Connection Manager
============================
Handles both async (Motor) and sync (PyMongo) connections.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorCollection
from pymongo import MongoClient
from pymongo.database import Database as SyncDatabase
from pymongo.collection import Collection as SyncCollection

logger = logging.getLogger("ibms.database")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "ibms_enterprise")

# ---------------------------------------------------------------------------
# Async client (Motor) — used by FastAPI / server.py
# ---------------------------------------------------------------------------
_async_client: Optional[AsyncIOMotorClient] = None
_async_db: Optional[AsyncIOMotorDatabase] = None

# ---------------------------------------------------------------------------
# Sync client (PyMongo) — used by auth_engine, jobs, etc.
# ---------------------------------------------------------------------------
_sync_client: Optional[MongoClient] = None
_sync_db: Optional[SyncDatabase] = None


# ===================================================================
# ASYNC (Motor) — for FastAPI endpoints
# ===================================================================

async def connect_db() -> AsyncIOMotorDatabase:
    """Establish async MongoDB connection and create indexes."""
    global _async_client, _async_db

    _async_client = AsyncIOMotorClient(
        MONGO_URI,
        maxPoolSize=50,
        minPoolSize=5,
        serverSelectionTimeoutMS=5000,
        connectTimeoutMS=5000,
    )
    _async_db = _async_client[MONGO_DB_NAME]

    # Verify connection
    await _async_client.admin.command("ping")
    logger.info("MongoDB async connected: %s / %s", MONGO_URI, MONGO_DB_NAME)

    # Create indexes
    await _create_indexes(_async_db)

    return _async_db


async def close_db():
    """Close async MongoDB connection."""
    global _async_client, _async_db
    if _async_client:
        _async_client.close()
        _async_client = None
        _async_db = None
        logger.info("MongoDB async connection closed")


def get_db() -> AsyncIOMotorDatabase:
    """Get the async database instance."""
    if _async_db is None:
        raise RuntimeError("MongoDB not connected. Call connect_db() first.")
    return _async_db


def get_collection(name: str) -> AsyncIOMotorCollection:
    """Get an async collection by name."""
    return get_db()[name]


# ===================================================================
# SYNC (PyMongo) — for auth_engine, background jobs
# ===================================================================

def _ensure_sync_client():
    """Lazily initialize the sync PyMongo client."""
    global _sync_client, _sync_db
    if _sync_client is None:
        _sync_client = MongoClient(
            MONGO_URI,
            maxPoolSize=20,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000,
        )
        _sync_db = _sync_client[MONGO_DB_NAME]
        logger.info("MongoDB sync connected: %s / %s", MONGO_URI, MONGO_DB_NAME)


def get_sync_db() -> SyncDatabase:
    """Get the sync database instance."""
    _ensure_sync_client()
    return _sync_db


def get_sync_collection(name: str) -> SyncCollection:
    """Get a sync collection by name."""
    return get_sync_db()[name]


# ===================================================================
# INDEX CREATION
# ===================================================================

async def _create_indexes(db: AsyncIOMotorDatabase):
    """Create all required indexes for optimal query performance."""

    # --- users ---
    users = db["users"]
    await users.create_index("email", unique=True)
    await users.create_index("username", unique=True)
    await users.create_index("role")
    await users.create_index("is_active")

    # --- kpi_snapshots ---
    kpi = db["kpi_snapshots"]
    await kpi.create_index([("company", 1), ("recorded_at", -1)])
    await kpi.create_index("recorded_at")
    await kpi.create_index("metric_code")

    # --- ai_recommendations ---
    ai_rec = db["ai_recommendations"]
    await ai_rec.create_index([("company", 1), ("status", 1), ("generated_at", -1)])
    await ai_rec.create_index("context_type")

    # --- enterprise_profiles ---
    profiles = db["enterprise_profiles"]
    await profiles.create_index("user_id", unique=True)
    await profiles.create_index("department")

    # --- webhook_logs ---
    webhooks = db["webhook_logs"]
    await webhooks.create_index([("provider", 1), ("processed", 1), ("received_at", -1)])
    await webhooks.create_index("event_type")

    # --- smart_decision_rules ---
    rules = db["smart_decision_rules"]
    await rules.create_index("module")
    await rules.create_index("is_enabled")

    # --- ai_alerts ---
    alerts = db["ai_alerts"]
    await alerts.create_index([("severity", 1), ("status", 1)])
    await alerts.create_index("created_at")

    # --- audit_logs ---
    audit = db["audit_logs"]
    await audit.create_index([("event_type", 1), ("timestamp", -1)])
    await audit.create_index("user_id")
    await audit.create_index("timestamp")

    # --- notifications ---
    notifs = db["notifications"]
    await notifs.create_index([("target_user", 1), ("timestamp", -1)])
    await notifs.create_index("read")

    # --- refresh_tokens ---
    tokens = db["refresh_tokens"]
    await tokens.create_index("token", unique=True)
    await tokens.create_index("user_id")
    await tokens.create_index("family")
    await tokens.create_index("expires_at", expireAfterSeconds=0)  # TTL index

    # --- rate_limits ---
    rate = db["rate_limits"]
    await rate.create_index("key", unique=True)
    await rate.create_index("locked_until")

    # --- csrf_tokens ---
    csrf = db["csrf_tokens"]
    await csrf.create_index("token", unique=True)
    await csrf.create_index("expires_at", expireAfterSeconds=0)  # TTL index

    # --- sessions / kpi_latest (materialized view for fast dashboard) ---
    kpi_latest = db["kpi_latest"]
    await kpi_latest.create_index("company", unique=True)

    logger.info("MongoDB indexes created successfully")
