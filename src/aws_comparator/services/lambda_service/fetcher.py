"""
AWS Lambda service fetcher.

This module implements fetching of Lambda function and layer resources.
"""

from typing import Any

from botocore.exceptions import ClientError

from aws_comparator.core.registry import ServiceRegistry
from aws_comparator.models.common import AWSResource
from aws_comparator.models.lambda_svc import LambdaFunction, LambdaLayer
from aws_comparator.services.base import BaseServiceFetcher


@ServiceRegistry.register(
    'lambda',
    description='AWS Lambda',
    resource_types=['functions', 'layers']
)
class LambdaFetcher(BaseServiceFetcher):
    """
    Fetcher for AWS Lambda resources.

    This fetcher retrieves Lambda information including:
    - Functions (code, configuration, environment variables)
    - Layers (versions, compatible runtimes)
    - VPC configurations
    - Dead letter queues
    - Tracing configuration
    """

    SERVICE_NAME = "lambda"

    def _create_client(self) -> Any:
        """
        Create boto3 Lambda client.

        Returns:
            Configured boto3 Lambda client
        """
        return self.session.client('lambda', region_name=self.region)

    def fetch_resources(self) -> dict[str, list[AWSResource]]:
        """
        Fetch all Lambda resources.

        Returns:
            Dictionary mapping resource types to lists of resources
        """
        return {
            'functions': self._safe_fetch('functions', self._fetch_functions),
            'layers': self._safe_fetch('layers', self._fetch_layers)
        }

    def get_resource_types(self) -> list[str]:
        """
        Get list of resource types handled by this fetcher.

        Returns:
            List of resource type names
        """
        return ['functions', 'layers']

    def _fetch_functions(self) -> list[LambdaFunction]:
        """
        Fetch all Lambda functions and their configurations.

        Returns:
            List of LambdaFunction resources
        """
        functions: list[LambdaFunction] = []

        if self.client is None:
            return functions

        try:
            # Use pagination to list all functions
            results = self._paginate('list_functions', 'Functions')

            self.logger.info(f"Found {len(results)} Lambda functions")

            for function_data in results:
                try:
                    function_name = function_data['FunctionName']

                    # Get function tags
                    tags: dict[str, str] = {}
                    try:
                        tag_response = self.client.list_tags(
                            Resource=function_data['FunctionArn']
                        )
                        tags = tag_response.get('Tags', {})
                    except ClientError:
                        # Tags may not be accessible
                        pass

                    # Get concurrency configuration
                    try:
                        concurrency = self.client.get_function_concurrency(
                            FunctionName=function_name
                        )
                        if 'ReservedConcurrentExecutions' in concurrency:
                            function_data['ReservedConcurrentExecutions'] = \
                                concurrency['ReservedConcurrentExecutions']
                    except ClientError:
                        # Concurrency may not be configured
                        pass

                    # Create LambdaFunction instance
                    function = LambdaFunction.from_aws_response(function_data, tags)
                    functions.append(function)

                    self.logger.debug(f"Fetched function: {function_name}")

                except ClientError as e:
                    error_code = e.response.get('Error', {}).get('Code', '')
                    function_name = function_data.get('FunctionName', 'unknown')
                    if error_code in ['AccessDenied', 'ResourceNotFoundException']:
                        self.logger.warning(
                            f"Cannot access function {function_name}: {error_code}"
                        )
                    else:
                        self.logger.error(
                            f"Error fetching function {function_name}: {e}",
                            exc_info=True
                        )

        except Exception as e:
            self.logger.error(
                f"Failed to list Lambda functions: {e}", exc_info=True
            )

        return functions

    def _fetch_layers(self) -> list[LambdaLayer]:
        """
        Fetch all Lambda layers and their versions.

        Returns:
            List of LambdaLayer resources
        """
        layers: list[LambdaLayer] = []

        try:
            # List all layers
            results = self._paginate('list_layers', 'Layers')

            self.logger.info(f"Found {len(results)} Lambda layers")

            for layer_data in results:
                try:
                    layer_name = layer_data['LayerName']

                    # Get latest version details
                    if 'LatestMatchingVersion' in layer_data:
                        version_data = layer_data['LatestMatchingVersion']

                        # Create LambdaLayer instance
                        layer = LambdaLayer.from_aws_response({
                            'LayerName': layer_name,
                            'LayerArn': layer_data['LayerArn'],
                            **version_data
                        })
                        layers.append(layer)

                        self.logger.debug(f"Fetched layer: {layer_name}")

                except ClientError as e:
                    error_code = e.response.get('Error', {}).get('Code', '')
                    layer_name = layer_data.get('LayerName', 'unknown')
                    if error_code in ['AccessDenied', 'ResourceNotFoundException']:
                        self.logger.warning(
                            f"Cannot access layer {layer_name}: {error_code}"
                        )
                    else:
                        self.logger.error(
                            f"Error fetching layer {layer_name}: {e}",
                            exc_info=True
                        )

        except Exception as e:
            self.logger.error(
                f"Failed to list Lambda layers: {e}", exc_info=True
            )

        return layers
