"""
Pydantic models for AWS Lambda service resources.

This module defines strongly-typed models for Lambda functions and layers.
"""

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from aws_comparator.models.common import AWSResource


class Runtime(str, Enum):
    """Lambda function runtimes."""

    PYTHON_3_8 = "python3.8"
    PYTHON_3_9 = "python3.9"
    PYTHON_3_10 = "python3.10"
    PYTHON_3_11 = "python3.11"
    PYTHON_3_12 = "python3.12"
    NODEJS_16 = "nodejs16.x"
    NODEJS_18 = "nodejs18.x"
    NODEJS_20 = "nodejs20.x"
    JAVA_8 = "java8"
    JAVA_11 = "java11"
    JAVA_17 = "java17"
    JAVA_21 = "java21"
    DOTNET_6 = "dotnet6"
    DOTNET_8 = "dotnet8"
    GO_1_X = "go1.x"
    RUBY_3_2 = "ruby3.2"
    PROVIDED_AL2 = "provided.al2"
    PROVIDED_AL2023 = "provided.al2023"


class PackageType(str, Enum):
    """Lambda package types."""

    ZIP = "Zip"
    IMAGE = "Image"


class State(str, Enum):
    """Lambda function states."""

    PENDING = "Pending"
    ACTIVE = "Active"
    INACTIVE = "Inactive"
    FAILED = "Failed"


class VpcConfig(BaseModel):
    """Lambda VPC configuration."""

    model_config = ConfigDict(extra="ignore")

    subnet_ids: list[str] = Field(default_factory=list, description="VPC subnet IDs")
    security_group_ids: list[str] = Field(
        default_factory=list, description="Security group IDs"
    )
    vpc_id: Optional[str] = Field(None, description="VPC ID")


class Environment(BaseModel):
    """Lambda environment variables."""

    model_config = ConfigDict(extra="ignore")

    variables: dict[str, str] = Field(
        default_factory=dict, description="Environment variables"
    )


class DeadLetterConfig(BaseModel):
    """Lambda dead letter queue configuration."""

    model_config = ConfigDict(extra="ignore")

    target_arn: str = Field(..., description="Target ARN for failed invocations")


class TracingConfig(BaseModel):
    """Lambda X-Ray tracing configuration."""

    model_config = ConfigDict(extra="ignore")

    mode: str = Field(
        default="PassThrough", description="Tracing mode (Active/PassThrough)"
    )


class LambdaFunction(AWSResource):
    """
    Lambda function resource model.

    Represents an AWS Lambda function with all its configuration properties.
    """

    model_config = ConfigDict(extra="ignore")

    # Basic properties
    function_name: str = Field(..., description="Function name")
    function_arn: str = Field(..., description="Function ARN")
    runtime: Optional[Runtime] = Field(None, description="Function runtime")
    role: str = Field(..., description="IAM role ARN")
    handler: Optional[str] = Field(None, description="Function handler")

    # Code configuration
    code_size: int = Field(..., ge=0, description="Code size in bytes")
    code_sha256: str = Field(..., description="SHA256 hash of code")
    package_type: PackageType = Field(
        default=PackageType.ZIP, description="Package type"
    )

    # Execution configuration
    description: Optional[str] = Field(None, description="Function description")
    timeout: int = Field(default=3, ge=1, le=900, description="Timeout in seconds")
    memory_size: int = Field(default=128, ge=128, le=10240, description="Memory in MB")
    last_modified: str = Field(..., description="Last modified timestamp")

    # Versioning
    version: str = Field(..., description="Function version")
    last_update_status: Optional[State] = Field(None, description="Last update status")
    state: Optional[State] = Field(None, description="Current state")

    # Networking
    vpc_config: Optional[VpcConfig] = Field(None, description="VPC configuration")

    # Environment
    environment: Optional[Environment] = Field(
        None, description="Environment variables"
    )

    # Dead letter queue
    dead_letter_config: Optional[DeadLetterConfig] = Field(
        None, description="Dead letter configuration"
    )

    # Tracing
    tracing_config: Optional[TracingConfig] = Field(
        None, description="Tracing configuration"
    )

    # Layers
    layers: list[str] = Field(default_factory=list, description="Layer ARNs")

    # File systems
    file_system_configs: list[dict[str, Any]] = Field(
        default_factory=list, description="EFS file system configurations"
    )

    # Image config (for container images)
    image_config_response: Optional[dict[str, Any]] = Field(
        None, description="Container image configuration"
    )

    # Architectures
    architectures: list[str] = Field(
        default_factory=lambda: ["x86_64"], description="Instruction set architectures"
    )

    # Ephemeral storage
    ephemeral_storage_size: int = Field(
        default=512, ge=512, le=10240, description="Ephemeral storage size in MB"
    )

    # Reserved concurrent executions
    reserved_concurrent_executions: Optional[int] = Field(
        None, description="Reserved concurrent executions"
    )

    @field_validator("function_name")
    @classmethod
    def validate_function_name(cls, v: str) -> str:
        """
        Validate Lambda function name.

        Args:
            v: Function name to validate

        Returns:
            Validated function name

        Raises:
            ValueError: If function name is invalid
        """
        if not v:
            raise ValueError("Function name cannot be empty")
        if len(v) > 64:
            raise ValueError("Function name cannot exceed 64 characters")
        return v

    @classmethod
    def from_aws_response(
        cls, function_data: dict[str, Any], tags: Optional[dict[str, str]] = None
    ) -> "LambdaFunction":
        """
        Create LambdaFunction instance from AWS API response.

        Args:
            function_data: Function data from AWS API
            tags: Function tags

        Returns:
            LambdaFunction instance
        """
        function_dict: dict[str, Any] = {
            "function_name": function_data.get("FunctionName"),
            "function_arn": function_data.get("FunctionArn"),
            "arn": function_data.get("FunctionArn"),
            "runtime": function_data.get("Runtime"),
            "role": function_data.get("Role"),
            "handler": function_data.get("Handler"),
            "code_size": function_data.get("CodeSize", 0),
            "code_sha256": function_data.get("CodeSha256"),
            "description": function_data.get("Description"),
            "timeout": function_data.get("Timeout", 3),
            "memory_size": function_data.get("MemorySize", 128),
            "last_modified": function_data.get("LastModified"),
            "version": function_data.get("Version", "$LATEST"),
            "tags": tags or {},
        }

        # Optional fields
        if "PackageType" in function_data:
            function_dict["package_type"] = function_data["PackageType"]
        if "LastUpdateStatus" in function_data:
            function_dict["last_update_status"] = function_data["LastUpdateStatus"]
        if "State" in function_data:
            function_dict["state"] = function_data["State"]

        # VPC configuration
        if "VpcConfig" in function_data:
            vpc = function_data["VpcConfig"]
            function_dict["vpc_config"] = {
                "subnet_ids": vpc.get("SubnetIds", []),
                "security_group_ids": vpc.get("SecurityGroupIds", []),
                "vpc_id": vpc.get("VpcId"),
            }

        # Environment
        env_data = function_data.get("Environment", {})
        if "Variables" in env_data:
            function_dict["environment"] = {"variables": env_data["Variables"]}

        # Dead letter config
        dlc_data = function_data.get("DeadLetterConfig", {})
        if "TargetArn" in dlc_data:
            function_dict["dead_letter_config"] = {"target_arn": dlc_data["TargetArn"]}

        # Tracing
        if "TracingConfig" in function_data:
            function_dict["tracing_config"] = {
                "mode": function_data["TracingConfig"].get("Mode", "PassThrough")
            }

        # Layers
        if "Layers" in function_data:
            function_dict["layers"] = [
                layer["Arn"] for layer in function_data["Layers"]
            ]

        # File systems
        if "FileSystemConfigs" in function_data:
            function_dict["file_system_configs"] = function_data["FileSystemConfigs"]

        # Image config
        if "ImageConfigResponse" in function_data:
            function_dict["image_config_response"] = function_data[
                "ImageConfigResponse"
            ]

        # Architectures
        if "Architectures" in function_data:
            function_dict["architectures"] = function_data["Architectures"]

        # Ephemeral storage
        if "EphemeralStorage" in function_data:
            function_dict["ephemeral_storage_size"] = function_data[
                "EphemeralStorage"
            ].get("Size", 512)

        return cls(**function_dict)

    def __str__(self) -> str:
        """Return string representation of Lambda function."""
        runtime_str = self.runtime.value if self.runtime else "container"
        return f"LambdaFunction(name={self.function_name}, runtime={runtime_str})"


class LambdaLayer(AWSResource):
    """
    Lambda layer resource model.

    Represents an AWS Lambda layer with its configuration.
    """

    model_config = ConfigDict(extra="ignore")

    layer_name: str = Field(..., description="Layer name")
    layer_arn: str = Field(..., description="Layer ARN")
    layer_version_arn: str = Field(..., description="Layer version ARN")
    version: int = Field(..., description="Layer version number")
    description: Optional[str] = Field(None, description="Layer description")
    layer_created_date: str = Field(..., description="Creation date")
    compatible_runtimes: list[Runtime] = Field(
        default_factory=list, description="Compatible runtimes"
    )
    compatible_architectures: list[str] = Field(
        default_factory=list, description="Compatible architectures"
    )
    license_info: Optional[str] = Field(None, description="License information")

    @classmethod
    def from_aws_response(cls, layer_data: dict[str, Any]) -> "LambdaLayer":
        """
        Create LambdaLayer instance from AWS API response.

        Args:
            layer_data: Layer data from AWS API

        Returns:
            LambdaLayer instance
        """
        layer_dict: dict[str, Any] = {
            "layer_name": layer_data.get("LayerName"),
            "layer_arn": layer_data.get("LayerArn"),
            "layer_version_arn": layer_data.get("LayerVersionArn"),
            "arn": layer_data.get("LayerVersionArn"),
            "version": layer_data.get("Version"),
            "description": layer_data.get("Description"),
            "layer_created_date": layer_data.get("CreatedDate"),
            "compatible_runtimes": layer_data.get("CompatibleRuntimes", []),
            "compatible_architectures": layer_data.get("CompatibleArchitectures", []),
            "license_info": layer_data.get("LicenseInfo"),
        }

        return cls(**layer_dict)

    def __str__(self) -> str:
        """Return string representation of Lambda layer."""
        return f"LambdaLayer(name={self.layer_name}, version={self.version})"
