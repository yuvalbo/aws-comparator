"""
Unit tests for CloudWatch service fetcher.

This module tests the CloudWatch fetcher functionality using moto for AWS mocking.
"""

from datetime import datetime, timezone
from unittest.mock import Mock, patch

import boto3
import pytest
from botocore.exceptions import ClientError
from moto import mock_aws

from aws_comparator.models.cloudwatch import CloudWatchAlarm, Dashboard, LogGroup
from aws_comparator.services.cloudwatch.fetcher import CloudWatchFetcher


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
def cloudwatch_client(aws_credentials):
    """Create a mocked CloudWatch client."""
    with mock_aws():
        yield boto3.client("cloudwatch", region_name="us-east-1")


@pytest.fixture
def logs_client(aws_credentials):
    """Create a mocked CloudWatch Logs client."""
    with mock_aws():
        yield boto3.client("logs", region_name="us-east-1")


@pytest.fixture
def session(aws_credentials):
    """Create a mocked boto3 session."""
    with mock_aws():
        yield boto3.Session(region_name="us-east-1")


@pytest.fixture
def cloudwatch_fetcher(session):
    """Create a CloudWatch fetcher instance."""
    return CloudWatchFetcher(session=session, region="us-east-1")


class TestCloudWatchFetcher:
    """Test CloudWatchFetcher class."""

    def test_service_name(self, cloudwatch_fetcher):
        """Test that SERVICE_NAME is correctly set."""
        assert cloudwatch_fetcher.SERVICE_NAME == "cloudwatch"

    def test_get_resource_types(self, cloudwatch_fetcher):
        """Test get_resource_types returns correct resource types."""
        resource_types = cloudwatch_fetcher.get_resource_types()
        assert "alarms" in resource_types
        assert "log_groups" in resource_types
        assert "dashboards" in resource_types
        assert len(resource_types) == 3

    def test_create_client(self, cloudwatch_fetcher):
        """Test that _create_client creates a CloudWatch client."""
        client = cloudwatch_fetcher._create_client()
        assert client is not None
        assert client._service_model.service_name == "cloudwatch"

    def test_create_logs_client(self, cloudwatch_fetcher):
        """Test that _create_logs_client creates a CloudWatch Logs client."""
        client = cloudwatch_fetcher._create_logs_client()
        assert client is not None
        assert client._service_model.service_name == "logs"


class TestFetchAlarms:
    """Test fetching CloudWatch alarms."""

    def test_fetch_alarms_empty(self, cloudwatch_fetcher, cloudwatch_client):
        """Test fetching alarms when none exist."""
        alarms = cloudwatch_fetcher._fetch_alarms()
        assert isinstance(alarms, list)
        assert len(alarms) == 0

    def test_fetch_alarms_with_data(self, cloudwatch_fetcher, cloudwatch_client):
        """Test fetching alarms with mocked data."""
        # Create a test alarm
        cloudwatch_client.put_metric_alarm(
            AlarmName="TestAlarm",
            ComparisonOperator="GreaterThanThreshold",
            EvaluationPeriods=1,
            MetricName="CPUUtilization",
            Namespace="AWS/EC2",
            Period=300,
            Statistic="Average",
            Threshold=80.0,
            ActionsEnabled=True,
            AlarmDescription="Test alarm for CPU utilization",
            AlarmActions=["arn:aws:sns:us-east-1:123456789012:test-topic"],
        )

        alarms = cloudwatch_fetcher._fetch_alarms()

        assert len(alarms) == 1
        assert isinstance(alarms[0], CloudWatchAlarm)
        assert alarms[0].alarm_name == "TestAlarm"
        assert alarms[0].metric_name == "CPUUtilization"
        assert alarms[0].namespace == "AWS/EC2"
        assert alarms[0].threshold == 80.0
        assert alarms[0].comparison_operator == "GreaterThanThreshold"
        assert alarms[0].period == 300
        assert alarms[0].evaluation_periods == 1
        assert alarms[0].actions_enabled is True

    def test_fetch_alarms_with_dimensions(self, cloudwatch_fetcher, cloudwatch_client):
        """Test fetching alarms with dimensions."""
        cloudwatch_client.put_metric_alarm(
            AlarmName="TestAlarmWithDimensions",
            ComparisonOperator="GreaterThanThreshold",
            EvaluationPeriods=2,
            MetricName="CPUUtilization",
            Namespace="AWS/EC2",
            Period=60,
            Statistic="Average",
            Threshold=90.0,
            Dimensions=[{"Name": "InstanceId", "Value": "i-1234567890abcdef0"}],
        )

        alarms = cloudwatch_fetcher._fetch_alarms()

        assert len(alarms) == 1
        assert len(alarms[0].dimensions) == 1
        assert alarms[0].dimensions[0].name == "InstanceId"
        assert alarms[0].dimensions[0].value == "i-1234567890abcdef0"

    def test_fetch_alarms_multiple(self, cloudwatch_fetcher, cloudwatch_client):
        """Test fetching multiple alarms."""
        # Create multiple test alarms
        for i in range(3):
            cloudwatch_client.put_metric_alarm(
                AlarmName=f"TestAlarm{i}",
                ComparisonOperator="GreaterThanThreshold",
                EvaluationPeriods=1,
                MetricName="CPUUtilization",
                Namespace="AWS/EC2",
                Period=300,
                Statistic="Average",
                Threshold=80.0 + i * 5,
            )

        alarms = cloudwatch_fetcher._fetch_alarms()

        assert len(alarms) == 3
        alarm_names = [alarm.alarm_name for alarm in alarms]
        assert "TestAlarm0" in alarm_names
        assert "TestAlarm1" in alarm_names
        assert "TestAlarm2" in alarm_names

    @patch("aws_comparator.services.cloudwatch.fetcher.CloudWatchFetcher._paginate")
    def test_fetch_alarms_error_handling(self, mock_paginate, cloudwatch_fetcher):
        """Test error handling when fetching alarms fails."""
        mock_paginate.side_effect = Exception("Test error")

        alarms = cloudwatch_fetcher._fetch_alarms()

        assert isinstance(alarms, list)
        assert len(alarms) == 0


class TestFetchLogGroups:
    """Test fetching CloudWatch Logs log groups."""

    def test_fetch_log_groups_empty(self, cloudwatch_fetcher, logs_client):
        """Test fetching log groups when none exist."""
        log_groups = cloudwatch_fetcher._fetch_log_groups()
        assert isinstance(log_groups, list)
        assert len(log_groups) == 0

    def test_fetch_log_groups_with_data(self, cloudwatch_fetcher, logs_client):
        """Test fetching log groups with mocked data."""
        # Create a test log group
        logs_client.create_log_group(logGroupName="/aws/lambda/test-function")

        log_groups = cloudwatch_fetcher._fetch_log_groups()

        assert len(log_groups) == 1
        assert isinstance(log_groups[0], LogGroup)
        assert log_groups[0].log_group_name == "/aws/lambda/test-function"

    def test_fetch_log_groups_with_retention(self, cloudwatch_fetcher, logs_client):
        """Test fetching log groups with retention settings."""
        logs_client.create_log_group(logGroupName="/aws/lambda/test-function")
        logs_client.put_retention_policy(
            logGroupName="/aws/lambda/test-function", retentionInDays=7
        )

        log_groups = cloudwatch_fetcher._fetch_log_groups()

        assert len(log_groups) == 1
        assert log_groups[0].retention_in_days == 7

    def test_fetch_log_groups_multiple(self, cloudwatch_fetcher, logs_client):
        """Test fetching multiple log groups."""
        # Create multiple test log groups
        log_group_names = [
            "/aws/lambda/function1",
            "/aws/lambda/function2",
            "/aws/ecs/service1",
        ]

        for log_group_name in log_group_names:
            logs_client.create_log_group(logGroupName=log_group_name)

        log_groups = cloudwatch_fetcher._fetch_log_groups()

        assert len(log_groups) == 3
        fetched_names = [lg.log_group_name for lg in log_groups]
        for expected_name in log_group_names:
            assert expected_name in fetched_names

    @patch(
        "aws_comparator.services.cloudwatch.fetcher.CloudWatchFetcher._create_logs_client"
    )
    def test_fetch_log_groups_error_handling(
        self, mock_logs_client, cloudwatch_fetcher
    ):
        """Test error handling when fetching log groups fails."""
        mock_client = Mock()
        mock_client.can_paginate.return_value = True
        mock_client.get_paginator.side_effect = Exception("Test error")
        mock_logs_client.return_value = mock_client

        log_groups = cloudwatch_fetcher._fetch_log_groups()

        assert isinstance(log_groups, list)
        assert len(log_groups) == 0


class TestFetchDashboards:
    """Test fetching CloudWatch dashboards."""

    def test_fetch_dashboards_empty(self, cloudwatch_fetcher, cloudwatch_client):
        """Test fetching dashboards when none exist."""
        dashboards = cloudwatch_fetcher._fetch_dashboards()
        assert isinstance(dashboards, list)
        assert len(dashboards) == 0

    def test_fetch_dashboards_with_data(self, cloudwatch_fetcher, cloudwatch_client):
        """Test fetching dashboards with mocked data."""
        # Create a test dashboard
        dashboard_body = '{"widgets": []}'
        cloudwatch_client.put_dashboard(
            DashboardName="TestDashboard", DashboardBody=dashboard_body
        )

        dashboards = cloudwatch_fetcher._fetch_dashboards()

        assert len(dashboards) == 1
        assert isinstance(dashboards[0], Dashboard)
        assert dashboards[0].dashboard_name == "TestDashboard"

    def test_fetch_dashboards_multiple(self, cloudwatch_fetcher, cloudwatch_client):
        """Test fetching multiple dashboards."""
        # Create multiple test dashboards
        dashboard_names = ["Dashboard1", "Dashboard2", "Dashboard3"]

        for name in dashboard_names:
            cloudwatch_client.put_dashboard(
                DashboardName=name, DashboardBody='{"widgets": []}'
            )

        dashboards = cloudwatch_fetcher._fetch_dashboards()

        assert len(dashboards) == 3
        fetched_names = [d.dashboard_name for d in dashboards]
        for expected_name in dashboard_names:
            assert expected_name in fetched_names

    @patch("aws_comparator.services.cloudwatch.fetcher.CloudWatchFetcher._paginate")
    def test_fetch_dashboards_error_handling(self, mock_paginate, cloudwatch_fetcher):
        """Test error handling when fetching dashboards fails."""
        mock_paginate.side_effect = Exception("Test error")

        dashboards = cloudwatch_fetcher._fetch_dashboards()

        assert isinstance(dashboards, list)
        assert len(dashboards) == 0


class TestFetchResources:
    """Test the main fetch_resources method."""

    def test_fetch_resources_structure(self, cloudwatch_fetcher):
        """Test that fetch_resources returns the correct structure."""
        resources = cloudwatch_fetcher.fetch_resources()

        assert isinstance(resources, dict)
        assert "alarms" in resources
        assert "log_groups" in resources
        assert "dashboards" in resources

    def test_fetch_resources_with_data(
        self, cloudwatch_fetcher, cloudwatch_client, logs_client
    ):
        """Test fetch_resources with mocked data."""
        # Create test data
        cloudwatch_client.put_metric_alarm(
            AlarmName="TestAlarm",
            ComparisonOperator="GreaterThanThreshold",
            EvaluationPeriods=1,
            MetricName="CPUUtilization",
            Namespace="AWS/EC2",
            Period=300,
            Statistic="Average",
            Threshold=80.0,
        )

        logs_client.create_log_group(logGroupName="/aws/lambda/test")

        cloudwatch_client.put_dashboard(
            DashboardName="TestDashboard", DashboardBody='{"widgets": []}'
        )

        resources = cloudwatch_fetcher.fetch_resources()

        assert len(resources["alarms"]) == 1
        assert len(resources["log_groups"]) == 1
        assert len(resources["dashboards"]) == 1

    def test_fetch_resources_empty(self, cloudwatch_fetcher):
        """Test fetch_resources when no resources exist."""
        resources = cloudwatch_fetcher.fetch_resources()

        assert len(resources["alarms"]) == 0
        assert len(resources["log_groups"]) == 0
        assert len(resources["dashboards"]) == 0


class TestCloudWatchModels:
    """Test CloudWatch model parsing."""

    def test_cloudwatch_alarm_from_aws_response(self):
        """Test CloudWatchAlarm.from_aws_response method."""
        alarm_data = {
            "AlarmName": "TestAlarm",
            "AlarmArn": "arn:aws:cloudwatch:us-east-1:123456789012:alarm:TestAlarm",
            "AlarmDescription": "Test alarm description",
            "MetricName": "CPUUtilization",
            "Namespace": "AWS/EC2",
            "Statistic": "Average",
            "Dimensions": [{"Name": "InstanceId", "Value": "i-1234567890abcdef0"}],
            "Period": 300,
            "EvaluationPeriods": 2,
            "Threshold": 80.0,
            "ComparisonOperator": "GreaterThanThreshold",
            "StateValue": "OK",
            "ActionsEnabled": True,
            "AlarmActions": ["arn:aws:sns:us-east-1:123456789012:test-topic"],
            "OKActions": [],
            "InsufficientDataActions": [],
        }

        alarm = CloudWatchAlarm.from_aws_response(alarm_data)

        assert alarm.alarm_name == "TestAlarm"
        assert alarm.metric_name == "CPUUtilization"
        assert alarm.namespace == "AWS/EC2"
        assert alarm.period == 300
        assert alarm.evaluation_periods == 2
        assert alarm.threshold == 80.0
        assert alarm.comparison_operator == "GreaterThanThreshold"
        assert alarm.state_value == "OK"
        assert len(alarm.dimensions) == 1

    def test_log_group_from_aws_response(self):
        """Test LogGroup.from_aws_response method."""
        log_group_data = {
            "logGroupName": "/aws/lambda/test-function",
            "arn": "arn:aws:logs:us-east-1:123456789012:log-group:/aws/lambda/test-function",
            "creationTime": 1640995200000,  # Unix timestamp in milliseconds
            "retentionInDays": 7,
            "metricFilterCount": 2,
            "storedBytes": 1048576,
        }

        log_group = LogGroup.from_aws_response(log_group_data)

        assert log_group.log_group_name == "/aws/lambda/test-function"
        assert log_group.retention_in_days == 7
        assert log_group.metric_filter_count == 2
        assert log_group.stored_bytes == 1048576
        assert log_group.creation_time is not None

    def test_dashboard_from_aws_response(self):
        """Test Dashboard.from_aws_response method."""
        dashboard_data = {
            "DashboardName": "TestDashboard",
            "DashboardArn": "arn:aws:cloudwatch::123456789012:dashboard/TestDashboard",
            "LastModified": datetime.now(timezone.utc),
            "Size": 1024,
        }

        dashboard = Dashboard.from_aws_response(dashboard_data)

        assert dashboard.dashboard_name == "TestDashboard"
        assert dashboard.dashboard_arn == dashboard_data["DashboardArn"]
        assert dashboard.size == 1024

    def test_dashboard_from_aws_response_with_details(self):
        """Test Dashboard.from_aws_response with dashboard details."""
        dashboard_data = {
            "DashboardName": "TestDashboard",
            "DashboardArn": "arn:aws:cloudwatch::123456789012:dashboard/TestDashboard",
            "LastModified": datetime.now(timezone.utc),
            "Size": 1024,
        }

        dashboard_details = {"DashboardBody": '{"widgets": []}'}

        dashboard = Dashboard.from_aws_response(dashboard_data, dashboard_details)

        assert dashboard.dashboard_name == "TestDashboard"
        assert dashboard.dashboard_body == '{"widgets": []}'


class TestCloudWatchEdgeCases:
    """Test edge cases for CloudWatch fetcher."""

    @patch("aws_comparator.services.cloudwatch.fetcher.CloudWatchFetcher._paginate")
    def test_fetch_alarms_with_invalid_data(self, mock_paginate, cloudwatch_fetcher):
        """Test fetching alarms handles invalid data gracefully."""
        mock_paginate.return_value = [
            {
                "AlarmName": "TestAlarm",
                "AlarmArn": "arn:aws:cloudwatch:us-east-1:123:alarm:Test",
                "MetricName": "CPU",
                "Namespace": "AWS/EC2",
                "Statistic": "Average",
                "Period": 300,
                "EvaluationPeriods": 1,
                "Threshold": 80.0,
                "ComparisonOperator": "GreaterThanThreshold",
                "StateValue": "OK",
            }
        ]

        alarms = cloudwatch_fetcher._fetch_alarms()

        assert len(alarms) == 1

    @patch(
        "aws_comparator.services.cloudwatch.fetcher.CloudWatchFetcher._create_logs_client"
    )
    def test_fetch_log_groups_with_invalid_data(
        self, mock_logs_client, cloudwatch_fetcher
    ):
        """Test fetching log groups handles invalid data gracefully."""
        mock_client = Mock()
        mock_logs_client.return_value = mock_client

        mock_client.can_paginate.return_value = True
        mock_paginator = Mock()
        mock_client.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [
            {
                "logGroups": [
                    {
                        "logGroupName": "/aws/lambda/test",
                        "arn": "arn:aws:logs:us-east-1:123:log-group:/aws/lambda/test",
                        "creationTime": 1640995200000,
                    }
                ]
            }
        ]

        log_groups = cloudwatch_fetcher._fetch_log_groups()

        assert len(log_groups) == 1

    @patch("aws_comparator.services.cloudwatch.fetcher.CloudWatchFetcher._paginate")
    def test_fetch_dashboards_with_get_dashboard_error(
        self, mock_paginate, cloudwatch_fetcher
    ):
        """Test fetching dashboards handles get_dashboard errors."""
        mock_paginate.return_value = [
            {
                "DashboardName": "TestDashboard",
                "DashboardArn": "arn:aws:cloudwatch::123:dashboard/Test",
            }
        ]

        # Make get_dashboard fail
        cloudwatch_fetcher.client.get_dashboard = Mock(
            side_effect=ClientError(
                {"Error": {"Code": "ResourceNotFound", "Message": "Not found"}},
                "GetDashboard",
            )
        )

        dashboards = cloudwatch_fetcher._fetch_dashboards()

        # Should still return dashboards from list, without body
        assert len(dashboards) == 1

    @patch("aws_comparator.services.cloudwatch.fetcher.CloudWatchFetcher._paginate")
    def test_fetch_alarms_per_alarm_error(self, mock_paginate, cloudwatch_fetcher):
        """Test per-alarm error handling."""
        mock_paginate.return_value = [
            {
                "AlarmName": "Alarm1",
                "AlarmArn": "arn:aws:cloudwatch:us-east-1:123:alarm:A1",
                "MetricName": "CPU",
                "Namespace": "AWS/EC2",
                "Statistic": "Average",
                "Period": 300,
                "EvaluationPeriods": 1,
                "Threshold": 80.0,
                "ComparisonOperator": "GreaterThanThreshold",
                "StateValue": "OK",
            },
            {
                # Invalid alarm data - will fail validation
            },
        ]

        alarms = cloudwatch_fetcher._fetch_alarms()

        # Should get first alarm, skip invalid one
        assert len(alarms) >= 1

    @patch(
        "aws_comparator.services.cloudwatch.fetcher.CloudWatchFetcher._create_logs_client"
    )
    def test_fetch_log_groups_per_group_error(
        self, mock_logs_client, cloudwatch_fetcher
    ):
        """Test per-log-group error handling."""
        mock_client = Mock()
        mock_logs_client.return_value = mock_client

        mock_client.can_paginate.return_value = True
        mock_paginator = Mock()
        mock_client.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [
            {
                "logGroups": [
                    {
                        "logGroupName": "/aws/valid/group",
                        "arn": "arn:aws:logs:us-east-1:123:log-group:/aws/valid/group",
                        "creationTime": 1640995200000,
                    },
                    {
                        # Invalid log group data
                    },
                ]
            }
        ]

        log_groups = cloudwatch_fetcher._fetch_log_groups()

        # Should get first log group, skip invalid one
        assert len(log_groups) >= 1

    @patch("aws_comparator.services.cloudwatch.fetcher.CloudWatchFetcher._paginate")
    def test_fetch_dashboards_per_dashboard_error(
        self, mock_paginate, cloudwatch_fetcher
    ):
        """Test per-dashboard error handling."""
        mock_paginate.return_value = [
            {
                "DashboardName": "Dashboard1",
                "DashboardArn": "arn:aws:cloudwatch::123:dashboard/D1",
            },
            {
                # Invalid dashboard data
            },
        ]

        # Make get_dashboard succeed for first dashboard
        cloudwatch_fetcher.client.get_dashboard = Mock(
            return_value={"DashboardBody": '{"widgets": []}'}
        )

        dashboards = cloudwatch_fetcher._fetch_dashboards()

        # Should get first dashboard, skip invalid one
        assert len(dashboards) >= 1


class TestCloudWatchFetcherAdditionalCoverage:
    """Additional tests for coverage."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock boto3 session."""
        return Mock()

    @pytest.fixture
    def fetcher(self, mock_session):
        """Create a CloudWatch fetcher instance."""
        return CloudWatchFetcher(session=mock_session, region="us-east-1")

    def test_fetch_log_groups_fallback_no_paginator(self, fetcher):
        """Test log groups fetching fallback when paginator not available."""
        mock_logs_client = Mock()

        with patch.object(
            fetcher, "_create_logs_client", return_value=mock_logs_client
        ):
            mock_logs_client.can_paginate.return_value = False
            mock_logs_client.describe_log_groups.return_value = {
                "logGroups": [
                    {
                        "logGroupName": "/aws/lambda/test-function",
                        "arn": "arn:aws:logs:us-east-1:123456789012:log-group:/aws/lambda/test-function",
                        "creationTime": 1640995200000,
                    }
                ]
            }

            log_groups = fetcher._fetch_log_groups()

            assert len(log_groups) == 1
            assert log_groups[0].log_group_name == "/aws/lambda/test-function"

    def test_fetch_log_groups_fallback_client_error(self, fetcher):
        """Test log groups fetching fallback with ClientError."""
        mock_logs_client = Mock()

        with patch.object(
            fetcher, "_create_logs_client", return_value=mock_logs_client
        ):
            mock_logs_client.can_paginate.return_value = False
            mock_logs_client.describe_log_groups.side_effect = ClientError(
                {"Error": {"Code": "AccessDenied", "Message": "Access denied"}},
                "DescribeLogGroups",
            )

            log_groups = fetcher._fetch_log_groups()

            assert log_groups == []

    def test_fetch_log_groups_outer_exception(self, fetcher):
        """Test log groups fetching with outer exception."""
        with patch.object(fetcher, "_create_logs_client") as mock_create:
            mock_create.side_effect = Exception("Failed to create client")

            log_groups = fetcher._fetch_log_groups()

            assert log_groups == []

    def test_fetch_alarms_client_error(self, fetcher):
        """Test alarms fetching with ClientError."""
        with patch.object(fetcher, "_paginate") as mock_paginate:
            mock_paginate.side_effect = ClientError(
                {"Error": {"Code": "AccessDenied", "Message": "Access denied"}},
                "DescribeAlarms",
            )

            alarms = fetcher._fetch_alarms()

            assert alarms == []

    def test_fetch_dashboards_client_error(self, fetcher):
        """Test dashboards fetching with ClientError."""
        with patch.object(fetcher, "_paginate") as mock_paginate:
            mock_paginate.side_effect = ClientError(
                {"Error": {"Code": "AccessDenied", "Message": "Access denied"}},
                "ListDashboards",
            )

            dashboards = fetcher._fetch_dashboards()

            assert dashboards == []

    def test_fetch_log_groups_fallback_multiple_groups(self, fetcher):
        """Test log groups fetching fallback with multiple groups."""
        mock_logs_client = Mock()

        with patch.object(
            fetcher, "_create_logs_client", return_value=mock_logs_client
        ):
            mock_logs_client.can_paginate.return_value = False
            mock_logs_client.describe_log_groups.return_value = {
                "logGroups": [
                    {
                        "logGroupName": "/aws/lambda/func1",
                        "arn": "arn:aws:logs:us-east-1:123456789012:log-group:/aws/lambda/func1",
                        "creationTime": 1640995200000,
                    },
                    {
                        "logGroupName": "/aws/lambda/func2",
                        "arn": "arn:aws:logs:us-east-1:123456789012:log-group:/aws/lambda/func2",
                        "creationTime": 1640995200000,
                    },
                ]
            }

            log_groups = fetcher._fetch_log_groups()

            assert len(log_groups) == 2
            names = [lg.log_group_name for lg in log_groups]
            assert "/aws/lambda/func1" in names
            assert "/aws/lambda/func2" in names
