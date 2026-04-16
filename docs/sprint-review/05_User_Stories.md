# User Stories — IBMS (Integrated Business Management Suite)

| Field              | Detail                                              |
|--------------------|-----------------------------------------------------|
| **Project Name**   | Integrated Business Management Suite (IBMS) v2.0    |
| **Team**           | Shivansh Srivastava (Product Developer), Prahallad Padhan (Product Owner), Ranveer Rai Khare (Scrum Master) |
| **Sprint**         | Sprint 1                                            |
| **Date**           | April 9, 2026                                       |
| **Total Stories**   | 10                                                  |

---

## US-01: User Registration & Secure Login

**As a** new employee,  
**I want to** register an account and securely log in to the IBMS platform,  
**So that** I can access business tools and dashboards assigned to my role.

**Priority**: Critical | **Story Points**: 8

### Acceptance Criteria / Checklist

- [x] User can register with username, email, and password
- [x] Password strength is validated in real-time (min 8 chars, mixed case, numeric, special chars)
- [x] Common/weak passwords are rejected (blacklist: `password`, `123456`, `admin`, etc.)
- [x] Passwords are hashed with bcrypt (12 rounds) before storage
- [x] User can log in with username and password
- [x] Successful login returns a JWT access token (30-min TTL) and refresh token (7-day TTL, HTTP-only cookie)
- [x] A CSRF token is returned alongside the access token
- [x] Device fingerprint (user-agent, timezone, screen resolution) is captured and bound to the session
- [x] Failed login attempts are tracked per IP for brute-force protection
- [x] Login error messages do not reveal whether username or password was incorrect
- [x] Frontend displays auth overlay with login and registration forms
- [x] Frontend shows inline password strength meter during registration

---

## US-02: Two-Factor Authentication (2FA)

**As a** security-conscious user,  
**I want to** enable TOTP-based two-factor authentication on my account,  
**So that** my account is protected even if my password is compromised.

**Priority**: High | **Story Points**: 5

### Acceptance Criteria / Checklist

- [x] Authenticated user can call `/api/auth/2fa/setup` to generate a TOTP secret
- [x] Setup returns a provisioning URI suitable for QR scanning in authenticator apps (Google Authenticator, Authy)
- [x] User confirms 2FA by submitting a valid 6-digit TOTP code to `/api/auth/2fa/confirm`
- [x] Once enabled, login requires the TOTP code in addition to username/password
- [x] TOTP validation allows ±1 time-step window tolerance (30-second steps)
- [x] User can disable 2FA via `/api/auth/2fa/disable` when authenticated
- [x] Frontend login form dynamically shows the 2FA code input field when required
- [x] Invalid or missing TOTP code during login returns a clear error message

---

## US-03: Role-Based Dashboard Access

**As an** administrator,  
**I want to** assign roles to users so they see only the features and data they are authorized to access,  
**So that** sensitive business information is restricted based on responsibility level.

**Priority**: Critical | **Story Points**: 8

### Acceptance Criteria / Checklist

- [x] Five roles are defined: `super_admin`, `admin`, `manager`, `analyst`, `viewer`
- [x] Role hierarchy supports permission inheritance (e.g., `manager` inherits from `analyst`, which inherits from `viewer`)
- [x] `super_admin` has wildcard (`*`) access to all endpoints and features
- [x] `viewer` role is restricted to `dashboard.view` and `kpi.view` only
- [x] `analyst` can access reports, AI insights, risk view, compliance view, forecast, and copilot
- [x] `manager` adds export, manage, and approve permissions on top of analyst
- [x] `/api/auth/roles` endpoint lists all roles with their permission sets
- [x] `/api/auth/me` returns the current user's resolved permissions
- [x] Audit log endpoint (`/api/audit/log`) requires `audit.view` permission
- [x] Unauthorized access attempts return `403 Forbidden` with no data leakage
- [x] Frontend sidebar navigation shows/hides pages based on user permissions

---

## US-04: Real-Time KPI Dashboard

**As a** business manager,  
**I want to** view a live dashboard of key performance indicators that updates automatically,  
**So that** I can monitor business health in real-time without manually refreshing.

**Priority**: Critical | **Story Points**: 8

### Acceptance Criteria / Checklist

- [x] `/api/dashboard` returns current KPI snapshot (revenue, net margin, risk exposure, forecast accuracy, compliance score, alerts, fraud blocked, efficiency, customer satisfaction)
- [x] `/api/dashboard/history` returns historical KPI data points for trend charts
- [x] WebSocket endpoint `/ws/kpi` pushes KPI updates to connected clients automatically every 15 seconds
- [x] WebSocket supports `refresh` message type for on-demand KPI update
- [x] WebSocket supports `ping/pong` heartbeat for connection health monitoring
- [x] Frontend displays KPI cards with animated counters and 3D tilt spotlight effects
- [x] Chart.js is integrated for forecast, analytics, and KPI history trend charts
- [x] WebSocket auto-reconnects with exponential backoff on disconnection
- [x] Connection health indicator is visible in the UI (connected/disconnected states)
- [x] KPI data is cached in Redis (or in-memory fallback) to reduce computation overhead
- [x] Company-level filtering is supported for multi-entity organizations

---

## US-05: AI-Powered Business Insights & Copilot

**As a** data analyst,  
**I want to** get AI-generated insights and ask natural language questions about business metrics,  
**So that** I can quickly identify trends, anomalies, and actionable opportunities without writing queries.

**Priority**: High | **Story Points**: 8

### Acceptance Criteria / Checklist

- [x] `/api/ai/insights` returns the top 4 AI-generated business insights (anomalies, trends, predictions, recommendations)
- [x] `/api/ai/anomalies` returns currently active anomalies detected in transaction volume and metrics
- [x] `/api/copilot/ask` accepts a natural language query and returns context-aware responses spanning KPI, risk, forecast, and compliance data
- [x] AI assistant can process risk-related queries and return risk metrics from KPI snapshots
- [x] `recommend_actions()` generates actionable recommendations with confidence scores and recommendation codes
- [x] Sales forecasting endpoint (`/api/forecast`) returns Prophet Ensemble v2 predictions with confidence interval bands
- [x] Frontend has a dedicated "AI Insights" page accessible from sidebar navigation
- [x] Anomaly detection models can be refreshed on demand
- [x] Invoice anomaly checks can be enqueued asynchronously for background processing

---

## US-06: Risk Scoring & Fraud Detection

**As a** finance controller,  
**I want to** automatically score transactions for risk and detect potential fraud,  
**So that** high-risk or fraudulent transactions are flagged before they cause financial loss.

**Priority**: Critical | **Story Points**: 8

### Acceptance Criteria / Checklist

- [x] `/api/risk/score` calculates a transaction risk score (0–100) with a breakdown of contributing factors
- [x] `/api/risk/composite` computes a weighted composite risk: amount (50%) + behavior (30%) + compliance (20%)
- [x] `/api/fraud/detect` runs Isolation Forest algorithm and returns a fraud score (0–1) with a `flag_for_review` boolean
- [x] High-risk transactions (score > threshold) are flagged for manual review
- [x] Fraud detection integrates isolation forest scoring as the primary ML model
- [x] Frontend has a dedicated "Risk & Fraud" page in the sidebar navigation
- [x] Risk and fraud endpoints return structured JSON responses suitable for downstream workflow automation
- [x] The decision engine (`/api/decision/evaluate`) routes transactions to approve, review, or reject based on risk levels

---

## US-07: Compliance Checking & Audit Trail

**As a** compliance officer,  
**I want to** automatically validate transactions against control policies and maintain a tamper-evident audit trail,  
**So that** the organization meets regulatory requirements and can demonstrate compliance during audits.

**Priority**: High | **Story Points**: 5

### Acceptance Criteria / Checklist

- [x] `/api/compliance/check` evaluates transactions against a control-set (e.g., high-value transactions > ₹500K require an approval reference)
- [x] Compliance result returns `passed: true/false` and a list of specific violation codes (e.g., `MISSING_HIGH_VALUE_APPROVAL`)
- [x] All authentication events (login, logout, 2FA setup, token refresh) are recorded in the audit log
- [x] `/api/audit/log` endpoint returns paginated, filterable audit events (requires `audit.view` permission)
- [x] Audit events are base64-encoded for tamper evidence
- [x] Background compliance check job detects stale webhooks and generates AI recommendations for unprocessed items
- [x] Frontend has a dedicated "Compliance" page and "Audit Log" page in sidebar navigation
- [x] Compliance score is displayed as a KPI on the main dashboard (target: 97%+)

---

## US-08: Budget Optimization & Dynamic Pricing

**As a** department head,  
**I want to** get AI-optimized budget allocations and dynamic pricing recommendations,  
**So that** I can maximize revenue and allocate resources efficiently based on market conditions.

**Priority**: Medium | **Story Points**: 5

### Acceptance Criteria / Checklist

- [x] `/api/budget/optimize` accepts budget line items with amounts and a growth target percentage
- [x] Optimizer returns `current_total` and `optimized_total` (adjusted by growth multiplier)
- [x] `/api/pricing/suggest` accepts demand index, stock level, and competitor pricing data
- [x] Dynamic pricing returns a recommended price using weighted multipliers: demand (+40%), stock (-20%), competitors (+20%)
- [x] Both endpoints return structured JSON suitable for integration with approval workflows
- [x] Frontend has dedicated "Budget Optimizer" and "Dynamic Pricing" pages in sidebar
- [x] Budget approval permission (`budget.approve`) is restricted to `manager` role and above

---

## US-09: Lead Scoring & Inventory Prediction

**As a** sales manager,  
**I want to** automatically score leads and predict inventory reorder points,  
**So that** my team focuses on high-potential leads and we never run out of critical stock.

**Priority**: Medium | **Story Points**: 5

### Acceptance Criteria / Checklist

- [x] `/api/leads/score` calculates a lead qualification score using weighted model: 55% engagement + 45% fit
- [x] Lead score input accepts engagement metrics (email opens, page visits, demo requests) and fit attributes (company size, industry, budget)
- [x] Lead scoring returns a numeric score with a qualification tier (hot/warm/cold)
- [x] `/api/inventory/predict` calculates reorder points using Prophet-based demand forecasting
- [x] Inventory prediction considers lead time, safety stock levels, and demand variability
- [x] Frontend has a dedicated "Lead Scoring" page accessible from sidebar
- [x] Lead management permission (`leads.manage`) is restricted to `manager` role and above

---

## US-10: System Health Monitoring & Deployment

**As a** DevOps engineer,  
**I want to** monitor system health in real-time and deploy the platform across Docker, Kubernetes, and AWS,  
**So that** I can ensure high availability and quickly diagnose issues in any environment.

**Priority**: High | **Story Points**: 8

### Acceptance Criteria / Checklist

- [x] `/api/health` returns system status (`healthy`/`degraded`), Redis connectivity, uptime, total requests, error count, error rate, and WebSocket connection count
- [x] `/api/metrics` returns a snapshot of system metrics (request totals, last refresh timestamp)
- [x] `/api/system/status` returns detailed status including top endpoints by request count, cache state, and uptime
- [x] Every API response includes `X-Trace-Id` (UUID) and `X-Response-Time-Ms` headers for observability
- [x] Security headers (CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy) are applied to all responses
- [x] Docker Compose config orchestrates web (FastAPI), nginx (reverse proxy), and Redis with health checks and restart policies
- [x] Kubernetes manifests deploy 3 replicas with readiness probes (15s delay), liveness probes (45s delay), and resource limits (500m–2 CPU, 1–4Gi memory)
- [x] K8s Ingress routes `ibms.example.com` with TLS termination to the service
- [x] Terraform provisions AWS VPC, RDS MariaDB (Multi-AZ, 100GB, 7-day backup), and ElastiCache Redis (encrypted, auto-failover) in private subnets
- [x] Frontend has a dedicated "System Health" page displaying server status and metrics
- [x] Notification system supports paginated queuing via `/api/notifications`

---

## Summary

| Story ID | Title                                  | Priority | Points | Status |
|----------|----------------------------------------|----------|--------|--------|
| US-01    | User Registration & Secure Login       | Critical | 8      | ✅ Done |
| US-02    | Two-Factor Authentication (2FA)        | High     | 5      | ✅ Done |
| US-03    | Role-Based Dashboard Access            | Critical | 8      | ✅ Done |
| US-04    | Real-Time KPI Dashboard                | Critical | 8      | ✅ Done |
| US-05    | AI-Powered Business Insights & Copilot | High     | 8      | ✅ Done |
| US-06    | Risk Scoring & Fraud Detection         | Critical | 8      | ✅ Done |
| US-07    | Compliance Checking & Audit Trail      | High     | 5      | ✅ Done |
| US-08    | Budget Optimization & Dynamic Pricing  | Medium   | 5      | ✅ Done |
| US-09    | Lead Scoring & Inventory Prediction    | Medium   | 5      | ✅ Done |
| US-10    | System Health Monitoring & Deployment  | High     | 8      | ✅ Done |
|          | **Total Story Points**                 |          | **68** |        |

---

*Document Version 1.0 — Sprint 1*

---
---

# User Stories — IBMS Sprint 2

| Field              | Detail                                              |
|--------------------|-----------------------------------------------------|
| **Project Name**   | Integrated Business Management Suite (IBMS) v2.0    |
| **Team**           | Shivansh Srivastava (Product Developer), Prahallad Padhan (Product Owner), Ranveer Rai Khare (Scrum Master) |
| **Sprint**         | Sprint 2                                            |
| **Date**           | April 16, 2026                                      |
| **Total Stories**  | 10                                                  |

---

## US-11: ERP Core — Customer & Product Management

**As a** sales representative,  
**I want to** create, search, and manage customer and product records through the IBMS platform,  
**So that** I have a centralized view of our customer base and product catalog for order processing.

**Priority**: Critical | **Story Points**: 8

### Acceptance Criteria / Checklist

- [ ] `POST /api/erp/customers` creates a new customer record with name, email, phone, segment, and address
- [ ] `GET /api/erp/customers` lists customers with optional `segment` and `search` query filters
- [ ] `GET /api/erp/customers/{id}` returns a single customer record by ID
- [ ] `PUT /api/erp/customers/{id}` updates an existing customer's details
- [ ] `DELETE /api/erp/customers/{id}` soft-deletes a customer record
- [ ] `GET /api/erp/customers/stats/summary` returns aggregate customer statistics (total count, segment breakdown)
- [ ] `POST /api/erp/products` creates a new product with name, category, price, stock quantity, and reorder level
- [ ] `GET /api/erp/products` lists products with optional `category` and `search` filters
- [ ] `GET /api/erp/products/{id}` returns a single product by ID
- [ ] `PUT /api/erp/products/{id}` updates product details (price, stock, reorder level)
- [ ] `DELETE /api/erp/products/{id}` removes a product record
- [ ] `GET /api/erp/products/stats/summary` returns product statistics (count by category, average price)
- [ ] `GET /api/erp/products/alerts/low-stock` returns products where `stock_quantity` ≤ `reorder_level`
- [ ] All ERP endpoints require at minimum `viewer` role authentication
- [ ] Create, update, and delete operations require `manager` role or above

---

## US-12: ERP Core — Order & Invoice Processing

**As an** operations manager,  
**I want to** create orders with line items, generate invoices, and track their payment status,  
**So that** the full order-to-cash cycle is managed within a single platform.

**Priority**: Critical | **Story Points**: 8

### Acceptance Criteria / Checklist

- [ ] `POST /api/erp/orders` creates an order with customer ID, list of line items (product_id, quantity, unit_price), and auto-calculates `total_amount`
- [ ] Order numbers are auto-generated sequentially (e.g., `ORD-0001`, `ORD-0002`)
- [ ] `GET /api/erp/orders` lists orders with optional `status` and `customer_id` filters
- [ ] `GET /api/erp/orders/{id}` returns order detail including line items
- [ ] `PATCH /api/erp/orders/{id}/status` updates order status (pending → confirmed → shipped → delivered → cancelled)
- [ ] `GET /api/erp/orders/stats/summary` returns order stats (count by status, total revenue)
- [ ] `POST /api/erp/invoices` creates an invoice linked to an order with due date and amount
- [ ] Invoice numbers are auto-generated sequentially (e.g., `INV-0001`, `INV-0002`)
- [ ] `GET /api/erp/invoices` lists invoices with optional `status` and `customer_id` filters
- [ ] `PATCH /api/erp/invoices/{id}/status` updates invoice status and records `paid_amount` on payment
- [ ] `GET /api/erp/invoices/stats/summary` returns invoice stats (total outstanding, total paid, overdue count)
- [ ] `GET /api/erp/overview` returns aggregated statistics across all ERP modules in a single API call

---

## US-13: Employee Management & Inventory Movements

**As an** HR administrator and warehouse manager,  
**I want to** manage employee records and track inventory stock movements (inbound/outbound),  
**So that** staffing data is centralized and stock levels stay accurate across the organization.

**Priority**: High | **Story Points**: 5

### Acceptance Criteria / Checklist

- [ ] `POST /api/erp/employees` creates an employee record with name, email, department, position, and hire date
- [ ] `GET /api/erp/employees` lists employees with optional `department` and `search` filters
- [ ] `GET /api/erp/employees/{id}` returns a single employee record
- [ ] `PUT /api/erp/employees/{id}` updates employee details (department, position, contact info)
- [ ] `GET /api/erp/employees/stats/summary` returns employee stats (count by department, recent hires)
- [ ] Field aliasing maps internal schema (`designation`, `date_of_joining`) to user-friendly names (`position`, `hire_date`)
- [ ] `POST /api/erp/inventory/movements` records an inventory movement with product ID, quantity, type (`IN` or `OUT`), and reason
- [ ] Inventory movement of type `IN` automatically increases the product's `stock_quantity`
- [ ] Inventory movement of type `OUT` automatically decreases the product's `stock_quantity`
- [ ] `GET /api/erp/inventory/movements/{product_id}` returns the movement history for a specific product
- [ ] All employee and inventory operations are access-controlled via RBAC permissions

---

## US-14: Webhook Integration & External System Connectivity

**As a** systems integrator,  
**I want to** receive inbound webhooks from third-party services and register outbound webhooks for IBMS events,  
**So that** the platform can exchange real-time data with external tools (payment gateways, CRMs, shipping providers).

**Priority**: High | **Story Points**: 8

### Acceptance Criteria / Checklist

- [ ] `POST /api/webhooks/ingest` accepts inbound webhook payloads with `provider`, `event_type`, and `payload` fields
- [ ] Inbound webhooks are logged to the `WebhookLog` store with a unique ID and `processed: false` status
- [ ] `POST /api/webhooks/outbound/register` registers an outbound webhook with target `url`, subscribed `event`, and a `secret` for signing
- [ ] Outbound webhooks are delivered with HMAC-SHA256 signature in the `X-Webhook-Signature` header for payload verification
- [ ] Background job drains unprocessed webhook queue in batches of up to 100 entries
- [ ] `WebhookLogOps.mark_processed(log_id)` updates the log entry status after successful processing
- [ ] `WebhookLogOps.find_unprocessed()` retrieves the pending webhook queue for the processor job
- [ ] Event router dispatches `webhook.*` events to the webhook processing pipeline
- [ ] Webhook processing failures are logged without crashing the batch processor
- [ ] OAuth2 provider config endpoint (`GET /api/auth/oauth-config`) returns authorization URL, token URL, and scopes (`openid`, `profile`, `erp.read`, `erp.write`) for external client integration

---

## US-15: Real-Time Notifications & Alert Management

**As a** business user,  
**I want to** receive real-time in-app notifications and view active alerts with severity levels,  
**So that** I am immediately aware of critical events (fraud flags, compliance violations, low stock) without checking each module manually.

**Priority**: High | **Story Points**: 5

### Acceptance Criteria / Checklist

- [ ] `POST` notification creation accepts `title`, `message`, `level` (info/warning/critical), and `target_user`
- [ ] `GET /api/notifications` returns the current user's notifications in reverse chronological order with pagination support
- [ ] Notifications are user-scoped — users only see notifications targeted to them
- [ ] Notifications support `mark as read` functionality
- [ ] `AlertOps.create_alert()` generates system alerts with `title`, `severity`, `risk_score`, and `reference` (linked entity)
- [ ] `AlertOps.find_active()` retrieves all unresolved alerts sorted by severity
- [ ] `AlertOps.resolve_alert(alert_id)` marks an alert as resolved with a timestamp
- [ ] Anomaly detection automatically creates an AI Alert when an invoice anomaly score exceeds threshold (0.75)
- [ ] Login events trigger a fire-and-forget notification push ("Login Successful") to the authenticated user
- [ ] Frontend notification badge updates in real-time via WebSocket push

---

## US-16: AI Recommendation Lifecycle & Workflow Automation

**As a** business analyst,  
**I want to** review AI-generated recommendations through a formal approval workflow (Open → Accepted → Applied or Rejected),  
**So that** AI suggestions are vetted before impacting business operations.

**Priority**: High | **Story Points**: 8

### Acceptance Criteria / Checklist

- [ ] AI recommendations are created with `company`, `module`, `title`, `description`, `confidence`, and `status: Open`
- [ ] `AIRecommendationOps.find_by_company(company, status)` retrieves recommendations filtered by company and optional status
- [ ] `AIRecommendationOps.update_status(rec_id, new_status)` transitions a recommendation through the lifecycle states
- [ ] Recommendation lifecycle enforces valid state transitions: `Open → Accepted`, `Accepted → Applied`, `Open → Rejected`
- [ ] Only users with appropriate roles (AI Admin, Business Analyst, System Manager) can transition recommendation states
- [ ] Auto Workflow Optimizer background job generates new `AI Recommendation` documents (e.g., "Reduce approval chain for low-risk vouchers") when pending recommendation count is low
- [ ] Compliance check background job detects stale webhook logs and generates AI recommendations for unprocessed items
- [ ] GraphQL API (`POST /api/graphql/execute`) supports querying recommendations by company and status with pagination
- [ ] Event router dispatches `ai.recommendation.created` events to trigger user notifications
- [ ] Frontend displays recommendation cards with status badges and action buttons (Accept/Reject/Apply)

---

## US-17: GraphQL API Gateway & Endpoint Discovery

**As a** frontend developer building custom dashboards,  
**I want to** query IBMS data via a flexible GraphQL gateway and discover all available REST endpoints programmatically,  
**So that** I can fetch exactly the data I need in a single request and integrate with the API without consulting external docs.

**Priority**: Medium | **Story Points**: 5

### Acceptance Criteria / Checklist

- [ ] `GET /api/graphql/schema` returns the full SDL (Schema Definition Language) for all exposed GraphQL types
- [ ] `POST /api/graphql/execute` accepts a `query` string and optional `variables` object
- [ ] GraphQL query `kpiSnapshots(company, limit)` returns paginated KPI history with all metric fields
- [ ] GraphQL query `recommendations(company, status, limit)` returns AI recommendations filtered by status
- [ ] GraphQL types include `KPISnapshot` (revenue, margin, risk exposure, compliance score, etc.) and `AIRecommendation` (title, description, confidence, status)
- [ ] Invalid or unsupported GraphQL queries return structured error messages
- [ ] `GET /api/endpoints` returns a self-documenting list of all registered REST routes with their HTTP methods
- [ ] API endpoint listing is accessible without authentication for developer onboarding
- [ ] All API responses include `X-Trace-Id` and `X-Response-Time-Ms` headers for debugging GraphQL and REST calls

---

## US-18: Event-Driven Architecture & Stream Processing

**As a** platform architect,  
**I want to** route internal events to appropriate handlers and process data streams in batches,  
**So that** modules are decoupled and high-throughput workflows (webhook processing, anomaly scanning, KPI aggregation) run asynchronously without blocking the request path.

**Priority**: Medium | **Story Points**: 8

### Acceptance Criteria / Checklist

- [ ] Event router supports topic-based routing with configurable handler mappings
- [ ] `invoice.submitted` events trigger realtime UI publish for live dashboard updates
- [ ] `webhook.*` events are routed to the webhook processing pipeline
- [ ] `ai.recommendation.created` events trigger notification dispatch to target users
- [ ] Stream processor consumes webhook log entries and converts them into structured events via subscriber pattern
- [ ] Batch processing mode processes multiple events per cycle to handle high-volume periods
- [ ] Nightly KPI refresh job runs `refresh_kpis()` for all companies as a scheduled background task
- [ ] ML model retraining job is enqueued on the dedicated `ml-heavy` queue to avoid blocking standard workers
- [ ] Compliance check job runs periodically to detect stale unprocessed items and generate alerts
- [ ] All background jobs log execution metrics (start time, duration, items processed) for observability

---

## US-19: Digital Twin Simulation & Behavioral Analytics

**As a** operations strategist,  
**I want to** run what-if simulations on business entities using a digital twin model and analyze user behavior patterns,  
**So that** I can predict operational outcomes before committing changes and detect abnormal user activity early.

**Priority**: Medium | **Story Points**: 5

### Acceptance Criteria / Checklist

- [ ] `POST /api/twin/simulate` accepts an entity object (any business entity: warehouse, production line, supply chain node)
- [ ] Digital twin returns a `simulation_status`, `confidence_score`, and projected operational metrics
- [ ] Simulation results can be used to compare current vs. projected KPIs before applying changes
- [ ] Behavioral analytics service captures user signals (page views, actions, time-on-page) with metadata
- [ ] `compute_risk_profile(user)` aggregates behavioral signals and returns a per-user risk score
- [ ] Anomalous user behavior (unusual login times, excessive data exports, rapid-fire API calls) contributes to elevated risk profiles
- [ ] Behavioral risk profiles feed into the composite risk scoring engine for holistic risk assessment
- [ ] Digital twin simulation and behavioral data endpoints are restricted to `analyst` role and above

---

## US-20: Enterprise Profile Management & Smart Decision Rules

**As a** system administrator,  
**I want to** manage per-user enterprise profiles and configure smart decision rules that automate routine business logic,  
**So that** user preferences are personalized and approval thresholds, routing rules, and escalation policies are centrally governed without code changes.

**Priority**: Medium | **Story Points**: 5

### Acceptance Criteria / Checklist

- [ ] `ProfileOps.upsert(user_id, profile_data)` creates or updates a user's enterprise profile (stored as JSONB)
- [ ] `ProfileOps.get(user_id)` retrieves the profile for the authenticated user
- [ ] Enterprise profiles support arbitrary data (preferred dashboard layout, notification preferences, default company, timezone)
- [ ] `DecisionRuleOps.create(rule_name, module, threshold, enabled)` defines a new smart decision rule
- [ ] `DecisionRuleOps.find_enabled(module)` returns all active rules for a given module (e.g., "finance", "compliance", "hr")
- [ ] Decision engine (`/api/decision/evaluate`) consults enabled rules to route transactions to approve, review, or reject
- [ ] Rules can be toggled (enabled/disabled) without redeploying the application
- [ ] Rule thresholds are configurable per module (e.g., auto-approve orders below ₹50K, escalate above ₹5L)
- [ ] Profile and rule management endpoints require `admin` role or above
- [ ] Changes to decision rules are recorded in the audit trail for governance

---

## Sprint 2 Summary

| Story ID | Title                                            | Priority | Points | Status      |
|----------|--------------------------------------------------|----------|--------|-------------|
| US-11    | ERP Core — Customer & Product Management         | Critical | 8      | 🔲 Not Started |
| US-12    | ERP Core — Order & Invoice Processing            | Critical | 8      | 🔲 Not Started |
| US-13    | Employee Management & Inventory Movements        | High     | 5      | 🔲 Not Started |
| US-14    | Webhook Integration & External System Connectivity | High   | 8      | 🔲 Not Started |
| US-15    | Real-Time Notifications & Alert Management       | High     | 5      | 🔲 Not Started |
| US-16    | AI Recommendation Lifecycle & Workflow Automation | High    | 8      | 🔲 Not Started |
| US-17    | GraphQL API Gateway & Endpoint Discovery         | Medium   | 5      | 🔲 Not Started |
| US-18    | Event-Driven Architecture & Stream Processing    | Medium   | 8      | 🔲 Not Started |
| US-19    | Digital Twin Simulation & Behavioral Analytics   | Medium   | 5      | 🔲 Not Started |
| US-20    | Enterprise Profile Management & Smart Decision Rules | Medium | 5   | 🔲 Not Started |
|          | **Total Story Points**                           |          | **65** |             |

---

*Document Version 2.0 — Sprint 2*
