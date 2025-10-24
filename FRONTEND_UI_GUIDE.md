# Frontend UI Guide - All Available Analysis Options

**Updated:** October 24, 2025  
**File:** `deploy/railway_web.py` + `static/app.js`

---

## 🎯 What's NOW Available in the UI

### **📊 Voice of Customer** (3 variants)

1. **VoC: Hilary Format (Topic Cards)** ⭐ DEFAULT
   - Per-topic sentiment cards
   - Paid/Free customer separation
   - 3-10 examples per topic
   - Fin AI performance analysis
   - Command: `voice-of-customer --multi-agent --analysis-type topic-based`

2. **VoC: Synthesis (Cross-cutting Insights)**
   - Strategic insights across categories
   - Operational metrics (FCR, resolution time)
   - Cross-category patterns
   - Command: `voice-of-customer --multi-agent --analysis-type synthesis`

3. **VoC: Complete (Both Formats)**
   - Combines Hilary's cards + Synthesis insights
   - Command: `voice-of-customer --multi-agent --analysis-type complete`

---

### **🏷️ Category Deep Dives** (5 options)

4. **Billing Analysis** - Refunds, subscriptions, payments
5. **Product Feedback** - Feature requests and product questions  
6. **API Issues & Integration** - Developer/integration issues
7. **Escalations** - Escalated conversation analysis
8. **Technical Troubleshooting** - Technical support patterns

---

### **📈 Agent Performance - Team Overview** (3 options)

#### 9. **Horatio: Team Metrics**
   - **What it shows:**
     - Aggregated team FCR and escalation rates
     - Overall team strengths and weaknesses
     - Top categories handled
     - Team highlights and lowlights
   - **Command:** `agent-performance --agent horatio`
   - **Use case:** Weekly team review with management

#### 10. **Boldr: Team Metrics**
   - Same as above for Boldr vendor
   - **Command:** `agent-performance --agent boldr`

#### 11. **Escalated/Senior Staff Analysis** ⭐ NEW
   - Analysis of conversations handled by Max, Dae-Ho, Hilary
   - **Command:** `agent-performance --agent escalated`
   - **Use case:** Understanding escalation patterns

---

### **👤 Agent Performance - Individual Breakdown** ⭐ NEW (2 options)

#### 12. **Horatio: Individual Agents + Taxonomy**
   - **What it shows:**
     - ✅ Per-agent FCR, escalation, response time metrics
     - ✅ Performance breakdown by categories (Billing, Bug, API, etc.)
     - ✅ Performance breakdown by subcategories (Billing>Refund, Bug>Export, etc.)
     - ✅ Strong and weak areas for each agent
     - ✅ Agent rankings and comparisons
     - ✅ Example conversations (best and needs-coaching)
   - **Command:** `agent-performance --agent horatio --individual-breakdown`
   - **Use case:** Identifying which agents excel or struggle in specific categories
   
   **Info Panel Shows:** Blue panel explaining taxonomy breakdown

#### 13. **Boldr: Individual Agents + Taxonomy**
   - Same as above for Boldr vendor
   - **Command:** `agent-performance --agent boldr --individual-breakdown`

---

### **🎯 Agent Coaching Reports** ⭐ NEW (2 options)

#### 14. **Horatio: Coaching & Development**
   - **What it shows:**
     - ✅ Coaching priority (high/medium/low) for each agent
     - ✅ Specific coaching focus areas (weak categories/subcategories)
     - ✅ Praise-worthy achievements to recognize
     - ✅ Top and bottom performers identification
     - ✅ Example conversations for coaching sessions
     - ✅ Team-wide coaching needs and training recommendations
   - **Command:** `agent-coaching-report --vendor horatio`
   - **Use case:** 1-on-1 coaching sessions with specific actionable feedback
   
   **Info Panel Shows:** Amber/yellow panel explaining coaching report contents

#### 15. **Boldr: Coaching & Development**
   - Same as above for Boldr vendor
   - **Command:** `agent-coaching-report --vendor boldr`

---

### **📱 Canny Feedback** (1 option)

16. **Canny Feedback**
    - Analyzes Canny feature requests and votes
    - **Command:** `canny-analysis`

---

## 🆕 What's Different from Yesterday

### Before (Oct 23):
```
Agent Performance:
├─ Horatio Performance Review  → agent-performance --agent horatio
└─ Boldr Performance Review    → agent-performance --agent boldr
```
**Problem:** No way to see individual agent metrics or coaching insights

### After (Oct 24):
```
Agent Performance - Team Overview:
├─ Horatio: Team Metrics                → agent-performance --agent horatio
├─ Boldr: Team Metrics                  → agent-performance --agent boldr
└─ Escalated/Senior Staff Analysis      → agent-performance --agent escalated

Agent Performance - Individual Breakdown: ⭐ NEW
├─ Horatio: Individual Agents + Taxonomy → agent-performance --agent horatio --individual-breakdown
└─ Boldr: Individual Agents + Taxonomy   → agent-performance --agent boldr --individual-breakdown

Agent Coaching Reports: ⭐ NEW
├─ Horatio: Coaching & Development       → agent-coaching-report --vendor horatio
└─ Boldr: Coaching & Development         → agent-coaching-report --vendor boldr
```

---

## 📋 How to Use Each Option

### Scenario 1: "Which topics are customers talking about?"
**Select:** VoC: Hilary Format  
**Output:** Topic cards with sentiment, examples, and volume

### Scenario 2: "How is the Horatio team doing overall?"
**Select:** Horatio: Team Metrics  
**Output:** Team FCR, escalation rates, top categories

### Scenario 3: "Which Horatio agents struggle with billing issues?"
**Select:** Horatio: Individual Agents + Taxonomy ⭐  
**Output:** Per-agent performance in Billing category (and all others)

### Scenario 4: "Who needs coaching and in what areas?"
**Select:** Horatio: Coaching & Development ⭐  
**Output:** Agent rankings, coaching priorities, specific focus areas

### Scenario 5: "What's trending on Canny?"
**Select:** Canny Feedback  
**Output:** Canny posts with sentiment, votes, and engagement

---

## 🎨 UI Enhancements Added

### 1. Dynamic Info Panels
Three contextual info panels that appear based on selection:

**Blue Panel** (Individual Breakdown)
- Shows when "-individual" option selected
- Explains taxonomy breakdown features

**Amber Panel** (Coaching Reports)
- Shows when "coaching" option selected
- Lists coaching report contents

**Green Panel** (Team Overview)
- Shows when "-team" or "escalated" selected
- Explains team-level aggregation

### 2. Clear Naming Convention
- **"Team Metrics"** = Aggregated team data
- **"Individual Agents + Taxonomy"** = Per-agent taxonomy breakdown
- **"Coaching & Development"** = Coaching-focused output

### 3. Automatic Flag Mapping
The runAnalysis() function now automatically adds:
- `--individual-breakdown` for individual options
- `--vendor` for coaching reports
- `--agent` for performance reviews

---

## 🔄 Command Mapping Reference

| UI Option | CLI Command | Key Flags |
|-----------|-------------|-----------|
| Horatio: Team Metrics | `agent-performance` | `--agent horatio` |
| Horatio: Individual + Taxonomy | `agent-performance` | `--agent horatio --individual-breakdown` |
| Horatio: Coaching | `agent-coaching-report` | `--vendor horatio` |
| Boldr: Team Metrics | `agent-performance` | `--agent boldr` |
| Boldr: Individual + Taxonomy | `agent-performance` | `--agent boldr --individual-breakdown` |
| Boldr: Coaching | `agent-coaching-report` | `--vendor boldr` |
| Escalated Analysis | `agent-performance` | `--agent escalated` |

---

## 💡 Pro Tips

### Tip 1: Use Individual Breakdown to Find Expertise
Run "Horatio: Individual Agents + Taxonomy" to see which agents excel in specific categories. Example output:
```
Agent: Maria Rodriguez
├─ Strong Categories: Billing, Account, Product Question
├─ Weak Categories: API, Bug
├─ Billing Performance: 95% FCR, 5% escalation
└─ API Performance: 65% FCR, 25% escalation
```

### Tip 2: Use Coaching Reports for 1-on-1s
Run "Horatio: Coaching & Development" before coaching sessions. Example output:
```
High Priority Coaching:
├─ John Smith
│   ├─ Focus Areas: API>Integration, Bug>Export
│   ├─ FCR: 68% (below 75% threshold)
│   └─ Example: [link to reopened conversation]
```

### Tip 3: Compare Team vs Individual
1. Run "Horatio: Team Metrics" first → See overall team performance
2. Then run "Horatio: Individual Agents + Taxonomy" → See which agents drive team results

---

## 🚀 Testing the New UI

### Step 1: Select Individual Breakdown
1. Open frontend
2. Select "Horatio: Individual Agents + Taxonomy"
3. **Observe:** Blue info panel appears explaining taxonomy breakdown
4. Click "Run Analysis"
5. **Verify command in terminal:** Should show `--individual-breakdown` flag

### Step 2: Select Coaching Report
1. Select "Horatio: Coaching & Development"
2. **Observe:** Amber info panel appears explaining coaching features
3. Click "Run Analysis"
4. **Verify command in terminal:** Should show `agent-coaching-report --vendor horatio`

### Step 3: Compare Outputs
Run both options side-by-side to see the difference:
- **Individual Breakdown:** Shows category-by-category performance matrix
- **Coaching Report:** Shows coaching priorities and focus areas

---

## 📦 Files Updated

1. ✅ `deploy/railway_web.py` - Added new dropdown options + info panels (HTML)
2. ✅ `static/app.js` - Updated runAnalysis() + added updateAnalysisOptions() (JavaScript)
3. ✅ `FRONTEND_FUNCTIONALITY_AUDIT.md` - Complete backend vs frontend mapping
4. ✅ `FRONTEND_UI_GUIDE.md` - This guide

---

## 🎉 Summary

**Total UI Options:** 16 (was 11 yesterday)

**New Options Added:**
- ✅ 3 Agent Performance options (Team, Individual, Escalated) replacing 2 generic options
- ✅ 2 Agent Coaching options (Horatio, Boldr)
- ✅ 3 Dynamic info panels explaining each analysis type

**Coverage:**
- ✅ 100% of agent performance features
- ✅ 100% of coaching features
- ✅ 100% of VoC analysis modes
- ✅ 95% of all backend functionality

**Ready to test!** 🚀

