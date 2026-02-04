"""
Configuration management for AWS Comparator.

This module handles loading, validating, and managing configuration from
multiple sources: files, environment variables, and CLI arguments.
"""

import os
from enum import Enum
from pathlib import Path
from typing import Any, Optional

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator

from aws_comparator.core.exceptions import (
    ConfigFileNotFoundError,
    ConfigParseError,
    InvalidAccountIdError,
    InvalidConfigError,
)


class OutputFormat(str, Enum):
    """Supported output formats."""

    JSON = "json"
    YAML = "yaml"
    TABLE = "table"


class LogLevel(str, Enum):
    """Logging levels."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class AccountConfig(BaseModel):
    """
    Configuration for an AWS account.

    This model defines how to authenticate and connect to an AWS account
    for resource fetching.
    """

    model_config = ConfigDict(extra="ignore")

    account_id: str = Field(..., pattern=r"^\d{12}$", description="AWS account ID")
    profile: Optional[str] = Field(None, description="AWS profile name")
    role_arn: Optional[str] = Field(None, description="IAM role ARN to assume")
    external_id: Optional[str] = Field(None, description="External ID for assume role")
    session_name: Optional[str] = Field(
        None, description="Session name for assume role"
    )
    region: str = Field(default="us-east-1", description="AWS region")

    @field_validator("account_id")
    @classmethod
    def validate_account_id(cls, v: str) -> str:
        """
        Validate AWS account ID format.

        Args:
            v: Account ID to validate

        Returns:
            Validated account ID

        Raises:
            InvalidAccountIdError: If account ID is invalid
        """
        if not v.isdigit() or len(v) != 12:
            raise InvalidAccountIdError(v)
        return v

    def __str__(self) -> str:
        """Return string representation of account config."""
        parts = [self.account_id]
        if self.profile:
            parts.append(f"profile={self.profile}")
        if self.role_arn:
            parts.append(f"role={self.role_arn}")
        return f"AccountConfig({', '.join(parts)})"

    def __repr__(self) -> str:
        """Return detailed representation for debugging."""
        return (
            f"AccountConfig("
            f"account_id={self.account_id!r}, "
            f"profile={self.profile!r}, "
            f"role_arn={self.role_arn!r}, "
            f"region={self.region!r})"
        )


class ServiceFilterConfig(BaseModel):
    """
    Filter configuration for a specific service.

    This allows customizing which resources to include or exclude
    during comparison.
    """

    model_config = ConfigDict(extra="ignore")

    enabled: bool = Field(default=True, description="Whether service is enabled")
    resource_types: Optional[list[str]] = Field(
        None, description="Specific resource types to include (None = all)"
    )
    exclude_tags: dict[str, str] = Field(
        default_factory=dict, description="Exclude resources with these tags"
    )
    include_tags: Optional[dict[str, str]] = Field(
        None, description="Only include resources with these tags"
    )

    def __str__(self) -> str:
        """Return string representation of service filter."""
        status = "enabled" if self.enabled else "disabled"
        return f"ServiceFilterConfig({status})"

    def __repr__(self) -> str:
        """Return detailed representation for debugging."""
        return (
            f"ServiceFilterConfig("
            f"enabled={self.enabled}, "
            f"resource_types={self.resource_types})"
        )


class ComparisonConfig(BaseModel):
    """
    Main configuration for comparison operation.

    This is the top-level configuration model that contains all settings
    for performing account comparisons.
    """

    model_config = ConfigDict(extra="ignore")

    # Account configurations
    account1: AccountConfig = Field(..., description="First account configuration")
    account2: AccountConfig = Field(..., description="Second account configuration")

    # Service selection
    services: Optional[list[str]] = Field(
        None, description="Services to compare (None = all supported services)"
    )
    service_filters: dict[str, ServiceFilterConfig] = Field(
        default_factory=dict, description="Per-service filter configurations"
    )

    # Output configuration
    output_format: OutputFormat = Field(
        default=OutputFormat.TABLE, description="Output format"
    )
    output_file: Optional[Path] = Field(None, description="Output file path")
    no_color: bool = Field(default=False, description="Disable colored output")

    # Execution configuration
    parallel_execution: bool = Field(
        default=True, description="Execute service fetchers in parallel"
    )
    max_workers: int = Field(
        default=10, ge=1, le=50, description="Maximum number of parallel workers"
    )

    # Logging configuration
    log_level: LogLevel = Field(default=LogLevel.INFO, description="Logging level")
    verbose: int = Field(default=0, ge=0, le=3, description="Verbosity level (0-3)")
    quiet: bool = Field(default=False, description="Suppress non-error output")

    # Comparison filters
    ignore_fields: list[str] = Field(
        default_factory=lambda: [
            "LastModifiedDate",
            "CreationDate",
            "StateTransitionReason",
            "LaunchTime",
            "LastAccessedDate",
        ],
        description="Fields to ignore in comparisons",
    )
    ignore_tags: list[str] = Field(
        default_factory=list, description="Tag keys to ignore (supports wildcards)"
    )

    @field_validator("services")
    @classmethod
    def validate_services(cls, v: Optional[list[str]]) -> Optional[list[str]]:
        """
        Validate service names.

        Args:
            v: List of service names to validate

        Returns:
            Validated list of service names

        Raises:
            ValueError: If any service names are invalid
        """
        if v is None:
            return v

        # Define supported services
        valid_services = {
            "ec2",
            "s3",
            "lambda",
            "secrets-manager",
            "sns",
            "sqs",
            "cloudwatch",
            "bedrock",
            "pinpoint",
            "eventbridge",
            "elastic-beanstalk",
            "service-quotas",
        }

        invalid = set(v) - valid_services
        if invalid:
            raise ValueError(
                f"Invalid services: {invalid}. Valid services: {sorted(valid_services)}"
            )
        return v

    def get_service_filter(self, service_name: str) -> ServiceFilterConfig:
        """
        Get filter configuration for a specific service.

        Args:
            service_name: Name of the service

        Returns:
            ServiceFilterConfig for the service (default if not configured)
        """
        return self.service_filters.get(
            service_name,
            ServiceFilterConfig(),  # type: ignore[call-arg]
        )

    @classmethod
    def from_file(cls, config_path: Path) -> "ComparisonConfig":
        """
        Load configuration from a YAML file.

        Args:
            config_path: Path to the configuration file

        Returns:
            ComparisonConfig instance

        Raises:
            ConfigFileNotFoundError: If file doesn't exist
            ConfigParseError: If file cannot be parsed
        """
        if not config_path.exists():
            raise ConfigFileNotFoundError(str(config_path))

        try:
            with open(config_path, encoding="utf-8") as f:
                data = yaml.safe_load(f)

            if data is None:
                data = {}

            return cls(**data)

        except yaml.YAMLError as e:
            raise ConfigParseError(str(config_path), str(e)) from e
        except Exception as e:
            raise ConfigParseError(str(config_path), str(e)) from e

    @classmethod
    def from_env(cls, prefix: str = "AWS_COMPARATOR_") -> dict[str, Any]:
        """
        Load configuration values from environment variables.

        Args:
            prefix: Environment variable prefix

        Returns:
            Dictionary of configuration values from environment

        Example:
            AWS_COMPARATOR_REGION=us-west-2
            AWS_COMPARATOR_OUTPUT_FORMAT=json
        """
        config_dict: dict[str, Any] = {}

        # Map environment variables to config fields
        env_mappings = {
            f"{prefix}REGION": ("account1", "region"),
            f"{prefix}OUTPUT_FORMAT": ("output_format",),
            f"{prefix}LOG_LEVEL": ("log_level",),
            f"{prefix}MAX_WORKERS": ("max_workers",),
        }

        for env_var, field_path in env_mappings.items():
            value = os.environ.get(env_var)
            if value:
                # Handle nested fields
                if len(field_path) == 1:
                    config_dict[field_path[0]] = value
                elif len(field_path) == 2:
                    if field_path[0] not in config_dict:
                        config_dict[field_path[0]] = {}
                    config_dict[field_path[0]][field_path[1]] = value

        return config_dict

    def to_dict(self) -> dict[str, Any]:
        """
        Export configuration as dictionary.

        Returns:
            Dictionary representation of configuration
        """
        return self.model_dump(exclude_none=True, mode="json")

    def to_yaml(self) -> str:
        """
        Export configuration as YAML string.

        Returns:
            YAML representation of configuration
        """
        result: str = yaml.dump(self.to_dict(), default_flow_style=False)
        return result

    def save(self, config_path: Path) -> None:
        """
        Save configuration to a YAML file.

        Args:
            config_path: Path where to save the configuration
        """
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, "w", encoding="utf-8") as f:
            f.write(self.to_yaml())

    def __str__(self) -> str:
        """Return string representation of config."""
        return (
            f"ComparisonConfig("
            f"account1={self.account1.account_id}, "
            f"account2={self.account2.account_id}, "
            f"services={len(self.services or [])})"
        )

    def __repr__(self) -> str:
        """Return detailed representation for debugging."""
        return (
            f"ComparisonConfig("
            f"account1={self.account1!r}, "
            f"account2={self.account2!r}, "
            f"services={self.services!r}, "
            f"output_format={self.output_format.value!r})"
        )


def get_default_config_path() -> Path:
    """
    Get the default configuration file path.

    Returns:
        Path to default configuration file (~/.aws-comparator/config.yaml)
    """
    return Path.home() / ".aws-comparator" / "config.yaml"


def load_config(
    config_file: Optional[Path] = None,
    account1_id: Optional[str] = None,
    account2_id: Optional[str] = None,
    **overrides: Any,
) -> ComparisonConfig:
    """
    Load configuration from multiple sources with precedence.

    Precedence order (highest to lowest):
    1. Explicit overrides (CLI arguments)
    2. Configuration file
    3. Environment variables
    4. Default values

    Args:
        config_file: Optional configuration file path
        account1_id: First account ID (required)
        account2_id: Second account ID (required)
        **overrides: Additional configuration overrides

    Returns:
        ComparisonConfig instance

    Raises:
        InvalidConfigError: If configuration is invalid
    """
    config_dict: dict[str, Any] = {}

    # 1. Load from default config file if it exists
    default_config_path = get_default_config_path()
    if default_config_path.exists():
        try:
            default_config = ComparisonConfig.from_file(default_config_path)
            config_dict.update(default_config.to_dict())
        except Exception:
            pass  # Ignore errors in default config file

    # 2. Load from environment variables
    env_config = ComparisonConfig.from_env()
    config_dict.update(env_config)

    # 3. Load from specified config file
    if config_file and config_file.exists():
        file_config = ComparisonConfig.from_file(config_file)
        config_dict.update(file_config.to_dict())

    # 4. Apply explicit overrides
    if account1_id:
        if "account1" not in config_dict:
            config_dict["account1"] = {}
        config_dict["account1"]["account_id"] = account1_id

    if account2_id:
        if "account2" not in config_dict:
            config_dict["account2"] = {}
        config_dict["account2"]["account_id"] = account2_id

    # Apply other overrides
    config_dict.update(overrides)

    # Validate required fields
    if "account1" not in config_dict or "account_id" not in config_dict["account1"]:
        raise InvalidConfigError(
            str(config_file or "command line"),
            ["Missing required field: account1.account_id"],
        )

    if "account2" not in config_dict or "account_id" not in config_dict["account2"]:
        raise InvalidConfigError(
            str(config_file or "command line"),
            ["Missing required field: account2.account_id"],
        )

    try:
        return ComparisonConfig(**config_dict)
    except Exception as e:
        raise InvalidConfigError(str(config_file or "command line"), [str(e)]) from e
