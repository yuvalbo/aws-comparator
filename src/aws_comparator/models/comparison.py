"""
Pydantic models for comparison results and reports.

This module defines the data structures used to represent comparison results,
including changes, severity levels, and aggregated reports.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, computed_field


class ChangeType(str, Enum):
    """Types of changes detected during comparison."""
    ADDED = "added"
    REMOVED = "removed"
    MODIFIED = "modified"
    NO_CHANGE = "no_change"


class ChangeSeverity(str, Enum):
    """
    Severity levels for changes.

    CRITICAL: Security-impacting changes (security groups, IAM, encryption)
    HIGH: Configuration changes that affect functionality
    MEDIUM: Changes that may affect performance or behavior
    LOW: Metadata changes with minimal impact
    INFO: Informational changes only
    """
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class ResourceChange(BaseModel):
    """
    Represents a change to a single resource.

    This model captures all details about a specific change, including
    what changed, how it changed, and the severity of the change.
    """
    model_config = ConfigDict(
        extra="ignore",
        json_encoders={datetime: lambda v: v.isoformat()},
    )

    change_type: ChangeType = Field(..., description="Type of change")
    resource_id: str = Field(..., description="Unique resource identifier")
    resource_type: str = Field(..., description="Type of resource")
    field_path: Optional[str] = Field(
        None,
        description="Path to changed field (e.g., 'SecurityGroups[0].GroupId')"
    )
    old_value: Optional[Any] = Field(None, description="Previous value")
    new_value: Optional[Any] = Field(None, description="New value")
    severity: ChangeSeverity = Field(
        default=ChangeSeverity.INFO,
        description="Severity level of the change"
    )
    description: Optional[str] = Field(None, description="Human-readable description")

    def __str__(self) -> str:
        """Return string representation of the change."""
        if self.change_type == ChangeType.ADDED:
            return f"Added {self.resource_type}: {self.resource_id}"
        elif self.change_type == ChangeType.REMOVED:
            return f"Removed {self.resource_type}: {self.resource_id}"
        else:
            field_info = f" ({self.field_path})" if self.field_path else ""
            return f"Modified {self.resource_type}: {self.resource_id}{field_info}"

    def __repr__(self) -> str:
        """Return detailed representation for debugging."""
        return (
            f"ResourceChange("
            f"change_type={self.change_type.value!r}, "
            f"resource_id={self.resource_id!r}, "
            f"severity={self.severity.value!r})"
        )


class ResourceTypeComparison(BaseModel):
    """
    Comparison results for a single resource type within a service.

    This aggregates all changes for a specific type of resource
    (e.g., EC2 instances, S3 buckets).
    """
    model_config = ConfigDict(extra="ignore")

    resource_type: str = Field(..., description="Type of resource")
    account1_count: int = Field(ge=0, description="Count in first account")
    account2_count: int = Field(ge=0, description="Count in second account")
    added: list[ResourceChange] = Field(
        default_factory=list,
        description="Resources added in account2"
    )
    removed: list[ResourceChange] = Field(
        default_factory=list,
        description="Resources removed from account2"
    )
    modified: list[ResourceChange] = Field(
        default_factory=list,
        description="Resources modified between accounts"
    )
    unchanged_count: int = Field(ge=0, default=0, description="Unchanged resources")

    @computed_field  # type: ignore[misc]
    @property
    def total_changes(self) -> int:
        """Total number of changes (added + removed + modified)."""
        return len(self.added) + len(self.removed) + len(self.modified)

    @computed_field  # type: ignore[misc]
    @property
    def has_changes(self) -> bool:
        """Check if any changes exist."""
        return self.total_changes > 0

    def __str__(self) -> str:
        """Return string representation of comparison."""
        return (
            f"{self.resource_type}: "
            f"+{len(self.added)} -{len(self.removed)} "
            f"~{len(self.modified)} (={self.unchanged_count})"
        )

    def __repr__(self) -> str:
        """Return detailed representation for debugging."""
        return (
            f"ResourceTypeComparison("
            f"resource_type={self.resource_type!r}, "
            f"total_changes={self.total_changes})"
        )


class ServiceComparisonResult(BaseModel):
    """
    Comparison results for a single AWS service.

    This aggregates all resource type comparisons for a service
    (e.g., all EC2 resource types).
    """
    model_config = ConfigDict(extra="ignore")

    service_name: str = Field(..., description="AWS service name")
    resource_comparisons: dict[str, ResourceTypeComparison] = Field(
        default_factory=dict,
        description="Comparisons for each resource type"
    )
    errors: list[str] = Field(
        default_factory=list,
        description="Errors encountered during comparison"
    )
    execution_time_seconds: float = Field(ge=0, description="Execution time")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="When comparison was performed"
    )

    @computed_field  # type: ignore[misc]
    @property
    def total_changes(self) -> int:
        """Total changes across all resource types."""
        return sum(
            comp.total_changes
            for comp in self.resource_comparisons.values()
        )

    @computed_field  # type: ignore[misc]
    @property
    def has_errors(self) -> bool:
        """Check if any errors occurred."""
        return len(self.errors) > 0

    def __str__(self) -> str:
        """Return string representation of service result."""
        status = "with errors" if self.has_errors else "ok"
        return f"{self.service_name} {status}: {self.total_changes} changes"

    def __repr__(self) -> str:
        """Return detailed representation for debugging."""
        return (
            f"ServiceComparisonResult("
            f"service_name={self.service_name!r}, "
            f"total_changes={self.total_changes}, "
            f"has_errors={self.has_errors})"
        )


class ReportSummary(BaseModel):
    """
    Summary statistics for the entire comparison.

    This provides high-level metrics about the comparison results.
    """
    model_config = ConfigDict(extra="ignore")

    total_services_compared: int = Field(ge=0, description="Number of services")
    total_services_with_changes: int = Field(ge=0, description="Services with changes")
    total_changes: int = Field(ge=0, description="Total number of changes")
    total_resources_account1: int = Field(ge=0, description="Resources in account1")
    total_resources_account2: int = Field(ge=0, description="Resources in account2")
    changes_by_severity: dict[str, int] = Field(
        default_factory=lambda: {
            severity.value: 0 for severity in ChangeSeverity
        },
        description="Count of changes by severity level"
    )
    services_with_errors: list[str] = Field(
        default_factory=list,
        description="Services that had errors"
    )
    execution_time_seconds: float = Field(ge=0, description="Total execution time")

    def __str__(self) -> str:
        """Return string representation of summary."""
        return (
            f"Summary: {self.total_changes} changes across "
            f"{self.total_services_with_changes}/{self.total_services_compared} services"
        )

    def __repr__(self) -> str:
        """Return detailed representation for debugging."""
        return (
            f"ReportSummary("
            f"total_services_compared={self.total_services_compared}, "
            f"total_changes={self.total_changes})"
        )


class ServiceError(BaseModel):
    """
    Error that occurred during service processing.

    This captures all details about errors for debugging and reporting.
    """
    model_config = ConfigDict(extra="ignore")

    service_name: str = Field(..., description="Service where error occurred")
    error_type: str = Field(..., description="Type of error")
    error_message: str = Field(..., description="Error message")
    error_code: Optional[str] = Field(None, description="Error code if available")
    traceback: Optional[str] = Field(None, description="Stack trace")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="When error occurred"
    )

    def __str__(self) -> str:
        """Return string representation of error."""
        return f"[{self.service_name}] {self.error_type}: {self.error_message}"

    def __repr__(self) -> str:
        """Return detailed representation for debugging."""
        return (
            f"ServiceError("
            f"service_name={self.service_name!r}, "
            f"error_type={self.error_type!r}, "
            f"error_code={self.error_code!r})"
        )


class ComparisonReport(BaseModel):
    """
    Complete comparison report for all services.

    This is the top-level model that contains all comparison results,
    summaries, and metadata about the comparison operation.
    """
    model_config = ConfigDict(
        extra="ignore",
        json_encoders={datetime: lambda v: v.isoformat()},
    )

    account1_id: str = Field(..., pattern=r'^\d{12}$', description="First account ID")
    account2_id: str = Field(..., pattern=r'^\d{12}$', description="Second account ID")
    region: str = Field(..., description="AWS region (deprecated, use region1/region2)")
    region1: Optional[str] = Field(None, description="AWS region for account 1")
    region2: Optional[str] = Field(None, description="AWS region for account 2")
    services_compared: list[str] = Field(..., description="Services compared")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="When comparison was performed"
    )
    results: list[ServiceComparisonResult] = Field(
        default_factory=list,
        description="Results for each service"
    )
    summary: ReportSummary = Field(..., description="Summary statistics")
    errors: list[ServiceError] = Field(
        default_factory=list,
        description="Errors encountered"
    )

    def to_dict(self) -> dict[str, Any]:
        """
        Export as dictionary.

        Returns:
            Dictionary representation of the report
        """
        return self.model_dump()

    def get_service_result(self, service_name: str) -> Optional[ServiceComparisonResult]:
        """
        Get results for a specific service.

        Args:
            service_name: Name of the service to retrieve

        Returns:
            ServiceComparisonResult if found, None otherwise
        """
        for result in self.results:
            if result.service_name == service_name:
                return result
        return None

    def get_changes_by_severity(
        self,
        min_severity: ChangeSeverity = ChangeSeverity.INFO
    ) -> list[ResourceChange]:
        """
        Get all changes at or above a minimum severity level.

        Args:
            min_severity: Minimum severity level to include

        Returns:
            List of ResourceChange objects matching the criteria
        """
        severity_order = {
            ChangeSeverity.INFO: 0,
            ChangeSeverity.LOW: 1,
            ChangeSeverity.MEDIUM: 2,
            ChangeSeverity.HIGH: 3,
            ChangeSeverity.CRITICAL: 4,
        }
        min_level = severity_order[min_severity]

        changes: list[ResourceChange] = []
        for result in self.results:
            for resource_comp in result.resource_comparisons.values():
                for change_list in [resource_comp.added, resource_comp.removed, resource_comp.modified]:
                    changes.extend(
                        change for change in change_list
                        if severity_order.get(change.severity, 0) >= min_level
                    )
        return changes

    def __str__(self) -> str:
        """Return string representation of report."""
        return (
            f"ComparisonReport: {self.account1_id} vs {self.account2_id} "
            f"in {self.region} - {self.summary}"
        )

    def __repr__(self) -> str:
        """Return detailed representation for debugging."""
        return (
            f"ComparisonReport("
            f"account1_id={self.account1_id!r}, "
            f"account2_id={self.account2_id!r}, "
            f"region={self.region!r}, "
            f"services_compared={len(self.services_compared)})"
        )
