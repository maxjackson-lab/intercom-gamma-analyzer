# Multi-Agent System Restoration Plan
**Date:** 2025-10-31  
**Issue:** Lost functionality after SDK migration - 47% Unknown topics, no subcategories, no links, no quotes  

---

## What We Lost in SDK Migration

### ❌ Lost Feature 1: Subcategory Breakdown
**Pre-SDK:**
- "Billing → Refund" (441 convs, 44.6%)
- "Billing → Invoice" (164 convs, 16.6%)
- "Billing → Credits" (118 convs, 11.9%)

**Current Multi-Agent:**
- Just "Billing: 2145 conversations (35.4%)"
- No subcategory breakdown shown

**Root Cause:** 
- `TaxonomyManager` exists with 100+ subcategories but isn't integrated
- `TopicDetectionAgent` uses simple 12-topic list
- `SubTopicDetectionAgent` extracts from Intercom `topics.topics`, `tags`, `custom_attributes` but this data may be missing/different in SDK

---

### ❌ Lost Feature 2: Intercom Conversation Links
**Pre-SDK:**
```
Examples:
1. "I want a refund..." - View conversation (clickable link)
2. "Invoice is wrong..." - View conversation
```

**Current Multi-Agent:**
```
Examples:
- "No preview available..." - View conversation (#)
```

**Root Cause:**
- `ExampleExtractionAgent` **does** generate links (line 355-362)
- But depends on `settings.intercom_workspace_id` being set
- Links showing "#" suggests `INTERCOM_WORKSPACE_ID` env var not set or examples aren't being extracted

---

### ❌ Lost Feature 3: Quote Translation
**Pre-SDK:**
- Shows original language quote
- Shows English translation
- Labels language

**Current Multi-Agent:**
- "No preview available"

**Root Cause:**
- `QuoteTranslator` exists and is called (ExampleExtractionAgent line 214)
- But examples aren't being extracted because upstream agents are failing

---

### ❌ Lost Feature 4: Rich Taxonomy Classification
**Pre-SDK (from TaxonomyManager):**
- 13 primary categories
- 100+ subcategories
- Confidence thresholds per category
- Keyword matching + content analysis

**Current Multi-Agent:**
- 12 simple topics (no subcategories in TopicDetectionAgent)
- SubTopicDetectionAgent exists but extracts from Intercom data, not TaxonomyManager

**Root Cause:**
- TaxonomyManager not integrated into TopicDetectionAgent
- Multi-agent system bypasses the rich taxonomy you built

---

## Root Cause: Cascading Failure

```
TopicDetectionAgent FAILS
    ↓
No topics detected (0 topics)
    ↓
SubTopicDetectionAgent gets empty input → FAILS
    ↓
ExampleExtractionAgent never called (no topics to process)
    ↓
No examples = No Intercom links = No quotes
    ↓
OutputFormatterAgent gets empty data
    ↓
Result: Generic Fin analysis only, no topic breakdown
```

---

## Diagnosis: Why Is TopicDetectionAgent Failing?

From the error logs:
```
TopicDetectionAgent - ERROR - TopicDetectionAgent error: 'fallback'
Status: Failed
```

### Issue 1: KeyError on 'fallback' (FIXED)
✅ I just fixed this - method name compatibility issue

### Issue 2: Attribute Detection Bug (FIXED)  
✅ Fixed: `in attributes.values()` instead of `in attributes`

### Issue 3: Conversations May Not Have Intercom Topics/Tags
**Hypothesis:** SDK payloads might not include `topics.topics` or populated `custom_attributes`

**Need to verify:**
```python
# What does the SDK actually return?
conversation = {
    'id': '12345',
    'custom_attributes': {???},  # What's actually here?
    'tags': {???},  # Are tags populated?
    'topics': {???},  # Does this exist in SDK response?
    'conversation_topics': {???},  # Alternative field?
}
```

---

## Investigation Steps

### Step 1: Check What SDK Actually Returns ✅ LOGGING ADDED

Added debug logging (commit 40beb75) that will show:
```
🔍 Topic Detection Debug for 215471442509917:
   Custom Attributes: {actual SDK data}
   Attribute Values: [actual values]
   Tags: [actual tags]
   Text Length: XXX chars
   Text Preview: {actual text}
```

### Step 2: Check Intercom Workspace ID

```bash
# Is this set in your .env?
echo $INTERCOM_WORKSPACE_ID
```

If not set → Links will show `[WORKSPACE_ID]` placeholder

### Step 3: Verify Topics Field Structure

The SDK might return topics in different places:
- `conversation.topics.topics` (nested dict)
- `conversation.conversation_topics` (top-level)
- `conversation.custom_attributes.Category` (in attributes)
- `conversation.tags.tags[].name` (in tags)

---

## Restoration Plan

### Fix 1: Verify SDK Topic Field Extraction ⚡ PRIORITY 1

**Check:** Does the SDK include `topics` or `conversation_topics` in the payload?

**File:** `src/agents/subtopic_detection_agent.py` line 67

**Current code:**
```python
# Extract topic names from topics.topics or conversation_topics
```

**Need to verify:**
- Is `conv.get('topics')` populated?
- Is `conv.get('conversation_topics')` populated?
- Or are topics only in `custom_attributes` or `tags`?

**Fix if needed:**
```python
def _extract_intercom_topics(self, conv: Dict) -> List[str]:
    """Extract topics from all possible SDK locations"""
    topics = []
    
    # Method 1: conversation.topics.topics
    topics_data = conv.get('topics', {})
    if isinstance(topics_data, dict):
        topic_list = topics_data.get('topics', [])
        topics.extend([t.get('name', t) if isinstance(t, dict) else t for t in topic_list])
    
    # Method 2: conversation.conversation_topics
    conv_topics = conv.get('conversation_topics', [])
    topics.extend([t.get('name', t) if isinstance(t, dict) else t for t in conv_topics])
    
    # Method 3: custom_attributes with topic-like keys
    attrs = conv.get('custom_attributes', {})
    if isinstance(attrs, dict):
        for key in ['Category', 'Topic', 'Type', 'Issue']:
            if key in attrs:
                topics.append(attrs[key])
    
    return list(set(topics))  # Deduplicate
```

---

### Fix 2: Integrate TaxonomyManager into TopicDetectionAgent ⚡ PRIORITY 2

**Problem:** TopicDetectionAgent uses simple 12-topic dict, ignoring TaxonomyManager

**Solution:** Replace simple topics dict with TaxonomyManager

**File:** `src/agents/topic_detection_agent.py`

**Changes:**
```python
from src.config.taxonomy import TaxonomyManager

class TopicDetectionAgent(BaseAgent):
    def __init__(self):
        super().__init__(...)
        
        # NEW: Use TaxonomyManager instead of hardcoded topics
        self.taxonomy_manager = TaxonomyManager()
        
        # Build topic definitions from taxonomy
        self.topics = self._build_topics_from_taxonomy()
    
    def _build_topics_from_taxonomy(self) -> Dict:
        """Convert TaxonomyManager categories to topic detection format"""
        topics = {}
        
        for category_name, category in self.taxonomy_manager.categories.items():
            topics[category_name] = {
                'attribute': category_name,  # Look for category name in attributes
                'keywords': category.keywords,
                'priority': 2,  # Default priority
                'subcategories': category.subcategories  # PRESERVE subcategories!
            }
        
        return topics
```

**Benefits:**
- 13 categories + 100+ subcategories restored
- Taxonomy maintained in one place
- Easy to update taxonomy without touching agent code

---

### Fix 3: Ensure INTERCOM_WORKSPACE_ID is Set ⚡ PRIORITY 3

**File:** `.env` or environment variables

**Required:**
```bash
INTERCOM_WORKSPACE_ID=99cd7132_0d87_4553_b1a4_f53e87069b6c
```

**Why:** Without this, links show placeholder:
```
https://app.intercom.com/a/apps/[WORKSPACE_ID]/inbox/inbox/12345
```

---

### Fix 4: Handle Missing customer_messages Field ⚡ PRIORITY 4

**Problem:** We removed `customer_messages` from test data, but it needs to be injected during preprocessing

**Current:** DataPreprocessor injects it (✅ Already done in our fixes)

**Verify:** Ensure preprocessing is running BEFORE agents:
- `elt_pipeline.py` - ✅ Added
- `chunked_fetcher.py` - ✅ Already had it
- `voice_of_customer_analysis()` uses ChunkedFetcher ✅

**But:** ExampleExtractionAgent scoring depends on `customer_messages`:
```python
customer_msgs = conv.get('customer_messages', [])
if not isinstance(customer_msgs, list):
    return 0.0  # Invalid format
```

**Fix if needed:** Ensure all conversations are preprocessed before reaching agents

---

### Fix 5: Verify SubTopicDetectionAgent is Getting Data ⚡ PRIORITY 5

**File:** `src/agents/subtopic_detection_agent.py` lines 195-280

**Check:** Is it actually extracting Tier 2 subtopics from:
- `custom_attributes` (filtered by whitelist)
- `tags.tags`
- `topics.topics` or `conversation_topics`

**Add logging:**
```python
def _detect_tier2_subtopics(self, convs: List[Dict], tier1_topic: str) -> Dict:
    """Extract Tier 2 from Intercom structured data"""
    
    # Log what we're seeing in the data
    self.logger.info(f"Extracting Tier 2 for {tier1_topic} from {len(convs)} conversations")
    
    sample_conv = convs[0] if convs else {}
    self.logger.debug(f"Sample conversation structure:")
    self.logger.debug(f"   custom_attributes: {sample_conv.get('custom_attributes', {})}")
    self.logger.debug(f"   tags: {sample_conv.get('tags', {})}")
    self.logger.debug(f"   topics: {sample_conv.get('topics', {})}")
    self.logger.debug(f"   conversation_topics: {sample_conv.get('conversation_topics', [])}")
    
    # ... rest of extraction logic
```

---

## Expected Impact After Fixes

### Before (Current State)
```
Topics Identified: 0 categories
Unknown/unresponsive: 47.1%
No subcategories
No conversation links
No quotes
```

### After (Expected)
```
Topics Identified: 8-12 categories
Unknown/unresponsive: <20%

Billing: 2,145 conversations (35.4%)
├─ Refund: 441 (44.6%)
├─ Invoice: 164 (16.6%)
├─ Domain: 127 (12.8%)
└─ Credits: 118 (11.9%)

Product Question: 833 conversations (13.8%)
├─ Domain: 74 (15.0%)
├─ Invoices: 59 (12.0%)
└─ Refund: 57 (11.6%)

Examples with links:
1. "I accidentally subscribed to annual..." - View conversation (working link)
2. "환불 부탁드립니다..." → "Please refund..." - View conversation
```

---

## Action Items

### Immediate (Can Do Now)
1. ✅ **Check INTERCOM_WORKSPACE_ID** - Verify env var is set
2. ✅ **Re-run analysis** - See if attribute fix helps (already pushed)
3. ✅ **Check logs** - New debug logging will show what SDK returns

### Short-Term (1-2 hours)
4. ⏳ **Integrate TaxonomyManager** - Replace simple topics with full taxonomy
5. ⏳ **Verify SDK fields** - Check if `topics`, `conversation_topics`, `tags` are populated
6. ⏳ **Add robust field extraction** - Handle multiple SDK field locations
7. ⏳ **Test subcategory detection** - Verify Tier 2/Tier 3 hierarchy works

### Medium-Term (Investigation Required)
8. ⏳ **Compare SDK response to pre-SDK** - Document field structure changes
9. ⏳ **Update field extraction logic** - Adapt to SDK payload structure
10. ⏳ **Restore all features** - Verify links, quotes, translations, taxonomy all work

---

## Key Questions to Answer (Via Logs)

When you re-run the analysis, the logs will tell us:

1. **What does `custom_attributes` actually contain?**
   ```
   Custom Attributes: {'Language': 'English', 'tier': 'pro', ...?}
   ```

2. **Are tags populated?**
   ```
   Tags: ['Billing', 'Refund', 'urgent']  OR  Tags: []
   ```

3. **Do we get `topics` or `conversation_topics`?**
   ```
   Does the SDK include these fields?
   ```

4. **Why is text empty for some conversations?**
   ```
   ❌ TEXT IS EMPTY! → Need to investigate extract_conversation_text()
   ```

5. **Is INTERCOM_WORKSPACE_ID set?**
   ```
   Links showing: https://app.intercom.com/a/apps/[WORKSPACE_ID]/... → Not set
   Links showing: https://app.intercom.com/a/apps/99cd7132.../... → Set correctly
   ```

---

## My Hypothesis

Based on the architecture and your comments, I believe:

1. **TopicDetectionAgent was failing** due to the `in attributes` bug (fixed) and 'fallback' KeyError (fixed)
2. **With those fixes**, topic detection should work, BUT...
3. **SDK might not return the same fields** that the pre-SDK version had:
   - Pre-SDK might have tagged conversations with category names
   - SDK might not include those tags/topics in the response
   - May need to fetch additional data or use different fields

4. **Once topics are detected**, the downstream agents (SubTopic, Examples, etc.) should work automatically:
   - SubTopicDetectionAgent will extract Tier 2 from Intercom data
   - ExampleExtractionAgent will create links and extract quotes
   - OutputFormatterAgent will format everything nicely

---

## Next Steps

### Option A: Re-run Analysis First (Recommended)
**Why:** The logs will tell us what the SDK actually returns

**Command:**
```bash
python src/main.py voice-of-customer --start-date 2025-10-24 --end-date 2025-10-30 --verbose
```

**Look for:**
- Debug logs showing `custom_attributes`, `tags`, `topics` structure
- Warning logs showing "NO TOPICS DETECTED" with diagnostics
- Method breakdown showing attribute vs keyword detection rates

### Option B: Integrate TaxonomyManager Now (Proactive)
**Why:** Restore the 100+ subcategory taxonomy regardless of SDK fields

**Files to modify:**
1. `src/agents/topic_detection_agent.py` - Use TaxonomyManager
2. `src/agents/subtopic_detection_agent.py` - Map to TaxonomyManager subcategories
3. `src/agents/topic_orchestrator.py` - Pass taxonomy through

### Option C: Both (Most Thorough)
1. Re-run to see what SDK returns
2. Based on logs, integrate TaxonomyManager properly
3. Adapt field extraction to SDK structure
4. Restore all features

---

## Which Would You Prefer?

**A)** Re-run analysis and show me the logs → I'll diagnose from real data  
**B)** Integrate TaxonomyManager now → Restore subcategories immediately  
**C)** Both → Most thorough but takes longer  

The logs will tell us the truth about what's broken!


