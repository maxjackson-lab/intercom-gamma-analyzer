# Topic-Based Multi-Agent Architecture
## Designed to Match Hilary's Weekly VoC Format

---

## Overview

This multi-agent system is specifically designed to produce Hilary's desired weekly Voice of Customer analysis format, with clear segmentation between paid customer support and Fin AI performance.

## Core Workflow

```
Raw Conversations
    ↓
SegmentationAgent → Paid Customers (Human Support) + Free Customers (AI Only)
    ↓                                               ↓
TopicDetectionAgent                         FinPerformanceAgent
(Hybrid: Keywords + Attributes)             (AI performance metrics)
    ↓
FOR EACH TOPIC:
    ├─ TopicSentimentAgent (specific insight per topic)
    ├─ ExampleExtractionAgent (3-10 best conversations)
    └─ OperationalMetricsAgent (FCR, resolution time per topic)
    ↓
TrendAgent (week-over-week comparison)
    ↓
OutputFormatterAgent → Hilary's Exact Card Format
```

## Agent Specifications

### 1. SegmentationAgent

**Purpose**: Separate paid customers (human support) from free customers (AI-only)

**Logic**:
```python
def segment_conversation(conv):
    # Has human agent involvement?
    has_human = (
        conv.get('admin_assignee_id') or
        'horatio' in conv.get('full_text', '').lower() or
        'boldr' in conv.get('full_text', '').lower() or
        any(name in conv.get('full_text', '').lower() 
            for name in ['dae-ho', 'max jackson', 'hilary'])
    )
    
    # AI-only conversation?
    ai_only = (
        conv.get('ai_agent_participated') and 
        not has_human
    )
    
    if has_human:
        return 'paid_customer'  # Has access to human support
    elif ai_only:
        return 'free_customer'  # AI-only (Fin)
    else:
        return 'unknown'
```

**Output**:
```json
{
  "paid_customer_conversations": [...],  // 60-70% typically
  "free_customer_conversations": [...],   // 30-40% typically
  "unknown": [...]  // Should be minimal
}
```

---

### 2. TopicDetectionAgent

**Purpose**: Detect topics using hybrid method (Intercom attributes + keywords)

**Detection Methods**:

```python
TOPIC_DETECTION = {
    "Credits": {
        "attribute": "Credits",  // Intercom custom attribute
        "keywords": ["credit", "credits", "out of credits", "buy credits"],
        "method": "attribute_primary"  // Prefer attribute if exists
    },
    "Agent/Buddy": {
        "attribute": None,  // No attribute for this
        "keywords": ["buddy", "agent", "ai assistant", "copilot"],
        "method": "keyword_only"
    },
    "Workspace Templates": {
        "attribute": "Workspace Templates",
        "keywords": ["template", "workspace template", "starting point"],
        "method": "attribute_primary"
    },
    "Billing": {
        "attribute": "Billing",
        "keywords": ["refund", "cancel", "subscription", "payment"],
        "method": "attribute_primary"
    }
}

def detect_topics(conversation):
    """
    Returns: {
        "topic_name": "Credits",
        "detection_method": "attribute",  // or "keyword"
        "confidence": 0.95
    }
    """
    detected_topics = []
    
    # Check attributes first
    attributes = conversation.get('custom_attributes', {})
    
    for topic_name, config in TOPIC_DETECTION.items():
        # Try attribute first
        if config['attribute'] and config['attribute'] in attributes:
            detected_topics.append({
                'topic': topic_name,
                'method': 'attribute',
                'confidence': 1.0
            })
            continue
        
        # Fallback to keywords
        text = conversation.get('full_text', '').lower()
        keyword_matches = sum(1 for kw in config['keywords'] if kw in text)
        
        if keyword_matches > 0:
            detected_topics.append({
                'topic': topic_name,
                'method': 'keyword',
                'confidence': min(0.9, 0.6 + (keyword_matches * 0.1))
            })
    
    return detected_topics
```

---

### 3. TopicSentimentAgent

**Purpose**: Generate SPECIFIC sentiment insight for each topic (not generic negative/positive)

**Critical Instructions**:
```
For topic "[TOPIC_NAME]":

Analyze ONLY the conversations tagged with this topic.
Generate a ONE-SENTENCE insight that captures the NUANCED sentiment.

GOOD EXAMPLES:
- "Users are appreciative of the ability to buy more credits, but frustrated that Gamma moved to a credit model"
- "Users hate buddy so much"
- "Users think templates are rad but want to be able to use them with API"

BAD EXAMPLES:
- "Negative sentiment detected"
- "Users are frustrated"
- "Mixed sentiment with concerns"

The insight should:
1. Be specific to THIS topic
2. Capture the nuance (appreciative BUT frustrated)
3. Be actionable (tells us what to improve)
4. Use natural language (how Hilary would say it)
```

**Implementation**:
```python
async def analyze_topic_sentiment(self, topic_name, conversations):
    """
    Generate specific sentiment insight for a topic
    
    Args:
        topic_name: e.g., "Credits", "Agent/Buddy"
        conversations: Only conversations tagged with this topic
    
    Returns:
        Specific sentiment string
    """
    # Build focused prompt
    prompt = f"""
Analyze sentiment for the topic: {topic_name}

Conversations (sample of {min(10, len(conversations))}):
{self._format_conversations_for_analysis(conversations[:10])}

Generate a ONE-SENTENCE sentiment insight that:
- Captures the specific sentiment for THIS topic
- Shows nuance (e.g., "appreciative BUT frustrated")
- Is actionable and specific
- Uses natural, conversational language

Examples of good insights:
- "Users hate buddy so much"
- "Users think templates are rad but want to be able to use them with API"
- "Users are appreciative of the ability to buy more credits, but frustrated that Gamma moved to a credit model"

Your insight for {topic_name}:
"""
    
    response = await self.openai_client.generate_analysis(prompt)
    return response.strip()
```

---

### 4. ExampleExtractionAgent

**Purpose**: Find 3-10 BEST conversations that demonstrate the sentiment

**Selection Criteria**:
```python
def select_best_examples(conversations, topic_name, sentiment_insight, target_count=7):
    """
    Select representative conversations
    
    Criteria:
    1. Clear demonstration of the sentiment
    2. Readable/quotable customer message
    3. Diversity (different aspects of the sentiment)
    4. Recent (prefer newer conversations)
    """
    
    scored_conversations = []
    
    for conv in conversations:
        score = 0
        
        # Has clear customer message (not just agent responses)
        customer_messages = conv.get('customer_messages', [])
        if customer_messages and len(customer_messages[0]) > 50:
            score += 2
        
        # Matches sentiment keywords
        text = conv.get('full_text', '').lower()
        if 'frustrated' in sentiment_insight.lower() and 'frustrat' in text:
            score += 1
        if 'appreciative' in sentiment_insight.lower() and any(word in text for word in ['thank', 'appreciate', 'love']):
            score += 1
        if 'hate' in sentiment_insight.lower() and 'hate' in text:
            score += 2
        
        # Has conversation rating (CSAT)
        if conv.get('conversation_rating'):
            score += 1
        
        # Recency (newer is better)
        if conv.get('created_at'):
            days_old = (datetime.now() - conv['created_at']).days
            if days_old < 3:
                score += 1
        
        scored_conversations.append((score, conv))
    
    # Sort by score and select top N
    scored_conversations.sort(reverse=True, key=lambda x: x[0])
    return [conv for score, conv in scored_conversations[:target_count]]
```

---

### 5. FinPerformanceAgent (NEW!)

**Purpose**: Dedicated analysis of Fin AI performance for free tier customers

**Metrics to Calculate**:

```python
def analyze_fin_performance(fin_conversations):
    """
    Analyze Fin AI performance
    
    Metrics:
    1. Resolution rate (no escalation to human requested)
    2. Knowledge gaps (incorrect answers)
    3. Unnecessary escalations (user asked for human but Fin was right)
    4. Performance by topic
    """
    
    total_fin = len(fin_conversations)
    
    # Resolution rate (Fin solved it - no human request)
    resolved_by_fin = [
        c for c in fin_conversations
        if not any(phrase in c.get('full_text', '').lower() 
                  for phrase in ['speak to human', 'talk to agent', 'real person'])
    ]
    fin_resolution_rate = len(resolved_by_fin) / total_fin if total_fin > 0 else 0
    
    # Knowledge gaps (user explicitly says Fin was wrong)
    knowledge_gaps = [
        c for c in fin_conversations
        if any(phrase in c.get('full_text', '').lower()
              for phrase in ['incorrect', 'wrong', 'not helpful', 'didn\'t answer'])
    ]
    
    # Satisfaction
    fin_satisfaction = [
        c.get('conversation_rating', {}).get('rating', 0)
        for c in fin_conversations
        if c.get('conversation_rating')
    ]
    
    return {
        'total_fin_conversations': total_fin,
        'resolution_rate': fin_resolution_rate,
        'knowledge_gaps_count': len(knowledge_gaps),
        'knowledge_gap_examples': knowledge_gaps[:5],
        'avg_satisfaction': np.mean(fin_satisfaction) if fin_satisfaction else None,
        'performance_by_topic': self._fin_performance_by_topic(fin_conversations)
    }
```

---

### 6. OutputFormatterAgent (REDESIGNED)

**Purpose**: Format into Hilary's exact card structure

**Output Template**:

```python
def format_output(topic_results, fin_results, support_stats):
    """
    Generate output in Hilary's exact format
    """
    
    output = []
    
    # SECTION 1: Voice of Customer
    output.append("# Voice of Customer Analysis - Week of [DATE]")
    output.append("\n## Customer Topics (Paid Tier - Human Support)\n")
    
    for topic in topic_results:
        card = f"""
### {topic['name']}
**{topic['volume']} tickets / {topic['percentage']}% of weekly volume**
**Detection Method**: {topic['detection_method']}  
({"Intercom attribute" if topic['detection_method'] == 'attribute' else "Keyword detection"})

**Sentiment**: {topic['sentiment_insight']}

**Examples**:
{self._format_examples(topic['examples'])}

---
"""
        output.append(card)
    
    # SECTION 2: Fin AI Performance
    output.append("\n## Fin AI Performance (Free Tier - AI-Only Support)\n")
    
    fin_card = f"""
### Fin AI Analysis
**{fin_results['total_fin_conversations']} conversations handled by Fin this week**

**What Fin is Doing Well**:
- Resolution rate: {fin_results['resolution_rate']:.1%} of conversations resolved without escalation request
- [Topic where Fin excels]

**Where Fin Has Knowledge Gaps**:
- {fin_results['knowledge_gaps_count']} conversations where Fin gave incorrect/incomplete info
- Examples: [links to conversations]

**Unnecessary Escalations**:
- [Count] times users requested human for info Fin already provided correctly
- Indicates: User trust issue or unclear Fin responses

**Performance by Topic**:
{self._format_fin_topic_performance(fin_results['performance_by_topic'])}

---
"""
    output.append(fin_card)
    
    # SECTION 3: Support Operations (Optional - separate report)
    output.append("\n## Support Operations Stats\n")
    output.append(f"""
**Response Times**:
- Median first response: {support_stats['median_response_hours']} hours
- 90th percentile: {support_stats['p90_response_hours']} hours

**Resolution Efficiency**:
- First Contact Resolution: {support_stats['fcr_rate']:.1%}
- Median resolution time: {support_stats['median_resolution_hours']} hours

**Escalations** (Tier 1 → Senior Staff):
- Escalation rate: {support_stats['escalation_rate']:.1%}
- Most escalated topics: [list]

**Agent Performance**:
- Horatio: {support_stats['horatio_fcr']:.1%} FCR, {support_stats['horatio_median_hours']} hour median
- Boldr: (No data yet - not deployed)
""")
    
    return '\n'.join(output)

def _format_examples(self, examples):
    """Format example conversation links"""
    formatted = []
    for i, example in enumerate(examples, 1):
        formatted.append(f"{i}. {example['preview']} - [View conversation]({example['intercom_url']})")
    return '\n'.join(formatted)
```

---

## Implementation Files to Create

### File 1: `src/agents/segmentation_agent.py`
- Separates paid (human support access) from free (AI-only)
- Detects agent type (Tier 1, Escalated, Fin)

### File 2: `src/agents/topic_detection_agent.py`
- Hybrid detection (Intercom attributes + keywords)
- Flags which method was used
- Supports custom topic definitions

### File 3: `src/agents/topic_sentiment_agent.py`
- Analyzes sentiment PER TOPIC (not overall)
- Generates specific, nuanced insights
- Avoids generic "negative sentiment" language

### File 4: `src/agents/example_extraction_agent.py`
- Selects 3-10 best representative conversations per topic
- Scores by relevance, readability, recency
- Includes Intercom links

### File 5: `src/agents/fin_performance_agent.py`
- Dedicated Fin AI analysis
- Resolution rate, knowledge gaps, unnecessary escalations
- Performance by topic

### File 6: `src/agents/trend_agent.py`
- Week-over-week comparison (when historical data exists)
- Volume changes, sentiment shifts
- Trending up/down indicators

### File 7: `src/agents/output_formatter_agent.py`
- Formats into Hilary's exact card structure
- Separates VoC (paid) from Fin analysis (free)
- Includes operational stats section

### File 8: `src/agents/topic_orchestrator.py`
- Coordinates topic-based workflow
- Processes each topic independently
- Combines results into final output

---

## Expected Output Format

```markdown
# Voice of Customer Analysis - Week of October 14-20, 2024

## Customer Topics (Paid Tier - Human Support)

### Credits
**487 tickets / 13% of weekly volume**  
**Detection Method**: Intercom conversation attribute  

**Sentiment**: Users are appreciative of the ability to buy more credits, but frustrated that Gamma moved to a credit model.

**Examples**:
1. "When I first signed up for Gamma, it didn't charge credits for this... what changed?" - [View](link)
2. "I appreciate being able to buy more credits, but I preferred the old unlimited model" - [View](link)
3. "Why did you switch to credits? This feels like a downgrade" - [View](link)

---

### Agent/Buddy
**500 tickets / 16% of weekly volume**  
**Detection Method**: Keyword detection (no Intercom attribute)

**Sentiment**: Users hate buddy so much.

**Examples**:
1. "The AI keeps changing my text even when I tell it not to" - [View](link)
2. "Can I turn off buddy? It's making my presentations worse" - [View](link)
3. "Every time buddy 'helps' it ruins what I was trying to do" - [View](link)

---

### Workspace Templates
**572 tickets / 21% of weekly volume**  
**Detection Method**: Intercom conversation attribute

**Sentiment**: Users think templates are rad but want to be able to use them with API.

**Examples**:
1. "Love the templates! Any way to access them via API?" - [View](link)
2. "Templates are great but I need programmatic access" - [View](link)
3. "Can I duplicate templates via API?" - [View](link)

---

## Fin AI Performance (Free Tier - AI-Only Support)

### Fin Analysis
**1,234 conversations handled by Fin this week**

**What Fin is Doing Well**:
- Resolution rate: 68% of conversations resolved without user requesting human
- Excels at: Account setup questions, basic billing questions
- Average satisfaction: 3.2/5 (acceptable for AI-only support)

**Knowledge Gaps**:
- 127 conversations where Fin gave incorrect/incomplete information
- Common gaps: Export troubleshooting, advanced feature usage, billing edge cases
- Examples: [3-5 links to conversations showing knowledge gaps]

**Unnecessary Escalations**:
- 45 times users requested human for info Fin already provided correctly
- Pattern: Users don't trust Fin's answers even when accurate
- Indicates: Trust issue or unclear response formatting

**Performance by Topic**:
- Account Questions: 78% resolution (good)
- Billing: 62% resolution (needs improvement)
- Bug Reports: 31% resolution (poor - users want human validation)

---

## Support Operations (Optional - Separate Report)

**Response Times**:
- Median first response: 2.3 hours
- 90th percentile: 8.1 hours

**Resolution Efficiency**:
- First Contact Resolution: 58%
- Median resolution time: 8.2 hours

**Escalations**:
- 18% of tickets escalated to senior staff (Dae-Ho, Max, Hilary)
- Most escalated: Billing (28%), Bugs (31%)

**Agent Performance**:
- Horatio: 61% FCR, 6.8 hour median resolution
- Boldr: (Not yet deployed)

---

## Week-over-Week Trends (Available after Week 2)

**Credits**:
- Volume: 487 tickets (↑ 12% vs last week)
- Sentiment: Stable (frustration level unchanged)

**Agent/Buddy**:
- Volume: 500 tickets (↑ 23% vs last week) 🚨 Trending up
- Sentiment: Worsening (more "hate" language detected)

**Fin AI**:
- Resolution rate: 68% (↑ 5% vs last week) ✅ Improving
- Knowledge gaps: 127 (↓ 8% vs last week) ✅ Improving
```

---

This is the EXACT format Hilary wants, enhanced with multi-agent intelligence!

Ready to implement?

