# Fin Detection Logic Audit

## Issue: "2000+ Human Agents Detected" Seems Suspicious

### Current Fin Detection Logic

**File:** `src/agents/segmentation_agent.py` (lines 465-583)

#### Classification Flow:
```
1. Extract customer tier (FREE/PRO/PLUS/ULTRA)
   ↓
2. If FREE tier → Always return ('free', 'fin_ai') regardless of admin_assignee_id
   ↓
3. If PAID tier → Check for human involvement:
   a. Extract admin emails from conversation_parts, source, assignee fields
   b. Check for escalation patterns (senior staff names)
   c. Check for Horatio or Boldr email domains
   d. Check for Horatio/Boldr text patterns
   e. If has admin_assignee_id OR admin_emails → return ('paid', 'unknown')
   f. If ai_agent_participated → return ('paid', 'fin_resolved')
   g. Otherwise → Unknown
```

### Problem Areas Identified

#### 1. **Loose "Unknown Agent" Classification**
**Location:** Line 572-574
```python
# Check for human admin (generic)
if conv.get('admin_assignee_id') or admin_emails:
    self.logger.debug(f"Generic paid customer detected (unknown agent type) in conversation {conv_id}")
    return 'paid', 'unknown'  # Has human but can't identify which
```

**Issue:** ANY admin_assignee_id OR email gets classified as "human" (unknown agent type), which then gets counted in "Human Support" stats.

**Hypothesis:** If admin_assignee_id is populated for system admins, internal team members, or automated processing, these could be miscounted as human support.

#### 2. **admin_assignee_id Field Ambiguity**
The system assumes `admin_assignee_id` = human agent, but it could include:
- System admins (internal staff, not customer support)
- Automated assignment IDs
- Service bots other than Fin
- Escalation queue IDs
- Team assignment IDs (not individual agents)

#### 3. **Missing Actual Admin Response Check**
**Location:** Line 572
```python
if conv.get('admin_assignee_id') or admin_emails:
    return 'paid', 'unknown'
```

**Problem:** Assignment doesn't mean the admin actually RESPONDED. Compare with `is_fin_resolved()` which correctly checks:
```python
admin_parts = [p for p in parts_list if p.get('author', {}).get('type') == 'admin']
has_admin_response = len(admin_parts) > 0
```

#### 4. **Missing Cross-Validation**
The segmentation_agent doesn't validate that:
- Admin was actually assigned to the conversation
- Admin actually wrote a message (not just assigned)
- Assignment wasn't auto-cleared or changed mid-conversation

---

## Alternative Detection Methods Research

Based on industry standards for support attribution:

### Method 1: **Actual Response Attribution** ✅ RECOMMENDED
Instead of checking `admin_assignee_id`, check conversation_parts:
```python
admin_parts = [p for p in parts if p.get('author', {}).get('type') == 'admin']
if len(admin_parts) > 0:
    return ('paid', 'human')  # Admin actually wrote something
```

**Advantages:**
- Definitive proof of human involvement
- Matches what Fin detection logic already does
- Zero false positives

**Source:** `src/services/fin_escalation_analyzer.py` lines 659-662 (already implemented)

### Method 2: **Message Author Analysis** ✅ GOOD
Check the author type field in each message:
```python
for part in conversation_parts:
    if part.get('author', {}).get('type') == 'admin':
        return ('paid', detect_agent_type_from_email(part['author']['email']))
```

**Advantages:**
- Handles agent transfers mid-conversation
- Captures exact agent who responded
- Determines specific agent type (Horatio, Boldr, etc.)

### Method 3: **Response Time Patterns** ⚠️ SUPPLEMENTARY
Fin AI has predictable response times (immediate), humans have variable delays:
```python
first_admin_response = find_first_admin_message(conversation)
if first_admin_response:
    response_time = first_admin_response['timestamp'] - customer_message['timestamp']
    if response_time > 5_minutes:  # Humans rarely respond instantly
        return ('paid', 'human')
```

**Advantages:**
- Catches admins assigned but hidden in thread
- Detects shadow escalations

**Disadvantages:**
- Requires reliable timestamps
- Could be unreliable during off-hours

### Method 4: **Email Domain Validation** ⚠️ CURRENT APPROACH
Already done but incomplete:
- ✅ Detects @hirehoratio.co, @boldrimpact.com, @gamma.app
- ❌ Doesn't validate the admin actually responded
- ❌ Treats generic emails as "unknown" human agents

---

## Recommended Fix

### Change Classification Logic

**Before (Line 572-574):**
```python
# Check for human admin (generic)
if conv.get('admin_assignee_id') or admin_emails:
    return 'paid', 'unknown'
```

**After (Proposed):**
```python
# Check if admin actually responded (not just assigned)
admin_parts = [
    p for p in conv_parts 
    if p.get('author', {}).get('type') == 'admin'
]

if admin_parts:
    # Admin actually wrote a message - determine which agent
    # (use existing email domain detection logic)
    # ... email checking code ...
    return 'paid', 'unknown'  # Fallback for generic admins who responded
else:
    # Admin assigned but didn't respond
    # This is NOT human support - might be Fin AI only
    if ai_participated:
        return 'paid', 'fin_resolved'
    else:
        return 'unknown', 'unknown'
```

### Why This Matters

**Current Logic Problem:**
```
If admin_assignee_id exists → Mark as human support
Result: Any auto-assignment, system escalation, or internal note with assignee ID 
        gets marked as "human handled"
```

**Proposed Fix:**
```
If admin actually responded (has message in conversation_parts with author.type='admin')
  → Mark as human support (correct)
Else
  → Mark as Fin-only (correct)
```

---

## Validation Checklist

Run this query to validate:

```sql
-- Find conversations where admin_assignee_id exists but no admin messages
SELECT 
    id,
    admin_assignee_id,
    COUNT(FILTER(WHERE author_type = 'admin')) as admin_response_count,
    ai_agent_participated
FROM conversations
WHERE admin_assignee_id IS NOT NULL
  AND tier IN ('Pro', 'Plus', 'Ultra')
GROUP BY id
HAVING COUNT(FILTER(WHERE author_type = 'admin')) = 0
ORDER BY 1 DESC
LIMIT 100
```

If this query returns 1000+results, it confirms the issue: admin_assignee_id is being set without actual admin response.

---

## CLI Flags Consistency Issue

Separate from Fin detection, the user also reported CLI flags not consistent across commands.

### Current State:
- `voice-of-customer`: Has all flags (--test-mode, --verbose, --audit-trail, --generate-gamma, --multi-agent, --analysis-type, --ai-model)
- `agent-performance`: Missing some flags
- Other commands: Varied flag support

### Required Changes:
1. Create unified flag set in base CLI group
2. Propagate to all subcommands
3. Standardize behavior and defaults
4. Document flag matrix

---

## References

1. **Intercom Documentation**
   - admin_assignee_id field may include system values
   - conversation_parts is authoritative source for who actually responded

2. **Industry Standard**
   - CSAT companies (Zendesk, Freshdesk, Help Scout) use author.type as primary signal
   - admin_assignee_id is used for routing/assignment, not attribution

3. **Current Implementation Already Correct**
   - `is_fin_resolved()` in fin_escalation_analyzer.py (line 659-662) correctly uses admin_parts
   - segmentation_agent should use same logic for consistency
