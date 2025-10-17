"""
Tests for database models.
"""

from datetime import datetime
import pytest

from app.db.models import User, WebAuthnCredential, Session, AuditLog


class TestModels:
    """Test database models."""

    def test_user_model(self):
        """Test User model creation."""
        user = User(
            first_name="Test",
            last_name="User",
            username="testuser",
            email="test@example.com",
            display_name="Test User",
            is_active=True,
            is_verified=True
        )

        assert user.first_name == "Test"
        assert user.last_name == "User"
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.display_name == "Test User"
        assert user.is_active is True
        assert user.is_verified is True

    def test_user_model_with_middle_name(self):
        """Test User model with middle name."""
        user = User(
            first_name="Test",
            middle_name="Middle",
            last_name="User",
            username="testuser",
            email="test@example.com"
        )

        assert user.middle_name == "Middle"

    def test_webauthn_credential_model(self):
        """Test WebAuthnCredential model creation."""
        credential = WebAuthnCredential(
            user_id="user123",
            credential_id="cred123",
            public_key="pubkey123",
            sign_count=0,
            transports=["usb", "nfc"],
            device_name="Test Device"
        )

        assert credential.user_id == "user123"
        assert credential.credential_id == "cred123"
        assert credential.public_key == "pubkey123"
        assert credential.sign_count == 0
        assert credential.transports == ["usb", "nfc"]
        assert credential.device_name == "Test Device"

    def test_session_model(self):
        """Test Session model creation."""
        session = Session(
            user_id="user123",
            refresh_token="token123",
            expires_at=datetime.now(),
            ip_address="127.0.0.1",
            user_agent="Test Agent"
        )

        assert session.user_id == "user123"
        assert session.refresh_token == "token123"
        assert session.ip_address == "127.0.0.1"
        assert session.user_agent == "Test Agent"

    def test_audit_log_model(self):
        """Test AuditLog model creation."""
        audit_log = AuditLog(
            event_type="TEST_EVENT",
            user_id="user123",
            ip_address="127.0.0.1",
            user_agent="Test Agent",
            resource="test",
            action="test_action",
            status="SUCCESS",
            details={"test": "data"}
        )

        assert audit_log.event_type == "TEST_EVENT"
        assert audit_log.user_id == "user123"
        assert audit_log.ip_address == "127.0.0.1"
        assert audit_log.user_agent == "Test Agent"
        assert audit_log.resource == "test"
        assert audit_log.action == "test_action"
        assert audit_log.status == "SUCCESS"
        assert audit_log.details == {"test": "data"}

    def test_audit_log_model_minimal(self):
        """Test AuditLog model with minimal fields."""
        audit_log = AuditLog(
            event_type="MINIMAL_EVENT",
            resource="test",
            action="test_action",
            status="SUCCESS"
        )

        assert audit_log.event_type == "MINIMAL_EVENT"
        assert audit_log.resource == "test"
        assert audit_log.action == "test_action"
        assert audit_log.status == "SUCCESS"
        assert audit_log.user_id is None
        assert audit_log.ip_address is None
