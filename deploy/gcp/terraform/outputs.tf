# =============================================================================
# IBMS Enterprise — GCP Terraform Outputs
# =============================================================================

output "cloud_run_url" {
  description = "Public URL for the IBMS Cloud Run service"
  value       = google_cloud_run_v2_service.ibms_web.uri
}

output "artifact_registry_url" {
  description = "Artifact Registry Docker repo URL"
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/ibms-docker"
}

output "cloud_sql_private_ip" {
  description = "Cloud SQL MySQL private IP"
  value       = google_sql_database_instance.mysql.private_ip_address
}

output "redis_host" {
  description = "Memorystore Redis host"
  value       = google_redis_instance.ibms.host
}

output "redis_port" {
  description = "Memorystore Redis port"
  value       = google_redis_instance.ibms.port
}

output "vpc_connector" {
  description = "VPC Access Connector name"
  value       = google_vpc_access_connector.connector.name
}
