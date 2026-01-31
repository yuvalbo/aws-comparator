"""
Unit tests for AWS Service Quotas fetcher.

This module tests the ServiceQuotasFetcher class using moto for AWS mocking.
"""

from unittest.mock import MagicMock, Mock, patch

import boto3
import pytest
from botocore.exceptions import ClientError
from moto import mock_aws

from aws_comparator.models.servicequotas import ServiceInfo, ServiceQuota
from aws_comparator.services.servicequotas.fetcher import ServiceQuotasFetcher


@pytest.fixture
def aws_credentials():
    """Mock AWS credentials for moto."""
    import os
    os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
    os.environ['AWS_SECURITY_TOKEN'] = 'testing'
    os.environ['AWS_SESSION_TOKEN'] = 'testing'


@pytest.fixture
def mock_session(aws_credentials):
    """Create a mock boto3 session."""
    with mock_aws():
        session = boto3.Session(region_name='us-east-1')
        yield session


@pytest.fixture
def fetcher(mock_session):
    """Create ServiceQuotasFetcher instance."""
    return ServiceQuotasFetcher(mock_session, 'us-east-1')


class TestServiceQuotasFetcher:
    """Test suite for ServiceQuotasFetcher."""

    def test_initialization(self, fetcher):
        """Test fetcher initialization."""
        assert fetcher.SERVICE_NAME == 'service-quotas'
        assert fetcher.region == 'us-east-1'
        assert fetcher.client is not None
        assert len(fetcher.TARGET_SERVICE_CODES) == 11

    def test_target_service_codes(self, fetcher):
        """Test that all required service codes are present."""
        expected_services = [
            'elasticbeanstalk',
            'ec2',
            's3',
            'secretsmanager',
            'sqs',
            'logs',
            'monitoring',
            'bedrock',
            'mobiletargeting',
            'events',
            'lambda',
        ]
        assert fetcher.TARGET_SERVICE_CODES == expected_services

    def test_get_resource_types(self, fetcher):
        """Test get_resource_types returns correct types."""
        resource_types = fetcher.get_resource_types()
        assert resource_types == ['quotas']

    def test_create_client(self, fetcher):
        """Test client creation."""
        client = fetcher._create_client()
        assert client is not None
        assert client._service_model.service_name == 'service-quotas'

    @patch.object(ServiceQuotasFetcher, '_fetch_quotas')
    def test_fetch_resources(self, mock_fetch_quotas, fetcher):
        """Test fetch_resources returns correct structure."""
        mock_quotas = [
            Mock(spec=ServiceQuota),
            Mock(spec=ServiceQuota),
        ]
        mock_fetch_quotas.return_value = mock_quotas

        result = fetcher.fetch_resources()

        assert 'quotas' in result
        assert len(result['quotas']) == 2
        mock_fetch_quotas.assert_called_once()

    def test_fetch_quotas_for_service_success(self, fetcher):
        """Test fetching quotas for a single service."""
        # Mock the client methods
        fetcher.client.list_service_quotas = MagicMock(return_value={
            'Quotas': [
                {
                    'ServiceCode': 'lambda',
                    'ServiceName': 'AWS Lambda',
                    'QuotaCode': 'L-B99A9384',
                    'QuotaName': 'Concurrent executions',
                    'QuotaArn': 'arn:aws:servicequotas:us-east-1::lambda/L-B99A9384',
                    'Value': 1000.0,
                    'Unit': 'None',
                    'Adjustable': True,
                    'GlobalQuota': False,
                }
            ]
        })

        fetcher.client.list_aws_default_service_quotas = MagicMock(return_value={
            'Quotas': [
                {
                    'ServiceCode': 'lambda',
                    'QuotaCode': 'L-B99A9384',
                    'Value': 1000.0,
                }
            ]
        })

        # Mock pagination
        fetcher.client.can_paginate = MagicMock(return_value=False)

        quotas = fetcher._fetch_quotas_for_service('lambda')

        assert len(quotas) == 1
        assert quotas[0].service_code == 'lambda'
        assert quotas[0].quota_code == 'L-B99A9384'
        assert quotas[0].value == 1000.0
        assert quotas[0].adjustable is True

    def test_fetch_quotas_for_service_with_increased_quota(self, fetcher):
        """Test fetching quotas where current value differs from default."""
        fetcher.client.list_service_quotas = MagicMock(return_value={
            'Quotas': [
                {
                    'ServiceCode': 'lambda',
                    'ServiceName': 'AWS Lambda',
                    'QuotaCode': 'L-B99A9384',
                    'QuotaName': 'Concurrent executions',
                    'QuotaArn': 'arn:aws:servicequotas:us-east-1::lambda/L-B99A9384',
                    'Value': 3000.0,  # Increased from default
                    'Unit': 'None',
                    'Adjustable': True,
                    'GlobalQuota': False,
                }
            ]
        })

        fetcher.client.list_aws_default_service_quotas = MagicMock(return_value={
            'Quotas': [
                {
                    'ServiceCode': 'lambda',
                    'QuotaCode': 'L-B99A9384',
                    'Value': 1000.0,  # Default value
                }
            ]
        })

        fetcher.client.can_paginate = MagicMock(return_value=False)

        quotas = fetcher._fetch_quotas_for_service('lambda')

        assert len(quotas) == 1
        assert quotas[0].value == 3000.0
        assert quotas[0].default_value == 1000.0
        assert quotas[0].is_default is False
        assert quotas[0].has_been_increased() is True
        assert quotas[0].get_increase_amount() == 2000.0

    def test_fetch_quotas_for_nonexistent_service(self, fetcher):
        """Test fetching quotas for a service without quotas."""
        fetcher.client.list_service_quotas = MagicMock(
            side_effect=ClientError(
                {'Error': {'Code': 'NoSuchResourceException', 'Message': 'Not found'}},
                'list_service_quotas'
            )
        )

        quotas = fetcher._fetch_quotas_for_service('nonexistent-service')

        assert len(quotas) == 0

    def test_fetch_quotas_with_access_denied(self, fetcher):
        """Test handling of access denied errors."""
        fetcher.client.list_service_quotas = MagicMock(
            side_effect=ClientError(
                {'Error': {'Code': 'AccessDenied', 'Message': 'Access denied'}},
                'list_service_quotas'
            )
        )

        # Should raise the error
        with pytest.raises(ClientError) as exc_info:
            fetcher._fetch_quotas_for_service('lambda')

        assert exc_info.value.response['Error']['Code'] == 'AccessDenied'

    def test_fetch_default_quotas_success(self, fetcher):
        """Test fetching default quota values."""
        fetcher.client.list_aws_default_service_quotas = MagicMock(return_value={
            'Quotas': [
                {'QuotaCode': 'L-B99A9384', 'Value': 1000.0},
                {'QuotaCode': 'L-2ACBD22F', 'Value': 75.0},
            ]
        })

        fetcher.client.can_paginate = MagicMock(return_value=False)

        defaults = fetcher._fetch_default_quotas('lambda')

        assert len(defaults) == 2
        assert defaults['L-B99A9384'] == 1000.0
        assert defaults['L-2ACBD22F'] == 75.0

    def test_fetch_default_quotas_error(self, fetcher):
        """Test handling errors when fetching default quotas."""
        fetcher.client.list_aws_default_service_quotas = MagicMock(
            side_effect=ClientError(
                {'Error': {'Code': 'ServiceException', 'Message': 'Error'}},
                'list_aws_default_service_quotas'
            )
        )

        fetcher.client.can_paginate = MagicMock(return_value=False)

        defaults = fetcher._fetch_default_quotas('lambda')

        # Should return empty dict on error
        assert defaults == {}

    def test_fetch_quotas_multiple_services(self, fetcher):
        """Test fetching quotas for multiple services."""
        # Mock successful responses for some services
        def mock_list_service_quotas(**kwargs):
            service_code = kwargs.get('ServiceCode')
            if service_code in ['lambda', 's3']:
                return {
                    'Quotas': [
                        {
                            'ServiceCode': service_code,
                            'ServiceName': f'Service {service_code}',
                            'QuotaCode': 'TEST-001',
                            'QuotaName': 'Test Quota',
                            'QuotaArn': f'arn:aws:servicequotas::{service_code}/TEST-001',
                            'Value': 100.0,
                            'Unit': 'None',
                            'Adjustable': False,
                            'GlobalQuota': False,
                        }
                    ]
                }
            else:
                raise ClientError(
                    {'Error': {'Code': 'NoSuchResourceException'}},
                    'list_service_quotas'
                )

        fetcher.client.list_service_quotas = MagicMock(side_effect=mock_list_service_quotas)
        fetcher.client.list_aws_default_service_quotas = MagicMock(return_value={'Quotas': []})
        fetcher.client.can_paginate = MagicMock(return_value=False)

        # Only test with a subset of services
        original_services = fetcher.TARGET_SERVICE_CODES
        fetcher.TARGET_SERVICE_CODES = ['lambda', 's3', 'ec2']

        quotas = fetcher._fetch_quotas()

        # Should get 2 quotas (lambda and s3), ec2 should fail silently
        assert len(quotas) == 2

        # Restore original services
        fetcher.TARGET_SERVICE_CODES = original_services

    def test_list_available_services(self, fetcher):
        """Test listing available services."""
        fetcher.client.list_services = MagicMock(return_value={
            'Services': [
                {'ServiceCode': 'lambda', 'ServiceName': 'AWS Lambda'},
                {'ServiceCode': 'ec2', 'ServiceName': 'Amazon EC2'},
            ]
        })

        fetcher.client.can_paginate = MagicMock(return_value=False)

        services = fetcher.list_available_services()

        assert len(services) == 2
        assert services[0].service_code == 'lambda'
        assert services[0].service_name == 'AWS Lambda'
        assert services[1].service_code == 'ec2'

    def test_get_quota_by_code_success(self, fetcher):
        """Test getting a specific quota by code."""
        fetcher.client.get_service_quota = MagicMock(return_value={
            'Quota': {
                'ServiceCode': 'lambda',
                'ServiceName': 'AWS Lambda',
                'QuotaCode': 'L-B99A9384',
                'QuotaName': 'Concurrent executions',
                'QuotaArn': 'arn:aws:servicequotas::lambda/L-B99A9384',
                'Value': 3000.0,
                'Unit': 'None',
                'Adjustable': True,
                'GlobalQuota': False,
            }
        })

        fetcher.client.get_aws_default_service_quota = MagicMock(return_value={
            'Quota': {'Value': 1000.0}
        })

        quota = fetcher.get_quota_by_code('lambda', 'L-B99A9384')

        assert quota is not None
        assert quota.quota_code == 'L-B99A9384'
        assert quota.value == 3000.0
        assert quota.default_value == 1000.0

    def test_get_quota_by_code_not_found(self, fetcher):
        """Test getting a quota that doesn't exist."""
        fetcher.client.get_service_quota = MagicMock(
            side_effect=ClientError(
                {'Error': {'Code': 'NoSuchResourceException'}},
                'get_service_quota'
            )
        )

        quota = fetcher.get_quota_by_code('lambda', 'INVALID-CODE')

        assert quota is None

    def test_fetch_quotas_with_usage_metrics(self, fetcher):
        """Test fetching quotas that have usage metrics."""
        fetcher.client.list_service_quotas = MagicMock(return_value={
            'Quotas': [
                {
                    'ServiceCode': 'lambda',
                    'ServiceName': 'AWS Lambda',
                    'QuotaCode': 'L-B99A9384',
                    'QuotaName': 'Concurrent executions',
                    'QuotaArn': 'arn:aws:servicequotas::lambda/L-B99A9384',
                    'Value': 1000.0,
                    'Unit': 'None',
                    'Adjustable': True,
                    'GlobalQuota': False,
                    'UsageMetric': {
                        'MetricNamespace': 'AWS/Lambda',
                        'MetricName': 'ConcurrentExecutions',
                        'MetricDimensions': {},
                        'MetricStatisticRecommendation': 'Maximum'
                    }
                }
            ]
        })

        fetcher.client.list_aws_default_service_quotas = MagicMock(return_value={'Quotas': []})
        fetcher.client.can_paginate = MagicMock(return_value=False)

        quotas = fetcher._fetch_quotas_for_service('lambda')

        assert len(quotas) == 1
        assert quotas[0].usage_metric is not None
        assert quotas[0].usage_metric.metric_namespace == 'AWS/Lambda'
        assert quotas[0].usage_metric.metric_name == 'ConcurrentExecutions'

    def test_fetch_quotas_with_global_quota(self, fetcher):
        """Test fetching global quotas (not regional)."""
        fetcher.client.list_service_quotas = MagicMock(return_value={
            'Quotas': [
                {
                    'ServiceCode': 's3',
                    'ServiceName': 'Amazon S3',
                    'QuotaCode': 'L-DC2B2D3D',
                    'QuotaName': 'Buckets',
                    'QuotaArn': 'arn:aws:servicequotas::s3/L-DC2B2D3D',
                    'Value': 100.0,
                    'Unit': 'None',
                    'Adjustable': True,
                    'GlobalQuota': True,  # S3 buckets quota is global
                }
            ]
        })

        fetcher.client.list_aws_default_service_quotas = MagicMock(return_value={'Quotas': []})
        fetcher.client.can_paginate = MagicMock(return_value=False)

        quotas = fetcher._fetch_quotas_for_service('s3')

        assert len(quotas) == 1
        assert quotas[0].global_quota is True

    def test_service_quota_model_validation(self):
        """Test ServiceQuota model validation and methods."""
        quota_data = {
            'ServiceCode': 'lambda',
            'ServiceName': 'AWS Lambda',
            'QuotaCode': 'L-B99A9384',
            'QuotaName': 'Concurrent executions',
            'QuotaArn': 'arn:aws:servicequotas::lambda/L-B99A9384',
            'Value': 3000.0,
            'Unit': 'None',
            'Adjustable': True,
            'GlobalQuota': False,
        }

        quota = ServiceQuota.from_aws_response(quota_data, default_value=1000.0)

        assert quota.service_code == 'lambda'
        assert quota.value == 3000.0
        assert quota.default_value == 1000.0
        assert quota.has_been_increased() is True
        assert quota.get_increase_amount() == 2000.0
        assert quota.get_increase_percentage() == 200.0

    def test_service_info_model(self):
        """Test ServiceInfo model."""
        service_data = {
            'ServiceCode': 'lambda',
            'ServiceName': 'AWS Lambda'
        }

        service = ServiceInfo.from_aws_response(service_data)

        assert service.service_code == 'lambda'
        assert service.service_name == 'AWS Lambda'
        assert str(service) == 'ServiceInfo(lambda: AWS Lambda)'


class TestServiceQuotasIntegration:
    """Integration tests for ServiceQuotasFetcher."""

    def test_full_fetch_flow(self, fetcher):
        """Test complete flow of fetching quotas."""
        # Mock the entire fetch flow
        fetcher.client.list_service_quotas = MagicMock(return_value={
            'Quotas': [
                {
                    'ServiceCode': 'lambda',
                    'ServiceName': 'AWS Lambda',
                    'QuotaCode': 'L-B99A9384',
                    'QuotaName': 'Concurrent executions',
                    'QuotaArn': 'arn:aws:servicequotas::lambda/L-B99A9384',
                    'Value': 1000.0,
                    'Unit': 'None',
                    'Adjustable': True,
                    'GlobalQuota': False,
                }
            ]
        })

        fetcher.client.list_aws_default_service_quotas = MagicMock(return_value={
            'Quotas': [
                {'QuotaCode': 'L-B99A9384', 'Value': 1000.0}
            ]
        })

        fetcher.client.can_paginate = MagicMock(return_value=False)

        # Limit to just lambda for this test
        fetcher.TARGET_SERVICE_CODES = ['lambda']

        resources = fetcher.fetch_resources()

        assert 'quotas' in resources
        assert len(resources['quotas']) >= 1
        assert all(isinstance(q, ServiceQuota) for q in resources['quotas'])

    def test_error_handling_continues_with_other_services(self, fetcher):
        """Test that errors in one service don't stop others."""
        call_count = {'count': 0}

        def mock_list_service_quotas(**kwargs):
            call_count['count'] += 1
            service_code = kwargs.get('ServiceCode')

            if service_code == 'lambda':
                # Lambda fails
                raise ClientError(
                    {'Error': {'Code': 'InternalError'}},
                    'list_service_quotas'
                )
            else:
                # Others succeed
                return {
                    'Quotas': [
                        {
                            'ServiceCode': service_code,
                            'ServiceName': f'Service {service_code}',
                            'QuotaCode': 'TEST-001',
                            'QuotaName': 'Test Quota',
                            'QuotaArn': f'arn:aws:servicequotas::{service_code}/TEST-001',
                            'Value': 100.0,
                            'Unit': 'None',
                            'Adjustable': False,
                            'GlobalQuota': False,
                        }
                    ]
                }

        fetcher.client.list_service_quotas = MagicMock(side_effect=mock_list_service_quotas)
        fetcher.client.list_aws_default_service_quotas = MagicMock(return_value={'Quotas': []})
        fetcher.client.can_paginate = MagicMock(return_value=False)

        # Test with just a few services
        fetcher.TARGET_SERVICE_CODES = ['lambda', 's3', 'ec2']

        quotas = fetcher._fetch_quotas()

        # Lambda should fail but s3 and ec2 should succeed
        assert len(quotas) == 2
        # All three services should have been attempted
        assert call_count['count'] == 3
