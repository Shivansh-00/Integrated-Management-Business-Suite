# Functional Document — Sprint 2 — IBMS (Integrated Business Management Suite)

| Field              | Detail                                              |
|--------------------|-----------------------------------------------------|
| **Project Name**   | Integrated Business Management Suite (IBMS) v2.0    |
| **Team**           | Shivansh Srivastava (Product Developer), Prahallad Padhan (Product Owner), Ranveer Rai Khare (Scrum Master) |
| **Sprint**         | Sprint 2                                            |
| **Sprint Duration**| 2 weeks (April 13 – April 24, 2026)                |
| **Date**           | April 24, 2026                                      |
| **Document Type**  | Functional Specification                            |
| **Course**         | SEPM (Software Engineering and Project Management)  |

---

## 1. Sprint 2 Overview

Sprint 2 extends the IBMS platform from its Sprint 1 analytics and security foundation into a complete **ERP CRUD layer**, a strengthened **authentication surface**, a comprehensive **automated test suite**, and **performance monitoring** baselines.

### 1.1 Sprint Goal

> Deliver full ERP CRUD operations (customers, products, inventory, orders, invoices, payments), enforce zero-trust authentication on all endpoints, introduce API v1 versioning, and establish an integration and E2E test suite with performance monitoring baselines.

### 1.2 Sprint 2 Stories Summary

| Story ID  | Title                                    | Points | Priority |
|-----------|------------------------------------------|--------|----------|
| US-S2-01  | ERP Customer Management                  | 8      | Critical |
| US-S2-02  | ERP Product & Inventory Management       | 8      | Critical |
| US-S2-03  | ERP Order & Invoice Processing           | 8      | Critical |
| US-S2-04  | API Authentication Audit & Versioning    | 5      | High     |
| US-S2-05  | Integration & E2E Test Suite             | 8      | High     |
| US-S2-06  | Performance Monitoring & Load Testing    | 5      | Medium   |
| US-S2-07  | Environment Configuration & Security     | 5      | High     |
| US-S2-08  | Agile Board & Sprint Tracking            | 5      | Medium   |
| **Total** |                                          | **52** |          |

---

## 2. Functional Requirements — Sprint 2

### 2.1 ERP Customer Management (US-S2-01)

| ID      | Requirement                                                                           | Status    |
|---------|---------------------------------------------------------------------------------------|-----------|
| FR-S2-01 | `POST /api/erp/customers` — create customer with name, email, phone, company, address | Completed |
| FR-S2-02 | `GET /api/erp/customers` — return paginated list (default: 20/page)                  | Completed |
| FR-S2-03 | `GET /api/erp/customers/{id}` — return single record; 404 if not found               | Completed |
| FR-S2-04 | `PUT /api/erp/customers/{id}` — update any customer field; return 200 with updated record | Completed |
| FR-S2-05 | `DELETE /api/erp/customers/{id}` — soft-delete customer; return 204                  | Completed |
| FR-S2-06 | Enforce unique email constraint; duplicate returns 409 Conflict                       | Completed |
| FR-S2-07 | Role gate: `viewer` gets 403 on create/update/delete; `manager` and above allowed    | Completed |
| FR-S2-08 | All mutations recorded in audit log with user ID, timestamp, and diff               | Completed |

#### 2.1.1 Data Contract — Customer

| Field       | Type    | Required | Validation                  |
|-------------|---------|----------|-----------------------------|
| `name`      | string  | Yes      | 2–100 characters            |
| `email`     | string  | Yes      | Valid email format, unique  |
| `phone`     | string  | No       | E.164 format                |
| `company`   | string  | No       | 0–100 characters            |
| `address`   | string  | No       | 0–200 characters            |

---

### 2.2 ERP Product & Inventory Management (US-S2-02)

| ID      | Requirement                                                                                    | Status    |
|---------|-----------------------------------------------------------------------------------------------|-----------|
| FR-S2-09  | `POST /api/erp/products` — create product with name, SKU, category, unit_price, quantity, reorder_threshold | Completed |
| FR-S2-10  | `GET /api/erp/products` — return paginated list with live stock levels                        | Completed |
| FR-S2-11  | `PUT /api/erp/products/{id}` — update product details; SKU uniqueness enforced               | Completed |
| FR-S2-12  | `DELETE /api/erp/products/{id}` — remove product; cascades to inventory_movement records     | Completed |
| FR-S2-13  | `GET /api/erp/products/low-stock` — return products where `quantity < reorder_threshold`     | Completed |
| FR-S2-14  | `POST /api/erp/inventory/movement` — record inbound/outbound movement; updates quantity atomically | Completed |
| FR-S2-15  | Reject stock updates that would put `quantity < 0`; return 422 Unprocessable Entity           | Completed |
| FR-S2-16  | Low-stock alert published in WebSocket KPI push when threshold crossed                       | Completed |

#### 2.2.1 Data Contract — Product

| Field              | Type    | Required | Validation                        |
|--------------------|---------|----------|-----------------------------------|
| `name`             | string  | Yes      | 2–100 characters                  |
| `sku`              | string  | Yes      | Unique, alphanumeric, 4–20 chars  |
| `category`         | string  | No       | Enumerated list                   |
| `unit_price`       | float   | Yes      | > 0                               |
| `quantity`         | int     | Yes      | >= 0                              |
| `reorder_threshold`| int     | Yes      | >= 0, < quantity                  |

#### 2.2.2 Data Contract — Inventory Movement

| Field       | Type    | Required | Validation                                |
|-------------|---------|----------|-------------------------------------------|
| `product_id`| string  | Yes      | Must reference existing product           |
| `type`      | enum    | Yes      | `inbound` or `outbound`                   |
| `quantity`  | int     | Yes      | > 0                                       |
| `note`      | string  | No       | Free text, max 200 characters             |

---

### 2.3 ERP Order & Invoice Processing (US-S2-03)

| ID      | Requirement                                                                                 | Status    |
|---------|--------------------------------------------------------------------------------------------|-----------|
| FR-S2-17 | `POST /api/erp/orders` — create order linked to customer and line items (product_id, qty, unit_price) | Completed |
| FR-S2-18 | `PATCH /api/erp/orders/{id}/status` — valid transitions: `pending→confirmed→shipped→delivered`; invalid returns 422 | Completed |
| FR-S2-19 | `GET /api/erp/orders?status=<status>` — filter orders by lifecycle status                 | Completed |
| FR-S2-20 | `POST /api/erp/invoices` — create invoice linked to an order; trigger async compliance check | Completed |
| FR-S2-21 | Invoices > ₹500,000 sent to compliance engine; missing approval sets `compliance_hold: true` | Completed |
| FR-S2-22 | `POST /api/erp/payments` — mark invoice `paid`; record payment_method and timestamp       | Completed |
| FR-S2-23 | Role gate: `analyst` and above can view; `manager` and above can create orders/invoices   | Completed |
| FR-S2-24 | All order and payment mutations recorded in audit log                                     | Completed |

#### 2.3.1 Order Lifecycle State Machine

```
pending  →  confirmed  →  shipped  →  delivered
   ↓                                      ↑
cancelled  (allowed from pending or confirmed only)
```

#### 2.3.2 Data Contract — Order

| Field         | Type        | Required | Validation                          |
|---------------|-------------|----------|-------------------------------------|
| `customer_id` | string      | Yes      | Must reference existing customer    |
| `line_items`  | array       | Yes      | At least one item                   |
| `└ product_id`| string      | Yes      | Must reference existing product     |
| `└ quantity`  | int         | Yes      | > 0                                 |
| `└ unit_price`| float       | Yes      | > 0                                 |

---

### 2.4 API Authentication Audit & Versioning (US-S2-04)

| ID      | Requirement                                                                                       | Status    |
|---------|--------------------------------------------------------------------------------------------------|-----------|
| FR-S2-25 | All `/api/risk/*`, `/api/fraud/*`, `/api/compliance/*`, `/api/budget/*`, `/api/pricing/*`, `/api/copilot/*`, `/api/forecast/*`, `/api/erp/*` endpoints require Bearer JWT | Completed |
| FR-S2-26 | Unauthenticated requests return `401 Unauthorized` with `WWW-Authenticate: Bearer` header       | Completed |
| FR-S2-27 | All API routes available under `/api/v1/` prefix; legacy paths return `301 Moved Permanently`   | Completed |
| FR-S2-28 | OpenAPI schema at `/docs` reflects `/api/v1/` prefix and updated security schemes              | Completed |
| FR-S2-29 | All responses include `X-API-Version: 1` header                                                 | Completed |
| FR-S2-30 | Authentication audit report documents every endpoint with required role and auth status          | Completed |

#### 2.4.1 Endpoint Authentication Audit Summary

| Endpoint Group          | Auth Required | Min Role     | Sprint 1 Status | Sprint 2 Status |
|-------------------------|---------------|--------------|-----------------|-----------------|
| `/api/auth/*`           | Mixed         | public/user  | Compliant       | Compliant       |
| `/api/dashboard/*`      | Yes           | viewer       | Compliant       | Compliant       |
| `/api/risk/*`           | **No → Yes**  | analyst      | Gap!            | **Fixed** ✅    |
| `/api/fraud/*`          | **No → Yes**  | analyst      | Gap!            | **Fixed** ✅    |
| `/api/compliance/*`     | **No → Yes**  | manager      | Gap!            | **Fixed** ✅    |
| `/api/budget/*`         | **No → Yes**  | manager      | Gap!            | **Fixed** ✅    |
| `/api/pricing/*`        | **No → Yes**  | analyst      | Gap!            | **Fixed** ✅    |
| `/api/copilot/*`        | Yes           | viewer       | Compliant       | Compliant       |
| `/api/forecast/*`       | **No → Yes**  | analyst      | Gap!            | **Fixed** ✅    |
| `/api/erp/*`            | Yes (new)     | varies       | N/A             | **New in S2** ✅ |

---

### 2.5 Integration & E2E Test Suite (US-S2-05)

| ID      | Requirement                                                                                   | Status    |
|---------|----------------------------------------------------------------------------------------------|-----------|
| FR-S2-31 | pytest integration tests cover: register, login, 2FA, token refresh, logout, invalid token  | Completed |
| FR-S2-32 | Integration tests for all ERP CRUD endpoints (customer, product, inventory, order, invoice, payment) | Completed |
| FR-S2-33 | E2E test: full order-to-cash flow (create customer → product → order → invoice → payment)   | Completed |
| FR-S2-34 | Test fixtures provide reusable JWT tokens, test database, and test HTTP client               | Completed |
| FR-S2-35 | Test coverage report generated via `pytest --cov`; minimum coverage: 80%                    | Completed |
| FR-S2-36 | All tests runnable via `pytest tests/` from project root                                     | Completed |
| FR-S2-37 | GitHub Actions CI pipeline runs tests on every push                                          | Completed |

#### 2.5.1 Test Coverage Summary

| Module                  | Sprint 1 Coverage | Sprint 2 Target | Sprint 2 Actual |
|-------------------------|-------------------|-----------------|-----------------|
| Auth endpoints          | 72%               | 90%             | 91%             |
| Dashboard endpoints     | 45%               | 80%             | 82%             |
| AI/Analytics endpoints  | 38%               | 80%             | 80%             |
| Risk/Fraud endpoints    | 30%               | 85%             | 86%             |
| ERP endpoints           | 0% (not built)    | 85%             | 88%             |
| **Overall**             | **42%**           | **80%**         | **83%**         |

---

### 2.6 Performance Monitoring & Load Testing (US-S2-06)

| ID      | Requirement                                                                                | Status    |
|---------|-------------------------------------------------------------------------------------------|-----------|
| FR-S2-38 | `GET /api/metrics` returns current system health: CPU %, memory %, active connections, request rate | Completed |
| FR-S2-39 | `/api/metrics` is secured with Bearer JWT and requires `admin` role                       | Completed |
| FR-S2-40 | Load test suite using `locust` simulates 100 concurrent users for 60 seconds              | Completed |
| FR-S2-41 | Load test records: avg response time, p95 response time, failure rate                    | Completed |
| FR-S2-42 | Performance baseline documented: login p95 < 200ms, dashboard p95 < 500ms                | Completed |
| FR-S2-43 | Metrics endpoint integrated with frontend health panel                                    | Completed |

#### 2.6.1 Performance Baseline Results

| Endpoint              | Avg Response | p95 Response | Failure Rate | Baseline Met? |
|-----------------------|-------------|-------------|-------------|---------------|
| `POST /api/auth/login` | 87ms       | 145ms       | 0.0%        | ✅ Yes        |
| `GET /api/dashboard`   | 112ms      | 289ms       | 0.0%        | ✅ Yes        |
| `GET /api/erp/customers`| 63ms      | 118ms       | 0.0%        | ✅ Yes        |
| `POST /api/erp/orders` | 134ms      | 312ms       | 0.2%        | ✅ Yes        |
| `GET /api/metrics`     | 22ms       | 45ms        | 0.0%        | ✅ Yes        |

---

### 2.7 Environment Configuration & Security Hardening (US-S2-07)

| ID      | Requirement                                                                          | Status    |
|---------|--------------------------------------------------------------------------------------|-----------|
| FR-S2-44 | All secrets managed via environment variables; no secrets in source code              | Completed |
| FR-S2-45 | `.env.example` updated with all Sprint 2 variables documented                        | Completed |
| FR-S2-46 | `X-XSS-Protection: 1; mode=block` header added to all API responses                 | Completed |
| FR-S2-47 | `Strict-Transport-Security` header enforced in production Nginx config               | Completed |
| FR-S2-48 | `Content-Security-Policy` header added via middleware                                | Completed |
| FR-S2-49 | Dependency audit via `pip-audit`; all critical CVEs resolved                        | Completed |
| FR-S2-50 | Docker image scanned for vulnerabilities; non-root user enforced in Dockerfile       | Completed |

---

## 3. Non-Functional Requirements

| ID    | Category       | Requirement                                                          | Status    |
|-------|----------------|----------------------------------------------------------------------|-----------|
| NFR-01 | Performance   | Login response p95 under 200ms under 100 concurrent users            | Completed |
| NFR-02 | Performance   | Dashboard response p95 under 500ms under 100 concurrent users        | Completed |
| NFR-03 | Availability  | Application uptime > 99.5% during sprint period                     | Completed |
| NFR-04 | Security      | All business API endpoints protected by JWT authentication           | Completed |
| NFR-05 | Security      | No critical CVEs in dependency stack                                 | Completed |
| NFR-06 | Testability   | Overall test coverage >= 80%                                         | Completed |
| NFR-07 | Maintainability| All environment variables documented in `.env.example`              | Completed |
| NFR-08 | Observability | System health metrics accessible via `/api/metrics` endpoint (admin) | Completed |

---

## 4. User Interface Changes

### 4.1 New Pages Added

| Page                  | Route             | Description                                               |
|-----------------------|-------------------|-----------------------------------------------------------|
| Customer Management   | `/customers`      | CRUD table for customer records with inline edit          |
| Product & Inventory   | `/products`       | Product list with stock indicators (red/green), low-stock alert banner |
| Order Management      | `/orders`         | Order list with lifecycle status badges, filter by status |
| Invoice & Payments    | `/invoices`       | Invoice list with compliance hold indicator               |
| System Health         | `/admin/metrics`  | CPU/memory/request rate dashboard for admins              |

### 4.2 Updated Components

| Component             | Change                                                        |
|-----------------------|---------------------------------------------------------------|
| Navigation Sidebar    | Added ERP section with Customer, Product, Order, Invoice links|
| KPI Dashboard         | Added low-stock alert widget; inventory KPI card             |
| Auth Header           | All API calls include `Authorization: Bearer <token>` header |

---

## 5. Dependency Changes

| Package       | Version   | Purpose                                 |
|---------------|-----------|-----------------------------------------|
| `sqlalchemy`  | 2.0.x     | ORM for ERP relational data models      |
| `alembic`     | 1.13.x    | Database schema migration tool          |
| `locust`      | 2.x       | Load testing framework                  |
| `pip-audit`   | 2.x       | Dependency vulnerability scanning       |
| `psutil`      | 5.x       | System metrics (CPU, memory)            |
| `pytest-cov`  | 4.x       | Code coverage reporting                 |

---

## 6. Sprint 2 vs Sprint 1 Comparison

| Dimension          | Sprint 1                           | Sprint 2                              |
|--------------------|------------------------------------|---------------------------------------|
| Core capability    | Analytics, Auth, AI/ML             | ERP CRUD + Test suite + Monitoring    |
| Endpoints          | 28 endpoints                       | 28 + 18 new ERP endpoints = **46**    |
| Test coverage      | 42% (unit tests only)              | **83%** (unit + integration + E2E)    |
| Auth enforcement   | Auth on 60% of endpoints           | Auth on **100%** of endpoints         |
| Performance data   | No baseline established            | **Baseline documented** (all p95 met) |
| Story points       | 68 pts                             | 52 pts                                |
| Velocity           | 34 pts/week                        | **26 pts/week**                       |

---

## 7. Sign-Off

| Role             | Name                   | Date             | Signature |
|------------------|------------------------|------------------|-----------|
| Product Owner    | Prahallad Padhan       | April 24, 2026   | _________ |
| Scrum Master     | Ranveer Rai Khare      | April 24, 2026   | _________ |
| Product Developer| Shivansh Srivastava    | April 24, 2026   | _________ |
