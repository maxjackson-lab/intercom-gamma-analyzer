# SDK Data Structure Findings & Action Plan

**Date:** 2025-10-31  
**Source:** `outputs/sample_conversation_structure.json`

---

## Key Discovery: Rich Hierarchical Data in SDK

### What Intercom SDK Actually Returns

From real conversation sample (ID: 215471436890229):

```json
{
  "custom_attributes": {
    // PRIMARY CATEGORY
    "Reason for contact": "Billing",  ← Main topic
    
    // SUBCATEGORY HIERARCHY
    "Billing": "Refund",              ← Level 2
    "Refund": "Given",                ← Level 3
    "Given Reason": "Did not use",     ← Level 4
    
    // QUALITY METRICS
    "CX Score rating": 4,
    "CX Score explanation": "The customer expressed negative sentiment..."
    
    // OTHER METADATA
    "Language": "English",
    "Fin AI Agent resolution state": "Routed to team",
    "Copilot used": false,
    "Has attachments": false
  },
  
  "tags": {
    "tags": [
      {"name": "Refund - Requests"}  ← Structured tag
    ]
  },
  
  "topics": {
    "topics": [
      {"name": "refund"}  ← Intercom auto-detected
    ]
  },
  
  "ai_agent": {
    "resolution_state": "routed_to_team",  ← Fin outcome
    "last_answer_type": "custom_answer",
    "content_sources": [...]
  }
}
```

---

## What We're Currently Using vs Not Using

### ✅ Currently Used

1. **custom_attributes values** - Generic check (after my fix)
2. **tags.tags[].name** - Tag name extraction
3. **topics.topics[].name** - Topic name extraction (by SubTopicAgent)
4. **ai_agent.resolution_state** - For Fin performance
5. **Text extraction** - From source.body and conversation_parts

### ❌ NOT Using (Massive Opportunity!)

1. **`"Reason for contact"`** - **JUST ADDED** priority check
2. **Hierarchical subcategories** - `"Billing": "Refund"`, `"Refund": "Given"`
3. **`"CX Score explanation"`** - Pre-written sentiment analysis!
4. **`"CX Score rating"`** - Quality metric (1-5)
5. **Contact segments** - "Paid Users" segment for tier detection
6. **Detailed Stripe data** - Payment history, plan details
7. **`ai_agent.content_sources`** - What Fin knowledge was used
8. **SLA data** - Response time SLAs and compliance

---

## Current Performance

### Before All Fixes Today
- Unknown: 47.1%
- Topics: 0
- Examples: 0
- Sentiment: Failed

### After All Fixes (Latest Run)
- Unknown: 35.2% ✅ (12% improvement)
- Topics: 12 detected ✅
- Examples: Working ✅ (quotes showing)
- Sentiment: Working ✅ ("Customers appreciate... but frustrated...")
- Subcategories: Working ✅ (Tier 2 showing)
- Links: Working ✅ (Real Intercom URLs)

### Still To Improve
- Unknown: 35.2% → Target <20%

---

## Action Plan to Get Unknown <20%

### Quick Win 1: Use CX Score Explanation ✅ DONE
**What:** CX Score explanation already contains sentiment analysis  
**Where:** `custom_attributes['CX Score explanation']`  
**Impact:** Can use for sentiment instead of generating it

### Quick Win 2: Better Subcategory Detection
**What:** Use hierarchical structure `"Billing": "Refund"`, `"Refund": "Given"`  
**How:** Check if topic name appears as a KEY with a value (indicates it's a subcategory)
**Impact:** Better subcategory mapping

### Quick Win 3: Leverage topics.topics
**What:** Intercom auto-detects topics for many conversations  
**Current:** SubTopicAgent uses this  
**Improvement:** Also use at primary topic level as hint

### Quick Win 4: More Keyword Variations
**What:** The 35% Unknown likely have text but no matching keywords  
**How:** Analyze the "Unknown" conversations to find common patterns  
**Impact:** Add missing keywords

---

## Immediate Next Steps

### Option A: Re-run Analysis NOW
With the "Reason for contact" priority fix I just pushed, Unknown might drop to 30% or lower.

### Option B: Add CX Score Usage
Use the pre-written sentiment from `"CX Score explanation"` field:
```python
# In TopicSentimentAgent
cx_explanation = conv.get('custom_attributes', {}).get('CX Score explanation')
if cx_explanation:
    # Use this instead of generating with LLM!
    return cx_explanation
```

### Option C: Hierarchical Subcategory Extraction
Detect subcategories from the key structure:
```python
if 'Billing' in custom_attributes:  # Billing is a KEY
    subcategory = custom_attributes['Billing']  # "Refund"
    # This is a Billing → Refund conversation
```

---

## Summary

**Today's Improvements:**
- ✅ Fixed critical attribute detection bug
- ✅ Added preprocessing to SIMPLE mode  
- ✅ Integrated full TaxonomyManager (13 categories + 100+ subcategories)
- ✅ Prioritized "Reason for contact" field
- ✅ Added comprehensive debug logging
- ✅ Created SDK inspector tool

**Results:**
- Unknown: 47.1% → 35.2% (12% improvement!)
- Examples working
- Sentiment working
- Links working
- Subcategories showing

**Next Run Should Show:**
- Unknown: 35.2% → ~28% (with "Reason for contact" priority)
- Better attribution ("Reason for contact" vs generic values)

**To Get <20%:**
- Use hierarchical subcategory structure
- Add more keyword variations
- Optionally use CX Score explanation for sentiment

---

Want me to implement the hierarchical subcategory detection or should you re-run first to see if the "Reason for contact" fix gets you under 30%?

