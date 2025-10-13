"""
Structured logging utility for authentication system
"""

import inspect
import sys
import traceback
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional


class LogLevel(Enum):
    """Logging severity levels"""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class Logger:
    """
    Structured logging for authentication system

    Features:
    - Level-specific log files
    - Duplicate prevention
    - Function call context
    - Error tracebacks
    - Audit trail support
    """

    def __init__(self, log_dir: str | Path = "logs"):
        self.log_dir = Path(log_dir)
        self.log_files = {
            LogLevel.DEBUG: self.log_dir / "debug.log",
            LogLevel.INFO: self.log_dir / "info.log",
            LogLevel.WARNING: self.log_dir / "warning.log",
            LogLevel.ERROR: self.log_dir / "error.log",
            LogLevel.CRITICAL: self.log_dir / "critical.log",
        }
        self._ensure_log_directory()
        self._log_cache: set[int] = set()

    def _ensure_log_directory(self) -> None:
        self.log_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _get_caller_info() -> tuple[str, str]:
        stack = inspect.stack()
        caller_frame = next(
            (frame for frame in stack if frame.filename != __file__),
            stack[2] if len(stack) > 2 else None,
        )
        current_function = caller_frame.function if caller_frame else "Unknown"
        parent_function = stack[3].function if len(stack) > 3 else "Unknown"
        return current_function, parent_function

    def _format_message(
        self,
        level: LogLevel,
        message: str,
        error: Optional[Exception] = None,
        additional_info: Optional[Dict[str, Any]] = None,
        exc_info: bool = False,
    ) -> str:
        """Format the complete log message with all metadata."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        current_function, parent_function = self._get_caller_info()

        log_msg = [
            "=" * 80,
            f"TIMESTAMP: {timestamp}",
            f"LEVEL: {level.value}",
            f"FUNCTION: {current_function}",
            f"PARENT FUNCTION: {parent_function}",
            "-" * 80,
            f"MESSAGE: {message}",
        ]

        if error:
            log_msg.extend(
                [
                    f"ERROR TYPE: {type(error).__name__}",
                    f"ERROR MESSAGE: {str(error)}",
                    "-" * 80,
                ]
            )

            if exc_info:
                try:
                    trace_lines = traceback.format_exception(
                        type(error), error, error.__traceback__
                    )
                    log_msg.extend(["FULL TRACEBACK:", "".join(trace_lines)])
                except Exception as e:
                    log_msg.append(f"Failed to format traceback: {str(e)}")

        default_context = {
            "system_engineer": "Muhammad",
            "system": "authentication_system",
            "component": "backend",
        }

        if additional_info:
            default_context.update(additional_info)

        log_msg.extend(
            [
                "-" * 80,
                "CONTEXT:",
                "\n".join(f"{k}: {v}" for k, v in default_context.items()),
                "=" * 80 + "\n",
            ]
        )

        return "\n".join(log_msg)

    def _write_log(self, level: LogLevel, message: str) -> None:
        log_hash = hash(message)
        if log_hash in self._log_cache:
            return

        try:
            self._ensure_log_directory()
            with open(self.log_files[level], "a", encoding="utf-8") as f:
                f.write(message)
            self._log_cache.add(log_hash)
        except (IOError, PermissionError) as e:
            print(f"Failed to write log: {e}", file=sys.stderr)

    def debug(
        self, message: str, additional_info: Optional[Dict[str, Any]] = None
    ) -> None:
        formatted = self._format_message(
            LogLevel.DEBUG, message, additional_info=additional_info
        )
        self._write_log(LogLevel.DEBUG, formatted)

    def info(
        self, message: str, additional_info: Optional[Dict[str, Any]] = None
    ) -> None:
        formatted = self._format_message(
            LogLevel.INFO, message, additional_info=additional_info
        )
        self._write_log(LogLevel.INFO, formatted)

    def warning(
        self, message: str, additional_info: Optional[Dict[str, Any]] = None
    ) -> None:
        formatted = self._format_message(
            LogLevel.WARNING, message, additional_info=additional_info
        )
        self._write_log(LogLevel.WARNING, formatted)

    def error(
        self,
        error: Exception,
        additional_info: Optional[Dict[str, Any]] = None,
        exc_info: bool = True,
    ) -> None:
        message = f"{type(error).__name__}: {str(error)}"
        formatted = self._format_message(
            LogLevel.ERROR,
            message,
            error=error,
            additional_info=additional_info,
            exc_info=exc_info,
        )
        self._write_log(LogLevel.ERROR, formatted)

    def critical(
        self,
        error: Exception,
        additional_info: Optional[Dict[str, Any]] = None,
        exc_info: bool = True,
    ) -> None:
        message = f"{type(error).__name__}: {str(error)}"
        formatted = self._format_message(
            LogLevel.CRITICAL,
            message,
            error=error,
            additional_info=additional_info,
            exc_info=exc_info,
        )
        self._write_log(LogLevel.CRITICAL, formatted)

    def exception(
        self, message: str, additional_info: Optional[Dict[str, Any]] = None
    ) -> None:
        _, exc_value, _ = sys.exc_info()
        if exc_value is not None:
            self.error(
                exc_value,
                additional_info=additional_info
                if additional_info
                else {"message": message},
                exc_info=True,
            )
        else:
            self.error(
                Exception(message), additional_info=additional_info, exc_info=False
            )

    def clear_logs(self, level: Optional[LogLevel] = None) -> None:
        try:
            targets = [self.log_files[level]] if level else self.log_files.values()
            for file in targets:
                with open(file, "w", encoding="utf-8") as f:
                    f.write("")
            self._log_cache.clear()
        except Exception as e:
            print(f"Failed to clear logs: {e}", file=sys.stderr)


# Global logger instance
system_logger = Logger()


def get_logger(_name: Optional[str] = None) -> Logger:
    """Get logger instance"""
    return system_logger
