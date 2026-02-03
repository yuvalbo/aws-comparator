"""Tests for S3 service fetcher."""
from unittest.mock import MagicMock

import boto3
import pytest
from moto import mock_aws

from aws_comparator.services.s3.fetcher import S3Fetcher


@pytest.fixture
def mock_session():
    """Create a mock boto3 session."""
    session = MagicMock()
    return session


class TestS3FetcherInit:
    """Tests for S3Fetcher initialization."""

    def test_init_sets_service_name(self, mock_session):
        """Test fetcher sets correct service name."""
        fetcher = S3Fetcher(session=mock_session, region="us-east-1")
        assert fetcher.SERVICE_NAME == "s3"

    def test_init_sets_region(self, mock_session):
        """Test fetcher sets region."""
        fetcher = S3Fetcher(session=mock_session, region="us-west-2")
        assert fetcher.region == "us-west-2"


class TestS3FetcherGetResourceTypes:
    """Tests for get_resource_types method."""

    def test_get_resource_types(self, mock_session):
        """Test get_resource_types returns expected types."""
        fetcher = S3Fetcher(session=mock_session, region="us-east-1")
        resource_types = fetcher.get_resource_types()

        assert "buckets" in resource_types


class TestS3FetcherFetchResources:
    """Tests for fetch_resources method."""

    @mock_aws
    def test_fetch_resources_empty(self):
        """Test fetching resources when no buckets exist."""
        session = boto3.Session(region_name="us-east-1")
        fetcher = S3Fetcher(session=session, region="us-east-1")

        resources = fetcher.fetch_resources()

        assert "buckets" in resources
        assert len(resources["buckets"]) == 0

    @mock_aws
    def test_fetch_resources_with_buckets(self):
        """Test fetching resources with existing buckets."""
        session = boto3.Session(region_name="us-east-1")
        s3_client = session.client("s3", region_name="us-east-1")

        # Create test buckets
        s3_client.create_bucket(Bucket="test-bucket-1")
        s3_client.create_bucket(Bucket="test-bucket-2")

        fetcher = S3Fetcher(session=session, region="us-east-1")
        resources = fetcher.fetch_resources()

        assert "buckets" in resources
        assert len(resources["buckets"]) == 2

    @mock_aws
    def test_fetch_resources_bucket_properties(self):
        """Test fetched buckets have expected properties."""
        session = boto3.Session(region_name="us-east-1")
        s3_client = session.client("s3", region_name="us-east-1")

        # Create test bucket
        s3_client.create_bucket(Bucket="test-bucket")

        fetcher = S3Fetcher(session=session, region="us-east-1")
        resources = fetcher.fetch_resources()

        bucket = resources["buckets"][0]
        assert hasattr(bucket, "name")
        assert bucket.name == "test-bucket"

    @mock_aws
    def test_fetch_resources_with_tags(self):
        """Test fetching bucket with tags."""
        session = boto3.Session(region_name="us-east-1")
        s3_client = session.client("s3", region_name="us-east-1")

        # Create bucket with tags
        s3_client.create_bucket(Bucket="tagged-bucket")
        s3_client.put_bucket_tagging(
            Bucket="tagged-bucket",
            Tagging={
                "TagSet": [
                    {"Key": "Environment", "Value": "test"},
                    {"Key": "Team", "Value": "platform"},
                ]
            },
        )

        fetcher = S3Fetcher(session=session, region="us-east-1")
        resources = fetcher.fetch_resources()

        bucket = resources["buckets"][0]
        assert bucket.tags.get("Environment") == "test"
        assert bucket.tags.get("Team") == "platform"


class TestS3FetcherErrorHandling:
    """Tests for error handling in S3Fetcher."""

    def test_fetch_with_client_error(self, mock_session):
        """Test fetcher handles client errors gracefully."""
        from botocore.exceptions import ClientError

        mock_client = MagicMock()
        mock_client.list_buckets.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Access Denied"}},
            "ListBuckets",
        )
        mock_session.client.return_value = mock_client

        fetcher = S3Fetcher(session=mock_session, region="us-east-1")
        resources = fetcher.fetch_resources()

        # Should return empty list on error
        assert resources["buckets"] == []

    def test_fetch_with_no_client(self, mock_session):
        """Test fetcher handles missing client."""
        mock_session.client.return_value = None

        fetcher = S3Fetcher(session=mock_session, region="us-east-1")

        # Should handle gracefully
        resources = fetcher.fetch_resources()
        assert "buckets" in resources
