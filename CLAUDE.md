# CLAUDE.md - Project Guidelines

## CRITICAL: Git Commit Rules

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
