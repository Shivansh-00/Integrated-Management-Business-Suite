# Functional Document — IBMS (Integrated Business Management Suite)

| Field              | Detail                                              |
|--------------------|-----------------------------------------------------|
| **Project Name**   | Integrated Business Management Suite (IBMS) v2.0    |
| **Team**           | Shivansh Srivastava (Product Developer), Prahallad Padhan (Product Owner), Ranveer Rai Khare (Scrum Master) |
| **Sprint**         | Sprint 1                                            |
| **Date**           | April 8, 2026                                       |
| **Document Type**  | Functional Specification                            |

---

## 1. Project Overview

IBMS is an AI-first Enterprise Resource Planning (ERP) platform built with **FastAPI** (Python). It provides real-time business dashboards, AI-powered analytics, risk scoring, fraud detection, compliance checking, budget optimization, and lead scoring — all exposed via a REST/WebSocket API with a responsive single-page frontend.

### 1.1 Objectives

- Deliver a unified business intelligence dashboard with real-time KPI tracking.
- Provide AI/ML-powered services for forecasting, anomaly detection, and fraud prevention.
- Enforce enterprise-grade security (JWT auth, TOTP 2FA, RBAC, CSRF, device fingerprinting).
- Support multi-tier deployment (Docker, Kubernetes, AWS).
- Enable real-time collaboration via WebSocket push updates.

---

## 2. Functional Requirements

### 2.1 Authentication & User Management

| ID     | Requirement                                      | Status    |
|--------|--------------------------------------------------|-----------|
| FR-01  | User registration with email and password        | Completed |
| FR-02  | User login with JWT access + refresh tokens      | Completed |
| FR-03  | TOTP-based Two-Factor Authentication (setup, confirm, disable) | Completed |
| FR-04  | Role-Based Access Control (super_admin, admin, manager, analyst, viewer) | Completed |
| FR-05  | Device fingerprint binding on login              | Completed |
| FR-06  | Password strength validation with policy enforcement | Completed |
| FR-07  | Silent token refresh with rotation               | Completed |
| FR-08  | CSRF token generation and validation             | Completed |
| FR-09  | Audit logging for all auth events                | Completed |
| FR-10  | OAuth provider configuration endpoint            | Completed |
| FR-11  | Brute-force protection with IP-based rate limiting | Completed |

### 2.2 Dashboard & KPI Module

| ID     | Requirement                                      | Status    |
|--------|--------------------------------------------------|-----------|
| FR-12  | Real-time KPI dashboard (revenue, margin, risk, compliance) | Completed |
| FR-13  | KPI history with trend data points               | Completed |
| FR-14  | WebSocket-based live KPI push updates            | Completed |
| FR-15  | Auto-refresh KPI snapshots every 15 seconds      | Completed |
| FR-16  | Company-level KPI filtering                      | Completed |

### 2.3 AI & Analytics Module

| ID     | Requirement                                      | Status    |
|--------|--------------------------------------------------|-----------|
| FR-17  | Sales forecasting with confidence interval bands | Completed |
| FR-18  | AI-generated business insights (anomalies, trends, predictions) | Completed |
| FR-19  | Active anomaly detection on transaction volume   | Completed |
| FR-20  | Natural language AI Copilot for business queries | Completed |

### 2.4 Risk & Fraud Module

| ID     | Requirement                                      | Status    |
|--------|--------------------------------------------------|-----------|
| FR-21  | Transaction risk scoring (0–100) with factor breakdown | Completed |
| FR-22  | Isolation Forest-based fraud detection with review flag | Completed |
| FR-23  | Composite risk score (amount 50%, behavior 30%, compliance 20%) | Completed |

### 2.5 Business Operations Module

| ID     | Requirement                                      | Status    |
|--------|--------------------------------------------------|-----------|
| FR-24  | Budget optimization with growth targets          | Completed |
| FR-25  | Compliance control-set evaluation (high-value approval checks) | Completed |
| FR-26  | Dynamic pricing recommendation (demand/stock/competitor) | Completed |
| FR-27  | Risk-based workflow decision engine (approve/review/reject) | Completed |
| FR-28  | Lead scoring (55% engagement + 45% fit)          | Completed |
| FR-29  | Digital twin operational simulation              | Completed |
| FR-30  | Inventory reorder point prediction               | Completed |

### 2.6 System & Monitoring

| ID     | Requirement                                      | Status    |
|--------|--------------------------------------------------|-----------|
| FR-31  | Health check endpoint with Redis and uptime status | Completed |
| FR-32  | System metrics (requests, errors, WS connections) | Completed |
| FR-33  | Detailed system status with top endpoints and cache state | Completed |
| FR-34  | Notification queue management                    | Completed |
| FR-35  | Event stream with publish-subscribe routing      | Completed |

---

## 3. API Endpoint Summary

The application exposes **70+ API endpoints** across the following categories:

### 3.1 Authentication Endpoints (14 routes)

| Method | Endpoint                     | Auth Required | Description                        |
|--------|------------------------------|---------------|------------------------------------|
| POST   | `/api/auth/login`            | No            | JWT login with device fingerprint + 2FA |
| POST   | `/api/auth/register`         | No            | New user registration              |
| POST   | `/api/auth/refresh`          | Cookie        | Refresh token rotation             |
| POST   | `/api/auth/logout`           | Bearer        | Revoke tokens, clear session       |
| GET    | `/api/auth/me`               | Bearer        | Current user profile + permissions |
| GET    | `/api/auth/csrf`             | Bearer        | Generate CSRF token                |
| POST   | `/api/auth/2fa/setup`        | Bearer        | Initialize TOTP 2FA               |
| POST   | `/api/auth/2fa/confirm`      | Bearer        | Verify and enable 2FA             |
| POST   | `/api/auth/2fa/disable`      | Bearer        | Disable 2FA                       |
| GET    | `/api/auth/roles`            | Bearer        | List roles with permissions        |
| POST   | `/api/auth/password-strength`| No            | Validate password against policy   |
| POST   | `/api/auth/token`            | No            | Legacy token endpoint              |
| POST   | `/api/auth/validate`         | No            | Legacy token validation            |
| GET    | `/api/auth/oauth-config`     | No            | OAuth provider configuration       |

### 3.2 Dashboard & KPI Endpoints (3 routes)

| Method    | Endpoint                 | Auth Required | Description                     |
|-----------|--------------------------|---------------|---------------------------------|
| GET       | `/api/dashboard`         | No            | Real-time KPI snapshot          |
| GET       | `/api/dashboard/history` | No            | Historical KPI trend data       |
| WebSocket | `/ws/kpi`                | Token (query) | Live KPI push updates           |

### 3.3 AI & Analytics Endpoints (4 routes)

| Method | Endpoint            | Auth Required | Description                        |
|--------|---------------------|---------------|------------------------------------|
| POST   | `/api/forecast`     | No            | Sales forecast with CI bands       |
| GET    | `/api/ai/insights`  | No            | AI-generated business insights     |
| GET    | `/api/ai/anomalies` | No            | Active anomaly detection results   |
| POST   | `/api/copilot/ask`  | No            | Natural language business queries  |

### 3.4 Risk, Fraud & Business Endpoints (7 routes)

| Method | Endpoint                  | Auth Required | Description                      |
|--------|---------------------------|---------------|----------------------------------|
| POST   | `/api/risk/score`         | No            | Transaction risk scoring         |
| POST   | `/api/fraud/detect`       | No            | Isolation Forest fraud detection |
| POST   | `/api/risk/composite`     | No            | Multi-factor composite risk      |
| POST   | `/api/budget/optimize`    | No            | Budget allocation optimization   |
| POST   | `/api/compliance/check`   | No            | Control-set compliance evaluation|
| POST   | `/api/pricing/suggest`    | No            | Dynamic pricing recommendation   |
| POST   | `/api/decision/evaluate`  | No            | Risk-based workflow decision     |
| POST   | `/api/leads/score`        | No            | Lead qualification scoring       |
| POST   | `/api/twin/simulate`      | No            | Digital twin simulation          |
| POST   | `/api/inventory/predict`  | No            | Inventory reorder prediction     |

### 3.5 System Endpoints (5 routes)

| Method | Endpoint              | Auth Required | Description                    |
|--------|-----------------------|---------------|--------------------------------|
| GET    | `/api/health`         | No            | Health check with uptime stats |
| GET    | `/api/metrics`        | No            | System metrics snapshot        |
| GET    | `/api/system/status`  | No            | Detailed system status         |
| GET    | `/api/notifications`  | Bearer        | Notification queue (paginated) |
| GET    | `/api/audit/log`      | Bearer + RBAC | Audit event log (audit.view)   |
| GET    | `/api/endpoints`      | No            | List all API routes            |

---

## 4. User Roles & Permissions

| Role         | Permissions                                                                 | Inherits From |
|--------------|-----------------------------------------------------------------------------|---------------|
| super_admin  | Full access (`*`)                                                           | —             |
| admin        | dashboard, users, reports, settings, api, ai, risk, compliance, audit       | —             |
| manager      | reports.export, risk.manage, compliance.manage, budget.approve, leads.manage, pricing.manage | analyst |
| analyst      | reports.view, ai.view, risk.view, compliance.view, forecast.view, copilot.use | viewer |
| viewer       | dashboard.view, kpi.view                                                    | —             |

---

## 5. Frontend Features

| Feature                        | Description                                                      |
|--------------------------------|------------------------------------------------------------------|
| **Login / Register UI**        | Auth overlay with username/password, TOTP 2FA field, password strength meter |
| **Real-Time Dashboard**        | KPI card grid with live WebSocket updates, animated counters     |
| **Forecast Chart**             | Chart.js integration with confidence interval visualization      |
| **Sidebar Navigation**         | 11 pages: Dashboard, Analytics, AI Insights, Risk & Fraud, Compliance, Pricing, Budget, Leads, Events, Health, Audit |
| **Theme Toggle**               | Dark/light mode with persistent state                            |
| **Toast Notifications**        | Max 5 concurrent, 5-second auto-dismiss                         |
| **Token Management**           | Silent refresh, auto-logout, CSRF injection                     |
| **WebSocket Connection**       | Auto-reconnect with exponential backoff, health indicator        |
| **3D Tilt Effects**            | GPU-accelerated animations on KPI spotlight cards                |
| **Reduced Motion Support**     | Respects `prefers-reduced-motion` media query                   |
| **Mobile Responsive**          | Collapsible sidebar, responsive grid layout                      |

---

## 6. Non-Functional Requirements

| Requirement          | Implementation                                                        |
|----------------------|-----------------------------------------------------------------------|
| **Performance**      | 15-second KPI refresh cycle; Redis caching with in-memory fallback    |
| **Security**         | JWT + 2FA, RBAC, CSRF, rate limiting, device binding, audit logging   |
| **Availability**     | K8s 3-replica deployment, health/readiness probes, auto-restart       |
| **Scalability**      | Stateless API, Redis cache, K8s horizontal scaling                    |
| **Observability**    | Trace IDs on all requests, metrics endpoint, response timing headers  |
| **Compliance**       | Audit log, compliance engine, control-set evaluation                  |

---

## 7. Technology Stack

| Layer            | Technology                                           |
|------------------|------------------------------------------------------|
| Backend          | FastAPI (Python 3.11), Uvicorn ASGI                  |
| Frontend         | Vanilla JavaScript, HTML5, CSS3, Chart.js            |
| Authentication   | JWT (HS256), TOTP (pyotp), bcrypt/PBKDF2             |
| Database         | MariaDB 10.6 (via Frappe ORM), Redis 7 (cache)      |
| Containers       | Docker, Docker Compose, Kubernetes                   |
| Infrastructure   | Terraform (AWS: VPC, RDS, ElastiCache)               |
| Reverse Proxy    | Nginx (Alpine)                                       |
| AI/ML            | Prophet (forecasting), Isolation Forest (fraud)      |
| CI/CD            | GitHub Actions, GitHub Container Registry (ghcr.io)  |

---

*Document Version 1.0 — Sprint 1 Review*
