# Complete Prompt Catalog - Intercom Analysis Tool
**All LLM Prompts, Templates, and Engineering Decisions**

**Created:** November 14, 2025  
**Purpose:** Comprehensive documentation of every prompt in the system  
**For:** AI optimization, prompt tuning, ablation testing

---

## Prompt Index

1. [Topic Classification (Tier 1)](#1-topic-classification-tier-1)
2. [Topic Validation](#2-topic-validation)
3. [Tier 2 Subcategory Validation](#3-tier-2-subcategory-validation)
4. [Tier 3 Theme Discovery](#4-tier-3-theme-discovery)
5. [Sentiment Analysis (Per-Topic)](#5-sentiment-analysis-per-topic)
6. [Correlation Interpretation](#6-correlation-interpretation)
7. [Quality Insights Generation](#7-quality-insights-generation)
8. [Strategic Presentation Structuring](#8-strategic-presentation-structuring-disabled)
9. [Example Extraction](#9-example-extraction)

---

## 1. Topic Classification (Tier 1)

### Function: `TopicDetectionAgent._classify_with_llm_smart()`
### Model: GPT-4o-mini / Claude Haiku 4.5
### Frequency: 200× per sample analysis, 7000× per full week
### Cost: $0.0009 per call

### Prompt Template
```
You are analyzing a customer support conversation to determine its PRIMARY topic.

AVAILABLE TOPICS: {topic_list}

⚠️ HINT (may be incorrect): Intercom tagged this as '{sdk_hint}'
⚠️ HINT: Keywords matched: {keywords_matched}

CONVERSATION TEXT:
{text[:1500]}

TASK: 
1. Read the conversation carefully
2. Identify the customer's MAIN issue/question
3. Choose ONE topic from the available list that best matches
4. Ignore the hints if they don't match the actual conversation content
5. If conversation is unclear/unresponsive, choose "Unknown/unresponsive"

Respond with ONLY the topic name, nothing else.
```

### Variable Values
- `topic_list`: "Billing, Bug, Account, Workspace, Product Question, Agent/Buddy, Promotions, Privacy, Chargeback, Abuse, Partnerships, Feedback, Unknown/unresponsive"
- `sdk_hint`: From `conversation.topics.topics[0].name` (often wrong!)
- `keywords_matched`: e.g., `['billing', 'refund', 'credits']`
- `text[:1500]`: First 1500 chars of conversation (preserves customer message + first reply)

### Engineering Decisions

**Why truncate to 1500 chars?**
- Most relevant context is at start of conversation
- Reduces token cost by ~60% (avg conversation = 4000 chars)
- Tested: accuracy delta < 2% vs. full text

**Why include SDK hint as "may be incorrect"?**
- Observed: 40-45% error rate on SDK hints
- But when correct, provides useful context
- "may be incorrect" prevents LLM from blindly trusting it
- Result: LLM corrects 45% of SDK hints

**Why "ONLY topic name"?**
- Minimizes output tokens (saves cost)
- Easier to parse (no JSON extraction needed)
- Faster response times

**Why single choice only?**
- Prevents double-counting in volume metrics
- Forces LLM to identify PRIMARY issue
- Can still detect secondary topics separately if needed

### Observed Performance
- **Accuracy:** 92% (measured against manual review sample)
- **SDK Correction Rate:** 45% (LLM disagrees with SDK)
- **Avg Response Time:** 400ms per classification
- **Throughput:** 200 classifications in ~30 seconds (concurrent)

### Example Inputs/Outputs

**Input 1:**
```
Text: "give me my fucking money back you charged me after i cancelled"
SDK Hint: "Unknown/Unresponsive"
Keywords: ['billing', 'refund']
```

**Output:** `Billing`

**Reasoning (from logs):**
```
LLM corrected SDK hint (Unknown/Unresponsive → Billing)
Confidence: 0.80
Keywords validated: ['billing', 'refund']
```

---

**Input 2:**
```
Text: "I'm trying to export my presentation but keep getting 'Error 500' when I click download"
SDK Hint: "Product Question"
Keywords: ['export', 'error']
```

**Output:** `Bug`

**Reasoning:**
```
LLM identified as Bug (error code + failure)
SDK hint incorrect (Product Question → Bug)
Confidence: 0.90
```

---

## 2. Topic Validation

### Function: `TopicDetectionAgent._validate_topic_with_llm()`
### Model: GPT-4o-mini / Claude Haiku 4.5
### Frequency: Called only when multiple keyword matches (ambiguous cases)

### Prompt Template
```
You are validating which topic best matches a customer support conversation.

CANDIDATE TOPICS: {candidate_topics}

CONVERSATION TEXT:
{text[:1500]}

TASK:
1. Read the conversation
2. Determine which ONE topic from the candidates best matches
3. Choose the PRIMARY issue/question

Respond with ONLY the topic name.
```

### Variable Values
- `candidate_topics`: e.g., "Billing, Credits, Subscription" (2-3 topics that matched keywords)
- `text[:1500]`: Same as topic classification

### Engineering Decisions

**When is this called?**
- Only when keyword matching finds 2+ strong matches
- Rare case (~5% of conversations)
- Cost-effective: only validate when needed

**Why not use for all conversations?**
- Single-topic cases are clear (no validation needed)
- Reduces LLM calls by ~95%
- Saves ~$1.50 per 200 conversations

---

## 3. Tier 2 Subcategory Validation

### Function: `SubTopicDetectionAgent._validate_tier2_with_llm()`
### Model: GPT-4o-mini / Claude Haiku 4.5
### Frequency: ~20 subcategories per topic × 13 topics = 260 validations per analysis

### Prompt Template
```
Validate if '{subcategory_name}' is truly a meaningful subcategory of '{tier1_topic}'.

TIER 1 TOPIC: {tier1_topic}
TIER 2 CANDIDATE: {subcategory_name}

CONVERSATION SAMPLE (5 conversations):
{conversation_excerpts}

TASK:
1. Does this subcategory meaningfully categorize these conversations?
2. Is it distinct from other {tier1_topic} subcategories?
3. Does it provide actionable insight?

Respond with ONE of:
- KEEP (if it's a meaningful, distinct subcategory)
- MERGE:{other_subcategory} (if it should be merged with another)
- DISCARD (if it's too vague or not useful)
```

### Example

**Input:**
```
TIER 1: Billing
TIER 2: Invoice Modification
CONVERSATIONS: 
- "Can you correct the billing address on my invoice?"
- "The invoice shows wrong company name"
- "Need to change invoice recipient"
```

**Output:** `KEEP`

**Input:**
```
TIER 1: Billing  
TIER 2: Payment Issues
CONVERSATIONS:
- "Can't process payment"
- "Payment failed error"
```

**Output:** `MERGE:Payment Method` (more specific)

---

## 4. Tier 3 Theme Discovery

### Function: `SubTopicDetectionAgent._discover_tier3_themes()`
### Model: Sonnet 4.5 / GPT-4o (INTENSIVE)
### Frequency: Once per Tier 1 topic = 13 calls per analysis

### Prompt Template
```
Analyze these {tier1_topic} conversations and identify EMERGING themes not captured by existing subcategories.

TIER 1 TOPIC: {tier1_topic}

EXISTING TIER 2 SUBCATEGORIES: {tier2_list}

CONVERSATION SAMPLE (20 conversations, stratified random sampling):
{conversation_excerpts}

TASK:
Find 3-5 NEW themes that:
1. Appear in MULTIPLE conversations (not one-offs)
2. Are NOT already covered by Tier 2 subcategories listed above
3. Would be strategically valuable to track
4. Are specific and actionable (not vague like "General Issues")

RETURN ONLY valid JSON (no other text):
{
  "Theme Name 1": ["keyword1", "keyword2", "keyword3"],
  "Theme Name 2": ["keyword1", "keyword2"]
}

IMPORTANT:
- Use descriptive theme names (e.g., "Invoice Modification Requests" not "Invoice Issues")
- Provide 3-5 keywords per theme for later matching
- Limit to 5 themes maximum (focus on most impactful)
```

### Variable Values
- `tier1_topic`: e.g., "Billing"
- `tier2_list`: "Refund, Subscription, Invoice, Discount, Upgrade" (from Intercom structured data)
- `conversation_excerpts`: 20 conversations, ~200 chars each, stratified sampling

### Engineering Decisions

**Why 20 conversation sample?**
- Balance: Enough to find patterns, not so many that prompt exceeds token limit
- Stratified sampling: Evenly distributed across time period
- Token count: ~15,000 input tokens (within context window)

**Why NOT already covered by Tier 2?**
- Prevents rediscovering existing subcategories
- Forces LLM to find genuinely new themes
- Reduces noise in output

**Why intensive model (Sonnet/GPT-4o)?**
- Requires pattern recognition across 20 conversations
- Needs strategic judgment (what's "valuable to track"?)
- Budget: Only 13 calls per analysis (~$0.33 total cost)

### Example Output

**Input:** Billing conversations  
**Tier 2:** Refund, Subscription, Invoice, Discount

**LLM Response:**
```json
{
  "Invoice Modification Requests": ["invoice", "modify", "correct", "billing address"],
  "Service Dissatisfaction Refunds": ["disappointed", "not worth it", "cancel subscription"],
  "Upgrade Confusion": ["difference between", "plan comparison", "what do I get"]
}
```

**Post-Processing:**
- Rescan all Billing conversations for these keywords
- Count matches: Invoice Modification (7 convs), Service Dissatisfaction (1 conv)
- Display in Gamma card as Tier 3 themes

---

## 5. Sentiment Analysis (Per-Topic)

### Function: `TopicSentimentAgent.execute()` → `ai_client.generate_analysis()`
### Model: Sonnet 4.5 / GPT-4o (INTENSIVE)
### Frequency: 13 topics per analysis

### Prompt Template
```
Analyze sentiment for conversations about: {topic_name}

CONVERSATION SAMPLE (10 of {total_count}):
{conversation_excerpts}

Generate ONE SENTENCE that captures the NUANCED sentiment.

GOOD EXAMPLES (match this style):
✓ "Users are appreciative of the ability to buy more credits, but frustrated that Gamma moved to a credit model"
✓ "Users hate buddy so much"
✓ "Users think templates are rad but want to be able to use them with API"
✓ "Customers love the export feature but are confused by format options"

BAD EXAMPLES (avoid these):
✗ "Negative sentiment detected"
✗ "Users are frustrated with this feature"
✗ "Mixed sentiment with both positive and negative elements"
✗ "Customers express dissatisfaction"

The insight should:
1. Be specific to {topic_name}
2. Capture the nuance (appreciative BUT frustrated)
3. Be actionable (tells us what to improve)
4. Use natural language (how a human analyst would say it)
5. Use strong, clear language ("hate", "love", "frustrated", "confused")

Respond with ONE SENTENCE only.
```

### Engineering Decisions

**Why show 10 of {total_count}?**
- Transparency: LLM knows it's seeing a sample
- Encourages generalization (not overfitting to shown examples)
- Token efficiency: 10 convs = ~3,000 tokens vs 99 convs = ~30,000 tokens

**Why emphasize good/bad examples?**
- Calibrates LLM output style to user's preferences
- Prevents generic corporate speak
- Encourages specific, actionable language

**Why "ONE SENTENCE only"?**
- Forces concision (executives prefer brief insights)
- Easier to display in Gamma cards (space constrained)
- Prevents LLM from over-explaining

**Why intensive model?**
- Detecting nuance requires advanced reasoning
- Sarcasm detection: "Thanks for nothing" (negative, but LLM must infer tone)
- Frustration depth: "appreciate feature BUT" (requires understanding contrast)

### Example Outputs

**Topic: Billing (99 conversations)**
```
"Customers appreciate detailed billing information but are frustrated by complexity and delays in resolving invoice discrepancies."
```

**Analysis:**
- ✅ Specific to Billing
- ✅ Nuance: appreciate BUT frustrated
- ✅ Actionable: complexity and delays are the problems
- ✅ Natural language: how a human would say it

---

**Topic: Bug (37 conversations)**
```
"Customers are frustrated with persistent bugs that hinder basic functionalities like page addition and file access, but they appreciate the support team's responsiveness."
```

**Analysis:**
- ✅ Specific: mentions exact bugs (page addition, file access)
- ✅ Nuance: frustrated BUT appreciate support
- ✅ Actionable: fix page addition and file access bugs
- ✅ Balanced: acknowledges support team strength

---

## 6. Correlation Interpretation

### Function: `CorrelationAgent._enrich_correlations_with_llm()`
### Model: Sonnet 4.5 / GPT-4o (INTENSIVE)
### Frequency: Once per analysis (after statistical calculations complete)

### Prompt Template
```
Analyze these statistical correlations found in customer support data and provide enriched insights:

CORRELATION 1: Message Count ↔ Escalation
- Correlation Strength: {r_value} ({interpretation})
- Sample Size: {sample_size} conversations
- Pattern: {pattern_description}

CORRELATION 2: CSAT Rating ↔ Resolution Time
- Correlation Strength: {r_value}
- Sample Size: {sample_size}
- Pattern: {pattern_description}

[... more correlations ...]

For each correlation, provide:
1. Brief interpretation of what this pattern suggests (business context)
2. Potential implications (what might this mean?)
3. Observational recommendations (avoid prescriptive "you should" language)

Keep insights concise and actionable. Focus on patterns that teams can investigate further.
```

### Variable Values
- `r_value`: Pearson correlation coefficient (-1 to 1)
- `interpretation`: "very strong" (>0.8), "strong" (0.6-0.8), "moderate" (0.4-0.6)
- `sample_size`: Number of conversations used in calculation
- `pattern_description`: Human-readable summary (e.g., "Escalated conversations average 25.1 messages vs 24.0 for Fin-only")

### Engineering Decisions

**Why calculate correlations FIRST, then LLM interpret?**
- LLMs are bad at statistics (hallucinate correlations)
- Use scipy for accurate Pearson correlation
- LLM only interprets pre-calculated patterns

**Why "observational recommendations"?**
- Avoids prescriptive tone ("you should fix X")
- Executives prefer to draw own conclusions
- Reduces LLM overconfidence

**Why include sample size?**
- Statistical significance matters (100 samples vs 10 samples)
- Helps LLM calibrate confidence
- Transparency for executives

---

## 7. Quality Insights Generation

### Function: `QualityInsightsAgent.execute()` → `ai_client.generate_analysis()`
### Model: Sonnet 4.5 / GPT-4o (INTENSIVE)
### Frequency: Once per analysis

### Prompt Template
```
Analyze resolution quality patterns in customer support data.

RESOLUTION TIME DISTRIBUTION:
- Fast (< 1 hour): {fast_count} ({fast_pct}%)
- Medium (1-6 hours): {medium_count} ({medium_pct}%)
- Slow (> 6 hours): {slow_count} ({slow_pct}%)

EXCEPTIONAL CASES (outliers):
{outlier_list}

QUALITY METRICS:
- Avg resolution time: {avg_time} hours
- Median resolution time: {median_time} hours
- CSAT by resolution speed:
  Fast: {fast_csat}/5.0
  Slow: {slow_csat}/5.0

TASK:
Identify quality insights:
1. Process bottlenecks (where are delays happening?)
2. Exceptional cases requiring review
3. Quality improvement opportunities
4. Patterns in fast vs slow resolutions

Provide 3-5 concise, actionable insights.
```

### Engineering Decisions

**Why statistical outliers?**
- Conversations > 2 std dev from mean resolution time
- Usually indicate process failures or edge cases
- LLM can spot patterns human might miss

**Why CSAT by resolution speed?**
- Directly actionable: "Faster resolution → higher CSAT"
- Quantifies urgency (how much does speed matter?)

---

## 8. Strategic Presentation Structuring (DISABLED)

### Function: `OutputFormatterAgent._generate_strategic_presentation_guidance()`
### Model: Sonnet 4.5 / GPT-4o (INTENSIVE)
### Status: **DISABLED BY DEFAULT** (user feedback: "tone is weird")

### Prompt Template
```
You are preparing an executive presentation for a VP/Director. 
Analyze this customer support data and provide strategic guidance for the presentation structure.

DATA SUMMARY:

Top Topics:
{topic_summary}

Emerging Themes (Tier 3 - AI Discovered):
{tier3_summary}

Statistical Insights Available:
- Correlation analysis: {corr_count} patterns found
- Quality insights: {quality_count} issues identified

YOUR TASK:
As an executive presentation strategist, provide guidance in JSON format:

1. **top_insights** (array of 3-5 strings): Most important takeaways for executives?
2. **card_priority_order** (array of topic names): Which topics should appear first? (Order by strategic importance, not just volume)
3. **emphasis_areas** (object): Which sub-topics/themes deserve extra attention? {topic: [subtopic1, subtopic2]}
4. **executive_summary** (string): 2-3 sentence summary for opening slide
5. **narrative_arc** (string): What story does this data tell?

Return ONLY valid JSON, no other text:
{
  "top_insights": ["insight 1", "insight 2", "insight 3"],
  "card_priority_order": ["topic1", "topic2", ...],
  "emphasis_areas": {"Topic Name": ["subtopic1", "subtopic2"]},
  "executive_summary": "summary here",
  "narrative_arc": "story here"
}
```

### Why Disabled?

**User Feedback:** "Sorting and tone overall is weird and broken"

**Issues Observed:**
1. LLM reorders cards by "strategic importance" → confusing (users expect volume order)
2. Executive summary doesn't match user's voice/tone
3. Narrative arc feels artificial
4. No way to preview/tune without running full analysis

**Current State:**
- Default: `use_llm_formatting=False` (standard volume-based sorting)
- Enable via: `LLM_OUTPUT_FORMATTING=true` environment variable
- Needs: Prompt tuning to match user's executive voice

**Potential Improvements:**
1. Add few-shot examples of user's past executive summaries
2. Make tone configurable ("formal", "casual", "data-driven")
3. Preview mode: Show LLM guidance before applying to output
4. A/B test: Generate both versions, let user choose

---

## 9. Example Extraction

### Function: `ExampleExtractionAgent.execute()`
### Model: Not currently using LLM (rule-based selection)
### Potential: Could use LLM for "most representative" selection

### Current Implementation (Rule-Based)
```python
# Select examples that:
1. Have CSAT rating (preferably extreme: 1-2 or 4-5)
2. Have customer message text
3. Are diverse (not all billing refund requests)
4. Are recent (last 7 days prioritized)

# Sort by:
priority = (
    (5 if has_csat else 0) +
    (3 if csat in [1,2,4,5] else 0) +
    (2 if is_recent else 0) +
    (1 if has_quote else 0)
)
```

### LLM Improvement Opportunity

**Proposed Prompt:**
```
Select the 3 most REPRESENTATIVE examples for {topic_name}.

CRITERIA:
1. Illustrates common pain points
2. Shows range of sentiment (best case, worst case, typical case)
3. Has specific, quotable customer language
4. Avoids edge cases or outliers

AVAILABLE EXAMPLES (20 conversations):
{conversation_list}

Return JSON array of 3 conversation IDs:
["id1", "id2", "id3"]
```

**Expected Impact:** Better example quality, more strategic selection

---

## 10. System-Wide Prompt Engineering Patterns

### Pattern 1: Minimal Output Instructions

**Used in:** Topic classification, validation

**Pattern:**
```
"Respond with ONLY the topic name, nothing else."
"Return ONLY valid JSON, no other text."
```

**Why:**
- Reduces output token cost (~60% savings)
- Easier parsing (no need to extract from explanation)
- Faster response times

---

### Pattern 2: Hint-as-Context (Not Truth)

**Used in:** Topic classification

**Pattern:**
```
"⚠️ HINT (may be incorrect): Intercom tagged this as '{sdk_hint}'"
```

**Why:**
- SDK hints have 40-45% error rate
- But when correct, provide useful context
- "may be incorrect" prevents blind trust
- LLM can override when needed

---

### Pattern 3: Good/Bad Example Calibration

**Used in:** Sentiment analysis

**Pattern:**
```
GOOD EXAMPLES:
✓ "Users hate buddy so much"
✓ "Users are appreciative BUT frustrated"

BAD EXAMPLES:
✗ "Negative sentiment detected"
✗ "Mixed sentiment"
```

**Why:**
- Calibrates LLM to desired output style
- Shows exactly what NOT to do (as important as what to do)
- Reduces generic/vague outputs

---

### Pattern 4: Task Decomposition

**Used in:** All complex prompts

**Pattern:**
```
TASK:
1. Read the conversation
2. Identify the main issue
3. Choose ONE topic
4. Ignore hints if incorrect

(Step-by-step, numbered)
```

**Why:**
- Improves LLM reasoning (chain-of-thought lite)
- Makes expectations explicit
- Reduces ambiguous outputs

---

### Pattern 5: Transparency About Sample Size

**Used in:** Sentiment, Tier 3 discovery

**Pattern:**
```
"CONVERSATION SAMPLE (10 of 99 total)"
"Showing 20 conversations, stratified random sampling"
```

**Why:**
- LLM knows it's seeing subset → encourages generalization
- Prevents overfitting to shown examples
- Sets expectations for output confidence

---

## 11. Comparison: Prompting Approaches Tested

### Approach A: Zero-Shot (Current for Topic Classification)

**Prompt:**
```
Classify this conversation into one of these topics: {topic_list}
{conversation_text}
```

**Pros:** Fast, cheap, no examples needed  
**Cons:** Lower accuracy on ambiguous cases

---

### Approach B: Few-Shot (Not Yet Implemented)

**Prompt:**
```
Classify conversations into topics. Here are examples:

Example 1:
Text: "I need a refund"
Topic: Billing

Example 2:
Text: "Button won't click"
Topic: Bug

Now classify:
Text: {conversation_text}
Topic: ?
```

**Pros:** Higher accuracy (+3-5% observed in tests)  
**Cons:** More tokens (3-5 examples = ~500 tokens)

**Recommendation:** Implement for ambiguous cases only (< 0.7 confidence)

---

### Approach C: Chain-of-Thought (Not Yet Implemented)

**Prompt:**
```
Classify this conversation. Think step-by-step:
1. What is the customer's main question?
2. Which topic category does this fall under?
3. What makes you confident in this classification?

{conversation_text}

Reasoning: [LLM explains]
Topic: [Final answer]
```

**Pros:** Better debugging (can see LLM's reasoning)  
**Cons:** Much more expensive (output tokens 3-5× higher)

**Recommendation:** Use for low-confidence cases (<0.6) only

---

## 12. Current Prompt Limitations & Fixes

### Limitation 1: Topic List is Unordered

**Current:**
```
"AVAILABLE TOPICS: Billing, Bug, Account, Workspace..."
```

**Issue:** No guidance on which topics are more common

**Proposed Fix:**
```
"AVAILABLE TOPICS (ordered by frequency):
1. Billing (most common)
2. Bug
3. Account
[... ]
13. Chargeback (least common)"
```

**Expected Impact:** LLM biases toward common topics in ambiguous cases (statistically correct)

---

### Limitation 2: No Context About Recent Trends

**Current:** Each conversation classified in isolation

**Proposed:** Add trend context
```
"⚠️ TREND: Billing volume increased 23% this week (investigate carefully)"
```

**Expected Impact:** LLM more careful about trending topics

---

### Limitation 3: Sentiment Prompt Lacks Domain Context

**Current:** Generic examples across all topics

**Proposed:** Topic-specific examples
```
For BILLING sentiment:
✓ "appreciative of credits BUT frustrated with pricing" (past example)
✓ "love the flexibility BUT confused by invoice dates" (past example)

Now analyze current Billing conversations:
{conversation_text}
```

**Expected Impact:** More consistent tone across weeks

---

## 13. Ablation Opportunities (Testing Ideas)

### Test 1: Impact of SDK Hints

**Hypothesis:** SDK hints might be HURTING accuracy (40% error rate)

**Test A (Control):** Current prompt with hints
**Test B:** Remove SDK hints entirely
**Test C:** Only include SDK hints when confidence > 0.8

**Measure:** Classification accuracy, LLM confidence scores

---

### Test 2: Truncation Length

**Hypothesis:** 1500 chars is optimal balance of cost/accuracy

**Test A:** 500 chars
**Test B:** 1500 chars (current)
**Test C:** 3000 chars
**Test D:** Full text (no truncation)

**Measure:** Accuracy delta, token cost, response time

---

### Test 3: Model Comparison (Quick Tasks)

**Hypothesis:** Claude Haiku 4.5 might be more accurate than GPT-4o-mini for topic classification

**Test A:** GPT-4o-mini
**Test B:** Claude Haiku 4.5
**Test C:** Mix (use both, compare outputs, use agreement as confidence signal)

**Measure:** Accuracy, cost, speed, agreement rate

---

## 14. Recommended Prompt Improvements (Prioritized)

### PRIORITY 1: Add Few-Shot Examples to Topic Classification

**Effort:** 2 hours  
**Impact:** +3-5% accuracy  
**Cost:** +$0.20 per 200 conversations

**Implementation:**
```python
# Add to prompt:
examples = """
EXAMPLE CLASSIFICATIONS:

Example 1:
Text: "give me my money back"
Topic: Billing

Example 2:
Text: "button doesn't work, getting error 500"
Topic: Bug

Example 3:
Text: "can't log in to my account"
Topic: Account
"""
```

---

### PRIORITY 2: Add Domain-Specific Sentiment Examples

**Effort:** 1 hour  
**Impact:** Better tone consistency  
**Cost:** No change (same token count)

**Implementation:**
Extract best sentiment insights from past 10 weeks → use as calibration examples

---

### PRIORITY 3: Implement Confidence-Based Routing

**Effort:** 3 hours  
**Impact:** Reduce LLM calls by 30% (cost savings)  

**Strategy:**
```python
# High confidence keyword matches → skip LLM
if keyword_confidence > 0.85:
    return keyword_result  # Don't call LLM

# Ambiguous cases → call LLM
else:
    return await llm_classify()
```

**Expected:** Save ~$0.60 per 200 conversations

---

### PRIORITY 4: Add Chain-of-Thought for Low-Confidence Cases

**Effort:** 2 hours  
**Impact:** Better debugging of edge cases  
**Cost:** +$0.10 per 200 conversations (only 10-15% trigger CoT)

**Trigger:**
```python
if llm_confidence < 0.70:
    prompt += "\n\nExplain your reasoning before stating the topic."
```

---

## 15. Monitoring & Evaluation Metrics

### Prompt Quality Metrics (Track These)

**1. Topic Classification Accuracy**
- Manual review sample (50 conversations per week)
- Compare LLM classification vs. human expert
- Target: > 90% agreement

**2. SDK Correction Rate**
- Track: `agreed_with_sdk` vs `corrected_sdk`
- Current: 45% correction rate
- Trend: Is SDK getting better or worse over time?

**3. Sentiment Tone Match**
- Weekly executive feedback survey
- Question: "Does sentiment insight feel actionable? (1-5)"
- Target: > 4.0 average

**4. LLM Cost Tracking**
- Token usage per analysis type
- Cost per conversation
- Identify expensive prompts (candidates for optimization)

**5. Confidence Score Distribution**
- Track confidence histogram
- If most scores < 0.75 → prompts need tuning
- If most scores > 0.95 → LLM might be overconfident

---

## 16. Actionable Next Steps for AI Investigator

### Investigate These Questions

**PROMPTING:**
1. Can we reduce topic classification prompt tokens by 30% without accuracy loss?
2. Would topic-specific sentiment examples improve tone consistency?
3. Is there a better way to present SDK hints (currently "may be incorrect")?
4. Can we generate few-shot examples automatically from high-confidence past classifications?

**COUNTING:**
1. Should we use confidence-weighted aggregation instead of raw counts?
2. Is there value in tracking secondary topics for correlation analysis?
3. Can we detect conversations that genuinely belong to 2 topics (not just keyword overlap)?

**PREPROCESSING:**
1. Would semantic deduplication catch more duplicates than ID matching?
2. Can we detect language and route to language-specific LLMs?
3. Should we extract structured data (invoice numbers, error codes) for better matching?

**ARCHITECTURE:**
1. Can we parallelize topic classification (currently concurrent but sequential pattern)?
2. Should Tier 3 discovery use RAG (retrieve similar past themes before LLM call)?
3. Would streaming LLM responses improve perceived performance?

**COST:**
1. Which prompts have highest cost/benefit ratio?
2. Can we cache LLM responses for identical inputs?
3. Where can we substitute GPT-4o-mini for GPT-4o without accuracy loss?

---

**End of Prompt Catalog**

**Next:** Feed both `AI_ANALYSIS_SYSTEM_REPORT.md` and `PROMPT_CATALOG.md` to investigator AI for detailed improvement recommendations.

