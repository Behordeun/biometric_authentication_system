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

## Tech Stack

**Backend**: Python 3.11+, FastAPI, SQLAlchemy, WebAuthn
**Frontend**: React, TypeScript, WebAuthn API
**Database**: PostgreSQL
**Cache**: Redis

## Quick Start

### Using Docker (Recommended)

```bash
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

- No passwords stored anywhere
- FIDO2/WebAuthn compliance
- HTTPS required for production
- CORS configured
- Rate limiting enabled
- JWT with refresh tokens
- Session management

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

# Required variables (see .env.example)
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/authdb  # pragma: allowlist secret
REDIS_URL=redis://:password@localhost:6379
SECRET_KEY=<generated-64-byte-key>
RP_ID=localhost
RP_NAME=Hybrid Auth System
ORIGIN=http://localhost:3000
```

See [SECURITY.md](docs/SECURITY.md) for detailed secrets management.

## Development

```bash
# Run tests
pytest

# Database migrations
alembic upgrade head

# Format code
black app/
```

## Production Deployment

⚠️ **CRITICAL SECURITY STEPS**:

1. **Generate secure secrets** with `./scripts/generate-secrets.sh`
2. **Use secrets manager** (AWS Secrets Manager, HashiCorp Vault)
3. **Never commit** .env files or terraform.tfvars
4. **Use HTTPS only** (TLS 1.3)
5. **Configure proper CORS** origins
6. **Set up database backups**
7. **Enable rate limiting**
8. **Monitor authentication logs**
9. **Rotate secrets** every 30-60 days
10. **Enable secret scanning** in GitHub

See [DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md) and [SECURITY.md](docs/SECURITY.md)

## License

MIT
