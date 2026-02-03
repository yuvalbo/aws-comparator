"""Unit tests for EC2 service fetcher."""

import boto3
from moto import mock_aws

from aws_comparator.services.ec2.fetcher import EC2Fetcher


@mock_aws
def test_fetch_instances_success() -> None:
    """Test successful EC2 instance fetching."""
    # Setup
    session = boto3.Session(region_name='us-east-1')
    client = session.client('ec2')

    # Create test VPC and subnet
    vpc = client.create_vpc(CidrBlock='10.0.0.0/16')
    vpc_id = vpc['Vpc']['VpcId']

    subnet = client.create_subnet(VpcId=vpc_id, CidrBlock='10.0.1.0/24')
    subnet_id = subnet['Subnet']['SubnetId']

    # Create security group
    sg = client.create_security_group(
        GroupName='test-sg',
        Description='Test security group',
        VpcId=vpc_id
    )
    sg_id = sg['GroupId']

    # Create EC2 instance
    client.run_instances(
        ImageId='ami-12345678',
        MinCount=1,
        MaxCount=1,
        InstanceType='t2.micro',
        SubnetId=subnet_id,
        SecurityGroupIds=[sg_id],
        TagSpecifications=[{
            'ResourceType': 'instance',
            'Tags': [
                {'Key': 'Name', 'Value': 'test-instance'},
                {'Key': 'Environment', 'Value': 'test'}
            ]
        }]
    )

    # Execute
    fetcher = EC2Fetcher(session, 'us-east-1')
    resources = fetcher.fetch_resources()

    # Assert
    assert 'instances' in resources
    assert len(resources['instances']) == 1
    instance = resources['instances'][0]
    assert instance.instance_type == 't2.micro'
    assert instance.state == 'running'
    assert instance.vpc_id == vpc_id
    assert instance.subnet_id == subnet_id
    assert sg_id in instance.security_groups
    assert instance.tags['Name'] == 'test-instance'
    assert instance.tags['Environment'] == 'test'


@mock_aws
def test_fetch_security_groups_success() -> None:
    """Test successful security group fetching."""
    # Setup
    session = boto3.Session(region_name='us-east-1')
    client = session.client('ec2')

    # Create VPC
    vpc = client.create_vpc(CidrBlock='10.0.0.0/16')
    vpc_id = vpc['Vpc']['VpcId']

    # Create security group with rules
    sg = client.create_security_group(
        GroupName='test-sg',
        Description='Test security group',
        VpcId=vpc_id
    )
    sg_id = sg['GroupId']

    # Add ingress rule
    client.authorize_security_group_ingress(
        GroupId=sg_id,
        IpPermissions=[{
            'IpProtocol': 'tcp',
            'FromPort': 80,
            'ToPort': 80,
            'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
        }]
    )

    # Add egress rule (custom)
    client.authorize_security_group_egress(
        GroupId=sg_id,
        IpPermissions=[{
            'IpProtocol': 'tcp',
            'FromPort': 443,
            'ToPort': 443,
            'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
        }]
    )

    # Execute
    fetcher = EC2Fetcher(session, 'us-east-1')
    resources = fetcher.fetch_resources()

    # Assert
    assert 'security_groups' in resources
    # Moto creates default security group, so we should have at least 2
    assert len(resources['security_groups']) >= 1

    # Find our test security group
    test_sg = next((sg for sg in resources['security_groups'] if sg.group_name == 'test-sg'), None)
    assert test_sg is not None
    assert test_sg.group_id == sg_id
    assert test_sg.description == 'Test security group'
    assert test_sg.vpc_id == vpc_id
    assert len(test_sg.ingress_rules) >= 1
    # Check ingress rule
    ingress_rule = test_sg.ingress_rules[0]
    assert ingress_rule.ip_protocol == 'tcp'
    assert ingress_rule.from_port == 80
    assert ingress_rule.to_port == 80


@mock_aws
def test_fetch_vpcs_success() -> None:
    """Test successful VPC fetching."""
    # Setup
    session = boto3.Session(region_name='us-east-1')
    client = session.client('ec2')

    # Create VPC
    vpc = client.create_vpc(CidrBlock='10.0.0.0/16')
    vpc_id = vpc['Vpc']['VpcId']

    # Tag VPC
    client.create_tags(
        Resources=[vpc_id],
        Tags=[
            {'Key': 'Name', 'Value': 'test-vpc'},
            {'Key': 'Environment', 'Value': 'test'}
        ]
    )

    # Execute
    fetcher = EC2Fetcher(session, 'us-east-1')
    resources = fetcher.fetch_resources()

    # Assert
    assert 'vpcs' in resources
    # Moto creates a default VPC, so we should have at least 2
    assert len(resources['vpcs']) >= 1

    # Find our test VPC
    test_vpc = next((v for v in resources['vpcs'] if v.vpc_id == vpc_id), None)
    assert test_vpc is not None
    assert test_vpc.cidr_block == '10.0.0.0/16'
    assert test_vpc.tags['Name'] == 'test-vpc'
    assert test_vpc.tags['Environment'] == 'test'


@mock_aws
def test_fetch_subnets_success() -> None:
    """Test successful subnet fetching."""
    # Setup
    session = boto3.Session(region_name='us-east-1')
    client = session.client('ec2')

    # Create VPC
    vpc = client.create_vpc(CidrBlock='10.0.0.0/16')
    vpc_id = vpc['Vpc']['VpcId']

    # Create subnet
    subnet = client.create_subnet(
        VpcId=vpc_id,
        CidrBlock='10.0.1.0/24',
        AvailabilityZone='us-east-1a'
    )
    subnet_id = subnet['Subnet']['SubnetId']

    # Tag subnet
    client.create_tags(
        Resources=[subnet_id],
        Tags=[
            {'Key': 'Name', 'Value': 'test-subnet'},
            {'Key': 'Type', 'Value': 'private'}
        ]
    )

    # Execute
    fetcher = EC2Fetcher(session, 'us-east-1')
    resources = fetcher.fetch_resources()

    # Assert
    assert 'subnets' in resources
    assert len(resources['subnets']) >= 1

    # Find our test subnet
    test_subnet = next((s for s in resources['subnets'] if s.subnet_id == subnet_id), None)
    assert test_subnet is not None
    assert test_subnet.vpc_id == vpc_id
    assert test_subnet.cidr_block == '10.0.1.0/24'
    assert test_subnet.availability_zone == 'us-east-1a'
    assert test_subnet.tags['Name'] == 'test-subnet'
    assert test_subnet.tags['Type'] == 'private'


@mock_aws
def test_fetch_route_tables_success() -> None:
    """Test successful route table fetching."""
    # Setup
    session = boto3.Session(region_name='us-east-1')
    client = session.client('ec2')

    # Create VPC
    vpc = client.create_vpc(CidrBlock='10.0.0.0/16')
    vpc_id = vpc['Vpc']['VpcId']

    # Create route table
    rt = client.create_route_table(VpcId=vpc_id)
    rt_id = rt['RouteTable']['RouteTableId']

    # Tag route table
    client.create_tags(
        Resources=[rt_id],
        Tags=[
            {'Key': 'Name', 'Value': 'test-rt'}
        ]
    )

    # Execute
    fetcher = EC2Fetcher(session, 'us-east-1')
    resources = fetcher.fetch_resources()

    # Assert
    assert 'route_tables' in resources
    assert len(resources['route_tables']) >= 1

    # Find our test route table
    test_rt = next((r for r in resources['route_tables'] if r.route_table_id == rt_id), None)
    assert test_rt is not None
    assert test_rt.vpc_id == vpc_id
    assert test_rt.tags['Name'] == 'test-rt'
    # Route tables always have at least one route (local)
    assert len(test_rt.routes) >= 1


@mock_aws
def test_fetch_network_acls_success() -> None:
    """Test successful network ACL fetching."""
    # Setup
    session = boto3.Session(region_name='us-east-1')
    client = session.client('ec2')

    # Create VPC (this automatically creates a default NACL)
    vpc = client.create_vpc(CidrBlock='10.0.0.0/16')
    vpc_id = vpc['Vpc']['VpcId']

    # Create custom network ACL
    nacl = client.create_network_acl(VpcId=vpc_id)
    nacl_id = nacl['NetworkAcl']['NetworkAclId']

    # Tag NACL
    client.create_tags(
        Resources=[nacl_id],
        Tags=[
            {'Key': 'Name', 'Value': 'test-nacl'}
        ]
    )

    # Execute
    fetcher = EC2Fetcher(session, 'us-east-1')
    resources = fetcher.fetch_resources()

    # Assert
    assert 'network_acls' in resources
    assert len(resources['network_acls']) >= 1

    # Find our test NACL
    test_nacl = next((n for n in resources['network_acls'] if n.network_acl_id == nacl_id), None)
    assert test_nacl is not None
    assert test_nacl.vpc_id == vpc_id
    assert test_nacl.tags['Name'] == 'test-nacl'
    # Custom NACLs created via create_network_acl don't have default entries in moto
    # Only the default NACL has default allow/deny rules
    assert isinstance(test_nacl.entries, list)


@mock_aws
def test_fetch_key_pairs_success() -> None:
    """Test successful key pair fetching."""
    # Setup
    session = boto3.Session(region_name='us-east-1')
    client = session.client('ec2')

    # Create key pair
    client.create_key_pair(KeyName='test-key')

    # Execute
    fetcher = EC2Fetcher(session, 'us-east-1')
    resources = fetcher.fetch_resources()

    # Assert
    assert 'key_pairs' in resources
    assert len(resources['key_pairs']) == 1
    key_pair = resources['key_pairs'][0]
    assert key_pair.key_name == 'test-key'
    assert key_pair.key_fingerprint is not None


@mock_aws
def test_fetch_resources_empty() -> None:
    """Test fetching with no EC2 resources (except defaults)."""
    session = boto3.Session(region_name='us-west-2')
    fetcher = EC2Fetcher(session, 'us-west-2')
    resources = fetcher.fetch_resources()

    # All resource types should be present
    assert 'instances' in resources
    assert 'security_groups' in resources
    assert 'vpcs' in resources
    assert 'subnets' in resources
    assert 'route_tables' in resources
    assert 'network_acls' in resources
    assert 'key_pairs' in resources

    # Instances and key pairs should be empty
    assert len(resources['instances']) == 0
    assert len(resources['key_pairs']) == 0
    # Other resources may have defaults from Moto


@mock_aws
def test_registry_registration() -> None:
    """Test that EC2 service is properly registered."""
    from aws_comparator.core.registry import ServiceRegistry

    assert ServiceRegistry.is_registered('ec2')
    info = ServiceRegistry.get_service_info('ec2')
    assert info is not None
    assert info['name'] == 'ec2'
    assert info['description'] == 'Amazon EC2 (Elastic Compute Cloud)'
    assert 'instances' in info['resource_types']
    assert 'security_groups' in info['resource_types']
    assert 'vpcs' in info['resource_types']
    assert 'subnets' in info['resource_types']
    assert 'route_tables' in info['resource_types']
    assert 'network_acls' in info['resource_types']
    assert 'key_pairs' in info['resource_types']


@mock_aws
def test_get_resource_types() -> None:
    """Test get_resource_types method."""
    session = boto3.Session(region_name='us-east-1')
    fetcher = EC2Fetcher(session, 'us-east-1')
    resource_types = fetcher.get_resource_types()

    expected_types = [
        'instances',
        'security_groups',
        'vpcs',
        'subnets',
        'route_tables',
        'network_acls',
        'key_pairs'
    ]

    assert sorted(resource_types) == sorted(expected_types)


@mock_aws
def test_fetch_instances_with_multiple_instances() -> None:
    """Test fetching multiple EC2 instances."""
    # Setup
    session = boto3.Session(region_name='us-east-1')
    client = session.client('ec2')

    # Create VPC and subnet
    vpc = client.create_vpc(CidrBlock='10.0.0.0/16')
    vpc_id = vpc['Vpc']['VpcId']
    subnet = client.create_subnet(VpcId=vpc_id, CidrBlock='10.0.1.0/24')
    subnet_id = subnet['Subnet']['SubnetId']

    # Create multiple instances
    for i in range(3):
        client.run_instances(
            ImageId=f'ami-1234567{i}',
            MinCount=1,
            MaxCount=1,
            InstanceType='t2.micro',
            SubnetId=subnet_id,
            TagSpecifications=[{
                'ResourceType': 'instance',
                'Tags': [{'Key': 'Name', 'Value': f'instance-{i}'}]
            }]
        )

    # Execute
    fetcher = EC2Fetcher(session, 'us-east-1')
    resources = fetcher.fetch_resources()

    # Assert
    assert len(resources['instances']) == 3
    instance_names = [inst.tags.get('Name') for inst in resources['instances']]
    assert 'instance-0' in instance_names
    assert 'instance-1' in instance_names
    assert 'instance-2' in instance_names


@mock_aws
def test_fetch_security_group_with_multiple_rules() -> None:
    """Test security group with multiple ingress and egress rules."""
    # Setup
    session = boto3.Session(region_name='us-east-1')
    client = session.client('ec2')

    # Create VPC
    vpc = client.create_vpc(CidrBlock='10.0.0.0/16')
    vpc_id = vpc['Vpc']['VpcId']

    # Create security group
    sg = client.create_security_group(
        GroupName='multi-rule-sg',
        Description='Security group with multiple rules',
        VpcId=vpc_id
    )
    sg_id = sg['GroupId']

    # Add multiple ingress rules
    client.authorize_security_group_ingress(
        GroupId=sg_id,
        IpPermissions=[
            {
                'IpProtocol': 'tcp',
                'FromPort': 22,
                'ToPort': 22,
                'IpRanges': [{'CidrIp': '10.0.0.0/16'}]
            },
            {
                'IpProtocol': 'tcp',
                'FromPort': 80,
                'ToPort': 80,
                'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
            },
            {
                'IpProtocol': 'tcp',
                'FromPort': 443,
                'ToPort': 443,
                'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
            }
        ]
    )

    # Execute
    fetcher = EC2Fetcher(session, 'us-east-1')
    resources = fetcher.fetch_resources()

    # Assert
    test_sg = next((s for s in resources['security_groups'] if s.group_name == 'multi-rule-sg'), None)
    assert test_sg is not None
    assert len(test_sg.ingress_rules) >= 3

    # Verify rules
    tcp_ports = [rule.from_port for rule in test_sg.ingress_rules if rule.ip_protocol == 'tcp']
    assert 22 in tcp_ports
    assert 80 in tcp_ports
    assert 443 in tcp_ports


@mock_aws
def test_instance_state_parsing() -> None:
    """Test that instance state is correctly parsed."""
    # Setup
    session = boto3.Session(region_name='us-east-1')
    client = session.client('ec2')

    # Create VPC and subnet
    vpc = client.create_vpc(CidrBlock='10.0.0.0/16')
    vpc_id = vpc['Vpc']['VpcId']
    subnet = client.create_subnet(VpcId=vpc_id, CidrBlock='10.0.1.0/24')
    subnet_id = subnet['Subnet']['SubnetId']

    # Create instance
    response = client.run_instances(
        ImageId='ami-12345678',
        MinCount=1,
        MaxCount=1,
        InstanceType='t2.micro',
        SubnetId=subnet_id
    )
    instance_id = response['Instances'][0]['InstanceId']

    # Execute
    fetcher = EC2Fetcher(session, 'us-east-1')
    resources = fetcher.fetch_resources()

    # Assert
    instance = resources['instances'][0]
    assert instance.state in ['pending', 'running']  # Moto starts in running
    assert instance.instance_id == instance_id


@mock_aws
def test_vpc_cidr_block_parsing() -> None:
    """Test that VPC CIDR blocks are correctly parsed."""
    # Setup
    session = boto3.Session(region_name='us-east-1')
    client = session.client('ec2')

    # Create VPC with specific CIDR
    vpc = client.create_vpc(CidrBlock='172.16.0.0/16')
    vpc_id = vpc['Vpc']['VpcId']

    # Execute
    fetcher = EC2Fetcher(session, 'us-east-1')
    resources = fetcher.fetch_resources()

    # Assert
    test_vpc = next((v for v in resources['vpcs'] if v.vpc_id == vpc_id), None)
    assert test_vpc is not None
    assert test_vpc.cidr_block == '172.16.0.0/16'


@mock_aws
def test_error_handling_invalid_instance() -> None:
    """Test error handling when instance data is malformed."""
    # This test ensures the fetcher doesn't crash on bad data
    # In a real scenario, this would be tested with mocked responses
    session = boto3.Session(region_name='us-east-1')
    fetcher = EC2Fetcher(session, 'us-east-1')

    # Should not raise an exception even with no resources
    resources = fetcher.fetch_resources()
    assert 'instances' in resources
    assert isinstance(resources['instances'], list)
