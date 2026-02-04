"""
Base class for comparison engines.

This module defines the abstract base class for implementing comparison
logic between AWS resources from different accounts. It provides core
functionality for deep object comparison using DeepDiff.
"""

import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from re import Pattern
from typing import Any, Optional

from deepdiff import DeepDiff

from aws_comparator.models.common import AWSResource
from aws_comparator.models.comparison import (
    ChangeSeverity,
    ChangeType,
    ResourceChange,
    ServiceComparisonResult,
)


@dataclass
class SeverityConfig:
    """
    Configuration for severity level assignment based on field patterns.

    This class defines patterns for categorizing changes into severity levels.
    Patterns are matched against field paths in a case-insensitive manner.

    Attributes:
        critical_patterns: Patterns indicating security-impacting changes.
        high_patterns: Patterns indicating functionality-affecting changes.
        medium_patterns: Patterns indicating behavior/performance changes.
        low_patterns: Patterns indicating metadata changes with minimal impact.
        info_patterns: Patterns indicating informational changes only.

    Example:
        >>> config = SeverityConfig()
        >>> # Use default patterns
        >>> custom_config = SeverityConfig(
        ...     critical_patterns=frozenset(['security', 'encryption', 'policy'])
        ... )
    """

    critical_patterns: frozenset[str] = field(
        default_factory=lambda: frozenset(
            [
                "security",
                "securitygroup",
                "encryption",
                "encrypted",
                "policy",
                "policies",
                "iam",
                "kms",
                "public_access",
                "publicaccess",
                "acl",
                "principal",
                "permission",
                "role",
                "credential",
                "secret",
                "password",
                "auth",
                "ssl",
                "tls",
                "certificate",
                "firewall",
                "vpce",
                "endpoint",
                "network_policy",
            ]
        )
    )

    high_patterns: frozenset[str] = field(
        default_factory=lambda: frozenset(
            [
                "configuration",
                "config",
                "settings",
                "enabled",
                "disabled",
                "size",
                "type",
                "status",
                "state",
                "instance_type",
                "instancetype",
                "storage",
                "volume",
                "backup",
                "snapshot",
                "replication",
                "availability",
                "multi_az",
                "multiaz",
                "engine",
                "version",
                "class",
                "tier",
            ]
        )
    )

    medium_patterns: frozenset[str] = field(
        default_factory=lambda: frozenset(
            [
                "lifecycle",
                "retention",
                "logging",
                "monitoring",
                "versioning",
                "notification",
                "alarm",
                "metric",
                "throughput",
                "iops",
                "bandwidth",
                "timeout",
                "cooldown",
                "scaling",
                "capacity",
                "limit",
                "quota",
            ]
        )
    )

    low_patterns: frozenset[str] = field(
        default_factory=lambda: frozenset(
            [
                "name",
                "description",
                "metadata",
                "label",
                "comment",
                "note",
                "displayname",
                "display_name",
                "alias",
            ]
        )
    )

    info_patterns: frozenset[str] = field(
        default_factory=lambda: frozenset(
            [
                "tags",
                "tag",
                "last_modified",
                "lastmodified",
                "created",
                "updated",
                "modified_date",
                "update_time",
                "create_time",
            ]
        )
    )


@dataclass
class ComparisonConfig:
    """
    Configuration options for resource comparison.

    This class provides configuration for controlling comparison behavior,
    including field exclusions, severity mappings, and comparison options.

    Attributes:
        excluded_fields: Fields to exclude from comparison (e.g., transient data).
        excluded_patterns: Regex patterns for fields to exclude.
        severity_config: Configuration for severity level assignment.
        ignore_order: Whether to ignore order in list comparisons.
        significant_digits: Decimal places for float comparison (None = exact).
        case_sensitive: Whether string comparisons are case-sensitive.
        report_repetition: Whether to report repeated values in iterables.

    Example:
        >>> config = ComparisonConfig(
        ...     excluded_fields={'request_id', 'response_metadata'},
        ...     ignore_order=True
        ... )
    """

    excluded_fields: set[str] = field(
        default_factory=lambda: {
            "request_id",
            "response_metadata",
            "ResponseMetadata",
            "RequestId",
            "HTTPStatusCode",
            "HTTPHeaders",
            "RetryAttempts",
            "request_metadata",
        }
    )

    excluded_patterns: list[str] = field(
        default_factory=lambda: [
            r".*timestamp.*",
            r".*_at$",
            r".*_time$",
            r".*etag.*",
            r".*request_id.*",
        ]
    )

    severity_config: SeverityConfig = field(default_factory=SeverityConfig)

    ignore_order: bool = True
    significant_digits: Optional[int] = None
    case_sensitive: bool = True
    report_repetition: bool = False


class BaseComparator(ABC):
    """
    Abstract base class for resource comparators.

    This class defines the interface and provides common functionality for
    comparing AWS resources between two accounts and generating structured
    comparison results. It uses DeepDiff for deep object comparison.

    Subclasses must implement the compare() method with service-specific
    comparison logic, but can leverage the helper methods provided here.

    Attributes:
        service_name: Name of the AWS service being compared.
        config: Comparison configuration options.
        logger: Logger instance for this comparator.

    Example:
        >>> class S3Comparator(BaseComparator):
        ...     def compare(self, account1_data, account2_data):
        ...         # Implementation using helper methods
        ...         pass
        >>> comparator = S3Comparator('s3')
        >>> result = comparator.compare(account1_data, account2_data)
    """

    def __init__(
        self,
        service_name: str,
        config: Optional[ComparisonConfig] = None,
        **kwargs: Any,
    ) -> None:
        """
        Initialize the comparator.

        Args:
            service_name: Name of the AWS service being compared.
            config: Comparison configuration options. If None, defaults are used.
            **kwargs: Additional configuration options (merged into config).

        Example:
            >>> comparator = BaseComparator('ec2', ignore_order=True)
        """
        self.service_name = service_name
        self.config = config or ComparisonConfig()
        self._kwargs = kwargs
        self.logger = logging.getLogger(
            f"{self.__class__.__module__}.{self.__class__.__name__}"
        )

        # Compile exclusion patterns for performance
        self._compiled_patterns: list[Pattern[str]] = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in self.config.excluded_patterns
        ]

    @abstractmethod
    def compare(
        self,
        account1_data: dict[str, list[AWSResource]],
        account2_data: dict[str, list[AWSResource]],
    ) -> ServiceComparisonResult:
        """
        Compare resources from two accounts.

        This method should analyze the differences between resources from
        two accounts and return a structured comparison result.

        Args:
            account1_data: Resources from first account, keyed by resource type.
            account2_data: Resources from second account, keyed by resource type.

        Returns:
            ServiceComparisonResult containing all detected differences.

        Raises:
            ValueError: If input data is invalid.

        Example:
            >>> account1_data = {'instances': [instance1, instance2]}
            >>> account2_data = {'instances': [instance2, instance3]}
            >>> result = comparator.compare(account1_data, account2_data)
            >>> print(f"Found {result.total_changes} changes")
        """
        pass

    def _get_resource_identifier(self, resource: AWSResource) -> str:
        """
        Extract unique identifier from a resource.

        This method attempts to find the best identifier for a resource,
        preferring ARN, then id, then name, and finally falling back to
        object identity.

        Can be overridden by subclasses for custom identification logic.

        Args:
            resource: AWS resource to identify.

        Returns:
            Unique identifier string for the resource.

        Example:
            >>> resource = S3Bucket(arn='arn:aws:s3:::my-bucket')
            >>> identifier = comparator._get_resource_identifier(resource)
            >>> print(identifier)  # 'arn:aws:s3:::my-bucket'
        """
        # Try ARN first (most unique)
        if hasattr(resource, "arn") and resource.arn:
            return str(resource.arn)

        # Try common identifier fields
        for field_name in ["id", "resource_id", "name", "bucket_name", "instance_id"]:
            if hasattr(resource, field_name):
                value = getattr(resource, field_name)
                if value:
                    return str(value)

        # Last resort: use model dump hash or object id
        try:
            # Use a hash of the serialized data
            data = resource.model_dump()
            # Remove transient fields for consistent identification
            for excluded_field in self.config.excluded_fields:
                data.pop(excluded_field, None)
            return str(hash(frozenset(str(v) for v in data.values() if v)))
        except Exception:
            return str(id(resource))

    def _resource_to_dict(
        self, resource: AWSResource, exclude_transient: bool = True
    ) -> dict[str, Any]:
        """
        Convert an AWS resource to a dictionary for comparison.

        This method serializes the resource and optionally removes
        transient fields that should not affect comparison results.

        Args:
            resource: AWS resource to convert.
            exclude_transient: Whether to exclude transient fields.

        Returns:
            Dictionary representation of the resource.

        Example:
            >>> resource = S3Bucket(name='my-bucket', region='us-east-1')
            >>> data = comparator._resource_to_dict(resource)
        """
        try:
            data = resource.model_dump()
        except AttributeError:
            # Fallback for non-Pydantic objects
            data = dict(resource) if hasattr(resource, "__iter__") else {}

        if exclude_transient:
            data = self._exclude_transient_fields(data)

        return data

    def _exclude_transient_fields(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Remove transient fields from a dictionary.

        This method recursively removes fields that should not be
        considered in comparisons (timestamps, request IDs, etc.).

        Args:
            data: Dictionary to process.

        Returns:
            Dictionary with transient fields removed.
        """
        result: dict[str, Any] = {}

        for key, value in data.items():
            # Skip explicitly excluded fields
            if key in self.config.excluded_fields:
                continue

            # Skip fields matching exclusion patterns
            if any(pattern.match(key) for pattern in self._compiled_patterns):
                continue

            # Recursively process nested dictionaries
            if isinstance(value, dict):
                nested = self._exclude_transient_fields(value)
                if nested:  # Only include non-empty dicts
                    result[key] = nested
            # Process lists of dictionaries
            elif isinstance(value, list):
                processed_list = []
                for item in value:
                    if isinstance(item, dict):
                        processed_item = self._exclude_transient_fields(item)
                        if processed_item:
                            processed_list.append(processed_item)
                    else:
                        processed_list.append(item)
                result[key] = processed_list
            else:
                result[key] = value

        return result

    def _perform_deep_diff(
        self, old_data: dict[str, Any], new_data: dict[str, Any]
    ) -> DeepDiff:
        """
        Perform deep comparison between two dictionaries using DeepDiff.

        This method wraps DeepDiff with configuration from this comparator.

        Args:
            old_data: Original data (from account1).
            new_data: New data (from account2).

        Returns:
            DeepDiff result containing all detected differences.

        Example:
            >>> diff = comparator._perform_deep_diff(old_bucket, new_bucket)
            >>> if diff:
            ...     print("Changes detected")
        """
        return DeepDiff(
            old_data,
            new_data,
            ignore_order=self.config.ignore_order,
            significant_digits=self.config.significant_digits,
            report_repetition=self.config.report_repetition,
            exclude_paths=self.config.excluded_fields,
            verbose_level=2,  # Include old and new values
        )

    def _normalize_field_path(self, deepdiff_path: str) -> str:
        """
        Convert DeepDiff field path to a user-friendly format.

        DeepDiff returns paths like: root['field']['nested'][0]['item']
        This method converts them to: field.nested[0].item

        Args:
            deepdiff_path: Field path from DeepDiff.

        Returns:
            Normalized, user-friendly field path.

        Example:
            >>> path = "root['security_groups'][0]['group_id']"
            >>> normalized = comparator._normalize_field_path(path)
            >>> print(normalized)  # 'security_groups[0].group_id'
        """
        if not deepdiff_path:
            return ""

        # Remove 'root' prefix
        path = deepdiff_path.replace("root", "")

        # Convert ['field'] to .field
        # Handle array indices separately to preserve them
        result_parts: list[str] = []

        # Pattern to match ['key'] or [index]
        pattern = re.compile(r"\['([^']+)'\]|\[(\d+)\]")

        for match in pattern.finditer(path):
            # Get the matched group (either string key or numeric index)
            if match.group(1):  # String key: ['field']
                if result_parts:
                    result_parts.append(".")
                result_parts.append(match.group(1))
            else:  # Numeric index: [0]
                result_parts.append(f"[{match.group(2)}]")

        return "".join(result_parts)

    def _determine_severity(self, field_path: str) -> ChangeSeverity:
        """
        Determine the severity level of a change based on the field path.

        This method matches the field path against configured severity
        patterns to assign an appropriate severity level.

        Args:
            field_path: Normalized field path of the changed field.

        Returns:
            Appropriate ChangeSeverity level for the change.

        Example:
            >>> severity = comparator._determine_severity('security_groups[0].group_id')
            >>> print(severity)  # ChangeSeverity.CRITICAL
        """
        if not field_path:
            return ChangeSeverity.INFO

        # Normalize for pattern matching
        path_lower = field_path.lower().replace("_", "").replace("-", "")
        severity_config = self.config.severity_config

        # Check patterns in order of severity (highest first)
        for pattern in severity_config.critical_patterns:
            normalized_pattern = pattern.lower().replace("_", "").replace("-", "")
            if normalized_pattern in path_lower:
                return ChangeSeverity.CRITICAL

        for pattern in severity_config.high_patterns:
            normalized_pattern = pattern.lower().replace("_", "").replace("-", "")
            if normalized_pattern in path_lower:
                return ChangeSeverity.HIGH

        for pattern in severity_config.medium_patterns:
            normalized_pattern = pattern.lower().replace("_", "").replace("-", "")
            if normalized_pattern in path_lower:
                return ChangeSeverity.MEDIUM

        for pattern in severity_config.low_patterns:
            normalized_pattern = pattern.lower().replace("_", "").replace("-", "")
            if normalized_pattern in path_lower:
                return ChangeSeverity.LOW

        for pattern in severity_config.info_patterns:
            normalized_pattern = pattern.lower().replace("_", "").replace("-", "")
            if normalized_pattern in path_lower:
                return ChangeSeverity.INFO

        # Default to MEDIUM for unknown fields
        return ChangeSeverity.MEDIUM

    def _extract_changes_from_diff(
        self, diff: DeepDiff, resource_id: str, resource_type: str
    ) -> list[ResourceChange]:
        """
        Extract ResourceChange objects from a DeepDiff result.

        This method processes DeepDiff output and creates structured
        ResourceChange objects for each detected difference.

        Args:
            diff: DeepDiff result containing detected differences.
            resource_id: Identifier of the resource being compared.
            resource_type: Type of the resource being compared.

        Returns:
            List of ResourceChange objects representing all differences.

        Example:
            >>> diff = comparator._perform_deep_diff(old_data, new_data)
            >>> changes = comparator._extract_changes_from_diff(
            ...     diff, 'my-bucket', 'bucket'
            ... )
        """
        changes: list[ResourceChange] = []

        if not diff:
            return changes

        # Process value changes
        values_changed = diff.get("values_changed", {})
        for path, change_info in values_changed.items():
            field_path = self._normalize_field_path(path)
            old_value = change_info.get("old_value")
            new_value = change_info.get("new_value")
            severity = self._determine_severity(field_path)

            changes.append(
                ResourceChange(
                    change_type=ChangeType.MODIFIED,
                    resource_id=resource_id,
                    resource_type=resource_type,
                    field_path=field_path,
                    old_value=old_value,
                    new_value=new_value,
                    severity=severity,
                    description=f"Value changed from '{old_value}' to '{new_value}'",
                )
            )

        # Process type changes
        type_changes = diff.get("type_changes", {})
        for path, change_info in type_changes.items():
            field_path = self._normalize_field_path(path)
            old_value = change_info.get("old_value")
            new_value = change_info.get("new_value")
            severity = self._determine_severity(field_path)

            changes.append(
                ResourceChange(
                    change_type=ChangeType.MODIFIED,
                    resource_id=resource_id,
                    resource_type=resource_type,
                    field_path=field_path,
                    old_value=old_value,
                    new_value=new_value,
                    severity=severity,
                    description=f"Type changed from {type(old_value).__name__} to {type(new_value).__name__}",
                )
            )

        # Process dictionary items added
        dict_items_added = diff.get("dictionary_item_added", {})
        if isinstance(dict_items_added, set):
            dict_items_added = dict.fromkeys(dict_items_added, None)
        for path in dict_items_added:
            field_path = self._normalize_field_path(path)
            severity = self._determine_severity(field_path)

            # Try to get the new value from the diff
            new_value = dict_items_added.get(path)
            if new_value is None:
                # DeepDiff sometimes returns a set of paths
                new_value = diff.get("new_value")

            changes.append(
                ResourceChange(
                    change_type=ChangeType.MODIFIED,
                    resource_id=resource_id,
                    resource_type=resource_type,
                    field_path=field_path,
                    old_value=None,
                    new_value=new_value,
                    severity=severity,
                    description=f"Field '{field_path}' exists only in Account 2",
                )
            )

        # Process dictionary items removed
        dict_items_removed = diff.get("dictionary_item_removed", {})
        if isinstance(dict_items_removed, set):
            dict_items_removed = dict.fromkeys(dict_items_removed, None)
        for path in dict_items_removed:
            field_path = self._normalize_field_path(path)
            severity = self._determine_severity(field_path)

            old_value = dict_items_removed.get(path)

            changes.append(
                ResourceChange(
                    change_type=ChangeType.MODIFIED,
                    resource_id=resource_id,
                    resource_type=resource_type,
                    field_path=field_path,
                    old_value=old_value,
                    new_value=None,
                    severity=severity,
                    description=f"Field '{field_path}' exists only in Account 1",
                )
            )

        # Process iterable items added
        iterable_added = diff.get("iterable_item_added", {})
        for path, value in iterable_added.items():
            field_path = self._normalize_field_path(path)
            severity = self._determine_severity(field_path)

            changes.append(
                ResourceChange(
                    change_type=ChangeType.MODIFIED,
                    resource_id=resource_id,
                    resource_type=resource_type,
                    field_path=field_path,
                    old_value=None,
                    new_value=value,
                    severity=severity,
                    description=f"Item added to '{field_path}'",
                )
            )

        # Process iterable items removed
        iterable_removed = diff.get("iterable_item_removed", {})
        for path, value in iterable_removed.items():
            field_path = self._normalize_field_path(path)
            severity = self._determine_severity(field_path)

            changes.append(
                ResourceChange(
                    change_type=ChangeType.MODIFIED,
                    resource_id=resource_id,
                    resource_type=resource_type,
                    field_path=field_path,
                    old_value=value,
                    new_value=None,
                    severity=severity,
                    description=f"Item removed from '{field_path}'",
                )
            )

        # Process set items added
        set_added = diff.get("set_item_added", set())
        for item in set_added:
            changes.append(
                ResourceChange(
                    change_type=ChangeType.MODIFIED,
                    resource_id=resource_id,
                    resource_type=resource_type,
                    field_path="(set)",
                    old_value=None,
                    new_value=item,
                    severity=ChangeSeverity.MEDIUM,
                    description=f"Set item added: {item}",
                )
            )

        # Process set items removed
        set_removed = diff.get("set_item_removed", set())
        for item in set_removed:
            changes.append(
                ResourceChange(
                    change_type=ChangeType.MODIFIED,
                    resource_id=resource_id,
                    resource_type=resource_type,
                    field_path="(set)",
                    old_value=item,
                    new_value=None,
                    severity=ChangeSeverity.MEDIUM,
                    description=f"Set item removed: {item}",
                )
            )

        return changes

    def _create_added_change(
        self,
        resource: AWSResource,
        resource_type: str,
        severity: ChangeSeverity = ChangeSeverity.HIGH,
    ) -> ResourceChange:
        """
        Create a ResourceChange for an added resource.

        Args:
            resource: The resource that was added.
            resource_type: Type of the resource.
            severity: Severity level for the addition (default: HIGH).

        Returns:
            ResourceChange representing the addition.
        """
        resource_id = self._get_resource_identifier(resource)
        return ResourceChange(
            change_type=ChangeType.ADDED,
            resource_id=resource_id,
            resource_type=resource_type,
            field_path=None,
            old_value=None,
            new_value=self._resource_to_dict(resource),
            severity=severity,
            description="Resource exists only in Account 2",
        )

    def _create_removed_change(
        self,
        resource: AWSResource,
        resource_type: str,
        severity: ChangeSeverity = ChangeSeverity.HIGH,
    ) -> ResourceChange:
        """
        Create a ResourceChange for a removed resource.

        Args:
            resource: The resource that was removed.
            resource_type: Type of the resource.
            severity: Severity level for the removal (default: HIGH).

        Returns:
            ResourceChange representing the removal.
        """
        resource_id = self._get_resource_identifier(resource)
        return ResourceChange(
            change_type=ChangeType.REMOVED,
            resource_id=resource_id,
            resource_type=resource_type,
            field_path=None,
            old_value=self._resource_to_dict(resource),
            new_value=None,
            severity=severity,
            description="Resource exists only in Account 1",
        )

    def __str__(self) -> str:
        """Return string representation of comparator."""
        return f"{self.__class__.__name__}(service={self.service_name})"

    def __repr__(self) -> str:
        """Return detailed representation for debugging."""
        return f"{self.__class__.__name__}(service_name={self.service_name!r})"
