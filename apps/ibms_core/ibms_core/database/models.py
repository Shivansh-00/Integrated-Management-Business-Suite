"""
MongoDB CRUD Operations for all IBMS collections.
===================================================
Async operations for FastAPI endpoints.
Sync operations for auth_engine, background jobs.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from ibms_core.database.connection import get_collection, get_sync_collection


# ===================================================================
# HELPERS
# ===================================================================

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return str(uuid.uuid4())


def _serialize_doc(doc: dict | None) -> dict | None:
    """Convert MongoDB _id to string for JSON serialization."""
    if doc is None:
        return None
    doc["_id"] = str(doc["_id"])
    return doc


def _serialize_docs(docs: list[dict]) -> list[dict]:
    return [_serialize_doc(d) for d in docs]


# ===================================================================
# USERS (sync — used by auth_engine)
# ===================================================================

class UserOps:
    """Sync user operations for auth_engine."""

    @staticmethod
    def col():
        return get_sync_collection("users")

    @staticmethod
    def create(*, email: str, username: str, password_hash: str, role: str = "viewer",
               is_active: bool = True, is_verified: bool = False) -> dict:
        user_id = _new_id()
        doc = {
            "user_id": user_id,
            "email": email,
            "username": username,
            "password_hash": password_hash,
            "role": role,
            "is_active": is_active,
            "is_verified": is_verified,
            "totp_secret": None,
            "totp_enabled": False,
            "created_at": _now_iso(),
            "last_login": None,
            "failed_attempts": 0,
        }
        try:
            UserOps.col().insert_one(doc)
        except Exception as e:
            if "DuplicateKeyError" in type(e).__name__ or "11000" in str(e):
                # User already exists — return existing
                existing = UserOps.find_by_username(username) or UserOps.find_by_email(email)
                if existing:
                    return existing
            raise
        return doc

    @staticmethod
    def find_by_username(username: str) -> dict | None:
        doc = UserOps.col().find_one({"username": username})
        return _serialize_doc(doc) if doc else None

    @staticmethod
    def find_by_email(email: str) -> dict | None:
        doc = UserOps.col().find_one({"email": email})
        return _serialize_doc(doc) if doc else None

    @staticmethod
    def find_by_id(user_id: str) -> dict | None:
        doc = UserOps.col().find_one({"user_id": user_id})
        return _serialize_doc(doc) if doc else None

    @staticmethod
    def find_by_username_or_email(identifier: str) -> dict | None:
        doc = UserOps.col().find_one({"$or": [{"username": identifier}, {"email": identifier}]})
        return _serialize_doc(doc) if doc else None

    @staticmethod
    def update(user_id: str, updates: dict):
        UserOps.col().update_one({"user_id": user_id}, {"$set": updates})

    @staticmethod
    def set_totp(user_id: str, secret: str | None, enabled: bool):
        UserOps.col().update_one(
            {"user_id": user_id},
            {"$set": {"totp_secret": secret, "totp_enabled": enabled}},
        )

    @staticmethod
    def record_login(user_id: str):
        UserOps.col().update_one(
            {"user_id": user_id},
            {"$set": {"last_login": _now_iso(), "failed_attempts": 0}},
        )

    @staticmethod
    def increment_failed_attempts(user_id: str):
        UserOps.col().update_one(
            {"user_id": user_id},
            {"$inc": {"failed_attempts": 1}},
        )

    @staticmethod
    def exists_by_username(username: str) -> bool:
        return UserOps.col().count_documents({"username": username}, limit=1) > 0

    @staticmethod
    def exists_by_email(email: str) -> bool:
        return UserOps.col().count_documents({"email": email}, limit=1) > 0

    @staticmethod
    def count() -> int:
        return UserOps.col().count_documents({})


# ===================================================================
# AUDIT LOGS (sync — used by auth_engine)
# ===================================================================

class AuditOps:
    """Sync audit log operations."""

    @staticmethod
    def col():
        return get_sync_collection("audit_logs")

    @staticmethod
    def create(event_type: str, user_id: str = "", ip: str = "", details: dict | None = None) -> dict:
        doc = {
            "audit_id": _new_id(),
            "event_type": event_type,
            "user_id": user_id,
            "ip": ip,
            "timestamp": _now_iso(),
            "details": details or {},
        }
        AuditOps.col().insert_one(doc)
        return doc

    @staticmethod
    def find(limit: int = 100, event_type: str = "") -> list[dict]:
        query = {}
        if event_type:
            query["event_type"] = event_type
        cursor = AuditOps.col().find(query).sort("timestamp", -1).limit(limit)
        return _serialize_docs(list(cursor))


# ===================================================================
# REFRESH TOKENS (sync — used by auth_engine)
# ===================================================================

class RefreshTokenOps:
    """Sync refresh token operations."""

    @staticmethod
    def col():
        return get_sync_collection("refresh_tokens")

    @staticmethod
    def create(token: str, user_id: str, device_fp: str = "", family: str = "") -> dict:
        import time
        doc = {
            "token": token,
            "user_id": user_id,
            "device_fp": device_fp,
            "issued_at": int(time.time()),
            "expires_at": datetime.fromtimestamp(int(time.time()) + 604800, tz=timezone.utc),
            "family": family or _new_id(),
            "revoked": False,
        }
        RefreshTokenOps.col().insert_one(doc)
        return doc

    @staticmethod
    def find_by_token(token: str) -> dict | None:
        doc = RefreshTokenOps.col().find_one({"token": token, "revoked": False})
        return _serialize_doc(doc) if doc else None

    @staticmethod
    def revoke(token: str):
        RefreshTokenOps.col().update_one({"token": token}, {"$set": {"revoked": True}})

    @staticmethod
    def revoke_family(family: str):
        RefreshTokenOps.col().update_many({"family": family}, {"$set": {"revoked": True}})

    @staticmethod
    def revoke_all_for_user(user_id: str):
        RefreshTokenOps.col().update_many({"user_id": user_id}, {"$set": {"revoked": True}})

    @staticmethod
    def is_revoked(token: str) -> bool:
        doc = RefreshTokenOps.col().find_one({"token": token})
        if doc is None:
            return False
        return doc.get("revoked", False)


# ===================================================================
# RATE LIMITS (sync — used by auth_engine)
# ===================================================================

class RateLimitOps:
    """Sync rate limit operations."""

    @staticmethod
    def col():
        return get_sync_collection("rate_limits")

    @staticmethod
    def get(key: str) -> dict | None:
        doc = RateLimitOps.col().find_one({"key": key})
        return _serialize_doc(doc) if doc else None

    @staticmethod
    def upsert(key: str, updates: dict):
        RateLimitOps.col().update_one(
            {"key": key},
            {"$set": updates},
            upsert=True,
        )

    @staticmethod
    def increment_attempts(key: str, first_attempt: float):
        RateLimitOps.col().update_one(
            {"key": key},
            {
                "$inc": {"attempts": 1},
                "$setOnInsert": {"key": key, "first_attempt": first_attempt, "locked_until": 0},
            },
            upsert=True,
        )

    @staticmethod
    def lock(key: str, locked_until: float):
        RateLimitOps.col().update_one(
            {"key": key},
            {"$set": {"locked_until": locked_until}},
        )

    @staticmethod
    def reset(key: str):
        RateLimitOps.col().delete_one({"key": key})


# ===================================================================
# CSRF TOKENS (sync — used by auth_engine)
# ===================================================================

class CSRFOps:
    """Sync CSRF token operations."""

    @staticmethod
    def col():
        return get_sync_collection("csrf_tokens")

    @staticmethod
    def create(token: str, expires_at: float):
        CSRFOps.col().insert_one({
            "token": token,
            "expires_at": datetime.fromtimestamp(expires_at, tz=timezone.utc),
        })

    @staticmethod
    def validate(token: str) -> bool:
        import time
        doc = CSRFOps.col().find_one({"token": token})
        if not doc:
            return False
        exp = doc.get("expires_at")
        if isinstance(exp, datetime):
            return exp.timestamp() > time.time()
        return False

    @staticmethod
    def delete(token: str):
        CSRFOps.col().delete_one({"token": token})


# ===================================================================
# KPI SNAPSHOTS (async — used by server.py)
# ===================================================================

class KPIOps:
    """Async KPI snapshot operations."""

    @staticmethod
    def col():
        return get_collection("kpi_snapshots")

    @staticmethod
    def latest_col():
        return get_collection("kpi_latest")

    @staticmethod
    async def save_snapshot(kpi: dict):
        kpi_doc = {**kpi, "snapshot_id": _new_id(), "recorded_at": _now_iso()}
        await KPIOps.col().insert_one(kpi_doc)
        # Upsert latest for fast dashboard read
        await KPIOps.latest_col().update_one(
            {"company": kpi["company"]},
            {"$set": kpi},
            upsert=True,
        )

    @staticmethod
    async def get_latest(company: str) -> dict | None:
        doc = await KPIOps.latest_col().find_one({"company": company})
        return _serialize_doc(doc) if doc else None

    @staticmethod
    async def get_history(limit: int = 50, company: str | None = None) -> list[dict]:
        query = {}
        if company:
            query["company"] = company
        cursor = KPIOps.col().find(query).sort("recorded_at", -1).limit(limit)
        docs = await cursor.to_list(length=limit)
        return _serialize_docs(docs)


# ===================================================================
# AI RECOMMENDATIONS (async)
# ===================================================================

class AIRecommendationOps:
    """Async AI recommendation operations."""

    @staticmethod
    def col():
        return get_collection("ai_recommendations")

    @staticmethod
    async def create(*, company: str, context_type: str, recommendation_code: str,
                     confidence: float, payload: dict, status: str = "Open") -> dict:
        doc = {
            "rec_id": _new_id(),
            "company": company,
            "context_type": context_type,
            "recommendation_code": recommendation_code,
            "confidence": confidence,
            "status": status,
            "payload": payload,
            "generated_at": _now_iso(),
        }
        await AIRecommendationOps.col().insert_one(doc)
        return doc

    @staticmethod
    async def find_by_company(company: str, status: str = "", limit: int = 50) -> list[dict]:
        query: dict = {"company": company}
        if status:
            query["status"] = status
        cursor = AIRecommendationOps.col().find(query).sort("generated_at", -1).limit(limit)
        return _serialize_docs(await cursor.to_list(length=limit))

    @staticmethod
    async def update_status(rec_id: str, status: str):
        await AIRecommendationOps.col().update_one(
            {"rec_id": rec_id}, {"$set": {"status": status}}
        )


# ===================================================================
# ENTERPRISE PROFILES (async)
# ===================================================================

class ProfileOps:
    """Async enterprise profile operations."""

    @staticmethod
    def col():
        return get_collection("enterprise_profiles")

    @staticmethod
    async def upsert(user_id: str, data: dict):
        await ProfileOps.col().update_one(
            {"user_id": user_id},
            {"$set": {**data, "user_id": user_id}},
            upsert=True,
        )

    @staticmethod
    async def find_by_user(user_id: str) -> dict | None:
        doc = await ProfileOps.col().find_one({"user_id": user_id})
        return _serialize_doc(doc) if doc else None


# ===================================================================
# WEBHOOK LOGS (async)
# ===================================================================

class WebhookLogOps:
    """Async webhook log operations."""

    @staticmethod
    def col():
        return get_collection("webhook_logs")

    @staticmethod
    async def create(*, provider: str, event_type: str, signature: str,
                     request_body: str, http_status: int = 200) -> dict:
        doc = {
            "log_id": _new_id(),
            "provider": provider,
            "event_type": event_type,
            "signature": signature,
            "request_body": request_body,
            "processed": False,
            "http_status": http_status,
            "response_body": "",
            "received_at": _now_iso(),
        }
        await WebhookLogOps.col().insert_one(doc)
        return doc

    @staticmethod
    async def mark_processed(log_id: str, response_body: str = ""):
        await WebhookLogOps.col().update_one(
            {"log_id": log_id},
            {"$set": {"processed": True, "response_body": response_body}},
        )

    @staticmethod
    async def find_unprocessed(limit: int = 100) -> list[dict]:
        cursor = WebhookLogOps.col().find({"processed": False}).sort("received_at", 1).limit(limit)
        return _serialize_docs(await cursor.to_list(length=limit))


# ===================================================================
# SMART DECISION RULES (async)
# ===================================================================

class DecisionRuleOps:
    """Async smart decision rule operations."""

    @staticmethod
    def col():
        return get_collection("smart_decision_rules")

    @staticmethod
    async def create(*, rule_name: str, module: str, threshold: float = 50.0,
                     is_enabled: bool = True) -> dict:
        doc = {
            "rule_id": _new_id(),
            "rule_name": rule_name,
            "module": module,
            "threshold": threshold,
            "is_enabled": is_enabled,
        }
        await DecisionRuleOps.col().insert_one(doc)
        return doc

    @staticmethod
    async def find_enabled(module: str = "") -> list[dict]:
        query: dict = {"is_enabled": True}
        if module:
            query["module"] = module
        cursor = DecisionRuleOps.col().find(query)
        return _serialize_docs(await cursor.to_list(length=500))


# ===================================================================
# AI ALERTS (async)
# ===================================================================

class AlertOps:
    """Async AI alert operations."""

    @staticmethod
    def col():
        return get_collection("ai_alerts")

    @staticmethod
    async def create(*, title: str, severity: str, reference_doctype: str = "",
                     reference_name: str = "", risk_score: float = 0) -> dict:
        doc = {
            "alert_id": _new_id(),
            "title": title,
            "severity": severity,
            "reference_doctype": reference_doctype,
            "reference_name": reference_name,
            "status": "Open",
            "risk_score": risk_score,
            "created_at": _now_iso(),
        }
        await AlertOps.col().insert_one(doc)
        return doc

    @staticmethod
    async def find_active(limit: int = 50) -> list[dict]:
        cursor = AlertOps.col().find({"status": "Open"}).sort("created_at", -1).limit(limit)
        return _serialize_docs(await cursor.to_list(length=limit))

    @staticmethod
    async def resolve(alert_id: str):
        await AlertOps.col().update_one(
            {"alert_id": alert_id}, {"$set": {"status": "Resolved"}}
        )


# ===================================================================
# NOTIFICATIONS (async — used by server.py)
# ===================================================================

class NotificationOps:
    """Async notification operations."""

    @staticmethod
    def col():
        return get_collection("notifications")

    @staticmethod
    async def create(*, title: str, message: str, level: str = "info",
                     target_user: str = "") -> dict:
        doc = {
            "notif_id": _new_id(),
            "title": title,
            "message": message,
            "level": level,
            "target_user": target_user,
            "read": False,
            "timestamp": _now_iso(),
        }
        await NotificationOps.col().insert_one(doc)
        return doc

    @staticmethod
    async def find_recent(limit: int = 50, user_id: str = "") -> list[dict]:
        query: dict = {}
        if user_id:
            query["$or"] = [{"target_user": user_id}, {"target_user": ""}]
        cursor = NotificationOps.col().find(query).sort("timestamp", -1).limit(limit)
        return _serialize_docs(await cursor.to_list(length=limit))

    @staticmethod
    async def mark_read(notif_id: str):
        await NotificationOps.col().update_one(
            {"notif_id": notif_id}, {"$set": {"read": True}}
        )
