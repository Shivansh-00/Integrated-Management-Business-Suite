"""
MongoDB Atlas Setup + Container Rebuild + Cloud Run Redeploy
=============================================================
1. Creates MongoDB Atlas M0 free cluster (via API or guided manual)
2. Rebuilds container image via Cloud Build (with updated code)
3. Redeploys Cloud Run with MONGO_URI pointing to Atlas

Usage:
  # With Atlas connection string already obtained:
  set MONGO_URI=mongodb+srv://user:pass@cluster.mongodb.net/ibms_enterprise
  python deploy/gcp/setup_atlas_and_redeploy.py

  # With Atlas API keys (automates cluster creation):
  set ATLAS_PUBLIC_KEY=xxxxx
  set ATLAS_PRIVATE_KEY=xxxxx
  python deploy/gcp/setup_atlas_and_redeploy.py

  # Interactive (prints instructions for manual Atlas setup):
  python deploy/gcp/setup_atlas_and_redeploy.py
"""
import sys, os, io, time, json, tarfile, hashlib, base64, secrets, webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlencode, urlparse, parse_qs
from pathlib import Path
import httpx

# ─── GCP config ──────────────────────────────────────────────────────────
PROJECT_ID = os.getenv("GCP_PROJECT_ID", "total-handler-463313-e2")
REGION = "asia-south1"
CONNECTOR_NAME = "ibms-connector"
SQL_INSTANCE = "ibms-mysql"
REDIS_INSTANCE = "ibms-redis"
SERVICE_NAME = "ibms-web"
REPO_NAME = "ibms-docker"
SECRET_KEY = "ibms-secret-key-change-in-production"
DB_USER_PASSWORD = "ibms_secure_pw_2025"

# ─── URLs ────────────────────────────────────────────────────────────────
SQL_URL = "https://sqladmin.googleapis.com/v1"
REDIS_URL_API = "https://redis.googleapis.com/v1"
RUN_URL = "https://run.googleapis.com/v2"
CB_URL = "https://cloudbuild.googleapis.com/v1"
STORAGE_URL = "https://storage.googleapis.com"

# ─── GCP OAuth ───────────────────────────────────────────────────────────
CLIENT_ID = "764086051850-6qr4p6gpi6hn506pt8ejuq83di341hur.apps.googleusercontent.com"
CLIENT_SECRET = "d-FL95Q19q7MQmFpd7hHD0Ty"
REDIRECT_URI = "http://localhost:8085"

# ─── Atlas config ────────────────────────────────────────────────────────
ATLAS_BASE = "https://cloud.mongodb.com/api/atlas/v1.0"
ATLAS_CLUSTER_NAME = "ibms-cluster"
ATLAS_DB_USER = "ibms_app"
ATLAS_DB_PASSWORD = os.getenv("ATLAS_DB_PASSWORD", "IbmsAtlas2025Secure")

gcp_token = None
gcp_client = httpx.Client(timeout=120)


# =====================================================================
# GCP OAuth2 (same flow as redeploy_cloudrun.py)
# =====================================================================
def gcp_authenticate():
    global gcp_token
    code_verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(code_verifier.encode()).digest()
    code_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    auth_code = None

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            nonlocal auth_code
            qs = parse_qs(urlparse(self.path).query)
            auth_code = qs.get("code", [None])[0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<h2>OK - return to terminal</h2>")
        def log_message(self, *a): pass

    print("  Authenticating with GCP...")
    url = "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode({
        "client_id": CLIENT_ID, "redirect_uri": REDIRECT_URI,
        "response_type": "code", "scope": "https://www.googleapis.com/auth/cloud-platform",
        "state": secrets.token_urlsafe(16), "code_challenge": code_challenge,
        "code_challenge_method": "S256", "access_type": "offline",
    })
    print(f"  {url}\n")
    webbrowser.open(url)
    srv = HTTPServer(("127.0.0.1", 8085), Handler)
    srv.handle_request()
    srv.server_close()
    resp = gcp_client.post("https://oauth2.googleapis.com/token", data={
        "client_id": CLIENT_ID, "client_secret": CLIENT_SECRET,
        "code": auth_code, "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code", "code_verifier": code_verifier,
    })
    gcp_token = resp.json()["access_token"]
    print("  [OK] GCP Authenticated\n")


def gcp_headers():
    return {"Authorization": f"Bearer {gcp_token}", "Content-Type": "application/json"}


def wait_op(url, label, timeout=600):
    print(f"    Waiting for {label}...", end="", flush=True)
    start = time.time()
    while time.time() - start < timeout:
        try:
            resp = gcp_client.get(url, headers=gcp_headers())
        except Exception:
            print("x", end="", flush=True)
            time.sleep(15)
            continue
        if resp.status_code != 200:
            time.sleep(10)
            print(".", end="", flush=True)
            continue
        data = resp.json()
        if data.get("done") or data.get("status") == "DONE":
            if data.get("error"):
                print(f" FAILED: {data['error']}")
                return False
            print(" done")
            return True
        time.sleep(10)
        print(".", end="", flush=True)
    print(" TIMEOUT")
    return False


# =====================================================================
# MongoDB Atlas — automated setup via API
# =====================================================================
def atlas_setup_via_api(public_key, private_key):
    """Create M0 free cluster, database user, and IP whitelist via Atlas API."""
    auth = httpx.DigestAuth(public_key, private_key)
    ac = httpx.Client(timeout=60)
    hdr = {"Content-Type": "application/json", "Accept": "application/json"}

    # 1. Get or create a project
    print("  [Atlas] Listing projects...")
    resp = ac.get(f"{ATLAS_BASE}/groups", headers=hdr, auth=auth)
    if resp.status_code != 200:
        print(f"    Failed to list projects: {resp.status_code} {resp.text[:300]}")
        return None
    groups = resp.json().get("results", [])
    group_id = None
    for g in groups:
        if g.get("name") == "IBMS":
            group_id = g["id"]
            print(f"    Found existing project 'IBMS' ({group_id})")
            break
    if not group_id:
        # Need org ID to create a project
        resp2 = ac.get(f"{ATLAS_BASE}/orgs", headers=hdr, auth=auth)
        if resp2.status_code != 200:
            print(f"    Failed to list orgs: {resp2.status_code}")
            return None
        orgs = resp2.json().get("results", [])
        if not orgs:
            print("    No Atlas organizations found. Create one at cloud.mongodb.com first.")
            return None
        org_id = orgs[0]["id"]
        print(f"    Creating project 'IBMS' in org {org_id}...")
        resp3 = ac.post(
            f"{ATLAS_BASE}/groups",
            headers=hdr, auth=auth,
            json={"name": "IBMS", "orgId": org_id},
        )
        if resp3.status_code in (200, 201):
            group_id = resp3.json()["id"]
            print(f"    [OK] Project created: {group_id}")
        else:
            print(f"    Failed to create project: {resp3.status_code} {resp3.text[:300]}")
            return None

    # 2. Check if cluster already exists
    print(f"  [Atlas] Checking cluster '{ATLAS_CLUSTER_NAME}'...")
    resp = ac.get(f"{ATLAS_BASE}/groups/{group_id}/clusters/{ATLAS_CLUSTER_NAME}", headers=hdr, auth=auth)
    if resp.status_code == 200:
        state = resp.json().get("stateName", "")
        print(f"    Cluster exists (state: {state})")
        if state != "IDLE":
            print("    Waiting for cluster to be IDLE...")
            for _ in range(60):
                time.sleep(15)
                r2 = ac.get(f"{ATLAS_BASE}/groups/{group_id}/clusters/{ATLAS_CLUSTER_NAME}", headers=hdr, auth=auth)
                if r2.status_code == 200 and r2.json().get("stateName") == "IDLE":
                    break
                print(".", end="", flush=True)
            print()
    else:
        # 3. Create M0 free cluster
        print(f"  [Atlas] Creating free M0 cluster '{ATLAS_CLUSTER_NAME}'...")
        cluster_body = {
            "name": ATLAS_CLUSTER_NAME,
            "providerSettings": {
                "providerName": "TENANT",
                "backingProviderName": "GCP",
                "instanceSizeName": "M0",
                "regionName": "ASIA_SOUTH_1",
            },
        }
        resp = ac.post(
            f"{ATLAS_BASE}/groups/{group_id}/clusters",
            headers=hdr, auth=auth, json=cluster_body,
        )
        if resp.status_code in (200, 201):
            print("    [OK] Cluster creation started")
        else:
            print(f"    Failed: {resp.status_code} {resp.text[:400]}")
            return None

        # Wait for cluster to be ready
        print("    Waiting for cluster to become IDLE...", end="", flush=True)
        for _ in range(80):  # up to ~20 minutes
            time.sleep(15)
            r2 = ac.get(f"{ATLAS_BASE}/groups/{group_id}/clusters/{ATLAS_CLUSTER_NAME}", headers=hdr, auth=auth)
            if r2.status_code == 200:
                st = r2.json().get("stateName", "")
                if st == "IDLE":
                    print(f" done ({st})")
                    break
                print(".", end="", flush=True)
            else:
                print("x", end="", flush=True)
        else:
            print(" TIMEOUT — cluster may still be provisioning.")
            print("    Run this script again after the cluster is ready.")
            return None

    # 4. Create database user
    print(f"  [Atlas] Creating database user '{ATLAS_DB_USER}'...")
    user_body = {
        "databaseName": "admin",
        "roles": [{"roleName": "readWriteAnyDatabase", "databaseName": "admin"}],
        "username": ATLAS_DB_USER,
        "password": ATLAS_DB_PASSWORD,
    }
    resp = ac.post(
        f"{ATLAS_BASE}/groups/{group_id}/databaseUsers",
        headers=hdr, auth=auth, json=user_body,
    )
    if resp.status_code in (200, 201):
        print(f"    [OK] User '{ATLAS_DB_USER}' created")
    elif resp.status_code == 409:
        print(f"    User '{ATLAS_DB_USER}' already exists")
        # Update password
        ac.patch(
            f"{ATLAS_BASE}/groups/{group_id}/databaseUsers/admin/{ATLAS_DB_USER}",
            headers=hdr, auth=auth,
            json={"password": ATLAS_DB_PASSWORD},
        )
    else:
        print(f"    Warning: user creation returned {resp.status_code}: {resp.text[:200]}")

    # 5. Whitelist 0.0.0.0/0 (required for Cloud Run — no static IP)
    print("  [Atlas] Setting network access (0.0.0.0/0)...")
    resp = ac.post(
        f"{ATLAS_BASE}/groups/{group_id}/accessList",
        headers=hdr, auth=auth,
        json=[{"cidrBlock": "0.0.0.0/0", "comment": "Cloud Run (no static egress IP)"}],
    )
    if resp.status_code in (200, 201):
        print("    [OK] Network access set")
    elif resp.status_code == 409:
        print("    Already whitelisted")
    else:
        print(f"    Warning: {resp.status_code}: {resp.text[:200]}")

    # 6. Get connection string
    resp = ac.get(f"{ATLAS_BASE}/groups/{group_id}/clusters/{ATLAS_CLUSTER_NAME}", headers=hdr, auth=auth)
    if resp.status_code == 200:
        srv = resp.json().get("connectionStrings", {}).get("standardSrv", "")
        if srv:
            # Build full URI: mongodb+srv://user:pass@host/dbname
            from urllib.parse import quote_plus
            user_enc = quote_plus(ATLAS_DB_USER)
            pass_enc = quote_plus(ATLAS_DB_PASSWORD)
            # srv looks like: mongodb+srv://cluster.xxxxx.mongodb.net
            host_part = srv.replace("mongodb+srv://", "")
            uri = f"mongodb+srv://{user_enc}:{pass_enc}@{host_part}/ibms_enterprise?retryWrites=true&w=majority"
            print(f"    Connection string: mongodb+srv://{user_enc}:****@{host_part}/ibms_enterprise")
            return uri
    print("    Could not retrieve connection string")
    return None


def print_manual_atlas_instructions():
    """Print step-by-step instructions for manual Atlas setup."""
    print("""
╔══════════════════════════════════════════════════════════════╗
║        MongoDB Atlas Free Tier — Manual Setup Guide         ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  1. Go to: https://cloud.mongodb.com/                        ║
║     - Sign up or sign in                                     ║
║                                                              ║
║  2. Click "Build a Database"                                 ║
║     - Select M0 FREE (Shared)                                ║
║     - Provider: Google Cloud                                 ║
║     - Region: Mumbai (asia-south1)                           ║
║     - Cluster name: ibms-cluster                             ║
║     - Click "Create Deployment"                              ║
║                                                              ║
║  3. Create Database User (on the popup):                     ║
║     - Username: ibms_app                                     ║
║     - Password: IbmsAtlas2025Secure                          ║
║     - Click "Create Database User"                           ║
║                                                              ║
║  4. Network Access (on the popup or Security > Network):     ║
║     - Click "Add My Current IP Address"                      ║
║     - ALSO add: 0.0.0.0/0 (allows access from anywhere)     ║
║       This is needed for Cloud Run (no static egress IP)     ║
║                                                              ║
║  5. Get Connection String:                                   ║
║     - Click "Connect" on your cluster                        ║
║     - Choose "Drivers"                                       ║
║     - Copy the connection string                             ║
║     - Replace <password> with: IbmsAtlas2025Secure           ║
║     - Add database name: /ibms_enterprise                    ║
║                                                              ║
║  Example:                                                    ║
║  mongodb+srv://ibms_app:IbmsAtlas2025Secure@ibms-cluster     ║
║  .xxxxx.mongodb.net/ibms_enterprise?retryWrites=true         ║
║  &w=majority                                                 ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
""")


# =====================================================================
# Step 1: Obtain MongoDB Atlas connection string
# =====================================================================
def obtain_mongo_uri():
    """Get Atlas URI from env, CLI arg, or API."""
    # Check CLI argument: python script.py "mongodb+srv://..."
    if len(sys.argv) > 1:
        arg = sys.argv[1].strip()
        if "mongodb+srv" in arg or "mongodb://" in arg:
            print(f"  [OK] Using MONGO_URI from CLI argument")
            return arg

    # Check env var
    uri = os.getenv("MONGO_URI", "").strip()
    if uri and "mongodb+srv" in uri:
        print(f"  [OK] Using MONGO_URI from environment")
        return uri

    # Check Atlas API keys
    atlas_pub = os.getenv("ATLAS_PUBLIC_KEY", "").strip()
    atlas_prv = os.getenv("ATLAS_PRIVATE_KEY", "").strip()
    if atlas_pub and atlas_prv:
        print("  [Atlas] API keys found — automating cluster setup...")
        uri = atlas_setup_via_api(atlas_pub, atlas_prv)
        if uri:
            return uri
        print("  Atlas API setup failed.\n")

    # No URI available — print instructions
    print_manual_atlas_instructions()
    print("  Re-run with:")
    print('    python deploy/gcp/setup_atlas_and_redeploy.py "mongodb+srv://user:pass@host/ibms_enterprise"')
    print("\n  Or set: MONGO_URI=mongodb+srv://... before running.\n")
    return None


# =====================================================================
# Step 2: Rebuild container via Cloud Build
# =====================================================================
def rebuild_container():
    """Upload source and trigger Cloud Build."""
    print("\n[2] Rebuilding container via Cloud Build...")

    project_root = Path(__file__).resolve().parent.parent.parent
    print(f"    Source: {project_root}")

    buf = io.BytesIO()
    exclude_dirs = {".git", "__pycache__", "node_modules", ".env", "deploy", "docs", ".github"}
    exclude_exts = {".pyc", ".pyo"}

    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for item in project_root.rglob("*"):
            rel = item.relative_to(project_root)
            parts = rel.parts
            if any(p in exclude_dirs for p in parts):
                continue
            if item.suffix in exclude_exts:
                continue
            if item.is_file():
                tar.add(str(item), arcname=str(rel))

    source_bytes = buf.getvalue()
    print(f"    Source archive: {len(source_bytes) / 1024:.1f} KB")

    image_tag = f"{REGION}-docker.pkg.dev/{PROJECT_ID}/{REPO_NAME}/ibms-web:latest"

    build_config = {
        "source": {
            "storageSource": {
                "bucket": f"{PROJECT_ID}_cloudbuild",
                "object": "source.tar.gz",
            }
        },
        "steps": [
            {
                "name": "gcr.io/cloud-builders/docker",
                "args": ["build", "-t", image_tag, "."],
            }
        ],
        "images": [image_tag],
        "timeout": "1200s",
    }

    bucket_name = f"{PROJECT_ID}_cloudbuild"

    # Create bucket (may already exist)
    gcp_client.post(
        f"{STORAGE_URL}/storage/v1/b",
        headers=gcp_headers(),
        params={"project": PROJECT_ID},
        json={"name": bucket_name, "location": REGION},
    )

    # Upload source tarball
    print("    Uploading source to Cloud Storage...")
    upload_resp = gcp_client.post(
        f"{STORAGE_URL}/upload/storage/v1/b/{bucket_name}/o",
        headers={"Authorization": f"Bearer {gcp_token}"},
        params={"uploadType": "media", "name": "source.tar.gz"},
        content=source_bytes,
    )
    if upload_resp.status_code in (200, 201):
        print("    [OK] Source uploaded")
    else:
        print(f"    [FAIL] Upload: {upload_resp.status_code} — {upload_resp.text[:300]}")
        return False

    # Trigger build
    print("    Triggering Cloud Build...")
    build_resp = gcp_client.post(
        f"{CB_URL}/projects/{PROJECT_ID}/builds",
        headers=gcp_headers(),
        json=build_config,
    )
    if build_resp.status_code == 200:
        op = build_resp.json()
        op_name = op.get("name", "")
        print(f"    Build started: {op_name}")
        return wait_op(f"{CB_URL}/{op_name}", "container build", timeout=900)
    else:
        print(f"    [FAIL] Build trigger: {build_resp.status_code} — {build_resp.text[:400]}")
        return False


# =====================================================================
# Step 3: Check infra (Cloud SQL + Redis)
# =====================================================================
def check_infra():
    """Check Cloud SQL and Redis, return (sql_ip, redis_host, redis_port)."""
    print("\n[3] Checking infrastructure...")

    # Cloud SQL
    resp = gcp_client.get(f"{SQL_URL}/projects/{PROJECT_ID}/instances/{SQL_INSTANCE}", headers=gcp_headers())
    sql_ip = None
    if resp.status_code == 200:
        data = resp.json()
        state = data.get("state", "UNKNOWN")
        for addr in data.get("ipAddresses", []):
            if addr.get("type") == "PRIVATE":
                sql_ip = addr["ipAddress"]
        print(f"    Cloud SQL: {state}, IP: {sql_ip}")
        if state != "RUNNABLE":
            print("    Waiting for RUNNABLE...", end="", flush=True)
            for _ in range(60):
                time.sleep(15)
                r2 = gcp_client.get(f"{SQL_URL}/projects/{PROJECT_ID}/instances/{SQL_INSTANCE}", headers=gcp_headers())
                if r2.status_code == 200:
                    s = r2.json().get("state", "")
                    if s == "RUNNABLE":
                        for a in r2.json().get("ipAddresses", []):
                            if a.get("type") == "PRIVATE":
                                sql_ip = a["ipAddress"]
                        print(f" done ({s})")
                        break
                    print(".", end="", flush=True)
            else:
                print(" TIMEOUT")
    else:
        print(f"    Cloud SQL not found: {resp.status_code}")

    # Redis
    resp = gcp_client.get(
        f"{REDIS_URL_API}/projects/{PROJECT_ID}/locations/{REGION}/instances/{REDIS_INSTANCE}",
        headers=gcp_headers(),
    )
    redis_host, redis_port = "10.0.0.4", 6379
    if resp.status_code == 200:
        data = resp.json()
        redis_host = data.get("host", redis_host)
        redis_port = data.get("port", redis_port)
        print(f"    Redis: {data.get('state')}, {redis_host}:{redis_port}")
    else:
        print(f"    Redis not found: {resp.status_code} — using defaults")

    # Ensure DB/user
    gcp_client.post(
        f"{SQL_URL}/projects/{PROJECT_ID}/instances/{SQL_INSTANCE}/databases",
        headers=gcp_headers(), json={"name": "ibms_enterprise"},
    )
    gcp_client.post(
        f"{SQL_URL}/projects/{PROJECT_ID}/instances/{SQL_INSTANCE}/users",
        headers=gcp_headers(), json={"name": "ibms_user", "password": DB_USER_PASSWORD},
    )
    print("    [OK] Database and user ensured")

    return sql_ip, redis_host, redis_port


# =====================================================================
# Step 4: Deploy Cloud Run with new MONGO_URI
# =====================================================================
def deploy_cloud_run(sql_ip, redis_host, redis_port, mongo_uri):
    """Deploy Cloud Run with updated environment."""
    print("\n[4] Deploying Cloud Run...")
    image = f"{REGION}-docker.pkg.dev/{PROJECT_ID}/{REPO_NAME}/ibms-web:latest"
    connector = f"projects/{PROJECT_ID}/locations/{REGION}/connectors/{CONNECTOR_NAME}"

    # If we have Atlas URI, MongoDB should work → Cloud Run can use it directly
    # VPC egress: PRIVATE_RANGES_ONLY for Cloud SQL/Redis, Atlas goes over public internet
    egress = "PRIVATE_RANGES_ONLY"
    if mongo_uri and "mongodb+srv" in mongo_uri:
        # Atlas needs public internet access → ALL_TRAFFIC through VPC connector
        # Actually PRIVATE_RANGES_ONLY is fine — Atlas goes direct, not through VPC
        egress = "PRIVATE_RANGES_ONLY"

    service_body = {
        "template": {
            "scaling": {"minInstanceCount": 0, "maxInstanceCount": 4},
            "vpcAccess": {
                "connector": connector,
                "egress": egress,
            },
            "containers": [{
                "image": image,
                "ports": [{"containerPort": 8080}],
                "resources": {"limits": {"cpu": "2", "memory": "2Gi"}},
                "env": [
                    {"name": "HOST", "value": "0.0.0.0"},
                    {"name": "RELOAD", "value": "false"},
                    {"name": "LOG_LEVEL", "value": "warning"},
                    {"name": "SECRET_KEY", "value": SECRET_KEY},
                    {"name": "REDIS_URL", "value": f"redis://{redis_host}:{redis_port}/0"},
                    {"name": "MARIADB_URI", "value": f"mysql+aiomysql://ibms_user:{DB_USER_PASSWORD}@{sql_ip}:3306/ibms_enterprise?connect_timeout=10"},
                    {"name": "MONGO_URI", "value": mongo_uri or "mongodb://localhost:27017"},
                    {"name": "MONGO_DB_NAME", "value": "ibms_enterprise"},
                ],
                "startupProbe": {
                    "httpGet": {"path": "/api/health"},
                    "initialDelaySeconds": 10,
                    "periodSeconds": 10,
                    "failureThreshold": 15,
                    "timeoutSeconds": 15,
                },
                "livenessProbe": {
                    "httpGet": {"path": "/api/health"},
                    "periodSeconds": 60,
                    "timeoutSeconds": 15,
                },
            }],
        },
    }

    resp = gcp_client.patch(
        f"{RUN_URL}/projects/{PROJECT_ID}/locations/{REGION}/services/{SERVICE_NAME}",
        headers=gcp_headers(),
        params={"allowMissing": "true"},
        json=service_body,
    )
    if resp.status_code == 200:
        op = resp.json()
        op_name = op.get("name", "")
        if op_name:
            ok = wait_op(f"{RUN_URL}/{op_name}", "Cloud Run deploy", timeout=600)
            if not ok:
                print("    Deploy failed")
                return False
    else:
        print(f"    [FAIL] Deploy: {resp.status_code} — {resp.text[:400]}")
        return False

    # Public access IAM
    gcp_client.post(
        f"{RUN_URL}/projects/{PROJECT_ID}/locations/{REGION}/services/{SERVICE_NAME}:setIamPolicy",
        headers=gcp_headers(),
        json={"policy": {"bindings": [{"role": "roles/run.invoker", "members": ["allUsers"]}]}},
    )

    # Get URL
    svc = gcp_client.get(
        f"{RUN_URL}/projects/{PROJECT_ID}/locations/{REGION}/services/{SERVICE_NAME}",
        headers=gcp_headers(),
    )
    if svc.status_code == 200:
        uri = svc.json().get("uri", "")
        mongo_status = "CONNECTED (Atlas)" if mongo_uri and "mongodb" in mongo_uri else "FALLBACK (in-memory)"
        print(f"\n{'=' * 60}")
        print(f"  IBMS LIVE — Redeployed!")
        print(f"{'=' * 60}")
        print(f"  URL:       {uri}")
        print(f"  Health:    {uri}/api/health")
        print(f"  Dashboard: {uri}/")
        print(f"  API Docs:  {uri}/api/docs")
        print(f"  MongoDB:   {mongo_status}")
        print(f"{'=' * 60}\n")
    return True


# =====================================================================
# Main
# =====================================================================
def main():
    print("=" * 60)
    print("  IBMS — Atlas Setup + Rebuild + Redeploy")
    print("=" * 60 + "\n")

    # Step 0: Authenticate with GCP
    gcp_authenticate()

    # Step 1: Obtain MongoDB Atlas URI
    print("[1] MongoDB Atlas Setup")
    print("-" * 40)
    mongo_uri = obtain_mongo_uri()
    if mongo_uri:
        print(f"\n  [OK] MONGO_URI obtained")
    elif "--skip-atlas" in sys.argv:
        print("\n  [SKIP] --skip-atlas: deploying with fast-fail (500ms) timeouts only")
        mongo_uri = "mongodb://localhost:27017"
    else:
        print("\n  No Atlas URI provided. Use --skip-atlas to deploy without Atlas,")
        print("  or pass the URI: python setup_atlas_and_redeploy.py 'mongodb+srv://...'")
        return

    # Step 2: Rebuild container (includes the timeout fix in connection.py)
    ok = rebuild_container()
    if not ok:
        print("\n  [FAIL] Container build failed — aborting")
        return

    # Step 3: Check Cloud SQL + Redis
    sql_ip, redis_host, redis_port = check_infra()
    if not sql_ip:
        print("\n  [FAIL] Cloud SQL IP not found — aborting")
        return

    # Step 4: Deploy Cloud Run
    deploy_cloud_run(sql_ip, redis_host, redis_port, mongo_uri)


if __name__ == "__main__":
    class Tee:
        def __init__(self, *streams): self.streams = streams
        def write(self, data):
            for s in self.streams:
                s.write(data)
                s.flush()
        def flush(self):
            for s in self.streams:
                s.flush()

    log_path = Path(__file__).parent / "_atlas_redeploy_log.txt"
    log = open(log_path, "w", encoding="utf-8")
    sys.stdout = Tee(sys.__stdout__, log)
    sys.stderr = Tee(sys.__stderr__, log)
    main()
