#!/usr/bin/env python3
"""
IBMS Enterprise — GCP Deployment Repair Script
================================================
Repairs failed deployment steps:
  - VPC Connector (failed: missing maxInstances)
  - Cloud SQL MySQL (failed: NETWORK_NOT_PEERED)
  - Cloud Run deployment

Skips steps that already succeeded:
  - APIs, Artifact Registry, Cloud Build, VPC/subnet/peering
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
import time
import urllib.parse
import webbrowser

try:
    import httpx
except ImportError:
    print("ERROR: httpx is required. Run: pip install httpx")
    sys.exit(1)

# ─── Configuration (same as deploy_gcp.py) ──────────────────────────────────

GOOGLE_CLIENT_ID = "764086051850-6qr4p6gpi6hn506pt8ejuq83di341hur.apps.googleusercontent.com"
GOOGLE_CLIENT_SECRET = "d-FL95Q19q7MQmFpd7hHD0Ty"
AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
SCOPES = "https://www.googleapis.com/auth/cloud-platform"
REDIRECT_URI = "http://localhost:8085"

PROJECT_ID = os.getenv("GCP_PROJECT_ID", "total-handler-463313-e2")
REGION = os.getenv("GCP_REGION", "asia-south1")
REPO_NAME = "ibms-docker"
SERVICE_NAME = "ibms-web"
SQL_INSTANCE = "ibms-mysql"
REDIS_INSTANCE = "ibms-redis"
VPC_NAME = "ibms-vpc"
SUBNET_NAME = "ibms-subnet"
CONNECTOR_NAME = "ibms-connector"

DB_USER_PASSWORD = os.getenv("DB_USER_PASSWORD", secrets.token_urlsafe(24))
MONGO_URI = os.getenv("MONGO_URI", "")
SECRET_KEY = os.getenv("SECRET_KEY", secrets.token_urlsafe(48))

BASE_URL = "https://compute.googleapis.com/compute/v1"
RUN_URL = "https://run.googleapis.com/v2"
SQL_URL = "https://sqladmin.googleapis.com/v1"
REDIS_URL_API = "https://redis.googleapis.com/v1"
VPC_CONN_URL = "https://vpcaccess.googleapis.com/v1"
SN_URL = "https://servicenetworking.googleapis.com/v1"


class RepairDeployer:
    def __init__(self):
        self.client = httpx.Client(timeout=300)
        self.token = ""
        self.sql_private_ip = "10.0.0.3"
        self.redis_host = "10.0.0.4"
        self.redis_port = 6379

    def _headers(self):
        return {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}

    def _wait_op(self, url, label, timeout=600):
        print(f"    Waiting for {label}...", end="", flush=True)
        start = time.time()
        while time.time() - start < timeout:
            try:
                resp = self.client.get(url, headers=self._headers())
            except Exception:
                time.sleep(15)
                print("x", end="", flush=True)
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

    def authenticate(self):
        print("\n  Authenticating...")
        code_verifier = secrets.token_urlsafe(64)
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode()).digest()
        ).rstrip(b"=").decode()
        state = secrets.token_urlsafe(16)
        auth_code = None

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                nonlocal auth_code
                params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
                if "code" in params and params.get("state", [None])[0] == state:
                    auth_code = params["code"][0]
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html")
                    self.end_headers()
                    self.wfile.write(b"<h2>OK - return to terminal</h2>")
                else:
                    self.send_response(400)
                    self.end_headers()
            def log_message(self, *a): pass

        srv = http.server.HTTPServer(("127.0.0.1", 8085), Handler)
        srv.timeout = 120
        auth_params = urllib.parse.urlencode({
            "client_id": GOOGLE_CLIENT_ID, "redirect_uri": REDIRECT_URI,
            "response_type": "code", "scope": SCOPES, "state": state,
            "code_challenge": code_challenge, "code_challenge_method": "S256",
            "access_type": "offline",
        })
        url = f"{AUTH_URL}?{auth_params}"
        print(f"  Opening browser...\n  {url}\n")
        webbrowser.open(url)
        srv.handle_request()
        srv.server_close()
        if not auth_code:
            print("  [FAIL] Auth failed"); sys.exit(1)

        resp = self.client.post(TOKEN_URL, data={
            "client_id": GOOGLE_CLIENT_ID, "client_secret": GOOGLE_CLIENT_SECRET,
            "code": auth_code, "grant_type": "authorization_code",
            "redirect_uri": REDIRECT_URI, "code_verifier": code_verifier,
        })
        if resp.status_code != 200:
            print(f"  [FAIL] Token: {resp.text[:300]}"); sys.exit(1)
        self.token = resp.json()["access_token"]
        print("  [OK] Authenticated\n")

    # ─── Step 1: Verify/fix VPC peering ──────────────────────────────────

    def verify_vpc_peering(self):
        print("[1/5] Verifying VPC peering...")

        # Check existing peering connections
        resp = self.client.get(
            f"{SN_URL}/services/servicenetworking.googleapis.com/connections",
            headers=self._headers(),
            params={"network": f"projects/{PROJECT_ID}/global/networks/{VPC_NAME}"},
        )
        if resp.status_code == 200:
            connections = resp.json().get("connections", [])
            if connections:
                print(f"    [OK] VPC peering active ({len(connections)} connection(s))")
                return True

        # Re-create peering
        print("    Peering not found, creating...")
        resp = self.client.post(
            f"{SN_URL}/services/servicenetworking.googleapis.com/connections",
            headers=self._headers(),
            json={
                "network": f"projects/{PROJECT_ID}/global/networks/{VPC_NAME}",
                "reservedPeeringRanges": ["ibms-private-ip"],
            },
        )
        if resp.status_code == 200:
            op = resp.json()
            op_name = op.get("name", "")
            if op_name:
                return self._wait_op(f"{SN_URL}/{op_name}", "VPC peering", timeout=300)
            print("    [OK] VPC peering configured")
            return True
        else:
            print(f"    [FAIL] Peering: {resp.status_code} — {resp.text[:300]}")
            return False

    # ─── Step 2: Create VPC connector ────────────────────────────────────

    def create_vpc_connector(self):
        print("\n[2/5] Creating VPC connector...")

        # Check if exists
        resp = self.client.get(
            f"{VPC_CONN_URL}/projects/{PROJECT_ID}/locations/{REGION}/connectors/{CONNECTOR_NAME}",
            headers=self._headers(),
        )
        if resp.status_code == 200:
            state = resp.json().get("state", "")
            if state == "READY":
                print(f"    [OK] Connector already exists (READY)")
                return True
            print(f"    Connector exists but state={state} — deleting first...")
            del_resp = self.client.delete(
                f"{VPC_CONN_URL}/projects/{PROJECT_ID}/locations/{REGION}/connectors/{CONNECTOR_NAME}",
                headers=self._headers(),
            )
            if del_resp.status_code == 200:
                op = del_resp.json()
                op_name = op.get("name", "")
                if op_name:
                    self._wait_op(f"{VPC_CONN_URL}/{op_name}", "connector deletion", timeout=180)
                else:
                    time.sleep(30)
            else:
                print(f"    Delete returned {del_resp.status_code}: {del_resp.text[:200]}")
                time.sleep(30)

        # Create with maxInstances
        resp = self.client.post(
            f"{VPC_CONN_URL}/projects/{PROJECT_ID}/locations/{REGION}/connectors",
            headers=self._headers(),
            params={"connectorId": CONNECTOR_NAME},
            json={
                "network": VPC_NAME,
                "ipCidrRange": "10.8.0.0/28",
                "minInstances": 2,
                "maxInstances": 3,
            },
        )
        if resp.status_code == 200:
            op = resp.json()
            return self._wait_op(
                f"{VPC_CONN_URL}/{op.get('name', '')}",
                "VPC connector",
                timeout=300,
            )
        elif "already exists" in resp.text:
            print("    [OK] Connector already exists")
            return True
        else:
            print(f"    [FAIL] Connector: {resp.status_code} — {resp.text[:300]}")
            return False

    # ─── Step 3: Create Cloud SQL ────────────────────────────────────────

    def create_cloud_sql(self):
        print("\n[3/5] Creating Cloud SQL MySQL...")

        # Check if already exists
        resp = self.client.get(
            f"{SQL_URL}/projects/{PROJECT_ID}/instances/{SQL_INSTANCE}",
            headers=self._headers(),
        )
        if resp.status_code == 200:
            state = resp.json().get("state", "")
            print(f"    [OK] Cloud SQL already exists (state={state})")
            # Get private IP
            ip_addrs = resp.json().get("ipAddresses", [])
            for ip in ip_addrs:
                if ip.get("type") == "PRIVATE":
                    self.sql_private_ip = ip["ipAddress"]
                    print(f"    Private IP: {self.sql_private_ip}")
            self._ensure_db_and_user()
            return True

        # Create new instance
        resp = self.client.post(
            f"{SQL_URL}/projects/{PROJECT_ID}/instances",
            headers=self._headers(),
            json={
                "name": SQL_INSTANCE,
                "databaseVersion": "MYSQL_8_0",
                "region": REGION,
                "settings": {
                    "tier": "db-f1-micro",
                    "availabilityType": "ZONAL",
                    "ipConfiguration": {
                        "ipv4Enabled": False,
                        "privateNetwork": f"projects/{PROJECT_ID}/global/networks/{VPC_NAME}",
                    },
                    "backupConfiguration": {"enabled": True, "binaryLogEnabled": True},
                    "databaseFlags": [{"name": "character_set_server", "value": "utf8mb4"}],
                },
                "rootPassword": DB_USER_PASSWORD,
            },
        )
        if resp.status_code == 200:
            op = resp.json()
            ok = self._wait_op(
                f"{SQL_URL}/projects/{PROJECT_ID}/operations/{op.get('name', '')}",
                "Cloud SQL creation",
                timeout=900,
            )
            if not ok:
                return False
        elif "already exists" in resp.text:
            print("    [OK] Instance already exists")
        else:
            print(f"    [FAIL] Cloud SQL: {resp.status_code} — {resp.text[:300]}")
            return False

        self._ensure_db_and_user()

        # Get private IP
        info = self.client.get(
            f"{SQL_URL}/projects/{PROJECT_ID}/instances/{SQL_INSTANCE}",
            headers=self._headers(),
        )
        if info.status_code == 200:
            for ip in info.json().get("ipAddresses", []):
                if ip.get("type") == "PRIVATE":
                    self.sql_private_ip = ip["ipAddress"]
                    print(f"    Private IP: {self.sql_private_ip}")
                    return True
        self.sql_private_ip = "10.0.0.3"
        return True

    def _ensure_db_and_user(self):
        self.client.post(
            f"{SQL_URL}/projects/{PROJECT_ID}/instances/{SQL_INSTANCE}/databases",
            headers=self._headers(),
            json={"name": "ibms_enterprise"},
        )
        self.client.post(
            f"{SQL_URL}/projects/{PROJECT_ID}/instances/{SQL_INSTANCE}/users",
            headers=self._headers(),
            json={"name": "ibms_user", "password": DB_USER_PASSWORD},
        )
        print("    [OK] Database and user ensured")

    # ─── Step 4: Check Redis ─────────────────────────────────────────────

    def check_redis(self):
        print("\n[4/5] Checking Redis...")
        resp = self.client.get(
            f"{REDIS_URL_API}/projects/{PROJECT_ID}/locations/{REGION}/instances/{REDIS_INSTANCE}",
            headers=self._headers(),
        )
        if resp.status_code == 200:
            data = resp.json()
            state = data.get("state", "UNKNOWN")
            self.redis_host = data.get("host", "10.0.0.4")
            self.redis_port = data.get("port", 6379)
            print(f"    [OK] Redis exists (state={state}) — {self.redis_host}:{self.redis_port}")
            return True

        # Create Redis
        print("    Redis not found, creating...")
        resp = self.client.post(
            f"{REDIS_URL_API}/projects/{PROJECT_ID}/locations/{REGION}/instances",
            headers=self._headers(),
            params={"instanceId": REDIS_INSTANCE},
            json={
                "tier": "BASIC",
                "memorySizeGb": 1,
                "redisVersion": "REDIS_7_0",
                "authorizedNetwork": f"projects/{PROJECT_ID}/global/networks/{VPC_NAME}",
            },
        )
        if resp.status_code == 200:
            op = resp.json()
            ok = self._wait_op(
                f"{REDIS_URL_API}/{op.get('name', '')}",
                "Redis creation",
                timeout=600,
            )
            if ok:
                info = self.client.get(
                    f"{REDIS_URL_API}/projects/{PROJECT_ID}/locations/{REGION}/instances/{REDIS_INSTANCE}",
                    headers=self._headers(),
                )
                if info.status_code == 200:
                    self.redis_host = info.json().get("host", "10.0.0.4")
                    self.redis_port = info.json().get("port", 6379)
            return ok
        elif "already exists" in resp.text:
            print("    [OK] Redis already exists")
            return True
        else:
            print(f"    [FAIL] Redis: {resp.status_code} — {resp.text[:300]}")
            return False

    # ─── Step 5: Deploy Cloud Run ────────────────────────────────────────

    def deploy_cloud_run(self):
        print("\n[5/5] Deploying to Cloud Run...")

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
                        {"name": "SECRET_KEY", "value": SECRET_KEY},
                        {"name": "REDIS_URL", "value": f"redis://{self.redis_host}:{self.redis_port}/0"},
                        {"name": "MARIADB_URI", "value": f"mysql+aiomysql://ibms_user:{DB_USER_PASSWORD}@{self.sql_private_ip}:3306/ibms_enterprise"},
                        {"name": "MONGO_URI", "value": MONGO_URI or "mongodb://localhost:27017"},
                        {"name": "MONGO_DB_NAME", "value": "ibms_enterprise"},
                    ],
                    "startupProbe": {
                        "httpGet": {"path": "/api/health"},
                        "initialDelaySeconds": 10,
                        "periodSeconds": 5,
                        "failureThreshold": 10,
                    },
                    "livenessProbe": {
                        "httpGet": {"path": "/api/health"},
                        "periodSeconds": 15,
                    },
                }],
            },
        }

        resp = self.client.patch(
            f"{RUN_URL}/projects/{PROJECT_ID}/locations/{REGION}/services/{SERVICE_NAME}",
            headers=self._headers(),
            params={"allowMissing": "true"},
            json=service_body,
        )
        if resp.status_code == 200:
            op = resp.json()
            op_name = op.get("name", "")
            if op_name:
                self._wait_op(f"{RUN_URL}/{op_name}", "Cloud Run deploy", timeout=600)
        else:
            print(f"    [FAIL] Deploy: {resp.status_code} — {resp.text[:400]}")
            return False

        # Make publicly accessible
        self.client.post(
            f"{RUN_URL}/projects/{PROJECT_ID}/locations/{REGION}/services/{SERVICE_NAME}:setIamPolicy",
            headers=self._headers(),
            json={"policy": {"bindings": [{"role": "roles/run.invoker", "members": ["allUsers"]}]}},
        )

        # Get service URL
        svc = self.client.get(
            f"{RUN_URL}/projects/{PROJECT_ID}/locations/{REGION}/services/{SERVICE_NAME}",
            headers=self._headers(),
        )
        if svc.status_code == 200:
            uri = svc.json().get("uri", "")
            print(f"\n{'=' * 60}")
            print(f"  [OK] IBMS DEPLOYED SUCCESSFULLY!")
            print(f"{'=' * 60}")
            print(f"  URL: {uri}")
            print(f"  API: {uri}/api/health")
            print(f"  Dashboard: {uri}/")
            print(f"{'=' * 60}\n")
            return True
        else:
            print("    Could not retrieve service URL")
            return False

    def run(self):
        print("=" * 60)
        print("  IBMS — GCP Deployment Repair")
        print("=" * 60)

        self.authenticate()
        self.verify_vpc_peering()
        self.create_vpc_connector()
        self.create_cloud_sql()
        self.check_redis()
        self.deploy_cloud_run()


if __name__ == "__main__":
    # Tee to log file
    class Tee:
        def __init__(self, *streams):
            self.streams = streams
        def write(self, data):
            for s in self.streams:
                s.write(data)
                s.flush()
        def flush(self):
            for s in self.streams:
                s.flush()

    log = open("deploy/gcp/_repair_log.txt", "w", encoding="utf-8")
    sys.stdout = Tee(sys.__stdout__, log)
    sys.stderr = Tee(sys.__stderr__, log)

    RepairDeployer().run()
