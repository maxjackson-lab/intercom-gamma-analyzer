# Tier Segmentation - Reality Check

**Date:** November 4, 2025  
**Issue:** Documentation mentioned "Enterprise" tier that doesn't exist

---

## ✅ Actual Tier Structure (Updated)

### CustomerTier Enum

```python
class CustomerTier(str, Enum):
    FREE = "free"
    TEAM = "team"           # ← ADDED
    BUSINESS = "business"   # ← ADDED
    PRO = "pro"
    PLUS = "plus"
    ULTRA = "ultra"
```

**Not "Enterprise"** - that was made up in documentation.

---

## How Tier Detection Actually Works

### Data Source Priority (in order):

1. **Intercom `custom_attributes.tier`** (if Gamma has set it)
   - `contact.custom_attributes.tier = "team"`
   - `conversation.custom_attributes.tier = "business"`
   - **This must be manually set in Intercom** - not automatic

2. **Stripe plan mapping** (if available)
   - `stripe_plan = "Team Monthly"` → TEAM
   - `stripe_plan = "Business Annual"` → BUSINESS
   - `stripe_plan = "Pro"` → PRO
   - etc.

3. **Default:** FREE (if nothing found)

### The Reality

**From the code:**
```python
if not has_tier:
    defaulted_tier_count += 1  # Tracks how many conversations have no tier data
```

**And the logs:**
```python
self.logger.info(f"Tier data quality: {defaulted_tier_count} conversations defaulted to FREE")
```

**This means:**
- If Gamma hasn't set `custom_attributes.tier` in Intercom
- AND there's no Stripe plan data
- **Everything defaults to FREE** ❌

---

## Where Tier Data Appears (Or Doesn't)

### ✅ Where It DOES Appear:

1. **Logs** (always)
   ```
   Tier distribution: {'free': 120, 'team': 15, 'business': 10, 'pro': 3, 'plus': 2, 'ultra': 0}
   Free: 120 (80%), Team: 15 (10%), Business: 10 (6.7%), Pro: 3 (2%), ...
   ```

2. **Fin Performance Analysis** (Gamma reports)
   ```markdown
   ## Fin AI Performance - Free Tier
   **150 conversations from Free tier customers**
   Resolution Rate: 65%
   
   ## Fin AI Performance - Paid Tier
   **50 conversations from Paid tier customers**
   Resolution Rate: 45%
   ```
   
   **But:** This only shows "Free" vs "Paid" (lumped together)
   
3. **JSON output** (data exports)
   ```json
   {
     "segmentation_summary": {
       "tier_distribution": {
         "free": 120,
         "team": 15,
         "business": 10,
         "pro": 3,
         "plus": 2,
         "ultra": 0
       }
     }
   }
   ```

### ❌ Where It DOESN'T Appear:

1. **Individual topic cards** (Billing, API, etc.)
   - No tier breakdown shown
   - Example: "Billing: 50 conversations" (doesn't show "Team: 30, Business: 15, Free: 5")

2. **Agent performance reports**
   - Shows overall performance
   - Doesn't segment by tier (e.g., "Horatio performs better with Business tier")

3. **Trend analysis**
   - Shows volume trends
   - Doesn't show "Team tier volume increasing"

4. **Coaching reports**
   - Shows agent strengths/weaknesses
   - Doesn't show "Agent struggles with Business tier customers"

---

## The Gap

### What's Built:
✅ Tier extraction logic (FREE, TEAM, BUSINESS, PRO, PLUS, ULTRA)  
✅ Tier distribution tracking  
✅ Tier logging  
✅ Tier in JSON exports  
✅ Free vs Paid split in Fin analysis  

### What's Missing:
❌ Per-topic tier breakdown in Gamma reports  
❌ Per-agent tier performance  
❌ Tier trends over time  
❌ Tier-specific insights ("Business tier experiencing more API issues")  

### Why It's Missing:

Looking at `OutputFormatterAgent`:
- It formats topic cards, but doesn't include tier breakdown
- It formats Fin performance, but lumps all paid tiers together
- It doesn't have logic to segment other metrics by tier

**Example of what's NOT happening:**
```markdown
## Billing Analysis

**Team Tier (30 conversations):**
- Sentiment: Negative
- Resolution Rate: 45%
- Top Issue: Subscription cancellations

**Business Tier (15 conversations):**
- Sentiment: Positive
- Resolution Rate: 90%
- Top Issue: Invoice questions

**Free Tier (5 conversations):**
- Sentiment: Neutral
- Resolution Rate: 100% (Fin only)
```

This would be valuable but **doesn't exist yet**.

---

## Data Quality Question

### Is `custom_attributes.tier` Actually Set?

**Unknown from code alone.** The code assumes it exists, but we don't know:

1. **Does Gamma consistently set this field in Intercom?**
   - If yes: tier data is accurate
   - If no: everything defaults to FREE (inaccurate)

2. **What values does Gamma use?**
   - "team", "business", "pro", "plus", "ultra"? ✅ (matches enum)
   - "Team Plan", "Business Plan"? ❌ (wouldn't match)
   - Something else? ❌ (would default to FREE)

3. **How complete is the data?**
   - 100% coverage? Great
   - 50% coverage? Half the conversations default to FREE
   - 0% coverage? Everything is FREE (useless segmentation)

### How to Verify

**Option 1: Check actual Intercom data**
```bash
python src/main.py --test-mode --time-period yesterday
# Check logs for:
# "Tier data quality: X conversations defaulted to FREE"
# If X is high → tier field isn't set consistently
```

**Option 2: Check a sample conversation in Intercom UI**
- Go to conversation
- Check custom attributes
- Look for `tier` field
- See what value it has

---

## Recommendation

### Immediate Actions:

1. **Verify tier data exists in Intercom**
   - Run analysis, check `defaulted_tier_count`
   - If high → tier field not set → need to populate it

2. **Map to actual Gamma plans**
   - Confirm: Does Gamma use "Team" and "Business" plan names?
   - If yes → update tier detection logic to handle those exact strings
   - If no → ask what the actual plan/tier values are

3. **Decide on tier reporting**
   - Should topic cards show tier breakdown?
   - Should agent performance be tier-segmented?
   - Or is Free vs Paid sufficient for now?

### Code Changes Needed (If Tier Reporting Wanted):

**To show tier breakdown in topic cards:**
- Update `OutputFormatterAgent._format_topic_card()` 
- Add tier sub-sections
- Show metrics per tier

**To show tier in agent performance:**
- Update coaching report generation
- Segment agent metrics by tier
- Show "Agent X performs better with Business tier"

---

## Summary

**What I got wrong in documentation:**
- ❌ Mentioned "Enterprise" (doesn't exist)
- ❌ Implied tier segmentation is visible everywhere (it's mostly in logs)

**What's actually true:**
- ✅ Tiers: FREE, TEAM, BUSINESS, PRO, PLUS, ULTRA (now updated)
- ✅ Tier extraction works (if data exists in Intercom)
- ✅ Tier logged and exported to JSON
- ⚠️ Tier NOT shown in most reports (Gamma cards, coaching)
- ❓ Unknown: Is tier field actually populated in Intercom?

**Your question answered:**
> "How do you actually distinguish it? There's no schema I know of to map that beyond Business and Team plans. Are you doing it by that?"

**Answer:** 
- We look for `custom_attributes.tier` field in Intercom
- We also try to map from `stripe_plan` if available
- If neither exists → defaults to FREE
- **You're right to be skeptical** - this may not be working if the field isn't set!

---

**Next step:** Verify tier field actually exists in real Intercom data, or we're just defaulting everything to FREE.

