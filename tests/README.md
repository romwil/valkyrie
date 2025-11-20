# Valkyrie Test Suite

Comprehensive test suite for the Valkyrie lead enrichment platform.

## Test Structure

```
tests/
├── __init__.py
├── conftest.py          # Pytest configuration and shared fixtures
├── factories.py         # Factory-boy test data factories
├── test_models/         # Database model unit tests
│   ├── __init__.py
│   └── test_models.py
├── test_api/            # API endpoint tests
│   ├── __init__.py
│   ├── test_auth.py
│   ├── test_jobs_api.py
│   ├── test_records_api.py
│   ├── test_companies_api.py
│   └── test_analytics_api.py
├── test_worker/         # Background worker tests
│   ├── __init__.py
│   └── test_tasks.py
├── test_processors/     # LLM processor tests
│   ├── __init__.py
│   └── test_llm_processor.py
└── test_integration.py  # End-to-end integration tests
```

## Running Tests

### Install test dependencies
```bash
pip install -r requirements-dev.txt
```

### Run all tests
```bash
pytest
```

### Run with coverage
```bash
pytest --cov=src --cov-report=html --cov-report=term-missing
```

### Run specific test categories
```bash
# Unit tests only
pytest tests/test_models tests/test_api tests/test_worker tests/test_processors

# Integration tests only
pytest tests/test_integration.py

# API tests only
pytest tests/test_api/
```

### Run with verbose output
```bash
pytest -v
```

### Run specific test
```bash
pytest tests/test_api/test_jobs_api.py::TestJobsAPI::test_create_job
```

## Test Categories

### Unit Tests
- **Model Tests**: Test database models, relationships, and constraints
- **API Tests**: Test individual API endpoints with mocked dependencies
- **Worker Tests**: Test background task processing with mocked external services
- **Processor Tests**: Test LLM integration and data processing logic

### Integration Tests
- **End-to-End Workflows**: Test complete user workflows from API to completion
- **Authentication Flows**: Test user registration, login, and authorization
- **Data Consistency**: Test data integrity across operations
- **Concurrent Operations**: Test handling of concurrent requests and jobs
- **Error Recovery**: Test error handling and partial failure scenarios
- **Performance**: Test with larger datasets to ensure scalability

## Test Fixtures

Common fixtures available in `conftest.py`:
- `db_session`: Test database session with rollback
- `client`: FastAPI test client
- `sample_user`: Pre-created test user
- `sample_job`: Pre-created enrichment job
- `sample_company`: Pre-created company
- `auth_headers`: Authentication headers with valid token
- `mock_gemini`: Mocked Gemini API responses

## Test Data Factories

Factory-boy factories for generating test data:
- `UserFactory`: Create test users
- `JobFactory`: Create enrichment jobs
- `RecordFactory`: Create job records
- `CompanyFactory`: Create companies

## Mocking External Services

### Gemini API
The Gemini API is automatically mocked in all tests via the `mock_gemini` fixture.
To customize responses:

```python
def test_custom_gemini_response(mock_gemini):
    mock_gemini.return_value.generate_content.return_value.text = json.dumps({
        "industry": "Custom Industry",
        "size": "100-500"
    })
```

### Database
Tests use a separate test database that is rolled back after each test.

## Coverage Requirements

- Minimum coverage: 80%
- Critical paths must have 100% coverage
- All API endpoints must be tested
- All error conditions must be tested

## CI/CD Integration

Tests run automatically on:
- Push to main, develop, or feature branches
- Pull requests to main or develop

GitHub Actions workflow includes:
- Multi-version Python testing (3.9, 3.10, 3.11)
- Code quality checks (flake8, black, isort, mypy)
- Security scanning (bandit)
- Coverage reporting to Codecov

## Writing New Tests

1. Follow existing test structure and naming conventions
2. Use descriptive test names that explain what is being tested
3. Include docstrings for test classes and methods
4. Use fixtures for common setup
5. Mock external dependencies
6. Test both success and failure cases
7. Keep tests focused and independent

## Debugging Tests

### Run with debugging output
```bash
pytest -s  # Don't capture stdout
pytest --pdb  # Drop into debugger on failure
```

### Run with specific log level
```bash
pytest --log-cli-level=DEBUG
```
