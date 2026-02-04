"""Tests for base output formatter module."""

from io import StringIO

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
def sample_service_result(sample_resource_change):
    """Create a sample service comparison result."""
    comparison = ResourceTypeComparison(
        resource_type="buckets",
        account1_count=5,
        account2_count=6,
        added=[],
        removed=[],
        modified=[sample_resource_change],
        unchanged_count=4,
    )
    return ServiceComparisonResult(
        service_name="s3",
        resource_comparisons={"buckets": comparison},
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


class TestBaseFormatterWriteToStream:
    """Tests for write_to_stream method."""

    def test_write_to_stream_default_stdout(self, sample_report):
        """Test writing to default stdout."""
        from unittest.mock import patch

        formatter = JSONFormatter()

        # Capture stdout
        mock_stdout = StringIO()
        with patch("sys.stdout", mock_stdout):
            formatter.write_to_stream(sample_report)

        output = mock_stdout.getvalue()
        assert "123456789012" in output
        assert output.endswith("\n")

    def test_write_to_stream_custom_stream(self, sample_report):
        """Test writing to custom stream."""
        formatter = JSONFormatter()
        stream = StringIO()

        formatter.write_to_stream(sample_report, stream=stream)

        output = stream.getvalue()
        assert "123456789012" in output
        assert output.endswith("\n")

    def test_write_to_stream_flushes(self, sample_report):
        """Test that stream is flushed after writing."""
        from unittest.mock import MagicMock

        formatter = JSONFormatter()
        stream = MagicMock()
        stream.write = MagicMock()
        stream.flush = MagicMock()

        formatter.write_to_stream(sample_report, stream=stream)

        stream.flush.assert_called_once()


class TestBaseFormatterGetAllChanges:
    """Tests for _get_all_changes method."""

    def test_get_all_changes_from_report(self, sample_report):
        """Test extracting all changes from ComparisonReport."""
        formatter = JSONFormatter()

        changes = formatter._get_all_changes(sample_report)

        assert len(changes) == 1
        assert changes[0].resource_id == "test-bucket"

    def test_get_all_changes_from_service_result(self, sample_service_result):
        """Test extracting all changes from ServiceComparisonResult."""
        formatter = JSONFormatter()

        changes = formatter._get_all_changes(sample_service_result)

        assert len(changes) == 1
        assert changes[0].resource_id == "test-bucket"

    def test_get_all_changes_empty_report(self):
        """Test extracting changes from empty report."""
        empty_comparison = ResourceTypeComparison(
            resource_type="buckets",
            account1_count=0,
            account2_count=0,
            added=[],
            removed=[],
            modified=[],
            unchanged_count=0,
        )
        service_result = ServiceComparisonResult(
            service_name="s3",
            resource_comparisons={"buckets": empty_comparison},
            errors=[],
            execution_time_seconds=1.0,
        )
        report = ComparisonReport(
            account1_id="123456789012",
            account2_id="987654321098",
            region="us-east-1",
            services_compared=["s3"],
            results=[service_result],
            summary=ReportSummary(
                total_services_compared=1,
                total_services_with_changes=0,
                total_changes=0,
                total_resources_account1=0,
                total_resources_account2=0,
                execution_time_seconds=1.0,
            ),
        )

        formatter = JSONFormatter()
        changes = formatter._get_all_changes(report)

        assert len(changes) == 0

    def test_get_all_changes_multiple_types(self, sample_resource_change):
        """Test extracting changes with multiple change types."""
        added_change = ResourceChange(
            change_type=ChangeType.ADDED,
            resource_id="new-bucket",
            resource_type="bucket",
            field_path=None,
            old_value=None,
            new_value={"name": "new-bucket"},
            description="Added bucket",
        )
        removed_change = ResourceChange(
            change_type=ChangeType.REMOVED,
            resource_id="old-bucket",
            resource_type="bucket",
            field_path=None,
            old_value={"name": "old-bucket"},
            new_value=None,
            description="Removed bucket",
        )
        comparison = ResourceTypeComparison(
            resource_type="buckets",
            account1_count=5,
            account2_count=5,
            added=[added_change],
            removed=[removed_change],
            modified=[sample_resource_change],
            unchanged_count=3,
        )
        service_result = ServiceComparisonResult(
            service_name="s3",
            resource_comparisons={"buckets": comparison},
            errors=[],
            execution_time_seconds=1.0,
        )

        formatter = JSONFormatter()
        changes = formatter._get_all_changes(service_result)

        assert len(changes) == 3


class TestBaseFormatterGenerateSummaryStats:
    """Tests for _generate_summary_stats method."""

    def test_generate_summary_stats(self, sample_report):
        """Test generating summary statistics."""
        formatter = JSONFormatter()

        stats = formatter._generate_summary_stats(sample_report)

        assert "total_changes" in stats
        assert "changes_by_type" in stats
        assert "changes_by_severity" in stats
        assert stats["total_changes"] == 1

    def test_generate_summary_stats_empty(self):
        """Test generating summary stats for empty report."""
        empty_comparison = ResourceTypeComparison(
            resource_type="buckets",
            account1_count=0,
            account2_count=0,
            added=[],
            removed=[],
            modified=[],
            unchanged_count=0,
        )
        service_result = ServiceComparisonResult(
            service_name="s3",
            resource_comparisons={"buckets": empty_comparison},
            errors=[],
            execution_time_seconds=1.0,
        )
        report = ComparisonReport(
            account1_id="123456789012",
            account2_id="987654321098",
            region="us-east-1",
            services_compared=["s3"],
            results=[service_result],
            summary=ReportSummary(
                total_services_compared=1,
                total_services_with_changes=0,
                total_changes=0,
                total_resources_account1=0,
                total_resources_account2=0,
                execution_time_seconds=1.0,
            ),
        )

        formatter = JSONFormatter()
        stats = formatter._generate_summary_stats(report)

        assert stats["total_changes"] == 0


class TestBaseFormatterIsComparisonReport:
    """Tests for _is_comparison_report method."""

    def test_is_comparison_report_true(self, sample_report):
        """Test identifying a ComparisonReport."""
        formatter = JSONFormatter()

        result = formatter._is_comparison_report(sample_report)

        assert result is True

    def test_is_comparison_report_false(self, sample_service_result):
        """Test identifying a ServiceComparisonResult."""
        formatter = JSONFormatter()

        result = formatter._is_comparison_report(sample_service_result)

        assert result is False


class TestBaseFormatterGetServiceChanges:
    """Tests for _get_service_changes method."""

    def test_get_service_changes(self, sample_service_result):
        """Test extracting changes from a service result."""
        formatter = JSONFormatter()

        changes = formatter._get_service_changes(sample_service_result)

        assert len(changes) == 1
        assert changes[0].resource_id == "test-bucket"

    def test_get_service_changes_empty(self):
        """Test extracting changes from empty service result."""
        empty_comparison = ResourceTypeComparison(
            resource_type="buckets",
            account1_count=0,
            account2_count=0,
            added=[],
            removed=[],
            modified=[],
            unchanged_count=0,
        )
        service_result = ServiceComparisonResult(
            service_name="s3",
            resource_comparisons={"buckets": empty_comparison},
            errors=[],
            execution_time_seconds=1.0,
        )

        formatter = JSONFormatter()
        changes = formatter._get_service_changes(service_result)

        assert len(changes) == 0


class TestBaseFormatterStr:
    """Tests for __str__ and __repr__ methods."""

    def test_str(self):
        """Test string representation."""
        formatter = JSONFormatter()

        result = str(formatter)

        assert "JSONFormatter" in result

    def test_repr(self):
        """Test repr representation."""
        formatter = JSONFormatter()

        result = repr(formatter)

        assert "JSONFormatter" in result
