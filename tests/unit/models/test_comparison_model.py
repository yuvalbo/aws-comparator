"""Tests for comparison models."""
import pytest

from aws_comparator.models.comparison import (
    ChangeSeverity,
    ChangeType,
    ComparisonReport,
    ReportSummary,
    ResourceChange,
    ResourceTypeComparison,
    ServiceComparisonResult,
    ServiceError,
)


class TestChangeType:
    """Tests for ChangeType enum."""

    def test_change_type_values(self):
        """Test ChangeType has expected values."""
        assert ChangeType.ADDED.value == "added"
        assert ChangeType.REMOVED.value == "removed"
        assert ChangeType.MODIFIED.value == "modified"
        assert ChangeType.NO_CHANGE.value == "no_change"


class TestChangeSeverity:
    """Tests for ChangeSeverity enum."""

    def test_change_severity_values(self):
        """Test ChangeSeverity has expected values."""
        assert ChangeSeverity.CRITICAL.value == "critical"
        assert ChangeSeverity.HIGH.value == "high"
        assert ChangeSeverity.MEDIUM.value == "medium"
        assert ChangeSeverity.LOW.value == "low"
        assert ChangeSeverity.INFO.value == "info"


class TestResourceChange:
    """Tests for ResourceChange model."""

    def test_create_resource_change(self):
        """Test creating a resource change."""
        change = ResourceChange(
            change_type=ChangeType.MODIFIED,
            resource_id="test-resource",
            resource_type="bucket",
            field_path="versioning",
            old_value="Disabled",
            new_value="Enabled",
            severity=ChangeSeverity.HIGH,
            description="Versioning enabled",
        )

        assert change.change_type == ChangeType.MODIFIED
        assert change.resource_id == "test-resource"
        assert change.resource_type == "bucket"
        assert change.field_path == "versioning"
        assert change.old_value == "Disabled"
        assert change.new_value == "Enabled"
        assert change.severity == ChangeSeverity.HIGH
        assert change.description == "Versioning enabled"

    def test_resource_change_defaults(self):
        """Test ResourceChange with defaults."""
        change = ResourceChange(
            change_type=ChangeType.ADDED,
            resource_id="new-resource",
            resource_type="instance",
            field_path=None,
            old_value=None,
            new_value={"id": "123"},
            description="New resource",
        )

        assert change.severity == ChangeSeverity.INFO
        assert change.field_path is None

    def test_resource_change_str_added(self):
        """Test string representation for added resource."""
        change = ResourceChange(
            change_type=ChangeType.ADDED,
            resource_id="new-resource",
            resource_type="bucket",
            field_path=None,
            old_value=None,
            new_value={},
            description="Added",
        )

        result = str(change)
        assert "Added" in result
        assert "bucket" in result

    def test_resource_change_str_removed(self):
        """Test string representation for removed resource."""
        change = ResourceChange(
            change_type=ChangeType.REMOVED,
            resource_id="old-resource",
            resource_type="bucket",
            field_path=None,
            old_value={},
            new_value=None,
            description="Removed",
        )

        result = str(change)
        assert "Removed" in result

    def test_resource_change_str_modified(self):
        """Test string representation for modified resource."""
        change = ResourceChange(
            change_type=ChangeType.MODIFIED,
            resource_id="test-resource",
            resource_type="bucket",
            field_path="versioning",
            old_value="Disabled",
            new_value="Enabled",
            description="Modified",
        )

        result = str(change)
        assert "Modified" in result
        assert "versioning" in result


class TestResourceTypeComparison:
    """Tests for ResourceTypeComparison model."""

    def test_create_resource_type_comparison(self):
        """Test creating a resource type comparison."""
        comparison = ResourceTypeComparison(
            resource_type="buckets",
            account1_count=5,
            account2_count=6,
            added=[],
            removed=[],
            modified=[],
            unchanged_count=5,
        )

        assert comparison.resource_type == "buckets"
        assert comparison.account1_count == 5
        assert comparison.account2_count == 6
        assert comparison.unchanged_count == 5

    def test_total_changes_computed(self):
        """Test total_changes is computed correctly."""
        change = ResourceChange(
            change_type=ChangeType.ADDED,
            resource_id="test",
            resource_type="bucket",
            field_path=None,
            old_value=None,
            new_value={},
            description="Added",
        )

        comparison = ResourceTypeComparison(
            resource_type="buckets",
            account1_count=1,
            account2_count=2,
            added=[change],
            removed=[],
            modified=[change, change],
            unchanged_count=0,
        )

        assert comparison.total_changes == 3

    def test_has_changes_true(self):
        """Test has_changes returns True when changes exist."""
        change = ResourceChange(
            change_type=ChangeType.ADDED,
            resource_id="test",
            resource_type="bucket",
            field_path=None,
            old_value=None,
            new_value={},
            description="Added",
        )

        comparison = ResourceTypeComparison(
            resource_type="buckets",
            account1_count=0,
            account2_count=1,
            added=[change],
            removed=[],
            modified=[],
            unchanged_count=0,
        )

        assert comparison.has_changes is True

    def test_has_changes_false(self):
        """Test has_changes returns False when no changes exist."""
        comparison = ResourceTypeComparison(
            resource_type="buckets",
            account1_count=5,
            account2_count=5,
            added=[],
            removed=[],
            modified=[],
            unchanged_count=5,
        )

        assert comparison.has_changes is False


class TestServiceComparisonResult:
    """Tests for ServiceComparisonResult model."""

    def test_create_service_comparison_result(self):
        """Test creating a service comparison result."""
        result = ServiceComparisonResult(
            service_name="s3",
            resource_comparisons={},
            errors=[],
            execution_time_seconds=1.5,
        )

        assert result.service_name == "s3"
        assert result.execution_time_seconds == 1.5
        assert result.timestamp is not None

    def test_total_changes_across_types(self):
        """Test total_changes sums across resource types."""
        change = ResourceChange(
            change_type=ChangeType.ADDED,
            resource_id="test",
            resource_type="bucket",
            field_path=None,
            old_value=None,
            new_value={},
            description="Added",
        )

        comparison = ResourceTypeComparison(
            resource_type="buckets",
            account1_count=0,
            account2_count=1,
            added=[change],
            removed=[],
            modified=[],
            unchanged_count=0,
        )

        result = ServiceComparisonResult(
            service_name="s3",
            resource_comparisons={"buckets": comparison},
            errors=[],
            execution_time_seconds=1.0,
        )

        assert result.total_changes == 1

    def test_has_errors(self):
        """Test has_errors property."""
        result_with_errors = ServiceComparisonResult(
            service_name="s3",
            resource_comparisons={},
            errors=["Error 1"],
            execution_time_seconds=1.0,
        )

        result_without_errors = ServiceComparisonResult(
            service_name="s3",
            resource_comparisons={},
            errors=[],
            execution_time_seconds=1.0,
        )

        assert result_with_errors.has_errors is True
        assert result_without_errors.has_errors is False


class TestReportSummary:
    """Tests for ReportSummary model."""

    def test_create_report_summary(self):
        """Test creating a report summary."""
        summary = ReportSummary(
            total_services_compared=5,
            total_services_with_changes=2,
            total_changes=10,
            total_resources_account1=100,
            total_resources_account2=105,
            execution_time_seconds=5.0,
        )

        assert summary.total_services_compared == 5
        assert summary.total_services_with_changes == 2
        assert summary.total_changes == 10
        assert summary.execution_time_seconds == 5.0

    def test_report_summary_defaults(self):
        """Test ReportSummary default values."""
        summary = ReportSummary(
            total_services_compared=1,
            total_services_with_changes=0,
            total_changes=0,
            total_resources_account1=0,
            total_resources_account2=0,
            execution_time_seconds=1.0,
        )

        assert summary.services_with_errors == []
        # changes_by_severity should have all severity levels
        assert ChangeSeverity.CRITICAL.value in summary.changes_by_severity


class TestServiceError:
    """Tests for ServiceError model."""

    def test_create_service_error(self):
        """Test creating a service error."""
        error = ServiceError(
            service_name="s3",
            error_type="AccessDenied",
            error_message="Access denied to S3",
            error_code="403",
            traceback=None,
        )

        assert error.service_name == "s3"
        assert error.error_type == "AccessDenied"
        assert error.error_message == "Access denied to S3"
        assert error.error_code == "403"
        assert error.timestamp is not None

    def test_service_error_str(self):
        """Test ServiceError string representation."""
        error = ServiceError(
            service_name="ec2",
            error_type="InvalidCredentials",
            error_message="Invalid credentials",
            error_code=None,
            traceback=None,
        )

        result = str(error)
        assert "ec2" in result
        assert "InvalidCredentials" in result


class TestComparisonReport:
    """Tests for ComparisonReport model."""

    def test_create_comparison_report(self):
        """Test creating a comparison report."""
        summary = ReportSummary(
            total_services_compared=1,
            total_services_with_changes=0,
            total_changes=0,
            total_resources_account1=5,
            total_resources_account2=5,
            execution_time_seconds=1.0,
        )

        report = ComparisonReport(
            account1_id="123456789012",
            account2_id="987654321098",
            region="us-east-1",
            services_compared=["s3"],
            results=[],
            summary=summary,
        )

        assert report.account1_id == "123456789012"
        assert report.account2_id == "987654321098"
        assert report.region == "us-east-1"
        assert "s3" in report.services_compared

    def test_comparison_report_invalid_account_id(self):
        """Test ComparisonReport rejects invalid account ID."""
        summary = ReportSummary(
            total_services_compared=0,
            total_services_with_changes=0,
            total_changes=0,
            total_resources_account1=0,
            total_resources_account2=0,
            execution_time_seconds=0.0,
        )

        with pytest.raises(ValueError):
            ComparisonReport(
                account1_id="invalid",
                account2_id="987654321098",
                region="us-east-1",
                services_compared=[],
                results=[],
                summary=summary,
            )

    def test_get_service_result(self):
        """Test get_service_result method."""
        result = ServiceComparisonResult(
            service_name="s3",
            resource_comparisons={},
            errors=[],
            execution_time_seconds=1.0,
        )

        summary = ReportSummary(
            total_services_compared=1,
            total_services_with_changes=0,
            total_changes=0,
            total_resources_account1=0,
            total_resources_account2=0,
            execution_time_seconds=1.0,
        )

        report = ComparisonReport(
            account1_id="123456789012",
            account2_id="987654321098",
            region="us-east-1",
            services_compared=["s3"],
            results=[result],
            summary=summary,
        )

        assert report.get_service_result("s3") == result
        assert report.get_service_result("ec2") is None

    def test_to_dict(self):
        """Test to_dict method."""
        summary = ReportSummary(
            total_services_compared=0,
            total_services_with_changes=0,
            total_changes=0,
            total_resources_account1=0,
            total_resources_account2=0,
            execution_time_seconds=0.0,
        )

        report = ComparisonReport(
            account1_id="123456789012",
            account2_id="987654321098",
            region="us-east-1",
            services_compared=[],
            results=[],
            summary=summary,
        )

        result = report.to_dict()

        assert isinstance(result, dict)
        assert result["account1_id"] == "123456789012"
        assert result["region"] == "us-east-1"
