"""
Unit tests for Elastic Beanstalk service fetcher.

Tests the ElasticBeanstalkFetcher class using moto for AWS mocking.
"""

from datetime import datetime, timezone
from unittest.mock import patch

import boto3
import pytest
from moto import mock_aws

from aws_comparator.models.elasticbeanstalk import (
    Application,
    ApplicationVersion,
    ConfigurationTemplate,
    Environment,
)
from aws_comparator.services.elasticbeanstalk import ElasticBeanstalkFetcher


@pytest.fixture
def aws_credentials():
    """Mock AWS credentials for moto."""
    import os

    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"


@pytest.fixture
def eb_client(aws_credentials):
    """Create a mocked Elastic Beanstalk client."""
    with mock_aws():
        yield boto3.client("elasticbeanstalk", region_name="us-east-1")


@pytest.fixture
def session(aws_credentials):
    """Create a mocked boto3 session."""
    with mock_aws():
        yield boto3.Session(region_name="us-east-1")


@pytest.fixture
def fetcher(session):
    """Create an ElasticBeanstalkFetcher instance."""
    return ElasticBeanstalkFetcher(session=session, region="us-east-1")


class TestElasticBeanstalkFetcher:
    """Test cases for ElasticBeanstalkFetcher."""

    def test_service_name(self, fetcher):
        """Test that service name is correctly set."""
        assert fetcher.SERVICE_NAME == "elasticbeanstalk"

    def test_get_resource_types(self, fetcher):
        """Test get_resource_types returns correct resource types."""
        resource_types = fetcher.get_resource_types()
        assert "applications" in resource_types
        assert "environments" in resource_types
        assert "configuration_templates" in resource_types
        assert "application_versions" in resource_types
        assert len(resource_types) == 4

    def test_fetch_applications_empty(self, fetcher, eb_client):
        """Test fetching applications when none exist."""
        applications = fetcher._fetch_applications()
        assert isinstance(applications, list)
        assert len(applications) == 0

    def test_fetch_applications(self, fetcher, eb_client):
        """Test fetching applications."""
        # Create test application
        eb_client.create_application(
            ApplicationName="test-app", Description="Test application"
        )

        applications = fetcher._fetch_applications()

        assert len(applications) == 1
        assert isinstance(applications[0], Application)
        assert applications[0].application_name == "test-app"
        # Note: moto doesn't return Description field in describe_applications response
        # so we only verify the application was created and fetched correctly

    def test_fetch_multiple_applications(self, fetcher, eb_client):
        """Test fetching multiple applications."""
        # Create multiple applications
        for i in range(3):
            eb_client.create_application(
                ApplicationName=f"test-app-{i}", Description=f"Test application {i}"
            )

        applications = fetcher._fetch_applications()

        assert len(applications) == 3
        app_names = {app.application_name for app in applications}
        assert app_names == {"test-app-0", "test-app-1", "test-app-2"}

    def test_fetch_environments_empty(self, fetcher, eb_client):
        """Test fetching environments when none exist."""
        environments = fetcher._fetch_environments()
        assert isinstance(environments, list)
        assert len(environments) == 0

    def test_fetch_environments(self, fetcher, eb_client):
        """Test fetching environments."""
        # Create test application first
        eb_client.create_application(ApplicationName="test-app")

        # Create environment
        eb_client.create_environment(
            ApplicationName="test-app",
            EnvironmentName="test-env",
            SolutionStackName="64bit Amazon Linux 2 v5.0.0 running Python 3.8",
        )

        environments = fetcher._fetch_environments()

        assert len(environments) == 1
        assert isinstance(environments[0], Environment)
        assert environments[0].environment_name == "test-env"
        assert environments[0].application_name == "test-app"

    def test_fetch_configuration_templates_empty(self, fetcher, eb_client):
        """Test fetching configuration templates when none exist."""
        templates = fetcher._fetch_configuration_templates()
        assert isinstance(templates, list)
        assert len(templates) == 0

    @pytest.mark.skip(reason="moto does not implement create_configuration_template")
    def test_fetch_configuration_templates(self, fetcher, eb_client):
        """Test fetching configuration templates."""
        # Create test application
        eb_client.create_application(ApplicationName="test-app")

        # Create configuration template
        eb_client.create_configuration_template(
            ApplicationName="test-app",
            TemplateName="test-template",
            SolutionStackName="64bit Amazon Linux 2 v5.0.0 running Python 3.8",
        )

        templates = fetcher._fetch_configuration_templates()

        assert len(templates) == 1
        assert isinstance(templates[0], ConfigurationTemplate)
        assert templates[0].template_name == "test-template"
        assert templates[0].application_name == "test-app"

    def test_fetch_application_versions_empty(self, fetcher, eb_client):
        """Test fetching application versions when none exist."""
        versions = fetcher._fetch_application_versions()
        assert isinstance(versions, list)
        assert len(versions) == 0

    @pytest.mark.skip(reason="moto does not implement create_application_version")
    def test_fetch_application_versions(self, fetcher, eb_client):
        """Test fetching application versions."""
        # Create test application
        eb_client.create_application(ApplicationName="test-app")

        # Create application version
        eb_client.create_application_version(
            ApplicationName="test-app",
            VersionLabel="v1.0.0",
            Description="Version 1.0.0",
        )

        versions = fetcher._fetch_application_versions()

        assert len(versions) == 1
        assert isinstance(versions[0], ApplicationVersion)
        assert versions[0].version_label == "v1.0.0"
        assert versions[0].application_name == "test-app"
        assert versions[0].description == "Version 1.0.0"

    @pytest.mark.skip(
        reason="moto does not implement create_application_version and create_configuration_template"
    )
    def test_fetch_resources(self, fetcher, eb_client):
        """Test fetch_resources returns all resource types."""
        # Create test data
        eb_client.create_application(ApplicationName="test-app")
        eb_client.create_environment(
            ApplicationName="test-app",
            EnvironmentName="test-env",
            SolutionStackName="64bit Amazon Linux 2 v5.0.0 running Python 3.8",
        )
        eb_client.create_application_version(
            ApplicationName="test-app", VersionLabel="v1.0.0"
        )
        eb_client.create_configuration_template(
            ApplicationName="test-app",
            TemplateName="test-template",
            SolutionStackName="64bit Amazon Linux 2 v5.0.0 running Python 3.8",
        )

        resources = fetcher.fetch_resources()

        assert isinstance(resources, dict)
        assert "applications" in resources
        assert "environments" in resources
        assert "configuration_templates" in resources
        assert "application_versions" in resources

        assert len(resources["applications"]) == 1
        assert len(resources["environments"]) == 1
        assert len(resources["application_versions"]) == 1
        assert len(resources["configuration_templates"]) == 1

    def test_fetch_applications_error_handling(self, fetcher):
        """Test error handling when describe_applications fails."""
        with patch.object(fetcher.client, "describe_applications") as mock_describe:
            mock_describe.side_effect = Exception("API Error")

            applications = fetcher._fetch_applications()

            assert isinstance(applications, list)
            assert len(applications) == 0

    def test_fetch_environments_error_handling(self, fetcher):
        """Test error handling when describe_environments fails."""
        with patch.object(fetcher.client, "describe_environments") as mock_describe:
            mock_describe.side_effect = Exception("API Error")

            environments = fetcher._fetch_environments()

            assert isinstance(environments, list)
            assert len(environments) == 0

    def test_client_creation(self, fetcher):
        """Test that the Elastic Beanstalk client is created correctly."""
        assert fetcher.client is not None
        assert hasattr(fetcher.client, "describe_applications")
        assert hasattr(fetcher.client, "describe_environments")


class TestApplicationModel:
    """Test cases for Application model."""

    def test_from_aws_response(self):
        """Test creating Application from AWS response."""
        app_data = {
            "ApplicationName": "my-app",
            "ApplicationArn": "arn:aws:elasticbeanstalk:us-east-1:123456789012:application/my-app",
            "Description": "My application",
            "DateCreated": datetime(2024, 1, 1, tzinfo=timezone.utc),
            "DateUpdated": datetime(2024, 1, 2, tzinfo=timezone.utc),
            "Versions": ["v1.0.0", "v1.0.1"],
            "ConfigurationTemplates": ["template1"],
        }

        application = Application.from_aws_response(app_data)

        assert application.application_name == "my-app"
        assert application.description == "My application"
        assert len(application.versions) == 2
        assert len(application.configuration_templates) == 1

    def test_application_name_validation(self):
        """Test application name validation."""
        with pytest.raises(ValueError, match="Application name cannot be empty"):
            Application(
                application_name="",
                arn="arn:aws:elasticbeanstalk:us-east-1:123456789012:application/test",
            )  # type: ignore[call-arg]

        with pytest.raises(ValueError, match="must be 100 characters or less"):
            Application(
                application_name="a" * 101,
                arn="arn:aws:elasticbeanstalk:us-east-1:123456789012:application/test",
            )  # type: ignore[call-arg]


class TestEnvironmentModel:
    """Test cases for Environment model."""

    def test_from_aws_response(self):
        """Test creating Environment from AWS response."""
        env_data = {
            "EnvironmentName": "my-env",
            "EnvironmentId": "e-abc123",
            "ApplicationName": "my-app",
            "VersionLabel": "v1.0.0",
            "SolutionStackName": "64bit Amazon Linux 2 v5.0.0 running Python 3.8",
            "Status": "Ready",
            "Health": "Green",
            "DateCreated": datetime(2024, 1, 1, tzinfo=timezone.utc),
            "DateUpdated": datetime(2024, 1, 2, tzinfo=timezone.utc),
        }

        environment = Environment.from_aws_response(env_data)

        assert environment.environment_name == "my-env"
        assert environment.application_name == "my-app"
        assert environment.version_label == "v1.0.0"
        assert environment.status == "Ready"
        assert environment.health == "Green"

    def test_environment_name_validation(self):
        """Test environment name validation."""
        with pytest.raises(ValueError, match="Environment name cannot be empty"):
            Environment(environment_name="", application_name="test")  # type: ignore[call-arg]

        with pytest.raises(ValueError, match="must be 40 characters or less"):
            Environment(environment_name="a" * 41, application_name="test")  # type: ignore[call-arg]


class TestConfigurationTemplateModel:
    """Test cases for ConfigurationTemplate model."""

    def test_from_aws_response(self):
        """Test creating ConfigurationTemplate from AWS response."""
        config_data = {
            "TemplateName": "my-template",
            "ApplicationName": "my-app",
            "Description": "My template",
            "SolutionStackName": "64bit Amazon Linux 2 v5.0.0 running Python 3.8",
            "DateCreated": datetime(2024, 1, 1, tzinfo=timezone.utc),
            "DateUpdated": datetime(2024, 1, 2, tzinfo=timezone.utc),
            "OptionSettings": [
                {
                    "Namespace": "aws:autoscaling:launchconfiguration",
                    "OptionName": "InstanceType",
                    "Value": "t2.micro",
                }
            ],
        }

        template = ConfigurationTemplate.from_aws_response(config_data)

        assert template.template_name == "my-template"
        assert template.application_name == "my-app"
        assert template.description == "My template"
        assert len(template.option_settings) == 1
        assert template.option_settings[0].option_name == "InstanceType"


class TestApplicationVersionModel:
    """Test cases for ApplicationVersion model."""

    def test_from_aws_response(self):
        """Test creating ApplicationVersion from AWS response."""
        version_data = {
            "ApplicationName": "my-app",
            "VersionLabel": "v1.0.0",
            "Description": "Version 1.0.0",
            "DateCreated": datetime(2024, 1, 1, tzinfo=timezone.utc),
            "DateUpdated": datetime(2024, 1, 2, tzinfo=timezone.utc),
            "Status": "PROCESSED",
            "SourceBundle": {"S3Bucket": "my-bucket", "S3Key": "my-app/v1.0.0.zip"},
        }

        version = ApplicationVersion.from_aws_response(version_data)

        assert version.application_name == "my-app"
        assert version.version_label == "v1.0.0"
        assert version.description == "Version 1.0.0"
        assert version.status == "PROCESSED"
        assert version.source_bundle is not None


class TestElasticBeanstalkFetcherClientNone:
    """Tests for client is None paths."""

    def test_fetch_applications_client_none(self, session):
        """Test fetcher handles None client for applications."""
        fetcher = ElasticBeanstalkFetcher(session=session, region="us-east-1")
        fetcher.client = None

        applications = fetcher._fetch_applications()
        assert applications == []

    def test_fetch_environments_client_none(self, session):
        """Test fetcher handles None client for environments."""
        fetcher = ElasticBeanstalkFetcher(session=session, region="us-east-1")
        fetcher.client = None

        environments = fetcher._fetch_environments()
        assert environments == []

    def test_fetch_configuration_templates_client_none(self, session):
        """Test fetcher handles None client for configuration templates."""
        fetcher = ElasticBeanstalkFetcher(session=session, region="us-east-1")
        fetcher.client = None

        templates = fetcher._fetch_configuration_templates()
        assert templates == []

    def test_fetch_application_versions_client_none(self, session):
        """Test fetcher handles None client for application versions."""
        fetcher = ElasticBeanstalkFetcher(session=session, region="us-east-1")
        fetcher.client = None

        versions = fetcher._fetch_application_versions()
        assert versions == []

    def test_fetch_resources_has_all_keys(self, session):
        """Test fetch_resources returns dict with all expected keys."""
        fetcher = ElasticBeanstalkFetcher(session=session, region="us-east-1")

        resources = fetcher.fetch_resources()

        assert "applications" in resources
        assert "environments" in resources
        assert "configuration_templates" in resources
        assert "application_versions" in resources


class TestElasticBeanstalkFetcherErrorHandling:
    """Tests for error handling in ElasticBeanstalkFetcher."""

    def test_fetch_applications_client_error(self, session):
        """Test fetcher handles client errors for applications."""
        from unittest.mock import patch

        fetcher = ElasticBeanstalkFetcher(session=session, region="us-east-1")

        with patch.object(fetcher.client, "describe_applications") as mock_describe:
            from botocore.exceptions import ClientError

            mock_describe.side_effect = ClientError(
                {"Error": {"Code": "AccessDenied", "Message": "Access Denied"}},
                "DescribeApplications",
            )

            applications = fetcher._fetch_applications()

            assert applications == []

    def test_fetch_environments_client_error(self, session):
        """Test fetcher handles client errors for environments."""
        from unittest.mock import patch

        fetcher = ElasticBeanstalkFetcher(session=session, region="us-east-1")

        with patch.object(fetcher.client, "describe_environments") as mock_describe:
            from botocore.exceptions import ClientError

            mock_describe.side_effect = ClientError(
                {"Error": {"Code": "AccessDenied", "Message": "Access Denied"}},
                "DescribeEnvironments",
            )

            environments = fetcher._fetch_environments()

            assert environments == []

    def test_fetch_application_per_item_exception(self, session):
        """Test fetcher handles exception for individual application."""
        from unittest.mock import patch

        fetcher = ElasticBeanstalkFetcher(session=session, region="us-east-1")

        with patch.object(fetcher.client, "describe_applications") as mock_describe:
            mock_describe.return_value = {
                "Applications": [
                    {
                        "ApplicationName": "test-app",
                        # Missing required fields to trigger exception
                    }
                ]
            }

            applications = fetcher._fetch_applications()
            # Should handle the error gracefully
            assert isinstance(applications, list)

    def test_fetch_environments_per_item_exception(self, session):
        """Test fetcher handles exception for individual environment."""
        from unittest.mock import patch

        fetcher = ElasticBeanstalkFetcher(session=session, region="us-east-1")

        with patch.object(fetcher.client, "describe_environments") as mock_describe:
            mock_describe.return_value = {
                "Environments": [
                    {
                        "EnvironmentName": "test-env",
                        # Minimal data
                    }
                ]
            }

            environments = fetcher._fetch_environments()
            # Should handle gracefully
            assert isinstance(environments, list)

    def test_fetch_configuration_templates_with_templates(self, session):
        """Test fetching configuration templates."""
        from unittest.mock import patch

        fetcher = ElasticBeanstalkFetcher(session=session, region="us-east-1")

        with patch.object(fetcher.client, "describe_applications") as mock_apps:
            mock_apps.return_value = {
                "Applications": [
                    {
                        "ApplicationName": "test-app",
                        "ConfigurationTemplates": ["template1"],
                    }
                ]
            }

            with patch.object(
                fetcher.client, "describe_configuration_settings"
            ) as mock_settings:
                mock_settings.return_value = {
                    "ConfigurationSettings": [
                        {
                            "TemplateName": "template1",
                            "ApplicationName": "test-app",
                            "SolutionStackName": "64bit Amazon Linux",
                        }
                    ]
                }

                templates = fetcher._fetch_configuration_templates()

                assert len(templates) == 1

    def test_fetch_configuration_templates_error(self, session):
        """Test fetching templates handles errors."""
        from unittest.mock import patch

        fetcher = ElasticBeanstalkFetcher(session=session, region="us-east-1")

        with patch.object(fetcher.client, "describe_applications") as mock_apps:
            mock_apps.return_value = {
                "Applications": [
                    {
                        "ApplicationName": "test-app",
                        "ConfigurationTemplates": ["template1"],
                    }
                ]
            }

            with patch.object(
                fetcher.client, "describe_configuration_settings"
            ) as mock_settings:
                from botocore.exceptions import ClientError

                mock_settings.side_effect = ClientError(
                    {"Error": {"Code": "AccessDenied", "Message": "Denied"}},
                    "DescribeConfigurationSettings",
                )

                templates = fetcher._fetch_configuration_templates()

                # Should return empty list on error
                assert templates == []

    def test_fetch_application_versions_with_versions(self, session):
        """Test fetching application versions."""
        from unittest.mock import patch

        fetcher = ElasticBeanstalkFetcher(session=session, region="us-east-1")

        with patch.object(fetcher.client, "describe_applications") as mock_apps:
            mock_apps.return_value = {
                "Applications": [
                    {
                        "ApplicationName": "test-app",
                        "Versions": ["v1"],
                    }
                ]
            }

            with patch.object(
                fetcher.client, "describe_application_versions"
            ) as mock_versions:
                mock_versions.return_value = {
                    "ApplicationVersions": [
                        {
                            "ApplicationName": "test-app",
                            "VersionLabel": "v1",
                        }
                    ]
                }

                versions = fetcher._fetch_application_versions()

                assert len(versions) == 1

    def test_fetch_application_versions_error(self, session):
        """Test fetching versions handles errors."""
        from unittest.mock import patch

        fetcher = ElasticBeanstalkFetcher(session=session, region="us-east-1")

        with patch.object(fetcher.client, "describe_applications") as mock_apps:
            mock_apps.return_value = {
                "Applications": [
                    {
                        "ApplicationName": "test-app",
                        "Versions": ["v1"],
                    }
                ]
            }

            with patch.object(
                fetcher.client, "describe_application_versions"
            ) as mock_versions:
                from botocore.exceptions import ClientError

                mock_versions.side_effect = ClientError(
                    {"Error": {"Code": "AccessDenied", "Message": "Denied"}},
                    "DescribeApplicationVersions",
                )

                versions = fetcher._fetch_application_versions()

                # Should return empty list on error
                assert versions == []

    def test_fetch_configuration_templates_general_exception(self, session):
        """Test fetcher handles general exception for templates."""
        from unittest.mock import patch

        fetcher = ElasticBeanstalkFetcher(session=session, region="us-east-1")

        with patch.object(fetcher.client, "describe_applications") as mock_apps:
            mock_apps.side_effect = Exception("Unexpected error")

            templates = fetcher._fetch_configuration_templates()
            assert templates == []

    def test_fetch_application_versions_general_exception(self, session):
        """Test fetcher handles general exception for versions."""
        from unittest.mock import patch

        fetcher = ElasticBeanstalkFetcher(session=session, region="us-east-1")

        with patch.object(fetcher.client, "describe_applications") as mock_apps:
            mock_apps.side_effect = Exception("Unexpected error")

            versions = fetcher._fetch_application_versions()
            assert versions == []

    def test_fetch_configuration_templates_per_template_exception(self, session):
        """Test fetcher handles per-template exception."""
        from unittest.mock import patch

        fetcher = ElasticBeanstalkFetcher(session=session, region="us-east-1")

        with patch.object(fetcher.client, "describe_applications") as mock_apps:
            mock_apps.return_value = {
                "Applications": [
                    {
                        "ApplicationName": "test-app",
                        "ConfigurationTemplates": ["template1"],
                    }
                ]
            }

            with patch.object(
                fetcher.client, "describe_configuration_settings"
            ) as mock_settings:
                mock_settings.side_effect = Exception("Unexpected per-item error")

                templates = fetcher._fetch_configuration_templates()
                # Should return empty list when per-item error
                assert templates == []

    def test_fetch_application_versions_per_version_exception(self, session):
        """Test fetcher handles per-version exception."""
        from unittest.mock import patch

        fetcher = ElasticBeanstalkFetcher(session=session, region="us-east-1")

        with patch.object(fetcher.client, "describe_applications") as mock_apps:
            mock_apps.return_value = {
                "Applications": [
                    {
                        "ApplicationName": "test-app",
                        "Versions": ["v1"],
                    }
                ]
            }

            with patch.object(
                fetcher.client, "describe_application_versions"
            ) as mock_versions:
                mock_versions.side_effect = Exception("Unexpected error")

                versions = fetcher._fetch_application_versions()
                # Should return empty list when per-item error
                assert versions == []

    def test_fetch_application_versions_version_parsing_error(self, session):
        """Test fetcher handles version parsing errors."""
        from unittest.mock import patch

        fetcher = ElasticBeanstalkFetcher(session=session, region="us-east-1")

        with patch.object(fetcher.client, "describe_applications") as mock_apps:
            mock_apps.return_value = {
                "Applications": [
                    {
                        "ApplicationName": "test-app",
                        "Versions": ["v1"],
                    }
                ]
            }

            with patch.object(
                fetcher.client, "describe_application_versions"
            ) as mock_versions:
                mock_versions.return_value = {
                    "ApplicationVersions": [
                        {
                            "ApplicationName": "test-app",
                            # Missing VersionLabel to trigger parsing error
                        }
                    ]
                }

                versions = fetcher._fetch_application_versions()
                # Should continue and return what it can
                assert isinstance(versions, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
