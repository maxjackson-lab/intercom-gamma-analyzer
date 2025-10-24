# Individual Agent Performance & Coaching Guide

## Overview

The Individual Agent Performance system provides detailed coaching insights for Horatio and Boldr vendors, tracking individual agent performance with taxonomy-based category/subcategory breakdowns.

## Key Features

### 1. Individual Agent Tracking
- Identifies agents via Intercom Admin API (handles nested email extraction)
- Tracks performance per agent, not just team-level
- Extracts work email even when public email is Intercom-generated

### 2. Taxonomy-Based Performance Breakdown
- Performance metrics by **primary category** (13 categories: Billing, Bug, Account, etc.)
- Performance metrics by **subcategory** (100+ subcategories: Billing>Refund, Bug>Export, etc.)
- Identifies specific subcategories where agents excel or struggle

### 3. Coaching Insights
- **Agents Needing Coaching**: Bottom 25% or specific performance issues
- **Agents for Praise**: Top 25% or exceptional achievements  
- **Team Training Needs**: Subcategories affecting multiple agents
- **Coaching Priority**: Low/Medium/High based on performance thresholds

### 4. Historical Trending
- Stores performance snapshots in DuckDB
- Week-over-week comparison
- Tracks individual agent improvement/decline over time

### 5. Data Preprocessing Integration
- Deduplication, validation, outlier detection
- Text cleaning for better category detection
- Missing data inference

---

## Commands

### Option 1: Enhanced Existing Command

```bash
# Team-level analysis (original behavior)
python src/main.py agent-performance --agent horatio --time-period week

# Individual breakdown with taxonomy analysis
python src/main.py agent-performance --agent horatio --time-period week --individual-breakdown

# With Gamma presentation
python src/main.py agent-performance --agent boldr --time-period month --individual-breakdown --generate-gamma

# Specific date range
python src/main.py agent-performance --agent horatio \
  --start-date 2025-01-01 --end-date 2025-01-31 \
  --individual-breakdown
```

### Option 2: Dedicated Coaching Report

```bash
# Weekly coaching report
python src/main.py agent-coaching-report --vendor horatio

# Monthly coaching report
python src/main.py agent-coaching-report --vendor boldr --time-period month

# Highlight top/bottom 5 performers
python src/main.py agent-coaching-report --vendor horatio --top-n 5 --generate-gamma
```

---

## Output Structure

### Individual Agent Metrics

```json
{
  "agent_id": "7885880",
  "agent_name": "Maria Rodriguez",
  "agent_email": "maria@hirehoratio.co",
  "vendor": "horatio",
  
  "total_conversations": 95,
  "fcr_rate": 0.91,
  "reopen_rate": 0.06,
  "escalation_rate": 0.05,
  "median_resolution_hours": 4.2,
  "median_response_hours": 0.8,
  "over_48h_count": 2,
  "avg_conversation_complexity": 3.5,
  
  "performance_by_category": {
    "Billing": {
      "primary_category": "Billing",
      "volume": 30,
      "fcr_rate": 0.95,
      "escalation_rate": 0.03,
      "median_resolution_hours": 3.5,
      "performance_level": "excellent"
    },
    "Bug": {
      "primary_category": "Bug",
      "volume": 25,
      "fcr_rate": 0.88,
      "escalation_rate": 0.08,
      "median_resolution_hours": 5.2,
      "performance_level": "good"
    }
  },
  
  "performance_by_subcategory": {
    "Billing>Refund": {
      "primary_category": "Billing",
      "subcategory": "Refund",
      "volume": 15,
      "fcr_rate": 0.93,
      "escalation_rate": 0.07,
      "median_resolution_hours": 3.0,
      "performance_level": "excellent"
    },
    "Bug>Export": {
      "primary_category": "Bug",
      "subcategory": "Export",
      "volume": 8,
      "fcr_rate": 0.75,
      "escalation_rate": 0.12,
      "median_resolution_hours": 6.5,
      "performance_level": "fair"
    }
  },
  
  "strong_categories": ["Billing", "Account"],
  "weak_categories": [],
  "strong_subcategories": ["Billing>Refund", "Account>Login"],
  "weak_subcategories": ["Bug>Export", "Bug>API"],
  
  "fcr_rank": 1,
  "response_time_rank": 2,
  
  "coaching_priority": "low",
  "coaching_focus_areas": [],
  "praise_worthy_achievements": [
    "Excellent FCR rate: 91.0%",
    "Top FCR performer on team",
    "Excellence across 2 categories"
  ],
  
  "best_example_url": "https://app.intercom.com/a/apps/xyz/inbox/inbox/12345",
  "needs_coaching_example_url": null
}
```

### Vendor Performance Report

```json
{
  "vendor_name": "Horatio",
  "analysis_period": {
    "start": "2025-01-01T00:00:00",
    "end": "2025-01-31T23:59:59"
  },
  
  "team_metrics": {
    "total_conversations": 450,
    "team_fcr_rate": 0.82,
    "team_escalation_rate": 0.08,
    "total_agents": 8
  },
  
  "agents": [
    /* All 8 agents with full metrics */
  ],
  
  "agents_needing_coaching": [
    /* Bottom 25% or high priority */
  ],
  
  "agents_for_praise": [
    /* Top 25% or exceptional performers */
  ],
  
  "team_strengths": ["Billing", "Account"],
  "team_weaknesses": ["Bug>API", "Bug>Export"],
  
  "team_training_needs": [
    {
      "topic": "Bug>Export",
      "reason": "4 agents showing poor performance in this area",
      "affected_agents": ["John Smith", "Sarah Chen", "Mike Wilson", "Lisa Wong"],
      "priority": "high",
      "example_conversations": []
    }
  ],
  
  "week_over_week_changes": {
    "fcr_rate_change": 2.5,
    "escalation_rate_change": -5.3,
    "resolution_time_change": -8.2
  },
  
  "highlights": [
    "Excellent team FCR: 82.0%",
    "Maria Rodriguez: 91.0% FCR",
    "Team FCR improved 2.5% week-over-week"
  ],
  
  "lowlights": [
    "Team struggles with Bug>Export (4 agents)",
    "2 agents need immediate coaching"
  ]
}
```

---

## Console Output Examples

### Team-Level Analysis (without --individual-breakdown)

```
🎉 Horatio Performance Analysis Complete!
================================================================================

📊 Overall Metrics:
   Total Conversations: 450
   First Contact Resolution: 82.0%
   Median Resolution Time: 6.5 hours
   Escalation Rate: 8.0%
   Confidence: high

📋 Performance by Category:
   Billing: 120 conversations
      FCR: 88.0%, Escalation: 5.0%, Avg Resolution: 4.2h
   Bug: 95 conversations
      FCR: 75.0%, Escalation: 12.0%, Avg Resolution: 8.5h
   Account: 80 conversations
      FCR: 90.0%, Escalation: 3.0%, Avg Resolution: 3.8h
```

### Individual Breakdown (with --individual-breakdown)

```
🎉 Horatio Performance Analysis Complete!
================================================================================

📊 Team Summary:
   Total Agents: 8
   Total Conversations: 450
   Team FCR: 82.0%
   Team Escalation Rate: 8.0%

✨ Highlights:
   ✓ Excellent team FCR: 82.0%
   ✓ Maria Rodriguez: 91.0% FCR
   ✓ Team FCR improved 2.5% week-over-week

⚠️  Lowlights:
   • 2 agents need immediate coaching
   • Team struggles with Bug>Export (4 agents)

👥 Individual Agent Performance:

┌─────┬────────────────────┬──────────────┬────────┬───────────┬──────────────┬──────────┐
│Rank │ Agent Name         │Conversations │   FCR  │Escalation │Response Time │ Coaching │
├─────┼────────────────────┼──────────────┼────────┼───────────┼──────────────┼──────────┤
│  1  │ Maria Rodriguez    │          95  │ 91.0%  │    5.0%   │      0.8h    │    LOW   │
│  2  │ Sarah Chen         │          78  │ 85.0%  │    7.0%   │      1.2h    │    LOW   │
│  3  │ Tom Anderson       │          65  │ 80.0%  │    9.0%   │      1.5h    │  MEDIUM  │
│  4  │ Lisa Wong          │          52  │ 78.0%  │   11.0%   │      1.8h    │  MEDIUM  │
│  5  │ Mike Wilson        │          48  │ 75.0%  │   13.0%   │      2.1h    │  MEDIUM  │
│  6  │ John Smith         │          42  │ 72.0%  │   15.0%   │      2.5h    │   HIGH   │
│  7  │ Amy Chen           │          38  │ 68.0%  │   18.0%   │      3.2h    │   HIGH   │
│  8  │ David Lee          │          32  │ 65.0%  │   22.0%   │      3.8h    │   HIGH   │
└─────┴────────────────────┴──────────────┴────────┴───────────┴──────────────┴──────────┘

🎯 Agents Needing Coaching (3):

   John Smith (john@hirehoratio.co)
   FCR: 72.0%, Escalation: 15.0%
   Focus on: Bug>Export, Bug>API, Account>Login
   Weak subcategories: Bug>Export, Bug>API, Account>Login

   Amy Chen (amy@hirehoratio.co)
   FCR: 68.0%, Escalation: 18.0%
   Focus on: Bug>API, Billing>Refund, Account>Password
   Weak subcategories: Bug>API, Billing>Refund, Account>Password

   David Lee (david@hirehoratio.co)
   FCR: 65.0%, Escalation: 22.0%
   Focus on: Bug>Export, Product Question>Integration
   Weak subcategories: Bug>Export, Product Question>Integration

🌟 Top Performers (2):

   Maria Rodriguez (maria@hirehoratio.co)
   FCR: 91.0%, Rank: #1
   ✓ Excellent FCR rate: 91.0%
   ✓ Top FCR performer on team

   Sarah Chen (sarah@hirehoratio.co)
   FCR: 85.0%, Rank: #2
   ✓ Minimal escalations: 7.0%
   ✓ Excellence across 3 categories

📚 Team Training Needs:

   HIGH: Bug>Export
   4 agents showing poor performance in this area
   Affects: John Smith, Lisa Wong, Amy Chen and 1 more

   MEDIUM: Bug>API
   3 agents showing poor performance in this area
   Affects: John Smith, Amy Chen, David Lee

📈 Week-over-Week Changes:
   fcr_rate_change: ↑ 2.5%
   escalation_rate_change: ↓ 5.3%
   resolution_time_change: ↓ 8.2%
```

---

## Use Cases

### 1. Weekly Coaching Sessions

```bash
# Get weekly report for Horatio
python src/main.py agent-coaching-report --vendor horatio

# Review:
# - Who needs 1-on-1 coaching this week?
# - Who should be publicly praised in team meeting?
# - What training topics affect multiple agents?
```

### 2. Monthly Performance Reviews

```bash
# Get monthly breakdown with historical trending
python src/main.py agent-performance --agent boldr \
  --time-period month \
  --individual-breakdown
  
# Review:
# - Individual agent FCR rankings
# - Category-specific strengths/weaknesses
# - Month-over-month improvement trends
```

### 3. Identify Training Gaps

The taxonomy breakdown shows exactly which subcategories need training:

- **Bug>Export**: 4 agents struggling (team training session needed)
- **Bug>API**: 3 agents with high escalation (create better docs)
- **Billing>Refund**: 1 agent weak (pair with top performer)

### 4. Vendor Comparison

```bash
# Run for both vendors
python src/main.py agent-coaching-report --vendor horatio
python src/main.py agent-coaching-report --vendor boldr

# Compare:
# - Which vendor has better FCR?
# - Which categories does each vendor handle well?
# - Are training needs similar or different?
```

---

## Performance Thresholds

### FCR (First Contact Resolution)
- **Excellent**: ≥85% FCR
- **Good**: 75-84% FCR
- **Fair**: 70-74% FCR
- **Poor**: <70% FCR

### Escalation Rate
- **Excellent**: ≤10% escalation
- **Good**: 11-15% escalation
- **Fair**: 16-20% escalation
- **Poor**: >20% escalation

### Coaching Priority
- **High**: FCR <70% OR escalation >20%
- **Medium**: Multiple weak categories (2+) or subcategories (3+)
- **Low**: Good overall performance

---

## Technical Details

### Nested Email Extraction

The system handles Intercom's nested email structure:

1. **Public Email** (from conversation): May be `user-7885880@intercom-mail.io`
2. **Work Email** (from Admin API): The actual email like `maria@hirehoratio.co`

```python
# Extracts from conversation
public_email = author.get('email')  # user-7885880@intercom-mail.io

# Fetches from /admins/{id} API endpoint
work_email = admin_profile.get('email')  # maria@hirehoratio.co
```

### Caching Strategy

- **Session Cache**: In-memory cache for current analysis
- **DuckDB Cache**: Persistent cache (7-day TTL)
- **Prevents**: Redundant API calls for same admin

### Data Storage

Performance snapshots stored in:
- **JSON files**: `outputs/historical_data/agent_performance_horatio_20250124.json`
- **DuckDB tables**: `admin_profiles`, `agent_performance_history`, `vendor_performance_history`

---

## Example Coaching Workflow

### Step 1: Run Weekly Report

```bash
python src/main.py agent-coaching-report --vendor horatio --generate-gamma
```

### Step 2: Review Console Output

- Check **Highlights**: Who to praise in team meeting?
- Check **Lowlights**: What urgent issues need addressing?
- Check **Coaching Needed**: Who needs 1-on-1 sessions?

### Step 3: Review Detailed JSON

Open `outputs/coaching_report_horatio_YYYYMMDD_HHMMSS.json`:

- Drill into individual agent `performance_by_subcategory`
- Identify specific subcategories for coaching
- Get Intercom URLs for example conversations

### Step 4: Take Action

- **Praise**: Share Maria's 91% FCR in team Slack
- **Coaching**: Schedule 1-on-1 with John on Bug>Export handling
- **Training**: Team session on Bug>Export (affects 4 agents)
- **Documentation**: Create guide for Bug>API troubleshooting

### Step 5: Track Trends

Next week, compare:
- Did John's Bug>Export performance improve?
- Did team training reduce Bug>Export escalations?
- Are week-over-week metrics trending positive?

---

## API Endpoints Used

### Intercom Conversations Search
```
POST https://api.intercom.io/conversations/search
```

### Intercom Admin Profile (NEW)
```
GET https://api.intercom.io/admins/{admin_id}
```

Returns:
```json
{
  "type": "admin",
  "id": "7885880",
  "name": "Maria Rodriguez",
  "email": "maria@hirehoratio.co",
  "away_mode_enabled": false,
  "has_inbox_seat": true,
  "team_ids": []
}
```

---

## Data Preprocessing

When `--individual-breakdown` is used, preprocessing includes:

1. **Validation**: Ensure conversations have required fields
2. **Deduplication**: Remove duplicate conversations
3. **Missing Data Inference**: Fill in missing fields with confidence scoring
4. **Text Cleaning**: Remove HTML, normalize URLs/emails
5. **Outlier Detection**: Flag unusual conversations (very long, very short, etc.)

This ensures higher-quality analysis and better category detection.

---

## Taxonomy Categories

### Primary Categories (13)
- Abuse
- Account
- Agent/Buddy
- Billing
- Bug
- Chargeback
- Feedback
- Partnerships
- Privacy
- Product Question
- Promotions
- Unknown
- Workspace

### Example Subcategories (100+)

**Billing** (26 subcategories):
- Refund, Invoice, Subscription, Payment Method, Pricing, Discount, etc.

**Bug** (24 subcategories):
- Export, Account, Agent, API, Authentication, Billing, Collaboration, etc.

**Account** (11 subcategories):
- Login Issues, Password Reset, Email Change, Account Settings, etc.

**Product Question** (10 subcategories):
- How to Use, Feature Explanation, Best Practices, Workflow, etc.

---

## Files Created/Modified

### New Files
- `src/models/agent_performance_models.py` - Pydantic models
- `src/services/admin_profile_cache.py` - Admin profile caching
- `src/services/individual_agent_analyzer.py` - Individual agent analysis
- `tests/test_admin_profile_cache.py` - Cache tests
- `tests/test_individual_agent_analyzer.py` - Analyzer tests

### Modified Files
- `src/services/duckdb_storage.py` - Added 3 new tables
- `src/agents/agent_performance_agent.py` - Added individual breakdown mode
- `src/services/historical_data_manager.py` - Added agent snapshots
- `src/main.py` - Enhanced commands + new coaching report

---

## Next Steps

1. **Test with real data**: Run on recent Horatio/Boldr conversations
2. **Validate email extraction**: Ensure work emails are correctly extracted
3. **Calibrate thresholds**: Adjust FCR/escalation thresholds based on your standards
4. **Build coaching cadence**: Weekly coaching reports + monthly performance reviews
5. **Track improvements**: Use historical data to measure coaching effectiveness

---

**Last Updated**: October 24, 2025  
**Version**: 1.0

