# CSAT Integration & Trend Analysis Implementation Plan

Based on Horatio's CSAT report format and user requirements.

## 📊 **Three Key Enhancements**

### 1. ✅ CSAT Integration (HIGH PRIORITY)
### 2. ⚠️ Controllable vs Uncontrollable Classification (NEEDS DEFINITION)
### 3. ✅ Week-over-Week Trend Comparison (HIGH PRIORITY)

---

## 1. CSAT Integration

### Current State
- ✅ We **already extract** `conversation_rating` from Intercom
- ✅ We calculate overall CSAT in `metrics_calculator.py`
- ❌ We **don't use CSAT** in agent performance analysis

### What We Need
Add CSAT metrics to individual agent analysis, matching Horatio's format:

**Per Agent:**
- Total surveys (conversations with ratings)
- Average CSAT score (1-5 scale)
- CSAT score breakdown by rating (1★, 2★, 3★, 4★, 5★)
- Negative CSAT count (ratings ≤ 2)
- Top/Bottom performers by CSAT

### Implementation

#### **File: `src/services/individual_agent_analyzer.py`**

**Lines 126-150: Add CSAT collection to `_calculate_individual_metrics()`**

```python
async def _calculate_individual_metrics(...) -> IndividualAgentMetrics:
    # ... existing FCR, escalation, resolution time calcs...
    
    # CSAT METRICS (NEW)
    rated_convs = [c for c in convs if c.get('conversation_rating') is not None]
    ratings = [c.get('conversation_rating') for c in rated_convs]
    
    csat_score = np.mean(ratings) if ratings else 0.0
    csat_survey_count = len(rated_convs)
    negative_csat_count = len([r for r in ratings if r <= 2])  # 1★ or 2★
    
    # Rating breakdown
    rating_distribution = {
        '5_star': len([r for r in ratings if r == 5]),
        '4_star': len([r for r in ratings if r == 4]),
        '3_star': len([r for r in ratings if r == 3]),
        '2_star': len([r for r in ratings if r == 2]),
        '1_star': len([r for r in ratings if r == 1])
    }
```

#### **File: `src/models/agent_performance_models.py`**

**Add CSAT fields to `IndividualAgentMetrics`:**

```python
class IndividualAgentMetrics(BaseModel):
    # ... existing fields ...
    
    # CSAT Metrics (NEW)
    csat_score: float = 0.0  # Average rating (1-5)
    csat_survey_count: int = 0  # Number of rated conversations
    negative_csat_count: int = 0  # Ratings ≤ 2
    rating_distribution: Dict[str, int] = {}  # Breakdown by star rating
```

#### **File: `src/agents/agent_performance_agent.py`**

**Update prompts to include CSAT analysis:**

```python
def get_agent_specific_instructions(self) -> str:
    return f"""
1. Analyze performance objectively with data-driven insights:
   - First Contact Resolution rate
   - CSAT Score (customer satisfaction ratings)  # NEW
   - Resolution time (median, P90)
   - Escalation patterns
   - Category-specific performance

2. Identify CSAT drivers:  # NEW
   - Which agents have high vs low CSAT?
   - Are low CSAT scores tied to specific categories?
   - Correlation between FCR and CSAT?
"""
```

#### **File: `src/services/presentation_builder.py`**

**Add CSAT tables to Gamma presentation:**

```python
def _build_agent_performance_section(self, agent_metrics) -> str:
    # Top performers by CSAT
    top_by_csat = sorted(agent_metrics, key=lambda a: a.csat_score, reverse=True)[:5]
    
    section = f"""
## Top Performers by CSAT

| Agent | Surveys | CSAT Score | FCR Rate |
|-------|---------|------------|----------|
{self._format_agent_csat_table(top_by_csat)}

## Bottom Performers by CSAT

| Agent | Surveys | CSAT Score | Negative Count |
|-------|---------|------------|----------------|
{self._format_agent_csat_table(bottom_by_csat)}
"""
```

---

## 2. Controllable vs Uncontrollable Classification

### The Challenge
**How do we define "controllable"?**

Horatio's definition from their report:
- **Controllable**: Agent could have done something differently (tone, accuracy, speed)
- **Uncontrollable**: Product issue, policy limitation, legitimate complaint

### Proposed Framework

#### **Controllable Factors (Agent Responsibility):**
1. **Response Quality**
   - Inaccurate information given
   - Didn't follow procedure/macro
   - Incomplete answer (customer had to ask follow-up)
   
2. **Tone/Professionalism**
   - Rude or dismissive language
   - Lack of empathy
   - Copy-paste responses without personalization

3. **Speed/Efficiency**
   - Slow response time (when agent was online)
   - Long back-and-forth that could have been resolved faster
   - Unnecessary escalation (should have handled themselves)

4. **Resolution Quality**
   - Didn't solve the actual problem
   - Customer had to reopen (count_reopens > 0)
   - Escalated when shouldn't have

#### **Uncontrollable Factors (Product/Policy):**
1. **Product Bugs**
   - Actual bug in Gamma (export failing, editor glitches)
   - Missing features customer needs
   - System downtime

2. **Policy Limitations**
   - Customer wants refund outside policy
   - Feature not available on their plan
   - Legitimate billing issue (actually charged wrong)

3. **Legitimate Customer Issues**
   - Account actually compromised
   - Real abuse/spam problem
   - Actual data loss/corruption

### Implementation Approach

#### **Option A: AI Classification (Recommended)**

Use AI to classify each low-CSAT or escalated conversation:

```python
async def classify_controllability(self, conversation: Dict) -> Dict[str, Any]:
    """
    Classify whether a negative outcome was controllable by the agent.
    
    Returns:
        {
            'controllable': bool,
            'reason': str,
            'category': 'response_quality' | 'tone' | 'speed' | 'product_bug' | 'policy_limitation' | 'legitimate_issue'
        }
    """
    prompt = f"""
Analyze this customer support conversation and determine if the negative outcome 
was controllable by the agent or uncontrollable (product/policy issue).

CONTROLLABLE (agent responsibility):
- Inaccurate information
- Poor tone/unprofessional
- Slow response when avoidable
- Unnecessary escalation
- Incomplete resolution

UNCONTROLLABLE (product/policy):
- Actual product bug
- Feature doesn't exist
- Policy limitation (valid denial)
- System outage
- Legitimate billing issue

Conversation:
{conversation['full_text']}

Customer reopened: {conversation.get('count_reopens', 0) > 0}
CSAT Rating: {conversation.get('conversation_rating', 'N/A')}
Escalated: {self._was_escalated(conversation)}

Return JSON: {{"controllable": true/false, "reason": "...", "category": "..."}}
"""
```

#### **Option B: Rule-Based Heuristics**

Simpler approach using patterns:

```python
def classify_controllability_heuristic(self, conv: Dict) -> bool:
    """Heuristic-based controllability classification"""
    
    # Likely UNCONTROLLABLE if:
    if any(pattern in conv['full_text'].lower() for pattern in [
        'bug', 'error', 'broken', 'doesn\'t work', 'not working',
        'feature request', 'can\'t export', 'glitch', 'issue with the product'
    ]):
        return False  # Uncontrollable (product issue)
    
    # Likely CONTROLLABLE if:
    if conv.get('count_reopens', 0) > 0:
        return True  # Reopened = agent didn't fully resolve
    
    if self._was_escalated(conv):
        # Check if escalation was necessary
        if any(term in conv['full_text'].lower() for term in [
            'billing', 'refund', 'subscription', 'api', 'enterprise'
        ]):
            return False  # Valid escalation
        return True  # Unnecessary escalation
    
    # Default: assume uncontrollable (be generous)
    return False
```

### My Recommendation

**Start with Option B (rule-based) for MVP**, then enhance with Option A (AI) once we validate the rules work.

Why?
- Faster to implement
- Cheaper (no extra AI calls)
- Easier to tune/debug
- Can gather data to train better AI classification later

---

## 3. Week-over-Week Trend Analysis

### Current State
- ❌ We don't store historical data
- ❌ We don't compare time periods
- ❌ We don't show trends

### What We Need

**Per Agent, show trend data:**
- Current week CSAT vs previous week
- Current week FCR vs previous week  
- Current week escalation rate vs previous week
- Visual indicators (↑ improving, ↓ declining, → stable)

### Implementation

#### **File: `src/services/historical_performance_manager.py` (NEW)**

```python
class HistoricalPerformanceManager:
    """Manage historical agent performance data for trend analysis"""
    
    def __init__(self, storage: DuckDBStorage):
        self.storage = storage
    
    async def store_weekly_snapshot(
        self, 
        vendor: str,
        week_start: datetime,
        agent_metrics: List[IndividualAgentMetrics]
    ):
        """Store a weekly snapshot of agent performance"""
        
        for agent in agent_metrics:
            await self.storage.insert_agent_weekly_snapshot({
                'vendor': vendor,
                'agent_id': agent.agent_id,
                'agent_name': agent.agent_name,
                'week_start': week_start,
                'fcr_rate': agent.fcr_rate,
                'escalation_rate': agent.escalation_rate,
                'csat_score': agent.csat_score,
                'csat_survey_count': agent.csat_survey_count,
                'conversations_handled': agent.conversations_handled
            })
    
    async def get_week_over_week_comparison(
        self, 
        vendor: str,
        current_week_start: datetime
    ) -> Dict[str, Dict[str, float]]:
        """
        Get week-over-week changes for all agents.
        
        Returns:
            {
                'agent_id': {
                    'fcr_change': +0.05,  # 5% improvement
                    'csat_change': -0.2,  # 0.2 point decline
                    'escalation_change': +0.03  # 3% increase (bad)
                }
            }
        """
        # Query last week's data
        previous_week = current_week_start - timedelta(weeks=1)
        previous_data = await self.storage.get_agent_weekly_snapshot(vendor, previous_week)
        current_data = await self.storage.get_agent_weekly_snapshot(vendor, current_week_start)
        
        # Calculate deltas
        comparisons = {}
        for agent_id in current_data:
            if agent_id in previous_data:
                comparisons[agent_id] = {
                    'fcr_change': current_data[agent_id]['fcr_rate'] - previous_data[agent_id]['fcr_rate'],
                    'csat_change': current_data[agent_id]['csat_score'] - previous_data[agent_id]['csat_score'],
                    'escalation_change': current_data[agent_id]['escalation_rate'] - previous_data[agent_id]['escalation_rate']
                }
        
        return comparisons
```

#### **DuckDB Schema Addition**

```sql
CREATE TABLE IF NOT EXISTS agent_weekly_snapshots (
    vendor TEXT,
    agent_id TEXT,
    agent_name TEXT,
    week_start DATE,
    fcr_rate REAL,
    escalation_rate REAL,
    csat_score REAL,
    csat_survey_count INTEGER,
    conversations_handled INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (vendor, agent_id, week_start)
);
```

#### **Display in Gamma**

```markdown
## Agent Performance Trends (Week-over-Week)

| Agent | CSAT (Current) | CSAT (Change) | FCR (Current) | FCR (Change) | Escalation (Change) |
|-------|----------------|---------------|---------------|--------------|---------------------|
| Juan | 4.83 | ↑ +0.3 | 85% | ↑ +5% | ↓ -2% |
| Lorna | 3.07 | ↓ -0.5 | 65% | ↓ -10% | ↑ +8% |
```

---

## Implementation Priority

### Phase 1: CSAT Integration (Immediate)
1. Add CSAT fields to `IndividualAgentMetrics` model
2. Calculate CSAT in `individual_agent_analyzer.py`
3. Display CSAT in agent performance reports
4. Add CSAT to Gamma presentation

**Estimated effort**: 4-6 hours

### Phase 2: Trend Analysis (High Priority)
1. Create `historical_performance_manager.py`
2. Add DuckDB schema for weekly snapshots
3. Store snapshots after each analysis
4. Calculate week-over-week deltas
5. Display trends in reports

**Estimated effort**: 6-8 hours

### Phase 3: Controllable Classification (Nice-to-Have)
1. Define classification rules (rule-based MVP)
2. Add classification to negative CSAT/escalations
3. Display controllable vs uncontrollable breakdown
4. (Future) Enhance with AI classification

**Estimated effort**: 8-10 hours (rule-based), 16-20 hours (AI-enhanced)

---

## Questions for User (Answered)

1. **CSAT Integration**: ✅ YES - Definitely want this
2. **Controllable Classification**: ⚠️ TRICKY - Need to define criteria (proposed framework above)
3. **Week-over-Week Trends**: ✅ YES - Definitely want this
4. **Visual Style**: ❌ NO - Don't need to match Horatio's exact visual style

---

## Next Steps

**Immediate (Today):**
1. Add CSAT fields to models
2. Calculate CSAT per agent
3. Display in reports

**This Week:**
1. Implement historical snapshot storage
2. Add week-over-week comparison logic
3. Display trends in Gamma

**Future:**
1. Define and implement controllable classification rules
2. Add AI-based classification (if rule-based proves insufficient)
3. Add more trend visualizations (6-week trends like Horatio)


