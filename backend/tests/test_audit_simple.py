"""
Simple tests for audit functionality.
"""

from unittest.mock import AsyncMock

import pytest

from app.core.audit import AuditLogger, log_login_attempt, log_registration


class TestAuditLogger:
    """Test AuditLogger functionality."""

    @pytest.mark.asyncio
    async def test_audit_logger_log_event(self):
        """Test AuditLogger.log_event method."""
        mock_db = AsyncMock()

        await AuditLogger.log_event(
            db=mock_db,
            event_type="test_event",
            user_id=123,
            ip_address="192.168.1.1",
            action="login",
            status="success",
        )

        # Should add audit entry to database
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_audit_logger_with_details(self):
        """Test AuditLogger with additional details."""
        mock_db = AsyncMock()

        details = {"method": "biometric", "device": "mobile"}

        await AuditLogger.log_event(
            db=mock_db,
            event_type="authentication",
            user_id=456,
            ip_address="10.0.0.1",
            user_agent="Mozilla/5.0",
            resource="user_account",
            action="login",
            status="success",
            details=details,
        )

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_audit_logger_database_error(self):
        """Test AuditLogger handling database errors."""
        mock_db = AsyncMock()
        mock_db.commit.side_effect = Exception("Database error")

        with pytest.raises(Exception):
            await AuditLogger.log_event(
                db=mock_db,
                event_type="test_event",
                action="test_action",
                status="success",
            )

        mock_db.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_log_login_attempt_success(self):
        """Test log_login_attempt function for successful login."""
        mock_db = AsyncMock()

        await log_login_attempt(
            db=mock_db,
            username="testuser",
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
            success=True,
            user_id=123,
        )

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_log_login_attempt_failure(self):
        """Test log_login_attempt function for failed login."""
        mock_db = AsyncMock()

        await log_login_attempt(
            db=mock_db,
            username="testuser",
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
            success=False,
        )

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_log_registration(self):
        """Test log_registration function."""
        mock_db = AsyncMock()

        await log_registration(
            db=mock_db,
            user_id=123,
            username="newuser",
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
        )

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_audit_logger_minimal_params(self):
        """Test AuditLogger with minimal required parameters."""
        mock_db = AsyncMock()

        await AuditLogger.log_event(db=mock_db, event_type="minimal_test")

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_audit_logger_all_params(self):
        """Test AuditLogger with all parameters."""
        mock_db = AsyncMock()

        await AuditLogger.log_event(
            db=mock_db,
            event_type="comprehensive_test",
            user_id=789,
            ip_address="172.16.0.1",
            user_agent="TestAgent/1.0",
            resource="test_resource",
            action="test_action",
            status="completed",
            details={"key": "value", "count": 42},
        )

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_audit_functions_error_handling(self):
        """Test that audit convenience functions handle errors gracefully."""
        mock_db = AsyncMock()
        mock_db.commit.side_effect = Exception("Database connection lost")

        # These functions should not raise exceptions, just log errors
        await log_login_attempt(
            db=mock_db,
            username="testuser",
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
            success=True,
        )

        await log_registration(
            db=mock_db,
            user_id=123,
            username="testuser",
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
        )

        # Functions should have attempted to add to database
        assert mock_db.add.call_count >= 2
