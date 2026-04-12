"""Create ibms-enterprise project and link billing, then hand off to deploy."""
import http.server, urllib.parse, secrets, hashlib, base64, webbrowser, sys, time
import httpx

CLIENT_ID = "764086051850-6qr4p6gpi6hn506pt8ejuq83di341hur.apps.googleusercontent.com"
CLIENT_SECRET = "d-FL95Q19q7MQmFpd7hHD0Ty"
REDIRECT_URI = "http://localhost:8087"
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
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<h2>OK - return to terminal</h2>")
        else:
            self.send_response(400)
            self.end_headers()
    def log_message(self, *a): pass

s = http.server.HTTPServer(("127.0.0.1", 8087), H)
s.timeout = 120
url = (f"https://accounts.google.com/o/oauth2/v2/auth?"
       f"client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&response_type=code"
       f"&scope={SCOPES}&state={state}&code_challenge={code_challenge}"
       f"&code_challenge_method=S256&access_type=offline")
print("Opening browser for auth...")
webbrowser.open(url)
s.handle_request()
s.server_close()
if not auth_code:
    print("Auth failed"); sys.exit(1)

r = httpx.post("https://oauth2.googleapis.com/token", data={
    "client_id": CLIENT_ID, "client_secret": CLIENT_SECRET,
    "code": auth_code, "grant_type": "authorization_code",
    "redirect_uri": REDIRECT_URI, "code_verifier": code_verifier,
})
token = r.json()["access_token"]
print("[OK] Authenticated\n")

c = httpx.Client(timeout=60)
h = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# Step 1: Create project
print("Step 1: Creating project ibms-enterprise...")
resp = c.post("https://cloudresourcemanager.googleapis.com/v1/projects",
              headers=h, json={"projectId": PROJECT_ID, "name": "IBMS Enterprise"})
print(f"  Status: {resp.status_code}")
if resp.status_code == 200:
    op = resp.json()
    op_name = op.get("name", "")
    print(f"  Operation: {op_name}")
    # Poll until done
    for i in range(30):
        time.sleep(3)
        poll = c.get(f"https://cloudresourcemanager.googleapis.com/v1/{op_name}", headers=h)
        pdata = poll.json()
        if pdata.get("done"):
            if pdata.get("error"):
                print(f"  [FAIL] {pdata['error']}")
                sys.exit(1)
            print("  [OK] Project created!")
            break
    else:
        print("  [WARN] Timed out waiting but continuing...")
elif resp.status_code == 409:
    print("  Project already exists - continuing")
else:
    print(f"  [FAIL] {resp.text[:500]}")
    sys.exit(1)

# Step 2: Link billing
print("\nStep 2: Linking billing account...")
resp2 = c.put(f"https://cloudbilling.googleapis.com/v1/projects/{PROJECT_ID}/billingInfo",
              headers=h, json={"billingAccountName": BILLING_ACCOUNT})
print(f"  Status: {resp2.status_code}")
if resp2.status_code == 200:
    print("  [OK] Billing linked!")
else:
    print(f"  {resp2.text[:500]}")
    print("  [WARN] May need manual billing setup at https://console.cloud.google.com")

# Step 3: Enable essential APIs
print("\nStep 3: Enabling essential APIs...")
apis = [
    "serviceusage.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "cloudbilling.googleapis.com",
]
for api in apis:
    resp3 = c.post(
        f"https://serviceusage.googleapis.com/v1/projects/{PROJECT_ID}/services/{api}:enable",
        headers=h)
    if resp3.status_code == 200:
        print(f"  [OK] {api}")
    else:
        print(f"  [{resp3.status_code}] {api}: {resp3.text[:200]}")

print("\n=== Setup complete! Now run: python deploy/gcp/deploy_gcp.py ===")
