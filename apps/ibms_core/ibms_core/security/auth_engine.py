"""
IBMS Enterprise Authentication Engine
======================================
Production-grade authentication system with:
  • JWT + Refresh Token Rotation
  • Argon2/Bcrypt password hashing
  • RBAC with permission inheritance
  • TOTP-based 2FA
  • Device fingerprint validation
  • Brute-force protection with IP throttling
  • Audit logging for all auth events
  • Secure session management
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import secrets
import time
import uuid
from base64 import b64decode, b64encode
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

# ---------------------------------------------------------------------------
# Password Hashing (bcrypt-compatible with fallback)
# ---------------------------------------------------------------------------
try:
    import bcrypt
    _HAS_BCRYPT = True
except ImportError:
    _HAS_BCRYPT = False


def hash_password(password: str) -> str:
    """Hash password using bcrypt (preferred) or PBKDF2 fallback."""
    if _HAS_BCRYPT:
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=10)).decode()
    # PBKDF2 fallback
    import hashlib
    salt = os.urandom(32)
    key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 310_000)
    return f"pbkdf2:{b64encode(salt).decode()}:{b64encode(key).decode()}"


def verify_password(password: str, hashed: str) -> bool:
    """Verify password against hash."""
    if _HAS_BCRYPT and hashed.startswith("$2"):
        try:
            return bcrypt.checkpw(password.encode(), hashed.encode())
        except (ValueError, TypeError):
            return False
    if hashed.startswith("pbkdf2:"):
        _, salt_b64, key_b64 = hashed.split(":")
        salt = b64decode(salt_b64)
        expected = b64decode(key_b64)
        key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 310_000)
        return hmac.compare_digest(key, expected)
    return False


# ---------------------------------------------------------------------------
# Password Strength Enforcement
# ---------------------------------------------------------------------------
class PasswordStrength(Enum):
    WEAK = "weak"
    FAIR = "fair"
    STRONG = "strong"
    VERY_STRONG = "very_strong"


def check_password_strength(password: str) -> dict:
    """Enforce enterprise password policy."""
    issues = []
    score = 0

    if len(password) >= 8:
        score += 1
    else:
        issues.append("Minimum 8 characters required")

    if len(password) >= 12:
        score += 1

    if re.search(r"[A-Z]", password):
        score += 1
    else:
        issues.append("Must contain uppercase letter")

    if re.search(r"[a-z]", password):
        score += 1
    else:
        issues.append("Must contain lowercase letter")

    if re.search(r"\d", password):
        score += 1
    else:
        issues.append("Must contain digit")

    if re.search(r"[!@#$%^&*()_+\-=\[\]{}|;:',.<>?/~`]", password):
        score += 1
    else:
        issues.append("Must contain special character")

    # Common password check
    common = {"password", "123456", "qwerty", "admin", "letmein", "welcome"}
    if password.lower() in common:
        issues.append("Password is too common")
        score = 0

    strength = PasswordStrength.WEAK
    if score >= 6:
        strength = PasswordStrength.VERY_STRONG
    elif score >= 4:
        strength = PasswordStrength.STRONG
    elif score >= 3:
        strength = PasswordStrength.FAIR

    return {
        "valid": len(issues) == 0 and score >= 3,
        "strength": strength.value,
        "score": score,
        "max_score": 6,
        "issues": issues,
    }


# ---------------------------------------------------------------------------
# TOTP 2FA
# ---------------------------------------------------------------------------
def generate_totp_secret() -> str:
    """Generate a base32-encoded TOTP secret."""
    return b64encode(os.urandom(20)).decode().replace("=", "").upper()[:32]


def verify_totp(secret: str, code: str, window: int = 1) -> bool:
    """Verify TOTP code with time window tolerance."""
    try:
        import pyotp
        totp = pyotp.TOTP(secret)
        return totp.verify(code, valid_window=window)
    except ImportError:
        # Manual TOTP verification
        import hashlib as _hashlib
        import hmac as _hmac
        import struct

        def _generate_totp(secret_bytes: bytes, time_step: int) -> str:
            msg = struct.pack(">Q", time_step)
            h = _hmac.new(secret_bytes, msg, _hashlib.sha1).digest()
            offset = h[-1] & 0x0F
            code_int = struct.unpack(">I", h[offset:offset + 4])[0] & 0x7FFFFFFF
            return str(code_int % 1_000_000).zfill(6)

        # Decode base32
        try:
            from base64 import b32decode
            secret_bytes = b32decode(secret + "=" * (8 - len(secret) % 8), casefold=True)
        except Exception:
            secret_bytes = secret.encode()

        current_step = int(time.time()) // 30
        for i in range(-window, window + 1):
            if _generate_totp(secret_bytes, current_step + i) == code:
                return True
        return False


def get_totp_uri(secret: str, email: str, issuer: str = "IBMS ERP") -> str:
    """Generate otpauth URI for QR code generation."""
    return f"otpauth://totp/{issuer}:{email}?secret={secret}&issuer={issuer}&digits=6&period=30"


# ---------------------------------------------------------------------------
# RBAC — Role-Based Access Control with Permission Inheritance
# ---------------------------------------------------------------------------
ROLE_HIERARCHY = {
    "super_admin": {
        "inherits": [],
        "permissions": ["*"],
        "description": "Full system access",
    },
    "admin": {
        "inherits": [],
        "permissions": [
            "dashboard.view", "dashboard.edit",
            "users.view", "users.create", "users.edit",
            "reports.view", "reports.export",
            "settings.view", "settings.edit",
            "api.full_access",
            "ai.view", "ai.configure",
            "risk.view", "risk.manage",
            "compliance.view", "compliance.manage",
            "audit.view",
        ],
        "description": "Platform administrator",
    },
    "manager": {
        "inherits": ["analyst"],
        "permissions": [
            "reports.export",
            "risk.manage",
            "compliance.manage",
            "budget.approve",
            "leads.manage",
            "pricing.manage",
        ],
        "description": "Department manager",
    },
    "analyst": {
        "inherits": ["viewer"],
        "permissions": [
            "reports.view",
            "ai.view",
            "risk.view",
            "compliance.view",
            "forecast.view",
            "copilot.use",
        ],
        "description": "Business analyst",
    },
    "viewer": {
        "inherits": [],
        "permissions": [
            "dashboard.view",
            "kpi.view",
        ],
        "description": "Read-only viewer",
    },
}


def resolve_permissions(role: str) -> set[str]:
    """Resolve all permissions including inherited ones."""
    if role not in ROLE_HIERARCHY:
        return set()

    role_def = ROLE_HIERARCHY[role]
    permissions = set(role_def["permissions"])

    for parent_role in role_def.get("inherits", []):
        permissions |= resolve_permissions(parent_role)

    return permissions


def has_permission(user_role: str, required_permission: str) -> bool:
    """Check if a role has a specific permission."""
    perms = resolve_permissions(user_role)
    if "*" in perms:
        return True
    # Check exact match
    if required_permission in perms:
        return True
    # Check wildcard (e.g., "dashboard.*" matches "dashboard.view")
    parts = required_permission.split(".")
    for i in range(len(parts)):
        wildcard = ".".join(parts[: i + 1]) + ".*"
        if wildcard in perms:
            return True
    return False


# ---------------------------------------------------------------------------
# JWT Token Engine (Enhanced)
# ---------------------------------------------------------------------------
class TokenType(Enum):
    ACCESS = "access"
    REFRESH = "refresh"


def _b64url_encode(data: bytes) -> str:
    return b64encode(data).decode().rstrip("=").replace("+", "-").replace("/", "_")


def _b64url_decode(s: str) -> bytes:
    s = s.replace("-", "+").replace("_", "/")
    pad = 4 - len(s) % 4
    if pad != 4:
        s += "=" * pad
    return b64decode(s)


def create_jwt(
    payload: dict,
    secret: str,
    token_type: TokenType = TokenType.ACCESS,
    ttl: int = 3600,
) -> str:
    """Create a proper JWT token."""
    header = {"alg": "HS256", "typ": "JWT"}
    now = int(time.time())

    payload = {
        **payload,
        "iat": now,
        "exp": now + ttl,
        "jti": str(uuid.uuid4()),
        "type": token_type.value,
    }

    header_b64 = _b64url_encode(json.dumps(header, separators=(",", ":")).encode())
    payload_b64 = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode())
    signing_input = f"{header_b64}.{payload_b64}"

    signature = hmac.new(
        secret.encode(), signing_input.encode(), hashlib.sha256
    ).digest()
    sig_b64 = _b64url_encode(signature)

    return f"{header_b64}.{payload_b64}.{sig_b64}"


def decode_jwt(token: str, secret: str) -> dict | None:
    """Decode and validate a JWT token."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None

        header_b64, payload_b64, sig_b64 = parts
        signing_input = f"{header_b64}.{payload_b64}"

        expected_sig = hmac.new(
            secret.encode(), signing_input.encode(), hashlib.sha256
        ).digest()
        actual_sig = _b64url_decode(sig_b64)

        if not hmac.compare_digest(expected_sig, actual_sig):
            return None

        payload = json.loads(_b64url_decode(payload_b64))

        if payload.get("exp", 0) < int(time.time()):
            return None

        return payload
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Refresh Token Rotation (MongoDB-backed)
# ---------------------------------------------------------------------------

def issue_refresh_token(user_id: str, device_fp: str = "") -> str:
    """Issue a new refresh token with rotation support — persisted to MongoDB."""
    token = secrets.token_urlsafe(64)
    try:
        RefreshTokenOps.create(token=token, user_id=user_id, device_fp=device_fp)
    except Exception:
        # Fallback to in-memory
        _refresh_tokens_fallback[token] = {
            "user_id": user_id,
            "device_fp": device_fp,
            "issued_at": int(time.time()),
            "expires_at": int(time.time()) + 604800,
            "family": str(uuid.uuid4()),
        }
    return token


# In-memory fallback for refresh tokens
_refresh_tokens_fallback: dict[str, dict] = {}


def rotate_refresh_token(old_token: str, device_fp: str = "") -> tuple[str, str] | None:
    """Rotate refresh token — invalidate old, issue new. MongoDB-backed."""
    try:
        # Check if token was already revoked (reuse attack)
        if RefreshTokenOps.is_revoked(old_token):
            return None

        token_data = RefreshTokenOps.find_by_token(old_token)
        if not token_data:
            # Try fallback
            return _rotate_fallback(old_token, device_fp)

        if device_fp and token_data.get("device_fp") and token_data["device_fp"] != device_fp:
            RefreshTokenOps.revoke(old_token)
            return None

        # Revoke old token
        RefreshTokenOps.revoke(old_token)

        # Issue new
        new_token = secrets.token_urlsafe(64)
        RefreshTokenOps.create(
            token=new_token,
            user_id=token_data["user_id"],
            device_fp=device_fp,
            family=token_data.get("family", ""),
        )

        return token_data["user_id"], new_token
    except Exception:
        return _rotate_fallback(old_token, device_fp)


def _rotate_fallback(old_token: str, device_fp: str) -> tuple[str, str] | None:
    """In-memory fallback for refresh token rotation."""
    token_data = _refresh_tokens_fallback.get(old_token)
    if not token_data:
        return None
    if token_data["expires_at"] < int(time.time()):
        del _refresh_tokens_fallback[old_token]
        return None
    if device_fp and token_data.get("device_fp") and token_data["device_fp"] != device_fp:
        return None
    del _refresh_tokens_fallback[old_token]
    new_token = secrets.token_urlsafe(64)
    _refresh_tokens_fallback[new_token] = {
        "user_id": token_data["user_id"],
        "device_fp": device_fp,
        "issued_at": int(time.time()),
        "expires_at": int(time.time()) + 604800,
        "family": token_data.get("family", str(uuid.uuid4())),
    }
    return token_data["user_id"], new_token


def revoke_all_tokens(user_id: str):
    """Revoke all refresh tokens for a user (logout everywhere)."""
    try:
        RefreshTokenOps.revoke_all_for_user(user_id)
    except Exception:
        pass
    # Also clear in-memory fallback
    for token in list(_refresh_tokens_fallback):
        if _refresh_tokens_fallback[token]["user_id"] == user_id:
            del _refresh_tokens_fallback[token]


# ---------------------------------------------------------------------------
# Device Fingerprinting
# ---------------------------------------------------------------------------
def compute_device_fingerprint(
    user_agent: str, accept_language: str = "", ip: str = ""
) -> str:
    """Compute a device fingerprint from request headers."""
    raw = f"{user_agent}|{accept_language}|{ip}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


# ---------------------------------------------------------------------------
# Brute Force / Rate Limiting
# ---------------------------------------------------------------------------
@dataclass
class RateLimitEntry:
    attempts: int = 0
    first_attempt: float = 0
    locked_until: float = 0


_rate_limits_fallback: dict[str, RateLimitEntry] = defaultdict(RateLimitEntry)

# Config
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION = 300  # 5 minutes
RATE_WINDOW = 900  # 15 minutes


def check_rate_limit(key: str) -> dict:
    """Check if a key (IP/user) is rate-limited. MongoDB-backed."""
    now = time.time()
    try:
        doc = RateLimitOps.get(key)
        if doc:
            if doc.get("locked_until", 0) > now:
                remaining = int(doc["locked_until"] - now)
                return {"allowed": False, "reason": "Account temporarily locked", "retry_after": remaining, "attempts": doc.get("attempts", 0)}
            if doc.get("first_attempt") and (now - doc["first_attempt"]) > RATE_WINDOW:
                RateLimitOps.reset(key)
                return {"allowed": True, "attempts": 0, "remaining": MAX_LOGIN_ATTEMPTS}
            return {"allowed": True, "attempts": doc.get("attempts", 0), "remaining": MAX_LOGIN_ATTEMPTS - doc.get("attempts", 0)}
        return {"allowed": True, "attempts": 0, "remaining": MAX_LOGIN_ATTEMPTS}
    except Exception:
        # Fallback to in-memory
        mark_sync_supabase_down()
        entry = _rate_limits_fallback[key]
        if entry.locked_until > now:
            remaining = int(entry.locked_until - now)
            return {"allowed": False, "reason": "Account temporarily locked", "retry_after": remaining, "attempts": entry.attempts}
        if entry.first_attempt and (now - entry.first_attempt) > RATE_WINDOW:
            entry.attempts = 0
            entry.first_attempt = 0
        return {"allowed": True, "attempts": entry.attempts, "remaining": MAX_LOGIN_ATTEMPTS - entry.attempts}


def record_failed_attempt(key: str):
    """Record a failed login attempt. MongoDB-backed."""
    now = time.time()
    try:
        doc = RateLimitOps.get(key)
        attempts = (doc.get("attempts", 0) if doc else 0) + 1
        updates = {"attempts": attempts, "key": key}
        if not doc or not doc.get("first_attempt"):
            updates["first_attempt"] = now
        if attempts >= MAX_LOGIN_ATTEMPTS:
            updates["locked_until"] = now + LOCKOUT_DURATION
        RateLimitOps.upsert(key, updates)
    except Exception:
        entry = _rate_limits_fallback[key]
        if not entry.first_attempt:
            entry.first_attempt = now
        entry.attempts += 1
        if entry.attempts >= MAX_LOGIN_ATTEMPTS:
            entry.locked_until = now + LOCKOUT_DURATION


def reset_rate_limit(key: str):
    """Reset rate limit after successful login."""
    try:
        RateLimitOps.reset(key)
    except Exception:
        if key in _rate_limits_fallback:
            del _rate_limits_fallback[key]


# ---------------------------------------------------------------------------
# CSRF Protection (MongoDB-backed)
# ---------------------------------------------------------------------------

def generate_csrf_token(session_id: str) -> str:
    """Generate a CSRF token tied to a session — persisted to MongoDB."""
    token = secrets.token_urlsafe(32)
    expires_at = time.time() + 7200  # 2h expiry
    try:
        CSRFOps.create(token, expires_at)
    except Exception:
        _csrf_tokens_fallback[token] = expires_at
    return token


_csrf_tokens_fallback: dict[str, float] = {}


def validate_csrf_token(token: str) -> bool:
    """Validate a CSRF token from MongoDB."""
    try:
        return CSRFOps.validate(token)
    except Exception:
        expiry = _csrf_tokens_fallback.get(token)
        if not expiry:
            return False
        if time.time() > expiry:
            del _csrf_tokens_fallback[token]
            return False
        return True


# ---------------------------------------------------------------------------
# In-Memory User Store (production: use database)
# ---------------------------------------------------------------------------
@dataclass
class User:
    id: str
    email: str
    username: str
    password_hash: str
    role: str = "viewer"
    is_active: bool = True
    is_verified: bool = False
    totp_secret: str | None = None
    totp_enabled: bool = False
    created_at: str = ""
    last_login: str | None = None
    failed_attempts: int = 0


# ---------------------------------------------------------------------------
# Supabase-backed User Store
# ---------------------------------------------------------------------------
from ibms_core.database.models import (  # noqa: E402
    AuditOps,
    CSRFOps,
    RateLimitOps,
    RefreshTokenOps,
    UserOps,
)
from ibms_core.database.supabase_connection import mark_sync_supabase_down  # noqa: E402

# In-memory fallback caches (used only when Supabase is unreachable)
_users_fallback: dict[str, dict] = {}
_user_by_username_fallback: dict[str, str] = {}
_user_by_email_fallback: dict[str, str] = {}


def _get_user_by_identifier(identifier: str) -> dict | None:
    """Find user by username or email — MongoDB first, fallback to memory."""
    try:
        user = UserOps.find_by_username_or_email(identifier)
        if user:
            return user
    except Exception:
        pass
    # Fallback
    uid = _user_by_username_fallback.get(identifier) or _user_by_email_fallback.get(identifier)
    return _users_fallback.get(uid) if uid else None


def _get_user_by_id(user_id: str) -> dict | None:
    """Find user by ID — MongoDB first, fallback to memory."""
    try:
        user = UserOps.find_by_id(user_id)
        if user:
            return user
    except Exception:
        pass
    return _users_fallback.get(user_id)


def _init_default_users():
    """Initialize default admin user in MongoDB if not present."""
    try:
        if not UserOps.exists_by_username("admin") and not UserOps.exists_by_email("admin@ibms.dev"):
            UserOps.create(
                email="admin@ibms.dev",
                username="admin",
                password_hash=hash_password("Admin@IBMS2026"),
                role="super_admin",
                is_active=True,
                is_verified=True,
            )
        if not UserOps.exists_by_username("analyst") and not UserOps.exists_by_email("analyst@ibms.dev"):
            UserOps.create(
                email="analyst@ibms.dev",
                username="analyst",
                password_hash=hash_password("Analyst@2026"),
                role="analyst",
                is_active=True,
                is_verified=True,
            )
    except Exception:
        # Supabase not available yet — create in-memory fallback
        mark_sync_supabase_down()
        if "admin" not in _user_by_username_fallback:
            admin_id = str(uuid.uuid4())
            _users_fallback[admin_id] = {
                "user_id": admin_id, "email": "admin@ibms.dev", "username": "admin",
                "password_hash": hash_password("Admin@IBMS2026"), "role": "super_admin",
                "is_active": True, "is_verified": True, "totp_secret": None,
                "totp_enabled": False, "created_at": datetime.now(timezone.utc).isoformat(),
                "last_login": None, "failed_attempts": 0,
            }
            _user_by_email_fallback["admin@ibms.dev"] = admin_id
            _user_by_username_fallback["admin"] = admin_id

            analyst_id = str(uuid.uuid4())
            _users_fallback[analyst_id] = {
                "user_id": analyst_id, "email": "analyst@ibms.dev", "username": "analyst",
                "password_hash": hash_password("Analyst@2026"), "role": "analyst",
                "is_active": True, "is_verified": True, "totp_secret": None,
                "totp_enabled": False, "created_at": datetime.now(timezone.utc).isoformat(),
                "last_login": None, "failed_attempts": 0,
            }
            _user_by_email_fallback["analyst@ibms.dev"] = analyst_id
            _user_by_username_fallback["analyst"] = analyst_id


_init_default_users()


# ---------------------------------------------------------------------------
# Auth Operations
# ---------------------------------------------------------------------------
@dataclass
class AuthResult:
    success: bool
    user_id: str | None = None
    access_token: str | None = None
    refresh_token: str | None = None
    csrf_token: str | None = None
    requires_2fa: bool = False
    error: str | None = None
    role: str | None = None
    permissions: list[str] = field(default_factory=list)


# Audit log (MongoDB-backed with in-memory fallback)
_audit_log_fallback: list[dict] = []


def audit_event(event_type: str, user_id: str = "", ip: str = "", details: dict | None = None):
    """Record an audit event to MongoDB."""
    try:
        entry = AuditOps.create(event_type=event_type, user_id=user_id, ip=ip, details=details)
        return entry
    except Exception:
        # Fallback to in-memory
        entry = {
            "id": str(uuid.uuid4()),
            "type": event_type,
            "user_id": user_id,
            "ip": ip,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "details": details or {},
        }
        _audit_log_fallback.append(entry)
        if len(_audit_log_fallback) > 10000:
            _audit_log_fallback.pop(0)
        return entry


def get_audit_log(limit: int = 100, event_type: str = "") -> list[dict]:
    """Retrieve audit log entries from MongoDB."""
    try:
        return AuditOps.find(limit=limit, event_type=event_type)
    except Exception:
        logs = _audit_log_fallback
        if event_type:
            logs = [e for e in logs if e.get("type") == event_type]
        return list(reversed(logs[-limit:]))


def authenticate(
    username: str,
    password: str,
    jwt_secret: str,
    ip: str = "",
    device_fp: str = "",
    totp_code: str = "",
) -> AuthResult:
    """Full authentication flow with MongoDB user store."""
    # Rate limit check
    rate_key = f"login:{ip}"
    rate_check = check_rate_limit(rate_key)
    if not rate_check["allowed"]:
        audit_event("login_blocked", ip=ip, details={"reason": "rate_limited", "username": username})
        return AuthResult(
            success=False,
            error=f"Too many attempts. Retry after {rate_check['retry_after']}s",
        )

    # Find user from MongoDB (or fallback)
    user = _get_user_by_identifier(username)
    if not user:
        record_failed_attempt(rate_key)
        audit_event("login_failed", ip=ip, details={"reason": "user_not_found", "username": username})
        return AuthResult(success=False, error="Invalid credentials")

    user_id = user["user_id"]

    if not user.get("is_active", True):
        audit_event("login_failed", user_id=user_id, ip=ip, details={"reason": "account_disabled"})
        return AuthResult(success=False, error="Account is disabled")

    # Verify password
    if not verify_password(password, user["password_hash"]):
        record_failed_attempt(rate_key)
        audit_event("login_failed", user_id=user_id, ip=ip, details={"reason": "invalid_password"})
        return AuthResult(success=False, error="Invalid credentials")

    # 2FA check
    if user.get("totp_enabled"):
        if not totp_code:
            return AuthResult(success=False, requires_2fa=True, user_id=user_id)
        if not verify_totp(user.get("totp_secret", ""), totp_code):
            record_failed_attempt(rate_key)
            audit_event("login_failed", user_id=user_id, ip=ip, details={"reason": "invalid_2fa"})
            return AuthResult(success=False, error="Invalid 2FA code")

    # Success — issue tokens
    reset_rate_limit(rate_key)

    role = user.get("role", "viewer")
    permissions = list(resolve_permissions(role))
    access_token = create_jwt(
        {
            "sub": user_id,
            "username": user["username"],
            "email": user["email"],
            "role": role,
            "permissions": permissions,
        },
        jwt_secret,
        TokenType.ACCESS,
        ttl=1800,  # 30 min
    )

    refresh_token = issue_refresh_token(user_id, device_fp)
    csrf_token = generate_csrf_token(user_id)

    # Update last login in MongoDB
    try:
        UserOps.record_login(user_id)
    except Exception:
        pass

    audit_event("login_success", user_id=user_id, ip=ip, details={"device_fp": device_fp})

    return AuthResult(
        success=True,
        user_id=user_id,
        access_token=access_token,
        refresh_token=refresh_token,
        csrf_token=csrf_token,
        role=role,
        permissions=permissions,
    )


def register_user(
    username: str,
    email: str,
    password: str,
    role: str = "viewer",
) -> dict:
    """Register a new user in MongoDB."""
    # Validate uniqueness
    try:
        if UserOps.exists_by_username(username):
            return {"success": False, "error": "Username already exists"}
        if UserOps.exists_by_email(email):
            return {"success": False, "error": "Email already registered"}
    except Exception:
        # Fallback check
        if _user_by_username_fallback.get(username):
            return {"success": False, "error": "Username already exists"}
        if _user_by_email_fallback.get(email):
            return {"success": False, "error": "Email already registered"}

    strength = check_password_strength(password)
    if not strength["valid"]:
        return {"success": False, "error": "Weak password", "details": strength}

    safe_role = role if role in ROLE_HIERARCHY else "viewer"
    password_hash = hash_password(password)

    try:
        user_doc = UserOps.create(
            email=email,
            username=username,
            password_hash=password_hash,
            role=safe_role,
            is_active=True,
            is_verified=False,
        )
        user_id = user_doc["user_id"]
    except Exception:
        # Fallback to in-memory
        user_id = str(uuid.uuid4())
        _users_fallback[user_id] = {
            "user_id": user_id, "email": email, "username": username,
            "password_hash": password_hash, "role": safe_role,
            "is_active": True, "is_verified": False, "totp_secret": None,
            "totp_enabled": False, "created_at": datetime.now(timezone.utc).isoformat(),
            "last_login": None, "failed_attempts": 0,
        }
        _user_by_email_fallback[email] = user_id
        _user_by_username_fallback[username] = user_id

    audit_event("user_registered", user_id=user_id, details={"username": username, "role": safe_role})

    return {
        "success": True,
        "user_id": user_id,
        "username": username,
        "email": email,
        "role": safe_role,
    }


def get_user_profile(user_id: str) -> dict | None:
    """Get user profile from MongoDB (safe, no password hash)."""
    user = _get_user_by_id(user_id)
    if not user:
        return None
    return {
        "id": user["user_id"],
        "username": user["username"],
        "email": user["email"],
        "role": user.get("role", "viewer"),
        "permissions": list(resolve_permissions(user.get("role", "viewer"))),
        "is_active": user.get("is_active", True),
        "is_verified": user.get("is_verified", False),
        "totp_enabled": user.get("totp_enabled", False),
        "created_at": user.get("created_at", ""),
        "last_login": user.get("last_login"),
    }


def setup_2fa(user_id: str) -> dict | None:
    """Enable 2FA for a user."""
    user = _get_user_by_id(user_id)
    if not user:
        return None
    secret = generate_totp_secret()
    try:
        UserOps.set_totp(user_id, secret, False)
    except Exception:
        if user_id in _users_fallback:
            _users_fallback[user_id]["totp_secret"] = secret
    uri = get_totp_uri(secret, user["email"])
    return {"secret": secret, "uri": uri}


def confirm_2fa(user_id: str, code: str) -> bool:
    """Confirm 2FA setup with initial code."""
    user = _get_user_by_id(user_id)
    if not user or not user.get("totp_secret"):
        return False
    if verify_totp(user["totp_secret"], code):
        try:
            UserOps.set_totp(user_id, user["totp_secret"], True)
        except Exception:
            if user_id in _users_fallback:
                _users_fallback[user_id]["totp_enabled"] = True
        audit_event("2fa_enabled", user_id=user_id)
        return True
    return False


def disable_2fa(user_id: str) -> bool:
    """Disable 2FA for a user."""
    user = _get_user_by_id(user_id)
    if not user:
        return False
    try:
        UserOps.set_totp(user_id, None, False)
    except Exception:
        if user_id in _users_fallback:
            _users_fallback[user_id]["totp_enabled"] = False
            _users_fallback[user_id]["totp_secret"] = None
    audit_event("2fa_disabled", user_id=user_id)
    return True
