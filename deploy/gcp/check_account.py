"""Quick GCP account check — list projects and billing."""
import http.server
import urllib.parse
import secrets
import hashlib
import base64
import webbrowser
import sys

import httpx

CLIENT_ID = "764086051850-6qr4p6gpi6hn506pt8ejuq83di341hur.apps.googleusercontent.com"
CLIENT_SECRET = "d-FL95Q19q7MQmFpd7hHD0Ty"
REDIRECT_URI = "http://localhost:8086"
SCOPES = "https://www.googleapis.com/auth/cloud-platform"

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
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<h2>OK - return to terminal</h2>")
        else:
            self.send_response(400)
            self.end_headers()

    def log_message(self, *a):
        pass


s = http.server.HTTPServer(("127.0.0.1", 8086), H)
s.timeout = 120
url = (
    f"https://accounts.google.com/o/oauth2/v2/auth?"
    f"client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&response_type=code"
    f"&scope={SCOPES}&state={state}&code_challenge={code_challenge}"
    f"&code_challenge_method=S256&access_type=offline"
)
print("Opening browser...")
webbrowser.open(url)
s.handle_request()
s.server_close()
if not auth_code:
    print("Auth failed")
    sys.exit(1)

r = httpx.post(
    "https://oauth2.googleapis.com/token",
    data={
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code": auth_code,
        "grant_type": "authorization_code",
        "redirect_uri": REDIRECT_URI,
        "code_verifier": code_verifier,
    },
)
token = r.json()["access_token"]
print("Authenticated!")

c = httpx.Client(timeout=30)
h = {"Authorization": f"Bearer {token}"}

# List projects
resp = c.get("https://cloudresourcemanager.googleapis.com/v1/projects", headers=h)
print(f"\n=== Projects (status {resp.status_code}) ===")
if resp.status_code == 200:
    projects = resp.json().get("projects", [])
    if projects:
        for p in projects:
            print(f"  - {p['projectId']} ({p.get('name','')}) state={p.get('lifecycleState','')}")
    else:
        print("  No projects found — you need to create one")
else:
    print(f"  {resp.text[:300]}")

# Check billing
resp2 = c.get("https://cloudbilling.googleapis.com/v1/billingAccounts", headers=h)
print(f"\n=== Billing Accounts (status {resp2.status_code}) ===")
if resp2.status_code == 200:
    accts = resp2.json().get("billingAccounts", [])
    if accts:
        for a in accts:
            print(f"  - {a['name']}: {a.get('displayName','')}, open={a.get('open',False)}")
    else:
        print("  No billing accounts — billing must be enabled for deployment")
else:
    print(f"  {resp2.text[:300]}")
