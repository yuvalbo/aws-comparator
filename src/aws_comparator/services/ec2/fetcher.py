"""
AWS EC2 service fetcher.

This module implements fetching of EC2 resources including instances,
security groups, VPCs, subnets, route tables, network ACLs, and key pairs.
"""

from typing import Any

from aws_comparator.core.registry import ServiceRegistry
from aws_comparator.models.common import AWSResource
from aws_comparator.models.ec2 import (
    EC2Instance,
    KeyPair,
    NetworkAcl,
    RouteTable,
    SecurityGroup,
    Subnet,
    VPC,
)
from aws_comparator.services.base import BaseServiceFetcher


@ServiceRegistry.register(
    'ec2',
    description='Amazon EC2 (Elastic Compute Cloud)',
    resource_types=['instances', 'security_groups', 'vpcs', 'subnets', 'route_tables', 'network_acls', 'key_pairs']
)
class EC2Fetcher(BaseServiceFetcher):
    """
    Fetcher for AWS EC2 resources.

    This fetcher retrieves EC2 resource information including:
    - EC2 instances with all configurations
    - Security groups with ingress/egress rules
    - VPCs with CIDR blocks
    - Subnets with availability zones
    - Route tables with routes and associations
    - Network ACLs with rules
    - Key pairs

    All EC2 resources are fetched with proper pagination and error handling.
    """

    SERVICE_NAME = "ec2"

    def _create_client(self) -> Any:
        """
        Create boto3 EC2 client.

        Returns:
            Configured boto3 EC2 client
        """
        return self.session.client('ec2', region_name=self.region)

    def fetch_resources(self) -> dict[str, list[AWSResource]]:
        """
        Fetch all EC2 resources.

        Returns:
            Dictionary mapping resource types to lists of resources
        """
        return {
            'instances': self._safe_fetch('instances', self._fetch_instances),
            'security_groups': self._safe_fetch('security_groups', self._fetch_security_groups),
            'vpcs': self._safe_fetch('vpcs', self._fetch_vpcs),
            'subnets': self._safe_fetch('subnets', self._fetch_subnets),
            'route_tables': self._safe_fetch('route_tables', self._fetch_route_tables),
            'network_acls': self._safe_fetch('network_acls', self._fetch_network_acls),
            'key_pairs': self._safe_fetch('key_pairs', self._fetch_key_pairs),
        }

    def get_resource_types(self) -> list[str]:
        """
        Get list of resource types handled by this fetcher.

        Returns:
            List of resource type names
        """
        return [
            'instances',
            'security_groups',
            'vpcs',
            'subnets',
            'route_tables',
            'network_acls',
            'key_pairs'
        ]

    def _fetch_instances(self) -> list[EC2Instance]:
        """
        Fetch all EC2 instances.

        Returns:
            List of EC2Instance resources

        Note:
            Uses pagination to handle large numbers of instances.
            Normalizes tags from AWS format to dict format.
        """
        instances: list[EC2Instance] = []

        try:
            # Use pagination for describe_instances
            reservations = self._paginate('describe_instances', 'Reservations')
            self.logger.info(f"Found {len(reservations)} reservation(s)")

            instance_count = 0
            for reservation in reservations:
                for instance_data in reservation.get('Instances', []):
                    try:
                        # Normalize tags
                        tags_list = instance_data.get('Tags', [])
                        tags = {tag['Key']: tag['Value'] for tag in tags_list}

                        # Create instance model
                        instance = EC2Instance.from_aws_response(instance_data, tags)
                        instances.append(instance)
                        instance_count += 1

                        self.logger.debug(
                            f"Fetched instance: {instance.instance_id} "
                            f"({instance.instance_type}, {instance.state})"
                        )

                    except Exception as e:
                        instance_id = instance_data.get('InstanceId', 'unknown')
                        self.logger.error(
                            f"Error parsing instance {instance_id}: {e}",
                            exc_info=True
                        )

            self.logger.info(f"Fetched {instance_count} EC2 instances")

        except Exception as e:
            self.logger.error(f"Failed to list EC2 instances: {e}", exc_info=True)

        return instances

    def _fetch_security_groups(self) -> list[SecurityGroup]:
        """
        Fetch all security groups.

        Returns:
            List of SecurityGroup resources

        Note:
            Includes both ingress and egress rules for each security group.
        """
        security_groups: list[SecurityGroup] = []

        try:
            sg_list = self._paginate('describe_security_groups', 'SecurityGroups')
            self.logger.info(f"Found {len(sg_list)} security group(s)")

            for sg_data in sg_list:
                try:
                    # Normalize tags
                    tags_list = sg_data.get('Tags', [])
                    tags = {tag['Key']: tag['Value'] for tag in tags_list}

                    # Create security group model
                    sg = SecurityGroup.from_aws_response(sg_data, tags)
                    security_groups.append(sg)

                    self.logger.debug(
                        f"Fetched security group: {sg.group_id} ({sg.group_name}) "
                        f"with {len(sg.ingress_rules)} ingress and {len(sg.egress_rules)} egress rules"
                    )

                except Exception as e:
                    sg_id = sg_data.get('GroupId', 'unknown')
                    self.logger.error(
                        f"Error parsing security group {sg_id}: {e}",
                        exc_info=True
                    )

            self.logger.info(f"Fetched {len(security_groups)} security groups")

        except Exception as e:
            self.logger.error(f"Failed to list security groups: {e}", exc_info=True)

        return security_groups

    def _fetch_vpcs(self) -> list[VPC]:
        """
        Fetch all VPCs.

        Returns:
            List of VPC resources

        Note:
            Includes CIDR block associations and default VPC indicator.
        """
        vpcs: list[VPC] = []

        try:
            vpc_list = self._paginate('describe_vpcs', 'Vpcs')
            self.logger.info(f"Found {len(vpc_list)} VPC(s)")

            for vpc_data in vpc_list:
                try:
                    # Normalize tags
                    tags_list = vpc_data.get('Tags', [])
                    tags = {tag['Key']: tag['Value'] for tag in tags_list}

                    # Create VPC model
                    vpc = VPC.from_aws_response(vpc_data, tags)
                    vpcs.append(vpc)

                    self.logger.debug(
                        f"Fetched VPC: {vpc.vpc_id} ({vpc.cidr_block}) "
                        f"default={vpc.is_default}"
                    )

                except Exception as e:
                    vpc_id = vpc_data.get('VpcId', 'unknown')
                    self.logger.error(
                        f"Error parsing VPC {vpc_id}: {e}",
                        exc_info=True
                    )

            self.logger.info(f"Fetched {len(vpcs)} VPCs")

        except Exception as e:
            self.logger.error(f"Failed to list VPCs: {e}", exc_info=True)

        return vpcs

    def _fetch_subnets(self) -> list[Subnet]:
        """
        Fetch all subnets.

        Returns:
            List of Subnet resources

        Note:
            Includes availability zone and IP address availability information.
        """
        subnets: list[Subnet] = []

        try:
            subnet_list = self._paginate('describe_subnets', 'Subnets')
            self.logger.info(f"Found {len(subnet_list)} subnet(s)")

            for subnet_data in subnet_list:
                try:
                    # Normalize tags
                    tags_list = subnet_data.get('Tags', [])
                    tags = {tag['Key']: tag['Value'] for tag in tags_list}

                    # Create subnet model
                    subnet = Subnet.from_aws_response(subnet_data, tags)
                    subnets.append(subnet)

                    self.logger.debug(
                        f"Fetched subnet: {subnet.subnet_id} in {subnet.availability_zone} "
                        f"({subnet.cidr_block})"
                    )

                except Exception as e:
                    subnet_id = subnet_data.get('SubnetId', 'unknown')
                    self.logger.error(
                        f"Error parsing subnet {subnet_id}: {e}",
                        exc_info=True
                    )

            self.logger.info(f"Fetched {len(subnets)} subnets")

        except Exception as e:
            self.logger.error(f"Failed to list subnets: {e}", exc_info=True)

        return subnets

    def _fetch_route_tables(self) -> list[RouteTable]:
        """
        Fetch all route tables.

        Returns:
            List of RouteTable resources

        Note:
            Includes routes and subnet associations for each route table.
        """
        route_tables: list[RouteTable] = []

        try:
            rt_list = self._paginate('describe_route_tables', 'RouteTables')
            self.logger.info(f"Found {len(rt_list)} route table(s)")

            for rt_data in rt_list:
                try:
                    # Normalize tags
                    tags_list = rt_data.get('Tags', [])
                    tags = {tag['Key']: tag['Value'] for tag in tags_list}

                    # Create route table model
                    rt = RouteTable.from_aws_response(rt_data, tags)
                    route_tables.append(rt)

                    self.logger.debug(
                        f"Fetched route table: {rt.route_table_id} "
                        f"with {len(rt.routes)} route(s)"
                    )

                except Exception as e:
                    rt_id = rt_data.get('RouteTableId', 'unknown')
                    self.logger.error(
                        f"Error parsing route table {rt_id}: {e}",
                        exc_info=True
                    )

            self.logger.info(f"Fetched {len(route_tables)} route tables")

        except Exception as e:
            self.logger.error(f"Failed to list route tables: {e}", exc_info=True)

        return route_tables

    def _fetch_network_acls(self) -> list[NetworkAcl]:
        """
        Fetch all network ACLs.

        Returns:
            List of NetworkAcl resources

        Note:
            Includes ACL entries (rules) and subnet associations.
        """
        network_acls: list[NetworkAcl] = []

        try:
            nacl_list = self._paginate('describe_network_acls', 'NetworkAcls')
            self.logger.info(f"Found {len(nacl_list)} network ACL(s)")

            for nacl_data in nacl_list:
                try:
                    # Normalize tags
                    tags_list = nacl_data.get('Tags', [])
                    tags = {tag['Key']: tag['Value'] for tag in tags_list}

                    # Create network ACL model
                    nacl = NetworkAcl.from_aws_response(nacl_data, tags)
                    network_acls.append(nacl)

                    self.logger.debug(
                        f"Fetched network ACL: {nacl.network_acl_id} "
                        f"with {len(nacl.entries)} entry(ies)"
                    )

                except Exception as e:
                    nacl_id = nacl_data.get('NetworkAclId', 'unknown')
                    self.logger.error(
                        f"Error parsing network ACL {nacl_id}: {e}",
                        exc_info=True
                    )

            self.logger.info(f"Fetched {len(network_acls)} network ACLs")

        except Exception as e:
            self.logger.error(f"Failed to list network ACLs: {e}", exc_info=True)

        return network_acls

    def _fetch_key_pairs(self) -> list[KeyPair]:
        """
        Fetch all key pairs.

        Returns:
            List of KeyPair resources

        Note:
            Only metadata is fetched - private keys are never retrieved.
        """
        key_pairs: list[KeyPair] = []

        try:
            key_list = self._paginate('describe_key_pairs', 'KeyPairs')
            self.logger.info(f"Found {len(key_list)} key pair(s)")

            for key_data in key_list:
                try:
                    # Normalize tags
                    tags_list = key_data.get('Tags', [])
                    tags = {tag['Key']: tag['Value'] for tag in tags_list}

                    # Create key pair model
                    key_pair = KeyPair.from_aws_response(key_data, tags)
                    key_pairs.append(key_pair)

                    self.logger.debug(
                        f"Fetched key pair: {key_pair.key_name} ({key_pair.key_type})"
                    )

                except Exception as e:
                    key_name = key_data.get('KeyName', 'unknown')
                    self.logger.error(
                        f"Error parsing key pair {key_name}: {e}",
                        exc_info=True
                    )

            self.logger.info(f"Fetched {len(key_pairs)} key pairs")

        except Exception as e:
            self.logger.error(f"Failed to list key pairs: {e}", exc_info=True)

        return key_pairs
