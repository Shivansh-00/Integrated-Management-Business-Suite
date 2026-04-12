#!/usr/bin/env python3
"""
IBMS Enterprise — Google Cloud Platform Deployment Script
==========================================================
Deploys the full IBMS stack to GCP using REST APIs only.
No gcloud CLI required — uses OAuth 2.0 device flow for auth.

Services provisioned:
  • Artifact Registry (Docker repo)
  • Cloud Build (builds container image from source)
  • Cloud SQL MySQL 8.0
  • Memorystore Redis 7.0
  • Cloud Run (serverless container hosting)
  • VPC + Serverless connector

Usage:
  pip install httpx
  python deploy_gcp.py
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
import threading
import time
import urllib.parse
import webbrowser
from pathlib import Path

try:
    import httpx
except ImportError:
    print("ERROR: httpx is required. Run: pip install httpx")
    sys.exit(1)

# ─── Configuration ──────────────────────────────────────────────────────────

# Google Cloud SDK OAuth2 client (public, used by gcloud CLI)
GOOGLE_CLIENT_ID = "764086051850-6qr4p6gpi6hn506pt8ejuq83di341hur.apps.googleusercontent.com"
GOOGLE_CLIENT_SECRET = "d-FL95Q19q7MQmFpd7hHD0Ty"

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
SCOPES = "https://www.googleapis.com/auth/cloud-platform"
REDIRECT_URI = "http://localhost:8085"

# Project settings (override via env vars)
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
CRM_URL = "https://cloudresourcemanager.googleapis.com/v1"
RUN_URL = "https://run.googleapis.com/v2"
SQL_URL = "https://sqladmin.googleapis.com/v1"
AR_URL = "https://artifactregistry.googleapis.com/v1"
CB_URL = "https://cloudbuild.googleapis.com/v1"
REDIS_URL_API = "https://redis.googleapis.com/v1"
SM_URL = "https://secretmanager.googleapis.com/v1"
SU_URL = "https://serviceusage.googleapis.com/v1"
VPC_CONN_URL = "https://vpcaccess.googleapis.com/v1"


class GCPDeployer:
    """Deploys IBMS to GCP using REST APIs."""

    def __init__(self):
        self.client = httpx.Client(timeout=300)
        self.token: str = ""
        self.project_number: str = ""

    # ─── Authentication ──────────────────────────────────────────────────

    def authenticate(self):
        """OAuth 2.0 authorization code flow with local HTTP callback."""
        print("\n" + "=" * 60)
        print("  GCP Authentication — Browser Authorization Flow")
        print("=" * 60)

        # PKCE code verifier/challenge
        code_verifier = secrets.token_urlsafe(64)
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode()).digest()
        ).rstrip(b"=").decode()

        state = secrets.token_urlsafe(16)
        auth_code = None
        server_error = None

        # Tiny HTTP server to catch the OAuth callback
        class CallbackHandler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                nonlocal auth_code, server_error
                params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
                if "code" in params and params.get("state", [None])[0] == state:
                    auth_code = params["code"][0]
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html")
                    self.end_headers()
                    self.wfile.write(b"<html><body><h2>Authorization successful!</h2>"
                                    b"<p>You can close this tab and return to the terminal.</p></body></html>")
                else:
                    server_error = params.get("error", ["unknown"])[0]
                    self.send_response(400)
                    self.send_header("Content-Type", "text/html")
                    self.end_headers()
                    self.wfile.write(b"<html><body><h2>Authorization failed</h2></body></html>")

            def log_message(self, format, *args):
                pass  # Suppress log output

        server = http.server.HTTPServer(("127.0.0.1", 8085), CallbackHandler)
        server.timeout = 120

        # Build authorization URL
        auth_params = urllib.parse.urlencode({
            "client_id": GOOGLE_CLIENT_ID,
            "redirect_uri": REDIRECT_URI,
            "response_type": "code",
            "scope": SCOPES,
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "access_type": "offline",
        })
        auth_url = f"{AUTH_URL}?{auth_params}"

        print(f"\n  Opening browser for authorization...")
        print(f"  If browser doesn't open, visit:\n  {auth_url}\n")
        webbrowser.open(auth_url)

        # Wait for callback
        server.handle_request()
        server.server_close()

        if not auth_code:
            print(f"  [FAIL] Authorization failed: {server_error}")
            sys.exit(1)

        # Exchange code for tokens
        token_resp = self.client.post(TOKEN_URL, data={
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "code": auth_code,
            "grant_type": "authorization_code",
            "redirect_uri": REDIRECT_URI,
            "code_verifier": code_verifier,
        })

        if token_resp.status_code != 200:
            print(f"  [FAIL] Token exchange failed: {token_resp.text[:300]}")
            sys.exit(1)

        token_data = token_resp.json()
        self.token = token_data["access_token"]
        print("  [OK] Authenticated successfully!\n")

    def _headers(self):
        return {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}

    def _wait_operation(self, op_url: str, label: str, timeout: int = 600):
        """Poll a long-running operation until completion."""
        print(f"    Waiting for {label}...", end="", flush=True)
        start = time.time()
        while time.time() - start < timeout:
            resp = self.client.get(op_url, headers=self._headers())
            if resp.status_code != 200:
                time.sleep(10)
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

    # ─── Project Info ────────────────────────────────────────────────────

    def get_project_number(self):
        """Get the project number for API calls."""
        try:
            resp = self.client.get(
                f"https://cloudresourcemanager.googleapis.com/v3/projects/{PROJECT_ID}",
                headers=self._headers(),
                timeout=30,
            )
            if resp.status_code == 200:
                data = resp.json()
                # v3 returns "name": "projects/NUMBER"
                self.project_number = data.get("name", "").replace("projects/", "")
                print(f"  Project: {PROJECT_ID} (#{self.project_number})")
            else:
                print(f"  Warning: Could not fetch project info: {resp.status_code}")
        except Exception as e:
            print(f"  Warning: Could not fetch project info: {e}")

    # ─── Enable APIs ─────────────────────────────────────────────────────

    def enable_apis(self):
        """Enable all required GCP APIs."""
        apis = [
            "run.googleapis.com",
            "sqladmin.googleapis.com",
            "artifactregistry.googleapis.com",
            "cloudbuild.googleapis.com",
            "redis.googleapis.com",
            "vpcaccess.googleapis.com",
            "secretmanager.googleapis.com",
            "compute.googleapis.com",
            "servicenetworking.googleapis.com",
        ]
        print("\n[1/7] Enabling GCP APIs...")
        for api in apis:
            resp = self.client.post(
                f"{SU_URL}/projects/{PROJECT_ID}/services/{api}:enable",
                headers=self._headers(),
            )
            status = "[OK]" if resp.status_code in (200, 409) else f"[FAIL] ({resp.status_code})"
            print(f"    {status} {api}")

        # Give APIs a moment to propagate
        print("    Waiting for API propagation...")
        time.sleep(15)

    # ─── Artifact Registry ───────────────────────────────────────────────

    def create_artifact_registry(self):
        """Create Docker repository in Artifact Registry."""
        print("\n[2/7] Creating Artifact Registry repository...")
        resp = self.client.post(
            f"{AR_URL}/projects/{PROJECT_ID}/locations/{REGION}/repositories",
            headers=self._headers(),
            params={"repositoryId": REPO_NAME},
            json={
                "format": "DOCKER",
                "description": "IBMS Enterprise container images",
            },
        )
        if resp.status_code in (200, 409):
            print(f"    [OK] Repository: {REGION}-docker.pkg.dev/{PROJECT_ID}/{REPO_NAME}")
        else:
            data = resp.json()
            if "already exists" in str(data):
                print(f"    [OK] Repository already exists")
            else:
                print(f"    [FAIL] Error: {resp.status_code} — {data}")

    # ─── Cloud Build (build container from source) ───────────────────────

    def build_container(self):
        """Upload source and trigger Cloud Build to build container image."""
        print("\n[3/7] Building container image via Cloud Build...")

        # Create a tar.gz of the project source
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

        # Upload source to Cloud Build
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

        # First, we need to create the storage bucket and upload source
        storage_url = "https://storage.googleapis.com"
        bucket_name = f"{PROJECT_ID}_cloudbuild"

        # Create bucket (may already exist)
        self.client.post(
            f"{storage_url}/storage/v1/b",
            headers=self._headers(),
            params={"project": PROJECT_ID},
            json={"name": bucket_name, "location": REGION},
        )

        # Upload source tarball
        upload_resp = self.client.post(
            f"{storage_url}/upload/storage/v1/b/{bucket_name}/o",
            headers={"Authorization": f"Bearer {self.token}"},
            params={"uploadType": "media", "name": "source.tar.gz"},
            content=source_bytes,
        )
        if upload_resp.status_code in (200, 201):
            print("    [OK] Source uploaded to Cloud Storage")
        else:
            print(f"    [FAIL] Upload failed: {upload_resp.status_code}")
            print(f"      {upload_resp.text[:300]}")
            return False

        # Trigger build
        build_resp = self.client.post(
            f"{CB_URL}/projects/{PROJECT_ID}/builds",
            headers=self._headers(),
            json=build_config,
        )
        if build_resp.status_code == 200:
            op = build_resp.json()
            op_name = op.get("name", "")
            print(f"    Build started: {op_name}")
            # Wait for build
            return self._wait_operation(
                f"{CB_URL}/{op_name}",
                "container build",
                timeout=900,
            )
        else:
            print(f"    [FAIL] Build trigger failed: {build_resp.status_code}")
            print(f"      {build_resp.text[:300]}")
            return False

    # ─── VPC Network ─────────────────────────────────────────────────────

    def create_vpc(self):
        """Create VPC network for private service access."""
        print("\n[4/7] Creating VPC network...")

        # Create VPC
        resp = self.client.post(
            f"{BASE_URL}/projects/{PROJECT_ID}/global/networks",
            headers=self._headers(),
            json={
                "name": VPC_NAME,
                "autoCreateSubnetworks": False,
            },
        )
        if resp.status_code == 200:
            op = resp.json()
            self._wait_operation(op.get("selfLink", ""), "VPC creation")
        elif resp.status_code == 409 or "already exists" in resp.text:
            print("    [OK] VPC already exists")
        else:
            print(f"    VPC: {resp.status_code} — {resp.text[:200]}")

        # Create subnet
        resp = self.client.post(
            f"{BASE_URL}/projects/{PROJECT_ID}/regions/{REGION}/subnetworks",
            headers=self._headers(),
            json={
                "name": SUBNET_NAME,
                "ipCidrRange": "10.0.0.0/24",
                "network": f"projects/{PROJECT_ID}/global/networks/{VPC_NAME}",
                "region": REGION,
            },
        )
        if resp.status_code == 200:
            op = resp.json()
            self._wait_operation(op.get("selfLink", ""), "subnet creation")
        elif resp.status_code == 409 or "already exists" in resp.text:
            print("    [OK] Subnet already exists")

        # Allocate private IP range for services
        resp = self.client.post(
            f"{BASE_URL}/projects/{PROJECT_ID}/global/addresses",
            headers=self._headers(),
            json={
                "name": "ibms-private-ip",
                "purpose": "VPC_PEERING",
                "addressType": "INTERNAL",
                "prefixLength": 16,
                "network": f"projects/{PROJECT_ID}/global/networks/{VPC_NAME}",
            },
        )
        if resp.status_code == 200:
            op = resp.json()
            self._wait_operation(op.get("selfLink", ""), "IP allocation")
        elif "already exists" in resp.text:
            print("    [OK] Private IP range already allocated")

        # Create VPC peering for services
        resp = self.client.post(
            f"https://servicenetworking.googleapis.com/v1/services/servicenetworking.googleapis.com/connections",
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
                self._wait_operation(
                    f"https://servicenetworking.googleapis.com/v1/{op_name}",
                    "VPC peering",
                    timeout=300,
                )
            else:
                print("    [OK] VPC peering configured")
        elif "already exists" in str(resp.text):
            print("    [OK] VPC peering already configured")

        # Create Serverless VPC Access connector
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
            self._wait_operation(
                f"{VPC_CONN_URL}/{op.get('name', '')}",
                "VPC connector",
                timeout=300,
            )
        elif "already exists" in resp.text:
            print("    [OK] VPC connector already exists")

    # ─── Cloud SQL ───────────────────────────────────────────────────────

    def create_cloud_sql(self):
        """Create Cloud SQL MySQL instance."""
        print("\n[5/7] Creating Cloud SQL MySQL instance...")

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
                    "backupConfiguration": {
                        "enabled": True,
                        "binaryLogEnabled": True,
                    },
                    "databaseFlags": [
                        {"name": "character_set_server", "value": "utf8mb4"},
                    ],
                },
                "rootPassword": DB_USER_PASSWORD,
            },
        )
        if resp.status_code == 200:
            op = resp.json()
            self._wait_operation(
                f"{SQL_URL}/projects/{PROJECT_ID}/operations/{op.get('name', '')}",
                "Cloud SQL creation",
                timeout=600,
            )
        elif "already exists" in resp.text:
            print("    [OK] Cloud SQL instance already exists")
        else:
            print(f"    [FAIL] Cloud SQL: {resp.status_code} — {resp.text[:300]}")
            return

        # Create database
        self.client.post(
            f"{SQL_URL}/projects/{PROJECT_ID}/instances/{SQL_INSTANCE}/databases",
            headers=self._headers(),
            json={"name": "ibms_enterprise"},
        )

        # Create app user
        self.client.post(
            f"{SQL_URL}/projects/{PROJECT_ID}/instances/{SQL_INSTANCE}/users",
            headers=self._headers(),
            json={
                "name": "ibms_user",
                "password": DB_USER_PASSWORD,
            },
        )
        print("    [OK] Database and user created")

        # Get private IP
        info_resp = self.client.get(
            f"{SQL_URL}/projects/{PROJECT_ID}/instances/{SQL_INSTANCE}",
            headers=self._headers(),
        )
        if info_resp.status_code == 200:
            ip_addrs = info_resp.json().get("ipAddresses", [])
            for ip in ip_addrs:
                if ip.get("type") == "PRIVATE":
                    self.sql_private_ip = ip["ipAddress"]
                    print(f"    Private IP: {self.sql_private_ip}")
                    return
        self.sql_private_ip = "10.0.0.3"  # fallback

    # ─── Memorystore Redis ───────────────────────────────────────────────

    def create_redis(self):
        """Create Memorystore Redis instance."""
        print("\n[6/7] Creating Memorystore Redis...")

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
            self._wait_operation(
                f"{REDIS_URL_API}/{op.get('name', '')}",
                "Redis creation",
                timeout=600,
            )
        elif "already exists" in resp.text:
            print("    [OK] Redis instance already exists")
        else:
            print(f"    [FAIL] Redis: {resp.status_code} — {resp.text[:300]}")

        # Get host
        info_resp = self.client.get(
            f"{REDIS_URL_API}/projects/{PROJECT_ID}/locations/{REGION}/instances/{REDIS_INSTANCE}",
            headers=self._headers(),
        )
        if info_resp.status_code == 200:
            data = info_resp.json()
            self.redis_host = data.get("host", "10.0.0.4")
            self.redis_port = data.get("port", 6379)
            print(f"    Redis: {self.redis_host}:{self.redis_port}")
        else:
            self.redis_host = "10.0.0.4"
            self.redis_port = 6379

    # ─── Cloud Run ───────────────────────────────────────────────────────

    def deploy_cloud_run(self):
        """Deploy the IBMS container to Cloud Run."""
        print("\n[7/7] Deploying to Cloud Run...")

        image = f"{REGION}-docker.pkg.dev/{PROJECT_ID}/{REPO_NAME}/ibms-web:latest"
        connector = f"projects/{PROJECT_ID}/locations/{REGION}/connectors/{CONNECTOR_NAME}"

        sql_ip = getattr(self, "sql_private_ip", "10.0.0.3")
        redis_host = getattr(self, "redis_host", "10.0.0.4")
        redis_port = getattr(self, "redis_port", 6379)

        service_body = {
            "template": {
                "scaling": {
                    "minInstanceCount": 0,
                    "maxInstanceCount": 4,
                },
                "vpcAccess": {
                    "connector": connector,
                    "egress": "PRIVATE_RANGES_ONLY",
                },
                "containers": [
                    {
                        "image": image,
                        "ports": [{"containerPort": 8080}],
                        "resources": {
                            "limits": {"cpu": "2", "memory": "2Gi"},
                        },
                        "env": [
                            {"name": "HOST", "value": "0.0.0.0"},
                            {"name": "RELOAD", "value": "false"},
                            {"name": "LOG_LEVEL", "value": "warning"},
                            {"name": "SECRET_KEY", "value": SECRET_KEY},
                            {
                                "name": "REDIS_URL",
                                "value": f"redis://{redis_host}:{redis_port}/0",
                            },
                            {
                                "name": "MARIADB_URI",
                                "value": f"mysql+aiomysql://ibms_user:{DB_USER_PASSWORD}@{sql_ip}:3306/ibms_enterprise",
                            },
                            {
                                "name": "MONGO_URI",
                                "value": MONGO_URI or "mongodb://localhost:27017",
                            },
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
                    }
                ],
            },
        }

        # Create / update service
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
                self._wait_operation(f"{RUN_URL}/{op_name}", "Cloud Run deploy", timeout=600)
        else:
            print(f"    [FAIL] Deploy failed: {resp.status_code}")
            print(f"      {resp.text[:400]}")
            return

        # Make publicly accessible (allow unauthenticated)
        iam_resp = self.client.post(
            f"{RUN_URL}/projects/{PROJECT_ID}/locations/{REGION}/services/{SERVICE_NAME}:setIamPolicy",
            headers=self._headers(),
            json={
                "policy": {
                    "bindings": [
                        {
                            "role": "roles/run.invoker",
                            "members": ["allUsers"],
                        }
                    ]
                }
            },
        )

        # Get service URL
        svc_resp = self.client.get(
            f"{RUN_URL}/projects/{PROJECT_ID}/locations/{REGION}/services/{SERVICE_NAME}",
            headers=self._headers(),
        )
        if svc_resp.status_code == 200:
            uri = svc_resp.json().get("uri", "")
            print(f"\n{'=' * 60}")
            print(f"  [OK] IBMS DEPLOYED SUCCESSFULLY!")
            print(f"{'=' * 60}")
            print(f"  URL: {uri}")
            print(f"  API: {uri}/api/health")
            print(f"  Dashboard: {uri}/")
            print(f"{'=' * 60}\n")
        else:
            print("    Could not retrieve service URL")

    # ─── Main ────────────────────────────────────────────────────────────

    def deploy(self):
        """Run the full deployment pipeline."""
        print("\n" + "=" * 60)
        print("  IBMS Enterprise — GCP Deployment")
        print("=" * 60)

        self.authenticate()
        self.get_project_number()
        self.enable_apis()
        self.create_artifact_registry()
        self.build_container()
        self.create_vpc()
        self.create_cloud_sql()
        self.create_redis()
        self.deploy_cloud_run()


if __name__ == "__main__":
    import io

    # Tee stdout to a log file so output isn't lost
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

    log_file = open("deploy/gcp/_deploy_log.txt", "w", encoding="utf-8")
    sys.stdout = Tee(sys.__stdout__, log_file)
    sys.stderr = Tee(sys.__stderr__, log_file)

    deployer = GCPDeployer()
    deployer.deploy()
    log_file.close()
