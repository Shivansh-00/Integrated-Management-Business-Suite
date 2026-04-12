"""
IBMS Database Initialization Script
=====================================
Seeds the MongoDB database with default users, decision rules,
and sample data. Run once after fresh install.

Usage:
    python -m scripts.init_db
    python scripts/init_db.py
"""

import os
import sys
from pathlib import Path

# Ensure the ibms_core package is importable
_BASE_DIR = Path(__file__).resolve().parent.parent
_APP_DIR = _BASE_DIR / "apps" / "ibms_core"
if str(_APP_DIR) not in sys.path:
    sys.path.insert(0, str(_APP_DIR))

from dotenv import load_dotenv
load_dotenv()

from ibms_core.database.connection import get_sync_db, get_sync_collection, MONGO_URI, MONGO_DB_NAME
from ibms_core.database.models import UserOps, AuditOps


def seed_database():
    """Initialize database with default data."""
    print(f"Connecting to MongoDB: {MONGO_URI}")
    print(f"Database: {MONGO_DB_NAME}")

    db = get_sync_db()

    # Verify connection
    db.client.admin.command("ping")
    print("MongoDB connection successful!\n")

    # ---------------------------------------------------------------
    # 1. Create collections explicitly (optional but clean)
    # ---------------------------------------------------------------
    collections_to_create = [
        "users", "kpi_snapshots", "kpi_latest", "ai_recommendations",
        "enterprise_profiles", "webhook_logs", "smart_decision_rules",
        "ai_alerts", "audit_logs", "notifications", "refresh_tokens",
        "rate_limits", "csrf_tokens",
    ]
    existing = db.list_collection_names()
    for col_name in collections_to_create:
        if col_name not in existing:
            db.create_collection(col_name)
            print(f"  Created collection: {col_name}")
        else:
            print(f"  Collection exists:  {col_name}")

    # ---------------------------------------------------------------
    # 2. Create indexes (sync version)
    # ---------------------------------------------------------------
    print("\nCreating indexes...")

    db["users"].create_index("email", unique=True)
    db["users"].create_index("username", unique=True)
    db["users"].create_index("role")
    db["users"].create_index("is_active")

    db["kpi_snapshots"].create_index([("company", 1), ("recorded_at", -1)])
    db["kpi_snapshots"].create_index("recorded_at")

    db["ai_recommendations"].create_index([("company", 1), ("status", 1), ("generated_at", -1)])

    db["enterprise_profiles"].create_index("user_id", unique=True)

    db["webhook_logs"].create_index([("provider", 1), ("processed", 1), ("received_at", -1)])

    db["smart_decision_rules"].create_index("module")

    db["ai_alerts"].create_index([("severity", 1), ("status", 1)])
    db["ai_alerts"].create_index("created_at")

    db["audit_logs"].create_index([("event_type", 1), ("timestamp", -1)])
    db["audit_logs"].create_index("user_id")

    db["notifications"].create_index([("target_user", 1), ("timestamp", -1)])

    db["refresh_tokens"].create_index("token", unique=True)
    db["refresh_tokens"].create_index("user_id")

    db["rate_limits"].create_index("key", unique=True)

    db["csrf_tokens"].create_index("token", unique=True)

    db["kpi_latest"].create_index("company", unique=True)

    print("  Indexes created successfully!")

    # ---------------------------------------------------------------
    # 3. Seed default users
    # ---------------------------------------------------------------
    print("\nSeeding default users...")
    from ibms_core.security.auth_engine import hash_password  # noqa: import here after DB is ready

    seed_users = [
        {"username": "admin",   "email": "admin@ibms.dev",   "password": "Admin@IBMS2026",   "role": "super_admin"},
        {"username": "analyst", "email": "analyst@ibms.dev", "password": "Analyst@2026",      "role": "analyst"},
        {"username": "manager", "email": "manager@ibms.dev", "password": "Manager@2026",      "role": "manager"},
    ]
    for u in seed_users:
        if UserOps.exists_by_username(u["username"]) or UserOps.exists_by_email(u["email"]):
            print(f"  Skipped: {u['username']} (already exists)")
            continue
        UserOps.create(
            email=u["email"],
            username=u["username"],
            password_hash=hash_password(u["password"]),
            role=u["role"],
            is_active=True,
            is_verified=True,
        )
        print(f"  Created: {u['username']} ({u['role']}) — password: {u['password']}")
    else:
        print("  Skipped: manager (already exists)")

    # ---------------------------------------------------------------
    # 4. Seed smart decision rules
    # ---------------------------------------------------------------
    print("\nSeeding decision rules...")

    rules_col = db["smart_decision_rules"]
    default_rules = [
        {"rule_name": "High-Value Transaction Review", "module": "Accounting", "threshold": 75.0, "is_enabled": True},
        {"rule_name": "Inventory Reorder Alert", "module": "Inventory", "threshold": 50.0, "is_enabled": True},
        {"rule_name": "CRM Lead Auto-Qualify", "module": "CRM", "threshold": 65.0, "is_enabled": True},
        {"rule_name": "HR Overtime Approval", "module": "HR", "threshold": 40.0, "is_enabled": True},
        {"rule_name": "Procurement Budget Gate", "module": "Procurement", "threshold": 80.0, "is_enabled": True},
        {"rule_name": "Asset Depreciation Review", "module": "Assets", "threshold": 60.0, "is_enabled": True},
    ]
    for rule in default_rules:
        if rules_col.count_documents({"rule_name": rule["rule_name"]}, limit=1) == 0:
            rules_col.insert_one({**rule, "rule_id": str(__import__("uuid").uuid4())})
            print(f"  Created rule: {rule['rule_name']}")
        else:
            print(f"  Skipped rule: {rule['rule_name']} (exists)")

    # ---------------------------------------------------------------
    # 5. Audit the initialization
    # ---------------------------------------------------------------
    AuditOps.create(
        event_type="system_init",
        details={"message": "Database initialized with seed data"},
    )

    # ---------------------------------------------------------------
    # Summary
    # ---------------------------------------------------------------
    print("\n" + "=" * 55)
    print("  IBMS MongoDB Initialization Complete!")
    print("=" * 55)
    print(f"  Database:     {MONGO_DB_NAME}")
    print(f"  Collections:  {len(collections_to_create)}")
    print(f"  Users:        {UserOps.count()}")
    print(f"  Rules:        {rules_col.count_documents({})}")
    print("=" * 55)


if __name__ == "__main__":
    seed_database()
