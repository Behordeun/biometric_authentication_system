"""
Simple tests for logging functionality.
"""
import tempfile
from pathlib import Path

from app.core.logging import Logger, LogLevel, get_logger


class TestLogging:
    """Test logging configuration and functionality."""

    def test_get_logger_basic(self):
        """Test basic logger creation."""
        logger = get_logger("test_module")

        assert logger is not None
        assert isinstance(logger, Logger)

    def test_get_logger_same_instance(self):
        """Test that get_logger returns same instance."""
        logger1 = get_logger("test")
        logger2 = get_logger("test")

        assert logger1 is logger2

    def test_logger_creation(self):
        """Test Logger creation."""
        logger = Logger()

        assert logger is not None
        assert hasattr(logger, "log_dir")
        assert hasattr(logger, "log_files")
        assert len(logger.log_files) == 5

    def test_logger_creates_directory(self):
        """Test that Logger creates log directory."""
        logger = Logger("test_logs")

        # Logger should create the directory structure
        assert logger.log_dir.exists()
        assert logger.log_dir.is_dir()
        assert "logs" in str(logger.log_dir)

    def test_logger_info_message(self):
        """Test logging info message."""
        logger = Logger("test_info")

        logger.info("Test info message")

        info_file = logger.log_files[LogLevel.INFO]
        assert info_file.exists()

        with open(info_file, "r") as f:
            content = f.read()

        assert "Test info message" in content

    def test_logger_debug_message(self):
        """Test logging debug message."""
        logger = Logger("test_debug")

        logger.debug("Test debug message")

        debug_file = logger.log_files[LogLevel.DEBUG]
        assert debug_file.exists()

        with open(debug_file, "r") as f:
            content = f.read()

        assert "Test debug message" in content

    def test_logger_warning_message(self):
        """Test logging warning message."""
        logger = Logger("test_warning")

        logger.warning("Test warning message")

        warning_file = logger.log_files[LogLevel.WARNING]
        assert warning_file.exists()

        with open(warning_file, "r") as f:
            content = f.read()

        assert "Test warning message" in content

    def test_logger_error_message(self):
        """Test logging error message."""
        logger = Logger("test_error")

        test_error = ValueError("Test error")
        logger.error(test_error)

        error_file = logger.log_files[LogLevel.ERROR]
        assert error_file.exists()

        with open(error_file, "r") as f:
            content = f.read()

        assert "ValueError" in content
        assert "Test error" in content

    def test_logger_critical_message(self):
        """Test logging critical message."""
        logger = Logger("test_critical")

        test_error = RuntimeError("Critical error")
        logger.critical(test_error)

        critical_file = logger.log_files[LogLevel.CRITICAL]
        assert critical_file.exists()

        with open(critical_file, "r") as f:
            content = f.read()

        assert "RuntimeError" in content
        assert "Critical error" in content

    def test_logger_exception_handling(self):
        """Test exception logging."""
        logger = Logger("test_exception")

        try:
            raise ValueError("Test exception")
        except ValueError:
            logger.exception("An error occurred")

        error_file = logger.log_files[LogLevel.ERROR]
        assert error_file.exists()

        with open(error_file, "r") as f:
            content = f.read()

        assert "An error occurred" in content or "ValueError" in content

    def test_logger_with_additional_info(self):
        """Test logging with additional information."""
        logger = Logger("test_additional")

        additional_info = {
            "user_id": "123",
            "action": "login",
            "ip_address": "192.168.1.1",
        }

        logger.info("User action", additional_info=additional_info)

        info_file = logger.log_files[LogLevel.INFO]
        with open(info_file, "r") as f:
            content = f.read()

        assert "User action" in content
        # Additional info should be included in some form
        assert "123" in content or "user_id" in content

    def test_logger_clear_logs(self):
        """Test clearing log files."""
        logger = Logger("test_clear")

        # Create some log entries
        logger.info("Test message")
        logger.warning("Warning message")

        # Verify files exist and have content
        info_file = logger.log_files[LogLevel.INFO]
        warning_file = logger.log_files[LogLevel.WARNING]

        assert info_file.exists()
        assert warning_file.exists()

        # Clear logs
        logger.clear_logs()

        # Files should still exist but be empty
        assert info_file.exists()
        assert warning_file.exists()

        with open(info_file, "r") as f:
            assert f.read() == ""

        with open(warning_file, "r") as f:
            assert f.read() == ""

    def test_logger_duplicate_prevention(self):
        """Test that duplicate messages are prevented."""
        logger = Logger("test_duplicate")

        # Log the same message multiple times
        message = "Duplicate test message"
        logger.info(message)
        logger.info(message)
        logger.info(message)

        info_file = logger.log_files[LogLevel.INFO]
        with open(info_file, "r") as f:
            content = f.read()

        # Should only appear once due to duplicate prevention
        assert content.count(message) == 1

    def test_logger_path_traversal_protection(self):
        """Test path traversal protection."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Try to create logger with path outside temp directory
            malicious_path = Path(temp_dir) / ".." / ".." / "malicious"

            logger = Logger(malicious_path)

            # Should be resolved to safe path within logs directory
            assert "logs" in str(logger.log_dir)
            assert logger.log_dir.exists()

    def test_concurrent_logging(self):
        """Test concurrent logging from multiple threads."""
        import threading

        logger = Logger("test_concurrent")

        results = []

        def log_worker(worker_id):
            for i in range(5):
                logger.info(f"Worker {worker_id} - Message {i}")
            results.append(worker_id)

        # Create multiple threads
        threads = []
        for i in range(3):
            thread = threading.Thread(target=log_worker, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # All workers should complete
        assert len(results) == 3

        # Log file should contain entries from all workers
        info_file = logger.log_files[LogLevel.INFO]
        with open(info_file, "r") as f:
            content = f.read()

        # Should have messages from workers (may be deduplicated)
        assert "Worker" in content
        assert "Message" in content

    def test_logger_performance(self):
        """Test logger performance with many messages."""
        import time

        logger = Logger("test_performance")

        start_time = time.time()

        # Log many messages
        for i in range(100):
            logger.info(f"Performance test message {i}")

        end_time = time.time()

        # Should complete in reasonable time (less than 5 seconds)
        assert (end_time - start_time) < 5.0

        # Log file should exist
        info_file = logger.log_files[LogLevel.INFO]
        assert info_file.exists()
