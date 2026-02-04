"""
JSON output formatter for comparison reports.

This module provides a JSON formatter that converts comparison reports
to JSON format with configurable formatting options.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, Union

from aws_comparator.models.comparison import (
    ComparisonReport,
    ServiceComparisonResult,
)
from aws_comparator.output.base import BaseFormatter


class JSONFormatter(BaseFormatter):
    """
    Formatter that outputs comparison reports as JSON.

    This formatter converts ComparisonReport or ServiceComparisonResult
    objects to JSON format with support for pretty-printing and
    custom serialization of datetime objects.

    Args:
        indent: Number of spaces for indentation (default: 2, None for compact)
        sort_keys: Whether to sort dictionary keys (default: False)
        include_summary: Whether to include summary statistics (default: True)
        ensure_ascii: Whether to escape non-ASCII characters (default: False)

    Example:
        >>> formatter = JSONFormatter(indent=4)
        >>> json_output = formatter.format(report)
        >>> formatter.write_to_file(report, Path("report.json"))
    """

    def __init__(
        self,
        indent: Optional[int] = 2,
        sort_keys: bool = False,
        include_summary: bool = True,
        ensure_ascii: bool = False,
        **options: Any,
    ) -> None:
        """
        Initialize the JSON formatter.

        Args:
            indent: Number of spaces for indentation (default: 2, None for compact)
            sort_keys: Whether to sort dictionary keys (default: False)
            include_summary: Whether to include summary statistics (default: True)
            ensure_ascii: Whether to escape non-ASCII characters (default: False)
            **options: Additional formatter options
        """
        super().__init__(**options)
        self.indent = indent
        self.sort_keys = sort_keys
        self.include_summary = include_summary
        self.ensure_ascii = ensure_ascii
        self.logger = logging.getLogger(
            f"{self.__class__.__module__}.{self.__class__.__name__}"
        )

    def format(
        self, report: Union[ComparisonReport, ServiceComparisonResult]
    ) -> str:
        """
        Format a comparison report as JSON.

        Args:
            report: The comparison report or service result to format

        Returns:
            JSON-formatted string representation of the report

        Example:
            >>> formatter = JSONFormatter()
            >>> json_str = formatter.format(report)
        """
        self.logger.debug("Formatting report as JSON")

        try:
            output_data = self._build_output_data(report)

            json_str = json.dumps(
                output_data,
                indent=self.indent,
                sort_keys=self.sort_keys,
                ensure_ascii=self.ensure_ascii,
                default=self._json_serializer,
            )

            self.logger.debug(
                f"JSON formatting complete, output size: {len(json_str)} bytes"
            )
            return json_str

        except Exception as e:
            self.logger.error(f"Error formatting report as JSON: {e}", exc_info=True)
            raise

    def write_to_file(
        self,
        report: Union[ComparisonReport, ServiceComparisonResult],
        filepath: Path,
    ) -> None:
        """
        Write formatted JSON report to a file.

        Args:
            report: The comparison report or service result to write
            filepath: Path where to write the JSON output

        Raises:
            OSError: If the file cannot be written
            ValueError: If the report cannot be serialized

        Example:
            >>> formatter = JSONFormatter()
            >>> formatter.write_to_file(report, Path("output/report.json"))
        """
        self.logger.info(f"Writing JSON report to {filepath}")

        try:
            # Ensure parent directory exists
            filepath.parent.mkdir(parents=True, exist_ok=True)

            output_data = self._build_output_data(report)

            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(
                    output_data,
                    f,
                    indent=self.indent,
                    sort_keys=self.sort_keys,
                    ensure_ascii=self.ensure_ascii,
                    default=self._json_serializer,
                )

            self.logger.info(f"Successfully wrote JSON report to {filepath}")

        except OSError as e:
            self.logger.error(
                f"Failed to write JSON report to {filepath}: {e}", exc_info=True
            )
            raise
        except Exception as e:
            self.logger.error(
                f"Error serializing report to JSON: {e}", exc_info=True
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
            Dictionary ready for JSON serialization
        """
        # Use model_dump() for Pydantic serialization
        output_data = report.model_dump(mode="json")

        # Add summary statistics if requested
        if self.include_summary:
            summary_stats = self._generate_summary_stats(report)
            output_data["_summary_stats"] = summary_stats

        return output_data

    def _json_serializer(self, obj: Any) -> Any:
        """
        Custom JSON serializer for non-standard types.

        Args:
            obj: Object to serialize

        Returns:
            JSON-serializable representation of the object

        Raises:
            TypeError: If the object cannot be serialized
        """
        if isinstance(obj, datetime):
            return obj.isoformat()
        if hasattr(obj, "model_dump"):
            return obj.model_dump(mode="json")
        if hasattr(obj, "__dict__"):
            return obj.__dict__

        raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")
