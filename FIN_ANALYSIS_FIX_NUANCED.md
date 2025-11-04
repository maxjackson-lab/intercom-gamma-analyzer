# Fin Analysis Fix - Adding Nuance to Escalation vs Failure

## Problem Statement

Current logic: **Escalation = Failure** ❌

This is technically true but lacks nuance:
- Fin routing to team = Fin **working correctly** (knows its limits)
- Fin should only "fail" when it tries to help but **actually fails** (bad CSAT, frustrated customer)

## Correct Interpretation

### Three Outcomes (Not Two):

1. **✅ Resolved by Fin**
   - No human admin needed
   - Closed or low engagement
   - No bad CSAT
   - Customer satisfied

2. **🔄 Correctly Escalated by Fin**
   - Fin recognized it couldn't help
   - Routed to human team **appropriately**
   - This is Fin **working as designed**
   - NOT a failure!

3. **❌ Fin Failed**
   - Fin tried to help but failed
   - Customer frustrated/gave bad CSAT
   - OR Fin didn't escalate when it should have

## Implementation Plan

### Current Code Location:
`src/services/fin_escalation_analyzer.py` - `is_fin_resolved()` function (lines 636-730)

### Proposed Changes:

```python
def categorize_fin_outcome(conversation: Dict[str, Any]) -> Dict[str, Any]:
    """
    Categorize Fin outcome with nuance.
    
    Returns dict with:
    - outcome: 'resolved' | 'escalated' | 'failed'
    - reason: explanation
    - confidence: float (0-1)
    """
    # Step 1: Check for human admin response
    parts = conversation.get('conversation_parts', {})
    if isinstance(parts, dict):
        parts_list = parts.get('conversation_parts', [])
    else:
        parts_list = parts if isinstance(parts, list) else []
    
    admin_parts = [p for p in parts_list if p.get('author', {}).get('type') == 'admin']
    
    # Filter out Sal (Fin AI) from admin parts
    human_admin_parts = [
        p for p in admin_parts 
        if not _is_sal_or_fin(p.get('author', {}))
    ]
    
    has_human_response = len(human_admin_parts) > 0
    
    # Step 2: Get signals
    state = conversation.get('state', 'open')
    is_closed = state == 'closed'
    
    rating_data = conversation.get('conversation_rating')
    if isinstance(rating_data, dict):
        rating = rating_data.get('rating')
    else:
        rating = rating_data if isinstance(rating_data, (int, float)) else None
    
    has_bad_rating = rating is not None and rating < 3
    
    stats = conversation.get('statistics', {}) or {}
    count_reopens = stats.get('count_reopens', 0)
    has_reopens = count_reopens > 1
    
    # Step 3: Categorize outcome
    
    if not has_human_response:
        # No human involved - Fin handled it alone
        if has_bad_rating:
            return {
                'outcome': 'failed',
                'reason': 'Fin tried alone but customer gave bad CSAT',
                'confidence': 0.9
            }
        elif has_reopens:
            return {
                'outcome': 'failed',
                'reason': 'Fin tried alone but conversation reopened multiple times',
                'confidence': 0.8
            }
        elif is_closed or _is_low_engagement(conversation):
            return {
                'outcome': 'resolved',
                'reason': 'Fin resolved without human help',
                'confidence': 0.9
            }
        else:
            return {
                'outcome': 'failed',
                'reason': 'Still open with high engagement but no human help',
                'confidence': 0.7
            }
    
    else:
        # Human admin involved - Was it a correct escalation?
        
        # Check if Fin AI metadata shows explicit escalation
        ai_agent = conversation.get('ai_agent', {}) or {}
        resolution_state = ai_agent.get('resolution_state', '')
        
        if resolution_state == 'routed_to_team':
            # Intercom explicitly says Fin routed to team
            if has_bad_rating:
                return {
                    'outcome': 'failed',
                    'reason': 'Fin escalated but customer still gave bad CSAT',
                    'confidence': 0.8
                }
            else:
                return {
                    'outcome': 'escalated',
                    'reason': 'Fin correctly recognized need for human help',
                    'confidence': 0.9
                }
        
        # No explicit routing - infer based on signals
        if has_bad_rating:
            return {
                'outcome': 'failed',
                'reason': 'Human helped but customer still gave bad CSAT',
                'confidence': 0.7
            }
        elif has_reopens:
            return {
                'outcome': 'failed',
                'reason': 'Required human help and multiple reopens',
                'confidence': 0.7
            }
        else:
            # Human helped, no bad signals
            return {
                'outcome': 'escalated',
                'reason': 'Appropriately escalated to human team',
                'confidence': 0.8
            }


def _is_low_engagement(conversation: Dict[str, Any]) -> bool:
    """Check if conversation has low engagement (<=2 user messages)."""
    parts = conversation.get('conversation_parts', {})
    if isinstance(parts, dict):
        parts_list = parts.get('conversation_parts', [])
    else:
        parts_list = parts if isinstance(parts, list) else []
    
    user_parts = [p for p in parts_list if p.get('author', {}).get('type') == 'user']
    return len(user_parts) <= 2
```

### Updated Metrics:

Instead of:
```python
resolution_rate = resolved / total
escalation_rate = escalated / total  # treated as bad
```

Show:
```python
resolved_rate = resolved / total              # ✅ Good
escalated_correctly_rate = escalated / total  # ✅ Also good! (Fin knows limits)
failed_rate = failed / total                  # ❌ Bad

# Combined success rate
fin_success_rate = (resolved + escalated_correctly) / total
```

### Narrative Changes:

**Before:**
> "Fin escalated 45% of conversations" ❌ (sounds bad)

**After:**
> "Fin resolved 35% independently and correctly escalated 45% to human experts" ✅ (80% success!)

## Files to Modify:

1. **`src/services/fin_escalation_analyzer.py`**
   - Add `categorize_fin_outcome()` function
   - Update `is_fin_resolved()` to use new logic
   - Update `has_knowledge_gap()` to only flag true failures

2. **`src/agents/fin_performance_agent.py`**
   - Update metrics calculation
   - Update narrative generation
   - Show three-way breakdown: resolved | escalated | failed

3. **`src/utils/fin_metrics_calculator.py`**
   - Update `_calculate_quality_adjusted()` to use new categorization
   - Add separate rates for each outcome

4. **Report templates**
   - Update language to distinguish escalation vs failure
   - Celebrate correct escalations as a positive signal

## Expected Impact:

### Before:
```
Fin Resolution Rate: 55%
Escalation Rate: 45% ❌
```

### After:
```
Fin Success Rate: 80% ✅
  ├─ Resolved independently: 35%
  ├─ Correctly escalated: 45%
  └─ Failed: 20% ❌
```

---

**This matches how Intercom represents it: what gets passed (escalated) vs what doesn't (resolved).**

