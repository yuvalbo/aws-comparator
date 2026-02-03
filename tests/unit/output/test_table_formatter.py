"""Tests for Table formatter module."""
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
from aws_comparator.output.formatters.table_formatter import TableFormatter


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
def sample_added_change():
    """Create a sample added resource change."""
    return ResourceChange(
        change_type=ChangeType.ADDED,
        resource_id="new-bucket",
        resource_type="bucket",
        field_path=None,
        old_value=None,
        new_value={"name": "new-bucket", "region": "us-east-1"},
        severity=ChangeSeverity.HIGH,
        description="Resource exists only in Account 2",
    )


@pytest.fixture
def sample_removed_change():
    """Create a sample removed resource change."""
    return ResourceChange(
        change_type=ChangeType.REMOVED,
        resource_id="old-bucket",
        resource_type="bucket",
        field_path=None,
        old_value={"name": "old-bucket", "region": "us-east-1"},
        new_value=None,
        severity=ChangeSeverity.HIGH,
        description="Resource exists only in Account 1",
    )


@pytest.fixture
def sample_resource_type_comparison(
    sample_resource_change, sample_added_change, sample_removed_change
):
    """Create a sample resource type comparison."""
    return ResourceTypeComparison(
        resource_type="buckets",
        account1_count=5,
        account2_count=5,
        added=[sample_added_change],
        removed=[sample_removed_change],
        modified=[sample_resource_change],
        unchanged_count=3,
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
            total_changes=3,
            total_resources_account1=5,
            total_resources_account2=5,
            execution_time_seconds=1.5,
        ),
    )


class TestTableFormatterInit:
    """Tests for TableFormatter initialization."""

    def test_default_init(self):
        """Test formatter with default options."""
        formatter = TableFormatter()
        assert formatter.show_unchanged is False
        assert formatter.use_colors is True
        assert formatter.max_value_length == 100
        assert formatter.show_details is True
        assert formatter.console_width == 120

    def test_custom_options(self):
        """Test formatter with custom options."""
        formatter = TableFormatter(
            show_unchanged=True,
            use_colors=False,
            max_value_length=50,
            show_details=False,
            console_width=80,
        )
        assert formatter.show_unchanged is True
        assert formatter.use_colors is False
        assert formatter.max_value_length == 50
        assert formatter.show_details is False
        assert formatter.console_width == 80


class TestTableFormatterFormat:
    """Tests for TableFormatter.format() method."""

    def test_format_returns_string(self, sample_report):
        """Test format() returns a string."""
        formatter = TableFormatter()
        result = formatter.format(sample_report)

        assert isinstance(result, str)
        assert len(result) > 0

    def test_format_includes_header(self, sample_report):
        """Test format() includes report header."""
        formatter = TableFormatter(use_colors=False)
        result = formatter.format(sample_report)

        assert "AWS COMPARATOR REPORT" in result

    def test_format_includes_account_ids(self, sample_report):
        """Test format() includes account IDs."""
        formatter = TableFormatter(use_colors=False)
        result = formatter.format(sample_report)

        assert "123456789012" in result
        assert "987654321098" in result

    def test_format_includes_region(self, sample_report):
        """Test format() includes region."""
        formatter = TableFormatter(use_colors=False)
        result = formatter.format(sample_report)

        assert "us-east-1" in result

    def test_format_includes_summary(self, sample_report):
        """Test format() includes summary section."""
        formatter = TableFormatter(use_colors=False)
        result = formatter.format(sample_report)

        assert "SUMMARY" in result
        assert "Total Changes" in result

    def test_format_includes_service_section(self, sample_report):
        """Test format() includes service section."""
        formatter = TableFormatter(use_colors=False)
        result = formatter.format(sample_report)

        assert "S3" in result

    def test_format_includes_added_section(self, sample_report):
        """Test format() includes added resources section."""
        formatter = TableFormatter(use_colors=False)
        result = formatter.format(sample_report)

        assert "ONLY IN ACCOUNT 2" in result

    def test_format_includes_removed_section(self, sample_report):
        """Test format() includes removed resources section."""
        formatter = TableFormatter(use_colors=False)
        result = formatter.format(sample_report)

        assert "ONLY IN ACCOUNT 1" in result

    def test_format_includes_modified_section(self, sample_report):
        """Test format() includes modified resources section."""
        formatter = TableFormatter(use_colors=False)
        result = formatter.format(sample_report)

        assert "DIFFERENT BETWEEN ACCOUNTS" in result

    def test_format_no_colors(self, sample_report):
        """Test format() produces output without ANSI codes when disabled."""
        formatter = TableFormatter(use_colors=False)
        result = formatter.format(sample_report)

        # Should not contain ANSI escape codes
        assert "\x1b[" not in result

    def test_format_service_result(self, sample_service_result):
        """Test format() works with ServiceComparisonResult."""
        formatter = TableFormatter(use_colors=False)
        result = formatter.format(sample_service_result)

        assert "s3" in result.lower()


class TestTableFormatterWriteToFile:
    """Tests for TableFormatter.write_to_file() method."""

    def test_write_to_file_creates_file(self, sample_report, tmp_path):
        """Test write_to_file() creates the output file."""
        formatter = TableFormatter()
        filepath = tmp_path / "report.txt"

        formatter.write_to_file(sample_report, filepath)

        assert filepath.exists()

    def test_write_to_file_no_ansi_codes(self, sample_report, tmp_path):
        """Test write_to_file() produces file without ANSI codes."""
        formatter = TableFormatter(use_colors=True)  # Even with colors enabled
        filepath = tmp_path / "report.txt"

        formatter.write_to_file(sample_report, filepath)

        content = filepath.read_text()
        # File output should not contain ANSI codes
        assert "\x1b[" not in content

    def test_write_to_file_creates_parent_dirs(self, sample_report, tmp_path):
        """Test write_to_file() creates parent directories."""
        formatter = TableFormatter()
        filepath = tmp_path / "nested" / "dir" / "report.txt"

        formatter.write_to_file(sample_report, filepath)

        assert filepath.exists()


class TestTableFormatterStripAnsi:
    """Tests for ANSI code stripping."""

    def test_strip_ansi_removes_codes(self):
        """Test _strip_ansi removes ANSI escape codes."""
        text = "\x1b[31mRed text\x1b[0m Normal text"
        result = TableFormatter._strip_ansi(text)

        assert result == "Red text Normal text"

    def test_strip_ansi_preserves_plain_text(self):
        """Test _strip_ansi preserves plain text."""
        text = "Plain text without any codes"
        result = TableFormatter._strip_ansi(text)

        assert result == text


class TestTableFormatterFormatValue:
    """Tests for value formatting."""

    def test_format_none_value(self):
        """Test formatting None value."""
        formatter = TableFormatter()
        result = formatter._format_value_for_display(None)

        assert result == "(none)"

    def test_format_bool_value(self):
        """Test formatting boolean value."""
        formatter = TableFormatter()
        result_true = formatter._format_value_for_display(True)
        result_false = formatter._format_value_for_display(False)

        assert result_true == "true"
        assert result_false == "false"

    def test_format_int_value(self):
        """Test formatting integer value."""
        formatter = TableFormatter()
        result = formatter._format_value_for_display(42)

        assert result == "42"

    def test_format_string_value(self):
        """Test formatting string value."""
        formatter = TableFormatter()
        result = formatter._format_value_for_display("test string")

        assert result == "test string"

    def test_format_long_string_truncated(self):
        """Test formatting long string is truncated."""
        formatter = TableFormatter(max_value_length=10)
        result = formatter._format_value_for_display("this is a very long string")

        assert len(result) <= 13  # 10 + "..."
        assert result.endswith("...")

    def test_format_dict_with_arn(self):
        """Test formatting dict with ARN extracts ARN."""
        formatter = TableFormatter()
        result = formatter._format_value_for_display(
            {"Arn": "arn:aws:s3:::bucket", "Other": "value"}
        )

        assert "arn:aws:s3:::bucket" in result

    def test_format_small_dict(self):
        """Test formatting small dict shows content."""
        formatter = TableFormatter()
        result = formatter._format_value_for_display({"key": "value"})

        assert "key" in result
        assert "value" in result

    def test_format_empty_list(self):
        """Test formatting empty list."""
        formatter = TableFormatter()
        result = formatter._format_value_for_display([])

        assert result == "[]"

    def test_format_single_item_list(self):
        """Test formatting single item list."""
        formatter = TableFormatter()
        result = formatter._format_value_for_display(["item"])

        assert "item" in result

    def test_format_multi_item_list(self):
        """Test formatting multi-item list shows count."""
        formatter = TableFormatter()
        result = formatter._format_value_for_display(["a", "b", "c"])

        assert "3 items" in result


class TestTableFormatterExtractResourceInfo:
    """Tests for resource info extraction."""

    def test_extract_from_none(self):
        """Test extracting info from None."""
        formatter = TableFormatter()
        result = formatter._extract_resource_info(None)

        assert result == {}

    def test_extract_arn(self):
        """Test extracting ARN from dict."""
        formatter = TableFormatter()
        result = formatter._extract_resource_info(
            {"Arn": "arn:aws:s3:::bucket", "Other": "value"}
        )

        assert "Arn" in result
        assert result["Arn"] == "arn:aws:s3:::bucket"

    def test_extract_name(self):
        """Test extracting Name from dict."""
        formatter = TableFormatter()
        result = formatter._extract_resource_info({"Name": "my-resource"})

        assert "Name" in result
        assert result["Name"] == "my-resource"

    def test_extract_from_string_arn(self):
        """Test extracting from string that looks like ARN."""
        formatter = TableFormatter()
        result = formatter._extract_resource_info("arn:aws:s3:::bucket")

        assert "ARN" in result
        assert result["ARN"] == "arn:aws:s3:::bucket"

    def test_extract_limits_fields(self):
        """Test extraction limits to 5 fields."""
        formatter = TableFormatter()
        data = {
            "Arn": "arn",
            "Name": "name",
            "Id": "id",
            "VpcId": "vpc",
            "SubnetId": "subnet",
            "InstanceId": "instance",
            "Extra": "extra",
        }
        result = formatter._extract_resource_info(data)

        assert len(result) <= 5
