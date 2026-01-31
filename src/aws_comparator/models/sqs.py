"""
Pydantic models for AWS SQS service resources.

This module defines strongly-typed models for SQS queues and related resources.
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, field_validator, ConfigDict

from aws_comparator.models.common import AWSResource


class SQSQueue(AWSResource):
    """
    SQS queue resource model.

    Represents an AWS SQS queue with all its configuration properties.
    """
    model_config = ConfigDict(extra="ignore")

    # Basic properties
    queue_url: str = Field(..., description="Queue URL")
    queue_name: str = Field(..., description="Queue name")

    # Queue configuration
    delay_seconds: int = Field(default=0, ge=0, le=900, description="Delivery delay in seconds")
    maximum_message_size: int = Field(
        default=262144,
        ge=1024,
        le=262144,
        description="Maximum message size in bytes"
    )
    message_retention_period: int = Field(
        default=345600,
        ge=60,
        le=1209600,
        description="Message retention period in seconds"
    )
    receive_message_wait_time_seconds: int = Field(
        default=0,
        ge=0,
        le=20,
        description="Long polling wait time in seconds"
    )
    visibility_timeout: int = Field(
        default=30,
        ge=0,
        le=43200,
        description="Visibility timeout in seconds"
    )

    # Queue type and features
    fifo_queue: bool = Field(default=False, description="Whether this is a FIFO queue")
    content_based_deduplication: bool = Field(
        default=False,
        description="Content-based deduplication enabled"
    )

    # Dead letter queue
    redrive_policy: Optional[Dict[str, Any]] = Field(
        None,
        description="Dead letter queue redrive policy"
    )
    redrive_allow_policy: Optional[Dict[str, Any]] = Field(
        None,
        description="Dead letter queue redrive allow policy"
    )

    # Encryption
    kms_master_key_id: Optional[str] = Field(None, description="KMS key ID for encryption")
    kms_data_key_reuse_period_seconds: int = Field(
        default=300,
        description="KMS data key reuse period"
    )
    sqs_managed_sse_enabled: bool = Field(
        default=False,
        description="SQS-managed server-side encryption enabled"
    )

    # Metrics
    approximate_number_of_messages: int = Field(
        default=0,
        description="Approximate messages in queue"
    )
    approximate_number_of_messages_delayed: int = Field(
        default=0,
        description="Approximate delayed messages"
    )
    approximate_number_of_messages_not_visible: int = Field(
        default=0,
        description="Approximate messages not visible"
    )

    # Timestamps
    created_timestamp: Optional[int] = Field(None, description="Queue creation timestamp")
    last_modified_timestamp: Optional[int] = Field(None, description="Last modified timestamp")

    # Policy
    policy: Optional[Dict[str, Any]] = Field(None, description="Queue policy document")

    @field_validator('queue_name')
    @classmethod
    def validate_queue_name(cls, v: str) -> str:
        """
        Validate SQS queue name.

        Args:
            v: Queue name to validate

        Returns:
            Validated queue name

        Raises:
            ValueError: If queue name is invalid
        """
        if not v:
            raise ValueError("Queue name cannot be empty")
        if len(v) > 80:
            raise ValueError("Queue name cannot exceed 80 characters")
        return v

    @classmethod
    def from_aws_response(
        cls,
        queue_url: str,
        attributes: Dict[str, Any],
        tags: Optional[Dict[str, str]] = None
    ) -> "SQSQueue":
        """
        Create SQSQueue instance from AWS API response.

        Args:
            queue_url: Queue URL
            attributes: Queue attributes from AWS API
            tags: Queue tags

        Returns:
            SQSQueue instance
        """
        # Extract queue name from URL
        queue_name = queue_url.split('/')[-1]

        # Parse attributes
        queue_dict = {
            'queue_url': queue_url,
            'queue_name': queue_name,
            'arn': attributes.get('QueueArn'),
            'tags': tags or {},
        }

        # Numeric attributes
        if 'DelaySeconds' in attributes:
            queue_dict['delay_seconds'] = int(attributes['DelaySeconds'])
        if 'MaximumMessageSize' in attributes:
            queue_dict['maximum_message_size'] = int(attributes['MaximumMessageSize'])
        if 'MessageRetentionPeriod' in attributes:
            queue_dict['message_retention_period'] = int(attributes['MessageRetentionPeriod'])
        if 'ReceiveMessageWaitTimeSeconds' in attributes:
            queue_dict['receive_message_wait_time_seconds'] = int(attributes['ReceiveMessageWaitTimeSeconds'])
        if 'VisibilityTimeout' in attributes:
            queue_dict['visibility_timeout'] = int(attributes['VisibilityTimeout'])

        # Boolean attributes
        queue_dict['fifo_queue'] = attributes.get('FifoQueue') == 'true'
        queue_dict['content_based_deduplication'] = attributes.get('ContentBasedDeduplication') == 'true'
        queue_dict['sqs_managed_sse_enabled'] = attributes.get('SqsManagedSseEnabled') == 'true'

        # JSON attributes
        if 'RedrivePolicy' in attributes:
            import json
            queue_dict['redrive_policy'] = json.loads(attributes['RedrivePolicy'])
        if 'RedriveAllowPolicy' in attributes:
            import json
            queue_dict['redrive_allow_policy'] = json.loads(attributes['RedriveAllowPolicy'])
        if 'Policy' in attributes:
            import json
            queue_dict['policy'] = json.loads(attributes['Policy'])

        # Encryption
        if 'KmsMasterKeyId' in attributes:
            queue_dict['kms_master_key_id'] = attributes['KmsMasterKeyId']
        if 'KmsDataKeyReusePeriodSeconds' in attributes:
            queue_dict['kms_data_key_reuse_period_seconds'] = int(attributes['KmsDataKeyReusePeriodSeconds'])

        # Metrics
        if 'ApproximateNumberOfMessages' in attributes:
            queue_dict['approximate_number_of_messages'] = int(attributes['ApproximateNumberOfMessages'])
        if 'ApproximateNumberOfMessagesDelayed' in attributes:
            queue_dict['approximate_number_of_messages_delayed'] = int(attributes['ApproximateNumberOfMessagesDelayed'])
        if 'ApproximateNumberOfMessagesNotVisible' in attributes:
            queue_dict['approximate_number_of_messages_not_visible'] = int(attributes['ApproximateNumberOfMessagesNotVisible'])

        # Timestamps
        if 'CreatedTimestamp' in attributes:
            queue_dict['created_timestamp'] = int(attributes['CreatedTimestamp'])
        if 'LastModifiedTimestamp' in attributes:
            queue_dict['last_modified_timestamp'] = int(attributes['LastModifiedTimestamp'])

        return cls(**queue_dict)

    def __str__(self) -> str:
        """Return string representation of SQS queue."""
        queue_type = "FIFO" if self.fifo_queue else "Standard"
        return f"SQSQueue(name={self.queue_name}, type={queue_type})"
