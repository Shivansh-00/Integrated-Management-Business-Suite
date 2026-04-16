"""
Supabase Connection Manager
==============================
Provides both sync and async Supabase clients.
  • Sync client  → used by auth_engine, background jobs
  • Async client → used by FastAPI endpoints (server.py)
"""

from __future__ import annotations

import logging
import os
import time as _time
from typing import Optional

from supabase import create_client, Client
from supabase import acreate_client, AsyncClient

logger = logging.getLogger("ibms.supabase")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

# ---------------------------------------------------------------------------
# Async client — used by FastAPI / server.py
# ---------------------------------------------------------------------------
_async_client: Optional[AsyncClient] = None

# ---------------------------------------------------------------------------
# Sync client — used by auth_engine, jobs, etc.
# ---------------------------------------------------------------------------
_sync_client: Optional[Client] = None

# Availability cache: skip sync calls when known to be down
_sync_available: bool = True
_sync_last_fail: float = 0.0
_SYNC_COOLDOWN: float = 60.0

# Availability cache: skip async calls when known to be down
_async_available: bool = True
_async_last_fail: float = 0.0
_ASYNC_COOLDOWN: float = 60.0


# ===================================================================
# ASYNC CLIENT — for FastAPI endpoints
# ===================================================================

async def connect_supabase() -> AsyncClient:
    """Establish async Supabase connection."""
    global _async_client

    if not SUPABASE_URL or not SUPABASE_KEY:
        raise RuntimeError("SUPABASE_URL and SUPABASE_KEY must be set")

    _async_client = await acreate_client(SUPABASE_URL, SUPABASE_KEY)
    logger.info("Supabase async connected: %s", SUPABASE_URL)
    return _async_client


async def close_supabase():
    """Close async Supabase connection."""
    global _async_client
    _async_client = None
    logger.info("Supabase async connection closed")


def get_supabase_async() -> AsyncClient:
    """Get the async Supabase client instance."""
    if _async_client is None:
        raise RuntimeError("Supabase not connected. Call connect_supabase() first.")
    return _async_client


# ===================================================================
# SYNC CLIENT — for auth_engine, background jobs
# ===================================================================

def _ensure_sync_client():
    """Lazily initialize the sync Supabase client."""
    global _sync_client
    if _sync_client is None:
        if not SUPABASE_URL or not SUPABASE_KEY:
            raise RuntimeError("SUPABASE_URL and SUPABASE_KEY must be set")
        _sync_client = create_client(SUPABASE_URL, SUPABASE_KEY)
        logger.info("Supabase sync connected: %s", SUPABASE_URL)


def get_supabase_sync() -> Client:
    """Get the sync Supabase client instance."""
    _ensure_sync_client()
    return _sync_client


# ===================================================================
# AVAILABILITY HELPERS (cooldown pattern)
# ===================================================================

def sync_supabase_is_available() -> bool:
    """Return True if sync Supabase is believed reachable (or cooldown expired)."""
    global _sync_available, _sync_last_fail
    if _sync_available:
        return True
    if (_time.time() - _sync_last_fail) >= _SYNC_COOLDOWN:
        _sync_available = True
        logger.info("Supabase sync cooldown expired — retrying")
        return True
    return False


def mark_sync_supabase_down():
    """Call after a sync Supabase operation fails to enable the cooldown."""
    global _sync_available, _sync_last_fail
    if _sync_available:
        logger.warning("Marking sync Supabase as unavailable for %ss", _SYNC_COOLDOWN)
    _sync_available = False
    _sync_last_fail = _time.time()


def async_supabase_is_available() -> bool:
    """Return True if async Supabase is believed reachable (or cooldown expired)."""
    global _async_available, _async_last_fail
    if _async_available:
        return True
    if (_time.time() - _async_last_fail) >= _ASYNC_COOLDOWN:
        _async_available = True
        logger.info("Supabase async cooldown expired — retrying")
        return True
    return False


def mark_async_supabase_down():
    """Call after an async Supabase operation fails to enable the cooldown."""
    global _async_available, _async_last_fail
    if _async_available:
        logger.warning("Marking async Supabase as unavailable for %ss", _ASYNC_COOLDOWN)
    _async_available = False
    _async_last_fail = _time.time()
