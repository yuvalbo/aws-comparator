"""
Unit tests for AWS Pinpoint service fetcher.

This module tests the PinpointFetcher class functionality including:
- Application fetching
- Campaign fetching
- Segment fetching
- Channel fetching
- Event stream fetching
- Error handling
"""

from unittest.mock import Mock

import pytest
from botocore.exceptions import ClientError

from aws_comparator.models.pinpoint import (
    ChannelType,
    PinpointApplication,
    PinpointCampaign,
    PinpointChannel,
    PinpointEventStream,
    PinpointSegment,
)
from aws_comparator.services.pinpoint.fetcher import PinpointFetcher


@pytest.fixture
def mock_session() -> Mock:
    """
    Create a mock boto3 session.

    Returns:
        Mock session object
    """
    session = Mock()
    return session


@pytest.fixture
def mock_pinpoint_client() -> Mock:
    """
    Create a mock Pinpoint client.

    Returns:
        Mock Pinpoint client
    """
    client = Mock()
    return client


@pytest.fixture
def pinpoint_fetcher(mock_session: Mock, mock_pinpoint_client: Mock) -> PinpointFetcher:
    """
    Create a PinpointFetcher instance with mocked dependencies.

    Args:
        mock_session: Mock boto3 session
        mock_pinpoint_client: Mock Pinpoint client

    Returns:
        PinpointFetcher instance
    """
    mock_session.client.return_value = mock_pinpoint_client
    fetcher = PinpointFetcher(mock_session, "us-east-1")
    return fetcher


class TestPinpointFetcherInit:
    """Test PinpointFetcher initialization."""

    def test_init_creates_client(self, mock_session: Mock) -> None:
        """Test that initialization creates a Pinpoint client."""
        fetcher = PinpointFetcher(mock_session, "us-west-2")

        mock_session.client.assert_called_once_with("pinpoint", region_name="us-west-2")
        assert fetcher.SERVICE_NAME == "pinpoint"
        assert fetcher.region == "us-west-2"

    def test_get_resource_types(self, pinpoint_fetcher: PinpointFetcher) -> None:
        """Test that get_resource_types returns correct types."""
        resource_types = pinpoint_fetcher.get_resource_types()

        assert len(resource_types) == 5
        assert "applications" in resource_types
        assert "campaigns" in resource_types
        assert "segments" in resource_types
        assert "channels" in resource_types
        assert "event_streams" in resource_types


class TestFetchApplications:
    """Test fetching Pinpoint applications."""

    def test_fetch_applications_success(
        self, pinpoint_fetcher: PinpointFetcher, mock_pinpoint_client: Mock
    ) -> None:
        """Test successful fetching of applications."""
        mock_pinpoint_client.get_apps.return_value = {
            "ApplicationsResponse": {
                "Item": [
                    {
                        "Id": "app-123",
                        "Arn": "arn:aws:mobiletargeting:us-east-1:123456789012:apps/app-123",
                        "Name": "TestApp",
                        "tags": {"Environment": "test"},
                        "CreationDate": "2024-01-01T00:00:00Z",
                    },
                    {
                        "Id": "app-456",
                        "Arn": "arn:aws:mobiletargeting:us-east-1:123456789012:apps/app-456",
                        "Name": "ProdApp",
                        "tags": {"Environment": "production"},
                        "CreationDate": "2024-01-02T00:00:00Z",
                    },
                ]
            }
        }

        applications = pinpoint_fetcher._fetch_applications()

        assert len(applications) == 2
        assert isinstance(applications[0], PinpointApplication)
        assert applications[0].application_id == "app-123"
        assert applications[0].application_name == "TestApp"
        assert applications[0].tags == {"Environment": "test"}
        assert applications[1].application_id == "app-456"

    def test_fetch_applications_empty(
        self, pinpoint_fetcher: PinpointFetcher, mock_pinpoint_client: Mock
    ) -> None:
        """Test fetching applications when none exist."""
        mock_pinpoint_client.get_apps.return_value = {
            "ApplicationsResponse": {"Item": []}
        }

        applications = pinpoint_fetcher._fetch_applications()

        assert len(applications) == 0

    def test_fetch_applications_access_denied(
        self, pinpoint_fetcher: PinpointFetcher, mock_pinpoint_client: Mock
    ) -> None:
        """Test handling of access denied error."""
        mock_pinpoint_client.get_apps.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Access Denied"}}, "GetApps"
        )

        applications = pinpoint_fetcher._fetch_applications()

        assert len(applications) == 0

    def test_fetch_applications_client_error(
        self, pinpoint_fetcher: PinpointFetcher, mock_pinpoint_client: Mock
    ) -> None:
        """Test handling of general client error."""
        mock_pinpoint_client.get_apps.side_effect = ClientError(
            {"Error": {"Code": "InternalError", "Message": "Internal error"}}, "GetApps"
        )

        applications = pinpoint_fetcher._fetch_applications()

        assert len(applications) == 0


class TestFetchCampaigns:
    """Test fetching Pinpoint campaigns."""

    def test_fetch_campaigns_success(
        self, pinpoint_fetcher: PinpointFetcher, mock_pinpoint_client: Mock
    ) -> None:
        """Test successful fetching of campaigns."""
        # Mock applications
        mock_pinpoint_client.get_apps.return_value = {
            "ApplicationsResponse": {
                "Item": [
                    {
                        "Id": "app-123",
                        "Arn": "arn:aws:mobiletargeting:us-east-1:123456789012:apps/app-123",
                        "Name": "TestApp",
                        "tags": {},
                        "CreationDate": "2024-01-01T00:00:00Z",
                    }
                ]
            }
        }

        # Mock campaigns
        mock_pinpoint_client.get_campaigns.return_value = {
            "CampaignsResponse": {
                "Item": [
                    {
                        "Id": "camp-123",
                        "Arn": "arn:aws:mobiletargeting:us-east-1:123456789012:apps/app-123/campaigns/camp-123",
                        "Name": "TestCampaign",
                        "Description": "Test campaign",
                        "State": {"CampaignStatus": "SCHEDULED"},
                        "SegmentId": "seg-123",
                        "tags": {},
                        "CreationDate": "2024-01-01T00:00:00Z",
                    }
                ]
            }
        }

        campaigns = pinpoint_fetcher._fetch_campaigns()

        assert len(campaigns) == 1
        assert isinstance(campaigns[0], PinpointCampaign)
        assert campaigns[0].campaign_id == "camp-123"
        assert campaigns[0].campaign_name == "TestCampaign"
        assert campaigns[0].application_id == "app-123"
        assert campaigns[0].state == "SCHEDULED"

    def test_fetch_campaigns_no_applications(
        self, pinpoint_fetcher: PinpointFetcher, mock_pinpoint_client: Mock
    ) -> None:
        """Test fetching campaigns when no applications exist."""
        mock_pinpoint_client.get_apps.return_value = {
            "ApplicationsResponse": {"Item": []}
        }

        campaigns = pinpoint_fetcher._fetch_campaigns()

        assert len(campaigns) == 0
        mock_pinpoint_client.get_campaigns.assert_not_called()

    def test_fetch_campaigns_not_found(
        self, pinpoint_fetcher: PinpointFetcher, mock_pinpoint_client: Mock
    ) -> None:
        """Test handling of not found error for campaigns."""
        mock_pinpoint_client.get_apps.return_value = {
            "ApplicationsResponse": {
                "Item": [
                    {
                        "Id": "app-123",
                        "Arn": "arn:aws:mobiletargeting:us-east-1:123456789012:apps/app-123",
                        "Name": "TestApp",
                        "tags": {},
                        "CreationDate": "2024-01-01T00:00:00Z",
                    }
                ]
            }
        }

        mock_pinpoint_client.get_campaigns.side_effect = ClientError(
            {"Error": {"Code": "NotFoundException", "Message": "Not found"}},
            "GetCampaigns",
        )

        campaigns = pinpoint_fetcher._fetch_campaigns()

        assert len(campaigns) == 0


class TestFetchSegments:
    """Test fetching Pinpoint segments."""

    def test_fetch_segments_success(
        self, pinpoint_fetcher: PinpointFetcher, mock_pinpoint_client: Mock
    ) -> None:
        """Test successful fetching of segments."""
        # Mock applications
        mock_pinpoint_client.get_apps.return_value = {
            "ApplicationsResponse": {
                "Item": [
                    {
                        "Id": "app-123",
                        "Arn": "arn:aws:mobiletargeting:us-east-1:123456789012:apps/app-123",
                        "Name": "TestApp",
                        "tags": {},
                        "CreationDate": "2024-01-01T00:00:00Z",
                    }
                ]
            }
        }

        # Mock segments
        mock_pinpoint_client.get_segments.return_value = {
            "SegmentsResponse": {
                "Item": [
                    {
                        "Id": "seg-123",
                        "Arn": "arn:aws:mobiletargeting:us-east-1:123456789012:apps/app-123/segments/seg-123",
                        "Name": "TestSegment",
                        "SegmentType": "DIMENSIONAL",
                        "Version": 1,
                        "tags": {},
                        "CreationDate": "2024-01-01T00:00:00Z",
                    }
                ]
            }
        }

        segments = pinpoint_fetcher._fetch_segments()

        assert len(segments) == 1
        assert isinstance(segments[0], PinpointSegment)
        assert segments[0].segment_id == "seg-123"
        assert segments[0].segment_name == "TestSegment"
        assert segments[0].application_id == "app-123"
        assert segments[0].segment_type == "DIMENSIONAL"

    def test_fetch_segments_empty(
        self, pinpoint_fetcher: PinpointFetcher, mock_pinpoint_client: Mock
    ) -> None:
        """Test fetching segments when none exist."""
        mock_pinpoint_client.get_apps.return_value = {
            "ApplicationsResponse": {
                "Item": [
                    {
                        "Id": "app-123",
                        "Arn": "arn:aws:mobiletargeting:us-east-1:123456789012:apps/app-123",
                        "Name": "TestApp",
                        "tags": {},
                        "CreationDate": "2024-01-01T00:00:00Z",
                    }
                ]
            }
        }

        mock_pinpoint_client.get_segments.return_value = {
            "SegmentsResponse": {"Item": []}
        }

        segments = pinpoint_fetcher._fetch_segments()

        assert len(segments) == 0


class TestFetchChannels:
    """Test fetching Pinpoint channels."""

    def test_fetch_channels_success(
        self, pinpoint_fetcher: PinpointFetcher, mock_pinpoint_client: Mock
    ) -> None:
        """Test successful fetching of channels."""
        # Mock applications
        mock_pinpoint_client.get_apps.return_value = {
            "ApplicationsResponse": {
                "Item": [
                    {
                        "Id": "app-123",
                        "Arn": "arn:aws:mobiletargeting:us-east-1:123456789012:apps/app-123",
                        "Name": "TestApp",
                        "tags": {},
                        "CreationDate": "2024-01-01T00:00:00Z",
                    }
                ]
            }
        }

        # Mock email channel
        mock_pinpoint_client.get_email_channel.return_value = {
            "EmailChannelResponse": {
                "ApplicationId": "app-123",
                "Enabled": True,
                "FromAddress": "noreply@example.com",
                "Identity": "arn:aws:ses:us-east-1:123456789012:identity/example.com",
                "Platform": "EMAIL",
                "Id": "email",
            }
        }

        # Mock SMS channel not found
        mock_pinpoint_client.get_sms_channel.side_effect = ClientError(
            {"Error": {"Code": "NotFoundException", "Message": "Not found"}},
            "GetSmsChannel",
        )

        # Mock APNS channel not found
        mock_pinpoint_client.get_apns_channel.side_effect = ClientError(
            {"Error": {"Code": "NotFoundException", "Message": "Not found"}},
            "GetApnsChannel",
        )

        # Mock GCM channel not found
        mock_pinpoint_client.get_gcm_channel.side_effect = ClientError(
            {"Error": {"Code": "NotFoundException", "Message": "Not found"}},
            "GetGcmChannel",
        )

        channels = pinpoint_fetcher._fetch_channels()

        assert len(channels) == 1
        assert isinstance(channels[0], PinpointChannel)
        assert channels[0].channel_type == ChannelType.EMAIL
        assert channels[0].application_id == "app-123"
        assert channels[0].enabled is True

    def test_fetch_channels_no_applications(
        self, pinpoint_fetcher: PinpointFetcher, mock_pinpoint_client: Mock
    ) -> None:
        """Test fetching channels when no applications exist."""
        mock_pinpoint_client.get_apps.return_value = {
            "ApplicationsResponse": {"Item": []}
        }

        channels = pinpoint_fetcher._fetch_channels()

        assert len(channels) == 0


class TestFetchEventStreams:
    """Test fetching Pinpoint event streams."""

    def test_fetch_event_streams_success(
        self, pinpoint_fetcher: PinpointFetcher, mock_pinpoint_client: Mock
    ) -> None:
        """Test successful fetching of event streams."""
        # Mock applications
        mock_pinpoint_client.get_apps.return_value = {
            "ApplicationsResponse": {
                "Item": [
                    {
                        "Id": "app-123",
                        "Arn": "arn:aws:mobiletargeting:us-east-1:123456789012:apps/app-123",
                        "Name": "TestApp",
                        "tags": {},
                        "CreationDate": "2024-01-01T00:00:00Z",
                    }
                ]
            }
        }

        # Mock event stream
        mock_pinpoint_client.get_event_stream.return_value = {
            "EventStream": {
                "ApplicationId": "app-123",
                "DestinationStreamArn": "arn:aws:kinesis:us-east-1:123456789012:stream/pinpoint-events",
                "RoleArn": "arn:aws:iam::123456789012:role/PinpointEventStreamRole",
                "ExternalId": "ext-123",
            }
        }

        event_streams = pinpoint_fetcher._fetch_event_streams()

        assert len(event_streams) == 1
        assert isinstance(event_streams[0], PinpointEventStream)
        assert event_streams[0].application_id == "app-123"
        assert "kinesis" in event_streams[0].destination_stream_arn

    def test_fetch_event_streams_not_found(
        self, pinpoint_fetcher: PinpointFetcher, mock_pinpoint_client: Mock
    ) -> None:
        """Test handling of not found error for event streams."""
        mock_pinpoint_client.get_apps.return_value = {
            "ApplicationsResponse": {
                "Item": [
                    {
                        "Id": "app-123",
                        "Arn": "arn:aws:mobiletargeting:us-east-1:123456789012:apps/app-123",
                        "Name": "TestApp",
                        "tags": {},
                        "CreationDate": "2024-01-01T00:00:00Z",
                    }
                ]
            }
        }

        mock_pinpoint_client.get_event_stream.side_effect = ClientError(
            {"Error": {"Code": "NotFoundException", "Message": "Not found"}},
            "GetEventStream",
        )

        event_streams = pinpoint_fetcher._fetch_event_streams()

        assert len(event_streams) == 0


class TestFetchResources:
    """Test fetching all resources."""

    def test_fetch_resources_success(
        self, pinpoint_fetcher: PinpointFetcher, mock_pinpoint_client: Mock
    ) -> None:
        """Test successful fetching of all resources."""
        # Mock empty responses for all resource types
        mock_pinpoint_client.get_apps.return_value = {
            "ApplicationsResponse": {"Item": []}
        }

        resources = pinpoint_fetcher.fetch_resources()

        assert "applications" in resources
        assert "campaigns" in resources
        assert "segments" in resources
        assert "channels" in resources
        assert "event_streams" in resources
        assert len(resources) == 5
