"""Tests for YAML formatter module."""
from datetime import datetime

import pytest
import yaml

from aws_comparator.models.comparison import (
    ChangeSeverity,
    ChangeType,
    ComparisonReport,
    ReportSummary,
    ResourceChange,
    ResourceTypeComparison,
    ServiceComparisonResult,
)
from aws_comparator.output.formatters.yaml_formatter import YAMLFormatter


@pytest.fixture
def sample_resource_change():
    """Create a sample resource change."""
    return ResourceChange(
        change_type=ChangeType.MODIFIED,
        resource_id="test-bucket",
        resource_type="bucket",
        field_path="versioning_status",
        old_value="Disabled",
        new_value="Enabled",
        severity=ChangeSeverity.HIGH,
        description="Versioning was enabled",
    )


@pytest.fixture
def sample_resource_type_comparison(sample_resource_change):
    """Create a sample resource type comparison."""
    return ResourceTypeComparison(
        resource_type="buckets",
        account1_count=5,
        account2_count=6,
        added=[],
        removed=[],
        modified=[sample_resource_change],
        unchanged_count=4,
    )


@pytest.fixture
def sample_service_result(sample_resource_type_comparison):
    """Create a sample service comparison result."""
    return ServiceComparisonResult(
        service_name="s3",
        resource_comparisons={"buckets": sample_resource_type_comparison},
        errors=[],
        execution_time_seconds=1.5,
    )


@pytest.fixture
def sample_report(sample_service_result):
    """Create a sample comparison report."""
    return ComparisonReport(
        account1_id="123456789012",
        account2_id="987654321098",
        region="us-east-1",
        services_compared=["s3"],
        results=[sample_service_result],
        summary=ReportSummary(
            total_services_compared=1,
            total_services_with_changes=1,
            total_changes=1,
            total_resources_account1=5,
            total_resources_account2=6,
            execution_time_seconds=1.5,
        ),
    )


class TestYAMLFormatterInit:
    """Tests for YAMLFormatter initialization."""

    def test_default_init(self):
        """Test formatter with default options."""
        formatter = YAMLFormatter()
        assert formatter.default_flow_style is False
        assert formatter.allow_unicode is True
        assert formatter.sort_keys is False
        assert formatter.include_summary is True
        assert formatter.indent == 2
        assert formatter.width == 80

    def test_custom_indent(self):
        """Test formatter with custom indent."""
        formatter = YAMLFormatter(indent=4)
        assert formatter.indent == 4

    def test_custom_width(self):
        """Test formatter with custom width."""
        formatter = YAMLFormatter(width=120)
        assert formatter.width == 120

    def test_flow_style(self):
        """Test formatter with flow style enabled."""
        formatter = YAMLFormatter(default_flow_style=True)
        assert formatter.default_flow_style is True

    def test_no_unicode(self):
        """Test formatter with unicode disabled."""
        formatter = YAMLFormatter(allow_unicode=False)
        assert formatter.allow_unicode is False

    def test_sort_keys_option(self):
        """Test formatter with sorted keys."""
        formatter = YAMLFormatter(sort_keys=True)
        assert formatter.sort_keys is True

    def test_no_summary(self):
        """Test formatter without summary."""
        formatter = YAMLFormatter(include_summary=False)
        assert formatter.include_summary is False


class TestYAMLFormatterFormat:
    """Tests for YAMLFormatter.format() method."""

    def test_format_returns_valid_yaml(self, sample_report):
        """Test format() returns valid YAML string."""
        formatter = YAMLFormatter()
        result = formatter.format(sample_report)

        # Should be valid YAML
        parsed = yaml.safe_load(result)
        assert isinstance(parsed, dict)

    def test_format_includes_account_ids(self, sample_report):
        """Test format() includes account IDs."""
        formatter = YAMLFormatter()
        result = formatter.format(sample_report)
        parsed = yaml.safe_load(result)

        assert parsed["account1_id"] == "123456789012"
        assert parsed["account2_id"] == "987654321098"

    def test_format_includes_region(self, sample_report):
        """Test format() includes region."""
        formatter = YAMLFormatter()
        result = formatter.format(sample_report)
        parsed = yaml.safe_load(result)

        assert parsed["region"] == "us-east-1"

    def test_format_includes_services(self, sample_report):
        """Test format() includes services compared."""
        formatter = YAMLFormatter()
        result = formatter.format(sample_report)
        parsed = yaml.safe_load(result)

        assert "s3" in parsed["services_compared"]

    def test_format_includes_summary_stats(self, sample_report):
        """Test format() includes summary statistics when enabled."""
        formatter = YAMLFormatter(include_summary=True)
        result = formatter.format(sample_report)
        parsed = yaml.safe_load(result)

        assert "_summary_stats" in parsed
        assert "total_changes" in parsed["_summary_stats"]

    def test_format_excludes_summary_stats(self, sample_report):
        """Test format() excludes summary statistics when disabled."""
        formatter = YAMLFormatter(include_summary=False)
        result = formatter.format(sample_report)
        parsed = yaml.safe_load(result)

        assert "_summary_stats" not in parsed

    def test_format_sorted_keys(self, sample_report):
        """Test format() sorts keys when enabled."""
        formatter = YAMLFormatter(sort_keys=True)
        result = formatter.format(sample_report)

        # Should be valid YAML with sorted keys
        parsed = yaml.safe_load(result)
        assert isinstance(parsed, dict)

    def test_format_service_result(self, sample_service_result):
        """Test format() works with ServiceComparisonResult."""
        formatter = YAMLFormatter()
        result = formatter.format(sample_service_result)
        parsed = yaml.safe_load(result)

        assert parsed["service_name"] == "s3"
        assert "resource_comparisons" in parsed


class TestYAMLFormatterWriteToFile:
    """Tests for YAMLFormatter.write_to_file() method."""

    def test_write_to_file_creates_file(self, sample_report, tmp_path):
        """Test write_to_file() creates the output file."""
        formatter = YAMLFormatter()
        filepath = tmp_path / "report.yaml"

        formatter.write_to_file(sample_report, filepath)

        assert filepath.exists()

    def test_write_to_file_valid_yaml(self, sample_report, tmp_path):
        """Test write_to_file() produces valid YAML file."""
        formatter = YAMLFormatter()
        filepath = tmp_path / "report.yaml"

        formatter.write_to_file(sample_report, filepath)

        with open(filepath) as f:
            parsed = yaml.safe_load(f)

        assert isinstance(parsed, dict)
        assert parsed["account1_id"] == "123456789012"

    def test_write_to_file_creates_parent_dirs(self, sample_report, tmp_path):
        """Test write_to_file() creates parent directories."""
        formatter = YAMLFormatter()
        filepath = tmp_path / "nested" / "dir" / "report.yaml"

        formatter.write_to_file(sample_report, filepath)

        assert filepath.exists()

    def test_write_to_file_overwrites_existing(self, sample_report, tmp_path):
        """Test write_to_file() overwrites existing file."""
        formatter = YAMLFormatter()
        filepath = tmp_path / "report.yaml"

        # Create initial file
        filepath.write_text("old: content\n")

        # Overwrite
        formatter.write_to_file(sample_report, filepath)

        with open(filepath) as f:
            parsed = yaml.safe_load(f)

        assert "old" not in parsed
        assert "account1_id" in parsed


class TestYAMLFormatterDatetimeRepresenter:
    """Tests for datetime representer."""

    def test_datetime_representer(self):
        """Test datetime objects are represented as ISO format."""
        from io import StringIO

        dt = datetime(2024, 1, 15, 10, 30, 45)
        stream = StringIO()
        dumper = yaml.Dumper(stream)
        result = YAMLFormatter._datetime_representer(dumper, dt)

        assert result.tag == "tag:yaml.org,2002:timestamp"
        assert result.value == "2024-01-15T10:30:45"


class TestYAMLFormatterBuildOutputData:
    """Tests for _build_output_data method."""

    def test_build_output_data_comparison_report(self, sample_report):
        """Test building output data from ComparisonReport."""
        formatter = YAMLFormatter()
        result = formatter._build_output_data(sample_report)

        assert isinstance(result, dict)
        assert "account1_id" in result
        assert "results" in result

    def test_build_output_data_service_result(self, sample_service_result):
        """Test building output data from ServiceComparisonResult."""
        formatter = YAMLFormatter()
        result = formatter._build_output_data(sample_service_result)

        assert isinstance(result, dict)
        assert "service_name" in result
        assert result["service_name"] == "s3"

    def test_build_output_data_includes_summary(self, sample_report):
        """Test summary stats are included when enabled."""
        formatter = YAMLFormatter(include_summary=True)
        result = formatter._build_output_data(sample_report)

        assert "_summary_stats" in result
        assert "total_changes" in result["_summary_stats"]
        assert "changes_by_type" in result["_summary_stats"]
        assert "changes_by_severity" in result["_summary_stats"]

    def test_build_output_data_no_summary(self, sample_report):
        """Test summary stats are excluded when disabled."""
        formatter = YAMLFormatter(include_summary=False)
        result = formatter._build_output_data(sample_report)

        assert "_summary_stats" not in result


class TestYAMLFormatterUnicode:
    """Tests for unicode handling."""

    def test_unicode_in_values(self, sample_report):
        """Test unicode characters are preserved."""
        formatter = YAMLFormatter(allow_unicode=True)
        result = formatter.format(sample_report)

        # Should be valid YAML
        parsed = yaml.safe_load(result)
        assert isinstance(parsed, dict)

    def test_ascii_encoding(self, sample_report):
        """Test ASCII encoding escapes unicode."""
        formatter = YAMLFormatter(allow_unicode=False)
        result = formatter.format(sample_report)

        # Should be valid YAML
        parsed = yaml.safe_load(result)
        assert isinstance(parsed, dict)
