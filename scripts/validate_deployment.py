#!/usr/bin/env python3
"""
IBMS Enterprise — Deployment Validation Script
================================================
Validates all service connections and endpoints after deployment.

Usage:
  python scripts/validate_deployment.py                         # localhost:8000
  python scripts/validate_deployment.py https://ibms.example.com
"""

from __future__ import annotations

import json
import sys
import time

try:
    import httpx
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "httpx"])
    import httpx

DEFAULT_BASE = "http://localhost:8000"

# ─── Checks ─────────────────────────────────────────────────────────────────

def check_health(client: httpx.Client, base: str) -> dict:
    """GET /api/health — core health endpoint."""
    resp = client.get(f"{base}/api/health")
    data = resp.json()
    ok = resp.status_code == 200 and data.get("status") == "healthy"
    return {"name": "Health Endpoint", "ok": ok, "detail": data}


def check_supabase(client: httpx.Client, base: str) -> dict:
    """Check Supabase connectivity via health endpoint details."""
    resp = client.get(f"{base}/api/health")
    data = resp.json()
    db_ok = data.get("database") in ("connected", "healthy", True)
    return {
        "name": "Supabase Connection",
        "ok": db_ok,
        "detail": {"database": data.get("database", "unknown")},
    }


def check_redis(client: httpx.Client, base: str) -> dict:
    """Check Redis connectivity via health endpoint details."""
    resp = client.get(f"{base}/api/health")
    data = resp.json()
    redis_ok = data.get("redis") in ("connected", "healthy", True)
    return {
        "name": "Redis Connection",
        "ok": redis_ok,
        "detail": {"redis": data.get("redis", "unknown")},
    }


def check_frontend(client: httpx.Client, base: str) -> dict:
    """GET / — frontend SPA serves HTML."""
    resp = client.get(f"{base}/")
    ok = resp.status_code == 200 and "text/html" in resp.headers.get("content-type", "")
    return {"name": "Frontend (HTML)", "ok": ok, "detail": {"status": resp.status_code}}


def check_api_modules(client: httpx.Client, base: str) -> dict:
    """GET /api/modules — public module listing."""
    resp = client.get(f"{base}/api/modules")
    ok = resp.status_code == 200
    return {"name": "API /modules", "ok": ok, "detail": {"status": resp.status_code}}


def check_kpis(client: httpx.Client, base: str) -> dict:
    """GET /api/kpis — KPI dashboard data."""
    resp = client.get(f"{base}/api/kpis")
    ok = resp.status_code == 200
    return {"name": "API /kpis", "ok": ok, "detail": {"status": resp.status_code}}


def check_security_headers(client: httpx.Client, base: str) -> dict:
    """Verify security response headers."""
    resp = client.get(f"{base}/")
    headers = resp.headers
    checks = {
        "x-frame-options": headers.get("x-frame-options", "").upper() == "DENY",
        "x-content-type-options": headers.get("x-content-type-options", "") == "nosniff",
    }
    all_ok = all(checks.values())
    return {"name": "Security Headers", "ok": all_ok, "detail": checks}


def check_websocket(client: httpx.Client, base: str) -> dict:
    """Attempt WebSocket upgrade on /ws/kpis — expect 403 (no token) or upgrade."""
    try:
        resp = client.get(
            f"{base}/ws/kpis",
            headers={"Upgrade": "websocket", "Connection": "Upgrade"},
        )
        # 403 = auth required (good — WS endpoint exists), 101 = upgrade
        ok = resp.status_code in (101, 403, 426)
        return {"name": "WebSocket /ws/kpis", "ok": ok, "detail": {"status": resp.status_code}}
    except Exception as e:
        return {"name": "WebSocket /ws/kpis", "ok": False, "detail": {"error": str(e)}}


CHECKS = [
    check_health,
    check_supabase,
    check_redis,
    check_frontend,
    check_api_modules,
    check_kpis,
    check_security_headers,
    check_websocket,
]


# ─── Runner ──────────────────────────────────────────────────────────────────

def run_all(base: str) -> bool:
    print(f"\n{'=' * 60}")
    print(f"  IBMS Deployment Validation")
    print(f"  Target: {base}")
    print(f"{'=' * 60}\n")

    client = httpx.Client(timeout=15, follow_redirects=True)
    results: list[dict] = []

    # Wait for server readiness (up to 30s)
    for attempt in range(6):
        try:
            client.get(f"{base}/api/health")
            break
        except httpx.ConnectError:
            if attempt == 5:
                print("  [FAIL] Server not reachable after 30s\n")
                return False
            print(f"  Waiting for server... ({(attempt + 1) * 5}s)")
            time.sleep(5)

    for check_fn in CHECKS:
        result = check_fn(client, base)
        results.append(result)
        status = "\u2705" if result["ok"] else "\u274c"
        print(f"  {status} {result['name']}")
        if not result["ok"]:
            print(f"     Detail: {json.dumps(result['detail'], indent=2)}")

    client.close()

    passed = sum(1 for r in results if r["ok"])
    total = len(results)
    print(f"\n{'=' * 60}")
    print(f"  Result: {passed}/{total} checks passed")
    print(f"{'=' * 60}\n")

    return passed == total


if __name__ == "__main__":
    base_url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_BASE
    # Strip trailing slash
    base_url = base_url.rstrip("/")
    success = run_all(base_url)
    sys.exit(0 if success else 1)
