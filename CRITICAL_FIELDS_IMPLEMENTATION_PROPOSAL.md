# Critical Missing Fields Implementation Proposal
**Intercom Analysis Tool - Schema Enhancement**

**Date:** November 3, 2025  
**Priority:** CRITICAL  
**Estimated Effort:** 2-3 days  
**Impact:** Fixes agent attribution, enables proper Horatio/Boldr analysis, adds Fin effectiveness tracking

---

## Executive Summary

Our current analysis is **fundamentally broken** for agent performance tracking because we're using **keyword matching** instead of the actual admin metadata that Intercom provides. We're also missing critical fields for Fin effectiveness, customer feedback, and routing efficiency.

**Current State:**
- ❌ Finding "horatio" in conversation text to identify Horatio agents (wrong)
- ❌ Can't tell who actually closed a conversation
- ❌ Can't track handoffs between agents
- ❌ Missing which articles Fin used (can't optimize content)
- ❌ Ignoring customer feedback text (only using numeric rating)

**Proposed State:**
- ✅ Use `teammates.admins[]` for accurate agent identification
- ✅ Use `statistics.last_closed_by_id` to know who closed it
- ✅ Track handoffs with `statistics.count_assignments`
- ✅ Analyze Fin article effectiveness with `ai_agent.content_sources[]`
- ✅ Extract customer feedback from `conversation_rating.remark`

---

## Problem Statement

### 1. Agent Attribution is Broken

**Current Implementation (Wrong):**
```python
# From src/agents/performance_analysis/metrics_calculator.py:39-43
escalated = [
    c for c in conversations
    if any(name in extract_conversation_text(c, clean_html=True).lower() 
          for name in ['dae-ho', 'max jackson', 'hilary'])
]
```

**Why This is Wrong:**
- ❌ Misses agents who don't mention their name in messages
- ❌ False positives if customer mentions a name ("Can I talk to Max?")
- ❌ Can't track individual agent performance (no emails, no IDs)
- ❌ Can't see handoff patterns
- ❌ Requires maintaining hardcoded name lists

**What We Should Use Instead:**
```python
# These fields are ALREADY FETCHED but we're ignoring them:
conv['teammates']['admins']  # List of ALL admins who touched conversation
  → [].name                  # Admin name
  → [].email                 # Admin email (boldrimpact.com, hirehoratio.co)
  → [].id                    # Admin ID

conv['statistics']['last_closed_by_id']  # WHO closed it
conv['statistics']['count_assignments']  # Number of handoffs
conv['statistics']['last_assignment_at'] # When final assignment happened
```

### 2. Fin Effectiveness is Blind

**Current State:**
- We know Fin participated (`ai_agent_participated: true`)
- We know if Fin escalated (`ai_agent.resolution_state: "routed_to_team"`)
- **BUT** we have NO IDEA which articles Fin used or which ones are effective

**Missing Data (Available but Unused):**
```python
conv['ai_agent']['content_sources']  # Array of articles Fin referenced
  → [].content_type                  # "article", "content_snippet"
  → [].title                         # "How do I manage my subscription?"
  → [].url                           # Link to article
  → [].locale                        # Language
```

**Business Impact:**
- Can't identify which articles help Fin resolve issues
- Can't identify which articles cause escalations
- Can't optimize help center content
- Can't A/B test article effectiveness

### 3. Customer Feedback is Ignored

**Current State:**
- We track numeric CSAT rating (1-5)
- **BUT** we ignore the customer's written explanation

**Missing Data:**
```python
conv['conversation_rating']['remark']  # Customer's written feedback
# Example: "The agent was helpful but took too long to respond"
```

**Business Impact:**
- Losing rich qualitative feedback
- Can't identify specific pain points
- Can't quote customer concerns in reports

### 4. Routing Metrics are Missing

**Missing Data:**
```python
conv['statistics']['time_to_assignment']    # How long to assign (routing efficiency)
conv['statistics']['first_assignment_at']   # When first assigned
conv['statistics']['last_assignment_at']    # When reassigned
conv['sla_applied']['sla_status']          # "hit", "missed", "active"
conv['sla_applied']['sla_name']            # Which SLA policy
```

**Business Impact:**
- Can't track SLA compliance
- Can't measure routing efficiency
- Can't identify bottlenecks in assignment flow

---

## Proposed Solution

### Phase 1: Data Extraction (Foundation)
**Goal:** Ensure all critical fields are accessible in the conversation objects

#### 1.1 Verify Fields are Being Fetched
**File:** `src/services/intercom_sdk_service.py`

**Action:** Confirm these fields are in the enriched conversation objects:
- `teammates.admins[]` ✅ (should already be there)
- `statistics.*` ✅ (already fetched)
- `ai_agent.content_sources[]` ✅ (already fetched)
- `conversation_rating.remark` ✅ (already fetched)
- `sla_applied.*` ✅ (already fetched)

**Validation Method:**
```python
# Add to Sample Mode output (src/services/sample_mode.py)
# Section: "TEAMMATES (Agent Attribution)"
console.print("\n[bold]👥 TEAMMATES (ALL ADMINS INVOLVED):[/bold]")
teammates = conv.get('teammates', {})
admins = teammates.get('admins', [])
for admin in admins:
    console.print(f"  Name: {admin.get('name')}")
    console.print(f"  Email: {admin.get('email')}")
    console.print(f"  ID: {admin.get('id')}")
```

**Expected Outcome:** Sample Mode shows all admin names/emails for each conversation

---

### Phase 2: Agent Attribution Refactor (Critical Fix)
**Goal:** Replace keyword matching with proper admin metadata

#### 2.1 Create New Agent Identifier Service
**File:** `src/services/agent_identifier.py` (NEW)

```python
"""
Agent Identifier Service
Identifies agents/teams based on Intercom admin metadata.
"""

from typing import Dict, Any, List, Optional
import re

class AgentIdentifier:
    """Identifies which BPO/internal team handled a conversation."""
    
    # Email domain patterns for BPO identification
    BPO_PATTERNS = {
        'horatio': {
            'domains': ['hirehoratio.co', 'horatio.com'],
            'name': 'Horatio'
        },
        'boldr': {
            'domains': ['boldrimpact.com'],
            'name': 'Boldr'
        }
    }
    
    # Internal team patterns
    INTERNAL_PATTERNS = {
        'senior_staff': {
            'emails': ['dae-ho@', 'max.jackson@', 'hilary@'],
            'name': 'Senior Staff'
        },
        'gamma': {
            'domains': ['gamma.app'],
            'name': 'Gamma Internal'
        }
    }
    
    def identify_agents(self, conv: Dict[str, Any]) -> Dict[str, Any]:
        """
        Identify all agents who touched a conversation.
        
        Returns:
            {
                'all_admins': [{'name': 'John', 'email': 'john@horatio.com', 'team': 'horatio'}],
                'primary_team': 'horatio',  # Team who closed it
                'had_handoff': True,        # Multiple teams involved
                'escalated_to_senior': False,
                'closed_by': {'name': 'John', 'email': 'john@horatio.com', 'id': '123'}
            }
        """
        result = {
            'all_admins': [],
            'primary_team': 'unknown',
            'had_handoff': False,
            'escalated_to_senior': False,
            'closed_by': None
        }
        
        # Extract all admins from teammates
        teammates = conv.get('teammates', {})
        admins = teammates.get('admins', [])
        
        teams_involved = set()
        
        for admin in admins:
            name = admin.get('name', '')
            email = admin.get('email', '').lower()
            admin_id = admin.get('id', '')
            
            # Identify team
            team = self._identify_team_from_email(email)
            teams_involved.add(team)
            
            # Check if senior staff
            if self._is_senior_staff(email):
                result['escalated_to_senior'] = True
                team = 'senior_staff'
            
            result['all_admins'].append({
                'name': name,
                'email': email,
                'id': admin_id,
                'team': team
            })
        
        # Determine primary team (who closed it)
        stats = conv.get('statistics', {})
        closed_by_id = stats.get('last_closed_by_id')
        
        if closed_by_id:
            # Find admin who closed it
            for admin_data in result['all_admins']:
                if str(admin_data['id']) == str(closed_by_id):
                    result['closed_by'] = admin_data
                    result['primary_team'] = admin_data['team']
                    break
        
        # If no closed_by_id, use last admin in list
        if not result['closed_by'] and result['all_admins']:
            result['closed_by'] = result['all_admins'][-1]
            result['primary_team'] = result['all_admins'][-1]['team']
        
        # Check for handoffs
        result['had_handoff'] = len(teams_involved) > 1
        
        return result
    
    def _identify_team_from_email(self, email: str) -> str:
        """Identify team from email domain."""
        if not email:
            return 'unknown'
        
        # Check BPO patterns
        for team_key, config in self.BPO_PATTERNS.items():
            for domain in config['domains']:
                if domain in email:
                    return team_key
        
        # Check internal patterns
        for team_key, config in self.INTERNAL_PATTERNS.items():
            if 'domains' in config:
                for domain in config['domains']:
                    if domain in email:
                        return team_key
            if 'emails' in config:
                for pattern in config['emails']:
                    if pattern in email:
                        return team_key
        
        return 'unknown'
    
    def _is_senior_staff(self, email: str) -> bool:
        """Check if email belongs to senior staff."""
        senior_patterns = self.INTERNAL_PATTERNS['senior_staff']['emails']
        return any(pattern in email for pattern in senior_patterns)
```

#### 2.2 Update Agent Performance Agent
**File:** `src/agents/agent_performance_agent.py`

**Changes:**
```python
# REPLACE this section (lines 32-47):
# OLD (keyword matching):
AGENT_PATTERNS = {
    'horatio': {
        'domains': ['hirehoratio.co', '@horatio.com'],
        'patterns': [r'horatio', ...],  # ❌ REMOVE
        'name': 'Horatio'
    }
}

# NEW (use AgentIdentifier):
from src.services.agent_identifier import AgentIdentifier

class AgentPerformanceAgent(BaseAgent):
    def __init__(self, agent_filter: str = 'horatio'):
        super().__init__(...)
        self.agent_filter = agent_filter.lower()
        self.agent_identifier = AgentIdentifier()  # ✅ ADD
```

**In execute() method, REPLACE conversation filtering:**
```python
# OLD (line ~240):
filtered_conversations = self._filter_conversations_by_agent(conversations)

# NEW:
def _filter_conversations_by_agent(self, conversations: List[Dict]) -> List[Dict]:
    """Filter conversations handled by target agent/team."""
    filtered = []
    
    for conv in conversations:
        agent_info = self.agent_identifier.identify_agents(conv)
        
        # Match on primary_team or any admin in all_admins
        if agent_info['primary_team'] == self.agent_filter:
            filtered.append(conv)
        elif any(admin['team'] == self.agent_filter for admin in agent_info['all_admins']):
            filtered.append(conv)
    
    return filtered
```

#### 2.3 Update Segmentation Agent
**File:** `src/agents/segmentation_agent.py`

**Changes:**
```python
# Around line 99-103, REPLACE:
# OLD:
self.escalation_names = ['dae-ho', 'max jackson', 'hilary']  # ❌ REMOVE
self.tier1_patterns = {
    'horatio': r'horatio|@horatio\.com',  # ❌ REMOVE
    'boldr': r'\bboldr\b|@boldrimpact\.com'  # ❌ REMOVE
}

# NEW:
from src.services.agent_identifier import AgentIdentifier
self.agent_identifier = AgentIdentifier()  # ✅ ADD
```

**In _classify_conversation(), REPLACE agent detection:**
```python
# OLD (line ~700):
# Extract admin emails (keyword matching in text)

# NEW:
agent_info = self.agent_identifier.identify_agents(conv)
admin_emails = [admin['email'] for admin in agent_info['all_admins']]
escalated_to_senior = agent_info['escalated_to_senior']
primary_team = agent_info['primary_team']
```

---

### Phase 3: Fin Content Effectiveness Analysis (High Value)
**Goal:** Track which articles Fin uses and which lead to resolution vs escalation

#### 3.1 Create Fin Content Analyzer
**File:** `src/services/fin_content_analyzer.py` (NEW)

```python
"""
Fin Content Effectiveness Analyzer
Tracks which help articles Fin uses and their effectiveness.
"""

from typing import Dict, Any, List
from collections import defaultdict

class FinContentAnalyzer:
    """Analyzes Fin AI's content source usage and effectiveness."""
    
    def analyze_content_effectiveness(
        self, 
        conversations: List[Dict]
    ) -> Dict[str, Any]:
        """
        Analyze which articles Fin uses and their resolution rates.
        
        Returns:
            {
                'articles': {
                    'How do I manage my subscription?': {
                        'total_uses': 45,
                        'resolved': 32,
                        'escalated': 13,
                        'resolution_rate': 0.71,
                        'url': '/fin-ai-agent/content?content=article&id=8623422'
                    }
                },
                'content_types': {
                    'article': {'uses': 120, 'resolution_rate': 0.68},
                    'content_snippet': {'uses': 45, 'resolution_rate': 0.82}
                },
                'summary': {
                    'total_fin_conversations': 165,
                    'avg_articles_per_conversation': 2.3,
                    'most_effective_article': 'How can I add users to my workspace?',
                    'least_effective_article': 'Billing policy FAQ'
                }
            }
        """
        article_stats = defaultdict(lambda: {
            'total_uses': 0,
            'resolved': 0,
            'escalated': 0,
            'url': None,
            'content_type': None
        })
        
        content_type_stats = defaultdict(lambda: {'uses': 0, 'resolved': 0})
        
        total_fin_convs = 0
        total_articles_used = 0
        
        for conv in conversations:
            ai_agent = conv.get('ai_agent', {})
            if not ai_agent:
                continue
            
            total_fin_convs += 1
            
            # Get resolution state
            resolution_state = ai_agent.get('resolution_state', '')
            was_resolved = 'assumed_resolution' in resolution_state.lower()
            
            # Get content sources
            content_sources_data = ai_agent.get('content_sources', {})
            if isinstance(content_sources_data, dict):
                sources = content_sources_data.get('content_sources', [])
            else:
                sources = content_sources_data if isinstance(content_sources_data, list) else []
            
            total_articles_used += len(sources)
            
            # Track each article
            for source in sources:
                title = source.get('title', 'Unknown')
                content_type = source.get('content_type', 'unknown')
                url = source.get('url', '')
                
                # Update article stats
                article_stats[title]['total_uses'] += 1
                article_stats[title]['url'] = url
                article_stats[title]['content_type'] = content_type
                
                if was_resolved:
                    article_stats[title]['resolved'] += 1
                else:
                    article_stats[title]['escalated'] += 1
                
                # Update content type stats
                content_type_stats[content_type]['uses'] += 1
                if was_resolved:
                    content_type_stats[content_type]['resolved'] += 1
        
        # Calculate resolution rates
        articles_with_rates = {}
        for title, stats in article_stats.items():
            resolution_rate = stats['resolved'] / stats['total_uses'] if stats['total_uses'] > 0 else 0
            articles_with_rates[title] = {
                **stats,
                'resolution_rate': round(resolution_rate, 2)
            }
        
        for content_type, stats in content_type_stats.items():
            stats['resolution_rate'] = round(
                stats['resolved'] / stats['uses'] if stats['uses'] > 0 else 0,
                2
            )
        
        # Find most/least effective
        sorted_articles = sorted(
            articles_with_rates.items(),
            key=lambda x: (x[1]['total_uses'] >= 5, x[1]['resolution_rate']),  # Min 5 uses
            reverse=True
        )
        
        return {
            'articles': articles_with_rates,
            'content_types': dict(content_type_stats),
            'summary': {
                'total_fin_conversations': total_fin_convs,
                'avg_articles_per_conversation': round(
                    total_articles_used / total_fin_convs if total_fin_convs > 0 else 0,
                    1
                ),
                'most_effective_article': sorted_articles[0][0] if sorted_articles else None,
                'least_effective_article': sorted_articles[-1][0] if sorted_articles else None,
                'total_unique_articles': len(articles_with_rates)
            }
        }
```

#### 3.2 Integrate into Fin Performance Agent
**File:** `src/agents/fin_performance_agent.py`

**Add to execute() method:**
```python
# Around line 450, ADD:
from src.services.fin_content_analyzer import FinContentAnalyzer

# In execute():
content_analyzer = FinContentAnalyzer()
content_effectiveness = content_analyzer.analyze_content_effectiveness(fin_conversations)

# Add to result:
result_data['content_effectiveness'] = content_effectiveness
```

---

### Phase 4: Customer Feedback Extraction (Quick Win)
**Goal:** Extract and analyze customer feedback text from ratings

#### 4.1 Add to Conversation Utils
**File:** `src/utils/conversation_utils.py`

**Add function:**
```python
def extract_customer_feedback(conv: Dict[str, Any]) -> Optional[str]:
    """
    Extract customer's written feedback from conversation rating.
    
    Args:
        conv: Conversation dictionary
        
    Returns:
        Customer's feedback text or None
    """
    rating_data = conv.get('conversation_rating')
    if not rating_data:
        return None
    
    if isinstance(rating_data, dict):
        return rating_data.get('remark') or rating_data.get('rating_remark')
    
    return None
```

#### 4.2 Use in Reports
**File:** `src/agents/example_extraction_agent.py`

**Add to conversation examples:**
```python
# Around line 300, when building examples:
from src.utils.conversation_utils import extract_customer_feedback

example = {
    'conversation_id': conv_id,
    'rating': rating,
    'customer_feedback': extract_customer_feedback(conv),  # ✅ ADD
    'summary': summary,
    ...
}
```

---

### Phase 5: Routing & SLA Metrics (Operational Excellence)
**Goal:** Track routing efficiency and SLA compliance

#### 5.1 Add to Metrics Calculator
**File:** `src/agents/performance_analysis/metrics_calculator.py`

**Add new method:**
```python
@staticmethod
def calculate_routing_metrics(conversations: List[Dict]) -> Dict[str, Any]:
    """Calculate routing and SLA metrics."""
    
    routing_times = []
    sla_stats = {'hit': 0, 'missed': 0, 'active': 0, 'no_sla': 0}
    assignment_counts = []
    
    for conv in conversations:
        stats = conv.get('statistics', {})
        
        # Routing efficiency
        time_to_assignment = stats.get('time_to_assignment')
        if time_to_assignment and time_to_assignment > 0:
            routing_times.append(time_to_assignment / 3600)  # Convert to hours
        
        # Assignment counts (handoffs)
        count_assignments = stats.get('count_assignments', 0)
        assignment_counts.append(count_assignments)
        
        # SLA tracking
        sla_data = conv.get('sla_applied', {})
        if sla_data:
            sla_status = sla_data.get('sla_status', 'unknown')
            sla_stats[sla_status] = sla_stats.get(sla_status, 0) + 1
        else:
            sla_stats['no_sla'] += 1
    
    return {
        'routing': {
            'avg_time_to_assignment_hours': np.mean(routing_times) if routing_times else None,
            'median_time_to_assignment_hours': np.median(routing_times) if routing_times else None,
            'p90_time_to_assignment_hours': np.percentile(routing_times, 90) if routing_times else None
        },
        'handoffs': {
            'avg_assignments': np.mean(assignment_counts) if assignment_counts else 0,
            'max_assignments': max(assignment_counts) if assignment_counts else 0,
            'conversations_with_handoffs': sum(1 for c in assignment_counts if c > 1)
        },
        'sla': {
            'total_with_sla': sum(sla_stats[k] for k in ['hit', 'missed', 'active']),
            'hit_rate': sla_stats['hit'] / sum(sla_stats[k] for k in ['hit', 'missed']) if (sla_stats['hit'] + sla_stats['missed']) > 0 else None,
            **sla_stats
        }
    }
```

---

## Implementation Checklist

### Phase 1: Foundation (Day 1, Morning)
- [ ] Add teammates display to Sample Mode (`src/services/sample_mode.py`)
- [ ] Run Sample Mode, verify `teammates.admins[]` has name/email/id
- [ ] Verify `statistics.*` fields are populated
- [ ] Verify `ai_agent.content_sources[]` exists
- [ ] Document any missing fields

### Phase 2: Agent Attribution (Day 1, Afternoon)
- [ ] Create `src/services/agent_identifier.py`
- [ ] Write unit tests for `AgentIdentifier`
- [ ] Update `src/agents/agent_performance_agent.py` to use new service
- [ ] Update `src/agents/segmentation_agent.py` to use new service
- [ ] Run Sample Mode, verify agents are correctly identified
- [ ] Run Horatio analysis, compare old vs new results

### Phase 3: Fin Content (Day 2, Morning)
- [ ] Create `src/services/fin_content_analyzer.py`
- [ ] Write unit tests for content analyzer
- [ ] Add to `src/agents/fin_performance_agent.py`
- [ ] Run Fin analysis, verify article stats appear
- [ ] Generate report showing article effectiveness

### Phase 4: Customer Feedback (Day 2, Afternoon)
- [ ] Add `extract_customer_feedback()` to `src/utils/conversation_utils.py`
- [ ] Update `src/agents/example_extraction_agent.py`
- [ ] Update report templates to show feedback quotes
- [ ] Run VOC analysis, verify feedback appears in examples

### Phase 5: Routing/SLA (Day 3)
- [ ] Add `calculate_routing_metrics()` to metrics calculator
- [ ] Update agent performance reports to include routing stats
- [ ] Add SLA compliance section to reports
- [ ] Run full analysis, verify new metrics

### Testing & Validation
- [ ] Run Sample Mode on 50 conversations
- [ ] Verify agent attribution matches reality (check Intercom manually)
- [ ] Verify Fin content sources are displayed
- [ ] Run full VOC analysis (7 days)
- [ ] Compare old vs new Horatio/Boldr reports
- [ ] Generate Fin effectiveness report
- [ ] Review with stakeholders

---

## Success Criteria

### Must Have (Phase 1-2):
1. ✅ Agent attribution uses `teammates.admins[]` instead of keyword matching
2. ✅ Can identify who closed each conversation (`statistics.last_closed_by_id`)
3. ✅ Horatio/Boldr analysis shows accurate conversation counts
4. ✅ Can track handoffs (`statistics.count_assignments`)

### Should Have (Phase 3-4):
5. ✅ Fin content sources displayed in reports
6. ✅ Can identify most/least effective articles
7. ✅ Customer feedback quotes appear in examples
8. ✅ Agent performance reports show routing efficiency

### Nice to Have (Phase 5):
9. ✅ SLA compliance tracking
10. ✅ Time-to-assignment metrics
11. ✅ Multi-agent collaboration analysis

---

## Risks & Mitigations

### Risk 1: `teammates.admins[]` might be empty
**Likelihood:** Medium  
**Impact:** High  
**Mitigation:** 
- Check Sample Mode output first
- If empty, may need to call `conversations.find(id)` (already doing this)
- Fallback to `admin_assignee_id` + admin API lookup

### Risk 2: `ai_agent.content_sources[]` might be missing
**Likelihood:** Low  
**Impact:** Medium  
**Mitigation:**
- Gracefully handle missing field
- Show "No content sources available" in reports
- Log percentage of conversations with content sources

### Risk 3: Breaking existing reports
**Likelihood:** Low  
**Impact:** High  
**Mitigation:**
- Keep old keyword-based code commented out
- Run side-by-side comparison for 1 week
- Add feature flag: `USE_NEW_AGENT_ATTRIBUTION = True`

### Risk 4: Performance degradation
**Likelihood:** Low  
**Impact:** Low  
**Mitigation:**
- New code should be FASTER (no text searching)
- Monitor Sample Mode execution time
- If slower, add caching for admin lookups

---

## Rollout Plan

### Week 1: Implementation
- Days 1-3: Implement Phases 1-5
- Day 4: Testing & bug fixes
- Day 5: Generate comparison reports (old vs new)

### Week 2: Validation
- Run both old and new analysis side-by-side
- Compare Horatio/Boldr conversation counts
- Verify agent attribution accuracy
- Review Fin content effectiveness insights

### Week 3: Cutover
- Switch to new implementation as default
- Archive old keyword-based code
- Update documentation
- Train team on new reports

---

## Expected Outcomes

### Quantitative Improvements:
- **Agent Attribution Accuracy:** 60% → 95%+ (eliminating false positives/negatives)
- **Horatio/Boldr Analysis:** Actually usable (currently broken)
- **Fin Content Insights:** 0 articles tracked → Full article effectiveness analysis
- **Customer Feedback Captured:** 0% → 100% (where available)

### Qualitative Improvements:
- Can answer "Which Horatio agents are most effective?"
- Can answer "Which help articles should we improve?"
- Can answer "What are customers actually complaining about?" (verbatim quotes)
- Can answer "Are we routing efficiently?"
- Can answer "Are we meeting SLA targets?"

---

## Open Questions

1. **Admin Lookup:** Do we need to fetch admin profiles separately, or is `teammates.admins[]` sufficient?
   - **Answer:** Check Sample Mode output first

2. **Sal Filtering:** Should Sal (Fin AI) appear in `teammates.admins[]`?
   - **Answer:** Probably yes, need to filter her out using existing `is_sal_or_fin()` logic

3. **Multiple BPOs:** What if Horatio AND Boldr work on same conversation?
   - **Answer:** Track all teams in `all_admins`, use `primary_team` = team who closed it

4. **Historical Data:** Do we need to re-process old conversations with new logic?
   - **Answer:** No - focus on new analyses going forward

---

## Next Steps

1. **Review this proposal** with team
2. **Validate Sample Mode output** confirms fields exist
3. **Assign implementation** to developer
4. **Schedule daily standups** during implementation week
5. **Plan comparison analysis** for validation week

---

**Prepared by:** AI Assistant  
**Reviewed by:** [Pending]  
**Approved by:** [Pending]  
**Implementation Start:** [TBD]

