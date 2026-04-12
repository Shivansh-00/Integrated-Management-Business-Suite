"""
IBMS MongoDB Database Layer
============================
Async MongoDB connection via Motor for FastAPI integration.
Sync PyMongo fallback for non-async contexts (auth_engine, jobs).
"""

from ibms_core.database.connection import (
    connect_db,
    close_db,
    get_db,
    get_sync_db,
    get_collection,
    get_sync_collection,
)

__all__ = [
    "connect_db",
    "close_db",
    "get_db",
    "get_sync_db",
    "get_collection",
    "get_sync_collection",
]
