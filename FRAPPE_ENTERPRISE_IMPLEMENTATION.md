# IBMS Frappe Enterprise Implementation

## 1. Enterprise Architecture

- Framework: Frappe custom app (`ibms_core`) with modular APIs, jobs, services, events, and UI assets.
- Data: MariaDB (transactional data) + Redis (cache, queue, socketio).
- API: Whitelisted REST endpoints and lightweight GraphQL endpoint.
- Auth: Session auth + JWT (`Authorization: Bearer`) + RBAC + row-level permissions.
- Automation: Scheduler jobs, event-driven webhook processing, real-time desk notifications.
- Deployment: Docker Compose (`docker-compose.frappe.yml`) and Kubernetes manifests in `deploy/k8s`.

## 2. Delivered Modules

### Core Security
- `apps/ibms_core/ibms_core/security/jwt_auth.py`: HS256 JWT issue/verify with iat/nbf/exp/jti.
- `apps/ibms_core/ibms_core/security/auth_hooks.py`: Request auth hook to bind bearer token to Frappe user.
- `apps/ibms_core/ibms_core/security/policies.py`: Row-level security for AI alerts and enterprise profiles.

### APIs
- `apps/ibms_core/ibms_core/api/auth.py`: registration, login, refresh, profile endpoint.
- `apps/ibms_core/ibms_core/api/rest.py`: CRUD + bulk import/export for approved doctypes.
- `apps/ibms_core/ibms_core/api/graphql_api.py`: GraphQL schema and query gateway.
- `apps/ibms_core/ibms_core/api/integrations.py`: inbound webhook ingestion and outbound webhook dispatch.
- `apps/ibms_core/ibms_core/api/ai_assistant.py`: chatbot and recommendation APIs.

### Data Model (Doctypes)
- `Enterprise Profile`: user personalization and profile controls.
- `KPI Snapshot`: analytics time-series records.
- `AI Recommendation`: recommendation lifecycle tracking.
- `Integration Webhook Log`: signed webhook audit and replay support.

### Automation & Eventing
- `apps/ibms_core/ibms_core/jobs/kpi_rollup.py`: periodic KPI aggregation.
- `apps/ibms_core/ibms_core/jobs/process_webhook_queue.py`: queue-driven webhook processing.
- `apps/ibms_core/ibms_core/jobs/auto_workflow_optimizer.py`: generates optimization recommendations.
- `apps/ibms_core/ibms_core/jobs/compliance_check.py`: nightly compliance signal generation.
- `apps/ibms_core/ibms_core/events/stream_processor.py`: log processing and status updates.

### UI/UX
- `apps/ibms_core/ibms_core/public/css/enterprise_theme.css`: modern glassmorphism skin.
- `apps/ibms_core/ibms_core/public/js/enterprise_dashboard.js`: animated dashboard enhancements.
- `apps/ibms_core/ibms_core/public/js/enterprise_profile.js`: Enterprise Profile UX.
- `apps/ibms_core/ibms_core/public/js/kpi_snapshot.js`: KPI validation helper.

### Workflows
- `apps/ibms_core/ibms_core/workflow/ai_recommendation_lifecycle/ai_recommendation_lifecycle.json`

### DevOps
- `docker-compose.frappe.yml`: Frappe + MariaDB + Redis deployment topology.
- `.github/workflows/frappe-enterprise-ci.yml`: lint, type checks, image build.
- `deploy/k8s/*`: deployment, service, and ingress manifests.
- `deploy/aws/terraform/*`: AWS managed infrastructure (VPC, RDS MariaDB, ElastiCache Redis).
- `scripts/bootstrap-frappe-wsl.sh`: one-command WSL2 Frappe bootstrap.
- `scripts/bootstrap-frappe-windows.ps1`: Windows wrapper for WSL bootstrap.
- `scripts/validate-frappe-apis.sh`: API smoke tests.
- `requirements-dev.txt`, `pyproject.toml`, `.pre-commit-config.yaml`: quality and test toolchain.
- `apps/ibms_core/tests/*`: unit tests for security and AI services.

## 3. Installation (Frappe Stack)

1. Create env file:

```bash
cp .env.example .env
```

2. Set required vars in `.env`:

```env
SITE_NAME=ibms.localhost
MYSQL_ROOT_PASSWORD=change-me
ADMIN_PASSWORD=change-me
```

3. Start stack:

```bash
docker compose -f docker-compose.frappe.yml up -d
```

4. Verify:

```bash
docker compose -f docker-compose.frappe.yml ps
```

5. Open Frappe:

- `http://localhost:8000`

## 3.1 Windows + WSL2 Bootstrap

```powershell
./scripts/bootstrap-frappe-windows.ps1
```

Then start bench:

```bash
wsl -d Ubuntu bash -lc "cd ~/frappe-bench && bench start"
```

## 4. API Examples

### JWT Login

```bash
curl -X POST "http://localhost:8000/api/method/ibms_core.api.auth.login_with_jwt" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=administrator@example.com" \
  -d "password=admin"
```

### REST List

```bash
curl "http://localhost:8000/api/method/ibms_core.api.rest.list_resources?doctype=KPI%20Snapshot"
```

### GraphQL Query

```bash
curl -X POST "http://localhost:8000/api/method/ibms_core.api.graphql_api.execute" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "query=query KPI($company:String!){kpiSnapshots(company:$company){name metric_code metric_value}}" \
  -d 'variables={"company":"Default Company"}'
```

## 5. Production Readiness Checklist

- Use managed MariaDB/Redis and persistent storage.
- Configure TLS ingress and WAF.
- Set strong `ibms_jwt_secret` in `site_config.json`.
- Enable audit logs and external log shipping.
- Run migrations/patches per release.
- Scale worker queues (`short`, `default`, `long`) based on backlog metrics.

## 6. Tests and Quality Gates

Run locally:

```bash
pip install -r requirements-dev.txt
pre-commit run --all-files
pytest -q apps/ibms_core/tests
```

## 7. AWS Provisioning

```bash
cd deploy/aws/terraform
terraform init
terraform plan -var-file=prod.tfvars
terraform apply -var-file=prod.tfvars
```
