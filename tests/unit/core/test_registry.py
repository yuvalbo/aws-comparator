"""
Unit tests for service registry.
"""

import pytest

from aws_comparator.core.registry import ServiceRegistry
from aws_comparator.core.exceptions import ServiceNotSupportedError
from aws_comparator.services.base import BaseServiceFetcher


class MockFetcher(BaseServiceFetcher):
    """Mock fetcher for testing."""

    SERVICE_NAME = "mock"

    def _create_client(self):
        return None

    def fetch_resources(self):
        return {}

    def get_resource_types(self):
        return ["test_resource"]


class TestServiceRegistry:
    """Test ServiceRegistry class."""

    def setup_method(self):
        """Clear registry before each test."""
        ServiceRegistry.clear()

    def test_register_service(self):
        """Test registering a service."""
        @ServiceRegistry.register('test-service', description='Test Service')
        class TestFetcher(MockFetcher):
            SERVICE_NAME = 'test-service'

        assert ServiceRegistry.is_registered('test-service')
        assert 'test-service' in ServiceRegistry.list_services()

    def test_register_service_without_description(self):
        """Test registering service without description."""
        @ServiceRegistry.register('test-service2')
        class TestFetcher2(MockFetcher):
            SERVICE_NAME = 'test-service2'

        info = ServiceRegistry.get_service_info('test-service2')
        assert info is not None
        assert 'description' in info

    def test_get_fetcher(self):
        """Test getting a fetcher instance."""
        @ServiceRegistry.register('test-service3')
        class TestFetcher3(MockFetcher):
            SERVICE_NAME = 'test-service3'

        # Mock session
        class MockSession:
            pass

        fetcher = ServiceRegistry.get_fetcher('test-service3', MockSession(), 'us-east-1')
        assert isinstance(fetcher, TestFetcher3)

    def test_get_fetcher_not_registered(self):
        """Test getting non-existent fetcher raises error."""
        class MockSession:
            pass

        with pytest.raises(ServiceNotSupportedError):
            ServiceRegistry.get_fetcher('non-existent', MockSession(), 'us-east-1')

    def test_list_services(self):
        """Test listing all services."""
        @ServiceRegistry.register('service-a')
        class ServiceA(MockFetcher):
            SERVICE_NAME = 'service-a'

        @ServiceRegistry.register('service-b')
        class ServiceB(MockFetcher):
            SERVICE_NAME = 'service-b'

        services = ServiceRegistry.list_services()
        assert 'service-a' in services
        assert 'service-b' in services
        assert services == sorted(services)  # Should be sorted

    def test_get_service_info(self):
        """Test getting service metadata."""
        @ServiceRegistry.register(
            'test-service4',
            description='Test Service 4',
            resource_types=['res1', 'res2']
        )
        class TestFetcher4(MockFetcher):
            SERVICE_NAME = 'test-service4'

        info = ServiceRegistry.get_service_info('test-service4')
        assert info is not None
        assert info['name'] == 'test-service4'
        assert info['description'] == 'Test Service 4'
        assert len(info['resource_types']) == 2

    def test_get_all_service_info(self):
        """Test getting all service metadata."""
        @ServiceRegistry.register('service1')
        class Service1(MockFetcher):
            SERVICE_NAME = 'service1'

        @ServiceRegistry.register('service2')
        class Service2(MockFetcher):
            SERVICE_NAME = 'service2'

        all_info = ServiceRegistry.get_all_service_info()
        assert isinstance(all_info, dict)
        assert 'service1' in all_info
        assert 'service2' in all_info

    def test_is_registered(self):
        """Test checking if service is registered."""
        @ServiceRegistry.register('test-service5')
        class TestFetcher5(MockFetcher):
            SERVICE_NAME = 'test-service5'

        assert ServiceRegistry.is_registered('test-service5')
        assert not ServiceRegistry.is_registered('non-existent')

    def test_get_service_count(self):
        """Test getting service count."""
        initial_count = ServiceRegistry.get_service_count()

        @ServiceRegistry.register('new-service')
        class NewService(MockFetcher):
            SERVICE_NAME = 'new-service'

        assert ServiceRegistry.get_service_count() == initial_count + 1

    def test_validate_services(self):
        """Test validating service names."""
        @ServiceRegistry.register('valid1')
        class Valid1(MockFetcher):
            SERVICE_NAME = 'valid1'

        @ServiceRegistry.register('valid2')
        class Valid2(MockFetcher):
            SERVICE_NAME = 'valid2'

        valid, invalid = ServiceRegistry.validate_services(['valid1', 'valid2', 'invalid'])

        assert 'valid1' in valid
        assert 'valid2' in valid
        assert 'invalid' in invalid

    def test_clear_registry(self):
        """Test clearing the registry."""
        @ServiceRegistry.register('temp-service')
        class TempService(MockFetcher):
            SERVICE_NAME = 'temp-service'

        assert ServiceRegistry.get_service_count() > 0

        ServiceRegistry.clear()
        assert ServiceRegistry.get_service_count() == 0

    def test_register_duplicate_service_warning(self, caplog):
        """Test warning when registering duplicate service."""
        @ServiceRegistry.register('dup-service')
        class DupService1(MockFetcher):
            SERVICE_NAME = 'dup-service'

        # Register again
        @ServiceRegistry.register('dup-service')
        class DupService2(MockFetcher):
            SERVICE_NAME = 'dup-service'

        # Should still work, but with warning
        assert ServiceRegistry.is_registered('dup-service')
