# Sprint 1 Demo — IBMS (Integrated Business Management Suite)

| Field              | Detail                                              |
|--------------------|-----------------------------------------------------|
| **Project Name**   | Integrated Business Management Suite (IBMS) v2.0    |
| **Team**           | Shivansh Srivastava (Product Developer), Prahallad Padhan (Product Owner), Ranveer Rai Khare (Scrum Master) |
| **Sprint**         | Sprint 1                                            |
| **Demo Date**      | April 12, 2026                                      |
| **Duration**       | ~15 minutes                                         |
| **Environment**    | Local (localhost:8000) — FastAPI + MongoDB 8.2 + Vanilla JS SPA |

---

## 1. Demo Objective

Demonstrate all 10 user stories delivered in Sprint 1 by walking through the running IBMS application, exercising the API endpoints, and showing the live frontend dashboard.

**Sprint Goal Recap**: Build a production-grade, AI-first enterprise management platform with real-time dashboards, AI-powered analytics, enterprise-grade security, and multi-environment deployment support.

---

## 2. Pre-Demo Checklist

| Step | Command / Action                                       | Expected State              |
|------|--------------------------------------------------------|-----------------------------|
| 1    | Start MongoDB: `net start MongoDB`                     | MongoDB running on port 27017 |
| 2    | Activate venv: `.venv2\Scripts\activate`               | Python 3.12 venv active     |
| 3    | Start server: `uvicorn server:app --host 0.0.0.0 --port 8000 --reload` | Server running at `http://localhost:8000` |
| 4    | Open browser: `http://localhost:8000`                  | IBMS login screen renders   |
| 5    | Verify MongoDB: check console for `MongoDB async connected` | Database connected          |

---

## 3. Demo Script — Feature Walkthrough

### Demo 1: User Registration & Secure Login (US-01) — 2 min

| Step | Action                                               | What to Show                              |
|------|------------------------------------------------------|-------------------------------------------|
| 1.1  | Open `http://localhost:8000` in browser              | Auth overlay with Login/Register toggle   |
| 1.2  | Click "Register" tab                                 | Registration form appears                 |
| 1.3  | Type a weak password (e.g., `abc`)                   | Password strength meter shows **Weak** (red) |
| 1.4  | Type a strong password (e.g., `Secure@2026!`)        | Strength meter shows **Strong** (green)   |
| 1.5  | Fill in username, email, password → Submit           | Success toast → auto-login → Dashboard    |
| 1.6  | **API Demo**: Show `POST /api/auth/register` response in DevTools | JWT access token + CSRF token returned |
| 1.7  | Show MongoDB `users` collection                      | Password stored as bcrypt hash (`$2b$12$...`), not plaintext |

**Acceptance Criteria Validated**: Password strength validation, bcrypt hashing, JWT issuance, device fingerprint capture, frontend overlay.

---

### Demo 2: Two-Factor Authentication (US-02) — 1.5 min

| Step | Action                                               | What to Show                              |
|------|------------------------------------------------------|-------------------------------------------|
| 2.1  | Call `POST /api/auth/2fa/setup` with Bearer token    | Returns TOTP provisioning URI + secret    |
| 2.2  | Show provisioning URI is compatible with authenticator apps | URI format: `otpauth://totp/IBMS:user@...` |
| 2.3  | Call `POST /api/auth/2fa/confirm` with a valid TOTP code | 2FA enabled successfully               |
| 2.4  | Logout and log back in                               | Login form now shows the 2FA code input field |
| 2.5  | Enter TOTP code → Login                              | Login succeeds with 2FA                   |
| 2.6  | Call `POST /api/auth/2fa/disable`                    | 2FA disabled, login reverts to password-only |

**Acceptance Criteria Validated**: TOTP setup/confirm/disable, dynamic 2FA field on login, provisioning URI generation.

---

### Demo 3: Role-Based Dashboard Access (US-03) — 1.5 min

| Step | Action                                               | What to Show                              |
|------|------------------------------------------------------|-------------------------------------------|
| 3.1  | Call `GET /api/auth/roles`                           | Returns 5 roles with permission arrays    |
| 3.2  | Login as `admin` user → call `GET /api/auth/me`     | Shows resolved permissions for admin role |
| 3.3  | Show sidebar — all 11 pages visible                  | Admin sees all navigation items           |
| 3.4  | Login as `viewer` user                               | Sidebar shows only Dashboard and basic pages |
| 3.5  | As viewer, call `GET /api/audit/log`                 | Returns `403 Forbidden` (requires `audit.view`) |
| 3.6  | As admin, call `GET /api/audit/log`                  | Returns paginated audit events            |

**Acceptance Criteria Validated**: 5-tier RBAC, permission inheritance, sidebar visibility, 403 on unauthorized access.

---

### Demo 4: Real-Time KPI Dashboard (US-04) — 2 min

| Step | Action                                               | What to Show                              |
|------|------------------------------------------------------|-------------------------------------------|
| 4.1  | Navigate to Dashboard page                           | 9 KPI cards with animated counters load   |
| 4.2  | Point out the WebSocket status indicator             | Green dot = connected to `/ws/kpi`        |
| 4.3  | Wait 15 seconds                                      | KPI values update automatically (live push) |
| 4.4  | Open DevTools → Network → WS tab                    | Show WebSocket frames arriving every 15s  |
| 4.5  | Call `GET /api/dashboard`                            | JSON snapshot: revenue, margin, risk, compliance, etc. |
| 4.6  | Call `GET /api/dashboard/history`                    | Historical data points for trend charts   |
| 4.7  | Navigate to Analytics page                           | Chart.js KPI history trend chart renders  |
| 4.8  | Show 3D tilt spotlight effect on KPI cards           | Hover over cards → GPU-accelerated tilt   |

**Acceptance Criteria Validated**: Live KPI push (15s), WebSocket auto-reconnect, Chart.js charts, Redis/in-memory cache, animated counters.

---

### Demo 5: AI-Powered Business Insights & Copilot (US-05) — 1.5 min

| Step | Action                                               | What to Show                              |
|------|------------------------------------------------------|-------------------------------------------|
| 5.1  | Call `GET /api/ai/insights`                          | 4 insights: anomaly, trend, prediction, recommendation |
| 5.2  | Call `GET /api/ai/anomalies`                         | Active anomalies in transaction volume    |
| 5.3  | Call `POST /api/copilot/ask` with `{"query":"show risk details"}` | AI returns risk metrics from KPI data |
| 5.4  | Call `POST /api/forecast`                            | Prophet Ensemble v2 forecast with confidence bands |
| 5.5  | Navigate to AI Insights page in frontend             | AI insight cards rendered in the UI       |

**Acceptance Criteria Validated**: AI insights (4 types), anomaly detection, NL copilot, forecast with CI bands, recommendations.

---

### Demo 6: Risk Scoring & Fraud Detection (US-06) — 1.5 min

| Step | Action                                               | What to Show                              |
|------|------------------------------------------------------|-------------------------------------------|
| 6.1  | `POST /api/risk/score` with `{"transaction":{"amount":75000,"vendor":"new"}}` | Risk score 0-100 with factor breakdown |
| 6.2  | `POST /api/risk/composite` with `{"factors":{"amount":80,"behavior":50,"compliance":30}}` | Weighted score: (0.5×80)+(0.3×50)+(0.2×30) = **61.0** |
| 6.3  | `POST /api/fraud/detect` with `{"transaction":{"amount":100000,"vendor":"unknown"}}` | Fraud score (0-1) + `flag_for_review: true` |
| 6.4  | `POST /api/decision/evaluate` with a high-risk input | Decision: approve / review / reject       |
| 6.5  | Navigate to Risk & Fraud page in frontend            | Risk scoring form + results displayed     |

**Acceptance Criteria Validated**: Transaction risk (0-100), composite weighted risk, Isolation Forest fraud, decision routing.

---

### Demo 7: Compliance Checking & Audit Trail (US-07) — 1 min

| Step | Action                                               | What to Show                              |
|------|------------------------------------------------------|-------------------------------------------|
| 7.1  | `POST /api/compliance/check` with `{"transaction":{"amount":600000}}` | `passed: false`, violation: `MISSING_HIGH_VALUE_APPROVAL` |
| 7.2  | `POST /api/compliance/check` with `{"transaction":{"amount":600000,"approval_ref":"APR-001"}}` | `passed: true`, no violations |
| 7.3  | `GET /api/audit/log` (as admin)                      | Paginated audit events with timestamps    |
| 7.4  | Show audit entries in MongoDB `audit_logs` collection | Events with base64-encoded details        |

**Acceptance Criteria Validated**: Control-set validation, violation codes, audit trail persistence, RBAC-gated audit log.

---

### Demo 8: Budget Optimization & Dynamic Pricing (US-08) — 1 min

| Step | Action                                               | What to Show                              |
|------|------------------------------------------------------|-------------------------------------------|
| 8.1  | `POST /api/budget/optimize` with `{"items":[{"name":"Marketing","amount":50000},{"name":"R&D","amount":80000}],"growth_target":15}` | Optimized totals with growth multiplier |
| 8.2  | `POST /api/pricing/suggest` with `{"demand_index":0.8,"stock_level":200,"competitor_price":999}` | Recommended dynamic price |
| 8.3  | Navigate to Budget and Pricing pages in frontend     | Forms + result output displayed           |

**Acceptance Criteria Validated**: Budget optimizer with growth target, dynamic pricing with demand/stock/competitor weights.

---

### Demo 9: Lead Scoring & Inventory Prediction (US-09) — 1 min

| Step | Action                                               | What to Show                              |
|------|------------------------------------------------------|-------------------------------------------|
| 9.1  | `POST /api/leads/score` with `{"engagement":{"email_opens":15,"page_visits":30,"demo_requests":2},"fit":{"company_size":"enterprise","industry":"fintech","budget":500000}}` | Score + tier (hot/warm/cold) |
| 9.2  | `POST /api/inventory/predict` with `{"product_id":"SKU-001","lead_time_days":14}` | Reorder point prediction |
| 9.3  | Navigate to Lead Scoring page in frontend            | Lead scoring form + tier output           |

**Acceptance Criteria Validated**: Lead qualification (55% engagement + 45% fit), tier classification, inventory reorder prediction.

---

### Demo 10: System Health Monitoring & Deployment (US-10) — 2 min

| Step | Action                                               | What to Show                              |
|------|------------------------------------------------------|-------------------------------------------|
| 10.1 | `GET /api/health`                                    | `status: healthy`, uptime, request count, error rate |
| 10.2 | `GET /api/metrics`                                   | System metrics snapshot                   |
| 10.3 | `GET /api/system/status`                             | Top endpoints, cache state, detailed status |
| 10.4 | Show response headers in DevTools                    | `X-Trace-Id`, `X-Response-Time-Ms`, security headers |
| 10.5 | Navigate to System Health page in frontend           | Server status dashboard                   |
| 10.6 | Show `docker-compose.yml`                            | Nginx + Web + Redis + MongoDB orchestration |
| 10.7 | Show `deploy/k8s/ibms-core-deployment.yaml`          | 3 replicas, resource limits, health probes |
| 10.8 | Show `deploy/aws/terraform/main.tf`                  | VPC, subnets, ElastiCache, security groups |

**Acceptance Criteria Validated**: Health/metrics/status endpoints, trace headers, security headers, Docker/K8s/Terraform configs.

---

## 4. Live Database Verification

| Collection        | Documents | Key Data                                          |
|-------------------|-----------|----------------------------------------------------|
| `users`           | 3         | admin, analyst, shiv1 — bcrypt-hashed passwords    |
| `kpi_snapshots`   | 24        | Revenue, margin, risk, compliance — every 15s      |
| `kpi_latest`      | 1         | Materialized view — latest KPI for instant reads   |
| `audit_logs`      | 2+        | Login, register events — timestamped, base64       |
| `refresh_tokens`  | 1+        | Active refresh tokens with TTL expiry index        |
| `csrf_tokens`     | 1+        | CSRF tokens with 1-hour TTL expiry index           |
| `notifications`   | 1+        | System notifications                               |
| `alerts`          | 0         | Ready — indexed by severity + resolved status      |
| `ai_recommendations` | 0      | Ready — indexed by company + recommendation type   |
| `enterprise_profiles` | 0     | Ready — unique index on company_id                 |
| `webhook_logs`    | 0         | Ready — indexed by processed status                |
| `decision_rules`  | 0         | Ready — indexed by module + enabled status         |
| `rate_limits`     | 0+        | IP-based rate limit tracking                       |

**Total Collections**: 13 with production-ready indexes and TTL policies.

---

## 5. Demo Summary — Sprint 1 Delivered Features

| # | Feature Area                     | Endpoints Demonstrated | Story Points | Verdict         |
|---|----------------------------------|------------------------|--------------|-----------------|
| 1 | Registration & Login             | 5 endpoints            | 8            | ✅ Fully Working |
| 2 | Two-Factor Authentication        | 3 endpoints            | 5            | ✅ Fully Working |
| 3 | Role-Based Access Control        | 3 endpoints            | 8            | ✅ Fully Working |
| 4 | Real-Time KPI Dashboard          | 3 endpoints + WS       | 8            | ✅ Fully Working |
| 5 | AI Insights & Copilot            | 4 endpoints            | 8            | ✅ Fully Working |
| 6 | Risk Scoring & Fraud Detection   | 4 endpoints            | 8            | ✅ Fully Working |
| 7 | Compliance & Audit Trail         | 2 endpoints            | 5            | ✅ Fully Working |
| 8 | Budget & Dynamic Pricing         | 2 endpoints            | 5            | ✅ Fully Working |
| 9 | Lead Scoring & Inventory         | 2 endpoints            | 5            | ✅ Fully Working |
| 10| System Health & Deployment       | 3 endpoints + configs  | 8            | ✅ Fully Working |
|   | **Total**                        | **31+ endpoints**      | **68 pts**   | **10/10 Done**  |

---

## 6. Q&A / Stakeholder Feedback

**Questions anticipated:**

| Question                                             | Answer Summary                                                      |
|------------------------------------------------------|---------------------------------------------------------------------|
| How is data persisted?                               | MongoDB 8.2 (13 collections, TTL indexes, materialized views)      |
| What if Redis goes down?                             | Graceful fallback to in-memory dict — zero downtime                |
| How are tokens secured?                              | JWT HS256 (30-min TTL) + refresh rotation (7-day) + device binding |
| What ML model is used for fraud?                     | Isolation Forest (scikit-learn) — unsupervised, no labeled data needed |
| Can this scale horizontally?                         | K8s 3-replica deployment ready; stateless backend allows scaling   |
| What's the test coverage?                            | 14 tests (5 unit + 9 integration), all passing — improving Sprint 2 |

---

*Document Version 1.0 — Sprint 1 Demo | April 12, 2026*
