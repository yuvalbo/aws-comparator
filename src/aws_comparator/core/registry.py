"""
Service registry for dynamic service discovery and loading.

This module implements the registry pattern, allowing service fetchers
to self-register and be discovered at runtime without modifying the
orchestrator code.
"""

from typing import Any, Dict, List, Type, Optional, Callable
import logging

from aws_comparator.core.exceptions import ServiceNotSupportedError

logger = logging.getLogger(__name__)


class ServiceRegistry:
    """
    Registry for AWS service fetchers.

    This class maintains a registry of all available service fetchers,
    allowing for dynamic discovery and instantiation. Services register
    themselves using the @register decorator.

    Example:
        >>> @ServiceRegistry.register('ec2')
        ... class EC2Fetcher(BaseServiceFetcher):
        ...     pass
        ...
        >>> fetcher = ServiceRegistry.get_fetcher('ec2', session, region)
    """

    _registry: Dict[str, Type[Any]] = {}
    _metadata: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def register(
        cls,
        service_name: str,
        description: Optional[str] = None,
        resource_types: Optional[List[str]] = None
    ) -> Callable[[Type[Any]], Type[Any]]:
        """
        Decorator to register a service fetcher.

        Args:
            service_name: Unique identifier for the service (e.g., 'ec2', 's3')
            description: Human-readable description of the service
            resource_types: List of resource types handled by this service

        Returns:
            Decorator function

        Example:
            >>> @ServiceRegistry.register('ec2', description='EC2 Service')
            ... class EC2Fetcher(BaseServiceFetcher):
            ...     pass
        """
        def decorator(fetcher_class: Type[Any]) -> Type[Any]:
            if service_name in cls._registry:
                logger.warning(
                    f"Service '{service_name}' is already registered. "
                    f"Overwriting with {fetcher_class.__name__}"
                )

            cls._registry[service_name] = fetcher_class

            # Store metadata
            cls._metadata[service_name] = {
                'name': service_name,
                'class': fetcher_class.__name__,
                'description': description or f"{service_name.upper()} service",
                'resource_types': resource_types or [],
            }

            logger.debug(f"Registered service: {service_name} ({fetcher_class.__name__})")
            return fetcher_class

        return decorator

    @classmethod
    def get_fetcher(
        cls,
        service_name: str,
        session: Any,
        region: str
    ) -> Any:
        """
        Get an instance of a registered service fetcher.

        Args:
            service_name: Name of the service
            session: boto3 Session instance
            region: AWS region

        Returns:
            Instance of the service fetcher

        Raises:
            ServiceNotSupportedError: If service is not registered
        """
        if service_name not in cls._registry:
            raise ServiceNotSupportedError(service_name)

        fetcher_class = cls._registry[service_name]
        try:
            return fetcher_class(session, region)
        except Exception as e:
            logger.error(
                f"Failed to instantiate fetcher for service '{service_name}': {e}"
            )
            raise

    @classmethod
    def list_services(cls) -> List[str]:
        """
        List all registered service names.

        Returns:
            Sorted list of registered service names
        """
        return sorted(cls._registry.keys())

    @classmethod
    def get_service_info(cls, service_name: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata about a registered service.

        Args:
            service_name: Name of the service

        Returns:
            Dictionary with service metadata, or None if not found
        """
        return cls._metadata.get(service_name)

    @classmethod
    def get_all_service_info(cls) -> Dict[str, Dict[str, Any]]:
        """
        Get metadata for all registered services.

        Returns:
            Dictionary mapping service names to their metadata
        """
        return dict(cls._metadata)

    @classmethod
    def is_registered(cls, service_name: str) -> bool:
        """
        Check if a service is registered.

        Args:
            service_name: Name of the service

        Returns:
            True if service is registered, False otherwise
        """
        return service_name in cls._registry

    @classmethod
    def clear(cls) -> None:
        """
        Clear all registered services.

        This is primarily used for testing purposes.
        """
        cls._registry.clear()
        cls._metadata.clear()
        logger.debug("Cleared service registry")

    @classmethod
    def get_service_count(cls) -> int:
        """
        Get the number of registered services.

        Returns:
            Number of registered services
        """
        return len(cls._registry)

    @classmethod
    def validate_services(cls, service_names: List[str]) -> tuple[List[str], List[str]]:
        """
        Validate a list of service names.

        Args:
            service_names: List of service names to validate

        Returns:
            Tuple of (valid_services, invalid_services)
        """
        valid = []
        invalid = []

        for service_name in service_names:
            if cls.is_registered(service_name):
                valid.append(service_name)
            else:
                invalid.append(service_name)

        return valid, invalid

    def __repr__(cls) -> str:
        """Return detailed representation of registry."""
        return (
            f"ServiceRegistry("
            f"registered_services={cls.get_service_count()}, "
            f"services={cls.list_services()})"
        )
