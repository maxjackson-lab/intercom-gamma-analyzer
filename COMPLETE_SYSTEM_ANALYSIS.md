# Complete System Analysis - Multi-Agent Branch
## What We Built, What's Broken, and Why

**Date:** October 22, 2025  
**Branch:** `feature/multi-agent-implementation`  
**Status:** 🔴 Many features built but core functionality unreliable

---

## 📊 Executive Summary

### What This Application Is Supposed To Do

**Primary Function:** Analyze Intercom support conversations and Canny feedback to generate Voice of Customer reports in Gamma presentations.

**Key Users:**
- Hilary (your boss) - Weekly VoC cards with topic-specific sentiment
- You (Max) - Agent performance reviews, strategic insights
- Leadership team - Executive summaries and trend analysis

### Current Reality

**What Works:**
- ✅ Fetches conversations from Intercom
- ✅ Multi-agent pipeline runs without crashing
- ✅ Generates markdown reports
- ✅ LLM sentiment analysis produces nuanced insights
- ✅ Parallel processing (9x faster than sequential)

**What Doesn't Work:**
- ❌ Gamma presentations fail or show wrong content
- ❌ Examples often show "0 examples" despite LLM selecting them
- ❌ Canny integration untested
- ❌ Import path inconsistencies cause local testing failures
- ❌ UI sometimes shows errors or broken references

---

## 🏗️ System Architecture

### Data Flow (Topic-Based Analysis)

```
1. WEB UI (Railway)
   └─ User selects: "VoC: Hilary Format", "Yesterday", "Gamma"
   
2. FRONTEND (static/app.js)
   └─ runAnalysis() builds command:
      "voice-of-customer --multi-agent --analysis-type topic-based --time-period yesterday --generate-gamma"
   
3. BACKEND (deploy/railway_web.py)
   └─ FastAPI receives command
   └─ WebCommandExecutor runs: python src/main.py voice-of-customer ...
   
4. CLI (src/main.py)
   └─ voice_of_customer_analysis() function
   └─ Calls: run_topic_based_analysis_custom()
   
5. DATA FETCHING
   └─ ChunkedFetcher fetches from Intercom API
   └─ Returns ~1000 conversations for "yesterday"
   
6. MULTI-AGENT PIPELINE (src/agents/topic_orchestrator.py)
   Phase 1: SegmentationAgent → Paid (human) vs Free (Fin AI)
   Phase 2: TopicDetectionAgent → Detect topics (+ LLM semantic discovery)
   Phase 3: Per-topic analysis (PARALLEL):
      ├─ TopicSentimentAgent → Nuanced sentiment insight
      └─ ExampleExtractionAgent → Select 3-10 examples
   Phase 4: FinPerformanceAgent → Fin AI metrics + LLM insights
   Phase 5: TrendAgent → Week-over-week trends + LLM explanations
   Phase 6: OutputFormatterAgent → Format into Hilary's cards
   
7. OUTPUT
   └─ Markdown report saved to outputs/topic_based_*.md
   └─ IF --generate-gamma:
      └─ GammaClient.generate_presentation() → Send to Gamma API
      └─ Poll for completion → Return Gamma URL
```

---

## 🔍 Detailed Component Analysis

### 1. Web UI (deploy/railway_web.py)

**Purpose:** Simple dropdown form for analysis configuration

**Current State:**
```html
<select id="analysisType">
  <optgroup label="Voice of Customer">
    <option value="voice-of-customer-hilary">Hilary Format</option>
    <option value="voice-of-customer-synthesis">Synthesis</option>
    <option value="voice-of-customer-complete">Complete</option>
  </optgroup>
  <optgroup label="Category Deep Dives">
    <option value="analyze-billing">Billing</option>
    <option value="analyze-product">Product</option>
    <option value="analyze-api">API</option>
    ...
  </optgroup>
  <optgroup label="Agent Performance">
    <option value="agent-performance-horatio">Horatio Review</option>
    <option value="agent-performance-boldr">Boldr Review</option>
  </optgroup>
</select>
```

**What Works:**
- ✅ Clean dropdown interface
- ✅ All analysis types present
- ✅ Time period selector
- ✅ Taxonomy filtering

**What's Broken:**
- ❌ Old wizard code removed but may have left orphaned functions
- ❌ checkSystemStatus() tries to access removed DOM elements
- ❌ Example queries section removed but setQuery() function may still be called
- ❌ Multiple hidden/legacy elements confusing the page

**File Location:** `deploy/railway_web.py` lines 220-400

---

### 2. JavaScript (static/app.js)

**Purpose:** Handle form submission and command execution

**Critical Function:**
```javascript
function runAnalysis() {
    const analysisType = document.getElementById('analysisType').value;
    const timePeriod = document.getElementById('timePeriod').value;
    const dataSource = document.getElementById('dataSource').value;
    const taxonomyFilter = document.getElementById('taxonomyFilter').value;
    const outputFormat = document.getElementById('outputFormat').value;
    
    let command = '';
    let args = [];
    
    if (analysisType === 'voice-of-customer-hilary') {
        command = 'voice-of-customer';
        args.push('--multi-agent', '--analysis-type', 'topic-based');
    }
    // ... more mappings
    
    if (timePeriod === 'custom') {
        args.push('--start-date', start, '--end-date', end);
    } else {
        args.push('--time-period', timePeriod);
    }
    
    executeCommand(command, args);
}
```

**What Works:**
- ✅ Maps UI selections to CLI commands
- ✅ Handles agent-performance commands
- ✅ Custom date range support

**What's Broken:**
- ❌ Old wizard functions still exist (lines 754+) but unused
- ❌ pollExecution() may not be called correctly
- ❌ Help query handler references removed DOM elements
- ❌ No validation before submission

**File Location:** `static/app.js` lines 755-826

---

### 3. Multi-Agent Pipeline (src/agents/topic_orchestrator.py)

**Purpose:** Coordinate 7 agents to produce Hilary's VoC cards

**Flow:**
```python
async def execute_weekly_analysis(conversations, week_id, start_date, end_date):
    # Phase 1: Segment paid vs free
    segmentation_result = await self.segmentation_agent.execute(context)
    
    # Phase 2: Detect topics
    topic_detection_result = await self.topic_detection_agent.execute(context)
    
    # Phase 3: Process each topic IN PARALLEL
    async def process_topic(topic_name, topic_stats):
        sentiment_result = await self.topic_sentiment_agent.execute()
        examples_result = await self.example_extraction_agent.execute()
        return topic_name, sentiment_result, examples_result
    
    topic_results = await asyncio.gather(*[process_topic(name, stats) for name, stats in topics])
    
    # Phase 4: Fin analysis
    fin_result = await self.fin_performance_agent.execute()
    
    # Phase 5: Trends
    trend_result = await self.trend_agent.execute()
    
    # Phase 6: Format output
    formatter_result = await self.output_formatter_agent.execute()
    
    return {
        'formatted_report': formatter_result.data['formatted_output'],
        'summary': {...}
    }
```

**What Works:**
- ✅ All agents execute
- ✅ Parallel processing works (fast!)
- ✅ Returns formatted markdown

**What's Broken:**
- ❌ LLM-discovered topics with 0 conversations still get analyzed (waste)
- ❌ Error handling doesn't gracefully skip failed topics
- ❌ Customer message extraction assumes specific structure
- ❌ No validation that conversations have required fields

**File Location:** `src/agents/topic_orchestrator.py`

---

### 4. Individual Agents

#### SegmentationAgent
**Purpose:** Separate paid (human) vs free (Fin) customers

**Code:**
```python
def _classify_conversation(self, conv):
    text = conv.get('full_text', '').lower()
    assignee = str(conv.get('admin_assignee_id', '')).lower()
    
    # Check for escalation
    if any(name in text for name in ['dae-ho', 'max jackson', 'hilary']):
        return 'paid', 'escalated'
    
    # Check for Tier 1 agents
    if re.search(r'horatio|@hirehoratio\.co', text):
        return 'paid', 'horatio'
    
    if re.search(r'boldr|@boldrimpact\.com', text):
        return 'paid', 'boldr'
    
    # AI-only
    if conv.get('ai_agent_participated') and not conv.get('admin_assignee_id'):
        return 'free', 'fin_ai'
    
    return 'unknown', 'unknown'
```

**What Works:**
- ✅ Rule-based classification (fast, no LLM needed)
- ✅ Detects Horatio via email domain

**What's Broken:**
- ❌ Horatio count always 0 in logs (pattern not matching)
- ❌ Most conversations classified as 'unknown' (99%)
- ❌ Email domain patterns may not be in conversation text

**Issue:** Line 2780 logs show `'horatio': 0` despite Horatio handling conversations. Pattern matching is failing.

---

#### TopicDetectionAgent
**Purpose:** Detect topics via Intercom attributes + keywords + LLM

**Code:**
```python
# Rule-based detection
for topic_name, config in self.topics.items():
    if config['attribute'] in attributes:
        detected.append({'topic': topic_name, 'method': 'attribute', 'confidence': 1.0})
    elif sum(1 for kw in config['keywords'] if kw in text) > 0:
        detected.append({'topic': topic_name, 'method': 'keyword', 'confidence': 0.7})

# LLM enhancement
llm_topics = await self._enhance_with_llm(conversations, topic_distribution)
# Discovers: "Subscription Cancellation", "Refund Request", etc.
```

**What Works:**
- ✅ Hybrid detection (attributes + keywords)
- ✅ LLM discovers additional topics
- ✅ Logs show: "LLM discovered 4 additional topics"

**What's Broken:**
- ❌ LLM-discovered topics have 0 conversations (not rescanned)
- ❌ Wastes LLM calls analyzing empty topics
- ❌ Topics dictionary hardcoded (only 8 topics defined)

**Issue:** Lines 207-216 in topic_detection_agent.py add LLM topics but don't rescan conversations to assign them, so they always have `volume: 0`.

---

#### TopicSentimentAgent
**Purpose:** Generate specific sentiment insights per topic

**Code:**
```python
prompt = f"""
Analyze sentiment for: {topic_name}

Sample conversations:
{json.dumps(sample, indent=2)}

Generate ONE SENTENCE that captures nuanced sentiment.

Examples:
- "Users hate buddy so much"
- "Customers appreciate X BUT frustrated by Y"

Your insight for {topic_name}:
"""

insight = await self.openai_client.generate_analysis(prompt)
```

**What Works:**
- ✅ Produces nuanced insights
- ✅ Examples: "Customers frustrated with charges BUT appreciate refunds"
- ✅ Professional tone

**What's Broken:**
- ❌ Sometimes returns "cannot verify" for valid topics
- ❌ Samples only 10 conversations (may miss patterns)
- ❌ No validation that sample has actual content

**Issue:** If `customer_messages` is empty, prompt has no actual data, leading to "cannot verify" responses.

---

#### ExampleExtractionAgent
**Purpose:** Select 3-10 most representative conversation examples

**Code:**
```python
# Score conversations
for conv in conversations:
    score = self._score_conversation(conv, sentiment)
    scored_conversations.append((score, conv))

# Take top 20 candidates
candidates = [conv for score, conv in scored_conversations if score >= 2.0][:20]

# LLM selects best
prompt = f"""
Select most representative examples for {topic}.

Candidates:
1. "Message 1"
2. "Message 2"
...

Return JSON array: [1, 3, 7, 12, ...]
"""

selected_numbers = json.loads(llm_response)
selected = [candidates[num-1] for num in selected_numbers]
```

**What Works:**
- ✅ LLM selection works
- ✅ Logs show: "LLM selected 7 examples: [1, 3, 5...]"

**What's Broken:**
- ❌ Crashes with timestamp error: `'int' object has no attribute 'isoformat'`
- ❌ Fixed in latest commit but may still fail
- ❌ Returns 0 examples when it should return 7

**Issue:** Line 269 tries to call `.isoformat()` on Unix timestamp. Fixed in commit but Railway may not have latest code.

---

#### FinPerformanceAgent
**Purpose:** Analyze Fin AI's performance

**Code:**
```python
# Calculate metrics
escalation_phrases = ['speak to human', 'talk to agent', 'real person']
resolved_by_fin = [c for c in fin_conversations 
                  if not any(phrase in c.get('full_text', '').lower() 
                            for phrase in escalation_phrases)]
resolution_rate = len(resolved_by_fin) / total

# LLM insights
prompt = f"""
Fin AI Metrics:
- Resolution rate: {resolution_rate:.1%}
- Knowledge gaps: {knowledge_gaps}

Provide nuanced performance insights (150 words, professional tone)
"""

llm_insights = await self.openai_client.generate_analysis(prompt)
```

**What Works:**
- ✅ Calculates resolution rate
- ✅ Identifies knowledge gaps
- ✅ LLM generates insights

**What's Broken:**
- ❌ Small sample sizes (6 Fin conversations) lead to 100% rates
- ❌ LLM insights may not appear in final output
- ❌ No validation of Fin detection accuracy

---

#### TrendAgent
**Purpose:** Week-over-week trend analysis with LLM explanations

**Code:**
```python
# Load historical data
historical = []
for file in self.historical_dir.glob("week_*.json"):
    historical.append(json.load(file))

if not historical:
    return {'note': 'First analysis - establishing baseline'}

# Calculate trends
previous = historical[-1]['results']
for topic, current_stats in current_topics.items():
    pct_change = ((current_vol - previous_vol) / previous_vol) * 100
    
    # LLM explains WHY
    if abs(pct_change) > 10:
        explanation = await llm.generate(f"Explain why {topic} changed {pct_change}%")
```

**What Works:**
- ✅ Saves weekly data for future comparison
- ✅ Calculates percentage changes

**What's Broken:**
- ❌ First run = no trends (expected)
- ❌ LLM explanations may not integrate into cards
- ❌ Historical data saved but not shown in UI

---

#### OutputFormatterAgent
**Purpose:** Format all results into Hilary's card structure

**Code:**
```python
formatted_output = f"""### {topic_name}{trend_indicator}
**{volume} tickets / {percentage}% of weekly volume**
**Detection Method**: {method}

**Sentiment**: {sentiment_insight}

**Trend Analysis**: {trend_explanation}

**Examples**:
1. "{preview}" - [View conversation](link)
2. ...

---
"""
```

**What Works:**
- ✅ Creates Hilary's exact format
- ✅ Integrates all agent outputs

**What's Broken:**
- ❌ Examples section often shows "_No examples extracted_"
- ❌ Trend explanations may be empty
- ❌ Fin insights may not show

**Issue:** Data from other agents may be None/empty, leading to gaps in output.

---

### 5. Gamma Integration (src/main.py lines 2963-3022)

**Current Code:**
```python
if generate_gamma:
    gamma_client = GammaClient()
    
    generation_id = await gamma_client.generate_presentation(
        input_text=markdown_report,
        format="presentation",
        text_mode="preserve",
        card_split="inputTextBreaks",  # Use --- breaks
        theme_name="Night Sky",
        text_options={
            "tone": "professional, analytical",
            "audience": "executives, leadership team"
        }
    )
    
    # Poll for completion
    while attempt < 24:
        status = await gamma_client.get_generation_status(generation_id)
        if status['status'] == 'completed':
            gamma_url = status['url']
            print(f"✅ Gamma URL: {gamma_url}")
            break
```

**What Works:**
- ✅ Sends markdown directly (not through PresentationBuilder)
- ✅ Uses preserve mode
- ✅ Uses --- breaks for slides

**What's Broken:**
- ❌ Previous runs showed validation errors
- ❌ May still be using old data structure
- ❌ Polling may time out
- ❌ URL not displayed in UI (only terminal)

**Latest Issues from Logs:**
- Line 2390: "Canny API connection successful" but then what?
- Canny integration at line 2463 imports `from services.gamma_generator` (wrong path!)

---

## 🐛 Critical Bugs Identified

### Bug #1: Import Path Inconsistencies
**Location:** Multiple files
**Issue:** Mix of `from services.X` and `from src.services.X`
**Files Affected:**
- `src/services/elt_pipeline.py` - FIXED
- `src/main.py` line 2463 - `from services.gamma_generator` ❌
- Others unknown

**Fix Needed:**
```python
# WRONG:
from services.gamma_generator import GammaGenerator

# RIGHT:
from src.services.gamma_generator import GammaGenerator
```

---

### Bug #2: Examples Always "0 examples"
**Location:** `src/agents/example_extraction_agent.py` line 269
**Issue:** Timestamp conversion
**Status:** Fixed in commit but may not be deployed

**Original Code:**
```python
'created_at': conv.get('created_at').isoformat()  # Crashes if int
```

**Fixed Code:**
```python
created_at = conv.get('created_at')
if isinstance(created_at, (int, float)):
    created_at_str = datetime.fromtimestamp(created_at).isoformat()
```

**Status:** ✅ Fixed in commit 4e24f46

---

### Bug #3: LLM Topics with 0 Conversations
**Location:** `src/agents/topic_detection_agent.py` lines 203-216
**Issue:** LLM discovers topics but doesn't rescan to assign conversations

**Code:**
```python
# LLM discovers: ["Refund Request", "Subscription Cancellation"]
for topic_name in llm_topics:
    topic_distribution[topic_name] = {
        'volume': 0,  # ← ALWAYS ZERO!
        'percentage': 0,
        'detection_method': 'llm_semantic'
    }
```

**Result:** Agents waste time analyzing topics with no conversations

**Fix Needed:**
```python
# After LLM discovery, rescan conversations OR
# Skip topics with 0 conversations in orchestrator
```

---

### Bug #4: Horatio Detection Returns 0
**Location:** `src/agents/segmentation_agent.py` lines 186-196
**Issue:** Email domain patterns not found in conversation text

**Pattern:**
```python
if re.search(r'horatio|@hirehoratio\.co', text):
    return 'paid', 'horatio'
```

**Problem:** Conversations may not contain "@hirehoratio.co" in `full_text`. Need to check:
- Admin email address
- Assignee metadata
- Different conversation fields

**Log Evidence:** Always shows `'horatio': 0` despite Horatio handling tickets

---

### Bug #5: Gamma Validation Failures
**Location:** `src/services/gamma_generator.py` line 627
**Issue:** Expects `category_results` structure we're not providing

**Code:**
```python
category_results = analysis_results.get('category_results', {})
if not category_results:
    validation_errors.append("No category analysis results available")
```

**Our Data:**
```python
gamma_input = {
    'analysis_text': markdown_report,
    'conversations': conversations[:50],
    'category_results': {},  # ← We build this but may be empty
    'results': {},
    'metadata': {...}
}
```

**Status:** ✅ Should be fixed by bypassing GammaGenerator.generate_from_analysis() and calling GammaClient directly (commit 5917fa9)

---

### Bug #6: Canny Import Path
**Location:** `src/main.py` line 2463
**Issue:** Wrong import path

**Code:**
```python
from services.gamma_generator import GammaGenerator  # ❌ WRONG
```

**Should be:**
```python
from src.services.gamma_generator import GammaGenerator  # ✅ RIGHT
```

**Impact:** Canny analysis will crash when trying to generate Gamma

---

## 📋 Complete File Manifest

### Core Application Files

| File | Purpose | Status | Issues |
|------|---------|--------|--------|
| `src/main.py` | CLI entry point | ⚠️ Mostly works | Import paths, Canny |
| `deploy/railway_web.py` | Web UI HTML | ⚠️ Works | Legacy elements |
| `static/app.js` | Frontend logic | ⚠️ Works | Unused functions |
| `static/styles.css` | Styling | ✅ Works | None |

### Multi-Agent System

| Agent | Purpose | Uses LLM? | Status | Issues |
|-------|---------|-----------|--------|--------|
| SegmentationAgent | Paid/Free split | ❌ No | ⚠️ Works | Horatio detection broken |
| TopicDetectionAgent | Find topics | ✅ Yes | ⚠️ Works | Empty topic analysis |
| TopicSentimentAgent | Per-topic insights | ✅ Yes | ✅ Works | None found |
| ExampleExtractionAgent | Select examples | ✅ Yes | ⚠️ Works | Timestamp bug (fixed?) |
| FinPerformanceAgent | Fin AI analysis | ✅ Yes | ✅ Works | Small samples |
| TrendAgent | Week-over-week | ✅ Yes | ✅ Works | No historical data yet |
| OutputFormatterAgent | Hilary's cards | ❌ No | ✅ Works | None found |

### Supporting Services

| Service | Purpose | Status | Issues |
|---------|---------|--------|--------|
| ChunkedFetcher | Fetch from Intercom | ✅ Works | Date range warnings |
| GammaClient | Gamma API calls | ⚠️ Untested | May work now |
| GammaGenerator | Old generator | ⚠️ Bypassed | Not used anymore |
| CannyClient | Canny API | ❓ Unknown | Untested |
| OpenAIClient | LLM calls | ✅ Works | None |

---

## 🔥 Most Critical Issues (Priority Order)

### 1. **Examples Not Showing** (CRITICAL)
**Symptom:** Logs say "LLM selected 7 examples" but output shows "0 examples"  
**Cause:** Timestamp conversion crash OR examples_result.data structure mismatch  
**File:** `src/agents/example_extraction_agent.py:269`  
**Fix:** Already committed (4e24f46) but Railway may not have it  
**Test:** Run on Railway and check if examples appear

### 2. **Horatio Detection Broken** (HIGH)
**Symptom:** Logs show `'horatio': 0` for all runs  
**Cause:** Pattern `@hirehoratio.co` not in conversation full_text  
**File:** `src/agents/segmentation_agent.py:186-196`  
**Fix:** Check admin email field, not just text  
**Impact:** Can't do Horatio performance reviews

### 3. **Empty Topics Analyzed** (HIGH)
**Symptom:** LLM analyzes "Refund Request" with 0 conversations  
**Cause:** LLM discovers topics but doesn't assign conversations to them  
**File:** `src/agents/topic_detection_agent.py:203-216`  
**Fix:** Skip topics with volume==0 in orchestrator  
**Impact:** Wastes LLM calls, clutters output

### 4. **Gamma May Still Fail** (HIGH)
**Symptom:** Need to verify it actually generates  
**Cause:** Multiple fixes made, unsure which worked  
**File:** `src/main.py:2963-3022`  
**Fix:** Test end-to-end on Railway  
**Impact:** No presentations = no value

### 5. **Canny Import Path** (MEDIUM)
**Symptom:** Will crash when Canny + Gamma requested  
**Cause:** `from services.gamma_generator`  
**File:** `src/main.py:2463`  
**Fix:** Change to `from src.services.gamma_generator`  
**Impact:** Canny analysis with Gamma broken

---

## 🧪 Testing Strategy

### Phase 1: Test Mode (No External APIs)
```bash
test-mode --test-type topic-based --num-conversations 50
```

**Should produce:**
- Markdown report with 5 topics
- Each topic has sentiment
- Examples (if working)
- Saves to outputs/test_output.md

**Check:**
- Does it crash?
- Are examples present?
- Is sentiment nuanced?

### Phase 2: Railway Yesterday Test
```
Analysis Type: VoC: Hilary Format
Time Period: Yesterday
Output: Markdown (not Gamma yet)
```

**Should produce:**
- ~1000 conversations analyzed
- 5-7 topics detected
- Sentiment + examples per topic
- Fin section
- Saves markdown report

**Check:**
- Examples present?
- Sentiment specific?
- Report makes sense?

### Phase 3: Gamma Test
```
Analysis Type: VoC: Hilary Format
Time Period: Yesterday  
Output: Gamma Presentation
```

**Should produce:**
- Gamma URL
- Each topic card = one slide
- Professional theme

**Check:**
- URL appears in terminal?
- Slides match topics?
- Content preserved?

---

## 💡 Recommended Fixes (In Order)

### Fix #1: Import Path Consistency
**Priority:** CRITICAL  
**Effort:** 5 minutes  
**Files:** `src/main.py:2463`

```python
# Line 2463
from src.services.gamma_generator import GammaGenerator  # Fix import
```

### Fix #2: Skip Empty Topics
**Priority:** HIGH  
**Effort:** 10 minutes  
**File:** `src/agents/topic_orchestrator.py:149`

```python
for topic_name, topic_stats in topic_dist.items():
    # SKIP empty topics
    if topic_stats.get('volume', 0) == 0:
        self.logger.info(f"   Skipping {topic_name}: 0 conversations")
        continue
    
    # Process topic...
```

### Fix #3: Horatio Detection
**Priority:** HIGH  
**Effort:** 15 minutes  
**File:** `src/agents/segmentation_agent.py:186`

```python
def _classify_conversation(self, conv):
    text = conv.get('full_text', '').lower()
    
    # NEW: Check admin email from conversation parts
    admin_emails = []
    for part in conv.get('conversation_parts', {}).get('conversation_parts', []):
        if part.get('author', {}).get('type') == 'admin':
            email = part.get('author', {}).get('email', '')
            if email:
                admin_emails.append(email.lower())
    
    # Check email domains
    if any('hirehoratio.co' in email for email in admin_emails):
        return 'paid', 'horatio'
    if any('boldrimpact.com' in email for email in admin_emails):
        return 'paid', 'boldr'
    
    # ... rest of logic
```

### Fix #4: Examples Display
**Priority:** HIGH  
**Effort:** Already done (verify deployment)  
**File:** `src/agents/example_extraction_agent.py:269`  
**Status:** Fixed in commit 4e24f46, just needs Railway deployment

---

## 📦 What Actually Needs to Work

**Minimum Viable Product:**
1. ✅ UI form submits without errors
2. ✅ Topic-based analysis completes
3. ✅ Markdown report generated with topics
4. ✅ Sentiment insights are specific
5. ❌ Examples show with Intercom links ← FIX THIS
6. ❌ Gamma URL generated ← TEST THIS
7. ❌ Horatio performance works ← FIX DETECTION

**Everything Else is Nice-to-Have**

---

## 🎯 Immediate Action Plan

1. **Fix Canny import** (1 line change)
2. **Skip empty topics** (3 line change)
3. **Test on Railway** with yesterday data
4. **Verify examples appear**
5. **Verify Gamma generates**

**STOP adding features until these 5 things work.**

---

## 📄 Key Code Snippets

### Main Entry Point (src/main.py:2751-2854)

The test-mode command I just added:
```python
@cli.command(name='test-mode')
def test_mode(test_type: str, num_conversations: int):
    # Creates fake conversations
    # Runs analysis without Intercom API
    # Saves test output
```

### Topic Orchestrator Core Loop (src/agents/topic_orchestrator.py:149-187)

```python
# Process topics in parallel
async def process_topic(topic_name, topic_stats):
    sentiment = await topic_sentiment_agent.execute()
    examples = await example_extraction_agent.execute()
    return topic_name, sentiment, examples

results = await asyncio.gather(*[process_topic(...) for topic in topics])
```

### Gamma Call (src/main.py:3022-3032)

```python
generation_id = await gamma_client.generate_presentation(
    input_text=markdown_report,
    format="presentation",
    text_mode="preserve",
    card_split="inputTextBreaks",
    theme_name="Night Sky"
)
```

---

## 🏁 Summary

**You have:** A complex multi-agent system with 7 agents, LLM intelligence, parallel processing, Gamma integration, and agent performance analysis.

**Reality:** The basics don't work reliably.

**Root causes:**
1. Too many features added without testing each one
2. Import path inconsistencies
3. Assumptions about data structure
4. Edge cases not handled

**Path forward:** Fix the 3 critical bugs above, test one thing end-to-end, then iterate.


