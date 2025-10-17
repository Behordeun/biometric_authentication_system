from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.core.auth import (
    create_access_token,
    create_id_token,
    create_refresh_token,
    generate_client_credentials,
    get_current_user,
)
from app.db.models import User
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from jose import jwt as jose_jwt


class TestCoreAuth:
    def test_create_access_token(self):
        data = {"sub": "user123", "email": "test@example.com"}

        # Mock settings during token creation
        with patch("app.core.auth.settings") as mock_settings:
            mock_settings.SECRET_KEY = "test_secret"  # pragma: allowlist secret
            mock_settings.ALGORITHM = "HS256"
            mock_settings.ACCESS_TOKEN_EXPIRE_MINUTES = 30

            token = create_access_token(data)

            assert isinstance(token, str)

            # Decode and verify token structure
            decoded = jose_jwt.decode(
                token, "test_secret", algorithms=["HS256"]
            )  # pragma: allowlist secret
            assert decoded["sub"] == "user123"
            assert decoded["type"] == "access"
            assert "exp" in decoded

    def test_create_refresh_token(self):
        data = {"sub": "user123"}

        # Mock settings during token creation
        with patch("app.core.auth.settings") as mock_settings:
            mock_settings.SECRET_KEY = "test_secret"  # pragma: allowlist secret
            mock_settings.ALGORITHM = "HS256"
            mock_settings.REFRESH_TOKEN_EXPIRE_DAYS = 7

            token = create_refresh_token(data)

            assert isinstance(token, str)

            # Decode and verify token structure
            decoded = jose_jwt.decode(
                token, "test_secret", algorithms=["HS256"]
            )  # pragma: allowlist secret
            assert decoded["sub"] == "user123"
            assert decoded["type"] == "refresh"
            assert "exp" in decoded

    def test_create_id_token(self):
        user = User(
            id="user123",
            email="test@example.com",
            username="testuser",
            display_name="Test User",
            is_verified=True,
        )

        with patch("app.core.auth.settings") as mock_settings:
            mock_settings.SECRET_KEY = "test_secret"  # pragma: allowlist secret
            mock_settings.ALGORITHM = "HS256"

            token = create_id_token(user)
            assert isinstance(token, str)

            decoded = jose_jwt.decode(
                token, "test_secret", algorithms=["HS256"]
            )  # pragma: allowlist secret
            assert decoded["sub"] == "user123"
            assert decoded["email"] == "test@example.com"
            assert decoded["preferred_username"] == "testuser"
            assert decoded["email_verified"] is True

    @pytest.mark.asyncio
    async def test_get_current_user_success(self):
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_user = User(id="user123", email="test@example.com")
        mock_result.scalar.return_value = mock_user
        mock_db.execute.return_value = mock_result

        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials="valid_token"
        )

        with patch("app.core.auth.jwt.decode") as mock_decode:
            mock_decode.return_value = {
                "sub": "user123",
                "type": "access",
                "exp": (datetime.now(timezone.utc) + timedelta(minutes=30)).timestamp(),
            }

            user = await get_current_user(credentials, mock_db)
            assert user == mock_user

    @pytest.mark.asyncio
    async def test_get_current_user_invalid_token_type(self):
        mock_db = AsyncMock()
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials="invalid_token"
        )

        with patch("app.core.auth.jwt.decode") as mock_decode:
            mock_decode.return_value = {
                "sub": "user123",
                "type": "refresh",  # Wrong token type
                "exp": (datetime.now(timezone.utc) + timedelta(minutes=30)).timestamp(),
            }

            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(credentials, mock_db)

            assert exc_info.value.status_code == 401
            assert "Invalid token type" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_current_user_missing_subject(self):
        mock_db = AsyncMock()
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials="invalid_token"
        )

        with patch("app.core.auth.jwt.decode") as mock_decode:
            mock_decode.return_value = {
                "type": "access",
                "exp": (datetime.now(timezone.utc) + timedelta(minutes=30)).timestamp(),
                # Missing "sub"
            }

            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(credentials, mock_db)

            assert exc_info.value.status_code == 401
            assert "Invalid token" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_current_user_jwt_error(self):
        mock_db = AsyncMock()
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials="malformed_token"
        )

        with patch("app.core.auth.jwt.decode") as mock_decode:
            from jose import JWTError

            mock_decode.side_effect = JWTError("Invalid token")

            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(credentials, mock_db)

            assert exc_info.value.status_code == 401
            assert "Invalid token" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_current_user_not_found(self):
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar.return_value = None  # User not found
        mock_db.execute.return_value = mock_result

        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials="valid_token"
        )

        with patch("app.core.auth.jwt.decode") as mock_decode:
            mock_decode.return_value = {
                "sub": "nonexistent_user",
                "type": "access",
                "exp": (datetime.now(timezone.utc) + timedelta(minutes=30)).timestamp(),
            }

            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(credentials, mock_db)

            assert exc_info.value.status_code == 401
            assert "User not found" in str(exc_info.value.detail)

    def test_generate_client_credentials(self):
        client_id, client_secret = generate_client_credentials()

        assert isinstance(client_id, str)
        assert isinstance(client_secret, str)
        assert len(client_id) > 20  # URL-safe base64 should be reasonably long
        assert len(client_secret) > 30

        # Each call should generate unique credentials
        client_id2, client_secret2 = generate_client_credentials()
        assert client_id != client_id2
        assert client_secret != client_secret2
