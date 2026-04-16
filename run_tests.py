"""Comprehensive endpoint test."""
import json
import urllib.request

BASE = "http://localhost:8001"

def test(method, path, data=None):
    try:
        req = urllib.request.Request(BASE + path, method=method)
        if data:
            req.data = json.dumps(data).encode()
            req.add_header("Content-Type", "application/json")
        r = urllib.request.urlopen(req)
        print(f"OK {r.status} {method:6} {path}")
    except Exception as e:
        code = getattr(e, "code", "ERR")
        print(f"FAIL {code} {method:6} {path}")

# Public GETs
for p in ["/api/health", "/api/dashboard", "/api/system/status", "/api/ai/insights"]:
    test("GET", p)

# ERP GETs
for p in [
    "/api/erp/customers", "/api/erp/customers/stats",
    "/api/erp/products", "/api/erp/products/stats", "/api/erp/products/low-stock",
    "/api/erp/orders", "/api/erp/orders/stats",
    "/api/erp/invoices", "/api/erp/invoices/stats",
    "/api/erp/employees", "/api/erp/employees/stats",
]:
    test("GET", p)

# POST endpoints
test("POST", "/api/forecast", {"periods": 6})
test("POST", "/api/compliance/check", {"voucher_type": "Sales Invoice", "amount": 1000, "party": "Test", "date": "2026-01-01"})
test("POST", "/api/risk/score", {"voucher_type": "Sales Invoice", "amount": 1000, "party": "Test", "date": "2026-01-01"})

# Frontend
test("GET", "/")

print("\nDone!")
