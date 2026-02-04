"""
Pytest configuration and shared fixtures.

This module provides common fixtures and configuration for all tests.
"""

from pathlib import Path

import pytest

from aws_comparator.core.config import AccountConfig, ComparisonConfig
from aws_comparator.models.comparison import (
    ComparisonReport,
    ReportSummary,
)


@pytest.fixture
def account1_config() -> AccountConfig:
    """Fixture for first account configuration."""
    return AccountConfig(
        account_id="123456789012",
        profile="test-profile-1",
        region="us-east-1"
    )


@pytest.fixture
def account2_config() -> AccountConfig:
    """Fixture for second account configuration."""
    return AccountConfig(
        account_id="987654321098",
        profile="test-profile-2",
        region="us-east-1"
    )


@pytest.fixture
def comparison_config(
    account1_config: AccountConfig, account2_config: AccountConfig
) -> ComparisonConfig:
    """Fixture for comparison configuration."""
    return ComparisonConfig(
        account1=account1_config,
        account2=account2_config,
        services=["ec2", "s3"],
        parallel_execution=True,
        max_workers=5
    )


@pytest.fixture
def sample_summary() -> ReportSummary:
    """Fixture for report summary."""
    return ReportSummary(
        total_services_compared=2,
        total_services_with_changes=1,
        total_changes=5,
        total_resources_account1=10,
        total_resources_account2=12,
        execution_time_seconds=3.5
    )


@pytest.fixture
def sample_report(
    comparison_config: ComparisonConfig, sample_summary: ReportSummary
) -> ComparisonReport:
    """Fixture for comparison report."""
    return ComparisonReport(
        account1_id=comparison_config.account1.account_id,
        account2_id=comparison_config.account2.account_id,
        region=comparison_config.account1.region,
        services_compared=["ec2", "s3"],
        summary=sample_summary
    )


@pytest.fixture
def temp_config_file(tmp_path: Path, comparison_config: ComparisonConfig) -> Path:
    """Fixture for temporary configuration file."""
    config_file = tmp_path / "test_config.yaml"
    comparison_config.save(config_file)
    return config_file
