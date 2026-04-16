# Test Case Report — IBMS (Integrated Business Management Suite)

| Field              | Detail                                              |
|--------------------|-----------------------------------------------------|
| **Project Name**   | Integrated Business Management Suite (IBMS) v2.0    |
| **Team**           | Shivansh Srivastava (Product Developer), Prahallad Padhan (Product Owner), Ranveer Rai Khare (Scrum Master) |
| **Sprint**         | Sprint 1                                            |
| **Date**           | April 14, 2026                                      |
| **Document Type**  | Test Case Execution Report                          |
| **Test Framework** | pytest (Python 3.11)                                |
| **Quality Gate**   | 100% pass rate on critical/high priority tests      |

---

## 1. Executive Summary

This report documents the test execution results for IBMS Sprint 1. The test suite covers **unit tests** for core security (JWT authentication) and AI services (AI assistant), as well as a comprehensive set of **planned integration and system tests** mapped to the full API surface. All implemented tests pass successfully. Additional test scenarios are identified for Sprint 2 implementation.

| Metric                     | Value          |
|----------------------------|----------------|
| Total Test Cases Defined   | 38             |
| Tests Implemented & Executed | 5            |
| Tests Passed               | 5              |
| Tests Failed               | 0              |
| Tests Planned (Sprint 2+)  | 33             |
| Pass Rate (Executed)       | **100%**       |
| Code Coverage (Estimated)  | ~15% (security + AI assistant modules) |
| Target Coverage (Sprint 4) | 80%            |

---

## 2. Test Environment

### 2.1 Environment Configuration

| Component          | Configuration                                          |
|--------------------|--------------------------------------------------------|
| Python Version     | 3.11                                                   |
| Test Runner        | pytest                                                 |
| Test Path          | `apps/ibms_core/tests/`                                |
| Mock Strategy      | Frappe ORM mocked via `SimpleNamespace` in `conftest.py` |
| Database           | Mocked (no live DB required for unit tests)            |
| CI Integration     | GitHub Actions (planned)                               |

### 2.2 Test Fixtures (`conftest.py`)

| Fixture/Mock        | Purpose                                                         |
|---------------------|-----------------------------------------------------------------|
| `ROOT` / `APP_PATH` | Adds `apps/ibms_core` to `sys.path` for module resolution       |
| `fake_cache`        | Mock Frappe cache — `get_value()`, `set_value()` return `None`  |
| `fake_frappe`       | Mock Frappe ORM — `get_all()`, `cache()`, `session`, `has_permission()`, `throw()` |
| Module injection    | Injects mock `frappe` into `sys.modules` when not in Frappe bench |

---

## 3. Test Suite Results — JWT Authentication

**Module Under Test**: `ibms_core.security.jwt_auth`
**Source File**: `apps/ibms_core/ibms_core/security/jwt_auth.py`
**Functions Tested**: `issue_token()`, `validate_token()`, `decode_token()`

### TC-AUTH-001: Token Issue and Validate Round Trip

| Field              | Detail                                                          |
|--------------------|-----------------------------------------------------------------|
| **Test ID**        | TC-AUTH-001                                                     |
| **Test Name**      | `test_issue_and_validate_token_round_trip`                      |
| **Objective**      | Verify JWT token issuance and validation with matching secret   |
| **Preconditions**  | `jwt_auth` module imported                                      |
| **Steps**          | 1. Issue token for `alice@example.com` (secret: `secret-1`, TTL: 3600s) |
|                    | 2. Validate token with the same secret                          |
| **Expected**       | `validate_token()` returns `True`                               |
| **Actual**         | `True`                                                          |
| **Status**         | ✅ PASS                                                         |
| **Priority**       | Critical                                                        |
| **Type**           | Unit — Positive                                                 |

### TC-AUTH-002: Token Payload Contains Subject and Type

| Field              | Detail                                                          |
|--------------------|-----------------------------------------------------------------|
| **Test ID**        | TC-AUTH-002                                                     |
| **Test Name**      | `test_decode_token_contains_subject_and_type`                   |
| **Objective**      | Verify decoded JWT payload includes `sub` and `token_type`      |
| **Preconditions**  | `jwt_auth` module imported                                      |
| **Steps**          | 1. Issue token for `bob@example.com` (type: `access`)           |
|                    | 2. Decode and assert `sub` == `bob@example.com`                 |
|                    | 3. Assert `token_type` == `access`                              |
| **Expected**       | Payload contains correct `sub` and `token_type` claims          |
| **Actual**         | Both assertions pass                                            |
| **Status**         | ✅ PASS                                                         |
| **Priority**       | Critical                                                        |
| **Type**           | Unit — Positive                                                 |

### TC-AUTH-003: Token Validation Fails with Wrong Secret

| Field              | Detail                                                          |
|--------------------|-----------------------------------------------------------------|
| **Test ID**        | TC-AUTH-003                                                     |
| **Test Name**      | `test_validate_token_fails_with_wrong_secret`                   |
| **Objective**      | Verify token rejection when validated with incorrect secret     |
| **Preconditions**  | `jwt_auth` module imported                                      |
| **Steps**          | 1. Issue token for `eve@example.com` (secret: `good-secret`)   |
|                    | 2. Validate with `bad-secret`                                   |
| **Expected**       | `validate_token()` returns `False`                              |
| **Actual**         | `False`                                                         |
| **Status**         | ✅ PASS                                                         |
| **Priority**       | Critical                                                        |
| **Type**           | Unit — Negative (Security)                                      |

---

## 4. Test Suite Results — AI Assistant Service

**Module Under Test**: `ibms_core.services.ai_assistant`
**Source File**: `apps/ibms_core/ibms_core/services/ai_assistant.py`
**Functions Tested**: `ask_assistant()`, `recommend_actions()`

### Mock Data

| DocType             | Mock Data                                                         |
|---------------------|-------------------------------------------------------------------|
| KPI Snapshot        | `risk_exposure: 32.1`, `revenue_run_rate: 12,500,000` (2026-03-13) |
| AI Recommendation   | `REC-0001`, code: `WF-REDUCE-APPROVAL-HOPS`, confidence: `0.78`  |

### TC-AI-001: AI Assistant Risk Query

| Field              | Detail                                                          |
|--------------------|-----------------------------------------------------------------|
| **Test ID**        | TC-AI-001                                                       |
| **Test Name**      | `test_assistant_risk_query`                                     |
| **Objective**      | Verify AI assistant returns risk metrics for risk-related query  |
| **Preconditions**  | `ai_assistant.frappe` monkeypatched with `FakeFrappe`           |
| **Steps**          | 1. Patch `ai_assistant.frappe` with `FakeFrappe()`              |
|                    | 2. Call `ask_assistant("show risk details", "Default Company", "alice@example.com")` |
|                    | 3. Assert `risk_metrics` key in result                          |
|                    | 4. Assert ≥ 1 risk metric record                               |
| **Expected**       | Result contains `risk_metrics` with ≥ 1 entry                  |
| **Actual**         | `risk_metrics` present, 1 entry returned                        |
| **Status**         | ✅ PASS                                                         |
| **Priority**       | High                                                            |
| **Type**           | Unit — Positive                                                 |

### TC-AI-002: AI Recommendations Payload

| Field              | Detail                                                          |
|--------------------|-----------------------------------------------------------------|
| **Test ID**        | TC-AI-002                                                       |
| **Test Name**      | `test_recommendations_payload`                                  |
| **Objective**      | Verify `recommend_actions()` returns correct recommendation count and data |
| **Preconditions**  | `ai_assistant.frappe` monkeypatched with `FakeFrappe`           |
| **Steps**          | 1. Patch `ai_assistant.frappe` with `FakeFrappe()`              |
|                    | 2. Call `recommend_actions("Default Company")`                  |
|                    | 3. Assert `count == 1`                                          |
|                    | 4. Assert recommendation code == `WF-REDUCE-APPROVAL-HOPS`     |
| **Expected**       | 1 recommendation returned with code `WF-REDUCE-APPROVAL-HOPS`  |
| **Actual**         | Matches expected                                                |
| **Status**         | ✅ PASS                                                         |
| **Priority**       | High                                                            |
| **Type**           | Unit — Positive                                                 |

---

## 5. Planned Test Cases — Authentication & Authorization

These test cases are defined for Sprint 2 implementation.

### TC-AUTH-004: Login Endpoint — Valid Credentials

| Field              | Detail                                                          |
|--------------------|-----------------------------------------------------------------|
| **Test ID**        | TC-AUTH-004                                                     |
| **Objective**      | Verify `POST /api/auth/login` returns access + refresh tokens with valid credentials |
| **Type**           | Integration                                                     |
| **Priority**       | Critical                                                        |
| **Status**         | 🔲 Planned                                                     |

### TC-AUTH-005: Login Endpoint — Invalid Password

| Field              | Detail                                                          |
|--------------------|-----------------------------------------------------------------|
| **Test ID**        | TC-AUTH-005                                                     |
| **Objective**      | Verify `POST /api/auth/login` returns 401 for wrong password    |
| **Type**           | Integration — Negative                                          |
| **Priority**       | Critical                                                        |
| **Status**         | 🔲 Planned                                                     |

### TC-AUTH-006: Login Rate Limiting

| Field              | Detail                                                          |
|--------------------|-----------------------------------------------------------------|
| **Test ID**        | TC-AUTH-006                                                     |
| **Objective**      | Verify rate limiter blocks after excessive failed login attempts |
| **Type**           | Integration — Security                                          |
| **Priority**       | Critical                                                        |
| **Status**         | 🔲 Planned                                                     |

### TC-AUTH-007: Refresh Token Rotation

| Field              | Detail                                                          |
|--------------------|-----------------------------------------------------------------|
| **Test ID**        | TC-AUTH-007                                                     |
| **Objective**      | Verify `POST /api/auth/refresh` issues new token pair and invalidates old refresh token |
| **Type**           | Integration                                                     |
| **Priority**       | Critical                                                        |
| **Status**         | 🔲 Planned                                                     |

### TC-AUTH-008: RBAC Permission Enforcement

| Field              | Detail                                                          |
|--------------------|-----------------------------------------------------------------|
| **Test ID**        | TC-AUTH-008                                                     |
| **Objective**      | Verify `viewer` role cannot access `POST /api/budget/optimize` (admin/manager only) |
| **Type**           | Integration — Authorization                                     |
| **Priority**       | Critical                                                        |
| **Status**         | 🔲 Planned                                                     |

### TC-AUTH-009: TOTP 2FA Setup and Verification

| Field              | Detail                                                          |
|--------------------|-----------------------------------------------------------------|
| **Test ID**        | TC-AUTH-009                                                     |
| **Objective**      | Verify TOTP setup, confirm, and login with 2FA flow end-to-end  |
| **Type**           | Integration                                                     |
| **Priority**       | High                                                            |
| **Status**         | 🔲 Planned                                                     |

### TC-AUTH-010: Token Expiry Handling

| Field              | Detail                                                          |
|--------------------|-----------------------------------------------------------------|
| **Test ID**        | TC-AUTH-010                                                     |
| **Objective**      | Verify expired JWT tokens are rejected with 401 response        |
| **Type**           | Unit — Negative                                                 |
| **Priority**       | Critical                                                        |
| **Status**         | 🔲 Planned                                                     |

---

## 6. Planned Test Cases — API Endpoints

### TC-API-001: Dashboard KPI Retrieval

| Field              | Detail                                                          |
|--------------------|-----------------------------------------------------------------|
| **Test ID**        | TC-API-001                                                     |
| **Objective**      | Verify `GET /api/dashboard` returns cached KPI snapshot with valid auth |
| **Type**           | Integration                                                     |
| **Priority**       | High                                                            |
| **Status**         | 🔲 Planned                                                     |

### TC-API-002: Risk Scoring

| Field              | Detail                                                          |
|--------------------|-----------------------------------------------------------------|
| **Test ID**        | TC-API-002                                                     |
| **Objective**      | Verify `POST /api/risk/score` returns valid risk score for transaction payload |
| **Type**           | Integration                                                     |
| **Priority**       | High                                                            |
| **Status**         | 🔲 Planned                                                     |

### TC-API-003: Fraud Detection

| Field              | Detail                                                          |
|--------------------|-----------------------------------------------------------------|
| **Test ID**        | TC-API-003                                                     |
| **Objective**      | Verify `POST /api/fraud/detect` returns `requires_review: true` for amount > threshold |
| **Type**           | Integration                                                     |
| **Priority**       | High                                                            |
| **Status**         | 🔲 Planned                                                     |

### TC-API-004: Compliance Check

| Field              | Detail                                                          |
|--------------------|-----------------------------------------------------------------|
| **Test ID**        | TC-API-004                                                     |
| **Objective**      | Verify `POST /api/compliance/check` evaluates controls and returns pass/fail per control |
| **Type**           | Integration                                                     |
| **Priority**       | High                                                            |
| **Status**         | 🔲 Planned                                                     |

### TC-API-005: Budget Optimization

| Field              | Detail                                                          |
|--------------------|-----------------------------------------------------------------|
| **Test ID**        | TC-API-005                                                     |
| **Objective**      | Verify `POST /api/budget/optimize` returns optimized allocations within total constraint |
| **Type**           | Integration                                                     |
| **Priority**       | Medium                                                          |
| **Status**         | 🔲 Planned                                                     |

### TC-API-006: Dynamic Pricing Suggestion

| Field              | Detail                                                          |
|--------------------|-----------------------------------------------------------------|
| **Test ID**        | TC-API-006                                                     |
| **Objective**      | Verify `POST /api/pricing/suggest` returns price within base ± 50% bounds |
| **Type**           | Integration                                                     |
| **Priority**       | Medium                                                          |
| **Status**         | 🔲 Planned                                                     |

### TC-API-007: AI Copilot Q&A

| Field              | Detail                                                          |
|--------------------|-----------------------------------------------------------------|
| **Test ID**        | TC-API-007                                                     |
| **Objective**      | Verify `POST /api/copilot/ask` returns contextual AI response with confidence score |
| **Type**           | Integration                                                     |
| **Priority**       | Medium                                                          |
| **Status**         | 🔲 Planned                                                     |

### TC-API-008: Sales Forecast

| Field              | Detail                                                          |
|--------------------|-----------------------------------------------------------------|
| **Test ID**        | TC-API-008                                                     |
| **Objective**      | Verify `POST /api/forecast` returns time-series forecast with confidence intervals |
| **Type**           | Integration                                                     |
| **Priority**       | Medium                                                          |
| **Status**         | 🔲 Planned                                                     |

### TC-API-009: Digital Twin Simulation

| Field              | Detail                                                          |
|--------------------|-----------------------------------------------------------------|
| **Test ID**        | TC-API-009                                                     |
| **Objective**      | Verify `POST /api/twin/simulate` returns simulation output for valid scenario input |
| **Type**           | Integration                                                     |
| **Priority**       | Medium                                                          |
| **Status**         | 🔲 Planned                                                     |

### TC-API-010: Inventory Prediction

| Field              | Detail                                                          |
|--------------------|-----------------------------------------------------------------|
| **Test ID**        | TC-API-010                                                     |
| **Objective**      | Verify `POST /api/inventory/predict` returns reorder point above safety stock level |
| **Type**           | Integration                                                     |
| **Priority**       | Medium                                                          |
| **Status**         | 🔲 Planned                                                     |

---

## 7. Planned Test Cases — ERP CRUD Operations

### TC-ERP-001: Customer CRUD Lifecycle

| Field              | Detail                                                          |
|--------------------|-----------------------------------------------------------------|
| **Test ID**        | TC-ERP-001                                                     |
| **Objective**      | Verify full Create → Read → Update → Delete cycle on `/api/erp/customers` |
| **Type**           | Integration — CRUD                                              |
| **Priority**       | High                                                            |
| **Status**         | 🔲 Planned                                                     |

### TC-ERP-002: Product CRUD with Low-Stock Alert

| Field              | Detail                                                          |
|--------------------|-----------------------------------------------------------------|
| **Test ID**        | TC-ERP-002                                                     |
| **Objective**      | Verify product CRUD and that `/api/erp/products/low-stock` returns products below threshold |
| **Type**           | Integration                                                     |
| **Priority**       | High                                                            |
| **Status**         | 🔲 Planned                                                     |

### TC-ERP-003: Order Creation and Status Transitions

| Field              | Detail                                                          |
|--------------------|-----------------------------------------------------------------|
| **Test ID**        | TC-ERP-003                                                     |
| **Objective**      | Verify order creation and valid status transitions (pending → confirmed → shipped → delivered) |
| **Type**           | Integration — Workflow                                          |
| **Priority**       | High                                                            |
| **Status**         | 🔲 Planned                                                     |

### TC-ERP-004: Invoice Creation and Payment Processing

| Field              | Detail                                                          |
|--------------------|-----------------------------------------------------------------|
| **Test ID**        | TC-ERP-004                                                     |
| **Objective**      | Verify invoice creation triggers anomaly check event and status update to `paid` |
| **Type**           | Integration — Event-Driven                                      |
| **Priority**       | High                                                            |
| **Status**         | 🔲 Planned                                                     |

### TC-ERP-005: Inventory Movement Tracking

| Field              | Detail                                                          |
|--------------------|-----------------------------------------------------------------|
| **Test ID**        | TC-ERP-005                                                     |
| **Objective**      | Verify `POST /api/erp/inventory/movement` records movement and updates product stock |
| **Type**           | Integration                                                     |
| **Priority**       | High                                                            |
| **Status**         | 🔲 Planned                                                     |

---

## 8. Planned Test Cases — Infrastructure & Monitoring

### TC-INFRA-001: Health Endpoint

| Field              | Detail                                                          |
|--------------------|-----------------------------------------------------------------|
| **Test ID**        | TC-INFRA-001                                                   |
| **Objective**      | Verify `GET /api/health` returns 200 with Redis, MongoDB, MariaDB status fields |
| **Type**           | Integration — Infrastructure                                    |
| **Priority**       | High                                                            |
| **Status**         | 🔲 Planned                                                     |

### TC-INFRA-002: WebSocket KPI Stream

| Field              | Detail                                                          |
|--------------------|-----------------------------------------------------------------|
| **Test ID**        | TC-INFRA-002                                                   |
| **Objective**      | Verify `WS /ws/kpi` authenticates, streams KPI updates, and handles ping/pong |
| **Type**           | Integration — WebSocket                                         |
| **Priority**       | High                                                            |
| **Status**         | 🔲 Planned                                                     |

### TC-INFRA-003: Redis Failover Graceful Degradation

| Field              | Detail                                                          |
|--------------------|-----------------------------------------------------------------|
| **Test ID**        | TC-INFRA-003                                                   |
| **Objective**      | Verify system falls back to in-memory cache when Redis is unavailable |
| **Type**           | Integration — Resilience                                        |
| **Priority**       | Medium                                                          |
| **Status**         | 🔲 Planned                                                     |

### TC-INFRA-004: CORS Header Validation

| Field              | Detail                                                          |
|--------------------|-----------------------------------------------------------------|
| **Test ID**        | TC-INFRA-004                                                   |
| **Objective**      | Verify CORS headers are correctly set and reject unauthorized origins |
| **Type**           | Integration — Security                                          |
| **Priority**       | Medium                                                          |
| **Status**         | 🔲 Planned                                                     |

### TC-INFRA-005: Security Headers

| Field              | Detail                                                          |
|--------------------|-----------------------------------------------------------------|
| **Test ID**        | TC-INFRA-005                                                   |
| **Objective**      | Verify responses include `X-Content-Type-Options`, `X-Frame-Options`, `X-XSS-Protection`, `Referrer-Policy` headers |
| **Type**           | Integration — Security                                          |
| **Priority**       | Medium                                                          |
| **Status**         | 🔲 Planned                                                     |

### TC-INFRA-006: Audit Log Recording

| Field              | Detail                                                          |
|--------------------|-----------------------------------------------------------------|
| **Test ID**        | TC-INFRA-006                                                   |
| **Objective**      | Verify sensitive actions (login, role change, data delete) produce audit log entries |
| **Type**           | Integration — Compliance                                        |
| **Priority**       | High                                                            |
| **Status**         | 🔲 Planned                                                     |

---

## 9. Test Execution Summary

### 9.1 Results by Module

| Module                  | Total | Passed | Failed | Skipped | Pass Rate |
|-------------------------|-------|--------|--------|---------|-----------|
| JWT Authentication      | 3     | 3      | 0      | 0       | 100%      |
| AI Assistant Service    | 2     | 2      | 0      | 0       | 100%      |
| **Total (Executed)**    | **5** | **5**  | **0**  | **0**   | **100%**  |

### 9.2 Results by Priority

| Priority  | Total | Passed | Planned | Pass Rate (Executed) |
|-----------|-------|--------|---------|----------------------|
| Critical  | 10    | 3      | 7       | 100%                 |
| High      | 18    | 2      | 16      | 100%                 |
| Medium    | 10    | 0      | 10      | —                    |
| **Total** | **38**| **5**  | **33**  | **100%**             |

### 9.3 Results by Type

| Type                     | Executed | Planned |
|--------------------------|----------|---------|
| Unit — Positive          | 4        | 0       |
| Unit — Negative          | 1        | 1       |
| Integration              | 0        | 19      |
| Integration — Security   | 0        | 4       |
| Integration — CRUD       | 0        | 1       |
| Integration — Workflow   | 0        | 1       |
| Integration — Event      | 0        | 1       |
| Integration — Resilience | 0        | 1       |
| Integration — Compliance | 0        | 1       |
| Integration — WebSocket  | 0        | 1       |
| Integration — Authorization | 0     | 1       |
| Integration — Infrastructure | 0    | 1       |

---

## 10. Defects Found

No defects were found during Sprint 1 test execution. All 5 executed tests passed on first run.

---

## 11. Test Coverage Gaps & Recommendations

| Gap Area | Current State | Recommendation | Sprint Target |
|----------|--------------|----------------|---------------|
| Auth endpoint integration tests | No integration tests for login/register/refresh | Implement TC-AUTH-004 through TC-AUTH-010 | Sprint 2 |
| API endpoint coverage | Services tested only via unit mocks | Add FastAPI `TestClient` integration tests | Sprint 2 |
| ERP CRUD operations | 0% coverage | Implement TC-ERP-001 through TC-ERP-005 | Sprint 2 |
| WebSocket testing | 0% coverage | Add async WebSocket test using `websockets` library | Sprint 2 |
| Database layer | Only mocked | Add integration tests with test MongoDB/MariaDB containers | Sprint 3 |
| Security headers | Not validated | Automate header validation in CI | Sprint 2 |
| Performance/load | No load tests | Add locust or k6 load tests for critical endpoints | Sprint 3 |
| ML model accuracy | Not measured | Add model evaluation tests with labeled datasets | Sprint 3 |

---

## 12. Approval

| Role              | Name                    | Date           |
|-------------------|-------------------------|----------------|
| Product Developer | Shivansh Srivastava     | April 14, 2026 |
| Product Owner     | Prahallad Padhan        | April 14, 2026 |
| Scrum Master      | Ranveer Rai Khare       | April 14, 2026 |
