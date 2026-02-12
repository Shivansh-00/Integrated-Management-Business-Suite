# Deployment Guide

## Local
1. Copy `.env.example` to `.env`.
2. Start services via `docker compose up --build`.

## Kubernetes
- Apply `apps/imbs_core/imbs_core/k8s/deployment.yaml`.
- Scale deployment replicas based on queue depth and API RPS.

## CI
- GitHub Actions compiles Python modules and can be extended with tests/security scans.
