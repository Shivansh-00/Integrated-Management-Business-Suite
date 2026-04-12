# =============================================================================
# IBMS Enterprise — GCP Infrastructure (Terraform)
# =============================================================================
# Resources: Artifact Registry, Cloud SQL MySQL, Memorystore Redis, Cloud Run
# MongoDB: Use MongoDB Atlas Free Tier (external — not managed by Terraform)
# =============================================================================

# ─── Enable Required APIs ────────────────────────────────────────────────────

resource "google_project_service" "apis" {
  for_each = toset([
    "run.googleapis.com",
    "sqladmin.googleapis.com",
    "artifactregistry.googleapis.com",
    "cloudbuild.googleapis.com",
    "redis.googleapis.com",
    "vpcaccess.googleapis.com",
    "secretmanager.googleapis.com",
    "compute.googleapis.com",
  ])

  project            = var.project_id
  service            = each.value
  disable_on_destroy = false
}

# ─── VPC Network (for Cloud SQL + Redis private access) ─────────────────────

resource "google_compute_network" "ibms_vpc" {
  name                    = "ibms-vpc"
  auto_create_subnetworks = false
  depends_on              = [google_project_service.apis]
}

resource "google_compute_subnetwork" "ibms_subnet" {
  name          = "ibms-subnet"
  ip_cidr_range = "10.0.0.0/24"
  region        = var.region
  network       = google_compute_network.ibms_vpc.id
}

resource "google_compute_global_address" "private_ip" {
  name          = "ibms-private-ip"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = google_compute_network.ibms_vpc.id
}

resource "google_service_networking_connection" "private_vpc" {
  network                 = google_compute_network.ibms_vpc.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_ip.name]
}

# ─── VPC Serverless Connector (Cloud Run → Cloud SQL / Redis) ───────────────

resource "google_vpc_access_connector" "connector" {
  name          = "ibms-connector"
  region        = var.region
  ip_cidr_range = "10.8.0.0/28"
  network       = google_compute_network.ibms_vpc.name
  depends_on    = [google_project_service.apis]
}

# ─── Artifact Registry ──────────────────────────────────────────────────────

resource "google_artifact_registry_repository" "ibms" {
  location      = var.region
  repository_id = "ibms-docker"
  format        = "DOCKER"
  description   = "IBMS Enterprise container images"
  depends_on    = [google_project_service.apis]
}

# ─── Cloud SQL MySQL 8.0 ────────────────────────────────────────────────────

resource "google_sql_database_instance" "mysql" {
  name             = "ibms-mysql"
  database_version = "MYSQL_8_0"
  region           = var.region

  settings {
    tier              = "db-f1-micro" # Free-tier eligible
    availability_type = "ZONAL"

    ip_configuration {
      ipv4_enabled    = false
      private_network = google_compute_network.ibms_vpc.id
    }

    backup_configuration {
      enabled            = true
      binary_log_enabled = true
    }

    database_flags {
      name  = "character_set_server"
      value = "utf8mb4"
    }
  }

  deletion_protection = false
  depends_on          = [google_service_networking_connection.private_vpc]
}

resource "google_sql_database" "ibms_db" {
  name     = "ibms_enterprise"
  instance = google_sql_database_instance.mysql.name
}

resource "google_sql_user" "root" {
  name     = "root"
  instance = google_sql_database_instance.mysql.name
  password = var.db_password
}

resource "google_sql_user" "ibms_user" {
  name     = "ibms_user"
  instance = google_sql_database_instance.mysql.name
  password = var.db_user_password
}

# ─── Memorystore Redis ──────────────────────────────────────────────────────

resource "google_redis_instance" "ibms" {
  name               = "ibms-redis"
  tier               = "BASIC"
  memory_size_gb     = 1
  region             = var.region
  authorized_network = google_compute_network.ibms_vpc.id
  redis_version      = "REDIS_7_0"
  depends_on         = [google_project_service.apis]
}

# ─── Secret Manager (application secrets) ────────────────────────────────────

resource "google_secret_manager_secret" "secret_key" {
  secret_id = "ibms-secret-key"
  replication {
    auto {}
  }
  depends_on = [google_project_service.apis]
}

resource "google_secret_manager_secret_version" "secret_key_value" {
  secret      = google_secret_manager_secret.secret_key.id
  secret_data = var.secret_key
}

resource "google_secret_manager_secret" "db_password" {
  secret_id = "ibms-db-password"
  replication {
    auto {}
  }
  depends_on = [google_project_service.apis]
}

resource "google_secret_manager_secret_version" "db_password_value" {
  secret      = google_secret_manager_secret.db_password.id
  secret_data = var.db_user_password
}

# ─── Cloud Run Service ──────────────────────────────────────────────────────

resource "google_cloud_run_v2_service" "ibms_web" {
  name     = "ibms-web"
  location = var.region

  template {
    scaling {
      min_instance_count = 0
      max_instance_count = 4
    }

    vpc_access {
      connector = google_vpc_access_connector.connector.id
      egress    = "PRIVATE_RANGES_ONLY"
    }

    containers {
      image = "${var.region}-docker.pkg.dev/${var.project_id}/ibms-docker/ibms-web:${var.image_tag}"

      ports {
        container_port = 8000
      }

      resources {
        limits = {
          cpu    = "2"
          memory = "2Gi"
        }
      }

      env {
        name  = "HOST"
        value = "0.0.0.0"
      }
      env {
        name  = "PORT"
        value = "8000"
      }
      env {
        name  = "RELOAD"
        value = "false"
      }
      env {
        name  = "LOG_LEVEL"
        value = "warning"
      }
      env {
        name  = "REDIS_URL"
        value = "redis://${google_redis_instance.ibms.host}:${google_redis_instance.ibms.port}/0"
      }
      env {
        name  = "MARIADB_URI"
        value = "mysql+aiomysql://ibms_user:${var.db_user_password}@${google_sql_database_instance.mysql.private_ip_address}:3306/ibms_enterprise"
      }
      env {
        name  = "MONGO_URI"
        value = "mongodb+srv://ibms_admin:${var.mongo_password}@cluster0.mongodb.net/?retryWrites=true&w=majority"
      }
      env {
        name  = "MONGO_DB_NAME"
        value = "ibms_enterprise"
      }
      env {
        name = "SECRET_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.secret_key.secret_id
            version = "latest"
          }
        }
      }

      startup_probe {
        http_get {
          path = "/api/health"
        }
        initial_delay_seconds = 10
        period_seconds        = 5
        failure_threshold     = 10
      }

      liveness_probe {
        http_get {
          path = "/api/health"
        }
        period_seconds = 15
      }
    }
  }

  depends_on = [
    google_project_service.apis,
    google_secret_manager_secret_version.secret_key_value,
  ]
}

# ─── Make Cloud Run publicly accessible ─────────────────────────────────────

resource "google_cloud_run_v2_service_iam_member" "public" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.ibms_web.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}
