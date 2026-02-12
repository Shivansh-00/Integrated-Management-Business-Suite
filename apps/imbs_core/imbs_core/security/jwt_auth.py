import hashlib
import hmac
import json
import time


def issue_token(subject: str, secret: str, ttl_seconds: int = 3600):
    payload = {"sub": subject, "exp": int(time.time()) + ttl_seconds}
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    sig = hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()
    return f"{body}.{sig}"


def validate_token(token: str, secret: str):
    body, sig = token.rsplit(".", 1)
    expected = hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, sig):
        return False
    payload = json.loads(body)
    return payload.get("exp", 0) >= int(time.time())
