# Test Mode Guide 🧪

## Overview

Test Mode allows you to run the entire analysis pipeline with **realistic mock data** instead of hitting the Intercom API. This is perfect for:
- Testing changes without API calls
- Debugging agent behavior with verbose logs
- Stress testing with different volumes
- Validating fixes before production

---

## How to Use Test Mode

### Web UI (Easiest)

1. **Check the Test Mode box** in the analysis form
2. **Select conversation count:**
   - 50 conversations (fast test)
   - 100 conversations (realistic - default)
   - 500 conversations (full test)
   - 1,000 conversations (stress test)
3. **Enable Verbose Logging** (checked by default in test mode)
4. **Click Run Analysis**

The analysis will run instantly (no API delays!) with realistic test data.

### Command Line

```bash
# Basic test mode
python src/main.py voice-of-customer --time-period week --test-mode

# With custom count
python src/main.py voice-of-customer --time-period week --test-mode --test-data-count 500

# With verbose logging
python src/main.py voice-of-customer --time-period week --test-mode --verbose

# Full test with Gamma
python src/main.py voice-of-customer --time-period week --test-mode --test-data-count 100 --verbose --generate-gamma
```

---

## What Test Mode Does

### 1. Generates Realistic Mock Data

The `TestDataGenerator` creates conversations with:

**Realistic Topic Distribution:**
- Billing: 13% (matches real data)
- Product Questions: 3%
- Bugs: 2%
- Account: 1%
- Credits: 0.5%
- Other: 80.5%

**Realistic Tier Distribution:**
- Free: 47%
- Pro: 28%
- Plus: 24%
- Ultra: 1%

**Realistic Language Distribution:**
- English: 46%
- Spanish: 11%
- Brazilian Portuguese: 10%
- Russian: 5%
- French: 4%
- Korean: 4%
- Other: 20%

**Realistic Agent Assignment:**
- Horatio: 70% of paid tier
- Boldr: 20% of paid tier
- Escalated (Gamma team): 10% of paid tier
- Fin AI only: 100% of free tier + 5% of paid tier

### 2. Enables Verbose Logging

When verbose mode is enabled, you'll see:

**Agent Decision-Making:**
```
DEBUG - TopicDetectionAgent: Checking conversation conv_123
DEBUG - TopicDetectionAgent: Found topic 'Billing' via custom_attribute
DEBUG - TopicDetectionAgent: Found topic 'Credits' via keyword match
DEBUG - TopicSentimentAgent: Analyzing sentiment for Billing (333 conversations)
DEBUG - FinPerformanceAgent: Classifying conversation conv_456
DEBUG - FinPerformanceAgent: Resolution detected: no escalation request found
```

**Sub-Topic Detection:**
```
DEBUG - SubTopicDetectionAgent: Processing Tier 1 topic: Billing
DEBUG - SubTopicDetectionAgent: Found Tier 2 subtopic 'refund' (246 conversations)
DEBUG - SubTopicDetectionAgent: LLM discovering Tier 3 themes...
DEBUG - SubTopicDetectionAgent: Discovered theme 'Subscription Plan Confusion'
```

**Fin Performance Analysis:**
```
DEBUG - FinPerformanceAgent: Analyzing subtopic performance for Billing
DEBUG - FinPerformanceAgent: Billing>refund: 99.1% resolution (180 convs)
DEBUG - FinPerformanceAgent: Billing>subscription: 98.2% resolution (55 convs)
```

### 3. Runs Full Pipeline

Test mode runs the **exact same pipeline** as production:
- ✅ Segmentation Agent
- ✅ Topic Detection Agent
- ✅ Sub-Topic Detection Agent
- ✅ Topic Sentiment Agent (per topic)
- ✅ Example Extraction Agent (per topic)
- ✅ Fin Performance Agent
- ✅ Trend Agent
- ✅ Output Formatter Agent
- ✅ Gamma Generation (if --generate-gamma)

---

## Use Cases

### Testing Bug Fixes

After fixing a bug, test it instantly:

```bash
# Before deploying your Fin topic fix
python src/main.py voice-of-customer --time-period week \
  --test-mode --test-data-count 500 --verbose

# Check that Fin breakdown now shows topics instead of "Other"
```

### Debugging Agent Behavior

See exactly what each agent is doing:

```bash
python src/main.py voice-of-customer --time-period week \
  --test-mode --test-data-count 100 --verbose 2>&1 | tee test_run.log

# Search the log for specific behavior
grep "TopicDetectionAgent: Found topic" test_run.log
grep "FinPerformanceAgent: Resolution" test_run.log
```

### Performance Testing

Test with realistic volumes:

```bash
# Simulate a full week (~5k conversations)
time python src/main.py voice-of-customer --time-period week \
  --test-mode --test-data-count 5000

# Stress test
time python src/main.py voice-of-customer --time-period week \
  --test-mode --test-data-count 10000
```

### Validating Gamma Integration

Test Gamma generation end-to-end:

```bash
python src/main.py voice-of-customer --time-period week \
  --test-mode --test-data-count 200 --generate-gamma --verbose

# You should see:
# - Mock data generation
# - Full analysis pipeline
# - Gamma API call (with real API)
# - Gamma URL returned
```

---

## Test Data Details

### Conversation Structure

Each test conversation includes:

- **All required fields:** id, created_at, updated_at, state, etc.
- **Realistic timestamps:** Spread across the date range
- **Proper tier info:** Free/Pro/Plus/Ultra with correct distribution
- **Topic indicators:** Tags, custom_attributes, conversation_topics
- **Agent emails:** Horatio/Boldr email domains for detection
- **Conversation parts:** User messages + agent/Fin responses
- **Ratings:** 30% of conversations have ratings (mostly 4-5 stars)

### Message Templates

Realistic customer messages for each topic:

**Billing:**
- "I just signed up for gamma pro monthly plan but it charged me for the whole year"
- "I got confused and paid for the annual pro, the reality is that I can't afford it"
- "Can I get a refund? I selected the wrong plan"

**Product Questions:**
- "How do I connect my custom domain?"
- "Where can I find domain settings or SSL settings?"
- "Can I export to PowerPoint?"

**Bugs:**
- "When I export my slides to Google Slides, the icons are not exported"
- "I upgraded to Pro but only received 2000 credits instead of 4000"
- "PDF export shows incorrect page numbers"

**And more for Account, Credits, and Other categories...**

---

## Verbose Logging Output

### What You'll See

**Without Verbose:**
```
📥 Fetching conversations...
   ✅ Fetched 4885 conversations

📊 Phase 1: Segmentation
   ✅ Paid: 2584, Free: 2297
🏷️  Phase 2: Topic Detection
   ✅ Detected 7 topics
💭 Phase 3: Per-Topic Analysis
   ✅ Billing: Sentiment + 10 examples
```

**With Verbose (--verbose):**
```
📥 Fetching conversations...
DEBUG - ChunkedFetcher: Starting chunked fetch from 2025-10-18 to 2025-10-25
DEBUG - ChunkedFetcher: Total date range: 7 days
DEBUG - IntercomServiceV2: Fetching page 1
DEBUG - IntercomServiceV2: Fetched 50 conversations (total: 50)
   ✅ Fetched 4885 conversations

📊 Phase 1: Segmentation
DEBUG - SegmentationAgent: Conversation 215471429901252 tier: Pro
DEBUG - SegmentationAgent: Classifying paid tier conversation 215471429901252
DEBUG - SegmentationAgent: Found admin email: agent@hirehoratio.co
DEBUG - SegmentationAgent: Classified as ('paid', 'horatio')
   ✅ Paid: 2584 (Horatio: 1205, Boldr: 380, Escalated: 45), Free: 2297

🏷️  Phase 2: Topic Detection
DEBUG - TopicDetectionAgent: Detecting topics for 4885 conversations
DEBUG - TopicDetectionAgent: Conversation 215471429901252: Found 'Billing' via attribute
DEBUG - TopicDetectionAgent: Conversation 215471428521638: Found 'Product Question' via keyword
DEBUG - TopicDetectionAgent: Running LLM semantic discovery...
DEBUG - TopicDetectionAgent: LLM discovered 3 additional topics
   ✅ Detected 7 topics across all tiers

💭 Phase 3: Per-Topic Analysis
DEBUG - TopicSentimentAgent: Analyzing 'Billing' (333 conversations)
DEBUG - TopicSentimentAgent: Generated insight with HIGH confidence
DEBUG - ExampleExtractionAgent: Selecting from 333 candidates
DEBUG - ExampleExtractionAgent: LLM selected 10 examples
DEBUG - ExampleExtractionAgent: Translating 6 non-English quotes
   ✅ Billing: Sentiment + 10 examples
```

---

## Benefits

### Speed
- **Test Mode: 5-10 seconds** (no API calls)
- **Production: 3-8 minutes** (API rate limits)

### Safety
- No risk of hitting API rate limits
- No cost for API credits
- Can run unlimited tests

### Debugging
- See exact agent logic
- Trace topic detection decisions
- Watch sentiment analysis reasoning
- Monitor example selection process

### Validation
- Verify bug fixes work correctly
- Test new features end-to-end
- Catch regressions early

---

## Combining Test Mode with Real Data

### Hybrid Testing Strategy

1. **First: Test with mock data**
   ```bash
   python src/main.py voice-of-customer --time-period week --test-mode --verbose
   ```

2. **Then: Test with small real dataset**
   ```bash
   python src/main.py voice-of-customer --time-period yesterday --verbose
   ```

3. **Finally: Run production analysis**
   ```bash
   python src/main.py voice-of-customer --time-period week --generate-gamma
   ```

---

## Examples

### Example 1: Debug Fin Topic Breakdown

```bash
python src/main.py voice-of-customer --time-period week \
  --test-mode --test-data-count 200 --verbose 2>&1 | \
  grep "FinPerformanceAgent"

# Output:
# DEBUG - FinPerformanceAgent: Analyzing Fin conversations by tier
# DEBUG - FinPerformanceAgent: Free tier: 94 conversations
# DEBUG - FinPerformanceAgent: Analyzing subtopic performance for Billing
# DEBUG - FinPerformanceAgent: Billing>refund: 99.1% resolution (18 convs)
# INFO - FinPerformanceAgent: Free tier resolution rate: 98.9%
```

### Example 2: Test Gamma Generation

```bash
python src/main.py voice-of-customer --time-period week \
  --test-mode --test-data-count 100 --generate-gamma

# Output:
# 🧪 TEST MODE: Generating 100 mock conversations...
# ✅ Generated 100 test conversations
# [... analysis runs ...]
# 🎨 Generating Gamma presentation...
# ✅ Generation ID: xyz123
# ⏳ Waiting for Gamma to process...
# 📊 Gamma URL: https://gamma.app/docs/...
```

### Example 3: Agent Performance Testing

```bash
python src/main.py agent-performance --agent horatio \
  --time-period week --test-mode --test-data-count 150 --verbose

# Tests Horatio agent analysis with mock data
```

---

## Technical Details

### Test Data Generator Code

Location: `src/services/test_data_generator.py`

**Key Methods:**
- `generate_conversations()` - Main entry point
- `_create_fin_conversation()` - Generate Fin AI conversation
- `_create_human_conversation()` - Generate human-supported conversation
- `_select_random_tier()` - Pick tier based on distribution
- `_select_random_topic()` - Pick topic based on distribution

**Distribution Accuracy:**
The generator uses actual data distributions from your production Intercom:
- Topic percentages match real customer behavior
- Tier split matches your customer base
- Language distribution reflects global usage
- Agent assignment reflects actual BPO contracts

### Integration Points

**1. CLI Integration (`src/main.py`)**
```python
if test_mode:
    from src.services.test_data_generator import TestDataGenerator
    generator = TestDataGenerator()
    conversations = generator.generate_conversations(
        count=test_data_count,
        start_date=start_date,
        end_date=end_date
    )
else:
    fetcher = ChunkedFetcher()
    conversations = await fetcher.fetch_conversations_chunked(...)
```

**2. Web UI Integration (`deploy/railway_web.py` + `static/app.js`)**
- Checkbox in form
- Dynamic options panel
- JavaScript wiring to pass flags
- Command executor whitelist updated

**3. Verbose Logging (`src/main.py`)**
```python
if verbose:
    logging.getLogger().setLevel(logging.DEBUG)
    for module in ['agents', 'services', 'src.agents', 'src.services']:
        logging.getLogger(module).setLevel(logging.DEBUG)
```

---

## Comparing Test vs Production

### Test Mode Output:
```
🧪 TEST MODE: Generating 100 mock conversations...
   Tier distribution: {'Free': 47, 'Pro': 28, 'Plus': 24, 'Ultra': 1}
   Topic distribution: {'Billing': 13, 'Product Question': 3, 'Bug': 2, 'Other': 82}
   Agent distribution: {'fin_ai': 47, 'horatio': 37, 'boldr': 11, 'escalated': 5}
   ✅ Generated 100 test conversations
```

### Production Mode Output:
```
📥 Fetching conversations from Intercom...
   Fetching page 1
   Fetched 50 conversations (total: 50)
   [... 8 minutes later ...]
   ✅ Fetched 4885 conversations
```

---

## Troubleshooting

### Issue: Test mode not available in web UI

**Solution:** Clear browser cache and refresh. Check that you're on the latest deployment.

### Issue: Verbose logs not showing

**Solution:** 
1. Check that "Verbose Logging" checkbox is checked
2. Logs appear in Terminal tab, not Summary tab
3. Scroll down - DEBUG logs are at the top

### Issue: Test data doesn't match expectations

**Solution:** Adjust distributions in `src/services/test_data_generator.py`:
```python
TOPIC_DISTRIBUTION = {
    'Billing': 0.20,  # Increase billing to 20%
    # ... etc
}
```

### Issue: Agent performance shows 0 conversations in test mode

**Solution:** Test mode generates both paid and free tier by default. For agent-performance analysis specifically, it only generates paid tier (since agents only handle paid customers).

---

## Future Enhancements

Potential improvements to test mode:

1. **Configurable distributions** - Let users adjust topic/tier mix
2. **Scenario presets** - "High billing load", "API outage", etc.
3. **Deterministic mode** - Same data every time for regression testing
4. **Export test data** - Save generated data for offline testing
5. **Load from file** - Use saved test data sets

---

## Summary

✅ **Test Mode Features:**
- Realistic mock data generation
- No API calls required
- Instant execution
- Verbose DEBUG logging
- Full pipeline testing
- Web UI integration

✅ **Use Cases:**
- Bug fix validation
- Feature testing
- Performance benchmarking
- Agent behavior debugging
- Pre-production checks

✅ **Realistic Data:**
- Matches real topic distribution
- Proper tier split
- Correct language mix
- Accurate agent assignment
- Valid Intercom structure

**Test with confidence!** 🚀

