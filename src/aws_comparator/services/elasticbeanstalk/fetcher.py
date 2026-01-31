"""
AWS Elastic Beanstalk service fetcher.

This module implements fetching of Elastic Beanstalk application, environment,
configuration template, and application version resources.
"""

from typing import Any

from botocore.exceptions import ClientError

from aws_comparator.core.registry import ServiceRegistry
from aws_comparator.models.common import AWSResource
from aws_comparator.models.elasticbeanstalk import (
    Application,
    ApplicationVersion,
    ConfigurationTemplate,
    Environment,
)
from aws_comparator.services.base import BaseServiceFetcher


@ServiceRegistry.register(
    'elasticbeanstalk',
    description='AWS Elastic Beanstalk',
    resource_types=['applications', 'environments', 'configuration_templates', 'application_versions']
)
class ElasticBeanstalkFetcher(BaseServiceFetcher):
    """
    Fetcher for AWS Elastic Beanstalk resources.

    This fetcher retrieves Elastic Beanstalk information including:
    - Applications (logical collections of components)
    - Environments (deployed versions on AWS resources)
    - Configuration templates (saved configurations)
    - Application versions (specific iterations of deployable code)
    """

    SERVICE_NAME = "elasticbeanstalk"

    def _create_client(self) -> Any:
        """
        Create boto3 Elastic Beanstalk client.

        Returns:
            Configured boto3 Elastic Beanstalk client
        """
        return self.session.client('elasticbeanstalk', region_name=self.region)

    def fetch_resources(self) -> dict[str, list[AWSResource]]:
        """
        Fetch all Elastic Beanstalk resources.

        Returns:
            Dictionary mapping resource types to lists of resources
        """
        return {
            'applications': self._safe_fetch('applications', self._fetch_applications),
            'environments': self._safe_fetch('environments', self._fetch_environments),
            'configuration_templates': self._safe_fetch(
                'configuration_templates',
                self._fetch_configuration_templates
            ),
            'application_versions': self._safe_fetch(
                'application_versions',
                self._fetch_application_versions
            ),
        }

    def get_resource_types(self) -> list[str]:
        """
        Get list of resource types handled by this fetcher.

        Returns:
            List of resource type names
        """
        return ['applications', 'environments', 'configuration_templates', 'application_versions']

    def _fetch_applications(self) -> list[Application]:
        """
        Fetch all Elastic Beanstalk applications.

        Returns:
            List of Application resources
        """
        applications: list[Application] = []

        try:
            # Describe all applications
            response = self.client.describe_applications()
            app_list = response.get('Applications', [])

            self.logger.info(f"Found {len(app_list)} Elastic Beanstalk applications")

            for app_data in app_list:
                try:
                    # Create Application instance
                    application = Application.from_aws_response(app_data)
                    applications.append(application)

                    app_name = app_data.get('ApplicationName', 'unknown')
                    self.logger.debug(f"Fetched application: {app_name}")

                except ClientError as e:
                    error_code = e.response.get('Error', {}).get('Code', '')
                    app_name = app_data.get('ApplicationName', 'unknown')
                    if error_code in ['AccessDenied', 'ResourceNotFoundException']:
                        self.logger.warning(
                            f"Cannot access application {app_name}: {error_code}"
                        )
                    else:
                        self.logger.error(
                            f"Error fetching application {app_name}: {e}",
                            exc_info=True
                        )
                except Exception as e:
                    app_name = app_data.get('ApplicationName', 'unknown')
                    self.logger.error(
                        f"Unexpected error processing application {app_name}: {e}",
                        exc_info=True
                    )

        except Exception as e:
            self.logger.error(
                f"Failed to list Elastic Beanstalk applications: {e}",
                exc_info=True
            )

        return applications

    def _fetch_environments(self) -> list[Environment]:
        """
        Fetch all Elastic Beanstalk environments.

        Returns:
            List of Environment resources
        """
        environments: list[Environment] = []

        try:
            # Describe all environments (across all applications)
            response = self.client.describe_environments(IncludeDeleted=False)
            env_list = response.get('Environments', [])

            self.logger.info(f"Found {len(env_list)} Elastic Beanstalk environments")

            for env_data in env_list:
                try:
                    # Create Environment instance
                    environment = Environment.from_aws_response(env_data)
                    environments.append(environment)

                    env_name = env_data.get('EnvironmentName', 'unknown')
                    self.logger.debug(f"Fetched environment: {env_name}")

                except ClientError as e:
                    error_code = e.response.get('Error', {}).get('Code', '')
                    env_name = env_data.get('EnvironmentName', 'unknown')
                    if error_code in ['AccessDenied', 'ResourceNotFoundException']:
                        self.logger.warning(
                            f"Cannot access environment {env_name}: {error_code}"
                        )
                    else:
                        self.logger.error(
                            f"Error fetching environment {env_name}: {e}",
                            exc_info=True
                        )
                except Exception as e:
                    env_name = env_data.get('EnvironmentName', 'unknown')
                    self.logger.error(
                        f"Unexpected error processing environment {env_name}: {e}",
                        exc_info=True
                    )

        except Exception as e:
            self.logger.error(
                f"Failed to list Elastic Beanstalk environments: {e}",
                exc_info=True
            )

        return environments

    def _fetch_configuration_templates(self) -> list[ConfigurationTemplate]:
        """
        Fetch all Elastic Beanstalk configuration templates.

        Configuration templates are fetched per application, so we first need
        to get all applications and then query their templates.

        Returns:
            List of ConfigurationTemplate resources
        """
        templates: list[ConfigurationTemplate] = []

        try:
            # First, get all applications
            response = self.client.describe_applications()
            app_list = response.get('Applications', [])

            for app_data in app_list:
                app_name = app_data.get('ApplicationName')
                template_names = app_data.get('ConfigurationTemplates', [])

                if not template_names:
                    continue

                # Fetch configuration settings for each template
                for template_name in template_names:
                    try:
                        config_response = self.client.describe_configuration_settings(
                            ApplicationName=app_name,
                            TemplateName=template_name
                        )

                        config_settings = config_response.get('ConfigurationSettings', [])
                        if config_settings:
                            # Usually returns one configuration setting
                            config_data = config_settings[0]
                            template = ConfigurationTemplate.from_aws_response(config_data)
                            templates.append(template)

                            self.logger.debug(
                                f"Fetched configuration template: {template_name} "
                                f"for application {app_name}"
                            )

                    except ClientError as e:
                        error_code = e.response.get('Error', {}).get('Code', '')
                        if error_code in ['AccessDenied', 'ResourceNotFoundException']:
                            self.logger.warning(
                                f"Cannot access template {template_name} "
                                f"for application {app_name}: {error_code}"
                            )
                        else:
                            self.logger.error(
                                f"Error fetching template {template_name} "
                                f"for application {app_name}: {e}",
                                exc_info=True
                            )
                    except Exception as e:
                        self.logger.error(
                            f"Unexpected error processing template {template_name} "
                            f"for application {app_name}: {e}",
                            exc_info=True
                        )

            self.logger.info(f"Found {len(templates)} configuration templates")

        except Exception as e:
            self.logger.error(
                f"Failed to list configuration templates: {e}",
                exc_info=True
            )

        return templates

    def _fetch_application_versions(self) -> list[ApplicationVersion]:
        """
        Fetch all Elastic Beanstalk application versions.

        Application versions are fetched per application, so we first need
        to get all applications and then query their versions.

        Returns:
            List of ApplicationVersion resources
        """
        versions: list[ApplicationVersion] = []

        try:
            # First, get all applications
            response = self.client.describe_applications()
            app_list = response.get('Applications', [])

            for app_data in app_list:
                app_name = app_data.get('ApplicationName')
                version_labels = app_data.get('Versions', [])

                if not version_labels:
                    continue

                # Fetch application version details
                try:
                    versions_response = self.client.describe_application_versions(
                        ApplicationName=app_name
                    )

                    version_list = versions_response.get('ApplicationVersions', [])

                    for version_data in version_list:
                        try:
                            version = ApplicationVersion.from_aws_response(version_data)
                            versions.append(version)

                            version_label = version_data.get('VersionLabel', 'unknown')
                            self.logger.debug(
                                f"Fetched application version: {version_label} "
                                f"for application {app_name}"
                            )

                        except Exception as e:
                            version_label = version_data.get('VersionLabel', 'unknown')
                            self.logger.error(
                                f"Unexpected error processing version {version_label} "
                                f"for application {app_name}: {e}",
                                exc_info=True
                            )

                except ClientError as e:
                    error_code = e.response.get('Error', {}).get('Code', '')
                    if error_code in ['AccessDenied', 'ResourceNotFoundException']:
                        self.logger.warning(
                            f"Cannot access versions for application {app_name}: {error_code}"
                        )
                    else:
                        self.logger.error(
                            f"Error fetching versions for application {app_name}: {e}",
                            exc_info=True
                        )
                except Exception as e:
                    self.logger.error(
                        f"Unexpected error fetching versions for application {app_name}: {e}",
                        exc_info=True
                    )

            self.logger.info(f"Found {len(versions)} application versions")

        except Exception as e:
            self.logger.error(
                f"Failed to list application versions: {e}",
                exc_info=True
            )

        return versions
