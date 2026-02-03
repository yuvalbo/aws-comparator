"""
Pydantic models for AWS SNS service resources.

This module defines strongly-typed models for SNS topics and subscriptions.
"""

import json
from typing import Any, Optional

from pydantic import ConfigDict, Field, field_validator

from aws_comparator.models.common import AWSResource


class SNSTopic(AWSResource):
    """
    SNS topic resource model.

    Represents an AWS SNS topic with all its configuration properties.
    """
    model_config = ConfigDict(extra="ignore")

    # Basic properties
    topic_arn: str = Field(..., description="Topic ARN")
    topic_name: str = Field(..., description="Topic name (extracted from ARN)")

    # Topic configuration
    display_name: Optional[str] = Field(None, description="Display name for SMS")
    policy: Optional[dict[str, Any]] = Field(None, description="Topic access policy")
    delivery_policy: Optional[dict[str, Any]] = Field(
        None, description="HTTP/S delivery policy"
    )
    effective_delivery_policy: Optional[dict[str, Any]] = Field(
        None, description="Effective delivery policy"
    )

    # Encryption
    kms_master_key_id: Optional[str] = Field(
        None, description="KMS key ID for encryption"
    )

    # FIFO topic settings
    fifo_topic: bool = Field(default=False, description="Whether this is a FIFO topic")
    content_based_deduplication: bool = Field(
        default=False, description="Content-based deduplication enabled"
    )

    # Metrics
    subscriptions_confirmed: int = Field(
        default=0, description="Number of confirmed subscriptions"
    )
    subscriptions_pending: int = Field(
        default=0, description="Number of pending subscriptions"
    )
    subscriptions_deleted: int = Field(
        default=0, description="Number of deleted subscriptions"
    )

    @field_validator('topic_name')
    @classmethod
    def validate_topic_name(cls, v: str) -> str:
        """
        Validate SNS topic name.

        Args:
            v: Topic name to validate

        Returns:
            Validated topic name

        Raises:
            ValueError: If topic name is invalid
        """
        if not v:
            raise ValueError("Topic name cannot be empty")
        if len(v) > 256:
            raise ValueError("Topic name cannot exceed 256 characters")
        return v

    @classmethod
    def from_aws_response(
        cls,
        topic_arn: str,
        attributes: dict[str, Any],
        tags: Optional[dict[str, str]] = None
    ) -> "SNSTopic":
        """
        Create SNSTopic instance from AWS API response.

        Args:
            topic_arn: Topic ARN
            attributes: Topic attributes from AWS API
            tags: Topic tags

        Returns:
            SNSTopic instance
        """
        # Extract topic name from ARN
        topic_name = topic_arn.split(':')[-1]

        topic_dict: dict[str, Any] = {
            'topic_arn': topic_arn,
            'topic_name': topic_name,
            'arn': topic_arn,
            'tags': tags or {},
        }

        # String attributes
        if 'DisplayName' in attributes:
            topic_dict['display_name'] = attributes['DisplayName']

        # JSON attributes
        if 'Policy' in attributes:
            try:
                topic_dict['policy'] = json.loads(attributes['Policy'])
            except (json.JSONDecodeError, TypeError):
                topic_dict['policy'] = None

        if 'DeliveryPolicy' in attributes:
            try:
                topic_dict['delivery_policy'] = json.loads(attributes['DeliveryPolicy'])
            except (json.JSONDecodeError, TypeError):
                topic_dict['delivery_policy'] = None

        if 'EffectiveDeliveryPolicy' in attributes:
            try:
                topic_dict['effective_delivery_policy'] = json.loads(
                    attributes['EffectiveDeliveryPolicy']
                )
            except (json.JSONDecodeError, TypeError):
                topic_dict['effective_delivery_policy'] = None

        # Encryption
        if 'KmsMasterKeyId' in attributes:
            topic_dict['kms_master_key_id'] = attributes['KmsMasterKeyId']

        # FIFO settings
        topic_dict['fifo_topic'] = attributes.get('FifoTopic', 'false') == 'true'
        topic_dict['content_based_deduplication'] = (
            attributes.get('ContentBasedDeduplication', 'false') == 'true'
        )

        # Subscription counts
        if 'SubscriptionsConfirmed' in attributes:
            topic_dict['subscriptions_confirmed'] = int(
                attributes['SubscriptionsConfirmed']
            )
        if 'SubscriptionsPending' in attributes:
            topic_dict['subscriptions_pending'] = int(
                attributes['SubscriptionsPending']
            )
        if 'SubscriptionsDeleted' in attributes:
            topic_dict['subscriptions_deleted'] = int(
                attributes['SubscriptionsDeleted']
            )

        return cls(**topic_dict)

    def __str__(self) -> str:
        """Return string representation of SNS topic."""
        topic_type = "FIFO" if self.fifo_topic else "Standard"
        return f"SNSTopic(name={self.topic_name}, type={topic_type})"


class SNSSubscription(AWSResource):
    """
    SNS subscription resource model.

    Represents an AWS SNS subscription with all its configuration properties.
    """
    model_config = ConfigDict(extra="ignore")

    # Basic properties
    subscription_arn: str = Field(..., description="Subscription ARN")
    topic_arn: str = Field(..., description="Topic ARN this subscription belongs to")
    topic_name: str = Field(..., description="Topic name (extracted from ARN)")
    protocol: str = Field(..., description="Subscription protocol")
    endpoint: str = Field(..., description="Subscription endpoint")
    owner: Optional[str] = Field(None, description="Subscription owner account ID")

    # Subscription configuration
    confirmation_was_authenticated: bool = Field(
        default=False, description="Whether confirmation was authenticated"
    )
    pending_confirmation: bool = Field(
        default=False, description="Whether subscription is pending confirmation"
    )

    # Delivery settings
    delivery_policy: Optional[dict[str, Any]] = Field(
        None, description="Subscription delivery policy"
    )
    filter_policy: Optional[dict[str, Any]] = Field(
        None, description="Message filter policy"
    )
    filter_policy_scope: Optional[str] = Field(
        None, description="Filter policy scope (MessageAttributes or MessageBody)"
    )
    raw_message_delivery: bool = Field(
        default=False, description="Raw message delivery enabled"
    )
    redrive_policy: Optional[dict[str, Any]] = Field(
        None, description="Dead letter queue redrive policy"
    )

    @classmethod
    def from_aws_response(
        cls,
        subscription_data: dict[str, Any],
        attributes: Optional[dict[str, Any]] = None
    ) -> "SNSSubscription":
        """
        Create SNSSubscription instance from AWS API response.

        Args:
            subscription_data: Subscription data from list operation
            attributes: Detailed attributes from get operation

        Returns:
            SNSSubscription instance
        """
        subscription_arn = subscription_data.get('SubscriptionArn', '')
        topic_arn = subscription_data.get('TopicArn', '')
        topic_name = topic_arn.split(':')[-1] if topic_arn else ''

        subscription_dict: dict[str, Any] = {
            'subscription_arn': subscription_arn,
            'topic_arn': topic_arn,
            'topic_name': topic_name,
            'arn': subscription_arn,
            'protocol': subscription_data.get('Protocol', ''),
            'endpoint': subscription_data.get('Endpoint', ''),
            'owner': subscription_data.get('Owner'),
        }

        # Process detailed attributes if available
        if attributes:
            # Boolean attributes
            subscription_dict['confirmation_was_authenticated'] = (
                attributes.get('ConfirmationWasAuthenticated', 'false') == 'true'
            )
            subscription_dict['pending_confirmation'] = (
                attributes.get('PendingConfirmation', 'false') == 'true'
            )
            subscription_dict['raw_message_delivery'] = (
                attributes.get('RawMessageDelivery', 'false') == 'true'
            )

            # Filter policy scope
            if 'FilterPolicyScope' in attributes:
                subscription_dict['filter_policy_scope'] = attributes['FilterPolicyScope']

            # JSON attributes
            if 'DeliveryPolicy' in attributes:
                try:
                    subscription_dict['delivery_policy'] = json.loads(
                        attributes['DeliveryPolicy']
                    )
                except (json.JSONDecodeError, TypeError):
                    pass

            if 'FilterPolicy' in attributes:
                try:
                    subscription_dict['filter_policy'] = json.loads(
                        attributes['FilterPolicy']
                    )
                except (json.JSONDecodeError, TypeError):
                    pass

            if 'RedrivePolicy' in attributes:
                try:
                    subscription_dict['redrive_policy'] = json.loads(
                        attributes['RedrivePolicy']
                    )
                except (json.JSONDecodeError, TypeError):
                    pass

        return cls(**subscription_dict)

    def get_identifier(self) -> str:
        """
        Get a unique identifier for cross-account comparison.

        Uses topic_name + protocol + endpoint to match subscriptions
        across accounts.

        Returns:
            Unique identifier string
        """
        return f"{self.topic_name}:{self.protocol}:{self.endpoint}"

    def __str__(self) -> str:
        """Return string representation of SNS subscription."""
        return (
            f"SNSSubscription(topic={self.topic_name}, "
            f"protocol={self.protocol}, endpoint={self.endpoint})"
        )
