provider "aws" {
  region = var.aws_region
}

# --- VPC & NETWORKING ---
resource "aws_vpc" "finops_vpc" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name        = "finoptica-vpc"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

resource "aws_subnet" "public_subnet" {
  count                   = 2
  vpc_id                  = aws_vpc.finops_vpc.id
  cidr_block              = "10.0.${count.index}.0/24"
  availability_zone       = data.aws_availability_zones.available.names[count.index]
  map_public_ip_on_launch = true

  tags = {
    Name = "finoptica-public-subnet-${count.index}"
  }
}

resource "aws_subnet" "private_subnet" {
  count             = 2
  vpc_id            = aws_vpc.finops_vpc.id
  cidr_block        = "10.0.${count.index + 10}.0/24"
  availability_zone = data.aws_availability_zones.available.names[count.index]

  tags = {
    Name = "finoptica-private-subnet-${count.index}"
  }
}

data "aws_availability_zones" "available" {
  state = "available"
}

# --- BUCKET S3 POUR LES RAPPORTS DE FACTURATION (AWS CUR) ---
resource "aws_s3_bucket" "billing_cur_bucket" {
  bucket        = "finoptica-billing-cur-${var.environment}-2026"
  force_destroy = false

  tags = {
    Name        = "FinOps Billing CUR Ingestion S3 Bucket"
    Environment = var.environment
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "s3_encrypt" {
  bucket = aws_s3_bucket.billing_cur_bucket.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "block_public" {
  bucket = aws_s3_bucket.billing_cur_bucket.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# --- BASE DE DONNÉES MANAGÉE RDS (POSTGRESQL) ---
resource "aws_db_subnet_group" "rds_subnet_group" {
  name       = "finoptica-rds-subnet-group"
  subnet_ids = aws_subnet.private_subnet[*].id
}

resource "aws_security_group" "rds_sg" {
  name        = "finoptica-rds-sg"
  description = "Autorise le port PostgreSQL interne"
  vpc_id      = aws_vpc.finops_vpc.id

  ingress {
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = [aws_vpc.finops_vpc.cidr_block]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_db_instance" "postgres_db" {
  identifier             = "finoptica-db-${var.environment}"
  allocated_storage      = 20
  max_allocated_storage  = 100
  db_name                = "finoptica_prod"
  engine                 = "postgres"
  engine_version         = "14"
  instance_class         = "db.t4g.micro" # Instance Burstable à faible coût (FinOps approuvé !)
  username               = "finoptica_db_admin"
  password               = var.db_password
  db_subnet_group_name   = aws_db_subnet_group.rds_subnet_group.name
  vpc_security_group_ids = [aws_security_group.rds_sg.id]
  skip_final_snapshot    = true

  tags = {
    Name        = "FinOptica RDS Database Instance"
    Environment = var.environment
  }
}
