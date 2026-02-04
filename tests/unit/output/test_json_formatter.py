"""Tests for JSON formatter module."""
import json
from datetime import datetime

import pytest

from aws_comparator.models.comparison import (
    ChangeSeverity,
    ChangeType,
    ComparisonReport,
    ReportSummary,
    ResourceChange,
    ResourceTypeComparison,
    ServiceComparisonResult,
)
from aws_comparator.output.formatters.json_formatter import JSONFormatter


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


class TestJSONFormatterInit:
    """Tests for JSONFormatter initialization."""

    def test_default_init(self):
        """Test formatter with default options."""
        formatter = JSONFormatter()
        assert formatter.indent == 2
        assert formatter.sort_keys is False
        assert formatter.include_summary is True
        assert formatter.ensure_ascii is False

    def test_custom_indent(self):
        """Test formatter with custom indent."""
        formatter = JSONFormatter(indent=4)
        assert formatter.indent == 4

    def test_compact_output(self):
        """Test formatter with no indentation (compact)."""
        formatter = JSONFormatter(indent=None)
        assert formatter.indent is None

    def test_sort_keys_option(self):
        """Test formatter with sorted keys."""
        formatter = JSONFormatter(sort_keys=True)
        assert formatter.sort_keys is True

    def test_no_summary(self):
        """Test formatter without summary."""
        formatter = JSONFormatter(include_summary=False)
        assert formatter.include_summary is False

    def test_ensure_ascii(self):
        """Test formatter with ASCII encoding."""
        formatter = JSONFormatter(ensure_ascii=True)
        assert formatter.ensure_ascii is True


class TestJSONFormatterFormat:
    """Tests for JSONFormatter.format() method."""

    def test_format_returns_valid_json(self, sample_report):
        """Test format() returns valid JSON string."""
        formatter = JSONFormatter()
        result = formatter.format(sample_report)

        # Should be valid JSON
        parsed = json.loads(result)
        assert isinstance(parsed, dict)

    def test_format_includes_account_ids(self, sample_report):
        """Test format() includes account IDs."""
        formatter = JSONFormatter()
        result = formatter.format(sample_report)
        parsed = json.loads(result)

        assert parsed["account1_id"] == "123456789012"
        assert parsed["account2_id"] == "987654321098"

    def test_format_includes_region(self, sample_report):
        """Test format() includes region."""
        formatter = JSONFormatter()
        result = formatter.format(sample_report)
        parsed = json.loads(result)

        assert parsed["region"] == "us-east-1"

    def test_format_includes_services(self, sample_report):
        """Test format() includes services compared."""
        formatter = JSONFormatter()
        result = formatter.format(sample_report)
        parsed = json.loads(result)

        assert "s3" in parsed["services_compared"]

    def test_format_includes_summary_stats(self, sample_report):
        """Test format() includes summary statistics when enabled."""
        formatter = JSONFormatter(include_summary=True)
        result = formatter.format(sample_report)
        parsed = json.loads(result)

        assert "_summary_stats" in parsed
        assert "total_changes" in parsed["_summary_stats"]

    def test_format_excludes_summary_stats(self, sample_report):
        """Test format() excludes summary statistics when disabled."""
        formatter = JSONFormatter(include_summary=False)
        result = formatter.format(sample_report)
        parsed = json.loads(result)

        assert "_summary_stats" not in parsed

    def test_format_compact_output(self, sample_report):
        """Test format() produces compact output when indent is None."""
        formatter = JSONFormatter(indent=None)
        result = formatter.format(sample_report)

        # Compact JSON should not have newlines
        assert "\n" not in result.strip()

    def test_format_sorted_keys(self, sample_report):
        """Test format() sorts keys when enabled."""
        formatter = JSONFormatter(sort_keys=True)
        result = formatter.format(sample_report)

        # Should be valid JSON with sorted keys
        parsed = json.loads(result)
        assert isinstance(parsed, dict)

    def test_format_service_result(self, sample_service_result):
        """Test format() works with ServiceComparisonResult."""
        formatter = JSONFormatter()
        result = formatter.format(sample_service_result)
        parsed = json.loads(result)

        assert parsed["service_name"] == "s3"
        assert "resource_comparisons" in parsed


class TestJSONFormatterWriteToFile:
    """Tests for JSONFormatter.write_to_file() method."""

    def test_write_to_file_creates_file(self, sample_report, tmp_path):
        """Test write_to_file() creates the output file."""
        formatter = JSONFormatter()
        filepath = tmp_path / "report.json"

        formatter.write_to_file(sample_report, filepath)

        assert filepath.exists()

    def test_write_to_file_valid_json(self, sample_report, tmp_path):
        """Test write_to_file() produces valid JSON file."""
        formatter = JSONFormatter()
        filepath = tmp_path / "report.json"

        formatter.write_to_file(sample_report, filepath)

        with open(filepath) as f:
            parsed = json.load(f)

        assert isinstance(parsed, dict)
        assert parsed["account1_id"] == "123456789012"

    def test_write_to_file_creates_parent_dirs(self, sample_report, tmp_path):
        """Test write_to_file() creates parent directories."""
        formatter = JSONFormatter()
        filepath = tmp_path / "nested" / "dir" / "report.json"

        formatter.write_to_file(sample_report, filepath)

        assert filepath.exists()

    def test_write_to_file_overwrites_existing(self, sample_report, tmp_path):
        """Test write_to_file() overwrites existing file."""
        formatter = JSONFormatter()
        filepath = tmp_path / "report.json"

        # Create initial file
        filepath.write_text('{"old": "content"}')

        # Overwrite
        formatter.write_to_file(sample_report, filepath)

        with open(filepath) as f:
            parsed = json.load(f)

        assert "old" not in parsed
        assert "account1_id" in parsed


class TestJSONFormatterSerializer:
    """Tests for custom JSON serializer."""

    def test_serialize_datetime(self):
        """Test datetime objects are serialized to ISO format."""
        formatter = JSONFormatter()
        dt = datetime(2024, 1, 15, 10, 30, 45)
        result = formatter._json_serializer(dt)

        assert result == "2024-01-15T10:30:45"

    def test_serialize_pydantic_model(self):
        """Test Pydantic models are serialized via model_dump."""
        formatter = JSONFormatter()
        change = ResourceChange(
            change_type=ChangeType.ADDED,
            resource_id="test",
            resource_type="bucket",
            field_path=None,
            old_value=None,
            new_value={"name": "test-bucket"},
            description="Resource added",
        )
        result = formatter._json_serializer(change)

        assert isinstance(result, dict)
        assert result["resource_id"] == "test"

    def test_serialize_object_with_dict(self):
        """Test objects with __dict__ are serialized."""
        formatter = JSONFormatter()

        class SimpleObj:
            def __init__(self):
                self.name = "test"
                self.value = 42

        obj = SimpleObj()
        result = formatter._json_serializer(obj)

        assert result == {"name": "test", "value": 42}

    def test_serialize_unsupported_type(self):
        """Test unsupported types raise TypeError."""
        formatter = JSONFormatter()

        with pytest.raises(TypeError) as exc_info:
            formatter._json_serializer({1, 2, 3})

        assert "not JSON serializable" in str(exc_info.value)


class TestJSONFormatterBuildOutputData:
    """Tests for _build_output_data method."""

    def test_build_output_data_comparison_report(self, sample_report):
        """Test building output data from ComparisonReport."""
        formatter = JSONFormatter()
        result = formatter._build_output_data(sample_report)

        assert isinstance(result, dict)
        assert "account1_id" in result
        assert "results" in result

    def test_build_output_data_service_result(self, sample_service_result):
        """Test building output data from ServiceComparisonResult."""
        formatter = JSONFormatter()
        result = formatter._build_output_data(sample_service_result)

        assert isinstance(result, dict)
        assert "service_name" in result
        assert result["service_name"] == "s3"

    def test_build_output_data_includes_summary(self, sample_report):
        """Test summary stats are included when enabled."""
        formatter = JSONFormatter(include_summary=True)
        result = formatter._build_output_data(sample_report)

        assert "_summary_stats" in result
        assert "total_changes" in result["_summary_stats"]
        assert "changes_by_type" in result["_summary_stats"]
        assert "changes_by_severity" in result["_summary_stats"]

    def test_build_output_data_no_summary(self, sample_report):
        """Test summary stats are excluded when disabled."""
        formatter = JSONFormatter(include_summary=False)
        result = formatter._build_output_data(sample_report)

        assert "_summary_stats" not in result


class TestJSONFormatterErrorHandling:
    """Tests for error handling in JSONFormatter."""

    def test_format_raises_on_error(self, sample_report):
        """Test format raises exception on serialization error."""
        from unittest.mock import patch

        formatter = JSONFormatter()

        # Create a mock report that causes serialization to fail
        with patch.object(
            formatter, "_build_output_data", side_effect=ValueError("Mock error")
        ):
            with pytest.raises(ValueError, match="Mock error"):
                formatter.format(sample_report)

    def test_write_to_file_os_error(self, sample_report, tmp_path):
        """Test write_to_file handles OSError."""
        from unittest.mock import patch

        formatter = JSONFormatter()
        filepath = tmp_path / "report.json"

        with patch("builtins.open", side_effect=OSError("Permission denied")):
            with pytest.raises(OSError):
                formatter.write_to_file(sample_report, filepath)

    def test_write_to_file_serialization_error(self, sample_report, tmp_path):
        """Test write_to_file handles serialization errors."""
        from unittest.mock import patch

        formatter = JSONFormatter()
        filepath = tmp_path / "report.json"

        # Patch json.dump to raise a serialization error
        with patch("json.dump", side_effect=TypeError("Not serializable")):
            with pytest.raises(TypeError):
                formatter.write_to_file(sample_report, filepath)
