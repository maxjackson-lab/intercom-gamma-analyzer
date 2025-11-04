# Insight System Redesign - Complete Implementation Plan

**Date:** November 4, 2025  
**Goal:** Transform from prescriptive "boss mode" to analytical "forecaster mode" + build historical foundation

---

## Table of Contents
1. [The Problem](#the-problem)
2. [The Solution](#the-solution)
3. [Historical Infrastructure](#historical-infrastructure-duckdb-schema)
4. [New Insight Agents](#new-insight-agents)
5. [Tonal Transformation](#tonal-transformation)
6. [Visual UI](#visual-ui-components)
7. [Implementation Timeline](#implementation-timeline)

---

## The Problem

### Current State: Limited & Prescriptive

**Issues identified:**
1. ❌ **Too prescriptive** - "You should fix X" (boss tone)
2. ❌ **Reductive** - Forces everything into 3-4 themes
3. ❌ **Limited cards** - Only 5-6 total views
4. ❌ **No forecasting** - Can't forecast without historical data
5. ❌ **No nuance** - Binary good/bad, no gray areas

**Current output:**
```markdown
## Recommendations
1. Improve billing refund process - too many escalations
2. Train agents on API - low FCR indicates knowledge gap
3. Fix Sites bugs - volume increasing, sentiment negative

Action Items:
- Assign billing team to review workflow
- Schedule training session
```

☝️ **Tells people what to do. No historical context. No nuance.**

---

## The Solution

### Three-Part Redesign:

1. **Historical Foundation** - Build snapshots, enable comparisons
2. **New Insight Agents** - Pattern detection without needing history
3. **Tonal Shift** - From prescriptive → analytical/observational

### What We CAN Do (No History):
- ✅ Find correlations within current week
- ✅ Detect statistical anomalies
- ✅ Flag churn/opportunity signals
- ✅ Compare topics within dataset
- ✅ Shift tone to observational

### What We CANNOT Do (Yet):
- ❌ True forecasting ("API will hit 50 convs next week")
- ❌ Trend detection ("Billing declining 12% per week")
- ❌ Seasonality ("Sites spike every Monday")
- ❌ "Getting better/worse" statements

**Strategy:** Start collecting data NOW, add forecasting in 4-12 weeks

---

## Historical Infrastructure (DuckDB Schema)

### New Tables

```sql
-- 1. Analysis snapshots (weekly/monthly/quarterly)
CREATE TABLE analysis_snapshots (
    snapshot_id VARCHAR PRIMARY KEY,
    analysis_type VARCHAR,              -- 'weekly', 'monthly', 'quarterly'
    period_start DATE,
    period_end DATE,
    created_at TIMESTAMP,
    
    -- Summary for UI
    total_conversations INTEGER,
    date_range_label VARCHAR,           -- "Nov 1-7, 2025", "Q4 2025"
    insights_summary TEXT,              -- 2-3 sentence summary
    
    -- Core metrics (JSON for flexibility)
    topic_volumes JSON,                 -- {'Billing': 45, 'API': 32, ...}
    topic_sentiments JSON,              -- {'Billing': {'positive': 0.6}, ...}
    tier_distribution JSON,             -- {'free': 120, 'team': 25, ...}
    agent_attribution JSON,             -- {'fin_ai': 70, 'horatio': 40, ...}
    resolution_metrics JSON,            -- {'fcr_rate': 0.65, 'median_hours': 4.2, ...}
    fin_performance JSON,               -- {'resolution_rate': 0.58, ...}
    key_patterns JSON,                  -- [{'pattern': 'API spike', 'confidence': 0.82}]
    
    -- Checkbox tracking
    reviewed BOOLEAN DEFAULT FALSE,
    reviewed_by VARCHAR,
    reviewed_at TIMESTAMP,
    notes TEXT
);

-- 2. Comparative analyses (week-over-week, etc.)
CREATE TABLE comparative_analyses (
    comparison_id VARCHAR PRIMARY KEY,
    comparison_type VARCHAR,            -- 'week_over_week', 'month_over_month'
    current_snapshot_id VARCHAR,
    prior_snapshot_id VARCHAR,
    created_at TIMESTAMP,
    
    -- Deltas
    volume_changes JSON,                -- {'Billing': {'change': +15, 'pct': 0.33}}
    sentiment_changes JSON,
    resolution_changes JSON,
    
    -- Significant changes (>25% change, >5 conv delta)
    significant_changes JSON,
    emerging_patterns JSON,             -- New patterns appearing
    declining_patterns JSON,            -- Patterns disappearing
    
    FOREIGN KEY (current_snapshot_id) REFERENCES analysis_snapshots(snapshot_id),
    FOREIGN KEY (prior_snapshot_id) REFERENCES analysis_snapshots(snapshot_id)
);

-- 3. Time-series metrics (for charting)
CREATE TABLE metrics_timeseries (
    metric_id VARCHAR PRIMARY KEY,
    snapshot_id VARCHAR,
    metric_name VARCHAR,                -- 'billing_volume', 'api_fcr', 'fin_resolution'
    metric_value FLOAT,
    metric_unit VARCHAR,                -- 'count', 'percentage', 'hours'
    category VARCHAR,                   -- 'volume', 'quality', 'efficiency'
    
    FOREIGN KEY (snapshot_id) REFERENCES analysis_snapshots(snapshot_id)
);

-- Indexes for time-based queries
CREATE INDEX idx_snapshots_period ON analysis_snapshots(period_start, period_end);
CREATE INDEX idx_snapshots_type ON analysis_snapshots(analysis_type);
CREATE INDEX idx_snapshots_reviewed ON analysis_snapshots(reviewed);
CREATE INDEX idx_timeseries_metric ON metrics_timeseries(metric_name);
```

### Why DuckDB is Perfect

✅ **Time-series optimized** - Columnar storage, fast aggregations  
✅ **JSON flexibility** - Add new metrics without schema changes  
✅ **Analytical workload** - Read-heavy queries (not transactional)  
✅ **Single-file portability** - Easy backup/migration  
✅ **Small footprint** - 1 snapshot/week = 50KB, 2.6MB/year  

**Verdict:** DuckDB handles this perfectly. ✅

---

## New Insight Agents

### Agent 1: CorrelationAgent (No History Required)

**Purpose:** Find relationships within current week's data

**What it detects:**
```
• Tier × Topic correlations
  "Business tier: 12% of volume, but 68% of API issues"
  
• CSAT × Reopens correlations
  "78% of reopened conversations have bad CSAT vs 9% of first-touch"
  
• Complexity × Escalation correlations
  "Escalated conversations average 6.8 messages vs 2.1 for Fin-only"
  
• Agent × Resolution Time
  "Horatio: 3.2 hours median, Boldr: 5.8 hours median"
```

**Output example:**
```json
{
  "correlations": [
    {
      "type": "tier_topic",
      "description": "Business tier ↔ API issues (r=0.87)",
      "strength": 0.87,
      "insight": "Business customers experience 68% of API issues",
      "context": "Business tier likely uses API features more heavily",
      "confidence": 0.82
    },
    {
      "type": "csat_reopens",
      "description": "Bad CSAT ↔ Multiple Reopens (r=0.74)",
      "strength": 0.74,
      "insight": "78% of reopened conversations result in bad CSAT",
      "context": "Reopens strongly predict dissatisfaction",
      "confidence": 0.85
    }
  ]
}
```

**Tone:** Observational - shows relationships, doesn't prescribe fixes

**File:** `src/agents/correlation_agent.py`

---

### Agent 2: AnomalyDetectionAgent (No History Required)

**Purpose:** Flag statistical outliers within current dataset

**What it detects:**
```
• Topic volume outliers
  "API: 18 convs (expected 3-5 based on distribution) - 260% deviation"
  
• Resolution time outliers
  "Conv #12345: 8 min resolution vs 4.2 hour median - study this"
  
• CSAT outliers
  "Conv #12346: 5 stars for billing refund (median 2.8) - what went right?"
  
• Temporal clustering
  "12 of 18 API convs occurred Nov 1-3 (Tue-Thu) - mid-week spike"
```

**Output example:**
```json
{
  "anomalies": [
    {
      "type": "volume_spike",
      "topic": "API Authentication",
      "expected": 4,
      "actual": 18,
      "deviation_pct": 260,
      "statistical_significance": 3.1,  // standard deviations
      "observation": "Unusual concentration of API auth issues",
      "timing": "12 occurred Nov 1-3",
      "confidence": 0.91
    }
  ],
  "exceptional_conversations": [
    {
      "conversation_id": "12345",
      "exceptional_in": "resolution_speed",
      "metric": "8 minutes",
      "vs_median": "4.2 hours",
      "recommendation": "Study as efficiency example",
      "intercom_url": "..."
    }
  ]
}
```

**Tone:** Statistical observer - flags unusual, doesn't explain why

**File:** `src/agents/anomaly_detection_agent.py`

---

### Agent 3: ChurnRiskAgent (No History Required)

**Purpose:** Detect explicit churn signals in conversation content

**What it detects:**
```
• Explicit language
  "cancel my subscription", "switching to [competitor]", "need refund"
  
• Frustration + High-Value pattern
  Business tier + multiple reopens + bad CSAT = high risk
  
• Competitor mentions
  "Pitch", "Canva", "Beautiful.ai" mentioned in context of comparison
  
• Resolution failure pattern
  Multiple reopens + no resolution + time elapsed
```

**Output example:**
```json
{
  "high_risk_conversations": [
    {
      "conversation_id": "12345",
      "risk_score": 0.85,
      "tier": "business",
      "signals": ["cancellation_language", "competitor_mentioned", "bad_csat"],
      "quotes": ["switching to Pitch", "cancel my subscription"],
      "intercom_url": "...",
      "priority": "immediate"  // Business tier = high priority
    }
  ],
  "risk_breakdown": {
    "high_value_at_risk": 5,     // Business/Ultra tier
    "medium_value_at_risk": 3,   // Team/Pro tier
    "total_risk_signals": 8
  }
}
```

**Tone:** Signal detector - flags for human review, doesn't predict churn probability

**File:** `src/agents/churn_risk_agent.py`

---

### Agent 4: ResolutionQualityAgent (No History Required)

**Purpose:** Analyze resolution effectiveness within current dataset

**What it measures:**
```
• FCR by topic
  "Billing Refunds: 78% FCR, API Auth: 34% FCR"
  
• Reopen rates by topic
  "Billing Invoices: 18% reopen rate (concerning)"
  
• Multi-touch patterns
  "API issues average 4.7 touches vs 2.1 overall"
  
• Time-to-resolution distribution
  "68% resolved in <24 hours, 22% take 24-48 hours, 10% take >48 hours"
```

**Output example:**
```json
{
  "fcr_by_topic": {
    "Billing Refunds": {"fcr": 0.78, "sample_size": 45},
    "API Authentication": {"fcr": 0.34, "sample_size": 18},
    "Sites Publishing": {"fcr": 0.56, "sample_size": 22}
  },
  "reopen_patterns": {
    "Billing Invoices": {
      "reopen_rate": 0.18,
      "observation": "18% reopen rate suggests knowledge gap or process issue"
    }
  },
  "multi_touch_analysis": {
    "API Authentication": {
      "avg_touches": 4.7,
      "vs_overall": 2.1,
      "observation": "Requires 2x more interactions - inherent complexity"
    }
  }
}
```

**Tone:** Quality auditor - measures effectiveness, doesn't blame agents

**File:** `src/agents/resolution_quality_agent.py`

---

### Agent 5: ConfidenceMetaAgent (No History Required)

**Purpose:** Report on the analysis itself (self-awareness)

**What it shows:**
```
• Confidence distribution across agents
• Data quality issues
• Coverage gaps
• Limitations of current analysis
```

**Output example:**
```json
{
  "confidence_distribution": {
    "high_confidence_insights": [
      {"agent": "TopicDetectionAgent", "confidence": 0.91, "reason": "Tag-based detection"},
      {"agent": "FinPerformanceAgent", "confidence": 0.88, "reason": "Clear signals"}
    ],
    "low_confidence_insights": [
      {"agent": "SegmentationAgent", "confidence": 0.54, "reason": "42% defaulted to FREE tier"}
    ]
  },
  "data_quality": {
    "tier_coverage": 0.58,           // Only 58% have Stripe data
    "csat_coverage": 0.18,           // Only 18% rated
    "conversation_parts_coverage": 0.95,  // 95% have full messages
    "impact": "Tier-based analysis has moderate confidence due to incomplete Stripe data"
  },
  "limitations": [
    "No historical baseline - cannot determine if metrics are normal",
    "Tier detection: 42% conversations defaulted to FREE (Stripe data incomplete)",
    "Sentiment analysis: Based on customer messages only (agent responses not analyzed)"
  ],
  "what_would_improve_confidence": [
    "Complete Stripe tier data in Intercom custom attributes",
    "4+ weeks of historical data for trend confidence",
    "Higher CSAT response rate (currently 18%)"
  ]
}
```

**Tone:** Self-aware - honest about limitations, identifies improvement areas

**File:** `src/agents/confidence_meta_agent.py`

---

## Tonal Transformation

### Before (Boss Mode) → After (Analyst Mode)

#### Example 1: Billing

**Before:**
```markdown
### Recommendations
1. **Improve billing refund process** - 22% escalation rate is too high
2. Assign billing team lead to audit refund workflow
3. Target: Reduce escalation to <15% within 30 days
```

**After:**
```markdown
### Billing Refunds - Observed Patterns

**Volume & Distribution:**
- 45 conversations (30% of total billing volume)
- Tier breakdown: Business 58%, Team 31%, Free 11%

**Resolution Efficiency:**
- FCR: 78% (22% require follow-up)
- Reopen rate: 4% (low)
- Median touches: 2.1
- CSAT: 4.2/5 (when rated, n=8)

**Observation:** Well-handled topic with strong resolution quality. 78% FCR is healthy for refund scenarios.

**Context:** 22% multi-touch is expected for refunds (complexity: verification, approval, processing time).

**Without historical data:** Cannot determine if 45 convs/week is normal, increasing, or decreasing.
```

#### Example 2: API

**Before:**
```markdown
### Recommendations
1. **Train agents on API authentication** - 34% FCR is unacceptable
2. Create API troubleshooting guide immediately
3. Escalate to engineering - likely product bug
```

**After:**
```markdown
### API Authentication - Complexity Pattern

**Volume & Distribution:**
- 18 conversations (12% of total volume)
- Tier breakdown: Business 72%, Team 22%, Free 6%

**Resolution Efficiency:**
- FCR: 34% (66% require multiple touches)
- Average touches: 4.7 (vs 2.1 overall)
- Reopen rate: 23%
- Median resolution time: 6.8 hours (vs 4.2 overall)

**Correlation Detected:**
- Business tier → API issues (r = 0.87, strong)
- Business tier represents 12% of volume but 72% of API issues
- Interpretation: Business customers use API features more heavily

**Observation:** Topic requires extended troubleshooting (4.7 touches average). This may reflect inherent technical complexity rather than knowledge gap.

**Anomaly:** 12 of 18 conversations occurred Nov 1-3 (temporal clustering). Suggests possible trigger event.

**Without historical data:** Cannot determine if this is new issue, recurring pattern, or one-time spike.

**Signal for investigation:** Mid-week clustering + Business tier concentration suggests reviewing recent API changes or Business tier onboarding.
```

#### Example 3: Churn Signals

**Before:**
```markdown
### Critical Issues
**5 customers at risk of churn** - immediate action required
- Contact these customers within 24 hours
- Offer compensation or escalation to senior staff
- Track win-back rate
```

**After:**
```markdown
### Churn Risk Signals Detected

**Explicit Signals: 5 conversations**
- "Cancel subscription": 2 convs (Business tier)
- Competitor mention: 2 convs ("switching to Pitch")
- Refund + frustration: 1 conv (Team tier)

**Tier Distribution:**
- Business tier: 3 conversations (high value)
- Team tier: 2 conversations

**Flagged for Manual Review:**
1. Conv #12345 - Business tier, "switching to Pitch", CSAT 1 [View →]
2. Conv #12346 - Business tier, "cancel my subscription", 4 reopens [View →]
3. Conv #12347 - Team tier, competitor comparison, CSAT 2 [View →]

**Context:** These are explicit signals, not churn predictions. Require human review to assess actual risk and determine response.

**Pattern:** 3 of 5 are Business tier customers (60% vs 12% overall) - high-value concentration.
```

---

## Visual UI Components

### Timeline View (Railway Web Interface)

```html
<div class="analysis-timeline-container">
  
  <!-- Historical Context Banner -->
  <div class="historical-context-banner">
    <span class="context-icon">📊</span>
    <span class="context-message">
      4 weeks of data available - Trend analysis enabled. 
      8 more weeks until seasonality detection.
    </span>
  </div>
  
  <!-- Weekly Timeline -->
  <h3>Weekly Analysis History</h3>
  <div class="timeline-weeks">
    
    <!-- Past Week (Reviewed) -->
    <div class="week-card reviewed">
      <div class="week-header">
        <input type="checkbox" class="review-checkbox" checked disabled>
        <span class="week-label">Nov 1-7, 2025</span>
        <span class="status-badge reviewed">✓ Reviewed</span>
      </div>
      <div class="week-summary">
        150 conversations. Top: Billing (45, 30%). Fin: 58%. 5 churn signals.
      </div>
      <div class="week-metrics">
        <span class="metric">📊 150 convs</span>
      </div>
      <div class="week-actions">
        <button class="btn-secondary" onclick="viewSnapshot('weekly_20251107')">
          View Report
        </button>
      </div>
    </div>
    
    <!-- Current Week (Needs Review) -->
    <div class="week-card current">
      <div class="week-header">
        <input type="checkbox" class="review-checkbox" 
               onchange="markReviewed('weekly_20251114')">
        <span class="week-label">Nov 8-14, 2025</span>
        <span class="status-badge current">⭐ Current</span>
      </div>
      <div class="week-summary">
        175 conversations. Top: API (52, 30%). Fin: 62%. 3 churn signals.
      </div>
      <div class="week-metrics">
        <span class="metric">📊 175 convs</span>
        <span class="metric trend-up">📈 +17% vs last week</span>
      </div>
      <div class="week-changes">
        <div class="change-item significant">
          <span class="change-topic">API</span>
          <span class="change-delta">+63%</span>
          <span class="change-note">⚠️ Significant spike</span>
        </div>
        <div class="change-item">
          <span class="change-topic">Billing</span>
          <span class="change-delta">+16%</span>
        </div>
      </div>
      <div class="week-actions">
        <button class="btn-primary" onclick="viewSnapshot('weekly_20251114')">
          View Full Report
        </button>
        <button class="btn-secondary" onclick="compareWeeks('weekly_20251114', 'weekly_20251107')">
          Compare to Prior Week
        </button>
      </div>
    </div>
    
    <!-- Future Week -->
    <div class="week-card future">
      <div class="week-label">Nov 15-21, 2025</div>
      <div class="week-summary">Not yet analyzed</div>
      <div class="week-actions">
        <button class="btn-secondary" disabled>
          Run Analysis (Nov 22+)
        </button>
      </div>
    </div>
    
  </div>
  
  <!-- Monthly Rollup -->
  <h3>Monthly Analysis</h3>
  <div class="timeline-months">
    <div class="month-card reviewed">
      <input type="checkbox" checked disabled>
      <span class="month-label">October 2025</span>
      <span class="month-summary">580 conversations</span>
      <button onclick="viewSnapshot('monthly_20251031')">View</button>
    </div>
    
    <div class="month-card in-progress">
      <input type="checkbox">
      <span class="month-label">November 2025</span>
      <span class="month-summary">325 convs so far (2 of 4 weeks)</span>
      <span class="progress-bar">
        <span class="progress-fill" style="width: 50%"></span>
      </span>
    </div>
  </div>
  
  <!-- Quarterly Rollup -->
  <h3>Quarterly Analysis</h3>
  <div class="timeline-quarters">
    <div class="quarter-card in-progress">
      <input type="checkbox">
      <span class="quarter-label">Q4 2025</span>
      <span class="quarter-summary">905 conversations so far (6 of 13 weeks)</span>
      <span class="progress-bar">
        <span class="progress-fill" style="width: 46%"></span>
      </span>
    </div>
  </div>
  
</div>

<style>
.week-card {
  min-width: 320px;
  border: 2px solid #e0e0e0;
  border-radius: 12px;
  padding: 20px;
  background: white;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.week-card.current {
  border-color: #4CAF50;
  background: linear-gradient(135deg, #f1f8f4 0%, white 100%);
}

.week-card.reviewed {
  opacity: 0.75;
  border-color: #9e9e9e;
}

.week-card.future {
  border-style: dashed;
  opacity: 0.4;
}

.status-badge.reviewed {
  background: #4CAF50;
  color: white;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
}

.status-badge.current {
  background: #FF9800;
  color: white;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
}

.metric.trend-up {
  color: #f44336;  /* Red = more problems */
  font-weight: bold;
}

.metric.trend-down {
  color: #4CAF50;  /* Green = fewer problems */
  font-weight: bold;
}

.change-item.significant {
  background: #fff3cd;
  border-left: 4px solid #ff9800;
  padding: 8px;
  margin: 4px 0;
}

.progress-bar {
  display: inline-block;
  width: 100px;
  height: 8px;
  background: #e0e0e0;
  border-radius: 4px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #4CAF50 0%, #8BC34A 100%);
  transition: width 0.3s;
}
</style>
```

### Trend Chart (Once 4+ Weeks Exist)

```html
<div class="trend-chart-section">
  <h3>Topic Volume Trends</h3>
  <canvas id="volumeTrendChart" width="800" height="400"></canvas>
  
  <div class="chart-controls">
    <button onclick="showMetric('volume')">Volume</button>
    <button onclick="showMetric('fcr')">FCR</button>
    <button onclick="showMetric('resolution_time')">Resolution Time</button>
  </div>
  
  <div class="chart-message">
    ℹ️ Showing 4 weeks of trend data. 
    Forecast projections available with 70% confidence.
  </div>
</div>

<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script>
async function loadTrendChart() {
  const response = await fetch('/api/snapshots/timeseries?weeks=12');
  const data = await response.json();
  
  const ctx = document.getElementById('volumeTrendChart').getContext('2d');
  new Chart(ctx, {
    type: 'line',
    data: {
      labels: data.weeks.map(w => w.label),
      datasets: [
        {
          label: 'Billing',
          data: data.weeks.map(w => w.topic_volumes.Billing || 0),
          borderColor: '#FF6384',
          fill: false,
          tension: 0.1
        },
        {
          label: 'API',
          data: data.weeks.map(w => w.topic_volumes.API || 0),
          borderColor: '#36A2EB',
          fill: false,
          tension: 0.1
        },
        {
          label: 'Sites',
          data: data.weeks.map(w => w.topic_volumes.Sites || 0),
          borderColor: '#FFCE56',
          fill: false,
          tension: 0.1
        }
      ]
    },
    options: {
      responsive: true,
      plugins: {
        title: {
          display: true,
          text: 'Weekly Topic Volume Trends'
        },
        subtitle: {
          display: true,
          text: `Based on ${data.weeks.length} weeks of historical data`
        }
      },
      scales: {
        y: {
          beginAtZero: true,
          title: {
            display: true,
            text: 'Conversations per Week'
          }
        }
      }
    }
  });
}

loadTrendChart();
</script>
```

---

## Implementation Timeline

### ✅ Week 1: Foundation (Code Implementation)

**DuckDB Schema:**
- [ ] Add `analysis_snapshots` table
- [ ] Add `comparative_analyses` table
- [ ] Add `metrics_timeseries` table
- [ ] Add indexes

**Services:**
- [ ] Create `src/services/historical_snapshot_service.py`
  - `save_snapshot()` - Save after each analysis
  - `get_prior_snapshot()` - Retrieve for comparison
  - `calculate_comparison()` - Week-over-week deltas
  - `get_historical_context()` - How much data do we have?

- [ ] Create `src/services/period_analyzer.py`
  - `analyze_weekly()` - 7-day analysis with comparison
  - `analyze_monthly()` - 30-day analysis
  - `analyze_quarterly()` - 90-day analysis

**Integration:**
- [ ] Update `topic_orchestrator.py` to auto-save snapshots
- [ ] Add historical context check before comparative analysis

**Testing:**
- [ ] Run analysis, verify snapshot saves to DuckDB
- [ ] Check: `SELECT * FROM analysis_snapshots` shows data

**Deliverable:** Snapshots being saved automatically ✅

---

### ✅ Week 2: Comparison Logic (Once We Have 2 Snapshots)

**Comparison Calculator:**
- [ ] Implement `_calculate_volume_deltas()` - Topic volume changes
- [ ] Implement `_calculate_sentiment_deltas()` - Sentiment shifts
- [ ] Implement `_identify_significant_changes()` - >25% changes
- [ ] Implement `_detect_emerging_patterns()` - New topics appearing
- [ ] Implement `_detect_declining_patterns()` - Topics disappearing

**Output Formatting:**
- [ ] Add "Week-over-Week Changes" section to reports
- [ ] Show deltas: "Billing: 45 → 52 (+16%)"
- [ ] Flag significant changes: "⚠️ API +63% (significant spike)"

**CLI Enhancement:**
- [ ] Show comparison in terminal output
- [ ] Add `--no-comparison` flag to disable

**Testing:**
- [ ] Run 2 weekly analyses (Week 1, Week 2)
- [ ] Verify Week 2 shows comparison to Week 1
- [ ] Check: `SELECT * FROM comparative_analyses` shows deltas

**Deliverable:** Second analysis shows week-over-week comparison ✅

---

### ✅ Week 3: Visual UI (Railway Web)

**Routes:**
- [ ] `/analysis/history` - Timeline view
- [ ] `/analysis/view/:snapshot_id` - View specific snapshot
- [ ] `/analysis/compare/:current/:prior` - Side-by-side comparison
- [ ] `/api/snapshots/list` - JSON endpoint for timeline
- [ ] `/api/snapshots/:id/review` - Mark as reviewed
- [ ] `/api/snapshots/timeseries` - Chart data

**UI Components:**
- [ ] Timeline view with cards (weekly, monthly, quarterly)
- [ ] Checkbox "reviewed" functionality
- [ ] Brief summaries (2-3 sentences per snapshot)
- [ ] Visual indicators (✓ reviewed, ⭐ current, future)
- [ ] Trend charts (if 4+ weeks exist)

**Testing:**
- [ ] Visit `/analysis/history`, see timeline
- [ ] Click checkbox, verify DB updates
- [ ] View old report, verify content loads
- [ ] Check chart renders (once 4+ weeks exist)

**Deliverable:** Visual interface for browsing historical analyses ✅

---

### ✅ Week 4: New Insight Agents

**Agent Implementation:**
- [ ] Create `correlation_agent.py`
  - Tier × Topic correlation
  - CSAT × Reopens correlation
  - Agent × Resolution Time correlation
  
- [ ] Create `anomaly_detection_agent.py`
  - Topic volume outliers
  - Resolution time outliers
  - Temporal clustering detection
  
- [ ] Create `churn_risk_agent.py`
  - Cancellation language detection
  - Competitor mention tracking
  - High-risk conversation flagging
  
- [ ] Create `resolution_quality_agent.py`
  - FCR by topic
  - Reopen rates
  - Multi-touch analysis
  
- [ ] Create `confidence_meta_agent.py`
  - Confidence distribution
  - Data quality reporting
  - Limitation identification

**Orchestration:**
- [ ] Add agents to `topic_orchestrator.py`
- [ ] Run after analysis agents, before output
- [ ] Include in workflow results

**Output Formatting:**
- [ ] Add sections for each new agent
- [ ] Format correlations card
- [ ] Format anomalies card
- [ ] Format churn risk card
- [ ] Format quality metrics card
- [ ] Format confidence/limitations card

**Testing:**
- [ ] Run analysis, verify all 5 agents execute
- [ ] Check reports include new sections
- [ ] Verify tone is observational (not prescriptive)

**Deliverable:** Richer insights with observational tone ✅

---

### ⏳ Weeks 5-8: Enhanced Analysis (As History Builds)

**Week 5 (4 weeks of data):**
- [ ] Enable trend detection (4-week minimum)
- [ ] Add simple linear forecasting
- [ ] Show trend lines in charts
- [ ] Add "Trend Analysis" section to reports

**Week 8 (7 weeks of data):**
- [ ] Add baseline establishment (median, std dev)
- [ ] Improve anomaly detection (vs historical baseline)
- [ ] Add "vs baseline" comparisons

**Week 12 (12 weeks of data):**
- [ ] Enable seasonality detection
- [ ] Detect day-of-week patterns
- [ ] Detect monthly patterns
- [ ] Add "Seasonality" section to reports

---

## New Report Structure

### Current Report (5-6 Sections):
```
1. Billing Card
2. API Card
3. Sites Card
4. Fin Performance (Free Tier)
5. Fin Performance (Paid Tier)
```

### Enhanced Report (12-15 Sections):

```markdown
# Voice of Customer Analysis
*Period: Nov 8-14, 2025*
*Historical Context: 4 weeks of data - Trend analysis available*

---

## Historical Context ⏳
[What data we have, what analyses are possible]

## Week-over-Week Changes 📊
[Volume deltas, significant changes, emerging patterns]

---

## Topic Analysis (Volume & Sentiment)

### Billing
[Current format - keep this]

### API
[Current format - keep this]

### Sites
[Current format - keep this]

---

## Pattern Intelligence 🔍

### Correlations Detected
[CorrelationAgent output]
- Business tier ↔ API issues (r=0.87)
- Bad CSAT ↔ Reopens (r=0.74)

### Statistical Anomalies
[AnomalyDetectionAgent output]
- API volume spike: +260% vs expected
- Conv #12345: 8 min resolution (study this)

---

## Risk & Opportunity Signals ⚠️

### Churn Risk Flagged
[ChurnRiskAgent output]
- 5 conversations with explicit churn signals
- 3 are Business tier (high value)
- [Links for manual review]

---

## Resolution Quality Metrics 📈

### First Contact Resolution by Topic
[ResolutionQualityAgent output]
- Billing Refunds: 78% FCR
- API Auth: 34% FCR (multi-touch complexity)

### Reopen Patterns
- Billing Invoices: 18% reopen rate (investigate)

---

## Fin AI Performance 🤖

### Free Tier (Fin-Only)
[Current format - keep this]

### Paid Tier (Fin-Resolved)
[Current format - keep this]

---

## Analysis Confidence & Limitations 🎯

[ConfidenceMetaAgent output]
- High confidence: Topic volumes (0.91), Fin rates (0.88)
- Low confidence: Tier detection (0.54) - 42% defaulted to FREE
- What would improve: Complete Stripe tier data

---

## What We Cannot Determine (Yet)

- Is current volume normal? (Baseline establishes in 4 weeks)
- Seasonality patterns? (Need 12 weeks)
- Long-term trends? (Need 6+ months)

**Building baseline:** Week 4 of 12 needed for seasonality detection.

---
```

**Total sections: ~12-15** (vs current 5-6)

**Tone throughout:** Observational, analytical, shows patterns and signals, doesn't command actions

---

## CLI Commands

### New Commands Available:

```bash
# Weekly analysis with auto-comparison
python src/main.py analyze-weekly --week-ending 2025-11-14

# Monthly rollup
python src/main.py analyze-monthly --month 2025-11

# Quarterly rollup
python src/main.py analyze-quarterly --quarter Q4-2025

# View historical snapshots
python src/main.py list-snapshots

# Output:
# 📅 Analysis History
# 
# Weekly:
# ✓ Nov 1-7   (150 convs) [Reviewed by max.jackson on Nov 9]
# ⭐ Nov 8-14  (175 convs) [Current - Needs Review]
# 
# Monthly:
# ✓ October   (580 convs) [Reviewed]
# ⏳ November  (325 convs) [In Progress - 50% complete]
#
# Capability Status:
# ✓ Week-over-week comparison: Available (2 weeks data)
# ⏳ Trend detection: Available in 2 more weeks (4 weeks needed)
# ⏳ Seasonality: Available in 10 more weeks (12 weeks needed)

# Compare two specific periods
python src/main.py compare-snapshots \
  --current weekly_20251114 \
  --prior weekly_20251107

# Mark snapshot as reviewed
python src/main.py mark-reviewed weekly_20251114 \
  --reviewer "max.jackson" \
  --notes "Discussed with team, API spike correlates with webhook release"
```

---

## Summary

### What This Gives You:

**Immediate (Week 1):**
- ✅ Historical snapshots saved automatically
- ✅ Infrastructure for future comparisons
- ✅ Foundation for trend detection

**Week 2+:**
- ✅ Week-over-week comparison
- ✅ Delta tracking (volume, sentiment, resolution)
- ✅ "Significant changes" flagged

**Week 3:**
- ✅ Visual timeline UI
- ✅ Checkboxes to mark reviewed
- ✅ Brief summaries per analysis
- ✅ Trend charts

**Week 4:**
- ✅ 5 new insight agents (Correlation, Anomaly, ChurnRisk, ResolutionQuality, ConfidenceMeta)
- ✅ Tonal shift (observational not prescriptive)
- ✅ 12-15 report sections (vs 5-6)

**Week 5-12 (As Data Grows):**
- ⏳ Trend detection → forecasting
- ⏳ Baseline establishment → "is this normal?"
- ⏳ Seasonality detection → "Monday pattern confirmed"

### Tone Throughout:

**Not:** "Fix this" (boss)  
**Instead:** "Observing this pattern" (analyst)  

**Not:** "You should..." (directive)  
**Instead:** "We're seeing..." (observational)  

**Not:** "This is bad" (judgmental)  
**Instead:** "This deviates from X, correlates with Y" (neutral)

---

**One document, complete plan, realistic timeline, honest about what's possible when.**

Ready to implement Week 1 foundation?

