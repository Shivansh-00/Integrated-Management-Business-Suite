import requests, time

url_base = 'https://ibms-web-tivzf3l3ta-el.a.run.app'
s = requests.Session()

# Warm up TLS + container
print("Warming up...")
s.get(f'{url_base}/api/health', timeout=30)

for i in range(3):
    start = time.time()
    r = s.get(f'{url_base}/api/health', timeout=30)
    t1 = time.time() - start
    h_proc = r.headers.get('x-process-time', '?')
    
    start = time.time()
    r = s.post(f'{url_base}/api/auth/login',
        json={'username': 'admin', 'password': 'Admin@IBMS2026'}, timeout=30)
    t2 = time.time() - start
    l_proc = r.headers.get('x-process-time', '?')
    
    print(f'Run {i+1}: Health={t1:.2f}s(server:{h_proc}s)  Login={t2:.2f}s(server:{l_proc}s)  Net~{t2-float(l_proc) if l_proc!="?" else "?"}s')
