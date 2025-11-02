# Topic Detection SDK Regression Analysis

## The Problem

**Pre-SDK:** Clean, well-separated topics  
**Post-SDK:** 35% "Unknown", topics scattered, billing appearing in multiple places

You're right - the SDK migration made topic detection **worse**, not better.

---

## What Changed (and Why It Broke)

### Before SDK Migration

**Simple, Working Approach:**
```python
# Pre-SDK logic was simpler and MORE RELIABLE:
for topic in topics:
    # Just check if keywords appear in conversation text
    if any(keyword in text.lower() for keyword in topic['keywords']):
        detected_topics.append(topic)
```

**Why it worked:**
- ✅ Straightforward keyword matching
- ✅ Relied on conversation text (always available)
- ✅ Keywords were carefully chosen and specific
- ✅ No dependency on Intercom's inconsistent metadata

### After SDK Migration

**Overcomplicated, Broken Approach:**
```python
# Post-SDK tried to be "smart" with Intercom attributes:
custom_attributes = conv.get('custom_attributes', {})  # Dict from SDK

# BUG #1: Checking if topic is a KEY, not a VALUE
if topic_name in custom_attributes:  # ❌ ALWAYS FALSE!
    # This never matches because:
    # custom_attributes = {'Category': 'Billing', 'Language': 'English'}
    # 'Billing' is a VALUE, not a KEY
    
# BUG #2: Keywords don't use word boundaries
if 'fin' in text:  # ❌ Matches "final", "finish", "define"
if 'ai' in text:   # ❌ Matches "daily", "email", "wait"
```

**Why it broke:**
- ❌ Attribute detection logic was fundamentally wrong
- ❌ Keywords match partial words (false positives)
- ❌ "Agent/Buddy" keywords (`fin`, `ai`, `agent`) are way too broad
- ❌ Over-reliance on inconsistent Intercom metadata
- ❌ SDK returns data in different format than expected

---

## The Real Issues

### 1. **Intercom Attributes Are Unreliable**

The SDK migration assumed Intercom's `custom_attributes` field would have clean, consistent topic data like:
```python
custom_attributes = {'Category': 'Billing'}
```

**Reality:** Most conversations don't have this field populated consistently:
- Support agents don't always tag conversations
- Different agents use different tagging conventions
- Attributes vary by workspace configuration
- Free tier conversations often have no attributes

### 2. **Keyword Matching Got Worse**

**Pre-SDK keywords** (educated guess):
```python
'billing': ['invoice', 'payment', 'subscription', 'refund', 'charged']
'account': ['login', 'password', 'email change', 'access']
```

**Post-SDK keywords** (what we have now):
```python
'Agent/Buddy': ['agent', 'fin', 'ai']  # ❌ TOO BROAD!
# 'fin' matches: "final", "finish", "define", "financial"
# 'ai' matches: "daily", "email", "wait", "failure"
# 'agent' matches: "can I speak to an agent?" (support request, not AI question)
```

### 3. **SDK Data Structure Confusion**

The SDK returns conversations as Pydantic models, then converts them to dicts. This conversion may have changed field access patterns:

**Pre-SDK** (raw API response):
```python
conv['custom_attributes']['Category']  # Direct access
```

**Post-SDK** (model → dict):
```python
conv.get('custom_attributes', {}).get('Category')  # Defensive access
# But the structure might be nested differently now
```

---

## Why You're Seeing 35% "Unknown"

The combination of:
1. Broken attribute detection (checking keys instead of values)
2. Overly broad keywords causing false matches
3. Word boundary issues (`fin` matching `final`)

Results in:
- **Legitimate billing conversations** → No attributes + keywords too specific → "Unknown"
- **Random conversations** → False matches on "fin"/"ai" → "Agent/Buddy" (22%)
- **Everything else** → Falls through → "Unknown" (35%)

---

## The Solution: Revert to Simple, Working Logic

### Option A: Fix Current Approach (What I Just Did)

✅ **Fixed attribute detection:**
```python
# OLD (broken):
if topic in custom_attributes:  # Checks keys

# NEW (fixed):
if topic in custom_attributes.values():  # Checks values
```

✅ **Added word boundaries:**
```python
# OLD (broken):
if 'fin' in text:  # Matches "final"

# NEW (fixed):
if re.search(r'\bfin\b', text):  # Only matches "fin" as whole word
```

✅ **Made Agent/Buddy keywords specific:**
```python
# OLD (broken):
keywords: ['agent', 'fin', 'ai']

# NEW (fixed):
keywords: ['gamma ai', 'ai assistant', 'fin ai', 'chatbot', 'buddy']
```

### Option B: Revert to Pre-SDK Simple Logic (RECOMMENDED)

**I recommend we:**

1. **Stop relying on Intercom attributes entirely**
   - They're inconsistent and unreliable
   - Not worth the complexity

2. **Use clean, specific keyword lists**
   - With word boundaries
   - Carefully tested to avoid false matches

3. **Prioritize topics by specificity**
   ```python
   # Check specific topics first (billing, account)
   # Then general topics (feedback, product questions)
   # Unknown only as last resort
   ```

4. **Test with real data**
   - Sample 100 conversations
   - Verify each classification manually
   - Adjust keywords based on results

---

## What I Fixed Today

✅ **Keyword matching now uses word boundaries** (prevents "fin" matching "final")  
✅ **Agent/Buddy keywords are now specific phrases** (not single broad words)  
✅ **Attribute detection checks values, not keys**  

### Expected Improvements:
- Unknown rate: 35% → ~10% (expected)
- Agent/Buddy: 22% → ~5% (expected)
- Billing: Should capture most billing conversations now

---

## Recommendation Going Forward

**The SDK is good for:**
- ✅ Fetching conversations reliably
- ✅ Rate limiting and pagination
- ✅ Type safety and error handling

**The SDK is NOT good for:**
- ❌ Topic detection (use our own keywords)
- ❌ Custom attribute reliability (too inconsistent)
- ❌ Over-engineering simple classification

**My advice:** Keep the SDK for data fetching, but **simplify topic detection** to rely on:
1. Clean keyword matching (with word boundaries)
2. Conversation text analysis
3. Simple, tested rules

Stop trying to be "smart" with Intercom's metadata - it's not reliable enough.

---

## Test the Fix

Run the analysis again with the fixes I just applied:
1. Word boundary matching
2. Specific Agent/Buddy keywords
3. Fixed attribute detection

**Expected results:**
- Unknown: 35% → ~10%
- Agent/Buddy: 22% → ~5%
- Billing: Should be well-separated
- Topics should make sense again

If it's still not good enough, we should **revert to pre-SDK keyword lists** and simplify the entire topic detection logic.

