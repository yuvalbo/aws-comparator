# CLAUDE.md - Project Guidelines

## ⚠️ CRITICAL: Git Commit Rules ⚠️

**NEVER add Co-Authored-By lines to ANY commit. This is mandatory.**

When creating commits:
1. Do NOT add "Co-Authored-By:" trailers
2. Do NOT add "Co-authored-by:" trailers
3. Do NOT credit Claude, AI, or any assistant in commits
4. Use ONLY simple commit messages without trailers
5. The git user is: yuvalbo <yuvalbo@users.noreply.github.com>

Example of CORRECT commit:
```
git commit -m "Add new feature"
```

Example of WRONG commit (NEVER DO THIS):
```
git commit -m "Add new feature

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Project Overview

AWS Comparator is a CLI tool for comparing AWS resources across two accounts.

## Commands

```bash
# Install
python3 -m venv .venv && source .venv/bin/activate && pip install -e .

# Run tests
pytest

# Run with coverage
pytest --cov=aws_comparator

# Build Docker image
docker build -t aws-comparator .
```

## Architecture

- `src/aws_comparator/cli/` - CLI commands
- `src/aws_comparator/services/` - AWS service fetchers
- `src/aws_comparator/comparison/` - Comparison logic
- `src/aws_comparator/output/` - Output formatters
- `src/aws_comparator/models/` - Pydantic data models

---

## Code Style & Formatting

### Line Length & Formatting
- Maximum line length: 88 characters (Black/Ruff default)
- Use `ruff format` for all code formatting
- Never manually format code - let the formatter handle it

### Naming Conventions
- Variables and functions: `snake_case`
- Classes: `PascalCase`
- Constants: `UPPER_SNAKE_CASE`
- Private members: `_leading_underscore`
- Avoid single-letter variables except for iterators (i, j, k) and coordinates (x, y, z)

### Type Hints
- **REQUIRED** for all function signatures (arguments and return types)
- Use modern syntax: `list[str]` not `List[str]` (Python 3.9+)
- Enable mypy strict mode compliance
- Example:
```python
def process_file(path: str, options: dict[str, Any]) -> list[str]:
    ...
```

### Docstrings
- **REQUIRED** for all public functions, classes, and modules
- Use Google style format
- Include:
  - Brief description
  - Args with types and descriptions
  - Returns with type and description
  - Raises for expected exceptions
  - Examples for complex functions
- Example:
```python
def parse_config(config_path: str) -> dict[str, Any]:
    """Parse configuration file and return settings.

    Args:
        config_path: Path to the YAML or JSON config file.

    Returns:
        Dictionary containing parsed configuration settings.

    Raises:
        FileNotFoundError: If config file doesn't exist.
        ValueError: If config file is malformed.

    Examples:
        >>> config = parse_config("settings.yaml")
        >>> print(config["database"]["host"])
        localhost
    """
```

## Error Handling

### User-Facing Errors
- **ALWAYS** provide clear, actionable error messages
- Include what went wrong, why, and how to fix it
- Example:
```python
if not path.exists():
    raise FileNotFoundError(
        f"Configuration file not found: {path}\n"
        f"Expected location: {path.absolute()}\n"
        f"Please create the file or use --config to specify a different path."
    )
```

### Error Strategy
- Use specific exception types, not generic `Exception`
- Create custom exceptions for domain-specific errors:
```python
class ConfigurationError(Exception):
    """Raised when configuration is invalid or missing."""

class ProcessingError(Exception):
    """Raised when data processing fails."""
```
- Catch exceptions at the appropriate level (usually CLI entry point)
- Never use bare `except:` - always specify exception types
- Log errors before raising or re-raising them

### Exit Codes
Use standard exit codes:
- 0: Success
- 1: General error
- 2: Misuse of command (bad arguments)
- 130: Terminated by Ctrl+C

## Logging

### Logging Setup
- Use Python's standard `logging` module
- Configure in `cli.py` entry point
- Default to INFO level, support -v/--verbose for DEBUG
- Format: `%(asctime)s - %(name)s - %(levelname)s - %(message)s`

### Logging Levels
- **DEBUG**: Detailed diagnostic info (function calls, variable values)
- **INFO**: General progress information (file processed, operation completed)
- **WARNING**: Unexpected but handled situations (missing optional config)
- **ERROR**: Errors that prevent specific operations (file processing failed)
- **CRITICAL**: Fatal errors that stop the program (database unavailable)

### Example Usage
```python
import logging

logger = logging.getLogger(__name__)

def process_data(data: list[str]) -> None:
    logger.debug(f"Processing {len(data)} items")
    logger.info("Starting data processing")
    try:
        # ... processing logic
        logger.info("Data processing completed successfully")
    except ProcessingError as e:
        logger.error(f"Failed to process data: {e}")
        raise
```

### Logging Rules
- Never use `print()` for operational messages - use logging
- `print()` is only for actual CLI output (results, formatted data)
- Log at appropriate levels - don't spam INFO with debug details
- Include context in log messages (file names, counts, etc.)

## Dependencies

### Dependency Management
- Use `uv` for all dependency management
- Pin exact versions in production deployments
- Use version ranges in `pyproject.toml` for flexibility:
```toml
dependencies = [
    "click>=8.1.0,<9.0.0",
    "pydantic>=2.5.0,<3.0.0",
]
```

### Adding Dependencies
- Keep dependencies minimal - evaluate if you really need it
- Prefer well-maintained, popular libraries
- Check license compatibility
- Document why each major dependency is needed

### Version Requirements
- Minimum Python version: 3.9
- Use modern Python features available in 3.9+
- Avoid deprecated features

## Environment & Configuration

### Environment Variables
- Support `.env` files using `python-dotenv`
- Load at application startup
- Prefix with app name: `AWS_COMPARATOR_*`
- Document all environment variables in README.md

### Configuration Priority (highest to lowest)
1. Command-line arguments
2. Environment variables
3. Config file
4. Defaults

### Configuration Files
- Support YAML or JSON config files
- Use Pydantic for validation
- Provide example config file
- Never commit actual config files with secrets

## Documentation

### README.md Must Include
- Project description and purpose
- Installation instructions
- Quick start / basic usage examples
- Configuration options
- Environment variables
- Common use cases
- Troubleshooting section

### Inline Comments
- Explain **why**, not **what** (code should be self-explanatory)
- Comment complex algorithms or non-obvious business logic
- Use TODO comments sparingly and track them:
```python
# TODO(username): Implement caching for repeated queries
# NOTE: This workaround is needed because of upstream bug #123
```

## Testing

### Coverage Requirements
- Minimum 80% overall coverage
- 100% coverage for core business logic
- Run: `pytest --cov=aws_comparator --cov-report=html`

### Test Structure
- Mirror source structure in `tests/` directory
- Use descriptive test names: `test_parse_config_with_invalid_yaml_raises_error`
- Group related tests in classes
- Use fixtures for common setup

### Test Categories
```python
# Unit tests - test single functions in isolation
def test_validate_email_with_valid_email_returns_true():
    assert validate_email("user@example.com") is True

# Parametrized tests for multiple inputs
@pytest.mark.parametrize("input,expected", [
    ("valid", True),
    ("invalid", False),
])
def test_validation(input, expected):
    assert validate(input) == expected
```

## Git Workflow

### Commit Messages
Use Conventional Commits format:
```
<type>(<scope>): <subject>
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `style`: Code style (formatting)
- `refactor`: Code change that neither fixes a bug nor adds a feature
- `test`: Adding or updating tests
- `chore`: Maintenance (dependencies, build, etc.)

Examples:
```
feat(cli): add export command with JSON output
fix(config): handle missing config file gracefully
test: add integration tests for export command
```

## Code Review Checklist

Before suggesting code changes, verify:
- [ ] Type hints on all function signatures
- [ ] Docstrings on all public functions
- [ ] Appropriate logging at correct levels
- [ ] User-friendly error messages
- [ ] No `print()` for logging (only for output)
- [ ] Tests for new functionality
- [ ] Updated documentation if needed
- [ ] Conventional commit message format
- [ ] No hardcoded values (use config/env vars)
- [ ] Proper error handling (specific exceptions)

## Tools Configuration

Run before each commit:
```bash
ruff format .
ruff check . --fix
pytest --cov=aws_comparator
```

## When in Doubt

- Prioritize clarity over cleverness
- Write code that's easy to delete
- Make errors impossible, not just unlikely
- Document decisions, not just code
- Test behavior, not implementation
- Fail fast and fail clearly
