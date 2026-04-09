import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import Any


class JWTValidationError(Exception):
    pass


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _b64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode((value + padding).encode())


def _json_bytes(value: dict[str, Any]) -> bytes:
    return json.dumps(value, separators=(",", ":"), sort_keys=True).encode()


def issue_token(
    subject: str,
    secret: str,
    ttl_seconds: int = 3600,
    claims: dict[str, Any] | None = None,
    token_type: str = "access",
) -> str:
    now = int(time.time())
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": subject,
        "iat": now,
        "nbf": now,
        "exp": now + ttl_seconds,
        "jti": secrets.token_hex(16),
        "token_type": token_type,
    }
    if claims:
        payload.update(claims)

    encoded_header = _b64url_encode(_json_bytes(header))
    encoded_payload = _b64url_encode(_json_bytes(payload))
    signing_input = f"{encoded_header}.{encoded_payload}".encode()
    signature = hmac.new(secret.encode(), signing_input, hashlib.sha256).digest()
    encoded_signature = _b64url_encode(signature)
    return f"{encoded_header}.{encoded_payload}.{encoded_signature}"


def decode_token(token: str, secret: str, leeway_seconds: int = 30) -> dict[str, Any]:
    try:
        encoded_header, encoded_payload, encoded_signature = token.split(".")
    except ValueError as exc:
        raise JWTValidationError("Malformed token") from exc

    signing_input = f"{encoded_header}.{encoded_payload}".encode()
    expected_signature = hmac.new(secret.encode(), signing_input, hashlib.sha256).digest()
    actual_signature = _b64url_decode(encoded_signature)

    if not hmac.compare_digest(expected_signature, actual_signature):
        raise JWTValidationError("Invalid signature")

    try:
        payload = json.loads(_b64url_decode(encoded_payload).decode())
    except Exception as exc:
        raise JWTValidationError("Invalid payload") from exc

    now = int(time.time())
    if payload.get("nbf", 0) > now + leeway_seconds:
        raise JWTValidationError("Token not active")
    if payload.get("exp", 0) <= now - leeway_seconds:
        raise JWTValidationError("Token expired")
    return payload


def validate_token(token: str, secret: str) -> bool:
    try:
        decode_token(token, secret)
        return True
    except JWTValidationError:
        return False
