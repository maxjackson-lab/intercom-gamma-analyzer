# Sample Mode Guide 🔬

## What is Sample Mode?

**Sample Mode** pulls 50-100 **REAL conversations** from Intercom with **ultra-rich logging** to help you:

- ✅ Validate schema assumptions
- ✅ Debug topic detection issues  
- ✅ Test fixes quickly (no 5k+ conversation runs)
- ✅ See what `custom_attributes` actually contain
- ✅ Verify Sal vs Human detection
- ✅ Check keyword matching in real data

**Speed:** ~10-30 seconds (vs 2-5 minutes for full analysis)

---

## How to Use

### **Web UI (Easiest)**

1. Go to Railway web app
2. Select **"🔬 Sample Mode"** from dropdown
3. Choose time period (day/week/month)
4. Click **"Run Analysis"**
5. Check console for ultra-rich logging

### **Command Line**

```bash
# Pull 50 conversations from last week
python src/main.py sample-mode --count 50 --time-period week

# Custom date range
python src/main.py sample-mode --count 100 --start-date 2025-10-26 --end-date 2025-11-01

# Don't save JSON (console only)
python src/main.py sample-mode --count 50 --no-save
```

---

## What You'll See

### **1. Field Coverage Analysis**

Shows which Intercom fields are present across conversations:

```
┌─────────────────────┬─────────┬─────────┬───────┐
│ Field               │ Present │ Missing │ %     │
├─────────────────────┼─────────┼─────────┼───────┤
│ id                  │ 50      │ 0       │ 100%  │
│ created_at          │ 50      │ 0       │ 100%  │
│ custom_attributes   │ 18      │ 32      │ 36%   │ ← KEY INSIGHT!
│ ai_agent_participated│ 47     │ 3       │ 94%   │
│ tags                │ 12      │ 38      │ 24%   │
│ topics              │ 5       │ 45      │ 10%   │
└─────────────────────┴─────────┴─────────┴───────┘
```

**Insight:** Only 36% have `custom_attributes` - this is why attribute-based detection fails!

### **2. Custom Attributes Deep Dive**

Shows what keys and values actually exist:

```
┌──────────────────────┬───────┬───────┬─────────────────────────┐
│ Key                  │ Count │ %     │ Sample Values           │
├──────────────────────┼───────┼───────┼─────────────────────────┤
│ Language             │ 50    │ 100%  │ English, Spanish, French│
│ Reason for contact   │ 12    │ 24%   │ Billing, Bug, Account   │ ← Important!
│ Category             │ 8     │ 16%   │ Billing, Bug            │
│ tier                 │ 45    │ 90%   │ pro, plus, free         │
│ Fin AI Agent: Preview│ 40    │ 80%   │ True, False             │
└──────────────────────┴───────┴───────┴─────────────────────────┘
```

**Insight:** "Reason for contact" only appears in 24% of conversations!

### **3. Agent Attribution Analysis**

Shows Sal vs Human breakdown:

```
┌────────────────────┬───────┬───────┬─────────────────────────────┐
│ Agent Type         │ Count │ %     │ Note                        │
├────────────────────┼───────┼───────┼─────────────────────────────┤
│ Support Sal        │ 37    │ 74%   │ ✅ Should be ~75% if working│
│ Human Admin        │ 12    │ 24%   │ ✅ Should be ~25%           │
│ Bot (No Sal)       │ 1     │ 2%    │ Old Fin format              │
│ No Admin Response  │ 0     │ 0%    │ User-only messages          │
└────────────────────┴───────┴───────┴─────────────────────────────┘
```

**Validation:** ✅ 74% Sal matches expected ~75%!

### **4. Conversation Samples (First 5)**

Ultra-detailed view of each conversation:

```
================================================================================
CONVERSATION #1: 215471549580197
================================================================================

BASIC INFO:
  ID: 215471549580197
  State: closed
  Created: 2025-10-28 15:23:45
  Tier: Pro
  Admin Assigned ID: None
  AI Agent Participated: True

CUSTOM ATTRIBUTES:
  Language: English
  Fin AI Agent: Preview: True
  Copilot used: False
  (no Category or Reason for contact)  ← KEY INSIGHT!

TAGS:
  (empty)  ← No tags!

TOPICS:
  (empty)  ← No topics!

CONVERSATION PARTS:
  Part 1:
    Type: user
    Name: (no name)
    Email: customer@example.com
    Body: I need a refund for my annual subscription...

  Part 2:
    Type: admin
    Name: Support Sal  ← ✅ DETECTED AS SAL (Fin AI)
    Email: sal@gamma.app
    ID: sal_12345

KEYWORD DETECTION TEST:
  Billing: ['refund', 'subscription']  ← ✅ Keywords work!
  
================================================================================
```

**Insight:** This conversation has NO custom_attributes or tags, but keywords correctly detect "Billing"!

---

## Use Cases

### **Scenario 1: Validate Sal Detection**

```bash
python src/main.py sample-mode --count 50
```

**Look for:**
- Agent Attribution table showing ~75% Sal
- Sample Sal conversation showing `name: "Support Sal"`
- Verification that Sal is marked as "admin" type

### **Scenario 2: Debug Topic Detection**

```bash
python src/main.py sample-mode --count 100 --time-period week
```

**Look for:**
- How many conversations have `custom_attributes`
- What keys appear in `custom_attributes`
- Whether "Reason for contact" or "Category" fields exist
- Keyword detection test results

### **Scenario 3: Test Keyword Boundaries**

Check if edge cases work:

**Expected:**
- ✅ "invoice" matches Billing
- ✅ "refund" matches Billing  
- ❌ "final" does NOT match "fin"
- ❌ "daily" does NOT match "ai"
- ❌ "speak to an agent" does NOT match Agent/Buddy

### **Scenario 4: Verify Hybrid Detection**

If conversation has BOTH keywords AND custom_attributes:

```
Billing: ['invoice', 'payment']  ← Keywords
  + custom_attributes['Category'] = 'Billing'  ← SDK
  = HYBRID detection with 95% confidence ✅
```

---

## Output Files

### **Console Output**

- Rich tables and panels
- Color-coded insights
- Real-time analysis
- Validation checks

### **JSON File** (if --save-to-file)

Location: `outputs/sample_mode_YYYYMMDD_HHMMSS.json`

Contains:
```json
{
  "metadata": {
    "count": 50,
    "timestamp": "2025-11-02T...",
    "date_range": {...}
  },
  "conversations": [...],  // Full raw conversations
  "analysis": {
    "field_coverage": {...},
    "custom_attributes": {...},
    "agent_attribution": {...}
  }
}
```

**Use this file to:**
- Inspect raw Intercom data structure
- Share with team for schema validation
- Debug unexpected field formats
- Document real data examples

---

## When to Use

| Situation | Use Sample Mode? |
|-----------|------------------|
| Testing a fix | ✅ YES - Quick validation |
| Debugging 46% Unknown | ✅ YES - See real attribute coverage |
| Validating Sal detection | ✅ YES - Check agent attribution |
| Schema questions | ✅ YES - See raw field structure |
| Full production run | ❌ NO - Use normal VoC analysis |
| Historical comparison | ❌ NO - Need full dataset |

---

## Comparison: Sample Mode vs Test Mode vs Full Analysis

| Feature | Sample Mode | Test Mode | Full Analysis |
|---------|-------------|-----------|---------------|
| **Data Source** | 50-100 REAL tickets | Mock data | 5000+ real tickets |
| **Speed** | ~10-30 seconds | ~5 seconds | ~2-5 minutes |
| **Purpose** | Schema validation | Unit testing | Production insights |
| **Logging** | Ultra-rich | Standard | Standard |
| **Cost** | ~1-2 API calls | Zero API calls | ~100+ API calls |
| **When to Use** | Debugging, validation | Code testing | Production reports |

---

## Troubleshooting

### **No Sal detected**

If agent attribution shows 0% Sal:
1. Check conversation parts for `type: 'admin'` with `name: 'Support Sal'`
2. Verify `is_sal_or_fin()` function is working
3. Look for alternative Sal names/emails

### **All conversations have empty custom_attributes**

This is NORMAL! Most real conversations don't have metadata.
- Proves keyword detection is critical
- Shows why attribute-first detection failed
- Validates hybrid approach

### **Topic detection still shows Unknown**

1. Check keyword detection test in console
2. Verify word boundaries are working
3. Expand keywords in taxonomy.yaml
4. Look at actual message text to add missing keywords

---

## Example Session

```bash
$ python src/main.py sample-mode --count 50

🔬 SAMPLE MODE: Real Data Extraction
Pulling 50 random conversations
Date range: 2025-10-26 to 2025-11-02
With ULTRA-RICH logging for schema validation

📥 Fetching conversations from Intercom...
✅ Fetched 50 conversations

================================================================================
📊 FIELD COVERAGE ANALYSIS
================================================================================

[Tables showing which fields exist...]

================================================================================
🔍 CUSTOM ATTRIBUTES DEEP DIVE
================================================================================

Total conversations with custom_attributes: 18 (36%)
Unique attribute keys: 12

[Table showing attribute keys and sample values...]

================================================================================
👤 AGENT ATTRIBUTION ANALYSIS
================================================================================

[Table showing Sal vs Human breakdown...]

Sample Sal Conversation:
  Name: Support Sal
  Email: sal@gamma.app
  Type: admin

================================================================================
📝 CONVERSATION SAMPLES (First 5)
================================================================================

[Ultra-detailed view of 5 conversations...]

💾 Raw data saved to: outputs/sample_mode_20251102_143045.json

✅ Sample mode complete!
Analyzed 50 conversations
Key Findings:
  Sal conversations: 37 (74%)
  Human admin: 12 (24%)
  With custom_attributes: 18 (36%)
```

---

## Pro Tips

1. **Run after every fix** - Quick validation cycle
2. **Save the JSON** - Document what real data looks like
3. **Compare before/after** - Track improvements
4. **Share with team** - Show real Intercom structure
5. **Random sampling** - Gets diverse conversation types

---

## Next Steps After Sample Mode

1. **If Sal detection works (74-76%):** ✅ Deploy fix with confidence
2. **If custom_attributes are sparse (<40%):** ✅ Rely on keywords
3. **If Unknown rate is high:** Add missing keywords to taxonomy
4. **If confident in fixes:** Run full analysis to validate at scale

Sample Mode = **Your debugging secret weapon!** 🎯

