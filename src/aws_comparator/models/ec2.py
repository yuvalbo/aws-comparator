"""
Pydantic models for AWS EC2 service resources.

This module defines strongly-typed models for EC2 instances, security groups,
VPCs, subnets, route tables, network ACLs, and key pairs.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from aws_comparator.models.common import AWSResource


class InstanceState(str, Enum):
    """EC2 instance states."""
    PENDING = "pending"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    SHUTTING_DOWN = "shutting-down"
    TERMINATED = "terminated"


class VolumeType(str, Enum):
    """EBS volume types."""
    GP2 = "gp2"
    GP3 = "gp3"
    IO1 = "io1"
    IO2 = "io2"
    ST1 = "st1"
    SC1 = "sc1"
    STANDARD = "standard"


class IpPermission(BaseModel):
    """
    Security group rule (ingress or egress).

    Represents a single rule allowing traffic based on protocol, port, and source/destination.
    """
    model_config = ConfigDict(extra="ignore")

    ip_protocol: str = Field(..., description="IP protocol (tcp, udp, icmp, or -1 for all)")
    from_port: Optional[int] = Field(None, ge=-1, le=65535, description="Start of port range")
    to_port: Optional[int] = Field(None, ge=-1, le=65535, description="End of port range")
    cidr_blocks: list[str] = Field(default_factory=list, description="IPv4 CIDR blocks")
    ipv6_cidr_blocks: list[str] = Field(default_factory=list, description="IPv6 CIDR blocks")
    source_security_groups: list[str] = Field(
        default_factory=list,
        description="Source security group IDs"
    )
    description: Optional[str] = Field(None, description="Rule description")

    def __str__(self) -> str:
        """Return string representation of IP permission."""
        if self.from_port == self.to_port:
            ports = f"port {self.from_port}"
        elif self.from_port is not None and self.to_port is not None:
            ports = f"ports {self.from_port}-{self.to_port}"
        else:
            ports = "all ports"

        sources = []
        if self.cidr_blocks:
            sources.extend(self.cidr_blocks)
        if self.source_security_groups:
            sources.extend(self.source_security_groups)

        return f"{self.ip_protocol} {ports} from {', '.join(sources) if sources else 'any'}"


class EC2Instance(AWSResource):
    """
    EC2 instance resource model.

    Represents an AWS EC2 instance with all its configuration properties.
    """
    model_config = ConfigDict(extra="ignore")

    # Basic properties
    instance_id: str = Field(..., pattern=r'^i-[a-f0-9]+$', description="Instance ID")
    instance_type: str = Field(..., description="Instance type (e.g., t2.micro)")
    state: InstanceState = Field(..., description="Current instance state")
    ami_id: str = Field(..., pattern=r'^ami-[a-f0-9]+$', description="AMI ID")

    # Network properties
    vpc_id: Optional[str] = Field(None, pattern=r'^vpc-[a-f0-9]+$', description="VPC ID")
    subnet_id: Optional[str] = Field(
        None,
        pattern=r'^subnet-[a-f0-9]+$',
        description="Subnet ID"
    )
    private_ip_address: Optional[str] = Field(None, description="Private IP address")
    public_ip_address: Optional[str] = Field(None, description="Public IP address")
    private_dns_name: Optional[str] = Field(None, description="Private DNS name")
    public_dns_name: Optional[str] = Field(None, description="Public DNS name")
    security_groups: list[str] = Field(default_factory=list, description="Security group IDs")

    # Configuration
    key_name: Optional[str] = Field(None, description="SSH key pair name")
    iam_instance_profile: Optional[str] = Field(None, description="IAM instance profile ARN")
    availability_zone: Optional[str] = Field(None, description="Availability zone")
    platform: Optional[str] = Field(None, description="Platform (e.g., windows)")
    architecture: Optional[str] = Field(None, description="Architecture (x86_64, arm64)")
    root_device_type: Optional[str] = Field(None, description="Root device type (ebs, instance-store)")
    virtualization_type: Optional[str] = Field(None, description="Virtualization type (hvm, paravirtual)")
    monitoring_state: Optional[str] = Field(None, description="CloudWatch monitoring state")
    tenancy: Optional[str] = Field(None, description="Tenancy (default, dedicated, host)")
    launch_time: Optional[datetime] = Field(None, description="Launch timestamp")

    @field_validator('instance_id')
    @classmethod
    def validate_instance_id(cls, v: str) -> str:
        """Validate EC2 instance ID format."""
        if not v.startswith('i-'):
            raise ValueError("Instance ID must start with 'i-'")
        return v

    @classmethod
    def from_aws_response(
        cls,
        instance_data: dict[str, Any],
        tags: Optional[dict[str, str]] = None
    ) -> "EC2Instance":
        """
        Create EC2Instance from AWS API response.

        Args:
            instance_data: Instance data from describe_instances response
            tags: Optional pre-normalized tags dictionary

        Returns:
            EC2Instance instance
        """
        # Parse security groups
        security_groups = [sg['GroupId'] for sg in instance_data.get('SecurityGroups', [])]

        # Parse IAM instance profile
        iam_profile = instance_data.get('IamInstanceProfile', {})
        iam_profile_arn = iam_profile.get('Arn') if iam_profile else None

        # Parse monitoring
        monitoring = instance_data.get('Monitoring', {})
        monitoring_state = monitoring.get('State') if monitoring else None

        # Parse tags if not provided
        if tags is None:
            tags_list = instance_data.get('Tags', [])
            tags = {tag['Key']: tag['Value'] for tag in tags_list}

        instance_dict = {
            'instance_id': instance_data['InstanceId'],
            'instance_type': instance_data.get('InstanceType'),
            'state': instance_data['State']['Name'],
            'ami_id': instance_data.get('ImageId'),
            'vpc_id': instance_data.get('VpcId'),
            'subnet_id': instance_data.get('SubnetId'),
            'private_ip_address': instance_data.get('PrivateIpAddress'),
            'public_ip_address': instance_data.get('PublicIpAddress'),
            'private_dns_name': instance_data.get('PrivateDnsName'),
            'public_dns_name': instance_data.get('PublicDnsName'),
            'security_groups': security_groups,
            'key_name': instance_data.get('KeyName'),
            'iam_instance_profile': iam_profile_arn,
            'availability_zone': instance_data.get('Placement', {}).get('AvailabilityZone'),
            'platform': instance_data.get('Platform'),
            'architecture': instance_data.get('Architecture'),
            'root_device_type': instance_data.get('RootDeviceType'),
            'virtualization_type': instance_data.get('VirtualizationType'),
            'monitoring_state': monitoring_state,
            'tenancy': instance_data.get('Placement', {}).get('Tenancy'),
            'launch_time': instance_data.get('LaunchTime'),
            'arn': f"arn:aws:ec2:{instance_data.get('Placement', {}).get('AvailabilityZone', 'unknown')[:-1]}:instance/{instance_data['InstanceId']}",
            'tags': tags,
        }

        return cls(**instance_dict)

    def __str__(self) -> str:
        """Return string representation of EC2 instance."""
        return f"EC2Instance(id={self.instance_id}, type={self.instance_type}, state={self.state})"


class SecurityGroup(AWSResource):
    """
    EC2 security group resource model.

    Represents a security group with ingress and egress rules.
    """
    model_config = ConfigDict(extra="ignore")

    group_id: str = Field(..., pattern=r'^sg-[a-f0-9]+$', description="Security group ID")
    group_name: str = Field(..., min_length=1, description="Security group name")
    description: str = Field(..., description="Security group description")
    vpc_id: str = Field(..., pattern=r'^vpc-[a-f0-9]+$', description="VPC ID")
    ingress_rules: list[IpPermission] = Field(
        default_factory=list,
        description="Inbound rules"
    )
    egress_rules: list[IpPermission] = Field(
        default_factory=list,
        description="Outbound rules"
    )
    owner_id: Optional[str] = Field(None, description="AWS account ID")

    @field_validator('group_id')
    @classmethod
    def validate_group_id(cls, v: str) -> str:
        """Validate security group ID format."""
        if not v.startswith('sg-'):
            raise ValueError("Security group ID must start with 'sg-'")
        return v

    @classmethod
    def from_aws_response(
        cls,
        sg_data: dict[str, Any],
        tags: Optional[dict[str, str]] = None
    ) -> "SecurityGroup":
        """
        Create SecurityGroup from AWS API response.

        Args:
            sg_data: Security group data from describe_security_groups
            tags: Optional pre-normalized tags dictionary

        Returns:
            SecurityGroup instance
        """
        # Parse ingress rules
        ingress_rules = []
        for perm in sg_data.get('IpPermissions', []):
            rule = cls._parse_ip_permission(perm)
            ingress_rules.append(rule)

        # Parse egress rules
        egress_rules = []
        for perm in sg_data.get('IpPermissionsEgress', []):
            rule = cls._parse_ip_permission(perm)
            egress_rules.append(rule)

        # Parse tags if not provided
        if tags is None:
            tags_list = sg_data.get('Tags', [])
            tags = {tag['Key']: tag['Value'] for tag in tags_list}

        sg_dict = {
            'group_id': sg_data['GroupId'],
            'group_name': sg_data.get('GroupName', ''),
            'description': sg_data.get('Description', ''),
            'vpc_id': sg_data.get('VpcId', ''),
            'ingress_rules': ingress_rules,
            'egress_rules': egress_rules,
            'owner_id': sg_data.get('OwnerId'),
            'arn': f"arn:aws:ec2:::security-group/{sg_data['GroupId']}",
            'tags': tags,
        }

        return cls(**sg_dict)

    @staticmethod
    def _parse_ip_permission(perm: dict[str, Any]) -> IpPermission:
        """Parse an IP permission from AWS format."""
        # Extract CIDR blocks
        cidr_blocks = [ip['CidrIp'] for ip in perm.get('IpRanges', [])]
        ipv6_cidr_blocks = [ip['CidrIpv6'] for ip in perm.get('Ipv6Ranges', [])]

        # Extract source security groups
        source_sgs = [
            sg['GroupId'] for sg in perm.get('UserIdGroupPairs', [])
            if 'GroupId' in sg
        ]

        # Get description (may be on the IP range or the permission itself)
        description = None
        if perm.get('IpRanges') and perm['IpRanges']:
            description = perm['IpRanges'][0].get('Description')

        return IpPermission(
            ip_protocol=perm.get('IpProtocol', '-1'),
            from_port=perm.get('FromPort'),
            to_port=perm.get('ToPort'),
            cidr_blocks=cidr_blocks,
            ipv6_cidr_blocks=ipv6_cidr_blocks,
            source_security_groups=source_sgs,
            description=description
        )

    def __str__(self) -> str:
        """Return string representation of security group."""
        return f"SecurityGroup(id={self.group_id}, name={self.group_name}, vpc={self.vpc_id})"


class VPC(AWSResource):
    """
    Virtual Private Cloud (VPC) resource model.

    Represents an AWS VPC with its CIDR blocks and configuration.
    """
    model_config = ConfigDict(extra="ignore")

    vpc_id: str = Field(..., pattern=r'^vpc-[a-f0-9]+$', description="VPC ID")
    cidr_block: str = Field(
        ...,
        pattern=r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}/\d{1,2}$',
        description="Primary CIDR block"
    )
    cidr_block_associations: list[dict[str, str]] = Field(
        default_factory=list,
        description="Additional CIDR block associations"
    )
    state: str = Field(..., description="VPC state")
    is_default: bool = Field(default=False, description="Whether this is the default VPC")
    dhcp_options_id: Optional[str] = Field(None, description="DHCP options set ID")
    instance_tenancy: Optional[str] = Field(None, description="Instance tenancy")
    enable_dns_hostnames: Optional[bool] = Field(None, description="DNS hostnames enabled")
    enable_dns_support: Optional[bool] = Field(None, description="DNS support enabled")
    owner_id: Optional[str] = Field(None, description="AWS account ID")

    @field_validator('vpc_id')
    @classmethod
    def validate_vpc_id(cls, v: str) -> str:
        """Validate VPC ID format."""
        if not v.startswith('vpc-'):
            raise ValueError("VPC ID must start with 'vpc-'")
        return v

    @classmethod
    def from_aws_response(
        cls,
        vpc_data: dict[str, Any],
        tags: Optional[dict[str, str]] = None
    ) -> "VPC":
        """
        Create VPC from AWS API response.

        Args:
            vpc_data: VPC data from describe_vpcs
            tags: Optional pre-normalized tags dictionary

        Returns:
            VPC instance
        """
        # Parse CIDR block associations
        cidr_associations = []
        for assoc in vpc_data.get('CidrBlockAssociationSet', []):
            cidr_associations.append({
                'CidrBlock': assoc.get('CidrBlock', ''),
                'State': assoc.get('CidrBlockState', {}).get('State', ''),
            })

        # Parse tags if not provided
        if tags is None:
            tags_list = vpc_data.get('Tags', [])
            tags = {tag['Key']: tag['Value'] for tag in tags_list}

        vpc_dict = {
            'vpc_id': vpc_data['VpcId'],
            'cidr_block': vpc_data.get('CidrBlock', ''),
            'cidr_block_associations': cidr_associations,
            'state': vpc_data.get('State', ''),
            'is_default': vpc_data.get('IsDefault', False),
            'dhcp_options_id': vpc_data.get('DhcpOptionsId'),
            'instance_tenancy': vpc_data.get('InstanceTenancy'),
            'enable_dns_hostnames': None,  # Needs separate API call
            'enable_dns_support': None,    # Needs separate API call
            'owner_id': vpc_data.get('OwnerId'),
            'arn': f"arn:aws:ec2:::vpc/{vpc_data['VpcId']}",
            'tags': tags,
        }

        return cls(**vpc_dict)

    def __str__(self) -> str:
        """Return string representation of VPC."""
        return f"VPC(id={self.vpc_id}, cidr={self.cidr_block}, default={self.is_default})"


class Subnet(AWSResource):
    """
    VPC subnet resource model.

    Represents a subnet within a VPC.
    """
    model_config = ConfigDict(extra="ignore")

    subnet_id: str = Field(..., pattern=r'^subnet-[a-f0-9]+$', description="Subnet ID")
    vpc_id: str = Field(..., pattern=r'^vpc-[a-f0-9]+$', description="VPC ID")
    cidr_block: str = Field(..., description="Subnet CIDR block")
    availability_zone: str = Field(..., description="Availability zone")
    availability_zone_id: Optional[str] = Field(None, description="Availability zone ID")
    available_ip_address_count: int = Field(ge=0, description="Available IP addresses")
    state: str = Field(..., description="Subnet state")
    map_public_ip_on_launch: bool = Field(
        default=False,
        description="Auto-assign public IP"
    )
    assign_ipv6_address_on_creation: bool = Field(
        default=False,
        description="Auto-assign IPv6"
    )
    default_for_az: bool = Field(default=False, description="Default for AZ")
    owner_id: Optional[str] = Field(None, description="AWS account ID")

    @field_validator('subnet_id')
    @classmethod
    def validate_subnet_id(cls, v: str) -> str:
        """Validate subnet ID format."""
        if not v.startswith('subnet-'):
            raise ValueError("Subnet ID must start with 'subnet-'")
        return v

    @classmethod
    def from_aws_response(
        cls,
        subnet_data: dict[str, Any],
        tags: Optional[dict[str, str]] = None
    ) -> "Subnet":
        """
        Create Subnet from AWS API response.

        Args:
            subnet_data: Subnet data from describe_subnets
            tags: Optional pre-normalized tags dictionary

        Returns:
            Subnet instance
        """
        # Parse tags if not provided
        if tags is None:
            tags_list = subnet_data.get('Tags', [])
            tags = {tag['Key']: tag['Value'] for tag in tags_list}

        subnet_dict = {
            'subnet_id': subnet_data['SubnetId'],
            'vpc_id': subnet_data.get('VpcId', ''),
            'cidr_block': subnet_data.get('CidrBlock', ''),
            'availability_zone': subnet_data.get('AvailabilityZone', ''),
            'availability_zone_id': subnet_data.get('AvailabilityZoneId'),
            'available_ip_address_count': subnet_data.get('AvailableIpAddressCount', 0),
            'state': subnet_data.get('State', ''),
            'map_public_ip_on_launch': subnet_data.get('MapPublicIpOnLaunch', False),
            'assign_ipv6_address_on_creation': subnet_data.get('AssignIpv6AddressOnCreation', False),
            'default_for_az': subnet_data.get('DefaultForAz', False),
            'owner_id': subnet_data.get('OwnerId'),
            'arn': f"arn:aws:ec2:::subnet/{subnet_data['SubnetId']}",
            'tags': tags,
        }

        return cls(**subnet_dict)

    def __str__(self) -> str:
        """Return string representation of subnet."""
        return f"Subnet(id={self.subnet_id}, az={self.availability_zone}, cidr={self.cidr_block})"


class RouteTableRoute(BaseModel):
    """Individual route in a route table."""
    model_config = ConfigDict(extra="ignore")

    destination_cidr_block: Optional[str] = Field(None, description="Destination IPv4 CIDR")
    destination_ipv6_cidr_block: Optional[str] = Field(None, description="Destination IPv6 CIDR")
    gateway_id: Optional[str] = Field(None, description="Internet/VPN gateway ID")
    instance_id: Optional[str] = Field(None, description="Instance ID")
    nat_gateway_id: Optional[str] = Field(None, description="NAT gateway ID")
    network_interface_id: Optional[str] = Field(None, description="Network interface ID")
    vpc_peering_connection_id: Optional[str] = Field(None, description="VPC peering connection ID")
    transit_gateway_id: Optional[str] = Field(None, description="Transit gateway ID")
    state: Optional[str] = Field(None, description="Route state")
    origin: Optional[str] = Field(None, description="Route origin")

    def __str__(self) -> str:
        """Return string representation of route."""
        dest = self.destination_cidr_block or self.destination_ipv6_cidr_block or "unknown"
        target = (
            self.gateway_id or
            self.nat_gateway_id or
            self.instance_id or
            self.network_interface_id or
            "unknown"
        )
        return f"Route({dest} -> {target})"


class RouteTable(AWSResource):
    """
    VPC route table resource model.

    Represents a route table with its routes and associations.
    """
    model_config = ConfigDict(extra="ignore")

    route_table_id: str = Field(..., pattern=r'^rtb-[a-f0-9]+$', description="Route table ID")
    vpc_id: str = Field(..., pattern=r'^vpc-[a-f0-9]+$', description="VPC ID")
    routes: list[RouteTableRoute] = Field(default_factory=list, description="Routes")
    associations: list[dict[str, str]] = Field(
        default_factory=list,
        description="Subnet associations"
    )
    owner_id: Optional[str] = Field(None, description="AWS account ID")

    @field_validator('route_table_id')
    @classmethod
    def validate_route_table_id(cls, v: str) -> str:
        """Validate route table ID format."""
        if not v.startswith('rtb-'):
            raise ValueError("Route table ID must start with 'rtb-'")
        return v

    @classmethod
    def from_aws_response(
        cls,
        rt_data: dict[str, Any],
        tags: Optional[dict[str, str]] = None
    ) -> "RouteTable":
        """
        Create RouteTable from AWS API response.

        Args:
            rt_data: Route table data from describe_route_tables
            tags: Optional pre-normalized tags dictionary

        Returns:
            RouteTable instance
        """
        # Parse routes
        routes = []
        for route in rt_data.get('Routes', []):
            routes.append(RouteTableRoute(
                destination_cidr_block=route.get('DestinationCidrBlock'),
                destination_ipv6_cidr_block=route.get('DestinationIpv6CidrBlock'),
                gateway_id=route.get('GatewayId'),
                instance_id=route.get('InstanceId'),
                nat_gateway_id=route.get('NatGatewayId'),
                network_interface_id=route.get('NetworkInterfaceId'),
                vpc_peering_connection_id=route.get('VpcPeeringConnectionId'),
                transit_gateway_id=route.get('TransitGatewayId'),
                state=route.get('State'),
                origin=route.get('Origin')
            ))

        # Parse associations
        associations = []
        for assoc in rt_data.get('Associations', []):
            associations.append({
                'SubnetId': assoc.get('SubnetId', ''),
                'Main': str(assoc.get('Main', False)),
                'RouteTableAssociationId': assoc.get('RouteTableAssociationId', ''),
            })

        # Parse tags if not provided
        if tags is None:
            tags_list = rt_data.get('Tags', [])
            tags = {tag['Key']: tag['Value'] for tag in tags_list}

        rt_dict = {
            'route_table_id': rt_data['RouteTableId'],
            'vpc_id': rt_data.get('VpcId', ''),
            'routes': routes,
            'associations': associations,
            'owner_id': rt_data.get('OwnerId'),
            'arn': f"arn:aws:ec2:::route-table/{rt_data['RouteTableId']}",
            'tags': tags,
        }

        return cls(**rt_dict)

    def __str__(self) -> str:
        """Return string representation of route table."""
        return f"RouteTable(id={self.route_table_id}, vpc={self.vpc_id}, routes={len(self.routes)})"


class NetworkAclEntry(BaseModel):
    """Network ACL rule entry."""
    model_config = ConfigDict(extra="ignore")

    rule_number: int = Field(..., ge=1, le=32767, description="Rule number (32767 is default deny rule)")
    protocol: str = Field(..., description="Protocol number or '-1' for all")
    rule_action: str = Field(..., description="allow or deny")
    egress: bool = Field(..., description="Is egress rule")
    cidr_block: Optional[str] = Field(None, description="IPv4 CIDR block")
    ipv6_cidr_block: Optional[str] = Field(None, description="IPv6 CIDR block")
    port_from: Optional[int] = Field(None, description="Start of port range")
    port_to: Optional[int] = Field(None, description="End of port range")

    def __str__(self) -> str:
        """Return string representation of NACL entry."""
        direction = "egress" if self.egress else "ingress"
        cidr = self.cidr_block or self.ipv6_cidr_block or "any"
        return f"Rule {self.rule_number}: {self.rule_action} {direction} from {cidr}"


class NetworkAcl(AWSResource):
    """
    Network Access Control List (NACL) resource model.

    Represents a network ACL with its entries and associations.
    """
    model_config = ConfigDict(extra="ignore")

    network_acl_id: str = Field(..., pattern=r'^acl-[a-f0-9]+$', description="Network ACL ID")
    vpc_id: str = Field(..., pattern=r'^vpc-[a-f0-9]+$', description="VPC ID")
    is_default: bool = Field(default=False, description="Is default NACL")
    entries: list[NetworkAclEntry] = Field(default_factory=list, description="NACL entries")
    associations: list[dict[str, str]] = Field(
        default_factory=list,
        description="Subnet associations"
    )
    owner_id: Optional[str] = Field(None, description="AWS account ID")

    @field_validator('network_acl_id')
    @classmethod
    def validate_network_acl_id(cls, v: str) -> str:
        """Validate network ACL ID format."""
        if not v.startswith('acl-'):
            raise ValueError("Network ACL ID must start with 'acl-'")
        return v

    @classmethod
    def from_aws_response(
        cls,
        nacl_data: dict[str, Any],
        tags: Optional[dict[str, str]] = None
    ) -> "NetworkAcl":
        """
        Create NetworkAcl from AWS API response.

        Args:
            nacl_data: NACL data from describe_network_acls
            tags: Optional pre-normalized tags dictionary

        Returns:
            NetworkAcl instance
        """
        # Parse entries
        entries = []
        for entry in nacl_data.get('Entries', []):
            port_range = entry.get('PortRange', {})
            entries.append(NetworkAclEntry(
                rule_number=entry.get('RuleNumber', 0),
                protocol=entry.get('Protocol', '-1'),
                rule_action=entry.get('RuleAction', ''),
                egress=entry.get('Egress', False),
                cidr_block=entry.get('CidrBlock'),
                ipv6_cidr_block=entry.get('Ipv6CidrBlock'),
                port_from=port_range.get('From') if port_range else None,
                port_to=port_range.get('To') if port_range else None
            ))

        # Parse associations
        associations = []
        for assoc in nacl_data.get('Associations', []):
            associations.append({
                'SubnetId': assoc.get('SubnetId', ''),
                'NetworkAclAssociationId': assoc.get('NetworkAclAssociationId', ''),
            })

        # Parse tags if not provided
        if tags is None:
            tags_list = nacl_data.get('Tags', [])
            tags = {tag['Key']: tag['Value'] for tag in tags_list}

        nacl_dict = {
            'network_acl_id': nacl_data['NetworkAclId'],
            'vpc_id': nacl_data.get('VpcId', ''),
            'is_default': nacl_data.get('IsDefault', False),
            'entries': entries,
            'associations': associations,
            'owner_id': nacl_data.get('OwnerId'),
            'arn': f"arn:aws:ec2:::network-acl/{nacl_data['NetworkAclId']}",
            'tags': tags,
        }

        return cls(**nacl_dict)

    def __str__(self) -> str:
        """Return string representation of network ACL."""
        return f"NetworkAcl(id={self.network_acl_id}, vpc={self.vpc_id}, entries={len(self.entries)})"


class KeyPair(AWSResource):
    """
    EC2 key pair resource model.

    Represents an SSH key pair for EC2 instance access.
    """
    model_config = ConfigDict(extra="ignore")

    key_name: str = Field(..., description="Key pair name")
    key_fingerprint: str = Field(..., description="Key fingerprint")
    key_type: Optional[str] = Field(None, description="Key type (rsa, ed25519)")
    key_pair_id: Optional[str] = Field(None, description="Key pair ID")
    create_time: Optional[datetime] = Field(None, description="Creation timestamp")

    @classmethod
    def from_aws_response(
        cls,
        key_data: dict[str, Any],
        tags: Optional[dict[str, str]] = None
    ) -> "KeyPair":
        """
        Create KeyPair from AWS API response.

        Args:
            key_data: Key pair data from describe_key_pairs
            tags: Optional pre-normalized tags dictionary

        Returns:
            KeyPair instance
        """
        # Parse tags if not provided
        if tags is None:
            tags_list = key_data.get('Tags', [])
            tags = {tag['Key']: tag['Value'] for tag in tags_list}

        key_dict = {
            'key_name': key_data.get('KeyName', ''),
            'key_fingerprint': key_data.get('KeyFingerprint', ''),
            'key_type': key_data.get('KeyType'),
            'key_pair_id': key_data.get('KeyPairId'),
            'create_time': key_data.get('CreateTime'),
            'arn': f"arn:aws:ec2:::key-pair/{key_data.get('KeyName', '')}",
            'tags': tags,
        }

        return cls(**key_dict)

    def __str__(self) -> str:
        """Return string representation of key pair."""
        return f"KeyPair(name={self.key_name}, type={self.key_type})"
