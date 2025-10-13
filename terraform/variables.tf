variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "us-east-1"
}

variable "db_password" {
  description = "PostgreSQL database password. Must be at least 8 characters."
  type        = string
  sensitive   = true

  validation {
    condition     = length(var.db_password) >= 8
    error_message = "The db_password must be at least 8 characters long."
  }
}

variable "db_username" {
  description = "PostgreSQL database username. Must not be empty."
  type        = string
  default     = "authuser"
  sensitive   = true

  validation {
    condition     = length(var.db_username) > 0
    error_message = "The db_username must not be empty."
  }
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
  description = "Environment name. Allowed values: dev, staging, production."
  type        = string
  default     = "production"

  validation {
    condition     = contains(["dev", "staging", "production"], var.environment)
    error_message = "Environment must be one of: dev, staging, production."
  }
}

variable "rp_id" {
  description = "WebAuthn Relying Party ID (your domain). Must not be empty."
  type        = string

  validation {
    condition     = length(var.rp_id) > 0
    error_message = "The rp_id must not be empty."
  }
}

variable "origin" {
  description = "Frontend origin URL. Must start with http:// or https://"
  type        = string

  validation {
    condition     = can(regex("^(http|https)://", var.origin))
    error_message = "The origin must start with http:// or https://"
  }
}

# Usage:
# terraform apply -var="db_password=$(openssl rand -base64 32)" \
#                 -var="secret_key=$(openssl rand -base64 64)" \
#                 -var="redis_password=$(openssl rand -base64 32)" \
#                 -var="rp_id=auth.example.com" \
#                 -var="origin=https://example.com"
