"""
Output formatters for AWS comparison reports.

This module exports all available formatters for rendering comparison
reports in different formats.

Available formatters:
- JSONFormatter: Output as JSON with configurable formatting
- YAMLFormatter: Output as YAML with configurable formatting
- TableFormatter: Rich console table output with color-coded severity

Example:
    >>> from aws_comparator.output.formatters import JSONFormatter, get_formatter
    >>>
    >>> # Direct usage
    >>> formatter = JSONFormatter(indent=4)
    >>> output = formatter.format(report)
    >>>
    >>> # Factory usage
    >>> formatter = get_formatter("json")
    >>> formatter.write_to_file(report, Path("report.json"))
"""

from typing import Any

from aws_comparator.output.formatters.json_formatter import JSONFormatter
from aws_comparator.output.formatters.table_formatter import TableFormatter
from aws_comparator.output.formatters.yaml_formatter import YAMLFormatter

# Formatter type registry
FORMATTER_TYPES: dict[str, type[JSONFormatter | YAMLFormatter | TableFormatter]] = {
    "json": JSONFormatter,
    "yaml": YAMLFormatter,
    "yml": YAMLFormatter,
    "table": TableFormatter,
    "console": TableFormatter,
}


def get_formatter(
    format_type: str,
    **options: Any,
) -> JSONFormatter | YAMLFormatter | TableFormatter:
    """
    Factory function to get a formatter by type name.

    Args:
        format_type: The format type ("json", "yaml", "yml", "table", "console")
        **options: Formatter-specific options passed to the constructor

    Returns:
        Configured formatter instance

    Raises:
        ValueError: If the format type is not recognized

    Example:
        >>> formatter = get_formatter("json", indent=4)
        >>> formatter = get_formatter("yaml", default_flow_style=False)
        >>> formatter = get_formatter("table", use_colors=True)
    """
    format_type_lower = format_type.lower()

    if format_type_lower not in FORMATTER_TYPES:
        available = ", ".join(sorted(FORMATTER_TYPES.keys()))
        raise ValueError(
            f"Unknown format type: {format_type!r}. Available types: {available}"
        )

    formatter_class = FORMATTER_TYPES[format_type_lower]
    return formatter_class(**options)


def list_formatters() -> list[str]:
    """
    List all available formatter type names.

    Returns:
        Sorted list of available format type names

    Example:
        >>> formats = list_formatters()
        >>> print(formats)
        ['console', 'json', 'table', 'yaml', 'yml']
    """
    return sorted(FORMATTER_TYPES.keys())


__all__ = [
    "JSONFormatter",
    "YAMLFormatter",
    "TableFormatter",
    "get_formatter",
    "list_formatters",
    "FORMATTER_TYPES",
]
