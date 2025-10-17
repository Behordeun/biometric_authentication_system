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

        # Test request
        request_data = {"email": "test@example.com", "username": "testuser"}

        # Override the dependency
        def override_get_db():
            return mock_db

        from fastapi import FastAPI

        from app.db.database import get_db

        # Create a new test app and override the dependency
        test_app = FastAPI()
        test_app.include_router(router)
        test_app.dependency_overrides[get_db] = override_get_db

        test_client = TestClient(test_app)
        response = test_client.post("/auth/register/options", json=request_data)

        if response.status_code != 200:
            print(f"Response status: {response.status_code}")
            print(f"Response content: {response.text}")
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

        request_data = {"email": "test@example.com", "username": "testuser"}

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

        request_data = {"email": "test@example.com", "username": "testuser"}

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

        request_data = {"email": "test@example.com", "username": "testuser"}

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
        # Setup mocks
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
            "credential": sample_credential,
        }

        test_client = create_test_client_with_db_override(mock_db)
        response = test_client.post("/auth/register/verify", json=request_data)

        if response.status_code != 200:
            print(f"Response status: {response.status_code}")
            print(f"Response content: {response.text}")
        assert response.status_code == 200
        response_data = response.json()
        assert "access_token" in response_data
        assert "refresh_token" in response_data

    @patch("app.api.routes.auth.redis_client")
    async def test_registration_verify_expired_challenge(
        self, mock_redis, client, mock_db
    ):
        """Test registration verification with expired challenge."""
        mock_redis.get = AsyncMock(return_value=None)

        request_data = {
            "email": "test@example.com",
            "username": "testuser",
            "credential": {"id": "test"},
        }

        test_client = create_test_client_with_db_override(mock_db)
        response = test_client.post("/auth/register/verify", json=request_data)

        assert response.status_code == 400
        assert "Challenge expired" in response.json()["detail"]

    @patch("app.api.routes.auth.SecurityService")
    @patch("app.api.routes.auth.redis_client")
    async def test_registration_verify_device_mismatch(
        self, mock_redis, mock_security, client, mock_db, sample_credential
    ):
        """Test registration verification with device fingerprint mismatch."""
        import json

        mock_redis.get = AsyncMock(
            return_value=json.dumps(
                {
                    "challenge": "dGVzdC1jaGFsbGVuZ2U",  # base64 encoded
                    "device_fingerprint": "old-fingerprint",
                    "ip_address": "127.0.0.1",
                    "timestamp": datetime.now().isoformat(),
                }
            )
        )

        mock_security.generate_device_fingerprint.return_value = "new-fingerprint"
        mock_security.log_security_event = AsyncMock()

        request_data = {
            "email": "test@example.com",
            "username": "testuser",
            "credential": sample_credential,
        }

        with patch("app.api.routes.auth.get_db", return_value=mock_db):
            response = client.post("/auth/register/verify", json=request_data)

        assert response.status_code == 400
        assert "Device validation failed" in response.json()["detail"]

    @patch("app.api.routes.auth.SecurityService")
    @patch("app.api.routes.auth.redis_client")
    async def test_registration_verify_poor_biometric_quality(
        self, mock_redis, mock_security, client, mock_db, sample_credential
    ):
        """Test registration verification with poor biometric quality."""
        import json

        mock_redis.get = AsyncMock(
            return_value=json.dumps(
                {
                    "challenge": "dGVzdC1jaGFsbGVuZ2U",  # base64 encoded
                    "device_fingerprint": "test-fingerprint",
                    "ip_address": "127.0.0.1",
                    "timestamp": datetime.now().isoformat(),
                }
            )
        )

        mock_security.generate_device_fingerprint.return_value = "test-fingerprint"
        mock_security.validate_biometric_quality.return_value = False
        mock_security.log_security_event = AsyncMock()

        request_data = {
            "email": "test@example.com",
            "username": "testuser",
            "credential": sample_credential,
        }

        with patch("app.api.routes.auth.get_db", return_value=mock_db):
            response = client.post("/auth/register/verify", json=request_data)

        assert response.status_code == 400
        assert "Biometric quality insufficient" in response.json()["detail"]

    @patch("app.api.routes.auth.SecurityService")
    @patch("app.api.routes.auth.BiometricSecurityValidator")
    @patch("app.api.routes.auth.redis_client")
    async def test_registration_verify_presentation_attack(
        self,
        mock_redis,
        mock_biometric,
        mock_security,
        client,
        mock_db,
        sample_credential,
    ):
        """Test registration verification with presentation attack detected."""
        import json

        mock_redis.get = AsyncMock(
            return_value=json.dumps(
                {
                    "challenge": "dGVzdC1jaGFsbGVuZ2U",  # base64 encoded
                    "device_fingerprint": "test-fingerprint",
                    "ip_address": "127.0.0.1",
                    "timestamp": datetime.now().isoformat(),
                }
            )
        )

        mock_security.generate_device_fingerprint.return_value = "test-fingerprint"
        mock_security.validate_biometric_quality.return_value = True
        mock_security.log_security_event = AsyncMock()

        mock_biometric.detect_presentation_attack.return_value = True

        request_data = {
            "email": "test@example.com",
            "username": "testuser",
            "credential": sample_credential,
        }

        with patch("app.api.routes.auth.get_db", return_value=mock_db):
            response = client.post("/auth/register/verify", json=request_data)

        assert response.status_code == 400
        assert "Security validation failed" in response.json()["detail"]


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

        request_data = {"email": "test@example.com"}

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

        request_data = {"email": "test@example.com"}

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

        request_data = {"email": "test@example.com"}

        test_client = create_test_client_with_db_override(mock_db)
        response = test_client.post("/auth/login/options", json=request_data)

        assert response.status_code == 404
        assert "User not found" in response.json()["detail"]

    @patch("app.api.routes.auth.SecurityService.is_rate_limited")
    @patch("app.api.routes.auth.SecurityService.check_account_lockout")
    @patch("app.api.routes.auth.SecurityService.log_security_event")
    async def test_login_options_account_locked(
        self,
        mock_log_event,
        mock_lockout,
        mock_rate_limited,
        client,
        mock_db,
        sample_user,
    ):
        """Test login options with locked account."""
        mock_rate_limited.return_value = False
        mock_lockout.return_value = True
        mock_log_event.return_value = AsyncMock()

        from unittest.mock import MagicMock

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_user
        mock_db.execute = AsyncMock(return_value=mock_result)

        request_data = {"email": "test@example.com"}

        test_client = create_test_client_with_db_override(mock_db)
        response = test_client.post("/auth/login/options", json=request_data)

        assert response.status_code == 423
        assert "Account temporarily locked" in response.json()["detail"]

    @patch("app.api.routes.auth.SecurityService.is_rate_limited")
    @patch("app.api.routes.auth.SecurityService.check_account_lockout")
    @patch("app.api.routes.auth.SecurityService.detect_suspicious_activity")
    @patch("app.api.routes.auth.SecurityService.generate_device_fingerprint")
    @patch("app.api.routes.auth.SecurityService.log_security_event")
    @patch("app.api.routes.auth.WebAuthnService.generate_authentication_options")
    @patch("app.api.routes.auth.redis_client")
    async def test_login_options_suspicious_activity(
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
        """Test login options with suspicious activity detected."""
        mock_rate_limited.return_value = False
        mock_lockout.return_value = False
        mock_suspicious.return_value = ["unusual_location", "rapid_requests"]
        mock_fingerprint.return_value = "test-fingerprint"
        mock_log_event.return_value = AsyncMock()

        from unittest.mock import MagicMock

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_user
        mock_db.execute = AsyncMock(return_value=mock_result)

        mock_webauthn.return_value = {"challenge": "test-challenge"}
        mock_redis.setex = AsyncMock()

        request_data = {"email": "test@example.com"}

        test_client = create_test_client_with_db_override(mock_db)
        response = test_client.post("/auth/login/options", json=request_data)

        assert response.status_code == 200
        # Should log suspicious activity
        mock_log_event.assert_called()


class TestLoginVerify:
    """Test login verification endpoint."""

    @patch("app.api.routes.auth.SecurityService.generate_device_fingerprint")
    @patch("app.api.routes.auth.SecurityService.log_security_event")
    @patch("app.api.routes.auth.BiometricSecurityValidator.validate_liveness")
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
        mock_liveness,
        mock_log_event,
        mock_fingerprint,
        client,
        mock_db,
        sample_user,
        sample_credential,
    ):
        """Test successful login verification."""
        # Setup challenge data
        import json

        challenge_data = {
            "challenge": "dGVzdC1jaGFsbGVuZ2U",  # base64 encoded
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

        mock_liveness.return_value = True
        mock_presentation.return_value = False

        mock_webauthn.return_value = MagicMock(new_sign_count=1)

        mock_access_token.return_value = "test-access-token"
        mock_refresh_token.return_value = "test-refresh-token"

        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()

        request_data = {
            "email": "test@example.com",
            "credential": sample_credential,
        }

        test_client = create_test_client_with_db_override(mock_db)
        response = test_client.post("/auth/login/verify", json=request_data)

        assert response.status_code == 200
        response_data = response.json()
        assert "access_token" in response_data
        assert "refresh_token" in response_data

    @patch("app.api.routes.auth.redis_client")
    async def test_login_verify_expired_challenge(self, mock_redis, client, mock_db):
        """Test login verification with expired challenge."""
        mock_redis.get = AsyncMock(return_value=None)

        request_data = {
            "email": "test@example.com",
            "credential": {"id": "test"},
        }

        test_client = create_test_client_with_db_override(mock_db)
        response = test_client.post("/auth/login/verify", json=request_data)

        assert response.status_code == 400
        assert "Challenge expired" in response.json()["detail"]

    @patch("app.api.routes.auth.SecurityService.log_security_event")
    @patch("app.api.routes.auth.redis_client")
    async def test_login_verify_user_mismatch(
        self, mock_redis, mock_log_event, client, mock_db, sample_credential
    ):
        """Test login verification with user mismatch."""
        import json

        challenge_data = {
            "challenge": "dGVzdC1jaGFsbGVuZ2U",  # base64 encoded
            "device_fingerprint": "test-fingerprint",
            "ip_address": "127.0.0.1",
            "timestamp": datetime.now().isoformat(),
            "user_id": "999",  # Different user ID
        }

        mock_redis.get = AsyncMock(return_value=json.dumps(challenge_data))
        mock_log_event.return_value = AsyncMock()

        from unittest.mock import MagicMock

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        request_data = {
            "email": "test@example.com",
            "credential": sample_credential,
        }

        test_client = create_test_client_with_db_override(mock_db)
        response = test_client.post("/auth/login/verify", json=request_data)

        assert response.status_code == 404
        assert "Authentication failed" in response.json()["detail"]

    @patch("app.api.routes.auth.SecurityService.generate_device_fingerprint")
    @patch("app.api.routes.auth.SecurityService.log_security_event")
    @patch("app.api.routes.auth.BiometricSecurityValidator.validate_liveness")
    @patch("app.api.routes.auth.redis_client")
    async def test_login_verify_liveness_failed(
        self,
        mock_redis,
        mock_liveness,
        mock_log_event,
        mock_fingerprint,
        client,
        mock_db,
        sample_user,
        sample_credential,
    ):
        """Test login verification with liveness check failure."""
        import json

        challenge_data = {
            "challenge": "dGVzdC1jaGFsbGVuZ2U",  # base64 encoded
            "device_fingerprint": "test-fingerprint",
            "ip_address": "127.0.0.1",
            "timestamp": datetime.now().isoformat(),
            "user_id": "1",
        }

        mock_redis.get = AsyncMock(return_value=json.dumps(challenge_data))

        from unittest.mock import MagicMock

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_user
        mock_db.execute = AsyncMock(return_value=mock_result)

        mock_fingerprint.return_value = "test-fingerprint"
        mock_log_event.return_value = AsyncMock()

        mock_liveness.return_value = False

        request_data = {
            "email": "test@example.com",
            "credential": sample_credential,
        }

        test_client = create_test_client_with_db_override(mock_db)
        response = test_client.post("/auth/login/verify", json=request_data)

        assert response.status_code == 400
        assert "Biometric validation failed" in response.json()["detail"]

    @patch("app.api.routes.auth.SecurityService.generate_device_fingerprint")
    @patch("app.api.routes.auth.SecurityService.log_security_event")
    @patch("app.api.routes.auth.BiometricSecurityValidator.validate_liveness")
    @patch("app.api.routes.auth.BiometricSecurityValidator.detect_presentation_attack")
    @patch("app.api.routes.auth.redis_client")
    async def test_login_verify_presentation_attack(
        self,
        mock_redis,
        mock_presentation,
        mock_liveness,
        mock_log_event,
        mock_fingerprint,
        client,
        mock_db,
        sample_user,
        sample_credential,
    ):
        """Test login verification with presentation attack detected."""
        import json

        challenge_data = {
            "challenge": "dGVzdC1jaGFsbGVuZ2U",  # base64 encoded
            "device_fingerprint": "test-fingerprint",
            "ip_address": "127.0.0.1",
            "timestamp": datetime.now().isoformat(),
            "user_id": "1",
        }

        mock_redis.get = AsyncMock(return_value=json.dumps(challenge_data))

        from unittest.mock import MagicMock

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_user
        mock_db.execute = AsyncMock(return_value=mock_result)

        mock_fingerprint.return_value = "test-fingerprint"
        mock_log_event.return_value = AsyncMock()

        mock_liveness.return_value = True
        mock_presentation.return_value = True

        request_data = {
            "email": "test@example.com",
            "credential": sample_credential,
        }

        test_client = create_test_client_with_db_override(mock_db)
        response = test_client.post("/auth/login/verify", json=request_data)

        assert response.status_code == 400
        assert "Security validation failed" in response.json()["detail"]

    @patch("app.api.routes.auth.SecurityService.generate_device_fingerprint")
    @patch("app.api.routes.auth.SecurityService.log_security_event")
    @patch("app.api.routes.auth.redis_client")
    async def test_login_verify_device_mismatch(
        self,
        mock_redis,
        mock_log_event,
        mock_fingerprint,
        client,
        mock_db,
        sample_user,
        sample_credential,
    ):
        """Test login verification with device fingerprint mismatch."""
        import json

        challenge_data = {
            "challenge": "dGVzdC1jaGFsbGVuZ2U",  # base64 encoded
            "device_fingerprint": "old-fingerprint",
            "ip_address": "127.0.0.1",
            "timestamp": datetime.now().isoformat(),
            "user_id": "1",
        }

        mock_redis.get = AsyncMock(return_value=json.dumps(challenge_data))

        from unittest.mock import MagicMock

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_user
        mock_db.execute = AsyncMock(return_value=mock_result)

        mock_fingerprint.return_value = "new-fingerprint"
        mock_log_event.return_value = AsyncMock()

        request_data = {
            "email": "test@example.com",
            "credential": sample_credential,
        }

        test_client = create_test_client_with_db_override(mock_db)
        response = test_client.post("/auth/login/verify", json=request_data)

        assert response.status_code == 400
        assert "Device validation failed" in response.json()["detail"]

    @patch("app.api.routes.auth.SecurityService")
    @patch("app.api.routes.auth.BiometricSecurityValidator")
    @patch("app.api.routes.auth.WebAuthnService")
    @patch("app.api.routes.auth.redis_client")
    async def test_login_verify_webauthn_error(
        self,
        mock_redis,
        mock_webauthn,
        mock_biometric,
        mock_security,
        client,
        mock_db,
        sample_user,
        sample_credential,
    ):
        """Test login verification with WebAuthn service error."""
        challenge_data = {
            "challenge": "test-challenge",
            "device_fingerprint": "test-fingerprint",
            "ip_address": "127.0.0.1",
            "timestamp": datetime.now().isoformat(),
            "user_id": "1",
        }

        mock_redis.get = AsyncMock(return_value=str(challenge_data))

        mock_db.execute = AsyncMock()
        mock_db.execute.return_value.scalar_one_or_none.return_value = sample_user

        mock_security.generate_device_fingerprint.return_value = "test-fingerprint"
        mock_security.log_security_event = AsyncMock()

        mock_biometric.validate_liveness.return_value = True
        mock_biometric.detect_presentation_attack.return_value = False

        mock_webauthn.verify_authentication = AsyncMock(
            side_effect=Exception("WebAuthn verification failed")
        )

        request_data = {
            "email": "test@example.com",
            "credential": sample_credential,
        }

        with patch("app.api.routes.auth.get_db", return_value=mock_db):
            response = client.post("/auth/login/verify", json=request_data)

        assert response.status_code == 400
        assert "Authentication failed" in response.json()["detail"]
