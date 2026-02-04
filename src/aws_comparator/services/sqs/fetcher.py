"""
AWS SQS service fetcher.

This module implements fetching of SQS queue resources and their configurations.
"""

from typing import Any

from botocore.exceptions import ClientError

from aws_comparator.core.registry import ServiceRegistry
from aws_comparator.models.common import AWSResource
from aws_comparator.models.sqs import SQSQueue
from aws_comparator.services.base import BaseServiceFetcher


@ServiceRegistry.register(
    'sqs',
    description='Amazon SQS (Simple Queue Service)',
    resource_types=['queues']
)
class SQSFetcher(BaseServiceFetcher):
    """
    Fetcher for AWS SQS resources.

    This fetcher retrieves SQS queue information including:
    - Queue configuration (delays, timeouts, message sizes)
    - Dead letter queue configuration
    - Encryption settings
    - Queue metrics
    """

    SERVICE_NAME = "sqs"

    def _create_client(self) -> Any:
        """
        Create boto3 SQS client.

        Returns:
            Configured boto3 SQS client
        """
        return self.session.client('sqs', region_name=self.region)

    def fetch_resources(self) -> dict[str, list[AWSResource]]:
        """
        Fetch all SQS resources.

        Returns:
            Dictionary mapping resource types to lists of resources
        """
        return {
            'queues': self._safe_fetch('queues', self._fetch_queues)
        }

    def get_resource_types(self) -> list[str]:
        """
        Get list of resource types handled by this fetcher.

        Returns:
            List of resource type names
        """
        return ['queues']

    def _fetch_queues(self) -> list[SQSQueue]:
        """
        Fetch all SQS queues and their configurations.

        Returns:
            List of SQSQueue resources
        """
        queues: list[SQSQueue] = []

        if self.client is None:
            return queues

        try:
            # List all queue URLs
            response = self.client.list_queues()
            queue_urls = response.get('QueueUrls', [])

            self.logger.info(f"Found {len(queue_urls)} SQS queues")

            for queue_url in queue_urls:
                try:
                    # Get queue attributes
                    attr_response = self.client.get_queue_attributes(
                        QueueUrl=queue_url,
                        AttributeNames=['All']
                    )
                    attributes = attr_response.get('Attributes', {})

                    # Get queue tags
                    tags: dict[str, str] = {}
                    try:
                        tag_response = self.client.list_queue_tags(QueueUrl=queue_url)
                        tags = tag_response.get('Tags', {})
                    except ClientError:
                        # Tags may not be accessible
                        pass

                    # Create SQSQueue instance
                    queue = SQSQueue.from_aws_response(queue_url, attributes, tags)
                    queues.append(queue)

                    queue_name = queue_url.split('/')[-1]
                    self.logger.debug(f"Fetched queue: {queue_name}")

                except ClientError as e:
                    error_code = e.response.get('Error', {}).get('Code', '')
                    queue_name = queue_url.split('/')[-1]
                    if error_code in [
                        'AccessDenied',
                        'AWS.SimpleQueueService.NonExistentQueue'
                    ]:
                        self.logger.warning(
                            f"Cannot access queue {queue_name}: {error_code}"
                        )
                    else:
                        self.logger.error(
                            f"Error fetching queue {queue_name}: {e}",
                            exc_info=True
                        )

        except Exception as e:
            self.logger.error(f"Failed to list SQS queues: {e}", exc_info=True)

        return queues
