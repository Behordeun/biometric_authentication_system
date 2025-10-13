# IaaS Deployment Guide

## Infrastructure as a Service Deployment Options

### Option 1: AWS Deployment

#### Architecture
- **Compute**: ECS Fargate or EKS
- **Database**: RDS PostgreSQL Multi-AZ
- **Cache**: ElastiCache Redis Cluster
- **Load Balancer**: Application Load Balancer
- **Storage**: S3 for logs and backups
- **Secrets**: AWS Secrets Manager
- **Monitoring**: CloudWatch + Prometheus

#### Terraform Configuration
```hcl
# See terraform/aws/ directory for complete configuration
```

### Option 2: Google Cloud Platform

#### Architecture
- **Compute**: Cloud Run or GKE
- **Database**: Cloud SQL PostgreSQL HA
- **Cache**: Memorystore Redis
- **Load Balancer**: Cloud Load Balancing
- **Storage**: Cloud Storage
- **Secrets**: Secret Manager
- **Monitoring**: Cloud Monitoring + Prometheus

### Option 3: Azure Deployment

#### Architecture
- **Compute**: Container Apps or AKS
- **Database**: Azure Database for PostgreSQL
- **Cache**: Azure Cache for Redis
- **Load Balancer**: Azure Load Balancer
- **Storage**: Blob Storage
- **Secrets**: Key Vault
- **Monitoring**: Azure Monitor + Prometheus

### Option 4: On-Premise / Self-Hosted

#### Requirements
- Kubernetes cluster (K3s, K8s, OpenShift)
- PostgreSQL 15+ (with replication)
- Redis 7+ (cluster mode)
- Load balancer (Nginx, HAProxy)
- Object storage (MinIO, Ceph)
- Monitoring stack (Prometheus, Grafana)

## Deployment Steps

### 1. Infrastructure Provisioning

```bash
# Using Terraform
cd terraform/aws  # or gcp, azure, on-premise
terraform init
terraform plan
terraform apply
```

### 2. Database Setup

```bash
# Create database
psql -h <db-host> -U postgres
CREATE DATABASE authdb;
CREATE USER authuser WITH PASSWORD 'secure-password';  # pragma: allowlist secret
GRANT ALL PRIVILEGES ON DATABASE authdb TO authuser;

# Run migrations
cd backend
alembic upgrade head
```

### 3. Secrets Configuration

```bash
# Generate secure keys
openssl rand -base64 32  # SECRET_KEY  # pragma: allowlist secret
openssl rand -base64 48  # CLIENT_SECRET

# Store in secrets manager
aws secretsmanager create-secret --name auth-system-secrets \
  --secret-string '{"SECRET_KEY":"xxx","DATABASE_URL":"xxx"}'  # pragma: allowlist secret
```

### 4. Container Deployment

```bash
# Build images
docker build -t auth-api:latest ./backend
docker build -t auth-frontend:latest ./frontend

# Push to registry
docker tag auth-api:latest <registry>/auth-api:latest
docker push <registry>/auth-api:latest

# Deploy
kubectl apply -f k8s/
```

### 5. SSL/TLS Configuration

```bash
# Using Let's Encrypt
certbot certonly --standalone -d auth.yourdomain.com

# Or use cloud provider certificates
aws acm request-certificate --domain-name auth.yourdomain.com
```

### 6. DNS Configuration

```bash
# Point domain to load balancer
auth.yourdomain.com -> <load-balancer-ip>
```

## Scaling Configuration

### Horizontal Scaling

```yaml
# Kubernetes HPA
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: auth-api-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: auth-api
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

### Database Scaling

- **Read Replicas**: For read-heavy workloads
- **Connection Pooling**: PgBouncer for connection management
- **Partitioning**: Time-based partitioning for audit logs

### Cache Scaling

- **Redis Cluster**: Automatic sharding
- **Read Replicas**: For read-heavy operations

## Monitoring Setup

### Prometheus Metrics

```yaml
# Expose metrics endpoint
/metrics
  - http_requests_total
  - http_request_duration_seconds
  - auth_attempts_total
  - auth_failures_total
  - active_sessions_total
```

### Grafana Dashboards

- API Performance
- Authentication Metrics
- Database Performance
- Cache Hit Rates
- Error Rates

### Alerting Rules

```yaml
groups:
  - name: auth_system
    rules:
      - alert: HighAuthFailureRate
        expr: rate(auth_failures_total[5m]) > 10
        for: 5m
        annotations:
          summary: High authentication failure rate
```

## Backup Strategy

### Database Backups

```bash
# Automated daily backups
pg_dump -h <db-host> -U authuser authdb | gzip > backup-$(date +%Y%m%d).sql.gz

# Upload to S3 (use a unique, non-guessable bucket name and least-privilege IAM user)
aws s3 cp backup-$(date +%Y%m%d).sql.gz s3://your-unique-backup-bucket-name/auth-system/
```

### Retention Policy

- Daily backups: 7 days
- Weekly backups: 4 weeks
- Monthly backups: 12 months

## Disaster Recovery

### RTO (Recovery Time Objective): 1 hour

### RPO (Recovery Point Objective): 15 minutes

### Recovery Steps

1. Provision new infrastructure
2. Restore database from latest backup
3. Deploy application containers
4. Update DNS records
5. Verify functionality

## Security Hardening

### Network Security

- VPC with private subnets
- Security groups with minimal access
- WAF rules for common attacks
- DDoS protection enabled

### Application Security

- HTTPS only (TLS 1.3)
- HSTS headers
- CSP headers
- Rate limiting per IP
- Input validation

### Database Security

- Encrypted at rest (AES-256)
- Encrypted in transit (TLS)
- No public access
- Regular security patches

## Cost Optimization

### AWS Example (Monthly)

- ECS Fargate (3 tasks): $50
- RDS PostgreSQL (db.t3.medium): $100
- ElastiCache Redis (cache.t3.small): $30
- ALB: $20
- S3 Storage: $5
- Data Transfer: $20
**Total: ~$225/month**

### Scaling Costs

- 10x traffic: ~$500/month
- 100x traffic: ~$2,000/month

## Compliance

### GDPR Compliance

- Data encryption
- Right to erasure
- Data portability
- Audit logging

### SOC 2 Compliance

- Access controls
- Encryption
- Monitoring
- Incident response

### HIPAA Compliance

- BAA agreements
- Encryption
- Audit trails
- Access controls

## Maintenance

### Regular Tasks

- Weekly: Review logs and metrics
- Monthly: Security patches
- Quarterly: Disaster recovery testing
- Annually: Security audit

### Update Strategy

- Blue-green deployments
- Canary releases
- Automated rollback on errors
