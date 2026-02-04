"""
Logging configuration and utilities for AWS Comparator.

This module sets up structured logging with Rich console output,
file rotation, and service-specific log namespaces.
"""

import logging
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional, Union

from rich.console import Console
from rich.logging import RichHandler
from rich.traceback import install as install_rich_traceback

from aws_comparator.core.config import LogLevel

# Install Rich traceback handler for better error display
install_rich_traceback(show_locals=True, max_frames=10)

# Global console instance
console = Console()


class ServiceLoggerAdapter(logging.LoggerAdapter):
    """
    Logger adapter that adds service name to all log messages.

    This allows for easy filtering and identification of log messages
    by service.
    """

    def process(self, msg: str, kwargs: dict) -> tuple[str, dict]:  # type: ignore[type-arg]
        """
        Process log message to add service context.

        Args:
            msg: Original log message
            kwargs: Additional keyword arguments

        Returns:
            Tuple of (modified_message, kwargs)
        """
        extra = self.extra or {}
        service = extra.get("service", "unknown")
        return f"[{service}] {msg}", kwargs


def setup_logging(
    log_level: LogLevel = LogLevel.INFO,
    log_file: Optional[Path] = None,
    enable_file_logging: bool = False,
    verbose: int = 0,
    quiet: bool = False,
) -> None:
    """
    Configure logging for the application.

    Sets up console logging with Rich and optionally file logging with rotation.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file (default: ~/.aws-comparator/logs/comparator.log)
        enable_file_logging: Whether to enable logging to file
        verbose: Verbosity level (0-3), overrides log_level
        quiet: If True, only show errors

    Example:
        >>> setup_logging(LogLevel.DEBUG, verbose=2)
        >>> logger = logging.getLogger(__name__)
        >>> logger.info("Configuration loaded")
    """
    # Determine effective log level
    if quiet:
        effective_level = logging.ERROR
    elif verbose >= 3:
        effective_level = logging.DEBUG
    elif verbose == 2:
        effective_level = logging.DEBUG
    elif verbose == 1:
        effective_level = logging.INFO
    else:
        effective_level = getattr(logging, log_level.value)

    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(effective_level)

    # Remove existing handlers
    root_logger.handlers.clear()

    # Console handler with Rich
    if not quiet:
        console_handler = RichHandler(
            console=console,
            show_time=True,
            show_path=verbose >= 2,
            rich_tracebacks=True,
            tracebacks_show_locals=verbose >= 3,
            markup=True,
        )
        console_handler.setLevel(effective_level)

        # Format for console
        console_format = "%(message)s"
        console_handler.setFormatter(logging.Formatter(console_format))

        root_logger.addHandler(console_handler)

    # File handler with rotation (if enabled)
    if enable_file_logging or log_file:
        if log_file is None:
            log_dir = Path.home() / ".aws-comparator" / "logs"
            log_dir.mkdir(parents=True, exist_ok=True)
            log_file = log_dir / "comparator.log"

        # Ensure log directory exists
        log_file.parent.mkdir(parents=True, exist_ok=True)

        # Rotating file handler (10MB max, keep 5 backups)
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setLevel(logging.DEBUG)  # Always log everything to file

        # Detailed format for file
        file_format = (
            "%(asctime)s - %(name)s - %(levelname)s - "
            "%(filename)s:%(lineno)d - %(message)s"
        )
        file_handler.setFormatter(
            logging.Formatter(file_format, datefmt="%Y-%m-%d %H:%M:%S")
        )

        root_logger.addHandler(file_handler)

    # Set levels for third-party loggers to reduce noise
    logging.getLogger("boto3").setLevel(logging.WARNING)
    logging.getLogger("botocore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("s3transfer").setLevel(logging.WARNING)

    # Log startup message
    logger = logging.getLogger(__name__)
    logger.debug(
        f"Logging initialized: level={effective_level}, "
        f"verbose={verbose}, quiet={quiet}"
    )


def get_logger(
    name: str, service: Optional[str] = None
) -> Union[logging.Logger, ServiceLoggerAdapter]:
    """
    Get a logger for a specific module.

    Args:
        name: Logger name (typically __name__)
        service: Optional service name for service-specific logging

    Returns:
        Logger instance (or ServiceLoggerAdapter if service is provided)

    Example:
        >>> logger = get_logger(__name__, service='ec2')
        >>> logger.info("Fetching EC2 instances")
    """
    logger = logging.getLogger(name)

    if service:
        return ServiceLoggerAdapter(logger, {"service": service})

    return logger


class LogTimer:
    """
    Context manager for timing operations with logging.

    Example:
        >>> with LogTimer(logger, "Fetching EC2 instances"):
        ...     instances = fetch_instances()
    """

    def __init__(
        self, logger: logging.Logger, operation: str, level: int = logging.INFO
    ):
        """
        Initialize the timer.

        Args:
            logger: Logger instance to use
            operation: Description of the operation being timed
            level: Log level to use
        """
        self.logger = logger
        self.operation = operation
        self.level = level
        self.start_time: Optional[datetime] = None

    def __enter__(self) -> "LogTimer":
        """Start the timer."""
        self.start_time = datetime.now()
        self.logger.log(self.level, f"Starting: {self.operation}")
        return self

    def __exit__(
        self, exc_type: Optional[type], exc_val: Optional[Exception], exc_tb: object
    ) -> None:
        """Stop the timer and log duration."""
        if self.start_time:
            duration = (datetime.now() - self.start_time).total_seconds()

            if exc_type:
                self.logger.error(
                    f"Failed: {self.operation} (after {duration:.2f}s): {exc_val}"
                )
            else:
                self.logger.log(
                    self.level, f"Completed: {self.operation} ({duration:.2f}s)"
                )


def log_operation_start(logger: logging.Logger, operation: str, **context: str) -> None:
    """
    Log the start of an operation with context.

    Args:
        logger: Logger instance
        operation: Description of the operation
        **context: Additional context as keyword arguments
    """
    context_str = ", ".join(f"{k}={v}" for k, v in context.items())
    logger.info(f"Starting {operation} ({context_str})")


def log_operation_success(
    logger: logging.Logger, operation: str, duration: float, **context: str
) -> None:
    """
    Log successful completion of an operation.

    Args:
        logger: Logger instance
        operation: Description of the operation
        duration: Duration in seconds
        **context: Additional context as keyword arguments
    """
    context_str = ", ".join(f"{k}={v}" for k, v in context.items())
    logger.info(f"Completed {operation} in {duration:.2f}s ({context_str})")


def log_operation_failure(
    logger: logging.Logger, operation: str, error: Exception, **context: str
) -> None:
    """
    Log failure of an operation.

    Args:
        logger: Logger instance
        operation: Description of the operation
        error: Exception that occurred
        **context: Additional context as keyword arguments
    """
    context_str = ", ".join(f"{k}={v}" for k, v in context.items())
    logger.error(
        f"Failed {operation}: {error.__class__.__name__}: {error} ({context_str})"
    )


def log_progress(
    logger: logging.Logger, current: int, total: int, item: str = "items"
) -> None:
    """
    Log progress of a long-running operation.

    Args:
        logger: Logger instance
        current: Current count
        total: Total count
        item: Description of items being processed
    """
    percentage = (current / total * 100) if total > 0 else 0
    logger.info(f"Progress: {current}/{total} {item} ({percentage:.1f}%)")


# Export console for use in other modules
__all__ = [
    "setup_logging",
    "get_logger",
    "LogTimer",
    "log_operation_start",
    "log_operation_success",
    "log_operation_failure",
    "log_progress",
    "console",
    "ServiceLoggerAdapter",
]
