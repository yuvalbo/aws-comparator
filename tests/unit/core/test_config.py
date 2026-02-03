"""
Unit tests for configuration management.
"""

import pytest
from pydantic import ValidationError

from aws_comparator.core.config import (
    AccountConfig,
    ComparisonConfig,
    LogLevel,
    OutputFormat,
    ServiceFilterConfig,
    load_config,
)
from aws_comparator.core.exceptions import InvalidConfigError


class TestAccountConfig:
    """Test AccountConfig model."""

    def test_valid_account_config(self):
        """Test creating valid account configuration."""
        config = AccountConfig(  # type: ignore[call-arg]
            account_id="123456789012",
            profile="test-profile",
            region="us-east-1"
        )

        assert config.account_id == "123456789012"
        assert config.profile == "test-profile"
        assert config.region == "us-east-1"

    def test_invalid_account_id(self):
        """Test validation of account ID.

        Note: The Field pattern validator runs before the custom field_validator,
        so pydantic raises ValidationError for pattern mismatch.
        """
        with pytest.raises(ValidationError):
            AccountConfig(  # type: ignore[call-arg]
                account_id="123",  # Too short - doesn't match r'^\d{12}$' pattern
                region="us-east-1"
            )

    def test_default_region(self):
        """Test default region is set."""
        config = AccountConfig(account_id="123456789012")  # type: ignore[call-arg]
        assert config.region == "us-east-1"

    def test_str_representation(self):
        """Test string representation."""
        config = AccountConfig(  # type: ignore[call-arg]
            account_id="123456789012",
            profile="test"
        )
        assert "123456789012" in str(config)


class TestServiceFilterConfig:
    """Test ServiceFilterConfig model."""

    def test_default_filter_config(self):
        """Test default filter configuration."""
        config = ServiceFilterConfig()  # type: ignore[call-arg]

        assert config.enabled is True
        assert config.resource_types is None
        assert config.exclude_tags == {}

    def test_custom_filter_config(self):
        """Test custom filter configuration."""
        config = ServiceFilterConfig(  # type: ignore[call-arg]
            enabled=True,
            resource_types=["instances", "volumes"],
            exclude_tags={"temporary": "true"}
        )

        assert config.enabled is True
        assert config.resource_types is not None and len(config.resource_types) == 2
        assert config.exclude_tags["temporary"] == "true"


class TestComparisonConfig:
    """Test ComparisonConfig model."""

    def test_valid_comparison_config(self, account1_config, account2_config):
        """Test creating valid comparison configuration."""
        config = ComparisonConfig(  # type: ignore[call-arg]
            account1=account1_config,
            account2=account2_config,
            services=["ec2", "s3"]
        )

        assert config.account1.account_id == "123456789012"
        assert config.account2.account_id == "987654321098"
        assert config.services is not None and len(config.services) == 2

    def test_default_values(self, account1_config, account2_config):
        """Test default configuration values."""
        config = ComparisonConfig(  # type: ignore[call-arg]
            account1=account1_config,
            account2=account2_config
        )

        assert config.output_format == OutputFormat.TABLE
        assert config.parallel_execution is True
        assert config.max_workers == 10
        assert config.log_level == LogLevel.INFO

    def test_invalid_service_names(self, account1_config, account2_config):
        """Test validation of service names."""
        with pytest.raises(ValueError) as exc_info:
            ComparisonConfig(  # type: ignore[call-arg]
                account1=account1_config,
                account2=account2_config,
                services=["ec2", "invalid-service"]
            )
        assert "Invalid services" in str(exc_info.value)

    def test_get_service_filter(self, comparison_config):
        """Test getting service filter configuration."""
        filter_config = comparison_config.get_service_filter("ec2")
        assert filter_config.enabled is True

    def test_to_dict(self, comparison_config):
        """Test converting to dictionary."""
        config_dict = comparison_config.to_dict()

        assert isinstance(config_dict, dict)
        assert "account1" in config_dict
        assert "account2" in config_dict

    def test_to_yaml(self, comparison_config):
        """Test converting to YAML."""
        yaml_str = comparison_config.to_yaml()

        assert isinstance(yaml_str, str)
        assert "account1" in yaml_str

    def test_save_and_load(self, comparison_config, tmp_path):
        """Test saving and loading configuration."""
        config_file = tmp_path / "test_config.yaml"

        # Save
        comparison_config.save(config_file)
        assert config_file.exists()

        # Load
        loaded_config = ComparisonConfig.from_file(config_file)
        assert loaded_config.account1.account_id == comparison_config.account1.account_id
        assert loaded_config.account2.account_id == comparison_config.account2.account_id


class TestLoadConfig:
    """Test load_config function."""

    def test_load_config_with_accounts(self):
        """Test loading configuration with account IDs."""
        config = load_config(
            account1_id="123456789012",
            account2_id="987654321098"
        )

        assert config.account1.account_id == "123456789012"
        assert config.account2.account_id == "987654321098"

    def test_load_config_missing_account1(self):
        """Test error when account1 is missing."""
        with pytest.raises(InvalidConfigError) as exc_info:
            load_config(account2_id="987654321098")
        assert "account1" in str(exc_info.value).lower()

    def test_load_config_missing_account2(self):
        """Test error when account2 is missing."""
        with pytest.raises(InvalidConfigError) as exc_info:
            load_config(account1_id="123456789012")
        assert "account2" in str(exc_info.value).lower()

    def test_load_config_with_overrides(self):
        """Test loading configuration with overrides."""
        config = load_config(
            account1_id="123456789012",
            account2_id="987654321098",
            max_workers=20,
            parallel_execution=False
        )

        assert config.max_workers == 20
        assert config.parallel_execution is False
