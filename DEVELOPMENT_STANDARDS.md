# Development Standards for Intercom Analysis Tool

## Core Principles

### 1. Test-Driven Development (TDD)
**Every feature MUST include comprehensive unit tests before implementation is considered complete.**

### 2. Comprehensive Logging
**Every component MUST have proper logging for debugging, monitoring, and troubleshooting.**

### 3. Error Handling
**Every function MUST handle errors gracefully with proper logging and user feedback.**

## Development Workflow

### Before Starting Any Feature:
1. **Write tests first** - Define expected behavior through tests
2. **Plan logging strategy** - Identify what needs to be logged and at what levels
3. **Design error handling** - Plan how errors will be caught and handled
4. **Update documentation** - Document the feature's purpose and usage

### During Development:
1. **Run tests frequently** - Ensure tests pass as you develop
2. **Add logging statements** - Log important events, errors, and debug info
3. **Handle edge cases** - Test and handle unusual inputs/conditions
4. **Validate inputs** - Check all inputs and provide clear error messages

### Before Completing Any Feature:
1. **All tests must pass** - 100% test coverage for new code
2. **Logging is comprehensive** - All important events are logged
3. **Error handling is complete** - No unhandled exceptions
4. **Documentation is updated** - README, docstrings, and comments are current

## Testing Standards

### Test Requirements:
- **Unit tests** for every function/method
- **Integration tests** for service interactions
- **Error case tests** for exception handling
- **Edge case tests** for boundary conditions
- **Mock external dependencies** (APIs, databases, files)

### Test Structure:
```python
class TestNewFeature:
    """Test cases for new feature."""
    
    def test_normal_operation(self):
        """Test normal operation with valid inputs."""
        # Arrange
        input_data = create_test_data()
        
        # Act
        result = new_feature.process(input_data)
        
        # Assert
        assert result is not None
        assert result.status == "success"
    
    def test_error_handling(self):
        """Test error handling with invalid inputs."""
        # Arrange
        invalid_input = None
        
        # Act & Assert
        with pytest.raises(ValueError, match="Invalid input"):
            new_feature.process(invalid_input)
    
    def test_edge_cases(self):
        """Test edge cases and boundary conditions."""
        # Test empty inputs, maximum values, etc.
        pass
    
    @pytest.mark.asyncio
    async def test_async_operation(self):
        """Test async operations."""
        result = await new_feature.async_process()
        assert result is not None
```

### Test Naming Convention:
- **Test files**: `test_<module_name>.py`
- **Test classes**: `Test<ClassName>`
- **Test methods**: `test_<specific_functionality>`
- **Async tests**: `test_<async_functionality>`

## Logging Standards

### Logging Levels:
- **DEBUG**: Detailed information for debugging
- **INFO**: General information about program execution
- **WARNING**: Something unexpected happened, but program continues
- **ERROR**: A serious problem occurred, some function failed
- **CRITICAL**: A very serious error occurred, program may stop

### Logging Requirements:
```python
import logging

logger = logging.getLogger(__name__)

class NewFeature:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def process_data(self, data):
        """Process data with comprehensive logging."""
        self.logger.info(f"Starting data processing for {len(data)} items")
        
        try:
            # Process data
            result = self._do_processing(data)
            self.logger.info(f"Successfully processed {len(result)} items")
            return result
            
        except ValueError as e:
            self.logger.error(f"Invalid data provided: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error during processing: {e}")
            self.logger.debug(f"Error details: {e}", exc_info=True)
            raise
    
    async def async_operation(self):
        """Async operation with logging."""
        self.logger.info("Starting async operation")
        
        try:
            result = await self._async_work()
            self.logger.info("Async operation completed successfully")
            return result
        except Exception as e:
            self.logger.error(f"Async operation failed: {e}")
            raise
```

### Logging Best Practices:
1. **Log at appropriate levels** - Don't log everything as INFO
2. **Include context** - Log relevant data (IDs, counts, parameters)
3. **Log errors with stack traces** - Use `exc_info=True` for debugging
4. **Use structured logging** - Include relevant metadata
5. **Log performance metrics** - Timing, counts, success rates

## Error Handling Standards

### Error Handling Requirements:
```python
class NewFeature:
    def robust_method(self, input_data):
        """Method with comprehensive error handling."""
        # Validate inputs
        if not input_data:
            raise ValueError("Input data cannot be empty")
        
        try:
            # Main logic
            result = self._process(input_data)
            return result
            
        except SpecificException as e:
            self.logger.error(f"Specific error occurred: {e}")
            # Handle specific case
            return self._handle_specific_error(e)
            
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}", exc_info=True)
            # Re-raise or handle gracefully
            raise ProcessingError(f"Failed to process data: {e}") from e
```

### Error Handling Best Practices:
1. **Validate inputs early** - Check inputs at function entry
2. **Use specific exceptions** - Don't just catch generic Exception
3. **Provide meaningful error messages** - Help users understand what went wrong
4. **Log errors before re-raising** - Ensure errors are logged
5. **Use exception chaining** - Preserve original exception context

## Code Quality Standards

### Code Structure:
```python
"""
Module docstring describing the module's purpose.
"""

import logging
from typing import List, Dict, Optional, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class NewFeature:
    """
    Class docstring describing the class purpose and usage.
    
    Args:
        param1: Description of parameter
        param2: Description of parameter
    """
    
    def __init__(self, param1: str, param2: Optional[int] = None):
        """Initialize the feature with proper logging."""
        self.param1 = param1
        self.param2 = param2
        self.logger = logging.getLogger(__name__)
        
        self.logger.info(f"Initializing {self.__class__.__name__} with param1={param1}")
    
    def public_method(self, data: List[Dict]) -> Dict[str, Any]:
        """
        Public method with comprehensive docstring.
        
        Args:
            data: List of data dictionaries to process
            
        Returns:
            Dictionary containing processed results
            
        Raises:
            ValueError: If data is empty or invalid
            ProcessingError: If processing fails
        """
        self.logger.info(f"Processing {len(data)} items")
        
        # Implementation with proper error handling and logging
        pass
```

### Code Quality Requirements:
1. **Type hints** - All functions must have type annotations
2. **Docstrings** - All public methods must have docstrings
3. **Error handling** - All functions must handle errors appropriately
4. **Logging** - All important operations must be logged
5. **Input validation** - All inputs must be validated

## Testing Checklist

### Before Committing Any Code:
- [ ] All new functions have unit tests
- [ ] All tests pass (`pytest tests/`)
- [ ] Test coverage is maintained or improved
- [ ] Error cases are tested
- [ ] Edge cases are tested
- [ ] Async functions have async tests
- [ ] Mock external dependencies
- [ ] Logging is tested (if applicable)

### Logging Checklist:
- [ ] Important operations are logged at INFO level
- [ ] Errors are logged at ERROR level with context
- [ ] Debug information is logged at DEBUG level
- [ ] Performance metrics are logged
- [ ] User actions are logged
- [ ] External API calls are logged
- [ ] File operations are logged

### Error Handling Checklist:
- [ ] Input validation is performed
- [ ] Specific exceptions are caught and handled
- [ ] Generic exceptions are caught and logged
- [ ] Error messages are user-friendly
- [ ] Errors are logged before re-raising
- [ ] Graceful degradation is implemented where possible

## Continuous Integration

### Automated Checks:
1. **Test execution** - All tests must pass
2. **Code coverage** - Maintain minimum coverage threshold
3. **Linting** - Code must pass linting checks
4. **Type checking** - Type hints must be valid
5. **Documentation** - Docstrings must be present

### Pre-commit Hooks:
```bash
# Install pre-commit hooks
pip install pre-commit
pre-commit install

# Run checks manually
pre-commit run --all-files
```

## Monitoring and Debugging

### Production Logging:
- **Structured logging** - Use JSON format for log aggregation
- **Log levels** - Configure appropriate levels for production
- **Performance logging** - Log timing and resource usage
- **Error tracking** - Integrate with error tracking services

### Debugging Support:
- **Debug logging** - Comprehensive debug information
- **Stack traces** - Full exception details
- **Context information** - Request IDs, user IDs, etc.
- **Performance metrics** - Timing, memory usage, etc.

## Examples

### Good Example:
```python
import logging
from typing import List, Dict, Optional
import asyncio

logger = logging.getLogger(__name__)


class ConversationAnalyzer:
    """Analyzes conversation data with comprehensive logging and error handling."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize analyzer with configuration."""
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"Initializing ConversationAnalyzer with config keys: {list(config.keys())}")
    
    async def analyze_conversations(self, conversations: List[Dict]) -> Dict[str, Any]:
        """
        Analyze a list of conversations.
        
        Args:
            conversations: List of conversation dictionaries
            
        Returns:
            Analysis results dictionary
            
        Raises:
            ValueError: If conversations list is empty
            AnalysisError: If analysis fails
        """
        self.logger.info(f"Starting analysis of {len(conversations)} conversations")
        
        if not conversations:
            error_msg = "Conversations list cannot be empty"
            self.logger.error(error_msg)
            raise ValueError(error_msg)
        
        try:
            # Perform analysis
            results = await self._perform_analysis(conversations)
            
            self.logger.info(f"Analysis completed successfully. Found {len(results.get('insights', []))} insights")
            return results
            
        except Exception as e:
            self.logger.error(f"Analysis failed: {e}", exc_info=True)
            raise AnalysisError(f"Failed to analyze conversations: {e}") from e
    
    async def _perform_analysis(self, conversations: List[Dict]) -> Dict[str, Any]:
        """Internal analysis method."""
        self.logger.debug("Performing detailed analysis")
        
        # Analysis logic here
        results = {"insights": [], "metrics": {}}
        
        self.logger.debug(f"Analysis completed with {len(results['insights'])} insights")
        return results


class AnalysisError(Exception):
    """Custom exception for analysis errors."""
    pass
```

### Test Example:
```python
import pytest
from unittest.mock import AsyncMock, patch
from conversation_analyzer import ConversationAnalyzer, AnalysisError


class TestConversationAnalyzer:
    """Test cases for ConversationAnalyzer."""
    
    def test_initialization(self):
        """Test analyzer initialization."""
        config = {"setting1": "value1"}
        analyzer = ConversationAnalyzer(config)
        
        assert analyzer.config == config
        assert analyzer.logger is not None
    
    def test_analyze_conversations_empty_list(self):
        """Test analysis with empty conversation list."""
        analyzer = ConversationAnalyzer({})
        
        with pytest.raises(ValueError, match="Conversations list cannot be empty"):
            asyncio.run(analyzer.analyze_conversations([]))
    
    @pytest.mark.asyncio
    async def test_analyze_conversations_success(self):
        """Test successful conversation analysis."""
        analyzer = ConversationAnalyzer({})
        conversations = [{"id": "1", "text": "test"}]
        
        with patch.object(analyzer, '_perform_analysis') as mock_analyze:
            mock_analyze.return_value = {"insights": ["insight1"], "metrics": {}}
            
            result = await analyzer.analyze_conversations(conversations)
            
            assert result["insights"] == ["insight1"]
            mock_analyze.assert_called_once_with(conversations)
    
    @pytest.mark.asyncio
    async def test_analyze_conversations_error(self):
        """Test analysis error handling."""
        analyzer = ConversationAnalyzer({})
        conversations = [{"id": "1", "text": "test"}]
        
        with patch.object(analyzer, '_perform_analysis') as mock_analyze:
            mock_analyze.side_effect = Exception("Analysis failed")
            
            with pytest.raises(AnalysisError, match="Failed to analyze conversations"):
                await analyzer.analyze_conversations(conversations)
```

## Summary

**Every feature must include:**
1. ✅ **Comprehensive unit tests** (100% coverage)
2. ✅ **Proper logging** (all important events)
3. ✅ **Error handling** (graceful failure)
4. ✅ **Type hints** (all functions)
5. ✅ **Documentation** (docstrings and comments)
6. ✅ **Input validation** (check all inputs)
7. ✅ **Performance considerations** (log timing, optimize)

This ensures the system remains robust, debuggable, and maintainable as it grows in complexity.






