"""
AWS Pinpoint service fetcher.

This module implements fetching of Pinpoint application, campaign, segment,
channel, and event stream resources.
"""

from typing import Any

from botocore.exceptions import ClientError  # type: ignore[import-untyped]

from aws_comparator.core.registry import ServiceRegistry
from aws_comparator.models.common import AWSResource
from aws_comparator.models.pinpoint import (
    ChannelType,
    PinpointApplication,
    PinpointCampaign,
    PinpointChannel,
    PinpointEventStream,
    PinpointSegment,
)
from aws_comparator.services.base import BaseServiceFetcher


@ServiceRegistry.register(
    "pinpoint",
    description="Amazon Pinpoint (Customer Engagement)",
    resource_types=[
        "applications",
        "campaigns",
        "segments",
        "channels",
        "event_streams",
    ],
)
class PinpointFetcher(BaseServiceFetcher):
    """
    Fetcher for AWS Pinpoint resources.

    This fetcher retrieves Pinpoint resources including:
    - Applications
    - Campaigns (per application)
    - Segments (per application)
    - Channels (Email, SMS, Push per application)
    - Event Streams (per application)
    """

    SERVICE_NAME = "pinpoint"

    def _create_client(self) -> Any:
        """
        Create boto3 Pinpoint client.

        Returns:
            Configured boto3 Pinpoint client
        """
        return self.session.client("pinpoint", region_name=self.region)

    def fetch_resources(self) -> dict[str, list[AWSResource]]:
        """
        Fetch all Pinpoint resources.

        Returns:
            Dictionary mapping resource types to lists of resources
        """
        return {
            "applications": self._safe_fetch("applications", self._fetch_applications),
            "campaigns": self._safe_fetch("campaigns", self._fetch_campaigns),
            "segments": self._safe_fetch("segments", self._fetch_segments),
            "channels": self._safe_fetch("channels", self._fetch_channels),
            "event_streams": self._safe_fetch(
                "event_streams", self._fetch_event_streams
            ),
        }

    def get_resource_types(self) -> list[str]:
        """
        Get list of resource types handled by this fetcher.

        Returns:
            List of resource type names
        """
        return ["applications", "campaigns", "segments", "channels", "event_streams"]

    def _fetch_applications(self) -> list[PinpointApplication]:
        """
        Fetch all Pinpoint applications.

        Returns:
            List of PinpointApplication resources
        """
        applications: list[PinpointApplication] = []

        try:
            # Fetch applications using pagination if available
            # Note: get_apps doesn't have native pagination, but we handle NextToken
            if self.client is None:
                return applications
            response = self.client.get_apps()

            if "ApplicationsResponse" in response:
                apps_response = response["ApplicationsResponse"]
                app_items = apps_response.get("Item", [])

                self.logger.info(f"Found {len(app_items)} Pinpoint applications")

                for app_data in app_items:
                    try:
                        application = PinpointApplication.from_aws_response(app_data)
                        applications.append(application)

                        app_name = app_data.get("Name", app_data.get("Id"))
                        self.logger.debug(f"Fetched application: {app_name}")

                    except Exception as e:
                        app_id = app_data.get("Id", "unknown")
                        self.logger.error(
                            f"Error parsing application {app_id}: {e}", exc_info=True
                        )

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code in ["AccessDenied", "UnauthorizedOperation"]:
                self.logger.warning(
                    f"Cannot access Pinpoint applications: {error_code}"
                )
            else:
                self.logger.error(
                    f"Error fetching Pinpoint applications: {e}", exc_info=True
                )
        except Exception as e:
            self.logger.error(
                f"Failed to list Pinpoint applications: {e}", exc_info=True
            )

        return applications

    def _fetch_campaigns(self) -> list[PinpointCampaign]:
        """
        Fetch all campaigns across all applications.

        Returns:
            List of PinpointCampaign resources
        """
        campaigns: list[PinpointCampaign] = []

        # First get all applications
        applications = self._fetch_applications()

        for app in applications:
            try:
                # Get campaigns for this application
                if self.client is None:
                    continue
                response = self.client.get_campaigns(ApplicationId=app.application_id)

                if "CampaignsResponse" in response:
                    campaigns_response = response["CampaignsResponse"]
                    campaign_items = campaigns_response.get("Item", [])

                    self.logger.debug(
                        f"Found {len(campaign_items)} campaigns for app {app.application_id}"
                    )

                    for campaign_data in campaign_items:
                        try:
                            campaign = PinpointCampaign.from_aws_response(
                                campaign_data, app.application_id
                            )
                            campaigns.append(campaign)

                        except Exception as e:
                            campaign_id = campaign_data.get("Id", "unknown")
                            self.logger.error(
                                f"Error parsing campaign {campaign_id}: {e}",
                                exc_info=True,
                            )

            except ClientError as e:
                error_code = e.response.get("Error", {}).get("Code", "")
                if error_code in ["AccessDenied", "NotFoundException"]:
                    self.logger.warning(
                        f"Cannot access campaigns for app {app.application_id}: {error_code}"
                    )
                else:
                    self.logger.error(
                        f"Error fetching campaigns for app {app.application_id}: {e}",
                        exc_info=True,
                    )

        self.logger.info(f"Fetched total of {len(campaigns)} campaigns")
        return campaigns

    def _fetch_segments(self) -> list[PinpointSegment]:
        """
        Fetch all segments across all applications.

        Returns:
            List of PinpointSegment resources
        """
        segments: list[PinpointSegment] = []

        # First get all applications
        applications = self._fetch_applications()

        for app in applications:
            try:
                # Get segments for this application
                if self.client is None:
                    continue
                response = self.client.get_segments(ApplicationId=app.application_id)

                if "SegmentsResponse" in response:
                    segments_response = response["SegmentsResponse"]
                    segment_items = segments_response.get("Item", [])

                    self.logger.debug(
                        f"Found {len(segment_items)} segments for app {app.application_id}"
                    )

                    for segment_data in segment_items:
                        try:
                            segment = PinpointSegment.from_aws_response(
                                segment_data, app.application_id
                            )
                            segments.append(segment)

                        except Exception as e:
                            segment_id = segment_data.get("Id", "unknown")
                            self.logger.error(
                                f"Error parsing segment {segment_id}: {e}",
                                exc_info=True,
                            )

            except ClientError as e:
                error_code = e.response.get("Error", {}).get("Code", "")
                if error_code in ["AccessDenied", "NotFoundException"]:
                    self.logger.warning(
                        f"Cannot access segments for app {app.application_id}: {error_code}"
                    )
                else:
                    self.logger.error(
                        f"Error fetching segments for app {app.application_id}: {e}",
                        exc_info=True,
                    )

        self.logger.info(f"Fetched total of {len(segments)} segments")
        return segments

    def _fetch_channels(self) -> list[PinpointChannel]:
        """
        Fetch all channels across all applications.

        Retrieves Email, SMS, and Push channels for each application.

        Returns:
            List of PinpointChannel resources
        """
        channels: list[PinpointChannel] = []

        # First get all applications
        applications = self._fetch_applications()

        # Channel types to fetch with their corresponding API methods
        channel_methods = [
            (ChannelType.EMAIL, "get_email_channel"),
            (ChannelType.SMS, "get_sms_channel"),
            (ChannelType.PUSH, "get_apns_channel"),  # Apple Push
            (ChannelType.PUSH, "get_gcm_channel"),  # Google Cloud Messaging
        ]

        for app in applications:
            # Try to fetch each channel type
            for channel_type, method_name in channel_methods:
                try:
                    method = getattr(self.client, method_name)
                    response = method(ApplicationId=app.application_id)

                    # Response key varies by channel type
                    response_keys = {
                        "get_email_channel": "EmailChannelResponse",
                        "get_sms_channel": "SMSChannelResponse",
                        "get_apns_channel": "APNSChannelResponse",
                        "get_gcm_channel": "GCMChannelResponse",
                    }

                    response_key = response_keys.get(method_name)
                    if response_key and response_key in response:
                        channel_data = response[response_key]

                        try:
                            channel = PinpointChannel.from_aws_response(
                                channel_data, app.application_id, channel_type
                            )
                            channels.append(channel)

                            self.logger.debug(
                                f"Fetched {channel_type} channel for app {app.application_id}"
                            )

                        except Exception as e:
                            self.logger.error(
                                f"Error parsing {channel_type} channel for app {app.application_id}: {e}",
                                exc_info=True,
                            )

                except ClientError as e:
                    error_code = e.response.get("Error", {}).get("Code", "")
                    # NotFoundException is expected if channel is not configured
                    if error_code != "NotFoundException":
                        if error_code in ["AccessDenied"]:
                            self.logger.warning(
                                f"Cannot access {channel_type} channel for app {app.application_id}: {error_code}"
                            )
                        else:
                            self.logger.debug(
                                f"Error fetching {channel_type} channel for app {app.application_id}: {error_code}"
                            )
                except Exception as e:
                    self.logger.error(
                        f"Unexpected error fetching {channel_type} channel for app {app.application_id}: {e}",
                        exc_info=True,
                    )

        self.logger.info(f"Fetched total of {len(channels)} channels")
        return channels

    def _fetch_event_streams(self) -> list[PinpointEventStream]:
        """
        Fetch all event streams across all applications.

        Returns:
            List of PinpointEventStream resources
        """
        event_streams: list[PinpointEventStream] = []

        # First get all applications
        applications = self._fetch_applications()

        for app in applications:
            try:
                # Get event stream for this application
                if self.client is None:
                    continue
                response = self.client.get_event_stream(
                    ApplicationId=app.application_id
                )

                if "EventStream" in response:
                    event_stream_data = response["EventStream"]

                    try:
                        event_stream = PinpointEventStream.from_aws_response(
                            event_stream_data, app.application_id
                        )
                        event_streams.append(event_stream)

                        self.logger.debug(
                            f"Fetched event stream for app {app.application_id}"
                        )

                    except Exception as e:
                        self.logger.error(
                            f"Error parsing event stream for app {app.application_id}: {e}",
                            exc_info=True,
                        )

            except ClientError as e:
                error_code = e.response.get("Error", {}).get("Code", "")
                # NotFoundException is expected if event stream is not configured
                if error_code != "NotFoundException":
                    if error_code in ["AccessDenied"]:
                        self.logger.warning(
                            f"Cannot access event stream for app {app.application_id}: {error_code}"
                        )
                    else:
                        self.logger.error(
                            f"Error fetching event stream for app {app.application_id}: {e}",
                            exc_info=True,
                        )
            except Exception as e:
                self.logger.error(
                    f"Unexpected error fetching event stream for app {app.application_id}: {e}",
                    exc_info=True,
                )

        self.logger.info(f"Fetched total of {len(event_streams)} event streams")
        return event_streams
