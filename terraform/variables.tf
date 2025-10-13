variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "us-east-1"
}

variable "db_password" {
  description = "PostgreSQL database password"
  type        = string
  sensitive   = true
}

variable "db_username" {
  description = "PostgreSQL database username"
  type        = string
  default     = "authuser"
  sensitive   = true
}

variable "secret_key" {
  description = "JWT secret key for token signing"
  type        = string
  sensitive   = true
}

variable "redis_password" {
  description = "Redis password"
  type        = string
  sensitive   = true
}

variable "environment" {
  description = "Environment name (dev, staging, production)"
  type        = string
  default     = "production"
}

variable "rp_id" {
  description = "WebAuthn Relying Party ID (your domain)"
  type        = string
}

variable "origin" {
  description = "Frontend origin URL"
  type        = string
}

# Usage:
# terraform apply -var="db_password=$(openssl rand -base64 32)" \
#                 -var="secret_key=$(openssl rand -base64 64)" \
#                 -var="redis_password=$(openssl rand -base64 32)" \
#                 -var="rp_id=auth.example.com" \
#                 -var="origin=https://example.com"
