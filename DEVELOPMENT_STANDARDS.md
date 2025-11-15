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

## LLM Operational Controls: One Mechanism at a Time

**When adjusting LLM operational parameters, change ONE mechanism at a time and validate before proceeding.**

### The Problem: Interacting Mechanisms

LLM calls involve multiple interacting controls:
- **Timeouts** (`self.llm_timeout` in agents)
- **Concurrency** (semaphore size, max concurrent requests)
- **Chunking** (batch size, how many conversations per chunk)
- **Retries** (exponential backoff, max attempts)
- **Fallbacks** (keyword detection, graceful degradation)

**Changing multiple at once makes failures impossible to attribute.**

**Example (Nov 2025 - What NOT to Do):**
```python
# ❌ BAD: Changed 3 things at once
self.llm_timeout = 60  # Was 30
self.llm_semaphore = asyncio.Semaphore(20)  # Was 10
chunk_size = 100  # Was 50

# Result: Started getting 429 errors and timeouts
# Which change caused it? Impossible to tell!
```

### The Solution: Sequential Validation

**Change one mechanism → validate → observe → repeat.**

**Order of operations when tuning LLM performance:**

1. **FIRST: Adjust timeout**
   ```python
   # Try increasing timeout if seeing timeout errors
   self.llm_timeout = 60  # Was 30
   ```
   - Run sample-mode: `python src/main.py sample-mode --count 50 --save-to-file`
   - Check `.log` for timeout errors
   - If resolved → commit and proceed
   - If not → revert and try next mechanism

2. **SECOND: Adjust concurrency (semaphore)**
   ```python
   # Try reducing concurrency if seeing rate limits
   self.llm_semaphore = asyncio.Semaphore(5)  # Was 10
   ```
   - Run sample-mode again
   - Check for 429 (rate limit) errors
   - Commit if resolved, otherwise revert

3. **THIRD: Adjust chunk size**
   ```python
   # Try smaller chunks if processing too slow
   chunk_size = 25  # Was 50
   ```
   - Run sample-mode
   - Measure execution time
   - Commit if improved, otherwise revert

4. **LAST: Adjust retry/fallback logic**
   - Only after above mechanisms are tuned
   - Changes here affect error recovery, not throughput

### Configuration Comments

**Add reminders near configuration values:**

```python
class TopicDetectionAgent(BaseAgent):
    def __init__(self):
        # ⚠️ ONE MECHANISM AT A TIME: Validate via sample-mode before adjusting other knobs
        self.llm_timeout = 30  # Timeout per LLM call (seconds)
        self.llm_semaphore = asyncio.Semaphore(10)  # Max concurrent LLM requests
        
        # See DEVELOPMENT_STANDARDS.md: "LLM Operational Controls"
```

**In orchestration code:**

```python
# src/services/sample_mode.py or VoC pipeline
chunk_size = 50  # Conversations per batch
# ⚠️ Adjust AFTER tuning agent-level timeout/semaphore
# See DEVELOPMENT_STANDARDS.md: "LLM Operational Controls"
```

### Validation Requirements

**After each change:**
- [ ] Run `python src/main.py sample-mode --count 50 --save-to-file`
- [ ] Check `.log` for LLM errors (400, 429, timeout)
- [ ] Measure execution time (should be ~30-60s for 50 conversations)
- [ ] Verify no crashes or hangs
- [ ] Commit if successful, revert if not

**Do NOT:**
- Change multiple mechanisms simultaneously
- Skip validation between changes
- Assume "it should work" without testing
- Commit without running sample-mode

**This is process documentation, not runtime behavior.**

## Error-Log-First Debugging Workflow

**When a run fails, ALWAYS retrieve and analyze logs BEFORE adjusting code or configuration.**

### The Problem: Guesswork Under Failure

**Common anti-pattern:**
1. Run fails with vague error
2. Guess what went wrong
3. Adjust timeout/config/code
4. Run again → still fails or new error
5. Repeat guessing...

**This wastes time and introduces random changes that mask the real issue.**

### The Solution: Log-Driven Diagnosis

**Explicit order of operations when a run fails:**

#### Step 1: Retrieve Complete Log File

**Always check the full `.log` file first:**

```bash
# For Railway/web runs
# Download the .log file from the outputs/ directory

# For local runs
ls -lt outputs/*.log | head -1  # Find latest log
cat outputs/your-run.log        # Read full log
```

**Why the log file, not console output?**
- Console output may be truncated on SSE disconnect
- Log files persist complete output via `output_manager.py`
- Contains full error tracebacks and context
- Shows exact provider error codes (400, 429, 500)

#### Step 2: Identify Primary Error Codes and Messages

**Look for provider-specific errors:**

**OpenAI errors:**
```
Error code: 400 - Invalid request
Error code: 401 - Authentication failed
Error code: 429 - Rate limit exceeded
Error code: 500 - Server error
```

**Anthropic (Claude) errors:**
```
status_code: 400 - Bad request (check schema!)
status_code: 429 - Rate limit exceeded
status_code: 529 - Overloaded
```

**Timeout errors:**
```
asyncio.TimeoutError
Request timeout after 30s
```

**Parsing errors:**
```
json.JSONDecodeError
Pydantic ValidationError
KeyError: 'topic'
```

#### Step 3: Diagnose Root Cause from Error

**Map error codes to root causes:**

| Error | Root Cause | Fix |
|-------|-----------|-----|
| 400 Bad Request | Invalid schema, malformed prompt | Check JSON schema, remove incompatible fields (e.g., allOf) |
| 401 Unauthorized | API key missing/invalid | Verify env vars, check Railway secrets |
| 429 Rate Limit | Too many concurrent requests | Reduce semaphore size, increase delay |
| 500 Server Error | Provider issue (transient) | Add retry logic, check provider status page |
| asyncio.TimeoutError | LLM response too slow | Increase timeout, reduce prompt size |
| JSONDecodeError | LLM returned non-JSON | Fix prompt to enforce JSON, add validation |
| ValidationError | Response missing required fields | Check Pydantic model vs actual response |

#### Step 4: Only Then Adjust Configuration or Code

**After diagnosing from logs:**

1. **Make targeted fix** (not random guessing)
   ```python
   # Example: 429 errors → reduce concurrency
   self.llm_semaphore = asyncio.Semaphore(5)  # Was 10
   ```

2. **Run sample-mode to validate fix**
   ```bash
   python src/main.py sample-mode --count 50 --save-to-file
   ```

3. **Check log again** - error resolved?
   - ✅ Yes → commit fix
   - ❌ No → check log for new error, repeat

### Integration with Output Manager

**The system already persists logs automatically via `output_manager.py`:**

```python
# In service classes (e.g., sample_mode.py, voc_pipeline.py):
from src.utils.output_manager import OutputManager

output_manager = OutputManager(output_dir="outputs", base_filename="analysis")

# Enable console recording
output_manager.enable_recording()

# ... run analysis (all console.print() captured) ...

# Save complete log
log_content = output_manager.get_recorded_output()
log_file = output_manager.save_log(log_content)

# User can download log_file even if SSE disconnects
```

**This pattern ensures logs survive SSE disconnections.**

### Debugging Checklist

**When a run fails:**
- [ ] 1. Retrieved full `.log` file (not just console output)
- [ ] 2. Identified primary error codes (400, 429, timeout, parsing)
- [ ] 3. Mapped error code to root cause using table above
- [ ] 4. Made targeted fix (not random adjustment)
- [ ] 5. Validated fix via sample-mode
- [ ] 6. Checked new log to confirm resolution

**Do NOT:**
- Skip log retrieval and guess the problem
- Adjust multiple configs hoping one fixes it
- Only look at console output (may be truncated)
- Commit without validating fix via sample-mode

**See also:**
- `SAMPLE_MODE_GUIDE.md` - How to interpret sample-mode output
- `src/utils/output_manager.py` - Log persistence implementation
- `.cursorrules` - "Output File Resilience" section

## Summary

**Every feature must include:**
1. ✅ **Comprehensive unit tests** (100% coverage)
2. ✅ **Proper logging** (all important events)
3. ✅ **Error handling** (graceful failure)
4. ✅ **Type hints** (all functions)
5. ✅ **Documentation** (docstrings and comments)
6. ✅ **Input validation** (check all inputs)
7. ✅ **Performance considerations** (log timing, optimize)
8. ✅ **LLM tuning** (one mechanism at a time, validate each change)

This ensures the system remains robust, debuggable, and maintainable as it grows in complexity.






