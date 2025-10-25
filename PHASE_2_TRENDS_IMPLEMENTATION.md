# Phase 2: Week-over-Week Trends - IMPLEMENTED ✅

**Implementation Date**: October 25, 2025  
**Version**: 3.0.6-trends

## 🎯 **What Was Implemented**

Week-over-week trend tracking for agent performance metrics, enabling you to track improvements and identify declining performance.

---

## 📊 **Features**

### **1. Historical Data Storage**
- Automatic weekly snapshots stored in DuckDB
- Tracks: FCR, CSAT, escalation rate, response time, conversation volume
- Retained permanently (can configure retention if needed)

### **2. Week-over-Week Comparisons**
- Compares current week vs previous week for each agent
- Shows deltas (changes) in all key metrics
- Identifies improvements (↑) and declines (↓)

### **3. Trend Indicators**
```
↑ +5%     = Improvement (FCR increased 5%)
↓ -0.3    = Decline (CSAT dropped 0.3 points)
→ 0       = No change
⚠️↑ +3%   = Warning (escalation rate increased - bad)
```

---

## 🔧 **Implementation Details**

### **New File: `src/services/historical_performance_manager.py`**

**Key Methods:**
- `store_weekly_snapshot()` - Stores agent metrics after each analysis
- `get_week_over_week_comparison()` - Calculates deltas vs previous week
- `get_multi_week_trends()` - Retrieves 6-week history (like Horatio's chart)
- `format_trend_indicator()` - Formats ↑/↓ arrows with values

**DuckDB Schema:**
```sql
CREATE TABLE agent_weekly_snapshots (
    vendor TEXT,
    agent_id TEXT,
    agent_name TEXT,
    week_start DATE,
    week_end DATE,
    
    -- Performance metrics
    total_conversations INTEGER,
    fcr_rate REAL,
    escalation_rate REAL,
    median_resolution_hours REAL,
    
    -- CSAT metrics
    csat_score REAL,
    csat_survey_count INTEGER,
    negative_csat_count INTEGER,
    
    PRIMARY KEY (vendor, agent_id, week_start)
);
```

### **Updated: `src/agents/agent_performance_agent.py`**

**Integration (Lines 310-327):**
```python
# Store this week's snapshot
await historical_manager.store_weekly_snapshot(
    vendor=self.agent_filter,
    week_start=context.start_date,
    week_end=context.end_date,
    agent_metrics=agent_metrics
)

# Get week-over-week comparison
wow_changes = await historical_manager.get_week_over_week_comparison(
    self.agent_filter,
    context.start_date
)
report.week_over_week_changes = wow_changes
```

---

## 📈 **Example Output**

### **Agent Performance Report with Trends**

```json
{
  "vendor_name": "Horatio",
  "agents": [
    {
      "agent_name": "Juan",
      "fcr_rate": 0.85,
      "csat_score": 4.83,
      "escalation_rate": 0.12
    },
    {
      "agent_name": "Lorna",
      "fcr_rate": 0.65,
      "csat_score": 3.07,
      "escalation_rate": 0.25
    }
  ],
  "week_over_week_changes": {
    "agent_123": {
      "agent_name": "Juan",
      "fcr_change": +0.05,           // ↑ +5%
      "csat_change": +0.30,          // ↑ +0.3
      "escalation_change": -0.03,    // ↓ -3% (good)
      "conversations_change": +5,     // 5 more tickets
      "current_fcr": 0.85,
      "previous_fcr": 0.80
    },
    "agent_456": {
      "agent_name": "Lorna",
      "fcr_change": -0.10,           // ↓ -10% (bad)
      "csat_change": -0.50,          // ↓ -0.5 (bad)
      "escalation_change": +0.08,    // ↑ +8% (bad)
      "current_fcr": 0.65,
      "previous_fcr": 0.75
    }
  }
}
```

### **Formatted Report Display**

```
📊 Horatio Team Performance (Week of Oct 18-24)

🎯 INDIVIDUAL PERFORMANCE WITH TRENDS:

Juan:
  FCR: 85.0% (↑ +5% vs last week) ✅
  CSAT: 4.83 (↑ +0.3 vs last week) ✅
  Escalation: 12.0% (↓ -3% vs last week) ✅
  Status: IMPROVING ACROSS ALL METRICS
  
Lorna:
  FCR: 65.0% (↓ -10% vs last week) ⚠️
  CSAT: 3.07 (↓ -0.5 vs last week) ⚠️
  Escalation: 25.0% (↑ +8% vs last week) ⚠️
  Status: DECLINING - NEEDS IMMEDIATE COACHING

💡 HIGHLIGHTS:
- Juan: Strong improvement in all areas (FCR +5%, CSAT +0.3)

⚠️ LOWLIGHTS:
- Lorna: Declining performance across all metrics (needs urgent coaching)
```

---

## 🧪 **Testing**

### **First Week (No History)**
```bash
# Run first analysis - no trends yet
python src/main.py agent-performance --agent horatio --individual-breakdown --time-period week
```

**Output:**
- Snapshot stored in DuckDB
- No week-over-week changes shown (first run)
- `week_over_week_changes: null`

### **Second Week (With History)**
```bash
# Run second analysis - trends now available!
python src/main.py agent-performance --agent horatio --individual-breakdown --time-period week
```

**Output:**
- Snapshot stored for current week
- Week-over-week deltas calculated
- Trends displayed for each agent

---

## 🔄 **Data Flow**

```
1. Run Analysis
   ↓
2. Store Weekly Snapshot
   ├─ vendor: "horatio"
   ├─ week_start: 2025-10-18
   ├─ agent metrics: Juan (FCR 85%, CSAT 4.83)
   └─ [Saved to DuckDB]
   ↓
3. Calculate WoW Comparison
   ├─ Query current week (Oct 18-24)
   ├─ Query previous week (Oct 11-17)
   └─ Calculate deltas
   ↓
4. Display Trends
   ├─ Juan: FCR ↑ +5%
   ├─ Lorna: CSAT ↓ -0.5
   └─ Highlight improvements/declines
```

---

## 💡 **Use Cases**

### **1. Track Coaching Impact**
```
Week 1: Lorna CSAT = 3.5 (coaching session held)
Week 2: Lorna CSAT = 3.8 (↑ +0.3) ✅
Week 3: Lorna CSAT = 4.1 (↑ +0.3) ✅
→ Coaching is working!
```

### **2. Identify Declining Agents Early**
```
Week 1: Juan FCR = 85%
Week 2: Juan FCR = 80% (↓ -5%) ⚠️
Week 3: Juan FCR = 75% (↓ -5%) ⚠️
→ Intervene before it gets worse!
```

### **3. Recognize Consistent Performers**
```
Juan: 6 weeks of stable high performance
→ Recognize in team meeting!
```

---

## 🎯 **Next: Phase 3 (Troubleshooting Analysis)**

With Phase 2 complete, we can now track:
- ✅ Who improved/declined week-over-week
- ✅ Which metrics are trending up/down
- ✅ Long-term performance patterns

**Phase 3 will add:**
- 🔍 AI analysis of troubleshooting effort
- 🚩 Detection of premature escalations
- 📝 Controllable vs Uncontrollable classification
- 🎯 Coaching recommendations based on behavior patterns

---

## ✅ **Checklist**

- [x] HistoricalPerformanceManager class created
- [x] DuckDB schema for weekly snapshots
- [x] Automatic snapshot storage after analysis
- [x] Week-over-week delta calculation
- [x] Trend indicators (↑/↓ arrows)
- [x] Multi-week trend retrieval (for future charts)
- [x] Integration with agent performance agent
- [x] JSON output includes week_over_week_changes
- [x] No linter errors

---

## 🎉 **Result**

You can now see if agents are improving or declining week-over-week!

**Before Phase 2:**
```
❌ "Lorna has 3.07 CSAT"
   → Is that better or worse than last week?
   → Can't tell if coaching is working
```

**After Phase 2:**
```
✅ "Lorna has 3.07 CSAT (↓ -0.5 vs last week)"
   → Clear decline visible
   → Coaching not working yet, need different approach
   → Can track improvement once new coaching starts
```

Coaches can now track the impact of their interventions over time!

