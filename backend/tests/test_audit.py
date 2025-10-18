import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime

from app.core.audit import AuditLogger


class TestAuditLogger:

    @pytest.mark.asyncio
    async def test_log_event_success(self):
        mock_db = AsyncMock()
        logger = AuditLogger(mock_db)

        await logger.log_event(
            event_type="USER_LOGIN",
            user_id="user123",
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
            resource="auth",
            action="login",
            status="SUCCESS",
            details={"method": "webauthn"}
        )

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_log_event_with_exception(self):
        mock_db = AsyncMock()
        mock_db.commit.side_effect = Exception("Database error")

        logger = AuditLogger(mock_db)

        # Should not raise exception, just log error
        await logger.log_event(
            event_type="TEST_EVENT",
            user_id="user123",
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
            resource="test",
            action="test",
            status="SUCCESS"
        )

        mock_db.add.assert_called_once()
        mock_db.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_log_authentication_success(self):
        mock_db = AsyncMock()
        logger = AuditLogger(mock_db)

        await logger.log_authentication(
            user_id="user123",
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
            success=True,
            method="webauthn"
        )

        mock_db.add.assert_called_once()
        # Verify the audit log entry
        call_args = mock_db.add.call_args[0][0]
        assert call_args.event_type == "AUTHENTICATION"
        assert call_args.status == "SUCCESS"
        assert call_args.details["method"] == "webauthn"

    @pytest.mark.asyncio
    async def test_log_authentication_failure(self):
        mock_db = AsyncMock()
        logger = AuditLogger(mock_db)

        await logger.log_authentication(
            user_id="user123",
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
            success=False,
            method="webauthn",
            failure_reason="Invalid credential"
        )

        mock_db.add.assert_called_once()
        call_args = mock_db.add.call_args[0][0]
        assert call_args.event_type == "AUTHENTICATION"
        assert call_args.status == "FAILED"
        assert call_args.details["failure_reason"] == "Invalid credential"

    @pytest.mark.asyncio
    async def test_log_registration(self):
        mock_db = AsyncMock()
        logger = AuditLogger(mock_db)

        await logger.log_registration(
            user_id="user123",
            email="test@example.com",
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
            success=True
        )

        mock_db.add.assert_called_once()
        call_args = mock_db.add.call_args[0][0]
        assert call_args.event_type == "REGISTRATION"
        assert call_args.status == "SUCCESS"
        assert call_args.details["email"] == "test@example.com"

    @pytest.mark.asyncio
    async def test_log_security_event(self):
        mock_db = AsyncMock()
        logger = AuditLogger(mock_db)

        await logger.log_security_event(
            event_type="SUSPICIOUS_ACTIVITY",
            user_id="user123",
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
            severity="HIGH",
            details={"reason": "Multiple failed attempts"}
        )

        mock_db.add.assert_called_once()
        call_args = mock_db.add.call_args[0][0]
        assert call_args.event_type == "SECURITY_SUSPICIOUS_ACTIVITY"
        assert call_args.status == "HIGH"
        assert call_args.details["reason"] == "Multiple failed attempts"

    @pytest.mark.asyncio
    async def test_get_user_activity(self):
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_logs = [
            MagicMock(event_type="LOGIN", timestamp=datetime.now()),
            MagicMock(event_type="LOGOUT", timestamp=datetime.now())
        ]
        mock_result.scalars.return_value.all.return_value = mock_logs
        mock_db.execute.return_value = mock_result

        logger = AuditLogger(mock_db)

        logs = await logger.get_user_activity("user123", limit=10)

        assert len(logs) == 2
        assert logs[0].event_type == "LOGIN"
        assert logs[1].event_type == "LOGOUT"

    @pytest.mark.asyncio
    async def test_get_security_events(self):
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_events = [
            MagicMock(event_type="SECURITY_BREACH", severity="HIGH"),
            MagicMock(event_type="SECURITY_WARNING", severity="MEDIUM")
        ]
        mock_result.scalars.return_value.all.return_value = mock_events
        mock_db.execute.return_value = mock_result

        logger = AuditLogger(mock_db)

        events = await logger.get_security_events(severity="HIGH", limit=5)

        assert len(events) == 2
        mock_db.execute.assert_called_once()


class TestSecurityAuditLogger:

    @pytest.mark.asyncio
    async def test_log_failed_authentication_attempt(self):
        mock_db = AsyncMock()
        logger = SecurityAuditLogger(mock_db)

        await logger.log_failed_authentication_attempt(
            user_id="user123",
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
            reason="Invalid credential",
            attempt_count=3
        )

        mock_db.add.assert_called_once()
        call_args = mock_db.add.call_args[0][0]
        assert call_args.event_type == "SECURITY_FAILED_AUTH"
        assert call_args.details["attempt_count"] == 3

    @pytest.mark.asyncio
    async def test_log_suspicious_activity(self):
        mock_db = AsyncMock()
        logger = SecurityAuditLogger(mock_db)

        await logger.log_suspicious_activity(
            user_id="user123",
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
            activity_type="RAPID_REQUESTS",
            details={"request_count": 50, "time_window": "1 minute"}
        )

        mock_db.add.assert_called_once()
        call_args = mock_db.add.call_args[0][0]
        assert call_args.event_type == "SECURITY_SUSPICIOUS_ACTIVITY"
        assert call_args.details["activity_type"] == "RAPID_REQUESTS"

    @pytest.mark.asyncio
    async def test_log_account_lockout(self):
        mock_db = AsyncMock()
        logger = SecurityAuditLogger(mock_db)

        await logger.log_account_lockout(
            user_id="user123",
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
            reason="Too many failed attempts",
            lockout_duration=900  # 15 minutes
        )

        mock_db.add.assert_called_once()
        call_args = mock_db.add.call_args[0][0]
        assert call_args.event_type == "SECURITY_ACCOUNT_LOCKOUT"
        assert call_args.details["lockout_duration"] == 900

    @pytest.mark.asyncio
    async def test_log_security_breach(self):
        mock_db = AsyncMock()
        logger = SecurityAuditLogger(mock_db)

        await logger.log_security_breach(
            breach_type="CREDENTIAL_STUFFING",
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
            affected_users=["user1", "user2"],
            details={"attack_vector": "Automated login attempts"}
        )

        mock_db.add.assert_called_once()
        call_args = mock_db.add.call_args[0][0]
        assert call_args.event_type == "SECURITY_BREACH"
        assert call_args.details["breach_type"] == "CREDENTIAL_STUFFING"
        assert len(call_args.details["affected_users"]) == 2

    @pytest.mark.asyncio
    async def test_get_failed_attempts_count(self):
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar.return_value = 5
        mock_db.execute.return_value = mock_result

        logger = SecurityAuditLogger(mock_db)

        count = await logger.get_failed_attempts_count("user123", hours=1)

        assert count == 5
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_security_summary(self):
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_summary = [
            MagicMock(event_type="SECURITY_FAILED_AUTH", count=10),
            MagicMock(event_type="SECURITY_SUSPICIOUS_ACTIVITY", count=5)
        ]
        mock_result.all.return_value = mock_summary
        mock_db.execute.return_value = mock_result

        logger = SecurityAuditLogger(mock_db)

        summary = await logger.get_security_summary(hours=24)

        assert len(summary) == 2
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_old_logs(self):
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.rowcount = 100  # 100 rows deleted
        mock_db.execute.return_value = mock_result

        logger = SecurityAuditLogger(mock_db)

        deleted_count = await logger.cleanup_old_logs(days=90)

        assert deleted_count == 100
        mock_db.execute.assert_called_once()
        mock_db.commit.assert_called_once()
