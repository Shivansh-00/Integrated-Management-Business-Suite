"""Quick endpoint smoke test."""
import json
import urllib.request

BASE = "http://localhost:8001"

def test(url, method="GET", data=None):
    try:
        req = urllib.request.Request(BASE + url, method=method)
        if data:
            req.data = json.dumps(data).encode()
            req.add_header("Content-Type", "application/json")
        r = urllib.request.urlopen(req)
        body = json.loads(r.read())
        print(f"OK {r.status} {url}")
        return body
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:300]
        print(f"ERR {e.code} {url}: {body}")
        return None

# Unauthenticated
test("/api/health")
test("/api/dashboard")
test("/api/system/status")
test("/api/ai/insights")
test("/api/ai/anomalies")
test("/api/endpoints")

# Auth flow
r = test("/api/auth/register", "POST", {"username": "testuser2", "email": "test2@test.com", "password": "TestPass123!"})
print("  Register:", json.dumps(r, indent=2)[:300] if r else "FAILED")

r = test("/api/auth/login", "POST", {"username": "testuser2", "password": "TestPass123!"})
print("  Login:", json.dumps(r, indent=2)[:300] if r else "FAILED")

if r and r.get("data", {}).get("access_token"):
    token = r["data"]["access_token"]
    # Test authenticated endpoints
    def auth_test(url, method="GET", data=None):
        try:
            req = urllib.request.Request(BASE + url, method=method)
            req.add_header("Authorization", f"Bearer {token}")
            if data:
                req.data = json.dumps(data).encode()
                req.add_header("Content-Type", "application/json")
            resp = urllib.request.urlopen(req)
            body = json.loads(resp.read())
            print(f"OK {resp.status} {url}")
            return body
        except urllib.error.HTTPError as e:
            body = e.read().decode()[:300]
            print(f"ERR {e.code} {url}: {body}")
            return None

    auth_test("/api/auth/me")
    auth_test("/api/auth/roles")
    auth_test("/api/erp/customers")
    auth_test("/api/erp/products")
    auth_test("/api/erp/orders")
    auth_test("/api/erp/invoices")
    auth_test("/api/erp/employees")
    auth_test("/api/erp/overview")
    auth_test("/api/notifications")
    
    # Test POST endpoints
    test("/api/forecast", "POST", {"company": "Default Company", "periods": 6})
    test("/api/risk/score", "POST", {"voucher_type": "Sales Invoice", "voucher_no": "INV-001", "amount": 50000})
    test("/api/fraud/detect", "POST", {"voucher_type": "Sales Invoice", "voucher_no": "INV-001", "amount": 50000})
    test("/api/compliance/check", "POST", {"amount": 50000})
    test("/api/pricing/suggest", "POST", {"base_price": 100, "demand_index": 0.5})
    test("/api/budget/optimize", "POST", {"lines": [{"name": "Marketing", "amount": 10000}], "growth_target": 0.1})
    test("/api/decision/evaluate", "POST", {"risk_score": 45, "threshold": 60})
    test("/api/leads/score", "POST", {"lead_name": "Test Lead", "engagement": 0.7, "fit": 0.8})
    test("/api/copilot/ask", "POST", {"question": "What is the current revenue?"})
    test("/api/risk/composite", "POST", {"amount": 50000, "behavior": 0.5, "compliance": 0.8})
    test("/api/twin/simulate", "POST", {"entity": {"type": "warehouse", "capacity": 1000}})

    print("\n--- ERP CRUD Tests ---")
    # Create a customer
    c = auth_test("/api/erp/customers", "POST", {"name": "Test Corp", "email": "corp@test.com", "segment": "enterprise"})
    if c and c.get("data"):
        cid = c["data"].get("customer_id", "")
        if cid:
            auth_test(f"/api/erp/customers/{cid}")
    
    # Create a product
    p = auth_test("/api/erp/products", "POST", {"name": "Test Widget", "sku": "TW-001", "unit_price": 99.99})
    if p and p.get("data"):
        pid = p["data"].get("product_id", "")
        if pid:
            auth_test(f"/api/erp/products/{pid}")

print("\n=== All tests complete ===")
