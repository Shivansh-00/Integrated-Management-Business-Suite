"""Quick check: does ibms-enterprise exist and is billing linked?"""
import http.server, urllib.parse, secrets, hashlib, base64, webbrowser, sys
import httpx

CLIENT_ID = "764086051850-6qr4p6gpi6hn506pt8ejuq83di341hur.apps.googleusercontent.com"
CLIENT_SECRET = "d-FL95Q19q7MQmFpd7hHD0Ty"
REDIRECT_URI = "http://localhost:8088"
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

s = http.server.HTTPServer(("127.0.0.1", 8088), H)
s.timeout = 120
url = (f"https://accounts.google.com/o/oauth2/v2/auth?client_id={CLIENT_ID}"
       f"&redirect_uri={REDIRECT_URI}&response_type=code&scope={SCOPES}"
       f"&state={state}&code_challenge={code_challenge}"
       f"&code_challenge_method=S256&access_type=offline")
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
h = {"Authorization": f"Bearer {token}"}
c = httpx.Client(timeout=30)

# Check project
print("1. Project check:")
r1 = c.get("https://cloudresourcemanager.googleapis.com/v1/projects/ibms-enterprise", headers=h)
print(f"   Status: {r1.status_code}")
if r1.status_code == 200:
    d = r1.json()
    print(f"   Name: {d.get('name')}, State: {d.get('lifecycleState')}")
else:
    print(f"   {r1.text[:300]}")

# Check billing
print("2. Billing check:")
r2 = c.get("https://cloudbilling.googleapis.com/v1/projects/ibms-enterprise/billingInfo", headers=h)
print(f"   Status: {r2.status_code}")
if r2.status_code == 200:
    d = r2.json()
    print(f"   Enabled: {d.get('billingEnabled')}, Account: {d.get('billingAccountName')}")
else:
    print(f"   {r2.text[:300]}")

# If billing not linked, try to link it
if r2.status_code == 200 and not r2.json().get("billingEnabled"):
    print("3. Linking billing...")
    r3 = c.put(
        "https://cloudbilling.googleapis.com/v1/projects/ibms-enterprise/billingInfo",
        headers={**h, "Content-Type": "application/json"},
        json={"billingAccountName": "billingAccounts/016241-B8D40A-3102D2"})
    print(f"   Status: {r3.status_code}")
    print(f"   {r3.text[:300]}")
