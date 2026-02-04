"""
Pydantic models for AWS EventBridge service resources.

This module defines strongly-typed models for EventBridge event buses,
rules, targets, archives, and connections.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from aws_comparator.models.common import AWSResource


class RuleState(str, Enum):
    """EventBridge rule state."""

    ENABLED = "ENABLED"
    DISABLED = "DISABLED"


class ConnectionState(str, Enum):
    """EventBridge connection state."""

    CREATING = "CREATING"
    UPDATING = "UPDATING"
    DELETING = "DELETING"
    AUTHORIZED = "AUTHORIZED"
    DEAUTHORIZED = "DEAUTHORIZED"
    AUTHORIZING = "AUTHORIZING"
    DEAUTHORIZING = "DEAUTHORIZING"


class AuthorizationType(str, Enum):
    """EventBridge connection authorization type."""

    BASIC = "BASIC"
    OAUTH_CLIENT_CREDENTIALS = "OAUTH_CLIENT_CREDENTIALS"
    API_KEY = "API_KEY"
    INVOCATION_HTTP_PARAMETERS = "INVOCATION_HTTP_PARAMETERS"


class ArchiveState(str, Enum):
    """EventBridge archive state."""

    ENABLED = "ENABLED"
    DISABLED = "DISABLED"
    CREATING = "CREATING"
    UPDATING = "UPDATING"


class InputTransformer(BaseModel):
    """EventBridge rule target input transformer."""

    model_config = ConfigDict(extra="ignore")

    input_paths_map: dict[str, str] = Field(
        default_factory=dict, description="Map of JSON path to variable name"
    )
    input_template: str = Field(..., description="Input template")


class Target(BaseModel):
    """
    EventBridge rule target.

    Represents a target for an EventBridge rule (Lambda, SQS, SNS, etc.).
    """

    model_config = ConfigDict(extra="ignore")

    id: str = Field(..., description="Target ID")
    arn: str = Field(..., description="Target ARN")
    role_arn: Optional[str] = Field(
        None, description="IAM role ARN for target invocation"
    )
    input: Optional[str] = Field(None, description="Static input to the target")
    input_path: Optional[str] = Field(
        None, description="JSONPath to select part of event"
    )
    input_transformer: Optional[InputTransformer] = Field(
        None, description="Input transformer configuration"
    )
    dead_letter_config: Optional[dict[str, Any]] = Field(
        None, description="Dead letter queue configuration"
    )
    retry_policy: Optional[dict[str, Any]] = Field(
        None, description="Retry policy configuration"
    )

    def __str__(self) -> str:
        """Return string representation of target."""
        return f"Target(id={self.id}, arn={self.arn})"


class EventBus(AWSResource):
    """
    EventBridge event bus.

    Represents an EventBridge event bus with its configuration.
    """

    model_config = ConfigDict(extra="ignore")

    name: str = Field(..., description="Event bus name")
    arn: str = Field(..., description="Event bus ARN")
    policy: Optional[dict[str, Any]] = Field(
        None, description="Event bus policy document"
    )
    description: Optional[str] = Field(None, description="Event bus description")
    creation_time: Optional[datetime] = Field(None, description="Creation timestamp")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """
        Validate event bus name.

        Args:
            v: Event bus name to validate

        Returns:
            Validated event bus name

        Raises:
            ValueError: If name is invalid
        """
        if not v:
            raise ValueError("Event bus name cannot be empty")
        if len(v) > 256:
            raise ValueError("Event bus name must be 256 characters or less")
        return v

    @classmethod
    def from_aws_response(cls, bus_data: dict[str, Any]) -> "EventBus":
        """
        Create EventBus instance from AWS API response.

        Args:
            bus_data: Event bus data from AWS API

        Returns:
            EventBus instance
        """
        bus_dict = {
            "name": bus_data.get("Name"),
            "arn": bus_data.get("Arn"),
            "policy": bus_data.get("Policy"),
            "description": bus_data.get("Description"),
            "creation_time": bus_data.get("CreationTime"),
        }

        return cls(**bus_dict)

    def __str__(self) -> str:
        """Return string representation of event bus."""
        return f"EventBus(name={self.name})"


class Rule(AWSResource):
    """
    EventBridge rule.

    Represents an EventBridge rule that routes events to targets.
    """

    model_config = ConfigDict(extra="ignore")

    name: str = Field(..., description="Rule name")
    arn: str = Field(..., description="Rule ARN")
    event_bus_name: str = Field(default="default", description="Event bus name")
    event_pattern: Optional[str] = Field(None, description="Event pattern JSON")
    schedule_expression: Optional[str] = Field(
        None, description="Schedule expression (cron or rate)"
    )
    state: RuleState = Field(default=RuleState.ENABLED, description="Rule state")
    description: Optional[str] = Field(None, description="Rule description")
    role_arn: Optional[str] = Field(None, description="IAM role ARN")
    managed_by: Optional[str] = Field(None, description="Managed by (AWS service)")
    targets: list[Target] = Field(default_factory=list, description="Rule targets")
    creation_time: Optional[datetime] = Field(None, description="Creation timestamp")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """
        Validate rule name.

        Args:
            v: Rule name to validate

        Returns:
            Validated rule name

        Raises:
            ValueError: If name is invalid
        """
        if not v:
            raise ValueError("Rule name cannot be empty")
        if len(v) > 64:
            raise ValueError("Rule name must be 64 characters or less")
        return v

    @classmethod
    def from_aws_response(
        cls, rule_data: dict[str, Any], targets: Optional[list[dict[str, Any]]] = None
    ) -> "Rule":
        """
        Create Rule instance from AWS API response.

        Args:
            rule_data: Rule data from AWS API
            targets: List of target data from AWS API

        Returns:
            Rule instance
        """
        rule_dict = {
            "name": rule_data.get("Name"),
            "arn": rule_data.get("Arn"),
            "event_bus_name": rule_data.get("EventBusName", "default"),
            "event_pattern": rule_data.get("EventPattern"),
            "schedule_expression": rule_data.get("ScheduleExpression"),
            "state": rule_data.get("State", "ENABLED"),
            "description": rule_data.get("Description"),
            "role_arn": rule_data.get("RoleArn"),
            "managed_by": rule_data.get("ManagedBy"),
            "creation_time": rule_data.get("CreationTime"),
        }

        # Process targets
        if targets:
            target_objects = []
            for target_data in targets:
                target_dict = {
                    "id": target_data.get("Id"),
                    "arn": target_data.get("Arn"),
                    "role_arn": target_data.get("RoleArn"),
                    "input": target_data.get("Input"),
                    "input_path": target_data.get("InputPath"),
                    "dead_letter_config": target_data.get("DeadLetterConfig"),
                    "retry_policy": target_data.get("RetryPolicy"),
                }

                # Process input transformer
                if "InputTransformer" in target_data:
                    transformer = target_data["InputTransformer"]
                    target_dict["input_transformer"] = {
                        "input_paths_map": transformer.get("InputPathsMap", {}),
                        "input_template": transformer.get("InputTemplate", ""),
                    }

                target_objects.append(Target(**target_dict))

            rule_dict["targets"] = target_objects

        return cls(**rule_dict)

    def __str__(self) -> str:
        """Return string representation of rule."""
        return f"Rule(name={self.name}, event_bus={self.event_bus_name}, state={self.state})"


class Archive(AWSResource):
    """
    EventBridge archive.

    Represents an EventBridge archive for event replay.
    """

    model_config = ConfigDict(extra="ignore")

    archive_name: str = Field(..., description="Archive name")
    event_source_arn: str = Field(..., description="Event bus ARN")
    description: Optional[str] = Field(None, description="Archive description")
    state: ArchiveState = Field(..., description="Archive state")
    retention_days: Optional[int] = Field(None, description="Event retention in days")
    size_bytes: Optional[int] = Field(None, description="Archive size in bytes")
    event_count: Optional[int] = Field(None, description="Number of events in archive")
    creation_time: Optional[datetime] = Field(None, description="Creation timestamp")

    @field_validator("archive_name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """
        Validate archive name.

        Args:
            v: Archive name to validate

        Returns:
            Validated archive name

        Raises:
            ValueError: If name is invalid
        """
        if not v:
            raise ValueError("Archive name cannot be empty")
        if len(v) > 48:
            raise ValueError("Archive name must be 48 characters or less")
        return v

    @classmethod
    def from_aws_response(cls, archive_data: dict[str, Any]) -> "Archive":
        """
        Create Archive instance from AWS API response.

        Args:
            archive_data: Archive data from AWS API

        Returns:
            Archive instance
        """
        archive_dict = {
            "archive_name": archive_data.get("ArchiveName"),
            "event_source_arn": archive_data.get("EventSourceArn"),
            "description": archive_data.get("Description"),
            "state": archive_data.get("State"),
            "retention_days": archive_data.get("RetentionDays"),
            "size_bytes": archive_data.get("SizeBytes"),
            "event_count": archive_data.get("EventCount"),
            "creation_time": archive_data.get("CreationTime"),
            "arn": archive_data.get("ArchiveArn"),
        }

        return cls(**archive_dict)

    def __str__(self) -> str:
        """Return string representation of archive."""
        return f"Archive(name={self.archive_name}, state={self.state})"


class Connection(AWSResource):
    """
    EventBridge connection.

    Represents an EventBridge connection for API destinations.
    """

    model_config = ConfigDict(extra="ignore")

    name: str = Field(..., description="Connection name")
    arn: str = Field(..., description="Connection ARN")
    connection_state: ConnectionState = Field(..., description="Connection state")
    authorization_type: AuthorizationType = Field(..., description="Authorization type")
    description: Optional[str] = Field(None, description="Connection description")
    creation_time: Optional[datetime] = Field(None, description="Creation timestamp")
    last_modified_time: Optional[datetime] = Field(
        None, description="Last modification timestamp"
    )
    last_authorized_time: Optional[datetime] = Field(
        None, description="Last authorization timestamp"
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """
        Validate connection name.

        Args:
            v: Connection name to validate

        Returns:
            Validated connection name

        Raises:
            ValueError: If name is invalid
        """
        if not v:
            raise ValueError("Connection name cannot be empty")
        if len(v) > 64:
            raise ValueError("Connection name must be 64 characters or less")
        return v

    @classmethod
    def from_aws_response(cls, connection_data: dict[str, Any]) -> "Connection":
        """
        Create Connection instance from AWS API response.

        Args:
            connection_data: Connection data from AWS API

        Returns:
            Connection instance
        """
        connection_dict = {
            "name": connection_data.get("Name"),
            "arn": connection_data.get("ConnectionArn"),
            "connection_state": connection_data.get("ConnectionState"),
            "authorization_type": connection_data.get("AuthorizationType"),
            "description": connection_data.get("Description"),
            "creation_time": connection_data.get("CreationTime"),
            "last_modified_time": connection_data.get("LastModifiedTime"),
            "last_authorized_time": connection_data.get("LastAuthorizedTime"),
        }

        return cls(**connection_dict)

    def __str__(self) -> str:
        """Return string representation of connection."""
        return f"Connection(name={self.name}, state={self.connection_state})"
