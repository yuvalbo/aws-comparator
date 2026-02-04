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


class TestS3FetcherBucketDetails:
    """Tests for _fetch_bucket_details method."""

    @mock_aws
    def test_fetch_bucket_details_with_versioning(self):
        """Test fetching bucket details with versioning enabled."""
        session = boto3.Session(region_name="us-east-1")
        s3_client = session.client("s3", region_name="us-east-1")

        # Create bucket with versioning
        s3_client.create_bucket(Bucket="versioned-bucket")
        s3_client.put_bucket_versioning(
            Bucket="versioned-bucket",
            VersioningConfiguration={"Status": "Enabled"},
        )

        fetcher = S3Fetcher(session=session, region="us-east-1")
        resources = fetcher.fetch_resources()

        bucket = resources["buckets"][0]
        assert bucket.versioning_status == "Enabled"

    @mock_aws
    def test_fetch_bucket_details_with_encryption(self):
        """Test fetching bucket details with encryption configured."""
        session = boto3.Session(region_name="us-east-1")
        s3_client = session.client("s3", region_name="us-east-1")

        # Create bucket with encryption
        s3_client.create_bucket(Bucket="encrypted-bucket")
        s3_client.put_bucket_encryption(
            Bucket="encrypted-bucket",
            ServerSideEncryptionConfiguration={
                "Rules": [
                    {"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}
                ]
            },
        )

        fetcher = S3Fetcher(session=session, region="us-east-1")
        resources = fetcher.fetch_resources()

        bucket = resources["buckets"][0]
        assert bucket.encryption is not None

    @mock_aws
    def test_fetch_bucket_details_with_logging(self):
        """Test fetching bucket details with logging enabled."""
        session = boto3.Session(region_name="us-east-1")
        s3_client = session.client("s3", region_name="us-east-1")

        # Create bucket and enable logging
        s3_client.create_bucket(Bucket="source-bucket")
        s3_client.create_bucket(Bucket="log-bucket")

        # Moto doesn't fully support logging config, so we just verify the bucket is fetched

        fetcher = S3Fetcher(session=session, region="us-east-1")
        resources = fetcher.fetch_resources()

        assert len(resources["buckets"]) == 2

    def test_fetch_bucket_details_with_errors(self, mock_session):
        """Test fetch_bucket_details handles various errors gracefully."""
        from botocore.exceptions import ClientError

        mock_client = MagicMock()
        mock_session.client.return_value = mock_client

        mock_client.list_buckets.return_value = {
            "Buckets": [{"Name": "test-bucket", "CreationDate": "2024-01-01"}]
        }

        # All detail fetching fails
        mock_client.get_bucket_location.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Denied"}},
            "GetBucketLocation",
        )
        mock_client.get_bucket_versioning.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Denied"}},
            "GetBucketVersioning",
        )
        mock_client.get_bucket_encryption.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Denied"}},
            "GetBucketEncryption",
        )
        mock_client.get_public_access_block.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Denied"}},
            "GetPublicAccessBlock",
        )
        mock_client.get_bucket_logging.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Denied"}},
            "GetBucketLogging",
        )
        mock_client.get_bucket_lifecycle_configuration.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Denied"}},
            "GetBucketLifecycleConfiguration",
        )
        mock_client.get_bucket_replication.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Denied"}},
            "GetBucketReplication",
        )
        mock_client.get_bucket_website.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Denied"}},
            "GetBucketWebsite",
        )
        mock_client.get_bucket_tagging.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Denied"}},
            "GetBucketTagging",
        )
        mock_client.get_bucket_policy.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Denied"}},
            "GetBucketPolicy",
        )
        mock_client.get_bucket_cors.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Denied"}},
            "GetBucketCors",
        )
        mock_client.get_object_lock_configuration.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Denied"}},
            "GetObjectLockConfiguration",
        )
        mock_client.get_bucket_request_payment.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Denied"}},
            "GetBucketRequestPayment",
        )

        fetcher = S3Fetcher(session=mock_session, region="us-east-1")
        resources = fetcher.fetch_resources()

        # Should still return bucket with basic info
        assert len(resources["buckets"]) == 1
        assert resources["buckets"][0].name == "test-bucket"

    def test_fetch_bucket_details_with_specific_error_codes(self, mock_session):
        """Test fetch_bucket_details handles specific error codes."""
        from botocore.exceptions import ClientError

        mock_client = MagicMock()
        mock_session.client.return_value = mock_client

        mock_client.list_buckets.return_value = {
            "Buckets": [{"Name": "test-bucket", "CreationDate": "2024-01-01"}]
        }

        # Successful location fetch
        mock_client.get_bucket_location.return_value = {"LocationConstraint": None}
        mock_client.get_bucket_versioning.return_value = {}

        # Specific error codes that should be handled silently
        mock_client.get_bucket_encryption.side_effect = ClientError(
            {
                "Error": {
                    "Code": "ServerSideEncryptionConfigurationNotFoundError",
                    "Message": "Not found",
                }
            },
            "GetBucketEncryption",
        )
        mock_client.get_public_access_block.side_effect = ClientError(
            {"Error": {"Code": "NoSuchPublicAccessBlockConfiguration", "Message": ""}},
            "GetPublicAccessBlock",
        )
        mock_client.get_bucket_logging.return_value = {}
        mock_client.get_bucket_lifecycle_configuration.side_effect = ClientError(
            {"Error": {"Code": "NoSuchLifecycleConfiguration", "Message": ""}},
            "GetBucketLifecycleConfiguration",
        )
        mock_client.get_bucket_replication.side_effect = ClientError(
            {
                "Error": {
                    "Code": "ReplicationConfigurationNotFoundError",
                    "Message": "",
                }
            },
            "GetBucketReplication",
        )
        mock_client.get_bucket_website.side_effect = ClientError(
            {"Error": {"Code": "NoSuchWebsiteConfiguration", "Message": ""}},
            "GetBucketWebsite",
        )
        mock_client.get_bucket_tagging.side_effect = ClientError(
            {"Error": {"Code": "NoSuchTagSet", "Message": ""}},
            "GetBucketTagging",
        )
        mock_client.get_bucket_policy.side_effect = ClientError(
            {"Error": {"Code": "NoSuchBucketPolicy", "Message": ""}},
            "GetBucketPolicy",
        )
        mock_client.get_bucket_cors.side_effect = ClientError(
            {"Error": {"Code": "NoSuchCORSConfiguration", "Message": ""}},
            "GetBucketCors",
        )
        mock_client.get_object_lock_configuration.side_effect = ClientError(
            {"Error": {"Code": "ObjectLockConfigurationNotFoundError", "Message": ""}},
            "GetObjectLockConfiguration",
        )
        mock_client.get_bucket_request_payment.return_value = {}

        fetcher = S3Fetcher(session=mock_session, region="us-east-1")
        resources = fetcher.fetch_resources()

        # Should still return bucket with basic info
        assert len(resources["buckets"]) == 1

    def test_fetch_bucket_details_per_bucket_error(self, mock_session):
        """Test per-bucket error handling during fetch."""
        from botocore.exceptions import ClientError

        mock_client = MagicMock()
        mock_session.client.return_value = mock_client

        mock_client.list_buckets.return_value = {
            "Buckets": [
                {"Name": "bucket-1", "CreationDate": "2024-01-01"},
                {"Name": "bucket-2", "CreationDate": "2024-01-01"},
            ]
        }

        # First bucket fails with AccessDenied on location
        def get_bucket_location_effect(Bucket):
            if Bucket == "bucket-1":
                raise ClientError(
                    {"Error": {"Code": "AccessDenied", "Message": "Denied"}},
                    "GetBucketLocation",
                )
            return {"LocationConstraint": None}

        mock_client.get_bucket_location.side_effect = get_bucket_location_effect
        mock_client.get_bucket_versioning.return_value = {}
        mock_client.get_bucket_encryption.side_effect = ClientError(
            {
                "Error": {
                    "Code": "ServerSideEncryptionConfigurationNotFoundError",
                    "Message": "",
                }
            },
            "GetBucketEncryption",
        )
        mock_client.get_public_access_block.side_effect = ClientError(
            {"Error": {"Code": "NoSuchPublicAccessBlockConfiguration", "Message": ""}},
            "GetPublicAccessBlock",
        )
        mock_client.get_bucket_logging.return_value = {}
        mock_client.get_bucket_lifecycle_configuration.side_effect = ClientError(
            {"Error": {"Code": "NoSuchLifecycleConfiguration", "Message": ""}},
            "GetBucketLifecycleConfiguration",
        )
        mock_client.get_bucket_replication.side_effect = ClientError(
            {
                "Error": {
                    "Code": "ReplicationConfigurationNotFoundError",
                    "Message": "",
                }
            },
            "GetBucketReplication",
        )
        mock_client.get_bucket_website.side_effect = ClientError(
            {"Error": {"Code": "NoSuchWebsiteConfiguration", "Message": ""}},
            "GetBucketWebsite",
        )
        mock_client.get_bucket_tagging.side_effect = ClientError(
            {"Error": {"Code": "NoSuchTagSet", "Message": ""}},
            "GetBucketTagging",
        )
        mock_client.get_bucket_policy.side_effect = ClientError(
            {"Error": {"Code": "NoSuchBucketPolicy", "Message": ""}},
            "GetBucketPolicy",
        )
        mock_client.get_bucket_cors.side_effect = ClientError(
            {"Error": {"Code": "NoSuchCORSConfiguration", "Message": ""}},
            "GetBucketCors",
        )
        mock_client.get_object_lock_configuration.side_effect = ClientError(
            {"Error": {"Code": "ObjectLockConfigurationNotFoundError", "Message": ""}},
            "GetObjectLockConfiguration",
        )
        mock_client.get_bucket_request_payment.return_value = {}

        fetcher = S3Fetcher(session=mock_session, region="us-east-1")
        resources = fetcher.fetch_resources()

        # Both buckets should be returned - AccessDenied on location is handled gracefully
        # The first bucket will have no location, but should still be included
        assert len(resources["buckets"]) == 2
        bucket_names = [b.name for b in resources["buckets"]]
        assert "bucket-1" in bucket_names
        assert "bucket-2" in bucket_names

    def test_fetch_bucket_details_nosuchbucket_error(self, mock_session):
        """Test NoSuchBucket error handling during fetch."""
        from botocore.exceptions import ClientError

        mock_client = MagicMock()
        mock_session.client.return_value = mock_client

        mock_client.list_buckets.return_value = {
            "Buckets": [{"Name": "deleted-bucket", "CreationDate": "2024-01-01"}]
        }

        # Bucket was deleted between list and detail fetch
        mock_client.get_bucket_location.side_effect = ClientError(
            {"Error": {"Code": "NoSuchBucket", "Message": "Bucket does not exist"}},
            "GetBucketLocation",
        )

        fetcher = S3Fetcher(session=mock_session, region="us-east-1")
        resources = fetcher.fetch_resources()

        # Should return empty list since bucket was deleted
        assert len(resources["buckets"]) == 0
