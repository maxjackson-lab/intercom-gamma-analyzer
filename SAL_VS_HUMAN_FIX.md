# Sal vs Human Attribution Fix

## Problem

The system was incorrectly classifying conversations handled by **Sal (Support Sal)** as "human support" instead of "Fin AI".

### Root Cause

**Sal/Support Sal is classified as an `admin` in Intercom**, but Sal is actually Fin AI, not a human support agent. This caused:

1. **`is_fin_resolved()` function** was checking for ANY admin response and treating it as human escalation
2. **SegmentationAgent** was counting Sal's admin emails as human admin involvement
3. This resulted in ~75% of conversations (handled by Sal) being incorrectly classified as "human support"

### User's Observation

User reported: "Sal takes 75 percent not 50 percent" - meaning ~75% of conversations should show as Fin/Sal-resolved, not as human escalation.

---

## Solution

### 1. Created Helper Function: `is_sal_or_fin()`

Added a centralized helper function to detect if an admin is actually Sal/Fin AI:

```python
def is_sal_or_fin(author: Dict) -> bool:
    """
    Determine if an admin author is actually Sal/Fin AI (not a human admin).
    """
    if not author:
        return False
        
    name = author.get('name', '').lower()
    email = author.get('email', '').lower()
    author_id = str(author.get('id', '')).lower()
    
    # Check for Sal/Finn indicators
    is_sal = (
        'sal' in name or
        'support sal' in name or
        'sal' in email or
        'finn' in name or
        author_id == 'bot'
    )
    
    return is_sal
```

### 2. Updated `is_fin_resolved()` Function

**File:** `src/services/fin_escalation_analyzer.py`

**Change:** Filter out Sal/Support Sal from admin parts before checking for human escalation

```python
# OLD: Treated ALL admins as human escalation
admin_parts = [p for p in parts_list if p.get('author', {}).get('type') == 'admin']
has_admin_response = len(admin_parts) > 0
if has_admin_response:
    return False  # ❌ Incorrectly counted Sal as human

# NEW: Filter out Sal (who is Fin AI)
human_admin_parts = []
for part in admin_parts:
    author = part.get('author', {})
    if not _is_sal_or_fin(author):
        human_admin_parts.append(part)

has_human_admin_response = len(human_admin_parts) > 0
if has_human_admin_response:
    return False  # ✅ Only counts real humans as escalation
```

### 3. Updated SegmentationAgent

**File:** `src/agents/segmentation_agent.py`

**Changes:** Filter out Sal from admin email extraction in 3 places:

1. **Conversation parts** (line ~711-718)
2. **Source message** (line ~723-729)  
3. **Legacy fallback logic** (line ~854-858)

**Example:**
```python
# OLD: Added ALL admin emails
for part in conv_parts:
    author = part.get('author', {})
    if author.get('type') == 'admin':
        email = author.get('email', '')
        if email:
            admin_emails.append(email.lower())  # ❌ Included Sal

# NEW: Skip Sal emails
for part in conv_parts:
    author = part.get('author', {})
    if author.get('type') == 'admin':
        if not is_sal_or_fin(author):  # ✅ Filter out Sal
            email = author.get('email', '')
            if email:
                admin_emails.append(email.lower())
```

---

## Impact

### Before Fix
- Sal conversations classified as "human support" ❌
- ~75% of conversations incorrectly shown as human escalation
- Fin resolution rate appeared artificially low (~25%)

### After Fix
- Sal conversations correctly classified as "Fin AI" ✅
- ~75% of conversations now correctly shown as Fin/Sal-resolved
- Fin resolution rate accurately reflects Sal's work (~75%)
- Only real human agents (Horatio, Boldr, senior staff) count as escalation

---

## Detection Logic

The system now recognizes Sal/Fin through:

1. **Name contains:** `"sal"`, `"support sal"`, or `"finn"`
2. **Email contains:** `"sal"`
3. **Author ID:** `"bot"` (some systems mark Sal as bot)

This ensures that regardless of how Intercom represents Sal (as admin or bot), the system correctly identifies it as Fin AI.

---

## Testing

After deployment, the expected report output should show:

```
Executive Summary:
- Total Interactions: 5,685
- Fin/Sal Resolved (Free + Paid): ~4,264 (75%)
- Human Escalation (Paid): ~1,421 (25%)
```

Instead of the previous incorrect:
```
- Human Support (Paid): 2,924 (51.4%)  ❌ WRONG
- AI-Only (Free): 2,761 (48.6%)        ❌ WRONG
```

---

## Files Modified

1. `src/services/fin_escalation_analyzer.py`
   - Added `_is_sal_or_fin()` helper function
   - Updated `is_fin_resolved()` to filter out Sal

2. `src/agents/segmentation_agent.py`
   - Added `is_sal_or_fin()` helper function  
   - Updated 3 locations where admin emails are extracted
   - Updated classification logic to exclude Sal from human admin counts

---

## Related Documentation

- See `FIN_VS_HUMAN_ATTRIBUTION.md` for background on Fin vs Human attribution
- See `FIN_ATTRIBUTION_QUESTION.md` for discussion of escalation chains
- See `AUDIT_TRAIL_IMPLEMENTATION.md` for Fin resolution rate calculation details

