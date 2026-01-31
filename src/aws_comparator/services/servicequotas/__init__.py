"""
AWS Service Quotas service module.

This module provides functionality to fetch and compare service quotas
across AWS accounts.
"""

from aws_comparator.services.servicequotas.fetcher import ServiceQuotasFetcher

__all__ = ['ServiceQuotasFetcher']
