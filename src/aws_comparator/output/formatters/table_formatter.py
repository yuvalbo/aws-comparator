"""
Rich table output formatter for comparison reports.

This module provides a table formatter that outputs comparison reports
as formatted console output using the Rich library with color-coded
severity indicators and clean, readable layouts.
"""

import logging
import re
from io import StringIO
from pathlib import Path
from typing import Any

from rich.console import Console

from aws_comparator.models.comparison import (
    ChangeSeverity,
    ChangeType,
    ComparisonReport,
    ResourceChange,
    ServiceComparisonResult,
)
from aws_comparator.output.base import BaseFormatter

# Severity to Rich color mapping
SEVERITY_COLORS: dict[ChangeSeverity, str] = {
    ChangeSeverity.CRITICAL: "red bold",
    ChangeSeverity.HIGH: "bright_red",
    ChangeSeverity.MEDIUM: "yellow",
    ChangeSeverity.LOW: "blue",
    ChangeSeverity.INFO: "dim",
}

# Severity order for sorting (highest first)
SEVERITY_ORDER: dict[ChangeSeverity, int] = {
    ChangeSeverity.CRITICAL: 5,
    ChangeSeverity.HIGH: 4,
    ChangeSeverity.MEDIUM: 3,
    ChangeSeverity.LOW: 2,
    ChangeSeverity.INFO: 1,
}

# Change type to symbol mapping
CHANGE_TYPE_SYMBOLS: dict[ChangeType, tuple[str, str]] = {
    ChangeType.ADDED: ("+", "green"),
    ChangeType.REMOVED: ("-", "red"),
    ChangeType.MODIFIED: ("~", "yellow"),
    ChangeType.NO_CHANGE: ("=", "dim"),
}


class TableFormatter(BaseFormatter):
    """
    Formatter that outputs comparison reports as Rich console output.

    This formatter creates visually formatted output with color-coded
    severity levels and change types for easy reading in terminals.
    Supports both colored and plain text modes for piping/grep.

    Args:
        show_unchanged: Whether to show unchanged resources (default: False)
        use_colors: Whether to use colors in output (default: True)
        max_value_length: Maximum length for value display before wrapping (default: 100)
        show_details: Whether to show detailed change information (default: True)
        console_width: Width of the output console (default: 120)

    Example:
        >>> formatter = TableFormatter(use_colors=True)
        >>> formatter.write_to_stream(report)
        >>> formatter.write_to_file(report, Path("report.txt"))
    """

    def __init__(
        self,
        show_unchanged: bool = False,
        use_colors: bool = True,
        max_value_length: int = 100,
        show_details: bool = True,
        console_width: int = 120,
        **options: Any,
    ) -> None:
        """
        Initialize the table formatter.

        Args:
            show_unchanged: Whether to show unchanged resources (default: False)
            use_colors: Whether to use colors in output (default: True)
            max_value_length: Maximum length for value display before wrapping (default: 100)
            show_details: Whether to show detailed change information (default: True)
            console_width: Width of the output console (default: 120)
            **options: Additional formatter options
        """
        super().__init__(**options)
        self.show_unchanged = show_unchanged
        self.use_colors = use_colors
        self.max_value_length = max_value_length
        self.show_details = show_details
        self.console_width = console_width
        self.logger = logging.getLogger(
            f"{self.__class__.__module__}.{self.__class__.__name__}"
        )
        # Track account IDs for rendering (set during _render_report)
        self._account1_id: str = "Account 1"
        self._account2_id: str = "Account 2"

    def format(
        self, report: ComparisonReport | ServiceComparisonResult
    ) -> str:
        """
        Format a comparison report as Rich output.

        Args:
            report: The comparison report or service result to format

        Returns:
            Formatted string representation of the report

        Example:
            >>> formatter = TableFormatter()
            >>> output = formatter.format(report)
        """
        self.logger.debug("Formatting report as table")

        try:
            # Create console for string capture
            string_buffer = StringIO()
            console = Console(
                file=string_buffer,
                force_terminal=self.use_colors,
                no_color=not self.use_colors,
                width=self.console_width,
            )

            self._render_report(console, report)

            output = string_buffer.getvalue()

            # If colors are disabled, strip any remaining ANSI codes
            if not self.use_colors:
                output = self._strip_ansi(output)

            self.logger.debug(
                f"Table formatting complete, output size: {len(output)} bytes"
            )
            return output

        except Exception as e:
            self.logger.error(f"Error formatting report as table: {e}", exc_info=True)
            raise

    def write_to_file(
        self,
        report: ComparisonReport | ServiceComparisonResult,
        filepath: Path,
    ) -> None:
        """
        Write formatted table report to a file.

        When writing to a file, ANSI color codes are stripped for
        clean text output.

        Args:
            report: The comparison report or service result to write
            filepath: Path where to write the table output

        Raises:
            OSError: If the file cannot be written

        Example:
            >>> formatter = TableFormatter()
            >>> formatter.write_to_file(report, Path("output/report.txt"))
        """
        self.logger.info(f"Writing table report to {filepath}")

        try:
            # Ensure parent directory exists
            filepath.parent.mkdir(parents=True, exist_ok=True)

            # Create console without colors for file output
            string_buffer = StringIO()
            console = Console(
                file=string_buffer,
                force_terminal=False,
                no_color=True,
                width=self.console_width,
            )

            self._render_report(console, report)

            # Strip any remaining ANSI codes
            output = self._strip_ansi(string_buffer.getvalue())

            with open(filepath, "w", encoding="utf-8") as f:
                f.write(output)

            self.logger.info(f"Successfully wrote table report to {filepath}")

        except OSError as e:
            self.logger.error(
                f"Failed to write table report to {filepath}: {e}", exc_info=True
            )
            raise

    def _render_report(
        self,
        console: Console,
        report: ComparisonReport | ServiceComparisonResult,
    ) -> None:
        """
        Render the complete report to the console.

        Args:
            console: Rich console instance to render to
            report: The comparison report or service result
        """
        # Store account IDs if available for use in service sections
        if isinstance(report, ComparisonReport):
            self._account1_id = report.account1_id
            self._account2_id = report.account2_id

        # Render header
        self._render_header(console, report)

        # Render summary
        self._render_summary(console, report)

        # Render service results
        if isinstance(report, ComparisonReport):
            for service_result in report.results:
                if service_result.total_changes > 0 or self.show_unchanged:
                    self._render_service_section(console, service_result)

            # Render errors if any
            if report.errors:
                self._render_errors_section(console, report)
        else:
            self._render_service_section(console, report)

    def _render_header(
        self,
        console: Console,
        report: ComparisonReport | ServiceComparisonResult,
    ) -> None:
        """
        Render the report header with account and region info.

        Args:
            console: Rich console instance
            report: The comparison report or service result
        """
        # Double line separator
        console.print("=" * self.console_width)

        # Title
        title = "AWS COMPARATOR REPORT"
        padding = (self.console_width - len(title)) // 2
        if self.use_colors:
            console.print(" " * padding + "[bold cyan]" + title + "[/bold cyan]")
        else:
            console.print(" " * padding + title)

        console.print("=" * self.console_width)

        # Report metadata
        if isinstance(report, ComparisonReport):
            # Determine regions to display
            region1 = report.region1 if report.region1 else report.region
            region2 = report.region2 if report.region2 else report.region

            console.print(f"Account 1: {report.account1_id} ({region1})")
            console.print(f"Account 2: {report.account2_id} ({region2})")
            console.print(f"Timestamp: {report.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            console.print(f"Service: {report.service_name}")
            console.print(f"Execution Time: {report.execution_time_seconds:.2f}s")
            console.print(f"Timestamp: {report.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")

        console.print()

    def _render_summary(
        self,
        console: Console,
        report: ComparisonReport | ServiceComparisonResult,
    ) -> None:
        """
        Render the summary statistics section.

        Args:
            console: Rich console instance
            report: The comparison report or service result
        """
        stats = self._generate_summary_stats(report)

        console.print("SUMMARY")
        console.print("-" * self.console_width)

        console.print(f"Total Changes: {stats['total_changes']}")

        # Changes by severity (only show non-zero)
        severity_counts = stats["changes_by_severity"]
        severity_lines = []
        for severity in [ChangeSeverity.CRITICAL, ChangeSeverity.HIGH,
                         ChangeSeverity.MEDIUM, ChangeSeverity.LOW, ChangeSeverity.INFO]:
            count = severity_counts.get(severity.value, 0)
            if count > 0:
                if self.use_colors:
                    color = SEVERITY_COLORS.get(severity, "white")
                    severity_lines.append(f"  [{color}]{severity.value.upper()}: {count}[/{color}]")
                else:
                    severity_lines.append(f"  {severity.value.upper()}: {count}")

        if severity_lines:
            for line in severity_lines:
                console.print(line)

        # Changes by type
        type_counts = stats["changes_by_type"]
        added = type_counts.get("added", 0)
        removed = type_counts.get("removed", 0)
        modified = type_counts.get("modified", 0)

        console.print()
        if self.use_colors:
            console.print(f"  [green]ADDED: {added}[/green]  |  "
                         f"[red]REMOVED: {removed}[/red]  |  "
                         f"[yellow]MODIFIED: {modified}[/yellow]")
        else:
            console.print(f"  ADDED: {added}  |  REMOVED: {removed}  |  MODIFIED: {modified}")

        if stats.get("has_errors"):
            console.print()
            if self.use_colors:
                console.print(f"  [bold red]ERRORS: {stats['error_count']}[/bold red]")
            else:
                console.print(f"  ERRORS: {stats['error_count']}")

        console.print()

    def _render_service_section(
        self,
        console: Console,
        service_result: ServiceComparisonResult,
    ) -> None:
        """
        Render a section for a single service.

        Args:
            console: Rich console instance
            service_result: The service comparison result
        """
        # Service header with double lines
        console.print("=" * self.console_width)
        if self.use_colors:
            console.print(f"[bold cyan]SERVICE: {service_result.service_name.upper()}[/bold cyan]")
        else:
            console.print(f"SERVICE: {service_result.service_name.upper()}")
        console.print("=" * self.console_width)
        console.print()

        # Collect all changes by type across all resource types
        all_added: list[tuple[str, ResourceChange]] = []
        all_removed: list[tuple[str, ResourceChange]] = []
        all_modified: list[tuple[str, ResourceChange]] = []

        for resource_type, resource_comp in service_result.resource_comparisons.items():
            for change in resource_comp.added:
                all_added.append((resource_type, change))
            for change in resource_comp.removed:
                all_removed.append((resource_type, change))
            for change in resource_comp.modified:
                all_modified.append((resource_type, change))

        # Sort by severity (highest first)
        all_added.sort(key=lambda x: SEVERITY_ORDER.get(x[1].severity, 0), reverse=True)
        all_removed.sort(key=lambda x: SEVERITY_ORDER.get(x[1].severity, 0), reverse=True)
        all_modified.sort(key=lambda x: SEVERITY_ORDER.get(x[1].severity, 0), reverse=True)

        # Render ONLY IN ACCOUNT 2 section (was ADDED)
        if all_added:
            self._render_change_section(
                console,
                f"ONLY IN ACCOUNT 2 ({self._account2_id})",
                "exists only in Account 2",
                all_added,
                "green",
            )

        # Render ONLY IN ACCOUNT 1 section (was REMOVED)
        if all_removed:
            self._render_change_section(
                console,
                f"ONLY IN ACCOUNT 1 ({self._account1_id})",
                "exists only in Account 1",
                all_removed,
                "red",
            )

        # Render DIFFERENT BETWEEN ACCOUNTS section (was MODIFIED)
        if all_modified:
            self._render_modified_section(console, all_modified)

        # Service errors
        if service_result.errors:
            console.print()
            if self.use_colors:
                console.print("[bold red]Service Errors:[/bold red]")
            else:
                console.print("Service Errors:")
            for error in service_result.errors:
                console.print(f"  - {error}")
            console.print()

    def _render_change_section(
        self,
        console: Console,
        title: str,
        subtitle: str,
        changes: list[tuple[str, ResourceChange]],
        color: str,
    ) -> None:
        """
        Render a section for added or removed changes.

        Args:
            console: Rich console instance
            title: Section title (e.g., "ADDED")
            subtitle: Section subtitle (e.g., "Account 2 only")
            changes: List of (resource_type, change) tuples
            color: Color for the section header
        """
        if self.use_colors:
            console.print(f"[{color} bold]{title}[/{color} bold] ({subtitle}):")
        else:
            console.print(f"{title} ({subtitle}):")
        console.print()

        for resource_type, change in changes:
            self._render_added_removed_change(console, resource_type, change)

        console.print()

    def _render_added_removed_change(
        self,
        console: Console,
        resource_type: str,
        change: ResourceChange,
    ) -> None:
        """
        Render a single added or removed change.

        Args:
            console: Rich console instance
            resource_type: The type of resource
            change: The resource change
        """
        severity_str = f"[{change.severity.value.upper()}]"

        if self.use_colors:
            severity_color = SEVERITY_COLORS.get(change.severity, "white")
            console.print(f"  [{severity_color}]{severity_str}[/{severity_color}] {resource_type}: {change.resource_id}")
        else:
            console.print(f"  {severity_str} {resource_type}: {change.resource_id}")

        # Extract and display additional useful info from old_value or new_value
        value = change.new_value if change.new_value is not None else change.old_value
        if value is not None:
            extra_info = self._extract_resource_info(value)
            for key, val in extra_info.items():
                # Skip ARN-like fields if they match the resource_id already shown
                val_str = str(val)
                if key.lower() in ('arn', 'topicarn', 'clusterarn') and val_str == change.resource_id:
                    continue
                console.print(f"         {key}: {val_str}")

        # Show description if available
        if change.description:
            console.print(f"         Note: {change.description}")

    def _render_modified_section(
        self,
        console: Console,
        changes: list[tuple[str, ResourceChange]],
    ) -> None:
        """
        Render the modified resources section.

        Args:
            console: Rich console instance
            changes: List of (resource_type, change) tuples
        """
        if self.use_colors:
            console.print("[yellow bold]DIFFERENT BETWEEN ACCOUNTS[/yellow bold]:")
        else:
            console.print("DIFFERENT BETWEEN ACCOUNTS:")
        console.print()

        for resource_type, change in changes:
            self._render_modified_change(console, resource_type, change)

        console.print()

    def _render_modified_change(
        self,
        console: Console,
        resource_type: str,
        change: ResourceChange,
    ) -> None:
        """
        Render a single modified change.

        Args:
            console: Rich console instance
            resource_type: The type of resource
            change: The resource change
        """
        severity_str = f"[{change.severity.value.upper()}]"

        if self.use_colors:
            severity_color = SEVERITY_COLORS.get(change.severity, "white")
            console.print(f"  [{severity_color}]{severity_str}[/{severity_color}] {resource_type}: {change.resource_id}")
        else:
            console.print(f"  {severity_str} {resource_type}: {change.resource_id}")

        if self.show_details:
            # Field that changed
            field = change.field_path or "(unknown field)"
            console.print(f"         Field: {field}")

            # Format old and new values nicely
            old_formatted = self._format_value_for_display(change.old_value)
            new_formatted = self._format_value_for_display(change.new_value)

            if self.use_colors:
                console.print(f"         Account 1: [red]{old_formatted}[/red]")
                console.print(f"         Account 2: [green]{new_formatted}[/green]")
            else:
                console.print(f"         Account 1: {old_formatted}")
                console.print(f"         Account 2: {new_formatted}")

        # Show description if available
        if change.description:
            console.print(f"         Note: {change.description}")

    def _render_errors_section(
        self,
        console: Console,
        report: ComparisonReport,
    ) -> None:
        """
        Render the errors section for the full report.

        Args:
            console: Rich console instance
            report: The comparison report
        """
        console.print("=" * self.console_width)
        if self.use_colors:
            console.print("[bold red]ERRORS[/bold red]")
        else:
            console.print("ERRORS")
        console.print("=" * self.console_width)
        console.print()

        for error in report.errors:
            if self.use_colors:
                console.print(f"  [red][{error.service_name}][/red] {error.error_type}: {error.error_message}")
            else:
                console.print(f"  [{error.service_name}] {error.error_type}: {error.error_message}")

        console.print()

    def _extract_resource_info(self, value: Any) -> dict[str, Any]:
        """
        Extract useful information from a resource value.

        This intelligently extracts key identifiers like ARN, Name, ID
        from nested dictionaries and other structures.

        Args:
            value: The value to extract info from

        Returns:
            Dictionary of extracted key-value pairs
        """
        info: dict[str, Any] = {}

        if value is None:
            return info

        if isinstance(value, dict):
            # Priority fields to extract
            priority_fields = [
                'Arn', 'ARN', 'arn',
                'Name', 'name', 'ResourceName',
                'Id', 'ID', 'id', 'ResourceId',
                'VpcId', 'SubnetId', 'InstanceId', 'SecurityGroupId',
                'BucketName', 'FunctionName', 'RoleName', 'PolicyName',
                'KeyId', 'TableName', 'QueueUrl', 'TopicArn',
                'DomainName', 'HostedZoneId', 'ClusterArn', 'ClusterName',
                'Tags', 'State', 'Status',
            ]

            for field in priority_fields:
                if field in value and value[field] is not None:
                    field_value = value[field]
                    # Handle Tags specially
                    if field == 'Tags' and isinstance(field_value, list):
                        # Try to find Name tag
                        for tag in field_value:
                            if isinstance(tag, dict) and tag.get('Key') == 'Name':
                                info['Name (tag)'] = tag.get('Value', '')
                                break
                    elif isinstance(field_value, str):
                        info[field] = field_value
                    elif isinstance(field_value, (int, float, bool)):
                        info[field] = field_value

            # Limit to avoid overwhelming output
            if len(info) > 5:
                info = dict(list(info.items())[:5])

        elif isinstance(value, str):
            # If it's just a string, check if it looks like an ARN
            if value.startswith('arn:'):
                info['ARN'] = value

        return info

    def _format_value_for_display(self, value: Any) -> str:
        """
        Format a value for display, handling dicts and lists nicely.

        Args:
            value: The value to format

        Returns:
            Formatted string representation
        """
        if value is None:
            return "(none)"

        if isinstance(value, bool):
            return str(value).lower()

        if isinstance(value, (int, float)):
            return str(value)

        if isinstance(value, str):
            if len(value) > self.max_value_length:
                return value[:self.max_value_length] + "..."
            return value

        if isinstance(value, dict):
            # Try to extract a meaningful representation
            # Check for common identifier fields
            for key in ['Arn', 'ARN', 'arn', 'Name', 'name', 'Id', 'ID', 'id']:
                if key in value:
                    extracted = value[key]
                    if isinstance(extracted, str):
                        return f"{key}={extracted}"

            # For small dicts, show them compactly
            if len(value) <= 3:
                parts = [f"{k}={v}" for k, v in value.items()]
                return "{" + ", ".join(parts) + "}"

            # For larger dicts, show key count and sample
            keys = list(value.keys())[:3]
            return f"{{dict with {len(value)} keys: {', '.join(keys)}...}}"

        if isinstance(value, list):
            if len(value) == 0:
                return "[]"
            if len(value) == 1:
                return f"[{self._format_value_for_display(value[0])}]"
            # Show count and first item
            first = self._format_value_for_display(value[0])
            return f"[{first}, ... ({len(value)} items)]"

        # Fallback
        result = str(value)
        if len(result) > self.max_value_length:
            return result[:self.max_value_length] + "..."
        return result

    @staticmethod
    def _strip_ansi(text: str) -> str:
        """
        Remove ANSI escape codes from text.

        Args:
            text: Text potentially containing ANSI codes

        Returns:
            Clean text without ANSI codes
        """
        # Comprehensive ANSI escape pattern
        ansi_pattern = re.compile(r'\x1b\[[0-9;]*[A-Za-z]|\x1b\].*?\x07')
        return ansi_pattern.sub("", text)
