# Voice of Customer Analysis Guide

## Overview

The Voice of Customer (VoC) analysis tool provides comprehensive sentiment analysis of customer conversations from Intercom, with support for 46+ languages and intelligent agent separation.

## Quick Start

### Basic Usage

```bash
# Analyze last week's conversations with OpenAI
python src/main.py voice-of-customer --start-date 2024-01-01 --end-date 2024-01-07

# Use Claude instead
python src/main.py voice-of-customer --start-date 2024-01-01 --end-date 2024-01-07 --ai-model claude

# Include historical trends
python src/main.py voice-of-customer --start-date 2024-01-01 --end-date 2024-01-07 --include-trends
```

### VOC-V2 Narrative Mode

Use `voc-v2` when you need the weekly operations story Hilary shares with exec staff. It layers BPO workload, Fin gaps, and prioritized actions into one narrative.

```bash
# Run the new narrative report for last week
python src/main.py voc-v2 --time-period week --generate-gamma

# Fast digest for exec sync
python src.main.py voc-v2 --time-period week --digest-mode
```

Highlights:
- Executive summary tying top topics + Fin knowledge gaps + Horatio/Boldr load
- Embedded BPO snapshot, so no separate vendor command is required
- Inline quotes with Intercom links and a prioritized action list
- Outputs stored under `outputs/voc_v2/` to keep history separate from the classic reports

> Need per-agent coaching detail? Continue using `python src.main.py agent-performance --agent horatio --individual-breakdown` (or `--agent boldr`). VOC-V2 references the same vendor data but keeps individual evaluation inside the existing BPO modes.

> Want the same output with fewer flags? Use `python src/main.py agent-eval --vendor horatio --time-period week` to jump straight into the individual breakdown workflow (defaults to taxonomy + Gamma-ready narrative).

### Advanced Options

```bash
# Disable AI fallback
python src/main.py voice-of-customer --start-date 2024-01-01 --end-date 2024-01-07 --no-fallback

# Generate Gamma presentation
python src/main.py voice-of-customer --start-date 2024-01-01 --end-date 2024-01-07 --generate-gamma

# Custom output directory
python src/main.py voice-of-customer --start-date 2024-01-01 --end-date 2024-01-07 --output-dir /path/to/output
```

## Features

### 🌍 Multilingual Support
- **46+ Languages**: English, Spanish, French, German, Japanese, Chinese, Korean, Arabic, Hindi, and many more
- **Dynamic Detection**: Automatically detects language and provides cultural context
- **High Accuracy**: 0.80-0.90 confidence scores across all languages

### 🤖 Agent Separation
- **Finn AI**: Intercom's AI assistant conversations
- **Boldr Support**: External support team conversations
- **Horatio Support**: External support team conversations  
- **Gamma CX Staff**: Internal customer experience team
- **Mixed Agents**: Conversations with multiple agent types
- **Customer Only**: Conversations without agent responses

### 📊 Sentiment Analysis
- **Intercom Attributes**: Uses existing User Sentiment and CX Score data when available
- **AI Fallback**: Dynamic ChatGPT/Claude analysis for missing sentiment data
- **Confidence Scoring**: Provides confidence levels for all sentiment analysis
- **Emotional Indicators**: Detects specific emotions (grateful, frustrated, etc.)

### 📈 Historical Trends
- **Weekly Snapshots**: Automatic storage of weekly analysis results
- **Trend Analysis**: Volume and sentiment trends over time
- **Insights Generation**: Automated trend insights and recommendations
- **Data Retention**: Configurable historical data retention (default: 26 weeks)

## Output Format

### JSON Results
```json
{
  "analysis_results": {
    "results": {
      "Billing": {
        "volume": 25,
        "sentiment_breakdown": {
          "sentiment": "positive",
          "confidence": 0.85,
          "source": "intercom_attributes"
        },
        "examples": {
          "positive": ["Thank you so much! This really helped."]
        },
        "agent_breakdown": {
          "finn_ai": 15,
          "boldr_support": 10
        },
        "language_breakdown": {
          "en": 20,
          "es": 5
        }
      }
    },
    "metadata": {
      "ai_model": "openai",
      "total_conversations": 25,
      "execution_time_seconds": 15.5
    }
  },
  "insights": [
    "Top volume category: Billing (25 conversations)",
    "Strong positive sentiment in Billing (confidence: 0.85)"
  ]
}
```

## Configuration

### Environment Variables
```bash
# Required
INTERCOM_ACCESS_TOKEN=your_intercom_token
OPENAI_API_KEY=your_openai_key

# Optional
ANTHROPIC_API_KEY=your_claude_key
INTERCOM_WORKSPACE_ID=your_workspace_id
VOC_DEFAULT_AI_MODEL=openai  # or claude
VOC_ENABLE_AI_FALLBACK=true
VOC_HISTORICAL_WEEKS=26
```

## Troubleshooting

### Common Issues

**No conversations found**
- Check date range format (YYYY-MM-DD)
- Verify Intercom access token
- Ensure conversations exist in the date range

**AI analysis fails**
- Check API keys (OpenAI/Claude)
- Enable fallback with `--enable-fallback`
- Check internet connectivity

**Low sentiment coverage**
- Ensure Intercom custom attributes are configured
- Check conversation data quality
- Verify language detection is working

### Performance Tips

- Use `--include-trends` sparingly (adds processing time)
- Limit date ranges for faster processing
- Use `--no-fallback` for faster execution (if you trust your primary AI model)

## Examples

### Weekly Analysis
```bash
# Every Monday, analyze previous week
python src/main.py voice-of-customer \
  --start-date $(date -d "last monday" +%Y-%m-%d) \
  --end-date $(date -d "last sunday" +%Y-%m-%d) \
  --include-trends
```

### Monthly Report
```bash
# First of month, analyze previous month
python src/main.py voice-of-customer \
  --start-date 2024-01-01 \
  --end-date 2024-01-31 \
  --ai-model claude \
  --generate-gamma
```

### Emergency Analysis
```bash
# Quick analysis without trends
python src/main.py voice-of-customer \
  --start-date 2024-01-15 \
  --end-date 2024-01-15 \
  --no-fallback
```
