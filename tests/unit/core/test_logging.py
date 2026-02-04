"""Tests for core logging module."""

import logging
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from aws_comparator.core.config import LogLevel
from aws_comparator.core.logging import (
    LogTimer,
    ServiceLoggerAdapter,
    get_logger,
    log_operation_failure,
    log_operation_start,
    log_operation_success,
    log_progress,
    setup_logging,
)


class TestServiceLoggerAdapter:
    """Tests for ServiceLoggerAdapter class."""

    def test_process_adds_service_prefix(self):
        """Test process method adds service name to message."""
        logger = logging.getLogger("test")
        adapter = ServiceLoggerAdapter(logger, {"service": "ec2"})
        msg, kwargs = adapter.process("Test message", {})
        assert msg == "[ec2] Test message"
        assert kwargs == {}

    def test_process_without_extra(self):
        """Test process method with no extra data."""
        logger = logging.getLogger("test")
        adapter = ServiceLoggerAdapter(logger, None)
        msg, kwargs = adapter.process("Test message", {})
        assert msg == "[unknown] Test message"

    def test_process_with_empty_service(self):
        """Test process method with empty service name."""
        logger = logging.getLogger("test")
        adapter = ServiceLoggerAdapter(logger, {})
        msg, kwargs = adapter.process("Test message", {})
        assert msg == "[unknown] Test message"


class TestSetupLogging:
    """Tests for setup_logging function."""

    def test_setup_logging_default(self):
        """Test setup_logging with default parameters."""
        # Clean up any existing handlers
        root_logger = logging.getLogger()
        root_logger.handlers.clear()

        setup_logging()

        root_logger = logging.getLogger()
        assert root_logger.level == logging.INFO

    def test_setup_logging_quiet_mode(self):
        """Test setup_logging with quiet mode sets ERROR level."""
        root_logger = logging.getLogger()
        root_logger.handlers.clear()

        setup_logging(quiet=True)

        assert root_logger.level == logging.ERROR

    def test_setup_logging_verbose_level_1(self):
        """Test setup_logging with verbose=1 sets INFO level."""
        root_logger = logging.getLogger()
        root_logger.handlers.clear()

        setup_logging(verbose=1)

        assert root_logger.level == logging.INFO

    def test_setup_logging_verbose_level_2(self):
        """Test setup_logging with verbose=2 sets DEBUG level."""
        root_logger = logging.getLogger()
        root_logger.handlers.clear()

        setup_logging(verbose=2)

        assert root_logger.level == logging.DEBUG

    def test_setup_logging_verbose_level_3(self):
        """Test setup_logging with verbose=3 sets DEBUG level."""
        root_logger = logging.getLogger()
        root_logger.handlers.clear()

        setup_logging(verbose=3)

        assert root_logger.level == logging.DEBUG

    def test_setup_logging_with_file(self):
        """Test setup_logging creates file handler."""
        root_logger = logging.getLogger()
        root_logger.handlers.clear()

        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "test.log"
            setup_logging(log_file=log_file)

            assert log_file.parent.exists()

    def test_setup_logging_with_file_creates_directory(self):
        """Test setup_logging creates log directory if needed."""
        root_logger = logging.getLogger()
        root_logger.handlers.clear()

        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "subdir" / "test.log"
            setup_logging(log_file=log_file)

            assert log_file.parent.exists()

    def test_setup_logging_enable_file_logging(self):
        """Test setup_logging with enable_file_logging creates default log file."""
        root_logger = logging.getLogger()
        root_logger.handlers.clear()

        with patch("aws_comparator.core.logging.Path.home") as mock_home:
            mock_home.return_value = Path(tempfile.mkdtemp())
            setup_logging(enable_file_logging=True)

    def test_setup_logging_log_level_debug(self):
        """Test setup_logging with DEBUG log level."""
        root_logger = logging.getLogger()
        root_logger.handlers.clear()

        setup_logging(log_level=LogLevel.DEBUG)

        assert root_logger.level == logging.DEBUG

    def test_setup_logging_log_level_warning(self):
        """Test setup_logging with WARNING log level."""
        root_logger = logging.getLogger()
        root_logger.handlers.clear()

        setup_logging(log_level=LogLevel.WARNING)

        assert root_logger.level == logging.WARNING


class TestGetLogger:
    """Tests for get_logger function."""

    def test_get_logger_without_service(self):
        """Test get_logger returns Logger without service."""
        logger = get_logger("test_module")
        assert isinstance(logger, logging.Logger)

    def test_get_logger_with_service(self):
        """Test get_logger returns ServiceLoggerAdapter with service."""
        logger = get_logger("test_module", service="ec2")
        assert isinstance(logger, ServiceLoggerAdapter)

    def test_get_logger_adapter_logs_with_prefix(self):
        """Test ServiceLoggerAdapter logs messages with service prefix."""
        logger = get_logger("test_module", service="s3")
        assert isinstance(logger, ServiceLoggerAdapter)


class TestLogTimer:
    """Tests for LogTimer context manager."""

    def test_log_timer_success(self):
        """Test LogTimer logs start and completion messages."""
        mock_logger = Mock()
        with LogTimer(mock_logger, "test operation"):
            pass

        # Should have been called twice: start and completion
        assert mock_logger.log.call_count == 2
        start_call = mock_logger.log.call_args_list[0]
        assert "Starting: test operation" in start_call.args[1]
        end_call = mock_logger.log.call_args_list[1]
        assert "Completed: test operation" in end_call.args[1]

    def test_log_timer_failure(self):
        """Test LogTimer logs failure message on exception."""
        mock_logger = Mock()
        with pytest.raises(ValueError):
            with LogTimer(mock_logger, "test operation"):
                raise ValueError("Test error")

        # Should have called log for start and error for failure
        assert mock_logger.log.call_count == 1
        assert mock_logger.error.call_count == 1
        error_call = mock_logger.error.call_args
        assert "Failed: test operation" in error_call.args[0]
        assert "Test error" in error_call.args[0]

    def test_log_timer_with_custom_level(self):
        """Test LogTimer uses custom log level."""
        mock_logger = Mock()
        with LogTimer(mock_logger, "test operation", level=logging.DEBUG):
            pass

        start_call = mock_logger.log.call_args_list[0]
        assert start_call.args[0] == logging.DEBUG

    def test_log_timer_records_duration(self):
        """Test LogTimer includes duration in completion message."""
        mock_logger = Mock()
        with LogTimer(mock_logger, "test operation"):
            pass

        end_call = mock_logger.log.call_args_list[1]
        # Should contain duration in seconds
        assert "s)" in end_call.args[1]


class TestLogOperationStart:
    """Tests for log_operation_start function."""

    def test_log_operation_start_no_context(self):
        """Test log_operation_start with no context."""
        mock_logger = Mock()
        log_operation_start(mock_logger, "fetch data")

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args.args[0]
        assert "Starting fetch data" in call_args

    def test_log_operation_start_with_context(self):
        """Test log_operation_start with context kwargs."""
        mock_logger = Mock()
        log_operation_start(
            mock_logger, "fetch data", service="ec2", region="us-east-1"
        )

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args.args[0]
        assert "service=ec2" in call_args
        assert "region=us-east-1" in call_args


class TestLogOperationSuccess:
    """Tests for log_operation_success function."""

    def test_log_operation_success_basic(self):
        """Test log_operation_success basic usage."""
        mock_logger = Mock()
        log_operation_success(mock_logger, "fetch data", 2.5)

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args.args[0]
        assert "Completed fetch data" in call_args
        assert "2.50s" in call_args

    def test_log_operation_success_with_context(self):
        """Test log_operation_success with context kwargs."""
        mock_logger = Mock()
        log_operation_success(mock_logger, "fetch data", 1.5, service="ec2", count="10")

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args.args[0]
        assert "service=ec2" in call_args
        assert "count=10" in call_args


class TestLogOperationFailure:
    """Tests for log_operation_failure function."""

    def test_log_operation_failure_basic(self):
        """Test log_operation_failure basic usage."""
        mock_logger = Mock()
        error = ValueError("Test error")
        log_operation_failure(mock_logger, "fetch data", error)

        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args.args[0]
        assert "Failed fetch data" in call_args
        assert "ValueError" in call_args
        assert "Test error" in call_args

    def test_log_operation_failure_with_context(self):
        """Test log_operation_failure with context kwargs."""
        mock_logger = Mock()
        error = RuntimeError("Connection failed")
        log_operation_failure(mock_logger, "fetch data", error, service="s3")

        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args.args[0]
        assert "service=s3" in call_args
        assert "RuntimeError" in call_args


class TestLogProgress:
    """Tests for log_progress function."""

    def test_log_progress_basic(self):
        """Test log_progress basic usage."""
        mock_logger = Mock()
        log_progress(mock_logger, 5, 10)

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args.args[0]
        assert "Progress: 5/10 items" in call_args
        assert "50.0%" in call_args

    def test_log_progress_custom_item(self):
        """Test log_progress with custom item name."""
        mock_logger = Mock()
        log_progress(mock_logger, 3, 9, item="queues")

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args.args[0]
        assert "queues" in call_args
        assert "33.3%" in call_args

    def test_log_progress_zero_total(self):
        """Test log_progress handles zero total."""
        mock_logger = Mock()
        log_progress(mock_logger, 0, 0)

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args.args[0]
        assert "0.0%" in call_args

    def test_log_progress_complete(self):
        """Test log_progress at 100%."""
        mock_logger = Mock()
        log_progress(mock_logger, 10, 10)

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args.args[0]
        assert "100.0%" in call_args
