"""Tests for orchestration engine module."""
from unittest.mock import MagicMock, Mock, patch

import pytest
from botocore.exceptions import ClientError, NoCredentialsError, ProfileNotFound

from aws_comparator.core.config import AccountConfig, ComparisonConfig
from aws_comparator.core.exceptions import (
    AssumeRoleError,
    CredentialsNotFoundError,
    InvalidCredentialsError,
    ServiceNotSupportedError,
)
from aws_comparator.orchestration.engine import ComparisonOrchestrator


@pytest.fixture
def account1_config():
    """Create first account configuration."""
    return AccountConfig(
        account_id="123456789012",
        profile="test-profile-1",
        role_arn=None,
        external_id=None,
        session_name=None,
        region="us-east-1",
    )


@pytest.fixture
def account2_config():
    """Create second account configuration."""
    return AccountConfig(
        account_id="987654321098",
        profile="test-profile-2",
        role_arn=None,
        external_id=None,
        session_name=None,
        region="us-east-1",
    )


@pytest.fixture
def comparison_config(account1_config, account2_config):
    """Create comparison configuration."""
    return ComparisonConfig(
        account1=account1_config,
        account2=account2_config,
        services=["s3"],
        parallel_execution=False,
        max_workers=5,
        output_file=None,
    )


@pytest.fixture
def orchestrator(comparison_config):
    """Create an orchestrator instance."""
    return ComparisonOrchestrator(config=comparison_config)


class TestComparisonOrchestratorInit:
    """Tests for ComparisonOrchestrator initialization."""

    def test_init_with_config(self, comparison_config):
        """Test orchestrator initializes with config."""
        orchestrator = ComparisonOrchestrator(config=comparison_config)

        assert orchestrator.config == comparison_config
        assert orchestrator.progress_callback is None
        assert orchestrator._session1 is None
        assert orchestrator._session2 is None

    def test_init_with_progress_callback(self, comparison_config):
        """Test orchestrator initializes with progress callback."""
        callback = Mock()
        orchestrator = ComparisonOrchestrator(
            config=comparison_config, progress_callback=callback
        )

        assert orchestrator.progress_callback == callback


class TestCreateSession:
    """Tests for _create_session method."""

    @patch("aws_comparator.orchestration.engine.boto3.Session")
    def test_create_session_with_profile(
        self, mock_session_class, orchestrator, account1_config
    ):
        """Test creating session with profile."""
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        mock_sts = MagicMock()
        mock_session.client.return_value = mock_sts
        mock_sts.get_caller_identity.return_value = {"Account": "123456789012"}

        result = orchestrator._create_session(account1_config)

        mock_session_class.assert_called_with(
            profile_name="test-profile-1", region_name="us-east-1"
        )
        assert result == mock_session

    @patch("aws_comparator.orchestration.engine.boto3.Session")
    def test_create_session_without_profile(self, mock_session_class, orchestrator):
        """Test creating session without profile."""
        config = AccountConfig(
            account_id="123456789012",
            profile=None,
            role_arn=None,
            external_id=None,
            session_name=None,
            region="us-east-1",
        )
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        mock_sts = MagicMock()
        mock_session.client.return_value = mock_sts
        mock_sts.get_caller_identity.return_value = {"Account": "123456789012"}

        result = orchestrator._create_session(config)

        mock_session_class.assert_called_with(region_name="us-east-1")
        assert result == mock_session

    @patch("aws_comparator.orchestration.engine.boto3.Session")
    def test_create_session_profile_not_found(
        self, mock_session_class, orchestrator, account1_config
    ):
        """Test creating session with invalid profile raises error."""
        mock_session_class.side_effect = ProfileNotFound(profile="invalid")

        with pytest.raises(InvalidCredentialsError):
            orchestrator._create_session(account1_config)

    @patch("aws_comparator.orchestration.engine.boto3.Session")
    def test_create_session_no_credentials(
        self, mock_session_class, orchestrator, account1_config
    ):
        """Test creating session without credentials raises error."""
        mock_session_class.side_effect = NoCredentialsError()

        with pytest.raises(CredentialsNotFoundError):
            orchestrator._create_session(account1_config)


class TestAssumeRole:
    """Tests for _assume_role method."""

    def test_assume_role_success(self, orchestrator):
        """Test successful role assumption."""
        mock_session = MagicMock()
        mock_sts = MagicMock()
        mock_session.client.return_value = mock_sts
        mock_sts.assume_role.return_value = {
            "Credentials": {
                "AccessKeyId": "AKIA123",
                "SecretAccessKey": "secret",
                "SessionToken": "token",
            }
        }

        config = AccountConfig(
            account_id="123456789012",
            profile=None,
            role_arn="arn:aws:iam::123456789012:role/TestRole",
            external_id=None,
            session_name=None,
            region="us-east-1",
        )

        with patch("aws_comparator.orchestration.engine.boto3.Session"):
            orchestrator._assume_role(mock_session, config)

            mock_sts.assume_role.assert_called_once()
            call_kwargs = mock_sts.assume_role.call_args[1]
            assert call_kwargs["RoleArn"] == config.role_arn

    def test_assume_role_with_external_id(self, orchestrator):
        """Test role assumption with external ID."""
        mock_session = MagicMock()
        mock_sts = MagicMock()
        mock_session.client.return_value = mock_sts
        mock_sts.assume_role.return_value = {
            "Credentials": {
                "AccessKeyId": "AKIA123",
                "SecretAccessKey": "secret",
                "SessionToken": "token",
            }
        }

        config = AccountConfig(
            account_id="123456789012",
            profile=None,
            role_arn="arn:aws:iam::123456789012:role/TestRole",
            external_id="external-123",
            session_name=None,
            region="us-east-1",
        )

        with patch("aws_comparator.orchestration.engine.boto3.Session"):
            orchestrator._assume_role(mock_session, config)

            call_kwargs = mock_sts.assume_role.call_args[1]
            assert call_kwargs["ExternalId"] == "external-123"

    def test_assume_role_failure(self, orchestrator):
        """Test role assumption failure raises error."""
        mock_session = MagicMock()
        mock_sts = MagicMock()
        mock_session.client.return_value = mock_sts
        mock_sts.assume_role.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Access denied"}},
            "AssumeRole",
        )

        config = AccountConfig(
            account_id="123456789012",
            profile=None,
            role_arn="arn:aws:iam::123456789012:role/TestRole",
            external_id=None,
            session_name=None,
            region="us-east-1",
        )

        with pytest.raises(AssumeRoleError):
            orchestrator._assume_role(mock_session, config)


class TestValidateSession:
    """Tests for _validate_session method."""

    def test_validate_session_success(self, orchestrator):
        """Test successful session validation."""
        mock_session = MagicMock()
        mock_sts = MagicMock()
        mock_session.client.return_value = mock_sts
        mock_sts.get_caller_identity.return_value = {"Account": "123456789012"}

        # Should not raise
        orchestrator._validate_session(mock_session, "123456789012")

    def test_validate_session_account_mismatch(self, orchestrator):
        """Test session validation with account mismatch logs warning."""
        mock_session = MagicMock()
        mock_sts = MagicMock()
        mock_session.client.return_value = mock_sts
        mock_sts.get_caller_identity.return_value = {"Account": "111111111111"}

        # Should not raise, just log warning
        orchestrator._validate_session(mock_session, "123456789012")

    def test_validate_session_invalid_credentials(self, orchestrator):
        """Test session validation with invalid credentials raises error."""
        mock_session = MagicMock()
        mock_sts = MagicMock()
        mock_session.client.return_value = mock_sts
        mock_sts.get_caller_identity.side_effect = ClientError(
            {"Error": {"Code": "InvalidClientTokenId", "Message": "Invalid"}},
            "GetCallerIdentity",
        )

        with pytest.raises(InvalidCredentialsError):
            orchestrator._validate_session(mock_session, "123456789012")


class TestGetServicesToCompare:
    """Tests for _get_services_to_compare method."""

    @patch("aws_comparator.orchestration.engine.ServiceRegistry")
    def test_get_services_from_config(self, mock_registry, orchestrator):
        """Test getting services from config."""
        mock_registry.validate_services.return_value = (["s3"], [])
        mock_registry.list_services.return_value = ["s3", "ec2", "lambda"]

        result = orchestrator._get_services_to_compare()

        assert result == ["s3"]

    @patch("aws_comparator.orchestration.engine.ServiceRegistry")
    def test_get_all_services_when_none_specified(self, mock_registry):
        """Test getting all services when none specified in config."""
        mock_registry.list_services.return_value = ["s3", "ec2", "lambda"]

        config = ComparisonConfig(
            account1=AccountConfig(
                account_id="123456789012",
                profile=None,
                role_arn=None,
                external_id=None,
                session_name=None,
                region="us-east-1",
            ),
            account2=AccountConfig(
                account_id="987654321098",
                profile=None,
                role_arn=None,
                external_id=None,
                session_name=None,
                region="us-east-1",
            ),
            services=None,
            output_file=None,
        )
        orch = ComparisonOrchestrator(config=config)

        result = orch._get_services_to_compare()

        assert result == ["s3", "ec2", "lambda"]

    @patch("aws_comparator.orchestration.engine.ServiceRegistry")
    def test_get_services_filters_invalid(self, mock_registry, orchestrator):
        """Test invalid services are filtered out."""
        mock_registry.validate_services.return_value = (["s3"], ["invalid"])
        mock_registry.list_services.return_value = ["s3", "ec2"]

        result = orchestrator._get_services_to_compare()

        assert result == ["s3"]
        assert "invalid" not in result

    @patch("aws_comparator.orchestration.engine.ServiceRegistry")
    def test_get_services_raises_when_all_invalid(self, mock_registry, orchestrator):
        """Test raises error when all services are invalid."""
        mock_registry.validate_services.return_value = ([], ["invalid1", "invalid2"])

        with pytest.raises(ServiceNotSupportedError):
            orchestrator._get_services_to_compare()


class TestFetchServiceData:
    """Tests for _fetch_service_data method."""

    @patch("aws_comparator.orchestration.engine.ServiceRegistry")
    def test_fetch_service_data_success(self, mock_registry, orchestrator):
        """Test successful service data fetch."""
        mock_fetcher = MagicMock()
        mock_fetcher.fetch_resources.return_value = {"buckets": []}
        mock_registry.get_fetcher.return_value = mock_fetcher

        mock_session = MagicMock()
        name, resources, error = orchestrator._fetch_service_data(
            "s3", mock_session, "us-east-1"
        )

        assert name == "s3"
        assert resources == {"buckets": []}
        assert error is None

    @patch("aws_comparator.orchestration.engine.ServiceRegistry")
    def test_fetch_service_data_error(self, mock_registry, orchestrator):
        """Test service data fetch error handling."""
        mock_registry.get_fetcher.side_effect = Exception("Fetch failed")

        mock_session = MagicMock()
        name, resources, error = orchestrator._fetch_service_data(
            "s3", mock_session, "us-east-1"
        )

        assert name == "s3"
        assert resources == {}
        assert error is not None
        assert "Fetch failed" in error


class TestCompareService:
    """Tests for _compare_service method."""

    def test_compare_service_returns_result(self, orchestrator):
        """Test _compare_service returns ServiceComparisonResult."""
        account1_data: dict[str, list] = {"buckets": []}
        account2_data: dict[str, list] = {"buckets": []}

        result = orchestrator._compare_service("s3", account1_data, account2_data)

        assert result.service_name == "s3"
        assert hasattr(result, "resource_comparisons")
        assert hasattr(result, "execution_time_seconds")


class TestCalculateSummary:
    """Tests for _calculate_summary method."""

    def test_calculate_summary_empty(self, orchestrator):
        """Test calculating summary with no results."""
        summary = orchestrator._calculate_summary([], [], 1.0)

        assert summary.total_services_compared == 0
        assert summary.total_changes == 0
        assert summary.execution_time_seconds == 1.0

    def test_calculate_summary_with_errors(self, orchestrator):
        """Test calculating summary with errors."""
        from aws_comparator.models.comparison import ServiceError

        errors = [
            ServiceError(
                service_name="s3",
                error_type="TestError",
                error_message="Test error message",
                error_code=None,
                traceback=None,
            )
        ]

        summary = orchestrator._calculate_summary([], errors, 1.0)

        assert "s3" in summary.services_with_errors


class TestCompareAccounts:
    """Tests for compare_accounts method."""

    @patch.object(ComparisonOrchestrator, "_create_session")
    @patch.object(ComparisonOrchestrator, "_get_services_to_compare")
    @patch.object(ComparisonOrchestrator, "_compare_services_sequential")
    def test_compare_accounts_sequential(
        self,
        mock_compare_sequential,
        mock_get_services,
        mock_create_session,
        orchestrator,
    ):
        """Test compare_accounts with sequential execution."""
        from aws_comparator.models.comparison import ServiceComparisonResult

        mock_create_session.return_value = MagicMock()
        mock_get_services.return_value = ["s3"]
        mock_compare_sequential.return_value = (
            [
                ServiceComparisonResult(
                    service_name="s3",
                    resource_comparisons={},
                    execution_time_seconds=1.0,
                )
            ],
            [],
            ["s3"],
        )

        result = orchestrator.compare_accounts()

        assert result.account1_id == "123456789012"
        assert result.account2_id == "987654321098"
        assert "s3" in result.services_compared

    @patch.object(ComparisonOrchestrator, "_create_session")
    @patch.object(ComparisonOrchestrator, "_get_services_to_compare")
    @patch.object(ComparisonOrchestrator, "_compare_services_parallel")
    def test_compare_accounts_parallel(
        self,
        mock_compare_parallel,
        mock_get_services,
        mock_create_session,
    ):
        """Test compare_accounts with parallel execution."""
        from aws_comparator.models.comparison import ServiceComparisonResult

        config = ComparisonConfig(
            account1=AccountConfig(
                account_id="123456789012",
                profile=None,
                role_arn=None,
                external_id=None,
                session_name=None,
                region="us-east-1",
            ),
            account2=AccountConfig(
                account_id="987654321098",
                profile=None,
                role_arn=None,
                external_id=None,
                session_name=None,
                region="us-east-1",
            ),
            services=["s3"],
            parallel_execution=True,
            output_file=None,
        )
        orch = ComparisonOrchestrator(config=config)

        mock_create_session.return_value = MagicMock()
        mock_get_services.return_value = ["s3"]
        mock_compare_parallel.return_value = (
            [
                ServiceComparisonResult(
                    service_name="s3",
                    resource_comparisons={},
                    execution_time_seconds=1.0,
                )
            ],
            [],
            ["s3"],
        )

        result = orch.compare_accounts()

        mock_compare_parallel.assert_called_once()
        assert result.account1_id == "123456789012"


class TestProgressCallback:
    """Tests for progress callback functionality."""

    @patch.object(ComparisonOrchestrator, "_create_session")
    @patch.object(ComparisonOrchestrator, "_get_services_to_compare")
    @patch.object(ComparisonOrchestrator, "_fetch_service_data")
    @patch.object(ComparisonOrchestrator, "_compare_service")
    def test_progress_callback_called(
        self,
        mock_compare,
        mock_fetch,
        mock_get_services,
        mock_create_session,
        comparison_config,
    ):
        """Test progress callback is called during comparison."""
        from aws_comparator.models.comparison import ServiceComparisonResult

        callback = Mock()
        orch = ComparisonOrchestrator(
            config=comparison_config, progress_callback=callback
        )

        mock_create_session.return_value = MagicMock()
        mock_get_services.return_value = ["s3"]
        mock_fetch.return_value = ("s3", {}, None)
        mock_compare.return_value = ServiceComparisonResult(
            service_name="s3",
            resource_comparisons={},
            execution_time_seconds=1.0,
        )

        orch.compare_accounts()

        callback.assert_called()
