"""
Quick check: Cloud SQL status + redeploy Cloud Run.
"""
import sys, os, time, json, hashlib, base64, secrets, webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlencode, urlparse, parse_qs
import httpx

PROJECT_ID = os.getenv("GCP_PROJECT_ID", "total-handler-463313-e2")
REGION = "asia-south1"
VPC_NAME = "ibms-vpc"
CONNECTOR_NAME = "ibms-connector"
SQL_INSTANCE = "ibms-mysql"
REDIS_INSTANCE = "ibms-redis"
SERVICE_NAME = "ibms-web"
REPO_NAME = "ibms-docker"
SECRET_KEY = os.getenv("SECRET_KEY", "ibms-secret-key-change-in-production")
JWT_SECRET = os.getenv("JWT_SECRET", SECRET_KEY)
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

SQL_URL = "https://sqladmin.googleapis.com/v1"
REDIS_URL_API = "https://redis.googleapis.com/v1"
RUN_URL = "https://run.googleapis.com/v2"
LOGS_URL = "https://logging.googleapis.com/v2"

CLIENT_ID = "764086051850-6qr4p6gpi6hn506pt8ejuq83di341hur.apps.googleusercontent.com"
CLIENT_SECRET = "d-FL95Q19q7MQmFpd7hHD0Ty"
REDIRECT_URI = "http://localhost:8085"

access_token = None

def authenticate():
    global access_token
    code_verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(code_verifier.encode()).digest()
    code_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    state = secrets.token_urlsafe(16)
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

    print("  Authenticating...")
    url = "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode({
        "client_id": CLIENT_ID, "redirect_uri": REDIRECT_URI,
        "response_type": "code", "scope": "https://www.googleapis.com/auth/cloud-platform",
        "state": state, "code_challenge": code_challenge,
        "code_challenge_method": "S256", "access_type": "offline",
    })
    print(f"  {url}\n")
    webbrowser.open(url)
    srv = HTTPServer(("127.0.0.1", 8085), Handler)
    srv.handle_request()
    srv.server_close()
    resp = httpx.post("https://oauth2.googleapis.com/token", data={
        "client_id": CLIENT_ID, "client_secret": CLIENT_SECRET,
        "code": auth_code, "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code", "code_verifier": code_verifier,
    })
    access_token = resp.json()["access_token"]
    print("  [OK] Authenticated\n")

def headers():
    return {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}

client = httpx.Client(timeout=60)

def wait_op(url, label, timeout=600):
    print(f"    Waiting for {label}...", end="", flush=True)
    start = time.time()
    while time.time() - start < timeout:
        try:
            resp = client.get(url, headers=headers())
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

def check_cloud_sql():
    print("[1] Checking Cloud SQL status...")
    resp = client.get(f"{SQL_URL}/projects/{PROJECT_ID}/instances/{SQL_INSTANCE}", headers=headers())
    if resp.status_code != 200:
        print(f"    Not found: {resp.status_code}")
        return None, None
    data = resp.json()
    state = data.get("state", "UNKNOWN")
    ip = None
    for addr in data.get("ipAddresses", []):
        if addr.get("type") == "PRIVATE":
            ip = addr["ipAddress"]
    print(f"    State: {state}, IP: {ip}")
    return state, ip

def wait_for_sql_runnable():
    print("    Waiting for RUNNABLE...", end="", flush=True)
    for _ in range(60):
        try:
            resp = client.get(f"{SQL_URL}/projects/{PROJECT_ID}/instances/{SQL_INSTANCE}", headers=headers())
            if resp.status_code == 200:
                state = resp.json().get("state", "")
                if state == "RUNNABLE":
                    print(f" done ({state})")
                    return True
                print(".", end="", flush=True)
        except Exception:
            print("x", end="", flush=True)
        time.sleep(15)
    print(" TIMEOUT")
    return False

def check_redis():
    print("\n[2] Checking Redis...")
    resp = client.get(
        f"{REDIS_URL_API}/projects/{PROJECT_ID}/locations/{REGION}/instances/{REDIS_INSTANCE}",
        headers=headers(),
    )
    if resp.status_code == 200:
        data = resp.json()
        h = data.get("host", "10.0.0.4")
        p = data.get("port", 6379)
        print(f"    [OK] {h}:{p} (state={data.get('state')})")
        return h, p
    print(f"    Not found: {resp.status_code}")
    return "10.0.0.4", 6379

def ensure_db_user(sql_ip):
    print("\n[3] Ensuring database and user...")
    client.post(
        f"{SQL_URL}/projects/{PROJECT_ID}/instances/{SQL_INSTANCE}/databases",
        headers=headers(), json={"name": "ibms_enterprise"},
    )
    client.post(
        f"{SQL_URL}/projects/{PROJECT_ID}/instances/{SQL_INSTANCE}/users",
        headers=headers(), json={"name": "ibms_user", "password": DB_USER_PASSWORD},
    )
    print("    [OK] Database and user ensured")

def fetch_logs():
    print("\n[4] Fetching recent Cloud Run logs...")
    body = {
        "resourceNames": [f"projects/{PROJECT_ID}"],
        "filter": f'resource.type="cloud_run_revision" AND resource.labels.service_name="{SERVICE_NAME}" AND severity>=DEFAULT',
        "orderBy": "timestamp desc",
        "pageSize": 25,
    }
    resp = client.post(f"{LOGS_URL}/entries:list", headers=headers(), json=body)
    if resp.status_code == 200:
        entries = resp.json().get("entries", [])
        if not entries:
            print("    (no logs found)")
            return
        for e in reversed(entries):
            ts = e.get("timestamp", "")[:19]
            msg = e.get("textPayload", "") or json.dumps(e.get("jsonPayload", {}))[:200]
            print(f"    {ts} | {msg[:150]}")
    else:
        print(f"    Failed to fetch logs: {resp.status_code}")

def deploy_cloud_run(redis_host, redis_port):
    print("\n[5] Deploying Cloud Run...")
    image = f"{REGION}-docker.pkg.dev/{PROJECT_ID}/{REPO_NAME}/ibms-web:latest"
    connector = f"projects/{PROJECT_ID}/locations/{REGION}/connectors/{CONNECTOR_NAME}"

    service_body = {
        "template": {
            "scaling": {"minInstanceCount": 0, "maxInstanceCount": 4},
            "vpcAccess": {
                "connector": connector,
                "egress": "PRIVATE_RANGES_ONLY",
            },
            "containers": [{
                "image": image,
                "ports": [{"containerPort": 8080}],
                "resources": {"limits": {"cpu": "2", "memory": "2Gi"}},
                "env": [
                    {"name": "HOST", "value": "0.0.0.0"},
                    {"name": "RELOAD", "value": "false"},
                    {"name": "LOG_LEVEL", "value": "warning"},
                    {"name": "COOKIE_SECURE", "value": "true"},
                    {"name": "SECRET_KEY", "value": SECRET_KEY},
                    {"name": "JWT_SECRET", "value": JWT_SECRET},
                    {"name": "GROQ_API_KEY", "value": os.getenv("GROQ_API_KEY", "")},
                    {"name": "ALLOWED_ORIGINS", "value": os.getenv("ALLOWED_ORIGINS", "")},
                    {"name": "REDIS_URL", "value": f"redis://{redis_host}:{redis_port}/0"},
                    {"name": "SUPABASE_URL", "value": SUPABASE_URL},
                    {"name": "SUPABASE_KEY", "value": SUPABASE_KEY},
                ],
                "startupProbe": {
                    "httpGet": {"path": "/api/health", "port": 8080},
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

    resp = client.patch(
        f"{RUN_URL}/projects/{PROJECT_ID}/locations/{REGION}/services/{SERVICE_NAME}",
        headers=headers(),
        params={"allowMissing": "true"},
        json=service_body,
    )
    if resp.status_code == 200:
        op = resp.json()
        op_name = op.get("name", "")
        if op_name:
            ok = wait_op(f"{RUN_URL}/{op_name}", "Cloud Run deploy", timeout=600)
            if not ok:
                print("    Deploy failed — fetching logs...")
                fetch_logs()
                return False
    else:
        print(f"    [FAIL] Deploy: {resp.status_code} — {resp.text[:400]}")
        return False

    # Make publicly accessible
    client.post(
        f"{RUN_URL}/projects/{PROJECT_ID}/locations/{REGION}/services/{SERVICE_NAME}:setIamPolicy",
        headers=headers(),
        json={"policy": {"bindings": [{"role": "roles/run.invoker", "members": ["allUsers"]}]}},
    )

    # Get service URL
    svc = client.get(
        f"{RUN_URL}/projects/{PROJECT_ID}/locations/{REGION}/services/{SERVICE_NAME}",
        headers=headers(),
    )
    if svc.status_code == 200:
        uri = svc.json().get("uri", "")
        print(f"\n{'=' * 60}")
        print(f"  IBMS LIVE!")
        print(f"{'=' * 60}")
        print(f"  URL:       {uri}")
        print(f"  Health:    {uri}/api/health")
        print(f"  Dashboard: {uri}/")
        print(f"  API Docs:  {uri}/api/docs")
        print(f"{'=' * 60}\n")
    return True


def main():
    print("=" * 60)
    print("  IBMS — Cloud Run Redeploy")
    print("=" * 60 + "\n")

    authenticate()

    # Step 1: Check Redis (Cloud SQL removed — using Supabase)
    redis_host, redis_port = check_redis()

    # Step 2: Fetch existing logs
    fetch_logs()

    # Step 3: Deploy
    deploy_cloud_run(redis_host, redis_port)


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

    log = open("deploy/gcp/_redeploy_log.txt", "w", encoding="utf-8")
    sys.stdout = Tee(sys.__stdout__, log)
    sys.stderr = Tee(sys.__stderr__, log)
    main()
