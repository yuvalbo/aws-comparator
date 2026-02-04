"""Tests for base service fetcher module."""

from typing import Any
from unittest.mock import MagicMock

import pytest
from botocore.exceptions import ClientError, NoCredentialsError

from aws_comparator.core.exceptions import (
    DataFetchError,
    InsufficientPermissionsError,
    ServiceThrottlingError,
)
from aws_comparator.services.base import BaseServiceFetcher


class ConcreteFetcher(BaseServiceFetcher):
    """Concrete implementation for testing."""

    SERVICE_NAME = "test-service"
    RESOURCE_TYPES = ["items", "widgets"]

    def _create_client(self) -> Any:
        """Create a mock client."""
        return self.session.client("test")

    def fetch_resources(self) -> dict[str, list[Any]]:
        """Fetch resources."""
        return {"items": [], "widgets": []}

    def get_resource_types(self) -> list[str]:
        """Return resource types."""
        return self.RESOURCE_TYPES


class TestBaseServiceFetcherInit:
    """Tests for BaseServiceFetcher initialization."""

    def test_init_creates_client(self):
        """Test initialization creates a client."""
        mock_session = MagicMock()
        mock_client = MagicMock()
        mock_session.client.return_value = mock_client

        fetcher = ConcreteFetcher(session=mock_session, region="us-east-1")

        assert fetcher.client is not None
        assert fetcher.region == "us-east-1"

    def test_init_no_credentials_error(self):
        """Test initialization handles NoCredentialsError."""
        mock_session = MagicMock()
        mock_session.client.side_effect = NoCredentialsError()

        with pytest.raises(NoCredentialsError):
            ConcreteFetcher(session=mock_session, region="us-east-1")

    def test_init_generic_error(self):
        """Test initialization handles generic errors."""
        mock_session = MagicMock()
        mock_session.client.side_effect = RuntimeError("Client creation failed")

        with pytest.raises(RuntimeError, match="Client creation failed"):
            ConcreteFetcher(session=mock_session, region="us-east-1")


class TestBaseServiceFetcherProperties:
    """Tests for BaseServiceFetcher properties."""

    def test_service_name(self):
        """Test service_name property."""
        mock_session = MagicMock()

        fetcher = ConcreteFetcher(session=mock_session, region="us-east-1")

        assert fetcher.SERVICE_NAME == "test-service"

    def test_resource_types(self):
        """Test resource_types property."""
        mock_session = MagicMock()

        fetcher = ConcreteFetcher(session=mock_session, region="us-east-1")

        assert fetcher.RESOURCE_TYPES == ["items", "widgets"]


class TestBaseServiceFetcherResourceOperations:
    """Tests for resource operation methods."""

    def test_fetch_resources(self):
        """Test fetch_resources returns expected structure."""
        mock_session = MagicMock()

        fetcher = ConcreteFetcher(session=mock_session, region="us-east-1")
        resources = fetcher.fetch_resources()

        assert "items" in resources
        assert "widgets" in resources
        assert isinstance(resources["items"], list)
        assert isinstance(resources["widgets"], list)

    def test_get_resource_types(self):
        """Test get_resource_types returns expected list."""
        mock_session = MagicMock()

        fetcher = ConcreteFetcher(session=mock_session, region="us-east-1")
        types = fetcher.get_resource_types()

        assert types == ["items", "widgets"]


class TestBaseServiceFetcherStr:
    """Tests for string representation."""

    def test_str_representation(self):
        """Test string representation."""
        mock_session = MagicMock()

        fetcher = ConcreteFetcher(session=mock_session, region="us-east-1")

        result = str(fetcher)

        assert "test-service" in result
        assert "us-east-1" in result

    def test_repr_representation(self):
        """Test repr representation."""
        mock_session = MagicMock()

        fetcher = ConcreteFetcher(session=mock_session, region="us-east-1")

        result = repr(fetcher)

        assert "ConcreteFetcher" in result
        assert "us-east-1" in result


class TestBaseServiceFetcherPaginate:
    """Tests for _paginate method."""

    def test_paginate_auto_detect_result_key(self):
        """Test _paginate auto-detects result key when not provided."""
        mock_session = MagicMock()
        mock_client = MagicMock()
        mock_session.client.return_value = mock_client

        # Setup paginator
        mock_client.can_paginate.return_value = True
        mock_paginator = MagicMock()
        mock_client.get_paginator.return_value = mock_paginator

        # Return pages with auto-detectable result key
        mock_paginator.paginate.return_value = [
            {"Items": [{"id": "1"}, {"id": "2"}], "ResponseMetadata": {}},
            {"Items": [{"id": "3"}], "ResponseMetadata": {}},
        ]

        fetcher = ConcreteFetcher(session=mock_session, region="us-east-1")
        results = fetcher._paginate("list_items")

        assert len(results) == 3
        assert results[0]["id"] == "1"

    def test_paginate_no_result_key_returns_pages(self):
        """Test _paginate returns whole pages when no result key found."""
        mock_session = MagicMock()
        mock_client = MagicMock()
        mock_session.client.return_value = mock_client

        mock_client.can_paginate.return_value = True
        mock_paginator = MagicMock()
        mock_client.get_paginator.return_value = mock_paginator

        # Return pages with no list keys (only ResponseMetadata)
        mock_paginator.paginate.return_value = [
            {"ResponseMetadata": {}, "Count": 5},
        ]

        fetcher = ConcreteFetcher(session=mock_session, region="us-east-1")
        results = fetcher._paginate("get_count")

        # Should return the whole page
        assert len(results) == 1
        assert results[0]["Count"] == 5

    def test_paginate_no_paginator_no_result_key(self):
        """Test _paginate without paginator and no result key in response."""
        mock_session = MagicMock()
        mock_client = MagicMock()
        mock_session.client.return_value = mock_client

        mock_client.can_paginate.return_value = False
        mock_client.get_item.return_value = {"Item": {"id": "1"}}

        fetcher = ConcreteFetcher(session=mock_session, region="us-east-1")
        results = fetcher._paginate("get_item", result_key="NonExistent")

        # Should return response as single-item list
        assert len(results) == 1
        assert results[0]["Item"]["id"] == "1"

    def test_paginate_throttling_error(self):
        """Test _paginate raises ServiceThrottlingError on throttling."""
        mock_session = MagicMock()
        mock_client = MagicMock()
        mock_session.client.return_value = mock_client

        mock_client.can_paginate.return_value = True
        mock_paginator = MagicMock()
        mock_client.get_paginator.return_value = mock_paginator

        error_response = {"Error": {"Code": "Throttling", "Message": "Rate exceeded"}}
        mock_paginator.paginate.side_effect = ClientError(error_response, "ListItems")

        fetcher = ConcreteFetcher(session=mock_session, region="us-east-1")

        with pytest.raises(ServiceThrottlingError):
            fetcher._paginate("list_items")


class TestBaseServiceFetcherSafeFetch:
    """Tests for _safe_fetch method."""

    def test_safe_fetch_insufficient_permissions(self):
        """Test _safe_fetch handles InsufficientPermissionsError."""
        mock_session = MagicMock()

        fetcher = ConcreteFetcher(session=mock_session, region="us-east-1")

        def failing_fetch():
            raise InsufficientPermissionsError(
                "test-service", "list_items", "test-service:list_items"
            )

        result = fetcher._safe_fetch("items", failing_fetch)

        assert result == []

    def test_safe_fetch_throttling_error(self):
        """Test _safe_fetch handles ServiceThrottlingError."""
        mock_session = MagicMock()

        fetcher = ConcreteFetcher(session=mock_session, region="us-east-1")

        def failing_fetch():
            raise ServiceThrottlingError("test-service", "list_items")

        result = fetcher._safe_fetch("items", failing_fetch)

        assert result == []

    def test_safe_fetch_data_fetch_error(self):
        """Test _safe_fetch handles DataFetchError."""
        mock_session = MagicMock()

        fetcher = ConcreteFetcher(session=mock_session, region="us-east-1")

        def failing_fetch():
            raise DataFetchError("test-service", "list_items", "Something went wrong")

        result = fetcher._safe_fetch("items", failing_fetch)

        assert result == []
