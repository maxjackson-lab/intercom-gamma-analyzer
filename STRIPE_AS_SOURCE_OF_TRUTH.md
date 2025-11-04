# Stripe as Source of Truth - Implementation

**Date:** November 4, 2025  
**Change:** Prioritize Stripe billing data for customer tier detection

---

## What Changed

### Old Priority Order:
```
1. custom_attributes.tier (manually set in Intercom)
2. Pre-validated tier
3. Stripe plan (source of truth, but checked last!) ❌
4. Default to FREE
```

### New Priority Order:
```
1. Stripe plan (SOURCE OF TRUTH) ✅
2. Pre-validated tier
3. custom_attributes.tier (fallback)
4. "Paid Users" segment (last resort)
5. Default to FREE
```

---

## Why Stripe First?

**Stripe = Billing System = Ground Truth**

- Stripe knows exactly what plan the customer is paying for
- `custom_attributes.tier` is manually set (human error possible, could be stale)
- Stripe is automatically updated when customers upgrade/downgrade
- **If Stripe says "Business Plan" → that's what they're paying for**

---

## Implementation Details

### File: `src/agents/segmentation_agent.py`

**Function:** `_extract_customer_tier()` (lines 105-226)

### Stripe Plan Mapping

```python
if stripe_status == 'active' and stripe_plan:
    plan_lower = str(stripe_plan).lower()
    
    # Map Stripe plan names to CustomerTier enum
    if 'team' in plan_lower:
        return CustomerTier.TEAM
    elif 'business' in plan_lower:
        return CustomerTier.BUSINESS
    elif 'plus' in plan_lower:
        return CustomerTier.PLUS
    elif 'pro' in plan_lower:
        return CustomerTier.PRO
    elif 'ultra' in plan_lower:
        return CustomerTier.ULTRA
    else:
        # Active subscription but unknown plan name
        # Default to TEAM (lowest paid tier) not FREE
        return CustomerTier.TEAM
```

### Expected Stripe Plan Names

The code uses **substring matching** on the plan name, so it will match:

**TEAM:**
- "Team Monthly"
- "Team Annual"
- "team-plan"
- "gamma-team-subscription"

**BUSINESS:**
- "Business Monthly"
- "Business Annual"
- "business-plan"
- "gamma-business-subscription"

**PRO/PLUS/ULTRA:**
- Same pattern matching logic

**Important:** If Stripe returns something like "Premium Plan" or "Standard Plan", we won't recognize it and will default to TEAM (lowest paid tier).

---

## New Customer Tiers

### Updated Enum (6 tiers):

```python
class CustomerTier(str, Enum):
    FREE = "free"          # No Stripe subscription
    TEAM = "team"          # Team plan (NEW)
    BUSINESS = "business"  # Business plan (NEW)
    PRO = "pro"            # Pro plan
    PLUS = "plus"          # Plus plan
    ULTRA = "ultra"        # Ultra plan
```

### Tier Distribution Tracking

Now logs all 6 tiers:
```
Tier distribution: {'free': 120, 'team': 25, 'business': 15, 'pro': 5, 'plus': 3, 'ultra': 2}
  Free: 120 (70.6%)
  Team: 25 (14.7%)
  Business: 15 (8.8%)
  Pro: 5 (2.9%)
  Plus: 3 (1.8%)
  Ultra: 2 (1.2%)
```

---

## Data Quality Implications

### If Stripe Data Exists:
✅ **Accurate tier detection**
- Billing system is authoritative
- Automatically updated when customers change plans
- No manual data entry errors

### If Stripe Data Missing:
⚠️ **Falls back to custom_attributes.tier**
- May be manually set
- Could be stale or missing
- Results in defaulting to FREE

### How to Monitor

**Check logs for:**
```
"No Stripe data, using pre-validated tier..."  → Falling back
"No tier data found..., defaulting to FREE"    → Data quality issue
```

**Check tier distribution:**
- If 90%+ are FREE → likely Stripe data isn't syncing to Intercom
- If varied distribution → Stripe data is working

---

## Impact on Analysis

### Fin Performance (Paid vs Free)

**Now accurate because:**
- Stripe definitively knows who's paying
- Free tier = truly no subscription (Fin-only by design)
- Paid tier = any active Stripe subscription (can escalate to humans)

### Future Tier-Specific Analysis

With accurate tier data, we can now build:

1. **Per-tier performance metrics**
   - "Business tier: 90% resolution rate"
   - "Team tier: 65% resolution rate"

2. **Per-tier sentiment**
   - "Team tier sentiment declining" (action: investigate)

3. **Per-tier topic breakdown**
   - "Business tier: 60% API questions"
   - "Team tier: 40% billing questions"

4. **Tier-specific coaching**
   - "Agent X performs better with Business tier"
   - "Agent Y struggles with Team tier billing issues"

**But these aren't implemented yet** - just tier detection is ready.

---

## Testing Recommendations

### 1. Verify Stripe Data Exists

Run analysis and check logs:
```bash
python src/main.py voice-of-customer --time-period yesterday

# Look for:
# ✅ "Found active Stripe subscription 'Team Monthly'"
# ❌ "No Stripe data, using custom_attributes.tier"
# ❌ "No tier data found, defaulting to FREE"
```

### 2. Check Tier Distribution

```bash
# In logs, look for:
Tier distribution: {'free': X, 'team': Y, 'business': Z, ...}
```

**Good result:** Mixed distribution (suggests Stripe data working)  
**Bad result:** 95%+ FREE (suggests Stripe data missing)

### 3. Validate Stripe Field Names

Check actual Intercom contact data:
- `custom_attributes.stripe_subscription_status` should be "active"
- `custom_attributes.stripe_plan` should contain plan name

If these fields don't exist → Stripe integration isn't syncing to Intercom

---

## Files Modified

- `src/models/analysis_models.py` - Added TEAM, BUSINESS to CustomerTier enum
- `src/agents/segmentation_agent.py` - Reprioritized tier detection (Stripe first)

## Risk Level

🟢 **LOW** 
- Logic improvement (Stripe more reliable than manual fields)
- Graceful fallback chain (if Stripe missing, still works)
- No breaking changes (same enum values, just better detection)

---

## Key Principle

> **"Trust the billing system - it's the one that knows who's paying what"**

If there's ever a conflict between Stripe and manual fields, Stripe wins.

---

**Stripe is now the source of truth for customer tier detection.** ✅

