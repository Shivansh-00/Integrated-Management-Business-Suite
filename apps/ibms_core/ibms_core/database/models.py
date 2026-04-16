"""
Supabase CRUD Operations for all IBMS collections.
=====================================================
Async operations for FastAPI endpoints.
Sync operations for auth_engine, background jobs.
Uses Supabase PostgREST client (replaces MongoDB).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from ibms_core.database.supabase_connection import get_supabase_async, get_supabase_sync

# ===================================================================
# HELPERS
# ===================================================================

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return str(uuid.uuid4())


def _first_or_none(response) -> dict | None:
    """Extract the first row from a Supabase response or return None."""
    data = response.data
    if data and len(data) > 0:
        return data[0]
    return None


# ===================================================================
# USERS (sync — used by auth_engine)
# ===================================================================

class UserOps:
    """Sync user operations for auth_engine."""

    @staticmethod
    def _table():
        return get_supabase_sync().table("users")

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
            result = UserOps._table().insert(doc).execute()
            return result.data[0] if result.data else doc
        except Exception as e:
            err_str = str(e)
            if "duplicate" in err_str.lower() or "23505" in err_str:
                existing = UserOps.find_by_username(username) or UserOps.find_by_email(email)
                if existing:
                    return existing
            raise

    @staticmethod
    def find_by_username(username: str) -> dict | None:
        result = UserOps._table().select("*").eq("username", username).limit(1).execute()
        return _first_or_none(result)

    @staticmethod
    def find_by_email(email: str) -> dict | None:
        result = UserOps._table().select("*").eq("email", email).limit(1).execute()
        return _first_or_none(result)

    @staticmethod
    def find_by_id(user_id: str) -> dict | None:
        result = UserOps._table().select("*").eq("user_id", user_id).limit(1).execute()
        return _first_or_none(result)

    @staticmethod
    def find_by_username_or_email(identifier: str) -> dict | None:
        result = UserOps._table().select("*").or_(f"username.eq.{identifier},email.eq.{identifier}").limit(1).execute()
        return _first_or_none(result)

    @staticmethod
    def update(user_id: str, updates: dict):
        UserOps._table().update(updates).eq("user_id", user_id).execute()

    @staticmethod
    def set_totp(user_id: str, secret: str | None, enabled: bool):
        UserOps._table().update({
            "totp_secret": secret,
            "totp_enabled": enabled,
        }).eq("user_id", user_id).execute()

    @staticmethod
    def record_login(user_id: str):
        UserOps._table().update({
            "last_login": _now_iso(),
            "failed_attempts": 0,
        }).eq("user_id", user_id).execute()

    @staticmethod
    def increment_failed_attempts(user_id: str):
        user = UserOps.find_by_id(user_id)
        if user:
            new_count = user.get("failed_attempts", 0) + 1
            UserOps._table().update({"failed_attempts": new_count}).eq("user_id", user_id).execute()

    @staticmethod
    def exists_by_username(username: str) -> bool:
        result = UserOps._table().select("user_id", count="exact").eq("username", username).limit(1).execute()
        return (result.count or 0) > 0

    @staticmethod
    def exists_by_email(email: str) -> bool:
        result = UserOps._table().select("user_id", count="exact").eq("email", email).limit(1).execute()
        return (result.count or 0) > 0

    @staticmethod
    def count() -> int:
        result = UserOps._table().select("user_id", count="exact").execute()
        return result.count or 0


# ===================================================================
# AUDIT LOGS (sync — used by auth_engine)
# ===================================================================

class AuditOps:
    """Sync audit log operations."""

    @staticmethod
    def _table():
        return get_supabase_sync().table("audit_logs")

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
        result = AuditOps._table().insert(doc).execute()
        return result.data[0] if result.data else doc

    @staticmethod
    def find(limit: int = 100, event_type: str = "") -> list[dict]:
        q = AuditOps._table().select("*").order("timestamp", desc=True).limit(limit)
        if event_type:
            q = q.eq("event_type", event_type)
        result = q.execute()
        return result.data or []


# ===================================================================
# REFRESH TOKENS (sync — used by auth_engine)
# ===================================================================

class RefreshTokenOps:
    """Sync refresh token operations."""

    @staticmethod
    def _table():
        return get_supabase_sync().table("refresh_tokens")

    @staticmethod
    def create(token: str, user_id: str, device_fp: str = "", family: str = "") -> dict:
        import time
        doc = {
            "token": token,
            "user_id": user_id,
            "device_fp": device_fp,
            "issued_at": int(time.time()),
            "expires_at": datetime.fromtimestamp(int(time.time()) + 604800, tz=timezone.utc).isoformat(),
            "family": family or _new_id(),
            "revoked": False,
        }
        result = RefreshTokenOps._table().insert(doc).execute()
        return result.data[0] if result.data else doc

    @staticmethod
    def find_by_token(token: str) -> dict | None:
        result = RefreshTokenOps._table().select("*").eq("token", token).eq("revoked", False).limit(1).execute()
        return _first_or_none(result)

    @staticmethod
    def revoke(token: str):
        RefreshTokenOps._table().update({"revoked": True}).eq("token", token).execute()

    @staticmethod
    def revoke_family(family: str):
        RefreshTokenOps._table().update({"revoked": True}).eq("family", family).execute()

    @staticmethod
    def revoke_all_for_user(user_id: str):
        RefreshTokenOps._table().update({"revoked": True}).eq("user_id", user_id).execute()

    @staticmethod
    def is_revoked(token: str) -> bool:
        result = RefreshTokenOps._table().select("revoked").eq("token", token).limit(1).execute()
        row = _first_or_none(result)
        if row is None:
            return False
        return row.get("revoked", False)


# ===================================================================
# RATE LIMITS (sync — used by auth_engine)
# ===================================================================

class RateLimitOps:
    """Sync rate limit operations."""

    @staticmethod
    def _table():
        return get_supabase_sync().table("rate_limits")

    @staticmethod
    def get(key: str) -> dict | None:
        result = RateLimitOps._table().select("*").eq("key", key).limit(1).execute()
        return _first_or_none(result)

    @staticmethod
    def upsert(key: str, updates: dict):
        updates["key"] = key
        RateLimitOps._table().upsert(updates, on_conflict="key").execute()

    @staticmethod
    def increment_attempts(key: str, first_attempt: float):
        existing = RateLimitOps.get(key)
        if existing:
            new_attempts = existing.get("attempts", 0) + 1
            RateLimitOps._table().update({"attempts": new_attempts}).eq("key", key).execute()
        else:
            RateLimitOps._table().insert({
                "key": key,
                "attempts": 1,
                "first_attempt": first_attempt,
                "locked_until": 0,
            }).execute()

    @staticmethod
    def lock(key: str, locked_until: float):
        RateLimitOps._table().update({"locked_until": locked_until}).eq("key", key).execute()

    @staticmethod
    def reset(key: str):
        RateLimitOps._table().delete().eq("key", key).execute()


# ===================================================================
# CSRF TOKENS (sync — used by auth_engine)
# ===================================================================

class CSRFOps:
    """Sync CSRF token operations."""

    @staticmethod
    def _table():
        return get_supabase_sync().table("csrf_tokens")

    @staticmethod
    def create(token: str, expires_at: float):
        CSRFOps._table().insert({
            "token": token,
            "expires_at": datetime.fromtimestamp(expires_at, tz=timezone.utc).isoformat(),
        }).execute()

    @staticmethod
    def validate(token: str) -> bool:
        import time
        result = CSRFOps._table().select("expires_at").eq("token", token).limit(1).execute()
        row = _first_or_none(result)
        if not row:
            return False
        exp = row.get("expires_at")
        if exp:
            try:
                exp_dt = datetime.fromisoformat(exp.replace("Z", "+00:00"))
                return exp_dt.timestamp() > time.time()
            except (ValueError, TypeError):
                return False
        return False

    @staticmethod
    def delete(token: str):
        CSRFOps._table().delete().eq("token", token).execute()


# ===================================================================
# KPI SNAPSHOTS (async — used by server.py)
# ===================================================================

class KPIOps:
    """Async KPI snapshot operations."""

    @staticmethod
    async def save_snapshot(kpi: dict):
        sb = get_supabase_async()
        snapshot_id = _new_id()
        recorded_at = _now_iso()
        company = kpi.get("company", "Default Company")
        # Store full KPI in the data JSONB column
        kpi_doc = {
            "snapshot_id": snapshot_id,
            "company": company,
            "recorded_at": recorded_at,
            "data": kpi,
        }
        await sb.table("kpi_snapshots").insert(kpi_doc).execute()
        # Upsert latest for fast dashboard read
        await sb.table("kpi_latest").upsert({
            "company": company,
            "data": kpi,
        }, on_conflict="company").execute()

    @staticmethod
    async def get_latest(company: str) -> dict | None:
        sb = get_supabase_async()
        result = await sb.table("kpi_latest").select("*").eq("company", company).limit(1).execute()
        row = result.data[0] if result.data else None
        if row and "data" in row:
            return row["data"]
        return row

    @staticmethod
    async def get_history(limit: int = 50, company: str | None = None) -> list[dict]:
        sb = get_supabase_async()
        q = sb.table("kpi_snapshots").select("*").order("recorded_at", desc=True).limit(limit)
        if company:
            q = q.eq("company", company)
        result = await q.execute()
        return result.data or []


# ===================================================================
# AI RECOMMENDATIONS (async)
# ===================================================================

class AIRecommendationOps:
    """Async AI recommendation operations."""

    @staticmethod
    async def create(*, company: str, context_type: str, recommendation_code: str,
                     confidence: float, payload: dict, status: str = "Open") -> dict:
        sb = get_supabase_async()
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
        result = await sb.table("ai_recommendations").insert(doc).execute()
        return result.data[0] if result.data else doc

    @staticmethod
    async def find_by_company(company: str, status: str = "", limit: int = 50) -> list[dict]:
        sb = get_supabase_async()
        q = sb.table("ai_recommendations").select("*").eq("company", company).order("generated_at", desc=True).limit(limit)
        if status:
            q = q.eq("status", status)
        result = await q.execute()
        return result.data or []

    @staticmethod
    async def update_status(rec_id: str, status: str):
        sb = get_supabase_async()
        await sb.table("ai_recommendations").update({"status": status}).eq("rec_id", rec_id).execute()


# ===================================================================
# ENTERPRISE PROFILES (async)
# ===================================================================

class ProfileOps:
    """Async enterprise profile operations."""

    @staticmethod
    async def upsert(user_id: str, data: dict):
        sb = get_supabase_async()
        await sb.table("enterprise_profiles").upsert({
            "user_id": user_id,
            "data": data,
        }, on_conflict="user_id").execute()

    @staticmethod
    async def find_by_user(user_id: str) -> dict | None:
        sb = get_supabase_async()
        result = await sb.table("enterprise_profiles").select("*").eq("user_id", user_id).limit(1).execute()
        row = result.data[0] if result.data else None
        if row and "data" in row:
            return {**row["data"], "user_id": user_id}
        return row


# ===================================================================
# WEBHOOK LOGS (async)
# ===================================================================

class WebhookLogOps:
    """Async webhook log operations."""

    @staticmethod
    async def create(*, provider: str, event_type: str, signature: str,
                     request_body: str, http_status: int = 200) -> dict:
        sb = get_supabase_async()
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
        result = await sb.table("webhook_logs").insert(doc).execute()
        return result.data[0] if result.data else doc

    @staticmethod
    async def mark_processed(log_id: str, response_body: str = ""):
        sb = get_supabase_async()
        await sb.table("webhook_logs").update({
            "processed": True,
            "response_body": response_body,
        }).eq("log_id", log_id).execute()

    @staticmethod
    async def find_unprocessed(limit: int = 100) -> list[dict]:
        sb = get_supabase_async()
        result = await sb.table("webhook_logs").select("*").eq("processed", False).order("received_at", desc=False).limit(limit).execute()
        return result.data or []


# ===================================================================
# SMART DECISION RULES (async)
# ===================================================================

class DecisionRuleOps:
    """Async smart decision rule operations."""

    @staticmethod
    async def create(*, rule_name: str, module: str, threshold: float = 50.0,
                     is_enabled: bool = True) -> dict:
        sb = get_supabase_async()
        doc = {
            "rule_id": _new_id(),
            "rule_name": rule_name,
            "module": module,
            "threshold": threshold,
            "is_enabled": is_enabled,
        }
        result = await sb.table("smart_decision_rules").insert(doc).execute()
        return result.data[0] if result.data else doc

    @staticmethod
    async def find_enabled(module: str = "") -> list[dict]:
        sb = get_supabase_async()
        q = sb.table("smart_decision_rules").select("*").eq("is_enabled", True)
        if module:
            q = q.eq("module", module)
        result = await q.execute()
        return result.data or []


# ===================================================================
# AI ALERTS (async)
# ===================================================================

class AlertOps:
    """Async AI alert operations."""

    @staticmethod
    async def create(*, title: str, severity: str, reference_doctype: str = "",
                     reference_name: str = "", risk_score: float = 0) -> dict:
        sb = get_supabase_async()
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
        result = await sb.table("ai_alerts").insert(doc).execute()
        return result.data[0] if result.data else doc

    @staticmethod
    async def find_active(limit: int = 50) -> list[dict]:
        sb = get_supabase_async()
        result = await sb.table("ai_alerts").select("*").eq("status", "Open").order("created_at", desc=True).limit(limit).execute()
        return result.data or []

    @staticmethod
    async def resolve(alert_id: str):
        sb = get_supabase_async()
        await sb.table("ai_alerts").update({"status": "Resolved"}).eq("alert_id", alert_id).execute()


# ===================================================================
# NOTIFICATIONS (async — used by server.py)
# ===================================================================

class NotificationOps:
    """Async notification operations."""

    @staticmethod
    async def create(*, title: str, message: str, level: str = "info",
                     target_user: str = "") -> dict:
        sb = get_supabase_async()
        doc = {
            "notif_id": _new_id(),
            "title": title,
            "message": message,
            "level": level,
            "target_user": target_user,
            "read": False,
            "timestamp": _now_iso(),
        }
        result = await sb.table("notifications").insert(doc).execute()
        return result.data[0] if result.data else doc

    @staticmethod
    async def find_recent(limit: int = 50, user_id: str = "") -> list[dict]:
        sb = get_supabase_async()
        q = sb.table("notifications").select("*").order("timestamp", desc=True).limit(limit)
        if user_id:
            q = q.or_(f"target_user.eq.{user_id},target_user.eq.")
        result = await q.execute()
        return result.data or []

    @staticmethod
    async def mark_read(notif_id: str):
        sb = get_supabase_async()
        await sb.table("notifications").update({"read": True}).eq("notif_id", notif_id).execute()
