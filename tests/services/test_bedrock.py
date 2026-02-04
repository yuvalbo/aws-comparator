"""
Unit tests for AWS Bedrock service fetcher.

This module tests the BedrockFetcher class functionality including:
- Foundation model fetching
- Custom model fetching
- Provisioned throughput fetching
- Guardrail fetching
- Error handling
"""

from datetime import datetime, timezone
from unittest.mock import Mock

import pytest
from botocore.exceptions import ClientError

from aws_comparator.models.bedrock import (
    CustomModel,
    FoundationModel,
    Guardrail,
    ProvisionedModelThroughput,
)
from aws_comparator.services.bedrock.fetcher import BedrockFetcher


@pytest.fixture
def mock_session() -> Mock:
    """
    Create a mock boto3 session.

    Returns:
        Mock session object
    """
    session = Mock()
    return session


@pytest.fixture
def mock_bedrock_client() -> Mock:
    """
    Create a mock Bedrock client.

    Returns:
        Mock Bedrock client
    """
    client = Mock()
    return client


@pytest.fixture
def bedrock_fetcher(mock_session: Mock, mock_bedrock_client: Mock) -> BedrockFetcher:
    """
    Create a BedrockFetcher instance with mocked dependencies.

    Args:
        mock_session: Mock boto3 session
        mock_bedrock_client: Mock Bedrock client

    Returns:
        BedrockFetcher instance
    """
    mock_session.client.return_value = mock_bedrock_client
    fetcher = BedrockFetcher(mock_session, "us-east-1")
    return fetcher


class TestBedrockFetcherInit:
    """Test BedrockFetcher initialization."""

    def test_init_creates_client(self, mock_session: Mock) -> None:
        """Test that initialization creates a Bedrock client."""
        fetcher = BedrockFetcher(mock_session, "us-west-2")

        mock_session.client.assert_called_once_with("bedrock", region_name="us-west-2")
        assert fetcher.SERVICE_NAME == "bedrock"
        assert fetcher.region == "us-west-2"

    def test_get_resource_types(self, bedrock_fetcher: BedrockFetcher) -> None:
        """Test that get_resource_types returns correct types."""
        resource_types = bedrock_fetcher.get_resource_types()

        assert len(resource_types) == 4
        assert "foundation_models" in resource_types
        assert "custom_models" in resource_types
        assert "provisioned_throughput" in resource_types
        assert "guardrails" in resource_types


class TestFetchFoundationModels:
    """Test fetching foundation models."""

    def test_fetch_foundation_models_success(
        self, bedrock_fetcher: BedrockFetcher, mock_bedrock_client: Mock
    ) -> None:
        """Test successful fetching of foundation models."""
        mock_bedrock_client.list_foundation_models.return_value = {
            "modelSummaries": [
                {
                    "modelArn": "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-v2",
                    "modelId": "anthropic.claude-v2",
                    "modelName": "Claude v2",
                    "providerName": "Anthropic",
                    "inputModalities": ["TEXT"],
                    "outputModalities": ["TEXT"],
                    "responseStreamingSupported": True,
                    "customizationsSupported": ["FINE_TUNING"],
                    "inferenceTypesSupported": ["ON_DEMAND", "PROVISIONED"],
                },
                {
                    "modelArn": "arn:aws:bedrock:us-east-1::foundation-model/amazon.titan-text-express-v1",
                    "modelId": "amazon.titan-text-express-v1",
                    "modelName": "Titan Text Express",
                    "providerName": "Amazon",
                    "inputModalities": ["TEXT"],
                    "outputModalities": ["TEXT"],
                    "responseStreamingSupported": False,
                    "customizationsSupported": [],
                    "inferenceTypesSupported": ["ON_DEMAND"],
                },
            ]
        }

        models = bedrock_fetcher._fetch_foundation_models()

        assert len(models) == 2
        assert all(isinstance(model, FoundationModel) for model in models)

        # Check first model
        assert models[0].model_id == "anthropic.claude-v2"
        assert models[0].model_name == "Claude v2"
        assert models[0].provider_name == "Anthropic"
        assert models[0].response_streaming_supported is True
        assert "TEXT" in models[0].input_modalities

        # Check second model
        assert models[1].model_id == "amazon.titan-text-express-v1"
        assert models[1].provider_name == "Amazon"
        assert models[1].response_streaming_supported is False

    def test_fetch_foundation_models_empty(
        self, bedrock_fetcher: BedrockFetcher, mock_bedrock_client: Mock
    ) -> None:
        """Test fetching when no foundation models exist."""
        mock_bedrock_client.list_foundation_models.return_value = {"modelSummaries": []}

        models = bedrock_fetcher._fetch_foundation_models()

        assert len(models) == 0

    def test_fetch_foundation_models_access_denied(
        self, bedrock_fetcher: BedrockFetcher, mock_bedrock_client: Mock
    ) -> None:
        """Test handling of access denied error."""
        mock_bedrock_client.list_foundation_models.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Access denied"}},
            "list_foundation_models",
        )

        models = bedrock_fetcher._fetch_foundation_models()

        assert len(models) == 0

    def test_fetch_foundation_models_client_error(
        self, bedrock_fetcher: BedrockFetcher, mock_bedrock_client: Mock
    ) -> None:
        """Test handling of other client errors."""
        mock_bedrock_client.list_foundation_models.side_effect = ClientError(
            {"Error": {"Code": "ServiceUnavailable", "Message": "Service unavailable"}},
            "list_foundation_models",
        )

        models = bedrock_fetcher._fetch_foundation_models()

        assert len(models) == 0


class TestFetchCustomModels:
    """Test fetching custom models."""

    def test_fetch_custom_models_success(
        self, bedrock_fetcher: BedrockFetcher, mock_bedrock_client: Mock
    ) -> None:
        """Test successful fetching of custom models."""
        mock_paginator = Mock()
        mock_bedrock_client.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [
            {
                "modelSummaries": [
                    {
                        "modelArn": "arn:aws:bedrock:us-east-1:123456789012:custom-model/my-model",
                        "modelName": "my-custom-model",
                        "jobName": "training-job-1",
                        "baseModelArn": "arn:aws:bedrock:::foundation-model/anthropic.claude-v2",
                        "creationTime": datetime(2024, 1, 1, tzinfo=timezone.utc),
                        "modelKmsKeyArn": "arn:aws:kms:us-east-1:123456789012:key/abc123",
                    }
                ]
            }
        ]

        models = bedrock_fetcher._fetch_custom_models()

        assert len(models) == 1
        assert isinstance(models[0], CustomModel)
        assert models[0].model_name == "my-custom-model"
        assert models[0].job_name == "training-job-1"

    def test_fetch_custom_models_empty(
        self, bedrock_fetcher: BedrockFetcher, mock_bedrock_client: Mock
    ) -> None:
        """Test fetching when no custom models exist."""
        mock_paginator = Mock()
        mock_bedrock_client.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [{"modelSummaries": []}]

        models = bedrock_fetcher._fetch_custom_models()

        assert len(models) == 0

    def test_fetch_custom_models_pagination(
        self, bedrock_fetcher: BedrockFetcher, mock_bedrock_client: Mock
    ) -> None:
        """Test custom models fetching with pagination."""
        mock_paginator = Mock()
        mock_bedrock_client.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [
            {
                "modelSummaries": [
                    {
                        "modelArn": "arn:aws:bedrock:us-east-1:123456789012:custom-model/model1",
                        "modelName": "model-1",
                        "baseModelArn": "arn:aws:bedrock:::foundation-model/base1",
                        "creationTime": datetime(2024, 1, 1, tzinfo=timezone.utc),
                    }
                ]
            },
            {
                "modelSummaries": [
                    {
                        "modelArn": "arn:aws:bedrock:us-east-1:123456789012:custom-model/model2",
                        "modelName": "model-2",
                        "baseModelArn": "arn:aws:bedrock:::foundation-model/base2",
                        "creationTime": datetime(2024, 1, 2, tzinfo=timezone.utc),
                    }
                ]
            },
        ]

        models = bedrock_fetcher._fetch_custom_models()

        assert len(models) == 2
        assert models[0].model_name == "model-1"
        assert models[1].model_name == "model-2"


class TestFetchProvisionedThroughput:
    """Test fetching provisioned throughput."""

    def test_fetch_provisioned_throughput_success(
        self, bedrock_fetcher: BedrockFetcher, mock_bedrock_client: Mock
    ) -> None:
        """Test successful fetching of provisioned throughput."""
        mock_paginator = Mock()
        mock_bedrock_client.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [
            {
                "provisionedModelSummaries": [
                    {
                        "provisionedModelArn": "arn:aws:bedrock:us-east-1:123456789012:provisioned-model/my-model",
                        "provisionedModelName": "my-provisioned-model",
                        "modelArn": "arn:aws:bedrock:::foundation-model/anthropic.claude-v2",
                        "desiredModelUnits": 2,
                        "modelUnits": 2,
                        "status": "InService",
                        "creationTime": datetime(2024, 1, 1, tzinfo=timezone.utc),
                    }
                ]
            }
        ]

        throughputs = bedrock_fetcher._fetch_provisioned_throughput()

        assert len(throughputs) == 1
        assert isinstance(throughputs[0], ProvisionedModelThroughput)
        assert throughputs[0].provisioned_model_name == "my-provisioned-model"
        assert throughputs[0].desired_model_units == 2
        assert throughputs[0].status == "InService"

    def test_fetch_provisioned_throughput_empty(
        self, bedrock_fetcher: BedrockFetcher, mock_bedrock_client: Mock
    ) -> None:
        """Test fetching when no provisioned throughput exists."""
        mock_paginator = Mock()
        mock_bedrock_client.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [{"provisionedModelSummaries": []}]

        throughputs = bedrock_fetcher._fetch_provisioned_throughput()

        assert len(throughputs) == 0


class TestFetchGuardrails:
    """Test fetching guardrails."""

    def test_fetch_guardrails_success(
        self, bedrock_fetcher: BedrockFetcher, mock_bedrock_client: Mock
    ) -> None:
        """Test successful fetching of guardrails."""
        mock_paginator = Mock()
        mock_bedrock_client.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [
            {
                "guardrails": [
                    {
                        "id": "guardrail-123",
                        "arn": "arn:aws:bedrock:us-east-1:123456789012:guardrail/guardrail-123",
                        "name": "content-filter",
                        "status": "READY",
                        "version": "1",
                        "createdAt": datetime(2024, 1, 1, tzinfo=timezone.utc),
                        "updatedAt": datetime(2024, 1, 2, tzinfo=timezone.utc),
                    }
                ]
            }
        ]

        guardrails = bedrock_fetcher._fetch_guardrails()

        assert len(guardrails) == 1
        assert isinstance(guardrails[0], Guardrail)
        assert guardrails[0].name == "content-filter"
        assert guardrails[0].status == "READY"
        assert guardrails[0].guardrail_id == "guardrail-123"

    def test_fetch_guardrails_empty(
        self, bedrock_fetcher: BedrockFetcher, mock_bedrock_client: Mock
    ) -> None:
        """Test fetching when no guardrails exist."""
        mock_paginator = Mock()
        mock_bedrock_client.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [{"guardrails": []}]

        guardrails = bedrock_fetcher._fetch_guardrails()

        assert len(guardrails) == 0


class TestFetchResources:
    """Test the main fetch_resources method."""

    def test_fetch_resources_all_types(
        self, bedrock_fetcher: BedrockFetcher, mock_bedrock_client: Mock
    ) -> None:
        """Test fetching all resource types."""
        # Mock foundation models
        mock_bedrock_client.list_foundation_models.return_value = {
            "modelSummaries": [
                {
                    "modelArn": "arn:aws:bedrock:::foundation-model/model1",
                    "modelId": "model1",
                    "modelName": "Model 1",
                    "providerName": "Provider1",
                    "inputModalities": ["TEXT"],
                    "outputModalities": ["TEXT"],
                    "responseStreamingSupported": True,
                    "customizationsSupported": [],
                    "inferenceTypesSupported": ["ON_DEMAND"],
                }
            ]
        }

        # Mock custom models
        mock_paginator_custom = Mock()
        mock_paginator_custom.paginate.return_value = [{"modelSummaries": []}]

        # Mock provisioned throughput
        mock_paginator_throughput = Mock()
        mock_paginator_throughput.paginate.return_value = [
            {"provisionedModelSummaries": []}
        ]

        # Mock guardrails
        mock_paginator_guardrails = Mock()
        mock_paginator_guardrails.paginate.return_value = [{"guardrails": []}]

        # Configure get_paginator to return appropriate paginator
        def get_paginator_side_effect(operation_name: str) -> Mock:
            if operation_name == "list_custom_models":
                return mock_paginator_custom
            elif operation_name == "list_provisioned_model_throughputs":
                return mock_paginator_throughput
            elif operation_name == "list_guardrails":
                return mock_paginator_guardrails
            raise ValueError(f"Unexpected operation: {operation_name}")

        mock_bedrock_client.get_paginator.side_effect = get_paginator_side_effect

        resources = bedrock_fetcher.fetch_resources()

        assert "foundation_models" in resources
        assert "custom_models" in resources
        assert "provisioned_throughput" in resources
        assert "guardrails" in resources
        assert len(resources["foundation_models"]) == 1
        assert len(resources["custom_models"]) == 0
        assert len(resources["provisioned_throughput"]) == 0
        assert len(resources["guardrails"]) == 0

    def test_fetch_resources_handles_errors_gracefully(
        self, bedrock_fetcher: BedrockFetcher, mock_bedrock_client: Mock
    ) -> None:
        """Test that fetch_resources handles errors in individual fetchers."""
        # Make foundation models fail
        mock_bedrock_client.list_foundation_models.side_effect = Exception("API Error")

        # Mock other resources to succeed
        mock_paginator = Mock()
        mock_paginator.paginate.return_value = [{"modelSummaries": []}]
        mock_bedrock_client.get_paginator.return_value = mock_paginator

        resources = bedrock_fetcher.fetch_resources()

        # Should return empty lists for all types (errors are caught)
        assert "foundation_models" in resources
        assert len(resources["foundation_models"]) == 0


class TestErrorHandling:
    """Test error handling scenarios."""

    def test_handles_unauthorized_error(
        self, bedrock_fetcher: BedrockFetcher, mock_bedrock_client: Mock
    ) -> None:
        """Test handling of UnauthorizedOperation error."""
        mock_bedrock_client.list_foundation_models.side_effect = ClientError(
            {"Error": {"Code": "UnauthorizedOperation", "Message": "Unauthorized"}},
            "list_foundation_models",
        )

        models = bedrock_fetcher._fetch_foundation_models()

        assert len(models) == 0

    def test_handles_generic_exception(
        self, bedrock_fetcher: BedrockFetcher, mock_bedrock_client: Mock
    ) -> None:
        """Test handling of generic exceptions."""
        mock_bedrock_client.list_foundation_models.side_effect = Exception(
            "Unexpected error"
        )

        models = bedrock_fetcher._fetch_foundation_models()

        assert len(models) == 0

    def test_handles_malformed_response(
        self, bedrock_fetcher: BedrockFetcher, mock_bedrock_client: Mock
    ) -> None:
        """Test handling of malformed API responses."""
        mock_bedrock_client.list_foundation_models.return_value = {
            "modelSummaries": [
                {
                    # Missing modelId which is required and validated
                    "modelName": "incomplete-model"
                }
            ]
        }

        models = bedrock_fetcher._fetch_foundation_models()

        # Should handle gracefully and skip entries with empty modelId
        assert len(models) == 0
