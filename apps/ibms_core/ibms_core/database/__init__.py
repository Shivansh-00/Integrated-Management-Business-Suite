"""
IBMS Supabase Database Layer
==============================
Async + Sync Supabase client for FastAPI integration.
"""

from ibms_core.database.supabase_connection import (
    close_supabase,
    connect_supabase,
    get_supabase_async,
    get_supabase_sync,
)

__all__ = [
    "connect_supabase",
    "close_supabase",
    "get_supabase_async",
    "get_supabase_sync",
]
