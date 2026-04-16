"""Reset Cloud SQL ibms_user password to match quick_redeploy.py."""
import requests, secrets, hashlib, base64, webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlencode, urlparse, parse_qs
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

PROJECT_ID = "total-handler-463313-e2"
SQL_INSTANCE = "ibms-mysql"
NEW_PASSWORD = "ibms_secure_pw_2025"

CLIENT_ID = "764086051850-6qr4p6gpi6hn506pt8ejuq83di341hur.apps.googleusercontent.com"
CLIENT_SECRET = "d-FL95Q19q7MQmFpd7hHD0Ty"
REDIRECT_URI = "http://localhost:8086"

session = requests.Session()
retry = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
session.mount("https://", HTTPAdapter(max_retries=retry))

code_verifier = secrets.token_urlsafe(64)
digest = hashlib.sha256(code_verifier.encode()).digest()
code_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
auth_code = None

class H(BaseHTTPRequestHandler):
    def do_GET(self):
        global auth_code
        qs = parse_qs(urlparse(self.path).query)
        auth_code = qs.get("code", [None])[0]
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(b"<h2>OK - return to terminal</h2>")
    def log_message(self, *a):
        pass

url = "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode({
    "client_id": CLIENT_ID,
    "redirect_uri": REDIRECT_URI,
    "response_type": "code",
    "scope": "https://www.googleapis.com/auth/cloud-platform",
    "state": secrets.token_urlsafe(16),
    "code_challenge": code_challenge,
    "code_challenge_method": "S256",
    "access_type": "offline",
})
print("[Auth] Opening browser...")
webbrowser.open(url)
srv = HTTPServer(("127.0.0.1", 8086), H)
srv.handle_request()
srv.server_close()

resp = session.post("https://oauth2.googleapis.com/token", data={
    "client_id": CLIENT_ID,
    "client_secret": CLIENT_SECRET,
    "code": auth_code,
    "redirect_uri": REDIRECT_URI,
    "grant_type": "authorization_code",
    "code_verifier": code_verifier,
})
token = resp.json()["access_token"]
print("[Auth] OK")

headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# Update ibms_user password
print("[SQL] Updating ibms_user password...")
r = session.put(
    f"https://sqladmin.googleapis.com/v1/projects/{PROJECT_ID}/instances/{SQL_INSTANCE}/users",
    headers=headers,
    params={"name": "ibms_user"},
    json={"password": NEW_PASSWORD},
    timeout=30,
)
print(f"  Status: {r.status_code}")
print(f"  Response: {r.text[:300]}")

# Also update root password
print("[SQL] Updating root password...")
r2 = session.put(
    f"https://sqladmin.googleapis.com/v1/projects/{PROJECT_ID}/instances/{SQL_INSTANCE}/users",
    headers=headers,
    params={"name": "root", "host": "%"},
    json={"password": NEW_PASSWORD},
    timeout=30,
)
print(f"  Status: {r2.status_code}")
print("Done!")
