"""Tests for SQS model module."""

import json

import pytest

from aws_comparator.models.sqs import SQSQueue


class TestSQSQueueValidation:
    """Tests for SQSQueue validation."""

    def test_queue_name_cannot_be_empty(self):
        """Test queue name validation rejects empty string."""
        with pytest.raises(ValueError, match="Queue name cannot be empty"):
            SQSQueue(
                queue_url="https://sqs.us-east-1.amazonaws.com/123456789012/",
                queue_name="",
                arn="arn:aws:sqs:us-east-1:123456789012:test-queue",
            )

    def test_queue_name_cannot_exceed_80_characters(self):
        """Test queue name validation rejects names over 80 characters."""
        long_name = "a" * 81
        with pytest.raises(ValueError, match="cannot exceed 80 characters"):
            SQSQueue(
                queue_url=f"https://sqs.us-east-1.amazonaws.com/123456789012/{long_name}",
                queue_name=long_name,
                arn=f"arn:aws:sqs:us-east-1:123456789012:{long_name}",
            )

    def test_valid_queue_name(self):
        """Test queue creation with valid name."""
        queue = SQSQueue(
            queue_url="https://sqs.us-east-1.amazonaws.com/123456789012/my-queue",
            queue_name="my-queue",
            arn="arn:aws:sqs:us-east-1:123456789012:my-queue",
        )
        assert queue.queue_name == "my-queue"


class TestSQSQueueFromAWSResponse:
    """Tests for SQSQueue.from_aws_response method."""

    def test_from_aws_response_basic(self):
        """Test creating SQSQueue from basic AWS response."""
        queue_url = "https://sqs.us-east-1.amazonaws.com/123456789012/test-queue"
        attributes = {
            "QueueArn": "arn:aws:sqs:us-east-1:123456789012:test-queue",
        }

        queue = SQSQueue.from_aws_response(queue_url, attributes)

        assert queue.queue_url == queue_url
        assert queue.queue_name == "test-queue"
        assert queue.arn == "arn:aws:sqs:us-east-1:123456789012:test-queue"

    def test_from_aws_response_with_numeric_attributes(self):
        """Test creating SQSQueue with numeric attributes."""
        queue_url = "https://sqs.us-east-1.amazonaws.com/123456789012/test-queue"
        attributes = {
            "QueueArn": "arn:aws:sqs:us-east-1:123456789012:test-queue",
            "DelaySeconds": "30",
            "MaximumMessageSize": "65536",
            "MessageRetentionPeriod": "86400",
            "ReceiveMessageWaitTimeSeconds": "10",
            "VisibilityTimeout": "60",
        }

        queue = SQSQueue.from_aws_response(queue_url, attributes)

        assert queue.delay_seconds == 30
        assert queue.maximum_message_size == 65536
        assert queue.message_retention_period == 86400
        assert queue.receive_message_wait_time_seconds == 10
        assert queue.visibility_timeout == 60

    def test_from_aws_response_fifo_queue(self):
        """Test creating FIFO queue from AWS response."""
        queue_url = "https://sqs.us-east-1.amazonaws.com/123456789012/test.fifo"
        attributes = {
            "QueueArn": "arn:aws:sqs:us-east-1:123456789012:test.fifo",
            "FifoQueue": "true",
            "ContentBasedDeduplication": "true",
        }

        queue = SQSQueue.from_aws_response(queue_url, attributes)

        assert queue.fifo_queue is True
        assert queue.content_based_deduplication is True

    def test_from_aws_response_standard_queue(self):
        """Test creating standard queue (not FIFO) from AWS response."""
        queue_url = "https://sqs.us-east-1.amazonaws.com/123456789012/test-queue"
        attributes = {
            "QueueArn": "arn:aws:sqs:us-east-1:123456789012:test-queue",
            "FifoQueue": "false",
        }

        queue = SQSQueue.from_aws_response(queue_url, attributes)

        assert queue.fifo_queue is False

    def test_from_aws_response_with_redrive_policy(self):
        """Test creating queue with dead letter queue redrive policy."""
        queue_url = "https://sqs.us-east-1.amazonaws.com/123456789012/test-queue"
        redrive_policy = {
            "deadLetterTargetArn": "arn:aws:sqs:us-east-1:123456789012:dlq",
            "maxReceiveCount": 3,
        }
        attributes = {
            "QueueArn": "arn:aws:sqs:us-east-1:123456789012:test-queue",
            "RedrivePolicy": json.dumps(redrive_policy),
        }

        queue = SQSQueue.from_aws_response(queue_url, attributes)

        assert queue.redrive_policy is not None
        assert (
            queue.redrive_policy["deadLetterTargetArn"]
            == redrive_policy["deadLetterTargetArn"]
        )
        assert queue.redrive_policy["maxReceiveCount"] == 3

    def test_from_aws_response_with_redrive_allow_policy(self):
        """Test creating queue with redrive allow policy."""
        queue_url = "https://sqs.us-east-1.amazonaws.com/123456789012/test-dlq"
        allow_policy = {
            "redrivePermission": "byQueue",
            "sourceQueueArns": ["arn:aws:sqs:us-east-1:123456789012:source-queue"],
        }
        attributes = {
            "QueueArn": "arn:aws:sqs:us-east-1:123456789012:test-dlq",
            "RedriveAllowPolicy": json.dumps(allow_policy),
        }

        queue = SQSQueue.from_aws_response(queue_url, attributes)

        assert queue.redrive_allow_policy is not None
        assert queue.redrive_allow_policy["redrivePermission"] == "byQueue"

    def test_from_aws_response_with_kms_encryption(self):
        """Test creating queue with KMS encryption."""
        queue_url = "https://sqs.us-east-1.amazonaws.com/123456789012/test-queue"
        attributes = {
            "QueueArn": "arn:aws:sqs:us-east-1:123456789012:test-queue",
            "KmsMasterKeyId": "alias/my-key",
            "KmsDataKeyReusePeriodSeconds": "600",
        }

        queue = SQSQueue.from_aws_response(queue_url, attributes)

        assert queue.kms_master_key_id == "alias/my-key"
        assert queue.kms_data_key_reuse_period_seconds == 600

    def test_from_aws_response_with_sqs_managed_sse(self):
        """Test creating queue with SQS-managed SSE."""
        queue_url = "https://sqs.us-east-1.amazonaws.com/123456789012/test-queue"
        attributes = {
            "QueueArn": "arn:aws:sqs:us-east-1:123456789012:test-queue",
            "SqsManagedSseEnabled": "true",
        }

        queue = SQSQueue.from_aws_response(queue_url, attributes)

        assert queue.sqs_managed_sse_enabled is True

    def test_from_aws_response_with_metrics(self):
        """Test creating queue with approximate metrics."""
        queue_url = "https://sqs.us-east-1.amazonaws.com/123456789012/test-queue"
        attributes = {
            "QueueArn": "arn:aws:sqs:us-east-1:123456789012:test-queue",
            "ApproximateNumberOfMessages": "100",
            "ApproximateNumberOfMessagesDelayed": "10",
            "ApproximateNumberOfMessagesNotVisible": "5",
        }

        queue = SQSQueue.from_aws_response(queue_url, attributes)

        assert queue.approximate_number_of_messages == 100
        assert queue.approximate_number_of_messages_delayed == 10
        assert queue.approximate_number_of_messages_not_visible == 5

    def test_from_aws_response_with_timestamps(self):
        """Test creating queue with timestamps."""
        queue_url = "https://sqs.us-east-1.amazonaws.com/123456789012/test-queue"
        attributes = {
            "QueueArn": "arn:aws:sqs:us-east-1:123456789012:test-queue",
            "CreatedTimestamp": "1609459200",
            "LastModifiedTimestamp": "1609545600",
        }

        queue = SQSQueue.from_aws_response(queue_url, attributes)

        assert queue.created_timestamp == 1609459200
        assert queue.last_modified_timestamp == 1609545600

    def test_from_aws_response_with_policy(self):
        """Test creating queue with policy document."""
        queue_url = "https://sqs.us-east-1.amazonaws.com/123456789012/test-queue"
        policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": "*",
                    "Action": "sqs:SendMessage",
                    "Resource": "arn:aws:sqs:us-east-1:123456789012:test-queue",
                }
            ],
        }
        attributes = {
            "QueueArn": "arn:aws:sqs:us-east-1:123456789012:test-queue",
            "Policy": json.dumps(policy),
        }

        queue = SQSQueue.from_aws_response(queue_url, attributes)

        assert queue.policy is not None
        assert queue.policy["Version"] == "2012-10-17"

    def test_from_aws_response_with_tags(self):
        """Test creating queue with tags."""
        queue_url = "https://sqs.us-east-1.amazonaws.com/123456789012/test-queue"
        attributes = {
            "QueueArn": "arn:aws:sqs:us-east-1:123456789012:test-queue",
        }
        tags = {"Environment": "production", "Team": "platform"}

        queue = SQSQueue.from_aws_response(queue_url, attributes, tags=tags)

        assert queue.tags == tags

    def test_from_aws_response_without_tags(self):
        """Test creating queue without tags."""
        queue_url = "https://sqs.us-east-1.amazonaws.com/123456789012/test-queue"
        attributes = {
            "QueueArn": "arn:aws:sqs:us-east-1:123456789012:test-queue",
        }

        queue = SQSQueue.from_aws_response(queue_url, attributes)

        assert queue.tags == {}


class TestSQSQueueStr:
    """Tests for SQSQueue string representation."""

    def test_str_standard_queue(self):
        """Test string representation of standard queue."""
        queue = SQSQueue(
            queue_url="https://sqs.us-east-1.amazonaws.com/123456789012/my-queue",
            queue_name="my-queue",
            arn="arn:aws:sqs:us-east-1:123456789012:my-queue",
            fifo_queue=False,
        )

        result = str(queue)

        assert "my-queue" in result
        assert "Standard" in result

    def test_str_fifo_queue(self):
        """Test string representation of FIFO queue."""
        queue = SQSQueue(
            queue_url="https://sqs.us-east-1.amazonaws.com/123456789012/my-queue.fifo",
            queue_name="my-queue.fifo",
            arn="arn:aws:sqs:us-east-1:123456789012:my-queue.fifo",
            fifo_queue=True,
        )

        result = str(queue)

        assert "my-queue.fifo" in result
        assert "FIFO" in result


class TestSQSQueueDefaults:
    """Tests for SQSQueue default values."""

    def test_default_delay_seconds(self):
        """Test default delay_seconds is 0."""
        queue = SQSQueue(
            queue_url="https://sqs.us-east-1.amazonaws.com/123456789012/test-queue",
            queue_name="test-queue",
            arn="arn:aws:sqs:us-east-1:123456789012:test-queue",
        )
        assert queue.delay_seconds == 0

    def test_default_maximum_message_size(self):
        """Test default maximum_message_size is 262144."""
        queue = SQSQueue(
            queue_url="https://sqs.us-east-1.amazonaws.com/123456789012/test-queue",
            queue_name="test-queue",
            arn="arn:aws:sqs:us-east-1:123456789012:test-queue",
        )
        assert queue.maximum_message_size == 262144

    def test_default_message_retention_period(self):
        """Test default message_retention_period is 345600 (4 days)."""
        queue = SQSQueue(
            queue_url="https://sqs.us-east-1.amazonaws.com/123456789012/test-queue",
            queue_name="test-queue",
            arn="arn:aws:sqs:us-east-1:123456789012:test-queue",
        )
        assert queue.message_retention_period == 345600

    def test_default_visibility_timeout(self):
        """Test default visibility_timeout is 30."""
        queue = SQSQueue(
            queue_url="https://sqs.us-east-1.amazonaws.com/123456789012/test-queue",
            queue_name="test-queue",
            arn="arn:aws:sqs:us-east-1:123456789012:test-queue",
        )
        assert queue.visibility_timeout == 30

    def test_default_fifo_queue(self):
        """Test default fifo_queue is False."""
        queue = SQSQueue(
            queue_url="https://sqs.us-east-1.amazonaws.com/123456789012/test-queue",
            queue_name="test-queue",
            arn="arn:aws:sqs:us-east-1:123456789012:test-queue",
        )
        assert queue.fifo_queue is False
