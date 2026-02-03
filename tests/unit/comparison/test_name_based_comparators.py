"""Tests for name-based comparators module."""
from typing import Any

import pytest

from aws_comparator.comparison.name_based_comparators import (
    BedrockComparator,
    CloudWatchComparator,
    EC2Comparator,
    ElasticBeanstalkComparator,
    EventBridgeComparator,
    LambdaComparator,
    S3Comparator,
    SecretsManagerComparator,
    SNSComparator,
    SQSComparator,
)
from aws_comparator.models.common import AWSResource


class MockResource(AWSResource):
    """Mock resource with additional fields for testing."""


def create_resource(**kwargs: Any) -> MockResource:
    """Create a mock resource with given attributes."""
    defaults: dict[str, Any] = {
        "arn": None,
        "tags": {},
        "region": None,
        "created_date": None,
    }
    defaults.update(kwargs)
    resource = MockResource(**defaults)
    # Add any extra attributes dynamically
    for key, value in kwargs.items():
        if not hasattr(resource, key):
            object.__setattr__(resource, key, value)
    return resource


class TestCloudWatchComparator:
    """Tests for CloudWatchComparator."""

    @pytest.fixture
    def comparator(self):
        """Create CloudWatch comparator."""
        return CloudWatchComparator()

    def test_init_excluded_fields(self, comparator):
        """Test excluded fields are set."""
        assert "alarm_arn" in comparator.config.excluded_fields
        assert "state_value" in comparator.config.excluded_fields

    def test_get_resource_identifier_alarm(self, comparator):
        """Test identifier extraction for alarm."""
        resource = create_resource(alarm_name="test-alarm")

        identifier = comparator._get_resource_identifier(resource)

        assert identifier == "test-alarm"

    def test_get_resource_identifier_log_group(self, comparator):
        """Test identifier extraction for log group."""
        resource = create_resource(log_group_name="/aws/lambda/test")

        identifier = comparator._get_resource_identifier(resource)

        assert identifier == "/aws/lambda/test"

    def test_get_resource_identifier_dashboard(self, comparator):
        """Test identifier extraction for dashboard."""
        resource = create_resource(dashboard_name="my-dashboard")

        identifier = comparator._get_resource_identifier(resource)

        assert identifier == "my-dashboard"


class TestEventBridgeComparator:
    """Tests for EventBridgeComparator."""

    @pytest.fixture
    def comparator(self):
        """Create EventBridge comparator."""
        return EventBridgeComparator()

    def test_init_excluded_fields(self, comparator):
        """Test excluded fields are set."""
        assert "arn" in comparator.config.excluded_fields

    def test_get_resource_identifier_rule(self, comparator):
        """Test identifier extraction for rule with event bus."""
        resource = create_resource(name="test-rule", event_bus_name="default")

        identifier = comparator._get_resource_identifier(resource)

        assert identifier == "test-rule@default"

    def test_get_resource_identifier_event_bus(self, comparator):
        """Test identifier extraction for event bus."""
        resource = create_resource(name="custom-bus")

        identifier = comparator._get_resource_identifier(resource)

        assert identifier == "custom-bus"

    def test_get_resource_identifier_archive(self, comparator):
        """Test identifier extraction for archive."""
        resource = create_resource(archive_name="test-archive")

        identifier = comparator._get_resource_identifier(resource)

        assert identifier == "test-archive"


class TestSecretsManagerComparator:
    """Tests for SecretsManagerComparator."""

    @pytest.fixture
    def comparator(self):
        """Create Secrets Manager comparator."""
        return SecretsManagerComparator()

    def test_init_excluded_fields(self, comparator):
        """Test excluded fields are set."""
        assert "arn" in comparator.config.excluded_fields
        assert "version_ids_to_stages" in comparator.config.excluded_fields
        assert "last_accessed_date" in comparator.config.excluded_fields

    def test_get_resource_identifier_secret(self, comparator):
        """Test identifier extraction for secret."""
        resource = create_resource(name="my-secret")

        identifier = comparator._get_resource_identifier(resource)

        assert identifier == "my-secret"


class TestLambdaComparator:
    """Tests for LambdaComparator."""

    @pytest.fixture
    def comparator(self):
        """Create Lambda comparator."""
        return LambdaComparator()

    def test_init_excluded_fields(self, comparator):
        """Test excluded fields are set."""
        assert "function_arn" in comparator.config.excluded_fields
        assert "code_sha256" in comparator.config.excluded_fields
        assert "role" in comparator.config.excluded_fields

    def test_get_resource_identifier_function(self, comparator):
        """Test identifier extraction for function."""
        resource = create_resource(function_name="my-function")

        identifier = comparator._get_resource_identifier(resource)

        assert identifier == "my-function"

    def test_get_resource_identifier_layer(self, comparator):
        """Test identifier extraction for layer."""
        resource = create_resource(layer_name="my-layer")

        identifier = comparator._get_resource_identifier(resource)

        assert identifier == "my-layer"


class TestS3Comparator:
    """Tests for S3Comparator."""

    @pytest.fixture
    def comparator(self):
        """Create S3 comparator."""
        return S3Comparator()

    def test_init_excluded_fields(self, comparator):
        """Test excluded fields are set."""
        assert "arn" in comparator.config.excluded_fields
        assert "owner_id" in comparator.config.excluded_fields

    def test_get_resource_identifier_bucket(self, comparator):
        """Test identifier extraction for bucket."""
        resource = create_resource(name="my-bucket")

        identifier = comparator._get_resource_identifier(resource)

        assert identifier == "my-bucket"


class TestEC2Comparator:
    """Tests for EC2Comparator."""

    @pytest.fixture
    def comparator(self):
        """Create EC2 comparator."""
        return EC2Comparator()

    def test_init_excluded_fields(self, comparator):
        """Test excluded fields are set."""
        assert "arn" in comparator.config.excluded_fields
        assert "instance_id" in comparator.config.excluded_fields
        assert "private_ip_address" in comparator.config.excluded_fields

    def test_get_resource_identifier_instance_with_name_tag(self, comparator):
        """Test identifier extraction for instance with Name tag."""
        resource = create_resource(
            instance_id="i-12345",
            tags={"Name": "my-instance"},
        )

        identifier = comparator._get_resource_identifier(resource)

        assert "my-instance" in identifier

    def test_get_resource_identifier_security_group(self, comparator):
        """Test identifier extraction for security group."""
        resource = create_resource(
            group_id="sg-12345",
            group_name="my-security-group",
        )

        identifier = comparator._get_resource_identifier(resource)

        assert identifier == "sg:my-security-group"

    def test_get_resource_identifier_vpc(self, comparator):
        """Test identifier extraction for VPC."""
        resource = create_resource(
            vpc_id="vpc-12345",
            cidr_block="10.0.0.0/16",
        )

        identifier = comparator._get_resource_identifier(resource)

        assert identifier == "vpc:10.0.0.0/16"

    def test_get_resource_identifier_subnet(self, comparator):
        """Test identifier extraction for subnet."""
        resource = create_resource(
            subnet_id="subnet-12345",
            cidr_block="10.0.1.0/24",
            availability_zone="us-east-1a",
        )

        identifier = comparator._get_resource_identifier(resource)

        assert identifier == "subnet:10.0.1.0/24@us-east-1a"

    def test_get_resource_identifier_key_pair(self, comparator):
        """Test identifier extraction for key pair."""
        resource = create_resource(
            key_name="my-key-pair",
            key_fingerprint="ab:cd:ef",
        )

        identifier = comparator._get_resource_identifier(resource)

        assert identifier == "keypair:my-key-pair"


class TestSQSComparator:
    """Tests for SQSComparator."""

    @pytest.fixture
    def comparator(self):
        """Create SQS comparator."""
        return SQSComparator()

    def test_init_excluded_fields(self, comparator):
        """Test excluded fields are set."""
        assert "arn" in comparator.config.excluded_fields
        assert "queue_url" in comparator.config.excluded_fields
        assert "queue_arn" in comparator.config.excluded_fields

    def test_get_resource_identifier_queue(self, comparator):
        """Test identifier extraction for queue."""
        resource = create_resource(queue_name="my-queue")

        identifier = comparator._get_resource_identifier(resource)

        assert identifier == "my-queue"


class TestBedrockComparator:
    """Tests for BedrockComparator."""

    @pytest.fixture
    def comparator(self):
        """Create Bedrock comparator."""
        return BedrockComparator()

    def test_init_excluded_fields(self, comparator):
        """Test excluded fields are set."""
        assert "arn" in comparator.config.excluded_fields
        assert "model_arn" in comparator.config.excluded_fields

    def test_get_resource_identifier_model_id(self, comparator):
        """Test identifier extraction for model by ID."""
        resource = create_resource(model_id="anthropic.claude-v2")

        identifier = comparator._get_resource_identifier(resource)

        assert identifier == "anthropic.claude-v2"

    def test_get_resource_identifier_model_name(self, comparator):
        """Test identifier extraction for model by name."""
        resource = create_resource(model_name="claude-instant")

        identifier = comparator._get_resource_identifier(resource)

        assert identifier == "claude-instant"

    def test_get_resource_identifier_provisioned_model(self, comparator):
        """Test identifier extraction for provisioned model."""
        resource = create_resource(provisioned_model_name="my-provisioned-model")

        identifier = comparator._get_resource_identifier(resource)

        assert identifier == "my-provisioned-model"


class TestElasticBeanstalkComparator:
    """Tests for ElasticBeanstalkComparator."""

    @pytest.fixture
    def comparator(self):
        """Create Elastic Beanstalk comparator."""
        return ElasticBeanstalkComparator()

    def test_init_excluded_fields(self, comparator):
        """Test excluded fields are set."""
        assert "arn" in comparator.config.excluded_fields
        assert "environment_id" in comparator.config.excluded_fields
        assert "endpoint_url" in comparator.config.excluded_fields

    def test_get_resource_identifier_environment(self, comparator):
        """Test identifier extraction for environment."""
        resource = create_resource(
            application_name="my-app",
            environment_name="production",
        )

        identifier = comparator._get_resource_identifier(resource)

        assert identifier == "my-app/production"

    def test_get_resource_identifier_application(self, comparator):
        """Test identifier extraction for application."""
        resource = create_resource(application_name="my-app")

        identifier = comparator._get_resource_identifier(resource)

        assert identifier == "my-app"


class TestSNSComparator:
    """Tests for SNSComparator."""

    @pytest.fixture
    def comparator(self):
        """Create SNS comparator."""
        return SNSComparator()

    def test_init_excluded_fields(self, comparator):
        """Test excluded fields are set."""
        assert "arn" in comparator.config.excluded_fields
        assert "topic_arn" in comparator.config.excluded_fields
        assert "subscription_arn" in comparator.config.excluded_fields
        assert "owner" in comparator.config.excluded_fields

    def test_get_resource_identifier_topic(self, comparator):
        """Test identifier extraction for topic."""
        resource = create_resource(topic_name="my-topic")

        identifier = comparator._get_resource_identifier(resource)

        assert identifier == "my-topic"

    def test_get_resource_identifier_subscription(self, comparator):
        """Test identifier extraction for subscription."""
        resource = create_resource(
            subscription_arn="arn:aws:sns:us-east-1:123:my-topic:abc",
            topic_name="my-topic",
            protocol="email",
            endpoint="test@example.com",
        )

        identifier = comparator._get_resource_identifier(resource)

        assert identifier == "my-topic:email:test@example.com"
