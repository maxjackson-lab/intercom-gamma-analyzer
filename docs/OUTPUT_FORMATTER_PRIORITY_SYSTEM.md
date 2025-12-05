# OutputFormatterAgent: Priority Severity System

## Overview

The Priority Severity System keeps the highest-impact customer issues front and center in every Voice of Customer report. Instead of alarmist “fire” language, topics are labeled as **High Priority**, **Medium Priority**, or **Monitoring** based on a transparent composite score that blends sentiment, topic share, Fin AI performance, CSAT, and quality metrics.

## Composite Severity Scoring

### Severity Components

Each topic receives a severity score (range 1.0–3.5) based on:

1. **Base Score**: 1.0 (all topics start here)
2. **Sentiment Negativity** (0–0.8 points)
   - SEVERE pain level: +0.8
   - MODERATE: +0.3
   - LOW: +0.1
   - Fallback: keyword scan of sentiment insight when `pain_level` missing
3. **Volume Percentage** (0–0.5 points)
   - Formula: `min(volume_pct / 100 * 0.5, 0.5)`
   - Example: 40% volume → +0.2 pts
4. **Fin AI Failure Rate** (0–0.6 points)
   - Uses worst resolution rate from Free/Paid tiers (or legacy metrics)
   - Formula: `max(0.0, 0.6 - resolution_rate)`
5. **CSAT Impact** (0–0.4 points)
   - Only applied when the topic has ≥3 rated conversations
   - Formula: `(3.5 - avg_csat) / 3.5 * 0.4`
6. **Quality Metrics (FCR)** (0–0.5 points)
   - Formula: `0.5 - fcr` when FCR < 50%
7. **Analytical Callouts** (+0.3 per callout)
   - Correlations, churn risk, or quality anomalies

### Severity Labels

- **🔴 High Priority** (score ≥ 2.5): Needs executive attention this week
- **🟡 Medium Priority** (score ≥ 1.8): Significant friction to monitor closely
- **⚪️ Monitoring** (score < 1.8): Keep an eye on trends, but not urgent

### Example Calculations

**Scenario 1: High-Severity Billing Issue**
- Base: 1.0
- Sentiment (SEVERE): +0.8
- Volume (45%): +0.225
- Fin failure (30% resolution): +0.3
- CSAT (2.1/5): +0.16
- **Total: 2.485** → 🟡 Medium Priority (borderline High)

**Scenario 2: Critical Churn Risk**
- Base: 1.0
- Sentiment (SEVERE): +0.8
- Volume (15%): +0.075
- Fin failure (20% resolution): +0.4
- CSAT (1.8/5): +0.194
- FCR (35%): +0.15
- Churn callout: +0.3
- **Total: 2.919** → 🔴 High Priority

## Executive Summary Enhancements

### Section Ordering

1. **🔎 Priority Issues** – top 3–4 issues with customer quotes
2. **📊 High-Volume Drivers** – ticket share view for workload planning
3. **🏢 BPO Vendor Snapshot** – workload & pressure per vendor
4. **📈 Volume & Segmentation Overview** – paid vs. free breakdown

### Customer Quotes in Priority Issues

Top issues include a 100-character customer quote (when available) pulled from `TopicExamplesAgent` so the audience can “hear the customer” directly.

### In-Line Severity Explainer

The executive summary now includes an italicized line explaining how the priority scale works: `High ≥2.5 • Medium ≥1.8 • Monitoring <1.8`, with a reminder that the score blends sentiment, topic share, Fin performance, CSAT, and quality metrics.

## Topic Card Enhancements

### Severity Badges in Headers

Topic cards display severity badges directly in the header:

```markdown
### 🔴 High Priority Billing Issues ↑
**50 tickets / 40% of weekly volume**
```

The badge text keeps the tone professional without “fire” metaphors.

## Severity-Based Sorting

### Default Behavior (Volume-Based)

By default, cards are sorted by ticket volume, matching historical expectations for operational reviews.

### Opt-In Severity Sorting

Set the environment variable to surface smaller but riskier topics first:

```bash
export SORT_TOPICS_BY_SEVERITY=true
```

When enabled, topics are sorted by severity (primary) and volume (secondary), ensuring churn-risk topics appear before large-but-manageable ones.

### When to Use Severity Sorting

Use severity sorting when:
- Executives need quick visibility into churn or trust-breaking issues
- Quality metrics matter more than raw volume
- You’re running proactive improvement sessions

Stick with volume sorting when:
- Planning staffing or queue management
- Comparing week-over-week volume changes
- You need parity with historical reports

## Integration with Existing Agents

### Required Agent Outputs

1. **TopicSentimentAgent** – provides `pain_level` and narrative sentiment
2. **TopicExamplesAgent** – provides conversation previews for quotes
3. **FinPerformanceAgent** – supplies tier-level resolution metrics
4. **QualityInsightsAgent** – supplies FCR/quality anomalies
5. **SegmentationAgent** – ensures CSAT ratings are attached to conversations

### Backward Compatibility

- Missing `pain_level` falls back to text scanning for tone
- Missing CSAT means severity proceeds without CSAT penalties
- Missing examples simply omits quotes for that topic
- Sorting stays volume-first unless the severity flag is enabled

## Testing

Run the priority severity tests to validate functionality:

```bash
pytest tests/test_output_formatter_agent.py::test_get_severity_badge
pytest tests/test_output_formatter_agent.py::test_calculate_topic_severity_with_volume_and_csat
pytest tests/test_output_formatter_agent.py::test_executive_summary_includes_customer_quotes
pytest tests/test_output_formatter_agent.py::test_severity_based_topic_sorting
```

## Troubleshooting

### Severity badges missing on cards
**Cause:** `_get_severity_badge()` not called or badge not passed to `_format_topic_card()`.  
**Fix:** Ensure `severity_badge` parameter receives `"{emoji} {label}"`.

### No customer quotes in top issues
**Cause:** `TopicExamplesAgent` missing or returned empty data.  
**Fix:** Verify the agent ran and produced at least one example per topic.

### CSAT impact not reflected
**Cause:** Fewer than 3 rated conversations for that topic.  
**Fix:** Confirm Intercom is returning `conversation_rating` data and check logs for “CSAT aggregation” counts.

### Severity sorting not taking effect
**Cause:** `settings.sort_topics_by_severity` is False (default).  
**Fix:** Set `SORT_TOPICS_BY_SEVERITY=true` before running the analysis (restart if already running).

## Future Enhancements

1. Dynamic thresholds that adapt based on historical baselines
2. Trend-aware severity boosts for rapidly worsening topics
3. Personalized weighting (e.g., heavier CSAT impact for support leadership)
4. Notifications when topics cross the High Priority threshold



