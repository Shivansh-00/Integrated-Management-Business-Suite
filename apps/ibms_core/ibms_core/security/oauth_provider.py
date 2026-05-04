"""
IBMS Google OAuth2 Helper
==========================
Implements Google OAuth2 authorization-code flow with CSRF state protection.
"""

from __future__ import annotations

import os
import secrets
import time
import urllib.parse

import httpx

GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET: str = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI: str = os.getenv(
    "GOOGLE_REDIRECT_URI", "http://localhost:8000/api/auth/google/callback"
)

# In-memory CSRF state store: {state_token: expiry_epoch}
_oauth_states: dict[str, float] = {}


def _cleanup_states() -> None:
    """Remove expired state tokens."""
    now = time.time()
    expired = [s for s, exp in list(_oauth_states.items()) if exp < now]
    for s in expired:
        _oauth_states.pop(s, None)


def generate_google_auth_url() -> str:
    """
    Generate a Google OAuth2 authorization URL with a CSRF state token.
    The state is single-use and expires in 10 minutes.
    """
    _cleanup_states()
    state = secrets.token_urlsafe(32)
    _oauth_states[state] = time.time() + 600  # 10-minute window

    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid profile email",
        "state": state,
        "access_type": "offline",
        "prompt": "select_account",
    }
    return "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(params)


def validate_oauth_state(state: str) -> bool:
    """
    Validate and *consume* a CSRF state token (single-use).
    Returns False if unknown or expired.
    """
    if not state:
        return False
    expiry = _oauth_states.pop(state, None)
    if expiry is None:
        return False
    return time.time() < expiry


async def exchange_google_code(code: str) -> dict:
    """
    Exchange an authorization code for Google OAuth tokens.
    Returns the token response dict (contains access_token, id_token, etc.).
    Raises httpx.HTTPStatusError on failure.
    """
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uri": GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
        )
        resp.raise_for_status()
        return resp.json()


async def get_google_user_info(access_token: str) -> dict:
    """
    Fetch the authenticated user's profile from Google's userinfo endpoint.
    Returns a dict with at minimum: sub, email, name, picture.
    """
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        resp.raise_for_status()
        return resp.json()


def get_oauth_provider_config() -> dict:
    """Return OAuth provider availability info (consumed by /api/auth/oauth-config)."""
    return {
        "google": {
            "enabled": bool(GOOGLE_CLIENT_ID),
            "auth_url": "/api/auth/google",
        },
        "providers": ["google"] if GOOGLE_CLIENT_ID else [],
    }

