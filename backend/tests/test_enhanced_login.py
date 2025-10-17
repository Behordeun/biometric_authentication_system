"""
Test for enhanced login functionality with email or username.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.api.routes.auth import router
from app.db.models import User


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


class TestEnhancedLogin:
    """Test enhanced login with email or username."""

    @patch("app.api.routes.auth.SecurityService.is_rate_limited")
    @patch("app.api.routes.auth.SecurityService.check_account_lockout")
    @patch("app.api.routes.auth.SecurityService.detect_suspicious_activity")
    @patch("app.api.routes.auth.SecurityService.generate_device_fingerprint")
    @patch("app.api.routes.auth.SecurityService.log_security_event")
    @patch("app.api.routes.auth.WebAuthnService.generate_authentication_options")
    @patch("app.api.routes.auth.redis_client")
    async def test_login_with_email(
        self,
        mock_redis,
        mock_webauthn,
        mock_log_event,
        mock_fingerprint,
        mock_suspicious,
        mock_lockout,
        mock_rate_limited,
        mock_db,
        sample_user,
    ):
        """Test login options with email identifier."""
        mock_rate_limited.return_value = False
        mock_lockout.return_value = False
        mock_suspicious.return_value = []
        mock_fingerprint.return_value = "test-fingerprint"
        mock_log_event.return_value = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_user
        mock_db.execute = AsyncMock(return_value=mock_result)

        mock_webauthn.return_value = {"challenge": "test-challenge"}
        mock_redis.setex = AsyncMock()

        request_data = {"identifier": "test@example.com"}

        test_client = create_test_client_with_db_override(mock_db)
        response = test_client.post("/auth/login/options", json=request_data)

        assert response.status_code == 200

    @patch("app.api.routes.auth.SecurityService.is_rate_limited")
    @patch("app.api.routes.auth.SecurityService.check_account_lockout")
    @patch("app.api.routes.auth.SecurityService.detect_suspicious_activity")
    @patch("app.api.routes.auth.SecurityService.generate_device_fingerprint")
    @patch("app.api.routes.auth.SecurityService.log_security_event")
    @patch("app.api.routes.auth.WebAuthnService.generate_authentication_options")
    @patch("app.api.routes.auth.redis_client")
    async def test_login_with_username(
        self,
        mock_redis,
        mock_webauthn,
        mock_log_event,
        mock_fingerprint,
        mock_suspicious,
        mock_lockout,
        mock_rate_limited,
        mock_db,
        sample_user,
    ):
        """Test login options with username identifier."""
        mock_rate_limited.return_value = False
        mock_lockout.return_value = False
        mock_suspicious.return_value = []
        mock_fingerprint.return_value = "test-fingerprint"
        mock_log_event.return_value = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_user
        mock_db.execute = AsyncMock(return_value=mock_result)

        mock_webauthn.return_value = {"challenge": "test-challenge"}
        mock_redis.setex = AsyncMock()

        request_data = {"identifier": "testuser"}

        test_client = create_test_client_with_db_override(mock_db)
        response = test_client.post("/auth/login/options", json=request_data)

        assert response.status_code == 200

    @patch("app.api.routes.auth.SecurityService.is_rate_limited")
    @patch("app.api.routes.auth.SecurityService.log_security_event")
    async def test_login_identifier_not_found(
        self, mock_log_event, mock_rate_limited, mock_db
    ):
        """Test login options when identifier not found."""
        mock_rate_limited.return_value = False
        mock_log_event.return_value = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        request_data = {"identifier": "nonexistent@example.com"}

        test_client = create_test_client_with_db_override(mock_db)
        response = test_client.post("/auth/login/options", json=request_data)

        assert response.status_code == 404
        assert "User not found" in response.json()["detail"]
