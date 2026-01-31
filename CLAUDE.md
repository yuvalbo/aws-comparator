# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This repository "aws comperator" (AWS Comparator) is currently in its initial setup phase. Based on the name, this project likely aims to compare AWS resources, configurations, or services.

**Note**: This CLAUDE.md file will need to be updated once the project structure and codebase are established.

## Getting Started

Once the project is set up, this section should include:
- Prerequisites (Node.js, Python, AWS CLI, etc.)
- Installation steps
- Environment setup (AWS credentials, configuration files)
- Initial configuration

## Commands

Update this section with actual commands once the project tooling is established:

```bash
# Example placeholders - replace with actual commands
# Build
npm run build / make build / python setup.py build

# Test
npm test / pytest / go test ./...

# Lint
npm run lint / pylint / flake8

# Development server
npm run dev / python manage.py runserver
```

## Architecture

This section should describe:
- Overall project structure (e.g., monorepo vs single package)
- Main components and their responsibilities
- Data flow between components
- External dependencies (AWS services, databases, APIs)

### Project Structure

```
# Update this tree once the codebase structure is established
aws-comperator/
├── src/           # Source code
├── tests/         # Test files
├── docs/          # Documentation
└── config/        # Configuration files
```

## AWS Integration

Since this is an AWS-related project, document:
- Required AWS services and permissions
- AWS SDK configuration
- Environment variables for AWS credentials
- Region-specific considerations

## Key Workflows

Document important workflows such as:
- How AWS resource comparison is performed
- Data collection and processing pipeline
- Report generation process
- Authentication and authorization flow

## Development Guidelines

### Naming Conventions
- Document any specific naming patterns used in the codebase

### Code Organization
- Explain how code is organized (e.g., by feature, by layer)

### Testing Strategy
- Unit tests location and patterns
- Integration tests approach
- Mocking AWS services in tests

## Configuration

Document configuration files and their purposes:
- Environment variables
- AWS configuration files
- Application settings

## Common Patterns

Once the codebase develops, document:
- Frequently used patterns for AWS operations
- Error handling approaches
- Logging conventions
- Data transformation patterns

## Troubleshooting

Add common issues and their solutions as they are discovered during development.

---

**TODO**: This file should be updated as the project develops with:
1. Actual build and development commands
2. Real architecture details
3. Specific AWS services being used
4. Concrete examples of comparison logic
5. Integration with other tools or services
