"""
Base class for output formatters.

This module defines the abstract base class for implementing different
output formats (JSON, YAML, table, etc.) for comparison reports.
"""

import logging
import sys
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Optional, TextIO, Union

from aws_comparator.models.comparison import (
    ChangeSeverity,
    ChangeType,
    ComparisonReport,
    ResourceChange,
    ServiceComparisonResult,
)


class BaseFormatter(ABC):
    """
    Abstract base class for all output formatters.

    This class defines the interface for formatting and outputting
    comparison reports in different formats.

    Subclasses must implement:
    - format(): Convert report to formatted string
    - write_to_file(): Write formatted report to file
    """

    def __init__(self, **options: Any) -> None:
        """
        Initialize the formatter.

        Args:
            **options: Formatter-specific options (e.g., colors, indent)
        """
        self.options = options
        self.logger = logging.getLogger(
            f"{self.__class__.__module__}.{self.__class__.__name__}"
        )

    @abstractmethod
    def format(self, report: Union[ComparisonReport, ServiceComparisonResult]) -> str:
        """
        Format a comparison report as a string.

        Args:
            report: The comparison report or service result to format

        Returns:
            Formatted string representation of the report

        Example:
            >>> formatter = JSONFormatter()
            >>> formatted = formatter.format(report)
            >>> print(formatted)
        """
        pass

    @abstractmethod
    def write_to_file(
        self,
        report: Union[ComparisonReport, ServiceComparisonResult],
        filepath: Path,
    ) -> None:
        """
        Write formatted report directly to a file.

        Args:
            report: The comparison report or service result to write
            filepath: Path where to write the output

        Example:
            >>> formatter = JSONFormatter()
            >>> formatter.write_to_file(report, Path("report.json"))
        """
        pass

    def write_to_stream(
        self,
        report: Union[ComparisonReport, ServiceComparisonResult],
        stream: Optional[TextIO] = None,
    ) -> None:
        """
        Write formatted report to a stream (default: stdout).

        Args:
            report: The comparison report or service result to write
            stream: Output stream (default: sys.stdout)
        """
        output_stream = stream if stream is not None else sys.stdout

        formatted = self.format(report)
        output_stream.write(formatted)
        output_stream.write("\n")  # Ensure newline at end
        output_stream.flush()

    def _get_all_changes(
        self, report: Union[ComparisonReport, ServiceComparisonResult]
    ) -> list[ResourceChange]:
        """
        Extract all changes from a report.

        Args:
            report: The comparison report or service result

        Returns:
            List of all ResourceChange objects from the report
        """
        changes: list[ResourceChange] = []

        if isinstance(report, ComparisonReport):
            for service_result in report.results:
                changes.extend(self._get_service_changes(service_result))
        else:
            changes.extend(self._get_service_changes(report))

        return changes

    def _get_service_changes(
        self, service_result: ServiceComparisonResult
    ) -> list[ResourceChange]:
        """
        Extract all changes from a service comparison result.

        Args:
            service_result: The service comparison result

        Returns:
            List of all ResourceChange objects from the service
        """
        changes: list[ResourceChange] = []

        for resource_comp in service_result.resource_comparisons.values():
            changes.extend(resource_comp.added)
            changes.extend(resource_comp.removed)
            changes.extend(resource_comp.modified)

        return changes

    def _generate_summary_stats(
        self, report: Union[ComparisonReport, ServiceComparisonResult]
    ) -> dict[str, Any]:
        """
        Generate summary statistics for a report.

        Args:
            report: The comparison report or service result

        Returns:
            Dictionary containing summary statistics including:
            - total_changes: Total number of changes
            - changes_by_type: Count of changes by ChangeType
            - changes_by_severity: Count of changes by ChangeSeverity
            - services_with_changes: Number of services with changes (for ComparisonReport)
            - has_errors: Whether any errors occurred
        """
        changes = self._get_all_changes(report)

        # Count by type
        changes_by_type: dict[str, int] = {ct.value: 0 for ct in ChangeType}
        for change in changes:
            changes_by_type[change.change_type.value] += 1

        # Count by severity
        changes_by_severity: dict[str, int] = {cs.value: 0 for cs in ChangeSeverity}
        for change in changes:
            changes_by_severity[change.severity.value] += 1

        stats: dict[str, Any] = {
            "total_changes": len(changes),
            "changes_by_type": changes_by_type,
            "changes_by_severity": changes_by_severity,
        }

        if isinstance(report, ComparisonReport):
            services_with_changes = sum(
                1 for result in report.results if result.total_changes > 0
            )
            stats["services_with_changes"] = services_with_changes
            stats["total_services"] = len(report.results)
            stats["has_errors"] = len(report.errors) > 0
            stats["error_count"] = len(report.errors)
        else:
            stats["has_errors"] = report.has_errors
            stats["error_count"] = len(report.errors)

        return stats

    def _is_comparison_report(
        self, report: Union[ComparisonReport, ServiceComparisonResult]
    ) -> bool:
        """
        Check if the report is a full ComparisonReport.

        Args:
            report: The report to check

        Returns:
            True if report is a ComparisonReport, False otherwise
        """
        return isinstance(report, ComparisonReport)

    def __str__(self) -> str:
        """Return string representation of formatter."""
        return f"{self.__class__.__name__}()"

    def __repr__(self) -> str:
        """Return detailed representation for debugging."""
        return f"{self.__class__.__name__}(options={self.options!r})"
