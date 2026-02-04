"""Tests for SNS service fetcher."""

from unittest.mock import MagicMock

import boto3
import pytest
from moto import mock_aws

from aws_comparator.services.sns.fetcher import SNSFetcher


@pytest.fixture
def mock_session():
    """Create a mock boto3 session."""
    session = MagicMock()
    return session


class TestSNSFetcherInit:
    """Tests for SNSFetcher initialization."""

    def test_init_sets_service_name(self, mock_session):
        """Test fetcher sets correct service name."""
        fetcher = SNSFetcher(session=mock_session, region="us-east-1")
        assert fetcher.SERVICE_NAME == "sns"

    def test_init_sets_region(self, mock_session):
        """Test fetcher sets region."""
        fetcher = SNSFetcher(session=mock_session, region="us-west-2")
        assert fetcher.region == "us-west-2"


class TestSNSFetcherGetResourceTypes:
    """Tests for get_resource_types method."""

    def test_get_resource_types(self, mock_session):
        """Test get_resource_types returns expected types."""
        fetcher = SNSFetcher(session=mock_session, region="us-east-1")
        resource_types = fetcher.get_resource_types()

        assert "topics" in resource_types
        assert "subscriptions" in resource_types


class TestSNSFetcherFetchResources:
    """Tests for fetch_resources method."""

    @mock_aws
    def test_fetch_resources_empty(self):
        """Test fetching resources when no topics exist."""
        session = boto3.Session(region_name="us-east-1")
        fetcher = SNSFetcher(session=session, region="us-east-1")

        resources = fetcher.fetch_resources()

        assert "topics" in resources
        assert "subscriptions" in resources
        assert len(resources["topics"]) == 0
        assert len(resources["subscriptions"]) == 0

    @mock_aws
    def test_fetch_resources_with_topics(self):
        """Test fetching resources with existing topics."""
        session = boto3.Session(region_name="us-east-1")
        sns_client = session.client("sns", region_name="us-east-1")

        # Create test topics
        sns_client.create_topic(Name="test-topic-1")
        sns_client.create_topic(Name="test-topic-2")

        fetcher = SNSFetcher(session=session, region="us-east-1")
        resources = fetcher.fetch_resources()

        assert "topics" in resources
        assert len(resources["topics"]) == 2

    @mock_aws
    def test_fetch_resources_topic_properties(self):
        """Test fetched topics have expected properties."""
        session = boto3.Session(region_name="us-east-1")
        sns_client = session.client("sns", region_name="us-east-1")

        # Create test topic
        sns_client.create_topic(Name="test-topic")

        fetcher = SNSFetcher(session=session, region="us-east-1")
        resources = fetcher.fetch_resources()

        topic = resources["topics"][0]
        assert hasattr(topic, "topic_name")
        assert topic.topic_name == "test-topic"
        assert hasattr(topic, "topic_arn")

    @mock_aws
    def test_fetch_resources_fifo_topic(self):
        """Test fetching FIFO topic."""
        session = boto3.Session(region_name="us-east-1")
        sns_client = session.client("sns", region_name="us-east-1")

        # Create FIFO topic
        sns_client.create_topic(
            Name="test-topic.fifo",
            Attributes={"FifoTopic": "true"},
        )

        fetcher = SNSFetcher(session=session, region="us-east-1")
        resources = fetcher.fetch_resources()

        assert len(resources["topics"]) == 1
        topic = resources["topics"][0]
        assert topic.fifo_topic is True

    @mock_aws
    def test_fetch_resources_with_subscriptions(self):
        """Test fetching topics with subscriptions."""
        session = boto3.Session(region_name="us-east-1")
        sns_client = session.client("sns", region_name="us-east-1")

        # Create topic and subscription
        topic_arn = sns_client.create_topic(Name="test-topic")["TopicArn"]
        sns_client.subscribe(
            TopicArn=topic_arn,
            Protocol="email",
            Endpoint="test@example.com",
        )

        fetcher = SNSFetcher(session=session, region="us-east-1")
        resources = fetcher.fetch_resources()

        assert len(resources["topics"]) == 1
        # Note: moto may not fully support subscription confirmation
        assert "subscriptions" in resources

    @mock_aws
    def test_fetch_resources_with_tags(self):
        """Test fetching topic with tags."""
        session = boto3.Session(region_name="us-east-1")
        sns_client = session.client("sns", region_name="us-east-1")

        # Create topic with tags
        sns_client.create_topic(
            Name="tagged-topic",
            Tags=[
                {"Key": "Environment", "Value": "test"},
                {"Key": "Team", "Value": "platform"},
            ],
        )

        fetcher = SNSFetcher(session=session, region="us-east-1")
        resources = fetcher.fetch_resources()

        topic = resources["topics"][0]
        assert topic.tags.get("Environment") == "test"
        assert topic.tags.get("Team") == "platform"


class TestSNSFetcherErrorHandling:
    """Tests for error handling in SNSFetcher."""

    def test_fetch_with_client_error(self, mock_session):
        """Test fetcher handles client errors gracefully."""
        from botocore.exceptions import ClientError

        mock_client = MagicMock()
        mock_client.get_paginator.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Access Denied"}},
            "ListTopics",
        )
        mock_session.client.return_value = mock_client

        fetcher = SNSFetcher(session=mock_session, region="us-east-1")
        resources = fetcher.fetch_resources()

        # Should return empty lists on error
        assert resources["topics"] == []
        assert resources["subscriptions"] == []

    def test_fetch_with_no_client(self, mock_session):
        """Test fetcher handles missing client."""
        mock_session.client.return_value = None

        fetcher = SNSFetcher(session=mock_session, region="us-east-1")

        # Should handle gracefully
        resources = fetcher.fetch_resources()
        assert "topics" in resources
        assert "subscriptions" in resources
