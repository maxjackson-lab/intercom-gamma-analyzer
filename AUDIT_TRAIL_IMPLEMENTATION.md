# Audit Trail System - "Show Your Work" Mode

## 🎯 **Purpose**

> "I'm insecure since I vibecoded all of this, can we have extra verbose tool that shows as much detail as possible and sort of narrates the whole process so a data engineer can audit it"

**Perfect solution:** Audit Trail System that narrates every step in plain language!

---

## 📋 **What It Does**

Creates a **human-readable narrative** of the entire analysis:

1. **What data was fetched** and from where
2. **What decisions were made** and why
3. **What transformations were applied** to the data
4. **What metrics were calculated** and how
5. **What AI calls were made** and what they returned
6. **What quality checks passed/failed**
7. **What warnings were encountered** and how they were handled

---

## 📊 **Example Audit Report**

```markdown
# Analysis Audit Trail

**Generated:** 2025-10-25 21:45:32
**Total Duration:** 342.5 seconds
**Total Steps:** 47
**Decisions Made:** 12
**Warnings:** 3

---

## 📊 Executive Summary

**Phases Completed:**
- Data Fetching: 8 steps
- Data Preprocessing: 6 steps
- Segmentation: 5 steps
- Topic Detection: 12 steps
- Sentiment Analysis: 8 steps
- Example Extraction: 5 steps
- Output Formatting: 3 steps

---

## ✅ Data Quality Checks

### ✅ PASSED Conversation Count Validation
**When:** 2025-10-25 21:05:50

**Results:**
- Total conversations fetched: 5,286
- Valid conversations after preprocessing: 5,286
- Duplicate conversations removed: 420
- Invalid/corrupted conversations: 0
- Data quality score: 100%

### ✅ PASSED Date Range Validation
**When:** 2025-10-25 21:05:49

**Results:**
- Requested start: 2025-10-18
- Requested end: 2025-10-25
- Actual start: 2025-10-18
- Actual end: 2025-10-25
- Missing days: 0
- Coverage: 100%

### ⚠️ WARNING CSAT Data Coverage
**When:** 2025-10-25 21:08:15

**Results:**
- Total conversations: 5,286
- Conversations with CSAT ratings: 1,057 (20%)
- Conversations without ratings: 4,229 (80%)
- Note: This is normal - not all customers rate conversations

---

## 🤔 Key Decisions

### Decision #1: How to segment Free vs Paid customers?
**Answer:** Use customer tier from custom_attributes

**Reasoning:** The 'tier' field in custom_attributes is the most reliable 
source for customer tier information. Fallback to tags if not present.

**Supporting Data:**
- Conversations with tier field: 5,100 (96.5%)
- Conversations missing tier: 186 (3.5%)
- Fallback used: 186 times

### Decision #2: How to detect Fin-only conversations?
**Answer:** Check if ai_agent_participated=True AND no admin replies in conversation_parts

**Reasoning:** Fin-only means Fin responded but no human admin actually replied.
We check conversation_parts for admin-type authors to ensure accuracy.

**Supporting Data:**
- ai_agent_participated=True: 4,521 conversations
- Admin replies found: 2,103 conversations
- Fin-only (no admin replies): 2,418 conversations
- Human-handled: 2,865 conversations

### Decision #3: How to classify topics?
**Answer:** Use AI-based taxonomy classification with keyword fallback

**Reasoning:** AI classification provides better accuracy than keyword matching alone.
Fallback to keywords if AI fails or returns low confidence.

**Supporting Data:**
- Conversations classified by AI: 4,890 (92.5%)
- Conversations classified by keywords: 396 (7.5%)
- Average AI confidence: 0.87
- Topics detected: 12

### Decision #4: What threshold for "premature escalation"?
**Answer:** Escalation with <2 diagnostic questions = premature

**Reasoning:** Industry best practice suggests minimum 2-3 diagnostic questions
before escalation. We use 2 as threshold to catch the most egregious cases.

**Supporting Data:**
- Total escalations analyzed: 245
- Escalations with 0 questions: 78 (32%)
- Escalations with 1 question: 45 (18%)
- Escalations with 2+ questions: 122 (50%)
- Flagged as premature: 123 (50%)

---

## ⚠️ Warnings and Issues

### Warning #1: Missing conversation_rating for many conversations
**Impact:** CSAT analysis only covers 20% of conversations.
Can't calculate CSAT for 80% of tickets.

**Resolution:** Proceeded with analysis using available CSAT data.
Noted in report that CSAT represents 1,057 rated conversations out of 5,286 total.

### Warning #2: Some conversations missing primary_category
**Impact:** 186 conversations couldn't be categorized by taxonomy.

**Resolution:** Applied "Unknown" category to these conversations.
They're included in overall metrics but excluded from category-specific analysis.

### Warning #3: Admin email not found for 12 admin IDs
**Impact:** 12 conversations couldn't be attributed to specific agents.

**Resolution:** Used fallback attribution based on admin_assignee_id.
These conversations included in team metrics but not individual agent metrics.

---

## 📋 Detailed Step-by-Step Process

### Phase: Data Fetching

**Step 1** (0.1s): Started conversation fetch from Intercom API
  - Start date: `2025-10-18`
  - End date: `2025-10-25`
  - API endpoint: `/conversations/search`
  - Chunking strategy: `Daily chunks (7-day max per chunk)`

**Step 2** (21.3s): Fetched chunk 1 of 2
  - Date range: `2025-10-18 to 2025-10-24`
  - Pages fetched: `106`
  - Conversations: `5,288`
  - API calls made: `106`
  - Average response time: `0.2s per page`

**Step 3** (36.8s): Fetched chunk 2 of 2
  - Date range: `2025-10-25 to 2025-10-25`
  - Pages fetched: `9`
  - Conversations: `418`
  - API calls made: `9`

**Step 4** (36.9s): Combined all chunks
  - Total conversations: `5,706`
  - Duplicate IDs found: `420`
  - Unique conversations: `5,286`

### Phase: Data Preprocessing

**Step 5** (37.0s): Started data validation
  - Input conversations: `5,286`
  - Validation rules: `7 checks`

**Step 6** (37.1s): Validated conversation structure
  - Valid conversations: `5,286`
  - Invalid/malformed: `0`
  - Required fields present: `100%`

**Step 7** (37.5s): Inferred missing data
  - Conversations with missing tier: `186`
  - Inferred from tags: `143`
  - Inferred from email domain: `38`
  - Still unknown: `5`

**Step 8** (38.2s): Cleaned conversation text
  - Removed HTML tags: `4,521 conversations`
  - Normalized whitespace: `5,286 conversations`
  - Fixed encoding issues: `23 conversations`

### Phase: Segmentation

**Step 9** (39.0s): Started customer segmentation
  - Segmentation strategy: `Tier-first (Free/Paid)`
  - Agents analyzed: `Horatio, Boldr, Escalated, Fin`

**Step 10** (39.5s): Classified Free tier conversations
  - Total Free tier: `2,103 conversations`
  - All handled by Fin: `2,103` (100%)
  - Reason: `Free tier cannot escalate to humans`

**Step 11** (40.1s): Classified Paid tier conversations
  - Total Paid tier: `3,183 conversations`
  - Fin-only (resolved): `315 conversations` (9.9%)
  - Horatio agents: `1,874 conversations` (58.9%)
  - Boldr agents: `523 conversations` (16.4%)
  - Escalated to Gamma: `471 conversations` (14.8%)

**Step 12** (40.3s): Validated segmentation results
  - Total classified: `5,286`
  - Unclassified: `0`
  - Segmentation accuracy: `100%`

### Phase: Topic Detection

**Step 13** (41.0s): Started AI-based topic classification
  - AI model used: `gpt-4o`
  - Temperature: `0.3`
  - Taxonomy categories: `12`

**Step 14** (45.2s): Classified batch 1 of 10
  - Conversations in batch: `528`
  - AI classification succeeded: `523`
  - Fallback to keywords: `5`
  - Average confidence: `0.89`
  - Topics detected: `Billing (245), Bug (156), Product Question (89), Other (38)`

[... 8 more batches ...]

**Step 23** (68.5s): Completed topic classification
  - Total conversations classified: `5,286`
  - AI classified: `4,890` (92.5%)
  - Keyword classified: `396` (7.5%)
  - Topics detected: `12`
  - Average confidence: `0.87`

### Phase: Fin Performance Analysis

**Step 24** (69.0s): Started Fin performance calculation
  - Fin-involved conversations: `4,521`
  - Free tier (Fin-only): `2,103`
  - Paid tier (Fin-resolved): `315`
  - Paid tier (Fin→Human): `2,103`

**Step 25** (69.2s): Calculated Fin resolution rate
  - Formula: `(Fin-only + Fin-resolved) / Fin-involved`
  - Numerator: `2,418 conversations` (Fin resolved without human)
  - Denominator: `4,521 conversations` (Fin involved)
  - Result: `53.5%` Fin resolution rate

**Step 26** (69.5s): Detected Fin knowledge gaps
  - Method: `Analyzed conversations with low CSAT (<3 stars) where Fin was only responder`
  - Low-CSAT Fin-only: `87 conversations`
  - Knowledge gap rate: `3.6%` (87 / 2,418)

### Phase: Agent Performance (Horatio)

**Step 27** (70.0s): Started Horatio agent analysis
  - Total Horatio conversations: `1,874`
  - Unique Horatio agents: `17`
  - Analysis type: `Individual breakdown with CSAT`

**Step 28** (72.5s): Fetched admin profiles from Intercom API
  - Admin IDs to fetch: `17`
  - API calls made: `17`
  - Successful fetches: `15`
  - Failed fetches: `2` (used fallback)
  - Vendor distribution: `horatio: 15, unknown: 2`

**Step 29** (75.0s): Calculated individual agent metrics
  - Agents analyzed: `15` (2 excluded due to vendor mismatch)
  - Metrics per agent: `FCR, Escalation, Response Time, CSAT, Troubleshooting`

**Step 30** (76.0s): Calculated CSAT for agent Juan
  - Total conversations: `42`
  - Conversations with CSAT: `6` (14.3%)
  - Average CSAT: `4.83 stars`
  - Negative CSATs (1-2 stars): `0`
  - Rating distribution: `5★: 5, 4★: 1, 3★: 0, 2★: 0, 1★: 0`

**Step 31** (76.5s): Calculated CSAT for agent Lorna
  - Total conversations: `38`
  - Conversations with CSAT: `15` (39.5%)
  - Average CSAT: `3.07 stars`
  - Negative CSATs (1-2 stars): `7` (46.7%)
  - Rating distribution: `5★: 1, 4★: 2, 3★: 5, 2★: 4, 1★: 3`

**Step 32** (77.0s): Found worst CSAT tickets for Lorna
  - Low-CSAT conversations (1-2 stars): `7`
  - Extracted top 5 worst for coaching
  - Conversation IDs: `[456789, 456790, 456791, 456792, 456793]`
  - All have Intercom URLs generated

[... more agents ...]

### Phase: Troubleshooting Analysis (Optional - If Enabled)

**Step 40** (280.0s): Analyzing troubleshooting for Lorna
  - Priority conversations (escalated/low-CSAT): `12`
  - Analyzing with AI: `10 conversations`
  - AI model: `gpt-4o-mini`

**Step 41** (285.0s): Conversation #456789 troubleshooting analysis
  - Diagnostic questions asked: `1`
  - Asked for error messages: `No`
  - Asked for screenshots: `No`
  - Tried alternative solutions: `No`
  - Showed empathy: `No`
  - Troubleshooting score: `0.2 / 1.0`
  - Premature escalation: `Yes`
  - AI reasoning: `"Agent escalated immediately without asking diagnostic questions"`

[... 9 more conversations ...]

**Step 42** (320.0s): Aggregated troubleshooting pattern for Lorna
  - Average troubleshooting score: `0.35 / 1.0`
  - Average diagnostic questions: `1.2`
  - Premature escalation rate: `70%` (7 / 10)
  - Consistency score: `0.45` (inconsistent approach)
  - Issues identified: `High premature escalation rate, Insufficient diagnostic questions`

---

## 📊 Output Generation

**Step 45** (325.0s): Built agent performance report
  - Agents ranked by FCR
  - Top performers: `Juan (85%), Samil (82%)`
  - Bottom performers: `Lorna (65%), Jose (68%)`
  - Agents needing coaching: `5` (coaching_priority = high)
  - Agents for praise: `4` (top 25%)

**Step 46** (328.0s): Saved analysis JSON
  - File path: `outputs/horatio_performance_20251025_2145.json`
  - File size: `2.4 MB`
  - Contains: `All agent metrics, worst CSAT examples, troubleshooting data`

**Step 47** (342.5s): Generated Gamma presentation
  - API call to Gamma
  - Credits used: `75`
  - Presentation URL: `https://gamma.app/docs/abc-123`
  - Generation time: `14.3s`

===== ANALYSIS COMPLETE =====
```

---

## 🔧 **How to Use**

### **CLI Flag:**
```bash
# Regular analysis
python src/main.py agent-performance --agent horatio --individual-breakdown --time-period week

# WITH AUDIT TRAIL
python src/main.py agent-performance --agent horatio --individual-breakdown --time-period week --audit-trail
```

### **What You Get:**

**Two files generated:**
1. **`audit_trail_YYYYMMDD_HHMMSS.md`** - Human-readable narration
2. **`audit_trail_YYYYMMDD_HHMMSS.json`** - Machine-readable data for validation

---

## 📊 **What Gets Audited**

### **1. Data Fetching**
```
Step 1: Started conversation fetch
  - API endpoint: /conversations/search
  - Date range: 2025-10-18 to 2025-10-25
  - Filter query: created_at>1729224000 AND created_at<1729915199

Step 2: Fetched page 1
  - Conversations returned: 50
  - Cursor for next page: xyz123
  - API response time: 1.2s
```

### **2. Data Transformations**
```
Step 5: Removed duplicate conversations
  - Input: 5,706 conversations
  - Duplicates found: 420 (detected by ID)
  - Output: 5,286 unique conversations
  - Deduplication rate: 7.4%
```

### **3. Metrics Calculations**
```
Step 15: Calculated FCR for Horatio team
  - Formula: (closed - reopened) / closed
  - Closed conversations: 1,654
  - Reopened conversations: 412
  - FCR numerator: 1,242
  - FCR denominator: 1,654
  - Result: 75.1% FCR
```

### **4. AI Decisions**
```
Step 20: AI classified conversation #789 as "Billing>Refund"
  - AI model: gpt-4o
  - Prompt tokens: 245
  - Response tokens: 18
  - Confidence: 0.92
  - Reasoning: "Customer mentioned 'refund', 'subscription', 'cancel payment'"
  - Taxonomy match: Billing (primary), Refund (subcategory)
```

### **5. Quality Checks**
```
Quality Check: Validate Fin resolution logic
  ✅ PASSED
  - Fin-only conversations have ai_agent_participated=True: Yes
  - Fin-only conversations have NO admin replies: Verified
  - Fin-only conversations are closed or have ≤2 customer messages: Yes
  - No bad ratings (<3 stars) in Fin-resolved: Verified
```

---

## 💡 **Benefits**

### **For You (Confidence):**
- ✅ See exactly what the system did
- ✅ Verify logic is correct
- ✅ Catch bugs/issues early
- ✅ Understand where numbers come from

### **For Data Engineers:**
- ✅ Validate calculations step-by-step
- ✅ Reproduce results manually if needed
- ✅ Verify AI decisions make sense
- ✅ Check data quality issues

### **For Debugging:**
- ✅ Find exactly where analysis went wrong
- ✅ See what data was used for each decision
- ✅ Trace metrics back to source conversations
- ✅ Validate formulas and thresholds

---

## 🚀 **Implementation Status**

### **Core Service Created:**
- ✅ `src/services/audit_trail.py` - Audit trail service

### **To Integrate:**
- [ ] Add `--audit-trail` flag to CLI commands
- [ ] Integrate into TopicOrchestrator
- [ ] Integrate into AgentPerformanceAgent
- [ ] Integrate into data preprocessor
- [ ] Add audit steps throughout analysis

### **Estimated Work:**
- Core service: ✅ DONE (30 minutes)
- Integration: ~2-3 hours (adding audit.step() calls throughout code)
- Testing: ~30 minutes

---

## 📝 **Example Integration**

```python
# In TopicOrchestrator
class TopicOrchestrator:
    def __init__(self, enable_audit=False):
        # ... existing init ...
        
        if enable_audit:
            self.audit = AuditTrail()
        else:
            self.audit = None
    
    async def execute_weekly_analysis(self, conversations, ...):
        if self.audit:
            self.audit.step(
                "Data Fetching", 
                f"Received {len(conversations)} conversations",
                {'count': len(conversations), 'date_range': f'{start_date} to {end_date}'}
            )
        
        # Segmentation
        segmentation_result = await self.segmentation_agent.execute(context)
        
        if self.audit:
            self.audit.decision(
                "How to segment Free vs Paid customers?",
                "Use customer tier from custom_attributes",
                "Tier field is most reliable source",
                {
                    'free_count': len(segmentation_result.data['free_tier']),
                    'paid_count': len(segmentation_result.data['paid_tier'])
                }
            )
        
        # ... continue analysis ...
        
        # At end
        if self.audit:
            audit_path = self.audit.save_report()
            print(f"\n📋 Audit trail saved to: {audit_path}")
```

---

## 🎯 **Want Me to Integrate It Now?**

I've created the core audit trail service. Should I:

**Option A:** Integrate it now (2-3 hours)
- Add audit steps throughout analysis
- Generate full audit reports
- Test with sample analysis

**Option B:** Integrate later (when you have time to test)
- Core service is ready
- Can be added incrementally
- Won't slow down current analyses

**Option C:** Just keep the service available for manual use
- You can call `audit.step()` manually when debugging
- Don't slow down production runs

Let me know which you prefer!

