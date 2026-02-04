"""Tests for comparison base module."""

from unittest.mock import MagicMock

from deepdiff import DeepDiff

from aws_comparator.comparison.base import (
    BaseComparator,
    ComparisonConfig,
    SeverityConfig,
)
from aws_comparator.models.common import AWSResource
from aws_comparator.models.comparison import (
    ChangeSeverity,
    ChangeType,
    ServiceComparisonResult,
)


class ConcreteComparator(BaseComparator):
    """Concrete implementation for testing."""

    def compare(
        self,
        account1_data: dict[str, list[AWSResource]],
        account2_data: dict[str, list[AWSResource]],
    ) -> ServiceComparisonResult:
        """Minimal implementation for testing."""
        return ServiceComparisonResult(
            service_name=self.service_name,
            resource_comparisons={},
            execution_time_seconds=0.0,
        )


class TestSeverityConfig:
    """Tests for SeverityConfig dataclass."""

    def test_default_critical_patterns(self):
        """Test default critical patterns are set."""
        config = SeverityConfig()
        assert "security" in config.critical_patterns
        assert "encryption" in config.critical_patterns
        assert "policy" in config.critical_patterns

    def test_default_high_patterns(self):
        """Test default high patterns are set."""
        config = SeverityConfig()
        assert "configuration" in config.high_patterns
        assert "status" in config.high_patterns

    def test_default_medium_patterns(self):
        """Test default medium patterns are set."""
        config = SeverityConfig()
        assert "lifecycle" in config.medium_patterns
        assert "retention" in config.medium_patterns

    def test_default_low_patterns(self):
        """Test default low patterns are set."""
        config = SeverityConfig()
        assert "name" in config.low_patterns
        assert "description" in config.low_patterns

    def test_default_info_patterns(self):
        """Test default info patterns are set."""
        config = SeverityConfig()
        assert "tags" in config.info_patterns

    def test_custom_patterns(self):
        """Test custom patterns override defaults."""
        config = SeverityConfig(critical_patterns=frozenset(["custom_critical"]))
        assert "custom_critical" in config.critical_patterns
        assert "security" not in config.critical_patterns


class TestComparisonConfig:
    """Tests for ComparisonConfig dataclass."""

    def test_default_excluded_fields(self):
        """Test default excluded fields are set."""
        config = ComparisonConfig()
        assert "request_id" in config.excluded_fields
        assert "ResponseMetadata" in config.excluded_fields

    def test_default_excluded_patterns(self):
        """Test default excluded patterns are set."""
        config = ComparisonConfig()
        assert any("timestamp" in p for p in config.excluded_patterns)

    def test_default_ignore_order(self):
        """Test ignore_order defaults to True."""
        config = ComparisonConfig()
        assert config.ignore_order is True

    def test_default_case_sensitive(self):
        """Test case_sensitive defaults to True."""
        config = ComparisonConfig()
        assert config.case_sensitive is True

    def test_custom_excluded_fields(self):
        """Test custom excluded fields."""
        config = ComparisonConfig(excluded_fields={"custom_field"})
        assert "custom_field" in config.excluded_fields


class TestBaseComparatorInit:
    """Tests for BaseComparator initialization."""

    def test_init_with_service_name(self):
        """Test initialization with service name."""
        comparator = ConcreteComparator("test-service")
        assert comparator.service_name == "test-service"

    def test_init_with_default_config(self):
        """Test initialization with default config."""
        comparator = ConcreteComparator("test-service")
        assert comparator.config is not None
        assert isinstance(comparator.config, ComparisonConfig)

    def test_init_with_custom_config(self):
        """Test initialization with custom config."""
        custom_config = ComparisonConfig(ignore_order=False)
        comparator = ConcreteComparator("test-service", config=custom_config)
        assert comparator.config.ignore_order is False

    def test_init_compiles_patterns(self):
        """Test initialization compiles exclusion patterns."""
        comparator = ConcreteComparator("test-service")
        assert len(comparator._compiled_patterns) > 0


class TestBaseComparatorGetResourceIdentifier:
    """Tests for _get_resource_identifier method."""

    def test_identifier_from_arn(self):
        """Test identifier extraction from ARN."""
        comparator = ConcreteComparator("test-service")
        resource = MagicMock(spec=AWSResource)
        resource.arn = "arn:aws:s3:::my-bucket"
        identifier = comparator._get_resource_identifier(resource)
        assert identifier == "arn:aws:s3:::my-bucket"

    def test_identifier_from_id(self):
        """Test identifier extraction from id field."""
        comparator = ConcreteComparator("test-service")
        resource = MagicMock(spec=AWSResource)
        resource.arn = None
        resource.id = "test-id-123"
        identifier = comparator._get_resource_identifier(resource)
        assert identifier == "test-id-123"

    def test_identifier_from_name(self):
        """Test identifier extraction from name field."""
        comparator = ConcreteComparator("test-service")
        resource = MagicMock(spec=AWSResource)
        resource.arn = None
        resource.id = None
        resource.resource_id = None
        resource.name = "test-name"
        identifier = comparator._get_resource_identifier(resource)
        assert identifier == "test-name"

    def test_identifier_fallback_to_hash(self):
        """Test identifier falls back to hash when no standard fields."""
        comparator = ConcreteComparator("test-service")
        resource = MagicMock(spec=AWSResource)
        resource.arn = None

        # Remove all standard identifier fields
        del resource.id
        del resource.resource_id
        del resource.name
        del resource.bucket_name
        del resource.instance_id

        resource.model_dump.return_value = {"field1": "value1"}

        identifier = comparator._get_resource_identifier(resource)
        assert identifier is not None

    def test_identifier_fallback_to_object_id(self):
        """Test identifier falls back to object id on exception."""
        comparator = ConcreteComparator("test-service")
        resource = MagicMock(spec=AWSResource)
        resource.arn = None

        # Remove all standard identifier fields
        del resource.id
        del resource.resource_id
        del resource.name
        del resource.bucket_name
        del resource.instance_id

        resource.model_dump.side_effect = Exception("model_dump failed")

        identifier = comparator._get_resource_identifier(resource)
        assert identifier == str(id(resource))


class TestBaseComparatorResourceToDict:
    """Tests for _resource_to_dict method."""

    def test_resource_to_dict_basic(self):
        """Test converting resource to dictionary."""
        comparator = ConcreteComparator("test-service")
        resource = MagicMock(spec=AWSResource)
        resource.model_dump.return_value = {"field1": "value1", "field2": "value2"}

        result = comparator._resource_to_dict(resource)
        assert "field1" in result

    def test_resource_to_dict_excludes_transient(self):
        """Test transient fields are excluded."""
        comparator = ConcreteComparator("test-service")
        resource = MagicMock(spec=AWSResource)
        resource.model_dump.return_value = {
            "field1": "value1",
            "request_id": "should-be-removed",
        }

        result = comparator._resource_to_dict(resource, exclude_transient=True)
        assert "field1" in result
        assert "request_id" not in result

    def test_resource_to_dict_keeps_transient(self):
        """Test transient fields are kept when specified."""
        comparator = ConcreteComparator("test-service")
        resource = MagicMock(spec=AWSResource)
        resource.model_dump.return_value = {
            "field1": "value1",
            "request_id": "keep-this",
        }

        result = comparator._resource_to_dict(resource, exclude_transient=False)
        assert "request_id" in result

    def test_resource_to_dict_non_pydantic(self):
        """Test conversion for non-Pydantic objects."""
        comparator = ConcreteComparator("test-service")
        resource = MagicMock(spec=AWSResource)
        resource.model_dump.side_effect = AttributeError("no model_dump")

        # Make it iterable to test dict() fallback
        resource.__iter__ = MagicMock(return_value=iter([("key", "value")]))

        result = comparator._resource_to_dict(resource)
        assert result == {"key": "value"}


class TestBaseComparatorExcludeTransientFields:
    """Tests for _exclude_transient_fields method."""

    def test_exclude_explicit_fields(self):
        """Test explicitly excluded fields are removed."""
        comparator = ConcreteComparator("test-service")
        data = {"field1": "value1", "request_id": "remove-me"}

        result = comparator._exclude_transient_fields(data)
        assert "field1" in result
        assert "request_id" not in result

    def test_exclude_pattern_matched_fields(self):
        """Test pattern-matched fields are excluded."""
        comparator = ConcreteComparator("test-service")
        data = {"field1": "value1", "created_at": "2024-01-01"}

        result = comparator._exclude_transient_fields(data)
        assert "field1" in result
        assert "created_at" not in result

    def test_exclude_nested_dicts(self):
        """Test nested dictionaries are processed."""
        comparator = ConcreteComparator("test-service")
        data = {
            "outer": {
                "inner": "value",
                "request_id": "remove-nested",
            }
        }

        result = comparator._exclude_transient_fields(data)
        assert "inner" in result["outer"]
        assert "request_id" not in result["outer"]

    def test_exclude_in_lists(self):
        """Test lists of dicts are processed."""
        comparator = ConcreteComparator("test-service")
        data = {
            "items": [
                {"name": "item1", "request_id": "remove"},
                {"name": "item2"},
            ]
        }

        result = comparator._exclude_transient_fields(data)
        assert len(result["items"]) == 2
        assert "request_id" not in result["items"][0]

    def test_exclude_empty_nested_dicts(self):
        """Test empty nested dicts are not included."""
        comparator = ConcreteComparator("test-service")
        data = {"outer": {"request_id": "only-field"}}

        result = comparator._exclude_transient_fields(data)
        # Empty nested dict should not be included
        assert "outer" not in result

    def test_exclude_preserves_non_dict_list_items(self):
        """Test non-dict list items are preserved."""
        comparator = ConcreteComparator("test-service")
        data = {"tags": ["tag1", "tag2", "tag3"]}

        result = comparator._exclude_transient_fields(data)
        assert result["tags"] == ["tag1", "tag2", "tag3"]


class TestBaseComparatorPerformDeepDiff:
    """Tests for _perform_deep_diff method."""

    def test_deep_diff_no_changes(self):
        """Test deep diff with no changes."""
        comparator = ConcreteComparator("test-service")
        old_data = {"field1": "value1"}
        new_data = {"field1": "value1"}

        diff = comparator._perform_deep_diff(old_data, new_data)
        assert not diff

    def test_deep_diff_with_changes(self):
        """Test deep diff detects changes."""
        comparator = ConcreteComparator("test-service")
        old_data = {"field1": "old_value"}
        new_data = {"field1": "new_value"}

        diff = comparator._perform_deep_diff(old_data, new_data)
        assert diff

    def test_deep_diff_uses_config(self):
        """Test deep diff uses configuration options."""
        config = ComparisonConfig(ignore_order=False)
        comparator = ConcreteComparator("test-service", config=config)

        old_data = {"items": [1, 2, 3]}
        new_data = {"items": [3, 2, 1]}

        diff = comparator._perform_deep_diff(old_data, new_data)
        # With ignore_order=False, the diff should detect changes
        assert diff


class TestBaseComparatorNormalizeFieldPath:
    """Tests for _normalize_field_path method."""

    def test_normalize_simple_path(self):
        """Test normalizing simple field path."""
        comparator = ConcreteComparator("test-service")
        path = "root['field']"
        normalized = comparator._normalize_field_path(path)
        assert normalized == "field"

    def test_normalize_nested_path(self):
        """Test normalizing nested field path."""
        comparator = ConcreteComparator("test-service")
        path = "root['outer']['inner']"
        normalized = comparator._normalize_field_path(path)
        assert normalized == "outer.inner"

    def test_normalize_with_array_index(self):
        """Test normalizing path with array index."""
        comparator = ConcreteComparator("test-service")
        path = "root['items'][0]['name']"
        normalized = comparator._normalize_field_path(path)
        assert normalized == "items[0].name"

    def test_normalize_empty_path(self):
        """Test normalizing empty path."""
        comparator = ConcreteComparator("test-service")
        normalized = comparator._normalize_field_path("")
        assert normalized == ""


class TestBaseComparatorDetermineSeverity:
    """Tests for _determine_severity method."""

    def test_severity_critical(self):
        """Test critical severity detection."""
        comparator = ConcreteComparator("test-service")
        severity = comparator._determine_severity("security_group_id")
        assert severity == ChangeSeverity.CRITICAL

    def test_severity_high(self):
        """Test high severity detection."""
        comparator = ConcreteComparator("test-service")
        severity = comparator._determine_severity("instance_type")
        assert severity == ChangeSeverity.HIGH

    def test_severity_medium(self):
        """Test medium severity detection."""
        comparator = ConcreteComparator("test-service")
        severity = comparator._determine_severity("retention_days")
        assert severity == ChangeSeverity.MEDIUM

    def test_severity_low(self):
        """Test low severity detection."""
        comparator = ConcreteComparator("test-service")
        severity = comparator._determine_severity("description")
        assert severity == ChangeSeverity.LOW

    def test_severity_info(self):
        """Test info severity detection."""
        comparator = ConcreteComparator("test-service")
        severity = comparator._determine_severity("tags")
        assert severity == ChangeSeverity.INFO

    def test_severity_default(self):
        """Test default severity for unknown fields."""
        comparator = ConcreteComparator("test-service")
        severity = comparator._determine_severity("unknown_field_xyz")
        assert severity == ChangeSeverity.MEDIUM

    def test_severity_empty_path(self):
        """Test severity for empty path."""
        comparator = ConcreteComparator("test-service")
        severity = comparator._determine_severity("")
        assert severity == ChangeSeverity.INFO


class TestBaseComparatorExtractChangesFromDiff:
    """Tests for _extract_changes_from_diff method."""

    def test_extract_value_changes(self):
        """Test extracting value changes."""
        comparator = ConcreteComparator("test-service")
        diff = DeepDiff(
            {"field": "old_value"},
            {"field": "new_value"},
        )

        changes = comparator._extract_changes_from_diff(diff, "res-123", "test_type")
        assert len(changes) == 1
        assert changes[0].change_type == ChangeType.MODIFIED
        assert changes[0].old_value == "old_value"
        assert changes[0].new_value == "new_value"

    def test_extract_type_changes(self):
        """Test extracting type changes."""
        comparator = ConcreteComparator("test-service")
        diff = DeepDiff(
            {"field": "string_value"},
            {"field": 123},
        )

        changes = comparator._extract_changes_from_diff(diff, "res-123", "test_type")
        assert len(changes) == 1
        assert changes[0].description is not None
        assert "Type changed" in changes[0].description

    def test_extract_no_changes(self):
        """Test extracting from empty diff."""
        comparator = ConcreteComparator("test-service")
        diff = DeepDiff({"field": "value"}, {"field": "value"})

        changes = comparator._extract_changes_from_diff(diff, "res-123", "test_type")
        assert len(changes) == 0

    def test_extract_iterable_added(self):
        """Test extracting iterable item added."""
        comparator = ConcreteComparator("test-service")
        diff = DeepDiff(
            {"items": [1, 2]},
            {"items": [1, 2, 3]},
            ignore_order=False,
        )

        changes = comparator._extract_changes_from_diff(diff, "res-123", "test_type")
        # Should detect the added item
        assert len(changes) >= 1

    def test_extract_iterable_removed(self):
        """Test extracting iterable item removed."""
        comparator = ConcreteComparator("test-service")
        diff = DeepDiff(
            {"items": [1, 2, 3]},
            {"items": [1, 2]},
            ignore_order=False,
        )

        changes = comparator._extract_changes_from_diff(diff, "res-123", "test_type")
        # Should detect the removed item
        assert len(changes) >= 1


class TestBaseComparatorCreateAddedChange:
    """Tests for _create_added_change method."""

    def test_create_added_change(self):
        """Test creating an added change."""
        comparator = ConcreteComparator("test-service")
        resource = MagicMock(spec=AWSResource)
        resource.arn = "arn:aws:test:::resource"
        resource.model_dump.return_value = {"field": "value"}

        change = comparator._create_added_change(resource, "test_type")

        assert change.change_type == ChangeType.ADDED
        assert change.resource_id == "arn:aws:test:::resource"
        assert change.resource_type == "test_type"
        assert change.severity == ChangeSeverity.HIGH

    def test_create_added_change_custom_severity(self):
        """Test creating an added change with custom severity."""
        comparator = ConcreteComparator("test-service")
        resource = MagicMock(spec=AWSResource)
        resource.arn = "arn:aws:test:::resource"
        resource.model_dump.return_value = {"field": "value"}

        change = comparator._create_added_change(
            resource, "test_type", severity=ChangeSeverity.CRITICAL
        )

        assert change.severity == ChangeSeverity.CRITICAL


class TestBaseComparatorCreateRemovedChange:
    """Tests for _create_removed_change method."""

    def test_create_removed_change(self):
        """Test creating a removed change."""
        comparator = ConcreteComparator("test-service")
        resource = MagicMock(spec=AWSResource)
        resource.arn = "arn:aws:test:::resource"
        resource.model_dump.return_value = {"field": "value"}

        change = comparator._create_removed_change(resource, "test_type")

        assert change.change_type == ChangeType.REMOVED
        assert change.resource_id == "arn:aws:test:::resource"
        assert change.resource_type == "test_type"
        assert change.severity == ChangeSeverity.HIGH

    def test_create_removed_change_custom_severity(self):
        """Test creating a removed change with custom severity."""
        comparator = ConcreteComparator("test-service")
        resource = MagicMock(spec=AWSResource)
        resource.arn = "arn:aws:test:::resource"
        resource.model_dump.return_value = {"field": "value"}

        change = comparator._create_removed_change(
            resource, "test_type", severity=ChangeSeverity.LOW
        )

        assert change.severity == ChangeSeverity.LOW


class TestBaseComparatorStringRepresentations:
    """Tests for __str__ and __repr__ methods."""

    def test_str_representation(self):
        """Test string representation."""
        comparator = ConcreteComparator("test-service")
        assert "ConcreteComparator" in str(comparator)
        assert "test-service" in str(comparator)

    def test_repr_representation(self):
        """Test repr representation."""
        comparator = ConcreteComparator("test-service")
        assert "ConcreteComparator" in repr(comparator)
        assert "test-service" in repr(comparator)
