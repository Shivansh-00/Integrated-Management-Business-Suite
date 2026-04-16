"""
IBMS — Repair Billing & Full Redeploy
======================================
1. Authenticates via OAuth browser flow
2. Lists billing accounts and finds an OPEN one
3. Re-links billing to the project
4. Enables required APIs
5. Triggers Cloud Build
6. Deploys to Cloud Run with full env vars (Supabase, Redis, etc.)

Usage:
  python deploy/gcp/repair_and_deploy.py
"""
from __future__ import annotations

import base64
import hashlib
import http.server
import io
import json
import os
import secrets
import sys
import tarfile
import time
import urllib.parse
import webbrowser
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from dotenv import load_dotenv

# Load .env from project root
_project_root = Path(__file__).resolve().parent.parent.parent
load_dotenv(_project_root / ".env")

# ─── Config ──────────────────────────────────────────────────────────────
PROJECT_ID = os.getenv("GCP_PROJECT_ID", "total-handler-463313-e2")
REGION = "asia-south1"
SERVICE_NAME = "ibms-web"
REPO_NAME = "ibms-docker"
CONNECTOR_NAME = "ibms-connector"

CLIENT_ID = "764086051850-6qr4p6gpi6hn506pt8ejuq83di341hur.apps.googleusercontent.com"
CLIENT_SECRET = "d-FL95Q19q7MQmFpd7hHD0Ty"
REDIRECT_URI = "http://localhost:8085"

CB_URL = f"https://cloudbuild.googleapis.com/v1/projects/{PROJECT_ID}"
STORAGE_URL = "https://storage.googleapis.com"
RUN_URL = "https://run.googleapis.com/v2"

gcp_token = None

# ─── Robust HTTP session ────────────────────────────────────────────────
session = requests.Session()
retry_strategy = Retry(
    total=5, backoff_factor=2,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["GET", "POST", "PATCH", "PUT", "DELETE"],
    raise_on_status=False,
)
adapter = HTTPAdapter(max_retries=retry_strategy)
session.mount("https://", adapter)
session.mount("http://", adapter)


def headers():
    return {"Authorization": f"Bearer {gcp_token}", "Content-Type": "application/json"}


# ─── Step 0: Authenticate ───────────────────────────────────────────────
def authenticate():
    global gcp_token
    code_verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(code_verifier.encode()).digest()
    code_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    state = secrets.token_urlsafe(16)
    auth_code = None

    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            nonlocal auth_code
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            if "code" in qs and qs.get("state", [None])[0] == state:
                auth_code = qs["code"][0]
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(b"<h2>OK - return to terminal</h2>")
            else:
                self.send_response(400)
                self.end_headers()

        def log_message(self, *a):
            pass

    url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode({
        "client_id": CLIENT_ID, "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": "https://www.googleapis.com/auth/cloud-platform",
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "access_type": "offline",
    })
    print(f"\n[Auth] Opening browser for Google sign-in...")
    webbrowser.open(url)
    srv = http.server.HTTPServer(("127.0.0.1", 8085), H)
    srv.timeout = 120
    srv.handle_request()
    srv.server_close()
    if not auth_code:
        print("[FAIL] Authentication failed")
        sys.exit(1)

    resp = session.post("https://oauth2.googleapis.com/token", data={
        "client_id": CLIENT_ID, "client_secret": CLIENT_SECRET,
        "code": auth_code, "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code", "code_verifier": code_verifier,
    }, timeout=30)
    gcp_token = resp.json().get("access_token")
    if not gcp_token:
        print(f"[FAIL] Token exchange failed: {resp.text[:300]}")
        sys.exit(1)
    print("[Auth] OK\n")


# ─── Step 1: Repair billing ─────────────────────────────────────────────
def repair_billing():
    print("=" * 60)
    print("  Step 1: Check & Repair Billing")
    print("=" * 60)

    # Check current billing state
    resp = session.get(
        f"https://cloudbilling.googleapis.com/v1/projects/{PROJECT_ID}/billingInfo",
        headers={"Authorization": f"Bearer {gcp_token}"}, timeout=30)
    if resp.status_code == 200:
        info = resp.json()
        enabled = info.get("billingEnabled", False)
        acct = info.get("billingAccountName", "")
        print(f"  Current billing: enabled={enabled}, account={acct}")
        if enabled:
            print("  [OK] Billing is already active!")
            return True
    else:
        print(f"  Could not check billing: {resp.status_code}")

    # List all billing accounts
    resp2 = session.get(
        "https://cloudbilling.googleapis.com/v1/billingAccounts",
        headers={"Authorization": f"Bearer {gcp_token}"}, timeout=30)
    if resp2.status_code != 200:
        print(f"  [FAIL] Cannot list billing accounts: {resp2.status_code}")
        return False

    accts = resp2.json().get("billingAccounts", [])
    open_acct = None
    print(f"\n  Found {len(accts)} billing account(s):")
    for a in accts:
        name = a["name"]
        display = a.get("displayName", "")
        is_open = a.get("open", False)
        print(f"    {name} ({display}) — open={is_open}")
        if is_open and not open_acct:
            open_acct = name

    if not open_acct:
        print("\n  [FAIL] No OPEN billing account found.")
        print("  Please go to https://console.cloud.google.com/billing")
        print("  and resolve the delinquent billing account, then re-run this script.")
        return False

    # Link the open billing account to our project
    print(f"\n  Linking {open_acct} to project {PROJECT_ID}...")
    resp3 = session.put(
        f"https://cloudbilling.googleapis.com/v1/projects/{PROJECT_ID}/billingInfo",
        headers=headers(),
        json={"billingAccountName": open_acct},
        timeout=30)
    if resp3.status_code == 200:
        result = resp3.json()
        if result.get("billingEnabled"):
            print("  [OK] Billing re-enabled!")
            return True
        else:
            print(f"  Billing link response: {json.dumps(result)[:300]}")
            print("  [WARN] Billing may not be fully active yet.")
            return False
    else:
        print(f"  [FAIL] Could not link billing: {resp3.status_code} {resp3.text[:300]}")
        return False


# ─── Step 2: Enable APIs ────────────────────────────────────────────────
def enable_apis():
    print("\n" + "=" * 60)
    print("  Step 2: Enable Required APIs")
    print("=" * 60)
    apis = [
        "cloudbuild.googleapis.com",
        "run.googleapis.com",
        "artifactregistry.googleapis.com",
        "vpcaccess.googleapis.com",
        "compute.googleapis.com",
        "secretmanager.googleapis.com",
        "redis.googleapis.com",
    ]
    for api in apis:
        try:
            r = session.post(
                f"https://serviceusage.googleapis.com/v1/projects/{PROJECT_ID}/services/{api}:enable",
                headers=headers(), timeout=60)
            if r.status_code == 200:
                print(f"  [OK] {api}")
            else:
                print(f"  [{r.status_code}] {api}: {r.text[:150]}")
        except Exception as e:
            print(f"  [ERR] {api}: {e}")
    print("  Waiting 10s for API propagation...")
    time.sleep(10)


# ─── Step 3: Build container ────────────────────────────────────────────
def build_container():
    print("\n" + "=" * 60)
    print("  Step 3: Build Container Image via Cloud Build")
    print("=" * 60)

    # Create source archive
    src = _project_root
    buf = io.BytesIO()
    skip_dirs = {".git", "__pycache__", "node_modules", ".venv", "deploy",
                 ".mypy_cache", "docs", "scripts", ".env"}
    skip_ext = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".svg", ".pdf", ".log"}
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for p in sorted(src.rglob("*")):
            rel = p.relative_to(src)
            if any(part in skip_dirs for part in rel.parts):
                continue
            if p.is_file() and p.suffix.lower() not in skip_ext:
                tar.add(str(p), arcname=str(rel))
    buf.seek(0)
    data_bytes = buf.getvalue()
    total_size = len(data_bytes)
    print(f"  Source archive: {total_size / 1024:.0f} KB")

    # Upload to Cloud Storage (resumable)
    bucket = f"{PROJECT_ID}_cloudbuild"
    obj_name = f"source/ibms-src-{int(time.time())}.tar.gz"
    print(f"  Uploading to gs://{bucket}/{obj_name}...")

    init_url = (f"{STORAGE_URL}/upload/storage/v1/b/{bucket}/o"
                f"?uploadType=resumable&name={obj_name}")
    init_resp = session.post(init_url, headers={
        **headers(),
        "X-Upload-Content-Type": "application/gzip",
        "X-Upload-Content-Length": str(total_size),
    }, json={"name": obj_name}, timeout=60)

    if init_resp.status_code != 200:
        print(f"  [FAIL] Upload init: {init_resp.status_code} {init_resp.text[:300]}")
        return None
    upload_uri = init_resp.headers.get("Location")
    if not upload_uri:
        print("  [FAIL] No upload URI")
        return None

    # Upload in 2MB chunks
    CHUNK = 2 * 1024 * 1024
    offset = 0
    while offset < total_size:
        end = min(offset + CHUNK, total_size)
        chunk_data = data_bytes[offset:end]
        content_range = f"bytes {offset}-{end - 1}/{total_size}"
        for attempt in range(5):
            try:
                cr = session.put(upload_uri, data=chunk_data,
                                 headers={"Content-Range": content_range,
                                          "Content-Type": "application/gzip"},
                                 timeout=120)
                if cr.status_code in (200, 201):
                    offset = total_size
                    break
                elif cr.status_code == 308:
                    offset = end
                    break
                else:
                    print(f"  Chunk error {cr.status_code}, retry {attempt + 1}")
                    time.sleep(2 ** attempt)
            except Exception as e:
                print(f"  Chunk exception ({attempt + 1}/5): {e}")
                time.sleep(2 ** attempt)
        else:
            print("  [FAIL] Upload failed after 5 retries")
            return None
        pct = min(100, int(offset / total_size * 100))
        if pct % 25 == 0 or pct == 100:
            print(f"  Upload: {pct}%")

    # Trigger Cloud Build
    tag = f"v{int(time.time())}"
    image = f"{REGION}-docker.pkg.dev/{PROJECT_ID}/{REPO_NAME}/{SERVICE_NAME}:{tag}"
    image_latest = f"{REGION}-docker.pkg.dev/{PROJECT_ID}/{REPO_NAME}/{SERVICE_NAME}:latest"
    build_body = {
        "source": {"storageSource": {"bucket": bucket, "object": obj_name}},
        "steps": [{"name": "gcr.io/cloud-builders/docker",
                    "args": ["build", "--no-cache", "-t", image, "-t", image_latest, "."]}],
        "images": [image, image_latest],
        "timeout": "1200s",
    }
    print(f"  Triggering Cloud Build (image: {tag})...")
    session.close()  # Reset stale connections
    resp = session.post(f"{CB_URL}/builds", headers=headers(), json=build_body, timeout=60)
    if resp.status_code not in (200, 201):
        print(f"  [FAIL] Build trigger: {resp.status_code} {resp.text[:500]}")
        return None

    op_name = resp.json().get("name", "")
    print(f"  Build operation: {op_name}")
    print("  Waiting for build", end="", flush=True)
    start = time.time()
    while time.time() - start < 900:
        time.sleep(15)
        try:
            r = session.get(f"https://cloudbuild.googleapis.com/v1/{op_name}",
                            headers=headers(), timeout=60)
            if r.status_code == 200:
                data = r.json()
                if data.get("done"):
                    if data.get("error"):
                        print(f"\n  [FAIL] Build error: {json.dumps(data['error'])[:300]}")
                        return None
                    print(" DONE")
                    return image
            print(".", end="", flush=True)
        except Exception:
            print("x", end="", flush=True)
    print(" TIMEOUT")
    return image


# ─── Step 4: Deploy to Cloud Run ────────────────────────────────────────
def deploy_to_cloud_run(image):
    print("\n" + "=" * 60)
    print("  Step 4: Deploy to Cloud Run")
    print("=" * 60)

    # Get Redis host from Memorystore
    redis_url = ""
    try:
        resp = session.get(
            f"https://redis.googleapis.com/v1/projects/{PROJECT_ID}/locations/{REGION}/instances/ibms-redis",
            headers=headers(), timeout=30)
        if resp.status_code == 200:
            host = resp.json().get("host", "")
            port = resp.json().get("port", 6379)
            redis_url = f"redis://{host}:{port}/0"
            print(f"  Redis: {redis_url}")
        else:
            print(f"  Redis not found (will use in-memory fallback)")
    except Exception:
        print("  Redis check failed (will use in-memory fallback)")

    # Build env vars
    env_vars = {
        "SUPABASE_URL": os.getenv("SUPABASE_URL", ""),
        "SUPABASE_KEY": os.getenv("SUPABASE_KEY", ""),
        "REDIS_URL": redis_url,
        "SECRET_KEY": os.getenv("SECRET_KEY", secrets.token_urlsafe(48)),
        "JWT_SECRET": os.getenv("JWT_SECRET", os.getenv("SECRET_KEY", "")),
        "HOST": "0.0.0.0",
        "PORT": "8080",
        "RELOAD": "false",
        "COOKIE_SECURE": "true",
        "ENVIRONMENT": "production",
        "LOG_LEVEL": "info",
        "GROQ_API_KEY": os.getenv("GROQ_API_KEY", ""),
        "ALLOWED_ORIGINS": os.getenv("ALLOWED_ORIGINS", ""),
    }
    env_list = [{"name": k, "value": v} for k, v in env_vars.items() if v]

    print(f"  Env vars configured: {len(env_list)}")
    print(f"  SUPABASE_URL: {env_vars['SUPABASE_URL'][:50]}...")
    print(f"  REDIS_URL: {env_vars['REDIS_URL'] or '(in-memory fallback)'}")

    svc_body = {
        "template": {
            "containers": [{
                "image": image,
                "ports": [{"containerPort": 8080}],
                "env": env_list,
                "resources": {"limits": {"memory": "1Gi", "cpu": "1"}},
                "startupProbe": {
                    "httpGet": {"path": "/api/health", "port": 8080},
                    "initialDelaySeconds": 5,
                    "timeoutSeconds": 15,
                    "periodSeconds": 10,
                    "failureThreshold": 15,
                },
            }],
            "scaling": {"minInstanceCount": 0, "maxInstanceCount": 4},
            "vpcAccess": {
                "connector": f"projects/{PROJECT_ID}/locations/{REGION}/connectors/{CONNECTOR_NAME}",
                "egress": "PRIVATE_RANGES_ONLY",
            },
        },
    }

    svc_url = f"{RUN_URL}/projects/{PROJECT_ID}/locations/{REGION}/services/{SERVICE_NAME}"
    print(f"  Deploying to Cloud Run...")
    resp = session.patch(svc_url, headers=headers(), json=svc_body, timeout=60)
    if resp.status_code not in (200, 201):
        print(f"  [FAIL] Deploy: {resp.status_code} {resp.text[:500]}")
        return False

    op = resp.json()
    op_name = op.get("name", "")
    if op_name:
        print(f"  Operation: {op_name}")
        print("  Waiting for deployment", end="", flush=True)
        start = time.time()
        while time.time() - start < 300:
            time.sleep(10)
            try:
                r = session.get(f"https://run.googleapis.com/v2/{op_name}",
                                headers=headers(), timeout=30)
                if r.status_code == 200 and r.json().get("done"):
                    if r.json().get("error"):
                        print(f"\n  [FAIL] {r.json()['error']}")
                        return False
                    print(" DONE")
                    break
                print(".", end="", flush=True)
            except Exception:
                print("x", end="", flush=True)

    # Set public IAM
    try:
        session.post(f"{svc_url}:setIamPolicy", headers=headers(), json={
            "policy": {"bindings": [{"role": "roles/run.invoker", "members": ["allUsers"]}]}
        }, timeout=30)
    except Exception:
        pass

    # Get URL
    try:
        r = session.get(svc_url, headers=headers(), timeout=30)
        if r.status_code == 200:
            url = r.json().get("uri", "")
            if url:
                print(f"\n  [OK] Live URL: {url}")
                print(f"  Health:  {url}/api/health")
                print(f"  Docs:    {url}/api/docs")
                return url
    except Exception:
        pass

    return True


# ─── Step 5: Verify health ──────────────────────────────────────────────
def verify_health(base_url):
    print("\n" + "=" * 60)
    print("  Step 5: Verify Deployment Health")
    print("=" * 60)
    if not isinstance(base_url, str) or not base_url.startswith("http"):
        base_url = f"https://{SERVICE_NAME}-tivzf3l3ta-el.a.run.app"

    health_url = f"{base_url}/api/health"
    print(f"  Checking {health_url}...")

    # Give Cloud Run a moment to spin up
    time.sleep(10)
    for attempt in range(5):
        try:
            r = session.get(health_url, timeout=30)
            if r.status_code == 200:
                data = r.json()
                print(f"\n  Status:   {data.get('status', 'unknown')}")
                print(f"  Version:  {data.get('version', 'unknown')}")
                print(f"  Supabase: {data.get('supabase', False)}")
                print(f"  Redis:    {data.get('redis', False)}")
                print(f"  Uptime:   {data.get('uptime_human', 'unknown')}")
                if data.get("supabase"):
                    print("\n  [OK] Supabase connected!")
                else:
                    print("\n  [WARN] Supabase NOT connected — check SUPABASE_URL and SUPABASE_KEY")
                if data.get("redis"):
                    print("  [OK] Redis connected!")
                else:
                    print("  [INFO] Redis not connected (using in-memory fallback)")
                return True
            else:
                print(f"  Attempt {attempt + 1}: HTTP {r.status_code}")
        except Exception as e:
            print(f"  Attempt {attempt + 1}: {e}")
        time.sleep(10)

    print("  [WARN] Health check did not succeed after 5 attempts")
    print(f"  Try manually: {health_url}")
    return False


# ─── Main ────────────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("  IBMS — Repair Billing & Full Redeploy")
    print("=" * 60)
    print(f"  Project:  {PROJECT_ID}")
    print(f"  Region:   {REGION}")
    print(f"  Supabase: {os.getenv('SUPABASE_URL', '(not set)')[:50]}")
    print()

    authenticate()

    # Step 1: Fix billing
    billing_ok = repair_billing()
    if not billing_ok:
        print("\n[FATAL] Cannot proceed without active billing.")
        print("Fix billing at: https://console.cloud.google.com/billing")
        sys.exit(1)

    # Step 2: Enable APIs
    enable_apis()

    # Step 3: Build
    image = build_container()
    if not image:
        print("\n[FAIL] Build failed. Exiting.")
        sys.exit(1)
    print(f"\n  Image: {image}")

    # Step 4: Deploy
    url = deploy_to_cloud_run(image)
    if not url:
        print("\n[FAIL] Deploy failed.")
        sys.exit(1)

    # Step 5: Verify
    verify_health(url)

    print("\n" + "=" * 60)
    print("  DEPLOYMENT COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
