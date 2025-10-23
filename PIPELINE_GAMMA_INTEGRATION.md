# Pipeline Gamma Integration Guide

## Overview

This document explains how Gamma presentation generation is integrated across all analysis pipelines in the Intercom Analysis Tool. It ensures consistency, proper URL handling, and markdown summary generation.

**Key Principle:** Gamma URLs are **always** retrieved from the Gamma API GET endpoint (`/generations/{generation_id}`), never manually constructed from generation IDs.

## Table of Contents

1. [How Gamma URL Generation Works](#how-gamma-url-generation-works)
2. [Pipeline Integration Status](#pipeline-integration-status)
3. [Standard Output Format](#standard-output-format)
4. [Web Interface Integration](#web-interface-integration)
5. [Markdown Summary Generation](#markdown-summary-generation)
6. [Testing Guidelines](#testing-guidelines)
7. [Common Issues](#common-issues)

---

## How Gamma URL Generation Works

### The Correct Flow

```python
# 1. Generate presentation
generation_id = await gamma_client.generate_presentation(
    input_text=content,
    format="presentation",
    num_cards=10
)

# 2. Poll for completion
result = await gamma_client.poll_generation(generation_id)

# 3. Extract URL from API response
gamma_url = result.get('gammaUrl')  # ✅ From API
# NOT: gamma_url = f"https://gamma.app/{generation_id}"  # ❌ Manual construction
```

### URL Validation

The `GammaClient` automatically validates URLs:

- Checks URL starts with `https://gamma.app/`
- Warns if URL appears to be manually constructed
- Logs full URL for debugging

```python
# Example validated URL
gamma_url = "https://gamma.app/docs/customer-analysis-abc123xyz"
# NOT: "https://gamma.app/gen_123"
```

---

## Pipeline Integration Status

### ✅ Fully Integrated Pipelines

| Pipeline | Command | Gamma Method | Markdown |
|----------|---------|--------------|----------|
| **VOC Analysis** | `voc-analysis --generate-gamma` | `generate_from_voc_analysis()` | ✅ Auto-generated |
| **Canny Analysis** | `canny-analysis --generate-gamma` | `generate_from_canny_analysis()` | ✅ Auto-generated |
| **Billing Analysis** | `analyze-billing --generate-gamma` | `generate_from_analysis()` | ✅ Auto-generated |
| **Product Analysis** | `analyze-product --generate-gamma` | `generate_from_analysis()` | ✅ Auto-generated |
| **Sites Analysis** | `analyze-sites --generate-gamma` | `generate_from_analysis()` | ✅ Auto-generated |
| **API Analysis** | `analyze-api --generate-gamma` | `generate_from_analysis()` | ✅ Auto-generated |
| **Comprehensive** | `comprehensive --gamma-style executive` | `generate_from_analysis()` | ✅ Auto-generated |

### Generate Gamma Commands

| Command | Description |
|---------|-------------|
| `generate-gamma --input results.json` | Generate from existing analysis |
| `generate-all-gamma --input results.json` | Generate all styles (executive/detailed/training) |

---

## Standard Output Format

All pipelines follow this consistent output format for web UI parsing:

### Console Output

```
[bold green]Analysis Completed![/bold green]
Total conversations analyzed: 1,234
Results saved to: outputs/analysis_20241023_123456.json

✅ Gamma presentation generated
Gamma URL: https://gamma.app/docs/analysis-xyz123
Credits used: 2
Generation time: 15.3s
Markdown summary: outputs/analysis_executive_20241023_123456.md
Gamma metadata saved to: outputs/analysis_gamma_metadata_20241023_123456.json
```

### Critical Format Rules

1. **Gamma URL line:** Must be exactly `Gamma URL: {url}`
2. **Credits line:** Must be exactly `Credits used: {number}`
3. **Time line:** Must be exactly `Generation time: {number}s`
4. **Markdown line:** Must be exactly `Markdown summary: {path}`

This format is parsed by:
- Web UI regex patterns (short-term)
- Metadata extraction in `WebCommandExecutor` (structured)
- SSE event handlers in `railway_web.py`

---

## Web Interface Integration

### How the Web UI Displays Gamma URLs

1. **Output Detection:** Web UI parses stdout/status events for pattern `Gamma URL: {url}`
2. **Metadata Extraction:** Extracts credits, time, and markdown path from output
3. **SSE Event:** Sends special `gamma_url` event with full metadata
4. **Display:** Shows Gamma panel with:
   - Clickable presentation link
   - Credits used and generation time
   - Markdown download link (if available)
   - Copy buttons for URL and path

### Frontend Code (Simplified)

```javascript
// Detect Gamma URL in output
function detectGammaUrl(text) {
    const urlPattern = /Gamma URL:\s*(https:\/\/gamma\.app\/[^\s]+)/;
    const match = text.match(urlPattern);
    return match ? match[1] : null;
}

// Display Gamma panel
function displayGammaUrl(url) {
    document.getElementById('gammaUrlLink').href = url;
    document.getElementById('gammaPanel').style.display = 'block';
}

// Extract metadata
const creditsMatch = text.match(/Credits used:\s*(\d+)/);
const timeMatch = text.match(/Generation time:\s*([\d.]+)s/);
const markdownMatch = text.match(/Markdown summary:\s*([^\s]+)/);
```

### SSE Event Structure

```json
{
    "event": "gamma_url",
    "data": {
        "type": "gamma_url",
        "url": "https://gamma.app/docs/analysis-xyz123",
        "credits_used": 2,
        "generation_time": 15.3,
        "markdown_path": "outputs/analysis_executive_20241023_123456.md",
        "timestamp": "2024-10-23T12:34:56Z"
    }
}
```

---

## Markdown Summary Generation

### Automatic Generation

All `GammaGenerator` methods automatically generate markdown summaries:

```python
# This happens automatically
result = await gamma_generator.generate_from_analysis(
    analysis_results=analysis_results,
    style="executive",
    output_dir=output_dir
)

# Result includes:
{
    'gamma_url': 'https://gamma.app/docs/...',
    'markdown_summary_path': 'outputs/analysis_executive_20241023_123456.md',
    'markdown_preview': 'First 500 characters...',
    'markdown_size_bytes': 12345
}
```

### Naming Convention

```
{analysis_type}_{style}_{timestamp}.md
```

Examples:
- `analysis_executive_20241023_123456.md`
- `voc_analysis_detailed_20241023_123456.md`
- `canny_analysis_executive_20241023_123456.md`
- `billing_analysis_executive_20241023_123456.md`

### Content Structure

Markdown summaries include:

1. **Executive Summary** - Key findings and recommendations
2. **Data Overview** - Conversation counts, date ranges, categories
3. **Customer Quotes** - With Intercom links
4. **Category Breakdowns** - Volume, sentiment, escalation rates
5. **Recommendations** - Actionable next steps
6. **Metadata** - Generation date, data quality, next review date

---

## Testing Guidelines

### Running Integration Tests

```bash
# Run all pipeline integration tests
pytest tests/integration/test_all_pipelines_gamma.py -v

# Run specific pipeline test
pytest tests/integration/test_all_pipelines_gamma.py::TestVoCPipelineGamma -v

# Run with output
pytest tests/integration/test_all_pipelines_gamma.py -v -s
```

### What Tests Validate

1. **URL Correctness:**
   - URL starts with `https://gamma.app/`
   - URL is from API, not manually constructed
   - URL has proper structure (not just generation_id)

2. **Metadata Completeness:**
   - `gamma_url` exists
   - `generation_id` exists
   - `credits_used` ≥ 0
   - `generation_time_seconds` > 0
   - `markdown_summary_path` exists (or is None with warning)

3. **Pipeline-Specific Tests:**
   - VOC: Validates VoC-specific result structure
   - Canny: Validates Canny-specific result structure
   - Category Analyzers: Validates standard analysis structure
   - Comprehensive: Validates synthesis results

### Manual Testing

```bash
# Test billing analysis with Gamma
python -m src.main analyze-billing --days 30 --generate-gamma

# Expected output:
# ✅ Gamma presentation generated
# Gamma URL: https://gamma.app/docs/...
# Credits used: 2
# Generation time: 15.3s
# Markdown summary: outputs/...
```

---

## Common Issues

### Issue 1: Gamma URL Not Appearing in Web UI

**Symptoms:**
- Analysis completes successfully
- No Gamma panel shown in web interface

**Causes & Solutions:**

1. **Incorrect output format**
   ```python
   # ❌ Wrong
   print(f"Presentation URL: {url}")
   
   # ✅ Correct
   console.print(f"Gamma URL: {result['gamma_url']}")
   ```

2. **Missing web UI regex match**
   - Check browser console for detection logs
   - Verify pattern: `Gamma URL:\s*(https://gamma\.app/[^\s]+)`

3. **SSE event not emitted**
   - Check `railway_web.py` line ~1227 for event emission
   - Verify output type is "stdout" or "status"

### Issue 2: Markdown Not Generated

**Symptoms:**
- Gamma URL works
- Markdown summary path is `null` or missing

**Causes & Solutions:**

1. **GoogleDocsExporter failure**
   ```python
   # Check logs for warnings:
   # "markdown_summary_generation_failed"
   ```

2. **Missing output directory**
   ```python
   # Ensure output_dir is passed:
   result = await gamma_generator.generate_from_analysis(
       analysis_results=analysis_results,
       style="executive",
       output_dir=Path("outputs")  # ← Must exist
   )
   ```

3. **File permissions**
   - Check write permissions on `outputs/` directory
   - Verify disk space available

### Issue 3: Credits Not Displayed

**Symptoms:**
- Gamma URL works
- Credits/time metadata not shown

**Causes & Solutions:**

1. **Missing print statements**
   ```python
   # ✅ Required prints
   console.print(f"Credits used: {result['credits_used']}")
   console.print(f"Generation time: {result['generation_time_seconds']:.1f}s")
   ```

2. **Metadata extraction failure**
   - Check `_extract_gamma_metadata()` in `web_command_executor.py`
   - Verify regex patterns match output format

3. **Frontend parsing issues**
   - Check `extractGammaMetadata()` in `railway_web.py`
   - Verify JavaScript regex patterns

### Issue 4: URL Appears Constructed

**Symptoms:**
- URL looks like `https://gamma.app/gen_123`
- Warning in logs: "gamma_url_appears_constructed"

**Causes & Solutions:**

This should **never** happen with correct implementation. If it does:

1. **Check GammaClient usage**
   ```python
   # ❌ Wrong - manual construction
   gamma_url = f"https://gamma.app/{generation_id}"
   
   # ✅ Correct - from API
   result = await client.poll_generation(generation_id)
   gamma_url = result.get('gammaUrl')
   ```

2. **Verify API response**
   - Check Gamma API logs
   - Ensure `gammaUrl` field is in response
   - Contact Gamma support if API returns invalid URLs

---

## File Reference

### Key Files for Gamma Integration

| File | Purpose | Key Methods |
|------|---------|-------------|
| `src/services/gamma_client.py` | API client | `generate_presentation()`, `poll_generation()` |
| `src/services/gamma_generator.py` | High-level generator | `generate_from_analysis()`, `generate_from_voc_analysis()` |
| `src/services/google_docs_exporter.py` | Markdown export | `export_to_markdown()` |
| `src/services/orchestrator.py` | Comprehensive analysis | `_generate_gamma_presentation()` |
| `src/main.py` | CLI commands | `run_billing_analysis()`, `run_product_analysis()`, etc. |
| `railway_web.py` | Web interface | Gamma panel HTML, SSE handlers |
| `src/services/web_command_executor.py` | Command execution | `_extract_gamma_metadata()` |
| `src/services/execution_state_manager.py` | State management | `update_gamma_metadata()` |

### Configuration Files

| File | Purpose |
|------|---------|
| `src/config/gamma_prompts.py` | Presentation style configs |
| `config/analysis_config.yaml` | Analysis settings |
| `.env` | `GAMMA_API_KEY` required |

---

## Best Practices

### For Pipeline Developers

1. **Always use GammaGenerator methods**
   - Don't call `GammaClient` directly
   - Use `generate_from_analysis()` for standard pipelines
   - Use specialized methods (`generate_from_voc_analysis()`) when available

2. **Follow standard output format**
   - Use exact string patterns for web UI parsing
   - Include all metadata fields (credits, time, markdown)
   - Save metadata JSON for structured access

3. **Handle errors gracefully**
   - Markdown generation failures should not break Gamma generation
   - Log warnings, don't raise exceptions
   - Return partial results with error flags

4. **Test thoroughly**
   - Write integration tests for new pipelines
   - Test both CLI and web interfaces
   - Verify URL validation and metadata extraction

### For Frontend Developers

1. **Parse output reliably**
   - Use exact regex patterns
   - Handle missing metadata gracefully
   - Show partial information if available

2. **Display user-friendly messages**
   - Explain what each metric means
   - Provide helpful error messages
   - Show loading states during generation

3. **Support downloads**
   - Link to markdown summaries
   - Enable URL/path copying
   - Handle file access errors

---

## Changelog

### 2024-10-23: Initial Standardization
- Unified Gamma integration across all pipelines
- Added markdown auto-generation
- Implemented URL validation
- Enhanced web UI display
- Created comprehensive integration tests

---

## Support

For issues or questions:

1. Check this guide's [Common Issues](#common-issues) section
2. Review integration tests in `tests/integration/test_all_pipelines_gamma.py`
3. Check logs for detailed error messages
4. Consult team for complex issues

---

**Last Updated:** October 23, 2024  
**Maintainer:** Intercom Analysis Tool Team

