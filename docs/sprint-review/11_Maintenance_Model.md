# Maintenance Model — IBMS (Integrated Business Management Suite)

| Field              | Detail                                              |
|--------------------|-----------------------------------------------------|
| **Project Name**   | Integrated Business Management Suite (IBMS) v2.0    |
| **Team**           | Shivansh Srivastava (Product Developer), Prahallad Padhan (Product Owner), Ranveer Rai Khare (Scrum Master) |
| **Sprint**         | Sprint 1                                            |
| **Date**           | April 14, 2026                                      |
| **Document Type**  | Software Maintenance Model                          |

---

## 1. Introduction

This document defines the maintenance model for the IBMS platform, covering all post-deployment activities required to keep the system operational, secure, and aligned with evolving business needs. IBMS is a multi-layered enterprise system spanning FastAPI backend, Frappe framework integration, dual databases (MongoDB + MariaDB), Redis caching, real-time WebSocket streaming, AI/ML services, and multi-cloud deployment (Docker, Kubernetes, AWS, GCP).

The maintenance model follows a **hybrid approach** combining proactive scheduled maintenance with reactive incident response, aligning with IEEE 14764 software maintenance standards.

---

## 2. Maintenance Categories

### 2.1 Overview

| Category | Description | Estimated Effort | Frequency |
|----------|-------------|-----------------|-----------|
| **Corrective** | Bug fixes, defect resolution, incident patches | 30% | As needed (reactive) |
| **Adaptive** | Environment changes, dependency updates, platform migrations | 25% | Monthly / Quarterly |
| **Perfective** | Feature enhancements, performance optimization, UX improvements | 30% | Per sprint (bi-weekly) |
| **Preventive** | Code refactoring, tech debt reduction, proactive hardening | 15% | Monthly |

---

### 2.2 Corrective Maintenance

Corrective maintenance addresses defects discovered in production or through testing.

| Activity | Scope | Trigger | SLA |
|----------|-------|---------|-----|
| Critical bug fix (SEV-1) | System-down, data corruption, security breach | User report, monitoring alert | 4 hours to fix, 1 hour to deploy |
| Major bug fix (SEV-2) | Feature broken, data inconsistency, high error rate | User report, automated tests | 24 hours to fix |
| Minor bug fix (SEV-3) | UI defect, non-critical logic error, edge case | User report, QA testing | Next sprint |
| Cosmetic fix (SEV-4) | Typos, alignment, minor UI issues | User feedback | Backlog |

**Corrective Maintenance Workflow:**
```
Bug Report → Triage (Severity) → Assign → Root Cause Analysis → Fix → Test → Review → Deploy → Verify → Close
```

**IBMS-Specific Corrective Focus Areas:**

| Component | Common Issue Types | Diagnostic Tools |
|-----------|-------------------|-----------------|
| JWT Auth (`security/jwt_auth.py`) | Token expiry edge cases, secret rotation failures | `/api/debug/auth-bench`, audit logs |
| Dual DB Layer (`database/`) | Cross-database inconsistency, connection pool exhaustion | `/api/health`, reconciliation jobs |
| AI Services (`services/`) | False positive anomalies, stale model predictions | AI Alert tracking, confidence metrics |
| WebSocket (`/ws/kpi`) | Connection drops, auth race conditions | WS connection counter in `/api/health` |
| Background Jobs (`jobs/`) | Missed schedules, Frappe queue deadlocks | Frappe scheduler logs, `/api/metrics` |
| Rate Limiter | False rate-limit blocks, Redis fallback misses | Rate limit logs, `/api/system/status` |

---

### 2.3 Adaptive Maintenance

Adaptive maintenance addresses changes in the operating environment, dependencies, and platform requirements.

| Activity | Scope | Schedule | Owner |
|----------|-------|----------|-------|
| Python dependency updates | Update `requirements.txt` packages (FastAPI, Pydantic, Motor, etc.) | Monthly | Developer |
| Frappe framework upgrades | Compatibility testing with upstream Frappe releases | Quarterly | Developer |
| Database engine updates | MongoDB 7.x, MariaDB 10.x patch updates | Quarterly | DevOps |
| Redis version updates | Redis 7.x patch updates, feature adoption | Quarterly | DevOps |
| Docker base image updates | `python:3.11-slim` security patches | Monthly | DevOps |
| Kubernetes version updates | K8s API changes, deprecation handling | Semi-annually | DevOps |
| Cloud provider changes | AWS/GCP service updates, API changes, pricing adjustments | As announced | DevOps |
| SSL/TLS certificate renewal | Nginx TLS certificates for production | Before expiry (auto-renew preferred) | DevOps |
| OS-level security patches | Container base OS CVE patches | Monthly | DevOps |

**Dependency Update Process:**
```
Scan (dependabot/pip-audit) → Evaluate Impact → Update → Test Suite → Staging Deploy → Production Deploy
```

---

### 2.4 Perfective Maintenance

Perfective maintenance implements new features and optimizations planned in the product roadmap.

| Activity | Example | Sprint Allocation |
|----------|---------|-------------------|
| New API endpoints | Additional ERP modules (purchasing, HR, payroll) | Per roadmap |
| AI model improvements | Enhanced anomaly detection, new lead scoring features | Per sprint |
| UI/UX enhancements | Dashboard redesign, mobile responsiveness, accessibility | Per sprint |
| Performance optimization | Query optimization, caching strategy improvements | Per sprint |
| New integrations | Additional webhook providers, SSO providers, payment gateways | Per roadmap |
| Reporting enhancements | New KPI metrics, custom report builder, export formats | Per sprint |

**Feature Delivery Workflow:**
```
User Story → Sprint Planning → Design → Implement → Unit Test → Integration Test → Code Review → Staging → UAT → Production
```

---

### 2.5 Preventive Maintenance

Preventive maintenance proactively addresses tech debt and structural weaknesses before they become incidents.

| Activity | Scope | Schedule | Benefit |
|----------|-------|----------|---------|
| Code quality audits | Lint, type checking, complexity analysis | Monthly | Reduce bug density |
| Database index optimization | Analyze slow queries, add/remove indexes | Monthly | Improve response times |
| Log rotation and archival | Rotate `audit_logs`, `kpi_snapshots`, `webhook_logs` | Weekly (automated) | Prevent storage exhaustion |
| Security vulnerability scanning | `pip-audit`, `safety`, container image scanning | Per commit (CI) | Prevent known CVE exposure |
| Dead code removal | Remove unused endpoints, deprecated services | Quarterly | Reduce attack surface |
| Configuration drift detection | Compare running config vs source-of-truth | Monthly | Prevent misconfiguration |
| Load testing | Simulate peak traffic against staging | Quarterly | Validate capacity planning |
| Backup integrity verification | Restore test from MongoDB/MariaDB backups | Monthly | Ensure recoverability |

---

## 3. Maintenance Infrastructure

### 3.1 Existing Automated Maintenance Systems

IBMS already includes several automated maintenance capabilities:

| System | Component | Function | Schedule |
|--------|-----------|----------|----------|
| KPI Refresh | `jobs/nightly_kpi_refresh.py` | Full KPI metric recalculation | Daily at 3:00 AM |
| KPI Rollup | `jobs/kpi_rollup.py` | Hourly metric aggregation | Every hour |
| Compliance Audit | `jobs/compliance_check.py` | Automated compliance checks + recommendations | Daily at 3:30 AM |
| Workflow Optimization | `jobs/auto_workflow_optimizer.py` | Analyze and optimize workflow configurations | Weekly |
| Model Retraining | `jobs/retrain_models.py` | Retrain ML models with latest data | Daily at 2:00 AM |
| Webhook Processing | `jobs/process_webhook_queue.py` | Process queued webhook deliveries | Continuous |
| Health Monitoring | `GET /api/health` | Redis, MongoDB, MariaDB health probes | Every 15s (K8s) |
| Request Metrics | `monitoring/metrics.py` | Request counting and performance tracking | Continuous |
| Trace Generation | `monitoring/tracing.py` | UUID-based request tracing | Per request |

### 3.2 Monitoring Infrastructure

| Tool/Endpoint | Purpose | Access |
|---------------|---------|--------|
| `/api/health` | Service health (Redis, MongoDB, MariaDB, uptime, error rate) | Public (unauthenticated) |
| `/api/metrics` | Request/error counters | Authenticated |
| `/api/system/status` | Per-endpoint latency stats, detailed system health | Authenticated (admin) |
| `/api/audit/log` | Audit trail for security events | Authenticated (`audit.view` permission) |
| K8s Readiness/Liveness | `/api/method/ping` (15s interval, 5s timeout) | K8s internal |
| Docker Healthcheck | `curl /api/health` (30s interval) | Docker internal |

### 3.3 Deployment Pipeline

| Stage | Tool | Purpose |
|-------|------|---------|
| Code Quality | `pre-commit`, `ruff`, `black` | Lint and format enforcement |
| Unit Tests | `pytest` | Automated test execution |
| Security Scan | `pip-audit`, `safety` | Dependency vulnerability scanning |
| Build | Docker | Container image creation |
| Staging Deploy | Docker Compose / K8s | Pre-production validation |
| Production Deploy | K8s rolling update / GCP Cloud Run | Zero-downtime deployment |
| Post-Deploy Verify | `/api/health` + smoke tests | Production health validation |

---

## 4. Maintenance Schedules

### 4.1 Daily Maintenance (Automated)

| Time (UTC) | Activity | Component |
|------------|----------|-----------|
| 02:00 | ML model retraining | `jobs/retrain_models.py` |
| 03:00 | Full KPI metric refresh | `jobs/nightly_kpi_refresh.py` |
| 03:30 | Compliance audit scan | `jobs/compliance_check.py` |
| Continuous | Webhook queue processing | `jobs/process_webhook_queue.py` |
| Continuous | KPI streaming to WebSocket clients | `server.py` background scheduler |
| Every hour | KPI metric rollup/aggregation | `jobs/kpi_rollup.py` |

### 4.2 Weekly Maintenance

| Day | Activity | Owner |
|-----|----------|-------|
| Monday | Review error rate trends from `/api/metrics` | Developer |
| Monday | Automated workflow optimization | `jobs/auto_workflow_optimizer.py` |
| Wednesday | Review AI alert false positive rates | Developer |
| Friday | Review webhook delivery success rates | Developer |
| Friday | Sprint retrospective and maintenance backlog grooming | Team |

### 4.3 Monthly Maintenance

| Activity | Owner | Duration |
|----------|-------|----------|
| Dependency security scan and update | Developer | 4 hours |
| Database index performance review | Developer | 2 hours |
| MongoDB collection size audit and archival | DevOps | 2 hours |
| Docker base image update | DevOps | 2 hours |
| Configuration drift check | DevOps | 1 hour |
| Backup restore verification | DevOps | 2 hours |
| Code quality metrics review (complexity, duplication) | Developer | 2 hours |

### 4.4 Quarterly Maintenance

| Activity | Owner | Duration |
|----------|-------|----------|
| Frappe framework compatibility upgrade | Developer | 8 hours |
| Database engine patch updates (MongoDB, MariaDB, Redis) | DevOps | 4 hours |
| Load/stress testing on staging | Developer + DevOps | 8 hours |
| Full security audit (OWASP Top 10 review) | Developer | 8 hours |
| Dead code and unused dependency cleanup | Developer | 4 hours |
| Disaster recovery drill (backup restore + failover) | Team | 4 hours |
| RMMM plan review and risk re-assessment | Team | 2 hours |

---

## 5. Change Management Process

### 5.1 Change Categories

| Category | Examples | Approval Required | Testing Required |
|----------|---------|-------------------|-----------------|
| **Standard** | Config changes, minor bug fixes, dependency patches | Developer self-approval | Unit tests pass |
| **Normal** | New features, API changes, schema changes | Code review + Scrum Master | Full test suite + staging |
| **Emergency** | Security patches, critical bug fixes, incident response | Fast-track: Developer + Product Owner verbal | Targeted tests + post-deploy monitoring |

### 5.2 Change Request Workflow

```
Change Request → Impact Assessment → Approval → Implementation → Testing → Staging → Production → Post-Implementation Review
```

### 5.3 Rollback Strategy

| Deployment Type | Rollback Method | RTO |
|----------------|-----------------|-----|
| Docker Compose | `docker compose down && docker compose up` with previous image tag | 5 minutes |
| Kubernetes | `kubectl rollout undo deployment/ibms-core` | 2 minutes |
| GCP Cloud Run | Revert to previous revision via Cloud Console | 3 minutes |
| Database Schema | Run reverse migration script (Alembic downgrade / mongomigrate rollback) | 15 minutes |

---

## 6. Component Maintenance Matrix

### 6.1 Backend Components

| Component | File/Module | Maintenance Focus | Update Frequency |
|-----------|------------|-------------------|-----------------|
| FastAPI Server | `server.py` | Endpoint additions, middleware updates, security patches | Per sprint |
| Auth Engine | `security/auth_engine.py` | Password policy updates, rate limit tuning, RBAC changes | Monthly |
| JWT Auth | `security/jwt_auth.py` | Secret rotation, algorithm updates, expiry policy | Quarterly |
| Zero Trust | `security/zero_trust.py` | Service identity rules, network policy updates | Quarterly |
| AI Assistant | `services/ai_assistant.py` | NLP improvements, KPI context expansion | Per sprint |
| Anomaly Detection | `services/anomaly.py` | Model retraining, threshold calibration | Monthly (auto) |
| Fraud Detection | `services/fraud_detection.py` | Scoring model updates, threshold adjustments | Monthly |
| Decision Engine | `services/decision_engine.py` | Rule additions, threshold tuning | Per sprint |
| KPI Engine | `services/kpi_engine.py` | New metric definitions, computation logic | Per sprint |
| Dynamic Pricing | `services/dynamic_pricing.py` | Pricing formula updates, market factor weights | Monthly |
| Lead Scoring | `services/lead_scoring.py` | Scoring weight adjustments, new signal types | Monthly |
| Predictive Inventory | `services/predictive_inventory.py` | Demand model updates, safety stock calibration | Monthly |
| Risk Scoring Engine | `risk_scoring_engine.py` | Risk factor weights, new risk indicators | Monthly |
| Compliance Engine | `compliance_engine.py` | Regulatory rule updates, new compliance frameworks | Quarterly |
| Budget Optimizer | `auto_budget_optimizer.py` | Optimization algorithm refinement | Quarterly |
| Digital Twin | `digital_twin.py` | Simulation model updates, new scenario types | Quarterly |

### 6.2 Database Components

| Component | Technology | Maintenance Focus | Schedule |
|-----------|-----------|-------------------|----------|
| MongoDB | Motor + PyMongo | Index optimization, TTL policies, collection sharding | Monthly |
| MariaDB | SQLAlchemy + aiomysql | Schema migrations, query optimization, backup testing | Monthly |
| Redis | redis-py | Memory policy tuning, eviction strategy, persistence config | Quarterly |

### 6.3 Frontend Components

| Component | File | Maintenance Focus | Schedule |
|-----------|------|-------------------|----------|
| SPA Dashboard | `frontend/index.html` | Feature additions, accessibility, responsiveness | Per sprint |
| JavaScript App | `frontend/static/js/app.js` | New dashboard tabs, WebSocket enhancements, bug fixes | Per sprint |
| CSS/Tailwind | `frontend/static/css/` | Theme updates, design system maintenance | Per sprint |

### 6.4 Infrastructure Components

| Component | Configuration | Maintenance Focus | Schedule |
|-----------|--------------|-------------------|----------|
| Docker | `Dockerfile`, `docker-compose.yml` | Base image updates, security patches, optimization | Monthly |
| Docker Prod | `docker-compose.prod.yml` | Secret management, resource limits, SSL certs | Monthly |
| Kubernetes | `deploy/k8s/` | Manifest updates, resource right-sizing, HPA tuning | Quarterly |
| Nginx | `nginx.conf` | TLS config, rate limiting, header policies | Quarterly |
| AWS Terraform | `deploy/aws/terraform/` | Provider updates, resource changes, cost optimization | Quarterly |
| GCP Terraform | `deploy/gcp/terraform/` | Provider updates, service configuration | Quarterly |

---

## 7. Knowledge Management

### 7.1 Documentation Maintenance

| Document | Purpose | Update Trigger |
|----------|---------|---------------|
| `README.md` | Project overview, quickstart | Major feature additions |
| `ARCHITECTURE.md` | System architecture diagram | Architectural changes |
| `API_DOCUMENTATION.md` | API reference | Endpoint additions/changes |
| `SECURITY_OVERVIEW.md` | Security posture | Security control changes |
| `DEPLOYMENT_GUIDE.md` | Deployment procedures | Infrastructure changes |
| `docs/system_blueprint.md` | System design blueprint | Design changes |
| Sprint review docs (`docs/sprint-review/`) | Sprint deliverables and decisions | Every sprint |

### 7.2 Runbook Requirements

| Runbook Topic | Status | Priority |
|---------------|--------|----------|
| Incident response (SEV-1/SEV-2) | Planned | Critical |
| Database backup and restore | Planned | Critical |
| JWT secret rotation procedure | Planned | High |
| Kubernetes scaling and failover | Planned | High |
| MongoDB collection maintenance (TTL, archival) | Planned | Medium |
| New developer onboarding | Planned | Medium |

---

## 8. Maintenance Metrics & KPIs

| Metric | Target | Measurement |
|--------|--------|-------------|
| Mean Time to Repair (MTTR) — SEV-1 | < 4 hours | Incident tracker |
| Mean Time to Repair (MTTR) — SEV-2 | < 24 hours | Incident tracker |
| System Uptime | ≥ 99.5% | `/api/health` monitoring |
| Deployment Success Rate | ≥ 95% | CI/CD pipeline metrics |
| Test Pass Rate | 100% (critical/high) | pytest CI reports |
| Dependency CVE Exposure | 0 critical, < 5 high | `pip-audit` monthly scan |
| Change Failure Rate | < 10% | Post-deploy incident correlation |
| Mean Time Between Failures (MTBF) | > 720 hours | Incident frequency analysis |
| Code Quality Score | A (SonarQube or similar) | Monthly scan |
| Documentation Currency | Updated within 1 sprint of change | Manual review |

---

## 9. Maintenance Roles & Responsibilities

| Role | Responsibilities |
|------|-----------------|
| **Product Developer** | Corrective fixes, perfective enhancements, code quality, test maintenance, dependency updates, model retraining oversight |
| **Product Owner** | Change prioritization, feature roadmap alignment, user feedback triage, maintenance budget allocation |
| **Scrum Master** | Process enforcement, sprint planning for maintenance items, escalation management, team capacity planning |
| **DevOps** (future) | Infrastructure maintenance, deployment automation, monitoring, backup management, security patching |

---

## 10. End-of-Life (EOL) Planning

| Consideration | Plan |
|---------------|------|
| Data retention policy | KPI Snapshots: 2 years active + 5 years archived. Audit logs: 7 years. Webhook logs: 90 days. |
| Data export | Provide API and CLI tools for bulk data export in JSON/CSV format |
| Migration path | Document data schema and API contracts for successor system integration |
| User notification | 6-month advance notice for any module deprecation |
| Dependency EOL tracking | Monitor Python, FastAPI, Frappe, MongoDB, MariaDB, Redis EOL timelines |

---

## 11. Approval

| Role              | Name                    | Date           |
|-------------------|-------------------------|----------------|
| Product Developer | Shivansh Srivastava     | April 14, 2026 |
| Product Owner     | Prahallad Padhan        | April 14, 2026 |
| Scrum Master      | Ranveer Rai Khare       | April 14, 2026 |
