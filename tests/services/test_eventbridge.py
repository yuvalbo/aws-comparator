"""
Unit tests for EventBridge service fetcher.

This module tests the EventBridge fetcher implementation using moto for
AWS API mocking.
"""

import json
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import boto3
import pytest
from moto import mock_aws

from aws_comparator.models.eventbridge import (
    Archive,
    ArchiveState,
    AuthorizationType,
    Connection,
    ConnectionState,
    EventBus,
    Rule,
    RuleState,
    Target,
)
from aws_comparator.services.eventbridge.fetcher import EventBridgeFetcher


@pytest.fixture
def aws_credentials(monkeypatch):
    """Mock AWS credentials for moto."""
    monkeypatch.setenv('AWS_ACCESS_KEY_ID', 'testing')
    monkeypatch.setenv('AWS_SECRET_ACCESS_KEY', 'testing')
    monkeypatch.setenv('AWS_SECURITY_TOKEN', 'testing')
    monkeypatch.setenv('AWS_SESSION_TOKEN', 'testing')
    monkeypatch.setenv('AWS_DEFAULT_REGION', 'us-east-1')


@pytest.fixture
def mock_session(aws_credentials):
    """Create a mock boto3 session."""
    with mock_aws():
        session = boto3.Session(region_name='us-east-1')
        yield session


@pytest.fixture
def eventbridge_fetcher(mock_session):
    """Create an EventBridge fetcher instance."""
    return EventBridgeFetcher(session=mock_session, region='us-east-1')


@pytest.fixture
def events_client(mock_session):
    """Create a mocked EventBridge client."""
    return mock_session.client('events', region_name='us-east-1')


class TestEventBridgeFetcher:
    """Test suite for EventBridge fetcher."""

    def test_create_client(self, eventbridge_fetcher):
        """Test that client is created correctly."""
        assert eventbridge_fetcher.client is not None
        assert eventbridge_fetcher.SERVICE_NAME == 'eventbridge'

    def test_get_resource_types(self, eventbridge_fetcher):
        """Test that resource types are returned correctly."""
        resource_types = eventbridge_fetcher.get_resource_types()
        assert 'event_buses' in resource_types
        assert 'rules' in resource_types
        assert 'archives' in resource_types
        assert 'connections' in resource_types
        assert len(resource_types) == 4

    def test_fetch_resources(self, eventbridge_fetcher, events_client):
        """Test fetching all resources."""
        # Create some test resources
        events_client.create_event_bus(Name='test-bus')
        events_client.put_rule(
            Name='test-rule',
            EventPattern=json.dumps({'source': ['aws.ec2']}),
            State='ENABLED'
        )

        # Fetch all resources
        resources = eventbridge_fetcher.fetch_resources()

        # Verify structure
        assert isinstance(resources, dict)
        assert 'event_buses' in resources
        assert 'rules' in resources
        assert 'archives' in resources
        assert 'connections' in resources


class TestEventBusFetching:
    """Tests for event bus fetching."""

    def test_fetch_default_event_bus(self, eventbridge_fetcher, events_client):
        """Test fetching default event bus."""
        event_buses = eventbridge_fetcher._fetch_event_buses()

        # Default bus always exists
        assert len(event_buses) >= 1
        assert any(bus.name == 'default' for bus in event_buses)

        # Verify default bus properties
        default_bus = next(bus for bus in event_buses if bus.name == 'default')
        assert isinstance(default_bus, EventBus)
        assert default_bus.arn is not None
        assert 'default' in default_bus.arn

    def test_fetch_custom_event_bus(self, eventbridge_fetcher, events_client):
        """Test fetching custom event bus."""
        # Create custom event bus
        events_client.create_event_bus(Name='custom-bus')

        event_buses = eventbridge_fetcher._fetch_event_buses()

        # Find custom bus
        custom_bus = next((bus for bus in event_buses if bus.name == 'custom-bus'), None)
        assert custom_bus is not None
        assert isinstance(custom_bus, EventBus)
        assert custom_bus.name == 'custom-bus'
        assert custom_bus.arn is not None

    def test_fetch_event_bus_with_tags(self, eventbridge_fetcher, events_client):
        """Test fetching event bus with tags."""
        # Create event bus with tags
        response = events_client.create_event_bus(
            Name='tagged-bus',
            Tags=[
                {'Key': 'Environment', 'Value': 'test'},
                {'Key': 'Application', 'Value': 'comparator'}
            ]
        )

        event_buses = eventbridge_fetcher._fetch_event_buses()

        # Find tagged bus
        tagged_bus = next((bus for bus in event_buses if bus.name == 'tagged-bus'), None)
        assert tagged_bus is not None
        # Note: moto may not fully support tags for event buses
        # This test verifies the code path works without errors

    def test_fetch_event_bus_empty_result(self, eventbridge_fetcher):
        """Test handling of no custom event buses."""
        with patch.object(eventbridge_fetcher, '_paginate') as mock_paginate:
            # Return only default bus
            mock_paginate.return_value = [
                {'Name': 'default', 'Arn': 'arn:aws:events:us-east-1:123456789012:event-bus/default'}
            ]

            event_buses = eventbridge_fetcher._fetch_event_buses()
            assert len(event_buses) == 1
            assert event_buses[0].name == 'default'


class TestRuleFetching:
    """Tests for rule fetching."""

    def test_fetch_rule_basic(self, eventbridge_fetcher, events_client):
        """Test fetching basic rule."""
        # Create rule
        events_client.put_rule(
            Name='test-rule',
            EventPattern=json.dumps({'source': ['aws.ec2']}),
            State='ENABLED',
            Description='Test rule'
        )

        rules = eventbridge_fetcher._fetch_rules()

        # Verify rule was fetched
        assert len(rules) >= 1
        test_rule = next((r for r in rules if r.name == 'test-rule'), None)
        assert test_rule is not None
        assert isinstance(test_rule, Rule)
        assert test_rule.name == 'test-rule'
        assert test_rule.state == RuleState.ENABLED
        assert test_rule.event_pattern is not None

    def test_fetch_scheduled_rule(self, eventbridge_fetcher, events_client):
        """Test fetching scheduled rule."""
        # Create scheduled rule
        events_client.put_rule(
            Name='scheduled-rule',
            ScheduleExpression='rate(5 minutes)',
            State='ENABLED',
            Description='Scheduled rule'
        )

        rules = eventbridge_fetcher._fetch_rules()

        # Verify rule was fetched
        scheduled_rule = next((r for r in rules if r.name == 'scheduled-rule'), None)
        assert scheduled_rule is not None
        assert scheduled_rule.schedule_expression == 'rate(5 minutes)'
        assert scheduled_rule.event_pattern is None

    def test_fetch_rule_with_targets(self, eventbridge_fetcher, events_client):
        """Test fetching rule with targets."""
        # Create rule
        rule_name = 'rule-with-targets'
        events_client.put_rule(
            Name=rule_name,
            EventPattern=json.dumps({'source': ['aws.ec2']}),
            State='ENABLED'
        )

        # Add target (Lambda function ARN)
        target_arn = 'arn:aws:lambda:us-east-1:123456789012:function:my-function'
        events_client.put_targets(
            Rule=rule_name,
            Targets=[
                {
                    'Id': '1',
                    'Arn': target_arn,
                    'Input': json.dumps({'key': 'value'})
                }
            ]
        )

        rules = eventbridge_fetcher._fetch_rules()

        # Verify rule with targets
        rule = next((r for r in rules if r.name == rule_name), None)
        assert rule is not None
        assert len(rule.targets) >= 1
        
        target = rule.targets[0]
        assert isinstance(target, Target)
        assert target.id == '1'
        assert target.arn == target_arn

    def test_fetch_disabled_rule(self, eventbridge_fetcher, events_client):
        """Test fetching disabled rule."""
        # Create disabled rule
        events_client.put_rule(
            Name='disabled-rule',
            EventPattern=json.dumps({'source': ['aws.s3']}),
            State='DISABLED'
        )

        rules = eventbridge_fetcher._fetch_rules()

        # Verify disabled rule
        disabled_rule = next((r for r in rules if r.name == 'disabled-rule'), None)
        assert disabled_rule is not None
        assert disabled_rule.state == RuleState.DISABLED

    def test_fetch_rules_from_custom_bus(self, eventbridge_fetcher, events_client):
        """Test fetching rules from custom event bus."""
        # Create custom bus
        events_client.create_event_bus(Name='custom-bus')

        # Create rule on custom bus
        events_client.put_rule(
            Name='custom-bus-rule',
            EventBusName='custom-bus',
            EventPattern=json.dumps({'source': ['custom.app']}),
            State='ENABLED'
        )

        rules = eventbridge_fetcher._fetch_rules()

        # Verify rule from custom bus
        custom_rule = next((r for r in rules if r.name == 'custom-bus-rule'), None)
        assert custom_rule is not None
        assert custom_rule.event_bus_name == 'custom-bus'

    def test_fetch_rules_empty_result(self, eventbridge_fetcher):
        """Test handling of no rules."""
        with patch.object(eventbridge_fetcher, '_paginate') as mock_paginate:
            # First call returns default bus, second returns no rules
            mock_paginate.side_effect = [
                [{'Name': 'default', 'Arn': 'arn:aws:events:us-east-1:123456789012:event-bus/default'}],
                []
            ]

            rules = eventbridge_fetcher._fetch_rules()
            assert len(rules) == 0


class TestArchiveFetching:
    """Tests for archive fetching."""

    def test_fetch_archives_empty(self, eventbridge_fetcher):
        """Test fetching archives when none exist."""
        with patch.object(eventbridge_fetcher, '_paginate') as mock_paginate:
            mock_paginate.return_value = []

            archives = eventbridge_fetcher._fetch_archives()
            assert len(archives) == 0

    def test_fetch_archive_basic(self, eventbridge_fetcher):
        """Test fetching archive with mocked data."""
        with patch.object(eventbridge_fetcher, '_paginate') as mock_paginate:
            mock_paginate.return_value = [
                {
                    'ArchiveName': 'test-archive',
                    'EventSourceArn': 'arn:aws:events:us-east-1:123456789012:event-bus/default',
                    'State': 'ENABLED',
                    'RetentionDays': 7,
                    'SizeBytes': 1024,
                    'EventCount': 100,
                    'ArchiveArn': 'arn:aws:events:us-east-1:123456789012:archive/test-archive'
                }
            ]

            with patch.object(eventbridge_fetcher.client, 'describe_archive') as mock_describe:
                mock_describe.return_value = mock_paginate.return_value[0]

                archives = eventbridge_fetcher._fetch_archives()

                assert len(archives) == 1
                archive = archives[0]
                assert isinstance(archive, Archive)
                assert archive.archive_name == 'test-archive'
                assert archive.state == ArchiveState.ENABLED
                assert archive.retention_days == 7


class TestConnectionFetching:
    """Tests for connection fetching."""

    def test_fetch_connections_empty(self, eventbridge_fetcher):
        """Test fetching connections when none exist."""
        with patch.object(eventbridge_fetcher, '_paginate') as mock_paginate:
            mock_paginate.return_value = []

            connections = eventbridge_fetcher._fetch_connections()
            assert len(connections) == 0

    def test_fetch_connection_basic(self, eventbridge_fetcher):
        """Test fetching connection with mocked data."""
        with patch.object(eventbridge_fetcher, '_paginate') as mock_paginate:
            mock_paginate.return_value = [
                {
                    'Name': 'test-connection',
                    'ConnectionArn': 'arn:aws:events:us-east-1:123456789012:connection/test-connection',
                    'ConnectionState': 'AUTHORIZED',
                    'AuthorizationType': 'API_KEY',
                    'CreationTime': datetime(2024, 1, 1, tzinfo=timezone.utc)
                }
            ]

            with patch.object(eventbridge_fetcher.client, 'describe_connection') as mock_describe:
                mock_describe.return_value = mock_paginate.return_value[0]

                connections = eventbridge_fetcher._fetch_connections()

                assert len(connections) == 1
                connection = connections[0]
                assert isinstance(connection, Connection)
                assert connection.name == 'test-connection'
                assert connection.connection_state == ConnectionState.AUTHORIZED
                assert connection.authorization_type == AuthorizationType.API_KEY


class TestErrorHandling:
    """Tests for error handling."""

    def test_fetch_event_buses_access_denied(self, eventbridge_fetcher):
        """Test handling of access denied error."""
        with patch.object(eventbridge_fetcher, '_paginate') as mock_paginate:
            from botocore.exceptions import ClientError
            
            mock_paginate.side_effect = ClientError(
                {'Error': {'Code': 'AccessDenied', 'Message': 'Access Denied'}},
                'ListEventBuses'
            )

            # Should handle error gracefully and return empty list
            event_buses = eventbridge_fetcher._fetch_event_buses()
            assert len(event_buses) == 0

    def test_fetch_rules_access_denied(self, eventbridge_fetcher):
        """Test handling of access denied for rules."""
        with patch.object(eventbridge_fetcher, '_paginate') as mock_paginate:
            # First call for event buses succeeds
            # Second call for rules fails
            from botocore.exceptions import ClientError
            
            mock_paginate.side_effect = [
                [{'Name': 'default', 'Arn': 'arn:aws:events:us-east-1:123456789012:event-bus/default'}],
                ClientError(
                    {'Error': {'Code': 'AccessDenied', 'Message': 'Access Denied'}},
                    'ListRules'
                )
            ]

            # Should handle error gracefully
            rules = eventbridge_fetcher._fetch_rules()
            assert len(rules) == 0

    def test_safe_fetch_wrapper(self, eventbridge_fetcher):
        """Test that _safe_fetch handles exceptions."""
        def failing_fetch():
            raise Exception("Test error")

        # Should not raise exception
        result = eventbridge_fetcher._safe_fetch('test_resource', failing_fetch)
        assert result == []


class TestPagination:
    """Tests for pagination handling."""

    def test_paginate_event_buses(self, eventbridge_fetcher):
        """Test pagination for event buses."""
        with patch.object(eventbridge_fetcher.client, 'can_paginate') as mock_can_paginate:
            with patch.object(eventbridge_fetcher.client, 'get_paginator') as mock_get_paginator:
                mock_can_paginate.return_value = True
                
                # Mock paginator
                mock_paginator = MagicMock()
                mock_get_paginator.return_value = mock_paginator
                
                # Mock pages
                mock_paginator.paginate.return_value = [
                    {'EventBuses': [
                        {'Name': 'bus1', 'Arn': 'arn:aws:events:us-east-1:123456789012:event-bus/bus1'}
                    ]},
                    {'EventBuses': [
                        {'Name': 'bus2', 'Arn': 'arn:aws:events:us-east-1:123456789012:event-bus/bus2'}
                    ]}
                ]

                results = eventbridge_fetcher._paginate('list_event_buses', 'EventBuses')
                
                assert len(results) == 2
                assert results[0]['Name'] == 'bus1'
                assert results[1]['Name'] == 'bus2'


class TestModels:
    """Tests for EventBridge models."""

    def test_event_bus_creation(self):
        """Test EventBus model creation."""
        bus_data = {
            'Name': 'test-bus',
            'Arn': 'arn:aws:events:us-east-1:123456789012:event-bus/test-bus',
            'Policy': {'Version': '2012-10-17', 'Statement': []}
        }

        event_bus = EventBus.from_aws_response(bus_data)
        
        assert event_bus.name == 'test-bus'
        assert event_bus.arn == bus_data['Arn']
        assert event_bus.policy is not None

    def test_rule_creation_with_targets(self):
        """Test Rule model creation with targets."""
        rule_data = {
            'Name': 'test-rule',
            'Arn': 'arn:aws:events:us-east-1:123456789012:rule/test-rule',
            'EventPattern': json.dumps({'source': ['aws.ec2']}),
            'State': 'ENABLED',
            'EventBusName': 'default'
        }
        
        targets_data = [
            {
                'Id': '1',
                'Arn': 'arn:aws:lambda:us-east-1:123456789012:function:my-function',
                'Input': json.dumps({'key': 'value'})
            }
        ]

        rule = Rule.from_aws_response(rule_data, targets_data)
        
        assert rule.name == 'test-rule'
        assert rule.state == RuleState.ENABLED
        assert len(rule.targets) == 1
        assert rule.targets[0].id == '1'

    def test_archive_creation(self):
        """Test Archive model creation."""
        archive_data = {
            'ArchiveName': 'test-archive',
            'EventSourceArn': 'arn:aws:events:us-east-1:123456789012:event-bus/default',
            'State': 'ENABLED',
            'RetentionDays': 7,
            'ArchiveArn': 'arn:aws:events:us-east-1:123456789012:archive/test-archive'
        }

        archive = Archive.from_aws_response(archive_data)
        
        assert archive.archive_name == 'test-archive'
        assert archive.state == ArchiveState.ENABLED
        assert archive.retention_days == 7

    def test_connection_creation(self):
        """Test Connection model creation."""
        connection_data = {
            'Name': 'test-connection',
            'ConnectionArn': 'arn:aws:events:us-east-1:123456789012:connection/test-connection',
            'ConnectionState': 'AUTHORIZED',
            'AuthorizationType': 'API_KEY'
        }

        connection = Connection.from_aws_response(connection_data)
        
        assert connection.name == 'test-connection'
        assert connection.connection_state == ConnectionState.AUTHORIZED
        assert connection.authorization_type == AuthorizationType.API_KEY


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
