# Feature Plan: Custom Date Ranges + Pre-Gamma Text Reports

**User Request:**
1. Select specific date ranges for all functionality (not just dropdowns)
2. Human-readable text file BEFORE Gamma (see what's being shown)

---

## FEATURE 1: Custom Date Range Selector

### Current State (Dropdown Only):
```
Time Period:
  - Yesterday
  - Last Week
  - Last Month
  - Last 3 Months
  - Last 6 Months
```

**Limitations:**
- ❌ Can't analyze "Nov 1-7" specifically
- ❌ Can't compare "This October vs Last October"
- ❌ Can't analyze specific date when incident occurred
- ❌ Can't do custom timeframes like "Last 14 days" or "Q4 2024"

---

### Proposed UI (Date Range Picker):

```html
Time Period:
  [Preset Dropdown ▼] OR [Custom Date Range]
  
  ┌─────────────────────────────────────────┐
  │ Quick Presets: [Last Week ▼]            │
  │                                         │
  │ OR Custom Range:                        │
  │   From: [2025-11-01 📅]                 │
  │   To:   [2025-11-07 📅]                 │
  │                                         │
  │   Examples:                             │
  │   • Last 14 days: Nov 4 - Nov 18        │
  │   • Specific week: Nov 1 - Nov 7        │
  │   • Month: Oct 1 - Oct 31               │
  └─────────────────────────────────────────┘
```

---

### Implementation Plan:

**UI Changes (deploy/railway_web.py + static/app.js):**

1. **Add date picker inputs** (HTML5 date inputs)
   ```html
   <div id="customDateRange" style="display: none;">
     <label>From: <input type="date" id="startDate"></label>
     <label>To: <input type="date" id="endDate"></label>
   </div>
   ```

2. **Add toggle logic** (JavaScript)
   ```javascript
   if (customRangeEnabled) {
     args.push('--start-date', startDate);
     args.push('--end-date', endDate);
   } else {
     args.push('--time-period', timePeriod);
   }
   ```

3. **Backend already supports it!**
   - All commands accept `--start-date` and `--end-date`
   - No backend changes needed!

---

### Pros:
✅ **Flexibility:** Analyze ANY date range
✅ **Precision:** Isolate specific weeks/days
✅ **Comparison:** Compare identical timeframes across months
✅ **Incident Analysis:** "Show me Nov 12 when the outage happened"
✅ **Easy to implement:** Backend already supports it!
✅ **No breaking changes:** Keep dropdowns as defaults

### Cons:
⚠️ **User error:** Invalid ranges (end before start)
⚠️ **Performance:** Very large ranges might timeout (mitigated by chunking)
⚠️ **UI complexity:** More fields = more cognitive load
⚠️ **Validation needed:** Reject ranges >6 months (too slow)

### Risk Level: **LOW**
- Backend already handles custom dates
- Just adding UI layer
- Can validate before sending

---

## FEATURE 2: Pre-Gamma Human-Readable Text Report

### Current Flow:
```
Agents → OutputFormatter → Markdown → Gamma API → Presentation
         ↑ User can't see this step!
```

### Proposed Flow:
```
Agents → OutputFormatter → Markdown → SAVE TEXT FILE → Gamma API
                            ↑ User reviews this!
```

---

### What the Text Report Would Contain:

**Example: `voice_of_customer_READABLE_REPORT.txt`**

```
================================================================================
VOICE OF CUSTOMER ANALYSIS - READABLE REPORT
================================================================================

Analysis Period: Nov 11-18, 2025 (Last Week)
Total Conversations: 803
AI Model: OpenAI (GPT-4o-mini + GPT-4o)
Generated: Nov 18, 2025 8:45pm

================================================================================
EXECUTIVE SUMMARY
================================================================================

Key Insights:
• Billing issues dominate (41% of volume) - primarily refund requests
• Product questions trending up (+15% vs last week) - export features
• Fin handling 68% of conversations with 72% assumed resolution
• Churn risk: 23 high-priority accounts flagged for proactive outreach

================================================================================
TOPIC BREAKDOWN (8 Primary Topics)
================================================================================

1. BILLING (329 conversations - 41.0%)
   ────────────────────────────────────────────────────────
   Sentiment: 65% Frustrated, 25% Neutral, 10% Appreciative
   
   Tier 2 Breakdown:
     • Refund Requests: 180 (54.7%) - "charged twice", "cancel subscription"
     • Invoice Issues: 95 (28.9%) - receipt requests, billing statements
     • Payment Failures: 54 (16.4%) - declined cards, payment errors
   
   Tier 3 Deep Dive (Top 3):
     • Pricing Confusion: 45 conversations
       "Confused annual with monthly pricing"
       "Didn't realize it was $10/month not $10/year"
     
     • Unexpected Charges: 38 conversations
       "Thought I cancelled but got charged"
       "Trial ended and auto-renewed"
     
     • Duplicate Charges: 32 conversations
       "Charged twice for same month"
       "Multiple charges on same day"
   
   Fin Performance:
     • Fin handled: 223/329 (67.8%)
     • Assumed resolution: 145 (65%)
     • Routed to human: 78 (35%)
     • Human satisfaction: 67% positive
   
   Example Conversations:
     [1] https://app.intercom.com/a/apps/abc123/conversations/xyz789
         "I was charged $240 instead of $120 - need immediate refund"
         Resolution: Refund processed within 2 hours
     
     [2] https://app.intercom.com/a/apps/abc123/conversations/xyz456
         "Confused annual vs monthly - want to switch plans"
         Resolution: Fin explained pricing, user satisfied

2. PRODUCT QUESTION (215 conversations - 26.8%)
   ────────────────────────────────────────────────────────
   Sentiment: 45% Curious, 35% Frustrated, 20% Appreciative
   
   [Similar structure for each topic...]

================================================================================
CROSS-TOPIC INSIGHTS (Correlation Analysis)
================================================================================

Correlation 1: Billing + Bug (correlation: 0.68)
  Pattern: "Can't export → Can't get refund"
  Volume: 23 conversations
  Insight: Export failures blocking refund requests
  Recommendation: Fix export bug to reduce billing escalations

Correlation 2: Account + Privacy (correlation: 0.45)
  Pattern: Email change requests + GDPR concerns
  Volume: 12 conversations
  Insight: Users changing email to comply with company data policies

================================================================================
CHURN RISK SIGNALS
================================================================================

High Risk (23 accounts):
  • Multiple billing issues + unresolved bug reports
  • Paid tier customers expressing cancellation intent
  • Example: "If this isn't fixed by next month, I'm cancelling"

Medium Risk (47 accounts):
  • Fin routed to human multiple times in past week
  • Escalation patterns suggest frustration building

================================================================================
QUALITY INSIGHTS
================================================================================

Strategic Recommendations:
1. Prioritize export bug fix (blocking 23 refunds)
2. Improve Fin's pricing explanation (40% of billing confusion)
3. Add self-service subscription management (reduce human load)

Data Quality Notes:
  • 95% conversations have complete metadata
  • 12% missing "Reason for contact" field
  • Confidence: HIGH (0.88) - based on 803 conversations

================================================================================
WHAT WILL BE SENT TO GAMMA
================================================================================

This report will be condensed into a 12-slide presentation:
  • Slide 1: Executive Summary (key metrics)
  • Slides 2-9: Topic Cards (one per topic)
  • Slide 10: Cross-topic Insights
  • Slide 11: Churn Risks
  • Slide 12: Strategic Recommendations

Estimated generation time: 3-5 minutes
Gamma API cost: ~$0.15

================================================================================
END OF READABLE REPORT
================================================================================
```

---

### Implementation Plan:

**Step 1: Add text report generation** (src/agents/output_formatter_agent.py)

```python
def _generate_readable_text_report(self, context, formatted_output):
    """
    Generate human-readable text report BEFORE Gamma.
    
    User can review exactly what will be sent to Gamma API.
    """
    sections = []
    
    # Header
    sections.append("=" * 80)
    sections.append("VOICE OF CUSTOMER ANALYSIS - READABLE REPORT")
    sections.append("=" * 80)
    sections.append(f"Analysis Period: {context.date_range}")
    sections.append(f"Total Conversations: {context.total_conversations}")
    # ... etc
    
    # Executive Summary (from formatted_output)
    sections.append("\n" + "=" * 80)
    sections.append("EXECUTIVE SUMMARY")
    sections.append("=" * 80)
    # Extract and format key insights
    
    # Topic Breakdown (detailed)
    for topic, data in topic_dist.items():
        sections.append(f"\n{topic.upper()} ({data['volume']} conversations - {data['percentage']:.1f}%)")
        sections.append("─" * 60)
        sections.append(f"Sentiment: {sentiment_breakdown}")
        sections.append(f"\nTier 2 Breakdown:")
        for subtopic in tier2_data:
            sections.append(f"  • {subtopic}: {count} ({pct}%)")
        # ... etc
    
    # Correlations, Churn, Quality (from other agents)
    
    # Footer: What will be sent to Gamma
    sections.append("\n" + "=" * 80)
    sections.append("WHAT WILL BE SENT TO GAMMA")
    sections.append("=" * 80)
    sections.append("This report will be condensed into a 12-slide presentation...")
    
    return "\n".join(sections)
```

**Step 2: Save text report** (src/main.py)

```python
# After OutputFormatter completes
text_report = formatter_result.data.get('readable_text_report')
if text_report:
    text_file = output_file.with_suffix('.READABLE_REPORT.txt')
    with open(text_file, 'w') as f:
        f.write(text_report)
    console.print(f"📄 Readable report saved to: {text_file}")

# THEN generate Gamma (user has reviewed text file first!)
if generate_gamma:
    gamma_generator.generate(...)
```

---

### Pros:
✅ **Transparency:** See EXACTLY what Gamma receives
✅ **Validation:** Catch boilerplate BEFORE spending $0.15 on Gamma
✅ **Debugging:** If Gamma slides are wrong, compare to text report
✅ **Archival:** Text files easier to search/grep than JSON
✅ **Review:** Can review and approve before Gamma API call
✅ **Shareable:** Send text report to stakeholders who don't want slides
✅ **Confidence:** Verify all agent insights are included

### Cons:
⚠️ **File clutter:** Another file per run (now 5 files total)
⚠️ **Disk space:** Text reports are ~50-200KB each
⚠️ **Duplication:** Data exists in JSON, markdown in Gamma, now text too
⚠️ **Maintenance:** Need to keep text format in sync with Gamma format
⚠️ **Development time:** ~2-3 hours to implement well

### Risk Level: **LOW-MEDIUM**
- No breaking changes (just adds file)
- Easy to implement (just formatting)
- Slight risk: Another output format to maintain

---

## COMBINED IMPLEMENTATION ESTIMATE:

### **Feature 1: Custom Date Range**
- **Time:** 1-2 hours
- **Complexity:** LOW (backend ready, just UI)
- **Risk:** LOW
- **Files:** `deploy/railway_web.py` (HTML), `static/app.js` (logic)

### **Feature 2: Pre-Gamma Text Report**
- **Time:** 2-3 hours  
- **Complexity:** MEDIUM (need to format nicely)
- **Risk:** LOW-MEDIUM
- **Files:** `src/agents/output_formatter_agent.py`, `src/main.py`

### **Total:** 3-5 hours development + testing

---

## RECOMMENDATION:

### **Implement Both? YES!**

**Why:**
1. **Custom dates:** HIGH value, LOW effort
2. **Text reports:** HIGH transparency, MEDIUM effort
3. **Synergy:** Custom dates + text reports = powerful debugging tool

**Order:**
1. ✅ Custom date range (quick win, 1-2 hours)
2. ✅ Pre-Gamma text report (more complex, 2-3 hours)

**Alternative:**
- Do Feature 1 first, test it
- Then do Feature 2 if still needed

---

## EXAMPLE USE CASES:

### **With Custom Dates:**
```
Scenario: "We had an outage on Nov 12"
Action: Set range to Nov 12 only
Result: Analyze JUST that day's conversations
```

### **With Text Reports:**
```
Scenario: "Gamma slides show no topics"
Action: 
  1. Check voice_of_customer_READABLE_REPORT.txt
  2. See if topics exist in text report
  3. If yes → Gamma formatting bug
  4. If no → Agent detection bug
```

### **Combined Power:**
```
Scenario: "Compare Black Friday 2024 vs 2025"
Action:
  1. Run analysis: Nov 24-30, 2024 (custom dates)
  2. Review text report (see patterns)
  3. Run analysis: Nov 24-30, 2025 (custom dates)
  4. Compare text reports side-by-side
  5. Generate Gamma for each if satisfied
```

---

## FILES THAT WOULD BE CREATED (After Both Features):

### **Current (5 files per run):**
```
voice_of_customer_analysis_2025-W46.json          (9 MB - raw data)
voice_of_customer_analysis_2025-W46.log           (120 KB - console output)
agent_thinking_2025-W46.log                       (80 KB - LLM prompts/responses)
agent_debug_report_2025-W46.txt                   (45 KB - agent summaries)
voice_of_customer_analysis_2025-W46_STRUCTURED_DATA.json  (2 MB - structured insights)
```

### **After Feature 2 (6 files per run):**
```
+ voice_of_customer_analysis_2025-W46_READABLE_REPORT.txt  (150 KB - NEW!)
```

**Total:** 11.4 MB per run → 11.6 MB per run (+1.7%)

---

## DETAILED IMPLEMENTATION BREAKDOWN:

### **FEATURE 1: Custom Date Range (1-2 hours)**

**Phase 1a: UI Layer (30 min)**
- Add radio buttons: "Preset" vs "Custom"
- Add two date inputs (HTML5 `<input type="date">`)
- Add validation (end >= start, not future dates)

**Phase 1b: Frontend Logic (30 min)**
- Toggle visibility based on radio selection
- Construct command args correctly
- Add date validation before submission

**Phase 1c: Validation (30 min)**
- Test with various date ranges
- Verify Railway validation accepts dates
- Ensure chunking works with custom ranges

**Files Changed:**
- `deploy/railway_web.py` (add HTML elements)
- `static/app.js` (add toggle + validation logic)
- `deploy/railway_web.py` CANONICAL_COMMAND_MAPPINGS (already accepts --start-date/--end-date)

---

### **FEATURE 2: Pre-Gamma Text Report (2-3 hours)**

**Phase 2a: Report Generator (1.5 hours)**
- Create `_generate_readable_text_report()` in OutputFormatterAgent
- Format each section (Executive Summary, Topics, Correlations, etc.)
- Include example conversation links
- Add "What will be sent to Gamma" footer

**Phase 2b: Integration (30 min)**
- Call generator in OutputFormatterAgent.execute()
- Add to result_data dict
- Save to file in main.py (before Gamma call)

**Phase 2c: Testing (1 hour)**
- Run VOC analysis with text report enabled
- Verify all agent insights appear
- Compare to Gamma slides for completeness
- Test with empty topics (should show clear error)

**Files Changed:**
- `src/agents/output_formatter_agent.py` (add generator method)
- `src/main.py` (save text file before Gamma)

---

## MOCKUP: How Files Tab Would Look After Both Features

```
📂 voice-of-customer_Nov-11-to-Nov-18_custom-range
   📋 voice_of_customer_analysis.log (120 KB)
   📄 voice_of_customer_analysis.json (9 MB)
   📊 voice_of_customer_analysis_STRUCTURED_DATA.json (2 MB)
   📝 voice_of_customer_analysis_READABLE_REPORT.txt (150 KB) ← NEW!
   🧠 agent_thinking.log (80 KB)
   📊 agent_debug_report.txt (45 KB)
   🎨 voice_of_customer_gamma_presentation.pdf (2 MB)
```

**Download flow:**
1. Download `READABLE_REPORT.txt`
2. Review topics, insights, correlations
3. If satisfied → Keep Gamma presentation
4. If not → Debug with other files before regenerating

---

## DECISION MATRIX:

### **Should we implement?**

| Feature | Value | Effort | Risk | Priority |
|---------|-------|--------|------|----------|
| Custom Date Range | HIGH | LOW | LOW | **P0** |
| Pre-Gamma Text Report | HIGH | MEDIUM | LOW | **P1** |

**Recommendation:** Implement BOTH, but do Custom Dates first (quick win!)

---

## NEXT STEPS:

**Option A: Implement Both Now**
- 3-5 hours total development
- Test together as integrated feature
- Deploy once

**Option B: Phased Rollout (Recommended)**
- Phase 1: Custom Date Range (1-2 hours) → Deploy → Test
- Phase 2: Text Reports (2-3 hours) → Deploy → Test
- Safer, easier to debug

**Option C: Just Custom Dates**
- Quick win (1-2 hours)
- High value, low risk
- Can add text reports later if needed

---

## USER DECISION NEEDED:

1. **Which features to implement?**
   - [ ] Custom Date Range only
   - [ ] Text Reports only
   - [X] Both (recommended)

2. **Which approach?**
   - [ ] Both at once (3-5 hours, single deploy)
   - [X] Phased (Custom dates first, then text reports)
   - [ ] Just custom dates for now

3. **When to start?**
   - [ ] Now (before testing current fixes)
   - [X] After validating LLM checkbox fix + keywords
   - [ ] Later (after production VOC run succeeds)

