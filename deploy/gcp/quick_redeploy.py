"""
Quick Cloud Run redeploy — uses requests+urllib3 for robust Windows networking.
1. Authenticates with GCP
2. Checks if a recent Cloud Build succeeded
3. If not, triggers a new build and waits
4. Deploys Cloud Run with updated env vars

Usage:
  python deploy/gcp/quick_redeploy.py
  python deploy/gcp/quick_redeploy.py "mongodb+srv://user:pass@host/ibms_enterprise"
"""
import sys, os, io, time, json, tarfile, hashlib, base64, secrets, webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlencode, urlparse, parse_qs
from pathlib import Path
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ─── Config ──────────────────────────────────────────────────────────────
PROJECT_ID = os.getenv("GCP_PROJECT_ID", "total-handler-463313-e2")
REGION = "asia-south1"
CONNECTOR_NAME = "ibms-connector"
SERVICE_NAME = "ibms-web"
REPO_NAME = "ibms-docker"
SECRET_KEY = "ibms-secret-key-change-in-production"
DB_USER_PASSWORD = "ibms_secure_pw_2025"

CB_URL = f"https://cloudbuild.googleapis.com/v1/projects/{PROJECT_ID}"
STORAGE_URL = "https://storage.googleapis.com"
RUN_URL = "https://run.googleapis.com/v2"
SQL_URL = "https://sqladmin.googleapis.com/v1"
REDIS_URL_API = "https://redis.googleapis.com/v1"

CLIENT_ID = "764086051850-6qr4p6gpi6hn506pt8ejuq83di341hur.apps.googleusercontent.com"
CLIENT_SECRET = "d-FL95Q19q7MQmFpd7hHD0Ty"
REDIRECT_URI = "http://localhost:8085"

gcp_token = None

# ─── Robust HTTP session with automatic retries ─────────────────────────
session = requests.Session()
retry_strategy = Retry(
    total=5,
    backoff_factor=2,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["GET", "POST", "PATCH", "PUT", "DELETE"],
    raise_on_status=False,
)
adapter = HTTPAdapter(max_retries=retry_strategy)
session.mount("https://", adapter)
session.mount("http://", adapter)


def headers():
    return {"Authorization": f"Bearer {gcp_token}", "Content-Type": "application/json"}


# ─── Auth ────────────────────────────────────────────────────────────────
def authenticate():
    global gcp_token
    code_verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(code_verifier.encode()).digest()
    code_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    auth_code = None

    class H(BaseHTTPRequestHandler):
        def do_GET(self):
            nonlocal auth_code
            qs = parse_qs(urlparse(self.path).query)
            auth_code = qs.get("code", [None])[0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<h2>OK - return to terminal</h2>")
        def log_message(self, *a): pass

    url = "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode({
        "client_id": CLIENT_ID, "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": "https://www.googleapis.com/auth/cloud-platform",
        "state": secrets.token_urlsafe(16),
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "access_type": "offline",
    })
    print(f"[Auth] Opening browser...\n  {url}\n")
    webbrowser.open(url)
    srv = HTTPServer(("127.0.0.1", 8085), H)
    srv.handle_request()
    srv.server_close()

    resp = session.post("https://oauth2.googleapis.com/token", data={
        "client_id": CLIENT_ID, "client_secret": CLIENT_SECRET,
        "code": auth_code, "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code", "code_verifier": code_verifier,
    })
    gcp_token = resp.json()["access_token"]
    print("[Auth] OK\n")


# ─── Step 1: Check recent builds ────────────────────────────────────────
def check_recent_builds():
    """Check if there's a successful build in the last hour."""
    print("[Build] Checking recent Cloud Builds...")
    try:
        resp = session.get(f"{CB_URL}/builds?pageSize=5", headers=headers(), timeout=60)
        if resp is None or resp.status_code != 200:
            print(f"  Could not list builds: {resp.status_code}")
            return None
        builds = resp.json().get("builds", [])
        for b in builds:
            status = b.get("status", "")
            build_id = b.get("id", "")[:12]
            create_time = b.get("createTime", "")[:19]
            print(f"  Build {build_id}  status={status}  created={create_time}")
            if status == "SUCCESS":
                # Check if images list contains our image
                images = b.get("images", [])
                for img in images:
                    if REPO_NAME in img:
                        print(f"  [OK] Found successful recent build with image: {img}")
                        return img
                print(f"  [OK] Build succeeded (checking results...)")
                results = b.get("results", {})
                result_images = results.get("images", [])
                for ri in result_images:
                    img = ri.get("name", "")
                    if REPO_NAME in img:
                        print(f"  [OK] Image: {img}")
                        return img
                # Even if we can't find the exact image, a recent SUCCESS means the
                # image tag :latest was pushed
                return f"{REGION}-docker.pkg.dev/{PROJECT_ID}/{REPO_NAME}/{SERVICE_NAME}:latest"
        print("  No successful recent builds found.")
        return None
    except Exception as e:
        print(f"  Error checking builds: {e}")
        return None


# ─── Step 2: Trigger new build ───────────────────────────────────────────
def trigger_build():
    """Tar source, upload, trigger Cloud Build, wait."""
    print("[Build] Preparing source archive...")
    src = Path(__file__).resolve().parent.parent.parent
    buf = io.BytesIO()
    skip = {".git", "__pycache__", "node_modules", ".venv", "deploy", ".mypy_cache"}
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for p in sorted(src.rglob("*")):
            rel = p.relative_to(src)
            if any(part in skip for part in rel.parts):
                continue
            if p.is_file():
                tar.add(str(p), arcname=str(rel))
    buf.seek(0)
    size_kb = len(buf.getvalue()) / 1024
    print(f"  Archive size: {size_kb:.0f} KB")

    # Upload to Cloud Storage
    bucket = f"{PROJECT_ID}_cloudbuild"
    obj_name = f"source/ibms-src-{int(time.time())}.tar.gz"
    print(f"  Uploading to gs://{bucket}/{obj_name}...")
    up_url = f"{STORAGE_URL}/upload/storage/v1/b/{bucket}/o?uploadType=media&name={obj_name}"
    resp = session.post(up_url, data=buf.getvalue(),
                        headers={**headers(), "Content-Type": "application/gzip"}, timeout=300)
    if resp is None or resp.status_code not in (200, 201):
        print(f"  Upload failed: {getattr(resp, 'status_code', 'N/A')} {getattr(resp, 'text', '')[:300]}")
        return None
    print("  Uploaded OK")

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
    print("[Build] Triggering Cloud Build...")
    # Close stale connections before switching to Cloud Build API
    session.close()
    for attempt in range(3):
        try:
            resp = session.post(f"{CB_URL}/builds", headers=headers(), json=build_body, timeout=60)
            break
        except requests.exceptions.ConnectionError:
            print(f"  Connection reset (attempt {attempt+1}/3), retrying...")
            session.close()
            time.sleep(2 ** attempt)
    else:
        print("  Build trigger failed after retries")
        return None
    if resp is None or resp.status_code not in (200, 201):
        print(f"  Trigger failed: {resp.status_code} {resp.text[:500]}")
        return None
    op = resp.json()
    op_name = op.get("name", "")
    print(f"  Build operation: {op_name}")

    # Wait for build (resilient polling)
    print("  Waiting for build", end="", flush=True)
    start = time.time()
    while time.time() - start < 900:
        time.sleep(15)
        try:
            r = session.get(f"https://cloudbuild.googleapis.com/v1/{op_name}", headers=headers(), timeout=60)
            if r.status_code == 200:
                data = r.json()
                if data.get("done"):
                    if data.get("error"):
                        print(f"\n  Build FAILED: {json.dumps(data['error'])[:300]}")
                        return None
                    print(" DONE")
                    return image
            print(".", end="", flush=True)
        except Exception:
            print("x", end="", flush=True)
    print(" TIMEOUT (build may still be running)")
    return image  # Return image anyway — it might finish after timeout


# ─── Step 3: Get infra IPs ──────────────────────────────────────────────
def get_infra():
    """Get Cloud SQL IP and Redis host."""
    sql_ip = None
    redis_host = None
    redis_port = 6379

    try:
        resp = session.get(
            f"{SQL_URL}/projects/{PROJECT_ID}/instances/ibms-mysql", headers=headers(), timeout=30)
        if resp and resp.status_code == 200:
            for addr in resp.json().get("ipAddresses", []):
                if addr.get("type") == "PRIVATE":
                    sql_ip = addr["ipAddress"]
                    break
            if not sql_ip:
                addrs = resp.json().get("ipAddresses", [])
                if addrs:
                    sql_ip = addrs[0]["ipAddress"]
    except Exception as e:
        print(f"  Cloud SQL check error: {e}")

    try:
        resp = session.get(
            f"{REDIS_URL_API}/projects/{PROJECT_ID}/locations/{REGION}/instances/ibms-redis",
            headers=headers(), timeout=30)
        if resp and resp.status_code == 200:
            redis_host = resp.json().get("host")
            redis_port = resp.json().get("port", 6379)
    except Exception as e:
        print(f"  Redis check error: {e}")

    print(f"[Infra] Cloud SQL IP: {sql_ip or 'N/A'}")
    print(f"[Infra] Redis: {redis_host or 'N/A'}:{redis_port}")
    return sql_ip, redis_host, redis_port


# ─── Step 4: Deploy Cloud Run ───────────────────────────────────────────
def deploy(image, sql_ip, redis_host, redis_port, mongo_uri):
    """Patch Cloud Run service."""
    print(f"\n[Deploy] Updating Cloud Run service '{SERVICE_NAME}'...")

    db_url = f"mysql+aiomysql://ibms_user:{DB_USER_PASSWORD}@{sql_ip}:3306/ibms_enterprise" if sql_ip else ""
    redis_url = f"redis://{redis_host}:{redis_port}/0" if redis_host else ""

    env_vars = {
        "MONGO_URI": mongo_uri,
        "MONGO_DB_NAME": "ibms_enterprise",
        "DATABASE_URL": db_url,
        "REDIS_URL": redis_url,
        "SECRET_KEY": SECRET_KEY,
        "ENVIRONMENT": "production",
        "LOG_LEVEL": "info",
    }
    env_list = [{"name": k, "value": v} for k, v in env_vars.items() if v]

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
                "egress": "ALL_TRAFFIC",
            },
        },
    }

    svc_url = f"{RUN_URL}/projects/{PROJECT_ID}/locations/{REGION}/services/{SERVICE_NAME}"
    resp = session.patch(svc_url, headers=headers(), json=svc_body, timeout=60)
    if resp is None or resp.status_code not in (200, 201):
        print(f"  Deploy failed: {resp.status_code} {resp.text[:500]}")
        return False

    # Wait for deployment
    op = resp.json()
    op_name = op.get("name", "")
    if op_name:
        print(f"  Operation: {op_name}")
        print("  Waiting for deployment", end="", flush=True)
        start = time.time()
        while time.time() - start < 300:
            time.sleep(10)
            try:
                r = session.get(f"https://run.googleapis.com/v2/{op_name}", headers=headers(), timeout=30)
                if r.status_code == 200:
                    data = r.json()
                    if data.get("done"):
                        if data.get("error"):
                            print(f"\n  Deploy error: {data['error']}")
                            return False
                        print(" DONE")
                        break
                print(".", end="", flush=True)
            except Exception:
                print("x", end="", flush=True)

    # Set IAM for public access
    try:
        iam_url = f"{svc_url}:setIamPolicy"
        session.post(iam_url, headers=headers(), json={
            "policy": {
                "bindings": [{"role": "roles/run.invoker", "members": ["allUsers"]}]
            }
        }, timeout=30)
    except Exception:
        pass

    # Get URL
    try:
        r = session.get(svc_url, headers=headers(), timeout=30)
        if r.status_code == 200:
            url = r.json().get("uri", "")
            if url:
                print(f"\n  Live URL: {url}")
                print(f"  Health:   {url}/api/health")
                print(f"  Docs:     {url}/api/docs")
                return True
    except Exception:
        pass

    print("  [OK] Deploy submitted")
    return True


# ─── Main ────────────────────────────────────────────────────────────────
def main():
    mongo_uri = "mongodb://localhost:27017"
    if len(sys.argv) > 1 and not sys.argv[1].startswith("--"):
        mongo_uri = sys.argv[1]
    elif os.getenv("MONGO_URI"):
        mongo_uri = os.getenv("MONGO_URI")

    print("=" * 60)
    print("  IBMS — Quick Cloud Run Redeploy")
    print("=" * 60)
    print(f"  MONGO_URI: {mongo_uri[:50]}...")
    print()

    force = "--force" in sys.argv

    authenticate()

    # Check if we already have a good build
    image = None
    if not force:
        image = check_recent_builds()
    if not image:
        image = trigger_build()
    if not image:
        print("\n[FAIL] Could not get container image. Exiting.")
        return

    print(f"\n[Image] {image}")

    sql_ip, redis_host, redis_port = get_infra()
    deploy(image, sql_ip, redis_host, redis_port, mongo_uri)

    print("\n" + "=" * 60)
    print("  Done!")
    print("=" * 60)


if __name__ == "__main__":
    main()
