"""
Pydantic models for AWS Secrets Manager service resources.

This module defines strongly-typed models for Secrets Manager secret metadata.
SECURITY CRITICAL: This module NEVER includes secret values - only metadata.
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from aws_comparator.models.common import AWSResource


class RotationRules(BaseModel):
    """
    Secret rotation rules configuration.

    Defines how and when secrets should be rotated automatically.
    """

    model_config = ConfigDict(extra="ignore")

    automatically_after_days: Optional[int] = Field(
        None, ge=1, le=365, description="Number of days between automatic rotations"
    )
    duration: Optional[str] = Field(None, description="Duration of the rotation window")
    schedule_expression: Optional[str] = Field(
        None, description="Rotation schedule expression (cron or rate)"
    )


class SecretMetadata(AWSResource):
    """
    Secrets Manager secret metadata model.

    SECURITY CRITICAL: This model contains ONLY metadata about secrets.
    It NEVER contains actual secret values. All data comes from
    describe_secret() or list_secrets(), NEVER from get_secret_value().

    This is intentional by design to prevent accidental exposure of
    sensitive information during comparison operations.
    """

    model_config = ConfigDict(extra="ignore")

    # Basic properties
    name: str = Field(..., description="Secret name")
    arn: str = Field(..., description="Secret ARN")
    description: Optional[str] = Field(None, description="Secret description")

    # Encryption
    kms_key_id: Optional[str] = Field(
        None, description="KMS key ID used for encryption"
    )

    # Rotation configuration
    rotation_enabled: bool = Field(
        default=False, description="Whether automatic rotation is enabled"
    )
    rotation_lambda_arn: Optional[str] = Field(
        None, description="Lambda function ARN for rotation"
    )
    rotation_rules: Optional[RotationRules] = Field(
        None, description="Rotation schedule rules"
    )

    # Timestamps
    last_rotated_date: Optional[datetime] = Field(
        None, description="Last rotation timestamp"
    )
    last_changed_date: Optional[datetime] = Field(
        None, description="Last modification timestamp"
    )
    last_accessed_date: Optional[datetime] = Field(
        None, description="Last access timestamp (updated daily)"
    )
    deleted_date: Optional[datetime] = Field(
        None, description="Deletion timestamp (if scheduled for deletion)"
    )

    # Ownership
    owning_service: Optional[str] = Field(
        None, description="AWS service that owns this secret"
    )

    # Version information
    version_ids_to_stages: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Mapping of version IDs to their staging labels",
    )

    # Replication (multi-region secrets)
    replication_status: Optional[list[dict[str, Any]]] = Field(
        None, description="Replication status for multi-region secrets"
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """
        Validate secret name format.

        Args:
            v: Secret name to validate

        Returns:
            Validated secret name

        Raises:
            ValueError: If secret name is invalid
        """
        if not v:
            raise ValueError("Secret name cannot be empty")
        if len(v) > 256:
            raise ValueError("Secret name cannot exceed 256 characters")
        return v

    @classmethod
    def from_aws_response(
        cls, secret_data: dict[str, Any], tags: Optional[dict[str, str]] = None
    ) -> "SecretMetadata":
        """
        Create SecretMetadata instance from AWS API response.

        SECURITY NOTE: This method only accepts data from list_secrets()
        or describe_secret() responses. It will never process data from
        get_secret_value() responses.

        Args:
            secret_data: Secret metadata from AWS API (NOT secret values)
            tags: Secret tags as key-value pairs

        Returns:
            SecretMetadata instance

        Raises:
            ValueError: If secret_data contains 'SecretString' or 'SecretBinary'
                       (indicating someone tried to pass secret values)
        """
        # SECURITY CHECK: Ensure no secret values are in the data
        if "SecretString" in secret_data or "SecretBinary" in secret_data:
            raise ValueError(
                "SECURITY VIOLATION: Attempted to create SecretMetadata with "
                "actual secret values. Only metadata is allowed."
            )

        # Parse tags from AWS response if not provided directly
        if tags is None:
            tags_list = secret_data.get("Tags", [])
            tags = {tag["Key"]: tag["Value"] for tag in tags_list}

        secret_dict = {
            "name": secret_data.get("Name"),
            "arn": secret_data.get("ARN"),
            "description": secret_data.get("Description"),
            "kms_key_id": secret_data.get("KmsKeyId"),
            "rotation_enabled": secret_data.get("RotationEnabled", False),
            "rotation_lambda_arn": secret_data.get("RotationLambdaARN"),
            "owning_service": secret_data.get("OwningService"),
            "tags": tags,
        }

        # Rotation rules
        if "RotationRules" in secret_data and secret_data["RotationRules"]:
            rotation_rules = secret_data["RotationRules"]
            secret_dict["rotation_rules"] = {
                "automatically_after_days": rotation_rules.get(
                    "AutomaticallyAfterDays"
                ),
                "duration": rotation_rules.get("Duration"),
                "schedule_expression": rotation_rules.get("ScheduleExpression"),
            }

        # Timestamps
        if "LastRotatedDate" in secret_data:
            secret_dict["last_rotated_date"] = secret_data["LastRotatedDate"]
        if "LastChangedDate" in secret_data:
            secret_dict["last_changed_date"] = secret_data["LastChangedDate"]
        if "LastAccessedDate" in secret_data:
            secret_dict["last_accessed_date"] = secret_data["LastAccessedDate"]
        if "DeletedDate" in secret_data:
            secret_dict["deleted_date"] = secret_data["DeletedDate"]
        if "CreatedDate" in secret_data:
            secret_dict["created_date"] = secret_data["CreatedDate"]

        # Version IDs to stages
        if "VersionIdsToStages" in secret_data:
            secret_dict["version_ids_to_stages"] = secret_data["VersionIdsToStages"]

        # Replication status
        if "ReplicationStatus" in secret_data:
            secret_dict["replication_status"] = secret_data["ReplicationStatus"]

        return cls(**secret_dict)

    def __str__(self) -> str:
        """Return string representation of secret metadata."""
        rotation = "enabled" if self.rotation_enabled else "disabled"
        return f"SecretMetadata(name={self.name}, rotation={rotation})"
