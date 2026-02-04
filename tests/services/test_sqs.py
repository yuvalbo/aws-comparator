"""Tests for SQS service fetcher."""
from unittest.mock import MagicMock

import boto3
import pytest
from moto import mock_aws

from aws_comparator.services.sqs.fetcher import SQSFetcher


@pytest.fixture
def mock_session():
    """Create a mock boto3 session."""
    session = MagicMock()
    return session


class TestSQSFetcherInit:
    """Tests for SQSFetcher initialization."""

    def test_init_sets_service_name(self, mock_session):
        """Test fetcher sets correct service name."""
        fetcher = SQSFetcher(session=mock_session, region="us-east-1")
        assert fetcher.SERVICE_NAME == "sqs"

    def test_init_sets_region(self, mock_session):
        """Test fetcher sets region."""
        fetcher = SQSFetcher(session=mock_session, region="us-west-2")
        assert fetcher.region == "us-west-2"


class TestSQSFetcherGetResourceTypes:
    """Tests for get_resource_types method."""

    def test_get_resource_types(self, mock_session):
        """Test get_resource_types returns expected types."""
        fetcher = SQSFetcher(session=mock_session, region="us-east-1")
        resource_types = fetcher.get_resource_types()

        assert "queues" in resource_types


class TestSQSFetcherFetchResources:
    """Tests for fetch_resources method."""

    @mock_aws
    def test_fetch_resources_empty(self):
        """Test fetching resources when no queues exist."""
        session = boto3.Session(region_name="us-east-1")
        fetcher = SQSFetcher(session=session, region="us-east-1")

        resources = fetcher.fetch_resources()

        assert "queues" in resources
        assert len(resources["queues"]) == 0

    @mock_aws
    @pytest.mark.skip(reason="Moto returns timestamps in float format incompatible with SQS model")
    def test_fetch_resources_with_queues(self):
        """Test fetching resources with existing queues."""
        session = boto3.Session(region_name="us-east-1")
        sqs_client = session.client("sqs", region_name="us-east-1")

        # Create test queues
        sqs_client.create_queue(QueueName="test-queue-1")
        sqs_client.create_queue(QueueName="test-queue-2")

        fetcher = SQSFetcher(session=session, region="us-east-1")
        resources = fetcher.fetch_resources()

        assert "queues" in resources
        assert len(resources["queues"]) == 2

    @mock_aws
    @pytest.mark.skip(reason="Moto returns timestamps in float format incompatible with SQS model")
    def test_fetch_resources_queue_properties(self):
        """Test fetched queues have expected properties."""
        session = boto3.Session(region_name="us-east-1")
        sqs_client = session.client("sqs", region_name="us-east-1")

        # Create test queue
        sqs_client.create_queue(QueueName="test-queue")

        fetcher = SQSFetcher(session=session, region="us-east-1")
        resources = fetcher.fetch_resources()

        queue = resources["queues"][0]
        assert hasattr(queue, "queue_name")
        assert queue.queue_name == "test-queue"

    @mock_aws
    @pytest.mark.skip(reason="Moto returns timestamps in float format incompatible with SQS model")
    def test_fetch_resources_fifo_queue(self):
        """Test fetching FIFO queue."""
        session = boto3.Session(region_name="us-east-1")
        sqs_client = session.client("sqs", region_name="us-east-1")

        # Create FIFO queue
        sqs_client.create_queue(
            QueueName="test-queue.fifo",
            Attributes={"FifoQueue": "true"},
        )

        fetcher = SQSFetcher(session=session, region="us-east-1")
        resources = fetcher.fetch_resources()

        assert len(resources["queues"]) == 1
        queue = resources["queues"][0]
        assert queue.fifo_queue is True

    @mock_aws
    @pytest.mark.skip(reason="Moto returns timestamps in float format incompatible with SQS model")
    def test_fetch_resources_with_tags(self):
        """Test fetching queue with tags."""
        session = boto3.Session(region_name="us-east-1")
        sqs_client = session.client("sqs", region_name="us-east-1")

        # Create queue with tags
        queue_url = sqs_client.create_queue(QueueName="tagged-queue")["QueueUrl"]
        sqs_client.tag_queue(
            QueueUrl=queue_url,
            Tags={"Environment": "test", "Team": "platform"},
        )

        fetcher = SQSFetcher(session=session, region="us-east-1")
        resources = fetcher.fetch_resources()

        queue = resources["queues"][0]
        assert queue.tags.get("Environment") == "test"
        assert queue.tags.get("Team") == "platform"


class TestSQSFetcherErrorHandling:
    """Tests for error handling in SQSFetcher."""

    def test_fetch_with_client_error(self, mock_session):
        """Test fetcher handles client errors gracefully."""
        from botocore.exceptions import ClientError

        mock_client = MagicMock()
        mock_client.list_queues.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Access Denied"}},
            "ListQueues",
        )
        mock_session.client.return_value = mock_client

        fetcher = SQSFetcher(session=mock_session, region="us-east-1")
        resources = fetcher.fetch_resources()

        # Should return empty list on error
        assert resources["queues"] == []

    def test_fetch_with_no_client(self, mock_session):
        """Test fetcher handles missing client."""
        mock_session.client.return_value = None

        fetcher = SQSFetcher(session=mock_session, region="us-east-1")

        # Should handle gracefully
        resources = fetcher.fetch_resources()
        assert "queues" in resources

    def test_fetch_queue_attributes_access_denied(self, mock_session):
        """Test fetcher handles AccessDenied error on queue attributes."""
        from botocore.exceptions import ClientError

        mock_client = MagicMock()
        mock_client.list_queues.return_value = {
            "QueueUrls": ["https://sqs.us-east-1.amazonaws.com/123456789012/test-queue"]
        }
        mock_client.get_queue_attributes.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Access Denied"}},
            "GetQueueAttributes",
        )
        mock_session.client.return_value = mock_client

        fetcher = SQSFetcher(session=mock_session, region="us-east-1")
        resources = fetcher.fetch_resources()

        # Should return empty list when queue attributes can't be fetched
        assert resources["queues"] == []

    def test_fetch_queue_non_existent_queue(self, mock_session):
        """Test fetcher handles NonExistentQueue error."""
        from botocore.exceptions import ClientError

        mock_client = MagicMock()
        mock_client.list_queues.return_value = {
            "QueueUrls": ["https://sqs.us-east-1.amazonaws.com/123456789012/test-queue"]
        }
        mock_client.get_queue_attributes.side_effect = ClientError(
            {
                "Error": {
                    "Code": "AWS.SimpleQueueService.NonExistentQueue",
                    "Message": "Queue does not exist",
                }
            },
            "GetQueueAttributes",
        )
        mock_session.client.return_value = mock_client

        fetcher = SQSFetcher(session=mock_session, region="us-east-1")
        resources = fetcher.fetch_resources()

        # Should return empty list when queue doesn't exist
        assert resources["queues"] == []

    def test_fetch_queue_other_client_error(self, mock_session):
        """Test fetcher handles other client errors gracefully."""
        from botocore.exceptions import ClientError

        mock_client = MagicMock()
        mock_client.list_queues.return_value = {
            "QueueUrls": ["https://sqs.us-east-1.amazonaws.com/123456789012/test-queue"]
        }
        mock_client.get_queue_attributes.side_effect = ClientError(
            {"Error": {"Code": "InternalError", "Message": "Internal error"}},
            "GetQueueAttributes",
        )
        mock_session.client.return_value = mock_client

        fetcher = SQSFetcher(session=mock_session, region="us-east-1")
        resources = fetcher.fetch_resources()

        # Should return empty list on other errors
        assert resources["queues"] == []

    def test_fetch_queue_tags_client_error(self, mock_session):
        """Test fetcher handles error when fetching tags."""
        from botocore.exceptions import ClientError

        mock_client = MagicMock()
        mock_client.list_queues.return_value = {
            "QueueUrls": ["https://sqs.us-east-1.amazonaws.com/123456789012/test-queue"]
        }
        mock_client.get_queue_attributes.return_value = {
            "Attributes": {
                "QueueArn": "arn:aws:sqs:us-east-1:123456789012:test-queue",
            }
        }
        mock_client.list_queue_tags.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Access Denied"}},
            "ListQueueTags",
        )
        mock_session.client.return_value = mock_client

        fetcher = SQSFetcher(session=mock_session, region="us-east-1")
        resources = fetcher.fetch_resources()

        # Should still return the queue, just without tags
        assert len(resources["queues"]) == 1
        assert resources["queues"][0].tags == {}

    def test_fetch_queue_success_with_full_attributes(self, mock_session):
        """Test fetcher returns queue with full attributes."""
        mock_client = MagicMock()
        mock_client.list_queues.return_value = {
            "QueueUrls": ["https://sqs.us-east-1.amazonaws.com/123456789012/test-queue"]
        }
        mock_client.get_queue_attributes.return_value = {
            "Attributes": {
                "QueueArn": "arn:aws:sqs:us-east-1:123456789012:test-queue",
                "DelaySeconds": "0",
                "MaximumMessageSize": "262144",
                "MessageRetentionPeriod": "345600",
                "ReceiveMessageWaitTimeSeconds": "0",
                "VisibilityTimeout": "30",
                "FifoQueue": "false",
            }
        }
        mock_client.list_queue_tags.return_value = {
            "Tags": {"Environment": "test"}
        }
        mock_session.client.return_value = mock_client

        fetcher = SQSFetcher(session=mock_session, region="us-east-1")
        resources = fetcher.fetch_resources()

        assert len(resources["queues"]) == 1
        queue = resources["queues"][0]
        assert queue.queue_name == "test-queue"
        assert queue.delay_seconds == 0
        assert queue.tags == {"Environment": "test"}
