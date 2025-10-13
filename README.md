# Hybrid Passwordless Authentication System

A modern, enterprise-grade authentication system combining OAuth2, OpenID Connect, and WebAuthn (FIDO2) for passwordless biometric authentication.

## Features

- 🔐 **Passwordless Authentication**: WebAuthn/FIDO2 for biometric login (fingerprint, Face ID)
- 🎫 **OAuth2 & OpenID Connect**: Full authorization server implementation
- 🔑 **JWT Tokens**: Secure access and refresh token management
- 👥 **User Management**: Registration, profile, and session management
- 🛡️ **Multi-Factor Authentication**: Additional security layers
- 🔌 **API Key Management**: For service-to-service authentication
- 📊 **Audit Logging**: Track authentication events

## Architecture

```plain-text
├── backend/          # FastAPI authentication server
│   ├── app/
│   │   ├── api/routes/    # HTTP endpoints
│   │   ├── core/          # Configuration & utilities
│   │   ├── db/            # Database layer
│   │   └── services/      # Business logic
├── frontend/         # React client application
├── database/         # PostgreSQL schemas
├── k8s/              # Kubernetes manifests
├── terraform/        # Infrastructure as Code
└── diagrams/         # Architecture diagrams
```

See [REFACTORING.md](docs/REFACTORING.md) for detailed structure.

## 📋 Documentation

- [CHANGELOG.md](CHANGELOG.md) - Version history and fixes
- [BIOMETRIC_SECURITY.md](docs/BIOMETRIC_SECURITY.md) - Anti-spoofing & biometric security
- [SECURITY_FIXES.md](docs/SECURITY_FIXES.md) - Security improvements
- [CODE_QUALITY.md](docs/CODE_QUALITY.md) - Code quality enhancements
- [DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md) - Production deployment
- [DOCKER_QUICKSTART.md](docs/DOCKER_QUICKSTART.md) - Docker setup guide

## Tech Stack

**Backend**: Python 3.11+, FastAPI, SQLAlchemy, WebAuthn
**Frontend**: React, TypeScript, WebAuthn API
**Database**: PostgreSQL
**Cache**: Redis

## Quick Start

### Using Docker (Recommended)

```bash
# Validate environment setup
./scripts/validate-env.sh

# Start everything
./docker/docker-start.sh

# Or use Makefile
make docker-up

# Access
# Backend: http://localhost:8000
# Frontend: http://localhost:3000
# API Docs: http://localhost:8000/docs
```

See [DOCKER_QUICKSTART.md](docs/DOCKER_QUICKSTART.md) for details.

### Using Makefile

```bash
# Complete setup
make all

# Start development
make dev

# Run tests
make test
```

See [Makefile.md](docs/Makefile.md) for all commands.

### Manual Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Generate secure secrets
../scripts/generate-secrets.sh

# Create .env file
cp .env.example .env
# Edit .env with generated secrets (NEVER use example values)

# Run the server
uvicorn app.main:app --reload
```

### Frontend Setup

```bash
cd frontend
npm install
npm start
```

## API Endpoints

### Authentication

- `POST /auth/register/options` - Get registration options for biometric
- `POST /auth/register/verify` - Complete registration with biometric
- `POST /auth/login/options` - Get login options for biometric
- `POST /auth/login/verify` - Complete login with biometric

### OAuth2/OpenID

- `POST /oauth2/token` - OAuth2 token endpoint
- `GET /.well-known/openid-configuration` - OpenID discovery
- `GET /userinfo` - User information endpoint

## Security Features

- **Passwordless Authentication**: No passwords stored anywhere
- **FIDO2/WebAuthn Compliance**: Latest biometric standards with enhanced security
- **Anti-Spoofing Protection**: Multi-layer biometric spoofing prevention
- **Liveness Detection**: Hardware-backed biometric validation
- **Device Fingerprinting**: Consistent device tracking and validation
- **Behavioral Analysis**: Real-time suspicious activity detection
- **HTTPS Enforcement**: TLS 1.3 required for production
- **CORS Protection**: Configured for secure origins
- **Rate Limiting**: DDoS and brute-force protection with progressive penalties
- **JWT Security**: Secure access and refresh tokens
- **Session Management**: Secure session handling with device binding
- **Path Traversal Protection**: Secure file operations
- **Log Injection Prevention**: Sanitized logging
- **Secret Detection**: Automated secret scanning
- **Dependency Scanning**: Vulnerability monitoring
- **Replay Attack Prevention**: Timestamp and nonce validation
- **Credential Cloning Detection**: Unique credential validation

## Database Schema

- **users**: User accounts
- **webauthn_credentials**: Biometric credentials
- **sessions**: Active user sessions
- **oauth_clients**: OAuth2 client applications
- **authorization_codes**: OAuth2 authorization codes

## Environment Variables

⚠️ **SECURITY**: Never hardcode secrets. Use environment variables.

```bash
# Generate secrets first
./scripts/generate-secrets.sh

# Validate environment setup
./scripts/validate-env.sh

# Required variables (see .env.example)
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/authdb  # pragma: allowlist secret
REDIS_URL=redis://:password@localhost:6379
SECRET_KEY=<generated-64-byte-key>
RP_ID=localhost
RP_NAME=Hybrid Auth System
ORIGIN=http://localhost:3000
```

### Configuration Management

- **Symlinked .env files**: Single source of truth for configuration
- **Environment validation**: Automated checks for required variables
- **Cross-platform support**: Works on Windows, macOS, and Linux
- **Docker integration**: Seamless container configuration

See [SECURITY.md](docs/SECURITY.md) for detailed secrets management.

## Development

```bash
# Validate environment
./scripts/validate-env.sh

# Run tests with coverage
cd backend && pytest --cov=app --cov-report=term

# Database migrations
cd backend && alembic upgrade head

# Format code
cd backend && black app/ && isort app/

# Security scan
make security-scan

# Type checking
cd backend && mypy app/
```

### Code Quality Standards

- **SQLAlchemy 2.0**: Modern ORM with type safety
- **Type annotations**: Full type coverage with mypy
- **Error handling**: Comprehensive exception management
- **Logging**: Structured logging with security considerations
- **Testing**: 90%+ test coverage requirement

## Production Deployment

⚠️ **CRITICAL SECURITY STEPS**:

### Pre-Deployment Security Checklist
1. **Generate secure secrets** with `./scripts/generate-secrets.sh`
2. **Validate environment** with `./scripts/validate-env.sh`
3. **Use secrets manager** (AWS Secrets Manager, HashiCorp Vault)
4. **Never commit** .env files or terraform.tfvars
5. **Use HTTPS only** (TLS 1.3) - CWE-319 protection
6. **Configure proper CORS** origins
7. **Enable path traversal protection** - CWE-22 mitigation
8. **Implement log injection prevention** - CWE-117 protection

### Infrastructure Security
9. **Set up database backups** with encryption
10. **Enable rate limiting** and DDoS protection
11. **Configure Secrets Manager encryption** (KMS)
12. **Enable IAM authentication** for RDS
13. **Set up VPC security groups** and NACLs
14. **Implement container security** contexts

### Monitoring and Compliance
15. **Monitor authentication logs** with SIEM integration
16. **Set up vulnerability scanning** (Snyk, Trivy)
17. **Enable secret scanning** in GitHub (TruffleHog)
18. **Configure audit logging** for compliance
19. **Rotate secrets** every 30-60 days
20. **Schedule security assessments** quarterly

### Code Quality Assurance
21. **Run security scans** before deployment
22. **Validate type safety** with mypy
23. **Check test coverage** (90%+ requirement)
24. **Verify dependency updates** are secure

See [DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md), [SECURITY.md](docs/SECURITY.md), [SECURITY_FIXES.md](docs/SECURITY_FIXES.md), and [BIOMETRIC_SECURITY.md](docs/BIOMETRIC_SECURITY.md) for comprehensive security guidance.

## Architecture Diagrams

- [Security Architecture](diagrams/security-architecture.md) - Multi-layer security design
- [Enhanced Authentication Flow](diagrams/enhanced-auth-flow.md) - Biometric authentication with anti-spoofing
- [System Architecture](diagrams/system-architecture.mmd) - Overall system design
- [Database Schema](diagrams/database-schema.mmd) - Data model relationships

## License

MIT
