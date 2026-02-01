"""
Pydantic models for AWS CloudWatch service resources.

This module defines strongly-typed models for CloudWatch alarms, log groups,
dashboards, and related resources.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

from aws_comparator.models.common import AWSResource


class AlarmState(str, Enum):
    """CloudWatch alarm state values."""
    OK = "OK"
    ALARM = "ALARM"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class ComparisonOperator(str, Enum):
    """CloudWatch alarm comparison operators."""
    GREATER_THAN_OR_EQUAL = "GreaterThanOrEqualToThreshold"
    GREATER_THAN = "GreaterThanThreshold"
    LESS_THAN = "LessThanThreshold"
    LESS_THAN_OR_EQUAL = "LessThanOrEqualToThreshold"
    LESS_THAN_LOWER_OR_GREATER_THAN_UPPER = "LessThanLowerOrGreaterThanUpperThreshold"
    LESS_THAN_LOWER = "LessThanLowerThreshold"
    GREATER_THAN_UPPER = "GreaterThanUpperThreshold"


class Statistic(str, Enum):
    """CloudWatch metric statistics."""
    SAMPLE_COUNT = "SampleCount"
    AVERAGE = "Average"
    SUM = "Sum"
    MINIMUM = "Minimum"
    MAXIMUM = "Maximum"


class MetricDimension(BaseModel):
    """CloudWatch metric dimension."""
    model_config = ConfigDict(extra="ignore")

    name: str = Field(..., description="Dimension name")
    value: str = Field(..., description="Dimension value")


class MetricStat(BaseModel):
    """CloudWatch metric statistic configuration."""
    model_config = ConfigDict(extra="ignore")

    metric_name: str = Field(..., description="Metric name")
    namespace: str = Field(..., description="Metric namespace")
    period: int = Field(..., description="Evaluation period in seconds")
    stat: str = Field(..., description="Statistic to apply")
    unit: Optional[str] = Field(None, description="Metric unit")
    dimensions: list[MetricDimension] = Field(
        default_factory=list,
        description="Metric dimensions"
    )


class CloudWatchAlarm(AWSResource):
    """
    CloudWatch alarm resource model.

    Represents an AWS CloudWatch alarm with all its configuration properties.
    """
    model_config = ConfigDict(extra="ignore")

    # Basic properties
    alarm_name: str = Field(..., description="Alarm name")
    alarm_arn: str = Field(..., description="Alarm ARN")
    alarm_description: Optional[str] = Field(None, description="Alarm description")

    # Metric configuration
    metric_name: Optional[str] = Field(None, description="Metric name")
    namespace: Optional[str] = Field(None, description="Metric namespace")
    statistic: Optional[str] = Field(None, description="Statistic applied to metric")
    extended_statistic: Optional[str] = Field(None, description="Extended statistic (e.g., p99)")
    dimensions: list[MetricDimension] = Field(
        default_factory=list,
        description="Metric dimensions"
    )

    # Evaluation configuration
    period: Optional[int] = Field(None, description="Evaluation period in seconds (not present for composite alarms)")
    evaluation_periods: Optional[int] = Field(None, description="Number of periods to evaluate (not present for composite alarms)")
    datapoints_to_alarm: Optional[int] = Field(
        None,
        description="Number of datapoints that must breach to trigger alarm"
    )
    threshold: Optional[float] = Field(None, description="Threshold value")
    comparison_operator: Optional[str] = Field(None, description="Comparison operator (not present for composite alarms)")
    treat_missing_data: Optional[str] = Field(
        None,
        description="How to treat missing data"
    )
    evaluate_low_sample_count_percentile: Optional[str] = Field(
        None,
        description="How to evaluate low sample count percentiles"
    )

    # State information
    state_value: str = Field(..., description="Current alarm state")
    state_reason: Optional[str] = Field(None, description="Reason for current state")
    state_reason_data: Optional[str] = Field(None, description="State reason data (JSON)")
    state_updated_timestamp: Optional[datetime] = Field(
        None,
        description="When state was last updated"
    )

    # Actions
    actions_enabled: bool = Field(default=True, description="Whether actions are enabled")
    alarm_actions: list[str] = Field(
        default_factory=list,
        description="Actions to execute when alarm state is ALARM"
    )
    ok_actions: list[str] = Field(
        default_factory=list,
        description="Actions to execute when alarm state is OK"
    )
    insufficient_data_actions: list[str] = Field(
        default_factory=list,
        description="Actions to execute when alarm state is INSUFFICIENT_DATA"
    )

    # Composite alarms
    alarm_rule: Optional[str] = Field(
        None,
        description="Rule expression for composite alarms"
    )

    # Metrics math
    metrics: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Metric math expressions"
    )

    # Timestamps
    alarm_configuration_updated_timestamp: Optional[datetime] = Field(
        None,
        description="When alarm configuration was last updated"
    )

    @classmethod
    def from_aws_response(cls, alarm_data: dict[str, Any]) -> "CloudWatchAlarm":
        """
        Create CloudWatchAlarm instance from AWS API response.

        Args:
            alarm_data: Alarm data from AWS API

        Returns:
            CloudWatchAlarm instance
        """
        # Extract dimensions
        dimensions = [
            MetricDimension(name=dim['Name'], value=dim['Value'])
            for dim in alarm_data.get('Dimensions', [])
        ]

        # Build the alarm model
        alarm_dict = {
            'alarm_name': alarm_data['AlarmName'],
            'alarm_arn': alarm_data['AlarmArn'],
            'alarm_description': alarm_data.get('AlarmDescription'),
            'arn': alarm_data['AlarmArn'],
            'metric_name': alarm_data.get('MetricName'),
            'namespace': alarm_data.get('Namespace'),
            'statistic': alarm_data.get('Statistic'),
            'extended_statistic': alarm_data.get('ExtendedStatistic'),
            'dimensions': dimensions,
            'period': alarm_data.get('Period'),
            'evaluation_periods': alarm_data.get('EvaluationPeriods'),
            'datapoints_to_alarm': alarm_data.get('DatapointsToAlarm'),
            'threshold': alarm_data.get('Threshold'),
            'comparison_operator': alarm_data.get('ComparisonOperator'),
            'treat_missing_data': alarm_data.get('TreatMissingData'),
            'evaluate_low_sample_count_percentile': alarm_data.get('EvaluateLowSampleCountPercentile'),
            'state_value': alarm_data['StateValue'],
            'state_reason': alarm_data.get('StateReason'),
            'state_reason_data': alarm_data.get('StateReasonData'),
            'state_updated_timestamp': alarm_data.get('StateUpdatedTimestamp'),
            'actions_enabled': alarm_data.get('ActionsEnabled', True),
            'alarm_actions': alarm_data.get('AlarmActions', []),
            'ok_actions': alarm_data.get('OKActions', []),
            'insufficient_data_actions': alarm_data.get('InsufficientDataActions', []),
            'alarm_rule': alarm_data.get('AlarmRule'),
            'metrics': alarm_data.get('Metrics', []),
            'alarm_configuration_updated_timestamp': alarm_data.get('AlarmConfigurationUpdatedTimestamp'),
        }

        return cls(**alarm_dict)

    def __str__(self) -> str:
        """Return string representation of CloudWatch alarm."""
        return f"CloudWatchAlarm(name={self.alarm_name}, state={self.state_value})"


class LogGroup(AWSResource):
    """
    CloudWatch Logs log group resource model.

    Represents an AWS CloudWatch Logs log group with all its configuration properties.
    """
    model_config = ConfigDict(extra="ignore")

    # Basic properties
    log_group_name: str = Field(..., description="Log group name")
    log_group_arn: Optional[str] = Field(None, description="Log group ARN")
    creation_time: Optional[datetime] = Field(None, description="Creation timestamp")

    # Configuration
    retention_in_days: Optional[int] = Field(
        None,
        description="Retention period in days"
    )
    metric_filter_count: Optional[int] = Field(
        None,
        description="Number of metric filters"
    )
    stored_bytes: Optional[int] = Field(
        None,
        description="Number of bytes stored"
    )

    # Security
    kms_key_id: Optional[str] = Field(
        None,
        description="KMS key ID for encryption"
    )

    @classmethod
    def from_aws_response(cls, log_group_data: dict[str, Any]) -> "LogGroup":
        """
        Create LogGroup instance from AWS API response.

        Args:
            log_group_data: Log group data from AWS API

        Returns:
            LogGroup instance
        """
        # Convert Unix timestamp (milliseconds) to datetime if present
        creation_time = None
        if 'creationTime' in log_group_data:
            creation_time = datetime.fromtimestamp(
                log_group_data['creationTime'] / 1000.0
            )

        log_group_dict = {
            'log_group_name': log_group_data['logGroupName'],
            'log_group_arn': log_group_data.get('arn'),
            'arn': log_group_data.get('arn'),
            'creation_time': creation_time,
            'retention_in_days': log_group_data.get('retentionInDays'),
            'metric_filter_count': log_group_data.get('metricFilterCount'),
            'stored_bytes': log_group_data.get('storedBytes'),
            'kms_key_id': log_group_data.get('kmsKeyId'),
        }

        return cls(**log_group_dict)

    def __str__(self) -> str:
        """Return string representation of log group."""
        return f"LogGroup(name={self.log_group_name})"


class Dashboard(AWSResource):
    """
    CloudWatch dashboard resource model.

    Represents an AWS CloudWatch dashboard.
    """
    model_config = ConfigDict(extra="ignore")

    # Basic properties
    dashboard_name: str = Field(..., description="Dashboard name")
    dashboard_arn: str = Field(..., description="Dashboard ARN")
    dashboard_body: Optional[str] = Field(
        None,
        description="Dashboard body (JSON string)"
    )
    last_modified: Optional[datetime] = Field(
        None,
        description="Last modification timestamp"
    )
    size: Optional[int] = Field(None, description="Dashboard size in bytes")

    @classmethod
    def from_aws_response(
        cls,
        dashboard_data: dict[str, Any],
        dashboard_details: Optional[dict[str, Any]] = None
    ) -> "Dashboard":
        """
        Create Dashboard instance from AWS API response.

        Args:
            dashboard_data: Dashboard metadata from list_dashboards
            dashboard_details: Dashboard details from get_dashboard (optional)

        Returns:
            Dashboard instance
        """
        dashboard_dict = {
            'dashboard_name': dashboard_data['DashboardName'],
            'dashboard_arn': dashboard_data['DashboardArn'],
            'arn': dashboard_data['DashboardArn'],
            'last_modified': dashboard_data.get('LastModified'),
            'size': dashboard_data.get('Size'),
        }

        # Add dashboard body if details were fetched
        if dashboard_details:
            dashboard_dict['dashboard_body'] = dashboard_details.get('DashboardBody')

        return cls(**dashboard_dict)

    def __str__(self) -> str:
        """Return string representation of dashboard."""
        return f"Dashboard(name={self.dashboard_name})"
