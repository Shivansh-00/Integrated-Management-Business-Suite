locals {
  prefix = "${var.project_name}-${var.environment}"
}

data "aws_availability_zones" "available" {
  state = "available"
}

resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name = "${local.prefix}-vpc"
  }
}

resource "aws_subnet" "private_a" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.70.1.0/24"
  availability_zone = data.aws_availability_zones.available.names[0]

  tags = {
    Name = "${local.prefix}-private-a"
  }
}

resource "aws_subnet" "private_b" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.70.2.0/24"
  availability_zone = data.aws_availability_zones.available.names[1]

  tags = {
    Name = "${local.prefix}-private-b"
  }
}

resource "aws_security_group" "app" {
  name   = "${local.prefix}-app-sg"
  vpc_id = aws_vpc.main.id

  ingress {
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    cidr_blocks = ["10.70.0.0/16"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_db_subnet_group" "mariadb" {
  name       = "${local.prefix}-db-subnet-group"
  subnet_ids = [aws_subnet.private_a.id, aws_subnet.private_b.id]
}

resource "aws_db_instance" "mariadb" {
  identifier              = "${local.prefix}-mariadb"
  allocated_storage       = 100
  engine                  = "mariadb"
  engine_version          = "10.6"
  instance_class          = "db.t3.medium"
  db_name                 = "imbs"
  username                = var.db_username
  password                = var.db_password
  db_subnet_group_name    = aws_db_subnet_group.mariadb.name
  vpc_security_group_ids  = [aws_security_group.app.id]
  skip_final_snapshot     = false
  final_snapshot_identifier = "${local.prefix}-mariadb-final"
  backup_retention_period = 7
  multi_az                = true
  publicly_accessible     = false
}

resource "aws_elasticache_subnet_group" "redis" {
  name       = "${local.prefix}-redis-subnet-group"
  subnet_ids = [aws_subnet.private_a.id, aws_subnet.private_b.id]
}

resource "aws_elasticache_replication_group" "redis" {
  replication_group_id         = "${replace(local.prefix, "-", "")}-redis"
  description                  = "IMBS Redis"
  engine                       = "redis"
  node_type                    = "cache.t3.medium"
  num_cache_clusters           = 2
  automatic_failover_enabled   = true
  at_rest_encryption_enabled   = true
  transit_encryption_enabled   = true
  subnet_group_name            = aws_elasticache_subnet_group.redis.name
  security_group_ids           = [aws_security_group.app.id]
}
