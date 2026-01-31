"""
Pydantic models for AWS Service Quotas resources.

This module defines strongly-typed models for Service Quotas and related resources.
"""

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from aws_comparator.models.common import AWSResource


class UsageMetric(BaseModel):
    """
    Usage metric configuration for a service quota.

    Provides information about how to measure quota usage via CloudWatch metrics.
    """
    model_config = ConfigDict(extra="ignore")

    metric_namespace: Optional[str] = Field(None, description="CloudWatch metric namespace")
    metric_name: Optional[str] = Field(None, description="CloudWatch metric name")
    metric_dimensions: Optional[dict[str, str]] = Field(
        None,
        description="CloudWatch metric dimensions"
    )
    metric_statistic_recommendation: Optional[str] = Field(
        None,
        description="Recommended statistic (e.g., 'Maximum', 'Sum')"
    )

    def __str__(self) -> str:
        """Return string representation of usage metric."""
        if self.metric_namespace and self.metric_name:
            return f"{self.metric_namespace}/{self.metric_name}"
        return "UsageMetric(not configured)"


class ServiceQuota(AWSResource):
    """
    Service quota resource model.

    Represents a service quota (limit) for an AWS service, including its
    current value, whether it's adjustable, and usage metrics.
    """
    model_config = ConfigDict(extra="ignore")

    # Service identification
    service_code: str = Field(..., description="Service code (e.g., 'lambda', 'ec2')")
    service_name: str = Field(..., description="Service display name")

    # Quota identification
    quota_code: str = Field(..., description="Unique quota code")
    quota_name: str = Field(..., description="Human-readable quota name")

    # Quota value and properties
    value: float = Field(..., description="Current quota value")
    unit: str = Field(default="None", description="Unit of measurement")
    adjustable: bool = Field(default=False, description="Whether quota is adjustable")
    global_quota: bool = Field(default=False, description="Whether quota is global (not regional)")

    # Usage tracking
    usage_metric: Optional[UsageMetric] = Field(
        None,
        description="CloudWatch metric for tracking quota usage"
    )

    # Default value comparison
    is_default: bool = Field(
        default=True,
        description="Whether quota is at default value"
    )
    default_value: Optional[float] = Field(
        None,
        description="Default AWS quota value"
    )

    @field_validator('value')
    @classmethod
    def validate_value(cls, v: float) -> float:
        """
        Validate quota value.

        Args:
            v: Quota value to validate

        Returns:
            Validated quota value

        Raises:
            ValueError: If value is negative
        """
        if v < 0:
            raise ValueError("Quota value cannot be negative")
        return v

    @classmethod
    def from_aws_response(
        cls,
        quota_data: dict[str, Any],
        default_value: Optional[float] = None
    ) -> "ServiceQuota":
        """
        Create ServiceQuota instance from AWS API response.

        Args:
            quota_data: Quota data from AWS Service Quotas API
            default_value: Default quota value for comparison

        Returns:
            ServiceQuota instance
        """
        quota_dict = {
            'service_code': quota_data['ServiceCode'],
            'service_name': quota_data['ServiceName'],
            'quota_code': quota_data['QuotaCode'],
            'quota_name': quota_data['QuotaName'],
            'arn': quota_data.get('QuotaArn'),
            'value': float(quota_data['Value']),
            'unit': quota_data.get('Unit', 'None'),
            'adjustable': quota_data.get('Adjustable', False),
            'global_quota': quota_data.get('GlobalQuota', False),
        }

        # Parse usage metric if present
        if 'UsageMetric' in quota_data and quota_data['UsageMetric']:
            usage_metric_data = quota_data['UsageMetric']
            quota_dict['usage_metric'] = UsageMetric(
                metric_namespace=usage_metric_data.get('MetricNamespace'),
                metric_name=usage_metric_data.get('MetricName'),
                metric_dimensions=usage_metric_data.get('MetricDimensions', {}),
                metric_statistic_recommendation=usage_metric_data.get('MetricStatisticRecommendation')
            )

        # Set default value comparison
        if default_value is not None:
            quota_dict['default_value'] = default_value
            quota_dict['is_default'] = abs(quota_dict['value'] - default_value) < 0.01

        return cls(**quota_dict)

    def has_been_increased(self) -> bool:
        """
        Check if quota has been increased from default.

        Returns:
            True if quota has been increased from default value
        """
        if self.default_value is None:
            return False
        return self.value > self.default_value

    def get_increase_amount(self) -> Optional[float]:
        """
        Get amount quota has been increased from default.

        Returns:
            Increase amount, or None if default value is unknown
        """
        if self.default_value is None:
            return None
        return self.value - self.default_value

    def get_increase_percentage(self) -> Optional[float]:
        """
        Get percentage quota has been increased from default.

        Returns:
            Increase percentage, or None if default value is unknown or zero
        """
        if self.default_value is None or self.default_value == 0:
            return None
        return ((self.value - self.default_value) / self.default_value) * 100

    def __str__(self) -> str:
        """Return string representation of service quota."""
        adjustable_str = "adjustable" if self.adjustable else "fixed"
        global_str = " (global)" if self.global_quota else ""
        return (
            f"ServiceQuota({self.service_code}/{self.quota_name}: "
            f"{self.value} {self.unit}, {adjustable_str}{global_str})"
        )


class QuotaComparison(BaseModel):
    """
    Comparison of quotas between two accounts.

    Represents differences in quota values between two AWS accounts.
    """
    model_config = ConfigDict(extra="forbid")

    service_code: str = Field(..., description="Service code")
    quota_code: str = Field(..., description="Quota code")
    quota_name: str = Field(..., description="Quota name")

    account1_value: Optional[float] = Field(None, description="Quota value in account 1")
    account2_value: Optional[float] = Field(None, description="Quota value in account 2")

    difference: Optional[float] = Field(None, description="Difference (account2 - account1)")
    percentage_difference: Optional[float] = Field(
        None,
        description="Percentage difference"
    )

    only_in_account1: bool = Field(default=False, description="Quota only exists in account 1")
    only_in_account2: bool = Field(default=False, description="Quota only exists in account 2")
    values_differ: bool = Field(default=False, description="Quota values differ")

    adjustable: bool = Field(default=False, description="Whether quota is adjustable")

    def __str__(self) -> str:
        """Return string representation of quota comparison."""
        if self.only_in_account1:
            return f"QuotaComparison({self.quota_name}: only in account1)"
        elif self.only_in_account2:
            return f"QuotaComparison({self.quota_name}: only in account2)"
        elif self.values_differ:
            return (
                f"QuotaComparison({self.quota_name}: "
                f"{self.account1_value} vs {self.account2_value})"
            )
        else:
            return f"QuotaComparison({self.quota_name}: same)"


class ServiceInfo(BaseModel):
    """
    Information about an AWS service in Service Quotas.

    Basic metadata about a service available in Service Quotas API.
    """
    model_config = ConfigDict(extra="ignore")

    service_code: str = Field(..., description="Service code")
    service_name: str = Field(..., description="Service display name")

    @classmethod
    def from_aws_response(cls, service_data: dict[str, Any]) -> "ServiceInfo":
        """
        Create ServiceInfo instance from AWS API response.

        Args:
            service_data: Service data from AWS Service Quotas API

        Returns:
            ServiceInfo instance
        """
        return cls(
            service_code=service_data['ServiceCode'],
            service_name=service_data['ServiceName']
        )

    def __str__(self) -> str:
        """Return string representation of service info."""
        return f"ServiceInfo({self.service_code}: {self.service_name})"
