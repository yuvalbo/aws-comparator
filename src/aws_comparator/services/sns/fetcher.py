"""
AWS SNS service fetcher.

This module implements fetching of SNS topic and subscription resources.
"""

from typing import Any

from botocore.exceptions import ClientError  # type: ignore[import-untyped]

from aws_comparator.core.registry import ServiceRegistry
from aws_comparator.models.common import AWSResource
from aws_comparator.models.sns import SNSSubscription, SNSTopic
from aws_comparator.services.base import BaseServiceFetcher


@ServiceRegistry.register(
    "sns",
    description="Amazon SNS (Simple Notification Service)",
    resource_types=["topics", "subscriptions"],
)
class SNSFetcher(BaseServiceFetcher):
    """
    Fetcher for AWS SNS resources.

    This fetcher retrieves SNS information including:
    - Topics and their attributes
    - Subscriptions and their configurations
    - Delivery policies and filter policies
    - Encryption settings
    """

    SERVICE_NAME = "sns"

    def _create_client(self) -> Any:
        """
        Create boto3 SNS client.

        Returns:
            Configured boto3 SNS client
        """
        return self.session.client("sns", region_name=self.region)

    def fetch_resources(self) -> dict[str, list[AWSResource]]:
        """
        Fetch all SNS resources.

        Returns:
            Dictionary mapping resource types to lists of resources
        """
        return {
            "topics": self._safe_fetch("topics", self._fetch_topics),
            "subscriptions": self._safe_fetch(
                "subscriptions", self._fetch_subscriptions
            ),
        }

    def get_resource_types(self) -> list[str]:
        """
        Get list of resource types handled by this fetcher.

        Returns:
            List of resource type names
        """
        return ["topics", "subscriptions"]

    def _fetch_topics(self) -> list[SNSTopic]:
        """
        Fetch all SNS topics and their configurations.

        Returns:
            List of SNSTopic resources
        """
        topics: list[SNSTopic] = []

        if not self.client:
            self.logger.error("SNS client not initialized")
            return topics

        try:
            # List all topics using pagination
            topic_arns: list[str] = []
            paginator = self.client.get_paginator("list_topics")

            for page in paginator.paginate():
                for topic in page.get("Topics", []):
                    topic_arns.append(topic["TopicArn"])

            self.logger.info(f"Found {len(topic_arns)} SNS topics")

            for topic_arn in topic_arns:
                try:
                    # Get topic attributes
                    attr_response = self.client.get_topic_attributes(TopicArn=topic_arn)
                    attributes = attr_response.get("Attributes", {})

                    # Get topic tags
                    tags: dict[str, str] = {}
                    try:
                        tag_response = self.client.list_tags_for_resource(
                            ResourceArn=topic_arn
                        )
                        tags = {
                            tag["Key"]: tag["Value"]
                            for tag in tag_response.get("Tags", [])
                        }
                    except ClientError:
                        # Tags may not be accessible
                        pass

                    # Create SNSTopic instance
                    topic = SNSTopic.from_aws_response(topic_arn, attributes, tags)
                    topics.append(topic)

                    topic_name = topic_arn.split(":")[-1]
                    self.logger.debug(f"Fetched topic: {topic_name}")

                except ClientError as e:
                    error_code = e.response.get("Error", {}).get("Code", "")
                    topic_name = topic_arn.split(":")[-1]
                    if error_code in ["AccessDenied", "NotFound"]:
                        self.logger.warning(
                            f"Cannot access topic {topic_name}: {error_code}"
                        )
                    else:
                        self.logger.error(
                            f"Error fetching topic {topic_name}: {e}", exc_info=True
                        )

        except Exception as e:
            self.logger.error(f"Failed to list SNS topics: {e}", exc_info=True)

        return topics

    def _fetch_subscriptions(self) -> list[SNSSubscription]:
        """
        Fetch all SNS subscriptions and their configurations.

        Returns:
            List of SNSSubscription resources
        """
        subscriptions: list[SNSSubscription] = []

        if not self.client:
            self.logger.error("SNS client not initialized")
            return subscriptions

        try:
            # List all subscriptions using pagination
            subscription_list: list[dict[str, Any]] = []
            paginator = self.client.get_paginator("list_subscriptions")

            for page in paginator.paginate():
                subscription_list.extend(page.get("Subscriptions", []))

            self.logger.info(f"Found {len(subscription_list)} SNS subscriptions")

            for sub_data in subscription_list:
                subscription_arn = sub_data.get("SubscriptionArn", "")

                # Skip pending confirmations (they don't have full ARNs)
                if subscription_arn == "PendingConfirmation":
                    continue

                try:
                    # Get subscription attributes
                    attributes: dict[str, Any] = {}
                    try:
                        attr_response = self.client.get_subscription_attributes(
                            SubscriptionArn=subscription_arn
                        )
                        attributes = attr_response.get("Attributes", {})
                    except ClientError:
                        # Attributes may not be accessible
                        pass

                    # Create SNSSubscription instance
                    subscription = SNSSubscription.from_aws_response(
                        sub_data, attributes
                    )
                    subscriptions.append(subscription)

                    self.logger.debug(
                        f"Fetched subscription: {subscription.protocol}:{subscription.endpoint}"
                    )

                except ClientError as e:
                    error_code = e.response.get("Error", {}).get("Code", "")
                    if error_code in ["AccessDenied", "NotFound"]:
                        self.logger.warning(
                            f"Cannot access subscription {subscription_arn}: {error_code}"
                        )
                    else:
                        self.logger.error(
                            f"Error fetching subscription {subscription_arn}: {e}",
                            exc_info=True,
                        )

        except Exception as e:
            self.logger.error(f"Failed to list SNS subscriptions: {e}", exc_info=True)

        return subscriptions
