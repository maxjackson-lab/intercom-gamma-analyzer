# Gamma Presentation Generation Guide

This guide explains how to use the Gamma presentation generation features in the Intercom Analysis Tool.

## Overview

The Gamma integration allows you to automatically generate professional presentations from your Intercom conversation analysis. The system supports three presentation styles and can export to multiple formats.

## Prerequisites

### 1. Gamma API Key

You need a Gamma Pro+ subscription to use the API:

1. **Sign up for Gamma Pro+**: Visit [gamma.app](https://gamma.app) and upgrade to Pro or Ultra
2. **Get your API key**: 
   - Go to your Gamma account settings
   - Navigate to API section
   - Copy your API key (starts with `sk-gamma-`)

### 2. Intercom Workspace ID

You need your Intercom workspace ID for conversation links:

1. **Find your workspace ID**:
   - Go to [app.intercom.com](https://app.intercom.com)
   - Look at the URL: `https://app.intercom.com/a/apps/{WORKSPACE_ID}/...`
   - Copy the workspace ID from the URL

### 3. Environment Setup

Add these to your `.env` file:

```bash
# Required for Gamma integration
GAMMA_API_KEY=sk-gamma-your-api-key-here
INTERCOM_WORKSPACE_ID=your-workspace-id-here

# Existing Intercom settings
INTERCOM_ACCESS_TOKEN=your-intercom-token
OPENAI_API_KEY=your-openai-key
```

## Presentation Styles

### Executive Style (8-12 slides)
- **Audience**: C-level executives, stakeholders
- **Focus**: High-level insights, business impact, strategic recommendations
- **Content**: Executive summary, key metrics, customer voice, ROI analysis
- **Use case**: Board presentations, executive briefings

### Detailed Style (15-20 slides)
- **Audience**: Operations teams, managers
- **Focus**: Comprehensive analysis, implementation details, process improvements
- **Content**: Detailed breakdowns, technical performance, implementation roadmap
- **Use case**: Team meetings, operational reviews

### Training Style (10-15 slides)
- **Audience**: Support teams, customer success
- **Focus**: Training materials, best practices, common scenarios
- **Content**: Practice exercises, communication patterns, escalation guidelines
- **Use case**: Team training, onboarding materials

## CLI Commands

### Generate Single Presentation

```bash
# Generate executive presentation from existing analysis
python src/main.py generate-gamma \
  --analysis-file outputs/comprehensive_analysis_20240101_120000.json \
  --style executive \
  --export-pdf

# Generate detailed presentation with Google Docs export
python src/main.py generate-gamma \
  --analysis-file outputs/analysis.json \
  --style detailed \
  --export-docs
```

### Generate All Styles

```bash
# Generate all three presentation styles
python src/main.py generate-all-gamma \
  --analysis-file outputs/analysis.json \
  --export-pptx \
  --export-docs
```

### Comprehensive Analysis with Gamma

```bash
# Run full analysis and generate Gamma presentation
python src/main.py comprehensive-analysis \
  --start-date 2024-01-01 \
  --end-date 2024-01-31 \
  --max-conversations 1000 \
  --generate-gamma \
  --gamma-style executive \
  --gamma-export pdf \
  --export-docs
```

## Command Options

### generate-gamma
- `--analysis-file`: Path to analysis JSON file (required)
- `--style`: Presentation style (`executive`, `detailed`, `training`)
- `--export-pdf`: Export as PDF
- `--export-pptx`: Export as PowerPoint
- `--export-docs`: Generate markdown for Google Docs
- `--output-dir`: Output directory (default: `outputs`)

### generate-all-gamma
- `--analysis-file`: Path to analysis JSON file (required)
- `--export-pdf`: Export all as PDF
- `--export-pptx`: Export all as PowerPoint
- `--export-docs`: Generate markdown for all styles
- `--output-dir`: Output directory (default: `outputs`)

### comprehensive-analysis
- `--generate-gamma`: Enable Gamma presentation generation
- `--gamma-style`: Presentation style (`executive`, `detailed`, `training`)
- `--gamma-export`: Export format (`pdf`, `pptx`)
- `--export-docs`: Generate markdown for Google Docs
- All existing comprehensive-analysis options

## Output Files

### Gamma Presentations
- **Gamma URL**: Direct link to view/edit presentation online
- **Export URLs**: Download links for PDF/PPTX (if requested)
- **Metadata**: JSON file with generation details

### Google Docs Export
- **Markdown files**: Ready to import into Google Docs
- **Format**: Professional markdown with proper headings, tables, and links
- **Intercom links**: Direct links to source conversations

### Example Output Structure
```
outputs/
├── gamma_generation_executive_20240101_120000.json
├── comprehensive_analysis_executive_20240101_120000.md
├── comprehensive_analysis_detailed_20240101_120000.md
└── comprehensive_analysis_training_20240101_120000.md
```

## API Rate Limits

### Gamma API Limits
- **Pro Plan**: 50 presentations per day
- **Ultra Plan**: 75 presentations per day
- **Beta Status**: Limits may change post-beta

### Best Practices
- **Batch generation**: Use `generate-all-gamma` for multiple styles
- **Export options**: Choose PDF or PPTX, not both (saves credits)
- **Error handling**: System automatically retries with exponential backoff

## Troubleshooting

### Common Issues

#### 1. "Gamma API key not provided"
**Solution**: Add `GAMMA_API_KEY` to your `.env` file
```bash
GAMMA_API_KEY=sk-gamma-your-actual-key-here
```

#### 2. "INTERCOM_WORKSPACE_ID not set"
**Solution**: Add your workspace ID to `.env`
```bash
INTERCOM_WORKSPACE_ID=your-workspace-id
```

#### 3. "Generation polling timed out"
**Causes**: 
- Large presentations take longer to generate
- Network connectivity issues
- Gamma API is experiencing delays

**Solutions**:
- Wait and retry
- Reduce presentation complexity
- Check Gamma status page

#### 4. "Rate limited" errors
**Solution**: 
- Wait before making more requests
- Use batch generation instead of individual calls
- Consider upgrading Gamma plan

#### 5. Invalid API key errors
**Solutions**:
- Verify API key format: `sk-gamma-...`
- Check key is from Pro+ account
- Ensure key hasn't expired

### Debug Mode

Enable detailed logging:
```bash
export LOG_LEVEL=DEBUG
python src/main.py generate-gamma --analysis-file analysis.json
```

### Test Connection

Test your Gamma API connection:
```bash
python -c "
import asyncio
from services.gamma_client import GammaClient
async def test():
    client = GammaClient()
    result = await client.test_connection()
    print('Connection successful!' if result else 'Connection failed!')
asyncio.run(test())
"
```

## Advanced Usage

### Custom Presentation Content

The system automatically extracts:
- **Customer quotes** with Intercom conversation links
- **Category breakdowns** with volume and escalation rates
- **Key insights** from AI analysis
- **Recommendations** based on findings

### Integration with Existing Workflows

1. **Automated reporting**: Schedule comprehensive analysis with Gamma generation
2. **Team handoffs**: Generate training materials for new team members
3. **Executive updates**: Create executive summaries for monthly reviews

### API Integration

Use the services directly in your code:

```python
from services.gamma_generator import GammaGenerator

# Initialize generator
generator = GammaGenerator()

# Generate presentation
result = await generator.generate_from_analysis(
    analysis_results=your_analysis_data,
    style="executive",
    export_format="pdf"
)

print(f"Presentation URL: {result['gamma_url']}")
```

## Cost Management

### Gamma Credits
- **Generation cost**: ~1-5 credits per presentation (varies by complexity)
- **Export cost**: Additional credits for PDF/PPTX export
- **Monitoring**: Check credit usage in generation results

### Optimization Tips
1. **Choose appropriate style**: Executive uses fewer credits than detailed
2. **Limit exports**: Only export when needed
3. **Batch processing**: Generate multiple styles in one session
4. **Content optimization**: Shorter content = faster generation = fewer credits

## Support

### Getting Help
1. **Check logs**: Look for detailed error messages in console output
2. **Test components**: Use integration tests to verify setup
3. **Gamma support**: Contact Gamma support for API issues
4. **Tool issues**: Check GitHub issues or create new one

### Integration Tests

Run integration tests to verify everything works:
```bash
# Set your API key
export GAMMA_API_KEY=sk-gamma-your-key

# Run integration tests
pytest tests/integration/test_gamma_api_integration.py -v
```

### Manual Testing

Test individual components:
```bash
# Test Gamma connection
python -c "import asyncio; from services.gamma_client import GammaClient; asyncio.run(GammaClient().test_connection())"

# Test presentation builder
python -c "from services.presentation_builder import PresentationBuilder; print('Builder OK')"

# Test Google Docs exporter
python -c "from services.google_docs_exporter import GoogleDocsExporter; print('Exporter OK')"
```

## Examples

### Example 1: Monthly Executive Report
```bash
python src/main.py comprehensive-analysis \
  --start-date 2024-01-01 \
  --end-date 2024-01-31 \
  --max-conversations 2000 \
  --generate-gamma \
  --gamma-style executive \
  --gamma-export pdf
```

### Example 2: Team Training Materials
```bash
python src/main.py comprehensive-analysis \
  --start-date 2024-01-01 \
  --end-date 2024-01-31 \
  --generate-gamma \
  --gamma-style training \
  --export-docs
```

### Example 3: Detailed Operations Review
```bash
python src/main.py comprehensive-analysis \
  --start-date 2024-01-01 \
  --end-date 2024-01-31 \
  --generate-gamma \
  --gamma-style detailed \
  --gamma-export pptx
```

## Best Practices

1. **Start small**: Test with small date ranges first
2. **Monitor credits**: Keep track of Gamma credit usage
3. **Use appropriate styles**: Match style to audience
4. **Export selectively**: Only export when you need the files
5. **Save metadata**: Keep generation metadata for reference
6. **Test regularly**: Run integration tests periodically

## Changelog

### Version 1.0.0
- Initial Gamma API integration
- Three presentation styles (executive, detailed, training)
- PDF and PPTX export support
- Google Docs markdown export
- Comprehensive CLI integration
- Full test coverage

---

*For more information, see the main README.md or contact the development team.*





