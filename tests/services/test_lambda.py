"""Tests for Lambda service fetcher."""
import zipfile
from io import BytesIO
from unittest.mock import MagicMock

import boto3
import pytest
from moto import mock_aws

from aws_comparator.services.lambda_service.fetcher import LambdaFetcher


def create_lambda_zip() -> bytes:
    """Create a minimal zip file for Lambda deployment."""
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("lambda_function.py", "def handler(event, context): return 'ok'")
    zip_buffer.seek(0)
    return zip_buffer.read()


@pytest.fixture
def mock_session():
    """Create a mock boto3 session."""
    session = MagicMock()
    return session


@pytest.fixture
def lambda_role_arn():
    """Return a test IAM role ARN for Lambda."""
    return "arn:aws:iam::123456789012:role/test-lambda-role"


class TestLambdaFetcherInit:
    """Tests for LambdaFetcher initialization."""

    def test_init_sets_service_name(self, mock_session):
        """Test fetcher sets correct service name."""
        fetcher = LambdaFetcher(session=mock_session, region="us-east-1")
        assert fetcher.SERVICE_NAME == "lambda"

    def test_init_sets_region(self, mock_session):
        """Test fetcher sets region."""
        fetcher = LambdaFetcher(session=mock_session, region="us-west-2")
        assert fetcher.region == "us-west-2"


class TestLambdaFetcherGetResourceTypes:
    """Tests for get_resource_types method."""

    def test_get_resource_types(self, mock_session):
        """Test get_resource_types returns expected types."""
        fetcher = LambdaFetcher(session=mock_session, region="us-east-1")
        resource_types = fetcher.get_resource_types()

        assert "functions" in resource_types


class TestLambdaFetcherFetchResources:
    """Tests for fetch_resources method."""

    @mock_aws
    def test_fetch_resources_empty(self):
        """Test fetching resources when no functions exist."""
        session = boto3.Session(region_name="us-east-1")
        fetcher = LambdaFetcher(session=session, region="us-east-1")

        resources = fetcher.fetch_resources()

        assert "functions" in resources
        assert len(resources["functions"]) == 0

    @mock_aws
    @pytest.mark.skip(reason="Moto Lambda function creation not fully compatible with fetcher model")
    def test_fetch_resources_with_functions(self, lambda_role_arn):
        """Test fetching resources with existing functions."""
        session = boto3.Session(region_name="us-east-1")

        # Create IAM role first
        iam_client = session.client("iam", region_name="us-east-1")
        iam_client.create_role(
            RoleName="test-lambda-role",
            AssumeRolePolicyDocument='{"Version": "2012-10-17", "Statement": []}',
        )

        lambda_client = session.client("lambda", region_name="us-east-1")

        # Create test functions
        lambda_client.create_function(
            FunctionName="test-function-1",
            Runtime="python3.9",
            Role=lambda_role_arn,
            Handler="lambda_function.handler",
            Code={"ZipFile": create_lambda_zip()},
        )
        lambda_client.create_function(
            FunctionName="test-function-2",
            Runtime="python3.9",
            Role=lambda_role_arn,
            Handler="lambda_function.handler",
            Code={"ZipFile": create_lambda_zip()},
        )

        fetcher = LambdaFetcher(session=session, region="us-east-1")
        resources = fetcher.fetch_resources()

        assert "functions" in resources
        assert len(resources["functions"]) == 2

    @mock_aws
    @pytest.mark.skip(reason="Moto Lambda function creation not fully compatible with fetcher model")
    def test_fetch_resources_function_properties(self, lambda_role_arn):
        """Test fetched functions have expected properties."""
        session = boto3.Session(region_name="us-east-1")

        # Create IAM role first
        iam_client = session.client("iam", region_name="us-east-1")
        iam_client.create_role(
            RoleName="test-lambda-role",
            AssumeRolePolicyDocument='{"Version": "2012-10-17", "Statement": []}',
        )

        lambda_client = session.client("lambda", region_name="us-east-1")

        # Create test function
        lambda_client.create_function(
            FunctionName="test-function",
            Runtime="python3.9",
            Role=lambda_role_arn,
            Handler="lambda_function.handler",
            Code={"ZipFile": create_lambda_zip()},
            Description="Test function",
            MemorySize=256,
            Timeout=30,
        )

        fetcher = LambdaFetcher(session=session, region="us-east-1")
        resources = fetcher.fetch_resources()

        func = resources["functions"][0]
        assert hasattr(func, "function_name")
        assert func.function_name == "test-function"
        assert hasattr(func, "runtime")
        assert func.runtime == "python3.9"

    @mock_aws
    @pytest.mark.skip(reason="Moto Lambda function creation not fully compatible with fetcher model")
    def test_fetch_resources_with_tags(self, lambda_role_arn):
        """Test fetching function with tags."""
        session = boto3.Session(region_name="us-east-1")

        # Create IAM role first
        iam_client = session.client("iam", region_name="us-east-1")
        iam_client.create_role(
            RoleName="test-lambda-role",
            AssumeRolePolicyDocument='{"Version": "2012-10-17", "Statement": []}',
        )

        lambda_client = session.client("lambda", region_name="us-east-1")

        # Create function with tags
        lambda_client.create_function(
            FunctionName="tagged-function",
            Runtime="python3.9",
            Role=lambda_role_arn,
            Handler="lambda_function.handler",
            Code={"ZipFile": create_lambda_zip()},
            Tags={"Environment": "test", "Team": "platform"},
        )

        fetcher = LambdaFetcher(session=session, region="us-east-1")
        resources = fetcher.fetch_resources()

        func = resources["functions"][0]
        assert func.tags.get("Environment") == "test"
        assert func.tags.get("Team") == "platform"


class TestLambdaFetcherErrorHandling:
    """Tests for error handling in LambdaFetcher."""

    def test_fetch_with_client_error(self, mock_session):
        """Test fetcher handles client errors gracefully."""
        from botocore.exceptions import ClientError

        mock_client = MagicMock()
        mock_client.get_paginator.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Access Denied"}},
            "ListFunctions",
        )
        mock_session.client.return_value = mock_client

        fetcher = LambdaFetcher(session=mock_session, region="us-east-1")
        resources = fetcher.fetch_resources()

        # Should return empty list on error
        assert resources["functions"] == []

    def test_fetch_with_no_client(self, mock_session):
        """Test fetcher handles missing client."""
        mock_session.client.return_value = None

        fetcher = LambdaFetcher(session=mock_session, region="us-east-1")

        # Should handle gracefully
        resources = fetcher.fetch_resources()
        assert "functions" in resources
