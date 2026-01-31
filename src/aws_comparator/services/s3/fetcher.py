"""
AWS S3 service fetcher.

This module implements fetching of S3 bucket resources and their configurations.
"""

import json
from typing import Any, Dict, List, Optional
from botocore.exceptions import ClientError

from aws_comparator.services.base import BaseServiceFetcher
from aws_comparator.models.common import AWSResource
from aws_comparator.models.s3 import S3Bucket
from aws_comparator.core.registry import ServiceRegistry


@ServiceRegistry.register(
    's3',
    description='Amazon S3 (Simple Storage Service)',
    resource_types=['buckets']
)
class S3Fetcher(BaseServiceFetcher):
    """
    Fetcher for AWS S3 resources.

    This fetcher retrieves S3 bucket information including:
    - Bucket properties (location, creation date, etc.)
    - Versioning configuration
    - Encryption settings
    - Public access block configuration
    - Logging configuration
    - Lifecycle rules
    - Replication configuration
    - Website hosting configuration
    - Bucket policies and CORS rules
    """

    SERVICE_NAME = "s3"

    def _create_client(self) -> Any:
        """
        Create boto3 S3 client.

        Returns:
            Configured boto3 S3 client
        """
        return self.session.client('s3', region_name=self.region)

    def fetch_resources(self) -> Dict[str, List[AWSResource]]:
        """
        Fetch all S3 resources.

        Returns:
            Dictionary mapping resource types to lists of resources
        """
        return {
            'buckets': self._safe_fetch('buckets', self._fetch_buckets)
        }

    def get_resource_types(self) -> List[str]:
        """
        Get list of resource types handled by this fetcher.

        Returns:
            List of resource type names
        """
        return ['buckets']

    def _fetch_buckets(self) -> List[S3Bucket]:
        """
        Fetch all S3 buckets and their configurations.

        Returns:
            List of S3Bucket resources
        """
        buckets: List[S3Bucket] = []

        # List all buckets
        try:
            response = self.client.list_buckets()
            bucket_list = response.get('Buckets', [])

            self.logger.info(f"Found {len(bucket_list)} S3 buckets")

            for bucket_data in bucket_list:
                bucket_name = bucket_data['Name']

                try:
                    # Fetch additional bucket configuration
                    additional_data = self._fetch_bucket_details(bucket_name)

                    # Create S3Bucket instance
                    bucket = S3Bucket.from_aws_response(bucket_data, additional_data)
                    buckets.append(bucket)

                    self.logger.debug(f"Fetched bucket: {bucket_name}")

                except ClientError as e:
                    error_code = e.response.get('Error', {}).get('Code', '')
                    if error_code in ['AccessDenied', 'NoSuchBucket']:
                        self.logger.warning(
                            f"Cannot access bucket {bucket_name}: {error_code}"
                        )
                    else:
                        self.logger.error(
                            f"Error fetching bucket {bucket_name}: {e}",
                            exc_info=True
                        )

        except Exception as e:
            self.logger.error(f"Failed to list S3 buckets: {e}", exc_info=True)

        return buckets

    def _fetch_bucket_details(self, bucket_name: str) -> Dict[str, Any]:
        """
        Fetch detailed configuration for a specific bucket.

        Args:
            bucket_name: Name of the bucket

        Returns:
            Dictionary containing all bucket configuration data
        """
        details: Dict[str, Any] = {}

        # Fetch location
        try:
            location = self.client.get_bucket_location(Bucket=bucket_name)
            details['LocationConstraint'] = location.get('LocationConstraint') or 'us-east-1'
        except ClientError:
            pass

        # Fetch versioning
        try:
            versioning = self.client.get_bucket_versioning(Bucket=bucket_name)
            details['Versioning'] = versioning
        except ClientError:
            pass

        # Fetch encryption
        try:
            encryption = self.client.get_bucket_encryption(Bucket=bucket_name)
            details['Encryption'] = encryption.get('ServerSideEncryptionConfiguration', {})
        except ClientError as e:
            # Encryption may not be configured
            if e.response.get('Error', {}).get('Code') != 'ServerSideEncryptionConfigurationNotFoundError':
                self.logger.debug(f"No encryption configured for {bucket_name}")

        # Fetch public access block
        try:
            public_access = self.client.get_public_access_block(Bucket=bucket_name)
            details['PublicAccessBlock'] = public_access.get('PublicAccessBlockConfiguration', {})
        except ClientError:
            pass

        # Fetch logging
        try:
            logging = self.client.get_bucket_logging(Bucket=bucket_name)
            details['Logging'] = logging
        except ClientError:
            pass

        # Fetch lifecycle configuration
        try:
            lifecycle = self.client.get_bucket_lifecycle_configuration(Bucket=bucket_name)
            details['Lifecycle'] = lifecycle
        except ClientError as e:
            # Lifecycle may not be configured
            if e.response.get('Error', {}).get('Code') != 'NoSuchLifecycleConfiguration':
                self.logger.debug(f"No lifecycle configured for {bucket_name}")

        # Fetch replication
        try:
            replication = self.client.get_bucket_replication(Bucket=bucket_name)
            details['Replication'] = replication.get('ReplicationConfiguration', {})
        except ClientError as e:
            # Replication may not be configured
            if e.response.get('Error', {}).get('Code') != 'ReplicationConfigurationNotFoundError':
                self.logger.debug(f"No replication configured for {bucket_name}")

        # Fetch website configuration
        try:
            website = self.client.get_bucket_website(Bucket=bucket_name)
            details['Website'] = website
        except ClientError as e:
            # Website may not be configured
            if e.response.get('Error', {}).get('Code') != 'NoSuchWebsiteConfiguration':
                self.logger.debug(f"No website configured for {bucket_name}")

        # Fetch tags
        try:
            tags = self.client.get_bucket_tagging(Bucket=bucket_name)
            details['Tags'] = tags
        except ClientError as e:
            # Tags may not be configured
            if e.response.get('Error', {}).get('Code') != 'NoSuchTagSet':
                self.logger.debug(f"No tags for {bucket_name}")

        # Fetch bucket policy
        try:
            policy = self.client.get_bucket_policy(Bucket=bucket_name)
            policy_text = policy.get('Policy', '{}')
            details['Policy'] = json.loads(policy_text) if isinstance(policy_text, str) else policy_text
        except ClientError as e:
            # Policy may not exist
            if e.response.get('Error', {}).get('Code') != 'NoSuchBucketPolicy':
                self.logger.debug(f"No policy for {bucket_name}")

        # Fetch CORS
        try:
            cors = self.client.get_bucket_cors(Bucket=bucket_name)
            details['Cors'] = cors
        except ClientError as e:
            # CORS may not be configured
            if e.response.get('Error', {}).get('Code') != 'NoSuchCORSConfiguration':
                self.logger.debug(f"No CORS configured for {bucket_name}")

        # Fetch object lock
        try:
            object_lock = self.client.get_object_lock_configuration(Bucket=bucket_name)
            details['ObjectLock'] = object_lock.get('ObjectLockConfiguration', {})
        except ClientError as e:
            # Object lock may not be configured
            if e.response.get('Error', {}).get('Code') != 'ObjectLockConfigurationNotFoundError':
                self.logger.debug(f"No object lock for {bucket_name}")

        # Fetch request payment
        try:
            request_payment = self.client.get_bucket_request_payment(Bucket=bucket_name)
            details['RequestPayment'] = request_payment
        except ClientError:
            pass

        return details
