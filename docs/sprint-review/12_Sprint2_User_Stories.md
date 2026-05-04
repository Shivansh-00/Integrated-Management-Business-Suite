# Sprint 2 User Stories — IBMS (Integrated Business Management Suite)

| Field              | Detail                                              |
|--------------------|-----------------------------------------------------|
| **Project Name**   | Integrated Business Management Suite (IBMS) v2.0    |
| **Team**           | Shivansh Srivastava (Product Developer), Prahallad Padhan (Product Owner), Ranveer Rai Khare (Scrum Master) |
| **Sprint**         | Sprint 2                                            |
| **Sprint Duration**| 2 weeks (April 13 – April 24, 2026)                |
| **Date**           | April 13, 2026                                      |
| **Total Stories**  | 8                                                   |
| **Total Points**   | 52                                                  |
| **Course**         | SEPM (Software Engineering and Project Management)  |

---

## Sprint 2 Goal

> Extend IBMS with full ERP CRUD operations, enhance automated test coverage with integration and E2E tests, enforce authentication on all sensitive endpoints, introduce API versioning, and improve system resilience through performance monitoring baselines.

---

## US-S2-01: ERP Customer Management

**As a** sales manager,  
**I want to** create, view, update, and delete customer records through a structured API,  
**So that** the IBMS platform maintains a single source of truth for customer data.

**Priority**: Critical | **Story Points**: 8

### Acceptance Criteria / Checklist

- [ ] `POST /api/erp/customers` creates a new customer with name, email, phone, company, address
- [ ] `GET /api/erp/customers` returns a paginated list of all customers
- [ ] `GET /api/erp/customers/{id}` returns a single customer by ID; returns 404 if not found
- [ ] `PUT /api/erp/customers/{id}` updates any customer field; returns 200 with updated record
- [ ] `DELETE /api/erp/customers/{id}` deletes customer; returns 204; subsequent GET returns 404
- [ ] All customer endpoints require Bearer JWT authentication (401 if unauthenticated)
- [ ] Only `manager` role and above can create or update customers; `viewer` gets 403
- [ ] Customer email must be unique; duplicate email returns 409 Conflict
- [ ] All customer mutations are recorded in the audit log
- [ ] Frontend Customer Management page shows CRUD table with inline edit actions

---

## US-S2-02: ERP Product & Inventory Management

**As a** warehouse manager,  
**I want to** manage product records and track inventory movements,  
**So that** stock levels are always accurate and low-stock situations are proactively surfaced.

**Priority**: Critical | **Story Points**: 8

### Acceptance Criteria / Checklist

- [ ] `POST /api/erp/products` creates a product with name, SKU, category, unit price, quantity, reorder_threshold
- [ ] `GET /api/erp/products` returns paginated product list with stock levels
- [ ] `PUT /api/erp/products/{id}` updates product details; SKU must remain unique
- [ ] `DELETE /api/erp/products/{id}` removes product; cascades to inventory movement records
- [ ] `GET /api/erp/products/low-stock` returns all products where `quantity < reorder_threshold`
- [ ] `POST /api/erp/inventory/movement` records a stock movement (inbound/outbound) and updates product quantity atomically
- [ ] Stock cannot go below zero; negative stock update returns 422
- [ ] Low-stock alert is included in the WebSocket KPI push when stock falls below threshold
- [ ] All inventory mutations are logged in the audit trail
- [ ] Frontend Inventory page shows stock levels with colour indicator (red = low, green = ok)

---

## US-S2-03: ERP Order & Invoice Processing

**As a** finance team member,  
**I want to** create customer orders and generate invoices with automated compliance checks,  
**So that** the order-to-cash cycle is fully traceable and compliant.

**Priority**: Critical | **Story Points**: 8

### Acceptance Criteria / Checklist

- [ ] `POST /api/erp/orders` creates an order linked to a customer and one or more products; initial status: `pending`
- [ ] `PATCH /api/erp/orders/{id}/status` allows valid transitions: `pending → confirmed → shipped → delivered`; invalid transitions return 422
- [ ] `POST /api/erp/invoices` creates an invoice linked to an order; publishes an `anomaly_check` event asynchronously
- [ ] `POST /api/erp/payments` marks an invoice as `paid` and records the payment method and timestamp
- [ ] Invoices > ₹500,000 are automatically sent to compliance check engine; missing approval reference sets `compliance_hold: true`
- [ ] `GET /api/erp/orders?status=pending` filters orders by status
- [ ] Order and invoice endpoints require authentication; role `analyst` and above can view; `manager` and above can create
- [ ] All order and payment mutations are recorded in the audit log with user and timestamp
- [ ] Frontend Order Management page shows order lifecycle as a status-tag column

---

## US-S2-04: API Authentication Audit & Versioning

**As a** security engineer,  
**I want to** ensure all business-critical API endpoints require authentication and follow a consistent versioning scheme,  
**So that** the platform meets zero-trust security requirements and supports future API evolution without breaking changes.

**Priority**: High | **Story Points**: 5

### Acceptance Criteria / Checklist

- [ ] All `/api/risk/*`, `/api/fraud/*`, `/api/compliance/*`, `/api/budget/*`, `/api/pricing/*`, `/api/copilot/*`, `/api/forecast/*`, and `/api/erp/*` endpoints require Bearer JWT authentication
- [ ] Unauthenticated requests to any of the above return `401 Unauthorized` with a `WWW-Authenticate: Bearer` header
- [ ] All existing API routes are available under `/api/v1/` prefix; old paths redirect with `301 Moved Permanently`
- [ ] OpenAPI schema (`/docs`) reflects v1 prefix and updated security schemes
- [ ] API version is included in all response headers as `X-API-Version: 1`
- [ ] Authentication audit report documents every endpoint, its required role, and authentication status
- [ ] Automated test asserts that hitting a protected endpoint without a token returns 401

---

## US-S2-05: Integration & E2E Test Suite

**As a** QA engineer,  
**I want to** run automated integration and end-to-end tests that cover the full API surface and key user flows,  
**So that** regressions are detected automatically before deployment.

**Priority**: High | **Story Points**: 8

### Acceptance Criteria / Checklist

- [ ] pytest integration test suite covers all authentication flows: register, login, 2FA, refresh, logout
- [ ] Integration tests cover all ERP endpoints: customers, products, orders, invoices, inventory
- [ ] Integration tests cover risk scoring, fraud detection, compliance check, and budget optimization APIs
- [ ] Negative test cases assert correct 401/403/404/422 HTTP status codes for all error paths
- [ ] All tests run against a live test server with a dedicated test database (isolated from production)
- [ ] Test coverage report generated with `pytest --cov`; target ≥ 60% code coverage
- [ ] CI GitHub Actions workflow runs the full integration suite on every push to `main`
- [ ] E2E test script validates: (1) register → login → dashboard KPI → WebSocket heartbeat flow
- [ ] Test results are exported as JUnit XML for CI reporting

---

## US-S2-06: Performance Monitoring & Load Testing

**As a** DevOps engineer,  
**I want to** establish p50/p95/p99 latency baselines and run load tests against critical API endpoints,  
**So that** the team can quantify system capacity and proactively address performance bottlenecks.

**Priority**: Medium | **Story Points**: 5

### Acceptance Criteria / Checklist

- [ ] Locust or k6 load test script created targeting: `/api/dashboard`, `/api/risk/composite`, `/api/fraud/detect`
- [ ] Baseline test: 50 concurrent users, 60-second duration, target < 500ms p95 response time
- [ ] Stress test: ramp from 10 to 200 concurrent users; identify breaking point
- [ ] Load test results documented with p50/p95/p99 metrics and requests/sec throughput
- [ ] `/api/metrics` endpoint added returning: `uptime_seconds`, `total_requests`, `error_rate`, `avg_response_ms`, `active_ws_connections`
- [ ] Prometheus-compatible `/api/metrics/prometheus` endpoint added (optional, medium priority)
- [ ] Performance baseline report committed to `docs/performance_baseline.md`
- [ ] Any endpoint exceeding p95 > 500ms is flagged as a performance risk item

---

## US-S2-07: Environment Configuration & Security Hardening

**As a** developer,  
**I want to** have a properly documented environment setup with no hardcoded secrets and a dependency vulnerability scan in CI,  
**So that** the application is secure by default and new team members can onboard without manual guesswork.

**Priority**: High | **Story Points**: 5

### Acceptance Criteria / Checklist

- [ ] `.env.example` file created with all required environment variables, their types, and example/default values
- [ ] `JWT_SECRET` removed from any hardcoded defaults in `server.py`; startup fails with clear error if not set in env
- [ ] `pip-audit` added to CI pipeline; build fails if any HIGH or CRITICAL CVEs are found
- [ ] `SECURITY_OVERVIEW.md` updated with Sprint 2 security changes
- [ ] Database connection strings, API keys (Groq, Supabase, MongoDB URI) documented in `.env.example`
- [ ] Docker Compose updated to load all secrets from environment variables (no inline secrets)
- [ ] All hardcoded values replaced with `os.getenv()` calls with explicit startup validation

---

## US-S2-08: Agile Board & Sprint Tracking Documentation

**As a** Scrum Master,  
**I want to** maintain an updated Agile board with task movement evidence and a complete sprint tracking record,  
**So that** the team has transparency into sprint progress and stakeholders can see delivery status.

**Priority**: Medium | **Story Points**: 5

### Acceptance Criteria / Checklist

- [ ] MS Planner Agile board updated daily: tasks move from Backlog → In Progress → Done
- [ ] Sprint 2 backlog items created for all tasks derived from US-S2-01 to US-S2-07
- [ ] Agile board screenshot captured at: Sprint start (Day 1), Sprint midpoint (Day 7), Sprint end (Day 14)
- [ ] Screenshot evidence committed to `docs/agile_board_screenshots/`
- [ ] Daily standup notes recorded: what was done yesterday, what will be done today, any blockers
- [ ] Sprint burndown data: story points remaining per day tracked in a table
- [ ] Velocity comparison: Sprint 1 vs Sprint 2 documented

---

## Story Point Summary

| Story ID  | Title                                     | Priority | Points |
|-----------|-------------------------------------------|----------|--------|
| US-S2-01  | ERP Customer Management                   | Critical | 8      |
| US-S2-02  | ERP Product & Inventory Management        | Critical | 8      |
| US-S2-03  | ERP Order & Invoice Processing            | Critical | 8      |
| US-S2-04  | API Authentication Audit & Versioning     | High     | 5      |
| US-S2-05  | Integration & E2E Test Suite              | High     | 8      |
| US-S2-06  | Performance Monitoring & Load Testing     | Medium   | 5      |
| US-S2-07  | Environment Configuration & Security      | High     | 5      |
| US-S2-08  | Agile Board & Sprint Tracking             | Medium   | 5      |
|           | **Total**                                 |          | **52** |

---

*Sprint 2 User Stories — Version 1.0 | April 13, 2026*
