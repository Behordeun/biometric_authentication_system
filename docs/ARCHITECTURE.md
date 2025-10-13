# System Architecture

## Overview

This is a hybrid passwordless authentication system that combines the best features of KeyCloak, OpenID Connect, OAuth2, and WebAuthn/FIDO2 for biometric authentication.

## Core Components

### 1. Authentication Layer (WebAuthn/FIDO2)
- **Passwordless by Design**: No passwords stored anywhere
- **Biometric Support**: Fingerprint, Face ID, Windows Hello
- **Hardware Security**: Uses device's secure enclave
- **Public Key Cryptography**: Asymmetric key pairs per device

### 2. Authorization Layer (OAuth2)
- **Authorization Code Flow**: Standard OAuth2 flow
- **Client Credentials**: For service-to-service auth
- **Refresh Tokens**: Long-lived session management
- **Scope-based Access**: Granular permissions

### 3. Identity Layer (OpenID Connect)
- **ID Tokens**: JWT-based identity claims
- **UserInfo Endpoint**: Standard user profile access
- **Discovery Endpoint**: Auto-configuration support
- **Claims Mapping**: Flexible attribute mapping

## Data Flow

### Registration Flow
```
1. User enters email/username
2. Frontend requests registration options from backend
3. Backend generates WebAuthn challenge
4. User authenticates with biometric (device prompts)
5. Device creates key pair, returns public key + signature
6. Backend verifies signature, stores public key
7. User account created, tokens issued
```

### Login Flow
```
1. User enters email
2. Frontend requests authentication options
3. Backend generates challenge, retrieves user's credentials
4. User authenticates with biometric
5. Device signs challenge with private key
6. Backend verifies signature with stored public key
7. Tokens issued, session created
```

### OAuth2 Flow
```
1. Client redirects user to /oauth2/authorize
2. User authenticates with biometric
3. Authorization code generated
4. Client exchanges code for tokens at /oauth2/token
5. Client uses access token for API calls
```

## Security Features

### WebAuthn Security
- **Origin Binding**: Credentials tied to domain
- **Attestation**: Device authenticity verification
- **Counter Tracking**: Replay attack prevention
- **User Verification**: Biometric or PIN required

### Token Security
- **Short-lived Access Tokens**: 30 minutes default
- **Rotating Refresh Tokens**: 7 days default
- **JWT Signing**: HS256 algorithm
- **Token Revocation**: Session management

### Database Security
- **No Password Storage**: Only public keys stored
- **UUID Primary Keys**: Non-sequential IDs
- **Encrypted Connections**: TLS for all DB traffic
- **Audit Logging**: Track all auth events

## Technology Stack

### Backend
- **FastAPI**: Modern async Python framework
- **SQLAlchemy**: ORM with async support
- **PostgreSQL**: Relational database
- **Redis**: Session and challenge storage
- **py_webauthn**: WebAuthn implementation

### Frontend
- **React**: UI framework
- **TypeScript**: Type safety
- **@simplewebauthn/browser**: WebAuthn client
- **Axios**: HTTP client

## Database Schema

### users
- id (UUID, PK)
- email (unique)
- username (unique)
- display_name
- is_active, is_verified
- created_at, updated_at

### webauthn_credentials
- id (UUID, PK)
- user_id (FK)
- credential_id (unique)
- public_key (base64)
- sign_count (replay protection)
- transports (USB, NFC, BLE, internal)
- device_name
- created_at, last_used

### sessions
- id (UUID, PK)
- user_id (FK)
- refresh_token (unique)
- expires_at
- ip_address, user_agent
- created_at

### oauth_clients
- id (UUID, PK)
- client_id, client_secret
- name
- redirect_uris (JSONB)
- grant_types (JSONB)
- scope
- owner_id (FK)

### authorization_codes
- id (UUID, PK)
- code (unique)
- client_id, user_id (FK)
- redirect_uri, scope
- expires_at

## API Endpoints

### Authentication
- POST /auth/register/options
- POST /auth/register/verify
- POST /auth/login/options
- POST /auth/login/verify

### OAuth2/OIDC
- GET /oauth2/authorize
- POST /oauth2/token
- GET /userinfo
- GET /.well-known/openid-configuration

### User Management
- GET /users/me
- PATCH /users/me
- GET /users/me/sessions
- DELETE /users/me/sessions/{id}

## Deployment

### Development
```bash
docker-compose up
```

### Production Considerations
- Use HTTPS only (WebAuthn requirement)
- Set strong SECRET_KEY
- Configure proper CORS
- Enable rate limiting
- Set up monitoring
- Database backups
- Redis persistence
- Load balancing

## Comparison with Existing Systems

### vs KeyCloak
- Lighter weight, easier to customize
- Native passwordless support
- Simpler deployment

### vs Auth0
- Self-hosted, full control
- No per-user pricing
- Open source

### vs Okta
- Modern tech stack
- Biometric-first approach
- Developer-friendly API

## Future Enhancements

- [ ] Multi-device management
- [ ] Passkey sync across devices
- [ ] SAML support
- [ ] Social login integration
- [ ] Admin dashboard
- [ ] Audit log UI
- [ ] Rate limiting per endpoint
- [ ] Email verification
- [ ] Account recovery flow
- [ ] MFA with TOTP backup
