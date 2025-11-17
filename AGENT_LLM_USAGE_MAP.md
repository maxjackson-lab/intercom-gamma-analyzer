# Agent LLM Usage Map - Voice of Customer Analysis
**Which agents use LLM and which don't**

---

## VOC Analysis Agent Execution Flow (12 Total Agents)

### **PHASE 1: Segmentation**

**1. SegmentationAgent** - Paid vs Free classification
- **LLM:** ❌ NO (purely rule-based)
- **Method:** Checks `custom_attributes['tier']` field + admin assignment
- **Speed:** <1 second for 800 conversations
- **Cost:** $0
- **Tested:** ✅ Yes (working correctly)
- **Purpose:** Separate paid customers (get human support) from free (Fin-only)

---

### **PHASE 2: Topic Detection**

**2. TopicDetectionAgent** - Topic classification (Billing, Account, Bug, etc.)
- **LLM:** ⚡ **OPTIONAL** (controlled by `--llm-topic-detection` flag)
- **Default:** ✅ ENABLED (hybrid mode)
- **Method:** 
  - Try keywords first (fast, free)
  - If no keyword match → LLM fallback (accurate but costs money)
- **Speed (with new multilingual keywords):**
  - ~70% matched by keywords (instant)
  - ~30% need LLM (~20-25 min for 1000 convs)
- **Cost:** ~$2 per 1000 conversations (was $5)
- **Tested:** ✅ Yes (1000 conversation validation complete)
- **Status:** ✅ WORKING (just improved with multilingual keywords!)

---

### **PHASE 3: Subtopic Detection**

**3. SubTopicDetectionAgent** - 3-tier hierarchy (Tier 1 → Tier 2 → Tier 3)
- **LLM:** ⚡ **PARTIAL** (only for Tier 3 theme discovery)
- **Method:**
  - **Tier 2:** Rule-based keyword patterns (fast, $0)
  - **Tier 3:** LLM discovers emerging themes (costs money)
- **Speed:** ~60-90 seconds (with concurrent processing)
- **Cost:** ~$0.50 per analysis
- **Tested:** ⚠️ NOT recently validated (last test: Nov 4)
- **Status:** ⚠️ UNKNOWN (need to test)

---

### **PHASE 4: Per-Topic Analysis (Parallel)**

**4. TopicSentimentAgent** - Sentiment per topic
- **LLM:** ✅ YES (always)
- **Method:** GPT-4o-mini analyzes sentiment for each topic
- **Runs:** Once per detected topic (~8-12 times)
- **Speed:** ~30-45 seconds total
- **Cost:** ~$0.20 per analysis
- **Tested:** ⚠️ NOT recently validated
- **Status:** ⚠️ UNKNOWN (need to test)

**5. ExampleExtractionAgent** - Extract example conversations
- **LLM:** ❌ NO (rule-based selection)
- **Method:** Selects conversations based on:
  - Recency (newer preferred)
  - Sentiment diversity (mix of positive/negative)
  - Text length (readable examples)
  - Rating presence
- **Speed:** <1 second
- **Cost:** $0
- **Tested:** ✅ Yes (working correctly)
- **Status:** ✅ WORKING

---

### **PHASE 5: Fin Performance Analysis**

**6. FinPerformanceAgent** - Fin AI metrics
- **LLM:** ❌ NO (purely statistical)
- **Method:** Calculates:
  - Deflection rate (Fin resolved / total Fin participated)
  - Resolution breakdown (Assumed, Confirmed, Routed)
  - Per-topic Fin performance
- **Speed:** <1 second
- **Cost:** $0
- **Tested:** ✅ Yes (fixed Nov 12 - dual metrics working)
- **Status:** ✅ WORKING

---

### **PHASE 6: Analytical Insights (Parallel - 4 agents)**

**7. CorrelationAgent** - Cross-topic pattern detection
- **LLM:** ✅ YES (Claude Sonnet 4.5 for strategic reasoning)
- **Method:** Analyzes topic co-occurrence, sentiment correlations
- **Speed:** ~20-30 seconds
- **Cost:** ~$0.30 per analysis
- **Tested:** ⚠️ NOT recently validated
- **Status:** ⚠️ UNKNOWN (need to test)

**8. QualityInsightsAgent** - Strategic quality insights
- **LLM:** ✅ YES (Claude Sonnet 4.5 for strategic analysis)
- **Method:** Identifies systemic issues, root causes, patterns
- **Speed:** ~20-30 seconds
- **Cost:** ~$0.30 per analysis
- **Tested:** ⚠️ NOT recently validated
- **Status:** ⚠️ UNKNOWN (need to test)

**9. ChurnRiskAgent** - Churn risk detection
- **LLM:** ✅ YES (GPT-4o for pattern analysis)
- **Method:** Detects churn signals (refund requests, cancellations, frustration)
- **Speed:** ~15-20 seconds
- **Cost:** ~$0.15 per analysis
- **Tested:** ⚠️ NOT recently validated
- **Status:** ⚠️ UNKNOWN (need to test)

**10. ConfidenceMetaAgent** - Data confidence scoring
- **LLM:** ❌ NO (statistical analysis)
- **Method:** Calculates confidence based on:
  - Sample size
  - Weeks of historical data
  - Detection method reliability
- **Speed:** <1 second
- **Cost:** $0
- **Tested:** ⚠️ NOT recently validated
- **Status:** ⚠️ UNKNOWN (need to test)

---

### **PHASE 7: Trend Analysis (Optional)**

**11. TrendAgent** - Week-over-week trends
- **LLM:** ❌ NO (statistical comparison)
- **Method:** Compares current week to historical average
- **Speed:** ~1-2 seconds
- **Cost:** $0
- **Tested:** ⚠️ NOT recently validated (requires 3+ weeks data)
- **Status:** ⚠️ UNKNOWN (need historical data)

---

### **PHASE 8: Output Formatting**

**12. OutputFormatterAgent** - Format for Gamma
- **LLM:** ❌ NO (template-based formatting)
- **Method:** Converts agent outputs to markdown structure
- **Speed:** <1 second
- **Cost:** $0
- **Tested:** ⚠️ UNKNOWN (may have data loss issues)
- **Status:** ⚠️ NEEDS INVESTIGATION (user reported empty topics in Gamma)

---

## Summary: LLM Usage

### **Agents Using LLM:**
1. ✅ TopicDetectionAgent (optional - hybrid mode)
2. ✅ SubTopicDetectionAgent (Tier 3 only)
3. ✅ TopicSentimentAgent (always)
4. ✅ CorrelationAgent (always)
5. ✅ QualityInsightsAgent (always)
6. ✅ ChurnRiskAgent (always)

**Total LLM agents:** 6 out of 12 (50%)

### **Agents WITHOUT LLM:**
1. ❌ SegmentationAgent (rule-based)
2. ❌ ExampleExtractionAgent (rule-based)
3. ❌ FinPerformanceAgent (statistical)
4. ❌ ConfidenceMetaAgent (statistical)
5. ❌ TrendAgent (statistical)
6. ❌ OutputFormatterAgent (template-based)

**Total non-LLM agents:** 6 out of 12 (50%)

---

## Testing Status

### ✅ **TESTED & WORKING:**
- SegmentationAgent (Nov 15 - 803 conversations, 100% success)
- TopicDetectionAgent (Nov 17 - 1000 conversations, keywords working)
- ExampleExtractionAgent (Nov 12 - working correctly)
- FinPerformanceAgent (Nov 12 - dual metrics fixed)

### ⚠️ **NOT RECENTLY TESTED:**
- SubTopicDetectionAgent (last: Nov 4)
- TopicSentimentAgent (last: Nov 4)
- CorrelationAgent (never tested in isolation)
- QualityInsightsAgent (never tested in isolation)
- ChurnRiskAgent (never tested in isolation)
- ConfidenceMetaAgent (never tested in isolation)
- TrendAgent (requires 3+ weeks historical data)
- OutputFormatterAgent (likely has bugs - user reported empty Gamma output)

---

## Cost Breakdown (1000 conversations)

### **With LLM Hybrid Mode (Current Default):**
```
TopicDetectionAgent:    ~$2.00  (300 LLM calls)
SubTopicDetectionAgent: ~$0.50  (Tier 3 discovery)
TopicSentimentAgent:    ~$0.20  (8-12 topic analyses)
CorrelationAgent:       ~$0.30  (1 strategic analysis)
QualityInsightsAgent:   ~$0.30  (1 strategic analysis)
ChurnRiskAgent:         ~$0.15  (1 pattern analysis)
──────────────────────────────────────────
TOTAL:                  ~$3.45 per 1000 conversations
```

### **With Keywords Only (LLM disabled):**
```
TopicDetectionAgent:    $0      (keyword-only)
SubTopicDetectionAgent: ~$0.50  (Tier 3 still uses LLM)
TopicSentimentAgent:    ~$0.20  (still runs)
CorrelationAgent:       ~$0.30  (still runs)
QualityInsightsAgent:   ~$0.30  (still runs)
ChurnRiskAgent:         ~$0.15  (still runs)
──────────────────────────────────────────
TOTAL:                  ~$1.45 per 1000 conversations
```

**Savings:** ~$2 per 1000 by disabling TopicDetectionAgent LLM

---

## Speed Breakdown (1000 conversations)

### **With LLM Hybrid Mode:**
```
SegmentationAgent:          ~1 second
TopicDetectionAgent:        ~20-25 minutes  (300 LLM calls)
SubTopicDetectionAgent:     ~60-90 seconds  (concurrent Tier 3)
Per-Topic Analysis:         ~2-3 minutes    (sentiment + examples for 8-12 topics)
Analytical Insights:        ~1-2 minutes    (4 agents in parallel)
FinPerformanceAgent:        ~1 second
OutputFormatterAgent:       ~1 second
──────────────────────────────────────────
TOTAL:                      ~25-30 minutes
```

### **With Keywords Only:**
```
SegmentationAgent:          ~1 second
TopicDetectionAgent:        ~2-3 minutes    (keyword matching only)
SubTopicDetectionAgent:     ~60-90 seconds
Per-Topic Analysis:         ~2-3 minutes
Analytical Insights:        ~1-2 minutes
FinPerformanceAgent:        ~1 second
OutputFormatterAgent:       ~1 second
──────────────────────────────────────────
TOTAL:                      ~7-10 minutes
```

**Speedup:** 3× faster with keywords only

---

## Recommendations

### **For YOUR Use Case (Weekly analysis, 7000 conversations):**

**Option A: Keep Hybrid Mode (Current Default)**
- ✅ High accuracy (95%+)
- ✅ Catches edge cases
- ⏱️ Time: ~3 hours per week
- 💰 Cost: ~$24 per week ($100/month)

**Option B: Keywords Only**
- ✅ Fast (1-1.5 hours per week)
- ✅ Cheap (~$10 per week, $40/month)
- ⚠️ Lower accuracy (~70%)
- ⚠️ 30% marked as "Unknown"

### **Testing Priority:**

Before next production run, TEST these agents:
1. **SubTopicDetectionAgent** (Tier 3 discovery)
2. **TopicSentimentAgent** (per-topic sentiment)
3. **CorrelationAgent** (cross-topic patterns)
4. **QualityInsightsAgent** (strategic insights)
5. **OutputFormatterAgent** (data → Gamma formatting)

**Use sample-mode to test each:**
```bash
python src/main.py sample-mode --count 200 --test-all-agents --save-to-file
```

This will run ALL agents and show if any are broken.

---

## Critical Question

**You mentioned "empty topics in Gamma" - which agents are ACTUALLY failing?**

Based on your logs, I suspect:
- ✅ TopicDetectionAgent IS working (detects topics)
- ❌ OutputFormatterAgent MIGHT be broken (data loss during formatting)
- ❌ OR Gamma API call might be failing

**Should we test OutputFormatterAgent next to see if it's properly passing topic data?**

