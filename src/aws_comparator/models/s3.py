"""
Pydantic models for AWS S3 service resources.

This module defines strongly-typed models for S3 buckets and related resources.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from aws_comparator.models.common import AWSResource


class BucketVersioningStatus(str, Enum):
    """S3 bucket versioning status."""

    ENABLED = "Enabled"
    SUSPENDED = "Suspended"
    DISABLED = "Disabled"


class BucketCannedACL(str, Enum):
    """S3 bucket canned ACLs."""

    PRIVATE = "private"
    PUBLIC_READ = "public-read"
    PUBLIC_READ_WRITE = "public-read-write"
    AUTHENTICATED_READ = "authenticated-read"


class ServerSideEncryptionAlgorithm(str, Enum):
    """S3 server-side encryption algorithms."""

    AES256 = "AES256"
    AWS_KMS = "aws:kms"


class PublicAccessBlockConfiguration(BaseModel):
    """S3 bucket public access block configuration."""

    model_config = ConfigDict(extra="ignore")

    block_public_acls: bool = Field(default=False, description="Block public ACLs")
    ignore_public_acls: bool = Field(default=False, description="Ignore public ACLs")
    block_public_policy: bool = Field(default=False, description="Block public policy")
    restrict_public_buckets: bool = Field(
        default=False, description="Restrict public buckets"
    )


class BucketEncryption(BaseModel):
    """S3 bucket encryption configuration."""

    model_config = ConfigDict(extra="ignore")

    sse_algorithm: ServerSideEncryptionAlgorithm = Field(
        ..., description="Server-side encryption algorithm"
    )
    kms_master_key_id: Optional[str] = Field(
        None, description="KMS key ID for encryption"
    )
    bucket_key_enabled: bool = Field(default=False, description="Bucket key enabled")


class LifecycleRule(BaseModel):
    """S3 bucket lifecycle rule."""

    model_config = ConfigDict(extra="ignore")

    id: Optional[str] = Field(None, description="Rule ID")
    status: str = Field(..., description="Rule status (Enabled/Disabled)")
    prefix: Optional[str] = Field(None, description="Object key prefix")
    expiration_days: Optional[int] = Field(None, description="Days until expiration")
    transition_days: Optional[int] = Field(None, description="Days until transition")
    transition_storage_class: Optional[str] = Field(
        None, description="Target storage class"
    )


class ReplicationRule(BaseModel):
    """S3 bucket replication rule."""

    model_config = ConfigDict(extra="ignore")

    id: Optional[str] = Field(None, description="Rule ID")
    status: str = Field(..., description="Rule status (Enabled/Disabled)")
    priority: Optional[int] = Field(None, description="Rule priority")
    destination_bucket: str = Field(..., description="Destination bucket ARN")
    destination_storage_class: Optional[str] = Field(
        None, description="Destination storage class"
    )


class S3Bucket(AWSResource):
    """
    S3 bucket resource model.

    Represents an AWS S3 bucket with all its configuration properties.
    """

    model_config = ConfigDict(extra="ignore")

    # Basic properties
    name: str = Field(..., description="Bucket name")
    creation_date: datetime = Field(..., description="Bucket creation date")

    # Location and ownership
    location: Optional[str] = Field(None, description="Bucket location constraint")
    owner_id: Optional[str] = Field(None, description="Bucket owner ID")
    owner_display_name: Optional[str] = Field(
        None, description="Bucket owner display name"
    )

    # Versioning
    versioning_status: BucketVersioningStatus = Field(
        default=BucketVersioningStatus.DISABLED, description="Versioning status"
    )
    mfa_delete: Optional[str] = Field(None, description="MFA delete status")

    # Encryption
    encryption: Optional[BucketEncryption] = Field(
        None, description="Encryption configuration"
    )

    # Public access
    public_access_block: Optional[PublicAccessBlockConfiguration] = Field(
        None, description="Public access block configuration"
    )

    # Logging
    logging_enabled: bool = Field(default=False, description="Access logging enabled")
    logging_target_bucket: Optional[str] = Field(
        None, description="Logging target bucket"
    )
    logging_target_prefix: Optional[str] = Field(
        None, description="Logging target prefix"
    )

    # Lifecycle
    lifecycle_rules: list[LifecycleRule] = Field(
        default_factory=list, description="Lifecycle rules"
    )

    # Replication
    replication_rules: list[ReplicationRule] = Field(
        default_factory=list, description="Replication rules"
    )

    # Website hosting
    website_enabled: bool = Field(
        default=False, description="Static website hosting enabled"
    )
    website_index_document: Optional[str] = Field(
        None, description="Website index document"
    )
    website_error_document: Optional[str] = Field(
        None, description="Website error document"
    )

    # Policies
    policy: Optional[dict[str, Any]] = Field(None, description="Bucket policy document")
    cors_rules: list[dict[str, Any]] = Field(
        default_factory=list, description="CORS configuration rules"
    )

    # Additional properties
    acl: Optional[str] = Field(None, description="Bucket ACL")
    object_lock_enabled: bool = Field(default=False, description="Object lock enabled")
    requester_pays: bool = Field(default=False, description="Requester pays enabled")

    @field_validator("name")
    @classmethod
    def validate_bucket_name(cls, v: str) -> str:
        """
        Validate S3 bucket name.

        Args:
            v: Bucket name to validate

        Returns:
            Validated bucket name

        Raises:
            ValueError: If bucket name is invalid
        """
        if not v:
            raise ValueError("Bucket name cannot be empty")
        if len(v) < 3 or len(v) > 63:
            raise ValueError("Bucket name must be between 3 and 63 characters")
        if not v[0].isalnum() or not v[-1].isalnum():
            raise ValueError("Bucket name must start and end with a letter or number")
        return v

    @classmethod
    def from_aws_response(
        cls,
        bucket_data: dict[str, Any],
        additional_data: Optional[dict[str, Any]] = None,
    ) -> "S3Bucket":
        """
        Create S3Bucket instance from AWS API response.

        Args:
            bucket_data: Bucket data from AWS API
            additional_data: Additional configuration data fetched separately

        Returns:
            S3Bucket instance
        """
        additional_data = additional_data or {}

        # Build the bucket model
        bucket_dict: dict[str, Any] = {
            "name": bucket_data.get("Name"),
            "creation_date": bucket_data.get("CreationDate"),
            "arn": f"arn:aws:s3:::{bucket_data.get('Name')}",
        }

        # Add location
        if "LocationConstraint" in additional_data:
            bucket_dict["location"] = additional_data["LocationConstraint"]

        # Add versioning
        if "Versioning" in additional_data:
            versioning = additional_data["Versioning"]
            status = versioning.get("Status", "Disabled")
            bucket_dict["versioning_status"] = status if status else "Disabled"
            bucket_dict["mfa_delete"] = versioning.get("MFADelete")

        # Add encryption
        if "Encryption" in additional_data:
            rules = additional_data["Encryption"].get("Rules", [])
            if rules:
                rule = rules[0]
                sse = rule.get("ApplyServerSideEncryptionByDefault", {})
                bucket_dict["encryption"] = {
                    "sse_algorithm": sse.get("SSEAlgorithm", "AES256"),
                    "kms_master_key_id": sse.get("KMSMasterKeyID"),
                    "bucket_key_enabled": rule.get("BucketKeyEnabled", False),
                }

        # Add public access block
        if "PublicAccessBlock" in additional_data:
            pab = additional_data["PublicAccessBlock"]
            bucket_dict["public_access_block"] = {
                "block_public_acls": pab.get("BlockPublicAcls", False),
                "ignore_public_acls": pab.get("IgnorePublicAcls", False),
                "block_public_policy": pab.get("BlockPublicPolicy", False),
                "restrict_public_buckets": pab.get("RestrictPublicBuckets", False),
            }

        # Add logging
        if "Logging" in additional_data:
            logging_config = additional_data["Logging"].get("LoggingEnabled", {})
            if logging_config:
                bucket_dict["logging_enabled"] = True
                bucket_dict["logging_target_bucket"] = logging_config.get(
                    "TargetBucket"
                )
                bucket_dict["logging_target_prefix"] = logging_config.get(
                    "TargetPrefix"
                )

        # Add lifecycle rules
        if "Lifecycle" in additional_data:
            rules = additional_data["Lifecycle"].get("Rules", [])
            bucket_dict["lifecycle_rules"] = [
                {
                    "id": rule.get("ID"),
                    "status": rule.get("Status"),
                    "prefix": rule.get("Prefix"),
                    "expiration_days": rule.get("Expiration", {}).get("Days"),
                    "transition_days": (
                        rule.get("Transitions", [{}])[0].get("Days")
                        if rule.get("Transitions")
                        else None
                    ),
                    "transition_storage_class": (
                        rule.get("Transitions", [{}])[0].get("StorageClass")
                        if rule.get("Transitions")
                        else None
                    ),
                }
                for rule in rules
            ]

        # Add replication rules
        if "Replication" in additional_data:
            rules = additional_data["Replication"].get("Rules", [])
            bucket_dict["replication_rules"] = [
                {
                    "id": rule.get("ID"),
                    "status": rule.get("Status"),
                    "priority": rule.get("Priority"),
                    "destination_bucket": rule.get("Destination", {}).get("Bucket"),
                    "destination_storage_class": rule.get("Destination", {}).get(
                        "StorageClass"
                    ),
                }
                for rule in rules
            ]

        # Add website configuration
        if "Website" in additional_data:
            website = additional_data["Website"]
            bucket_dict["website_enabled"] = True
            bucket_dict["website_index_document"] = website.get(
                "IndexDocument", {}
            ).get("Suffix")
            bucket_dict["website_error_document"] = website.get(
                "ErrorDocument", {}
            ).get("Key")

        # Add tags
        if "Tags" in additional_data:
            tags_list = additional_data["Tags"].get("TagSet", [])
            bucket_dict["tags"] = {tag["Key"]: tag["Value"] for tag in tags_list}

        # Add policy
        if "Policy" in additional_data:
            bucket_dict["policy"] = additional_data["Policy"]

        # Add CORS
        if "Cors" in additional_data:
            bucket_dict["cors_rules"] = additional_data["Cors"].get("CORSRules", [])

        # Add object lock
        if "ObjectLock" in additional_data:
            bucket_dict["object_lock_enabled"] = (
                additional_data["ObjectLock"].get("ObjectLockEnabled") == "Enabled"
            )

        # Add requester pays
        if "RequestPayment" in additional_data:
            bucket_dict["requester_pays"] = (
                additional_data["RequestPayment"].get("Payer") == "Requester"
            )

        return cls(**bucket_dict)

    def __str__(self) -> str:
        """Return string representation of S3 bucket."""
        return f"S3Bucket(name={self.name}, region={self.location or 'us-east-1'})"
