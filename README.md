# AWS Account Comparator

A powerful Python CLI tool for comparing AWS resources across two accounts and generating detailed diff reports.

[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue)]
[![License](https://img.shields.io/badge/license-MIT-green)]
[![Version](https://img.shields.io/badge/version-0.1.0-blue)]

## Overview

AWS Account Comparator helps you identify configuration differences between AWS accounts, making it easier to:

- **Audit Drift**: Detect configuration drift between production/staging environments
- **Validate Migrations**: Ensure resources are correctly migrated between accounts
- **Compliance Checking**: Verify that accounts conform to organizational standards
- **Cost Analysis**: Identify resource discrepancies that may impact costs
- **Security Review**: Compare security configurations across accounts

### Key Features

- **Smart Comparison by Name**: Compares resources by logical names (not ARNs) for meaningful cross-account analysis
- **Human-Readable Output**: Clear table format with service quota names and descriptions
- **Multiple Output Formats**: Table, JSON, and YAML output options
- **Severity-Based Classification**: Differences are categorized by severity level
- **Flexible Authentication**: Support for AWS profiles and IAM role assumption

## Installation

### Prerequisites

- Python 3.9 or higher
- AWS credentials configured
- Appropriate IAM permissions (read-only access to services)

### From Source

```bash
# Clone the repository
git clone https://github.com/yuvalbo/aws-comparator.git
cd aws-comparator

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install in development mode
pip install -e .

# Verify installation
aws-comparator --version
```

### Using Docker

Run aws-comparator without installing Python or any dependencies:

```bash
# Build the image
docker build -t aws-comparator .

# Check image size (should be < 100MB)
docker images aws-comparator
```

**Run with AWS credentials mounted:**
```bash
docker run --rm \
  -v ~/.aws:/home/appuser/.aws:ro \
  aws-comparator compare -a1 111111111111 -a2 222222222222 \
  -p1 profile1 -p2 profile2
```

**Run with environment variables:**
```bash
docker run --rm \
  -e AWS_ACCESS_KEY_ID=your-access-key \
  -e AWS_SECRET_ACCESS_KEY=your-secret-key \
  -e AWS_DEFAULT_REGION=us-east-1 \
  aws-comparator list-services
```

**Run with specific region:**
```bash
docker run --rm \
  -v ~/.aws:/home/appuser/.aws:ro \
  -e AWS_DEFAULT_REGION=us-west-2 \
  aws-comparator compare -a1 111111111111 -a2 222222222222 \
  -p1 profile1 -p2 profile2
```

**Check version:**
```bash
docker run --rm aws-comparator version
```

**Save output to file:**
```bash
docker run --rm \
  -v ~/.aws:/home/appuser/.aws:ro \
  -v $(pwd)/output:/output \
  aws-comparator compare -a1 111111111111 -a2 222222222222 \
  -p1 profile1 -p2 profile2 \
  --output-format json \
  --output-file /output/report.json
```

## Quick Start

### Basic Usage

Compare all services between two accounts using AWS profiles:

```bash
aws-comparator compare -a1 123456789012 -a2 987654321098 -p1 prod-profile -p2 staging-profile
```

### Common Use Cases

**Compare specific services only:**
```bash
aws-comparator compare -a1 123456789012 -a2 987654321098 \
  -p1 prod-profile -p2 staging-profile \
  --services ec2,s3,sqs
```

**Output to JSON file:**
```bash
aws-comparator compare -a1 123456789012 -a2 987654321098 \
  -p1 prod-profile -p2 staging-profile \
  --output-format json \
  --output-file comparison-report.json
```

**Output to YAML:**
```bash
aws-comparator compare -a1 123456789012 -a2 987654321098 \
  -p1 prod-profile -p2 staging-profile \
  --output-format yaml
```

**Machine-parseable output (no colors):**
```bash
aws-comparator compare -a1 123456789012 -a2 987654321098 \
  -p1 prod-profile -p2 staging-profile \
  --no-color
```

**Using IAM role assumption:**
```bash
aws-comparator compare -a1 123456789012 -a2 987654321098 \
  --role1 arn:aws:iam::123456789012:role/ComparisonRole \
  --role2 arn:aws:iam::987654321098:role/ComparisonRole
```

**Verbose output for debugging:**
```bash
aws-comparator compare -a1 123456789012 -a2 987654321098 \
  -p1 prod-profile -p2 staging-profile -vv
```

**Compare in a specific region:**
```bash
aws-comparator compare -a1 123456789012 -a2 987654321098 \
  -p1 prod-profile -p2 staging-profile \
  --region eu-west-1
```

## Supported Services

The following 11 AWS services are currently supported:

| Service | Description |
|---------|-------------|
| `bedrock` | Amazon Bedrock (Foundation Models) |
| `cloudwatch` | Amazon CloudWatch - Monitoring and Observability |
| `ec2` | Amazon EC2 (Elastic Compute Cloud) |
| `elasticbeanstalk` | AWS Elastic Beanstalk |
| `eventbridge` | Amazon EventBridge |
| `pinpoint` | Amazon Pinpoint (Customer Engagement) |
| `s3` | Amazon S3 (Simple Storage Service) |
| `secretsmanager` | AWS Secrets Manager (metadata only, values never fetched) |
| `service-quotas` | AWS Service Quotas |
| `sns` | Amazon SNS (Simple Notification Service) |
| `sqs` | Amazon SQS (Simple Queue Service) |

To see all supported services:
```bash
aws-comparator list-services
```

## CLI Reference

### Commands

```
aws-comparator [OPTIONS] COMMAND [ARGS]...

Commands:
  compare        Compare resources between two AWS accounts
  list-services  List all supported AWS services
  version        Show version information
```

### `compare` Command

Compare resources between two AWS accounts.

```
aws-comparator compare [OPTIONS]
```

**Required Options:**

| Option | Description |
|--------|-------------|
| `-a1, --account1 TEXT` | First AWS account ID (12 digits) |
| `-a2, --account2 TEXT` | Second AWS account ID (12 digits) |

**Authentication Options:**

| Option | Description |
|--------|-------------|
| `-p1, --profile1 TEXT` | AWS profile name for account1 |
| `-p2, --profile2 TEXT` | AWS profile name for account2 |
| `--role1 TEXT` | IAM role ARN to assume for account1 |
| `--role2 TEXT` | IAM role ARN to assume for account2 |

**Filtering and Region Options:**

| Option | Description |
|--------|-------------|
| `-r, --region TEXT` | AWS region to compare (default: us-east-1) |
| `-s, --services TEXT` | Comma-separated list of services to compare (default: all) |

**Output Options:**

| Option | Description |
|--------|-------------|
| `-f, --output-format` | Output format: `json`, `yaml`, or `table` (default: table) |
| `-o, --output-file FILE` | Output file path (default: stdout) |
| `--no-color` | Disable colored output |

**Other Options:**

| Option | Description |
|--------|-------------|
| `-c, --config FILE` | Path to configuration file |
| `-v, --verbose` | Increase verbosity (can be used multiple times: -v, -vv, -vvv) |
| `-q, --quiet` | Suppress non-error output |

### `list-services` Command

List all supported AWS services:

```bash
aws-comparator list-services
```

### `version` Command

Show version information:

```bash
aws-comparator version
```

## Output Formats

### Table (Default)

Human-readable table format with colored output:

```bash
aws-comparator compare -a1 123456789012 -a2 987654321098 -p1 prod -p2 staging
```

### JSON

Machine-readable JSON format, ideal for automation:

```bash
aws-comparator compare -a1 123456789012 -a2 987654321098 \
  -p1 prod -p2 staging \
  --output-format json \
  --output-file report.json
```

### YAML

YAML format for configuration management tools:

```bash
aws-comparator compare -a1 123456789012 -a2 987654321098 \
  -p1 prod -p2 staging \
  --output-format yaml
```

### Grep-Friendly Output

Disable colors for piping and grepping:

```bash
aws-comparator compare -a1 123456789012 -a2 987654321098 \
  -p1 prod -p2 staging \
  --no-color | grep "s3"
```

## IAM Permissions

The tool requires read-only permissions for the services being compared:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:Describe*",
        "s3:Get*",
        "s3:List*",
        "secretsmanager:DescribeSecret",
        "secretsmanager:ListSecrets",
        "sqs:GetQueueAttributes",
        "sqs:ListQueues",
        "sns:GetTopicAttributes",
        "sns:ListTopics",
        "sns:ListSubscriptions",
        "cloudwatch:Describe*",
        "logs:Describe*",
        "bedrock:Get*",
        "bedrock:List*",
        "mobiletargeting:Get*",
        "events:Describe*",
        "events:List*",
        "elasticbeanstalk:Describe*",
        "servicequotas:Get*",
        "servicequotas:List*"
      ],
      "Resource": "*"
    }
  ]
}
```

**Important**: The tool NEVER fetches secret values from Secrets Manager, only metadata.

## Development

### Setup Development Environment

```bash
# Clone and setup
git clone https://github.com/yuvalbo/aws-comparator.git
cd aws-comparator

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install with dev dependencies
pip install -e ".[dev]"
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=aws_comparator --cov-report=html

# Run with verbose output
pytest -v
```

### Code Quality

```bash
# Format code
black src/ tests/

# Lint
flake8 src/ tests/
ruff check src/ tests/

# Type checking
mypy src/
```

## Troubleshooting

### Common Issues

**1. Credentials not found**
```
Error: AWS credentials not found
```
- Solution: Configure AWS credentials via `aws configure` or set environment variables

**2. Permission denied**
```
Error: Permission denied for ec2.DescribeInstances
```
- Solution: Ensure IAM user/role has required read permissions

**3. Invalid account ID**
```
Error: Account ID must be 12 digits
```
- Solution: Verify account IDs are exactly 12 digits

### Debug Mode

Enable debug logging for detailed troubleshooting:

```bash
aws-comparator compare -a1 123456789012 -a2 987654321098 -p1 prod -p2 staging -vvv
```

## Security

- **Least Privilege**: Use read-only IAM policies
- **Secrets Protection**: Tool never fetches secret values, only metadata
- **Credential Management**: Use AWS profiles or IAM roles
- **Audit Logging**: Enable CloudTrail for API calls

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

Built with:
- [boto3](https://github.com/boto/boto3) - AWS SDK for Python
- [Click](https://github.com/pallets/click) - CLI framework
- [Rich](https://github.com/Textualize/rich) - Terminal formatting
- [Pydantic](https://github.com/pydantic/pydantic) - Data validation

## Support

- Issues: [https://github.com/yuvalbo/aws-comparator/issues](https://github.com/yuvalbo/aws-comparator/issues)
- Discussions: [https://github.com/yuvalbo/aws-comparator/discussions](https://github.com/yuvalbo/aws-comparator/discussions)
