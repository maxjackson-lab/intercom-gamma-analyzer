# Voice of Customer Developer Guide

## Architecture Overview

The VoC system is built with a modular, service-oriented architecture that separates concerns and enables easy testing and extension.

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   CLI Layer     │    │   Service Layer  │    │   Data Layer    │
│                 │    │                  │    │                 │
│ voice-of-customer│───▶│ AIModelFactory   │───▶│ Intercom API    │
│                 │    │ AgentSeparator   │    │ DuckDB Storage  │
│                 │    │ HistoricalMgr    │    │ JSON Outputs    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                       ┌──────────────────┐
                       │  Analysis Layer  │
                       │                  │
                       │ VoiceOfCustomer  │
                       │ Analyzer         │
                       └──────────────────┘
```

## Core Components

### 1. AIModelFactory (`src/services/ai_model_factory.py`)
**Purpose**: Centralized factory for AI model clients with fallback support.

**Key Methods**:
- `get_client(model)`: Returns OpenAI or Claude client
- `analyze_sentiment(text, language, model, fallback)`: Unified sentiment analysis
- `test_connections()`: Health check for all AI models

**Usage**:
```python
factory = AIModelFactory()
result = await factory.analyze_sentiment(
    text="Customer feedback text",
    language="es",  # Optional language hint
    model=AIModel.OPENAI_GPT4,
    fallback=True
)
```

### 2. AgentFeedbackSeparator (`src/services/agent_feedback_separator.py`)
**Purpose**: Separates conversations by agent type using email domain patterns.

**Agent Types**:
- `finn_ai`: Intercom AI assistant
- `boldr_support`: External support (boldr.com/io domains)
- `horatio_support`: External support (horatio.com/ai domains)
- `gamma_cx_staff`: Internal Gamma team
- `mixed_agent`: Multiple agent types
- `customer_only`: No agent responses

**Usage**:
```python
separator = AgentFeedbackSeparator()
separated = separator.separate_by_agent_type(conversations)
```

### 3. HistoricalDataManager (`src/services/historical_data_manager.py`)
**Purpose**: Manages historical snapshots for trend analysis.

**Features**:
- Weekly/monthly/quarterly snapshots
- Automatic cleanup of old data
- Trend analysis and insights generation
- JSON-based storage

**Usage**:
```python
manager = HistoricalDataManager()
await manager.store_weekly_snapshot(results, datetime.now())
trends = manager.get_historical_trends(weeks_back=26)
```

### 4. VoiceOfCustomerAnalyzer (`src/analyzers/voice_of_customer_analyzer.py`)
**Purpose**: Main orchestrator for VoC analysis.

**Key Methods**:
- `analyze_weekly_sentiment()`: Main analysis method
- `_analyze_category_sentiment()`: Category-specific sentiment
- `_extract_sentiment_from_attributes()`: Intercom attribute extraction
- `_generate_insights()`: Automated insight generation

## AI Model Integration

### OpenAI Client (`src/services/openai_client.py`)
- **Model**: GPT-4 (configurable)
- **Features**: Multilingual support, confidence scoring, emotional indicators
- **Error Handling**: Graceful degradation with detailed logging

### Claude Client (`src/services/claude_client.py`)
- **Model**: Claude-3-Opus (configurable)
- **Features**: Same interface as OpenAI for seamless switching
- **Error Handling**: Consistent error patterns with OpenAI

### Fallback Strategy
1. Try primary AI model
2. If fails and fallback enabled, try secondary model
3. If both fail, raise exception with detailed error info
4. Log all attempts for debugging

## Testing Strategy

### Unit Tests
```bash
# Run all VoC tests
pytest tests/test_voice_of_customer_analyzer.py -v
pytest tests/test_ai_model_factory.py -v
pytest tests/test_claude_client.py -v
```

### Integration Tests
```bash
# Test with real Intercom data (requires API keys)
python -m pytest tests/integration/test_voc_integration.py -v
```

### Mock Testing
All external dependencies (Intercom API, AI models) are mocked in unit tests for reliability and speed.

## Logging Conventions

### Log Levels
- **DEBUG**: Detailed AI analysis, conversation processing
- **INFO**: Major operations, analysis results
- **WARNING**: Fallback usage, data quality issues
- **ERROR**: API failures, critical errors

### Log Format
```
[timestamp] [level] [module] message
2024-01-15 10:30:45 INFO voice_of_customer_analyzer Starting VoC analysis with 150 conversations
```

## Extending the System

### Adding New AI Models
1. Create new client class inheriting from base interface
2. Add model enum to `AIModelFactory`
3. Update factory's `get_client()` method
4. Add tests for new model

### Adding New Agent Types
1. Update `AgentFeedbackSeparator` patterns
2. Add new agent type to enum
3. Update analysis logic in `VoiceOfCustomerAnalyzer`
4. Add tests for new agent type

### Custom Sentiment Sources
1. Extend `_extract_sentiment_from_attributes()` method
2. Add new custom attribute patterns
3. Update confidence calculation logic
4. Add tests for new sentiment sources

## Performance Optimization

### Caching Strategy
- AI model clients are cached in factory
- Historical data is cached in memory
- Conversation text is processed in batches

### Parallel Processing
- Multiple conversations analyzed concurrently
- AI API calls are batched when possible
- Historical data processing is parallelized

### Memory Management
- Large conversation datasets are processed in chunks
- Historical snapshots are compressed
- Temporary data is cleaned up after analysis

## Error Handling

### Graceful Degradation
- Missing API keys: Skip AI analysis, use Intercom attributes only
- API failures: Log error, continue with available data
- Invalid data: Skip problematic conversations, log warnings

### Recovery Strategies
- Automatic retry with exponential backoff
- Fallback to alternative AI models
- Partial results when full analysis fails

## Configuration Management

### Settings (`src/config/settings.py`)
```python
# VoC-specific settings
voc_default_ai_model: str = "openai"
voc_enable_ai_fallback: bool = True
voc_historical_weeks: int = 26
voc_top_categories_count: int = 10
```

### Environment Variables
All settings can be overridden via environment variables with `VOC_` prefix.

## Deployment Considerations

### Dependencies
- Python 3.8+
- AsyncIO support
- Network access to Intercom and AI APIs
- Sufficient disk space for historical data

### Resource Requirements
- **CPU**: Moderate (AI API calls are the bottleneck)
- **Memory**: 1-2GB for large conversation datasets
- **Storage**: ~100MB per month of historical data
- **Network**: Stable connection to external APIs

### Monitoring
- Track API usage and costs
- Monitor analysis execution times
- Alert on high error rates
- Log sentiment analysis accuracy
