import time
from typing import Any

import frappe
from frappe import _

from ibms_core.security.jwt_auth import decode_token, issue_token

ACCESS_TTL_SECONDS = 1800
REFRESH_TTL_SECONDS = 604800
RATE_LIMIT_WINDOW_SECONDS = 60
RATE_LIMIT_ATTEMPTS = 20


def _auth_secret() -> str:
    return frappe.conf.get("ibms_jwt_secret") or frappe.local.conf.get("encryption_key") or "ibms-default-secret"


def _rate_limit_key(identifier: str) -> str:
    now_window = int(time.time()) // RATE_LIMIT_WINDOW_SECONDS
    return f"ibms:auth:rate:{identifier}:{now_window}"


def _enforce_rate_limit(identifier: str):
    cache = frappe.cache()
    key = _rate_limit_key(identifier)
    current = int(cache.get_value(key) or 0)
    if current >= RATE_LIMIT_ATTEMPTS:
        frappe.throw(_("Too many requests. Retry in one minute."), frappe.TooManyRequestsError)
    cache.set_value(key, current + 1, expires_in_sec=RATE_LIMIT_WINDOW_SECONDS)


def _token_bundle(user: str, role_profile_name: str | None = None) -> dict[str, Any]:
    claims = {
        "roles": frappe.get_roles(user),
        "role_profile": role_profile_name,
    }
    access_token = issue_token(user, _auth_secret(), ttl_seconds=ACCESS_TTL_SECONDS, claims=claims, token_type="access")
    refresh_token = issue_token(user, _auth_secret(), ttl_seconds=REFRESH_TTL_SECONDS, claims={"scope": "refresh"}, token_type="refresh")
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "Bearer",
        "expires_in": ACCESS_TTL_SECONDS,
    }


@frappe.whitelist(allow_guest=True, methods=["POST"])
def register_user(email: str, first_name: str, last_name: str = "", password: str = "", role_profile: str = ""):
    _enforce_rate_limit(frappe.local.request_ip or "guest")

    if frappe.db.exists("User", email):
        frappe.throw(_("User already exists"), frappe.DuplicateEntryError)

    user = frappe.get_doc(
        {
            "doctype": "User",
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "new_password": password,
            "send_welcome_email": 0,
            "enabled": 1,
            "role_profile_name": role_profile or "",
        }
    )
    user.flags.ignore_permissions = True
    user.insert()

    return {"message": "User registered", "user": user.name}


@frappe.whitelist(allow_guest=True, methods=["POST"])
def login_with_jwt(username: str, password: str):
    _enforce_rate_limit(f"{frappe.local.request_ip or 'guest'}:{username}")

    login_manager = frappe.auth.LoginManager()
    login_manager.authenticate(username, password)
    login_manager.post_login()

    user_doc = frappe.get_doc("User", login_manager.user)
    return {
        "message": "Authenticated",
        "user": user_doc.name,
        "full_name": user_doc.full_name,
        "roles": frappe.get_roles(user_doc.name),
        "tokens": _token_bundle(user_doc.name, user_doc.role_profile_name),
    }


@frappe.whitelist(allow_guest=True, methods=["POST"])
def refresh_jwt(refresh_token: str):
    payload = decode_token(refresh_token, _auth_secret())
    if payload.get("token_type") != "refresh":
        frappe.throw("Invalid token type", frappe.AuthenticationError)

    user = payload.get("sub")
    if not user or not frappe.db.exists("User", user):
        frappe.throw("Unknown user", frappe.AuthenticationError)

    user_doc = frappe.get_doc("User", user)
    if not user_doc.enabled:
        frappe.throw("User disabled", frappe.AuthenticationError)

    return {
        "message": "Token refreshed",
        "tokens": _token_bundle(user_doc.name, user_doc.role_profile_name),
    }


@frappe.whitelist(methods=["GET"])
def whoami():
    if frappe.session.user == "Guest":
        frappe.throw("Not authenticated", frappe.AuthenticationError)

    user_doc = frappe.get_doc("User", frappe.session.user)
    return {
        "user": user_doc.name,
        "full_name": user_doc.full_name,
        "email": user_doc.email,
        "roles": frappe.get_roles(user_doc.name),
    }
