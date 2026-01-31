"""
AWS Service Quotas service fetcher.

This module implements fetching of service quotas for all services
being compared by the AWS Account Comparator.
"""

from typing import Any

from botocore.exceptions import ClientError

from aws_comparator.core.registry import ServiceRegistry
from aws_comparator.models.common import AWSResource
from aws_comparator.models.servicequotas import ServiceInfo, ServiceQuota
from aws_comparator.services.base import BaseServiceFetcher


@ServiceRegistry.register(
    'service-quotas',
    description='AWS Service Quotas',
    resource_types=['quotas']
)
class ServiceQuotasFetcher(BaseServiceFetcher):
    """
    Fetcher for AWS Service Quotas.

    This fetcher retrieves service quota information for all services
    being compared in the AWS Account Comparator, including:
    - Current quota values
    - Default quota values
    - Adjustability status
    - Usage metrics (if available)

    The fetcher queries quotas for these 11 services:
    - elasticbeanstalk (Elastic Beanstalk)
    - ec2 (EC2)
    - s3 (S3)
    - secretsmanager (Secrets Manager)
    - sqs (SQS)
    - logs (CloudWatch Logs)
    - monitoring (CloudWatch)
    - bedrock (Bedrock)
    - mobiletargeting (Pinpoint)
    - events (EventBridge)
    - lambda (Lambda)
    """

    SERVICE_NAME = "service-quotas"

    # Service codes for all services we're comparing
    TARGET_SERVICE_CODES = [
        'elasticbeanstalk',
        'ec2',
        's3',
        'secretsmanager',
        'sqs',
        'logs',           # CloudWatch Logs
        'monitoring',     # CloudWatch (note: not 'cloudwatch')
        'bedrock',
        'mobiletargeting',  # Pinpoint
        'events',         # EventBridge
        'lambda',
    ]

    def _create_client(self) -> Any:
        """
        Create boto3 Service Quotas client.

        Returns:
            Configured boto3 Service Quotas client
        """
        return self.session.client('service-quotas', region_name=self.region)

    def fetch_resources(self) -> dict[str, list[AWSResource]]:
        """
        Fetch all Service Quotas resources.

        Returns:
            Dictionary mapping resource types to lists of resources
        """
        return {
            'quotas': self._safe_fetch('quotas', self._fetch_quotas)
        }

    def get_resource_types(self) -> list[str]:
        """
        Get list of resource types handled by this fetcher.

        Returns:
            List of resource type names
        """
        return ['quotas']

    def _fetch_quotas(self) -> list[ServiceQuota]:
        """
        Fetch service quotas for all target services.

        Returns:
            List of ServiceQuota resources
        """
        quotas: list[ServiceQuota] = []

        self.logger.info(
            f"Fetching service quotas for {len(self.TARGET_SERVICE_CODES)} services"
        )

        for service_code in self.TARGET_SERVICE_CODES:
            try:
                service_quotas = self._fetch_quotas_for_service(service_code)
                quotas.extend(service_quotas)
                self.logger.debug(
                    f"Fetched {len(service_quotas)} quotas for service: {service_code}"
                )
            except ClientError as e:
                error_code = e.response.get('Error', {}).get('Code', '')
                if error_code in ['AccessDenied', 'NoSuchResourceException']:
                    self.logger.warning(
                        f"Cannot access quotas for service {service_code}: {error_code}"
                    )
                else:
                    self.logger.error(
                        f"Error fetching quotas for service {service_code}: {e}",
                        exc_info=True
                    )
            except Exception as e:
                self.logger.error(
                    f"Unexpected error fetching quotas for service {service_code}: {e}",
                    exc_info=True
                )

        self.logger.info(f"Fetched total of {len(quotas)} service quotas")
        return quotas

    def _fetch_quotas_for_service(self, service_code: str) -> list[ServiceQuota]:
        """
        Fetch quotas for a specific service.

        Args:
            service_code: Service code (e.g., 'lambda', 'ec2')

        Returns:
            List of ServiceQuota resources for the service
        """
        quotas: list[ServiceQuota] = []

        try:
            # Fetch current quotas
            current_quotas = self._paginate(
                'list_service_quotas',
                'Quotas',
                ServiceCode=service_code
            )

            # Fetch default quotas for comparison
            default_quotas_map = self._fetch_default_quotas(service_code)

            # Process each quota
            for quota_data in current_quotas:
                try:
                    quota_code = quota_data['QuotaCode']
                    default_value = default_quotas_map.get(quota_code)

                    # Create ServiceQuota instance
                    quota = ServiceQuota.from_aws_response(
                        quota_data,
                        default_value=default_value
                    )
                    quotas.append(quota)

                except Exception as e:
                    quota_name = quota_data.get('QuotaName', 'unknown')
                    self.logger.warning(
                        f"Failed to parse quota {quota_name} for {service_code}: {e}"
                    )

        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code == 'NoSuchResourceException':
                # Service may not have any quotas in Service Quotas API
                self.logger.debug(
                    f"Service {service_code} has no quotas in Service Quotas API"
                )
            else:
                raise

        return quotas

    def _fetch_default_quotas(self, service_code: str) -> dict[str, float]:
        """
        Fetch default quota values for a service.

        Args:
            service_code: Service code

        Returns:
            Dictionary mapping quota codes to default values
        """
        default_quotas: dict[str, float] = {}

        try:
            # Use paginate to get all default quotas
            default_quota_list = self._paginate(
                'list_aws_default_service_quotas',
                'Quotas',
                ServiceCode=service_code
            )

            for quota_data in default_quota_list:
                quota_code = quota_data['QuotaCode']
                default_value = float(quota_data['Value'])
                default_quotas[quota_code] = default_value

        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code != 'NoSuchResourceException':
                self.logger.warning(
                    f"Failed to fetch default quotas for {service_code}: {error_code}"
                )

        return default_quotas

    def list_available_services(self) -> list[ServiceInfo]:
        """
        List all services available in Service Quotas API.

        This is a utility method that can be used to discover which services
        are available in the Service Quotas API for the current region.

        Returns:
            List of ServiceInfo resources
        """
        services: list[ServiceInfo] = []

        try:
            # Fetch all services
            service_list = self._paginate('list_services', 'Services')

            for service_data in service_list:
                service = ServiceInfo.from_aws_response(service_data)
                services.append(service)

            self.logger.info(
                f"Found {len(services)} services in Service Quotas API"
            )

        except Exception as e:
            self.logger.error(
                f"Failed to list services: {e}",
                exc_info=True
            )

        return services

    def get_quota_by_code(
        self,
        service_code: str,
        quota_code: str
    ) -> ServiceQuota | None:
        """
        Get a specific quota by service and quota code.

        Args:
            service_code: Service code (e.g., 'lambda')
            quota_code: Quota code (e.g., 'L-B99A9384')

        Returns:
            ServiceQuota instance, or None if not found
        """
        try:
            response = self.client.get_service_quota(
                ServiceCode=service_code,
                QuotaCode=quota_code
            )

            quota_data = response.get('Quota')
            if quota_data:
                # Also fetch default value
                try:
                    default_response = self.client.get_aws_default_service_quota(
                        ServiceCode=service_code,
                        QuotaCode=quota_code
                    )
                    default_value = float(default_response['Quota']['Value'])
                except ClientError:
                    default_value = None

                return ServiceQuota.from_aws_response(
                    quota_data,
                    default_value=default_value
                )

        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code not in ['NoSuchResourceException', 'ResourceNotFoundException']:
                self.logger.error(
                    f"Error fetching quota {quota_code} for {service_code}: {e}"
                )

        return None
