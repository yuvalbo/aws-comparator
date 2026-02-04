"""Tests for Service Quotas comparator module."""

from typing import Any
from unittest.mock import MagicMock

from aws_comparator.comparison.base import ComparisonConfig
from aws_comparator.comparison.servicequotas_comparator import ServiceQuotasComparator
from aws_comparator.models.common import AWSResource
from aws_comparator.models.servicequotas import ServiceQuota


class TestServiceQuotasComparatorInit:
    """Tests for ServiceQuotasComparator initialization."""

    def test_init_default_service_name(self):
        """Test default service name is service-quotas."""
        comparator = ServiceQuotasComparator()
        assert comparator.service_name == "service-quotas"

    def test_init_custom_service_name(self):
        """Test custom service name."""
        comparator = ServiceQuotasComparator("custom-service")
        assert comparator.service_name == "custom-service"

    def test_init_excludes_arn(self):
        """Test ARN is added to excluded fields."""
        comparator = ServiceQuotasComparator()
        assert "arn" in comparator.config.excluded_fields

    def test_init_with_config_keeps_arn_excluded(self):
        """Test ARN is still excluded with custom config."""
        custom_config = ComparisonConfig(excluded_fields={"custom_field"})
        comparator = ServiceQuotasComparator(config=custom_config)
        assert "arn" in comparator.config.excluded_fields
        assert "custom_field" in comparator.config.excluded_fields

    def test_init_has_logger(self):
        """Test logger is initialized."""
        comparator = ServiceQuotasComparator()
        assert comparator.logger is not None


class TestServiceQuotasComparatorGetResourceIdentifier:
    """Tests for _get_resource_identifier method."""

    def test_identifier_from_service_quota(self):
        """Test identifier extraction from ServiceQuota model."""
        comparator = ServiceQuotasComparator()
        quota = ServiceQuota(
            arn="arn:aws:servicequotas:us-east-1:123456789012:ec2/L-1234",
            service_code="ec2",
            service_name="Amazon EC2",
            quota_code="L-1234",
            quota_name="Running instances",
            value=100.0,
        )

        identifier = comparator._get_resource_identifier(quota)

        assert "ec2/L-1234" in identifier
        assert "Amazon EC2" in identifier
        assert "Running instances" in identifier

    def test_identifier_format(self):
        """Test identifier format is correct."""
        comparator = ServiceQuotasComparator()
        quota = ServiceQuota(
            arn="arn:aws:servicequotas:us-east-1:123456789012:lambda/L-5678",
            service_code="lambda",
            service_name="AWS Lambda",
            quota_code="L-5678",
            quota_name="Concurrent executions",
            value=1000.0,
        )

        identifier = comparator._get_resource_identifier(quota)

        # Expected format: service_code/quota_code (service_name - quota_name)
        expected = "lambda/L-5678 (AWS Lambda - Concurrent executions)"
        assert identifier == expected

    def test_identifier_from_resource_with_attributes(self):
        """Test identifier from resource with service_code and quota_code attrs."""
        comparator = ServiceQuotasComparator()
        resource = MagicMock(spec=AWSResource)
        resource.service_code = "s3"
        resource.quota_code = "L-9999"
        resource.service_name = "Amazon S3"
        resource.quota_name = "Buckets"

        # Make it not a ServiceQuota instance
        identifier = comparator._get_resource_identifier(resource)

        assert "s3/L-9999" in identifier
        assert "Amazon S3" in identifier
        assert "Buckets" in identifier

    def test_identifier_from_resource_without_names(self):
        """Test identifier from resource without service_name/quota_name."""
        comparator = ServiceQuotasComparator()
        resource = MagicMock(spec=AWSResource)
        resource.service_code = "ec2"
        resource.quota_code = "L-1234"
        resource.service_name = None
        resource.quota_name = None

        identifier = comparator._get_resource_identifier(resource)

        assert identifier == "ec2/L-1234"

    def test_identifier_fallback_to_parent(self):
        """Test fallback to parent implementation for non-quota resources."""
        comparator = ServiceQuotasComparator()
        resource = MagicMock(spec=AWSResource)
        resource.arn = "arn:aws:other:::resource"

        # Remove quota-specific attributes
        del resource.service_code
        del resource.quota_code

        identifier = comparator._get_resource_identifier(resource)

        # Should use parent implementation (ARN)
        assert identifier == "arn:aws:other:::resource"

    def test_identifier_with_empty_service_code(self):
        """Test identifier when service_code is empty."""
        comparator = ServiceQuotasComparator()
        resource = MagicMock(spec=AWSResource)
        resource.service_code = ""
        resource.quota_code = "L-1234"
        resource.arn = "arn:aws:test:::resource"

        identifier = comparator._get_resource_identifier(resource)

        # Should fallback to parent (ARN) when service_code is empty
        assert identifier == "arn:aws:test:::resource"

    def test_identifier_with_empty_quota_code(self):
        """Test identifier when quota_code is empty."""
        comparator = ServiceQuotasComparator()
        resource = MagicMock(spec=AWSResource)
        resource.service_code = "ec2"
        resource.quota_code = ""
        resource.arn = "arn:aws:test:::resource"

        identifier = comparator._get_resource_identifier(resource)

        # Should fallback to parent (ARN) when quota_code is empty
        assert identifier == "arn:aws:test:::resource"


class TestServiceQuotasComparatorCompare:
    """Tests for compare method."""

    def test_compare_empty_data(self):
        """Test comparing empty data returns result."""
        comparator = ServiceQuotasComparator()
        account1_data: dict[str, list[Any]] = {}
        account2_data: dict[str, list[Any]] = {}

        result = comparator.compare(account1_data, account2_data)

        assert result.service_name == "service-quotas"
        assert result.total_changes == 0

    def test_compare_with_quotas(self):
        """Test comparing quotas."""
        comparator = ServiceQuotasComparator()

        quota1 = ServiceQuota(
            arn="arn:aws:servicequotas:us-east-1:111111111111:ec2/L-1234",
            service_code="ec2",
            service_name="Amazon EC2",
            quota_code="L-1234",
            quota_name="Running instances",
            value=100.0,
        )

        quota2 = ServiceQuota(
            arn="arn:aws:servicequotas:us-east-1:222222222222:ec2/L-1234",
            service_code="ec2",
            service_name="Amazon EC2",
            quota_code="L-1234",
            quota_name="Running instances",
            value=200.0,  # Different value
        )

        account1_data: dict[str, list[Any]] = {"quotas": [quota1]}
        account2_data: dict[str, list[Any]] = {"quotas": [quota2]}

        result = comparator.compare(account1_data, account2_data)

        assert result.service_name == "service-quotas"

    def test_compare_quota_only_in_account1(self):
        """Test quota exists only in account 1."""
        comparator = ServiceQuotasComparator()

        quota1 = ServiceQuota(
            arn="arn:aws:servicequotas:us-east-1:111111111111:ec2/L-1234",
            service_code="ec2",
            service_name="Amazon EC2",
            quota_code="L-1234",
            quota_name="Running instances",
            value=100.0,
        )

        account1_data: dict[str, list[Any]] = {"quotas": [quota1]}
        account2_data: dict[str, list[Any]] = {"quotas": []}

        result = comparator.compare(account1_data, account2_data)

        assert result.service_name == "service-quotas"
        # Should detect the removed quota
        assert result.total_changes >= 1

    def test_compare_quota_only_in_account2(self):
        """Test quota exists only in account 2."""
        comparator = ServiceQuotasComparator()

        quota2 = ServiceQuota(
            arn="arn:aws:servicequotas:us-east-1:222222222222:ec2/L-1234",
            service_code="ec2",
            service_name="Amazon EC2",
            quota_code="L-1234",
            quota_name="Running instances",
            value=100.0,
        )

        account1_data: dict[str, list[Any]] = {"quotas": []}
        account2_data: dict[str, list[Any]] = {"quotas": [quota2]}

        result = comparator.compare(account1_data, account2_data)

        assert result.service_name == "service-quotas"
        # Should detect the added quota
        assert result.total_changes >= 1
