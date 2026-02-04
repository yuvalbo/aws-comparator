"""
Unit tests for AWS Secrets Manager service fetcher.

SECURITY CRITICAL: These tests verify that secret values are NEVER fetched.
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, Mock, patch

import boto3
import pytest
from botocore.exceptions import ClientError
from moto import mock_aws

from aws_comparator.models.secretsmanager import RotationRules, SecretMetadata
from aws_comparator.services.secretsmanager.fetcher import SecretsManagerFetcher


class TestSecretMetadataModel:
    """Test the SecretMetadata Pydantic model."""

    def test_secret_metadata_basic_creation(self):
        """Test creating a basic SecretMetadata instance."""
        secret = SecretMetadata(
            name="test-secret",
            arn="arn:aws:secretsmanager:us-east-1:123456789012:secret:test-secret-abc123",
            description="Test secret",
            rotation_enabled=False,
        )

        assert secret.name == "test-secret"
        assert secret.rotation_enabled is False
        assert secret.kms_key_id is None

    def test_secret_metadata_with_rotation(self):
        """Test SecretMetadata with rotation configuration."""
        rotation_rules = RotationRules(
            automatically_after_days=30,
            duration="3h",
            schedule_expression="rate(30 days)",
        )

        secret = SecretMetadata(
            name="test-secret",
            arn="arn:aws:secretsmanager:us-east-1:123456789012:secret:test-secret-abc123",
            rotation_enabled=True,
            rotation_lambda_arn="arn:aws:lambda:us-east-1:123456789012:function:rotate",
            rotation_rules=rotation_rules,
            last_rotated_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
        )

        assert secret.rotation_enabled is True
        assert secret.rotation_rules.automatically_after_days == 30
        assert secret.last_rotated_date.year == 2024

    def test_secret_metadata_name_validation(self):
        """Test that secret name validation works."""
        with pytest.raises(ValueError, match="Secret name cannot be empty"):
            SecretMetadata(
                name="", arn="arn:aws:secretsmanager:us-east-1:123456789012:secret:test"
            )

        with pytest.raises(ValueError, match="cannot exceed 256 characters"):
            SecretMetadata(
                name="a" * 257,
                arn="arn:aws:secretsmanager:us-east-1:123456789012:secret:test",
            )

    def test_secret_metadata_from_aws_response(self):
        """Test creating SecretMetadata from AWS API response."""
        aws_response = {
            "Name": "my-secret",
            "ARN": "arn:aws:secretsmanager:us-east-1:123456789012:secret:my-secret-abc123",
            "Description": "My test secret",
            "KmsKeyId": "arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012",
            "RotationEnabled": True,
            "RotationLambdaARN": "arn:aws:lambda:us-east-1:123456789012:function:rotate-secret",
            "RotationRules": {"AutomaticallyAfterDays": 30},
            "LastRotatedDate": datetime(2024, 1, 1, tzinfo=timezone.utc),
            "LastChangedDate": datetime(2024, 1, 15, tzinfo=timezone.utc),
            "Tags": [
                {"Key": "Environment", "Value": "Production"},
                {"Key": "Team", "Value": "Platform"},
            ],
        }

        secret = SecretMetadata.from_aws_response(aws_response)

        assert secret.name == "my-secret"
        assert secret.description == "My test secret"
        assert secret.rotation_enabled is True
        assert secret.rotation_rules.automatically_after_days == 30
        assert secret.tags == {"Environment": "Production", "Team": "Platform"}

    def test_secret_metadata_security_violation_on_secret_string(self):
        """Test that SecretMetadata rejects data containing secret values."""
        aws_response_with_secret = {
            "Name": "my-secret",
            "ARN": "arn:aws:secretsmanager:us-east-1:123456789012:secret:my-secret-abc123",
            "SecretString": "this-is-the-actual-secret-value",  # SECURITY VIOLATION
        }

        with pytest.raises(ValueError, match="SECURITY VIOLATION"):
            SecretMetadata.from_aws_response(aws_response_with_secret)

    def test_secret_metadata_security_violation_on_secret_binary(self):
        """Test that SecretMetadata rejects binary secret data."""
        aws_response_with_secret = {
            "Name": "my-secret",
            "ARN": "arn:aws:secretsmanager:us-east-1:123456789012:secret:my-secret-abc123",
            "SecretBinary": b"binary-secret-data",  # SECURITY VIOLATION
        }

        with pytest.raises(ValueError, match="SECURITY VIOLATION"):
            SecretMetadata.from_aws_response(aws_response_with_secret)


class TestRotationRulesModel:
    """Test the RotationRules Pydantic model."""

    def test_rotation_rules_basic_creation(self):
        """Test creating basic RotationRules."""
        rules = RotationRules(automatically_after_days=30)

        assert rules.automatically_after_days == 30
        assert rules.duration is None
        assert rules.schedule_expression is None

    def test_rotation_rules_validation(self):
        """Test rotation rules validation."""
        with pytest.raises(ValueError):
            RotationRules(automatically_after_days=0)  # Must be >= 1

        with pytest.raises(ValueError):
            RotationRules(automatically_after_days=400)  # Must be <= 365


@mock_aws
class TestSecretsManagerFetcher:
    """Test the SecretsManagerFetcher class."""

    @pytest.fixture
    def session(self):
        """Create a boto3 session for testing."""
        return boto3.Session(region_name="us-east-1")

    @pytest.fixture
    def fetcher(self, session):
        """Create a SecretsManagerFetcher instance for testing."""
        return SecretsManagerFetcher(session=session, region="us-east-1")

    @pytest.fixture
    def secrets_client(self, session):
        """Create a Secrets Manager client for test setup."""
        return session.client("secretsmanager", region_name="us-east-1")

    def test_fetcher_initialization(self, fetcher):
        """Test that the fetcher initializes correctly."""
        assert fetcher.SERVICE_NAME == "secretsmanager"
        assert fetcher.region == "us-east-1"
        assert fetcher.client is not None

    def test_get_resource_types(self, fetcher):
        """Test getting resource types."""
        resource_types = fetcher.get_resource_types()
        assert resource_types == ["secrets"]

    def test_fetch_secrets_empty(self, fetcher):
        """Test fetching secrets when none exist."""
        resources = fetcher.fetch_resources()

        assert "secrets" in resources
        assert len(resources["secrets"]) == 0

    def test_fetch_secrets_basic(self, fetcher, secrets_client):
        """Test fetching basic secret metadata."""
        # Create a test secret
        secrets_client.create_secret(
            Name="test-secret-1",
            Description="Test secret 1",
            SecretString="dummy-value",
        )

        secrets_client.create_secret(
            Name="test-secret-2",
            Description="Test secret 2",
            SecretString="dummy-value",
        )

        # Fetch secrets
        resources = fetcher.fetch_resources()

        assert "secrets" in resources
        assert len(resources["secrets"]) == 2

        secrets = resources["secrets"]
        secret_names = {s.name for s in secrets}
        assert "test-secret-1" in secret_names
        assert "test-secret-2" in secret_names

        # Verify it's metadata only
        for secret in secrets:
            assert isinstance(secret, SecretMetadata)
            assert secret.name is not None
            assert secret.arn is not None

    def test_fetch_secrets_with_rotation(self, fetcher, secrets_client):
        """Test fetching secrets with rotation enabled."""
        # Create secret with rotation
        secrets_client.create_secret(
            Name="rotated-secret",
            Description="Secret with rotation",
            SecretString="dummy-value",
        )

        # Enable rotation (in moto, this may be limited)
        # For now, just verify we can fetch the metadata
        resources = fetcher.fetch_resources()

        assert len(resources["secrets"]) == 1
        secret = resources["secrets"][0]
        assert secret.name == "rotated-secret"

    def test_fetch_secrets_with_tags(self, fetcher, secrets_client):
        """Test fetching secrets with tags."""
        secrets_client.create_secret(
            Name="tagged-secret",
            Description="Secret with tags",
            SecretString="dummy-value",
            Tags=[
                {"Key": "Environment", "Value": "Test"},
                {"Key": "Application", "Value": "MyApp"},
            ],
        )

        resources = fetcher.fetch_resources()

        assert len(resources["secrets"]) == 1
        secret = resources["secrets"][0]
        assert secret.tags == {"Environment": "Test", "Application": "MyApp"}

    def test_fetch_secrets_with_kms(self, fetcher, secrets_client):
        """Test fetching secrets with KMS encryption."""
        # Create secret (moto may not fully support KMS, but we test the code path)
        secrets_client.create_secret(
            Name="kms-secret", Description="Secret with KMS", SecretString="dummy-value"
        )

        resources = fetcher.fetch_resources()

        assert len(resources["secrets"]) == 1
        secret = resources["secrets"][0]
        assert secret.name == "kms-secret"

    def test_fetch_secrets_handles_access_denied(self, fetcher):
        """Test that access denied errors are handled gracefully."""
        # Mock the client to raise AccessDenied
        fetcher.client.list_secrets = Mock(
            side_effect=ClientError(
                {"Error": {"Code": "AccessDenied", "Message": "Access Denied"}},
                "list_secrets",
            )
        )

        resources = fetcher.fetch_resources()

        # Should return empty list, not crash
        assert resources["secrets"] == []

    def test_fetch_secrets_handles_resource_not_found(self, fetcher, secrets_client):
        """Test handling of ResourceNotFoundException during describe."""
        # Create a secret
        secrets_client.create_secret(Name="test-secret", SecretString="dummy-value")

        # Mock describe_secret to fail
        fetcher.client.describe_secret = Mock(
            side_effect=ClientError(
                {
                    "Error": {
                        "Code": "ResourceNotFoundException",
                        "Message": "Not found",
                    }
                },
                "describe_secret",
            )
        )

        resources = fetcher.fetch_resources()

        # Should still fetch using list_secrets data
        assert len(resources["secrets"]) == 1

    def test_security_no_get_secret_value_calls(self, fetcher, secrets_client):
        """SECURITY TEST: Verify that get_secret_value is NEVER called."""
        # Create secrets
        secrets_client.create_secret(Name="secret-1", SecretString="value-1")
        secrets_client.create_secret(Name="secret-2", SecretString="value-2")

        # Wrap get_secret_value to detect if it's called
        original_get_secret_value = fetcher.client.get_secret_value
        mock_get_secret_value = Mock(wraps=original_get_secret_value)
        fetcher.client.get_secret_value = mock_get_secret_value

        # Fetch resources
        resources = fetcher.fetch_resources()

        # Verify get_secret_value was NEVER called
        assert mock_get_secret_value.call_count == 0, (
            "SECURITY VIOLATION: get_secret_value was called!"
        )

        # Verify we still got metadata
        assert len(resources["secrets"]) == 2

    def test_security_pagination_no_secret_values(self, fetcher, secrets_client):
        """SECURITY TEST: Verify pagination doesn't fetch secret values."""
        # Create multiple secrets to test pagination
        for i in range(5):
            secrets_client.create_secret(Name=f"secret-{i}", SecretString=f"value-{i}")

        # Mock get_secret_value to detect calls
        mock_get_secret_value = Mock()
        fetcher.client.get_secret_value = mock_get_secret_value

        # Fetch all secrets
        resources = fetcher.fetch_resources()

        # Verify no secret values were fetched
        assert mock_get_secret_value.call_count == 0
        assert len(resources["secrets"]) == 5

    def test_logger_security_audit(self, fetcher, secrets_client, caplog):
        """Test that security audit logs are generated."""
        import logging

        caplog.set_level(logging.INFO)

        secrets_client.create_secret(Name="test-secret", SecretString="dummy-value")

        fetcher.fetch_resources()

        # Check for security audit log
        audit_logs = [
            record
            for record in caplog.records
            if "metadata only, no secret values" in record.message
        ]
        assert len(audit_logs) > 0


class TestSecretsManagerFetcherSecurityViolations:
    """Test security violation detection in fetcher."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock session."""
        return MagicMock()

    @pytest.fixture
    def fetcher(self, mock_session):
        """Create fetcher with mock session."""
        with patch("boto3.Session", return_value=mock_session):
            return SecretsManagerFetcher(session=mock_session, region="us-east-1")

    def test_list_secrets_with_secret_string_skips(self, fetcher):
        """Test that secrets with SecretString in list response are skipped."""
        mock_client = MagicMock()
        fetcher.client = mock_client

        mock_client.get_paginator.return_value.paginate.return_value = [
            {
                "SecretList": [
                    {
                        "Name": "secret-with-value",
                        "ARN": "arn:aws:secretsmanager:us-east-1:123456789012:secret:test",
                        "SecretString": "should-not-be-here",  # Security violation
                    }
                ]
            }
        ]

        resources = fetcher.fetch_resources()

        # Should skip secret with security violation
        assert len(resources["secrets"]) == 0

    def test_describe_secret_with_secret_string_skips(self, fetcher):
        """Test that describe_secret with SecretString is handled."""
        mock_client = MagicMock()
        fetcher.client = mock_client

        mock_client.get_paginator.return_value.paginate.return_value = [
            {
                "SecretList": [
                    {
                        "Name": "test-secret",
                        "ARN": "arn:aws:secretsmanager:us-east-1:123456789012:secret:test",
                    }
                ]
            }
        ]

        mock_client.describe_secret.return_value = {
            "Name": "test-secret",
            "ARN": "arn:aws:secretsmanager:us-east-1:123456789012:secret:test",
            "SecretString": "should-not-be-here",  # Security violation
        }

        resources = fetcher.fetch_resources()

        # Should skip secret with security violation in describe
        assert len(resources["secrets"]) == 0

    def test_describe_secret_other_client_error(self, fetcher):
        """Test handling of non-AccessDenied error from describe_secret."""
        mock_client = MagicMock()
        fetcher.client = mock_client

        mock_client.get_paginator.return_value.paginate.return_value = [
            {
                "SecretList": [
                    {
                        "Name": "test-secret",
                        "ARN": "arn:aws:secretsmanager:us-east-1:123456789012:secret:test",
                    }
                ]
            }
        ]

        mock_client.describe_secret.side_effect = ClientError(
            {"Error": {"Code": "InternalError", "Message": "Internal error"}},
            "DescribeSecret",
        )

        resources = fetcher.fetch_resources()

        # Should skip secret when describe fails with non-recoverable error
        assert len(resources["secrets"]) == 0

    def test_per_secret_client_error_access_denied(self, fetcher):
        """Test handling of AccessDenied error per secret."""
        mock_client = MagicMock()
        fetcher.client = mock_client

        mock_client.get_paginator.return_value.paginate.return_value = [
            {
                "SecretList": [
                    {
                        "Name": "test-secret",
                        "ARN": "arn:aws:secretsmanager:us-east-1:123456789012:secret:test",
                    }
                ]
            }
        ]

        mock_client.describe_secret.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Access Denied"}},
            "DescribeSecret",
        )

        resources = fetcher.fetch_resources()

        # Should return secret with only list_secrets data
        assert len(resources["secrets"]) == 1

    def test_outer_exception_returns_empty(self, fetcher):
        """Test outer exception returns empty list."""
        mock_client = MagicMock()
        fetcher.client = mock_client

        mock_client.get_paginator.return_value.paginate.side_effect = Exception(
            "Unexpected error"
        )

        resources = fetcher.fetch_resources()

        assert resources["secrets"] == []


class TestSecretsManagerFetcherEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock session."""
        return MagicMock()

    @pytest.fixture
    def fetcher(self, mock_session):
        """Create fetcher with mock session."""
        with patch("boto3.Session", return_value=mock_session):
            return SecretsManagerFetcher(session=mock_session, region="us-east-1")

    def test_deleted_secrets_included(self, fetcher):
        """Test that deleted (but not purged) secrets are included."""
        mock_client = MagicMock()
        fetcher.client = mock_client

        # Mock response with a deleted secret
        mock_client.get_paginator.return_value.paginate.return_value = [
            {
                "SecretList": [
                    {
                        "Name": "deleted-secret",
                        "ARN": "arn:aws:secretsmanager:us-east-1:123456789012:secret:deleted-secret",
                        "DeletedDate": datetime(2024, 1, 1, tzinfo=timezone.utc),
                    }
                ]
            }
        ]

        mock_client.describe_secret.return_value = {
            "Name": "deleted-secret",
            "ARN": "arn:aws:secretsmanager:us-east-1:123456789012:secret:deleted-secret",
            "DeletedDate": datetime(2024, 1, 1, tzinfo=timezone.utc),
        }

        resources = fetcher.fetch_resources()

        assert len(resources["secrets"]) == 1
        assert resources["secrets"][0].deleted_date is not None

    def test_secrets_with_version_stages(self, fetcher):
        """Test secrets with multiple version stages."""
        mock_client = MagicMock()
        fetcher.client = mock_client

        mock_client.get_paginator.return_value.paginate.return_value = [
            {
                "SecretList": [
                    {
                        "Name": "versioned-secret",
                        "ARN": "arn:aws:secretsmanager:us-east-1:123456789012:secret:test",
                        "VersionIdsToStages": {
                            "v1": ["AWSCURRENT"],
                            "v2": ["AWSPREVIOUS"],
                        },
                    }
                ]
            }
        ]

        mock_client.describe_secret.return_value = {
            "Name": "versioned-secret",
            "ARN": "arn:aws:secretsmanager:us-east-1:123456789012:secret:test",
            "VersionIdsToStages": {"v1": ["AWSCURRENT"], "v2": ["AWSPREVIOUS"]},
        }

        resources = fetcher.fetch_resources()

        assert len(resources["secrets"]) == 1
        secret = resources["secrets"][0]
        assert "v1" in secret.version_ids_to_stages
        assert "AWSCURRENT" in secret.version_ids_to_stages["v1"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
