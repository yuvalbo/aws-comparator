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
        service_name: str = "service-quotas",
        config: Optional[ComparisonConfig] = None,
        **kwargs: Any,
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
        config.excluded_fields = config.excluded_fields | {"arn"}

        super().__init__(service_name, config, **kwargs)
        self.logger = logging.getLogger(
            f"{self.__class__.__module__}.{self.__class__.__name__}"
        )

    def _get_resource_identifier(self, resource: AWSResource) -> str:
        """
        Extract unique identifier from a Service Quota resource.

        For Service Quotas, we use service_code/quota_code as the identifier
        instead of ARN, since ARNs contain account IDs which are always
        different between accounts. The identifier includes human-readable
        service and quota names for better usability.

        Args:
            resource: AWS resource (expected to be a ServiceQuota).

        Returns:
            Unique identifier string in format "service_code/quota_code (service_name - quota_name)".

        Example:
            >>> quota = ServiceQuota(service_code='ec2', quota_code='L-1234',
            ...                      service_name='Amazon EC2', quota_name='Running instances', ...)
            >>> identifier = comparator._get_resource_identifier(quota)
            >>> print(identifier)  # 'ec2/L-1234 (Amazon EC2 - Running instances)'
        """
        # For ServiceQuota objects, use service_code/quota_code with human-readable names
        if isinstance(resource, ServiceQuota):
            base_id = f"{resource.service_code}/{resource.quota_code}"
            return f"{base_id} ({resource.service_name} - {resource.quota_name})"

        # Check if resource has service_code and quota_code attributes
        if hasattr(resource, "service_code") and hasattr(resource, "quota_code"):
            service_code = getattr(resource, "service_code", None)
            quota_code = getattr(resource, "quota_code", None)
            if service_code and quota_code:
                base_id = f"{service_code}/{quota_code}"
                # Try to get human-readable names if available
                service_name = getattr(resource, "service_name", None)
                quota_name = getattr(resource, "quota_name", None)
                if service_name and quota_name:
                    return f"{base_id} ({service_name} - {quota_name})"
                return base_id

        # Fallback to parent implementation for non-quota resources
        return super()._get_resource_identifier(resource)
