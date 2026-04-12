import requests, time, json
url = 'https://ibms-web-tivzf3l3ta-el.a.run.app/api/auth/login'
start = time.time()
r = requests.post(url, json={'username': 'admin', 'password': 'Admin@IBMS2026'}, timeout=30)
elapsed = time.time() - start
print(f'Status: {r.status_code}')
print(f'Time: {elapsed:.2f}s')
data = r.json()
if 'access_token' in data:
    print(f'Token: {data["access_token"][:30]}...')
else:
    print(f'Response: {json.dumps(data)[:200]}')
