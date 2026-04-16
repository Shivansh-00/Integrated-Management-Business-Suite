"""
IBMS Database Initialization Script
=====================================
Seeds the Supabase database with default users, decision rules,
and sample data. Run once after fresh install.

Prerequisites:
    - Run scripts/supabase_schema.sql in the Supabase SQL editor first.

Usage:
    python -m scripts.init_db
    python scripts/init_db.py
"""

import os
import sys
import uuid
from pathlib import Path

# Ensure the ibms_core package is importable
_BASE_DIR = Path(__file__).resolve().parent.parent
_APP_DIR = _BASE_DIR / "apps" / "ibms_core"
if str(_APP_DIR) not in sys.path:
    sys.path.insert(0, str(_APP_DIR))

from dotenv import load_dotenv
load_dotenv()

from supabase import create_client

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")


def seed_database():
    """Initialize Supabase database with default data."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("ERROR: SUPABASE_URL and SUPABASE_KEY must be set in .env")
        sys.exit(1)

    print(f"Connecting to Supabase: {SUPABASE_URL}")
    sb = create_client(SUPABASE_URL, SUPABASE_KEY)

    # Verify connection
    sb.table("users").select("user_id", count="exact").limit(0).execute()
    print("Supabase connection successful!\n")

    # ---------------------------------------------------------------
    # 1. Seed default users
    # ---------------------------------------------------------------
    print("Seeding default users...")
    from ibms_core.security.auth_engine import hash_password

    seed_users = [
        {"username": "admin",   "email": "admin@ibms.dev",   "password": "Admin@IBMS2026",   "role": "super_admin"},
        {"username": "analyst", "email": "analyst@ibms.dev", "password": "Analyst@2026",      "role": "analyst"},
        {"username": "manager", "email": "manager@ibms.dev", "password": "Manager@2026",      "role": "manager"},
    ]
    for u in seed_users:
        existing = sb.table("users").select("user_id").eq("username", u["username"]).maybe_single().execute()
        if existing.data:
            print(f"  Skipped: {u['username']} (already exists)")
            continue
        sb.table("users").insert({
            "user_id": str(uuid.uuid4()),
            "email": u["email"],
            "username": u["username"],
            "password_hash": hash_password(u["password"]),
            "role": u["role"],
            "is_active": True,
            "is_verified": True,
        }).execute()
        print(f"  Created: {u['username']} ({u['role']})")

    # ---------------------------------------------------------------
    # 2. Seed smart decision rules
    # ---------------------------------------------------------------
    print("\nSeeding decision rules...")

    default_rules = [
        {"rule_name": "High-Value Transaction Review", "module": "Accounting", "threshold": 75.0, "is_enabled": True},
        {"rule_name": "Inventory Reorder Alert", "module": "Inventory", "threshold": 50.0, "is_enabled": True},
        {"rule_name": "CRM Lead Auto-Qualify", "module": "CRM", "threshold": 65.0, "is_enabled": True},
        {"rule_name": "HR Overtime Approval", "module": "HR", "threshold": 40.0, "is_enabled": True},
        {"rule_name": "Procurement Budget Gate", "module": "Procurement", "threshold": 80.0, "is_enabled": True},
        {"rule_name": "Asset Depreciation Review", "module": "Assets", "threshold": 60.0, "is_enabled": True},
    ]
    for rule in default_rules:
        existing = sb.table("smart_decision_rules").select("rule_id").eq("rule_name", rule["rule_name"]).maybe_single().execute()
        if existing.data:
            print(f"  Skipped rule: {rule['rule_name']} (exists)")
            continue
        sb.table("smart_decision_rules").insert({
            **rule,
            "rule_id": str(uuid.uuid4()),
        }).execute()
        print(f"  Created rule: {rule['rule_name']}")

    # ---------------------------------------------------------------
    # 3. Audit the initialization
    # ---------------------------------------------------------------
    sb.table("audit_logs").insert({
        "log_id": str(uuid.uuid4()),
        "event_type": "system_init",
        "details": {"message": "Database initialized with seed data"},
    }).execute()

    # ---------------------------------------------------------------
    # Summary
    # ---------------------------------------------------------------
    user_count = sb.table("users").select("user_id", count="exact").limit(0).execute().count
    rule_count = sb.table("smart_decision_rules").select("rule_id", count="exact").limit(0).execute().count

    print("\n" + "=" * 55)
    print("  IBMS Supabase Initialization Complete!")
    print("=" * 55)
    print(f"  Endpoint:  {SUPABASE_URL}")
    print(f"  Users:     {user_count}")
    print(f"  Rules:     {rule_count}")
    print("=" * 55)


if __name__ == "__main__":
    seed_database()
