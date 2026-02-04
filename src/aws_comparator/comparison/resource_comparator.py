"""
Generic resource comparator for AWS resources.

This module provides a concrete implementation of BaseComparator that can
compare any AWS resource type between two accounts using DeepDiff for
deep object comparison.
"""

import logging
import time
from typing import Any, Optional

from aws_comparator.comparison.base import BaseComparator, ComparisonConfig
from aws_comparator.models.common import AWSResource
from aws_comparator.models.comparison import (
    ChangeSeverity,
    ResourceChange,
    ResourceTypeComparison,
    ServiceComparisonResult,
)


class ResourceComparator(BaseComparator):
    """
    Generic comparator for AWS resources.

    This comparator can handle any AWS resource type by using DeepDiff
    for deep object comparison. It matches resources by identifier
    (ARN, ID, or name) and detects additions, removals, and modifications.

    The comparator provides:
    - Resource matching by identifier across accounts
    - Deep field-level comparison using DeepDiff
    - Configurable severity levels based on field patterns
    - Exclusion of transient fields (timestamps, request IDs)
    - Detailed change descriptions for reporting

    Attributes:
        service_name: Name of the AWS service being compared.
        config: Comparison configuration options.
        logger: Logger instance for this comparator.

    Example:
        >>> comparator = ResourceComparator('s3')
        >>> result = comparator.compare(
        ...     {'buckets': account1_buckets},
        ...     {'buckets': account2_buckets}
        ... )
        >>> print(f"Found {result.total_changes} changes")

    Unit Test Considerations:
        - Test with empty data (both accounts empty)
        - Test with None values in resource fields
        - Test resource matching by ARN vs name
        - Test deep nested object comparison
        - Test severity assignment for various field patterns
        - Test exclusion of transient fields
        - Mock DeepDiff for edge cases
    """

    def __init__(
        self,
        service_name: str,
        config: Optional[ComparisonConfig] = None,
        **kwargs: Any,
    ) -> None:
        """
        Initialize the resource comparator.

        Args:
            service_name: Name of the AWS service being compared.
            config: Comparison configuration options. If None, defaults are used.
            **kwargs: Additional configuration options.

        Example:
            >>> comparator = ResourceComparator('ec2')
            >>> comparator_with_config = ResourceComparator(
            ...     's3',
            ...     config=ComparisonConfig(ignore_order=False)
            ... )
        """
        super().__init__(service_name, config, **kwargs)
        self.logger = logging.getLogger(
            f"{self.__class__.__module__}.{self.__class__.__name__}"
        )

    def compare(
        self,
        account1_data: dict[str, list[AWSResource]],
        account2_data: dict[str, list[AWSResource]],
    ) -> ServiceComparisonResult:
        """
        Compare resources from two AWS accounts.

        This method iterates through all resource types, matches resources
        by identifier, and detects additions, removals, and modifications.
        For modified resources, it uses DeepDiff to show detailed field-level
        differences.

        Args:
            account1_data: Resources from first account, keyed by resource type.
                Example: {'buckets': [bucket1, bucket2], 'policies': [policy1]}
            account2_data: Resources from second account, keyed by resource type.
                Example: {'buckets': [bucket2, bucket3], 'policies': [policy1]}

        Returns:
            ServiceComparisonResult containing:
                - resource_comparisons: Dict mapping resource types to comparisons
                - service_name: Name of the service compared
                - execution_time_seconds: Time taken for comparison
                - errors: Any errors encountered during comparison

        Raises:
            ValueError: If account1_data or account2_data is None.

        Example:
            >>> account1 = {'instances': [inst1, inst2]}
            >>> account2 = {'instances': [inst2, inst3]}
            >>> result = comparator.compare(account1, account2)
            >>> for resource_type, comparison in result.resource_comparisons.items():
            ...     print(f"{resource_type}: +{len(comparison.added)} "
            ...           f"-{len(comparison.removed)} ~{len(comparison.modified)}")
        """
        start_time = time.time()
        errors: list[str] = []
        resource_comparisons: dict[str, ResourceTypeComparison] = {}

        # Validate inputs
        if account1_data is None or account2_data is None:
            raise ValueError("account1_data and account2_data cannot be None")

        # Get all resource types from both accounts
        all_resource_types = set(account1_data.keys()) | set(account2_data.keys())

        self.logger.info(
            f"Comparing {self.service_name} resources: {len(all_resource_types)} resource types"
        )

        for resource_type in all_resource_types:
            try:
                comparison = self._compare_resource_type(
                    resource_type=resource_type,
                    resources1=account1_data.get(resource_type, []),
                    resources2=account2_data.get(resource_type, []),
                )
                resource_comparisons[resource_type] = comparison

                self.logger.debug(
                    f"Compared {resource_type}: "
                    f"+{len(comparison.added)} -{len(comparison.removed)} "
                    f"~{len(comparison.modified)} ={comparison.unchanged_count}"
                )

            except Exception as e:
                error_msg = f"Error comparing {resource_type}: {e}"
                self.logger.error(error_msg, exc_info=True)
                errors.append(error_msg)

        execution_time = time.time() - start_time

        self.logger.info(
            f"Completed {self.service_name} comparison in {execution_time:.2f}s"
        )

        return ServiceComparisonResult(
            service_name=self.service_name,
            resource_comparisons=resource_comparisons,
            errors=errors,
            execution_time_seconds=execution_time,
        )

    def _compare_resource_type(
        self,
        resource_type: str,
        resources1: list[AWSResource],
        resources2: list[AWSResource],
    ) -> ResourceTypeComparison:
        """
        Compare resources of a single type between two accounts.

        This method creates identifier maps for fast lookup, then detects
        added, removed, and modified resources.

        Args:
            resource_type: Type of resource being compared (e.g., 'buckets').
            resources1: Resources from first account.
            resources2: Resources from second account.

        Returns:
            ResourceTypeComparison containing added, removed, modified lists.

        Example:
            >>> comparison = comparator._compare_resource_type(
            ...     'buckets',
            ...     account1_buckets,
            ...     account2_buckets
            ... )
        """
        # Create identifier maps for fast lookup
        resources1_map = self._build_resource_map(resources1)
        resources2_map = self._build_resource_map(resources2)

        ids1 = set(resources1_map.keys())
        ids2 = set(resources2_map.keys())

        # Find added, removed, and potentially modified resources
        added_ids = ids2 - ids1
        removed_ids = ids1 - ids2
        common_ids = ids1 & ids2

        # Build change lists
        added: list[ResourceChange] = []
        removed: list[ResourceChange] = []
        modified: list[ResourceChange] = []
        unchanged_count = 0

        # Process added resources
        for resource_id in added_ids:
            resource = resources2_map[resource_id]
            change = self._create_added_change(resource, resource_type)
            added.append(change)

        # Process removed resources
        for resource_id in removed_ids:
            resource = resources1_map[resource_id]
            change = self._create_removed_change(resource, resource_type)
            removed.append(change)

        # Process potentially modified resources
        for resource_id in common_ids:
            resource1 = resources1_map[resource_id]
            resource2 = resources2_map[resource_id]

            changes = self._compare_resources(
                resource1=resource1,
                resource2=resource2,
                resource_type=resource_type,
                resource_id=resource_id,
            )

            if changes:
                modified.extend(changes)
            else:
                unchanged_count += 1

        return ResourceTypeComparison(
            resource_type=resource_type,
            account1_count=len(resources1),
            account2_count=len(resources2),
            added=added,
            removed=removed,
            modified=modified,
            unchanged_count=unchanged_count,
        )

    def _build_resource_map(
        self, resources: list[AWSResource]
    ) -> dict[str, AWSResource]:
        """
        Build a map of resource identifier to resource for fast lookup.

        Args:
            resources: List of AWS resources.

        Returns:
            Dictionary mapping resource identifiers to resources.

        Example:
            >>> resource_map = comparator._build_resource_map(buckets)
            >>> bucket = resource_map['arn:aws:s3:::my-bucket']
        """
        resource_map: dict[str, AWSResource] = {}

        for resource in resources:
            try:
                identifier = self._get_resource_identifier(resource)
                if identifier in resource_map:
                    self.logger.warning(
                        f"Duplicate resource identifier: {identifier}. "
                        "Later resource will overwrite earlier one."
                    )
                resource_map[identifier] = resource
            except Exception as e:
                self.logger.warning(
                    f"Failed to get identifier for resource: {e}. Skipping."
                )

        return resource_map

    def _compare_resources(
        self,
        resource1: AWSResource,
        resource2: AWSResource,
        resource_type: str,
        resource_id: str,
    ) -> list[ResourceChange]:
        """
        Compare two resources and return list of changes.

        This method converts resources to dictionaries, performs deep
        comparison using DeepDiff, and extracts structured changes.

        Args:
            resource1: Resource from first account.
            resource2: Resource from second account.
            resource_type: Type of resource being compared.
            resource_id: Identifier of the resource.

        Returns:
            List of ResourceChange objects representing differences.
            Empty list if resources are identical.

        Example:
            >>> changes = comparator._compare_resources(
            ...     bucket1, bucket2, 'bucket', 'my-bucket'
            ... )
            >>> for change in changes:
            ...     print(f"{change.field_path}: {change.old_value} -> {change.new_value}")
        """
        # Convert to dictionaries for comparison
        data1 = self._resource_to_dict(resource1)
        data2 = self._resource_to_dict(resource2)

        # Perform deep comparison
        diff = self._perform_deep_diff(data1, data2)

        if not diff:
            return []

        # Extract changes from diff result
        changes = self._extract_changes_from_diff(
            diff=diff, resource_id=resource_id, resource_type=resource_type
        )

        return changes

    def compare_single_resource_type(
        self,
        resource_type: str,
        resources1: list[AWSResource],
        resources2: list[AWSResource],
    ) -> ResourceTypeComparison:
        """
        Compare a single resource type between two accounts.

        This is a convenience method for comparing just one resource type
        without creating a full ServiceComparisonResult.

        Args:
            resource_type: Type of resource being compared.
            resources1: Resources from first account.
            resources2: Resources from second account.

        Returns:
            ResourceTypeComparison for the specified resource type.

        Example:
            >>> comparison = comparator.compare_single_resource_type(
            ...     'buckets',
            ...     account1_buckets,
            ...     account2_buckets
            ... )
            >>> print(f"Changes: {comparison.total_changes}")
        """
        return self._compare_resource_type(resource_type, resources1, resources2)

    def get_highest_severity(
        self, changes: list[ResourceChange]
    ) -> Optional[ChangeSeverity]:
        """
        Get the highest severity level from a list of changes.

        This is useful for determining the overall impact of a set of changes.

        Args:
            changes: List of ResourceChange objects.

        Returns:
            Highest ChangeSeverity in the list, or None if list is empty.

        Example:
            >>> highest = comparator.get_highest_severity(comparison.modified)
            >>> if highest == ChangeSeverity.CRITICAL:
            ...     print("Critical changes detected!")
        """
        if not changes:
            return None

        severity_order = {
            ChangeSeverity.INFO: 0,
            ChangeSeverity.LOW: 1,
            ChangeSeverity.MEDIUM: 2,
            ChangeSeverity.HIGH: 3,
            ChangeSeverity.CRITICAL: 4,
        }

        highest_level = 0
        highest_severity = ChangeSeverity.INFO

        for change in changes:
            level = severity_order.get(change.severity, 0)
            if level > highest_level:
                highest_level = level
                highest_severity = change.severity

        return highest_severity

    def filter_by_severity(
        self,
        changes: list[ResourceChange],
        min_severity: ChangeSeverity = ChangeSeverity.INFO,
    ) -> list[ResourceChange]:
        """
        Filter changes by minimum severity level.

        Args:
            changes: List of ResourceChange objects.
            min_severity: Minimum severity level to include.

        Returns:
            List of changes at or above the specified severity.

        Example:
            >>> critical_changes = comparator.filter_by_severity(
            ...     all_changes,
            ...     min_severity=ChangeSeverity.CRITICAL
            ... )
        """
        severity_order = {
            ChangeSeverity.INFO: 0,
            ChangeSeverity.LOW: 1,
            ChangeSeverity.MEDIUM: 2,
            ChangeSeverity.HIGH: 3,
            ChangeSeverity.CRITICAL: 4,
        }

        min_level = severity_order.get(min_severity, 0)

        return [
            change
            for change in changes
            if severity_order.get(change.severity, 0) >= min_level
        ]
