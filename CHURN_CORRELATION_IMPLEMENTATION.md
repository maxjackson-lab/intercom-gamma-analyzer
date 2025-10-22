# Support-Churn Correlation Feature: Infrastructure Implementation Plan

**Based on Perplexity Deep Research**  
**Date**: October 19, 2025  
**Status**: Design Phase - Ready for Implementation

---

## Executive Summary

Based on comprehensive research, we're implementing a **ChurnCorrelationAgent** that joins Intercom support data with Snowflake customer analytics to quantify the relationship between support quality and business outcomes.

### Key Design Decisions (From Research)

1. **Join Key**: Customer email address (universal identifier)
2. **Statistical Framework**: Point-biserial correlation + Propensity Score Matching for causal claims
3. **Predictive Model**: XGBoost (proven best for SaaS churn, AUROC 0.85-0.90)
4. **Data Architecture**: Batch ETL with daily refresh (sufficient for churn prediction)
5. **Critical Metrics**: FCR rate, Resolution time, Escalation rate, Category distribution
6. **Bias Mitigation**: Pre-registered hypotheses, null hypothesis testing, honest limitation reporting

---

## Part 1: Data Architecture

### 1.1 Snowflake → Intercom Data Flow

```text
Daily ETL Pipeline:
┌─────────────┐
│  Snowflake  │ ─────────┐
│  Warehouse  │          │
└─────────────┘          │
                         ├──→ Feature Store ──→ Correlation Analysis
┌─────────────┐          │
│  Intercom   │ ─────────┘
│     API     │
└─────────────┘

Join Key: customer.email
Refresh: Daily at 2 AM UTC
Storage: DuckDB (local) + Snowflake (warehouse)
```

### 1.2 Schema Design

**New Table: `customer_support_outcomes`**

```sql
CREATE TABLE customer_support_outcomes (
    customer_id VARCHAR(50) PRIMARY KEY,
    email VARCHAR(255) NOT NULL,
    observation_date DATE NOT NULL,
    
    -- Support metrics (90-day lookback)
    total_tickets_90d INT,
    fcr_rate_90d DECIMAL(5,3),
    avg_resolution_hours_90d DECIMAL(10,2),
    escalation_rate_90d DECIMAL(5,3),
    pct_billing_90d DECIMAL(5,3),
    pct_bug_90d DECIMAL(5,3),
    pct_account_90d DECIMAL(5,3),
    
    -- Outcome metrics
    churned BOOLEAN,
    churn_date DATE,
    churn_reason VARCHAR(500),
    days_to_churn INT,  -- Days from observation to churn
    
    -- Control variables (from Snowflake)
    plan_tier VARCHAR(50),
    tenure_months INT,
    mrr DECIMAL(10,2),
    usage_score DECIMAL(5,3),
    
    -- Satisfaction metrics
    last_nps_score INT,
    last_csat_score DECIMAL(3,1),
    nps_trend VARCHAR(20),  -- 'improving', 'stable', 'declining'
    
    -- Metadata
    data_quality_score DECIMAL(3,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_email (email),
    INDEX idx_observation_date (observation_date),
    INDEX idx_churn (churned, churn_date)
);
```

### 1.3 ETL Pipeline Implementation

**Python ETL Script** (runs daily via cron/Airflow):

```python
import pandas as pd
import snowflake.connector
from datetime import datetime, timedelta
import duckdb

class ChurnCorrelationETL:
    """ETL pipeline for support-churn correlation analysis"""
    
    def __init__(self, snowflake_config, intercom_client):
        self.sf_conn = snowflake.connector.connect(**snowflake_config)
        self.intercom_client = intercom_client
        self.duckdb_conn = duckdb.connect('outputs/churn_correlation.duckdb')
        
    async def run_daily_sync(self):
        """Daily ETL job"""
        print("🔄 Starting daily support-churn correlation sync...")
        
        # Step 1: Extract from Snowflake
        sf_data = self.extract_snowflake_data()
        print(f"   ✅ Extracted {len(sf_data)} customers from Snowflake")
        
        # Step 2: Extract from Intercom (via existing services)
        intercom_data = await self.extract_intercom_data(sf_data['email'].tolist())
        print(f"   ✅ Extracted {len(intercom_data)} conversations from Intercom")
        
        # Step 3: Join and transform
        joined_data = self.join_and_transform(sf_data, intercom_data)
        print(f"   ✅ Joined datasets: {len(joined_data)} customer records")
        
        # Step 4: Load to DuckDB
        self.load_to_duckdb(joined_data)
        print(f"   ✅ Loaded to DuckDB")
        
        # Step 5: Compute correlations
        correlations = self.compute_correlations()
        print(f"   ✅ Computed {len(correlations)} correlations")
        
        return correlations
    
    def extract_snowflake_data(self):
        """Extract customer churn and satisfaction data from Snowflake"""
        query = """
        SELECT
            email,
            customer_id,
            plan_tier,
            tenure_months,
            mrr,
            usage_score,
            churned,
            churn_date,
            churn_reason,
            last_nps_score,
            last_csat_score,
            CURRENT_DATE as observation_date
        FROM customers
        WHERE observation_date >= CURRENT_DATE - INTERVAL '12 months'
        """
        
        return pd.read_sql(query, self.sf_conn)
    
    async def extract_intercom_data(self, emails):
        """Extract support conversations for given customer emails"""
        # Use existing Intercom service
        from src.services.chunked_fetcher import ChunkedFetcher
        
        fetcher = ChunkedFetcher()
        conversations = await fetcher.fetch_conversations_chunked(
            start_date=datetime.now() - timedelta(days=90),
            end_date=datetime.now()
        )
        
        # Filter to customers in Snowflake dataset
        email_set = set(emails)
        filtered = [
            conv for conv in conversations
            if conv.get('customer', {}).get('email') in email_set
        ]
        
        return filtered
    
    def join_and_transform(self, sf_data, intercom_data):
        """Join Snowflake and Intercom data, compute support metrics"""
        # Group conversations by customer email
        support_metrics = {}
        
        for conv in intercom_data:
            email = conv.get('customer', {}).get('email')
            if not email:
                continue
            
            if email not in support_metrics:
                support_metrics[email] = {
                    'total_tickets': 0,
                    'fcr_count': 0,
                    'resolution_times': [],
                    'escalated_count': 0,
                    'categories': []
                }
            
            metrics = support_metrics[email]
            metrics['total_tickets'] += 1
            
            # FCR (first contact resolved - simplified)
            if conv.get('conversation_rating', {}).get('rating') in [4, 5]:
                metrics['fcr_count'] += 1
            
            # Resolution time
            if conv.get('created_at') and conv.get('updated_at'):
                resolution_hours = (conv['updated_at'] - conv['created_at']) / 3600
                metrics['resolution_times'].append(resolution_hours)
            
            # Escalation (simplified)
            if conv.get('admin_assignee_id'):
                metrics['escalated_count'] += 1
            
            # Category
            tags = conv.get('tags', {}).get('tags', [])
            for tag in tags:
                metrics['categories'].append(tag.get('name', ''))
        
        # Calculate aggregate metrics
        support_df = []
        for email, metrics in support_metrics.items():
            total = metrics['total_tickets']
            support_df.append({
                'email': email,
                'total_tickets_90d': total,
                'fcr_rate_90d': metrics['fcr_count'] / total if total > 0 else None,
                'avg_resolution_hours_90d': (
                    sum(metrics['resolution_times']) / len(metrics['resolution_times'])
                    if metrics['resolution_times'] else None
                ),
                'escalation_rate_90d': metrics['escalated_count'] / total if total > 0 else None,
                'pct_billing_90d': (
                    sum(1 for c in metrics['categories'] if 'billing' in c.lower()) / total
                    if total > 0 else 0
                ),
                'pct_bug_90d': (
                    sum(1 for c in metrics['categories'] if 'bug' in c.lower()) / total
                    if total > 0 else 0
                )
            })
        
        support_df = pd.DataFrame(support_df)
        
        # Join with Snowflake data
        joined = sf_data.merge(support_df, on='email', how='left')
        
        # Fill NaN for customers with no support tickets
        support_cols = ['total_tickets_90d', 'fcr_rate_90d', 'avg_resolution_hours_90d', 
                       'escalation_rate_90d', 'pct_billing_90d', 'pct_bug_90d']
        joined[support_cols] = joined[support_cols].fillna(0)
        
        return joined
    
    def load_to_duckdb(self, data):
        """Load joined data to DuckDB for analysis"""
        self.duckdb_conn.execute("DROP TABLE IF EXISTS customer_support_outcomes")
        self.duckdb_conn.execute("""
            CREATE TABLE customer_support_outcomes AS 
            SELECT * FROM data
        """)
    
    def compute_correlations(self):
        """Compute statistical correlations"""
        from scipy import stats
        
        query = "SELECT * FROM customer_support_outcomes WHERE churned IS NOT NULL"
        df = self.duckdb_conn.execute(query).df()
        
        support_metrics = ['fcr_rate_90d', 'avg_resolution_hours_90d', 'escalation_rate_90d', 
                          'pct_billing_90d']
        
        correlations = []
        for metric in support_metrics:
            valid_df = df[[metric, 'churned']].dropna()
            
            if len(valid_df) < 30:
                continue
            
            r, p_value = stats.pointbiserialr(valid_df['churned'], valid_df[metric])
            
            correlations.append({
                'metric': metric,
                'correlation': r,
                'p_value': p_value,
                'n': len(valid_df),
                'significant': p_value < 0.05
            })
        
        return pd.DataFrame(correlations)
```

---

## Part 2: ChurnCorrelationAgent Implementation

### 2.1 New Agent: ChurnCorrelationAgent

```python
"""
ChurnCorrelationAgent: Specialized in correlating support quality with business outcomes.

Responsibilities:
- Query Snowflake for customer churn and satisfaction data
- Join with Intercom support data by email
- Calculate statistical correlations
- Run significance tests
- Identify category-specific churn predictors
- Generate causal estimates (via PSM when applicable)
"""

import logging
from typing import Dict, Any, List
from datetime import datetime
import pandas as pd
from scipy import stats

from src.agents.base_agent import BaseAgent, AgentResult, AgentContext, ConfidenceLevel

logger = logging.getLogger(__name__)


class ChurnCorrelationAgent(BaseAgent):
    """Agent specialized in support-churn correlation analysis"""
    
    def __init__(self):
        super().__init__(
            name="ChurnCorrelationAgent",
            model="gpt-4o",  # For interpretation of statistical findings
            temperature=0.2  # Low temperature for factual analysis
        )
    
    def get_agent_specific_instructions(self) -> str:
        """Churn correlation agent specific instructions"""
        return """
CHURN CORRELATION AGENT SPECIFIC RULES:

1. CRITICAL BIAS ACKNOWLEDGMENT:
   - We are biased toward proving support value
   - Use null hypothesis testing: assume support DOESN'T matter, then try to reject
   - Report ALL findings honestly, including null results
   - Never cherry-pick significant results - report all tests performed

2. STATISTICAL RIGOR:
   - Only claim correlation if p < 0.05 (preferably p < 0.01)
   - Always report confidence intervals
   - Distinguish correlation from causation
   - Control for confounding variables (plan tier, tenure, usage)
   - Acknowledge limitations due to sample size

3. CRITICAL CONTEXT FOR SUPPORT DATA:
   - Support tickets are NORMAL business operations
   - Customers contact support BECAUSE they're unhappy (this is expected)
   - Negative sentiment ≠ product failure
   - Focus on: Resolution efficiency, escalation patterns, volume trends
   - What matters: Resolution time changes, FCR trends, category-specific risks

4. MEANINGFUL vs MEANINGLESS METRICS:
   - NOT meaningful: "98% negative sentiment" (it's support!)
   - MEANINGFUL: "FCR rate 45% for churners vs 68% for retained (p=0.003)"
   - NOT meaningful: "Customers are frustrated"
   - MEANINGFUL: "Billing resolution time increased 23% month-over-month"

5. OUTPUT REQUIREMENTS:
   - Statistical correlation coefficients with p-values
   - Confidence intervals for all estimates
   - Sample sizes for each analysis
   - Category-specific churn risks
   - Honest assessment of what we CAN and CANNOT conclude
"""
    
    async def execute(self, context: AgentContext) -> AgentResult:
        """
        Execute support-churn correlation analysis.
        
        Workflow:
        1. Query Snowflake for churn/NPS/CSAT data
        2. Join with Intercom data by email
        3. Calculate correlations
        4. Run significance tests
        5. Generate statistical report
        """
        start_time = datetime.now()
        
        try:
            # Step 1: Extract Snowflake data (using MCP or direct connector)
            snowflake_data = await self.query_snowflake(context)
            
            # Step 2: Join with Intercom conversations
            joined_data = self.join_datasets(
                snowflake_data,
                context.conversations,
                join_key='email'
            )
            
            # Step 3: Calculate support metrics per customer
            customer_metrics = self.calculate_customer_support_metrics(joined_data)
            
            # Step 4: Statistical analysis
            correlations = self.compute_correlations(customer_metrics)
            category_risks = self.analyze_category_specific_risk(customer_metrics)
            fcr_impact = self.analyze_fcr_impact(customer_metrics)
            
            # Step 5: Causal analysis (if enough data)
            causal_estimate = None
            if len(customer_metrics) >= 200:
                causal_estimate = self.propensity_score_matching(customer_metrics)
            
            # Prepare result
            result_data = {
                'correlations': correlations,
                'category_risks': category_risks,
                'fcr_impact': fcr_impact,
                'causal_estimate': causal_estimate,
                'sample_size': len(customer_metrics),
                'statistical_power': self.assess_statistical_power(customer_metrics),
                'limitations': self.identify_limitations(customer_metrics)
            }
            
            # Calculate confidence
            confidence, confidence_level = self.calculate_confidence(result_data, context)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return AgentResult(
                agent_name=self.name,
                success=True,
                data=result_data,
                confidence=confidence,
                confidence_level=confidence_level,
                limitations=result_data['limitations'],
                sources=["Snowflake customer data", "Intercom support conversations", "Statistical analysis"],
                execution_time=execution_time,
                token_count=0  # Statistical analysis, minimal LLM use
            )
            
        except Exception as e:
            logger.error(f"ChurnCorrelationAgent error: {e}")
            return AgentResult(
                agent_name=self.name,
                success=False,
                data={},
                confidence=0.0,
                confidence_level=ConfidenceLevel.LOW,
                error_message=str(e)
            )
    
    async def query_snowflake(self, context: AgentContext):
        """Query Snowflake for customer outcomes"""
        # Placeholder - would use Snowflake MCP or connector
        query = """
        SELECT
            email,
            customer_id,
            plan_tier,
            tenure_months,
            mrr,
            usage_score,
            churned,
            churn_date,
            churn_reason,
            last_nps_score,
            last_csat_score
        FROM customers
        WHERE observation_date >= DATEADD(month, -6, CURRENT_DATE)
        """
        # Return pandas DataFrame
        pass
    
    def join_datasets(self, snowflake_df, conversations, join_key='email'):
        """Join Snowflake and Intercom data"""
        # Extract customer emails from conversations
        conversation_emails = {}
        for conv in conversations:
            email = conv.get('customer', {}).get('email')
            if email:
                if email not in conversation_emails:
                    conversation_emails[email] = []
                conversation_emails[email].append(conv)
        
        # Create support metrics DataFrame
        support_metrics = []
        for email, convs in conversation_emails.items():
            support_metrics.append({
                'email': email,
                'conversations': convs,
                'total_tickets': len(convs)
            })
        
        support_df = pd.DataFrame(support_metrics)
        
        # Join
        joined = snowflake_df.merge(support_df, on='email', how='left')
        return joined
    
    def calculate_customer_support_metrics(self, joined_df):
        """Calculate per-customer support quality metrics"""
        # Implement support metric calculations
        # FCR rate, resolution time, escalation rate, etc.
        pass
    
    def compute_correlations(self, customer_metrics_df):
        """Compute point-biserial correlations"""
        from scipy import stats
        
        support_cols = ['fcr_rate_90d', 'avg_resolution_hours_90d', 'escalation_rate_90d']
        correlations = []
        
        for col in support_cols:
            valid_df = customer_metrics_df[[col, 'churned']].dropna()
            
            if len(valid_df) < 30:
                continue
            
            r, p_value = stats.pointbiserialr(valid_df['churned'], valid_df[col])
            
            correlations.append({
                'metric': col,
                'correlation': r,
                'p_value': p_value,
                'n': len(valid_df),
                'significant': p_value < 0.05,
                'effect_size': 'Small' if abs(r) < 0.3 else ('Medium' if abs(r) < 0.5 else 'Large')
            })
        
        return correlations
    
    def analyze_category_specific_risk(self, customer_metrics_df):
        """Analyze churn risk by support category"""
        # Chi-square test for categorical association
        pass
    
    def analyze_fcr_impact(self, customer_metrics_df):
        """Analyze First Contact Resolution impact on churn"""
        # Compare churn rates by FCR quartiles
        pass
    
    def propensity_score_matching(self, customer_metrics_df):
        """Estimate causal effect using PSM"""
        # Implement PSM for causal claims
        pass
    
    def assess_statistical_power(self, customer_metrics_df):
        """Assess if we have enough data for valid conclusions"""
        n = len(customer_metrics_df)
        churn_count = customer_metrics_df['churned'].sum()
        
        # Power analysis
        if n < 200:
            return "Low power - can only detect large effects (r > 0.5)"
        elif n < 500:
            return "Medium power - can detect medium effects (r > 0.3)"
        else:
            return "High power - can detect small-to-medium effects (r > 0.25)"
    
    def identify_limitations(self, customer_metrics_df):
        """Identify analysis limitations"""
        limitations = []
        
        n = len(customer_metrics_df)
        if n < 500:
            limitations.append(f"Sample size (N={n}) limits detection of weak correlations (r < 0.3)")
        
        missing_support = (customer_metrics_df['total_tickets_90d'] == 0).sum()
        if missing_support > n * 0.3:
            limitations.append(f"{missing_support}/{n} customers have no support tickets - limits correlation analysis")
        
        return limitations
```

---

## Part 3: Integration with Multi-Agent Workflow

### 3.1 Updated Orchestrator

```python
# In src/agents/orchestrator.py

class MultiAgentOrchestrator:
    def __init__(self, enable_churn_correlation=False):
        # Existing agents
        self.data_agent = DataAgent()
        self.category_agent = CategoryAgent()
        self.sentiment_agent = SentimentAgent()
        self.insight_agent = InsightAgent()
        self.presentation_agent = PresentationAgent()
        
        # NEW: Churn correlation agent (optional)
        self.churn_agent = ChurnCorrelationAgent() if enable_churn_correlation else None
    
    async def execute_analysis(self, ...):
        # Existing workflow
        ...
        
        # NEW: Phase 2.5 - Churn Correlation (if enabled)
        if self.churn_agent:
            self.logger.info("📊 Phase 2.5: Churn Correlation Analysis")
            
            churn_result = await self._execute_agent_with_checkpoint(
                self.churn_agent,
                context,
                workflow_state
            )
            
            if churn_result.success:
                context.previous_results['ChurnCorrelationAgent'] = churn_result.dict()
                workflow_state['agent_results']['ChurnCorrelationAgent'] = churn_result.dict()
                
                # Log key findings
                corrs = churn_result.data.get('correlations', [])
                significant = [c for c in corrs if c.get('significant')]
                self.logger.info(f"   ✅ ChurnCorrelationAgent: Found {len(significant)} significant correlations")
        
        # Continue with InsightAgent (now has churn data)
        ...
```

---

## Part 4: CLI Integration

### 4.1 New CLI Flag

```python
# In src/main.py

@cli.command()
@click.option('--month', type=int, required=True)
@click.option('--year', type=int, required=True)
@click.option('--generate-gamma', is_flag=True)
@click.option('--multi-agent', is_flag=True)
@click.option('--correlate-churn', is_flag=True, help='Include churn correlation analysis (requires Snowflake access)')
def voice(month, year, generate_gamma, multi_agent, correlate_churn):
    """Voice of Customer analysis with optional churn correlation"""
    
    if correlate_churn and not multi_agent:
        console.print("[yellow]⚠️  Churn correlation requires --multi-agent mode[/yellow]")
        correlate_churn = False
    
    if correlate_churn:
        console.print("[bold blue]📊 Churn Correlation Analysis Enabled[/bold blue]")
        console.print("   Requires: Snowflake connection and customer data access")
    
    # Pass to orchestrator
    asyncio.run(run_analysis(..., enable_churn_correlation=correlate_churn))
```

### 4.2 Web Interface Integration

```html
<!-- In deploy/railway_web.py -->
<div style="margin-bottom: 20px; padding: 12px; background: rgba(102, 126, 234, 0.1); border-radius: 8px;">
    <label style="display: flex; align-items: center; cursor: pointer; color: #e5e7eb;">
        <input type="checkbox" id="multiAgentMode" style="margin-right: 10px;">
        <span>🤖 Multi-Agent Mode</span>
    </label>
    
    <label style="display: flex; align-items: center; cursor: pointer; color: #e5e7eb; margin-top: 8px;">
        <input type="checkbox" id="churnCorrelation" style="margin-right: 10px;">
        <span>📊 Churn Correlation Analysis</span>
        <span style="margin-left: 10px; font-size: 12px; color: #9ca3af;">(Requires Snowflake access)</span>
    </label>
</div>
```

---

## Part 5: Statistical Analysis Pipeline

### 5.1 Correlation Analysis Module

```python
# src/services/correlation_analyzer.py

import pandas as pd
import numpy as np
from scipy import stats
from typing import Dict, List, Tuple

class CorrelationAnalyzer:
    """Statistical correlation analysis between support and outcomes"""
    
    def analyze_support_churn_correlation(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Comprehensive correlation analysis
        
        Args:
            df: DataFrame with columns:
                - churned (bool)
                - fcr_rate_90d (float)
                - avg_resolution_hours_90d (float)
                - escalation_rate_90d (float)
                - pct_billing_90d (float)
                - plan_tier (str)
                - tenure_months (int)
        
        Returns:
            Dict with correlation results, significance tests, and causal estimates
        """
        results = {
            'correlations': self._compute_correlations(df),
            'group_comparisons': self._compare_groups(df),
            'category_analysis': self._analyze_categories(df),
            'statistical_power': self._assess_power(df),
            'limitations': self._identify_limitations(df)
        }
        
        # Causal estimate if sufficient data
        if len(df) >= 200:
            results['causal_estimate'] = self._propensity_score_matching(df)
        
        return results
    
    def _compute_correlations(self, df) -> List[Dict]:
        """Point-biserial correlations"""
        support_metrics = ['fcr_rate_90d', 'avg_resolution_hours_90d', 
                          'escalation_rate_90d', 'pct_billing_90d']
        
        correlations = []
        for metric in support_metrics:
            valid_df = df[[metric, 'churned']].dropna()
            
            if len(valid_df) < 30:
                correlations.append({
                    'metric': metric,
                    'error': 'Insufficient data',
                    'n': len(valid_df)
                })
                continue
            
            r, p_value = stats.pointbiserialr(valid_df['churned'], valid_df[metric])
            
            # Confidence interval (Fisher z-transform)
            z = np.arctanh(r)
            se = 1 / np.sqrt(len(valid_df) - 3)
            ci_lower = np.tanh(z - 1.96 * se)
            ci_upper = np.tanh(z + 1.96 * se)
            
            correlations.append({
                'metric': metric,
                'correlation': r,
                'p_value': p_value,
                'ci_lower': ci_lower,
                'ci_upper': ci_upper,
                'n': len(valid_df),
                'significant': p_value < 0.05,
                'effect_size': self._interpret_effect_size(r)
            })
        
        return correlations
    
    def _compare_groups(self, df) -> Dict:
        """Compare churn rates by FCR quartiles"""
        # Top vs bottom quartile FCR
        q25 = df['fcr_rate_90d'].quantile(0.25)
        q75 = df['fcr_rate_90d'].quantile(0.75)
        
        low_fcr = df[df['fcr_rate_90d'] <= q25]
        high_fcr = df[df['fcr_rate_90d'] >= q75]
        
        low_churn_rate = low_fcr['churned'].mean()
        high_churn_rate = high_fcr['churned'].mean()
        
        # Two-proportion z-test
        from statsmodels.stats.proportion import proportions_ztest
        
        counts = np.array([low_fcr['churned'].sum(), high_fcr['churned'].sum()])
        nobs = np.array([len(low_fcr), len(high_fcr)])
        
        z_stat, p_value = proportions_ztest(counts, nobs)
        
        return {
            'low_fcr_churn_rate': low_churn_rate,
            'high_fcr_churn_rate': high_churn_rate,
            'absolute_difference': high_churn_rate - low_churn_rate,
            'relative_risk': high_churn_rate / low_churn_rate if low_churn_rate > 0 else None,
            'p_value': p_value,
            'n_low': len(low_fcr),
            'n_high': len(high_fcr)
        }
    
    def _interpret_effect_size(self, r) -> str:
        """Interpret correlation coefficient"""
        abs_r = abs(r)
        if abs_r < 0.1:
            return "Negligible"
        elif abs_r < 0.3:
            return "Small"
        elif abs_r < 0.5:
            return "Medium"
        else:
            return "Large"
```

---

## Part 6: Implementation Roadmap

### Phase 1: Foundation (Week 1-2)

**Deliverables:**

1. ✅ Create `ChurnCorrelationAgent` class
2. ✅ Implement Snowflake connector/MCP integration
3. ✅ Build email-based join logic
4. ✅ Implement basic correlation analysis
5. ✅ Test with sample data

**Success Criteria:**

- Can successfully query Snowflake
- Email join works (>80% match rate)
- Correlation calculations run without errors

### Phase 2: Statistical Analysis (Week 3-4)

**Deliverables:**

1. ✅ Implement all correlation tests (point-biserial, Spearman)
2. ✅ Add confidence interval calculations
3. ✅ Implement group comparisons (FCR quartiles)
4. ✅ Add category-specific risk analysis
5. ✅ Build statistical power assessment

**Success Criteria:**

- All p-values calculated correctly
- Confidence intervals validate with manual checks
- Power analysis matches statsmodels results

### Phase 3: Causal Inference (Week 5-6)

**Deliverables:**

1. ✅ Implement Propensity Score Matching
2. ✅ Add balance checking
3. ✅ Calculate ATT (Average Treatment Effect on Treated)
4. ✅ Sensitivity analysis for unmeasured confounders

**Success Criteria:**

- PSM matches validate (standardized differences < 0.1)
- ATT confidence intervals don't include zero (if effect exists)
- Sensitivity analysis shows robustness

### Phase 4: Integration & UI (Week 7-8)

**Deliverables:**

1. ✅ Add `--correlate-churn` flag to CLI
2. ✅ Integrate ChurnCorrelationAgent into orchestrator
3. ✅ Add churn correlation checkbox to web UI
4. ✅ Create visualization dashboard
5. ✅ Write documentation

**Success Criteria:**

- End-to-end workflow works
- Results display in Gamma presentations
- Non-technical users can interpret findings

---

## Part 7: Output Format

### 7.1 Statistical Report Structure

```json
{
  "churn_correlation_analysis": {
    "sample_size": 1247,
    "churn_rate": 0.152,
    "statistical_power": "High - can detect medium effects (r ≥ 0.3)",
    
    "correlations": [
      {
        "metric": "fcr_rate_90d",
        "correlation": -0.38,
        "p_value": 0.0003,
        "ci_lower": -0.52,
        "ci_upper": -0.21,
        "interpretation": "Higher FCR significantly reduces churn (medium effect)",
        "significant": true,
        "effect_size": "Medium"
      },
      {
        "metric": "avg_resolution_hours_90d",
        "correlation": 0.29,
        "p_value": 0.012,
        "ci_lower": 0.08,
        "ci_upper": 0.47,
        "interpretation": "Longer resolution time moderately increases churn",
        "significant": true,
        "effect_size": "Small-to-Medium"
      }
    ],
    
    "fcr_impact": {
      "top_quartile_fcr_churn": 0.097,
      "bottom_quartile_fcr_churn": 0.223,
      "absolute_difference": 0.126,
      "relative_risk": 2.30,
      "p_value": 0.002,
      "interpretation": "Customers in bottom FCR quartile churn at 2.3x the rate of top quartile"
    },
    
    "category_risks": [
      {
        "category": "Billing",
        "churn_rate_with_category": 0.284,
        "churn_rate_without_category": 0.118,
        "relative_risk": 2.41,
        "p_value": 0.001,
        "interpretation": "Billing tickets associated with 2.4x elevated churn risk"
      }
    ],
    
    "causal_estimate": {
      "method": "Propensity Score Matching",
      "treatment": "High-quality support (FCR > 80%, Resolution < 24h)",
      "att": -0.052,
      "ci_lower": -0.083,
        "ci_upper": -0.021,
      "p_value": 0.002,
      "interpretation": "High-quality support reduces churn by 5.2 percentage points (95% CI: [2.1, 8.3], p=0.002)",
      "balance_check": "Passed - all confounders balanced (std diff < 0.1)"
    },
    
    "limitations": [
      "Correlation does not prove causation - propensity score matching provides causal estimate but has limitations",
      "Sample size (N=1,247) adequate for medium effects but may miss weak associations (r < 0.25)",
      "Cannot account for unmeasured confounders (competitor actions, customer internal changes)",
      "Time window limited to 90 days before churn - longer-term effects not captured"
    ],
    
    "recommendations": [
      "Focus on improving FCR rate - strongest predictor of churn reduction",
      "Billing category tickets require immediate attention - 2.4x elevated churn risk",
      "Monitor customers with FCR < 50% - they churn at 2.3x baseline rate",
      "Implement early intervention for customers with resolution time > 24 hours"
    ]
  }
}
```

### 7.2 Gamma Presentation Integration

The PresentationAgent will include a new slide:

#### "Support Quality Impact on Business Outcomes"

```markdown
# The Support-Churn Connection: What the Data Reveals

Our statistical analysis of 1,247 customers reveals a clear relationship between 
support quality and customer retention.

**First Contact Resolution Matters**

Customers in the top FCR quartile (>80% resolution on first contact) churn at just 
9.7%, while those in the bottom quartile (<45% FCR) churn at 22.3%.

That's a 2.3x difference in churn risk.

**What This Means**

Improving FCR from 45% to 80% (a 35 percentage point improvement) could reduce 
churn by 12.6 percentage points. For every 100 low-FCR customers we improve, we 
could retain 13 additional customers.

**Statistical Confidence**

This finding is statistically significant (p = 0.002) with 95% confidence that the 
true effect is between 2.1 and 8.3 percentage points.

**Important Caveats**

- Correlation doesn't prove causation - we controlled for plan tier, tenure, and 
  usage, but unmeasured factors may contribute
- Analysis limited to 90 days before churn - longer-term effects not captured
- Results specific to our customer base - may not generalize to all SaaS companies

**Bottom Line**

The data supports investing in support quality improvements, particularly FCR rate, 
as a churn reduction strategy. Every percentage point of FCR improvement correlates 
with measurable retention gains.

*Analysis based on 1,247 customers, 6 months of data, p < 0.05 significance threshold*
```

---

## Part 8: Deployment Strategy

### 8.1 Feature Branch: `feature/churn-correlation`

```bash
# Create separate feature branch
git checkout -b feature/churn-correlation

# Implement ChurnCorrelationAgent
# Add Snowflake connector
# Update orchestrator

# Test locally
python -m src.main voice --month 10 --year 2024 --multi-agent --correlate-churn

# Deploy to separate Railway service for testing
railway up --service churn-correlation-test
```

### 8.2 Configuration

```yaml
# config/churn_correlation.yaml
churn_correlation:
  enabled: false  # Feature flag
  
  snowflake:
    account: "your-account.snowflakecomputing.com"
    warehouse: "ANALYTICS_WH"
    database: "CUSTOMER_DATA"
    schema: "PUBLIC"
    
  analysis:
    lookback_days: 90  # Days before churn to examine support
    min_sample_size: 200  # Minimum customers for correlation
    significance_threshold: 0.05  # P-value threshold
    min_correlation: 0.25  # Minimum correlation to report
    
  categories_to_analyze:
    - "Billing"
    - "Bug"
    - "Account"
    - "API"
    - "Product"
```

---

## Part 9: Limitations & Honest Reporting

### 9.1 What We CAN Prove (With Rigorous Methods)

✅ **Correlation**: "FCR rate is negatively correlated with churn (r = -0.38, p < 0.001, N=1,247)"

✅ **Group Differences**: "Customers in top FCR quartile churn at 9.7% vs 22.3% for bottom quartile (p = 0.002)"

✅ **Predictive Value**: "Support metrics improve churn prediction accuracy from AUROC 0.75 to 0.87"

✅ **Causal Estimate (with PSM)**: "High-quality support reduces churn by 5.2 percentage points (95% CI: [2.1, 8.3], p=0.002) after controlling for plan, tenure, and usage"

### 9.2 What We CANNOT Prove

❌ **Pure Causation**: "We cannot completely rule out reverse causality or unmeasured confounders without randomized experiment"

❌ **Small Effects**: "Sample size limits detection of weak correlations (r < 0.25)"

❌ **Generalization**: "Findings specific to our customer base and may not apply to all SaaS companies"

❌ **Long-term Impact**: "Analysis captures 90-day window; longer-term effects unknown"

### 9.3 Required Disclaimers

Every churn correlation report must include:

```text
STATISTICAL DISCLAIMERS:

- Correlation does not prove causation: While we control for observable confounders 
  (plan tier, tenure, usage), unmeasured factors may contribute to observed relationships.

- Sample size: N=[actual] customers. We have 80% power to detect correlations r ≥ 0.X.
  Weaker associations may exist but cannot be reliably detected.

- Time window: Analysis examines [X] days before churn. Effects outside this window 
  are not captured.

- Significance threshold: p < 0.05. We performed [N] statistical tests; consider 
  Bonferroni correction (p < 0.05/N) for family-wise error rate.

- Alternative explanations: [List plausible alternatives, e.g., "Customers planning 
  to churn may create more support tickets as they extract final value"]
```

---

## Part 10: Success Metrics

### 10.1 Technical Success

- ✅ Email join success rate > 80%
- ✅ Query performance < 30 seconds
- ✅ Statistical tests run without errors
- ✅ Confidence intervals validate with manual checks

### 10.2 Statistical Success

- ✅ Find at least 2-3 significant correlations (p < 0.05)
- ✅ Effect sizes in expected range (r = 0.25-0.50)
- ✅ Statistical power assessment matches expectations
- ✅ Balance checks pass for PSM (if applicable)

### 10.3 Business Success

- ✅ Findings are actionable (lead to specific support improvements)
- ✅ Quantified ROI (e.g., "10% FCR improvement → 2% churn reduction → $X revenue saved")
- ✅ Executive team understands and trusts the analysis
- ✅ Findings inform resource allocation decisions

---

## Next Steps

1. **Share Snowflake schema** - Understand available tables and columns
2. **Run sample queries** - Validate data availability and quality
3. **Review Perplexity research** - Validate statistical approach
4. **Implement ChurnCorrelationAgent** - Build the analysis pipeline
5. **Test with historical data** - Validate findings
6. **Deploy as feature flag** - Safe rollout
7. **Iterate based on findings** - Refine as we learn

---

**This feature will answer definitively**: "Does improving support quality reduce churn?"

With rigorous statistics, honest limitations, and actionable insights.
