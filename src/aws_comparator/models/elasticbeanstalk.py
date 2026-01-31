"""
Pydantic models for AWS Elastic Beanstalk service resources.

This module defines strongly-typed models for Elastic Beanstalk applications,
environments, configuration templates, and related resources.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from aws_comparator.models.common import AWSResource


class EnvironmentStatus(str, Enum):
    """Elastic Beanstalk environment status."""
    LAUNCHING = "Launching"
    UPDATING = "Updating"
    READY = "Ready"
    TERMINATING = "Terminating"
    TERMINATED = "Terminated"


class EnvironmentHealth(str, Enum):
    """Elastic Beanstalk environment health status."""
    GREEN = "Green"
    YELLOW = "Yellow"
    RED = "Red"
    GREY = "Grey"


class EnvironmentTier(str, Enum):
    """Elastic Beanstalk environment tier."""
    WEB_SERVER = "WebServer"
    WORKER = "Worker"


class OptionSetting(BaseModel):
    """
    Elastic Beanstalk configuration option setting.

    Represents a single configuration option that can be applied to an
    environment or saved in a configuration template.
    """
    model_config = ConfigDict(extra="ignore")

    namespace: str = Field(..., description="Configuration namespace")
    option_name: str = Field(..., description="Option name")
    value: Optional[str] = Field(None, description="Option value")
    resource_name: Optional[str] = Field(None, description="Resource name")

    def __str__(self) -> str:
        """Return string representation of option setting."""
        return f"{self.namespace}:{self.option_name}={self.value}"


class ResourceLifecycleConfig(BaseModel):
    """Resource lifecycle configuration for an application."""
    model_config = ConfigDict(extra="ignore")

    service_role: Optional[str] = Field(None, description="Service role ARN")
    version_lifecycle_config: Optional[dict[str, Any]] = Field(
        None,
        description="Version lifecycle configuration"
    )


class Application(AWSResource):
    """
    Elastic Beanstalk application resource model.

    Represents an Elastic Beanstalk application, which is a logical collection
    of components including environments, versions, and configurations.
    """
    model_config = ConfigDict(extra="ignore")

    application_name: str = Field(..., description="Application name")
    application_arn: Optional[str] = Field(None, description="Application ARN")
    description: Optional[str] = Field(None, description="Application description")
    date_created: Optional[datetime] = Field(None, description="Creation date")
    date_updated: Optional[datetime] = Field(None, description="Last updated date")
    versions: list[str] = Field(
        default_factory=list,
        description="List of application version labels"
    )
    configuration_templates: list[str] = Field(
        default_factory=list,
        description="List of configuration template names"
    )
    resource_lifecycle_config: Optional[ResourceLifecycleConfig] = Field(
        None,
        description="Resource lifecycle configuration"
    )

    @field_validator('application_name')
    @classmethod
    def validate_application_name(cls, v: str) -> str:
        """
        Validate Elastic Beanstalk application name.

        Args:
            v: Application name to validate

        Returns:
            Validated application name

        Raises:
            ValueError: If application name is invalid
        """
        if not v:
            raise ValueError("Application name cannot be empty")
        if len(v) > 100:
            raise ValueError("Application name must be 100 characters or less")
        return v

    @classmethod
    def from_aws_response(cls, app_data: dict[str, Any]) -> "Application":
        """
        Create Application instance from AWS API response.

        Args:
            app_data: Application data from AWS API

        Returns:
            Application instance
        """
        app_dict = {
            'application_name': app_data.get('ApplicationName'),
            'application_arn': app_data.get('ApplicationArn'),
            'description': app_data.get('Description'),
            'date_created': app_data.get('DateCreated'),
            'date_updated': app_data.get('DateUpdated'),
            'versions': app_data.get('Versions', []),
            'configuration_templates': app_data.get('ConfigurationTemplates', []),
            'arn': app_data.get('ApplicationArn'),
        }

        # Add resource lifecycle config if present
        if 'ResourceLifecycleConfig' in app_data:
            rlc = app_data['ResourceLifecycleConfig']
            app_dict['resource_lifecycle_config'] = {
                'service_role': rlc.get('ServiceRole'),
                'version_lifecycle_config': rlc.get('VersionLifecycleConfig')
            }

        return cls(**app_dict)

    def __str__(self) -> str:
        """Return string representation of application."""
        return f"Application(name={self.application_name})"


class EnvironmentTierInfo(BaseModel):
    """Environment tier information."""
    model_config = ConfigDict(extra="ignore")

    name: str = Field(..., description="Tier name")
    type: str = Field(..., description="Tier type")
    version: Optional[str] = Field(None, description="Tier version")


class Environment(AWSResource):
    """
    Elastic Beanstalk environment resource model.

    Represents an Elastic Beanstalk environment, which is a version that is
    deployed onto AWS resources.
    """
    model_config = ConfigDict(extra="ignore")

    environment_name: str = Field(..., description="Environment name")
    environment_id: Optional[str] = Field(None, description="Environment ID")
    application_name: str = Field(..., description="Associated application name")
    version_label: Optional[str] = Field(None, description="Application version label")
    solution_stack_name: Optional[str] = Field(
        None,
        description="Solution stack name"
    )
    platform_arn: Optional[str] = Field(None, description="Platform ARN")
    template_name: Optional[str] = Field(
        None,
        description="Configuration template name"
    )
    description: Optional[str] = Field(None, description="Environment description")
    endpoint_url: Optional[str] = Field(None, description="Endpoint URL")
    cname: Optional[str] = Field(None, description="CNAME for the environment")
    date_created: Optional[datetime] = Field(None, description="Creation date")
    date_updated: Optional[datetime] = Field(None, description="Last updated date")
    status: Optional[EnvironmentStatus] = Field(None, description="Environment status")
    abortable_operation_in_progress: bool = Field(
        default=False,
        description="Whether an abortable operation is in progress"
    )
    health: Optional[EnvironmentHealth] = Field(None, description="Health status")
    health_status: Optional[str] = Field(None, description="Detailed health status")
    tier: Optional[EnvironmentTierInfo] = Field(None, description="Environment tier")
    resources: Optional[dict[str, Any]] = Field(
        None,
        description="Environment resources"
    )

    @field_validator('environment_name')
    @classmethod
    def validate_environment_name(cls, v: str) -> str:
        """
        Validate Elastic Beanstalk environment name.

        Args:
            v: Environment name to validate

        Returns:
            Validated environment name

        Raises:
            ValueError: If environment name is invalid
        """
        if not v:
            raise ValueError("Environment name cannot be empty")
        if len(v) > 40:
            raise ValueError("Environment name must be 40 characters or less")
        return v

    @classmethod
    def from_aws_response(cls, env_data: dict[str, Any]) -> "Environment":
        """
        Create Environment instance from AWS API response.

        Args:
            env_data: Environment data from AWS API

        Returns:
            Environment instance
        """
        env_dict = {
            'environment_name': env_data.get('EnvironmentName'),
            'environment_id': env_data.get('EnvironmentId'),
            'application_name': env_data.get('ApplicationName'),
            'version_label': env_data.get('VersionLabel'),
            'solution_stack_name': env_data.get('SolutionStackName'),
            'platform_arn': env_data.get('PlatformArn'),
            'template_name': env_data.get('TemplateName'),
            'description': env_data.get('Description'),
            'endpoint_url': env_data.get('EndpointURL'),
            'cname': env_data.get('CNAME'),
            'date_created': env_data.get('DateCreated'),
            'date_updated': env_data.get('DateUpdated'),
            'status': env_data.get('Status'),
            'abortable_operation_in_progress': env_data.get('AbortableOperationInProgress', False),
            'health': env_data.get('Health'),
            'health_status': env_data.get('HealthStatus'),
            'arn': env_data.get('EnvironmentArn'),
        }

        # Add tier information if present
        if 'Tier' in env_data:
            tier = env_data['Tier']
            env_dict['tier'] = {
                'name': tier.get('Name'),
                'type': tier.get('Type'),
                'version': tier.get('Version')
            }

        # Add resources if present
        if 'Resources' in env_data:
            env_dict['resources'] = env_data['Resources']

        return cls(**env_dict)

    def __str__(self) -> str:
        """Return string representation of environment."""
        return f"Environment(name={self.environment_name}, app={self.application_name})"


class ConfigurationTemplate(AWSResource):
    """
    Elastic Beanstalk configuration template resource model.

    Represents a saved configuration that can be used to launch new environments
    or to apply configuration changes to existing environments.
    """
    model_config = ConfigDict(extra="ignore")

    template_name: str = Field(..., description="Template name")
    application_name: str = Field(..., description="Associated application name")
    description: Optional[str] = Field(None, description="Template description")
    solution_stack_name: Optional[str] = Field(
        None,
        description="Solution stack name"
    )
    platform_arn: Optional[str] = Field(None, description="Platform ARN")
    date_created: Optional[datetime] = Field(None, description="Creation date")
    date_updated: Optional[datetime] = Field(None, description="Last updated date")
    deployment_status: Optional[str] = Field(None, description="Deployment status")
    option_settings: list[OptionSetting] = Field(
        default_factory=list,
        description="Configuration option settings"
    )

    @classmethod
    def from_aws_response(cls, config_data: dict[str, Any]) -> "ConfigurationTemplate":
        """
        Create ConfigurationTemplate instance from AWS API response.

        Args:
            config_data: Configuration template data from AWS API

        Returns:
            ConfigurationTemplate instance
        """
        config_dict = {
            'template_name': config_data.get('TemplateName'),
            'application_name': config_data.get('ApplicationName'),
            'description': config_data.get('Description'),
            'solution_stack_name': config_data.get('SolutionStackName'),
            'platform_arn': config_data.get('PlatformArn'),
            'date_created': config_data.get('DateCreated'),
            'date_updated': config_data.get('DateUpdated'),
            'deployment_status': config_data.get('DeploymentStatus'),
        }

        # Add option settings if present
        if 'OptionSettings' in config_data:
            config_dict['option_settings'] = [
                {
                    'namespace': opt.get('Namespace'),
                    'option_name': opt.get('OptionName'),
                    'value': opt.get('Value'),
                    'resource_name': opt.get('ResourceName')
                }
                for opt in config_data['OptionSettings']
            ]

        return cls(**config_dict)

    def __str__(self) -> str:
        """Return string representation of configuration template."""
        return f"ConfigurationTemplate(name={self.template_name}, app={self.application_name})"


class ApplicationVersion(AWSResource):
    """
    Elastic Beanstalk application version resource model.

    Represents a specific iteration of deployable code for an application.
    """
    model_config = ConfigDict(extra="ignore")

    application_name: str = Field(..., description="Associated application name")
    version_label: str = Field(..., description="Version label")
    description: Optional[str] = Field(None, description="Version description")
    source_build_information: Optional[dict[str, str]] = Field(
        None,
        description="Source build information"
    )
    source_bundle: Optional[dict[str, str]] = Field(
        None,
        description="Source bundle location (S3 bucket and key)"
    )
    date_created: Optional[datetime] = Field(None, description="Creation date")
    date_updated: Optional[datetime] = Field(None, description="Last updated date")
    status: Optional[str] = Field(None, description="Version status")
    build_arn: Optional[str] = Field(None, description="CodeBuild build ARN")

    @classmethod
    def from_aws_response(cls, version_data: dict[str, Any]) -> "ApplicationVersion":
        """
        Create ApplicationVersion instance from AWS API response.

        Args:
            version_data: Application version data from AWS API

        Returns:
            ApplicationVersion instance
        """
        version_dict = {
            'application_name': version_data.get('ApplicationName'),
            'version_label': version_data.get('VersionLabel'),
            'description': version_data.get('Description'),
            'source_build_information': version_data.get('SourceBuildInformation'),
            'source_bundle': version_data.get('SourceBundle'),
            'date_created': version_data.get('DateCreated'),
            'date_updated': version_data.get('DateUpdated'),
            'status': version_data.get('Status'),
            'build_arn': version_data.get('BuildArn'),
            'arn': version_data.get('ApplicationVersionArn'),
        }

        return cls(**version_dict)

    def __str__(self) -> str:
        """Return string representation of application version."""
        return f"ApplicationVersion(app={self.application_name}, version={self.version_label})"
