# AWS Deployment (Terraform)

This directory provisions AWS managed infrastructure for IBMS:

- VPC and private subnets
- RDS MariaDB (Multi-AZ)
- ElastiCache Redis replication group

## Quick Start

1. Configure AWS credentials.
2. Create tfvars file:

```hcl
aws_region  = "us-east-1"
project_name = "ibms"
environment = "prod"
db_password = "replace-with-strong-secret"
```

3. Run:

```bash
cd deploy/aws/terraform
terraform init
terraform plan -var-file=prod.tfvars
terraform apply -var-file=prod.tfvars
```

## Notes

- Plug RDS and Redis outputs into Frappe site config and Kubernetes secrets.
- Use ACM + ALB/NLB ingress for TLS in production.
- Add AWS Backup plans and CloudWatch alarms for compliance.
