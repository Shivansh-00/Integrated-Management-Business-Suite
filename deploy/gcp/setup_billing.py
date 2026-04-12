"""Link billing and enable APIs for ibms-enterprise - saves output to file."""
import http.server, urllib.parse, secrets, hashlib, base64, webbrowser, sys, time
import httpx

LOG = open("deploy/gcp/_setup_log.txt", "w", encoding="utf-8")
def log(msg):
    print(msg)
    LOG.write(msg + "\n")
    LOG.flush()

CLIENT_ID = "764086051850-6qr4p6gpi6hn506pt8ejuq83di341hur.apps.googleusercontent.com"
CLIENT_SECRET = "d-FL95Q19q7MQmFpd7hHD0Ty"
REDIRECT_URI = "http://localhost:8089"
SCOPES = "https://www.googleapis.com/auth/cloud-platform"
PROJECT_ID = "ibms-enterprise"
BILLING_ACCOUNT = "billingAccounts/016241-B8D40A-3102D2"

code_verifier = secrets.token_urlsafe(64)
code_challenge = base64.urlsafe_b64encode(
    hashlib.sha256(code_verifier.encode()).digest()
).rstrip(b"=").decode()
state = secrets.token_urlsafe(16)
auth_code = None

class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        global auth_code
        p = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        if "code" in p and p.get("state", [None])[0] == state:
            auth_code = p["code"][0]
            self.send_response(200)
            self.send_header("Content-Type","text/html")
            self.end_headers()
            self.wfile.write(b"<h2>OK</h2>")
        else:
            self.send_response(400)
            self.end_headers()
    def log_message(self, *a): pass

s = http.server.HTTPServer(("127.0.0.1", 8089), H)
s.timeout = 120
url = (f"https://accounts.google.com/o/oauth2/v2/auth?client_id={CLIENT_ID}"
       f"&redirect_uri={REDIRECT_URI}&response_type=code&scope={SCOPES}"
       f"&state={state}&code_challenge={code_challenge}"
       f"&code_challenge_method=S256&access_type=offline")
log("Opening browser...")
webbrowser.open(url)
s.handle_request()
s.server_close()
if not auth_code:
    log("Auth failed"); sys.exit(1)

r = httpx.post("https://oauth2.googleapis.com/token", data={
    "client_id": CLIENT_ID, "client_secret": CLIENT_SECRET,
    "code": auth_code, "grant_type": "authorization_code",
    "redirect_uri": REDIRECT_URI, "code_verifier": code_verifier,
})
token = r.json()["access_token"]
log("[OK] Authenticated")
c = httpx.Client(timeout=60)
h = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# 1. Link billing
log("\n=== Linking billing ===")
r1 = c.put(
    f"https://cloudbilling.googleapis.com/v1/projects/{PROJECT_ID}/billingInfo",
    headers=h,
    json={"billingAccountName": BILLING_ACCOUNT})
log(f"Status: {r1.status_code}")
log(f"Response: {r1.text[:500]}")

# 2. Verify
log("\n=== Verify billing ===")
r2 = c.get(f"https://cloudbilling.googleapis.com/v1/projects/{PROJECT_ID}/billingInfo",
           headers={"Authorization": f"Bearer {token}"})
log(f"Billing enabled: {r2.json().get('billingEnabled')}")

# 3. Enable APIs needed for deployment
log("\n=== Enabling APIs ===")
apis = [
    "serviceusage.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "cloudbuild.googleapis.com",
    "run.googleapis.com",
    "artifactregistry.googleapis.com",
    "sqladmin.googleapis.com",
    "redis.googleapis.com",
    "vpcaccess.googleapis.com",
    "compute.googleapis.com",
    "secretmanager.googleapis.com",
    "servicenetworking.googleapis.com",
]
for api in apis:
    try:
        r3 = c.post(
            f"https://serviceusage.googleapis.com/v1/projects/{PROJECT_ID}/services/{api}:enable",
            headers=h)
        if r3.status_code == 200:
            log(f"  [OK] {api}")
        else:
            log(f"  [{r3.status_code}] {api}: {r3.text[:200]}")
    except Exception as e:
        log(f"  [ERR] {api}: {e}")

# Wait for APIs to propagate
log("\nWaiting 15s for API propagation...")
time.sleep(15)
log("\n=== SETUP COMPLETE ===")
LOG.close()
