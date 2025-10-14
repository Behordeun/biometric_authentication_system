from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.security_service import BiometricSecurityValidator, SecurityService


class TestSecurityService:
    def test_generate_device_fingerprint(self):
        headers = {
            "user-agent": "Mozilla/5.0",
            "accept-language": "en-US,en;q=0.9",
            "accept-encoding": "gzip, deflate",
        }
        ip_address = "192.168.1.1"

        fingerprint = SecurityService.generate_device_fingerprint(headers, ip_address)
        assert isinstance(fingerprint, str)
        assert len(fingerprint) == 16

        # Same input should produce same fingerprint
        fingerprint2 = SecurityService.generate_device_fingerprint(headers, ip_address)
        assert fingerprint == fingerprint2

    def test_is_rate_limited(self):
        # Clear cache for clean test
        SecurityService._rate_limit_cache.clear()

        identifier = "test_user"
        action = "authentication"

        # First few attempts should not be rate limited (limit is 5)
        for i in range(5):
            result = SecurityService.is_rate_limited(identifier, action)
            if i < 5:
                assert not result

        # 6th attempt should be rate limited
        result = SecurityService.is_rate_limited(identifier, action)
        assert result

    @pytest.mark.asyncio
    async def test_detect_suspicious_activity(self):
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        warnings = await SecurityService.detect_suspicious_activity(
            "user123", "192.168.1.1", "Mozilla/5.0", mock_db
        )
        assert isinstance(warnings, list)

    def test_validate_request_integrity(self):
        request_data = {"email": "test@example.com"}
        timestamp = datetime.now().isoformat()

        # Test with invalid signature
        result = SecurityService.validate_request_integrity(
            request_data, "invalid_signature", timestamp
        )
        assert not result

        # Test with old timestamp
        old_timestamp = (datetime.now() - timedelta(minutes=10)).isoformat()
        result = SecurityService.validate_request_integrity(
            request_data, "signature", old_timestamp
        )
        assert not result

    @pytest.mark.asyncio
    async def test_check_credential_reuse(self):
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await SecurityService.check_credential_reuse(
            "credential123", "user456", mock_db
        )
        assert not result

    def test_generate_secure_session_token(self):
        token = SecurityService.generate_secure_session_token()
        assert isinstance(token, str)
        assert len(token) > 50  # URL-safe base64 should be longer

        # Each token should be unique
        token2 = SecurityService.generate_secure_session_token()
        assert token != token2

    def test_hash_sensitive_data(self):
        data = "sensitive_password"
        hashed, salt = SecurityService.hash_sensitive_data(data)

        assert isinstance(hashed, str)
        assert isinstance(salt, str)
        assert len(hashed) > 50
        assert len(salt) == 64  # 32 bytes hex = 64 chars

        # Same data with same salt should produce same hash
        hashed2, _ = SecurityService.hash_sensitive_data(data, salt)
        assert hashed == hashed2

    @pytest.mark.asyncio
    async def test_log_security_event(self):
        mock_db = AsyncMock()

        await SecurityService.log_security_event(
            "TEST_EVENT",
            "user123",
            "192.168.1.1",
            "Mozilla/5.0",
            {"test": "data"},
            mock_db,
            "INFO",
        )

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_account_lockout(self):
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar.return_value = 5  # Less than lockout threshold
        mock_db.execute.return_value = mock_result

        result = await SecurityService.check_account_lockout("user123", mock_db)
        assert not result

        # Test with high failure count
        mock_result.scalar.return_value = 15  # Above threshold
        result = await SecurityService.check_account_lockout("user123", mock_db)
        assert result

    def test_validate_biometric_quality(self):
        # Valid biometric data
        valid_data = {
            "authenticatorData": "x" * 40,  # Sufficient length
            "signature": "y" * 70,
            "userHandle": "user123",
        }
        assert SecurityService.validate_biometric_quality(valid_data)

        # Invalid biometric data - missing fields
        invalid_data = {"authenticatorData": "short"}
        assert not SecurityService.validate_biometric_quality(invalid_data)

    @pytest.mark.asyncio
    async def test_detect_anomalous_behavior(self):
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        current_request = {"ip_address": "192.168.1.1"}
        anomalies = await SecurityService.detect_anomalous_behavior(
            "user123", current_request, mock_db
        )
        assert isinstance(anomalies, list)


class TestBiometricSecurityValidator:
    def test_validate_liveness(self):
        # Valid authenticator data with UV flag set
        auth_data = bytearray(40)
        auth_data[32] = 0x05  # Set UP (bit 0) and UV (bit 2) flags

        result = BiometricSecurityValidator.validate_liveness(bytes(auth_data))
        assert result

        # Invalid authenticator data without UV flag
        auth_data[32] = 0x01  # Only UP flag
        result = BiometricSecurityValidator.validate_liveness(bytes(auth_data))
        assert not result

        # Too short authenticator data
        short_data = b"short"
        result = BiometricSecurityValidator.validate_liveness(short_data)
        assert not result

    def test_detect_presentation_attack(self):
        # Valid credential data
        valid_credential = {
            "response": {"authenticatorData": "x" * 40, "signature": "y" * 70}
        }
        result = BiometricSecurityValidator.detect_presentation_attack(valid_credential)
        assert not result  # Should not detect attack

        # Suspicious credential data
        suspicious_credential = {
            "response": {
                "authenticatorData": "short",  # Too short
                "signature": "short",  # Too short
            }
        }
        result = BiometricSecurityValidator.detect_presentation_attack(
            suspicious_credential
        )
        assert result  # Should detect attack

    @pytest.mark.asyncio
    async def test_validate_device_integrity(self):
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = MagicMock()  # Known device
        mock_db.execute.return_value = mock_result

        result = await BiometricSecurityValidator.validate_device_integrity(
            "fingerprint123", "user456", mock_db
        )
        assert result  # Known device should be valid

        # Test unknown device
        mock_result.scalar_one_or_none.return_value = None
        result = await BiometricSecurityValidator.validate_device_integrity(
            "new_fingerprint", "user456", mock_db
        )
        assert not result  # New device should require additional validation
