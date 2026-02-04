"""
Name-based comparators for AWS resources.

This module provides specialized comparators that match resources by name
instead of ARN. This is essential for cross-account comparison because ARNs
contain account IDs which are always different between accounts.

Comparators included:
- CloudWatchComparator: For alarms, log groups, and dashboards
- EventBridgeComparator: For rules (by name + event bus)
- SecretsManagerComparator: For secrets
- LambdaComparator: For Lambda functions and layers
- S3Comparator: For S3 buckets
- EC2Comparator: For instances, security groups, VPCs, etc.
"""

import logging
from typing import Any, Optional

from aws_comparator.comparison.base import ComparisonConfig
from aws_comparator.comparison.resource_comparator import ResourceComparator
from aws_comparator.models.common import AWSResource


class CloudWatchComparator(ResourceComparator):
    """
    Specialized comparator for CloudWatch resources.

    Matches alarms by alarm_name, log groups by log_group_name, and
    dashboards by dashboard_name instead of ARN.
    """

    def __init__(
        self,
        service_name: str = "cloudwatch",
        config: Optional[ComparisonConfig] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize the CloudWatch comparator."""
        if config is None:
            config = ComparisonConfig()

        # Exclude ARN and transient state fields from comparison
        config.excluded_fields = config.excluded_fields | {
            "arn",
            "alarm_arn",
            "log_group_arn",
            "dashboard_arn",
            "state_value",
            "state_reason",
            "state_reason_data",
            "state_updated_timestamp",
            "stored_bytes",  # Changes over time
        }

        super().__init__(service_name, config, **kwargs)
        self.logger = logging.getLogger(
            f"{self.__class__.__module__}.{self.__class__.__name__}"
        )

    def _get_resource_identifier(self, resource: AWSResource) -> str:
        """
        Extract unique identifier from a CloudWatch resource.

        Uses name-based fields instead of ARN for cross-account comparison.
        """
        # CloudWatch Alarms
        if hasattr(resource, "alarm_name") and resource.alarm_name:  # type: ignore[attr-defined]
            return str(resource.alarm_name)  # type: ignore[attr-defined]

        # CloudWatch Log Groups
        if hasattr(resource, "log_group_name") and resource.log_group_name:  # type: ignore[attr-defined]
            return str(resource.log_group_name)  # type: ignore[attr-defined]

        # CloudWatch Dashboards
        if hasattr(resource, "dashboard_name") and resource.dashboard_name:  # type: ignore[attr-defined]
            return str(resource.dashboard_name)  # type: ignore[attr-defined]

        # Fallback to parent implementation
        return super()._get_resource_identifier(resource)


class EventBridgeComparator(ResourceComparator):
    """
    Specialized comparator for EventBridge resources.

    Matches rules by name + event_bus_name combination, and other resources
    by their name fields instead of ARN.
    """

    def __init__(
        self,
        service_name: str = "eventbridge",
        config: Optional[ComparisonConfig] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize the EventBridge comparator."""
        if config is None:
            config = ComparisonConfig()

        # Exclude ARN from comparison
        config.excluded_fields = config.excluded_fields | {"arn"}

        super().__init__(service_name, config, **kwargs)
        self.logger = logging.getLogger(
            f"{self.__class__.__module__}.{self.__class__.__name__}"
        )

    def _get_resource_identifier(self, resource: AWSResource) -> str:
        """
        Extract unique identifier from an EventBridge resource.

        For rules, uses name + event_bus_name combination.
        For other resources, uses name field.
        """
        # EventBridge Rules - use name@event_bus_name format
        if hasattr(resource, "event_bus_name") and hasattr(resource, "name"):
            name = getattr(resource, "name", None)
            event_bus_name = getattr(resource, "event_bus_name", "default")
            if name:
                return f"{name}@{event_bus_name}"

        # Event Buses
        if hasattr(resource, "name") and resource.name:  # type: ignore[attr-defined]
            return str(resource.name)  # type: ignore[attr-defined]

        # Archives
        if hasattr(resource, "archive_name") and resource.archive_name:  # type: ignore[attr-defined]
            return str(resource.archive_name)  # type: ignore[attr-defined]

        # Fallback to parent implementation
        return super()._get_resource_identifier(resource)


class SecretsManagerComparator(ResourceComparator):
    """
    Specialized comparator for Secrets Manager resources.

    Matches secrets by name instead of ARN.
    """

    def __init__(
        self,
        service_name: str = "secretsmanager",
        config: Optional[ComparisonConfig] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize the Secrets Manager comparator."""
        if config is None:
            config = ComparisonConfig()

        # Exclude ARN and transient fields from comparison
        config.excluded_fields = config.excluded_fields | {
            "arn",
            "version_ids_to_stages",  # Version IDs are different per account
            "last_accessed_date",
            "last_changed_date",
            "last_rotated_date",
        }

        super().__init__(service_name, config, **kwargs)
        self.logger = logging.getLogger(
            f"{self.__class__.__module__}.{self.__class__.__name__}"
        )

    def _get_resource_identifier(self, resource: AWSResource) -> str:
        """
        Extract unique identifier from a Secrets Manager resource.

        Uses secret name instead of ARN.
        """
        # Secrets - use name field
        if hasattr(resource, "name") and resource.name:  # type: ignore[attr-defined]
            return str(resource.name)  # type: ignore[attr-defined]

        # Fallback to parent implementation
        return super()._get_resource_identifier(resource)


class LambdaComparator(ResourceComparator):
    """
    Specialized comparator for Lambda resources.

    Matches functions by function_name and layers by layer_name
    instead of ARN.
    """

    def __init__(
        self,
        service_name: str = "lambda",
        config: Optional[ComparisonConfig] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize the Lambda comparator."""
        if config is None:
            config = ComparisonConfig()

        # Exclude ARN and transient fields from comparison
        config.excluded_fields = config.excluded_fields | {
            "arn",
            "function_arn",
            "layer_arn",
            "layer_version_arn",
            "code_sha256",  # Code deployment hash differs between accounts
            "last_modified",
            "role",  # IAM role ARNs contain account IDs
        }

        super().__init__(service_name, config, **kwargs)
        self.logger = logging.getLogger(
            f"{self.__class__.__module__}.{self.__class__.__name__}"
        )

    def _get_resource_identifier(self, resource: AWSResource) -> str:
        """
        Extract unique identifier from a Lambda resource.

        Uses function_name or layer_name instead of ARN.
        """
        # Lambda Functions
        if hasattr(resource, "function_name") and resource.function_name:  # type: ignore[attr-defined]
            return str(resource.function_name)  # type: ignore[attr-defined]

        # Lambda Layers
        if hasattr(resource, "layer_name") and resource.layer_name:  # type: ignore[attr-defined]
            return str(resource.layer_name)  # type: ignore[attr-defined]

        # Fallback to parent implementation
        return super()._get_resource_identifier(resource)


class S3Comparator(ResourceComparator):
    """
    Specialized comparator for S3 resources.

    Matches buckets by name (bucket names are globally unique).
    """

    def __init__(
        self,
        service_name: str = "s3",
        config: Optional[ComparisonConfig] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize the S3 comparator."""
        if config is None:
            config = ComparisonConfig()

        # Exclude ARN and account-specific fields
        config.excluded_fields = config.excluded_fields | {
            "arn",
            "owner_id",  # Account-specific
            "owner_display_name",  # Account-specific
        }

        super().__init__(service_name, config, **kwargs)
        self.logger = logging.getLogger(
            f"{self.__class__.__module__}.{self.__class__.__name__}"
        )

    def _get_resource_identifier(self, resource: AWSResource) -> str:
        """
        Extract unique identifier from an S3 resource.

        Uses bucket name (globally unique).
        """
        # S3 Buckets - use name field
        if hasattr(resource, "name") and resource.name:  # type: ignore[attr-defined]
            return str(resource.name)  # type: ignore[attr-defined]

        # Fallback to parent implementation
        return super()._get_resource_identifier(resource)


class EC2Comparator(ResourceComparator):
    """
    Specialized comparator for EC2 resources.

    EC2 resources have unique IDs per account (instance IDs, security group IDs,
    VPC IDs, etc.), so we need to compare them by Name tag or other meaningful
    identifiers. For resources without Name tags, we fall back to using configuration
    characteristics to match resources.
    """

    def __init__(
        self,
        service_name: str = "ec2",
        config: Optional[ComparisonConfig] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize the EC2 comparator."""
        if config is None:
            config = ComparisonConfig()

        # Exclude ARN and account/resource-specific IDs
        config.excluded_fields = config.excluded_fields | {
            "arn",
            "owner_id",  # Account-specific
            "instance_id",  # Resource-specific ID
            "vpc_id",  # Resource-specific ID (but we'll use Name tag)
            "subnet_id",  # Resource-specific ID
            "group_id",  # Security group ID
            "key_pair_id",  # Key pair ID
            "route_table_id",  # Route table ID
            "network_acl_id",  # NACL ID
            "security_groups",  # List of SG IDs - account specific
            "private_ip_address",  # Network-specific
            "public_ip_address",  # Network-specific
            "private_dns_name",  # Network-specific
            "public_dns_name",  # Network-specific
            "launch_time",  # Instance-specific timestamp
            "available_ip_address_count",  # Dynamic value
        }

        super().__init__(service_name, config, **kwargs)
        self.logger = logging.getLogger(
            f"{self.__class__.__module__}.{self.__class__.__name__}"
        )

    def _get_resource_identifier(self, resource: AWSResource) -> str:
        """
        Extract unique identifier from an EC2 resource.

        Prioritizes Name tag, then falls back to other meaningful identifiers.
        For some resources without Name tags, uses configuration characteristics.
        """
        # Try to get Name tag first (most common identifier)
        if hasattr(resource, "tags") and resource.tags:
            name_tag = resource.tags.get("Name")
            if name_tag:
                # Prefix with resource type for clarity
                resource_type = self._get_resource_type_prefix(resource)
                return f"{resource_type}:{name_tag}"

        # EC2 Instances - use Name tag (handled above) or instance type + ami combo
        if hasattr(resource, "instance_id"):
            # If no Name tag, use instance_type + ami_id as identifier
            instance_type = getattr(resource, "instance_type", "unknown")
            ami_id = getattr(resource, "ami_id", "unknown")
            return f"instance:{instance_type}/{ami_id}"

        # Security Groups - use group_name (within a VPC, names should be unique)
        if hasattr(resource, "group_name") and hasattr(resource, "group_id"):
            group_name = getattr(resource, "group_name", None)
            if group_name:
                return f"sg:{group_name}"

        # VPCs - use CIDR block as identifier (common pattern for VPC design)
        if hasattr(resource, "vpc_id") and hasattr(resource, "cidr_block"):
            cidr = getattr(resource, "cidr_block", None)
            if cidr:
                return f"vpc:{cidr}"

        # Subnets - use CIDR block + availability zone
        if hasattr(resource, "subnet_id") and hasattr(resource, "cidr_block"):
            cidr = getattr(resource, "cidr_block", None)
            az = getattr(resource, "availability_zone", "unknown")
            if cidr:
                return f"subnet:{cidr}@{az}"

        # Key pairs - use key_name
        if hasattr(resource, "key_name") and hasattr(resource, "key_fingerprint"):
            key_name = getattr(resource, "key_name", None)
            if key_name:
                return f"keypair:{key_name}"

        # Fallback to parent implementation
        return super()._get_resource_identifier(resource)

    def _get_resource_type_prefix(self, resource: AWSResource) -> str:
        """Get a short prefix for the resource type."""
        if hasattr(resource, "instance_id"):
            return "instance"
        if hasattr(resource, "group_id") and hasattr(resource, "group_name"):
            return "sg"
        if (
            hasattr(resource, "vpc_id")
            and hasattr(resource, "cidr_block")
            and not hasattr(resource, "subnet_id")
        ):
            return "vpc"
        if hasattr(resource, "subnet_id"):
            return "subnet"
        if hasattr(resource, "route_table_id"):
            return "rtb"
        if hasattr(resource, "network_acl_id"):
            return "nacl"
        if hasattr(resource, "key_name") and hasattr(resource, "key_fingerprint"):
            return "keypair"
        return "ec2"


class SQSComparator(ResourceComparator):
    """
    Specialized comparator for SQS resources.

    Matches queues by queue name instead of ARN/URL.
    """

    def __init__(
        self,
        service_name: str = "sqs",
        config: Optional[ComparisonConfig] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize the SQS comparator."""
        if config is None:
            config = ComparisonConfig()

        # Exclude ARN and URL (contains account ID)
        config.excluded_fields = config.excluded_fields | {
            "arn",
            "queue_url",  # Contains account ID
            "queue_arn",  # Contains account ID
        }

        super().__init__(service_name, config, **kwargs)
        self.logger = logging.getLogger(
            f"{self.__class__.__module__}.{self.__class__.__name__}"
        )

    def _get_resource_identifier(self, resource: AWSResource) -> str:
        """
        Extract unique identifier from an SQS resource.

        Uses queue_name instead of ARN/URL.
        """
        # SQS Queues - use queue_name
        if hasattr(resource, "queue_name") and resource.queue_name:  # type: ignore[attr-defined]
            return str(resource.queue_name)  # type: ignore[attr-defined]

        # Fallback to parent implementation
        return super()._get_resource_identifier(resource)


class BedrockComparator(ResourceComparator):
    """
    Specialized comparator for Bedrock resources.

    Matches resources by model ID or other name-based identifiers.
    """

    def __init__(
        self,
        service_name: str = "bedrock",
        config: Optional[ComparisonConfig] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize the Bedrock comparator."""
        if config is None:
            config = ComparisonConfig()

        # Exclude ARN from comparison
        config.excluded_fields = config.excluded_fields | {
            "arn",
            "model_arn",
            "provisioned_model_arn",
        }

        super().__init__(service_name, config, **kwargs)
        self.logger = logging.getLogger(
            f"{self.__class__.__module__}.{self.__class__.__name__}"
        )

    def _get_resource_identifier(self, resource: AWSResource) -> str:
        """
        Extract unique identifier from a Bedrock resource.

        Uses model_id or model_name instead of ARN.
        """
        # Model ID
        if hasattr(resource, "model_id") and resource.model_id:  # type: ignore[attr-defined]
            return str(resource.model_id)  # type: ignore[attr-defined]

        # Model name
        if hasattr(resource, "model_name") and resource.model_name:  # type: ignore[attr-defined]
            return str(resource.model_name)  # type: ignore[attr-defined]

        # Provisioned model name
        if (
            hasattr(resource, "provisioned_model_name")
            and resource.provisioned_model_name
        ):  # type: ignore[attr-defined]
            return str(resource.provisioned_model_name)  # type: ignore[attr-defined]

        # Fallback to parent implementation
        return super()._get_resource_identifier(resource)


class ElasticBeanstalkComparator(ResourceComparator):
    """
    Specialized comparator for Elastic Beanstalk resources.

    Matches applications and environments by name instead of ARN.
    """

    def __init__(
        self,
        service_name: str = "elasticbeanstalk",
        config: Optional[ComparisonConfig] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize the Elastic Beanstalk comparator."""
        if config is None:
            config = ComparisonConfig()

        # Exclude ARN and account-specific fields
        config.excluded_fields = config.excluded_fields | {
            "arn",
            "application_arn",
            "environment_arn",
            "environment_id",  # Environment-specific ID
            "endpoint_url",  # Account/environment-specific
            "cname",  # Account/environment-specific
        }

        super().__init__(service_name, config, **kwargs)
        self.logger = logging.getLogger(
            f"{self.__class__.__module__}.{self.__class__.__name__}"
        )

    def _get_resource_identifier(self, resource: AWSResource) -> str:
        """
        Extract unique identifier from an Elastic Beanstalk resource.

        Uses application_name or environment_name instead of ARN.
        """
        # Environment - use application_name/environment_name
        if hasattr(resource, "environment_name") and hasattr(
            resource, "application_name"
        ):
            app_name = getattr(resource, "application_name", None)
            env_name = getattr(resource, "environment_name", None)
            if app_name and env_name:
                return f"{app_name}/{env_name}"

        # Application - use application_name
        if hasattr(resource, "application_name") and resource.application_name:  # type: ignore[attr-defined]
            return str(resource.application_name)  # type: ignore[attr-defined]

        # Fallback to parent implementation
        return super()._get_resource_identifier(resource)


class SNSComparator(ResourceComparator):
    """
    Specialized comparator for SNS resources.

    Matches topics by topic_name and subscriptions by
    topic_name + protocol + endpoint combination.
    """

    def __init__(
        self,
        service_name: str = "sns",
        config: Optional[ComparisonConfig] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize the SNS comparator."""
        if config is None:
            config = ComparisonConfig()

        # Exclude ARN and account-specific fields
        config.excluded_fields = config.excluded_fields | {
            "arn",
            "topic_arn",
            "subscription_arn",
            "owner",  # Account ID
            # Exclude subscription counts as they're dynamic
            "subscriptions_confirmed",
            "subscriptions_pending",
            "subscriptions_deleted",
        }

        super().__init__(service_name, config, **kwargs)
        self.logger = logging.getLogger(
            f"{self.__class__.__module__}.{self.__class__.__name__}"
        )

    def _get_resource_identifier(self, resource: AWSResource) -> str:
        """
        Extract unique identifier from an SNS resource.

        Uses topic_name for topics and topic_name:protocol:endpoint
        for subscriptions.
        """
        # SNS Topics - use topic_name
        if hasattr(resource, "topic_name") and not hasattr(
            resource, "subscription_arn"
        ):
            topic_name = getattr(resource, "topic_name", None)
            if topic_name:
                return str(topic_name)

        # SNS Subscriptions - use topic_name:protocol:endpoint
        if hasattr(resource, "subscription_arn") and hasattr(resource, "protocol"):
            topic_name = getattr(resource, "topic_name", "")
            protocol = getattr(resource, "protocol", "")
            endpoint = getattr(resource, "endpoint", "")
            if topic_name and protocol:
                return f"{topic_name}:{protocol}:{endpoint}"

        # Fallback to parent implementation
        return super()._get_resource_identifier(resource)
