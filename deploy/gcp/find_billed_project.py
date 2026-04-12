"""Find an existing project with billing enabled."""
import http.server, urllib.parse, secrets, hashlib, base64, webbrowser, sys
import httpx

LOG = open("deploy/gcp/_find_project_log.txt", "w", encoding="utf-8")
def log(msg):
    print(msg, flush=True)
    LOG.write(msg + "\n"); LOG.flush()

CLIENT_ID = "764086051850-6qr4p6gpi6hn506pt8ejuq83di341hur.apps.googleusercontent.com"
CLIENT_SECRET = "d-FL95Q19q7MQmFpd7hHD0Ty"
REDIRECT_URI = "http://localhost:8090"
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
            self.send_header("Content-Type","text/html")
            self.end_headers()
            self.wfile.write(b"<h2>OK</h2>")
        else:
            self.send_response(400)
            self.end_headers()
    def log_message(self, *a): pass

s = http.server.HTTPServer(("127.0.0.1", 8090), H)
s.timeout = 120
url = (f"https://accounts.google.com/o/oauth2/v2/auth?client_id={CLIENT_ID}"
       f"&redirect_uri={REDIRECT_URI}&response_type=code&scope={SCOPES}"
       f"&state={state}&code_challenge={code_challenge}"
       f"&code_challenge_method=S256&access_type=offline")
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
log("[OK] Authenticated\n")
c = httpx.Client(timeout=30)
h = {"Authorization": f"Bearer {token}"}

# Get all projects
resp = c.get("https://cloudresourcemanager.googleapis.com/v1/projects", headers=h)
projects = resp.json().get("projects", [])
log(f"Found {len(projects)} projects. Checking billing...\n")

billed = []
for p in projects:
    pid = p["projectId"]
    name = p.get("name", "")
    r2 = c.get(f"https://cloudbilling.googleapis.com/v1/projects/{pid}/billingInfo", headers=h)
    if r2.status_code == 200:
        bi = r2.json()
        enabled = bi.get("billingEnabled", False)
        acct = bi.get("billingAccountName", "")
        status = "BILLING ON" if enabled else "no billing"
        log(f"  {pid:40s} ({name:30s}) -> {status}")
        if enabled:
            billed.append(pid)
    else:
        log(f"  {pid:40s} -> error {r2.status_code}")

log(f"\n=== Projects with billing enabled: {len(billed)} ===")
for b in billed:
    log(f"  -> {b}")

LOG.close()
