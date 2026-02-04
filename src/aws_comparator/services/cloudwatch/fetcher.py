"""
AWS CloudWatch service fetcher.

This module implements fetching of CloudWatch resources including alarms,
log groups, and dashboards.
"""

from typing import Any

from botocore.exceptions import ClientError

from aws_comparator.core.registry import ServiceRegistry
from aws_comparator.models.cloudwatch import CloudWatchAlarm, Dashboard, LogGroup
from aws_comparator.models.common import AWSResource
from aws_comparator.services.base import BaseServiceFetcher


@ServiceRegistry.register(
    "cloudwatch",
    description="Amazon CloudWatch - Monitoring and Observability",
    resource_types=["alarms", "log_groups", "dashboards"],
)
class CloudWatchFetcher(BaseServiceFetcher):
    """
    Fetcher for AWS CloudWatch resources.

    This fetcher retrieves CloudWatch resources including:
    - CloudWatch alarms (metric and composite)
    - CloudWatch Logs log groups
    - CloudWatch dashboards
    """

    SERVICE_NAME = "cloudwatch"

    def _create_client(self) -> Any:
        """
        Create boto3 CloudWatch client.

        Returns:
            Configured boto3 CloudWatch client
        """
        return self.session.client("cloudwatch", region_name=self.region)

    def _create_logs_client(self) -> Any:
        """
        Create boto3 CloudWatch Logs client.

        Returns:
            Configured boto3 CloudWatch Logs client
        """
        return self.session.client("logs", region_name=self.region)

    def fetch_resources(self) -> dict[str, list[AWSResource]]:
        """
        Fetch all CloudWatch resources.

        Returns:
            Dictionary mapping resource types to lists of resources
        """
        return {
            "alarms": self._safe_fetch("alarms", self._fetch_alarms),
            "log_groups": self._safe_fetch("log_groups", self._fetch_log_groups),
            "dashboards": self._safe_fetch("dashboards", self._fetch_dashboards),
        }

    def get_resource_types(self) -> list[str]:
        """
        Get list of resource types handled by this fetcher.

        Returns:
            List of resource type names
        """
        return ["alarms", "log_groups", "dashboards"]

    def _fetch_alarms(self) -> list[CloudWatchAlarm]:
        """
        Fetch all CloudWatch alarms.

        Returns:
            List of CloudWatchAlarm resources
        """
        alarms: list[CloudWatchAlarm] = []

        try:
            # Use pagination to fetch all alarms
            alarm_data_list = self._paginate("describe_alarms", "MetricAlarms")

            self.logger.info(f"Found {len(alarm_data_list)} CloudWatch alarms")

            for alarm_data in alarm_data_list:
                try:
                    # Create CloudWatchAlarm instance
                    alarm = CloudWatchAlarm.from_aws_response(alarm_data)
                    alarms.append(alarm)

                    self.logger.debug(f"Fetched alarm: {alarm.alarm_name}")

                except Exception as e:
                    alarm_name = alarm_data.get("AlarmName", "unknown")
                    self.logger.error(
                        f"Error parsing alarm {alarm_name}: {e}", exc_info=True
                    )

        except Exception as e:
            self.logger.error(f"Failed to fetch CloudWatch alarms: {e}", exc_info=True)

        return alarms

    def _fetch_log_groups(self) -> list[LogGroup]:
        """
        Fetch all CloudWatch Logs log groups.

        Returns:
            List of LogGroup resources
        """
        log_groups: list[LogGroup] = []

        try:
            # Create logs client
            logs_client = self._create_logs_client()

            # Check if logs client can paginate
            if logs_client.can_paginate("describe_log_groups"):
                paginator = logs_client.get_paginator("describe_log_groups")
                log_group_data_list: list[dict[str, Any]] = []

                self.logger.debug("Paginating describe_log_groups")

                for page in paginator.paginate():
                    log_group_data_list.extend(page.get("logGroups", []))

                self.logger.info(
                    f"Found {len(log_group_data_list)} CloudWatch log groups"
                )

                for log_group_data in log_group_data_list:
                    try:
                        # Create LogGroup instance
                        log_group = LogGroup.from_aws_response(log_group_data)
                        log_groups.append(log_group)

                        self.logger.debug(
                            f"Fetched log group: {log_group.log_group_name}"
                        )

                    except Exception as e:
                        log_group_name = log_group_data.get("logGroupName", "unknown")
                        self.logger.error(
                            f"Error parsing log group {log_group_name}: {e}",
                            exc_info=True,
                        )

            else:
                # Fallback to non-paginated call
                response = logs_client.describe_log_groups()
                log_group_data_list = response.get("logGroups", [])

                self.logger.info(
                    f"Found {len(log_group_data_list)} CloudWatch log groups"
                )

                for log_group_data in log_group_data_list:
                    try:
                        log_group = LogGroup.from_aws_response(log_group_data)
                        log_groups.append(log_group)
                    except Exception as e:
                        log_group_name = log_group_data.get("logGroupName", "unknown")
                        self.logger.error(
                            f"Error parsing log group {log_group_name}: {e}",
                            exc_info=True,
                        )

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code in ["AccessDenied", "UnauthorizedOperation"]:
                self.logger.warning(
                    f"Permission denied for CloudWatch Logs: {error_code}"
                )
            else:
                self.logger.error(f"AWS error fetching log groups: {e}", exc_info=True)

        except Exception as e:
            self.logger.error(
                f"Failed to fetch CloudWatch log groups: {e}", exc_info=True
            )

        return log_groups

    def _fetch_dashboards(self) -> list[Dashboard]:
        """
        Fetch all CloudWatch dashboards.

        Returns:
            List of Dashboard resources
        """
        dashboards: list[Dashboard] = []

        try:
            # Use pagination to fetch all dashboards
            dashboard_data_list = self._paginate("list_dashboards", "DashboardEntries")

            self.logger.info(f"Found {len(dashboard_data_list)} CloudWatch dashboards")

            for dashboard_data in dashboard_data_list:
                try:
                    dashboard_name = dashboard_data["DashboardName"]

                    # Optionally fetch dashboard details (body)
                    # Note: This can be expensive for many dashboards
                    dashboard_details = None
                    try:
                        if self.client is None:
                            continue
                        details_response = self.client.get_dashboard(
                            DashboardName=dashboard_name
                        )
                        dashboard_details = details_response
                    except ClientError as e:
                        error_code = e.response.get("Error", {}).get("Code", "")
                        if error_code not in ["ResourceNotFound", "DashboardNotFound"]:
                            self.logger.warning(
                                f"Could not fetch details for dashboard {dashboard_name}: {error_code}"
                            )

                    # Create Dashboard instance
                    dashboard = Dashboard.from_aws_response(
                        dashboard_data, dashboard_details
                    )
                    dashboards.append(dashboard)

                    self.logger.debug(f"Fetched dashboard: {dashboard_name}")

                except Exception as e:
                    dashboard_name = dashboard_data.get("DashboardName", "unknown")
                    self.logger.error(
                        f"Error parsing dashboard {dashboard_name}: {e}", exc_info=True
                    )

        except Exception as e:
            self.logger.error(
                f"Failed to fetch CloudWatch dashboards: {e}", exc_info=True
            )

        return dashboards
