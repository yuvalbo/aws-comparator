"""
Service Quotas specific comparator.

This module provides a specialized comparator for AWS Service Quotas that
matches quotas by service_code/quota_code instead of ARN (since ARNs contain
account IDs which are always different between accounts).
"""

import logging
from typing import Any, Optional

from aws_comparator.comparison.base import ComparisonConfig
from aws_comparator.comparison.resource_comparator import ResourceComparator
from aws_comparator.models.common import AWSResource
from aws_comparator.models.servicequotas import ServiceQuota


class ServiceQuotasComparator(ResourceComparator):
    """
    Specialized comparator for Service Quotas.

    This comparator overrides the default identifier logic to use
    service_code/quota_code instead of ARN for matching quotas between
    accounts. ARNs contain account IDs, which are always different,
    making ARN-based matching useless for cross-account comparison.

    Example:
        >>> comparator = ServiceQuotasComparator('service-quotas')
        >>> result = comparator.compare(account1_data, account2_data)
    """

    def __init__(
        self,
        service_name: str = 'service-quotas',
        config: Optional[ComparisonConfig] = None,
        **kwargs: Any
    ) -> None:
        """
        Initialize the Service Quotas comparator.

        Args:
            service_name: Name of the service (default: 'service-quotas').
            config: Comparison configuration options.
            **kwargs: Additional configuration options.
        """
        # Create config with ARN excluded if not provided
        if config is None:
            config = ComparisonConfig()

        # Add 'arn' to excluded fields since ARNs contain account IDs
        # which are always different between accounts
        config.excluded_fields = config.excluded_fields | {'arn'}

        super().__init__(service_name, config, **kwargs)
        self.logger = logging.getLogger(
            f"{self.__class__.__module__}.{self.__class__.__name__}"
        )

    def _get_resource_identifier(self, resource: AWSResource) -> str:
        """
        Extract unique identifier from a Service Quota resource.

        For Service Quotas, we use service_code/quota_code as the identifier
        instead of ARN, since ARNs contain account IDs which are always
        different between accounts.

        Args:
            resource: AWS resource (expected to be a ServiceQuota).

        Returns:
            Unique identifier string in format "service_code/quota_code".

        Example:
            >>> quota = ServiceQuota(service_code='ec2', quota_code='L-1234', ...)
            >>> identifier = comparator._get_resource_identifier(quota)
            >>> print(identifier)  # 'ec2/L-1234'
        """
        # For ServiceQuota objects, use service_code/quota_code
        if isinstance(resource, ServiceQuota):
            return f"{resource.service_code}/{resource.quota_code}"

        # Check if resource has service_code and quota_code attributes
        if hasattr(resource, 'service_code') and hasattr(resource, 'quota_code'):
            service_code = resource.service_code  # type: ignore[attr-defined]
            quota_code = resource.quota_code  # type: ignore[attr-defined]
            if service_code and quota_code:
                return f"{service_code}/{quota_code}"

        # Fallback to parent implementation for non-quota resources
        return super()._get_resource_identifier(resource)
