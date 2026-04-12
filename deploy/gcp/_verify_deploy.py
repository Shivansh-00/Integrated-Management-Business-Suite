"""Verify that the latest deploy is live with all code changes."""
import requests, time, json

BASE = "https://ibms-web-tivzf3l3ta-el.a.run.app"
s = requests.Session()

# 1. Health check
print("=== HEALTH ===")
r = s.get(f"{BASE}/api/health", timeout=30)
print(f"Status: {r.status_code}")
h = r.json()
print(f"Version: {h.get('version')}")
print(f"X-Process-Time: {r.headers.get('x-process-time', 'NOT PRESENT')}")
print()

# 2. Auth bench
print("=== AUTH BENCH ===")
r2 = s.get(f"{BASE}/api/debug/auth-bench", timeout=30)
print(f"Status: {r2.status_code}")
if r2.status_code == 200:
    print(json.dumps(r2.json(), indent=2))
else:
    print(f"Body: {r2.text[:500]}")
print()

# 3. Login test (warm connection)
print("=== LOGIN (warm) ===")
t0 = time.perf_counter()
r3 = s.post(f"{BASE}/api/auth/login",
            json={"username": "admin", "password": "Admin@IBMS2026"}, timeout=30)
t1 = time.perf_counter()
print(f"Login wall time: {t1-t0:.2f}s")
print(f"Status: {r3.status_code}")
print(f"X-Process-Time: {r3.headers.get('x-process-time', 'NOT PRESENT')}")
print(f"x-response-time-ms: {r3.headers.get('x-response-time-ms', 'NOT PRESENT')}")
if r3.status_code == 200:
    data = r3.json()
    print(f"Login success, user: {data.get('user',{}).get('username')}")
else:
    print(f"Body: {r3.text[:300]}")

# 4. Second login (everything should be hot now)
print()
print("=== LOGIN #2 (hot) ===")
t0 = time.perf_counter()
r4 = s.post(f"{BASE}/api/auth/login",
            json={"username": "admin", "password": "Admin@IBMS2026"}, timeout=30)
t1 = time.perf_counter()
print(f"Login wall time: {t1-t0:.2f}s")
print(f"X-Process-Time: {r4.headers.get('x-process-time', 'NOT PRESENT')}")
print(f"x-response-time-ms: {r4.headers.get('x-response-time-ms', 'NOT PRESENT')}")
