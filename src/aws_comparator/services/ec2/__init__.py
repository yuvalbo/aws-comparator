"""
AWS EC2 service fetcher module.

This module provides functionality for fetching EC2 resources including
instances, security groups, VPCs, subnets, route tables, NACLs, and key pairs.
"""

from aws_comparator.services.ec2.fetcher import EC2Fetcher

__all__ = ["EC2Fetcher"]
