"""
Pydantic models for AWS Bedrock service resources.

This module defines strongly-typed models for Bedrock foundation models,
custom models, provisioned throughput, and guardrails.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import ConfigDict, Field, field_validator

from aws_comparator.models.common import AWSResource


class ModelModalityType(str, Enum):
    """Bedrock model modality types."""

    TEXT = "TEXT"
    IMAGE = "IMAGE"
    EMBEDDING = "EMBEDDING"


class CustomizationType(str, Enum):
    """Bedrock model customization types."""

    FINE_TUNING = "FINE_TUNING"
    CONTINUED_PRE_TRAINING = "CONTINUED_PRE_TRAINING"


class InferenceType(str, Enum):
    """Bedrock inference types."""

    ON_DEMAND = "ON_DEMAND"
    PROVISIONED = "PROVISIONED"


class ModelAccessStatus(str, Enum):
    """Bedrock model access status."""

    AVAILABLE = "AVAILABLE"
    GRANTED = "GRANTED"
    DENIED = "DENIED"
    PENDING = "PENDING"


class ProvisionedModelStatus(str, Enum):
    """Provisioned model throughput status."""

    CREATING = "Creating"
    IN_SERVICE = "InService"
    UPDATING = "Updating"
    FAILED = "Failed"


class GuardrailStatus(str, Enum):
    """Guardrail status."""

    CREATING = "CREATING"
    VERSIONING = "VERSIONING"
    READY = "READY"
    FAILED = "FAILED"
    DELETING = "DELETING"


class FoundationModel(AWSResource):
    """
    Bedrock Foundation Model resource model.

    Represents a foundation model available in AWS Bedrock.
    """

    model_config = ConfigDict(extra="ignore")

    # Basic properties
    model_arn: str = Field(..., description="Model ARN")
    model_id: str = Field(..., description="Model identifier")
    model_name: str = Field(..., description="Model name")
    provider_name: str = Field(
        ..., description="Model provider (e.g., Anthropic, Amazon)"
    )

    # Capabilities
    input_modalities: list[str] = Field(
        default_factory=list,
        description="Supported input modalities (TEXT, IMAGE, etc.)",
    )
    output_modalities: list[str] = Field(
        default_factory=list, description="Supported output modalities"
    )
    response_streaming_supported: bool = Field(
        default=False, description="Whether response streaming is supported"
    )

    # Customization and inference
    customizations_supported: list[str] = Field(
        default_factory=list, description="Supported customization types"
    )
    inference_types_supported: list[str] = Field(
        default_factory=list,
        description="Supported inference types (ON_DEMAND, PROVISIONED)",
    )

    @field_validator("model_id")
    @classmethod
    def validate_model_id(cls, v: str) -> str:
        """
        Validate model ID format.

        Args:
            v: Model ID to validate

        Returns:
            Validated model ID

        Raises:
            ValueError: If model ID is invalid
        """
        if not v:
            raise ValueError("Model ID cannot be empty")
        return v

    @classmethod
    def from_aws_response(cls, model_data: dict[str, Any]) -> "FoundationModel":
        """
        Create FoundationModel instance from AWS API response.

        Args:
            model_data: Model data from AWS API

        Returns:
            FoundationModel instance
        """
        model_arn: str = model_data.get("modelArn") or ""
        model_id: str = model_data.get("modelId") or ""
        model_name: str = model_data.get("modelName") or ""
        provider_name: str = model_data.get("providerName") or ""
        input_modalities: list[str] = model_data.get("inputModalities") or []
        output_modalities: list[str] = model_data.get("outputModalities") or []
        customizations_supported: list[str] = (
            model_data.get("customizationsSupported") or []
        )
        inference_types_supported: list[str] = (
            model_data.get("inferenceTypesSupported") or []
        )
        return cls(
            model_arn=model_arn,
            model_id=model_id,
            model_name=model_name,
            provider_name=provider_name,
            input_modalities=input_modalities,
            output_modalities=output_modalities,
            response_streaming_supported=model_data.get(
                "responseStreamingSupported", False
            ),
            customizations_supported=customizations_supported,
            inference_types_supported=inference_types_supported,
            arn=model_arn,
            created_date=None,
            region=None,
        )

    def __str__(self) -> str:
        """Return string representation of foundation model."""
        return f"FoundationModel(id={self.model_id}, provider={self.provider_name})"


class CustomModel(AWSResource):
    """
    Bedrock Custom Model resource model.

    Represents a custom fine-tuned model in AWS Bedrock.
    """

    model_config = ConfigDict(extra="ignore")

    # Basic properties
    model_arn: str = Field(..., description="Model ARN")
    model_name: str = Field(..., description="Model name")
    job_name: Optional[str] = Field(None, description="Training job name")
    base_model_arn: str = Field(..., description="Base model ARN")
    creation_time: Optional[datetime] = Field(None, description="Creation timestamp")

    # Security
    model_kms_key_arn: Optional[str] = Field(
        None, description="KMS key ARN for encryption"
    )

    @field_validator("model_name")
    @classmethod
    def validate_model_name(cls, v: str) -> str:
        """
        Validate model name.

        Args:
            v: Model name to validate

        Returns:
            Validated model name

        Raises:
            ValueError: If model name is invalid
        """
        if not v:
            raise ValueError("Model name cannot be empty")
        return v

    @classmethod
    def from_aws_response(cls, model_data: dict[str, Any]) -> "CustomModel":
        """
        Create CustomModel instance from AWS API response.

        Args:
            model_data: Model data from AWS API

        Returns:
            CustomModel instance
        """
        model_arn: str = model_data.get("modelArn") or ""
        model_name: str = model_data.get("modelName") or ""
        base_model_arn: str = model_data.get("baseModelArn") or ""
        return cls(
            model_arn=model_arn,
            model_name=model_name,
            job_name=model_data.get("jobName"),
            base_model_arn=base_model_arn,
            creation_time=model_data.get("creationTime"),
            model_kms_key_arn=model_data.get("modelKmsKeyArn"),
            arn=model_arn,
            created_date=None,
            region=None,
        )

    def __str__(self) -> str:
        """Return string representation of custom model."""
        return f"CustomModel(name={self.model_name}, base={self.base_model_arn})"


class ProvisionedModelThroughput(AWSResource):
    """
    Bedrock Provisioned Model Throughput resource model.

    Represents provisioned throughput for a Bedrock model.
    """

    model_config = ConfigDict(extra="ignore")

    # Basic properties
    provisioned_model_arn: str = Field(..., description="Provisioned model ARN")
    provisioned_model_name: str = Field(..., description="Provisioned model name")
    model_arn: str = Field(..., description="Foundation model ARN")

    # Capacity
    desired_model_units: int = Field(..., ge=1, description="Desired model units")
    current_model_units: Optional[int] = Field(
        None, ge=0, description="Current model units"
    )

    # Status
    status: str = Field(..., description="Provisioned model status")
    creation_time: Optional[datetime] = Field(None, description="Creation timestamp")

    @field_validator("provisioned_model_name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """
        Validate provisioned model name.

        Args:
            v: Name to validate

        Returns:
            Validated name

        Raises:
            ValueError: If name is invalid
        """
        if not v:
            raise ValueError("Provisioned model name cannot be empty")
        return v

    @classmethod
    def from_aws_response(
        cls, throughput_data: dict[str, Any]
    ) -> "ProvisionedModelThroughput":
        """
        Create ProvisionedModelThroughput instance from AWS API response.

        Args:
            throughput_data: Throughput data from AWS API

        Returns:
            ProvisionedModelThroughput instance
        """
        provisioned_model_arn: str = throughput_data.get("provisionedModelArn") or ""
        provisioned_model_name: str = throughput_data.get("provisionedModelName") or ""
        model_arn: str = throughput_data.get("modelArn") or ""
        status: str = throughput_data.get("status") or ""
        desired_units = throughput_data.get("desiredModelUnits")
        desired_model_units: int = (
            desired_units if isinstance(desired_units, int) else 1
        )
        return cls(
            provisioned_model_arn=provisioned_model_arn,
            provisioned_model_name=provisioned_model_name,
            model_arn=model_arn,
            desired_model_units=desired_model_units,
            current_model_units=throughput_data.get("modelUnits"),
            status=status,
            creation_time=throughput_data.get("creationTime"),
            arn=provisioned_model_arn,
            created_date=None,
            region=None,
        )

    def __str__(self) -> str:
        """Return string representation of provisioned throughput."""
        return f"ProvisionedModelThroughput(name={self.provisioned_model_name}, status={self.status})"


class ModelAccessConfiguration(AWSResource):
    """
    Bedrock Model Access Configuration resource model.

    Represents model access status for a foundation model.
    """

    model_config = ConfigDict(extra="ignore")

    # Basic properties
    model_id: str = Field(..., description="Model identifier")
    access_status: str = Field(..., description="Access status")

    @classmethod
    def from_aws_response(
        cls, access_data: dict[str, Any]
    ) -> "ModelAccessConfiguration":
        """
        Create ModelAccessConfiguration instance from AWS API response.

        Args:
            access_data: Access data from AWS API

        Returns:
            ModelAccessConfiguration instance
        """
        model_id: str = access_data.get("modelId") or ""
        access_status: str = access_data.get("accessStatus") or ""
        return cls(
            model_id=model_id,
            access_status=access_status,
            arn=f"arn:aws:bedrock:::foundation-model/{model_id}",
            created_date=None,
            region=None,
        )

    def __str__(self) -> str:
        """Return string representation of model access."""
        return f"ModelAccessConfiguration(model={self.model_id}, status={self.access_status})"


class Guardrail(AWSResource):
    """
    Bedrock Guardrail resource model.

    Represents a guardrail for controlling model outputs.
    """

    model_config = ConfigDict(extra="ignore")

    # Basic properties
    guardrail_id: str = Field(..., description="Guardrail ID")
    guardrail_arn: str = Field(..., description="Guardrail ARN")
    name: str = Field(..., description="Guardrail name")
    status: str = Field(..., description="Guardrail status")
    version: str = Field(default="DRAFT", description="Guardrail version")

    # Timestamps
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """
        Validate guardrail name.

        Args:
            v: Name to validate

        Returns:
            Validated name

        Raises:
            ValueError: If name is invalid
        """
        if not v:
            raise ValueError("Guardrail name cannot be empty")
        return v

    @classmethod
    def from_aws_response(cls, guardrail_data: dict[str, Any]) -> "Guardrail":
        """
        Create Guardrail instance from AWS API response.

        Args:
            guardrail_data: Guardrail data from AWS API

        Returns:
            Guardrail instance
        """
        guardrail_id: str = guardrail_data.get("id") or ""
        guardrail_arn: str = guardrail_data.get("arn") or ""
        name: str = guardrail_data.get("name") or ""
        status: str = guardrail_data.get("status") or ""
        version: str = guardrail_data.get("version") or "DRAFT"
        tags_data = guardrail_data.get("tags")
        tags: dict[str, str] = tags_data if isinstance(tags_data, dict) else {}
        return cls(
            guardrail_id=guardrail_id,
            guardrail_arn=guardrail_arn,
            name=name,
            status=status,
            version=version,
            created_at=guardrail_data.get("createdAt"),
            updated_at=guardrail_data.get("updatedAt"),
            arn=guardrail_arn,
            tags=tags,
            created_date=None,
            region=None,
        )

    def __str__(self) -> str:
        """Return string representation of guardrail."""
        return f"Guardrail(name={self.name}, status={self.status})"
