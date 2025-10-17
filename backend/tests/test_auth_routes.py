"""
Comprehensive tests for authentication routes.
"""

import base64
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes.auth import router
from app.db.models import User


@pytest.fixture
def client():
    """Test client fixture."""
    # Create a test app without middleware to avoid middleware interference
    from fastapi import FastAPI

    test_app = FastAPI()
    test_app.include_router(router)
    return TestClient(test_app)


def create_test_client_with_db_override(mock_db):
    """Helper function to create test client with database override."""
    from fastapi import FastAPI

    from app.db.database import get_db

    def override_get_db():
        return mock_db

    test_app = FastAPI()
    test_app.include_router(router)
    test_app.dependency_overrides[get_db] = override_get_db

    return TestClient(test_app)


@pytest.fixture
def mock_db():
    """Mock database session."""
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    return AsyncMock()


@pytest.fixture
def sample_user():
    """Sample user for testing."""
    return User(
        id=1,
        email="test@example.com",
        username="testuser",
        display_name="Test User",
        is_active=True,
        is_verified=True,
    )


@pytest.fixture
def sample_credential():
    """Sample WebAuthn credential."""
    return {
        "id": "test-credential-id",
        "rawId": base64.b64encode(b"test-credential-id").decode(),
        "response": {
            "clientDataJSON": base64.b64encode(b'{"type":"webauthn.create"}').decode(),
            "attestationObject": base64.b64encode(b"test-attestation").decode(),
            "authenticatorData": base64.b64encode(b"test-auth-data").decode(),
        },
        "type": "public-key",
    }


class TestRegistrationOptions:
    """Test registration options endpoint."""

    @patch("app.api.routes.auth.SecurityService.is_rate_limited")
    @patch("app.api.routes.auth.SecurityService.generate_device_fingerprint")
    @patch("app.api.routes.auth.SecurityService.log_security_event")
    @patch("app.api.routes.auth.WebAuthnService.generate_registration_options")
    @patch("app.api.routes.auth.redis_client")
    async def test_registration_options_success(
        self,
        mock_redis,
        mock_webauthn,
        mock_log_event,
        mock_fingerprint,
        mock_rate_limited,
        client,
        mock_db,
    ):
        """Test successful registration options generation."""
        # Setup mocks
        mock_rate_limited.return_value = False
        mock_fingerprint.return_value = "test-fingerprint"
        mock_log_event.return_value = AsyncMock()

        mock_webauthn.return_value = {
            "challenge": "test-challenge",
            "user": {"id": "test-id"},
        }

        mock_redis.setex = AsyncMock()

        # Setup database mock properly
        from unittest.mock import MagicMock

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Test request with required fields
        request_data = {
            "email": "test@example.com",
            "username": "testuser",
            "first_name": "Test",
            "last_name": "User",
        }

        test_client = create_test_client_with_db_override(mock_db)
        response = test_client.post("/auth/register/options", json=request_data)

        assert response.status_code == 200
        mock_log_event.assert_called()
        mock_redis.setex.assert_called()

    @patch("app.api.routes.auth.SecurityService.is_rate_limited")
    @patch("app.api.routes.auth.SecurityService.log_security_event")
    async def test_registration_options_rate_limited(
        self, mock_log_event, mock_rate_limited, client, mock_db
    ):
        """Test registration options with rate limiting."""
        mock_rate_limited.return_value = True
        mock_log_event.return_value = AsyncMock()

        request_data = {
            "email": "test@example.com",
            "username": "testuser",
            "first_name": "Test",
            "last_name": "User",
        }

        test_client = create_test_client_with_db_override(mock_db)
        response = test_client.post("/auth/register/options", json=request_data)

        assert response.status_code == 429
        assert "Too many registration attempts" in response.json()["detail"]

    @patch("app.api.routes.auth.SecurityService.is_rate_limited")
    @patch("app.api.routes.auth.SecurityService.log_security_event")
    async def test_registration_options_user_exists(
        self, mock_log_event, mock_rate_limited, client, mock_db, sample_user
    ):
        """Test registration options when user already exists."""
        mock_rate_limited.return_value = False
        mock_log_event.return_value = AsyncMock()

        from unittest.mock import MagicMock

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_user
        mock_db.execute = AsyncMock(return_value=mock_result)

        request_data = {
            "email": "test@example.com",
            "username": "testuser",
            "first_name": "Test",
            "last_name": "User",
        }

        test_client = create_test_client_with_db_override(mock_db)
        response = test_client.post("/auth/register/options", json=request_data)

        assert response.status_code == 400
        assert "User already exists" in response.json()["detail"]

    @patch("app.api.routes.auth.SecurityService.is_rate_limited")
    @patch("app.api.routes.auth.SecurityService.generate_device_fingerprint")
    @patch("app.api.routes.auth.WebAuthnService.generate_registration_options")
    async def test_registration_options_webauthn_error(
        self, mock_webauthn, mock_fingerprint, mock_rate_limited, client, mock_db
    ):
        """Test registration options with WebAuthn service error."""
        mock_rate_limited.return_value = False
        mock_fingerprint.return_value = "test-fingerprint"

        from unittest.mock import MagicMock

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        mock_webauthn.side_effect = Exception("WebAuthn error")

        request_data = {
            "email": "test@example.com",
            "username": "testuser",
            "first_name": "Test",
            "last_name": "User",
        }

        test_client = create_test_client_with_db_override(mock_db)
        response = test_client.post("/auth/register/options", json=request_data)

        assert response.status_code == 500
        assert "Registration unavailable" in response.json()["detail"]


class TestRegistrationVerify:
    """Test registration verification endpoint."""

    @patch("app.api.routes.auth.SecurityService.generate_device_fingerprint")
    @patch("app.api.routes.auth.SecurityService.validate_biometric_quality")
    @patch("app.api.routes.auth.SecurityService.log_security_event")
    @patch("app.api.routes.auth.BiometricSecurityValidator.detect_presentation_attack")
    @patch("app.api.routes.auth.WebAuthnService.verify_registration")
    @patch("app.api.routes.auth.redis_client")
    @patch("app.api.routes.auth.create_access_token")
    @patch("app.api.routes.auth.create_refresh_token")
    async def test_registration_verify_success(
        self,
        mock_refresh_token,
        mock_access_token,
        mock_redis,
        mock_webauthn,
        mock_biometric,
        mock_log_event,
        mock_quality,
        mock_fingerprint,
        client,
        mock_db,
        sample_credential,
    ):
        """Test successful registration verification."""
        import json

        mock_redis.get = AsyncMock(
            return_value=json.dumps(
                {
                    "challenge": "test-challenge",
                    "device_fingerprint": "test-fingerprint",
                    "ip_address": "127.0.0.1",
                    "timestamp": datetime.now().isoformat(),
                }
            )
        )
        mock_redis.delete = AsyncMock()

        mock_fingerprint.return_value = "test-fingerprint"
        mock_quality.return_value = True
        mock_log_event.return_value = AsyncMock()
        mock_biometric.return_value = False
        mock_webauthn.return_value = MagicMock(credential_id=b"test-cred-id")
        mock_access_token.return_value = "test-access-token"
        mock_refresh_token.return_value = "test-refresh-token"

        mock_db.add = MagicMock()
        mock_db.flush = AsyncMock()
        mock_db.commit = AsyncMock()

        request_data = {
            "email": "test@example.com",
            "username": "testuser",
            "first_name": "Test",
            "last_name": "User",
            "credential": sample_credential,
        }

        test_client = create_test_client_with_db_override(mock_db)
        response = test_client.post("/auth/register/verify", json=request_data)

        assert response.status_code == 200
        response_data = response.json()
        assert "access_token" in response_data
        assert "refresh_token" in response_data


class TestLoginOptions:
    """Test login options endpoint."""

    @patch("app.api.routes.auth.SecurityService.is_rate_limited")
    @patch("app.api.routes.auth.SecurityService.check_account_lockout")
    @patch("app.api.routes.auth.SecurityService.detect_suspicious_activity")
    @patch("app.api.routes.auth.SecurityService.generate_device_fingerprint")
    @patch("app.api.routes.auth.SecurityService.log_security_event")
    @patch("app.api.routes.auth.WebAuthnService.generate_authentication_options")
    @patch("app.api.routes.auth.redis_client")
    async def test_login_options_success(
        self,
        mock_redis,
        mock_webauthn,
        mock_log_event,
        mock_fingerprint,
        mock_suspicious,
        mock_lockout,
        mock_rate_limited,
        client,
        mock_db,
        sample_user,
    ):
        """Test successful login options generation."""
        mock_rate_limited.return_value = False
        mock_lockout.return_value = False
        mock_suspicious.return_value = []
        mock_fingerprint.return_value = "test-fingerprint"
        mock_log_event.return_value = AsyncMock()

        from unittest.mock import MagicMock

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_user
        mock_db.execute = AsyncMock(return_value=mock_result)

        mock_webauthn.return_value = {"challenge": "test-challenge"}
        mock_redis.setex = AsyncMock()

        request_data = {"identifier": "test@example.com"}

        test_client = create_test_client_with_db_override(mock_db)
        response = test_client.post("/auth/login/options", json=request_data)

        assert response.status_code == 200
        mock_log_event.assert_called()

    @patch("app.api.routes.auth.SecurityService.is_rate_limited")
    @patch("app.api.routes.auth.SecurityService.log_security_event")
    async def test_login_options_rate_limited(
        self, mock_log_event, mock_rate_limited, client, mock_db
    ):
        """Test login options with rate limiting."""
        mock_rate_limited.return_value = True
        mock_log_event.return_value = AsyncMock()

        request_data = {"identifier": "test@example.com"}

        test_client = create_test_client_with_db_override(mock_db)
        response = test_client.post("/auth/login/options", json=request_data)

        assert response.status_code == 429
        assert "Too many authentication attempts" in response.json()["detail"]

    @patch("app.api.routes.auth.SecurityService.is_rate_limited")
    @patch("app.api.routes.auth.SecurityService.log_security_event")
    async def test_login_options_user_not_found(
        self, mock_log_event, mock_rate_limited, client, mock_db
    ):
        """Test login options when user not found."""
        mock_rate_limited.return_value = False
        mock_log_event.return_value = AsyncMock()

        from unittest.mock import MagicMock

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        request_data = {"identifier": "test@example.com"}

        test_client = create_test_client_with_db_override(mock_db)
        response = test_client.post("/auth/login/options", json=request_data)

        assert response.status_code == 404
        assert "User not found" in response.json()["detail"]


class TestLoginVerify:
    """Test login verification endpoint."""

    @patch("app.api.routes.auth.SecurityService.generate_device_fingerprint")
    @patch("app.api.routes.auth.SecurityService.log_security_event")
    @patch("app.api.routes.auth.BiometricSecurityValidator.detect_presentation_attack")
    @patch("app.api.routes.auth.WebAuthnService.verify_authentication")
    @patch("app.api.routes.auth.redis_client")
    @patch("app.api.routes.auth.create_access_token")
    @patch("app.api.routes.auth.create_refresh_token")
    async def test_login_verify_success(
        self,
        mock_refresh_token,
        mock_access_token,
        mock_redis,
        mock_webauthn,
        mock_presentation,
        mock_log_event,
        mock_fingerprint,
        client,
        mock_db,
        sample_user,
        sample_credential,
    ):
        """Test successful login verification."""
        import json

        challenge_data = {
            "challenge": "dGVzdC1jaGFsbGVuZ2U",
            "device_fingerprint": "test-fingerprint",
            "ip_address": "127.0.0.1",
            "timestamp": datetime.now().isoformat(),
            "user_id": "1",
        }

        mock_redis.get = AsyncMock(return_value=json.dumps(challenge_data))
        mock_redis.delete = AsyncMock()

        from unittest.mock import MagicMock

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_user
        mock_db.execute = AsyncMock(return_value=mock_result)

        mock_fingerprint.return_value = "test-fingerprint"
        mock_log_event.return_value = AsyncMock()
        mock_presentation.return_value = False
        mock_webauthn.return_value = MagicMock(new_sign_count=1)
        mock_access_token.return_value = "test-access-token"
        mock_refresh_token.return_value = "test-refresh-token"

        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()

        request_data = {
            "identifier": "test@example.com",
            "credential": sample_credential,
        }

        test_client = create_test_client_with_db_override(mock_db)
        response = test_client.post("/auth/login/verify", json=request_data)

        assert response.status_code == 200
        response_data = response.json()
        assert "access_token" in response_data
        assert "refresh_token" in response_data
