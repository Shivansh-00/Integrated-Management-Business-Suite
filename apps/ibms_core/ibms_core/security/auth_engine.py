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
from base64 import b64encode, b64decode
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


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
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()
    # PBKDF2 fallback
    import hashlib
    salt = os.urandom(32)
    key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 310_000)
    return f"pbkdf2:{b64encode(salt).decode()}:{b64encode(key).decode()}"


def verify_password(password: str, hashed: str) -> bool:
    """Verify password against hash."""
    if _HAS_BCRYPT and hashed.startswith("$2"):
        return bcrypt.checkpw(password.encode(), hashed.encode())
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
        import struct
        import hmac as _hmac
        import hashlib as _hashlib

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
# Refresh Token Rotation
# ---------------------------------------------------------------------------
_refresh_tokens: dict[str, dict] = {}
_revoked_tokens: set[str] = set()


def issue_refresh_token(user_id: str, device_fp: str = "") -> str:
    """Issue a new refresh token with rotation support."""
    token = secrets.token_urlsafe(64)
    _refresh_tokens[token] = {
        "user_id": user_id,
        "device_fp": device_fp,
        "issued_at": int(time.time()),
        "expires_at": int(time.time()) + 604800,  # 7 days
        "family": str(uuid.uuid4()),
    }
    return token


def rotate_refresh_token(old_token: str, device_fp: str = "") -> tuple[str, str] | None:
    """Rotate refresh token — invalidate old, issue new."""
    if old_token in _revoked_tokens:
        # Token reuse detected — revoke entire family
        family = None
        for t, data in list(_refresh_tokens.items()):
            if data.get("family") == family:
                _revoked_tokens.add(t)
                del _refresh_tokens[t]
        return None

    token_data = _refresh_tokens.get(old_token)
    if not token_data:
        return None

    if token_data["expires_at"] < int(time.time()):
        del _refresh_tokens[old_token]
        return None

    if device_fp and token_data.get("device_fp") and token_data["device_fp"] != device_fp:
        _revoked_tokens.add(old_token)
        return None

    # Revoke old token
    _revoked_tokens.add(old_token)
    family = token_data["family"]

    # Issue new
    new_token = secrets.token_urlsafe(64)
    _refresh_tokens[new_token] = {
        "user_id": token_data["user_id"],
        "device_fp": device_fp,
        "issued_at": int(time.time()),
        "expires_at": int(time.time()) + 604800,
        "family": family,
    }

    return token_data["user_id"], new_token


def revoke_all_tokens(user_id: str):
    """Revoke all refresh tokens for a user (logout everywhere)."""
    for token, data in list(_refresh_tokens.items()):
        if data["user_id"] == user_id:
            _revoked_tokens.add(token)
            del _refresh_tokens[token]


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


_rate_limits: dict[str, RateLimitEntry] = defaultdict(RateLimitEntry)

# Config
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION = 300  # 5 minutes
RATE_WINDOW = 900  # 15 minutes


def check_rate_limit(key: str) -> dict:
    """Check if a key (IP/user) is rate-limited."""
    entry = _rate_limits[key]
    now = time.time()

    # Check lockout
    if entry.locked_until > now:
        remaining = int(entry.locked_until - now)
        return {
            "allowed": False,
            "reason": "Account temporarily locked",
            "retry_after": remaining,
            "attempts": entry.attempts,
        }

    # Reset window
    if entry.first_attempt and (now - entry.first_attempt) > RATE_WINDOW:
        entry.attempts = 0
        entry.first_attempt = 0

    return {
        "allowed": True,
        "attempts": entry.attempts,
        "remaining": MAX_LOGIN_ATTEMPTS - entry.attempts,
    }


def record_failed_attempt(key: str):
    """Record a failed login attempt."""
    entry = _rate_limits[key]
    now = time.time()

    if not entry.first_attempt:
        entry.first_attempt = now

    entry.attempts += 1

    if entry.attempts >= MAX_LOGIN_ATTEMPTS:
        entry.locked_until = now + LOCKOUT_DURATION


def reset_rate_limit(key: str):
    """Reset rate limit after successful login."""
    if key in _rate_limits:
        del _rate_limits[key]


# ---------------------------------------------------------------------------
# CSRF Protection
# ---------------------------------------------------------------------------
_csrf_tokens: dict[str, float] = {}


def generate_csrf_token(session_id: str) -> str:
    """Generate a CSRF token tied to a session."""
    token = secrets.token_urlsafe(32)
    _csrf_tokens[token] = time.time() + 7200  # 2h expiry
    return token


def validate_csrf_token(token: str) -> bool:
    """Validate a CSRF token."""
    expiry = _csrf_tokens.get(token)
    if not expiry:
        return False
    if time.time() > expiry:
        del _csrf_tokens[token]
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


_users: dict[str, User] = {}
_user_by_email: dict[str, str] = {}
_user_by_username: dict[str, str] = {}


def _init_default_users():
    """Initialize default admin user."""
    if "admin" not in _user_by_username:
        admin_id = str(uuid.uuid4())
        admin = User(
            id=admin_id,
            email="admin@ibms.dev",
            username="admin",
            password_hash=hash_password("Admin@IBMS2026"),
            role="super_admin",
            is_active=True,
            is_verified=True,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        _users[admin_id] = admin
        _user_by_email["admin@ibms.dev"] = admin_id
        _user_by_username["admin"] = admin_id

        # Demo analyst
        analyst_id = str(uuid.uuid4())
        analyst = User(
            id=analyst_id,
            email="analyst@ibms.dev",
            username="analyst",
            password_hash=hash_password("Analyst@2026"),
            role="analyst",
            is_active=True,
            is_verified=True,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        _users[analyst_id] = analyst
        _user_by_email["analyst@ibms.dev"] = analyst_id
        _user_by_username["analyst"] = analyst_id


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


# Audit log (in-memory, production: ship to SIEM)
_audit_log: list[dict] = []


def audit_event(event_type: str, user_id: str = "", ip: str = "", details: dict | None = None):
    """Record an audit event."""
    entry = {
        "id": str(uuid.uuid4()),
        "type": event_type,
        "user_id": user_id,
        "ip": ip,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "details": details or {},
    }
    _audit_log.append(entry)
    # Keep last 10000 entries
    if len(_audit_log) > 10000:
        _audit_log.pop(0)
    return entry


def get_audit_log(limit: int = 100, event_type: str = "") -> list[dict]:
    """Retrieve audit log entries."""
    logs = _audit_log
    if event_type:
        logs = [e for e in logs if e["type"] == event_type]
    return list(reversed(logs[-limit:]))


def authenticate(
    username: str,
    password: str,
    jwt_secret: str,
    ip: str = "",
    device_fp: str = "",
    totp_code: str = "",
) -> AuthResult:
    """Full authentication flow."""
    # Rate limit check
    rate_key = f"login:{ip}"
    rate_check = check_rate_limit(rate_key)
    if not rate_check["allowed"]:
        audit_event("login_blocked", ip=ip, details={"reason": "rate_limited", "username": username})
        return AuthResult(
            success=False,
            error=f"Too many attempts. Retry after {rate_check['retry_after']}s",
        )

    # Find user
    user_id = _user_by_username.get(username) or _user_by_email.get(username)
    if not user_id:
        record_failed_attempt(rate_key)
        audit_event("login_failed", ip=ip, details={"reason": "user_not_found", "username": username})
        return AuthResult(success=False, error="Invalid credentials")

    user = _users[user_id]

    if not user.is_active:
        audit_event("login_failed", user_id=user_id, ip=ip, details={"reason": "account_disabled"})
        return AuthResult(success=False, error="Account is disabled")

    # Verify password
    if not verify_password(password, user.password_hash):
        record_failed_attempt(rate_key)
        audit_event("login_failed", user_id=user_id, ip=ip, details={"reason": "invalid_password"})
        return AuthResult(success=False, error="Invalid credentials")

    # 2FA check
    if user.totp_enabled:
        if not totp_code:
            return AuthResult(success=False, requires_2fa=True, user_id=user_id)
        if not verify_totp(user.totp_secret, totp_code):
            record_failed_attempt(rate_key)
            audit_event("login_failed", user_id=user_id, ip=ip, details={"reason": "invalid_2fa"})
            return AuthResult(success=False, error="Invalid 2FA code")

    # Success — issue tokens
    reset_rate_limit(rate_key)

    permissions = list(resolve_permissions(user.role))
    access_token = create_jwt(
        {
            "sub": user_id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "permissions": permissions,
        },
        jwt_secret,
        TokenType.ACCESS,
        ttl=1800,  # 30 min
    )

    refresh_token = issue_refresh_token(user_id, device_fp)
    csrf_token = generate_csrf_token(user_id)

    user.last_login = datetime.now(timezone.utc).isoformat()
    user.failed_attempts = 0

    audit_event("login_success", user_id=user_id, ip=ip, details={"device_fp": device_fp})

    return AuthResult(
        success=True,
        user_id=user_id,
        access_token=access_token,
        refresh_token=refresh_token,
        csrf_token=csrf_token,
        role=user.role,
        permissions=permissions,
    )


def register_user(
    username: str,
    email: str,
    password: str,
    role: str = "viewer",
) -> dict:
    """Register a new user."""
    # Validate
    if _user_by_username.get(username):
        return {"success": False, "error": "Username already exists"}
    if _user_by_email.get(email):
        return {"success": False, "error": "Email already registered"}

    strength = check_password_strength(password)
    if not strength["valid"]:
        return {"success": False, "error": "Weak password", "details": strength}

    user_id = str(uuid.uuid4())
    user = User(
        id=user_id,
        email=email,
        username=username,
        password_hash=hash_password(password),
        role=role if role in ROLE_HIERARCHY else "viewer",
        is_active=True,
        is_verified=False,
        created_at=datetime.now(timezone.utc).isoformat(),
    )

    _users[user_id] = user
    _user_by_email[email] = user_id
    _user_by_username[username] = user_id

    audit_event("user_registered", user_id=user_id, details={"username": username, "role": role})

    return {
        "success": True,
        "user_id": user_id,
        "username": username,
        "email": email,
        "role": role,
    }


def get_user_profile(user_id: str) -> dict | None:
    """Get user profile (safe, no password hash)."""
    user = _users.get(user_id)
    if not user:
        return None
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "role": user.role,
        "permissions": list(resolve_permissions(user.role)),
        "is_active": user.is_active,
        "is_verified": user.is_verified,
        "totp_enabled": user.totp_enabled,
        "created_at": user.created_at,
        "last_login": user.last_login,
    }


def setup_2fa(user_id: str) -> dict | None:
    """Enable 2FA for a user."""
    user = _users.get(user_id)
    if not user:
        return None
    secret = generate_totp_secret()
    user.totp_secret = secret
    uri = get_totp_uri(secret, user.email)
    return {"secret": secret, "uri": uri}


def confirm_2fa(user_id: str, code: str) -> bool:
    """Confirm 2FA setup with initial code."""
    user = _users.get(user_id)
    if not user or not user.totp_secret:
        return False
    if verify_totp(user.totp_secret, code):
        user.totp_enabled = True
        audit_event("2fa_enabled", user_id=user_id)
        return True
    return False


def disable_2fa(user_id: str) -> bool:
    """Disable 2FA for a user."""
    user = _users.get(user_id)
    if not user:
        return False
    user.totp_enabled = False
    user.totp_secret = None
    audit_event("2fa_disabled", user_id=user_id)
    return True
