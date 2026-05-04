# Committed vs Completed — Sprint 2 — IBMS (Integrated Business Management Suite)

| Field              | Detail                                              |
|--------------------|-----------------------------------------------------|
| **Project Name**   | Integrated Business Management Suite (IBMS) v2.0    |
| **Team**           | Shivansh Srivastava (Product Developer), Prahallad Padhan (Product Owner), Ranveer Rai Khare (Scrum Master) |
| **Sprint**         | Sprint 2                                            |
| **Sprint Duration**| April 13 – April 24, 2026 (10 working days)        |
| **Date**           | April 24, 2026                                      |
| **Document Type**  | Committed vs Completed Analysis                     |
| **Course**         | SEPM (Software Engineering and Project Management)  |

---

## 1. Sprint 2 Commitment Summary

| Metric                  | Value    |
|-------------------------|----------|
| Stories Committed       | 8        |
| Story Points Committed  | 52       |
| Stories Completed       | 8        |
| Story Points Completed  | 52       |
| **Completion Rate**     | **100%** |
| Bugs Found              | 3        |
| Bugs Fixed Within Sprint| 3        |
| Sprint Velocity         | 26 pts/week |

---

## 2. Story-Level Committed vs Completed

| Story ID  | Title                                    | Points Committed | Points Completed | Status      | Notes |
|-----------|------------------------------------------|-----------------|-----------------|-------------|-------|
| US-S2-01  | ERP Customer Management                  | 8               | 8               | ✅ Done     | All 5 CRUD endpoints built and tested; audit log confirmed |
| US-S2-02  | ERP Product & Inventory Management       | 8               | 8               | ✅ Done     | BUG-005 found and fixed; low-stock alert in WebSocket push |
| US-S2-03  | ERP Order & Invoice Processing           | 8               | 8               | ✅ Done     | BUG-006 found and fixed; compliance check triggers correctly |
| US-S2-04  | API Authentication Audit & Versioning    | 5               | 5               | ✅ Done     | All 7 endpoint groups secured; `/api/v1/` prefix active |
| US-S2-05  | Integration & E2E Test Suite             | 8               | 8               | ✅ Done     | 83% coverage achieved; CI pipeline live on GitHub Actions |
| US-S2-06  | Performance Monitoring & Load Testing    | 5               | 5               | ✅ Done     | All p95 baselines met; `/api/v1/metrics` secured |
| US-S2-07  | Environment Config & Security Hardening  | 5               | 5               | ✅ Done     | BUG-007 found and fixed; 7 security headers active |
| US-S2-08  | Agile Board & Sprint Tracking            | 5               | 5               | ✅ Done     | Sprint board maintained daily; all tasks moved to Done column |
| **Total** |                                          | **52**          | **52**          | **100% ✅** | |

---

## 3. Feature-Level Breakdown

### US-S2-01: ERP Customer Management (8 pts)

| Feature                                    | Committed | Completed | Evidence |
|--------------------------------------------|-----------|-----------|---------|
| `POST /api/v1/erp/customers`               | ✅        | ✅        | TC-ERP-C-001 PASS |
| `GET /api/v1/erp/customers` (paginated)    | ✅        | ✅        | Integration test PASS |
| `GET /api/v1/erp/customers/{id}`           | ✅        | ✅        | TC-ERP-C-004 PASS |
| `PUT /api/v1/erp/customers/{id}`           | ✅        | ✅        | Integration test PASS |
| `DELETE /api/v1/erp/customers/{id}`        | ✅        | ✅        | TC-ERP-C-005 PASS |
| Unique email constraint (409)              | ✅        | ✅        | TC-ERP-C-002 PASS |
| Viewer role blocked (403)                  | ✅        | ✅        | TC-ERP-C-003 PASS |
| Audit log for all mutations                | ✅        | ✅        | Audit log entries verified |
| Frontend Customer Management page         | ✅        | ✅        | UI rendered at `/customers` |

---

### US-S2-02: ERP Product & Inventory Management (8 pts)

| Feature                                    | Committed | Completed | Evidence |
|--------------------------------------------|-----------|-----------|---------|
| `POST /api/v1/erp/products`                | ✅        | ✅        | TC-ERP-P-001 PASS |
| `GET /api/v1/erp/products` (paginated)     | ✅        | ✅        | Integration test PASS |
| `PUT /api/v1/erp/products/{id}`            | ✅        | ✅        | Integration test PASS |
| `DELETE /api/v1/erp/products/{id}`         | ✅        | ✅        | Integration test PASS |
| `GET /api/v1/erp/products/low-stock`       | ✅        | ✅        | TC-ERP-P-002 PASS |
| `POST /api/v1/erp/inventory/movement`      | ✅        | ✅        | TC-ERP-P-004 PASS |
| Negative stock rejection (422)             | ✅        | ✅        | TC-ERP-P-003 PASS (after BUG-005 fix) |
| Low-stock WebSocket alert                  | ✅        | ✅        | Alert appears in WS push payload |
| Frontend inventory page with indicators   | ✅        | ✅        | UI rendered at `/products` |

---

### US-S2-03: ERP Order & Invoice Processing (8 pts)

| Feature                                     | Committed | Completed | Evidence |
|---------------------------------------------|-----------|-----------|---------|
| `POST /api/v1/erp/orders`                   | ✅        | ✅        | TC-ERP-O-001 PASS |
| Order status transitions                    | ✅        | ✅        | TC-ERP-O-002, TC-ERP-O-003 PASS |
| `GET /api/v1/erp/orders?status=` filter     | ✅        | ✅        | Integration test PASS |
| `POST /api/v1/erp/invoices`                 | ✅        | ✅        | TC-ERP-I-001 PASS (after BUG-006 fix) |
| Compliance check for invoices > ₹500k      | ✅        | ✅        | Triggered correctly after fix |
| `POST /api/v1/erp/payments`                 | ✅        | ✅        | E2E test PASS |
| Role gate (analyst view, manager create)    | ✅        | ✅        | Integration test PASS |
| Audit log for all mutations                 | ✅        | ✅        | Audit entries verified |
| E2E order-to-cash flow                      | ✅        | ✅        | TC-ERP-E2E-001 PASS |
| Frontend Order Management page              | ✅        | ✅        | UI rendered at `/orders` |

---

### US-S2-04: API Authentication Audit & Versioning (5 pts)

| Feature                                    | Committed | Completed | Evidence |
|--------------------------------------------|-----------|-----------|---------|
| `/api/v1/` prefix on all routes            | ✅        | ✅        | TC-AUTH-014 PASS |
| Legacy `/api/*` redirect 301               | ✅        | ✅        | Redirect tested and confirmed |
| `X-API-Version: 1` response header        | ✅        | ✅        | TC-AUTH-015 PASS |
| Auth on `/api/risk/*`                      | ✅        | ✅        | TC-AUTH-011 variant PASS |
| Auth on `/api/fraud/*`                     | ✅        | ✅        | TC-AUTH-012 PASS |
| Auth on `/api/compliance/*`                | ✅        | ✅        | TC-AUTH-013 PASS |
| Auth on `/api/budget/*`                    | ✅        | ✅        | Integration test PASS |
| Auth on `/api/pricing/*`                   | ✅        | ✅        | Integration test PASS |
| Auth on `/api/forecast/*`                  | ✅        | ✅        | Integration test PASS |
| Authentication audit report documented    | ✅        | ✅        | Endpoint audit table in Functional Doc |
| OpenAPI `/docs` updated                    | ✅        | ✅        | Verified at `/docs` |

---

### US-S2-05: Integration & E2E Test Suite (8 pts)

| Feature                                      | Committed | Completed | Evidence |
|----------------------------------------------|-----------|-----------|---------|
| Auth flow integration tests                  | ✅        | ✅        | 12 auth test cases PASS |
| ERP CRUD integration tests                   | ✅        | ✅        | 18 ERP test cases PASS |
| E2E order-to-cash scenario                   | ✅        | ✅        | TC-ERP-E2E-001 PASS |
| Reusable test fixtures (JWT, DB, client)      | ✅        | ✅        | `conftest.py` updated |
| `pytest --cov` >= 80% coverage               | ✅        | ✅        | 83% achieved |
| `pytest tests/` runs from project root       | ✅        | ✅        | Verified locally |
| GitHub Actions CI pipeline                   | ✅        | ✅        | `.github/workflows/ci.yml` committed |

---

### US-S2-06: Performance Monitoring & Load Testing (5 pts)

| Feature                                    | Committed | Completed | Evidence |
|--------------------------------------------|-----------|-----------|---------|
| `GET /api/v1/metrics` endpoint             | ✅        | ✅        | TC-PERF-001 PASS |
| Metrics secured (admin role only)          | ✅        | ✅        | TC-PERF-002 PASS |
| Locust load test suite                     | ✅        | ✅        | `tests/load_test.py` created |
| Login p95 < 200ms                          | ✅        | ✅        | TC-PERF-003: 145ms |
| Dashboard p95 < 500ms                      | ✅        | ✅        | TC-PERF-004: 289ms |
| Performance baseline documented            | ✅        | ✅        | Table in Functional Doc §2.6.1 |

---

### US-S2-07: Environment Configuration & Security Hardening (5 pts)

| Feature                                    | Committed | Completed | Evidence |
|--------------------------------------------|-----------|-----------|---------|
| All secrets in environment variables       | ✅        | ✅        | No secrets in source code (pip-audit confirms) |
| `.env.example` updated                     | ✅        | ✅        | All Sprint 2 vars documented |
| `X-XSS-Protection` header                  | ✅        | ✅        | TC-SEC-001 PASS (after BUG-007 fix) |
| HSTS header in Nginx                       | ✅        | ✅        | TC-SEC-002 PASS |
| Content-Security-Policy header             | ✅        | ✅        | TC-SEC-003 PASS |
| `pip-audit` clean                          | ✅        | ✅        | 0 critical CVEs |
| Dockerfile non-root user                   | ✅        | ✅        | `USER appuser` in Dockerfile |

---

### US-S2-08: Agile Board & Sprint Tracking (5 pts)

| Feature                                    | Committed | Completed | Evidence |
|--------------------------------------------|-----------|-----------|---------|
| Sprint board tasks created at sprint start | ✅        | ✅        | Board updated April 13 |
| Daily task movement tracked               | ✅        | ✅        | Board updated daily |
| All tasks in Done column at sprint end    | ✅        | ✅        | Board screenshot taken April 24 |
| Sprint burndown chart updated weekly      | ✅        | ✅        | Burndown reflects actual progress |
| Sprint 2 documents committed to repo      | ✅        | ✅        | This document set |

---

## 4. Sprint Velocity Comparison

| Sprint   | Story Points Committed | Story Points Completed | Completion Rate | Velocity (pts/week) |
|----------|----------------------|----------------------|-----------------|---------------------|
| Sprint 1 | 68                   | 68                   | 100%            | 34 pts/week         |
| Sprint 2 | 52                   | 52                   | 100%            | 26 pts/week         |

**Velocity note:** Sprint 2 velocity (26 pts/week) decreased from Sprint 1 (34 pts/week) primarily because Sprint 2 stories had higher quality overhead — integration tests, bug fixes (3 bugs), security hardening, and CI pipeline setup were all part of the story definition of done. The reduced velocity reflects a deliberate investment in **quality and testing**, which raised code coverage from 42% to 83%.

---

## 5. Sprint Burndown

| Day | Remaining Points (Ideal) | Remaining Points (Actual) |
|-----|--------------------------|--------------------------|
| Day 0  (Apr 13) | 52 | 52 |
| Day 2  (Apr 15) | 41.6 | 36 |
| Day 4  (Apr 17) | 31.2 | 24 |
| Day 6  (Apr 19) | 20.8 | 20 |
| Day 8  (Apr 21) | 10.4 | 8  |
| Day 10 (Apr 24) | 0   | 0  |

**Interpretation:** The team moved slightly ahead of the ideal burndown line in Weeks 1 (ERP stories completed faster than estimated) and finished at exactly 0 remaining points on the final day. The slight dip on Days 6–8 was caused by three bugs discovered during integration testing that required investigation and fixes.

---

## 6. Definition of Done Compliance

Each story was considered **Done** when all of the following criteria were met:

| Criterion                                           | Met for All Stories? |
|-----------------------------------------------------|----------------------|
| All acceptance criteria checked off                 | ✅ Yes               |
| Unit/integration tests written and passing          | ✅ Yes               |
| Code reviewed (self-review in solo team)            | ✅ Yes               |
| Test coverage contribution >= 80% for new code      | ✅ Yes               |
| No critical bugs outstanding                        | ✅ Yes (3 fixed)     |
| API documentation updated (OpenAPI spec)            | ✅ Yes               |
| Security headers validated                          | ✅ Yes               |
| Committed to main branch                            | ✅ Yes               |

---

## 7. Unplanned Work

| Item                                       | Time Spent | Impact |
|--------------------------------------------|------------|--------|
| BUG-005: Negative stock not rejected       | ~2 hours   | Delayed inventory integration tests by 0.5 days |
| BUG-006: Invoice compliance check bypass  | ~3 hours   | Delayed invoice story sign-off by 1 day |
| BUG-007: Security headers on error responses | ~1.5 hours | Minimal impact |
| **Total unplanned work**                   | **~6.5 hours** | Absorbed within sprint capacity |

---

## 8. Sign-Off

| Role             | Name                   | Date             | Signature |
|------------------|------------------------|------------------|-----------|
| Product Owner    | Prahallad Padhan       | April 24, 2026   | _________ |
| Scrum Master     | Ranveer Rai Khare      | April 24, 2026   | _________ |
| Product Developer| Shivansh Srivastava    | April 24, 2026   | _________ |
