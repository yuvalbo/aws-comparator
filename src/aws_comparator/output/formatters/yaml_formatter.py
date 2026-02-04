"""
YAML output formatter for comparison reports.

This module provides a YAML formatter that converts comparison reports
to YAML format with configurable formatting options.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Union

import yaml

from aws_comparator.models.comparison import (
    ComparisonReport,
    ServiceComparisonResult,
)
from aws_comparator.output.base import BaseFormatter


class YAMLFormatter(BaseFormatter):
    """
    Formatter that outputs comparison reports as YAML.

    This formatter converts ComparisonReport or ServiceComparisonResult
    objects to YAML format with support for custom formatting options
    and safe serialization.

    Args:
        default_flow_style: Use flow style for collections (default: False)
        allow_unicode: Allow unicode characters in output (default: True)
        sort_keys: Whether to sort dictionary keys (default: False)
        include_summary: Whether to include summary statistics (default: True)
        indent: Number of spaces for indentation (default: 2)
        width: Maximum line width before wrapping (default: 80)

    Example:
        >>> formatter = YAMLFormatter(indent=4)
        >>> yaml_output = formatter.format(report)
        >>> formatter.write_to_file(report, Path("report.yaml"))
    """

    def __init__(
        self,
        default_flow_style: bool = False,
        allow_unicode: bool = True,
        sort_keys: bool = False,
        include_summary: bool = True,
        indent: int = 2,
        width: int = 80,
        **options: Any,
    ) -> None:
        """
        Initialize the YAML formatter.

        Args:
            default_flow_style: Use flow style for collections (default: False)
            allow_unicode: Allow unicode characters in output (default: True)
            sort_keys: Whether to sort dictionary keys (default: False)
            include_summary: Whether to include summary statistics (default: True)
            indent: Number of spaces for indentation (default: 2)
            width: Maximum line width before wrapping (default: 80)
            **options: Additional formatter options
        """
        super().__init__(**options)
        self.default_flow_style = default_flow_style
        self.allow_unicode = allow_unicode
        self.sort_keys = sort_keys
        self.include_summary = include_summary
        self.indent = indent
        self.width = width
        self.logger = logging.getLogger(
            f"{self.__class__.__module__}.{self.__class__.__name__}"
        )

    def format(
        self, report: Union[ComparisonReport, ServiceComparisonResult]
    ) -> str:
        """
        Format a comparison report as YAML.

        Args:
            report: The comparison report or service result to format

        Returns:
            YAML-formatted string representation of the report

        Example:
            >>> formatter = YAMLFormatter()
            >>> yaml_str = formatter.format(report)
        """
        self.logger.debug("Formatting report as YAML")

        try:
            output_data = self._build_output_data(report)

            # Configure custom representer for datetime
            yaml.add_representer(datetime, self._datetime_representer)

            yaml_str = yaml.dump(
                output_data,
                default_flow_style=self.default_flow_style,
                allow_unicode=self.allow_unicode,
                sort_keys=self.sort_keys,
                indent=self.indent,
                width=self.width,
            )

            self.logger.debug(
                f"YAML formatting complete, output size: {len(yaml_str)} bytes"
            )
            return yaml_str

        except Exception as e:
            self.logger.error(f"Error formatting report as YAML: {e}", exc_info=True)
            raise

    def write_to_file(
        self,
        report: Union[ComparisonReport, ServiceComparisonResult],
        filepath: Path,
    ) -> None:
        """
        Write formatted YAML report to a file.

        Args:
            report: The comparison report or service result to write
            filepath: Path where to write the YAML output

        Raises:
            OSError: If the file cannot be written
            yaml.YAMLError: If the report cannot be serialized

        Example:
            >>> formatter = YAMLFormatter()
            >>> formatter.write_to_file(report, Path("output/report.yaml"))
        """
        self.logger.info(f"Writing YAML report to {filepath}")

        try:
            # Ensure parent directory exists
            filepath.parent.mkdir(parents=True, exist_ok=True)

            output_data = self._build_output_data(report)

            # Configure custom representer for datetime
            yaml.add_representer(datetime, self._datetime_representer)

            with open(filepath, "w", encoding="utf-8") as f:
                yaml.dump(
                    output_data,
                    f,
                    default_flow_style=self.default_flow_style,
                    allow_unicode=self.allow_unicode,
                    sort_keys=self.sort_keys,
                    indent=self.indent,
                    width=self.width,
                )

            self.logger.info(f"Successfully wrote YAML report to {filepath}")

        except OSError as e:
            self.logger.error(
                f"Failed to write YAML report to {filepath}: {e}", exc_info=True
            )
            raise
        except yaml.YAMLError as e:
            self.logger.error(
                f"Error serializing report to YAML: {e}", exc_info=True
            )
            raise

    def _build_output_data(
        self, report: Union[ComparisonReport, ServiceComparisonResult]
    ) -> dict[str, Any]:
        """
        Build the output data dictionary from the report.

        Args:
            report: The comparison report or service result

        Returns:
            Dictionary ready for YAML serialization
        """
        # Use model_dump() for Pydantic serialization with JSON mode for clean output
        output_data = report.model_dump(mode="json")

        # Add summary statistics if requested
        if self.include_summary:
            summary_stats = self._generate_summary_stats(report)
            output_data["_summary_stats"] = summary_stats

        return output_data

    @staticmethod
    def _datetime_representer(
        dumper: yaml.Dumper, data: datetime
    ) -> yaml.ScalarNode:
        """
        Custom YAML representer for datetime objects.

        Args:
            dumper: YAML dumper instance
            data: datetime object to represent

        Returns:
            YAML scalar node with ISO format datetime string
        """
        return dumper.represent_scalar("tag:yaml.org,2002:timestamp", data.isoformat())
