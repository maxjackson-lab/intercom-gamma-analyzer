# Testing Guide

This document provides comprehensive information about testing the Intercom Analysis Tool.

## Overview

The project uses a comprehensive testing strategy with:
- **Unit Tests**: Test individual components in isolation
- **Integration Tests**: Test component interactions
- **Coverage Reporting**: Track test coverage
- **Linting**: Ensure code quality and consistency

## Test Structure

```
tests/
├── test_category_filters.py      # CategoryFilters service tests
├── test_base_category_analyzer.py # BaseCategoryAnalyzer tests
├── test_billing_analyzer.py      # BillingAnalyzer tests
├── test_product_analyzer.py      # ProductAnalyzer tests
├── test_sites_analyzer.py        # SitesAnalyzer tests
├── test_api_analyzer.py          # ApiAnalyzer tests
├── test_gamma_generator.py       # GammaGenerator service tests
├── test_chunked_fetcher.py       # ChunkedFetcher service tests
└── test_data_preprocessor.py     # DataPreprocessor service tests
```

## Running Tests

### Quick Start

```bash
# Run all tests with coverage
python run_tests.py

# Run only linting checks
python run_tests.py --lint-only

# Run specific test files
python run_tests.py --test-files tests/test_billing_analyzer.py tests/test_product_analyzer.py

# Show help
python run_tests.py --help
```

### Manual Test Execution

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_billing_analyzer.py

# Run specific test method
pytest tests/test_billing_analyzer.py::TestBillingAnalyzer::test_analyze_category_success

# Run tests matching pattern
pytest -k "test_analyze_category"

# Run async tests
pytest -m asyncio
```

## Test Categories

### Unit Tests

Unit tests focus on testing individual components in isolation:

- **CategoryFilters**: Tests filtering logic for different categories
- **BaseCategoryAnalyzer**: Tests common functionality for all analyzers
- **BillingAnalyzer**: Tests billing-specific analysis logic
- **ProductAnalyzer**: Tests product-specific analysis logic
- **SitesAnalyzer**: Tests sites-specific analysis logic
- **ApiAnalyzer**: Tests API-specific analysis logic
- **GammaGenerator**: Tests presentation generation
- **ChunkedFetcher**: Tests data fetching with pagination
- **DataPreprocessor**: Tests data cleaning and normalization

### Integration Tests

Integration tests verify component interactions:

- End-to-end analysis workflows
- Service integration with external APIs
- Data flow between components

## Test Coverage

The project aims for high test coverage:

- **Target**: 90%+ code coverage
- **Critical Components**: 95%+ coverage
- **New Features**: 100% coverage requirement

### Coverage Reports

```bash
# Generate HTML coverage report
pytest --cov=src --cov-report=html

# View coverage report
open htmlcov/index.html

# Generate JSON coverage data
pytest --cov=src --cov-report=json
```

## Test Data

### Fixtures

Tests use pytest fixtures for consistent test data:

```python
@pytest.fixture
def sample_conversations():
    """Create sample conversation data for testing."""
    return [
        {
            'id': 'conv_1',
            'conversation_parts': {...},
            'source': {...},
            'tags': {...},
            # ... more fields
        }
    ]
```

### Mock Data

Tests use mock data to avoid external dependencies:

- **Intercom API**: Mocked responses
- **OpenAI API**: Mocked responses
- **Gamma API**: Mocked responses

## Writing Tests

### Test Naming

Follow these naming conventions:

```python
def test_component_method_scenario():
    """Test specific scenario for component method."""
    pass

def test_component_method_error_case():
    """Test error handling for component method."""
    pass

def test_component_method_edge_case():
    """Test edge case for component method."""
    pass
```

### Test Structure

Use the Arrange-Act-Assert pattern:

```python
def test_analyze_category_success(self, analyzer, sample_data):
    """Test successful category analysis."""
    # Arrange
    start_date = datetime(2022, 1, 1)
    end_date = datetime(2022, 1, 31)
    options = {'generate_ai_insights': False}
    
    # Act
    result = await analyzer.analyze_category(sample_data, start_date, end_date, options)
    
    # Assert
    assert result['category'] == 'ExpectedCategory'
    assert 'data_summary' in result
    assert 'analysis_results' in result
```

### Async Tests

For async methods, use pytest-asyncio:

```python
@pytest.mark.asyncio
async def test_async_method(self, analyzer):
    """Test async method."""
    result = await analyzer.async_method()
    assert result is not None
```

### Mocking

Use unittest.mock for external dependencies:

```python
@patch('module.external_service')
def test_with_mock(self, mock_service):
    """Test with mocked external service."""
    mock_service.return_value = "mocked_response"
    result = self.component.method()
    assert result == "expected_result"
```

## Test Configuration

### pytest.ini

```ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    -v
    --tb=short
    --strict-markers
    --disable-warnings
    --color=yes
    --durations=10
```

### .coveragerc

```ini
[run]
source = src
omit = 
    */tests/*
    */test_*
    */__pycache__/*
    */venv/*
    */env/*
    */.*
```

## Continuous Integration

### GitHub Actions

Tests run automatically on:
- Pull requests
- Push to main branch
- Scheduled runs

### Pre-commit Hooks

```bash
# Install pre-commit hooks
pre-commit install

# Run hooks manually
pre-commit run --all-files
```

## Debugging Tests

### Verbose Output

```bash
# Show detailed test output
pytest -v -s

# Show test durations
pytest --durations=10

# Show slowest tests
pytest --durations=0
```

### Debug Mode

```bash
# Drop into debugger on failure
pytest --pdb

# Drop into debugger on first failure
pytest --pdb -x
```

### Test Discovery

```bash
# List all tests
pytest --collect-only

# List tests matching pattern
pytest --collect-only -k "test_analyze"
```

## Best Practices

### Test Organization

1. **One test file per component**
2. **Group related tests in classes**
3. **Use descriptive test names**
4. **Keep tests focused and simple**

### Test Data

1. **Use fixtures for common data**
2. **Create realistic test data**
3. **Test edge cases and error conditions**
4. **Avoid hardcoded values**

### Assertions

1. **Use specific assertions**
2. **Test both positive and negative cases**
3. **Verify error messages**
4. **Check return values and side effects**

### Performance

1. **Mock external dependencies**
2. **Use async tests for async code**
3. **Avoid slow operations in tests**
4. **Use parametrized tests for multiple inputs**

## Troubleshooting

### Common Issues

1. **Import Errors**: Check PYTHONPATH and module structure
2. **Async Test Failures**: Ensure @pytest.mark.asyncio decorator
3. **Mock Issues**: Verify mock setup and return values
4. **Coverage Issues**: Check .coveragerc configuration

### Test Failures

1. **Check test output for details**
2. **Verify test data and expectations**
3. **Check for timing issues in async tests**
4. **Verify mock configurations**

## Resources

- [pytest Documentation](https://docs.pytest.org/)
- [pytest-asyncio Documentation](https://pytest-asyncio.readthedocs.io/)
- [pytest-cov Documentation](https://pytest-cov.readthedocs.io/)
- [unittest.mock Documentation](https://docs.python.org/3/library/unittest.mock.html)