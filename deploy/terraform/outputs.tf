output "vpc_id" {
  description = "L'identifiant du VPC créé"
  value       = aws_vpc.finops_vpc.id
}

output "billing_bucket_name" {
  description = "Nom du bucket S3 configuré pour stocker les rapports AWS CUR"
  value       = aws_s3_bucket.billing_cur_bucket.bucket
}

output "rds_endpoint" {
  description = "L'adresse réseau d'accès à la base de données PostgreSQL RDS"
  value       = aws_db_instance.postgres_db.endpoint
}
