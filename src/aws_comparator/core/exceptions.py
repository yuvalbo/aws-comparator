"""
Custom exception hierarchy for AWS Comparator.

This module defines all custom exceptions used throughout the application,
following a hierarchical structure for better error handling and debugging.
"""

from typing import Any, Optional


class AWSComparatorError(Exception):
    """
    Base exception for all AWS Comparator errors.

    All custom exceptions in this application inherit from this base class,
    allowing for easy catching of all application-specific errors.

    Attributes:
        message: Human-readable error message
        error_code: Unique error code for programmatic handling
        details: Additional context information about the error
    """

    def __init__(
        self,
        message: str,
        error_code: str,
        details: Optional[dict[str, Any]] = None
    ) -> None:
        """
        Initialize the base exception.

        Args:
            message: Human-readable error message
            error_code: Unique error code (e.g., "AUTH-001")
            details: Optional dictionary with additional context
        """
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)

    def __str__(self) -> str:
        """Return string representation of the error."""
        error_str = f"[{self.error_code}] {self.message}"
        if self.details:
            details_str = ", ".join(f"{k}={v}" for k, v in self.details.items())
            error_str += f" ({details_str})"
        return error_str

    def __repr__(self) -> str:
        """Return detailed representation for debugging."""
        return (
            f"{self.__class__.__name__}("
            f"message={self.message!r}, "
            f"error_code={self.error_code!r}, "
            f"details={self.details!r})"
        )


# ============================================================================
# Authentication Errors (AUTH-xxx)
# ============================================================================

class AuthenticationError(AWSComparatorError):
    """Base class for all authentication-related errors."""
    pass


class CredentialsNotFoundError(AuthenticationError):
    """Raised when AWS credentials cannot be found."""

    def __init__(self) -> None:
        super().__init__(
            message="AWS credentials not found",
            error_code="AUTH-001",
            details={
                "suggestion": (
                    "Configure AWS credentials via profile, "
                    "environment variables, or IAM role"
                )
            }
        )


class InvalidCredentialsError(AuthenticationError):
    """Raised when AWS credentials are invalid."""

    def __init__(self, reason: Optional[str] = None) -> None:
        details: dict[str, str] = {
            "suggestion": "Verify your AWS access key and secret key"
        }
        if reason:
            details["reason"] = reason

        super().__init__(
            message="Invalid AWS credentials",
            error_code="AUTH-002",
            details=details
        )


class AssumeRoleError(AuthenticationError):
    """Raised when assuming an IAM role fails."""

    def __init__(self, role_arn: str, reason: str) -> None:
        super().__init__(
            message=f"Failed to assume role: {role_arn}",
            error_code="AUTH-003",
            details={
                "role_arn": role_arn,
                "reason": reason,
                "suggestion": "Check role trust policy and permissions"
            }
        )


# ============================================================================
# Permission Errors (PERM-xxx)
# ============================================================================

class PermissionError(AWSComparatorError):
    """Base class for all permission-related errors."""
    pass


class InsufficientPermissionsError(PermissionError):
    """Raised when IAM permissions are insufficient for an operation."""

    def __init__(self, service: str, action: str, required_permission: str) -> None:
        super().__init__(
            message=f"Permission denied: {service}.{action}",
            error_code="PERM-001",
            details={
                "service": service,
                "action": action,
                "required_permission": required_permission,
                "suggestion": f"Add IAM policy with {required_permission} permission"
            }
        )


# ============================================================================
# Service Errors (SERV-xxx)
# ============================================================================

class ServiceError(AWSComparatorError):
    """Base class for all service-related errors."""
    pass


class ServiceNotAvailableError(ServiceError):
    """Raised when a service is not available in a specific region."""

    def __init__(self, service: str, region: str) -> None:
        super().__init__(
            message=f"Service {service} not available in region {region}",
            error_code="SERV-001",
            details={
                "service": service,
                "region": region,
                "suggestion": "Try a different region or check AWS service availability"
            }
        )


class ServiceNotSupportedError(ServiceError):
    """Raised when a service is not supported by the comparator."""

    def __init__(self, service: str) -> None:
        super().__init__(
            message=f"Service {service} not supported",
            error_code="SERV-002",
            details={
                "service": service,
                "suggestion": "Run 'aws-comparator list-services' to see supported services"
            }
        )


class ServiceThrottlingError(ServiceError):
    """Raised when AWS API throttling occurs."""

    def __init__(self, service: str, operation: str) -> None:
        super().__init__(
            message=f"Throttling error for {service}.{operation}",
            error_code="SERV-003",
            details={
                "service": service,
                "operation": operation,
                "suggestion": (
                    "Retry with exponential backoff or request rate limit increase"
                )
            }
        )


# ============================================================================
# Validation Errors (VALID-xxx)
# ============================================================================

class ValidationError(AWSComparatorError):
    """Base class for all validation errors."""
    pass


class InvalidAccountIdError(ValidationError):
    """Raised when an AWS account ID is invalid."""

    def __init__(self, account_id: str) -> None:
        super().__init__(
            message=f"Invalid account ID: {account_id}",
            error_code="VALID-001",
            details={
                "account_id": account_id,
                "suggestion": "Account ID must be exactly 12 digits"
            }
        )


class InvalidConfigError(ValidationError):
    """Raised when configuration is invalid."""

    def __init__(self, config_file: str, errors: list[str]) -> None:
        super().__init__(
            message=f"Invalid configuration file: {config_file}",
            error_code="VALID-002",
            details={
                "config_file": config_file,
                "errors": errors,
                "suggestion": "Fix configuration errors and try again"
            }
        )


class InvalidRegionError(ValidationError):
    """Raised when an AWS region is invalid."""

    def __init__(self, region: str) -> None:
        super().__init__(
            message=f"Invalid AWS region: {region}",
            error_code="VALID-003",
            details={
                "region": region,
                "suggestion": "Use a valid AWS region code (e.g., us-east-1)"
            }
        )


# ============================================================================
# Comparison Errors (COMP-xxx)
# ============================================================================

class ComparisonError(AWSComparatorError):
    """Base class for all comparison operation errors."""
    pass


class DataFetchError(ComparisonError):
    """Raised when fetching data from AWS fails."""

    def __init__(self, service: str, resource_type: str, reason: str) -> None:
        super().__init__(
            message=f"Failed to fetch {service}.{resource_type}",
            error_code="COMP-001",
            details={
                "service": service,
                "resource_type": resource_type,
                "reason": reason
            }
        )


class ComparisonFailedError(ComparisonError):
    """Raised when a comparison operation fails."""

    def __init__(self, service: str, reason: str) -> None:
        super().__init__(
            message=f"Comparison failed for service: {service}",
            error_code="COMP-002",
            details={
                "service": service,
                "reason": reason
            }
        )


class DataNormalizationError(ComparisonError):
    """Raised when data normalization fails."""

    def __init__(self, service: str, resource_type: str, reason: str) -> None:
        super().__init__(
            message=f"Failed to normalize data for {service}.{resource_type}",
            error_code="COMP-003",
            details={
                "service": service,
                "resource_type": resource_type,
                "reason": reason
            }
        )


# ============================================================================
# Configuration Errors (CONFIG-xxx)
# ============================================================================

class ConfigurationError(AWSComparatorError):
    """Base class for configuration errors."""
    pass


class ConfigFileNotFoundError(ConfigurationError):
    """Raised when configuration file is not found."""

    def __init__(self, config_path: str) -> None:
        super().__init__(
            message=f"Configuration file not found: {config_path}",
            error_code="CONFIG-001",
            details={
                "config_path": config_path,
                "suggestion": "Create a configuration file or use default settings"
            }
        )


class ConfigParseError(ConfigurationError):
    """Raised when configuration file cannot be parsed."""

    def __init__(self, config_path: str, reason: str) -> None:
        super().__init__(
            message=f"Failed to parse configuration file: {config_path}",
            error_code="CONFIG-002",
            details={
                "config_path": config_path,
                "reason": reason,
                "suggestion": "Check YAML syntax in configuration file"
            }
        )


# ============================================================================
# Output Errors (OUTPUT-xxx)
# ============================================================================

class OutputError(AWSComparatorError):
    """Base class for output-related errors."""
    pass


class OutputFormatError(OutputError):
    """Raised when output format is invalid."""

    def __init__(self, format_name: str) -> None:
        super().__init__(
            message=f"Invalid output format: {format_name}",
            error_code="OUTPUT-001",
            details={
                "format": format_name,
                "suggestion": "Use one of: json, yaml, table"
            }
        )


class OutputWriteError(OutputError):
    """Raised when writing output fails."""

    def __init__(self, output_path: str, reason: str) -> None:
        super().__init__(
            message=f"Failed to write output to: {output_path}",
            error_code="OUTPUT-002",
            details={
                "output_path": output_path,
                "reason": reason,
                "suggestion": "Check file permissions and disk space"
            }
        )
