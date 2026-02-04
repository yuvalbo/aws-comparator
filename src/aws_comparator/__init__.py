"""
AWS Account Comparator - Compare AWS resources across accounts.

This package provides tools to compare AWS resources between two accounts
and generate detailed diff reports.
"""

__version__ = "0.1.0"
__author__ = "AWS Comparator Team"

from aws_comparator.core.config import AccountConfig, ComparisonConfig
from aws_comparator.core.exceptions import AWSComparatorError

__all__ = [
    "__version__",
    "ComparisonConfig",
    "AccountConfig",
    "AWSComparatorError",
]
