"""
Unit tests for exception hierarchy.
"""

from aws_comparator.core.exceptions import (
    AssumeRoleError,
    AWSComparatorError,
    ComparisonFailedError,
    ConfigFileNotFoundError,
    CredentialsNotFoundError,
    DataFetchError,
    InsufficientPermissionsError,
    InvalidAccountIdError,
    InvalidConfigError,
    InvalidCredentialsError,
    InvalidRegionError,
    OutputFormatError,
    OutputWriteError,
    ServiceNotAvailableError,
    ServiceNotSupportedError,
    ServiceThrottlingError,
)


class TestAWSComparatorError:
    """Test base exception class."""

    def test_base_exception_creation(self):
        """Test creating base exception."""
        error = AWSComparatorError(
            message="Test error",
            error_code="TEST-001",
            details={"key": "value"}
        )

        assert error.message == "Test error"
        assert error.error_code == "TEST-001"
        assert error.details == {"key": "value"}
        assert str(error) == "[TEST-001] Test error (key=value)"

    def test_base_exception_without_details(self):
        """Test creating exception without details."""
        error = AWSComparatorError(
            message="Test error",
            error_code="TEST-001"
        )

        assert error.details == {}
        assert str(error) == "[TEST-001] Test error"

    def test_repr(self):
        """Test __repr__ method."""
        error = AWSComparatorError(
            message="Test error",
            error_code="TEST-001",
            details={"key": "value"}
        )

        repr_str = repr(error)
        assert "AWSComparatorError" in repr_str
        assert "Test error" in repr_str


class TestAuthenticationErrors:
    """Test authentication error classes."""

    def test_credentials_not_found_error(self):
        """Test CredentialsNotFoundError."""
        error = CredentialsNotFoundError()

        assert error.error_code == "AUTH-001"
        assert "not found" in error.message.lower()
        assert "suggestion" in error.details

    def test_invalid_credentials_error(self):
        """Test InvalidCredentialsError."""
        error = InvalidCredentialsError(reason="Expired token")

        assert error.error_code == "AUTH-002"
        assert "Invalid" in error.message
        assert error.details["reason"] == "Expired token"

    def test_assume_role_error(self):
        """Test AssumeRoleError."""
        role_arn = "arn:aws:iam::123456789012:role/TestRole"
        error = AssumeRoleError(role_arn, "Trust policy invalid")

        assert error.error_code == "AUTH-003"
        assert role_arn in error.message
        assert error.details["role_arn"] == role_arn
        assert error.details["reason"] == "Trust policy invalid"


class TestPermissionErrors:
    """Test permission error classes."""

    def test_insufficient_permissions_error(self):
        """Test InsufficientPermissionsError."""
        error = InsufficientPermissionsError(
            service="ec2",
            action="DescribeInstances",
            required_permission="ec2:DescribeInstances"
        )

        assert error.error_code == "PERM-001"
        assert "ec2" in error.message
        assert "DescribeInstances" in error.message
        assert error.details["required_permission"] == "ec2:DescribeInstances"


class TestServiceErrors:
    """Test service error classes."""

    def test_service_not_available_error(self):
        """Test ServiceNotAvailableError."""
        error = ServiceNotAvailableError("bedrock", "us-east-1")

        assert error.error_code == "SERV-001"
        assert "bedrock" in error.message
        assert "us-east-1" in error.message

    def test_service_not_supported_error(self):
        """Test ServiceNotSupportedError."""
        error = ServiceNotSupportedError("unknown-service")

        assert error.error_code == "SERV-002"
        assert "unknown-service" in error.message

    def test_service_throttling_error(self):
        """Test ServiceThrottlingError."""
        error = ServiceThrottlingError("s3", "ListBuckets")

        assert error.error_code == "SERV-003"
        assert "s3" in error.message
        assert "ListBuckets" in error.message


class TestValidationErrors:
    """Test validation error classes."""

    def test_invalid_account_id_error(self):
        """Test InvalidAccountIdError."""
        error = InvalidAccountIdError("123")

        assert error.error_code == "VALID-001"
        assert "123" in error.message

    def test_invalid_config_error(self):
        """Test InvalidConfigError."""
        error = InvalidConfigError(
            "config.yaml",
            ["Missing field: account_id", "Invalid format"]
        )

        assert error.error_code == "VALID-002"
        assert "config.yaml" in error.message
        assert len(error.details["errors"]) == 2

    def test_invalid_region_error(self):
        """Test InvalidRegionError."""
        error = InvalidRegionError("invalid-region")

        assert error.error_code == "VALID-003"
        assert "invalid-region" in error.message


class TestComparisonErrors:
    """Test comparison error classes."""

    def test_data_fetch_error(self):
        """Test DataFetchError."""
        error = DataFetchError("ec2", "instances", "Connection timeout")

        assert error.error_code == "COMP-001"
        assert "ec2" in error.message
        assert "instances" in error.message
        assert error.details["reason"] == "Connection timeout"

    def test_comparison_failed_error(self):
        """Test ComparisonFailedError."""
        error = ComparisonFailedError("s3", "DeepDiff error")

        assert error.error_code == "COMP-002"
        assert "s3" in error.message


class TestConfigurationErrors:
    """Test configuration error classes."""

    def test_config_file_not_found_error(self):
        """Test ConfigFileNotFoundError."""
        error = ConfigFileNotFoundError("/path/to/config.yaml")

        assert error.error_code == "CONFIG-001"
        assert "/path/to/config.yaml" in error.message


class TestOutputErrors:
    """Test output error classes."""

    def test_output_format_error(self):
        """Test OutputFormatError."""
        error = OutputFormatError("xml")

        assert error.error_code == "OUTPUT-001"
        assert "xml" in error.message

    def test_output_write_error(self):
        """Test OutputWriteError."""
        error = OutputWriteError("/tmp/report.json", "Permission denied")

        assert error.error_code == "OUTPUT-002"
        assert "/tmp/report.json" in error.message
        assert "Permission denied" in error.details["reason"]
