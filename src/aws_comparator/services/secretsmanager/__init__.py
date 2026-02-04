"""
AWS Secrets Manager service fetcher.

This module provides the fetcher for AWS Secrets Manager resources.
SECURITY CRITICAL: Only fetches metadata, NEVER fetches secret values.
"""

from aws_comparator.services.secretsmanager.fetcher import SecretsManagerFetcher

__all__ = ["SecretsManagerFetcher"]
