"""Tests for resource comparator module."""
from datetime import datetime
from typing import Optional

import pytest

from aws_comparator.comparison.base import ComparisonConfig
from aws_comparator.comparison.resource_comparator import ResourceComparator
from aws_comparator.models.common import AWSResource
from aws_comparator.models.comparison import (
    ChangeSeverity,
    ChangeType,
    ResourceChange,
)


class MockResource(AWSResource):
    """Mock resource for testing."""

    name: str = "test-resource"
    value: str = "test-value"


def create_mock_resource(
    arn: str = "arn:aws:test::123456789012:resource/test",
    name: str = "test-resource",
    value: str = "test-value",
    tags: Optional[dict[str, str]] = None,
    region: Optional[str] = None,
    created_date: Optional[datetime] = None,
) -> MockResource:
    """Create a mock resource for testing."""
    return MockResource(
        arn=arn,
        name=name,
        value=value,
        tags=tags or {},
        region=region,
        created_date=created_date,
    )


@pytest.fixture
def comparator():
    """Create a resource comparator."""
    return ResourceComparator("test-service")


@pytest.fixture
def comparator_with_config():
    """Create a resource comparator with custom config."""
    config = ComparisonConfig(
        ignore_order=True,
        excluded_fields={"transient_field"},
    )
    return ResourceComparator("test-service", config=config)


class TestResourceComparatorInit:
    """Tests for ResourceComparator initialization."""

    def test_init_default(self):
        """Test comparator with default config."""
        comparator = ResourceComparator("s3")
        assert comparator.service_name == "s3"
        assert comparator.config is not None

    def test_init_with_config(self):
        """Test comparator with custom config."""
        config = ComparisonConfig(ignore_order=False)
        comparator = ResourceComparator("ec2", config=config)
        assert comparator.service_name == "ec2"
        assert comparator.config.ignore_order is False


class TestResourceComparatorCompare:
    """Tests for compare method."""

    def test_compare_empty_data(self, comparator):
        """Test comparing empty data from both accounts."""
        result = comparator.compare({}, {})

        assert result.service_name == "test-service"
        assert len(result.resource_comparisons) == 0
        assert result.total_changes == 0

    def test_compare_none_raises_error(self, comparator):
        """Test comparing None data raises ValueError."""
        with pytest.raises(ValueError):
            comparator.compare(None, {})  # type: ignore[arg-type]

        with pytest.raises(ValueError):
            comparator.compare({}, None)  # type: ignore[arg-type]

    def test_compare_added_resources(self, comparator):
        """Test detecting added resources."""
        resource = create_mock_resource(
            arn="arn:aws:test::123456789012:resource/new",
            name="new-resource",
            value="new-value",
        )

        result = comparator.compare(
            {"resources": []},
            {"resources": [resource]},
        )

        assert "resources" in result.resource_comparisons
        comp = result.resource_comparisons["resources"]
        assert len(comp.added) == 1
        assert len(comp.removed) == 0
        assert len(comp.modified) == 0

    def test_compare_removed_resources(self, comparator):
        """Test detecting removed resources."""
        resource = create_mock_resource(
            arn="arn:aws:test::123456789012:resource/old",
            name="old-resource",
            value="old-value",
        )

        result = comparator.compare(
            {"resources": [resource]},
            {"resources": []},
        )

        comp = result.resource_comparisons["resources"]
        assert len(comp.added) == 0
        assert len(comp.removed) == 1
        assert len(comp.modified) == 0

    def test_compare_modified_resources(self, comparator):
        """Test detecting modified resources."""
        resource1 = create_mock_resource(
            arn="arn:aws:test::123456789012:resource/test",
            name="test-resource",
            value="old-value",
        )
        resource2 = create_mock_resource(
            arn="arn:aws:test::123456789012:resource/test",
            name="test-resource",
            value="new-value",
        )

        result = comparator.compare(
            {"resources": [resource1]},
            {"resources": [resource2]},
        )

        comp = result.resource_comparisons["resources"]
        assert len(comp.added) == 0
        assert len(comp.removed) == 0
        assert len(comp.modified) >= 1

    def test_compare_unchanged_resources(self, comparator):
        """Test unchanged resources are counted."""
        resource = create_mock_resource(
            arn="arn:aws:test::123456789012:resource/test",
            name="test-resource",
            value="same-value",
        )

        result = comparator.compare(
            {"resources": [resource]},
            {"resources": [resource]},
        )

        comp = result.resource_comparisons["resources"]
        assert comp.unchanged_count == 1

    def test_compare_multiple_resource_types(self, comparator):
        """Test comparing multiple resource types."""
        resource_a = create_mock_resource(
            arn="arn:aws:test::123456789012:resource/a",
            name="resource-a",
        )
        resource_b = create_mock_resource(
            arn="arn:aws:test::123456789012:resource/b",
            name="resource-b",
        )

        result = comparator.compare(
            {"type_a": [resource_a], "type_b": []},
            {"type_a": [], "type_b": [resource_b]},
        )

        assert "type_a" in result.resource_comparisons
        assert "type_b" in result.resource_comparisons

    def test_compare_returns_execution_time(self, comparator):
        """Test compare returns execution time."""
        result = comparator.compare({}, {})

        assert result.execution_time_seconds >= 0


class TestResourceComparatorCompareResourceType:
    """Tests for _compare_resource_type method."""

    def test_compare_resource_type_counts(self, comparator):
        """Test resource type comparison counts resources."""
        resource1 = create_mock_resource(arn="arn:aws:test::123456789012:resource/1")
        resource2 = create_mock_resource(arn="arn:aws:test::123456789012:resource/2")

        comparison = comparator._compare_resource_type(
            "test_type",
            [resource1],
            [resource2],
        )

        assert comparison.account1_count == 1
        assert comparison.account2_count == 1


class TestResourceComparatorBuildResourceMap:
    """Tests for _build_resource_map method."""

    def test_build_resource_map(self, comparator):
        """Test building resource map."""
        resource = create_mock_resource(
            arn="arn:aws:test::123456789012:resource/test",
            name="test-resource",
        )

        resource_map = comparator._build_resource_map([resource])

        assert len(resource_map) == 1
        assert resource.arn in resource_map

    def test_build_resource_map_empty(self, comparator):
        """Test building resource map with empty list."""
        resource_map = comparator._build_resource_map([])

        assert len(resource_map) == 0

    def test_build_resource_map_duplicate_warning(self, comparator):
        """Test building resource map with duplicates logs warning."""
        resource1 = create_mock_resource(arn="arn:aws:test::123456789012:resource/same")
        resource2 = create_mock_resource(arn="arn:aws:test::123456789012:resource/same")

        resource_map = comparator._build_resource_map([resource1, resource2])

        # Second resource should overwrite first
        assert len(resource_map) == 1


class TestResourceComparatorSingleResourceType:
    """Tests for compare_single_resource_type method."""

    def test_compare_single_resource_type(self, comparator):
        """Test comparing single resource type."""
        resource1 = create_mock_resource(arn="arn:aws:test::123456789012:resource/1")
        resource2 = create_mock_resource(arn="arn:aws:test::123456789012:resource/2")

        comparison = comparator.compare_single_resource_type(
            "test_type",
            [resource1],
            [resource2],
        )

        assert comparison.resource_type == "test_type"
        assert len(comparison.added) == 1
        assert len(comparison.removed) == 1


class TestResourceComparatorGetHighestSeverity:
    """Tests for get_highest_severity method."""

    def test_get_highest_severity_empty(self, comparator):
        """Test getting highest severity from empty list."""
        result = comparator.get_highest_severity([])

        assert result is None

    def test_get_highest_severity_single(self, comparator):
        """Test getting highest severity from single change."""
        change = ResourceChange(
            change_type=ChangeType.MODIFIED,
            resource_id="test",
            resource_type="resource",
            field_path="field",
            old_value="old",
            new_value="new",
            severity=ChangeSeverity.HIGH,
            description="Test change",
        )

        result = comparator.get_highest_severity([change])

        assert result == ChangeSeverity.HIGH

    def test_get_highest_severity_multiple(self, comparator):
        """Test getting highest severity from multiple changes."""
        changes = [
            ResourceChange(
                change_type=ChangeType.MODIFIED,
                resource_id="test1",
                resource_type="resource",
                field_path="field1",
                old_value="old",
                new_value="new",
                severity=ChangeSeverity.LOW,
                description="Low severity",
            ),
            ResourceChange(
                change_type=ChangeType.MODIFIED,
                resource_id="test2",
                resource_type="resource",
                field_path="field2",
                old_value="old",
                new_value="new",
                severity=ChangeSeverity.CRITICAL,
                description="Critical severity",
            ),
            ResourceChange(
                change_type=ChangeType.MODIFIED,
                resource_id="test3",
                resource_type="resource",
                field_path="field3",
                old_value="old",
                new_value="new",
                severity=ChangeSeverity.MEDIUM,
                description="Medium severity",
            ),
        ]

        result = comparator.get_highest_severity(changes)

        assert result == ChangeSeverity.CRITICAL


class TestResourceComparatorFilterBySeverity:
    """Tests for filter_by_severity method."""

    def test_filter_by_severity_all(self, comparator):
        """Test filtering with INFO level returns all."""
        changes = [
            ResourceChange(
                change_type=ChangeType.MODIFIED,
                resource_id="test1",
                resource_type="resource",
                field_path="field",
                old_value="old",
                new_value="new",
                severity=ChangeSeverity.INFO,
                description="Info change",
            ),
            ResourceChange(
                change_type=ChangeType.MODIFIED,
                resource_id="test2",
                resource_type="resource",
                field_path="field",
                old_value="old",
                new_value="new",
                severity=ChangeSeverity.CRITICAL,
                description="Critical change",
            ),
        ]

        result = comparator.filter_by_severity(changes, ChangeSeverity.INFO)

        assert len(result) == 2

    def test_filter_by_severity_high(self, comparator):
        """Test filtering for HIGH and above."""
        changes = [
            ResourceChange(
                change_type=ChangeType.MODIFIED,
                resource_id="test1",
                resource_type="resource",
                field_path="field",
                old_value="old",
                new_value="new",
                severity=ChangeSeverity.LOW,
                description="Low change",
            ),
            ResourceChange(
                change_type=ChangeType.MODIFIED,
                resource_id="test2",
                resource_type="resource",
                field_path="field",
                old_value="old",
                new_value="new",
                severity=ChangeSeverity.HIGH,
                description="High change",
            ),
            ResourceChange(
                change_type=ChangeType.MODIFIED,
                resource_id="test3",
                resource_type="resource",
                field_path="field",
                old_value="old",
                new_value="new",
                severity=ChangeSeverity.CRITICAL,
                description="Critical change",
            ),
        ]

        result = comparator.filter_by_severity(changes, ChangeSeverity.HIGH)

        assert len(result) == 2
        assert all(
            c.severity in [ChangeSeverity.HIGH, ChangeSeverity.CRITICAL]
            for c in result
        )

    def test_filter_by_severity_empty(self, comparator):
        """Test filtering empty list."""
        result = comparator.filter_by_severity([], ChangeSeverity.CRITICAL)

        assert len(result) == 0
