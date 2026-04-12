# IBMS Enterprise — Google Cloud Platform Deployment

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Google Cloud Platform                     │
│                                                             │
│  ┌──────────────┐    ┌──────────────┐   ┌──────────────┐   │
│  │  Cloud Run    │    │  Cloud SQL   │   │ Memorystore  │   │
│  │  (ibms-web)   │───▶│  MySQL 8.0   │   │  Redis 7.0   │   │
│  │  Port 8000    │    │  db-f1-micro │   │  1GB BASIC   │   │
│  └──────┬───────┘    └──────────────┘   └──────────────┘   │
│         │                     ▲                 ▲           │
│         │         ┌───────────┴─────────────────┘           │
│         │         │  VPC Serverless Connector               │
│         │         └─────────────────────────────            │
│  ┌──────┴───────┐                                           │
│  │  Artifact    │    ┌──────────────┐                       │
│  │  Registry    │    │ Cloud Build  │                       │
│  │  (Docker)    │◀───│ (CI/CD)      │                       │
│  └──────────────┘    └──────────────┘                       │
│                                                             │
│  External: MongoDB Atlas Free Tier (M0)                     │
└─────────────────────────────────────────────────────────────┘
```

## Prerequisites

- Google Cloud account with billing enabled
- Python 3.10+ with `httpx` installed
- (Optional) Terraform 1.5+, gcloud CLI

## Quick Deploy (No CLI Required)

The deploy script uses GCP REST APIs with OAuth device flow — no gcloud CLI needed:

```bash
# Install httpx if not already installed
pip install httpx

# Set environment variables (optional — defaults provided)
export GCP_PROJECT_ID=ibms-enterprise
export GCP_REGION=asia-south1
export MONGO_URI="mongodb+srv://user:pass@cluster0.mongodb.net/?retryWrites=true"

# Run deploy
python deploy/gcp/deploy_gcp.py
```

The script will:
1. Open a browser-based OAuth flow for authentication
2. Enable all required GCP APIs
3. Create Artifact Registry and build the container
4. Create VPC with serverless connector
5. Provision Cloud SQL MySQL and Memorystore Redis
6. Deploy to Cloud Run and output the public URL

## Terraform Deploy (Alternative)

```bash
cd deploy/gcp/terraform

terraform init
terraform plan -var="project_id=ibms-enterprise" \
               -var="db_password=YOUR_DB_PASS" \
               -var="db_user_password=YOUR_USER_PASS" \
               -var="mongo_password=YOUR_MONGO_PASS" \
               -var="secret_key=YOUR_SECRET_KEY"

terraform apply
```

## CI/CD (GitHub Actions)

The pipeline at `.github/workflows/gcp-deploy.yml` runs on push to `main`:

### Required GitHub Secrets

| Secret | Description |
|--------|-------------|
| `GCP_PROJECT_ID` | Your GCP project ID |
| `GCP_SA_KEY` | Service account JSON key with Cloud Run Admin, Artifact Registry Writer, Cloud Build Editor roles |

### Pipeline Stages

1. **Test** — Lint (ruff) + pytest
2. **Build** — Docker build → push to Artifact Registry
3. **Deploy** — Deploy to Cloud Run with secrets from Secret Manager

## MongoDB Atlas (Free Tier)

Since GCP doesn't offer a native MongoDB service, use MongoDB Atlas:

1. Create a free account at [mongodb.com/atlas](https://www.mongodb.com/atlas)
2. Create a free M0 cluster (AWS/GCP region closest to `asia-south1`)
3. Create a database user and get the connection string
4. Set `MONGO_URI` in your deploy config

## Cost Estimate (Free Tier Eligible)

| Service | Tier | Free Tier |
|---------|------|-----------|
| Cloud Run | 2 vCPU, 2GB RAM | 2M requests/month free |
| Cloud SQL | db-f1-micro | $7.67/month (no free tier) |
| Memorystore | 1GB BASIC | $0.049/GB/hour |
| Artifact Registry | Standard | 0.5 GB free |
| Cloud Build | — | 120 build-min/day free |
| MongoDB Atlas | M0 | Free forever (512 MB) |

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GCP_PROJECT_ID` | GCP project ID | `ibms-enterprise` |
| `GCP_REGION` | Deployment region | `asia-south1` |
| `MONGO_URI` | MongoDB connection string | — |
| `SECRET_KEY` | JWT/session secret | Auto-generated |
| `DB_USER_PASSWORD` | MySQL password | Auto-generated |

## Useful Commands

```bash
# View Cloud Run logs
gcloud run services logs read ibms-web --region asia-south1

# Get service URL
gcloud run services describe ibms-web --region asia-south1 --format 'value(status.url)'

# Update image
gcloud run deploy ibms-web --image asia-south1-docker.pkg.dev/PROJECT/ibms-docker/ibms-web:latest --region asia-south1
```
