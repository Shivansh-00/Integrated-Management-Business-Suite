# Architecture Document — Sprint 2 (Updated) — IBMS

| Field              | Detail                                              |
|--------------------|-----------------------------------------------------|
| **Project Name**   | Integrated Business Management Suite (IBMS) v2.0    |
| **Team**           | Shivansh Srivastava (Product Developer), Prahallad Padhan (Product Owner), Ranveer Rai Khare (Scrum Master) |
| **Sprint**         | Sprint 2                                            |
| **Sprint Duration**| April 13 – April 24, 2026                          |
| **Date**           | April 24, 2026                                      |
| **Document Type**  | Architecture Specification (Updated)                |
| **Course**         | SEPM (Software Engineering and Project Management)  |

---

## 1. Architecture Change Summary

Sprint 2 introduces three major architectural additions to the IBMS platform:

1. **ERP Data Layer** — Relational data models (Customer, Product, InventoryMovement, Order, OrderLineItem, Invoice, Payment) managed via SQLAlchemy ORM and Alembic migrations
2. **API Versioning Layer** — All routes unified under `/api/v1/` prefix; legacy routes redirect with `301`
3. **Observability Layer** — `/api/metrics` endpoint exposing system health, integrated with a performance baseline

The Sprint 1 architecture is fully preserved. Sprint 2 changes are additive.

---

## 2. Updated System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Client Layer                                 │
│   Browser SPA (HTML/CSS/JS/Tailwind)  ·  REST API clients          │
└────────────────────────────┬────────────────────────────────────────┘
                             │ HTTPS
┌────────────────────────────▼────────────────────────────────────────┐
│                   Nginx Reverse Proxy                               │
│   TLS termination · Rate limiting · CORS · Security headers         │
│   HSTS · CSP · X-XSS-Protection · X-Frame-Options                  │
└────────────────────────────┬────────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────────┐
│               FastAPI Application Server (Uvicorn)                  │
│                                                                     │
│  ┌─────────────┐  ┌─────────────┐  ┌────────────────────────────┐  │
│  │  Auth Layer  │  │  Middleware  │  │     WebSocket Hub          │  │
│  │  JWT + RBAC  │  │  CSRF · Rate │  │     Live KPI Push          │  │
│  │  2FA · Audit │  │  Limit · Log │  │     Low-Stock Alerts [NEW] │  │
│  └─────────────┘  └─────────────┘  └────────────────────────────┘  │
│                                                                     │
│  ┌──────────────── API Router /api/v1/ [NEW] ───────────────────┐   │
│  │                                                              │   │
│  │  /auth/*     /dashboard/*   /ai/*    /risk/*    /fraud/*     │   │
│  │  /compliance/*  /budget/*   /pricing/*  /forecast/*          │   │
│  │  /copilot/*                                                  │   │
│  │                                                              │   │
│  │  ┌──────────────── ERP Module [NEW Sprint 2] ─────────────┐ │   │
│  │  │  /erp/customers/*   /erp/products/*                    │ │   │
│  │  │  /erp/inventory/*   /erp/orders/*                      │ │   │
│  │  │  /erp/invoices/*    /erp/payments/*                    │ │   │
│  │  └────────────────────────────────────────────────────────┘ │   │
│  │                                                              │   │
│  │  /metrics [NEW Sprint 2] — System health (admin only)       │   │
│  └──────────────────────────────────────────────────────────────┘   │
└────────────┬──────────────────────────┬────────────────────────────┘
             │                          │
┌────────────▼──────────┐   ┌──────────▼──────────────────────────────┐
│   Primary Database    │   │         Service Layer                    │
│  MongoDB Atlas /      │   │                                          │
│  PostgreSQL (prod)    │   │  AIAssistantService  RiskScoringEngine   │
│                       │   │  ComplianceEngine    BudgetOptimizer     │
│  Sprint 2 ERP Tables: │   │  DigitalTwin         FraudDetector       │
│  customers            │   │                                          │
│  products             │   │  ┌── ERP Services [NEW Sprint 2] ──────┐ │
│  inventory_movements  │   │  │  CustomerService  ProductService    │ │
│  orders               │   │  │  OrderService     InvoiceService    │ │
│  order_line_items     │   │  │  InventoryService PaymentService    │ │
│  invoices             │   │  └─────────────────────────────────────┘ │
│  payments             │   │                                          │
└───────────────────────┘   │  ┌── Observability [NEW Sprint 2] ─────┐ │
                            │  │  MetricsCollector (psutil)          │ │
┌───────────────────────┐   │  │  PerformanceBaseline                │ │
│   Cache (Redis)       │   │  └─────────────────────────────────────┘ │
│  JWT blocklist        │   └──────────────────────────────────────────┘
│  Rate limit counters  │
│  Session store        │
└───────────────────────┘
```

---

## 3. ERP Module Architecture (New in Sprint 2)

### 3.1 ERP Data Model — Entity Relationship

```
Customer (1) ──────────── (N) Order
    id PK                       id PK
    name                        customer_id FK
    email UNIQUE                status ENUM(pending,confirmed,
    phone                              shipped,delivered,cancelled)
    company                     total_amount
    address                     created_at
    created_at
    updated_at          Order (1) ──── (N) OrderLineItem
                                               id PK
                                               order_id FK
Product (1) ──────── (N) OrderLineItem         product_id FK
    id PK                product_id FK          quantity
    name                 quantity               unit_price
    sku UNIQUE           unit_price             subtotal
    category
    unit_price          Order (1) ──── (1) Invoice
    quantity                                id PK
    reorder_threshold                       order_id FK UNIQUE
    created_at                              amount
    updated_at                              compliance_hold BOOL
                                            status ENUM(draft,sent,paid)
Product (1) ──── (N) InventoryMovement      created_at
    product_id FK
    type ENUM(inbound,outbound)   Invoice (1) ── (N) Payment
    quantity                                  id PK
    note                                      invoice_id FK
    created_at                                amount
                                              payment_method
                                              paid_at
```

### 3.2 ERP API Routes

| Method | Route                                  | Service               | Auth Required | Min Role   |
|--------|----------------------------------------|-----------------------|---------------|------------|
| POST   | `/api/v1/erp/customers`                | CustomerService.create | Yes          | manager    |
| GET    | `/api/v1/erp/customers`                | CustomerService.list  | Yes           | viewer     |
| GET    | `/api/v1/erp/customers/{id}`           | CustomerService.get   | Yes           | viewer     |
| PUT    | `/api/v1/erp/customers/{id}`           | CustomerService.update| Yes           | manager    |
| DELETE | `/api/v1/erp/customers/{id}`           | CustomerService.delete| Yes           | manager    |
| POST   | `/api/v1/erp/products`                 | ProductService.create | Yes           | manager    |
| GET    | `/api/v1/erp/products`                 | ProductService.list   | Yes           | viewer     |
| PUT    | `/api/v1/erp/products/{id}`            | ProductService.update | Yes           | manager    |
| DELETE | `/api/v1/erp/products/{id}`            | ProductService.delete | Yes           | manager    |
| GET    | `/api/v1/erp/products/low-stock`       | ProductService.lowStock| Yes          | viewer     |
| POST   | `/api/v1/erp/inventory/movement`       | InventoryService.move | Yes           | manager    |
| POST   | `/api/v1/erp/orders`                   | OrderService.create   | Yes           | manager    |
| GET    | `/api/v1/erp/orders`                   | OrderService.list     | Yes           | analyst    |
| PATCH  | `/api/v1/erp/orders/{id}/status`       | OrderService.transition| Yes          | manager    |
| POST   | `/api/v1/erp/invoices`                 | InvoiceService.create | Yes           | manager    |
| POST   | `/api/v1/erp/payments`                 | PaymentService.create | Yes           | manager    |
| GET    | `/api/v1/metrics`                      | MetricsCollector.get  | Yes           | admin      |

### 3.3 ERP Service Class Diagram

```
┌─────────────────────────────┐
│      ERPBaseService         │
│  - db: AsyncSession         │
│  - audit_log(event)         │
│  - paginate(query, page)    │
└─────────────┬───────────────┘
              │ inherits
    ┌─────────┴──────────┐
    │                    │
CustomerService    ProductService
+ create()         + create()
+ list()           + list()
+ get()            + update()
+ update()         + delete()
+ delete()         + low_stock()
                        │
                  InventoryService
                  + move(product_id,
                         type, qty)

OrderService            InvoiceService
+ create()              + create()
+ list()                + compliance_check()
+ get()                 + mark_paid()
+ transition_status()
    │
PaymentService
+ record_payment()
```

---

## 4. API Versioning Strategy (Updated in Sprint 2)

### 4.1 Versioning Approach

IBMS uses **URL path versioning** (`/api/v1/`) as the primary versioning strategy. This approach:
- Is explicitly visible and debuggable
- Is supported by all client types without custom headers
- Allows concurrent operation of multiple API versions during transitions

### 4.2 Router Configuration

```python
# FastAPI router registration (server.py)
from fastapi import APIRouter

v1_router = APIRouter(prefix="/api/v1")

# Include all sub-routers
v1_router.include_router(auth_router,       prefix="/auth")
v1_router.include_router(dashboard_router,  prefix="/dashboard")
v1_router.include_router(erp_router,        prefix="/erp")
v1_router.include_router(risk_router,       prefix="/risk")
# ... etc.

# Legacy route redirect middleware
@app.middleware("http")
async def legacy_redirect(request: Request, call_next):
    if request.url.path.startswith("/api/") and \
       not request.url.path.startswith("/api/v"):
        new_path = request.url.path.replace("/api/", "/api/v1/", 1)
        return RedirectResponse(url=new_path, status_code=301)
    return await call_next(request)
```

### 4.3 Version Response Header

All API responses include:
```
X-API-Version: 1
X-Request-ID: <uuid>
```

---

## 5. Authentication & Security Architecture (Updated)

### 5.1 Zero-Trust Enforcement

Sprint 2 closes all authentication gaps identified in Sprint 1:

```
Request
   │
   ▼
[Nginx] → Rate limiting, TLS, security headers
   │
   ▼
[Auth Middleware] → Verify JWT (every API request except /health, /docs, /api/auth/*)
   │
   ├── 401 → Invalid / Expired / Missing token
   │
   ▼
[RBAC Middleware] → Check role against endpoint requirement
   │
   ├── 403 → Insufficient role
   │
   ▼
[Route Handler] → Business logic
   │
   ▼
[Audit Logger] → Record action, user, timestamp, IP (for mutations)
```

### 5.2 Security Headers (Sprint 2 Additions)

| Header                      | Value                                   | Added In  |
|-----------------------------|----------------------------------------|-----------|
| `X-XSS-Protection`         | `1; mode=block`                        | Sprint 2  |
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` | Sprint 2  |
| `Content-Security-Policy`   | `default-src 'self'`                  | Sprint 2  |
| `X-Content-Type-Options`    | `nosniff`                              | Sprint 1  |
| `X-Frame-Options`           | `DENY`                                 | Sprint 1  |
| `Cache-Control`             | `no-store`                             | Sprint 1  |

---

## 6. Observability Architecture (New in Sprint 2)

### 6.1 Metrics Collection

```
┌────────────────────────────────────────────┐
│            MetricsCollector                │
│                                            │
│  psutil.cpu_percent()   → cpu_usage (%)   │
│  psutil.virtual_memory() → memory_used (%)│
│  asyncio active tasks   → active_ws_conns │
│  request counter (middleware) → req/sec   │
└──────────────────┬─────────────────────────┘
                   │
     GET /api/v1/metrics (admin JWT required)
                   │
     ┌─────────────▼──────────────┐
     │  {                         │
     │    "cpu_percent": 12.4,    │
     │    "memory_percent": 48.2, │
     │    "active_connections": 3,│
     │    "requests_per_second": 14.2, │
     │    "uptime_seconds": 86400 │
     │  }                         │
     └────────────────────────────┘
```

### 6.2 WebSocket Enhanced Push (Sprint 2)

Sprint 2 adds `inventory_alerts` to the WebSocket KPI push:

```json
{
  "type": "kpi_update",
  "timestamp": "2026-04-24T10:00:00Z",
  "kpis": { "revenue": 1250000, "margin": 0.34 },
  "inventory_alerts": [
    { "product_id": "P-042", "sku": "WDG-100", "quantity": 3, "threshold": 10 }
  ]
}
```

---

## 7. Database Architecture (Updated)

### 7.1 Database Strategy

| Store          | Technology         | Usage                                    |
|----------------|--------------------|-----------------------------------------|
| Primary DB     | PostgreSQL (prod)  | All relational data: users, ERP records |
| Primary DB     | SQLite (dev/test)  | Local development and CI testing        |
| Document Store | MongoDB Atlas      | AI insights, audit logs, unstructured   |
| Cache          | Redis              | JWT blocklist, rate limits, sessions    |

### 7.2 Schema Migration Strategy

Alembic is used for all PostgreSQL schema changes:

```bash
# Create a new migration
alembic revision --autogenerate -m "add_erp_tables"

# Apply all pending migrations
alembic upgrade head

# Roll back one migration
alembic downgrade -1
```

Migration files are stored in `alembic/versions/` and committed to source control.

---

## 8. CI/CD Pipeline (Sprint 2 Addition)

```
Developer Push to GitHub
        │
        ▼
  GitHub Actions
        │
  ┌─────▼──────┐
  │  Lint      │  ruff / flake8
  └─────┬──────┘
        │
  ┌─────▼──────┐
  │  Unit +    │  pytest tests/ --cov
  │  Integration│  Coverage >= 80%
  │  Tests     │
  └─────┬──────┘
        │
  ┌─────▼──────┐
  │  Security  │  pip-audit (CVE check)
  │  Scan      │
  └─────┬──────┘
        │
  ┌─────▼──────┐
  │  Docker    │  Build + push to registry
  │  Build     │
  └─────┬──────┘
        │
  ┌─────▼──────┐
  │  Deploy    │  Cloud Run / Render / K8s
  │  (on main) │
  └────────────┘
```

---

## 9. Technology Stack (Updated)

| Layer            | Technology                        | Sprint |
|------------------|-----------------------------------|--------|
| Framework        | FastAPI 0.111                     | S1     |
| ASGI Server      | Uvicorn                           | S1     |
| Auth             | python-jose (JWT), pyotp (TOTP)   | S1     |
| AI/ML            | scikit-learn, Prophet             | S1     |
| ORM              | SQLAlchemy 2.0 (async)            | **S2** |
| Migrations       | Alembic 1.13                      | **S2** |
| Metrics          | psutil 5.x                        | **S2** |
| Load Testing     | Locust 2.x                        | **S2** |
| Security Scan    | pip-audit 2.x                     | **S2** |
| Test Framework   | pytest + pytest-cov + httpx       | S1/S2  |
| Database (dev)   | SQLite                            | S1     |
| Database (prod)  | PostgreSQL / MongoDB Atlas        | S1     |
| Cache            | Redis                             | S1     |
| Frontend         | HTML5 / Tailwind CSS / Vanilla JS | S1     |
| Container        | Docker + Docker Compose           | S1     |
| Orchestration    | Kubernetes / Cloud Run            | S1     |
| Reverse Proxy    | Nginx                             | S1     |

---

## 10. Sprint 1 vs Sprint 2 Architecture Comparison

| Dimension               | Sprint 1                              | Sprint 2                                  |
|-------------------------|---------------------------------------|-------------------------------------------|
| API endpoints           | 28                                    | 46 (+18 ERP endpoints)                    |
| API versioning          | No versioning (`/api/*`)              | Versioned (`/api/v1/*`) + 301 redirect    |
| Data models             | Users, audit logs, AI snapshots       | + Customer, Product, Inventory, Order, Invoice, Payment |
| Auth enforcement        | Partial (60% of endpoints)            | Complete (100% of endpoints)              |
| Security headers        | 4 headers                             | 7 headers (+XSS, HSTS, CSP)              |
| Observability           | Basic health check only               | `/api/metrics` + load test baseline      |
| Test coverage           | 42% (unit only)                       | 83% (unit + integration + E2E)            |
| CI pipeline             | None                                  | GitHub Actions (lint + test + scan + deploy)|
| Database migrations     | Ad-hoc                                | Alembic managed                           |

---

## 11. Sign-Off

| Role             | Name                   | Date             | Signature |
|------------------|------------------------|------------------|-----------|
| Product Owner    | Prahallad Padhan       | April 24, 2026   | _________ |
| Scrum Master     | Ranveer Rai Khare      | April 24, 2026   | _________ |
| Product Developer| Shivansh Srivastava    | April 24, 2026   | _________ |
