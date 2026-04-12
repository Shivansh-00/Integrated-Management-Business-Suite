# =============================================================================
# IBMS Enterprise — GCP Terraform Variables
# =============================================================================

variable "project_id" {
  description = "GCP Project ID"
  type        = string
  default     = "total-handler-463313-e2"
}

variable "region" {
  description = "GCP region"
  type        = string
  default     = "asia-south1"
}

variable "zone" {
  description = "GCP zone"
  type        = string
  default     = "asia-south1-a"
}

variable "db_password" {
  description = "Cloud SQL root password"
  type        = string
  sensitive   = true
}

variable "db_user_password" {
  description = "Cloud SQL ibms_user password"
  type        = string
  sensitive   = true
}

variable "mongo_password" {
  description = "MongoDB Atlas password (use Atlas free tier)"
  type        = string
  sensitive   = true
}

variable "secret_key" {
  description = "Application JWT/session secret key"
  type        = string
  sensitive   = true
}

variable "image_tag" {
  description = "Container image tag to deploy"
  type        = string
  default     = "latest"
}
