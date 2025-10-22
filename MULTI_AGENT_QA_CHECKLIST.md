# Multi-Agent Branch QA Checklist

**Branch:** `feature/multi-agent-implementation`  
**Last Updated:** October 22, 2025  
**Status:** Ready for Railway Testing

---

## ✅ What Should Work

### **Web UI Dropdown Options:**

1. **Voice of Customer**
   - ✅ VoC: Hilary Format (Topic Cards) - DEFAULT
   - ✅ VoC: Synthesis (Cross-cutting Insights)
   - ✅ VoC: Complete (Both Formats)

2. **Category Deep Dives**
   - ✅ Billing Analysis
   - ✅ Product Feedback  
   - ✅ API Issues & Integration
   - ✅ Escalations
   - ✅ Technical Troubleshooting

3. **Combined Analysis**
   - ✅ All Categories

4. **Agent Performance**
   - ✅ Horatio Performance Review
   - ✅ Boldr Performance Review

5. **Other Sources**
   - ✅ Canny Feedback

### **Time Period Options:**
- ✅ Yesterday (fast - ~1k conversations)
- ✅ Last Week (~7k conversations)
- ✅ Last Month (full analysis)
- ✅ Custom Date Range

### **Data Sources:**
- ✅ Intercom Only
- ✅ Canny Only
- ✅ Both Sources

### **Taxonomy Filtering:**
All 13 categories available:
- ✅ Billing
- ✅ Bug Reports
- ✅ Product Questions
- ✅ Account Issues
- ✅ Feedback
- ✅ Agent/Buddy
- ✅ Workspace/Team
- ✅ Privacy/Security
- ✅ Chargebacks
- ✅ Partnerships
- ✅ Promotions
- ✅ Abuse Reports
- ✅ Unclassified

### **Output Formats:**
- ✅ Markdown Report
- ✅ Gamma Presentation

---

## 🧪 Critical Test Cases

### **Test 1: Basic VoC Analysis (Hilary Format)**

**Command:**
```
Analysis Type: VoC: Hilary Format
Time Period: Yesterday
Data Source: Intercom Only
Output: Markdown
```

**Expected Output:**
```markdown
# Voice of Customer Analysis - Week 2025-WXX

## Customer Topics (Paid Tier - Human Support)

### Billing
**204 tickets / 20% of weekly volume**
**Detection Method**: Intercom conversation attribute

**Sentiment**: Customers frustrated with unexpected charges BUT appreciate prompt refund process

**Examples**:
1. "I want a refund..." - [View conversation](link)
2. "Why was I charged..." - [View conversation](link)
...

## Fin AI Performance

### Fin AI Analysis
**159 conversations handled by Fin**
...
```

**Verify:**
- [ ] Report generated in `outputs/topic_based_*.md`
- [ ] Topics detected correctly
- [ ] Sentiment insights are nuanced (not generic)
- [ ] Examples have Intercom links
- [ ] Fin section present
- [ ] Paid/Free properly separated

---

### **Test 2: Gamma Presentation Generation**

**Command:**
```
Analysis Type: VoC: Hilary Format
Time Period: Yesterday
Output: Gamma Presentation
```

**Expected:**
```
✅ Topic-based analysis complete
📁 Report: outputs/topic_based_*.md
🎨 Generating Gamma presentation...
   Sending XXXX characters to Gamma API...
   Generation ID: xxxxxxxxxx
   Waiting for Gamma to process...
   Still processing... (1/24)
   ...
✅ Gamma URL: https://gamma.app/docs/xxxxx
📁 URL saved to: outputs/gamma_url_*.txt
```

**Verify:**
- [ ] Gamma URL is generated
- [ ] URL file saved
- [ ] Gamma presentation has topic cards as slides
- [ ] Each `---` break creates new slide
- [ ] Night Sky theme applied
- [ ] Text preserved (not rewritten by Gamma)

---

### **Test 3: LLM Agent Functionality**

**Agents That Should Use LLMs:**

1. **TopicDetectionAgent**
   - [ ] Discovers semantic topics beyond keywords
   - [ ] Example: "Subscription Cancellation", "Refund Request"
   - [ ] Log shows: "LLM discovered X additional topics"

2. **TopicSentimentAgent** (per topic)
   - [ ] Generates specific, nuanced insights
   - [ ] NOT generic: "negative sentiment"
   - [ ] YES specific: "Customers frustrated with X BUT appreciate Y"
   - [ ] Example count matches log

3. **ExampleExtractionAgent** (per topic)
   - [ ] LLM selects most representative examples
   - [ ] Log shows: "LLM selected 7 examples: [1, 3, 5...]"
   - [ ] Examples appear in output
   - [ ] No timestamp errors

4. **FinPerformanceAgent**
   - [ ] Generates nuanced performance insights
   - [ ] Explains patterns in Fin's performance
   - [ ] Insights appear in Fin section

5. **TrendAgent**
   - [ ] Explains WHY trends are happening (if historical data exists)
   - [ ] Example: "Volume up 23% likely due to..."
   - [ ] Only for significant changes (>10%)

---

### **Test 4: Parallel Processing**

**What to Check:**
- [ ] Log shows: "Processing 7 topics in parallel..."
- [ ] Topics process simultaneously (not one-by-one)
- [ ] Time for 7 topics should be ~5-10 seconds total (not 35-70 seconds)

---

### **Test 5: API-Only Analysis**

**Command:**
```
Analysis Type: API Issues & Integration
Time Period: Yesterday
Output: Gamma
```

**Expected:**
- [ ] Only API-tagged conversations analyzed
- [ ] Authentication issues
- [ ] Integration problems
- [ ] Webhook debugging
- [ ] Gamma presentation generated

---

### **Test 6: Horatio Performance Review**

**Command:**
```
Analysis Type: Horatio Performance Review
Time Period: 6-weeks
Output: Gamma
```

**Expected:**
- [ ] Only Horatio-handled conversations (hirehoratio.co pattern)
- [ ] FCR rate calculated
- [ ] Resolution time benchmarks
- [ ] Escalation patterns
- [ ] LLM insights about strengths/development areas
- [ ] Actionable recommendations

---

## ❌ Known Issues to Fix

### **Critical**
1. **Examples still showing "0 examples"** in some runs
   - Timestamp conversion issues
   - LLM selection sometimes returns empty

2. **Import path inconsistencies**
   - Some files use `from services.X` (breaks)
   - Some files use `from src.services.X` (works)
   - Need systematic fix across all files

3. **Empty topic analysis**
   - LLM-discovered topics with 0 conversations waste API calls
   - Should skip topics with 0 conversations

### **Medium**
4. **Date range warnings**
   - "API returned conversations outside requested range"
   - Intercom API timezone issues

5. **Gamma validation**
   - Still using old validation checks for category_results
   - Should update or bypass for new structure

### **Low**
6. **Generic sentiment warnings**
   - Some insights still trigger "generic sentiment" warnings
   - Need to refine prompts or validation

---

## 🎯 Testing Priority

**Do in this order:**

1. **Railway UI Test** - Select options, click Run, verify it doesn't crash
2. **Gamma Generation** - Verify URL is generated and slides are correct
3. **Report Quality** - Check if insights are actually nuanced and useful
4. **API Analysis** - Test API-only filtering works
5. **Horatio Performance** - Test agent performance review

**Don't test:**
- Local execution (import issues)
- Unit tests (not worth it until Railway works)
- Edge cases (fix core functionality first)

---

## 📊 Success Criteria

### **Minimum Viable:**
- [ ] Can select analysis from dropdown without errors
- [ ] Analysis completes and shows results
- [ ] Markdown report is generated
- [ ] Report has topic cards with sentiment + examples

### **Full Success:**
- [ ] Gamma URL generated successfully
- [ ] Gamma presentation shows topic cards as slides
- [ ] Sentiment insights are specific and nuanced
- [ ] Examples have working Intercom links
- [ ] LLM agents provide intelligent analysis
- [ ] Parallel processing is fast

---

## 🚨 If Things Break

**Most Likely Failure Points:**

1. **Gamma API fails** → Check error message, verify API key
2. **No examples extracted** → Check timestamp handling
3. **Generic insights** → Check prompts aren't too restrictive
4. **Slow/timeout** → Verify parallelization working

**Quick Fixes:**
- Set output to Markdown only (skip Gamma for debugging)
- Use "Yesterday" time period (small dataset)
- Check Railway logs for actual error messages

---

## 📝 Current State Summary

**What's Implemented:**
- 7-agent topic-based workflow
- LLM intelligence in 5 agents
- Parallel topic processing
- Gamma API v0.2 integration
- Horatio/Boldr performance analysis
- API-focused analysis
- Complete UI with all options

**What's Tested:**
- Nothing comprehensively (local import issues)
- Partial Railway runs showing some success

**Next Step:**
Test ONE thing end-to-end on Railway and fix whatever breaks before adding anything else.

