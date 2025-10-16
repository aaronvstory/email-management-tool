import json
import logging
import os
from datetime import datetime, timezone
from logging import Logger
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Dict

_DEF_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"

class JSONFormatter(logging.Formatter):
    """
    JSON formatter for structured logging.

    Outputs log records as JSON with fields:
    - timestamp: ISO 8601 timestamp
    - level: Log level (INFO, WARNING, ERROR, etc.)
    - logger: Logger name
    - message: Log message
    - module: Module name
    - function: Function name
    - line: Line number
    - exc_info: Exception info (if present)
    """

    def format(self, record: logging.LogRecord) -> str:
        log_data: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exc_info"] = self.formatException(record.exc_info)

        # Add extra fields if present (for structured logging)
        if hasattr(record, "extra_fields"):
            log_data.update(record.extra_fields)

        return json.dumps(log_data, default=str)


class _Formatter(logging.Formatter):
    """Simple formatter for console output."""
    def format(self, record: logging.LogRecord) -> str:
        # Minimal structured fields; avoid leaking sensitive data
        record.message = record.getMessage()
        return super().format(record)


def setup_app_logging(app, log_dir: str = "logs", log_level: str = "INFO") -> None:
    """
    Attach JSON file logging and console logging to Flask app.logger.

    Features:
    - JSON-formatted file logging with rotation (10MB max, 5 backups)
    - Console logging with simple format for development
    - Configurable log directory and level
    - Thread-safe operation

    Args:
        app: Flask application instance
        log_dir: Directory for log files (default: "logs")
        log_level: Minimum log level (default: "INFO")
    """
    try:
        logger: Logger = app.logger  # type: ignore

        # Only setup if no handlers exist (avoid duplicates)
        if logger.handlers:
            return

        # Get log level from environment or parameter
        level_name = os.getenv("LOG_LEVEL", log_level).upper()
        level = getattr(logging, level_name, logging.INFO)
        logger.setLevel(level)

        # Create log directory if it doesn't exist
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)

        # 1. JSON File Handler with Rotation (10MB max, 5 backups)
        json_log_file = log_path / "app.json.log"
        json_handler = RotatingFileHandler(
            json_log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding="utf-8"
        )
        json_handler.setLevel(level)
        json_handler.setFormatter(JSONFormatter())
        logger.addHandler(json_handler)

        # 2. Plain Text File Handler with Rotation (for backward compatibility)
        text_log_file = log_path / "app.log"
        text_handler = RotatingFileHandler(
            text_log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding="utf-8"
        )
        text_handler.setLevel(level)
        text_handler.setFormatter(_Formatter(_DEF_FORMAT))
        logger.addHandler(text_handler)

        # 3. Console Handler (for development)
        if os.getenv("TESTING") != "1":  # Skip console in tests
            console_handler = logging.StreamHandler()
            console_handler.setLevel(level)
            console_handler.setFormatter(_Formatter(_DEF_FORMAT))
            logger.addHandler(console_handler)

        logger.propagate = False

        logger.info(f"Logging initialized: level={level_name}, json_log={json_log_file}, text_log={text_log_file}")

    except Exception as e:
        # Fallback to stderr if logging setup fails
        import sys
        print(f"ERROR: Failed to setup logging: {e}", file=sys.stderr)


__all__ = ["setup_app_logging", "JSONFormatter"]
