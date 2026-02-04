"""
Common Pydantic models shared across all AWS services.

This module defines base models and common structures used throughout
the application for consistent data representation.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AWSRegion(str, Enum):
    """Supported AWS regions."""
    US_EAST_1 = "us-east-1"
    US_EAST_2 = "us-east-2"
    US_WEST_1 = "us-west-1"
    US_WEST_2 = "us-west-2"
    EU_WEST_1 = "eu-west-1"
    EU_WEST_2 = "eu-west-2"
    EU_WEST_3 = "eu-west-3"
    EU_CENTRAL_1 = "eu-central-1"
    EU_CENTRAL_2 = "eu-central-2"
    EU_NORTH_1 = "eu-north-1"
    EU_SOUTH_1 = "eu-south-1"
    AP_NORTHEAST_1 = "ap-northeast-1"
    AP_NORTHEAST_2 = "ap-northeast-2"
    AP_NORTHEAST_3 = "ap-northeast-3"
    AP_SOUTHEAST_1 = "ap-southeast-1"
    AP_SOUTHEAST_2 = "ap-southeast-2"
    AP_SOUTHEAST_3 = "ap-southeast-3"
    AP_SOUTH_1 = "ap-south-1"
    AP_EAST_1 = "ap-east-1"
    SA_EAST_1 = "sa-east-1"
    CA_CENTRAL_1 = "ca-central-1"
    AF_SOUTH_1 = "af-south-1"
    ME_SOUTH_1 = "me-south-1"


class AWSTag(BaseModel):
    """
    Standard AWS tag (Key-Value pair).

    AWS tags are used to organize and identify resources. They have specific
    naming restrictions that are validated here.
    """
    model_config = ConfigDict(extra="forbid")

    key: str = Field(..., min_length=1, max_length=128, description="Tag key")
    value: str = Field(..., max_length=256, description="Tag value")

    @field_validator('key')
    @classmethod
    def validate_key(cls, v: str) -> str:
        """
        Validate AWS tag key naming rules.

        Args:
            v: The tag key to validate

        Returns:
            The validated tag key

        Raises:
            ValueError: If key starts with 'aws:' (reserved prefix)
        """
        if v.lower().startswith('aws:'):
            raise ValueError("Tag keys cannot start with 'aws:' (reserved prefix)")
        return v

    def __str__(self) -> str:
        """Return string representation of tag."""
        return f"{self.key}={self.value}"

    def __repr__(self) -> str:
        """Return detailed representation for debugging."""
        return f"AWSTag(key={self.key!r}, value={self.value!r})"


class AWSResource(BaseModel):
    """
    Base model for all AWS resources.

    This class provides common fields and functionality that all AWS resources
    share, ensuring consistency across different resource types.

    Attributes:
        arn: Amazon Resource Name (unique identifier)
        tags: Resource tags as key-value pairs
        created_date: Resource creation timestamp
        region: AWS region where resource exists
    """
    model_config = ConfigDict(
        extra="ignore",  # Allow extra fields from AWS responses
        use_enum_values=True,
        json_encoders={datetime: lambda v: v.isoformat()},
    )

    arn: Optional[str] = Field(None, description="Amazon Resource Name")
    tags: dict[str, str] = Field(
        default_factory=dict,
        description="Resource tags as key-value pairs"
    )
    created_date: Optional[datetime] = Field(
        None,
        description="Resource creation timestamp"
    )
    region: Optional[str] = Field(None, description="AWS region")

    def normalize_tags(self, tag_list: list[dict[str, str]]) -> dict[str, str]:
        """
        Convert AWS tag list format to dictionary format.

        AWS APIs return tags in various formats. This method normalizes them
        to a consistent dictionary format for easier comparison.

        Args:
            tag_list: List of tag dictionaries from AWS API

        Returns:
            Dictionary mapping tag keys to values

        Example:
            >>> resource = AWSResource()
            >>> tags = [{'Key': 'Env', 'Value': 'prod'}]
            >>> resource.normalize_tags(tags)
            {'Env': 'prod'}
        """
        result: dict[str, str] = {}
        for tag in tag_list:
            # Handle both 'Key'/'Value' and 'key'/'value' formats
            key = tag.get('Key') or tag.get('key', '')
            value = tag.get('Value') or tag.get('value', '')
            if key:
                result[key] = value
        return result

    def __str__(self) -> str:
        """Return string representation of resource."""
        if self.arn:
            return f"{self.__class__.__name__}({self.arn})"
        return f"{self.__class__.__name__}(id={id(self)})"

    def __repr__(self) -> str:
        """Return detailed representation for debugging."""
        fields = []
        for field_name, field_value in self.model_dump().items():
            if field_value is not None and field_value != {} and field_value != []:
                if isinstance(field_value, str) and len(field_value) > 50:
                    field_value = field_value[:47] + "..."
                fields.append(f"{field_name}={field_value!r}")
        return f"{self.__class__.__name__}({', '.join(fields)})"


class ResourceIdentifier(BaseModel):
    """
    Unique identifier for any AWS resource.

    This model provides a standardized way to reference resources across
    different services and accounts.
    """
    model_config = ConfigDict(extra="forbid")

    service: str = Field(..., description="AWS service name (e.g., 'ec2')")
    resource_type: str = Field(..., description="Resource type (e.g., 'instance')")
    identifier: str = Field(..., description="Unique ID or ARN")
    account_id: str = Field(..., pattern=r'^\d{12}$', description="AWS account ID")
    region: str = Field(..., description="AWS region")

    @field_validator('account_id')
    @classmethod
    def validate_account_id(cls, v: str) -> str:
        """
        Validate AWS account ID format.

        Args:
            v: The account ID to validate

        Returns:
            The validated account ID

        Raises:
            ValueError: If account ID is not exactly 12 digits
        """
        if not v.isdigit() or len(v) != 12:
            raise ValueError("Account ID must be exactly 12 digits")
        return v

    def __str__(self) -> str:
        """Return string representation of resource identifier."""
        return f"{self.service}:{self.resource_type}:{self.identifier}"

    def __repr__(self) -> str:
        """Return detailed representation for debugging."""
        return (
            f"ResourceIdentifier("
            f"service={self.service!r}, "
            f"resource_type={self.resource_type!r}, "
            f"identifier={self.identifier!r}, "
            f"account_id={self.account_id!r}, "
            f"region={self.region!r})"
        )


class AccountInfo(BaseModel):
    """
    Information about an AWS account.

    This model stores metadata about AWS accounts being compared.
    """
    model_config = ConfigDict(extra="ignore")

    account_id: str = Field(..., pattern=r'^\d{12}$', description="AWS account ID")
    account_alias: Optional[str] = Field(None, description="Account alias")
    arn: Optional[str] = Field(None, description="IAM entity ARN")
    user_id: Optional[str] = Field(None, description="IAM user/role ID")

    @field_validator('account_id')
    @classmethod
    def validate_account_id(cls, v: str) -> str:
        """Validate AWS account ID format."""
        if not v.isdigit() or len(v) != 12:
            raise ValueError("Account ID must be exactly 12 digits")
        return v

    def __str__(self) -> str:
        """Return string representation of account info."""
        if self.account_alias:
            return f"{self.account_alias} ({self.account_id})"
        return self.account_id

    def __repr__(self) -> str:
        """Return detailed representation for debugging."""
        return (
            f"AccountInfo("
            f"account_id={self.account_id!r}, "
            f"account_alias={self.account_alias!r}, "
            f"arn={self.arn!r})"
        )


# Type aliases for better code readability
TagDict = dict[str, str]
MetadataDict = dict[str, Any]
