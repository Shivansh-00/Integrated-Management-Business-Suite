variable "project_name" {
  type        = string
  description = "Project name prefix"
  default     = "imbs"
}

variable "environment" {
  type        = string
  description = "Deployment environment"
  default     = "prod"
}

variable "aws_region" {
  type        = string
  description = "AWS region"
  default     = "us-east-1"
}

variable "vpc_cidr" {
  type        = string
  description = "VPC CIDR"
  default     = "10.70.0.0/16"
}

variable "db_username" {
  type        = string
  description = "RDS admin username"
  default     = "imbsadmin"
}

variable "db_password" {
  type        = string
  description = "RDS admin password"
  sensitive   = true
}
