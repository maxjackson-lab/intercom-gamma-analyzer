# VoC → Gamma Pipeline Validation Guide

This guide provides step-by-step instructions for testing the VoC analysis → Gamma generation flow on Railway.

## Overview

The VoC → Gamma pipeline consists of:
1. **VoC Analysis**: Multi-agent topic-based analysis produces Hilary-format markdown
2. **Markdown Generation**: OutputFormatterAgent creates cards with `---` slide breaks
3. **Gamma Generation**: GammaGenerator converts markdown to presentation
4. **Result Display**: Gamma URL displayed in terminal and saved to file

**What was added**: Gamma generation integration in `run_topic_based_analysis()` function (src/main.py lines 3274-3334)

**Expected outcome**: 
- Gamma URL displayed in terminal after analysis completes
- URL saved to `gamma_url_{week_id}_{timestamp}.txt` file
- Gamma metadata added to results JSON
- Presentation viewable in browser with topic cards

## Prerequisites

Before testing, ensure:
- ✅ Railway deployment is running
- ✅ `GAMMA_API_KEY` is configured in Railway environment variables
- ✅ `INTERCOM_ACCESS_TOKEN` is configured
- ✅ At least 20-50 conversations exist in the test date range
- ✅ Latest code is deployed (check deployment timestamp)

## Quick Validation Test (10 minutes)

### Step 1: Run VoC analysis with Gamma generation via CLI

```bash
python -m src.main voice --month 11 --year 2024 --generate-gamma --analysis-type topic-based --output-format gamma
```

### Step 2: Check terminal output

Look for these indicators:

```
🤖 Multi-Agent Topic-Based Analysis Starting
Mode: Topic-Based Workflow (Hilary's Format)
Agents: Segmentation → Topic Detection → Per-Topic Sentiment → Examples → Fin Analysis → Trends

📥 Fetching conversations...
   ✅ Fetched X conversations

[Agent execution progress...]

================================================================================
🎉 Topic-Based Analysis Complete!
================================================================================

📊 Total conversations: X
   Paid customers (human support): Y
   Free customers (Fin AI): Z
🏷️  Topics analyzed: N
⏱️  Total time: X.Xs
🤖 Agents completed: 7/7

📁 Report saved: outputs/weekly_voc_2024-11_TIMESTAMP.md
📁 Full results: outputs/weekly_voc_2024-11_TIMESTAMP.json

🎨 Generating Gamma presentation...

🎨 Gamma presentation generated!
📊 Gamma URL: https://gamma.app/docs/...
💳 Credits used: 2
⏱️  Generation time: 15.3s
📁 Gamma URL saved: outputs/gamma_url_2024-11_TIMESTAMP.txt
```

### Step 3: Verify Gamma URL

1. **Copy the URL** from terminal output
2. **Open in browser**
3. **Verify presentation**:
   - ✅ Presentation loads successfully
   - ✅ Title: "Voice of Customer Analysis - Week YYYY-MM"
   - ✅ Slides match topics from analysis
   - ✅ Each topic card has:
     - Topic name with volume
     - Detection method
     - Sentiment insight
     - Example conversation links
   - ✅ Fin AI Performance slide is present

### Step 4: Check saved files

Navigate to `outputs/` directory:

```bash
ls -lh outputs/weekly_voc_2024-11_*.* outputs/gamma_url_*.txt
```

**Expected files**:
- `weekly_voc_2024-11_TIMESTAMP.md` - Markdown report with Hilary cards
- `weekly_voc_2024-11_TIMESTAMP.json` - Full results with metadata
- `gamma_url_2024-11_TIMESTAMP.txt` - Gamma URL in text file

**Verify markdown file**:
```bash
cat outputs/weekly_voc_2024-11_TIMESTAMP.md
```

Should contain:
- `# Voice of Customer Analysis - Week 2024-11`
- `## Customer Topics (Paid Tier - Human Support)`
- Multiple `### Topic Name` sections
- `---` slide breaks between topics
- `## Fin AI Performance (Free Tier - AI-Only Support)`

**Verify JSON file**:
```bash
cat outputs/weekly_voc_2024-11_TIMESTAMP.json | jq '.gamma_presentation'
```

Should output:
```json
{
  "gamma_url": "https://gamma.app/docs/...",
  "generation_id": "gen_...",
  "credits_used": 2,
  "generation_time_seconds": 15.3,
  "theme": null,
  "slide_count": 10
}
```

## Railway Web UI Validation (15 minutes)

### Step 1: Access Railway web interface

1. Navigate to your Railway deployment URL
2. Should see "Intercom Analysis Tool - Chat Interface"

### Step 2: Select analysis options

In the form:
- **Analysis Type**: "VoC: Hilary Format (Topic Cards)"
- **Date Range**: "Yesterday" or "Last 7 days"
- **Multi-Agent Analysis Mode**: "Topic-Based (Hilary's VoC Cards)"
- **Output Format**: "Gamma Presentation" (if available) or "Markdown"
- **Generate Gamma**: Check the box if separate option

### Step 3: Execute analysis

1. Click "Execute" or "Run Analysis" button
2. Watch terminal output stream in real-time
3. Look for progress indicators:
   - ✅ Phase 1: Segmentation
   - ✅ Phase 2: Topic Detection
   - ✅ Phase 3: Per-Topic Analysis
   - ✅ Phase 4: Fin AI Performance
   - ✅ Phase 5: Trend Analysis
   - ✅ Phase 6: Output Formatting
   - ✅ Generating Gamma presentation...

### Step 4: Verify Gamma URL in response

- Check if Gamma URL is displayed in web UI
- If visible, click to open in new tab
- If not visible, check Railway logs (see Step 5)

### Step 5: Check Railway logs

In Railway dashboard:
1. Click "Logs" tab
2. Search for "Gamma presentation generated"
3. Look for log line with Gamma URL
4. Verify no errors during generation:
   ```
   ✅ No "Gamma generation failed" warnings
   ✅ No "GammaAPIError" exceptions
   ✅ No "Rate limit exceeded" errors
   ```

## Detailed Validation Test (30 minutes)

### Test with larger dataset

```bash
python -m src.main voice --month 11 --year 2024 --generate-gamma --analysis-type topic-based --output-format gamma
```

### Verification Checklist

#### 1. Analysis completes successfully

- [ ] All 7 agents complete without errors
- [ ] No timeout errors
- [ ] No rate limit errors from Intercom API
- [ ] Execution time is reasonable:
  - 50 conversations: < 2 minutes
  - 100 conversations: < 5 minutes
  - 200+ conversations: < 10 minutes

#### 2. Markdown format is correct

Open the markdown file:
```bash
cat outputs/weekly_voc_2024-11_TIMESTAMP.md
```

Verify structure:
- [ ] Title: `# Voice of Customer Analysis - Week 2024-11`
- [ ] Section: `## Customer Topics (Paid Tier - Human Support)`
- [ ] Multiple topic cards (3-15 topics expected)
- [ ] Each card has:
  - [ ] `### Topic Name`
  - [ ] `**X tickets / Y% of weekly volume**`
  - [ ] `**Detection Method**: ...`
  - [ ] `**Sentiment**: ... BUT ...` (contrast structure)
  - [ ] `**Examples**:` with numbered list
  - [ ] Intercom URLs: `https://app.intercom.com/a/inbox/inbox/conv_...`
  - [ ] `---` slide break after card
- [ ] Section: `## Fin AI Performance (Free Tier - AI-Only Support)`
- [ ] Fin card with:
  - [ ] Total conversations handled
  - [ ] What Fin is doing well
  - [ ] Knowledge gaps
  - [ ] `---` slide break

#### 3. Gamma presentation matches markdown

Open Gamma URL in browser:

- [ ] Presentation loads without errors
- [ ] Title slide: "Voice of Customer Analysis - Week 2024-11"
- [ ] Slide count ≈ topic count + 2 (title + Fin)
- [ ] Each topic slide has:
  - [ ] Topic name as title
  - [ ] Volume and percentage displayed
  - [ ] Sentiment insight visible
  - [ ] Example links are clickable
- [ ] Test 2-3 Intercom links:
  - [ ] Links open in new tab
  - [ ] Links go to correct conversations
  - [ ] Conversation IDs match
- [ ] Fin AI Performance slide is present
- [ ] No formatting errors (broken markdown, escaped characters)

#### 4. Gamma metadata is saved

Open JSON file:
```bash
cat outputs/weekly_voc_2024-11_TIMESTAMP.json | jq '.gamma_presentation'
```

Verify metadata:
- [ ] `gamma_url`: Valid URL starting with `https://gamma.app/`
- [ ] `generation_id`: Present (format: `gen_...`)
- [ ] `credits_used`: Number >= 0
- [ ] `generation_time_seconds`: Number > 0
- [ ] `theme`: null or theme name
- [ ] `slide_count`: Number matches expected slides

## Troubleshooting

### Issue: Gamma URL not displayed in terminal

**Possible causes**:

1. **Gamma generation failed**
   - Check logs for "Gamma generation failed" warning
   - Look for error message details
   - Common errors:
     - `Invalid API key` → Check `GAMMA_API_KEY` environment variable
     - `Input text must be 1-750,000 characters` → Markdown too long/short
     - `Validation errors` → Check markdown structure

2. **`generate_gamma` flag not set**
   - Verify command includes `--generate-gamma` flag
   - Verify `output_format` is 'gamma' or 'markdown'
   - Check that both conditions are met in code

3. **Code not deployed**
   - Check Railway deployment timestamp
   - Verify latest commit is deployed
   - Force redeploy if needed:
     ```bash
     railway up --detach
     ```

**Solution**:
```bash
# Check environment variable
railway variables | grep GAMMA_API_KEY

# Verify flag is set
python -m src.main voice --help | grep generate-gamma

# Check logs for detailed error
railway logs --tail 100
```

### Issue: Gamma presentation has wrong content

**Possible causes**:

1. **Markdown format incorrect**
   - Check markdown file for slide breaks
   - Verify topic cards have all required fields
   - Look for malformed links or escaped characters

2. **Gamma API interpretation**
   - Gamma may reformat content automatically
   - Check if `textMode="preserve"` is used (it should be)
   - Check if `cardSplit="inputTextBreaks"` is used (it should be)

**Solution**:
```bash
# Inspect markdown structure
cat outputs/weekly_voc_*.md | grep -E "^###|^---$|^\*\*"

# Count slide breaks
cat outputs/weekly_voc_*.md | grep -c "^---$"

# Check code settings
grep -A 5 "generate_presentation" src/services/gamma_generator.py
```

### Issue: Gamma generation times out

**Possible causes**:

1. **Polling timeout**
   - Default: 30 polls × 2 seconds = 60 seconds
   - Large presentations may take longer
   - Check logs for "polling timeout" error

2. **Gamma API slow**
   - API may be under heavy load
   - Retry generation after a few minutes

**Solution**:
```bash
# Check polling configuration
grep -A 10 "poll_generation" src/services/gamma_client.py

# Increase timeout if needed (in gamma_client.py)
# max_polls = 60  # Increase from 30 to 60
```

### Issue: Validation errors

**Possible causes**:

1. **Markdown too short**
   - Need at least 200 characters for meaningful presentation
   - Check if analysis found any topics

2. **Missing required sections**
   - Validation may expect certain sections
   - VoC format differs from standard analysis format

**Solution**:
```bash
# Check markdown length
wc -c outputs/weekly_voc_*.md

# Check for topics
grep -c "^###" outputs/weekly_voc_*.md

# Review validation logic
grep -A 20 "_validate_gamma_input" src/services/gamma_generator.py
```

### Issue: "Rate limit exceeded" error

**Possible causes**:
- Gamma API rate limits exceeded
- Too many generations in short time period

**Solution**:
- Wait 5-10 minutes before retrying
- Check Gamma API dashboard for rate limit status
- Consider upgrading Gamma plan if frequent issue

### Issue: "Insufficient credits" error

**Possible causes**:
- Gamma account out of credits
- Free tier limits reached

**Solution**:
- Check Gamma account credit balance
- Purchase more credits or upgrade plan
- Reduce `num_cards` parameter to use fewer credits

## Expected Results

For a typical VoC analysis:

| Metric | Expected Value |
|--------|---------------|
| Topics detected | 5-15 topics |
| Gamma slides | 7-17 slides (topics + title + Fin) |
| Generation time | 30-90 seconds |
| Credits used | 1-3 credits |
| Markdown length | 2,000-20,000 characters |
| Slide breaks | 6-16 breaks (one per topic + Fin) |

## Validation Checklist

Complete validation checklist:

- [ ] Ran VoC analysis with `--generate-gamma` flag
- [ ] Verified Gamma URL in terminal output
- [ ] Opened Gamma URL in browser
- [ ] Verified presentation has correct title
- [ ] Verified slides match topics from analysis
- [ ] Verified each topic card has all required fields:
  - [ ] Topic name with volume
  - [ ] Detection method
  - [ ] Sentiment insight
  - [ ] Example conversation links
- [ ] Verified Intercom links work (tested 3 links)
- [ ] Verified Fin AI Performance slide is present
- [ ] Checked `gamma_url_*.txt` file exists
- [ ] Checked `gamma_presentation` metadata in JSON
- [ ] Tested with Railway web UI
- [ ] Verified no errors in Railway logs
- [ ] Tested with different date ranges:
  - [ ] Yesterday
  - [ ] Last 7 days
  - [ ] Last 30 days
- [ ] Verified performance is acceptable:
  - [ ] Analysis completes in < 5 minutes
  - [ ] Gamma generation completes in < 90 seconds
  - [ ] No timeout errors

## Next Steps

Once validation is complete:

1. **Run with production data**
   - Test with full monthly analysis
   - Verify performance at scale
   - Monitor credit usage

2. **Test export formats**
   ```bash
   python -m src.main voice --month 11 --year 2024 --generate-gamma --export-format pdf
   ```

3. **Test with different themes**
   ```bash
   # Edit src/main.py to specify theme_name
   theme_name = "Night Sky"  # or "Minimal", "Bold"
   ```

4. **Set up automated weekly generation**
   - Create cron job or scheduled task
   - Email Gamma URL to stakeholders
   - Archive presentations for historical reference

5. **Monitor credit usage**
   - Track credits used per generation
   - Set up alerts for low credit balance
   - Plan credit budget for regular analyses

## Reference Files

Key files involved in the pipeline:

| File | Purpose | Lines |
|------|---------|-------|
| `src/main.py` | CLI command and Gamma integration | 3197-3338 |
| `src/agents/topic_orchestrator.py` | Multi-agent workflow orchestration | 67-304 |
| `src/agents/output_formatter_agent.py` | Markdown formatting (Hilary cards) | 78-195 |
| `src/services/gamma_generator.py` | Gamma generation logic | 147-251 |
| `src/services/gamma_client.py` | Gamma API client | Full file |

## Test Files

Automated tests:

| File | Purpose |
|------|---------|
| `tests/integration/test_voc_gamma_integration.py` | End-to-end integration tests |
| `tests/test_gamma_markdown_validation.py` | Markdown validation unit tests |
| `scripts/test_voc_gamma_pipeline.py` | Quick standalone test script |

Run tests:
```bash
# Run all VoC-Gamma integration tests
pytest tests/integration/test_voc_gamma_integration.py -v

# Run markdown validation tests
pytest tests/test_gamma_markdown_validation.py -v

# Run quick pipeline test
python scripts/test_voc_gamma_pipeline.py
```

## Contact & Support

If validation fails after following this guide:

1. **Check test files** for expected behavior
2. **Review implementation** in `src/main.py` lines 3274-3334
3. **Verify Gamma API key** is valid and has credits
4. **Check Railway logs** for detailed error messages
5. **Run unit tests** to isolate the issue:
   ```bash
   pytest tests/integration/test_voc_gamma_integration.py::TestVoCMarkdownToGammaConversion -v
   ```

## Appendix: Manual Testing Script

Quick test without running full analysis:

```python
# test_gamma_manual.py
import asyncio
from src.services.gamma_generator import GammaGenerator

async def test():
    markdown = """# Voice of Customer Analysis - Week 2024-W42
    
## Customer Topics (Paid Tier - Human Support)

### Billing Issues
**45 tickets / 28% of weekly volume**
**Detection Method**: Intercom conversation attribute

**Sentiment**: Customers frustrated with unexpected charges BUT appreciate quick refunds

**Examples**:
1. "I was charged twice" - [View conversation](https://app.intercom.com/a/inbox/inbox/conv_123)

---
"""
    
    generator = GammaGenerator()
    result = await generator.generate_from_markdown(
        input_text=markdown,
        title="Test VoC Analysis",
        num_cards=5
    )
    
    print(f"Gamma URL: {result['gamma_url']}")
    print(f"Credits used: {result['credits_used']}")

asyncio.run(test())
```

Run:
```bash
python test_gamma_manual.py
```

---

**Last updated**: 2024-10-23
**Version**: 1.0

