# Worst CSAT Examples Feature - Egregious Ticket Tracking

**Added**: October 25, 2025  
**Purpose**: Catch and highlight the most problematic customer satisfaction issues for immediate coaching

## 🎯 **Problem Solved**

As you noted: **"The most important thing is catching poor CSAT tickets that seem especially egregious and having those links."**

Previously, we showed aggregate CSAT scores, but coaches couldn't easily find the **specific terrible conversations** that needed immediate attention.

## ✅ **Solution**

Now, for each agent with low CSAT, we automatically extract and display:
- **Top 5 worst CSAT conversations** (1-2 star ratings)
- **Direct Intercom conversation URLs** for immediate review
- **Customer complaint excerpt** (what went wrong)
- **Category/subcategory** (what topic was mishandled)
- **Red flags** (Reopened? Escalated?)

---

## 📊 **Example Output**

### **Agent Coaching Report**

```
🎯 COACHING PRIORITY: HIGH - Lorna

⚠️ URGENT: Low CSAT (3.07) - Review worst tickets immediately

📋 Worst CSAT Examples (5 tickets requiring immediate review):

1. ⭐ 1-Star Rating | Billing>Refund
   🔗 https://app.intercom.com/a/inbox/abc123/inbox/conversation/456789
   💬 Customer: "This is absolutely ridiculous. I've been waiting 3 days 
       for a refund that should have been processed immediately. The agent 
       just kept giving me the same copy-paste answer..."
   🚩 Reopened, Escalated
   
2. ⭐ 1-Star Rating | Bug>Export
   🔗 https://app.intercom.com/a/inbox/abc123/inbox/conversation/456790
   💬 Customer: "Your agent didn't even try to help. Just said 'it's a known 
       issue' and closed the ticket. My presentation is due tomorrow and I 
       can't export it!"
   🚩 Escalated
   
3. ⭐⭐ 2-Star Rating | Account>Password
   🔗 https://app.intercom.com/a/inbox/abc123/inbox/conversation/456791
   💬 Customer: "Agent was rude and dismissive. Kept telling me to 'just reset 
       it' without actually reading that I already tried that 3 times..."
   🚩 Reopened

4. ⭐ 1-Star Rating | Bug>Editor
   🔗 https://app.intercom.com/a/inbox/abc123/inbox/conversation/456792
   💬 Customer: "No troubleshooting whatsoever. Agent didn't ask for screenshots,
       didn't ask what browser, didn't offer any solutions. Just escalated."
   🚩 Escalated

5. ⭐⭐ 2-Star Rating | Product Question>Features
   🔗 https://app.intercom.com/a/inbox/abc123/inbox/conversation/456793  
   💬 Customer: "Agent clearly didn't understand the question and gave me 
       information about a completely different feature..."
   
📈 Pattern Analysis:
   - 3/5 tickets escalated without troubleshooting
   - 2/5 tickets reopened (incomplete resolution)
   - Common themes: Lack of empathy, premature escalation, no diagnostic questions

🎯 Coaching Actions:
   1. Review all 5 tickets with Lorna in 1-on-1 session
   2. Identify what went wrong in each case
   3. Role-play alternative responses
   4. Establish troubleshooting checklist before escalating
```

---

## 🔍 **What Gets Captured**

For each worst CSAT ticket:

| Field | Description | Example |
|-------|-------------|---------|
| **Rating** | 1-2 stars | ⭐ 1-Star |
| **URL** | Direct Intercom link | `https://app.intercom.com/...` |
| **Category** | Topic handled poorly | `Billing>Refund` |
| **Complaint** | First 200 chars of customer message | "This is absolutely ridiculous..." |
| **Red Flags** | Reopened? Escalated? | `🚩 Reopened, Escalated` |

---

## 🎯 **Coaching Priority Impact**

### **New Rules:**
Agents are automatically flagged as **HIGH PRIORITY** if:
- CSAT score < 3.5 with ≥5 surveys
- ≥3 negative CSAT ratings (1-2 stars)
- Previous rules (low FCR, high escalation) still apply

### **Coaching Focus Areas Now Include:**
```
📋 Coaching Focus Areas:
1. URGENT: Low CSAT (3.07) - Review worst tickets immediately  ← NEW
2. Customer Satisfaction (7 negative ratings)  ← NEW
3. Billing>Refund (weak subcategory)
4. Bug>Export (weak subcategory)
```

---

## 💡 **Why This Matters**

### **Before:**
```
❌ "Lorna has a 3.07 CSAT score"
   → Okay... but what specifically went wrong?
   → Can't give concrete feedback
   → Can't show specific examples in coaching session
```

### **After:**
```
✅ "Lorna has a 3.07 CSAT score. Here are 5 specific tickets to review:"
   → Conversation #456789: Gave copy-paste answer, no empathy
   → Conversation #456790: Didn't troubleshoot, just escalated
   → Conversation #456791: Tone was dismissive
   → Now you can review EXACT conversations in coaching session
   → Can role-play better responses
```

---

## 🧪 **Technical Implementation**

### **Method: `_find_worst_csat_examples()`** (Lines 542-615)

```python
def _find_worst_csat_examples(self, rated_convs, ratings):
    """
    Find worst CSAT conversations for coaching.
    
    Returns top 3-5 most egregious low-CSAT tickets with:
    - Conversation URL
    - CSAT rating  
    - Brief customer complaint/issue
    - Category (if available)
    
    Prioritizes 1★ over 2★ ratings.
    """
    # Filter to 1-2 star ratings only
    low_csat_convs = [c for c in rated_convs if c.get('conversation_rating') <= 2]
    
    # Sort by rating (worst first)
    low_csat_convs.sort(key=lambda c: c.get('conversation_rating'))
    
    # Build examples for top 5 worst
    examples = []
    for conv in low_csat_convs[:5]:
        examples.append({
            'url': self._build_intercom_url(conv_id),
            'rating': int(rating),
            'category': category_label,
            'complaint': customer_message[:200],
            'red_flags': ['Reopened', 'Escalated'] if applicable
        })
    
    return examples
```

---

## 📈 **Usage**

### **Individual Agent Breakdown:**
```bash
python src/main.py agent-performance --agent horatio --individual-breakdown --time-period week
```

**Output includes:**
- Per-agent CSAT scores
- **Worst CSAT examples with URLs** ← NEW
- Coaching priorities based on CSAT

### **Coaching Report:**
```bash
python src/main.py agent-coaching-report --vendor horatio --time-period week
```

**Output includes:**
- Agents needing coaching (low CSAT flagged)
- **Direct links to worst tickets** ← NEW
- Concrete examples for coaching sessions

---

## 🎯 **JSON Output Structure**

```json
{
  "agent_name": "Lorna",
  "csat_score": 3.07,
  "negative_csat_count": 7,
  "worst_csat_examples": [
    {
      "url": "https://app.intercom.com/a/inbox/abc123/inbox/conversation/456789",
      "rating": 1,
      "category": "Billing>Refund",
      "complaint": "This is absolutely ridiculous. I've been waiting 3 days...",
      "red_flags": ["Reopened", "Escalated"],
      "conversation_id": "456789"
    },
    {
      "url": "https://app.intercom.com/a/inbox/abc123/inbox/conversation/456790",
      "rating": 1,
      "category": "Bug>Export",
      "complaint": "Your agent didn't even try to help. Just said it's a known...",
      "red_flags": ["Escalated"],
      "conversation_id": "456790"
    }
  ]
}
```

---

## 🔄 **Future Enhancement Ideas**

1. **AI Analysis of Worst Tickets** (Phase 3)
   - Automatically classify what went wrong
   - "Premature escalation" | "Lack of empathy" | "Didn't troubleshoot"
   - Generate coaching recommendations automatically

2. **Trend Tracking**
   - Is this agent's worst CSAT getting better/worse?
   - Are the same categories showing up repeatedly?

3. **Team Patterns**
   - Common themes across all worst CSATs
   - Are multiple agents struggling with same issue?

---

## ✅ **Checklist**

- [x] `worst_csat_examples` field added to IndividualAgentMetrics
- [x] `_find_worst_csat_examples()` method implemented
- [x] Worst examples captured (up to 5 per agent)
- [x] Conversation URLs generated
- [x] Customer complaint excerpt extracted
- [x] Red flags identified (Reopened/Escalated)
- [x] Coaching priority factors in low CSAT
- [x] "URGENT" flag added to coaching areas for low CSAT

---

## 🎉 **Result**

**You now have EXACTLY what you asked for:**

> "Catching poor CSAT tickets that seem especially egregious and having those links"

✅ **Worst 1-2 star tickets automatically identified**  
✅ **Direct Intercom URLs for immediate review**  
✅ **Context included (complaint, category, red flags)**  
✅ **Prioritized for coaching (1-star before 2-star)**  
✅ **Up to 5 examples per agent**  

Coaches can now **immediately click through to the worst conversations** and use them as concrete examples in coaching sessions!

