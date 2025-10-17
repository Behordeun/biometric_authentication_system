import base64
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.db.models import User
from app.services.webauthn_service import WebAuthnService


class TestWebAuthnService:
    @pytest.mark.asyncio
    @patch("app.services.webauthn_service.generate_registration_options")
    async def test_generate_registration_options(self, mock_generate):
        mock_generate.return_value = MagicMock()

        with patch("app.services.webauthn_service.options_to_json") as mock_to_json:
            mock_to_json.return_value = '{"challenge": "test_challenge"}'

            result = await WebAuthnService.generate_registration_options(
                "test@example.com", "testuser"
            )

            assert isinstance(result, dict)
            mock_generate.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.services.webauthn_service.verify_registration_response")
    async def test_verify_registration_success(self, mock_verify):
        mock_verification = MagicMock()
        mock_verification.credential_id = b"test_credential_id"
        mock_verification.credential_public_key = b"test_public_key"
        mock_verification.sign_count = 0
        mock_verification.authenticator_data = b"x" * 40
        mock_verify.return_value = mock_verification

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None  # No existing credential
        mock_db.execute.return_value = mock_result

        user = User(id="user123", email="test@example.com")
        credential = {"id": "test_id", "response": {"transports": ["usb"]}}
        challenge = b"test_challenge"

        with patch(
            "app.services.webauthn_service.WebAuthnService._validate_authenticator_data",
            return_value=True,
        ):
            result = await WebAuthnService.verify_registration(
                credential, challenge, user, mock_db
            )

            assert result == mock_verification
            mock_db.add.assert_called_once()
            mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_verify_registration_credential_exists(self):
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = MagicMock()  # Existing credential
        mock_db.execute.return_value = mock_result

        user = User(id="user123", email="test@example.com")
        credential = {"id": "test_id"}
        challenge = b"test_challenge"

        with patch(
            "app.services.webauthn_service.verify_registration_response"
        ) as mock_verify:
            mock_verification = MagicMock()
            mock_verification.credential_id = b"existing_credential"
            mock_verification.authenticator_data = b"x" * 40
            mock_verify.return_value = mock_verification

            with patch(
                "app.services.webauthn_service.WebAuthnService._validate_authenticator_data",
                return_value=True,
            ):
                with pytest.raises(RuntimeError, match="Credential already exists"):
                    await WebAuthnService.verify_registration(
                        credential, challenge, user, mock_db
                    )

    @pytest.mark.asyncio
    @patch("app.services.webauthn_service.generate_authentication_options")
    async def test_generate_authentication_options_success(self, mock_generate):
        mock_generate.return_value = MagicMock()

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_credentials = [
            MagicMock(
                credential_id=base64.b64encode(b"cred1").decode(), transports=["usb"]
            ),
            MagicMock(
                credential_id=base64.b64encode(b"cred2").decode(), transports=["nfc"]
            ),
        ]
        mock_result.scalars.return_value.all.return_value = mock_credentials
        mock_db.execute.return_value = mock_result

        user = User(id="user123", email="test@example.com")

        with patch("app.services.webauthn_service.options_to_json") as mock_to_json:
            mock_to_json.return_value = '{"challenge": "test_challenge"}'

            result = await WebAuthnService.generate_authentication_options(
                user, mock_db
            )

            assert isinstance(result, dict)
            mock_generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_authentication_options_no_credentials(self):
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []  # No credentials
        mock_db.execute.return_value = mock_result

        user = User(id="user123", email="test@example.com")

        with patch(
            "app.services.webauthn_service.WebAuthnService._check_rate_limiting",
            return_value=False,
        ):
            with pytest.raises(RuntimeError, match="No valid credentials found"):
                await WebAuthnService.generate_authentication_options(user, mock_db)

    @pytest.mark.asyncio
    @patch("app.services.webauthn_service.verify_authentication_response")
    async def test_verify_authentication_success(self, mock_verify):
        mock_verification = MagicMock()
        mock_verification.new_sign_count = 1
        mock_verification.authenticator_data = b"x" * 40
        mock_verify.return_value = mock_verification

        mock_db = AsyncMock()
        mock_result = MagicMock()

        # Mock credentials query
        mock_credential = MagicMock()
        mock_credential.credential_id = base64.b64encode(b"test_credential").decode()
        mock_credential.public_key = base64.b64encode(b"test_public_key").decode()
        mock_credential.sign_count = 0
        mock_result.scalars.return_value.all.return_value = [mock_credential]
        mock_db.execute.return_value = mock_result

        user = User(id="user123", email="test@example.com")
        credential = {
            "rawId": base64.urlsafe_b64encode(b"test_credential").decode(),
            "response": {"authenticatorData": base64.b64encode(b"x" * 40).decode()},
        }
        challenge = b"test_challenge"

        with (
            patch(
                "app.services.webauthn_service.WebAuthnService._check_rate_limiting",
                return_value=False,
            ),
            patch(
                "app.services.webauthn_service.WebAuthnService._validate_authenticator_data",
                return_value=True,
            ),
        ):
            result = await WebAuthnService.verify_authentication(
                credential, challenge, user, mock_db
            )

            assert result == mock_verification
            mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_verify_authentication_sign_count_regression(self):
        mock_db = AsyncMock()
        mock_result = MagicMock()

        mock_credential = MagicMock()
        mock_credential.credential_id = base64.b64encode(b"test_credential").decode()
        mock_credential.public_key = base64.b64encode(b"test_public_key").decode()
        mock_credential.sign_count = 5  # Higher than new count
        mock_result.scalars.return_value.all.return_value = [mock_credential]
        mock_db.execute.return_value = mock_result

        user = User(id="user123", email="test@example.com")
        credential = {
            "rawId": base64.urlsafe_b64encode(b"test_credential").decode(),
            "response": {"authenticatorData": base64.b64encode(b"x" * 40).decode()},
        }
        challenge = b"test_challenge"

        with patch(
            "app.services.webauthn_service.verify_authentication_response"
        ) as mock_verify:
            mock_verification = MagicMock()
            mock_verification.new_sign_count = 3  # Lower than stored count
            mock_verification.authenticator_data = b"x" * 40
            mock_verify.return_value = mock_verification

            with (
                patch(
                    "app.services.webauthn_service.WebAuthnService._check_rate_limiting",
                    return_value=False,
                ),
                patch(
                    "app.services.webauthn_service.WebAuthnService._validate_authenticator_data",
                    return_value=True,
                ),
            ):
                with pytest.raises(
                    RuntimeError, match="Potential replay attack detected"
                ):
                    await WebAuthnService.verify_authentication(
                        credential, challenge, user, mock_db
                    )

    @pytest.mark.asyncio
    async def test_revoke_credential_success(self):
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_credential = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_credential
        mock_db.execute.return_value = mock_result

        user = User(id="user123", email="test@example.com")

        result = await WebAuthnService.revoke_credential("cred123", user, mock_db)

        assert result is True
        mock_db.delete.assert_called_once_with(mock_credential)
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_revoke_credential_not_found(self):
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None  # Credential not found
        mock_db.execute.return_value = mock_result

        user = User(id="user123", email="test@example.com")

        result = await WebAuthnService.revoke_credential("cred123", user, mock_db)

        assert result is False
        mock_db.delete.assert_not_called()

    def test_validate_authenticator_data_valid(self):
        # Create valid authenticator data with UP and UV flags set
        auth_data = bytearray(40)
        auth_data[32] = 0x05  # Set UP (bit 0) and UV (bit 2) flags

        result = WebAuthnService._validate_authenticator_data(bytes(auth_data))
        assert result is True

    def test_validate_authenticator_data_invalid(self):
        # Test with too short data
        short_data = b"short"
        result = WebAuthnService._validate_authenticator_data(short_data)
        assert result is False

        # Test with missing flags
        auth_data = bytearray(40)
        auth_data[32] = 0x00  # No flags set
        result = WebAuthnService._validate_authenticator_data(bytes(auth_data))
        assert result is False

    @pytest.mark.asyncio
    async def test_check_rate_limiting(self):
        mock_db = AsyncMock()

        # Test rate limiting (simplified - always returns False for now)
        result = await WebAuthnService._check_rate_limiting("user123", mock_db)
        assert result is False

    def test_generate_secure_challenge(self):
        challenge = WebAuthnService._generate_secure_challenge()
        assert isinstance(challenge, bytes)
        assert len(challenge) == 64  # 512 bits

        # Each challenge should be unique
        challenge2 = WebAuthnService._generate_secure_challenge()
        assert challenge != challenge2
