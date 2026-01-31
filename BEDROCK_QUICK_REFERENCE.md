# Bedrock Service Fetcher - Quick Reference

## Files Created

| File | Lines | Purpose |
|------|-------|---------|
| `src/aws_comparator/models/bedrock.py` | 374 | Pydantic models for all Bedrock resources |
| `src/aws_comparator/services/bedrock/__init__.py` | 9 | Module exports |
| `src/aws_comparator/services/bedrock/fetcher.py` | 272 | Main fetcher implementation |
| `tests/services/test_bedrock.py` | 503 | Comprehensive unit tests |
| **Total** | **1,158** | **Complete implementation** |

## Pydantic Models (5 models)

1. **FoundationModel** - Available models from providers
2. **CustomModel** - Fine-tuned custom models  
3. **ProvisionedModelThroughput** - Provisioned capacity configs
4. **ModelAccessConfiguration** - Model access status
5. **Guardrail** - Content filtering rules

## Fetcher Methods

```python
BedrockFetcher(session, region)
├── fetch_resources() → Dict[str, List[AWSResource]]
│   ├── foundation_models
│   ├── custom_models
│   ├── provisioned_throughput
│   └── guardrails
│
├── _fetch_foundation_models() → List[FoundationModel]
├── _fetch_custom_models() → List[CustomModel]  
├── _fetch_provisioned_throughput() → List[ProvisionedModelThroughput]
└── _fetch_guardrails() → List[Guardrail]
```

## Test Coverage

- **7 Test Classes** covering all functionality
- **20+ Test Methods** with diverse scenarios
- **Expected Coverage**: >85%

### Test Categories
- ✅ Initialization tests
- ✅ Success case tests with realistic data
- ✅ Empty result handling
- ✅ Pagination tests
- ✅ Error handling (AccessDenied, ClientError, generic exceptions)
- ✅ Malformed response handling
- ✅ Integration tests

## Key Features

### Quality Standards Met
- ✅ 100% type hints (mypy strict)
- ✅ 100% docstrings (Google style)
- ✅ Follows existing patterns from S3/SQS/Lambda fetchers
- ✅ Registered with ServiceRegistry
- ✅ Graceful error handling
- ✅ Pagination support
- ✅ Regional availability handling

### Boto3 APIs Used
- `list_foundation_models` - Lists available models
- `list_custom_models` (paginated) - Lists custom models
- `list_provisioned_model_throughputs` (paginated) - Lists provisioned capacity
- `list_guardrails` (paginated) - Lists guardrails

## Usage

```python
from aws_comparator.services.bedrock import BedrockFetcher
import boto3

session = boto3.Session(profile_name='my-profile')
fetcher = BedrockFetcher(session, 'us-east-1')

# Fetch all Bedrock resources
resources = fetcher.fetch_resources()

# Access specific types
foundation_models = resources['foundation_models']  # List[FoundationModel]
custom_models = resources['custom_models']          # List[CustomModel]
throughput = resources['provisioned_throughput']    # List[ProvisionedModelThroughput]
guardrails = resources['guardrails']                # List[Guardrail]
```

## Testing

```bash
# Run Bedrock tests
pytest tests/services/test_bedrock.py -v

# With coverage report
pytest tests/services/test_bedrock.py --cov=aws_comparator.services.bedrock --cov-report=html

# Run specific test class
pytest tests/services/test_bedrock.py::TestFetchFoundationModels -v
```

## Integration

The fetcher automatically integrates with the comparator:
1. Auto-registered with `ServiceRegistry`
2. Available via `aws-comparator list-services`
3. Invoked when comparing Bedrock resources
4. Handles regional availability gracefully

## Error Handling

All fetch methods handle:
- `AccessDenied` / `UnauthorizedOperation` → Logs warning, returns empty list
- `ClientError` (other) → Logs error, returns empty list
- Generic exceptions → Logs error with traceback, returns empty list
- Malformed responses → Skips invalid entries, continues processing

This ensures one bad resource doesn't break the entire comparison.
