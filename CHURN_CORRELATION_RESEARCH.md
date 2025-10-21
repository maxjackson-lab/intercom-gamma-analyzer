# Support Quality → Churn Correlation Research & Implementation Plan

**Project**: Intercom Analysis Tool - Churn Correlation Feature  
**Date**: October 19, 2025  
**Objective**: Quantify the relationship between support quality and customer outcomes (churn, NPS/CSAT, revenue retention)

---

## Executive Summary

### The Big Question
**Does improving support quality reduce churn and improve satisfaction, and by how much?**

### Why This Matters
We want to prove that good support experiences provide measurable business value, specifically in:
- Reducing customer churn
- Improving NPS/CSAT scores
- Increasing revenue retention
- Justifying support team resources and infrastructure

### The Challenge
We are **biased** toward proving support value. To avoid confirmation bias, we must use rigorous statistical methods, control for confounding variables, and honestly report limitations.

### Key Insight: Email as Source of Truth
**Join Key**: Customer email address
- **Intercom**: `conversation.customer.email`
- **Snowflake**: `customers.email` or `users.email`

This universal identifier allows us to connect support interactions with business outcomes.

---

## Part 1: Snowflake MCP Agent Queries

### Query 1: Churn Analysis by Support Quality

**Objective**: Correlate support metrics with churn events

```sql
WITH support_metrics AS (
  -- Calculate per-customer support metrics over 6 months
  SELECT 
    customer_email,
    COUNT(*) as total_tickets,
    AVG(resolution_time_hours) as avg_resolution_time,
    COUNT(*) FILTER (WHERE first_contact_resolved = true) / NULLIF(COUNT(*), 0)::float as fcr_rate,
    COUNT(*) FILTER (WHERE escalated = true) / NULLIF(COUNT(*), 0)::float as escalation_rate,
    MIN(ticket_created_at) as first_ticket_date,
    MAX(ticket_created_at) as last_ticket_date,
    -- Category breakdown
    COUNT(*) FILTER (WHERE category = 'Billing') as billing_tickets,
    COUNT(*) FILTER (WHERE category = 'Bug') as bug_tickets,
    COUNT(*) FILTER (WHERE category = 'Account') as account_tickets,
    COUNT(*) FILTER (WHERE category = 'API') as api_tickets
  FROM support_tickets
  WHERE ticket_created_at >= CURRENT_DATE - INTERVAL '6 months'
  GROUP BY customer_email
),

churn_data AS (
  -- Get churn events with relevant customer context
  SELECT
    email,
    churned_at,
    churn_reason,
    mrr_at_churn,
    customer_lifetime_months,
    plan_tier,
    cohort,
    signup_date
  FROM customers
  WHERE churned_at >= CURRENT_DATE - INTERVAL '6 months'
)

SELECT
  c.email,
  c.churned_at,
  c.churn_reason,
  c.mrr_at_churn,
  c.customer_lifetime_months,
  c.plan_tier,
  c.cohort,
  -- Support metrics in the 90 days BEFORE churn
  s.total_tickets as tickets_90d_before_churn,
  s.avg_resolution_time,
  s.fcr_rate as first_contact_resolution_rate,
  s.escalation_rate,
  s.billing_tickets,
  s.bug_tickets,
  s.account_tickets,
  s.api_tickets,
  DATEDIFF('day', s.last_ticket_date, c.churned_at) as days_since_last_ticket,
  -- Control variables
  c.signup_date as customer_age_at_churn
FROM churn_data c
LEFT JOIN support_metrics s ON c.email = s.customer_email
WHERE s.last_ticket_date <= c.churned_at OR s.last_ticket_date IS NULL
ORDER BY c.churned_at DESC;
```

**Key Metrics to Extract**:
- Support ticket count (90 days before churn)
- Average resolution time
- First Contact Resolution rate
- Escalation rate
- Category distribution
- Days between last ticket and churn

**Analysis to Perform**:
```python
import pandas as pd
from scipy import stats

# After getting data from Snowflake
df = pd.read_sql(query, snowflake_connection)

# Correlation: FCR rate vs Churn
churned = df[df['churned_at'].notna()]
active = df[df['churned_at'].isna()]

fcr_churned = churned['fcr_rate'].mean()
fcr_active = active['fcr_rate'].mean()

# T-test for significance
t_stat, p_value = stats.ttest_ind(churned['fcr_rate'].dropna(), active['fcr_rate'].dropna())

print(f"FCR Rate - Churned: {fcr_churned:.2%}")
print(f"FCR Rate - Active: {fcr_active:.2%}")
print(f"Difference: {(fcr_active - fcr_churned):.2%}")
print(f"P-value: {p_value:.4f} {'(Significant!)' if p_value < 0.05 else '(Not significant)'}")
```

---

### Query 2: NPS/CSAT Correlation with Support Quality

**Objective**: Prove support quality impacts satisfaction scores

```sql
WITH support_30_days_before AS (
  -- Support metrics in 30 days BEFORE survey
  SELECT
    s.customer_email,
    n.survey_date,
    COUNT(*) as tickets_before_survey,
    AVG(s.resolution_time_hours) as avg_resolution_time,
    COUNT(*) FILTER (WHERE s.first_contact_resolved = true) / NULLIF(COUNT(*), 0)::float as fcr_rate,
    COUNT(*) FILTER (WHERE s.escalated = true) / NULLIF(COUNT(*), 0)::float as escalation_rate,
    -- Category breakdown
    COUNT(*) FILTER (WHERE s.category = 'Billing') as billing_tickets,
    COUNT(*) FILTER (WHERE s.category = 'Bug') as bug_tickets,
    COUNT(*) FILTER (WHERE s.category = 'Account') as account_tickets
  FROM support_tickets s
  CROSS JOIN nps_responses n
  WHERE s.customer_email = n.customer_email
    AND s.ticket_created_at BETWEEN (n.survey_date - INTERVAL '30 days') AND n.survey_date
  GROUP BY s.customer_email, n.survey_date
)

SELECT
  n.customer_email,
  n.nps_score,
  n.csat_score,
  n.survey_date,
  c.plan_tier,
  c.cohort,
  s.tickets_before_survey,
  s.avg_resolution_time,
  s.fcr_rate,
  s.escalation_rate,
  s.billing_tickets,
  s.bug_tickets,
  s.account_tickets,
  -- NPS segmentation
  CASE 
    WHEN n.nps_score >= 9 THEN 'Promoter'
    WHEN n.nps_score >= 7 THEN 'Passive'
    ELSE 'Detractor'
  END as nps_segment,
  -- CSAT segmentation
  CASE
    WHEN n.csat_score >= 4 THEN 'Satisfied'
    WHEN n.csat_score >= 3 THEN 'Neutral'
    ELSE 'Unsatisfied'
  END as csat_segment
FROM nps_responses n
JOIN customers c ON n.customer_email = c.email
LEFT JOIN support_30_days_before s ON n.customer_email = s.customer_email AND n.survey_date = s.survey_date
WHERE n.survey_date >= CURRENT_DATE - INTERVAL '6 months';
```

**Analysis to Perform**:
```python
# Correlation: Support quality vs NPS
correlation = df[['fcr_rate', 'nps_score']].corr()
print(f"FCR vs NPS Correlation: {correlation.loc['fcr_rate', 'nps_score']:.3f}")

# Compare NPS by support quality segments
high_fcr = df[df['fcr_rate'] >= 0.7]['nps_score'].mean()
low_fcr = df[df['fcr_rate'] < 0.4]['nps_score'].mean()
print(f"NPS - High FCR: {high_fcr:.1f}")
print(f"NPS - Low FCR: {low_fcr:.1f}")
print(f"Difference: {high_fcr - low_fcr:.1f} points")
```

---

### Query 3: Cohort Analysis - Retention by Support Quality

**Objective**: Segment customers by support quality and compare retention

```sql
WITH customer_cohorts AS (
  SELECT
    email,
    DATE_TRUNC('month', signup_date) as cohort_month,
    plan_tier,
    signup_date,
    churned_at,
    CASE WHEN churned_at IS NULL THEN false ELSE true END as has_churned,
    DATEDIFF('month', signup_date, COALESCE(churned_at, CURRENT_DATE)) as lifetime_months
  FROM customers
  WHERE signup_date >= CURRENT_DATE - INTERVAL '12 months'
),

support_quality_segments AS (
  SELECT
    customer_email,
    COUNT(*) as total_tickets,
    COUNT(*) FILTER (WHERE first_contact_resolved = true) / NULLIF(COUNT(*), 0)::float as fcr_rate,
    AVG(resolution_time_hours) as avg_resolution_time,
    -- Segmentation
    CASE
      WHEN COUNT(*) FILTER (WHERE first_contact_resolved = true) / NULLIF(COUNT(*), 0)::float >= 0.7 THEN 'High FCR (≥70%)'
      WHEN COUNT(*) FILTER (WHERE first_contact_resolved = true) / NULLIF(COUNT(*), 0)::float >= 0.4 THEN 'Medium FCR (40-70%)'
      ELSE 'Low FCR (<40%)'
    END as fcr_segment,
    CASE
      WHEN AVG(resolution_time_hours) <= 4 THEN 'Fast (≤4h)'
      WHEN AVG(resolution_time_hours) <= 12 THEN 'Medium (4-12h)'
      ELSE 'Slow (>12h)'
    END as resolution_speed_segment
  FROM support_tickets
  WHERE ticket_created_at >= CURRENT_DATE - INTERVAL '12 months'
  GROUP BY customer_email
  HAVING COUNT(*) >= 2  -- At least 2 tickets for meaningful FCR calculation
)

SELECT
  c.cohort_month,
  c.plan_tier,
  COALESCE(s.fcr_segment, 'No Support Tickets') as fcr_segment,
  COALESCE(s.resolution_speed_segment, 'No Support Tickets') as resolution_speed,
  COUNT(*) as customers_in_segment,
  COUNT(*) FILTER (WHERE c.has_churned) as churned_count,
  COUNT(*) FILTER (WHERE c.has_churned) / NULLIF(COUNT(*), 0)::float as churn_rate,
  AVG(c.lifetime_months) as avg_lifetime_months,
  AVG(s.total_tickets) as avg_tickets_per_customer
FROM customer_cohorts c
LEFT JOIN support_quality_segments s ON c.email = s.customer_email
GROUP BY c.cohort_month, c.plan_tier, s.fcr_segment, s.resolution_speed_segment
ORDER BY c.cohort_month, churn_rate;
```

**Expected Output**: 
```
cohort_month | plan_tier | fcr_segment | resolution_speed | customers | churned | churn_rate | avg_lifetime
2024-04      | Pro       | High FCR    | Fast            | 234       | 12      | 5.1%       | 8.2 months
2024-04      | Pro       | Medium FCR  | Medium          | 189       | 23      | 12.2%      | 6.1 months
2024-04      | Pro       | Low FCR     | Slow            | 87        | 18      | 20.7%      | 4.8 months
```

This would show: **Higher FCR = Lower Churn** (if the hypothesis is true)

---

### Query 4: Category-Specific Churn Risk

**Objective**: Which support categories predict churn?

```sql
WITH customer_category_exposure AS (
  SELECT
    customer_email,
    COUNT(*) as total_tickets,
    -- Category percentages
    COUNT(*) FILTER (WHERE category = 'Billing') / NULLIF(COUNT(*), 0)::float as billing_pct,
    COUNT(*) FILTER (WHERE category = 'Bug') / NULLIF(COUNT(*), 0)::float as bug_pct,
    COUNT(*) FILTER (WHERE category = 'API') / NULLIF(COUNT(*), 0)::float as api_pct,
    COUNT(*) FILTER (WHERE category = 'Account') / NULLIF(COUNT(*), 0)::float as account_pct,
    -- Category-specific resolution quality
    AVG(resolution_time_hours) FILTER (WHERE category = 'Billing') as billing_resolution_time,
    COUNT(*) FILTER (WHERE category = 'Billing' AND escalated = true) / NULLIF(COUNT(*) FILTER (WHERE category = 'Billing'), 0)::float as billing_escalation_rate,
    -- Multiple category flag
    COUNT(DISTINCT category) as categories_contacted
  FROM support_tickets
  WHERE ticket_created_at >= CURRENT_DATE - INTERVAL '12 months'
  GROUP BY customer_email
  HAVING COUNT(*) >= 2  -- At least 2 tickets
)

SELECT
  c.plan_tier,
  -- Category exposure segments
  CASE
    WHEN ce.billing_pct > 0.5 THEN 'Billing-Heavy'
    WHEN ce.bug_pct > 0.5 THEN 'Bug-Heavy'
    WHEN ce.categories_contacted >= 3 THEN 'Multi-Category'
    ELSE 'Other'
  END as category_profile,
  COUNT(*) as customers,
  COUNT(*) FILTER (WHERE c.churned_at IS NOT NULL) as churned,
  COUNT(*) FILTER (WHERE c.churned_at IS NOT NULL) / NULLIF(COUNT(*), 0)::float as churn_rate,
  AVG(ce.total_tickets) as avg_tickets,
  AVG(ce.billing_resolution_time) as avg_billing_resolution_time,
  AVG(ce.billing_escalation_rate) as avg_billing_escalation_rate
FROM customers c
LEFT JOIN customer_category_exposure ce ON c.email = ce.customer_email
WHERE c.signup_date >= CURRENT_DATE - INTERVAL '12 months'
GROUP BY c.plan_tier, category_profile
ORDER BY churn_rate DESC;
```

**Hypothesis to Test**:
- Billing-heavy customers have higher churn risk
- Bug-heavy customers churn faster
- Multi-category issues compound churn risk
- Poor resolution in high-impact categories (Billing) predicts churn

---

### Query 5: Time-Series Correlation

**Objective**: Track support quality and churn over time to find leading indicators

```sql
WITH monthly_metrics AS (
  SELECT
    DATE_TRUNC('month', ticket_created_at) as month,
    COUNT(*) as total_tickets,
    AVG(resolution_time_hours) as avg_resolution_time,
    COUNT(*) FILTER (WHERE first_contact_resolved = true) / NULLIF(COUNT(*), 0)::float as fcr_rate,
    COUNT(*) FILTER (WHERE escalated = true) / NULLIF(COUNT(*), 0)::float as escalation_rate,
    COUNT(DISTINCT customer_email) as unique_customers_with_tickets
  FROM support_tickets
  WHERE ticket_created_at >= CURRENT_DATE - INTERVAL '12 months'
  GROUP BY DATE_TRUNC('month', ticket_created_at)
),

monthly_churn AS (
  SELECT
    DATE_TRUNC('month', churned_at) as month,
    COUNT(*) as churn_count,
    COUNT(*) / (SELECT COUNT(*) FROM customers WHERE churned_at IS NULL)::float as churn_rate,
    AVG(mrr_at_churn) as avg_mrr_churned
  FROM customers
  WHERE churned_at >= CURRENT_DATE - INTERVAL '12 months'
  GROUP BY DATE_TRUNC('month', churned_at)
),

monthly_satisfaction AS (
  SELECT
    DATE_TRUNC('month', survey_date) as month,
    AVG(nps_score) as avg_nps,
    AVG(csat_score) as avg_csat,
    COUNT(*) as survey_responses
  FROM nps_responses
  WHERE survey_date >= CURRENT_DATE - INTERVAL '12 months'
  GROUP BY DATE_TRUNC('month', survey_date)
)

SELECT
  m.month,
  m.total_tickets,
  m.avg_resolution_time,
  m.fcr_rate,
  m.escalation_rate,
  ch.churn_count,
  ch.churn_rate,
  s.avg_nps,
  s.avg_csat
FROM monthly_metrics m
LEFT JOIN monthly_churn ch ON m.month = ch.month
LEFT JOIN monthly_satisfaction s ON m.month = s.month
ORDER BY m.month;
```

**Analysis to Perform**:
```python
# Calculate correlation coefficients
correlations = df[['fcr_rate', 'escalation_rate', 'avg_resolution_time', 'churn_rate', 'avg_nps']].corr()

# Lag analysis (does poor support THIS month predict churn NEXT month?)
df['churn_rate_next_month'] = df['churn_rate'].shift(-1)
lag_correlation = df[['fcr_rate', 'churn_rate_next_month']].corr()

print(f"FCR vs Immediate Churn: {correlations.loc['fcr_rate', 'churn_rate']:.3f}")
print(f"FCR vs Next Month Churn: {lag_correlation.loc['fcr_rate', 'churn_rate_next_month']:.3f}")
```

---

### Query 6: Control Group Comparison

**Objective**: Compare customers WITH support interactions vs WITHOUT to isolate support's impact

```sql
WITH customers_with_support AS (
  SELECT DISTINCT customer_email
  FROM support_tickets
  WHERE ticket_created_at >= CURRENT_DATE - INTERVAL '6 months'
),

customer_segments AS (
  SELECT
    c.email,
    c.plan_tier,
    c.cohort,
    c.mrr,
    c.signup_date,
    c.churned_at,
    CASE WHEN cws.customer_email IS NOT NULL THEN 'With Support' ELSE 'No Support' END as support_segment
  FROM customers c
  LEFT JOIN customers_with_support cws ON c.email = cws.customer_email
  WHERE c.signup_date >= CURRENT_DATE - INTERVAL '12 months'
)

SELECT
  plan_tier,
  cohort,
  support_segment,
  COUNT(*) as customers,
  COUNT(*) FILTER (WHERE churned_at IS NOT NULL) as churned,
  COUNT(*) FILTER (WHERE churned_at IS NOT NULL) / NULLIF(COUNT(*), 0)::float as churn_rate,
  AVG(DATEDIFF('month', signup_date, COALESCE(churned_at, CURRENT_DATE))) as avg_lifetime_months,
  AVG(mrr) as avg_mrr
FROM customer_segments
GROUP BY plan_tier, cohort, support_segment
ORDER BY plan_tier, cohort, support_segment;
```

**Hypothesis**: 
- Customers with NO support tickets might have LOWER churn (happy, don't need help)
- OR customers with NO support tickets might have HIGHER churn (disengaged, didn't bother asking for help)
- This helps us understand if support interaction itself is good/bad/neutral

---

## Part 2: Perplexity Deep Research Prompt

```markdown
# Research Request: Support Quality → Business Outcomes Correlation in SaaS

## Context

We are building a feature to quantify the relationship between customer support quality and business outcomes (churn, NPS/CSAT, revenue retention) in a SaaS product.

**Available Data**:
- Intercom support conversations (~1000 per analysis period)
- Snowflake data warehouse (customer churn, NPS/CSAT, revenue, usage)
- Join key: Customer email address
- Historical data: 6-12 months available

**Scale**: Small-scale internal tool, 1-2 users, ~1000 conversations per analysis

**Critical Bias**: We are motivated to prove support provides value - need rigorous methods to avoid confirmation bias

---

## Research Questions

### 1. Statistical Foundations

**Q**: What are the established statistical methods for proving support quality → churn causation (not just correlation)?

**Needed**:
- Specific statistical tests appropriate for this analysis
- Sample size requirements for valid conclusions
- P-value thresholds and confidence intervals
- Methods to control for confounding variables
- How to prove causation vs mere correlation

**Context**: At ~1000 conversations and potentially 200-500 customers per period, do we have sufficient statistical power?

### 2. Industry Research & Benchmarks

**Q**: What does published research say about support-churn correlation in SaaS?

**Needed**:
- Published studies with actual correlation coefficients
- Industry benchmarks for FCR (First Contact Resolution) impact on churn
- Quantified impact of resolution time on NPS/CSAT
- Case studies showing ROI of support quality improvements
- Meta-analyses if available

**Goal**: Understand what effect sizes are realistic and how our findings compare to industry norms.

### 3. Temporal Dynamics & Lag Effects

**Q**: How do we handle the time lag between support interactions and outcomes?

**Needed**:
- Optimal lookback window (30/60/90 days before churn to examine support?)
- How to analyze leading vs lagging indicators
- Time-series correlation methods
- Seasonality adjustments
- Whether to use support metrics from specific time windows or cumulative

**Example**: If a customer churns on Oct 15, do we look at:
- All their support history?
- Last 30 days before churn?
- Last 90 days?
- Time-weighted (recent tickets matter more)?

### 4. Causal Inference Methods

**Q**: How do we prove support quality CAUSES better outcomes (not just correlates)?

**Needed**:
- Propensity score matching implementation
- Difference-in-differences analysis approach
- Instrumental variables that could be used
- Natural experiments or quasi-experimental designs
- A/B testing frameworks for support quality
- Regression discontinuity designs

**Challenge**: We can't randomly assign support quality, so need observational causal inference methods.

### 5. Confounding Variables & Controls

**Q**: What factors might create spurious correlations between support and outcomes?

**Potential Confounds**:
- Plan tier (enterprise customers get better support AND have lower churn anyway)
- Product usage (high-usage customers create more tickets AND are stickier)
- Market segment (B2B vs B2C have different support needs and churn patterns)
- Customer lifecycle stage (new customers vs mature accounts)
- Product quality (bug-heavy periods increase both support volume and churn)

**Needed**: 
- How to control for these in regression analysis
- Which confounds are most critical
- Methods like multi-variate regression, stratification, matching

### 6. Category-Specific Analysis

**Q**: Do different support categories have different business impacts?

**Hypothesis**:
- Billing tickets → high churn risk (payment friction)
- Bug tickets → medium churn risk (product dissatisfaction)
- Product questions → low churn risk (engagement signal)
- API tickets → ??? (developers might be more tolerant OR critical)

**Needed**:
- Statistical methods for category-specific risk quantification
- How to handle category interaction effects
- Relative risk calculations
- Survival analysis by category exposure

### 7. Predictive Modeling

**Q**: Can we build models that predict churn using support metrics?

**Needed**:
- Best ML algorithms (logistic regression, random forest, XGBoost)
- Feature engineering from support data
- Model validation approaches (cross-validation, holdout sets)
- Calibration methods
- Threshold optimization for actionable predictions
- Interpretability techniques (SHAP values to explain predictions)

**Goal**: "Customer X has 67% churn risk in next 30 days because [support reasons]"

### 8. Small-Scale Statistical Power

**Q**: At our scale (~1000 conversations, 200-500 customers per period), what can we validly conclude?

**Needed**:
- Power analysis for detecting correlations at our sample size
- Minimum detectable effect size
- When to acknowledge "insufficient data"
- How to increase power (longer time periods, pooling data)
- Bayesian approaches for small samples

**Critical**: We need honest assessment of what we CAN'T prove at small scale.

### 9. Data Integration Architecture

**Q**: Best practices for joining operational (Intercom) and analytical (Snowflake) data?

**Needed**:
- ETL pipeline design
- Real-time vs batch processing trade-offs
- Change Data Capture (CDC) patterns
- Data warehouse schema design for support analytics
- Query optimization for large joins
- Caching strategies

**Specific**: How to efficiently join 1000 Intercom conversations with Snowflake customer data by email?

### 10. Bias Mitigation & Validation

**Q**: How do we ensure findings are valid despite our bias toward proving support value?

**Needed**:
- Null hypothesis testing protocols
- Pre-registration of hypotheses (to avoid p-hacking)
- Sensitivity analysis approaches
- Alternative explanation testing
- Independent validation methods
- Honest limitation disclosure

**Goal**: Build credibility by acknowledging what we DON'T know and testing against our hypotheses.

---

## Expected Deliverables from Research

1. **Statistical Framework**
   - Specific tests to run (t-tests, correlations, regressions)
   - Required sample sizes and power calculations
   - Significance thresholds and confidence intervals

2. **SQL Query Patterns**
   - Validated join strategies
   - Window functions for time-based analysis
   - Cohort analysis templates

3. **Python Analysis Code**
   - scipy.stats examples for correlations
   - scikit-learn for predictive modeling
   - statsmodels for regression analysis
   - Visualization examples (seaborn, plotly)

4. **Interpretation Guidelines**
   - How to read correlation coefficients
   - What effect sizes are meaningful in SaaS
   - How to present findings to non-technical executives

5. **Limitations Documentation**
   - What we can conclude at our scale
   - What we cannot prove
   - Caveats to disclose

6. **Implementation Roadmap**
   - Phase 1: Data extraction and validation
   - Phase 2: Statistical analysis
   - Phase 3: Predictive modeling
   - Phase 4: Integration with Intercom analysis

---

## Success Criteria

### Statistical Validity
- P-values < 0.05 for claimed correlations
- Confidence intervals that exclude zero
- Multiple hypothesis correction (Bonferroni if testing many categories)
- Adequate statistical power (>0.8) for detected effects

### Business Actionability
- Clear quantification: "10% FCR improvement → 2.3% churn reduction"
- Category-specific insights: "Billing tickets with poor resolution → 3x churn risk"
- Predictive value: "These support patterns predict 70% of churn events 30 days in advance"

### Honest Limitations
- Acknowledge correlation ≠ causation where we can't prove causation
- Disclose sample size limitations
- Note alternative explanations
- Specify confidence levels for all claims

---

## Next Steps

1. **Run Snowflake queries** to see what data is actually available
2. **Run Perplexity research** to understand statistical best practices
3. **Share findings** with development team
4. **Design solution** based on data reality and proven methods
5. **Implement** ChurnCorrelationAgent and data integration
6. **Validate** findings with statistical rigor
7. **Deploy** as separate feature with clear limitations disclosed

The goal is to build something that honestly and rigorously proves (or disproves!) the support-churn connection, providing actionable intelligence for resource allocation and support strategy.

