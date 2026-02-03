"""
Comparison engine for AWS resources.

This module provides the core comparison functionality for detecting
differences between AWS resources across accounts.

Classes:
    BaseComparator: Abstract base class for resource comparators.
    ResourceComparator: Generic comparator for any AWS resource type.
    ServiceQuotasComparator: Specialized comparator for Service Quotas.
    CloudWatchComparator: Comparator for CloudWatch alarms, log groups, dashboards.
    EventBridgeComparator: Comparator for EventBridge rules and buses.
    SecretsManagerComparator: Comparator for Secrets Manager secrets.
    LambdaComparator: Comparator for Lambda functions and layers.
    S3Comparator: Comparator for S3 buckets.
    EC2Comparator: Comparator for EC2 instances, security groups, VPCs, etc.
    SQSComparator: Comparator for SQS queues.
    BedrockComparator: Comparator for Bedrock resources.
    ElasticBeanstalkComparator: Comparator for Elastic Beanstalk applications/environments.
    ComparisonConfig: Configuration options for comparison behavior.
    SeverityConfig: Configuration for severity level assignment.

Example:
    >>> from aws_comparator.comparison import ResourceComparator
    >>> comparator = ResourceComparator('s3')
    >>> result = comparator.compare(account1_data, account2_data)
"""

from aws_comparator.comparison.base import (
    BaseComparator,
    ComparisonConfig,
    SeverityConfig,
)
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
from aws_comparator.comparison.resource_comparator import ResourceComparator
from aws_comparator.comparison.servicequotas_comparator import ServiceQuotasComparator

__all__ = [
    "BaseComparator",
    "BedrockComparator",
    "CloudWatchComparator",
    "ComparisonConfig",
    "EC2Comparator",
    "ElasticBeanstalkComparator",
    "EventBridgeComparator",
    "LambdaComparator",
    "ResourceComparator",
    "S3Comparator",
    "SecretsManagerComparator",
    "ServiceQuotasComparator",
    "SeverityConfig",
    "SNSComparator",
    "SQSComparator",
]
