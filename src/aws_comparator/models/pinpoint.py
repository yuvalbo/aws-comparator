"""
Pydantic models for AWS Pinpoint service resources.

This module defines strongly-typed models for Pinpoint applications, campaigns,
segments, channels, and event streams.
"""

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from aws_comparator.models.common import AWSResource


class CampaignStatus(str, Enum):
    """Pinpoint campaign status."""

    SCHEDULED = "SCHEDULED"
    EXECUTING = "EXECUTING"
    PENDING_NEXT_RUN = "PENDING_NEXT_RUN"
    COMPLETED = "COMPLETED"
    PAUSED = "PAUSED"
    DELETED = "DELETED"
    INVALID = "INVALID"


class SegmentType(str, Enum):
    """Pinpoint segment type."""

    DIMENSIONAL = "DIMENSIONAL"
    IMPORT = "IMPORT"


class ChannelType(str, Enum):
    """Pinpoint channel type."""

    EMAIL = "EMAIL"
    SMS = "SMS"
    PUSH = "PUSH"
    VOICE = "VOICE"
    CUSTOM = "CUSTOM"
    IN_APP = "IN_APP"


class Frequency(str, Enum):
    """Campaign schedule frequency."""

    ONCE = "ONCE"
    HOURLY = "HOURLY"
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"
    EVENT = "EVENT"


class PinpointApplication(AWSResource):
    """
    Pinpoint application resource model.

    Represents an AWS Pinpoint application with its configuration.
    """

    model_config = ConfigDict(extra="ignore")

    # Basic properties
    application_id: str = Field(..., description="Application ID")
    application_name: str = Field(..., description="Application name")

    # Creation date from Pinpoint API
    creation_date: Optional[str] = Field(
        None, description="Application creation date ISO string"
    )

    @field_validator("application_id")
    @classmethod
    def validate_application_id(cls, v: str) -> str:
        """
        Validate Pinpoint application ID.

        Args:
            v: Application ID to validate

        Returns:
            Validated application ID

        Raises:
            ValueError: If application ID is invalid
        """
        if not v:
            raise ValueError("Application ID cannot be empty")
        return v

    @classmethod
    def from_aws_response(cls, app_data: dict[str, Any]) -> "PinpointApplication":
        """
        Create PinpointApplication instance from AWS API response.

        Args:
            app_data: Application data from AWS Pinpoint API

        Returns:
            PinpointApplication instance
        """
        app_dict = {
            "application_id": app_data.get("Id"),
            "application_name": app_data.get("Name"),
            "arn": app_data.get("Arn"),
            "tags": app_data.get("tags", {}),
            "creation_date": app_data.get("CreationDate"),
        }

        return cls(**app_dict)

    def __str__(self) -> str:
        """Return string representation of Pinpoint application."""
        return f"PinpointApplication(id={self.application_id}, name={self.application_name})"


class CampaignSchedule(BaseModel):
    """Pinpoint campaign schedule configuration."""

    model_config = ConfigDict(extra="ignore")

    start_time: Optional[str] = Field(
        None, description="Campaign start time ISO string"
    )
    end_time: Optional[str] = Field(None, description="Campaign end time ISO string")
    timezone: Optional[str] = Field(None, description="Timezone for schedule")
    frequency: Optional[Frequency] = Field(None, description="Schedule frequency")
    is_local_time: bool = Field(default=False, description="Whether to use local time")
    quiet_time: Optional[dict[str, Any]] = Field(
        None, description="Quiet time configuration"
    )


class MessageConfiguration(BaseModel):
    """Pinpoint campaign message configuration."""

    model_config = ConfigDict(extra="ignore")

    default_message: Optional[dict[str, Any]] = Field(
        None, description="Default message"
    )
    email_message: Optional[dict[str, Any]] = Field(
        None, description="Email message configuration"
    )
    sms_message: Optional[dict[str, Any]] = Field(
        None, description="SMS message configuration"
    )
    push_notification_message: Optional[dict[str, Any]] = Field(
        None, description="Push notification message configuration"
    )
    in_app_message: Optional[dict[str, Any]] = Field(
        None, description="In-app message configuration"
    )
    custom_message: Optional[dict[str, Any]] = Field(
        None, description="Custom message configuration"
    )


class PinpointCampaign(AWSResource):
    """
    Pinpoint campaign resource model.

    Represents a Pinpoint campaign with its configuration and state.
    """

    model_config = ConfigDict(extra="ignore")

    # Basic properties
    application_id: str = Field(..., description="Application ID")
    campaign_id: str = Field(..., description="Campaign ID")
    campaign_name: str = Field(..., description="Campaign name")
    description: Optional[str] = Field(None, description="Campaign description")

    # State
    state: Optional[CampaignStatus] = Field(None, description="Campaign status")

    # Configuration
    schedule: Optional[CampaignSchedule] = Field(None, description="Campaign schedule")
    segment_id: Optional[str] = Field(None, description="Target segment ID")
    segment_version: Optional[int] = Field(None, description="Segment version")
    treatment_name: Optional[str] = Field(None, description="Treatment name")
    treatment_description: Optional[str] = Field(
        None, description="Treatment description"
    )

    # Message configuration
    message_configuration: Optional[MessageConfiguration] = Field(
        None, description="Message configuration"
    )

    # Additional configuration
    holdout_percent: Optional[int] = Field(
        None, ge=0, le=100, description="Holdout percentage"
    )
    hook: Optional[dict[str, Any]] = Field(
        None, description="Campaign hook configuration"
    )
    is_paused: bool = Field(default=False, description="Whether campaign is paused")
    limits: Optional[dict[str, Any]] = Field(None, description="Campaign limits")
    priority: Optional[int] = Field(None, description="Campaign priority")

    # Timestamps
    creation_date: Optional[str] = Field(None, description="Creation date ISO string")
    last_modified_date: Optional[str] = Field(
        None, description="Last modified date ISO string"
    )

    @classmethod
    def from_aws_response(
        cls, campaign_data: dict[str, Any], application_id: str
    ) -> "PinpointCampaign":
        """
        Create PinpointCampaign instance from AWS API response.

        Args:
            campaign_data: Campaign data from AWS Pinpoint API
            application_id: Application ID the campaign belongs to

        Returns:
            PinpointCampaign instance
        """
        campaign_dict = {
            "application_id": application_id,
            "campaign_id": campaign_data.get("Id"),
            "campaign_name": campaign_data.get("Name"),
            "arn": campaign_data.get("Arn"),
            "description": campaign_data.get("Description"),
            "tags": campaign_data.get("tags", {}),
        }

        # State
        if "State" in campaign_data:
            state_data = campaign_data["State"]
            campaign_dict["state"] = state_data.get("CampaignStatus")

        # Schedule
        if "Schedule" in campaign_data:
            schedule = campaign_data["Schedule"]
            campaign_dict["schedule"] = {
                "start_time": schedule.get("StartTime"),
                "end_time": schedule.get("EndTime"),
                "timezone": schedule.get("Timezone"),
                "frequency": schedule.get("Frequency"),
                "is_local_time": schedule.get("IsLocalTime", False),
                "quiet_time": schedule.get("QuietTime"),
            }

        # Segment
        campaign_dict["segment_id"] = campaign_data.get("SegmentId")
        campaign_dict["segment_version"] = campaign_data.get("SegmentVersion")

        # Treatment
        campaign_dict["treatment_name"] = campaign_data.get("TreatmentName")
        campaign_dict["treatment_description"] = campaign_data.get(
            "TreatmentDescription"
        )

        # Message configuration
        if "MessageConfiguration" in campaign_data:
            msg_config = campaign_data["MessageConfiguration"]
            campaign_dict["message_configuration"] = {
                "default_message": msg_config.get("DefaultMessage"),
                "email_message": msg_config.get("EmailMessage"),
                "sms_message": msg_config.get("SMSMessage"),
                "push_notification_message": msg_config.get("PushNotificationMessage"),
                "in_app_message": msg_config.get("InAppMessage"),
                "custom_message": msg_config.get("CustomMessage"),
            }

        # Additional fields
        campaign_dict["holdout_percent"] = campaign_data.get("HoldoutPercent")
        campaign_dict["hook"] = campaign_data.get("Hook")
        campaign_dict["is_paused"] = campaign_data.get("IsPaused", False)
        campaign_dict["limits"] = campaign_data.get("Limits")
        campaign_dict["priority"] = campaign_data.get("Priority")

        # Timestamps
        campaign_dict["creation_date"] = campaign_data.get("CreationDate")
        campaign_dict["last_modified_date"] = campaign_data.get("LastModifiedDate")

        return cls(**campaign_dict)

    def __str__(self) -> str:
        """Return string representation of Pinpoint campaign."""
        return f"PinpointCampaign(id={self.campaign_id}, name={self.campaign_name}, status={self.state})"


class SegmentDimensions(BaseModel):
    """Pinpoint segment dimensions."""

    model_config = ConfigDict(extra="ignore")

    attributes: Optional[dict[str, Any]] = Field(
        None, description="Attribute dimensions"
    )
    behavior: Optional[dict[str, Any]] = Field(None, description="Behavior dimensions")
    demographic: Optional[dict[str, Any]] = Field(
        None, description="Demographic dimensions"
    )
    location: Optional[dict[str, Any]] = Field(None, description="Location dimensions")
    metrics: Optional[dict[str, Any]] = Field(None, description="Metric dimensions")
    user_attributes: Optional[dict[str, Any]] = Field(
        None, description="User attribute dimensions"
    )


class SegmentImportDefinition(BaseModel):
    """Pinpoint segment import definition."""

    model_config = ConfigDict(extra="ignore")

    external_id: Optional[str] = Field(None, description="External ID")
    format: Optional[str] = Field(None, description="Import format")
    s3_url: Optional[str] = Field(None, description="S3 URL")
    role_arn: Optional[str] = Field(None, description="IAM role ARN")
    size: Optional[int] = Field(None, description="Size of import")


class PinpointSegment(AWSResource):
    """
    Pinpoint segment resource model.

    Represents a Pinpoint segment with its definition and configuration.
    """

    model_config = ConfigDict(extra="ignore")

    # Basic properties
    application_id: str = Field(..., description="Application ID")
    segment_id: str = Field(..., description="Segment ID")
    segment_name: str = Field(..., description="Segment name")
    segment_type: Optional[SegmentType] = Field(None, description="Segment type")

    # Segment definition
    dimensions: Optional[SegmentDimensions] = Field(
        None, description="Segment dimensions"
    )
    import_definition: Optional[SegmentImportDefinition] = Field(
        None, description="Import definition for imported segments"
    )

    # Segment groups (for complex segments)
    segment_groups: Optional[dict[str, Any]] = Field(
        None, description="Segment groups configuration"
    )

    # Version
    version: Optional[int] = Field(None, description="Segment version")

    # Timestamps
    creation_date: Optional[str] = Field(None, description="Creation date ISO string")
    last_modified_date: Optional[str] = Field(
        None, description="Last modified date ISO string"
    )

    @classmethod
    def from_aws_response(
        cls, segment_data: dict[str, Any], application_id: str
    ) -> "PinpointSegment":
        """
        Create PinpointSegment instance from AWS API response.

        Args:
            segment_data: Segment data from AWS Pinpoint API
            application_id: Application ID the segment belongs to

        Returns:
            PinpointSegment instance
        """
        segment_dict = {
            "application_id": application_id,
            "segment_id": segment_data.get("Id"),
            "segment_name": segment_data.get("Name"),
            "arn": segment_data.get("Arn"),
            "segment_type": segment_data.get("SegmentType"),
            "tags": segment_data.get("tags", {}),
        }

        # Dimensions
        if "Dimensions" in segment_data:
            dims = segment_data["Dimensions"]
            segment_dict["dimensions"] = {
                "attributes": dims.get("Attributes"),
                "behavior": dims.get("Behavior"),
                "demographic": dims.get("Demographic"),
                "location": dims.get("Location"),
                "metrics": dims.get("Metrics"),
                "user_attributes": dims.get("UserAttributes"),
            }

        # Import definition
        if "ImportDefinition" in segment_data:
            import_def = segment_data["ImportDefinition"]
            segment_dict["import_definition"] = {
                "external_id": import_def.get("ExternalId"),
                "format": import_def.get("Format"),
                "s3_url": import_def.get("S3Url"),
                "role_arn": import_def.get("RoleArn"),
                "size": import_def.get("Size"),
            }

        # Segment groups
        segment_dict["segment_groups"] = segment_data.get("SegmentGroups")

        # Version and timestamps
        segment_dict["version"] = segment_data.get("Version")
        segment_dict["creation_date"] = segment_data.get("CreationDate")
        segment_dict["last_modified_date"] = segment_data.get("LastModifiedDate")

        return cls(**segment_dict)

    def __str__(self) -> str:
        """Return string representation of Pinpoint segment."""
        return f"PinpointSegment(id={self.segment_id}, name={self.segment_name}, type={self.segment_type})"


class PinpointChannel(AWSResource):
    """
    Pinpoint channel resource model.

    Represents a Pinpoint communication channel (Email, SMS, Push, etc.).
    """

    model_config = ConfigDict(extra="ignore")

    # Basic properties
    application_id: str = Field(..., description="Application ID")
    channel_type: ChannelType = Field(..., description="Channel type")
    enabled: bool = Field(default=False, description="Whether channel is enabled")
    is_archived: bool = Field(default=False, description="Whether channel is archived")

    # Channel-specific configuration
    configuration: dict[str, Any] = Field(
        default_factory=dict, description="Channel-specific configuration"
    )

    # Platform (for push channels)
    platform: Optional[str] = Field(None, description="Platform for push notifications")

    # Identity (for email/SMS channels)
    identity: Optional[str] = Field(None, description="Identity ARN (for email)")
    role_arn: Optional[str] = Field(None, description="IAM role ARN")
    from_address: Optional[str] = Field(None, description="From address (for email)")
    sender_id: Optional[str] = Field(None, description="Sender ID (for SMS)")

    # Metrics
    has_credential: bool = Field(
        default=False, description="Whether credentials are configured"
    )
    version: Optional[int] = Field(None, description="Channel version")

    # Timestamps
    creation_date: Optional[str] = Field(None, description="Creation date ISO string")
    last_modified_date: Optional[str] = Field(
        None, description="Last modified date ISO string"
    )

    @classmethod
    def from_aws_response(
        cls,
        channel_data: dict[str, Any],
        application_id: str,
        channel_type: ChannelType,
    ) -> "PinpointChannel":
        """
        Create PinpointChannel instance from AWS API response.

        Args:
            channel_data: Channel data from AWS Pinpoint API
            application_id: Application ID the channel belongs to
            channel_type: Type of channel

        Returns:
            PinpointChannel instance
        """
        channel_dict = {
            "application_id": application_id,
            "channel_type": channel_type,
            "enabled": channel_data.get("Enabled", False),
            "is_archived": channel_data.get("IsArchived", False),
            "platform": channel_data.get("Platform"),
            "has_credential": channel_data.get("HasCredential", False),
            "version": channel_data.get("Version"),
        }

        # Channel-specific fields
        if channel_type == ChannelType.EMAIL:
            channel_dict["from_address"] = channel_data.get("FromAddress")
            channel_dict["identity"] = channel_data.get("Identity")
            channel_dict["role_arn"] = channel_data.get("RoleArn")
            channel_dict["configuration"] = {
                "configuration_set": channel_data.get("ConfigurationSet"),
            }
        elif channel_type == ChannelType.SMS:
            channel_dict["sender_id"] = channel_data.get("SenderId")
            channel_dict["configuration"] = {
                "short_code": channel_data.get("ShortCode"),
            }
        elif channel_type == ChannelType.PUSH:
            channel_dict["configuration"] = {
                "credential": channel_data.get("Credential"),
                "default_authentication_method": channel_data.get(
                    "DefaultAuthenticationMethod"
                ),
            }
        else:
            # Store all configuration for other channel types
            channel_dict["configuration"] = {
                k: v
                for k, v in channel_data.items()
                if k
                not in [
                    "ApplicationId",
                    "Enabled",
                    "IsArchived",
                    "Platform",
                    "HasCredential",
                    "Version",
                    "CreationDate",
                    "LastModifiedDate",
                    "Id",
                ]
            }

        # Timestamps
        channel_dict["creation_date"] = channel_data.get("CreationDate")
        channel_dict["last_modified_date"] = channel_data.get("LastModifiedDate")

        return cls(**channel_dict)

    def __str__(self) -> str:
        """Return string representation of Pinpoint channel."""
        status = "enabled" if self.enabled else "disabled"
        return f"PinpointChannel(type={self.channel_type}, status={status})"


class PinpointEventStream(AWSResource):
    """
    Pinpoint event stream resource model.

    Represents a Pinpoint event stream configuration for streaming events
    to Kinesis.
    """

    model_config = ConfigDict(extra="ignore")

    # Basic properties
    application_id: str = Field(..., description="Application ID")
    destination_stream_arn: str = Field(..., description="Kinesis stream ARN")
    role_arn: str = Field(..., description="IAM role ARN")

    # Configuration
    external_id: Optional[str] = Field(
        None, description="External ID for role assumption"
    )
    last_modified_date: Optional[str] = Field(
        None, description="Last modified date ISO string"
    )
    last_updated_by: Optional[str] = Field(
        None, description="Last updated by user/service"
    )

    @classmethod
    def from_aws_response(
        cls, event_stream_data: dict[str, Any], application_id: str
    ) -> "PinpointEventStream":
        """
        Create PinpointEventStream instance from AWS API response.

        Args:
            event_stream_data: Event stream data from AWS Pinpoint API
            application_id: Application ID the event stream belongs to

        Returns:
            PinpointEventStream instance
        """
        dest_arn: str = event_stream_data.get("DestinationStreamArn") or ""
        role_arn: str = event_stream_data.get("RoleArn") or ""
        return cls(
            application_id=application_id,
            destination_stream_arn=dest_arn,
            role_arn=role_arn,
            external_id=event_stream_data.get("ExternalId"),
            last_modified_date=event_stream_data.get("LastModifiedDate"),
            last_updated_by=event_stream_data.get("LastUpdatedBy"),
            arn=None,
            created_date=None,
            region=None,
        )

    def __str__(self) -> str:
        """Return string representation of Pinpoint event stream."""
        return f"PinpointEventStream(stream={self.destination_stream_arn})"
