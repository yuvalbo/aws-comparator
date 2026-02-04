"""
AWS EventBridge service fetcher.

This module implements fetching of EventBridge event buses, rules, targets,
archives, and connections.
"""

import json
from typing import Any

from botocore.exceptions import ClientError

from aws_comparator.core.registry import ServiceRegistry
from aws_comparator.models.common import AWSResource
from aws_comparator.models.eventbridge import (
    Archive,
    Connection,
    EventBus,
    Rule,
)
from aws_comparator.services.base import BaseServiceFetcher


@ServiceRegistry.register(
    "eventbridge",
    description="Amazon EventBridge",
    resource_types=["event_buses", "rules", "archives", "connections"],
)
class EventBridgeFetcher(BaseServiceFetcher):
    """
    Fetcher for AWS EventBridge resources.

    This fetcher retrieves EventBridge information including:
    - Event buses (default and custom)
    - Rules with their targets
    - Archives for event replay
    - Connections for API destinations
    """

    SERVICE_NAME = "eventbridge"

    def _create_client(self) -> Any:
        """
        Create boto3 EventBridge client.

        Returns:
            Configured boto3 EventBridge (events) client
        """
        return self.session.client("events", region_name=self.region)

    def fetch_resources(self) -> dict[str, list[AWSResource]]:
        """
        Fetch all EventBridge resources.

        Returns:
            Dictionary mapping resource types to lists of resources
        """
        return {
            "event_buses": self._safe_fetch("event_buses", self._fetch_event_buses),
            "rules": self._safe_fetch("rules", self._fetch_rules),
            "archives": self._safe_fetch("archives", self._fetch_archives),
            "connections": self._safe_fetch("connections", self._fetch_connections),
        }

    def get_resource_types(self) -> list[str]:
        """
        Get list of resource types handled by this fetcher.

        Returns:
            List of resource type names
        """
        return ["event_buses", "rules", "archives", "connections"]

    def _fetch_event_buses(self) -> list[EventBus]:
        """
        Fetch all EventBridge event buses.

        Returns:
            List of EventBus resources
        """
        event_buses: list[EventBus] = []

        try:
            # Use pagination to list all event buses
            results = self._paginate("list_event_buses", "EventBuses")

            self.logger.info(f"Found {len(results)} EventBridge event buses")

            for bus_data in results:
                try:
                    bus_name = bus_data["Name"]

                    # Get event bus details including policy
                    try:
                        if self.client is None:
                            continue
                        describe_response = self.client.describe_event_bus(
                            Name=bus_name
                        )
                        # Parse policy if it's a string
                        if "Policy" in describe_response:
                            policy_text = describe_response["Policy"]
                            if isinstance(policy_text, str):
                                describe_response["Policy"] = json.loads(policy_text)

                        # Merge with list data
                        bus_data.update(describe_response)
                    except ClientError:
                        # Policy may not exist or access denied
                        pass

                    # Get tags
                    try:
                        if "Arn" in bus_data and self.client is not None:
                            tag_response = self.client.list_tags_for_resource(
                                ResourceARN=bus_data["Arn"]
                            )
                            tags = tag_response.get("Tags", [])
                            bus_data["Tags"] = self._normalize_tags(tags)
                    except ClientError:
                        # Tags may not be accessible
                        pass

                    # Create EventBus instance
                    event_bus = EventBus.from_aws_response(bus_data)
                    if hasattr(event_bus, "tags") and "Tags" in bus_data:
                        event_bus.tags = bus_data["Tags"]

                    event_buses.append(event_bus)

                    self.logger.debug(f"Fetched event bus: {bus_name}")

                except ClientError as e:
                    error_code = e.response.get("Error", {}).get("Code", "")
                    bus_name = bus_data.get("Name", "unknown")
                    if error_code in ["AccessDenied", "ResourceNotFoundException"]:
                        self.logger.warning(
                            f"Cannot access event bus {bus_name}: {error_code}"
                        )
                    else:
                        self.logger.error(
                            f"Error fetching event bus {bus_name}: {e}", exc_info=True
                        )

        except Exception as e:
            self.logger.error(
                f"Failed to list EventBridge event buses: {e}", exc_info=True
            )

        return event_buses

    def _fetch_rules(self) -> list[Rule]:
        """
        Fetch all EventBridge rules across all event buses.

        Returns:
            List of Rule resources
        """
        rules: list[Rule] = []

        try:
            # First, get all event buses
            event_buses = self._paginate("list_event_buses", "EventBuses")
            bus_names = [bus["Name"] for bus in event_buses]

            self.logger.info(f"Fetching rules from {len(bus_names)} event buses")

            for bus_name in bus_names:
                try:
                    # List rules for this event bus
                    bus_rules = self._paginate(
                        "list_rules", "Rules", EventBusName=bus_name
                    )

                    self.logger.debug(f"Found {len(bus_rules)} rules in bus {bus_name}")

                    for rule_data in bus_rules:
                        try:
                            rule_name = rule_data["Name"]

                            # Get rule details
                            try:
                                if self.client is None:
                                    continue
                                describe_response = self.client.describe_rule(
                                    Name=rule_name, EventBusName=bus_name
                                )
                                rule_data.update(describe_response)
                            except ClientError:
                                # Use data from list operation
                                pass

                            # Get targets for this rule
                            targets = []
                            try:
                                if self.client is None:
                                    continue
                                target_response = self.client.list_targets_by_rule(
                                    Rule=rule_name, EventBusName=bus_name
                                )
                                targets = target_response.get("Targets", [])
                            except ClientError:
                                # Targets may not be accessible
                                pass

                            # Get tags
                            try:
                                if "Arn" in rule_data and self.client is not None:
                                    tag_response = self.client.list_tags_for_resource(
                                        ResourceARN=rule_data["Arn"]
                                    )
                                    tags = tag_response.get("Tags", [])
                                    rule_data["Tags"] = self._normalize_tags(tags)
                            except ClientError:
                                # Tags may not be accessible
                                pass

                            # Create Rule instance
                            rule = Rule.from_aws_response(rule_data, targets)
                            if hasattr(rule, "tags") and "Tags" in rule_data:
                                rule.tags = rule_data["Tags"]

                            rules.append(rule)

                            self.logger.debug(
                                f"Fetched rule: {rule_name} from bus {bus_name}"
                            )

                        except ClientError as e:
                            error_code = e.response.get("Error", {}).get("Code", "")
                            rule_name = rule_data.get("Name", "unknown")
                            if error_code in [
                                "AccessDenied",
                                "ResourceNotFoundException",
                            ]:
                                self.logger.warning(
                                    f"Cannot access rule {rule_name}: {error_code}"
                                )
                            else:
                                self.logger.error(
                                    f"Error fetching rule {rule_name}: {e}",
                                    exc_info=True,
                                )

                except ClientError as e:
                    error_code = e.response.get("Error", {}).get("Code", "")
                    if error_code in ["AccessDenied"]:
                        self.logger.warning(
                            f"Cannot access rules for bus {bus_name}: {error_code}"
                        )
                    else:
                        self.logger.error(
                            f"Error listing rules for bus {bus_name}: {e}",
                            exc_info=True,
                        )

            self.logger.info(f"Fetched total of {len(rules)} EventBridge rules")

        except Exception as e:
            self.logger.error(f"Failed to fetch EventBridge rules: {e}", exc_info=True)

        return rules

    def _fetch_archives(self) -> list[Archive]:
        """
        Fetch all EventBridge archives.

        Returns:
            List of Archive resources
        """
        archives: list[Archive] = []

        try:
            # Use pagination to list all archives
            results = self._paginate("list_archives", "Archives")

            self.logger.info(f"Found {len(results)} EventBridge archives")

            for archive_data in results:
                try:
                    archive_name = archive_data["ArchiveName"]

                    # Get archive details
                    try:
                        if self.client is None:
                            continue
                        describe_response = self.client.describe_archive(
                            ArchiveName=archive_name
                        )
                        archive_data.update(describe_response)
                    except ClientError:
                        # Use data from list operation
                        pass

                    # Get tags
                    try:
                        if "ArchiveArn" in archive_data and self.client is not None:
                            tag_response = self.client.list_tags_for_resource(
                                ResourceARN=archive_data["ArchiveArn"]
                            )
                            tags = tag_response.get("Tags", [])
                            archive_data["Tags"] = self._normalize_tags(tags)
                    except ClientError:
                        # Tags may not be accessible
                        pass

                    # Create Archive instance
                    archive = Archive.from_aws_response(archive_data)
                    if hasattr(archive, "tags") and "Tags" in archive_data:
                        archive.tags = archive_data["Tags"]

                    archives.append(archive)

                    self.logger.debug(f"Fetched archive: {archive_name}")

                except ClientError as e:
                    error_code = e.response.get("Error", {}).get("Code", "")
                    archive_name = archive_data.get("ArchiveName", "unknown")
                    if error_code in ["AccessDenied", "ResourceNotFoundException"]:
                        self.logger.warning(
                            f"Cannot access archive {archive_name}: {error_code}"
                        )
                    else:
                        self.logger.error(
                            f"Error fetching archive {archive_name}: {e}", exc_info=True
                        )

        except Exception as e:
            self.logger.error(
                f"Failed to list EventBridge archives: {e}", exc_info=True
            )

        return archives

    def _fetch_connections(self) -> list[Connection]:
        """
        Fetch all EventBridge connections.

        Returns:
            List of Connection resources
        """
        connections: list[Connection] = []

        try:
            # Use pagination to list all connections
            results = self._paginate("list_connections", "Connections")

            self.logger.info(f"Found {len(results)} EventBridge connections")

            for connection_data in results:
                try:
                    connection_name = connection_data["Name"]

                    # Get connection details
                    try:
                        if self.client is None:
                            continue
                        describe_response = self.client.describe_connection(
                            Name=connection_name
                        )
                        connection_data.update(describe_response)
                    except ClientError:
                        # Use data from list operation
                        pass

                    # Get tags
                    try:
                        if (
                            "ConnectionArn" in connection_data
                            and self.client is not None
                        ):
                            tag_response = self.client.list_tags_for_resource(
                                ResourceARN=connection_data["ConnectionArn"]
                            )
                            tags = tag_response.get("Tags", [])
                            connection_data["Tags"] = self._normalize_tags(tags)
                    except ClientError:
                        # Tags may not be accessible
                        pass

                    # Create Connection instance
                    connection = Connection.from_aws_response(connection_data)
                    if hasattr(connection, "tags") and "Tags" in connection_data:
                        connection.tags = connection_data["Tags"]

                    connections.append(connection)

                    self.logger.debug(f"Fetched connection: {connection_name}")

                except ClientError as e:
                    error_code = e.response.get("Error", {}).get("Code", "")
                    connection_name = connection_data.get("Name", "unknown")
                    if error_code in ["AccessDenied", "ResourceNotFoundException"]:
                        self.logger.warning(
                            f"Cannot access connection {connection_name}: {error_code}"
                        )
                    else:
                        self.logger.error(
                            f"Error fetching connection {connection_name}: {e}",
                            exc_info=True,
                        )

        except Exception as e:
            self.logger.error(
                f"Failed to list EventBridge connections: {e}", exc_info=True
            )

        return connections
