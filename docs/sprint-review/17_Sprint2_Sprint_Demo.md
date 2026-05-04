# Sprint Demo — Sprint 2 — IBMS (Integrated Business Management Suite)

| Field              | Detail                                              |
|--------------------|-----------------------------------------------------|
| **Project Name**   | Integrated Business Management Suite (IBMS) v2.0    |
| **Team**           | Shivansh Srivastava (Product Developer), Prahallad Padhan (Product Owner), Ranveer Rai Khare (Scrum Master) |
| **Sprint**         | Sprint 2                                            |
| **Demo Date**      | April 24, 2026                                      |
| **Sprint Duration**| April 13 – April 24, 2026                          |
| **Audience**       | Product Owner, Scrum Master, Course Instructor      |
| **Format**         | Live demo + brief walkthrough of key features       |
| **Course**         | SEPM (Software Engineering and Project Management)  |

---

## 1. Demo Agenda

| # | Section                            | Presenter            | Duration |
|---|------------------------------------|----------------------|----------|
| 1 | Sprint 2 Goal & Commitment Recap   | Scrum Master         | 2 min    |
| 2 | ERP Module Demo (Customer / Product / Order) | Product Developer | 8 min |
| 3 | Authentication Audit & API Versioning | Product Developer | 3 min |
| 4 | Test Suite & Coverage Results      | Product Developer    | 3 min    |
| 5 | Performance Metrics Demo           | Product Developer    | 2 min    |
| 6 | Committed vs Completed Summary     | Product Owner        | 2 min    |
| 7 | Q&A / Feedback                     | All                  | 5 min    |
| **Total** |                             |                      | **~25 min** |

---

## 2. Sprint 2 Goal Recap

> **Sprint Goal:** Deliver full ERP CRUD operations (customers, products, inventory, orders, invoices, payments), enforce zero-trust authentication on all endpoints, introduce `/api/v1/` versioning, and establish an integration and E2E test suite with documented performance baselines.

| Metric                  | Result   |
|-------------------------|----------|
| Stories committed       | 8        |
| Stories completed       | **8 (100%)** |
| Points committed        | 52       |
| Points completed        | **52 (100%)** |
| Bugs found              | 3        |
| Bugs fixed              | **3 (100%)** |
| Test coverage           | **83%** (was 42%) |

---

## 3. Feature Demo Script

### 3.1 Demo 1: ERP Customer Management

**Talking Points:**
> "Sprint 2 introduces a full ERP layer to IBMS, starting with customer management. We now have a complete CRUD API for customers, backed by a relational database, with full authentication and role-based access control."

**Demo Steps:**

1. Open browser at `/customers`
   - Show the Customer Management UI: clean table with columns for Name, Email, Company, Actions

2. Demonstrate Create Customer:
   - Click **+ New Customer**
   - Fill: Name = `TechVision Pvt Ltd`, Email = `contact@techvision.in`, Company = `TechVision`, Phone = `+912231456789`
   - Save → row appears in table

3. Demonstrate Duplicate Email Restriction:
   - Attempt to create second customer with same email
   - Show `409 Conflict` error message — "Email already registered"

4. Demonstrate Role Gate (Viewer):
   - Switch to viewer token in terminal: `curl -X POST /api/v1/erp/customers -H "Authorization: Bearer <viewer_token>"`
   - Show `403 Forbidden` response

5. Demonstrate Delete:
   - Delete TechVision from the UI
   - Table refreshes; customer gone

---

### 3.2 Demo 2: ERP Product & Inventory Management

**Talking Points:**
> "The inventory module tracks stock levels in real time. Managers can record inbound and outbound movements, and the system proactively alerts when stock falls below the reorder threshold — even pushing the alert through the live WebSocket connection to the KPI dashboard."

**Demo Steps:**

1. Open `/products`
   - Show Product table with stock indicator column (green = ok, red = low stock)

2. Create Product:
   - Name = `Industrial Widget`, SKU = `IND-WDG-042`, Unit Price = `₹1,250`, Quantity = `8`, Reorder Threshold = `10`
   - Save → Stock indicator immediately shows **red** (8 < 10)

3. Show Low-Stock Alert in Dashboard:
   - Switch to KPI Dashboard
   - Show the new inventory alert widget: "Industrial Widget (IND-WDG-042) — 8 units remaining (threshold: 10)"

4. Record Inbound Movement:
   - POST inventory movement: inbound, 50 units
   - Product quantity updates to 58; indicator turns **green**

5. Attempt Negative Stock:
   - Try outbound movement of 100 units on a product with only 58
   - Show `422 Unprocessable Entity` — "Insufficient stock for this outbound movement"

---

### 3.3 Demo 3: ERP Order & Invoice Processing

**Talking Points:**
> "The order-to-cash flow is now fully digital and traceable within IBMS. Every step from order creation to invoice generation to payment is tracked, with automatic compliance checking for high-value invoices."

**Demo Steps:**

1. Create Order:
   - Customer: TechVision Pvt Ltd
   - Add line item: Industrial Widget × 5 @ ₹1,250
   - Total: ₹6,250 shown automatically
   - Status: `pending`

2. Advance Order Status:
   - Click **Confirm** → status changes to `confirmed`
   - Click **Ship** → status changes to `shipped`
   - Show that jumping directly to `delivered` is blocked (422 if attempted via API)

3. Create Invoice:
   - Generate invoice for the order: ₹6,250
   - No compliance hold (below ₹500k threshold)
   
4. Demo High-Value Invoice (Compliance Hold):
   - Use prepared order with amount ₹750,000
   - Create invoice without approval reference
   - Show `compliance_hold: true` in response

5. Record Payment:
   - Mark invoice as paid: payment_method = `bank_transfer`
   - Invoice status updates to `paid`

---

### 3.4 Demo 4: Authentication Audit & API Versioning

**Talking Points:**
> "One of Sprint 1's retrospective findings was that several API endpoints were unprotected. In Sprint 2, we audited every single endpoint and enforced authentication on 100% of business-critical API routes. We also introduced `/api/v1/` versioning to future-proof the API."

**Demo Steps:**

1. Show Endpoint Audit Table (from Functional Document):
   - Point to the table showing Sprint 1 gaps (risk, fraud, compliance, budget, pricing, forecast)
   - Show Sprint 2 column: all **Fixed ✅**

2. Live Demo — Unauthenticated Request:
   ```bash
   curl -X POST https://ibms-api/api/v1/risk/score \
     -H "Content-Type: application/json" \
     -d '{"amount": 50000}'
   ```
   Response: `401 Unauthorized` + `WWW-Authenticate: Bearer`

3. Show API Versioning:
   ```bash
   # New versioned route works
   curl -H "Authorization: Bearer <token>" \
     https://ibms-api/api/v1/dashboard/kpis
   # Response header: X-API-Version: 1
   
   # Legacy route redirects
   curl -v https://ibms-api/api/dashboard/kpis
   # HTTP 301 → Location: /api/v1/dashboard/kpis
   ```

4. Show OpenAPI schema at `/docs` — confirm v1 prefix visible in all routes

---

### 3.5 Demo 5: Test Suite & Coverage Results

**Talking Points:**
> "Sprint 1's retrospective identified low test coverage as a key risk. Sprint 2 addressed this head-on — we went from 42% to 83% coverage, added a complete integration test suite, an end-to-end order-to-cash scenario test, and a GitHub Actions CI pipeline that runs on every push."

**Demo Steps:**

1. Run the test suite live:
   ```bash
   pytest tests/ --cov=. --cov-report=term-missing -v
   ```
   - Show tests running: auth, ERP, integration, E2E
   - Final output: `83 tests passed`, coverage report

2. Show GitHub Actions CI badge (if projected):
   - CI pipeline: lint → test → security scan → Docker build

3. Show coverage by module:
   | Module             | Coverage |
   |--------------------|---------|
   | Auth endpoints     | 91%     |
   | ERP endpoints      | 88%     |
   | Risk/Fraud         | 86%     |
   | Dashboard          | 82%     |
   | AI/Analytics       | 80%     |
   | **Overall**        | **83%** |

---

### 3.6 Demo 6: Performance Metrics

**Talking Points:**
> "We added a secured `/api/v1/metrics` endpoint that exposes real-time system health. We also ran load tests with 100 concurrent users and documented performance baselines — all endpoints met their targets."

**Demo Steps:**

1. Hit the metrics endpoint:
   ```bash
   curl -H "Authorization: Bearer <admin_token>" \
     https://ibms-api/api/v1/metrics
   ```
   Show response:
   ```json
   {
     "cpu_percent": 12.4,
     "memory_percent": 48.2,
     "active_connections": 3,
     "requests_per_second": 14.2,
     "uptime_seconds": 86400
   }
   ```

2. Show Load Test Results table:
   | Endpoint           | p95 (ms) | Target  | Result |
   |--------------------|---------|---------|--------|
   | `POST /auth/login` | 145     | < 200ms | ✅ Pass |
   | `GET /dashboard`   | 289     | < 500ms | ✅ Pass |
   | `GET /erp/customers`| 118    | < 200ms | ✅ Pass |

3. Show that `/api/v1/metrics` returns `403` for non-admin users

---

## 4. Committed vs Completed Summary Slide

> Presented by: Prahallad Padhan (Product Owner)

| Story   | Committed | Completed | Status |
|---------|-----------|-----------|--------|
| US-S2-01: ERP Customer Mgmt      | 8 pts | 8 pts | ✅ |
| US-S2-02: ERP Product/Inventory  | 8 pts | 8 pts | ✅ |
| US-S2-03: ERP Order/Invoice      | 8 pts | 8 pts | ✅ |
| US-S2-04: Auth Audit/Versioning  | 5 pts | 5 pts | ✅ |
| US-S2-05: Integration/E2E Tests  | 8 pts | 8 pts | ✅ |
| US-S2-06: Performance Monitoring | 5 pts | 5 pts | ✅ |
| US-S2-07: Security Hardening     | 5 pts | 5 pts | ✅ |
| US-S2-08: Agile Board Tracking   | 5 pts | 5 pts | ✅ |
| **Total**                        | **52** | **52** | **100% ✅** |

**Key Highlight:** Despite finding and fixing 3 bugs during integration testing, the team delivered 100% of committed stories within the sprint. Test coverage jumped from 42% (Sprint 1) to 83% (Sprint 2).

---

## 5. Sprint 2 vs Sprint 1 Comparison

| Dimension             | Sprint 1    | Sprint 2      | Delta       |
|-----------------------|-------------|---------------|-------------|
| Stories delivered     | 10/10       | 8/8           | 100% both   |
| Points delivered      | 68/68       | 52/52         | 100% both   |
| API endpoints         | 28          | 46            | +18 (ERP)   |
| Test coverage         | 42%         | 83%           | **+41%**    |
| Auth enforcement      | 60%         | 100%          | **+40%**    |
| Security headers      | 4           | 7             | +3          |
| Bugs found/fixed      | 4/4         | 3/3           | 100% both   |
| CI pipeline           | None        | GitHub Actions| ✅ Added    |

---

## 6. Feedback Requested From Stakeholders

During the Q&A, the team invites feedback on:

1. **ERP Feature Priority** — Are there additional ERP entities (e.g., vendors, purchase orders, warehouse locations) to prioritize for Sprint 3?
2. **Reporting** — Should Sprint 3 include ERP reporting features (sales reports, inventory aging, revenue by customer)?
3. **Frontend** — Are the ERP UI pages meeting usability expectations, or are specific improvements needed?
4. **Performance** — Are there endpoints where current p95 targets are insufficient for production use?

---

## 7. Sprint 3 Preview

Based on Sprint 2 outcomes and retrospective action items, Sprint 3 is planned to focus on:

| Proposed Story         | Description                              | Est. Points |
|------------------------|------------------------------------------|-------------|
| ERP Reporting          | Sales dashboard, revenue by customer/product, inventory aging | 8 |
| Vendor Management      | Supplier CRUD, purchase orders           | 8           |
| Frontend PWA           | Progressive Web App shell, offline mode  | 5           |
| AI ERP Insights        | AI-powered order trend analysis, demand forecast | 8 |
| Multi-tenant Support   | Company-level data isolation             | 8           |
| **Projected Total**    |                                          | **~37 pts** |

---

## 8. Sign-Off

| Role             | Name                   | Date             | Signature |
|------------------|------------------------|------------------|-----------|
| Product Owner    | Prahallad Padhan       | April 24, 2026   | _________ |
| Scrum Master     | Ranveer Rai Khare      | April 24, 2026   | _________ |
| Product Developer| Shivansh Srivastava    | April 24, 2026   | _________ |
