# Fin Resolution Rate Bug Diagnosis

**Date:** November 19, 2025  
**Issue:** Fin resolution rates showing 0.0%-0.3% when they should be ~100%  
**Severity:** CRITICAL - Core metric is incorrect

---

## The Problem

**User's Output:**
```
Fin AI Performance: Free Tier
- 602 conversations
- Resolution rate: 0.3%

Fin AI Performance: Paid Tier
- 325 conversations (Fin-resolved)
- Resolution rate: 0.0%
```

**What's Wrong:**
- These conversations are PRE-FILTERED as "Fin-resolved" (no human escalation)
- Resolution rate SHOULD be ~100% (by definition)
- But showing 0.0%-0.3% instead
- This makes the entire Fin performance analysis meaningless

---

## Root Cause Analysis

### Code Flow:

**Step 1: Segmentation** (`segmentation_agent.py:681`)
```python
if ai_participated and not admin_assignee_id:
    return ('paid', 'fin_only')  # ← 325 conversations classified as Fin-only
```

**Step 2: Metrics Calculation** (`fin_metrics_calculator.py:86`)
```python
if not admin_assignee_id and not requested_human:
    deflected.append(conv)  # ← Should match ALL 325 conversations
```

**Step 3: Display** (`output_formatter_agent.py:1099`)
```python
resolution_rate = paid_tier.get('resolution_rate', 0)  # ← Shows 0.0%
```

### The Contradiction

- **Segmentation says:** 325 conversations have `admin_assignee_id=None`
- **Metrics calculator says:** 0 conversations have `admin_assignee_id=None`
- **Conclusion:** Something changed between segmentation and metrics calculation!

---

## Hypothesis 1: Field Population Timing

**Theory:** `admin_assignee_id` is populated DURING enrichment, AFTER segmentation.

**Evidence from logs:**
```
2025-11-19 08:54:30 - agents.SegmentationAgent - WARNING - Free tier customer 215471833573581 has admin_assignee_id=5643511
```

This shows FREE tier customers have `admin_assignee_id` set! But free tier customers should NEVER have human agents.

**Possible Explanation:**
- `admin_assignee_id` represents the "assigned admin" even if they haven't responded yet
- Intercom may set this field automatically for routing
- It doesn't mean the admin actually participated

**Impact:**
- Segmentation runs BEFORE enrichment (uses partial conversation data)
- Metrics calculation runs AFTER enrichment (uses full conversation data with admin_assignee_id)
- Field state changes between the two phases

---

## Hypothesis 2: Wrong Field for Resolution Detection

**Theory:** We're using the wrong field to detect Fin resolution.

**Correct field (per Intercom SDK):**
```python
ai_agent.resolution_state  # Official field from Intercom
```

**Current field (what we use):**
```python
admin_assignee_id  # May not accurately reflect participation
```

**From segmentation_agent.py:696-708:**
```python
ai_agent = conv.get('ai_agent')
ai_resolution_state = None

if ai_agent is not None and isinstance(ai_agent, dict):
    ai_resolution_state = ai_agent.get('resolution_state')
    if ai_resolution_state is not None:
        self.logger.debug(f"ai_agent.resolution_state = {ai_resolution_state}")
```

But then this field is NOT used for the fin_only classification! It uses `admin_assignee_id` instead.

---

## Hypothesis 3: Enrichment Overwrites admin_assignee_id

**Theory:** Enrichment fetches full conversation details which includes admin_assignee_id.

**From intercom_sdk_service.py:397-418:**
```python
# STEP 1: Fetch full conversation details (includes conversation_parts)
full_conv_data = await self._fetch_full_conversation(conv_id)

# Merge conversation_parts into the conversation
if 'conversation_parts' in full_conv_data:
    conv['conversation_parts'] = ...  # Merge
```

**If `_fetch_full_conversation()` returns the FULL conversation object, it may include:**
- `admin_assignee_id` (even if no admin responded)
- `assignee` object
- Other fields that indicate admin assignment (for routing, not participation)

**Result:**
- Segmentation sees: `admin_assignee_id=None` (before enrichment)
- Metrics sees: `admin_assignee_id=5643511` (after enrichment)

---

## The Actual Bug

**Location:** `intercom_sdk_service.py:397-418` + `fin_metrics_calculator.py:73-87`

**What's Happening:**

1. **BEFORE enrichment** (segmentation):
   - Conversations have `admin_assignee_id=None` (partial data from search endpoint)
   - Classified as 'fin_only'

2. **DURING enrichment** (line 397-418):
   - `_fetch_full_conversation()` fetches complete conversation object
   - This includes `admin_assignee_id` field (set by Intercom for routing)
   - Field is copied into conversation dict

3. **AFTER enrichment** (metrics calculation):
   - Conversations NOW have `admin_assignee_id=5643511` (or other admin ID)
   - Metrics calculator checks `if not admin_assignee_id` → FALSE
   - Deflection count = 0
   - Resolution rate = 0.0%

**The field `admin_assignee_id` represents ASSIGNMENT (for routing), not PARTICIPATION!**

---

## The Fix

### Option 1: Use Correct Field for Resolution Detection

**Instead of:**
```python
admin_assignee_id = conv.get('admin_assignee_id')  # Assignment, not participation
if not admin_assignee_id:
    deflected.append(conv)
```

**Use:**
```python
# Check if admin actually PARTICIPATED (not just assigned)
conversation_parts = conv.get('conversation_parts', {}).get('conversation_parts', [])
admin_participated = any(
    part.get('author', {}).get('type') == 'admin'
    for part in conversation_parts
)

if not admin_participated:
    deflected.append(conv)
```

### Option 2: Don't Overwrite admin_assignee_id During Enrichment

**In `intercom_sdk_service.py:397-418`:**
```python
# Fetch full conversation
full_conv_data = await self._fetch_full_conversation(conv_id)

# Merge ONLY conversation_parts (don't overwrite other fields)
if 'conversation_parts' in full_conv_data:
    conv['conversation_parts'] = full_conv_data['conversation_parts']
# DON'T copy admin_assignee_id or other fields
```

### Option 3: Fix Segmentation to Use Participation, Not Assignment

**In `segmentation_agent.py:677-683`:**
```python
# Check if admin PARTICIPATED (not just assigned)
conversation_parts = conv.get('conversation_parts', {}).get('conversation_parts', [])
admin_participated = any(
    part.get('author', {}).get('type') == 'admin'
    for part in conversation_parts
)

if ai_participated and not admin_participated:
    return ('paid', 'fin_only')
```

---

## Recommended Fix

**Use Option 3: Fix BOTH segmentation and metrics to use participation.**

**Why:**
- Most accurate definition of "Fin-resolved"
- Consistent across all code
- Matches Intercom's intent (ai_agent.resolution_state also checks participation)

**Implementation:**
1. Update `segmentation_agent.py:677-683` to check conversation_parts
2. Update `fin_metrics_calculator.py:73-87` to check conversation_parts
3. Add helper function: `_admin_participated(conv)` for reuse

---

## Testing Plan

**Before fix:**
```bash
python src/main.py sample-mode --count 50 --save-to-file
grep "Resolution rate:" outputs/sample_mode_*.log
# Should show: 0.0%-0.3%
```

**After fix:**
```bash
python src/main.py sample-mode --count 50 --save-to-file
grep "Resolution rate:" outputs/sample_mode_*.log
# Should show: 80%-100% (realistic deflection rate)
```

---

## Impact

**Affected Reports:**
- Voice of Customer (Fin performance section)
- Agent Performance
- Historical snapshots (incorrect Fin metrics stored in DuckDB)

**User Impact:**
- Fin appears to be failing (0% resolution) when it's actually working
- Leadership making decisions based on incorrect data
- Wasted time investigating non-existent Fin issues

**Priority:** P0 - Fix immediately before next production run

---

## Additional Issues Found

While investigating, found that free tier conversations ALSO have `admin_assignee_id` set:

```
Free tier customer 215471833573581 has admin_assignee_id=5643511 - likely abuse/trust & safety case
```

This confirms that `admin_assignee_id` is NOT a reliable indicator of human participation.

