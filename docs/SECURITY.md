# Security Guidelines

## 🔒 Secrets Management

### ⚠️ CRITICAL: Never Hardcode Secrets

**NEVER commit these to version control:**

- Database passwords
- API keys
- Secret keys
- JWT signing keys
- Redis passwords
- TLS certificates
- Private keys

### ✅ Proper Secrets Management

#### 1. Local Development

Use `.env` file (already in `.gitignore`):

```bash
# Generate secure secrets
./scripts/generate-secrets.sh

# Copy output to backend/.env
cp backend/.env.example backend/.env
# Edit backend/.env with generated secrets
```

#### 2. Docker Compose

Use environment variables:

```bash
# Set in shell before running docker-compose
export POSTGRES_PASSWORD=$(openssl rand -base64 32)
export REDIS_PASSWORD=$(openssl rand -base64 32)
export SECRET_KEY=$(openssl rand -base64 64)

docker-compose up -d
```

#### 3. Kubernetes

Use Kubernetes Secrets:

```bash
# Generate secrets
kubectl create secret generic auth-secrets \
  --from-literal=secret-key=$(openssl rand -base64 64) \
  --from-literal=postgres-password=$(openssl rand -base64 32) \
  --from-literal=redis-password=$(openssl rand -base64 32) \
  --from-literal=database-url="postgresql+asyncpg://user:pass@host/db" \  # pragma: allowlist secret
  --from-literal=redis-url="redis://:pass@host:6379"  # pragma: allowlist secret

# Verify (values will be base64 encoded)
kubectl get secret auth-secrets -o yaml
```

#### 4. AWS Deployment

Use AWS Secrets Manager:

```bash
# Create secret
aws secretsmanager create-secret \
  --name auth-system-secrets \
  --secret-string '{
    "SECRET_KEY":"'$(openssl rand -base64 64)'",
    "POSTGRES_PASSWORD":"'$(openssl rand -base64 32)'",
    "REDIS_PASSWORD":"'$(openssl rand -base64 32)'"
  }'

# Retrieve secret
aws secretsmanager get-secret-value \
  --secret-id auth-system-secrets \
  --query SecretString \
  --output text
```

#### 5. Terraform

Use variables and never commit `terraform.tfvars`:

```bash
# Create terraform.tfvars (in .gitignore)
cat > terraform/terraform.tfvars <<EOF
db_password     = "$(openssl rand -base64 32)"
secret_key      = "$(openssl rand -base64 64)"
redis_password  = "$(openssl rand -base64 32)"
rp_id          = "auth.example.com"
origin         = "https://example.com"
EOF

# Apply
cd terraform
terraform apply
```

#### 6. GitHub Actions

Use GitHub Secrets:

1. Go to repository Settings → Secrets and variables → Actions
2. Add secrets:
   - `TEST_DB_PASSWORD`
   - `TEST_REDIS_PASSWORD`
   - `TEST_SECRET_KEY`
   - `AWS_ACCESS_KEY_ID` (for deployment)
   - `AWS_SECRET_ACCESS_KEY` (for deployment)

## 🛡️ Security Best Practices

### Secret Generation

```bash
# JWT Secret Key (64 bytes)
openssl rand -base64 64

# Database Password (32 bytes)
openssl rand -base64 32

# Redis Password (32 bytes)
openssl rand -base64 32

# API Key (32 bytes hex)
openssl rand -hex 32
```

### Secret Rotation

Rotate secrets regularly:

1. **Development**: Every 90 days
2. **Production**: Every 30-60 days
3. **After breach**: Immediately

### Access Control

- Use principle of least privilege
- Limit who can access secrets
- Use IAM roles instead of access keys when possible
- Enable MFA for secret access

### Audit Logging

- Enable CloudTrail (AWS)
- Log all secret access
- Monitor for unusual patterns
- Set up alerts for secret access

## 🚨 What to Do If Secrets Are Exposed

### Immediate Actions

1. **Revoke compromised secrets immediately**
2. **Generate new secrets**
3. **Update all services**
4. **Rotate all related credentials**
5. **Review access logs**
6. **Notify security team**

### GitHub Exposure

If secrets are committed to GitHub:

```bash
# Remove from history
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch backend/.env" \
  --prune-empty --tag-name-filter cat -- --all

# Force push
git push origin --force --all

# Rotate ALL exposed secrets immediately
```

Better: Use [BFG Repo-Cleaner](https://rtyley.github.io/bfg-repo-cleaner/)

```bash
bfg --delete-files .env
git reflog expire --expire=now --all
git gc --prune=now --aggressive
```

## 🔍 Secret Scanning

### Pre-commit Hooks

Install git-secrets:

```bash
# Install
brew install git-secrets  # macOS
apt-get install git-secrets  # Ubuntu

# Setup
cd authentication_system
git secrets --install
git secrets --register-aws
```

### GitHub Secret Scanning

Enable in repository settings:

- Settings → Code security and analysis
- Enable "Secret scanning"
- Enable "Push protection"

### Tools

- [truffleHog](https://github.com/trufflesecurity/trufflehog)
- [gitleaks](https://github.com/gitleaks/gitleaks)
- [detect-secrets](https://github.com/Yelp/detect-secrets)

## 📋 Checklist

Before deploying:

- [ ] All secrets use environment variables
- [ ] No hardcoded credentials in code
- [ ] `.env` files in `.gitignore`
- [ ] Secrets generated with cryptographically secure methods
- [ ] Production secrets different from development
- [ ] Secrets stored in proper secrets manager
- [ ] Access to secrets is logged
- [ ] Secret rotation policy in place
- [ ] Team trained on secrets management
- [ ] Pre-commit hooks installed

## 📚 References

- [OWASP Secrets Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html)
- [AWS Secrets Manager Best Practices](https://docs.aws.amazon.com/secretsmanager/latest/userguide/best-practices.html)
- [Kubernetes Secrets](https://kubernetes.io/docs/concepts/configuration/secret/)
- [12 Factor App - Config](https://12factor.net/config)
