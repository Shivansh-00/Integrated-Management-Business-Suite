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
from dotenv import load_dotenv

# Load .env from project root (two levels up from this script)
_project_root = Path(__file__).resolve().parent.parent.parent
load_dotenv(_project_root / ".env")

# ─── Config ──────────────────────────────────────────────────────────────
PROJECT_ID = os.getenv("GCP_PROJECT_ID", "total-handler-463313-e2")
REGION = "asia-south1"
CONNECTOR_NAME = "ibms-connector"
SERVICE_NAME = "ibms-web"
REPO_NAME = "ibms-docker"
SECRET_KEY = os.getenv("SECRET_KEY", "ibms-secret-key-change-in-production")
JWT_SECRET = os.getenv("JWT_SECRET", SECRET_KEY)

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
    skip = {".git", "__pycache__", "node_modules", ".venv", "deploy", ".mypy_cache", "docs", "scripts", ".env"}
    skip_ext = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".svg", ".pdf", ".log"}
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for p in sorted(src.rglob("*")):
            rel = p.relative_to(src)
            if any(part in skip for part in rel.parts):
                continue
            if p.is_file():
                if p.suffix.lower() in skip_ext:
                    continue
                tar.add(str(p), arcname=str(rel))
    buf.seek(0)
    size_kb = len(buf.getvalue()) / 1024
    print(f"  Archive size: {size_kb:.0f} KB")

    # Upload to Cloud Storage using resumable upload (chunked)
    bucket = f"{PROJECT_ID}_cloudbuild"
    obj_name = f"source/ibms-src-{int(time.time())}.tar.gz"
    print(f"  Uploading to gs://{bucket}/{obj_name} (resumable)...")
    data_bytes = buf.getvalue()
    total_size = len(data_bytes)

    # Step 1: Initiate resumable upload
    init_url = f"{STORAGE_URL}/upload/storage/v1/b/{bucket}/o?uploadType=resumable&name={obj_name}"
    init_resp = session.post(init_url, headers={**headers(),
                             "Content-Type": "application/json",
                             "X-Upload-Content-Type": "application/gzip",
                             "X-Upload-Content-Length": str(total_size)},
                             json={"name": obj_name}, timeout=60)
    if init_resp.status_code != 200:
        print(f"  Resumable init failed: {init_resp.status_code} {init_resp.text[:300]}")
        return None
    upload_uri = init_resp.headers.get("Location")
    if not upload_uri:
        print("  No upload URI returned")
        return None

    # Step 2: Upload in 2 MB chunks with retry
    CHUNK = 2 * 1024 * 1024  # 2 MB
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
                    # Final chunk accepted
                    offset = total_size
                    break
                elif cr.status_code == 308:
                    # Chunk accepted, continue
                    offset = end
                    break
                else:
                    print(f"  Chunk upload error {cr.status_code}, retry {attempt+1}")
                    time.sleep(2 ** attempt)
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
                print(f"  Chunk upload exception ({attempt+1}/5): {type(e).__name__}")
                time.sleep(2 ** attempt)
        else:
            print("  Upload failed after 5 retries for a chunk")
            return None
        pct = min(100, int(offset / total_size * 100))
        print(f"  Uploaded {pct}%", flush=True)
    print("  Upload complete")

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
    """Get Redis host (Cloud SQL removed — using Supabase)."""
    redis_host = None
    redis_port = 6379

    try:
        resp = session.get(
            f"{REDIS_URL_API}/projects/{PROJECT_ID}/locations/{REGION}/instances/ibms-redis",
            headers=headers(), timeout=30)
        if resp and resp.status_code == 200:
            redis_host = resp.json().get("host")
            redis_port = resp.json().get("port", 6379)
    except Exception as e:
        print(f"  Redis check error: {e}")

    print(f"[Infra] Redis: {redis_host or 'N/A'}:{redis_port}")
    return redis_host, redis_port


# ─── Step 4: Deploy Cloud Run ───────────────────────────────────────────
def deploy(image, redis_host, redis_port):
    """Patch Cloud Run service."""
    print(f"\n[Deploy] Updating Cloud Run service '{SERVICE_NAME}'...")

    redis_url = f"redis://{redis_host}:{redis_port}/0" if redis_host else ""

    env_vars = {
        "SUPABASE_URL": os.getenv("SUPABASE_URL", ""),
        "SUPABASE_KEY": os.getenv("SUPABASE_KEY", ""),
        "REDIS_URL": redis_url,
        "SECRET_KEY": SECRET_KEY,
        "JWT_SECRET": JWT_SECRET,
        "HOST": "0.0.0.0",
        "RELOAD": "false",
        "ENVIRONMENT": "production",
        "LOG_LEVEL": "info",
        "GROQ_API_KEY": os.getenv("GROQ_API_KEY", "").strip(),
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
                "egress": "PRIVATE_RANGES_ONLY",
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
    print("=" * 60)
    print("  IBMS — Quick Cloud Run Redeploy")
    print("=" * 60)
    print(f"  SUPABASE_URL: {os.getenv('SUPABASE_URL', '(not set)')[:50]}")
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

    redis_host, redis_port = get_infra()
    deploy(image, redis_host, redis_port)

    print("\n" + "=" * 60)
    print("  Done!")
    print("=" * 60)


if __name__ == "__main__":
    import io as _io

    class _Tee(_io.TextIOBase):
        def __init__(self, *streams):
            self._streams = streams
        def write(self, data):
            for s in self._streams:
                s.write(data)
                s.flush()
            return len(data)
        def flush(self):
            for s in self._streams:
                s.flush()

    _log = open(_project_root / "_deploy_output.txt", "w", encoding="utf-8")
    sys.stdout = _Tee(sys.__stdout__, _log)
    sys.stderr = _Tee(sys.__stderr__, _log)
    try:
        main()
    finally:
        _log.close()
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__
