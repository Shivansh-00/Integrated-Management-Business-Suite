output "vpc_id" {
  value = aws_vpc.main.id
}

output "mariadb_endpoint" {
  value = aws_db_instance.mariadb.address
}

output "redis_primary_endpoint" {
  value = aws_elasticache_replication_group.redis.primary_endpoint_address
}
