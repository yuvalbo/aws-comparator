# AWS Account Comparator

A powerful Python CLI tool for comparing AWS resources across two accounts and generating detailed diff reports.

[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue)]
[![License](https://img.shields.io/badge/license-MIT-green)]
[![Development Status](https://img.shields.io/badge/status-alpha-orange)]

## Overview

AWS Account Comparator helps you identify configuration differences between AWS accounts, making it easier to:

- **Audit Drift**: Detect configuration drift between production/staging environments
- **Validate Migrations**: Ensure resources are correctly migrated between accounts
- **Compliance Checking**: Verify that accounts conform to organizational standards
- **Cost Analysis**: Identify resource discrepancies that may impact costs
- **Security Review**: Compare security configurations across accounts

### Supported AWS Services

Currently supports 11 AWS services:

- **EC2**: Instances, Security Groups, VPCs, Subnets, Route Tables, Network ACLs
- **S3**: Buckets, Policies, Lifecycle Rules, Encryption, Versioning
- **Lambda**: Functions, Layers, Event Source Mappings, Aliases
- **Secrets Manager**: Secret metadata (values never fetched)
- **SQS**: Queues and attributes
- **CloudWatch**: Alarms, Log Groups, Dashboards
- **Bedrock**: Model access and custom models
- **Pinpoint**: Applications, Campaigns, Segments
- **EventBridge**: Event buses, Rules, Targets
- **Elastic Beanstalk**: Applications and Environments
- **Service Quotas**: Service limits across all services

## Installation

### Prerequisites

- Python 3.9 or higher
- AWS credentials configured
- Appropriate IAM permissions (read-only access to services)

### From Source (Development)

```bash
# Clone the repository
git clone https://github.com/yourusername/aws-comparator.git
cd aws-comparator

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e ".[dev]"

# Verify installation
aws-comparator --version
```

### From PyPI (Future Release)

```bash
pip install aws-comparator
```

## Quick Start

### Basic Usage

Compare all services between two accounts:

```bash
aws-comparator compare 123456789012 987654321098
```

### Common Use Cases

**Compare specific services:**
```bash
aws-comparator compare 123456789012 987654321098 --services ec2,s3,lambda
```

**Use specific AWS profiles:**
```bash
aws-comparator compare 123456789012 987654321098 \\
  --profile prod-account \\
  --region us-east-1
```

**Output to JSON file:**
```bash
aws-comparator compare 123456789012 987654321098 \\
  --output-format json \\
  --output-file comparison-report.json
```

**Filter by severity:**
```bash
aws-comparator compare 123456789012 987654321098 \\
  --filter-severity high  # Only show high/critical changes
```

**Verbose output for debugging:**
```bash
aws-comparator compare 123456789012 987654321098 -vv
```

## Configuration

### Configuration File

Create `~/.aws-comparator/config.yaml` for persistent settings:

```yaml
defaults:
  region: us-east-1
  output_format: table
  parallel_execution: true
  max_workers: 10
  log_level: INFO

services:
  ec2:
    enabled: true
    exclude_tags:
      temporary: "*"

  s3:
    enabled: true
    check_policies: true

filters:
  ignore_fields:
    - LastModifiedDate
    - CreationDate
    - LaunchTime

  ignore_tags:
    - temporary
    - "automation:*"  # Wildcard pattern

output:
  colors: true
  verbose: false
```

### Environment Variables

Configure via environment variables:

```bash
export AWS_COMPARATOR_REGION=us-east-1
export AWS_COMPARATOR_OUTPUT_FORMAT=json
export AWS_COMPARATOR_LOG_LEVEL=DEBUG
export AWS_COMPARATOR_MAX_WORKERS=20
```

### AWS Authentication

The tool uses the standard AWS credential chain:

1. Explicit `--profile` argument
2. `AWS_PROFILE` environment variable
3. Assume role if `--role-arn` provided
4. Default AWS credentials (`~/.aws/credentials`)
5. IAM instance profile (if running on EC2)

**Example with assume role:**
```bash
aws-comparator compare 123456789012 987654321098 \\
  --role-arn arn:aws:iam::123456789012:role/ComparisonRole \\
  --external-id my-external-id
```

## CLI Reference

### Main Commands

#### `compare`

Compare resources between two AWS accounts.

```bash
aws-comparator compare [OPTIONS] ACCOUNT1 ACCOUNT2
```

**Arguments:**
- `ACCOUNT1`: First AWS account ID (12 digits)
- `ACCOUNT2`: Second AWS account ID (12 digits)

**Options:**
- `--services TEXT`: Comma-separated list of services
- `--profile TEXT`: AWS profile name
- `--region TEXT`: AWS region (default: us-east-1)
- `--output-format CHOICE`: json, yaml, or table
- `--output-file PATH`: Write output to file
- `--parallel/--sequential`: Parallel execution (default: parallel)
- `--max-workers INTEGER`: Maximum parallel workers (1-50)
- `--filter-severity CHOICE`: Minimum severity (info, low, medium, high, critical)
- `--verbose, -v`: Increase verbosity (-v, -vv, -vvv)
- `--quiet, -q`: Suppress non-error output
- `--no-color`: Disable colored output

#### `list-services`

List all supported AWS services.

```bash
aws-comparator list-services [--detailed]
```

#### `validate`

Validate AWS credentials and permissions.

```bash
aws-comparator validate ACCOUNT_ID [OPTIONS]
```

## IAM Permissions

### Minimum Required Permissions

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
        "lambda:Get*",
        "lambda:List*",
        "secretsmanager:DescribeSecret",
        "secretsmanager:ListSecrets",
        "sqs:GetQueueAttributes",
        "sqs:ListQueues",
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
git clone https://github.com/yourusername/aws-comparator.git
cd aws-comparator

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install with dev dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=aws_comparator --cov-report=html

# Run specific test categories
pytest -m unit           # Unit tests only
pytest -m integration    # Integration tests only
pytest -m "not slow"     # Skip slow tests

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

### Project Structure

```
aws-comparator/
├── src/aws_comparator/
│   ├── cli/              # CLI commands
│   ├── core/             # Core business logic
│   │   ├── config.py     # Configuration management
│   │   ├── exceptions.py # Custom exceptions
│   │   ├── logging.py    # Logging setup
│   │   └── registry.py   # Service registry
│   ├── services/         # Service fetchers
│   │   ├── base.py       # Base fetcher class
│   │   ├── ec2/          # EC2 fetcher
│   │   ├── s3/           # S3 fetcher
│   │   └── ...
│   ├── comparison/       # Comparison engine
│   ├── output/           # Output formatters
│   ├── models/           # Pydantic models
│   └── orchestration/    # Orchestration layer
├── tests/
│   ├── unit/             # Unit tests
│   ├── integration/      # Integration tests
│   └── conftest.py       # Pytest fixtures
├── docs/                 # Documentation
└── examples/             # Example configurations
```

## Implementation Status

**Current Phase: Phase 3 - Core Infrastructure** ✅

### Completed Components

- ✅ Project structure and build configuration
- ✅ Exception hierarchy with 50+ error codes
- ✅ Pydantic models for all data structures
- ✅ Configuration management (file, env, CLI)
- ✅ Service registry pattern
- ✅ Logging infrastructure with Rich
- ✅ Base classes for fetchers, comparators, formatters
- ✅ Unit tests with >80% coverage

### Upcoming Phases

- 🔄 Phase 4: Service Fetchers (11 AWS services)
- 🔄 Phase 5: Comparison Engine
- 🔄 Phase 6: Output Formatters
- 🔄 Phase 7: Orchestration Layer
- 🔄 Phase 8: CLI Implementation

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Adding a New Service

1. Create a new fetcher in `src/aws_comparator/services/your_service/`
2. Implement `BaseServiceFetcher` interface
3. Register with `@ServiceRegistry.register('your-service')`
4. Add Pydantic models for resources
5. Write unit and integration tests

Example:

```python
from aws_comparator.core.registry import ServiceRegistry
from aws_comparator.services.base import BaseServiceFetcher

@ServiceRegistry.register('dynamodb', description='DynamoDB Tables')
class DynamoDBFetcher(BaseServiceFetcher):
    SERVICE_NAME = 'dynamodb'

    def _create_client(self):
        return self.session.client('dynamodb', region_name=self.region)

    def fetch_resources(self):
        return {'tables': self._fetch_tables()}

    def get_resource_types(self):
        return ['tables']

    def _fetch_tables(self):
        # Implementation
        pass
```

## Troubleshooting

### Common Issues

**1. Credentials not found**
```
Error: [AUTH-001] AWS credentials not found
```
- Solution: Configure AWS credentials via `aws configure` or set environment variables

**2. Permission denied**
```
Error: [PERM-001] Permission denied: ec2.DescribeInstances
```
- Solution: Ensure IAM user/role has required read permissions

**3. Service not available**
```
Error: [SERV-001] Service bedrock not available in region us-east-1
```
- Solution: Use a region where the service is available, or exclude the service

**4. Throttling errors**
```
Error: [SERV-003] Throttling error for s3.ListBuckets
```
- Solution: Reduce `--max-workers` or retry after a delay

### Debug Mode

Enable debug logging for detailed troubleshooting:

```bash
aws-comparator compare 123456789012 987654321098 -vvv
```

## Security

### Security Best Practices

1. **Least Privilege**: Use read-only IAM policies
2. **Secrets Protection**: Tool never fetches secret values
3. **Credential Management**: Use AWS profiles or IAM roles
4. **Audit Logging**: Enable CloudTrail for API calls
5. **Network Security**: Use VPC endpoints if running on EC2

### Reporting Security Issues

Please report security vulnerabilities to security@example.com

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

Built with:
- [boto3](https://github.com/boto/boto3) - AWS SDK for Python
- [Click](https://github.com/pallets/click) - CLI framework
- [Rich](https://github.com/Textualize/rich) - Terminal formatting
- [DeepDiff](https://github.com/seperman/deepdiff) - Deep comparison
- [Pydantic](https://github.com/pydantic/pydantic) - Data validation

## Support

- Documentation: [https://github.com/yourusername/aws-comparator](https://github.com/yourusername/aws-comparator)
- Issues: [https://github.com/yourusername/aws-comparator/issues](https://github.com/yourusername/aws-comparator/issues)
- Discussions: [https://github.com/yourusername/aws-comparator/discussions](https://github.com/yourusername/aws-comparator/discussions)

---

**Status**: Alpha - Core infrastructure complete, service implementations in progress
