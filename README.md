# Integrated-Management-Business-Suite

Enterprise-grade blueprint and starter implementation for an AI-first ERP platform built on **Frappe Framework + ERPNext principles**.

## Included in this repository

- Advanced system blueprint: architecture, RBAC, AI modules, queues, APIs, event-driven topology.
- Frappe custom app scaffold (`ibms_core`) with services, jobs, security, API endpoints, and monitoring hooks.
- Enterprise deployment templates: Docker, Compose, NGINX, Kubernetes manifest, CI workflow.
- UI assets for realtime KPI updates, AI insights panel, and dark mode.
- Security and deployment documentation.

## Key docs

- [`docs/system_blueprint.md`](docs/system_blueprint.md)
- [`ARCHITECTURE.md`](ARCHITECTURE.md)
- [`API_DOCUMENTATION.md`](API_DOCUMENTATION.md)
- [`SECURITY_OVERVIEW.md`](SECURITY_OVERVIEW.md)
- [`DEPLOYMENT_GUIDE.md`](DEPLOYMENT_GUIDE.md)
- [`FRAPPE_ENTERPRISE_IMPLEMENTATION.md`](FRAPPE_ENTERPRISE_IMPLEMENTATION.md)

## Enterprise Frappe Stack (New)

This repository now includes a production-style Frappe app implementation under `apps/ibms_core` with:

- Enterprise doctypes and validations
- JWT + RBAC API security hooks
- REST + GraphQL APIs
- Redis queue background jobs and event-driven webhook processing
- Workflow JSON for recommendation lifecycle
- Glassmorphism dashboard enhancements and Tailwind entry configuration
- Docker Compose and Kubernetes templates for deployment

Run the Frappe stack:

```bash
docker compose -f docker-compose.frappe.yml up -d
```

## Full Enterprise Tooling

### Bootstrap Frappe Bench

- Windows (WSL wrapper): `./scripts/bootstrap-frappe-windows.ps1`
- WSL/Linux: `./scripts/bootstrap-frappe-wsl.sh`

### Quality + Tests

```bash
pip install -r requirements-dev.txt
pre-commit run --all-files
pytest -q apps/ibms_core/tests
```

### AWS Infrastructure

Terraform templates are in `deploy/aws/terraform`.
See `deploy/aws/README.md` for usage.
