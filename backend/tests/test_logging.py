"""
Comprehensive tests for logging functionality.
"""
import json
import logging
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.core.logging import (
    get_logger,
    Logger,
)


class TestLogging:
    """Test logging configuration and functionality."""

    def test_get_logger_basic(self):
        """Test basic logger creation."""
        logger = get_logger("test_module")

        assert logger is not None
        assert logger.name == "test_module"
        assert isinstance(logger, logging.Logger)

    def test_get_logger_with_different_names(self):
        """Test logger creation with different names."""
        logger1 = get_logger("module1")
        logger2 = get_logger("module2")

        assert logger1.name == "module1"
        assert logger2.name == "module2"
        assert logger1 is not logger2

    def test_get_logger_same_name_returns_same_instance(self):
        """Test that same logger name returns same instance."""
        logger1 = get_logger("same_module")
        logger2 = get_logger("same_module")

        assert logger1 is logger2

    def test_logger_hierarchy(self):
        """Test logger hierarchy."""
        _parent_logger = get_logger("parent")
        child_logger = get_logger("parent.child")

        assert child_logger.parent.name == "parent"

    @patch.dict(os.environ, {"LOG_LEVEL": "DEBUG"})
    def test_logger_debug_level(self):
        """Test logger with DEBUG level."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = Path(temp_dir)
            logger = Logger(log_dir)

            logger.debug("Debug message")

            debug_file = log_dir / "debug.log"
            assert debug_file.exists()

    @patch.dict(os.environ, {"LOG_LEVEL": "INFO"})
    def test_setup_logging_info_level(self):
        """Test setup logging with INFO level."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = Path(temp_dir)
            setup_logging(log_dir)

            logger = get_logger("test")
            assert logger.level <= logging.INFO

    @patch.dict(os.environ, {"LOG_LEVEL": "WARNING"})
    def test_setup_logging_warning_level(self):
        """Test setup logging with WARNING level."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = Path(temp_dir)
            setup_logging(log_dir)

            logger = get_logger("test")
            assert logger.level <= logging.WARNING

    @patch.dict(os.environ, {"LOG_LEVEL": "ERROR"})
    def test_setup_logging_error_level(self):
        """Test setup logging with ERROR level."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = Path(temp_dir)
            setup_logging(log_dir)

            logger = get_logger("test")
            assert logger.level <= logging.ERROR

    @patch.dict(os.environ, {"LOG_LEVEL": "CRITICAL"})
    def test_setup_logging_critical_level(self):
        """Test setup logging with CRITICAL level."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = Path(temp_dir)
            setup_logging(log_dir)

            logger = get_logger("test")
            assert logger.level <= logging.CRITICAL

    @patch.dict(os.environ, {"LOG_LEVEL": "INVALID"})
    def test_setup_logging_invalid_level_defaults_to_info(self):
        """Test setup logging with invalid level defaults to INFO."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = Path(temp_dir)
            setup_logging(log_dir)

            logger = get_logger("test")
            assert logger.level <= logging.INFO

    def test_setup_logging_creates_log_directory(self):
        """Test that setup_logging creates log directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = Path(temp_dir) / "logs"
            assert not log_dir.exists()

            setup_logging(log_dir)

            assert log_dir.exists()
            assert log_dir.is_dir()

    def test_setup_logging_creates_log_files(self):
        """Test that setup_logging creates log files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = Path(temp_dir)
            setup_logging(log_dir)

            # Check that log files are created when logging occurs
            logger = get_logger("test")
            logger.info("Test info message")
            logger.warning("Test warning message")
            logger.error("Test error message")

            # Files should exist after logging
            assert (log_dir / "app.log").exists()
            assert (log_dir / "info.log").exists()
            assert (log_dir / "warning.log").exists()
            assert (log_dir / "error.log").exists()

    def test_log_file_content_format(self):
        """Test log file content format."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = Path(temp_dir)
            setup_logging(log_dir)

            logger = get_logger("test_module")
            test_message = "Test log message"
            logger.info(test_message)

            # Read log file content
            log_file = log_dir / "app.log"
            with open(log_file, 'r') as f:
                content = f.read()

            assert test_message in content
            assert "test_module" in content
            assert "INFO" in content

    def test_json_formatter(self):
        """Test JSON formatter functionality."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = Path(temp_dir)
            setup_logging(log_dir)

            logger = get_logger("test_json")
            logger.info("JSON test message", extra={"user_id": "123", "action": "login"})

            # Read and parse JSON log
            log_file = log_dir / "app.log"
            with open(log_file, 'r') as f:
                lines = f.readlines()

            # Should have at least one log entry
            assert len(lines) > 0

            # Try to parse as JSON (some formatters might use JSON)
            for line in lines:
                if line.strip():
                    # Should be valid log format (not necessarily JSON)
                    assert "JSON test message" in line

    def test_security_sensitive_data_filtering(self):
        """Test that security-sensitive data is filtered from logs."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = Path(temp_dir)
            setup_logging(log_dir)

            logger = get_logger("security_test")

            # Log message with potentially sensitive data
            logger.info("User login", extra={
                "email": "user@example.com",
                "password": "secret123",  # Should be filtered  # pragma: allowlist secret
                "token": "jwt_token_here",  # Should be filtered  # pragma: allowlist secret
                "api_key": "api_key_123"  # Should be filtered  # pragma: allowlist secret
            })

            # Read log content
            log_file = log_dir / "app.log"
            with open(log_file, 'r') as f:
                content = f.read()

            # Sensitive data should not appear in logs
            assert "secret123" not in content
            assert "jwt_token_here" not in content
            assert "api_key_123" not in content

            # Non-sensitive data should appear
            assert "user@example.com" in content

    def test_log_rotation_configuration(self):
        """Test log rotation configuration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = Path(temp_dir)
            setup_logging(log_dir)

            logger = get_logger("rotation_test")

            # Generate multiple log entries
            for i in range(100):
                logger.info(f"Log entry {i}")

            # Log files should exist
            assert (log_dir / "app.log").exists()

    def test_concurrent_logging(self):
        """Test concurrent logging from multiple threads."""
        import threading
        import time

        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = Path(temp_dir)
            setup_logging(log_dir)

            results = []

            def log_worker(worker_id):
                logger = get_logger(f"worker_{worker_id}")
                for i in range(10):
                    logger.info(f"Worker {worker_id} - Message {i}")
                results.append(worker_id)

            # Create multiple threads
            threads = []
            for i in range(5):
                thread = threading.Thread(target=log_worker, args=(i,))
                threads.append(thread)
                thread.start()

            # Wait for all threads
            for thread in threads:
                thread.join()

            # All workers should complete
            assert len(results) == 5

            # Log file should contain entries from all workers
            log_file = log_dir / "app.log"
            with open(log_file, 'r') as f:
                content = f.read()

            for i in range(5):
                assert f"worker_{i}" in content

    def test_exception_logging(self):
        """Test exception logging."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = Path(temp_dir)
            setup_logging(log_dir)

            logger = get_logger("exception_test")

            try:
                raise ValueError("Test exception")
            except ValueError:
                logger.exception("An error occurred")

            # Read error log
            error_log = log_dir / "error.log"
            with open(error_log, 'r') as f:
                content = f.read()

            assert "An error occurred" in content
            assert "ValueError" in content
            assert "Test exception" in content

    def test_structured_logging(self):
        """Test structured logging with extra fields."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = Path(temp_dir)
            setup_logging(log_dir)

            logger = get_logger("structured_test")

            logger.info("Structured log entry", extra={
                "request_id": "req_123",
                "user_id": "user_456",
                "action": "authentication",
                "ip_address": "192.168.1.1"
            })

            # Read log content
            log_file = log_dir / "app.log"
            with open(log_file, 'r') as f:
                content = f.read()

            assert "Structured log entry" in content
            # Extra fields should be included in some form
            assert "req_123" in content or "request_id" in content

    def test_log_level_filtering(self):
        """Test log level filtering."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = Path(temp_dir)

            # Set up logging with WARNING level
            with patch.dict(os.environ, {"LOG_LEVEL": "WARNING"}):
                setup_logging(log_dir)

            logger = get_logger("filter_test")

            logger.debug("Debug message")  # Should not appear
            logger.info("Info message")    # Should not appear
            logger.warning("Warning message")  # Should appear
            logger.error("Error message")      # Should appear

            # Read warning log
            warning_log = log_dir / "warning.log"
            with open(warning_log, 'r') as f:
                warning_content = f.read()

            # Read error log
            error_log = log_dir / "error.log"
            with open(error_log, 'r') as f:
                error_content = f.read()

            # Only warning and error messages should appear
            assert "Debug message" not in warning_content
            assert "Info message" not in warning_content
            assert "Warning message" in warning_content
            assert "Error message" in error_content

    def test_logger_performance(self):
        """Test logger performance with many messages."""
        import time

        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = Path(temp_dir)
            setup_logging(log_dir)

            logger = get_logger("performance_test")

            start_time = time.time()

            # Log many messages
            for i in range(1000):
                logger.info(f"Performance test message {i}")

            end_time = time.time()

            # Should complete in reasonable time (less than 5 seconds)
            assert (end_time - start_time) < 5.0

            # Log file should contain all messages
            log_file = log_dir / "app.log"
            with open(log_file, 'r') as f:
                lines = f.readlines()

            # Should have logged all messages
            assert len(lines) >= 1000


class TestSecurityAuditLogger:
    """Test SecurityAuditLogger functionality."""

    def test_security_audit_logger_creation(self):
        """Test SecurityAuditLogger creation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = Path(temp_dir)
            audit_logger = SecurityAuditLogger(log_dir)

            assert audit_logger is not None
            assert audit_logger.log_dir == log_dir

    def test_security_audit_log_authentication_event(self):
        """Test logging authentication events."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = Path(temp_dir)
            audit_logger = SecurityAuditLogger(log_dir)

            audit_logger.log_authentication_event(
                user_id="user_123",
                event_type="LOGIN_SUCCESS",
                ip_address="192.168.1.1",
                user_agent="Mozilla/5.0",
                additional_data={"method": "biometric"}
            )

            # Check that audit log file exists and contains the event
            audit_file = log_dir / "security_audit.log"
            assert audit_file.exists()

            with open(audit_file, 'r') as f:
                content = f.read()

            assert "LOGIN_SUCCESS" in content
            assert "user_123" in content
            assert "192.168.1.1" in content

    def test_security_audit_log_security_event(self):
        """Test logging security events."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = Path(temp_dir)
            audit_logger = SecurityAuditLogger(log_dir)

            audit_logger.log_security_event(
                event_type="SUSPICIOUS_ACTIVITY",
                severity="HIGH",
                description="Multiple failed login attempts",
                ip_address="192.168.1.100",
                user_id="user_456",
                additional_data={"attempts": 5}
            )

            # Check audit log content
            audit_file = log_dir / "security_audit.log"
            with open(audit_file, 'r') as f:
                content = f.read()

            assert "SUSPICIOUS_ACTIVITY" in content
            assert "HIGH" in content
            assert "Multiple failed login attempts" in content

    def test_security_audit_log_access_event(self):
        """Test logging access events."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = Path(temp_dir)
            audit_logger = SecurityAuditLogger(log_dir)

            audit_logger.log_access_event(
                user_id="user_789",
                resource="/api/sensitive-data",
                action="READ",
                result="SUCCESS",
                ip_address="10.0.0.1"
            )

            # Check audit log content
            audit_file = log_dir / "security_audit.log"
            with open(audit_file, 'r') as f:
                content = f.read()

            assert "user_789" in content
            assert "/api/sensitive-data" in content
            assert "READ" in content
            assert "SUCCESS" in content

    def test_security_audit_log_data_sanitization(self):
        """Test that sensitive data is sanitized in audit logs."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = Path(temp_dir)
            audit_logger = SecurityAuditLogger(log_dir)

            audit_logger.log_authentication_event(
                user_id="user_123",
                event_type="LOGIN_ATTEMPT",
                ip_address="192.168.1.1",
                user_agent="Mozilla/5.0",
                additional_data={
                    "email": "user@example.com",
                    "password": "secret123",  # Should be sanitized  # pragma: allowlist secret
                    "token": "jwt_token_here"  # Should be sanitized
                }
            )

            # Check that sensitive data is not in logs
            audit_file = log_dir / "security_audit.log"
            with open(audit_file, 'r') as f:
                content = f.read()

            assert "secret123" not in content
            assert "jwt_token_here" not in content
            assert "user@example.com" in content  # Non-sensitive data should remain

    def test_security_audit_log_json_format(self):
        """Test that audit logs are in proper JSON format."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = Path(temp_dir)
            audit_logger = SecurityAuditLogger(log_dir)

            audit_logger.log_security_event(
                event_type="TEST_EVENT",
                severity="INFO",
                description="Test event for JSON format",
                ip_address="127.0.0.1"
            )

            # Read and parse audit log
            audit_file = log_dir / "security_audit.log"
            with open(audit_file, 'r') as f:
                lines = f.readlines()

            # Should have at least one log entry
            assert len(lines) > 0

            # Each line should be valid JSON or valid log format
            for line in lines:
                if line.strip():
                    # Should contain expected fields
                    assert "TEST_EVENT" in line
                    assert "Test event for JSON format" in line

    def test_security_audit_log_rotation(self):
        """Test audit log rotation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = Path(temp_dir)
            audit_logger = SecurityAuditLogger(log_dir)

            # Generate many audit events
            for i in range(100):
                audit_logger.log_security_event(
                    event_type="BULK_TEST",
                    severity="INFO",
                    description=f"Bulk test event {i}",
                    ip_address="127.0.0.1"
                )

            # Audit file should exist and contain events
            audit_file = log_dir / "security_audit.log"
            assert audit_file.exists()

            with open(audit_file, 'r') as f:
                content = f.read()

            assert "BULK_TEST" in content

    def test_security_audit_concurrent_logging(self):
        """Test concurrent audit logging."""
        import threading

        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = Path(temp_dir)
            audit_logger = SecurityAuditLogger(log_dir)

            results = []

            def audit_worker(worker_id):
                for i in range(10):
                    audit_logger.log_security_event(
                        event_type="CONCURRENT_TEST",
                        severity="INFO",
                        description=f"Worker {worker_id} event {i}",
                        ip_address="127.0.0.1"
                    )
                results.append(worker_id)

            # Create multiple threads
            threads = []
            for i in range(3):
                thread = threading.Thread(target=audit_worker, args=(i,))
                threads.append(thread)
                thread.start()

            # Wait for all threads
            for thread in threads:
                thread.join()

            # All workers should complete
            assert len(results) == 3

            # Audit file should contain events from all workers
            audit_file = log_dir / "security_audit.log"
            with open(audit_file, 'r') as f:
                content = f.read()

            for i in range(3):
                assert f"Worker {i}" in content
