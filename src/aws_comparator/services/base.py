"""
Base class for all AWS service fetchers.

This module defines the abstract base class that all service-specific
fetchers must implement, ensuring a consistent interface across services.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Callable, Optional

import boto3
from botocore.exceptions import ClientError, NoCredentialsError

from aws_comparator.core.exceptions import (
    DataFetchError,
    InsufficientPermissionsError,
    ServiceThrottlingError,
)
from aws_comparator.models.common import AWSResource


class BaseServiceFetcher(ABC):
    """
    Abstract base class for all AWS service fetchers.

    This class enforces a consistent interface across all service fetchers,
    provides common utility methods for pagination and error handling,
    and ensures proper session management.

    Subclasses must implement:
    - _create_client(): Create the appropriate boto3 client
    - fetch_resources(): Fetch all resources for the service
    - get_resource_types(): Return list of resource types handled

    Example:
        >>> class EC2Fetcher(BaseServiceFetcher):
        ...     SERVICE_NAME = 'ec2'
        ...
        ...     def _create_client(self):
        ...         return self.session.client('ec2', region_name=self.region)
        ...
        ...     def fetch_resources(self) -> dict[str, list[AWSResource]]:
        ...         return {
        ...             'instances': self._fetch_instances(),
        ...             'security_groups': self._fetch_security_groups(),
        ...         }
    """

    # Service name should be overridden in subclasses
    SERVICE_NAME: str = "unknown"

    def __init__(self, session: boto3.Session, region: str) -> None:
        """
        Initialize the service fetcher.

        Args:
            session: Boto3 session with appropriate credentials
            region: AWS region to fetch resources from
        """
        self.session = session
        self.region = region
        self.logger = logging.getLogger(
            f"{self.__class__.__module__}.{self.__class__.__name__}"
        )
        self.client: Optional[Any] = None

        # Initialize the client
        try:
            self.client = self._create_client()
            self.logger.debug(
                f"Initialized {self.SERVICE_NAME} fetcher for region {region}"
            )
        except NoCredentialsError as e:
            self.logger.error(f"No credentials available: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Failed to create client: {e}")
            raise

    @abstractmethod
    def _create_client(self) -> Any:
        """
        Create and return the boto3 client for this service.

        This method must be implemented by subclasses to create the
        appropriate boto3 client for their service.

        Returns:
            Boto3 client instance

        Example:
            >>> def _create_client(self):
            ...     return self.session.client('ec2', region_name=self.region)
        """
        pass

    @abstractmethod
    def fetch_resources(self) -> dict[str, list[AWSResource]]:
        """
        Fetch all resources for this service.

        This is the main entry point for resource fetching. It should
        return a dictionary mapping resource types to lists of resources.

        Returns:
            Dictionary mapping resource types to lists of AWSResource objects

        Example:
            >>> {
            ...     'instances': [EC2Instance(...), EC2Instance(...)],
            ...     'security_groups': [SecurityGroup(...), ...]
            ... }
        """
        pass

    @abstractmethod
    def get_resource_types(self) -> list[str]:
        """
        Return list of resource types this fetcher handles.

        Returns:
            List of resource type names

        Example:
            >>> ['instances', 'security_groups', 'vpcs', 'subnets']
        """
        pass

    def _paginate(
        self, operation_name: str, result_key: Optional[str] = None, **kwargs: Any
    ) -> list[dict[str, Any]]:
        """
        Generic pagination helper for AWS API calls.

        This method handles pagination automatically using boto3's paginators,
        collecting all pages of results.

        Args:
            operation_name: Name of the client operation (e.g., 'describe_instances')
            result_key: Key in response containing results (auto-detected if None)
            **kwargs: Additional parameters to pass to the operation

        Returns:
            List of all results across all pages

        Raises:
            DataFetchError: If fetching fails
            ServiceThrottlingError: If AWS throttles the request
            InsufficientPermissionsError: If permission is denied

        Example:
            >>> instances = self._paginate('describe_instances', 'Reservations')
        """
        if not self.client:
            raise DataFetchError(
                self.SERVICE_NAME, operation_name, "Client not initialized"
            )

        try:
            # Check if paginator is available
            if self.client.can_paginate(operation_name):
                paginator = self.client.get_paginator(operation_name)
                results: list[dict[str, Any]] = []

                self.logger.debug(f"Paginating {operation_name} with params: {kwargs}")

                for page in paginator.paginate(**kwargs):
                    # Auto-detect result key if not provided
                    if result_key is None:
                        # Find the first key that contains a list
                        for key, value in page.items():
                            if isinstance(value, list) and key not in [
                                "ResponseMetadata",
                                "NextToken",
                                "Marker",
                            ]:
                                result_key = key
                                break

                    if result_key and result_key in page:
                        results.extend(page[result_key])
                    elif not result_key:
                        # If we still don't have a result key, return the whole page
                        results.append(page)

                self.logger.debug(
                    f"Paginated {operation_name}: {len(results)} items across multiple pages"
                )
                return results

            else:
                # No paginator available, make single request
                operation = getattr(self.client, operation_name)
                response = operation(**kwargs)

                if result_key and result_key in response:
                    return response[result_key]
                return [response]

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")

            if error_code in ["AccessDenied", "UnauthorizedOperation"]:
                raise InsufficientPermissionsError(
                    self.SERVICE_NAME,
                    operation_name,
                    f"{self.SERVICE_NAME}:{operation_name}",
                ) from e
            elif error_code in [
                "Throttling",
                "RequestLimitExceeded",
                "TooManyRequestsException",
            ]:
                raise ServiceThrottlingError(self.SERVICE_NAME, operation_name) from e
            else:
                raise DataFetchError(
                    self.SERVICE_NAME, operation_name, f"{error_code}: {e}"
                ) from e

        except Exception as e:
            raise DataFetchError(self.SERVICE_NAME, operation_name, str(e)) from e

    def _normalize_tags(self, tags: Optional[list[dict[str, str]]]) -> dict[str, str]:
        """
        Normalize AWS tags to consistent dictionary format.

        AWS APIs return tags in various formats. This method converts them
        to a consistent dictionary format for easier comparison.

        Args:
            tags: List of tag dictionaries from AWS API (may be None)

        Returns:
            Dictionary mapping tag keys to values

        Example:
            >>> tags = [{'Key': 'Environment', 'Value': 'prod'}]
            >>> self._normalize_tags(tags)
            {'Environment': 'prod'}
        """
        if not tags:
            return {}

        normalized: dict[str, str] = {}
        for tag in tags:
            # Handle both 'Key'/'Value' and 'key'/'value' formats
            key = tag.get("Key") or tag.get("key", "")
            value = tag.get("Value") or tag.get("value", "")

            if key:
                normalized[key] = value

        return normalized

    def _safe_fetch(
        self, resource_type: str, fetch_func: Callable[[], list[Any]]
    ) -> list[AWSResource]:
        """
        Safely execute a fetch function with error handling.

        This wrapper handles common errors and ensures that failures in
        fetching one resource type don't stop the entire comparison.

        Args:
            resource_type: Name of the resource type being fetched
            fetch_func: Function to call to fetch resources

        Returns:
            List of fetched resources, or empty list if error occurs
        """
        try:
            self.logger.info(f"Fetching {resource_type} for {self.SERVICE_NAME}")
            resources = fetch_func()
            self.logger.info(f"Fetched {len(resources)} {resource_type}")
            return resources
        except InsufficientPermissionsError as e:
            self.logger.warning(f"Permission denied for {resource_type}: {e.message}")
            return []
        except ServiceThrottlingError as e:
            self.logger.warning(
                f"Throttled while fetching {resource_type}: {e.message}"
            )
            return []
        except DataFetchError as e:
            self.logger.error(f"Failed to fetch {resource_type}: {e.message}")
            return []
        except Exception as e:
            self.logger.error(
                f"Unexpected error fetching {resource_type}: {e}", exc_info=True
            )
            return []

    def __str__(self) -> str:
        """Return string representation of fetcher."""
        return (
            f"{self.__class__.__name__}"
            f"(service={self.SERVICE_NAME}, region={self.region})"
        )

    def __repr__(self) -> str:
        """Return detailed representation for debugging."""
        return (
            f"{self.__class__.__name__}("
            f"SERVICE_NAME={self.SERVICE_NAME!r}, "
            f"region={self.region!r}, "
            f"client_initialized={self.client is not None})"
        )
