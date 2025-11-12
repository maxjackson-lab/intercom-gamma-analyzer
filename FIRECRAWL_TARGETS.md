# Firecrawl Targets to Reduce Hallucinations

## Overview
These documentation sites should be scraped to provide accurate context for AI agents and reduce hallucinations when working with external APIs and services.

## Priority 1: Critical API Documentation

### 1. Intercom API Reference (COMPLETE ✅)
**URL**: `https://developers.intercom.com/docs/references/rest-api/api.intercom.io`
**Status**: Already scraped → `INTERCOM_DEVELOPER_DOCS.md`
**Why**: Provides exact API endpoints, rate limits, pagination patterns, field schemas

### 2. Intercom Python SDK Documentation
**URL**: `https://github.com/intercom/python-intercom` (README + docs/)
**Why**: SDK-specific patterns, error handling, model structures
**What to scrape**:
- SDK README
- API reference docs
- Example code snippets
- Error handling patterns

### 3. Gamma API Documentation (COMPLETE ✅)
**URL**: `https://developers.gamma.app`
**Status**: Already scraped → `GAMMA_API_COMPLETE_V1_AND_V02.html`
**Why**: Exact API parameters, limits, error codes

## Priority 2: Architecture & Best Practices

### 4. OpenAI API Reference
**URL**: `https://platform.openai.com/docs/api-reference`
**Why**: Exact function calling patterns, error codes, rate limits
**What to scrape**:
- Chat completions API
- Function calling guide
- Error codes and handling
- Rate limits and best practices

### 5. Anthropic Claude API Reference
**URL**: `https://docs.anthropic.com/claude/reference`
**Why**: Claude-specific patterns, message formats, tool use
**What to scrape**:
- Messages API reference
- Tool use patterns
- Error handling
- Rate limits

### 6. Railway Deployment Documentation
**URL**: `https://docs.railway.app`
**Why**: Deployment patterns, environment variables, timeout limits
**What to scrape**:
- Environment variables
- Timeout configurations
- Logging best practices
- Deployment patterns

## Priority 3: Python Libraries

### 7. Pydantic Documentation
**URL**: `https://docs.pydantic.dev`
**Why**: Exact model validation patterns, field types, error messages
**What to scrape**:
- Model validation
- Field types and constraints
- Error handling
- Best practices

### 8. httpx Documentation
**URL**: `https://www.python-httpx.org`
**Why**: Async HTTP patterns, timeout handling, error types
**What to scrape**:
- Async client patterns
- Timeout configuration
- Error handling
- Retry patterns

### 9. asyncio Documentation
**URL**: `https://docs.python.org/3/library/asyncio.html`
**Why**: Exact async patterns, semaphores, timeouts
**What to scrape**:
- asyncio.wait_for patterns
- Semaphore usage
- Task management
- Error handling

## Priority 4: Domain-Specific

### 10. DuckDB Documentation (if using)
**URL**: `https://duckdb.org/docs/`
**Why**: SQL syntax, query patterns, data types
**What to scrape**:
- SQL reference
- Python API
- Data types
- Best practices

## Implementation Strategy

### Recommended Firecrawl Commands

```bash
# 1. Intercom Python SDK
firecrawl crawl https://github.com/intercom/python-intercom --limit 50 --maxDepth 3

# 2. OpenAI API Reference
firecrawl crawl https://platform.openai.com/docs/api-reference --limit 100 --maxDepth 2

# 3. Anthropic Claude API
firecrawl crawl https://docs.anthropic.com/claude/reference --limit 50 --maxDepth 2

# 4. Railway Docs
firecrawl crawl https://docs.railway.app --limit 50 --maxDepth 2

# 5. Pydantic Docs
firecrawl crawl https://docs.pydantic.dev --limit 100 --maxDepth 2

# 6. httpx Docs
firecrawl crawl https://www.python-httpx.org --limit 50 --maxDepth 2
```

### Storage Pattern
Save each scraped doc as:
- `{SERVICE}_API_DOCS.md` (e.g., `OPENAI_API_DOCS.md`)
- Add to `.gitignore` (they're large)
- Reference in `.cursorrules` for context

## How This Reduces Hallucinations

1. **Exact API Patterns**: Agents see real API signatures, not guessed ones
2. **Error Codes**: Know exact error codes and meanings
3. **Rate Limits**: Understand actual limits, not assumptions
4. **Best Practices**: Follow official recommendations
5. **Field Names**: Use correct field names from docs
6. **Data Types**: Know exact data types and formats

## Integration with Cursor

Add to `.cursorrules`:
```markdown
## Reference Documentation
When working with external APIs, refer to:
- INTERCOM_DEVELOPER_DOCS.md for Intercom API patterns
- GAMMA_API_COMPLETE_V1_AND_V02.html for Gamma API
- {SERVICE}_API_DOCS.md for other services

Always verify:
- API endpoint URLs
- Request/response formats
- Error codes and handling
- Rate limits and best practices
```

## Maintenance

- Update docs quarterly or when APIs change
- Scrape new API versions when released
- Remove deprecated API docs
- Keep docs in sync with actual API behavior






