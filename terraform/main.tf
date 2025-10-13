terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# Local variable for common tags
locals {
  vpc_tags = {
    Name = "auth-system-vpc"
  }
}

resource "aws_vpc" "main" {
  cidr_block  = "10.0.0.0/16"

  tags = local.vpc_tags
}

resource "aws_db_instance" "postgres" {
  identifier        = "auth-postgres"
  engine            = "postgres"
  engine_version    = "15.4"
  instance_class    = "db.t3.medium"
  allocated_storage = 20
  storage_encrypted = true
  db_name           = "authdb"
  username          = var.db_username
  password          = var.db_password
  multi_az          = true
  iam_database_authentication_enabled = true

  tags = {
    Name        = "auth-postgres"
    Environment = var.environment
  }

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_elasticache_cluster" "redis" {
  cluster_id           = "auth-redis"
  engine               = "redis"
  node_type            = "cache.t3.small"
  num_cache_nodes      = 1
  parameter_group_name = "default.redis7"
  engine_version       = "7.0"
  port                 = 6379

  tags = {
    Name        = "auth-redis"
    Environment = var.environment
  }

  lifecycle {
    create_before_destroy = true
    prevent_destroy       = true
  }
}

resource "aws_secretsmanager_secret" "auth_secrets" {
  name        = "auth-system-secrets-${var.environment}"
  kms_key_id  = var.secretsmanager_kms_key_id

  tags = {
    Name        = "auth-secrets"
    Environment = var.environment
  }
}

variable "secretsmanager_kms_key_id" {
  description = "KMS Key ID for encrypting Secrets Manager secrets"
  type        = string
}

resource "aws_secretsmanager_secret_version" "auth_secrets" {
  secret_id = aws_secretsmanager_secret.auth_secrets.id
  secret_string = jsonencode({
    SECRET_KEY     = var.secret_key
    DATABASE_URL   = "postgresql+asyncpg://${var.db_username}:${var.db_password}@${aws_db_instance.postgres.endpoint}/authdb"
    REDIS_URL      = "redis://:${var.redis_password}@${aws_elasticache_cluster.redis.cache_nodes[0].address}:6379"
    RP_ID          = var.rp_id
    ORIGIN         = var.origin
  })
}
