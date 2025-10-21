# Operational Metrics from Intercom Data: What We Have vs What We Need

**Context**: The multi-agent system is producing emotional/sentiment analysis instead of operational insights because we're not extracting and analyzing the operational metrics that Intercom provides.

---

## Part 1: What Intercom Gives Us (Raw Data)

### Fields We're Already Extracting:

```python
# From src/services/duckdb_storage.py line 284-306
{
    'id': conv.get('id'),
    'created_at': timestamp,
    'updated_at': timestamp,
    'state': 'open' | 'closed' | 'snoozed',
    'priority': 'priority' | 'not_priority',
    'admin_assignee_id': '12345',  # The admin who handled it
    'conversation_rating': {...},  # CSAT data
    
    # OPERATIONAL METRICS (the goldmine!)
    'time_to_admin_reply': 3600,  # Seconds to first response
    'handling_time': 7200,  # Seconds admin spent working
    'count_conversation_parts': 8,  # Number of messages
    'count_reopens': 2,  # How many times customer reopened
    
    # AI/Agent flags
    'ai_agent_participated': true/false,
    'fin_ai_preview': true/false,
    'copilot_used': true/false,
    
    # Text content
    'full_text': "...",
    'customer_messages': ["...", "..."],
    'admin_messages': ["...", "..."]
}
```

---

## Part 2: Operational Metrics We CAN Calculate

### 2.1 First Contact Resolution (FCR)

**Definition**: Conversation resolved without customer reopening

**Calculation**:
```python
def calculate_fcr(conversation):
    """
    FCR = true if count_reopens == 0 AND state == 'closed'
    """
    return conversation.get('count_reopens', 0) == 0 and conversation.get('state') == 'closed'

# Aggregate FCR rate
fcr_rate = conversations_df['fcr'].mean()
```

**What This Tells Us**:
- FCR < 50% = Poor (lots of back-and-forth)
- FCR 60-70% = Average
- FCR > 80% = Excellent

### 2.2 Resolution Time

**Definition**: Time from conversation creation to closure

**Calculation**:
```python
def calculate_resolution_time(conversation):
    """
    Resolution time = updated_at - created_at (for closed conversations)
    """
    if conversation.get('state') != 'closed':
        return None
    
    created = conversation.get('created_at')
    updated = conversation.get('updated_at')
    
    if created and updated:
        return (updated - created).total_seconds() / 3600  # Hours
    return None

# Aggregate
median_resolution_time = conversations_df['resolution_hours'].median()
p90_resolution_time = conversations_df['resolution_hours'].quantile(0.9)
```

**What This Tells Us**:
- Median < 4 hours = Fast
- Median 4-24 hours = Average
- Median > 24 hours = Slow
- P90 > 48 hours = Long tail of problem tickets

### 2.3 Escalation Detection

**Definition**: Conversation assigned to senior staff

**YOUR ESCALATION RULES**:
```python
ESCALATION_ADMINS = {
    # Admin IDs (need to look these up in Intercom)
    'dae_ho_id': 'Dae-Ho Chung',
    'max_jackson_id': 'Max Jackson',
    'hilary_id': 'Hilary Dudek'
}

TIER_1_AGENTS = {
    # Horatio agents (extract from email domain patterns)
    'pattern': r'@horatio\.com',
    'name': 'Horatio Support'
}

TIER_2_AGENTS = {
    # Boldr agents (will appear in future)
    'pattern': r'@boldr',
    'name': 'Boldr Support'
}

def is_escalated(conversation):
    """
    Escalated if:
    1. admin_assignee_id in ESCALATION_ADMINS, OR
    2. Text mentions Dae-Ho, Max Jackson, or Hilary, OR
    3. priority == 'priority'
    """
    assignee_id = conversation.get('admin_assignee_id')
    if assignee_id in ESCALATION_ADMINS:
        return True, ESCALATION_ADMINS[assignee_id]
    
    # Check text mentions
    text = conversation.get('full_text', '').lower()
    for name in ['dae-ho', 'max jackson', 'hilary']:
        if name in text:
            return True, name.title()
    
    # Check priority flag
    if conversation.get('priority') == 'priority':
        return True, 'Priority Escalation'
    
    return False, None

# Aggregate
escalation_rate = sum(is_escalated(c)[0] for c in conversations) / len(conversations)
```

**What This Tells Us**:
- Escalation rate < 10% = Good
- Escalation rate 10-20% = Average
- Escalation rate > 20% = High (agents struggling)

### 2.4 Response Time Efficiency

**Already Available**: `time_to_admin_reply`

**Calculation**:
```python
# Convert seconds to hours
def get_first_response_time(conversation):
    time_to_reply = conversation.get('time_to_admin_reply')
    if time_to_reply:
        return time_to_reply / 3600  # Hours
    return None

# Aggregate
median_response_time = conversations_df['response_hours'].median()
pct_under_1_hour = (conversations_df['response_hours'] < 1).mean() * 100
```

**What This Tells Us**:
- Median < 1 hour = Excellent
- Median 1-4 hours = Good
- Median > 4 hours = Needs improvement

### 2.5 Agent Efficiency (Handling Time)

**Already Available**: `handling_time`

**What This Tells Us**:
- How long agents spend per ticket
- Compare by category (billing takes longer than simple questions)
- Identify complex issue types

### 2.6 Conversation Complexity

**Already Available**: `count_conversation_parts`

**Calculation**:
```python
def categorize_complexity(conversation):
    parts = conversation.get('count_conversation_parts', 0)
    if parts <= 2:
        return 'Simple'
    elif parts <= 5:
        return 'Moderate'
    else:
        return 'Complex'

# Aggregate by category
complexity_by_category = conversations_df.groupby(['category', 'complexity']).size()
```

**What This Tells Us**:
- Simple tickets (2 messages) should have high FCR
- Complex tickets (>5 messages) are expected to be harder

---

## Part 3: Updated DataAgent - Calculate Operational Metrics

```python
# In src/agents/data_agent.py

def _calculate_operational_metrics(self, conversations: List[Dict]) -> Dict[str, Any]:
    """Calculate operational efficiency metrics from conversations"""
    
    if not conversations:
        return {}
    
    # FCR (First Contact Resolution)
    fcr_conversations = [c for c in conversations if c.get('count_reopens', 0) == 0 and c.get('state') == 'closed']
    closed_conversations = [c for c in conversations if c.get('state') == 'closed']
    fcr_rate = len(fcr_conversations) / len(closed_conversations) if closed_conversations else 0
    
    # Resolution time (for closed conversations)
    resolution_times = []
    for conv in closed_conversations:
        created = conv.get('created_at')
        updated = conv.get('updated_at')
        if created and updated:
            hours = (updated - created).total_seconds() / 3600
            resolution_times.append(hours)
    
    # Escalations
    ESCALATION_ADMINS = ['Dae-Ho Chung', 'Max Jackson', 'Hilary Dudek']
    escalated_count = 0
    
    for conv in conversations:
        # Check admin assignee
        assignee = conv.get('admin_assignee_id', '')
        if any(name.lower() in str(assignee).lower() for name in ESCALATION_ADMINS):
            escalated_count += 1
            continue
        
        # Check text mentions
        text = conv.get('full_text', '').lower()
        if any(name.lower() in text for name in ESCALATION_ADMINS):
            escalated_count += 1
            continue
        
        # Check priority flag
        if conv.get('priority') == 'priority':
            escalated_count += 1
    
    escalation_rate = escalated_count / len(conversations) if conversations else 0
    
    # Response time
    response_times = [
        conv.get('time_to_admin_reply', 0) / 3600  # Convert to hours
        for conv in conversations
        if conv.get('time_to_admin_reply')
    ]
    
    # Handling time
    handling_times = [
        conv.get('handling_time', 0) / 3600  # Convert to hours
        for conv in conversations
        if conv.get('handling_time')
    ]
    
    # Agent detection (Horatio, Boldr, Internal)
    agent_distribution = self._detect_agent_types(conversations)
    
    return {
        'fcr_rate': round(fcr_rate, 3),
        'fcr_count': len(fcr_conversations),
        'total_closed': len(closed_conversations),
        
        'resolution_time': {
            'median_hours': round(np.median(resolution_times), 2) if resolution_times else None,
            'mean_hours': round(np.mean(resolution_times), 2) if resolution_times else None,
            'p90_hours': round(np.percentile(resolution_times, 90), 2) if resolution_times else None
        },
        
        'escalation_rate': round(escalation_rate, 3),
        'escalated_count': escalated_count,
        
        'response_time': {
            'median_hours': round(np.median(response_times), 2) if response_times else None,
            'pct_under_1_hour': round(sum(1 for t in response_times if t < 1) / len(response_times) * 100, 1) if response_times else None
        },
        
        'handling_time': {
            'median_hours': round(np.median(handling_times), 2) if handling_times else None
        },
        
        'agent_distribution': agent_distribution,
        
        'conversation_complexity': {
            'simple': sum(1 for c in conversations if c.get('count_conversation_parts', 0) <= 2),
            'moderate': sum(1 for c in conversations if 2 < c.get('count_conversation_parts', 0) <= 5),
            'complex': sum(1 for c in conversations if c.get('count_conversation_parts', 0) > 5)
        }
    }

def _detect_agent_types(self, conversations: List[Dict]) -> Dict[str, int]:
    """Detect which agent type handled each conversation"""
    import re
    
    agent_counts = {
        'escalated': 0,  # Dae-Ho, Max, Hilary
        'horatio': 0,
        'boldr': 0,
        'ai_agent': 0,
        'unknown': 0
    }
    
    for conv in conversations:
        text = conv.get('full_text', '').lower()
        assignee = str(conv.get('admin_assignee_id', '')).lower()
        
        # Escalated to senior staff
        if any(name in text or name in assignee for name in ['dae-ho', 'max jackson', 'hilary']):
            agent_counts['escalated'] += 1
        # Horatio
        elif re.search(r'horatio|@horatio\.com', text) or 'horatio' in assignee:
            agent_counts['horatio'] += 1
        # Boldr (future)
        elif re.search(r'boldr|@boldr', text) or 'boldr' in assignee:
            agent_counts['boldr'] += 1
        # AI Agent
        elif conv.get('ai_agent_participated'):
            agent_counts['ai_agent'] += 1
        else:
            agent_counts['unknown'] += 1
    
    return agent_counts
```

---

## Part 4: What Operational Metrics SHOULD Be in the Report

### Instead of:
```
"87% negative sentiment" 
"Billing dominates conversations"
"Customers are frustrated"
```

### Should be:
```
**Resolution Efficiency Analysis**

First Contact Resolution: 58% (target: >70%)
- Billing: 45% FCR (problem area - 11% below target)
- Product Questions: 72% FCR (meeting target)
- Bug Reports: 41% FCR (problem area - requires iteration)

Resolution Time Performance:
- Median: 8.2 hours (target: <4 hours)
- 90th percentile: 36 hours (target: <24 hours)
- Billing tickets: 12.4 hour median (50% slower than average)

Escalation Patterns:
- Overall rate: 18% (target: <15%)
- Top escalation categories:
  - Billing: 28% escalation rate
  - API Issues: 22% escalation rate
  - Bug Reports: 31% escalation rate

Agent Efficiency:
- Horatio agents: 67% FCR, 6.2 hour median resolution
- Escalated to senior staff: 42% FCR, 18.3 hour median resolution
  (Indicates complex issues requiring expertise)

Month-over-Month Trends:
- FCR: 58% (no baseline - first analysis)
- Escalation rate: 18% (no baseline)
- Resolution time: 8.2 hours (no baseline)
  
**Actionable Insights**: Focus on improving Billing FCR from 45% to 60% (15 point improvement). This category represents 52% of volume and has lowest FCR. Estimated impact: 8% reduction in total ticket volume through better first-contact resolution.
```

---

## Part 5: How to Fix the Agents

### Step 1: Update DataAgent

**Add operational metrics extraction** (code above) to DataAgent.execute()

**Output**:
```json
{
  "conversations": [...],
  "operational_metrics": {
    "fcr_rate": 0.58,
    "median_resolution_hours": 8.2,
    "escalation_rate": 0.18,
    "agent_distribution": {...}
  }
}
```

### Step 2: Update CategoryAgent

**Add category-specific operational metrics**:

```python
def _calculate_category_metrics(self, conversations_by_category):
    """Calculate FCR, resolution time, escalation rate PER CATEGORY"""
    
    category_metrics = {}
    
    for category, convs in conversations_by_category.items():
        fcr = sum(1 for c in convs if is_fcr(c)) / len(convs)
        
        resolution_times = [calc_resolution_time(c) for c in convs if calc_resolution_time(c)]
        median_res = np.median(resolution_times) if resolution_times else None
        
        escalated = sum(1 for c in convs if is_escalated(c))
        esc_rate = escalated / len(convs)
        
        category_metrics[category] = {
            'volume': len(convs),
            'fcr_rate': fcr,
            'median_resolution_hours': median_res,
            'escalation_rate': esc_rate,
            'avg_conversation_parts': np.mean([c.get('count_conversation_parts', 0) for c in convs])
        }
    
    return category_metrics
```

**Output**:
```json
{
  "Billing": {
    "volume": 1166,
    "fcr_rate": 0.45,
    "median_resolution_hours": 12.4,
    "escalation_rate": 0.28,
    "avg_conversation_parts": 6.8
  },
  "Bug": {
    "volume": 357,
    "fcr_rate": 0.41,
    "median_resolution_hours": 18.2,
    "escalation_rate": 0.31,
    "avg_conversation_parts": 8.2
  }
}
```

### Step 3: Update InsightAgent Prompt

**REMOVE**:
```
Analyze sentiment and emotional patterns
Identify customer frustration
Focus on customer voice
```

**REPLACE WITH**:
```
FOCUS ON OPERATIONAL EFFICIENCY:

Analyze the operational metrics provided:
1. First Contact Resolution (FCR) rate overall and by category
2. Resolution time distribution and outliers
3. Escalation patterns and triggers
4. Agent efficiency differences
5. Complexity indicators (conversation parts, reopens)

Your analysis should answer:
- Which categories have poorest FCR and why?
- Where are resolution time bottlenecks?
- What types of issues require escalation most?
- What operational improvements would have highest impact?

DO NOT:
- Focus on customer emotional state (they're in support - they're unhappy)
- Report sentiment scores as if they're meaningful
- Use dramatic language about "crisis" or "pain"

DO:
- Compare to operational benchmarks (FCR target: 70%, resolution time target: <4 hours)
- Identify specific process inefficiencies
- Quantify potential improvements ("Improving Billing FCR from 45% to 60% could reduce ticket volume by 8%")
- Focus on "what's changing" if trend data available
```

---

## Part 6: Updated Analysis Output Example

### What It SHOULD Look Like:

```markdown
# Voice of Customer: Operational Analysis
## October 2024 Support Performance

**Key Findings**: Resolution efficiency below target in two high-volume categories

### Resolution Efficiency Metrics

**First Contact Resolution: 58%** (Target: >70%)
This is our first baseline measurement. Industry benchmark is 70-80%.

Category breakdown reveals where to focus:
- Product Questions: 72% FCR ✅ Meeting target
- Account Management: 69% FCR → Close to target
- Billing: 45% FCR ❌ 25 points below target
- Bug Reports: 41% FCR ❌ 29 points below target

**Impact**: Billing and Bug categories represent 68% of total volume. Improving their FCR to 60% (15 point improvement) would reduce overall ticket volume by an estimated 10%.

### Resolution Time Performance

**Median: 8.2 hours** (Target: <4 hours)
**90th Percentile: 36 hours** (Target: <24 hours)

Category-specific resolution times:
- Product Questions: 4.1 hours (at target)
- Account Management: 5.8 hours
- Billing: 12.4 hours (3x slower than product questions)
- Bug Reports: 18.2 hours (requires iteration with engineering)

**Insight**: Billing tickets take 3x longer to resolve than product questions despite being the highest volume category. This suggests either:
- Complex billing logic requiring senior staff input
- Lack of agent training/resources for billing issues
- Process bottlenecks in billing resolution workflow

### Escalation Analysis

**Overall Escalation Rate: 18%** (Target: <15%)

Escalations by category:
- Bug Reports: 31% escalation rate
- Billing: 28% escalation rate
- API Issues: 22% escalation rate
- Product Questions: 8% escalation rate

**Pattern**: Categories with poor FCR also have high escalation rates, suggesting these issues require expertise beyond front-line agents.

Escalation destinations:
- To senior staff (Dae-Ho, Max, Hilary): 12% of all tickets
- Priority flagged: 6% of all tickets

### Agent Performance Distribution

**Horatio agents**: 67% of conversations
- FCR: 61%
- Median resolution: 6.8 hours

**Escalated to senior staff**: 18% of conversations  
- FCR: 42% (lower because these are complex issues)
- Median resolution: 18.3 hours

**AI Agent participated**: 15% of conversations
- FCR: 71% (higher than human agents!)
- Median resolution: 3.1 hours

**Insight**: AI agent shows strong performance where it's deployed. Consider expanding AI coverage for routine issues to free up human agents for complex cases.

### Recommendations (Data-Driven)

**Priority 1: Improve Billing FCR** (High Impact, Medium Effort)
- Current: 45% FCR, 1,166 tickets/month
- Target: 60% FCR
- Expected outcome: 175 fewer repeat contacts/month
- Action: Develop billing resolution playbook, add self-service options

**Priority 2: Reduce Billing Resolution Time** (High Impact, Medium Effort)
- Current: 12.4 hour median
- Target: 6 hours
- Action: Audit billing process for bottlenecks, add agent training

**Priority 3: Expand AI Agent Coverage** (Medium Impact, Low Effort)
- Current: 15% coverage with 71% FCR
- Target: 30% coverage for routine questions
- Expected outcome: Improve overall FCR by 3-5 points

**Priority 4: Track Month-over-Month** (Baseline Establishment)
- This is our first analysis - no trend data yet
- Repeat monthly to identify:
  - FCR improvements/degradations
  - Resolution time changes
  - Category volume shifts
  - Escalation pattern changes
```

---

## Summary

**YES** - we ARE extracting the operational data from Intercom, but we're not:
1. **Calculating** the key metrics (FCR, resolution time, escalation rate)
2. **Analyzing** them instead of sentiment
3. **Presenting** them as the primary insights

The multi-agent system needs to be **completely refocused** from emotional analysis to operational efficiency analysis.

Want me to rewrite all the agent prompts and logic to focus on these operational metrics?
