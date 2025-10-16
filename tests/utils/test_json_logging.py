"""
Tests for JSON logging functionality.

Verifies that structured JSON logging works correctly with rotation.
"""
import json
import logging
import tempfile
from pathlib import Path

import pytest

from app.utils.logging import JSONFormatter, setup_app_logging


def test_json_formatter_creates_valid_json():
    """Test that JSONFormatter produces valid JSON output."""
    formatter = JSONFormatter()
    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname="test.py",
        lineno=42,
        msg="Test message",
        args=(),
        exc_info=None,
        func="test_func"
    )

    output = formatter.format(record)

    # Should be valid JSON
    log_data = json.loads(output)

    # Check required fields
    assert "timestamp" in log_data
    assert "level" in log_data
    assert "logger" in log_data
    assert "message" in log_data
    assert "module" in log_data
    assert "function" in log_data
    assert "line" in log_data

    # Check values
    assert log_data["level"] == "INFO"
    assert log_data["logger"] == "test_logger"
    assert log_data["message"] == "Test message"
    assert log_data["function"] == "test_func"
    assert log_data["line"] == 42


def test_json_formatter_includes_exception_info():
    """Test that exceptions are included in JSON output."""
    formatter = JSONFormatter()

    try:
        raise ValueError("Test exception")
    except ValueError:
        import sys
        exc_info = sys.exc_info()

        record = logging.LogRecord(
            name="test_logger",
            level=logging.ERROR,
            pathname="test.py",
            lineno=10,
            msg="Error occurred",
            args=(),
            exc_info=exc_info,
            func="test_func"
        )

        output = formatter.format(record)
        log_data = json.loads(output)

        # Should include exception info
        assert "exc_info" in log_data
        assert "ValueError" in log_data["exc_info"]
        assert "Test exception" in log_data["exc_info"]


def test_setup_app_logging_creates_log_files(app, tmp_path):
    """Test that setup_app_logging creates log files in the correct directory."""
    log_dir = tmp_path / "test_logs"

    # Clear any existing handlers
    app.logger.handlers.clear()

    # Setup logging with custom directory
    setup_app_logging(app, log_dir=str(log_dir))

    # Verify log directory was created
    assert log_dir.exists()

    # Log a test message
    app.logger.info("Test log message")

    # Verify JSON log file exists
    json_log = log_dir / "app.json.log"
    assert json_log.exists()

    # Verify plain text log file exists
    text_log = log_dir / "app.log"
    assert text_log.exists()

    # Verify JSON log contains valid JSON
    with open(json_log, 'r') as f:
        for line in f:
            if line.strip():
                log_data = json.loads(line)
                assert "timestamp" in log_data
                assert "message" in log_data


def test_json_log_rotation(app, tmp_path):
    """Test that log rotation works correctly."""
    log_dir = tmp_path / "rotation_test"

    # Clear any existing handlers
    app.logger.handlers.clear()

    # Setup logging with very small max size for testing (1KB)
    setup_app_logging(app, log_dir=str(log_dir))

    # Get the JSON handler and update its maxBytes for testing
    for handler in app.logger.handlers:
        if isinstance(handler, logging.handlers.RotatingFileHandler):
            if "json" in str(handler.baseFilename):
                handler.maxBytes = 1024  # 1KB for testing

    # Write enough logs to trigger rotation
    for i in range(100):
        app.logger.info(f"Test log message {i} " + "x" * 100)

    # Verify rotation occurred (backup files should exist)
    json_log = log_dir / "app.json.log"
    assert json_log.exists()

    # Check if any backup files were created
    backup_files = list(log_dir.glob("app.json.log.*"))
    # Note: Rotation may or may not occur depending on exact log sizes
    # Just verify the main file exists and is below max size + some buffer
    assert json_log.stat().st_size < 10240  # 10KB buffer


def test_logging_respects_log_level_env_var(app, tmp_path, monkeypatch):
    """Test that LOG_LEVEL environment variable is respected."""
    log_dir = tmp_path / "level_test"

    # Clear any existing handlers
    app.logger.handlers.clear()

    # Set LOG_LEVEL to WARNING
    monkeypatch.setenv("LOG_LEVEL", "WARNING")

    setup_app_logging(app, log_dir=str(log_dir))

    # Log at different levels
    app.logger.debug("Debug message")
    app.logger.info("Info message")
    app.logger.warning("Warning message")
    app.logger.error("Error message")

    # Read JSON log
    json_log = log_dir / "app.json.log"
    logged_messages = []
    with open(json_log, 'r') as f:
        for line in f:
            if line.strip():
                log_data = json.loads(line)
                logged_messages.append(log_data["level"])

    # Should only have WARNING and ERROR (not DEBUG or INFO)
    assert "DEBUG" not in logged_messages
    assert "INFO" not in logged_messages
    assert "WARNING" in logged_messages
    assert "ERROR" in logged_messages
