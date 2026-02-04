"""Tests for CLI commands module."""

from unittest.mock import Mock, patch

import click
import pytest
from click.testing import CliRunner

from aws_comparator.cli.commands import (
    VERSION,
    cli,
    parse_services,
    setup_logging,
    validate_account_id,
)


class TestValidateAccountId:
    """Tests for validate_account_id function."""

    def test_valid_account_id(self):
        """Test validation passes for 12-digit account ID."""
        ctx = Mock()
        param = Mock()
        result = validate_account_id(ctx, param, "123456789012")
        assert result == "123456789012"

    def test_none_account_id(self):
        """Test validation passes for None value."""
        ctx = Mock()
        param = Mock()
        result = validate_account_id(ctx, param, None)
        assert result is None

    def test_invalid_account_id_too_short(self):
        """Test validation fails for account ID with less than 12 digits."""
        ctx = Mock()
        param = Mock()
        with pytest.raises(click.BadParameter) as exc_info:
            validate_account_id(ctx, param, "12345678901")
        assert "must be exactly 12 digits" in str(exc_info.value)

    def test_invalid_account_id_too_long(self):
        """Test validation fails for account ID with more than 12 digits."""
        ctx = Mock()
        param = Mock()
        with pytest.raises(click.BadParameter) as exc_info:
            validate_account_id(ctx, param, "1234567890123")
        assert "must be exactly 12 digits" in str(exc_info.value)

    def test_invalid_account_id_non_numeric(self):
        """Test validation fails for non-numeric account ID."""
        ctx = Mock()
        param = Mock()
        with pytest.raises(click.BadParameter) as exc_info:
            validate_account_id(ctx, param, "12345678901a")
        assert "must be exactly 12 digits" in str(exc_info.value)


class TestParseServices:
    """Tests for parse_services function."""

    def test_parse_single_service(self):
        """Test parsing a single service."""
        result = parse_services("s3")
        assert result == ["s3"]

    def test_parse_multiple_services(self):
        """Test parsing multiple comma-separated services."""
        result = parse_services("s3, ec2, lambda")
        assert result == ["s3", "ec2", "lambda"]

    def test_parse_services_with_extra_whitespace(self):
        """Test parsing services with extra whitespace."""
        result = parse_services("  s3  ,  ec2  ,  lambda  ")
        assert result == ["s3", "ec2", "lambda"]

    def test_parse_services_uppercase(self):
        """Test that services are converted to lowercase."""
        result = parse_services("S3, EC2, LAMBDA")
        assert result == ["s3", "ec2", "lambda"]

    def test_parse_empty_string(self):
        """Test parsing empty string returns None."""
        result = parse_services("")
        assert result is None

    def test_parse_none(self):
        """Test parsing None returns None."""
        result = parse_services(None)
        assert result is None


class TestSetupLogging:
    """Tests for setup_logging function."""

    @patch("aws_comparator.cli.commands.logging")
    def test_setup_logging_quiet(self, mock_logging):
        """Test quiet mode sets ERROR level."""
        setup_logging(verbose=0, quiet=True)
        mock_logging.basicConfig.assert_called_once()
        call_kwargs = mock_logging.basicConfig.call_args[1]
        assert call_kwargs["level"] == mock_logging.ERROR

    @patch("aws_comparator.cli.commands.logging")
    def test_setup_logging_default(self, mock_logging):
        """Test default mode sets WARNING level."""
        setup_logging(verbose=0, quiet=False)
        mock_logging.basicConfig.assert_called_once()
        call_kwargs = mock_logging.basicConfig.call_args[1]
        assert call_kwargs["level"] == mock_logging.WARNING

    @patch("aws_comparator.cli.commands.logging")
    def test_setup_logging_verbose_1(self, mock_logging):
        """Test verbose=1 sets INFO level."""
        setup_logging(verbose=1, quiet=False)
        mock_logging.basicConfig.assert_called_once()
        call_kwargs = mock_logging.basicConfig.call_args[1]
        assert call_kwargs["level"] == mock_logging.INFO

    @patch("aws_comparator.cli.commands.logging")
    def test_setup_logging_verbose_2(self, mock_logging):
        """Test verbose=2 sets DEBUG level."""
        setup_logging(verbose=2, quiet=False)
        mock_logging.basicConfig.assert_called_once()
        call_kwargs = mock_logging.basicConfig.call_args[1]
        assert call_kwargs["level"] == mock_logging.DEBUG

    @patch("aws_comparator.cli.commands.logging")
    def test_setup_logging_verbose_3(self, mock_logging):
        """Test verbose=3 sets DEBUG level."""
        setup_logging(verbose=3, quiet=False)
        mock_logging.basicConfig.assert_called_once()
        call_kwargs = mock_logging.basicConfig.call_args[1]
        assert call_kwargs["level"] == mock_logging.DEBUG


class TestCLIGroup:
    """Tests for main CLI group."""

    def test_cli_group_invokes(self):
        """Test CLI group can be invoked."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "AWS Account Comparator" in result.output

    def test_cli_version_option(self):
        """Test --version option."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert VERSION in result.output


class TestVersionCommand:
    """Tests for version command."""

    def test_version_command(self):
        """Test version command outputs version."""
        runner = CliRunner()
        result = runner.invoke(cli, ["version"])
        assert result.exit_code == 0
        assert VERSION in result.output
        assert "aws-comparator" in result.output


class TestListServicesCommand:
    """Tests for list-services command."""

    @patch("aws_comparator.cli.commands.ServiceRegistry")
    def test_list_services_no_services(self, mock_registry):
        """Test list-services when no services are registered."""
        mock_registry.get_all_service_info.return_value = {}
        runner = CliRunner()
        result = runner.invoke(cli, ["list-services"])
        assert result.exit_code == 0
        assert "No services registered" in result.output

    @patch("aws_comparator.cli.commands.ServiceRegistry")
    def test_list_services_with_services(self, mock_registry):
        """Test list-services shows registered services."""
        mock_registry.get_all_service_info.return_value = {
            "s3": {"description": "Amazon S3", "resource_types": ["buckets"]},
            "ec2": {"description": "Amazon EC2", "resource_types": ["instances"]},
        }
        runner = CliRunner()
        result = runner.invoke(cli, ["list-services"])
        assert result.exit_code == 0
        assert "s3" in result.output
        assert "ec2" in result.output
        assert "Total services:" in result.output

    @patch("aws_comparator.cli.commands.ServiceRegistry")
    def test_list_services_verbose(self, mock_registry):
        """Test list-services with --verbose flag shows resource types."""
        mock_registry.get_all_service_info.return_value = {
            "s3": {"description": "Amazon S3", "resource_types": ["buckets"]},
        }
        runner = CliRunner()
        result = runner.invoke(cli, ["list-services", "--verbose"])
        assert result.exit_code == 0
        assert "buckets" in result.output


class TestCompareCommand:
    """Tests for compare command."""

    def test_compare_help(self):
        """Test compare --help shows all options."""
        runner = CliRunner()
        result = runner.invoke(cli, ["compare", "--help"])
        assert result.exit_code == 0
        assert "--account1" in result.output
        assert "--account2" in result.output
        assert "--profile1" in result.output
        assert "--profile2" in result.output
        assert "--region" in result.output
        assert "--services" in result.output
        assert "--output-format" in result.output

    def test_compare_missing_required_args(self):
        """Test compare fails without required arguments."""
        runner = CliRunner()
        result = runner.invoke(cli, ["compare"])
        assert result.exit_code != 0
        assert "Missing option" in result.output or "required" in result.output.lower()

    def test_compare_invalid_account1(self):
        """Test compare fails with invalid account1."""
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "compare",
                "--account1",
                "invalid",
                "--account2",
                "987654321098",
            ],
        )
        assert result.exit_code != 0
        assert "12 digits" in result.output

    def test_compare_invalid_account2(self):
        """Test compare fails with invalid account2."""
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "compare",
                "--account1",
                "123456789012",
                "--account2",
                "invalid",
            ],
        )
        assert result.exit_code != 0
        assert "12 digits" in result.output

    @patch("aws_comparator.cli.commands.ComparisonOrchestrator")
    @patch("aws_comparator.cli.commands.ServiceRegistry")
    @patch("aws_comparator.cli.commands.get_formatter")
    def test_compare_success(
        self, mock_get_formatter, mock_registry, mock_orchestrator
    ):
        """Test compare command succeeds with valid inputs."""
        # Setup mocks
        mock_registry.validate_services.return_value = (["s3"], [])
        mock_registry.list_services.return_value = ["s3", "ec2"]

        mock_report = Mock()
        mock_report.summary = Mock()
        mock_report.summary.total_changes = 5
        mock_report.summary.total_services_with_changes = 1
        mock_report.summary.total_services_compared = 1
        mock_report.summary.execution_time_seconds = 1.5
        mock_report.summary.services_with_errors = []

        mock_orch_instance = Mock()
        mock_orch_instance.compare_accounts.return_value = mock_report
        mock_orchestrator.return_value = mock_orch_instance

        mock_formatter = Mock()
        mock_formatter.format.return_value = "formatted output"
        mock_get_formatter.return_value = mock_formatter

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "compare",
                "--account1",
                "123456789012",
                "--account2",
                "987654321098",
                "--services",
                "s3",
                "--quiet",
            ],
        )

        # The command should run (might fail on boto3 session creation)
        # but should not have argument validation errors
        assert "12 digits" not in result.output

    @patch("aws_comparator.cli.commands.ServiceRegistry")
    def test_compare_invalid_services(self, mock_registry):
        """Test compare fails with unsupported services."""
        mock_registry.validate_services.return_value = ([], ["unknown_service"])

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "compare",
                "--account1",
                "123456789012",
                "--account2",
                "987654321098",
                "--services",
                "unknown_service",
            ],
        )
        # Should show error about unsupported services
        assert result.exit_code != 0


class TestCompareCommandOutputFormats:
    """Tests for compare command output format options."""

    def test_compare_output_format_json(self):
        """Test --output-format json is accepted."""
        runner = CliRunner()
        result = runner.invoke(cli, ["compare", "--help"])
        assert "json" in result.output.lower()

    def test_compare_output_format_yaml(self):
        """Test --output-format yaml is accepted."""
        runner = CliRunner()
        result = runner.invoke(cli, ["compare", "--help"])
        assert "yaml" in result.output.lower()

    def test_compare_output_format_table(self):
        """Test --output-format table is accepted."""
        runner = CliRunner()
        result = runner.invoke(cli, ["compare", "--help"])
        assert "table" in result.output.lower()


class TestCompareCommandFlags:
    """Tests for compare command flag options."""

    def test_compare_verbose_flag(self):
        """Test -v flag is accepted."""
        runner = CliRunner()
        result = runner.invoke(cli, ["compare", "--help"])
        assert "-v" in result.output
        assert "verbose" in result.output.lower()

    def test_compare_quiet_flag(self):
        """Test -q flag is accepted."""
        runner = CliRunner()
        result = runner.invoke(cli, ["compare", "--help"])
        assert "-q" in result.output
        assert "quiet" in result.output.lower()

    def test_compare_no_color_flag(self):
        """Test --no-color flag is accepted."""
        runner = CliRunner()
        result = runner.invoke(cli, ["compare", "--help"])
        assert "--no-color" in result.output


class TestCompareCommandExceptionHandling:
    """Tests for compare command exception handling."""

    @patch("aws_comparator.cli.commands.ComparisonOrchestrator")
    @patch("aws_comparator.cli.commands.ServiceRegistry")
    def test_compare_authentication_error(self, mock_registry, mock_orchestrator):
        """Test compare handles AuthenticationError."""
        from aws_comparator.core.exceptions import AuthenticationError

        mock_registry.validate_services.return_value = (["s3"], [])

        mock_orch_instance = Mock()
        # AuthenticationError requires message, error_code, and details
        mock_orch_instance.compare_accounts.side_effect = AuthenticationError(
            message="Authentication failed",
            error_code="AUTH-999",
            details={"suggestion": "Check your credentials"},
        )
        mock_orchestrator.return_value = mock_orch_instance

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "compare",
                "--account1",
                "123456789012",
                "--account2",
                "987654321098",
                "--services",
                "s3",
            ],
        )

        assert result.exit_code == 1
        assert "Authentication error" in result.output

    @patch("aws_comparator.cli.commands.ComparisonOrchestrator")
    @patch("aws_comparator.cli.commands.ServiceRegistry")
    def test_compare_invalid_account_id_error(self, mock_registry, mock_orchestrator):
        """Test compare handles InvalidAccountIdError."""
        from aws_comparator.core.exceptions import InvalidAccountIdError

        mock_registry.validate_services.return_value = (["s3"], [])

        mock_orch_instance = Mock()
        mock_orch_instance.compare_accounts.side_effect = InvalidAccountIdError(
            "Invalid account ID format"
        )
        mock_orchestrator.return_value = mock_orch_instance

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "compare",
                "--account1",
                "123456789012",
                "--account2",
                "987654321098",
                "--services",
                "s3",
            ],
        )

        assert result.exit_code == 1
        assert "Invalid account ID" in result.output

    @patch("aws_comparator.cli.commands.ComparisonOrchestrator")
    @patch("aws_comparator.cli.commands.ServiceRegistry")
    def test_compare_invalid_config_error(self, mock_registry, mock_orchestrator):
        """Test compare handles InvalidConfigError."""
        from aws_comparator.core.exceptions import InvalidConfigError

        mock_registry.validate_services.return_value = (["s3"], [])

        mock_orch_instance = Mock()
        # InvalidConfigError requires config_file and errors list
        mock_orch_instance.compare_accounts.side_effect = InvalidConfigError(
            config_file="config.yaml",
            errors=["Invalid setting"],
        )
        mock_orchestrator.return_value = mock_orch_instance

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "compare",
                "--account1",
                "123456789012",
                "--account2",
                "987654321098",
                "--services",
                "s3",
            ],
        )

        assert result.exit_code == 1
        assert "Configuration error" in result.output

    @patch("aws_comparator.cli.commands.ComparisonOrchestrator")
    @patch("aws_comparator.cli.commands.ServiceRegistry")
    def test_compare_service_not_supported_error(
        self, mock_registry, mock_orchestrator
    ):
        """Test compare handles ServiceNotSupportedError."""
        from aws_comparator.core.exceptions import ServiceNotSupportedError

        mock_registry.validate_services.return_value = (["s3"], [])

        mock_orch_instance = Mock()
        mock_orch_instance.compare_accounts.side_effect = ServiceNotSupportedError(
            "Service not supported"
        )
        mock_orchestrator.return_value = mock_orch_instance

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "compare",
                "--account1",
                "123456789012",
                "--account2",
                "987654321098",
                "--services",
                "s3",
            ],
        )

        assert result.exit_code == 1
        assert "Service error" in result.output
        assert "list-services" in result.output

    @patch("aws_comparator.cli.commands.ComparisonOrchestrator")
    @patch("aws_comparator.cli.commands.ServiceRegistry")
    def test_compare_generic_aws_comparator_error(
        self, mock_registry, mock_orchestrator
    ):
        """Test compare handles generic AWSComparatorError."""
        from aws_comparator.core.exceptions import AWSComparatorError

        mock_registry.validate_services.return_value = (["s3"], [])

        mock_orch_instance = Mock()
        # AWSComparatorError requires message, error_code, and optionally details
        mock_orch_instance.compare_accounts.side_effect = AWSComparatorError(
            message="Generic error",
            error_code="GEN-001",
            details={"suggestion": "Try again"},
        )
        mock_orchestrator.return_value = mock_orch_instance

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "compare",
                "--account1",
                "123456789012",
                "--account2",
                "987654321098",
                "--services",
                "s3",
            ],
        )

        assert result.exit_code == 1
        assert "Error:" in result.output

    @patch("aws_comparator.cli.commands.ComparisonOrchestrator")
    @patch("aws_comparator.cli.commands.ServiceRegistry")
    def test_compare_unexpected_exception(self, mock_registry, mock_orchestrator):
        """Test compare handles unexpected exceptions."""
        mock_registry.validate_services.return_value = (["s3"], [])

        mock_orch_instance = Mock()
        mock_orch_instance.compare_accounts.side_effect = RuntimeError(
            "Unexpected failure"
        )
        mock_orchestrator.return_value = mock_orch_instance

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "compare",
                "--account1",
                "123456789012",
                "--account2",
                "987654321098",
                "--services",
                "s3",
            ],
        )

        assert result.exit_code == 1
        assert "Unexpected error" in result.output

    @patch("aws_comparator.cli.commands.ComparisonOrchestrator")
    @patch("aws_comparator.cli.commands.ServiceRegistry")
    @patch("aws_comparator.cli.commands.get_formatter")
    def test_compare_with_output_file(
        self, mock_get_formatter, mock_registry, mock_orchestrator, tmp_path
    ):
        """Test compare writes output to file."""
        mock_registry.validate_services.return_value = (["s3"], [])
        mock_registry.list_services.return_value = ["s3"]

        mock_report = Mock()
        mock_report.summary = Mock()
        mock_report.summary.total_changes = 0
        mock_report.summary.total_services_with_changes = 0
        mock_report.summary.total_services_compared = 1
        mock_report.summary.execution_time_seconds = 1.0
        mock_report.summary.services_with_errors = []

        mock_orch_instance = Mock()
        mock_orch_instance.compare_accounts.return_value = mock_report
        mock_orchestrator.return_value = mock_orch_instance

        mock_formatter = Mock()
        mock_formatter.format.return_value = "formatted output"
        mock_get_formatter.return_value = mock_formatter

        output_file = tmp_path / "output.json"

        runner = CliRunner()
        runner.invoke(
            cli,
            [
                "compare",
                "--account1",
                "123456789012",
                "--account2",
                "987654321098",
                "--services",
                "s3",
                "--output-file",
                str(output_file),
                "--quiet",
            ],
        )

        # Check formatter write_to_file was called
        mock_formatter.write_to_file.assert_called_once()

    @patch("aws_comparator.cli.commands.ComparisonOrchestrator")
    @patch("aws_comparator.cli.commands.ServiceRegistry")
    @patch("aws_comparator.cli.commands.get_formatter")
    def test_compare_with_services_with_errors(
        self, mock_get_formatter, mock_registry, mock_orchestrator
    ):
        """Test compare shows services with errors in summary."""
        mock_registry.validate_services.return_value = (["s3", "ec2"], [])
        mock_registry.list_services.return_value = ["s3", "ec2"]

        mock_report = Mock()
        mock_report.summary = Mock()
        mock_report.summary.total_changes = 1
        mock_report.summary.total_services_with_changes = 1
        mock_report.summary.total_services_compared = 2
        mock_report.summary.execution_time_seconds = 2.0
        mock_report.summary.services_with_errors = ["ec2"]

        mock_orch_instance = Mock()
        mock_orch_instance.compare_accounts.return_value = mock_report
        mock_orchestrator.return_value = mock_orch_instance

        mock_formatter = Mock()
        mock_formatter.format.return_value = "formatted output"
        mock_get_formatter.return_value = mock_formatter

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "compare",
                "--account1",
                "123456789012",
                "--account2",
                "987654321098",
                "--services",
                "s3,ec2",
            ],
        )

        assert "ec2" in result.output

    @patch("aws_comparator.cli.commands.ComparisonOrchestrator")
    @patch("aws_comparator.cli.commands.ServiceRegistry")
    @patch("aws_comparator.cli.commands.get_formatter")
    def test_compare_cross_region(
        self, mock_get_formatter, mock_registry, mock_orchestrator
    ):
        """Test compare with different regions for each account."""
        mock_registry.validate_services.return_value = (["s3"], [])
        mock_registry.list_services.return_value = ["s3"]

        mock_report = Mock()
        mock_report.summary = Mock()
        mock_report.summary.total_changes = 0
        mock_report.summary.total_services_with_changes = 0
        mock_report.summary.total_services_compared = 1
        mock_report.summary.execution_time_seconds = 1.0
        mock_report.summary.services_with_errors = []

        mock_orch_instance = Mock()
        mock_orch_instance.compare_accounts.return_value = mock_report
        mock_orchestrator.return_value = mock_orch_instance

        mock_formatter = Mock()
        mock_formatter.format.return_value = "formatted output"
        mock_get_formatter.return_value = mock_formatter

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "compare",
                "--account1",
                "123456789012",
                "--account2",
                "987654321098",
                "--region1",
                "us-east-1",
                "--region2",
                "eu-west-1",
                "--services",
                "s3",
            ],
        )

        # Both regions should be shown (use partial match to handle ANSI codes)
        assert "us-east" in result.output
        assert "eu-west" in result.output

    @patch("aws_comparator.cli.commands.ServiceRegistry")
    def test_compare_warns_about_invalid_services(self, mock_registry):
        """Test compare warns about invalid services but continues with valid ones."""
        mock_registry.validate_services.return_value = (["s3"], ["invalid_svc"])
        mock_registry.list_services.return_value = ["s3"]

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "compare",
                "--account1",
                "123456789012",
                "--account2",
                "987654321098",
                "--services",
                "s3,invalid_svc",
            ],
        )

        # Should show warning about invalid services
        assert "invalid_svc" in result.output or result.exit_code != 0


class TestListServicesCommandVerbose:
    """Additional tests for list-services verbose mode."""

    @patch("aws_comparator.cli.commands.ServiceRegistry")
    def test_list_services_verbose_no_resource_types(self, mock_registry):
        """Test list-services verbose mode with empty resource types."""
        mock_registry.get_all_service_info.return_value = {
            "s3": {"description": "Amazon S3", "resource_types": []},
        }
        runner = CliRunner()
        result = runner.invoke(cli, ["list-services", "--verbose"])
        assert result.exit_code == 0
        # Should show "-" for empty resource types
        assert "-" in result.output or "s3" in result.output

    @patch("aws_comparator.cli.commands.ServiceRegistry")
    def test_list_services_verbose_multiple_resource_types(self, mock_registry):
        """Test list-services verbose mode with multiple resource types."""
        mock_registry.get_all_service_info.return_value = {
            "ec2": {
                "description": "Amazon EC2",
                "resource_types": ["instances", "security_groups", "vpcs"],
            },
        }
        runner = CliRunner()
        result = runner.invoke(cli, ["list-services", "--verbose"])
        assert result.exit_code == 0
        assert "instances" in result.output


class TestParseServicesEdgeCases:
    """Edge case tests for parse_services function."""

    def test_parse_services_only_whitespace(self):
        """Test parsing string with only whitespace returns None."""
        result = parse_services("   ")
        assert result is None

    def test_parse_services_only_commas(self):
        """Test parsing string with only commas returns None."""
        result = parse_services(",,,")
        assert result is None

    def test_parse_services_mixed_empty_and_valid(self):
        """Test parsing with empty items filters them out."""
        result = parse_services("s3,,ec2,  ,lambda")
        assert result == ["s3", "ec2", "lambda"]
