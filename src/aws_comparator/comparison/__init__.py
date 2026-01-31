"""
Comparison engine for AWS resources.

This module provides the core comparison functionality for detecting
differences between AWS resources across accounts.

Classes:
    BaseComparator: Abstract base class for resource comparators.
    ResourceComparator: Generic comparator for any AWS resource type.
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
from aws_comparator.comparison.resource_comparator import ResourceComparator

__all__ = [
    "BaseComparator",
    "ComparisonConfig",
    "ResourceComparator",
    "SeverityConfig",
]
