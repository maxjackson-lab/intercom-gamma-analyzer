# Intercom Analysis Tool - Complete Technical Specification
## For External QA/Review - October 22, 2025

---

# 📋 Table of Contents

1. [Executive Overview](#executive-overview)
2. [System Architecture](#system-architecture)
3. [Data Flow](#data-flow)
4. [Multi-Agent System](#multi-agent-system)
5. [API Integrations](#api-integrations)
6. [User Interface](#user-interface)
7. [Known Issues](#known-issues)
8. [Code Samples](#code-samples)
9. [Testing Guidance](#testing-guidance)

---

# Executive Overview

## What This Application Does

The Intercom Analysis Tool is a multi-agent AI system that:
1. Fetches customer support conversations from Intercom
2. Analyzes sentiment, categorizes topics, and identifies trends
3. Generates executive-ready reports in two formats:
   - **Hilary Format**: Topic-based cards with specific sentiment insights and conversation examples
   - **Synthesis Format**: Cross-category strategic insights with operational metrics
4. Produces Gamma presentations automatically for leadership review

## Primary Users

- **Hilary (Boss)**: Weekly Voice of Customer cards showing what customers are saying about each topic
- **Max (Product Lead)**: Agent performance reviews (Horatio/Boldr), strategic insights, trend analysis  
- **Leadership Team**: Executive summaries with actionable recommendations

## Technology Stack

**Backend:**
- Python 3.11
- FastAPI (web server)
- AsyncIO (concurrent processing)
- DuckDB (embedded analytics database)
- Pydantic (data validation)

**AI/LLM:**
- OpenAI GPT-4o (primary)
- Claude (fallback)
- 5 of 7 agents use LLMs for intelligent analysis

**External APIs:**
- Intercom API (conversation data)
- Canny API (feature requests)
- Gamma API v0.2 (presentation generation)

**Frontend:**
- Vanilla JavaScript (no framework)
- Server-Sent Events (real-time command output)
- Dropdown form interface

**Deployment:**
- Railway.app (production)
- Docker containerized
- Environment variables for API keys

---

# System Architecture

## High-Level Components

```
┌─────────────────────────────────────────────────────────────────┐
│                         WEB UI (Railway)                         │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Dropdown Form (deploy/railway_web.py + static/*.js/css)  │  │
│  │  - Analysis type selector                                 │  │
│  │  - Time period picker                                     │  │
│  │  - Data source selector                                   │  │
│  │  - Output format chooser                                  │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              ↓                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  FastAPI Backend (deploy/railway_web.py)                  │  │
│  │  - /execute/start → Start command                         │  │
│  │  - /execute/status → Poll for updates                     │  │
│  │  - /health → System status                                │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              ↓                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  WebCommandExecutor                                       │  │
│  │  - Spawns Python subprocess                               │  │
│  │  - Streams output via SSE                                 │  │
│  │  - Handles cancellation                                   │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    CLI APPLICATION (src/main.py)                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Click Commands:                                          │  │
│  │  - voice-of-customer                                      │  │
│  │  - agent-performance                                      │  │
│  │  - analyze-billing/api/product/etc                        │  │
│  │  - canny-analysis                                         │  │
│  │  - test-mode                                              │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              ↓                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Data Fetching Layer                                      │  │
│  │  - ChunkedFetcher (Intercom pagination)                   │  │
│  │  - CannyClient (Canny API)                                │  │
│  │  - Timezone conversion (Pacific → UTC)                    │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              ↓                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Multi-Agent Pipeline (7 agents)                          │  │
│  │  - SegmentationAgent                                      │  │
│  │  - TopicDetectionAgent                                    │  │
│  │  - TopicSentimentAgent (per topic)                        │  │
│  │  - ExampleExtractionAgent (per topic)                     │  │
│  │  - FinPerformanceAgent                                    │  │
│  │  - TrendAgent                                             │  │
│  │  - OutputFormatterAgent                                   │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              ↓                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Output Generation                                        │  │
│  │  - Markdown report (Hilary's cards)                       │  │
│  │  - Gamma API call (presentation)                          │  │
│  │  - JSON export (full data)                                │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

# Data Flow

## Complete Request Lifecycle

### 1. User Interaction (Web UI)

**File:** `deploy/railway_web.py` lines 220-294
**File:** `static/app.js` lines 755-817

User fills form:
```
Analysis Type: VoC: Hilary Format (Topic Cards)
Time Period: Yesterday
Data Source: Intercom Only
Filter by Taxonomy: Billing
Output Format: Gamma Presentation
```

JavaScript `runAnalysis()` function builds command:
```javascript
let command = 'voice-of-customer';
let args = ['--multi-agent', '--analysis-type', 'topic-based', 
            '--time-period', 'yesterday', '--generate-gamma'];

executeCommand(command, args);
```

Calls backend:
```javascript
POST /execute/start?command=python&args=["src/main.py","voice-of-customer","--multi-agent",...]
```

---

### 2. Backend Processing (FastAPI)

**File:** `deploy/railway_web.py` lines 619-650

```python
@app.post("/execute/start")
async def start_execution(command: str, args: str):
    # Parse args
    args_list = json.loads(args)  # ["src/main.py", "voice-of-customer", ...]
    
    # Generate execution ID
    execution_id = command_executor.generate_execution_id()
    
    # Create execution state
    execution = await state_manager.create_execution(execution_id, command, args_list)
    
    # Start background task
    asyncio.create_task(run_command_background(execution_id, command, args_list))
    
    return {"execution_id": execution_id, "status": "queued"}
```

WebCommandExecutor spawns subprocess:
```python
process = await asyncio.create_subprocess_exec(
    "python", "src/main.py", "voice-of-customer", "--multi-agent", ...,
    stdout=asyncio.subprocess.PIPE,
    stderr=asyncio.subprocess.PIPE,
    cwd="/app"
)
```

---

### 3. CLI Command Handling

**File:** `src/main.py` lines 2751-2887

```python
@cli.command(name='voice-of-customer')
@click.option('--time-period', ...)
@click.option('--multi-agent', is_flag=True)
@click.option('--analysis-type', type=click.Choice(['topic-based', 'synthesis', 'complete']))
@click.option('--generate-gamma', is_flag=True)
def voice_of_customer_analysis(time_period, ..., multi_agent, analysis_type, generate_gamma, ...):
    # Calculate dates from time_period
    if time_period == 'yesterday':
        start_dt = end_dt - timedelta(days=1)
    
    # Convert to Pacific Time
    from src.utils.timezone_utils import get_date_range_pacific
    start_dt, end_dt = get_date_range_pacific(start_date, end_date)
    
    # Route to appropriate analysis
    if analysis_type == 'topic-based':
        asyncio.run(run_topic_based_analysis_custom(start_dt, end_dt, generate_gamma))
```

---

### 4. Data Fetching (Intercom API)

**File:** `src/services/chunked_fetcher.py`
**File:** `src/services/intercom_service_v2.py`

```python
class ChunkedFetcher:
    async def fetch_conversations_chunked(start_date, end_date):
        # Calculate chunks (max 7 days per chunk)
        if (end_date - start_date).days <= 7:
            return await self._fetch_single_chunk(start_date, end_date)
        else:
            return await self._fetch_daily_chunks(start_date, end_date)
```

```python
class IntercomServiceV2:
    async def fetch_conversations_by_date_range(start_date, end_date):
        # Build query
        query_params = {
            'query': {
                'operator': 'AND',
                'value': [
                    {'field': 'created_at', 'operator': '>=', 
                     'value': int(start_date.timestamp())},
                    {'field': 'created_at', 'operator': '<=', 
                     'value': int(end_date.timestamp())}
                ]
            },
            'pagination': {'per_page': 50}
        }
        
        # Paginate through all results
        while True:
            response = await client.post(f"{base_url}/conversations/search", json=query_params)
            conversations.extend(response.json()['conversations'])
            
            if not response.json().get('pages', {}).get('next'):
                break
            
            # Update pagination cursor
            query_params['pagination']['starting_after'] = response.json()['pages']['next']['starting_after']
        
        return conversations
```

**Typical fetch for "yesterday":**
- 20-22 API calls (50 conversations per page)
- ~1000-1100 conversations total
- ~4-5 minutes fetch time
- Data includes: conversation ID, created_at, customer messages, admin messages, tags, custom attributes, statistics

---

### 5. Multi-Agent Pipeline Execution

**File:** `src/agents/topic_orchestrator.py` lines 67-241

#### Phase 1: Segmentation (0.01 seconds)

```python
segmentation_agent = SegmentationAgent()
result = await segmentation_agent.execute(context)

# Returns:
{
    'paid_customer_conversations': [...],  # Has human support
    'free_customer_conversations': [...],  # Fin AI only
    'agent_distribution': {
        'horatio': X,
        'boldr': X,
        'escalated': X,
        'fin_ai': X,
        'unknown': X
    }
}
```

**Logic:**
```python
def _classify_conversation(conv):
    # Extract admin emails from conversation_parts
    admin_emails = []
    for part in conv['conversation_parts']['conversation_parts']:
        if part['author']['type'] == 'admin':
            admin_emails.append(part['author']['email'].lower())
    
    # Check email domains
    if 'hirehoratio.co' in any(admin_emails):
        return 'paid', 'horatio'
    if 'boldrimpact.com' in any(admin_emails):
        return 'paid', 'boldr'
    
    # Check if escalated
    if any(name in email for name in ['max.jackson', 'dae-ho', 'hilary']):
        return 'paid', 'escalated'
    
    # Check if Fin AI only
    if conv['ai_agent_participated'] and not conv['admin_assignee_id']:
        return 'free', 'fin_ai'
    
    return 'unknown', 'unknown'
```

---

#### Phase 2: Topic Detection (1-3 seconds with LLM)

```python
topic_detection_agent = TopicDetectionAgent()
result = await topic_detection_agent.execute(context)

# Returns:
{
    'topic_distribution': {
        'Billing': {
            'volume': 239,
            'percentage': 23.4,
            'detection_method': 'attribute',  # or 'keyword' or 'llm_semantic'
            'attribute_count': 200,
            'keyword_count': 39
        },
        'Bug': {...},
        'Credits': {...}
    },
    'topics_by_conversation': {
        'conv_12345': [
            {'topic': 'Billing', 'method': 'attribute', 'confidence': 1.0},
            {'topic': 'Credits', 'method': 'keyword', 'confidence': 0.7}
        ]
    }
}
```

**Topic Detection Logic:**

**Step 1: Rule-Based Detection**
```python
# Predefined topics with attributes and keywords
self.topics = {
    "Credits": {
        "attribute": "Credits",  # Intercom custom attribute
        "keywords": ["credit", "credits", "out of credits", "buy credits"]
    },
    "Agent/Buddy": {
        "attribute": None,
        "keywords": ["buddy", "agent", "ai assistant", "copilot"]
    },
    "Billing": {
        "attribute": "Billing",
        "keywords": ["refund", "cancel", "subscription", "payment"]
    }
    # ... 8 total predefined topics
}

# Detection priority:
# 1. Check Intercom conversation attributes (confidence: 1.0)
# 2. Check keyword matches in full_text (confidence: 0.5-0.9)
```

**Step 2: LLM Semantic Discovery**
```python
# Sample 20 conversations
sample = conversations[:20]

prompt = f"""
Analyze these conversations and identify additional topics not in: {predefined_topics}

Conversations:
1. "I want a refund..."
2. "Can't publish my site..."
...

Return JSON array of new topics: ["Topic 1", "Topic 2"]
"""

llm_response = await openai_client.generate(prompt)
# Example response: ["Subscription Cancellation", "Refund Request", "Invoice Request"]

# Add to topic_distribution with method='llm_semantic'
```

**Current Issue:** LLM-discovered topics have `volume: 0` because conversations aren't rescanned to assign them.

---

#### Phase 3: Per-Topic Analysis (5-10 seconds, PARALLEL)

**For EACH detected topic**, run in parallel:

**3A. TopicSentimentAgent** (uses LLM)

```python
# Only analyze conversations tagged with THIS specific topic
topic_conversations = [conv for conv in conversations if topic in conv['detected_topics']]

# Sample 10 for prompt
sample = []
for conv in topic_conversations[:10]:
    sample.append({
        'id': conv['id'],
        'customer_message': conv['customer_messages'][0][:200],
        'rating': conv['conversation_rating']
    })

prompt = f"""
Analyze sentiment for topic: {topic_name}

Sample conversations (showing 10 of {len(topic_conversations)}):
{json.dumps(sample, indent=2)}

Generate ONE SENTENCE that:
1. Captures specific sentiment for THIS topic
2. Shows nuance (e.g., "appreciate X BUT frustrated by Y")
3. Uses natural language
4. Is actionable

Examples of good insights:
- "Users hate buddy so much"
- "Customers appreciate quick resolution BUT frustrated by unexpected charges"

Your insight for {topic_name}:
"""

sentiment_insight = await openai_client.generate(prompt)
# Example: "Customers frustrated with refund delays BUT appreciate when issues are resolved"
```

**3B. ExampleExtractionAgent** (uses LLM)

```python
# Score all conversations for this topic
scored = []
for conv in topic_conversations:
    score = 0
    
    # Has clear customer message (50+ chars): +2
    if len(conv['customer_messages'][0]) >= 50:
        score += 2
    
    # Matches sentiment keywords: +1.5
    if 'frustrated' in sentiment and 'frustrat' in conv['full_text']:
        score += 1.5
    
    # Recent (< 3 days): +1.5
    if (now - conv['created_at']).days <= 3:
        score += 1.5
    
    # Has rating: +1
    if conv['conversation_rating']:
        score += 1
    
    scored.append((score, conv))

# Take top 20 candidates
scored.sort(reverse=True)
candidates = [conv for score, conv in scored if score >= 2.0][:20]

# LLM selects best 7
prompt = f"""
Select most representative examples for {topic}.

Sentiment: {sentiment_insight}

Candidates:
1. "Customer message 1..."
2. "Customer message 2..."
...
20. "Customer message 20..."

Select 7 examples that are:
- Most representative
- Show different aspects
- Specific and actionable
- Professional for executive reports

Return ONLY numbers as JSON array: [1, 3, 7, 12, 15, 18, 20]
"""

selected_numbers = json.loads(await openai_client.generate(prompt))
# Example: [1, 3, 5, 6, 8, 10, 19]

selected_conversations = [candidates[num-1] for num in selected_numbers]

# Format examples
examples = []
for conv in selected_conversations:
    examples.append({
        'preview': conv['customer_messages'][0][:80] + "...",
        'intercom_url': f"https://app.intercom.com/a/inbox/inbox/{conv['id']}",
        'conversation_id': conv['id'],
        'created_at': datetime.fromtimestamp(conv['created_at']).isoformat()
    })
```

**Parallelization:**
```python
# All topics process simultaneously
async def process_topic(topic_name):
    sentiment = await sentiment_agent.execute()  # 2-3 seconds
    examples = await example_agent.execute()     # 2-3 seconds
    return sentiment, examples

# 9 topics × max(5s) = 5 seconds total (not 45 seconds)
results = await asyncio.gather(*[process_topic(name) for name in topics])
```

---

#### Phase 4: Fin Performance Analysis (6-8 seconds with LLM)

```python
fin_performance_agent = FinPerformanceAgent()

# Calculate metrics
fin_conversations = [conv for conv in conversations 
                     if conv['ai_agent_participated'] and not conv['admin_assignee_id']]

# Resolution rate
escalation_phrases = ['speak to human', 'talk to agent', 'real person']
resolved = [c for c in fin_conversations 
           if not any(phrase in c['full_text'].lower() for phrase in escalation_phrases)]
resolution_rate = len(resolved) / len(fin_conversations)

# Knowledge gaps
gap_phrases = ['incorrect', 'wrong', 'not helpful', "didn't answer"]
knowledge_gaps = [c for c in fin_conversations 
                 if any(phrase in c['full_text'].lower() for phrase in gap_phrases)]

# Performance by topic
topic_performance = {}
for conv in fin_conversations:
    topic = conv['detected_topics'][0]
    topic_performance[topic]['total'] += 1
    if conv in resolved:
        topic_performance[topic]['resolved'] += 1

# LLM insights
prompt = f"""
Analyze Fin AI performance:

Metrics:
- Total: {len(fin_conversations)}
- Resolution rate: {resolution_rate:.1%}
- Knowledge gaps: {len(knowledge_gaps)}

Top topics: {top_3_topics}
Struggling topics: {bottom_3_topics}

Provide 2-3 specific, actionable insights (150 words, professional tone)
"""

llm_insights = await openai_client.generate(prompt)
# Example: "Fin excels at account setup (78% resolution) but struggles with billing edge cases (62%). Knowledge gaps primarily in refund policies and subscription changes. Recommend expanding billing documentation and adding common refund scenarios to Fin's training data."
```

**Output:**
```python
{
    'total_fin_conversations': 159,
    'resolution_rate': 1.0,
    'knowledge_gaps_count': 0,
    'performance_by_topic': {
        'Account': {'total': 80, 'resolution_rate': 0.78},
        'Billing': {'total': 50, 'resolution_rate': 0.62}
    },
    'llm_insights': "Fin excels at..."
}
```

---

#### Phase 5: Trend Analysis (0-5 seconds with LLM if trends exist)

```python
trend_agent = TrendAgent(historical_data_dir="outputs/weekly_history")

# Load previous weeks
historical_data = []
for file in Path("outputs/weekly_history").glob("week_*.json"):
    historical_data.append(json.load(file))

if not historical_data:
    # First run - establish baseline
    self._save_week_data(week_id, current_results)
    return {'note': 'First analysis - establishing baseline'}

# Calculate trends
previous_week = historical_data[-1]['results']
trends = {}

for topic in current_topics:
    current_vol = current_topics[topic]['volume']
    previous_vol = previous_topics[topic]['volume']
    
    pct_change = ((current_vol - previous_vol) / previous_vol) * 100
    
    trends[topic] = {
        'volume_change': pct_change,
        'direction': '↑' if pct_change > 5 else '↓' if pct_change < -5 else '→',
        'alert': '🚨' if abs(pct_change) > 20 else ''
    }

# LLM explains WHY (only for significant changes)
for topic, trend in trends.items():
    if abs(trend['volume_change']) >= 10:
        prompt = f"""
Why did {topic} change {trend['volume_change']:+.1f}%?

Current sentiment: {current_sentiments[topic]}

Provide ONE sentence explanation considering:
- Product changes
- User behavior patterns  
- Seasonal factors
- Issues escalating

Example: "Agent/Buddy volume up 23% likely due to recent editing feature launch causing confusion"
"""
        
        explanation = await openai_client.generate(prompt)
        trend['explanation'] = explanation
```

**Output:**
```python
{
    'trends': {
        'Billing': {
            'volume_change': 12.3,
            'direction': '↑',
            'alert': '',
            'explanation': "Billing inquiries increased due to quarterly subscription renewals"
        },
        'Agent/Buddy': {
            'volume_change': 23.7,
            'direction': '↑',
            'alert': '🚨',
            'explanation': "Spike in complaints likely from recent Buddy editing update"
        }
    },
    'historical_weeks_available': 3
}
```

---

#### Phase 6: Output Formatting (0.01 seconds)

```python
output_formatter_agent = OutputFormatterAgent()

# Build Hilary's card structure
formatted_output = []

for topic_name, topic_stats in sorted_topics:
    sentiment = topic_sentiments[topic_name]['sentiment_insight']
    examples = topic_examples[topic_name]['examples']
    trend = trends.get(topic_name, {})
    
    card = f"""### {topic_name} {trend['direction']} {trend['alert']}
**{topic_stats['volume']} tickets / {topic_stats['percentage']}% of weekly volume**
**Detection Method**: {topic_stats['detection_method']}

**Sentiment**: {sentiment}

**Trend Analysis**: {trend['explanation']}

**Examples**:
1. "{examples[0]['preview']}" - [View conversation]({examples[0]['intercom_url']})
2. "{examples[1]['preview']}" - [View conversation]({examples[1]['intercom_url']})
...

---
"""
    formatted_output.append(card)

# Add Fin section
fin_card = f"""## Fin AI Performance

**{fin_data['total']} conversations handled by Fin**

**AI Performance Insights**:
{fin_data['llm_insights']}

**Resolution rate**: {fin_data['resolution_rate']:.1%}
...
"""
formatted_output.append(fin_card)

return '\\n'.join(formatted_output)
```

**Output saved to:** `outputs/topic_based_2025-W42_timestamp.md`

---

### 6. Gamma Presentation Generation (30-120 seconds)

**File:** `src/main.py` lines 2963-3022

```python
if generate_gamma:
    from src.services.gamma_client import GammaClient
    
    gamma_client = GammaClient()
    markdown_report = results['formatted_report']
    
    # Call Gamma API v0.2
    generation_id = await gamma_client.generate_presentation(
        input_text=markdown_report,
        format="presentation",
        text_mode="preserve",            # Keep our exact text
        card_split="inputTextBreaks",    # Use --- breaks for slides
        theme_name="Night Sky",          # Professional theme
        text_options={
            "tone": "professional, analytical",
            "audience": "executives, leadership team"
        }
    )
    
    # Poll for completion (max 2 minutes)
    for attempt in range(24):
        await asyncio.sleep(5)
        status = await gamma_client.get_generation_status(generation_id)
        
        if status['status'] == 'completed':
            gamma_url = status['url']
            print(f"✅ Gamma URL: {gamma_url}")
            
            # Save URL
            with open(f"outputs/gamma_url_{timestamp}.txt", 'w') as f:
                f.write(gamma_url)
            break
    
    if attempt >= 24:
        print("⚠️ Gamma timed out - check dashboard")
```

**Gamma API Request:**
```json
{
  "inputText": "# Voice of Customer Analysis - Week 2025-W42\n\n## Customer Topics\n\n### Billing\n**239 tickets / 23%**...",
  "format": "presentation",
  "textMode": "preserve",
  "cardSplit": "inputTextBreaks",
  "themeName": "Night Sky",
  "textOptions": {
    "tone": "professional, analytical",
    "audience": "executives, leadership team"
  }
}
```

**Expected Response:**
```json
{
  "generationId": "abc123xyz",
  "status": "pending"
}
```

**Poll Response:**
```json
{
  "generationId": "abc123xyz",
  "status": "completed",
  "gammaUrl": "https://gamma.app/docs/xyz123",
  "credits": {"deducted": 150, "remaining": 2850}
}
```

---

# Multi-Agent System Deep Dive

## Agent 1: SegmentationAgent

**File:** `src/agents/segmentation_agent.py`  
**Purpose:** Separate paid customers (human support) from free customers (Fin AI only)  
**Uses LLM:** ❌ No (rule-based for speed)  
**Execution Time:** ~0.01 seconds

**Input:**
```python
context = AgentContext(
    analysis_id="weekly_2025-W42",
    analysis_type="weekly_voc",
    start_date=datetime(2025, 10, 21),
    end_date=datetime(2025, 10, 21),
    conversations=[...],  # 1073 conversations
    metadata={'week_id': '2025-W42'}
)
```

**Processing:**
```python
for conv in conversations:
    # Extract admin emails from conversation_parts
    admin_emails = []
    for part in conv.get('conversation_parts', {}).get('conversation_parts', []):
        if part.get('author', {}).get('type') == 'admin':
            email = part.get('author', {}).get('email', '')
            if email:
                admin_emails.append(email.lower())
    
    # Classify based on email domains
    if 'hirehoratio.co' in ' '.join(admin_emails):
        agent_type = 'horatio'
        segment = 'paid'
    elif 'boldrimpact.com' in ' '.join(admin_emails):
        agent_type = 'boldr'
        segment = 'paid'
    elif any(name in email for email in admin_emails for name in ['max.jackson', 'dae-ho', 'hilary']):
        agent_type = 'escalated'
        segment = 'paid'
    elif conv['ai_agent_participated'] and not conv['admin_assignee_id']:
        agent_type = 'fin_ai'
        segment = 'free'
    else:
        agent_type = 'unknown'
        segment = 'paid' if conv['admin_assignee_id'] else 'unknown'
```

**Output:**
```python
AgentResult(
    agent_name="SegmentationAgent",
    success=True,
    data={
        'paid_customer_conversations': [conv1, conv2, ...],  # 906 conversations
        'free_customer_conversations': [conv50, conv51, ...],  # 159 conversations
        'unknown_tier': [conv100, ...],  # 8 conversations
        'agent_distribution': {
            'horatio': 654,  # ← Should be > 0, currently 0 (BUG)
            'boldr': 0,
            'escalated': 12,
            'fin_ai': 159,
            'unknown': 240
        },
        'segmentation_summary': {
            'paid_count': 906,
            'paid_percentage': 84.4,
            'free_count': 159,
            'free_percentage': 14.8
        }
    },
    confidence=0.99,
    execution_time=0.01
)
```

**Known Issue:** Horatio count is 0 despite Horatio handling conversations. Email extraction may be failing.

---

## Agent 2: TopicDetectionAgent

**File:** `src/agents/topic_detection_agent.py`  
**Purpose:** Detect topics via Intercom attributes, keywords, and LLM semantic analysis  
**Uses LLM:** ✅ Yes (for semantic discovery)  
**Execution Time:** ~1-3 seconds

**Predefined Topics:**
```python
self.topics = {
    "Credits": {
        "attribute": "Credits",
        "keywords": ["credit", "credits", "out of credits", "buy credits", "credit model"],
        "priority": 1
    },
    "Agent/Buddy": {
        "attribute": None,
        "keywords": ["buddy", "agent", "ai assistant", "copilot", "editing"],
        "priority": 1
    },
    "Workspace Templates": {
        "attribute": "Workspace Templates",
        "keywords": ["template", "workspace template", "starting point"],
        "priority": 1
    },
    "Billing": {
        "attribute": "Billing",
        "keywords": ["refund", "cancel", "subscription", "payment", "invoice"],
        "priority": 2
    },
    "Bug": {
        "attribute": "Bug",
        "keywords": ["bug", "broken", "not working", "error", "crash"],
        "priority": 2
    },
    "Account": {
        "attribute": "Account",
        "keywords": ["account", "login", "password", "email change"],
        "priority": 3
    },
    "API": {
        "attribute": "API",
        "keywords": ["api", "integration", "webhook", "developer"],
        "priority": 3
    },
    "Product Question": {
        "attribute": "Product Question",
        "keywords": ["how to", "how do i", "question"],
        "priority": 4
    }
}
```

**Detection Process:**
```python
for conv in conversations:
    detected_topics = []
    
    # Check 1: Intercom custom attributes (highest confidence)
    attributes = conv.get('custom_attributes', {})
    for topic_name, config in self.topics.items():
        if config['attribute'] and config['attribute'] in attributes:
            detected_topics.append({
                'topic': topic_name,
                'method': 'attribute',
                'confidence': 1.0
            })
            continue  # Skip keyword check if attribute matched
    
    # Check 2: Keyword matching
    text = conv.get('full_text', '').lower()
    for topic_name, config in self.topics.items():
        keyword_matches = sum(1 for kw in config['keywords'] if kw in text)
        if keyword_matches > 0:
            confidence = min(0.9, 0.5 + (keyword_matches * 0.15))
            detected_topics.append({
                'topic': topic_name,
                'method': 'keyword',
                'confidence': confidence
            })
    
    topics_by_conversation[conv['id']] = detected_topics

# Check 3: LLM semantic discovery
llm_topics = await self._enhance_with_llm(conversations, topic_distribution)
# Adds: {"Subscription Cancellation": {...}, "Refund Request": {...}}
```

**Output:**
```python
AgentResult(
    data={
        'topic_distribution': {
            'Billing': {
                'volume': 239,
                'percentage': 23.4,
                'detection_method': 'attribute',
                'attribute_count': 200,
                'keyword_count': 39
            },
            'Bug': {'volume': 14, ...},
            'Credits': {'volume': 3, ...},
            'Subscription Cancellation': {  # LLM-discovered
                'volume': 0,  # ← BUG: Not rescanned
                'detection_method': 'llm_semantic',
                'llm_discovered': True
            }
        },
        'total_conversations': 906,
        'conversations_with_topics': 304,
        'conversations_without_topics': 602
    },
    execution_time=1.66
)
```

**Known Issues:**
1. LLM topics have volume=0 (not rescanned)
2. Only 33% topic coverage (66% unclassified)
3. Empty topics still get analyzed (waste)

---

## Agent 3: TopicSentimentAgent

**File:** `src/agents/topic_sentiment_agent.py`  
**Purpose:** Generate specific, nuanced sentiment insight for ONE topic  
**Uses LLM:** ✅ Yes (GPT-4o, temp=0.6)  
**Execution Time:** ~2-3 seconds per topic  
**Runs:** Once per topic (9 topics = 9 calls in parallel)

**Input:**
```python
context.metadata = {
    'current_topic': 'Billing',
    'topic_conversations': [conv1, conv2, ...],  # 239 conversations
    'sentiment_insight': ''
}
```

**Prompt Template:**
```
CRITICAL HALLUCINATION PREVENTION RULES:
1. You are FORBIDDEN from inventing data
2. If unsure, state "I cannot verify this information"
3. Only use provided conversation data
4. Never fabricate conversation IDs, URLs, or statistics

TOPIC SENTIMENT RULES:
1. Generate ONE-SENTENCE insight that is:
   - Specific to THIS topic
   - Nuanced (show complexity: "appreciate X BUT frustrated by Y")
   - Actionable
   - Natural language

GOOD EXAMPLES:
✓ "Users hate buddy so much"
✓ "Customers appreciate quick resolution BUT frustrated by unexpected charges"
✓ "Users think templates are rad but want API access"

BAD EXAMPLES:
✗ "Negative sentiment detected"
✗ "Users are frustrated"  
✗ "Mixed sentiment"

Analyze sentiment for: Billing

You have 239 conversations tagged with this topic.

Sample conversations (showing 10 of 239):
[
  {
    "id": "215471377705486",
    "customer_message": "I want a refund for my subscription. I was charged but didn't use the service.",
    "rating": null
  },
  {
    "id": "215471376230298",
    "customer_message": "Quero pedir reembolso desse plano, já fiz o Cancelamento",
    "rating": null
  },
  ...
]

Your insight for Billing:
```

**Actual LLM Response Examples:**
- ✅ Good: "Customers frustrated with unexpected charges BUT appreciate prompt refund process"
- ✅ Good: "Customers appreciate quick resolution BUT are frustrated by refund delays"
- ⚠️ Mediocre: "Users are frustrated with persistent bugs preventing website publishing" (triggers warning)
- ❌ Bad: "This information is not available in the provided dataset" (empty topic)

**Output:**
```python
AgentResult(
    data={
        'topic': 'Billing',
        'sentiment_insight': "Customers frustrated with unexpected charges BUT appreciate prompt refunds",
        'conversation_count': 239,
        'sample_quotes': ["I want a refund...", "Why was I charged..."]
    },
    confidence=1.0,
    confidence_level='HIGH',
    execution_time=2.1,
    token_count=~800
)
```

---

## Agent 4: ExampleExtractionAgent

**File:** `src/agents/example_extraction_agent.py`  
**Purpose:** Select 3-10 most representative conversation examples  
**Uses LLM:** ✅ Yes (GPT-4o, temp=0.3)  
**Execution Time:** ~2-3 seconds per topic  
**Runs:** Once per topic in parallel

**Input:**
```python
context.metadata = {
    'current_topic': 'Billing',
    'topic_conversations': [...],  # 239 conversations
    'sentiment_insight': "Customers frustrated with charges BUT appreciate refunds"
}
```

**Step 1: Rule-Based Scoring**
```python
for conv in topic_conversations:
    score = 0.0
    
    # Has clear customer message (50+ chars)
    customer_msgs = conv.get('customer_messages', [])
    if customer_msgs and len(customer_msgs[0]) >= 50:
        score += 2.0
    
    # Matches sentiment keywords
    text = conv['full_text'].lower()
    if 'frustrated' in sentiment and 'frustrat' in text:
        score += 1.5
    if 'appreciate' in sentiment and any(word in text for word in ['thank', 'appreciate']):
        score += 1.5
    
    # Recent conversation (< 3 days old)
    created_at = datetime.fromtimestamp(conv['created_at'])
    if (datetime.now() - created_at).days <= 3:
        score += 1.5
    
    # Has conversation rating
    if conv['conversation_rating']:
        score += 1.0
    
    scored_conversations.append((score, conv))

# Sort and take top 20 candidates
scored_conversations.sort(reverse=True)
candidates = [conv for score, conv in scored_conversations if score >= 2.0][:20]
```

**Step 2: LLM Selection**
```python
# Build prompt with top candidates
prompt = f"""
Select most representative examples for {topic}.

Sentiment: {sentiment_insight}

Candidates:
1. "I want a refund for my subscription..."
2. "Why was I charged £75 when I cancelled..."
3. "Can I get a refund? I'm frustrated..."
...
20. "Subscription cancellation request"

Instructions:
1. Select 7 examples that are:
   - Most representative (clearly demonstrate sentiment)
   - Show different aspects
   - Specific and actionable
   - Professional for executive reports

2. Return ONLY numbers as JSON array: [1, 3, 7, 12, 15, 18, 20]

Selected example numbers:
"""

llm_response = await openai_client.generate(prompt)
# Example: "[1, 3, 5, 6, 8, 10, 19]"

selected_numbers = json.loads(extract_json_array(llm_response))
selected_conversations = [candidates[num-1] for num in selected_numbers]
```

**Step 3: Format Examples**
```python
examples = []
for conv in selected_conversations:
    # Handle created_at (can be int timestamp or datetime)
    created_at = conv['created_at']
    if isinstance(created_at, (int, float)):
        created_at_str = datetime.fromtimestamp(created_at).isoformat()
    else:
        created_at_str = created_at.isoformat()
    
    examples.append({
        'preview': conv['customer_messages'][0][:80] + "...",
        'intercom_url': f"https://app.intercom.com/a/inbox/inbox/{conv['id']}",
        'conversation_id': conv['id'],
        'created_at': created_at_str
    })
```

**Output:**
```python
AgentResult(
    data={
        'topic': 'Billing',
        'examples': [
            {
                'preview': "I want a refund for my subscription. I was charged but didn't use...",
                'intercom_url': "https://app.intercom.com/a/inbox/inbox/215471377705486",
                'conversation_id': "215471377705486",
                'created_at': "2025-10-21T14:23:45"
            },
            # ... 6 more examples
        ],
        'total_available': 239,
        'selected_count': 7
    },
    execution_time=2.3
)
```

**Known Issue:** Sometimes returns 0 examples despite LLM selecting 7. Timestamp conversion was crashing (fixed in commit 4e24f46).

---

## Agent 5: FinPerformanceAgent

**File:** `src/agents/fin_performance_agent.py`  
**Purpose:** Analyze Fin AI's performance on free-tier customers  
**Uses LLM:** ✅ Yes (GPT-4o, temp=0.4)  
**Execution Time:** ~6-8 seconds

**Input:**
```python
context.metadata = {
    'fin_conversations': [...]  # 159 Fin-only conversations
}
```

**Metrics Calculation:**
```python
# Resolution rate (no human escalation requested)
escalation_phrases = ['speak to human', 'talk to agent', 'real person', 'human support']
resolved_by_fin = []
for conv in fin_conversations:
    text = conv['full_text'].lower()
    if not any(phrase in text for phrase in escalation_phrases):
        resolved_by_fin.append(conv)

resolution_rate = len(resolved_by_fin) / len(fin_conversations)

# Knowledge gaps (incorrect answers)
gap_phrases = ['incorrect', 'wrong', 'not helpful', "didn't answer", 'not what i asked']
knowledge_gaps = []
for conv in fin_conversations:
    if any(phrase in conv['full_text'].lower() for phrase in gap_phrases):
        knowledge_gaps.append(conv)

# Performance by topic
topic_performance = defaultdict(lambda: {'total': 0, 'resolved': 0})
for conv in fin_conversations:
    topics = conv.get('detected_topics', ['Other'])
    resolved = conv in resolved_by_fin
    
    for topic in topics:
        topic_performance[topic]['total'] += 1
        if resolved:
            topic_performance[topic]['resolved'] += 1

# Calculate rates
for topic, stats in topic_performance.items():
    if stats['total'] >= 5:  # Min 5 conversations for meaningful rate
        stats['resolution_rate'] = stats['resolved'] / stats['total']
```

**LLM Insights Generation:**
```python
top_topics = sorted(topic_performance.items(), 
                   key=lambda x: x[1]['resolution_rate'], reverse=True)[:3]
struggling = sorted(topic_performance.items(), 
                   key=lambda x: x[1]['resolution_rate'])[:3]

prompt = f"""
Analyze Fin AI's performance:

Metrics:
- Total: {len(fin_conversations)}
- Resolution rate: {resolution_rate:.1%}
- Knowledge gaps: {len(knowledge_gaps)}

Top performing: Account (78%), Product (72%), ...
Struggling: Billing (62%), Bug (31%), ...

Instructions:
1. Provide 2-3 specific insights
2. Analytical and data-driven
3. Explain WHY Fin struggles/excels
4. Suggest improvements
5. Professional executive tone, 150 words max

Insights:
"""

llm_insights = await openai_client.generate(prompt)
```

**Example LLM Response:**
"Fin demonstrates strong performance on routine account questions (78% resolution) and product inquiries (72%), suggesting effective training on standard workflows. However, billing scenarios show lower resolution (62%), likely due to the complexity of refund policies and subscription edge cases. The 31% resolution rate on bug reports indicates users prefer human validation for technical issues. Recommend: 1) Expand Fin's billing knowledge base with common refund scenarios, 2) Add confidence thresholds to auto-escalate complex billing cases, 3) Keep bug reports routed to humans as users value technical expertise verification."

**Output:**
```python
{
    'total_fin_conversations': 159,
    'resolution_rate': 1.0,
    'resolved_count': 159,
    'knowledge_gaps_count': 0,
    'performance_by_topic': {
        'Account': {'total': 80, 'resolution_rate': 0.78},
        'Billing': {'total': 50, 'resolution_rate': 0.62}
    },
    'top_performing_topics': [('Account', 0.78), ('Product', 0.72)],
    'struggling_topics': [('Bug', 0.31), ('Billing', 0.62)],
    'llm_insights': "Fin demonstrates strong..."
}
```

---

## Agent 6: TrendAgent

**File:** `src/agents/trend_agent.py`  
**Purpose:** Week-over-week trend analysis with LLM explanations  
**Uses LLM:** ✅ Yes (GPT-4o, temp=0.5)  
**Execution Time:** 0 seconds (first run), 2-5 seconds (with trends)  
**Historical Data:** Stored in `outputs/weekly_history/week_*.json`

**First Run (No Historical Data):**
```python
historical_data = self._load_historical_data()  # Returns []

if not historical_data:
    result = {
        'trends': {},
        'note': 'First analysis - establishing baseline. Trends available next week.',
        'historical_weeks_available': 0
    }
    
    # Save current week for future comparison
    self._save_week_data('2025-W42', current_week_results)
    return result
```

**Subsequent Runs (With Historical Data):**
```python
previous_week = historical_data[-1]['results']  # Most recent week

trends = {}
for topic in current_topics:
    current_vol = current_topics[topic]['volume']
    previous_vol = previous_topics.get(topic, {}).get('volume', 0)
    
    if previous_vol > 0:
        pct_change = ((current_vol - previous_vol) / previous_vol) * 100
        
        trends[topic] = {
            'volume_change': pct_change,
            'direction': '↑' if pct_change > 5 else '↓' if pct_change < -5 else '→',
            'alert': '🚨' if abs(pct_change) > 20 else '',
            'current_volume': current_vol,
            'previous_volume': previous_vol
        }

# LLM explains significant trends
for topic, trend in trends.items():
    if abs(trend['volume_change']) >= 10:  # Only explain significant changes
        current_sentiment = current_week_results['topic_sentiments'][topic]
        
        prompt = f"""
Explain WHY {topic} changed {trend['volume_change']:+.1f}%

Current sentiment: {current_sentiment}

ONE sentence explanation considering:
- Product changes
- User patterns
- Seasonal factors
- Issues escalating

Example: "Agent/Buddy volume up 23% likely due to recent editing feature launch"

Explanation:
"""
        
        explanation = await openai_client.generate(prompt)
        trend['explanation'] = explanation
```

**Output:**
```python
{
    'trends': {
        'Billing': {
            'volume_change': 12.3,
            'direction': '↑',
            'current_volume': 239,
            'previous_volume': 213,
            'explanation': "Billing inquiries increased due to monthly subscription renewals"
        }
    },
    'historical_weeks_available': 3,
    'comparison_week': '2025-W41'
}
```

---

## Agent 7: OutputFormatterAgent

**File:** `src/agents/output_formatter_agent.py`  
**Purpose:** Format all agent outputs into Hilary's exact card structure  
**Uses LLM:** ❌ No (just formatting)  
**Execution Time:** ~0.01 seconds

**Input (from previous agents):**
```python
context.previous_results = {
    'SegmentationAgent': {...},
    'TopicDetectionAgent': {
        'data': {
            'topic_distribution': {...}
        }
    },
    'TopicSentiments': {
        'Billing': {
            'data': {
                'sentiment_insight': "Customers frustrated..."
            }
        }
    },
    'TopicExamples': {
        'Billing': {
            'data': {
                'examples': [...]
            }
        }
    },
    'FinPerformanceAgent': {...},
    'TrendAgent': {...}
}
```

**Formatting Logic:**
```python
output_sections = []

# Header
output_sections.append(f"# Voice of Customer Analysis - Week {week_id}")
output_sections.append("")

# Voice of Customer section
output_sections.append("## Customer Topics (Paid Tier - Human Support)")
output_sections.append("")

# Sort topics by volume
sorted_topics = sorted(topic_dist.items(), key=lambda x: x[1]['volume'], reverse=True)

for topic_name, topic_stats in sorted_topics:
    sentiment = topic_sentiments[topic_name]['data']['sentiment_insight']
    examples = topic_examples[topic_name]['data']['examples']
    trend = trends.get(topic_name, {})
    trend_explanation = trend_insights.get(topic_name, '')
    
    # Build card
    card = f"""### {topic_name} {trend['direction']} {trend['alert']}
**{topic_stats['volume']} tickets / {topic_stats['percentage']}% of weekly volume**
**Detection Method**: {topic_stats['detection_method']}

**Sentiment**: {sentiment}

**Trend Analysis**: {trend_explanation}

**Examples**:
1. "{examples[0]['preview']}" - [View]({examples[0]['intercom_url']})
2. "{examples[1]['preview']}" - [View]({examples[1]['intercom_url']})
...

---
"""
    output_sections.append(card)

# Fin section
fin_card = f"""## Fin AI Performance

**{fin_data['total']} conversations handled by Fin**

**AI Performance Insights**:
{fin_data['llm_insights']}

**Resolution rate**: {fin_data['resolution_rate']:.1%}
...
"""
output_sections.append(fin_card)

formatted_output = '\\n'.join(output_sections)
```

**Output:**
```python
{
    'formatted_output': "# Voice of Customer Analysis - Week 2025-W42\n\n## Customer Topics...",
    'total_topics': 7,
    'week_id': '2025-W42',
    'has_trend_data': False
}
```

---

# API Integrations

## 1. Intercom API

**Client:** `src/services/intercom_service_v2.py`  
**Base URL:** `https://api.intercom.io`  
**API Version:** `2.11`  
**Authentication:** Bearer token in `INTERCOM_ACCESS_TOKEN`

**Primary Endpoint Used:**
```
POST /conversations/search
```

**Request Body:**
```json
{
  "query": {
    "operator": "AND",
    "value": [
      {
        "field": "created_at",
        "operator": ">=",
        "value": 1760920800
      },
      {
        "field": "created_at",
        "operator": "<=",
        "value": 1761007199
      }
    ]
  },
  "pagination": {
    "per_page": 50,
    "starting_after": "cursor_xyz..."
  }
}
```

**Response Structure:**
```json
{
  "type": "list",
  "conversations": [
    {
      "type": "conversation",
      "id": "215471377705486",
      "created_at": 1760998808,
      "updated_at": 1761091004,
      "state": "closed",
      "admin_assignee_id": 7885880,
      "conversation_parts": {
        "type": "conversation_part.list",
        "conversation_parts": [
          {
            "type": "conversation_part",
            "author": {
              "type": "admin",
              "id": "7885880",
              "name": "Max Jackson",
              "email": "max.jackson@gamma.app"
            },
            "body": "..."
          }
        ]
      },
      "custom_attributes": {
        "Billing": true,
        "Language": "en"
      },
      "tags": {
        "type": "tag.list",
        "tags": [
          {"type": "tag", "name": "Billing"}
        ]
      },
      "statistics": {
        "time_to_admin_reply": 3600,
        "handling_time": 7200,
        "count_conversation_parts": 5,
        "count_reopens": 0
      },
      "ai_agent_participated": false
    }
  ],
  "pages": {
    "next": {
      "starting_after": "cursor_abc123..."
    }
  }
}
```

**Fields We Extract:**
- `id` - Conversation identifier
- `created_at` - Unix timestamp
- `updated_at` - Unix timestamp
- `state` - open/closed/snoozed
- `admin_assignee_id` - Which admin handled it
- `conversation_parts` - All messages (customer + admin)
- `custom_attributes` - Hilary's metadata tags
- `tags` - Manual tags
- `statistics.time_to_admin_reply` - Response time
- `statistics.handling_time` - Agent time spent
- `statistics.count_conversation_parts` - Message count
- `statistics.count_reopens` - FCR indicator
- `ai_agent_participated` - Fin involvement

**Rate Limiting:**
- Intercom: 500 requests/minute
- We make: ~20-50 requests per analysis (pagination)
- Delay: 10-12 seconds per page (with processing)

---

## 2. OpenAI API

**Client:** `src/services/openai_client.py`  
**Models Used:**
- `gpt-4o` - TopicSentimentAgent, ExampleExtractionAgent, FinPerformanceAgent, TrendAgent
- `gpt-4o-mini` - TopicDetectionAgent (cheaper for discovery)

**Typical Request:**
```python
async def generate_analysis(prompt: str, model="gpt-4o", temperature=0.3):
    response = await openai.ChatCompletion.acreate(
        model=model,
        messages=[
            {"role": "system", "content": "You are an expert VoC analyst..."},
            {"role": "user", "content": prompt}
        ],
        temperature=temperature,
        max_tokens=500
    )
    return response.choices[0].message.content
```

**LLM Calls Per Analysis:**
- TopicDetectionAgent: 1 call (semantic discovery)
- TopicSentimentAgent: N calls (N = number of topics, e.g., 7)
- ExampleExtractionAgent: N calls (parallel with sentiment)
- FinPerformanceAgent: 1 call (insights)
- TrendAgent: 0-N calls (only significant trends)

**Total for typical run:** ~15-20 LLM calls
**Cost estimate:** ~$0.50-1.00 per analysis (assuming GPT-4o pricing)

---

## 3. Gamma API

**Client:** `src/services/gamma_client.py`  
**Base URL:** `https://public-api.gamma.app/v0.2`  
**Authentication:** `X-API-KEY` header with `GAMMA_API_KEY`  
**Documentation:** https://developers.gamma.app/docs/how-does-the-generations-api-work

**Generation Request:**
```python
POST /v0.2/generations

{
  "inputText": "# Voice of Customer Analysis...\n\n### Billing\n**239 tickets**...",
  "format": "presentation",
  "textMode": "preserve",
  "cardSplit": "inputTextBreaks",
  "themeName": "Night Sky",
  "numCards": 15,
  "textOptions": {
    "tone": "professional, analytical",
    "audience": "executives, leadership team",
    "language": "en"
  },
  "imageOptions": {
    "source": "aiGenerated"
  }
}
```

**Response:**
```json
{
  "generationId": "abc123xyz"
}
```

**Status Polling:**
```python
GET /v0.2/generations/{generationId}

# Pending:
{"status": "pending", "generationId": "abc123xyz"}

# Completed:
{
  "status": "completed",
  "generationId": "abc123xyz",
  "gammaUrl": "https://gamma.app/docs/xyz123",
  "credits": {"deducted": 150, "remaining": 2700}
}

# Failed:
{"status": "failed", "error": "..."}
```

**Current Implementation:**
```python
generation_id = await gamma_client.generate_presentation(
    input_text=markdown_report,  # Our multi-agent output
    text_mode="preserve",         # Don't rewrite our content
    card_split="inputTextBreaks", # Each --- becomes a slide
    theme_name="Night Sky"
)

# Poll every 5 seconds, max 2 minutes
for attempt in range(24):
    await asyncio.sleep(5)
    status = await gamma_client.get_generation_status(generation_id)
    
    if status['status'] == 'completed':
        return status['gammaUrl']
```

**Known Issues:**
- Previous validation errors (may be fixed)
- Timeout handling unclear
- Error messages not surfaced to UI

---

## 4. Canny API

**Client:** `src/services/canny_client.py`  
**Purpose:** Fetch feature requests and feedback  
**Status:** ❓ Implemented but untested

**Import Path Issue:**
```python
# Line 2463 in src/main.py:
from services.gamma_generator import GammaGenerator  # ❌ WRONG

# Should be:
from src.services.gamma_generator import GammaGenerator  # ✅ FIXED in latest commit
```

**Endpoints:**
- GET /boards - List boards
- GET /posts - Fetch posts
- GET /posts/{id}/comments - Fetch comments
- GET /posts/{id}/votes - Fetch votes

**Currently Unknown:**
- Does authentication work?
- Are posts properly fetched?
- Does sentiment analysis run?
- Does Gamma generation work for Canny?

---

# User Interface

## Web UI Components

### Dropdown Form (`deploy/railway_web.py` lines 225-293)

**HTML Structure:**
```html
<div class="analysis-form">
    <h2>Configure Analysis</h2>
    
    <label>Analysis Type:</label>
    <select id="analysisType">
        <optgroup label="Voice of Customer">
            <option value="voice-of-customer-hilary" selected>VoC: Hilary Format</option>
            <option value="voice-of-customer-synthesis">VoC: Synthesis</option>
            <option value="voice-of-customer-complete">VoC: Complete</option>
        </optgroup>
        <optgroup label="Category Deep Dives">
            <option value="analyze-billing">Billing Analysis</option>
            <option value="analyze-product">Product Feedback</option>
            <option value="analyze-api">API Issues</option>
            <option value="analyze-escalations">Escalations</option>
            <option value="tech-analysis">Technical</option>
        </optgroup>
        <optgroup label="Combined Analysis">
            <option value="analyze-all-categories">All Categories</option>
        </optgroup>
        <optgroup label="Agent Performance">
            <option value="agent-performance-horatio">Horatio Review</option>
            <option value="agent-performance-boldr">Boldr Review</option>
        </optgroup>
        <optgroup label="Other Sources">
            <option value="canny-analysis">Canny Feedback</option>
        </optgroup>
    </select>
    
    <label>Time Period:</label>
    <select id="timePeriod">
        <option value="yesterday">Yesterday (fast)</option>
        <option value="week" selected>Last Week</option>
        <option value="month">Last Month</option>
        <option value="custom">Custom Date Range</option>
    </select>
    
    <div id="customDateInputs" style="display:none;">
        <label>Start: <input type="date" id="startDate"></label>
        <label>End: <input type="date" id="endDate"></label>
    </div>
    
    <label>Data Source:</label>
    <select id="dataSource">
        <option value="intercom" selected>Intercom Only</option>
        <option value="canny">Canny Only</option>
        <option value="both">Both</option>
    </select>
    
    <label>Filter by Taxonomy:</label>
    <select id="taxonomyFilter">
        <option value="">All Categories</option>
        <option value="Billing">Billing</option>
        <option value="Bug">Bug Reports</option>
        ... (13 total categories)
    </select>
    
    <label>Output Format:</label>
    <select id="outputFormat">
        <option value="markdown">Markdown</option>
        <option value="gamma">Gamma Presentation</option>
    </select>
    
    <button onclick="runAnalysis()">▶️ Run Analysis</button>
</div>
```

---

### Terminal Output Display

**HTML:** `deploy/railway_web.py` lines 349-397
**JavaScript:** `static/app.js` lines 408-567

**Tabbed Interface:**
```html
<div class="terminal-container">
    <div class="terminal-header">
        <span id="terminalTitle">Command Execution</span>
        <span id="executionStatus">Running</span>
        <button id="cancelButton">Cancel</button>
    </div>
    
    <!-- Tabs -->
    <div class="tab-navigation">
        <button class="tab-button active" onclick="switchTab('terminal')">Terminal</button>
        <button class="tab-button" onclick="switchTab('summary')">Summary</button>
        <button class="tab-button" onclick="switchTab('files')">Files</button>
        <button class="tab-button" onclick="switchTab('gamma')">Gamma</button>
    </div>
    
    <!-- Tab Content -->
    <div class="tab-content">
        <div class="tab-pane active" id="terminalTabContent">
            <div id="terminalOutput"></div>
        </div>
        <div class="tab-pane" id="summaryTabContent">
            <div id="analysisSummary"></div>
        </div>
        <div class="tab-pane" id="filesTabContent">
            <div class="files-list"></div>
        </div>
        <div class="tab-pane" id="gammaTabContent">
            <div id="gammaLinks"></div>
        </div>
    </div>
</div>
```

**Output Streaming:**
```javascript
// Start polling for updates
pollingInterval = setInterval(async () => {
    const response = await fetch(`/execute/status/${executionId}?since=${outputIndex}`);
    const data = await response.json();
    
    // Append new output
    if (data.output && data.output.length > 0) {
        data.output.forEach(outputItem => {
            const line = document.createElement('div');
            line.className = `terminal-line ${outputItem.type}`;
            line.innerHTML = ansiUp.ansi_to_html(outputItem.data);
            terminalOutput.appendChild(line);
        });
        outputIndex = data.output_length;
    }
    
    // Check completion
    if (data.status === 'completed') {
        stopPolling();
        showDownloadLinks();
        showTabs();
    }
}, 1000);
```

---

# Known Issues

## Critical Bugs (Must Fix)

### 1. Examples Often Show "0 examples"

**Symptom:**
```
Logs: "LLM selected 7 examples: [1, 3, 5, 6, 8, 10, 19]"
Output: "_No examples extracted_"
```

**Root Cause:**
Line 269 in `src/agents/example_extraction_agent.py`:
```python
'created_at': conv.get('created_at').isoformat()  # ❌ Crashes if int
```

**Fix Applied (Commit 4e24f46):**
```python
created_at = conv.get('created_at')
if isinstance(created_at, (int, float)):
    created_at_str = datetime.fromtimestamp(created_at).isoformat()
else:
    created_at_str = created_at.isoformat()
```

**Status:** Fixed in code but Railway may not have deployed yet

---

### 2. Horatio Detection Returns 0

**Symptom:**
```
Logs: "Agent distribution: {'horatio': 0, 'boldr': 0, 'unknown': 914}"
```

**Root Cause:**
Original code only checked conversation `full_text`:
```python
if re.search(r'horatio|@hirehoratio\.co', text):  # ❌ Email not in text
    return 'paid', 'horatio'
```

**Fix Applied (Commit aa30ff0):**
```python
# Extract admin emails from conversation_parts
admin_emails = []
for part in conv['conversation_parts']['conversation_parts']:
    if part['author']['type'] == 'admin':
        admin_emails.append(part['author']['email'].lower())

# Check email domains
if any('hirehoratio.co' in email for email in admin_emails):
    return 'paid', 'horatio'
```

**Status:** Fixed in latest commit

---

### 3. Empty Topics Waste LLM Calls

**Symptom:**
```
Processing Refund Request: 0 conversations
TopicSentimentAgent: "This information is not available"
ExampleExtractionAgent: "LLM selection failed, 0 examples"
```

**Root Cause:**
LLM discovers topics but doesn't rescan conversations:
```python
llm_topics = ["Refund Request", "Subscription Cancellation"]
for topic in llm_topics:
    topic_distribution[topic] = {
        'volume': 0,  # ❌ Always 0 - not rescanned
        'method': 'llm_semantic'
    }
```

**Fix Applied (Commit aa30ff0):**
```python
async def process_topic(topic_name, topic_stats):
    topic_convs = conversations_by_topic_full.get(topic_name, [])
    
    # Skip empty topics
    if len(topic_convs) == 0:
        self.logger.info(f"Skipping {topic_name}: 0 conversations")
        return topic_name, None, None
```

**Status:** Fixed in latest commit

---

### 4. Gamma Validation Failures (Previous Runs)

**Symptom:**
```
ValueError: Gamma input validation failed: No category analysis results available
```

**Root Cause:**
GammaGenerator expected old VoC analyzer data structure:
```python
if not analysis_results.get('category_results'):
    raise ValueError("No category analysis results")
```

But we were passing:
```python
{
    'analysis_text': markdown,
    'conversations': [...],
    'metadata': {...}
    # ❌ Missing 'category_results'
}
```

**Fix Applied (Commit 5917fa9):**
Bypass GammaGenerator entirely, call GammaClient directly:
```python
# Don't use:
await gamma_gen.generate_from_analysis(...)

# Use instead:
await gamma_client.generate_presentation(
    input_text=markdown_report,  # Direct API call
    ...
)
```

**Status:** Should be fixed but needs testing

---

### 5. Import Path Inconsistencies

**Symptom:**
```
ModuleNotFoundError: No module named 'services'
```

**Files Affected:**
- ❌ `src/main.py` line 39, 2122, 2202, 2463, 2645
- ❌ `src/services/elt_pipeline.py` line 14-16
- ❌ Possibly others

**Fix Applied (Commit aa30ff0):**
```python
# Changed ALL instances:
from services.gamma_generator import GammaGenerator
# To:
from src.services.gamma_generator import GammaGenerator
```

**Status:** Fixed in latest commit

---

## Medium Priority Issues

### 6. Topic Coverage Low (33%)

**Symptom:**
```
Topics detected: 7
Coverage: 33.6%
Conversations without topics: 602 of 906
```

**Cause:**
- Only 8 predefined topics
- Keyword matching is strict
- Taxonomy has 13 categories but we only use 8

**Possible Fix:**
Add more topic definitions or improve keyword matching

---

### 7. Date Range Warnings

**Symptom:**
```
⚠️ API returned conversations outside requested range!
Requested: 2025-10-21 to 2025-10-21
Received: 2025-10-21 to 2025-10-22
```

**Cause:**
Timezone conversion or Intercom API interpretation

**Impact:**
Getting slightly more conversations than requested (not critical)

---

# Code Samples

## Complete Multi-Agent Workflow

**File:** `src/main.py` lines 2930-3022

```python
async def run_topic_based_analysis_custom(start_date: datetime, end_date: datetime, generate_gamma: bool):
    """Run topic-based analysis (Hilary's VoC card format)"""
    from src.agents.topic_orchestrator import TopicOrchestrator
    from src.services.chunked_fetcher import ChunkedFetcher
    from src.services.gamma_client import GammaClient
    
    console.print("📥 Fetching conversations...")
    fetcher = ChunkedFetcher()
    conversations = await fetcher.fetch_conversations_chunked(start_date, end_date)
    console.print(f"   ✅ Fetched {len(conversations)} conversations")
    
    # Run multi-agent pipeline
    orchestrator = TopicOrchestrator()
    week_id = start_date.strftime('%Y-W%W')
    
    results = await orchestrator.execute_weekly_analysis(
        conversations=conversations,
        week_id=week_id,
        start_date=start_date,
        end_date=end_date
    )
    
    # Save markdown report
    output_dir = Path("outputs")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = output_dir / f"topic_based_{week_id}_{timestamp}.md"
    
    with open(report_file, 'w') as f:
        f.write(results['formatted_report'])
    
    console.print(f"✅ Report: {report_file}")
    
    # Generate Gamma if requested
    if generate_gamma:
        console.print("\n🎨 Generating Gamma presentation...")
        gamma_client = GammaClient()
        
        generation_id = await gamma_client.generate_presentation(
            input_text=results['formatted_report'],
            format="presentation",
            text_mode="preserve",
            card_split="inputTextBreaks",
            theme_name="Night Sky",
            text_options={
                "tone": "professional, analytical",
                "audience": "executives, leadership team"
            }
        )
        
        # Poll for completion
        for attempt in range(24):
            await asyncio.sleep(5)
            status = await gamma_client.get_generation_status(generation_id)
            
            if status['status'] == 'completed':
                gamma_url = status['url']
                console.print(f"✅ Gamma URL: {gamma_url}")
                
                # Save URL
                url_file = output_dir / f"gamma_url_{timestamp}.txt"
                with open(url_file, 'w') as f:
                    f.write(gamma_url)
                break
```

---

## Topic Orchestrator Core

**File:** `src/agents/topic_orchestrator.py` lines 67-241

```python
async def execute_weekly_analysis(conversations, week_id, start_date, end_date):
    start_time = datetime.now()
    
    # Preprocess: Extract customer messages
    conversations = self._extract_customer_messages(conversations)
    
    context = AgentContext(
        analysis_id=f"weekly_{week_id}",
        conversations=conversations,
        start_date=start_date,
        end_date=end_date,
        metadata={'week_id': week_id}
    )
    
    # Phase 1: Segmentation
    segmentation_result = await self.segmentation_agent.execute(context)
    paid_conversations = segmentation_result.data['paid_customer_conversations']
    free_conversations = segmentation_result.data['free_customer_conversations']
    
    # Phase 2: Topic Detection
    context.conversations = paid_conversations
    topic_detection_result = await self.topic_detection_agent.execute(context)
    topic_dist = topic_detection_result.data['topic_distribution']
    
    # Phase 3: Process topics in parallel
    async def process_topic(topic_name, topic_stats):
        topic_convs = conversations_by_topic_full[topic_name]
        
        if len(topic_convs) == 0:
            return topic_name, None, None  # Skip empty
        
        # Sentiment
        sentiment_result = await self.topic_sentiment_agent.execute(...)
        
        # Examples
        examples_result = await self.example_extraction_agent.execute(...)
        
        return topic_name, sentiment_result, examples_result
    
    # Launch all topics simultaneously
    topic_tasks = [process_topic(name, stats) for name, stats in topic_dist.items()]
    topic_results = await asyncio.gather(*topic_tasks, return_exceptions=True)
    
    # Collect results (skip None)
    for result in topic_results:
        if result and result[1] and result[2]:
            topic_sentiments[result[0]] = result[1].dict()
            topic_examples[result[0]] = result[2].dict()
    
    # Phase 4: Fin Performance
    fin_result = await self.fin_performance_agent.execute(...)
    
    # Phase 5: Trends
    trend_result = await self.trend_agent.execute(...)
    
    # Phase 6: Format Output
    formatter_result = await self.output_formatter_agent.execute(...)
    
    return {
        'formatted_report': formatter_result.data['formatted_output'],
        'summary': {
            'total_conversations': len(conversations),
            'paid_conversations': len(paid_conversations),
            'free_conversations': len(free_conversations),
            'topics_analyzed': len(topic_dist),
            'total_execution_time': (datetime.now() - start_time).total_seconds(),
            'agents_completed': 7
        }
    }
```

---

# Testing Guidance

## How to Test End-to-End

### Test 1: Minimal Test with Fake Data

```bash
# On Railway or local with proper environment
python -m src.main test-mode --test-type topic-based --num-conversations 50
```

**Expected Output:**
```
🧪 TEST MODE
Test type: topic-based
Fake conversations: 50
================================================================================
✅ Created 50 fake conversations
📁 Test data saved to: outputs/test_data.json

🤖 Running topic-based analysis with test data...
📊 Phase 1: Segmentation
   ✅ Paid: 50, Free: 0
🏷️ Phase 2: Topic Detection
   ✅ Detected 5 topics
💭 Phase 3: Per-Topic Analysis
   Processing 5 topics in parallel...
   ✅ Billing: Sentiment + 7 examples
   ✅ Bug: Sentiment + 5 examples
   ✅ Credits: Sentiment + 1 examples
   ✅ Account: Sentiment + 7 examples
   ✅ Product Question: Sentiment + 4 examples
🤖 Phase 4: Fin Analysis
   ✅ Fin analysis complete
📈 Phase 5: Trend Analysis
   ✅ First analysis - baseline
📝 Phase 6: Output Formatting
   ✅ Formatted 5 topic cards

================================================================================
✅ TEST PASSED
================================================================================

📊 Summary:
   Total: 50
   Topics: 5
   Agents: 7
   Time: 8.2s

📝 Report preview:
# Voice of Customer Analysis - Week TEST

## Customer Topics

### Billing
**10 tickets / 20% of weekly volume**
...

📁 Test output: outputs/test_output.md
```

**What to Check:**
- [ ] Does it complete without crashing?
- [ ] Are examples present (not "0 examples")?
- [ ] Are sentiment insights nuanced?
- [ ] Is the report readable?

---

### Test 2: Real Data (Yesterday)

**Via Railway UI:**
1. Select: VoC: Hilary Format
2. Select: Yesterday
3. Select: Intercom Only
4. Select: Markdown (not Gamma yet)
5. Click: Run Analysis

**Expected Behavior:**
```
Fetching: ~1000 conversations (4-5 min)
Segmentation: < 1 sec
Topic Detection: 2-3 sec
Per-Topic Analysis: 5-10 sec (parallel)
Fin Analysis: 6-8 sec
Trends: < 1 sec (first run)
Formatting: < 1 sec

Total: ~6-7 minutes
```

**What to Check:**
- [ ] Terminal shows progress
- [ ] No crashes
- [ ] Markdown file created
- [ ] Topics make sense
- [ ] Sentiment is specific
- [ ] Examples have Intercom links
- [ ] Examples are NOT "0 examples"

---

### Test 3: Gamma Generation

**Only after Test 2 passes!**

Same as Test 2 but select **Gamma Presentation**

**Expected:**
```
✅ Topic-based analysis complete
📁 Report: outputs/topic_based_2025-W42_*.md

🎨 Generating Gamma presentation...
   Sending 7763 characters to Gamma API...
   Generation ID: xyz123
   Waiting for Gamma to process...
   Still processing... (1/24)
   Still processing... (2/24)
   ...
   Still processing... (8/24)
✅ Gamma URL: https://gamma.app/docs/abc123xyz
📁 URL saved to: outputs/gamma_url_*.txt
```

**What to Check:**
- [ ] Gamma URL appears in terminal
- [ ] URL file is created
- [ ] Can open Gamma URL
- [ ] Presentation has slides
- [ ] Each topic is a slide
- [ ] Text is preserved (not rewritten)
- [ ] Theme is professional

---

### Test 4: API Analysis

**Via Railway UI:**
1. Select: API Issues & Integration
2. Select: Yesterday
3. Select: Markdown
4. Click: Run

**Expected:**
- Only API-tagged conversations
- Focused analysis on API topics
- Integration issues highlighted

**What to Check:**
- [ ] Command runs
- [ ] Filters to API only
- [ ] Report generated

---

### Test 5: Horatio Performance

**Via Railway UI:**
1. Select: Horatio Performance Review
2. Select: 6-weeks (or Week)
3. Select: Markdown
4. Click: Run

**Expected:**
```
Horatio Performance Analysis
Date Range: 2025-09-10 to 2025-10-22

Fetching conversations...
Filtering to Horatio conversations...
   Found X conversations handled by Horatio

Analyzing performance...
   FCR: XX%
   Median resolution: X.X hours
   Escalation rate: XX%

Generating performance insights...
✅ Horatio performance report generated
```

**What to Check:**
- [ ] Finds Horatio conversations (not 0)
- [ ] Calculates FCR
- [ ] Shows category breakdown
- [ ] LLM insights present

---

# Summary for QA Reviewer

## What We're Trying to Achieve

A Voice of Customer analysis tool that:
1. Fetches support conversations from Intercom
2. Uses 7 specialized AI agents to analyze topics, sentiment, and trends
3. Produces executive reports in Hilary's specific card format
4. Generates Gamma presentations automatically
5. Tracks agent performance (Horatio/Boldr)

## Current State

**What Works:**
- ✅ UI is clean and accessible
- ✅ Multi-agent pipeline executes
- ✅ LLM agents produce nuanced insights
- ✅ Parallel processing is fast
- ✅ Markdown reports are generated

**What's Broken:**
- ❌ Examples often don't show (timestamp bug - should be fixed)
- ❌ Horatio detection returns 0 (email extraction bug - should be fixed)
- ❌ Empty topics waste LLM calls (should be fixed)
- ❌ Gamma generation may fail (multiple fixes applied, needs testing)
- ❌ Canny integration untested

## Most Critical Question

**Does Gamma generation work now?**

After commits:
- 5917fa9: Bypass GammaGenerator, use GammaClient directly
- 25dd482: Proper Gamma API v0.2 parameters
- e899c38: Theme support added
- Latest: cardSplit, textMode, textOptions

**This should work but needs end-to-end Railway test to confirm.**

## Recommendations for QA

1. **Test the test mode first** - Verify agents work with fake data
2. **Test yesterday analysis** - Small real dataset
3. **Test Gamma last** - Only after markdown works
4. **Check logs** - Railway logs will show actual errors
5. **Focus on one thing** - Get examples working before anything else

The codebase is large (50+ files) but the core pipeline is:
```
UI → CLI → Fetch → 7 Agents → Format → Gamma
```

If any step breaks, the whole thing fails. Test each step independently.


---

# CRITICAL CODE - Pipeline Transition Points

## 1. UI → Backend Transition

**Frontend (static/app.js lines 755-818):**
```javascript
function runAnalysis() {
    const analysisType = document.getElementById('analysisType').value;
    const timePeriod = document.getElementById('timePeriod').value;
    const outputFormat = document.getElementById('outputFormat').value;
    
    let command = '';
    let args = [];
    
    // Map UI selections to CLI commands
    if (analysisType === 'voice-of-customer-hilary') {
        command = 'voice-of-customer';
        args.push('--multi-agent', '--analysis-type', 'topic-based');
    }
    
    args.push('--time-period', timePeriod);
    
    if (outputFormat === 'gamma') {
        args.push('--generate-gamma');
    }
    
    // Call backend
    executeCommand(command, args);
}

async function executeCommand(command, args) {
    const fullCommand = 'python';
    let fullArgs = ['src/main.py', command, ...args];
    
    // POST to backend
    const response = await fetch(`/execute/start?command=${fullCommand}&args=${JSON.stringify(fullArgs)}`, {
        method: 'POST'
    });
    
    const data = await response.json();
    currentExecutionId = data.execution_id;
    
    // Start polling
    startPolling();
}
```

**Backend (deploy/railway_web.py lines 624-650):**
```python
@app.post("/execute/start")
async def start_execution(command: str, args: str):
    # Parse args from JSON string
    args_list = json.loads(args)
    # ["src/main.py", "voice-of-customer", "--multi-agent", "--analysis-type", "topic-based", ...]
    
    # Generate execution ID
    execution_id = command_executor.generate_execution_id()  # UUID
    
    # Create execution state (queued)
    execution = await state_manager.create_execution(execution_id, command, args_list)
    
    # Start subprocess in background
    asyncio.create_task(run_command_background(execution_id, command, args_list))
    
    return {"execution_id": execution_id, "status": "queued"}
```

---

## 2. Backend → CLI Subprocess

**WebCommandExecutor (src/services/web_command_executor.py lines 209-304):**
```python
async def execute_command(command, args, execution_id):
    # Build subprocess
    process = await asyncio.create_subprocess_exec(
        "python",                    # command
        "src/main.py",              # args[0]
        "voice-of-customer",        # args[1]
        "--multi-agent",            # args[2]
        "--analysis-type",          # args[3]
        "topic-based",              # args[4]
        "--time-period",            # args[5]
        "yesterday",                # args[6]
        "--generate-gamma",         # args[7]
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd="/app",
        env=os.environ.copy()
    )
    
    # Stream output
    async for line in process.stdout:
        output = line.decode()
        yield {"type": "stdout", "data": output}
    
    # Wait for completion
    return_code = await process.wait()
```

---

## 3. CLI → Topic Orchestrator

**CLI Entry (src/main.py lines 2751-2992):**
```python
@cli.command(name='voice-of-customer')
@click.option('--time-period', ...)
@click.option('--multi-agent', is_flag=True)
@click.option('--analysis-type', type=click.Choice(['topic-based', 'synthesis', 'complete']))
@click.option('--generate-gamma', is_flag=True)
def voice_of_customer_analysis(time_period, multi_agent, analysis_type, generate_gamma, ...):
    # Calculate dates
    if time_period == 'yesterday':
        start_dt = datetime.now() - timedelta(days=1)
        end_dt = datetime.now() - timedelta(days=1)
    
    # Convert to Pacific Time
    from src.utils.timezone_utils import get_date_range_pacific
    start_dt, end_dt = get_date_range_pacific(start_date, end_date)
    
    # Route based on analysis type
    if analysis_type == 'topic-based':
        asyncio.run(run_topic_based_analysis_custom(start_dt, end_dt, generate_gamma))
```

**Analysis Runner (src/main.py lines 3064-3117):**
```python
async def run_topic_based_analysis_custom(start_date, end_date, generate_gamma):
    from src.agents.topic_orchestrator import TopicOrchestrator
    from src.services.chunked_fetcher import ChunkedFetcher
    from src.services.gamma_client import GammaClient
    
    # Fetch conversations
    fetcher = ChunkedFetcher()
    conversations = await fetcher.fetch_conversations_chunked(start_date, end_date)
    
    # Run multi-agent pipeline
    orchestrator = TopicOrchestrator()
    results = await orchestrator.execute_weekly_analysis(
        conversations=conversations,
        week_id=start_date.strftime('%Y-W%W'),
        start_date=start_date,
        end_date=end_date
    )
    
    # Save markdown
    report_file = Path("outputs") / f"topic_based_{week_id}_{timestamp}.md"
    with open(report_file, 'w') as f:
        f.write(results['formatted_report'])
    
    # Generate Gamma if requested
    if generate_gamma:
        gamma_client = GammaClient()
        
        generation_id = await gamma_client.generate_presentation(
            input_text=results['formatted_report'],
            format="presentation",
            text_mode="preserve",
            card_split="inputTextBreaks",
            theme_name="Night Sky"
        )
        
        # Poll for result
        for attempt in range(24):
            await asyncio.sleep(5)
            status = await gamma_client.get_generation_status(generation_id)
            if status['status'] == 'completed':
                print(f"✅ Gamma URL: {status['url']}")
                break
```

---

## 4. Intercom API Call Specification

**Request Construction (src/services/intercom_service_v2.py lines 73-93):**
```python
query_params = {
    'query': {
        'operator': 'AND',
        'value': [
            {
                'field': 'created_at',
                'operator': '>=',
                'value': int(start_date.timestamp())  # 1760920800 (Unix timestamp UTC)
            },
            {
                'field': 'created_at',
                'operator': '<=',
                'value': int(end_date.timestamp())    # 1761007199
            }
        ]
    },
    'pagination': {
        'per_page': 50,
        'starting_after': cursor_from_previous_page  # or None for first page
    }
}

# HTTP Call
async with httpx.AsyncClient(timeout=60) as client:
    response = await client.post(
        "https://api.intercom.io/conversations/search",
        headers={
            'Authorization': f'Bearer {INTERCOM_ACCESS_TOKEN}',
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Intercom-Version': '2.11'
        },
        json=query_params
    )
    
    data = response.json()
```

**Response Structure:**
```json
{
  "type": "list",
  "conversations": [
    {
      "type": "conversation",
      "id": "215471377705486",
      "created_at": 1760998808,
      "updated_at": 1761091004,
      "state": "closed",
      "admin_assignee_id": 7885880,
      "conversation_parts": {
        "conversation_parts": [
          {
            "author": {
              "type": "admin",
              "id": "7885880",
              "name": "Max Jackson",
              "email": "max.jackson@gamma.app"
            },
            "body": "Let me help you with that..."
          },
          {
            "author": {
              "type": "user"
            },
            "body": "I want a refund"
          }
        ]
      },
      "custom_attributes": {"Billing": true},
      "tags": {"tags": [{"name": "Billing"}]},
      "statistics": {
        "time_to_admin_reply": 3600,
        "count_reopens": 0
      }
    }
  ],
  "pages": {
    "next": {
      "starting_after": "WzE3NjA5OTg4MDgsIjIxNTQ3MTM3NzcwNTQ4NiJd"
    }
  }
}
```

**Pagination Logic:**
```python
page = 1
all_conversations = []

while True:
    # Fetch page
    data = await post_request(query_params)
    all_conversations.extend(data['conversations'])
    
    # Check for next page
    next_cursor = data.get('pages', {}).get('next', {}).get('starting_after')
    if not next_cursor:
        break  # No more pages
    
    # Update cursor for next request
    query_params['pagination']['starting_after'] = next_cursor
    page += 1
    
    await asyncio.sleep(1.5)  # Rate limiting
```

---

## 5. OpenAI API Call Specification

**Client (src/services/openai_client.py lines 46-74):**
```python
async def generate_analysis(prompt: str) -> str:
    response = await self.client.chat.completions.create(
        model="gpt-4o",  # or "gpt-4o-mini"
        messages=[
            {
                "role": "system",
                "content": "You are an expert data analyst specializing in customer support analytics."
            },
            {
                "role": "user",
                "content": prompt  # Full prompt with data and instructions
            }
        ],
        max_tokens=500,  # From settings
        temperature=0.3  # Varies by agent: 0.1-0.6
    )
    
    return response.choices[0].message.content
```

**Example Prompt (TopicSentimentAgent):**
```
CRITICAL HALLUCINATION PREVENTION RULES:
1. You are FORBIDDEN from inventing URLs, citations, conversation IDs
2. If unsure, state "I cannot verify this information"
3. Only use provided conversation data
4. Never fabricate statistics

TOPIC SENTIMENT AGENT SPECIFIC RULES:
1. Generate ONE-SENTENCE sentiment insights
2. Be specific to the topic
3. Show nuance (appreciate X BUT frustrated by Y)
4. Use natural language

GOOD EXAMPLES:
✓ "Users hate buddy so much"
✓ "Customers appreciate quick resolution BUT frustrated by unexpected charges"

BAD EXAMPLES:
✗ "Negative sentiment detected"
✗ "Users are frustrated"

Analyze sentiment for topic: Billing

You have 239 conversations tagged with this topic.

Sample conversations (showing 10 of 239):
[
  {
    "id": "215471377705486",
    "customer_message": "I want a refund for my subscription. I was charged £75...",
    "rating": null
  },
  {
    "id": "215471376230298",
    "customer_message": "Quero pedir reembolso desse plano, já fiz o Cancelamento...",
    "rating": null
  }
]

Your insight for Billing:
```

**Example Response:**
```
Customers frustrated with unexpected charges and subscription confusion BUT appreciate prompt refund process when issues are addressed.
```

**Token Usage:**
- Prompt: ~600 tokens
- Response: ~30-50 tokens
- Cost: ~$0.006 per call (GPT-4o)
- Per analysis: 15-20 calls = ~$0.10-0.15

---

## 6. Gamma API Call Specification

**Request (src/services/gamma_client.py lines 115-150):**
```python
POST https://public-api.gamma.app/v0.2/generations

Headers:
{
  "X-API-KEY": "sk-gamma-xxxxxxxxxxxxx",
  "Content-Type": "application/json"
}

Body:
{
  "inputText": "# Voice of Customer Analysis - Week 2025-W42\n\n## Customer Topics (Paid Tier - Human Support)\n\n### Billing\n**239 tickets / 23.4% of weekly volume**\n**Detection Method**: Intercom conversation attribute\n\n**Sentiment**: Customers frustrated with unexpected charges BUT appreciate prompt refund process\n\n**Examples**:\n1. \"I want a refund for my subscription...\" - [View conversation](https://app.intercom.com/a/inbox/inbox/215471377705486)\n...\n\n---\n\n### Bug\n**14 tickets / 1.4%**\n...",
  
  "format": "presentation",
  "textMode": "preserve",
  "cardSplit": "inputTextBreaks",
  "themeName": "Night Sky",
  "numCards": 15,
  "textOptions": {
    "tone": "professional, analytical",
    "audience": "executives, leadership team",
    "language": "en"
  },
  "imageOptions": {
    "source": "aiGenerated"
  }
}
```

**Response:**
```json
{
  "generationId": "67d89f2a3c1b2e4f5a6789bc"
}
```

**Status Polling (every 5 seconds):**
```python
GET https://public-api.gamma.app/v0.2/generations/{generationId}

Headers:
{
  "X-API-KEY": "sk-gamma-xxxxxxxxxxxxx"
}

Response (pending):
{
  "status": "pending",
  "generationId": "67d89f2a3c1b2e4f5a6789bc"
}

Response (completed):
{
  "status": "completed",
  "generationId": "67d89f2a3c1b2e4f5a6789bc",
  "gammaUrl": "https://gamma.app/docs/What-Your-Customers-Are-Really-Saying-xyz123",
  "credits": {
    "deducted": 150,
    "remaining": 2700
  }
}
```

**Polling Logic (src/main.py lines 3036-3052):**
```python
for attempt in range(24):  # Max 2 minutes
    await asyncio.sleep(5)
    status = await gamma_client.get_generation_status(generation_id)
    
    if status.get('status') == 'completed':
        gamma_url = status.get('url')
        print(f"✅ Gamma URL: {gamma_url}")
        
        # Save URL to file
        url_file = output_dir / f"gamma_url_{timestamp}.txt"
        with open(url_file, 'w') as f:
            f.write(gamma_url)
        break
    
    elif status.get('status') == 'failed':
        print(f"❌ Generation failed: {status.get('error')}")
        break
    
    print(f"Still processing... ({attempt+1}/24)")

if attempt >= 24:
    print("⚠️ Timeout - check Gamma dashboard")
```

---

## 7. Multi-Agent Orchestration (Complete Code)

**File:** `src/agents/topic_orchestrator.py`

```python
class TopicOrchestrator:
    def __init__(self):
        self.segmentation_agent = SegmentationAgent()
        self.topic_detection_agent = TopicDetectionAgent()
        self.topic_sentiment_agent = TopicSentimentAgent()
        self.example_extraction_agent = ExampleExtractionAgent()
        self.fin_performance_agent = FinPerformanceAgent()
        self.trend_agent = TrendAgent()
        self.output_formatter_agent = OutputFormatterAgent()
    
    async def execute_weekly_analysis(conversations, week_id, start_date, end_date):
        # Preprocess: Extract customer messages
        for conv in conversations:
            customer_msgs = []
            for part in conv['conversation_parts']['conversation_parts']:
                if part['author']['type'] == 'user':
                    customer_msgs.append(part['body'])
            conv['customer_messages'] = customer_msgs
        
        context = AgentContext(
            analysis_id=f"weekly_{week_id}",
            conversations=conversations,
            metadata={'week_id': week_id}
        )
        
        # PHASE 1: Segmentation (0.01s)
        segmentation_result = await self.segmentation_agent.execute(context)
        paid_conversations = segmentation_result.data['paid_customer_conversations']
        free_conversations = segmentation_result.data['free_customer_conversations']
        
        # PHASE 2: Topic Detection (1-3s with LLM)
        context.conversations = paid_conversations
        topic_detection_result = await self.topic_detection_agent.execute(context)
        topic_dist = topic_detection_result.data['topic_distribution']
        
        # PHASE 3: Per-Topic Analysis (PARALLEL - 5-10s total)
        async def process_topic(topic_name, topic_stats):
            topic_convs = conversations_by_topic_full[topic_name]
            
            if len(topic_convs) == 0:
                return topic_name, None, None  # Skip empty
            
            # Sentiment analysis (LLM)
            sentiment_result = await self.topic_sentiment_agent.execute({
                'current_topic': topic_name,
                'topic_conversations': topic_convs
            })
            
            # Example extraction (LLM)
            examples_result = await self.example_extraction_agent.execute({
                'current_topic': topic_name,
                'topic_conversations': topic_convs,
                'sentiment_insight': sentiment_result.data['sentiment_insight']
            })
            
            return topic_name, sentiment_result, examples_result
        
        # Launch all topics simultaneously
        topic_tasks = [process_topic(name, stats) for name, stats in topic_dist.items()]
        topic_results = await asyncio.gather(*topic_tasks, return_exceptions=True)
        
        # Collect non-None results
        topic_sentiments = {}
        topic_examples = {}
        for result in topic_results:
            if result and result[1] and result[2]:
                topic_sentiments[result[0]] = result[1].dict()
                topic_examples[result[0]] = result[2].dict()
        
        # PHASE 4: Fin Performance (6-8s with LLM)
        fin_result = await self.fin_performance_agent.execute({
            'fin_conversations': free_conversations
        })
        
        # PHASE 5: Trend Analysis (0-5s with LLM if trends exist)
        trend_result = await self.trend_agent.execute({
            'current_week_results': {
                'topic_distribution': topic_dist,
                'topic_sentiments': topic_sentiments
            },
            'week_id': week_id
        })
        
        # PHASE 6: Output Formatting (0.01s)
        formatter_result = await self.output_formatter_agent.execute({
            'previous_results': {
                'SegmentationAgent': segmentation_result.dict(),
                'TopicDetectionAgent': topic_detection_result.dict(),
                'TopicSentiments': topic_sentiments,
                'TopicExamples': topic_examples,
                'FinPerformanceAgent': fin_result.dict(),
                'TrendAgent': trend_result.dict()
            },
            'week_id': week_id
        })
        
        return {
            'formatted_report': formatter_result.data['formatted_output'],
            'summary': {
                'total_conversations': len(conversations),
                'topics_analyzed': len(topic_dist),
                'total_execution_time': elapsed_seconds
            }
        }
```

---

## 8. LLM Prompts (Exact Templates)

### TopicSentimentAgent Prompt

```python
def build_prompt(context):
    topic_name = context.metadata['current_topic']
    topic_conversations = context.metadata['topic_conversations']
    
    # Sample 10 conversations
    sample = []
    for conv in topic_conversations[:10]:
        customer_msgs = conv.get('customer_messages', [])
        if customer_msgs:
            sample.append({
                'id': conv['id'],
                'customer_message': customer_msgs[0][:200],
                'rating': conv.get('conversation_rating')
            })
    
    return f"""
CRITICAL HALLUCINATION PREVENTION RULES:

1. You are FORBIDDEN from inventing URLs, citations, conversation IDs, or references.

2. If you are unsure about any information, you MUST state "I cannot verify this information" 
   rather than guessing or fabricating.

3. Only use information from the provided context and data. Do NOT use your general knowledge 
   or training data to fill gaps.

4. For each claim you make, use the format: [Claim] - [Source from provided data]

5. If information is not in the provided data, state: "This information is not available 
   in the provided dataset"

TOPIC SENTIMENT AGENT SPECIFIC RULES:

1. Generate ONE-SENTENCE sentiment insights that are:
   - Specific to the topic
   - Nuanced (show complexity: "appreciative BUT frustrated")
   - Actionable (tells us what to fix)
   - Natural language (how a human analyst would say it)

2. GOOD EXAMPLES (match this style):
   ✓ "Users are appreciative of the ability to buy more credits, but frustrated that Gamma moved to a credit model"
   ✓ "Users hate buddy so much"
   ✓ "Users think templates are rad but want to be able to use them with API"

3. BAD EXAMPLES (avoid these):
   ✗ "Negative sentiment detected"
   ✗ "Users are frustrated with this feature"
   ✗ "Mixed sentiment with both positive and negative elements"

4. Capture the SPECIFIC sentiment:
   - What do users LIKE? (be specific)
   - What do users HATE? (be specific)
   - What's the tension/nuance?

5. Base ONLY on the conversations provided:
   - Quote actual customer language when possible
   - Don't invent sentiment not present in data

Analyze sentiment for the topic: {topic_name}

You have {len(topic_conversations)} conversations tagged with this topic.

Generate ONE SENTENCE that:
1. Captures the specific sentiment for THIS topic
2. Shows nuance (e.g., "love X BUT want Y")
3. Uses natural, conversational language
4. Is immediately actionable

Sample conversations for this topic (showing {len(sample)} of {len(topic_conversations)}):
{json.dumps(sample, indent=2)}

Analyze ALL {len(topic_conversations)} conversations to generate your insight.

Your insight for {topic_name}:
"""
```

### ExampleExtractionAgent Prompt

```python
def _llm_select_examples(candidates, topic, sentiment, target_count=7):
    # Build candidate list
    candidate_summaries = []
    for i, conv in enumerate(candidates):
        msg = conv['customer_messages'][0][:150]
        candidate_summaries.append(f"{i+1}. \"{msg}\"")
    
    return f"""
Select the most representative and informative examples for this topic analysis.

Topic: {topic}
Sentiment Insight: {sentiment}

Candidate conversations (ranked by quality):
{chr(10).join(candidate_summaries)}

Instructions:
1. Select {target_count} examples that are:
   - Most representative (clearly demonstrate the sentiment)
   - Show different aspects/facets of the issue
   - Specific and actionable (provide clear feedback)
   - Professional and informative (suitable for executive reports)

2. Return ONLY the numbers (1-{len(candidates)}) as a JSON array
3. Example: [1, 3, 7, 12, 15, 18, 20]

Selected example numbers:
"""
```

### FinPerformanceAgent Prompt

```python
def _generate_fin_insights(metrics):
    return f"""
Analyze Fin AI's performance and provide nuanced, actionable insights.

Metrics:
- Total Fin conversations: {metrics['total']}
- Resolution rate: {metrics['resolution_rate']:.1%}
- Knowledge gaps: {metrics['knowledge_gaps_count']}

Top performing topics: Account (78%), Product (72%)
Struggling topics: Billing (62%), Bug (31%)

Instructions:
1. Provide 2-3 specific insights about Fin's performance
2. Be analytical and data-driven, not generic
3. Identify patterns in what Fin does well vs struggles with
4. Suggest WHY Fin might be struggling (knowledge gaps, complex topics, etc.)
5. Keep it under 150 words, professional executive tone
6. Focus on actionable insights for improving AI performance

Insights:
"""
```

### TrendAgent Prompt

```python
def _interpret_trends(topic, pct_change, sentiment):
    return f"""
Explain WHY this trend might be happening based on the data.

Topic: {topic}
Volume change: {pct_change:+.1f}% ({"increasing" if pct_change > 0 else "decreasing"})
Current sentiment: {sentiment}

Instructions:
1. Provide ONE sentence explaining the likely cause
2. Be specific and actionable
3. Consider: product changes, user behavior patterns, seasonal factors, issues escalating
4. Example: "Agent/Buddy volume up 23% likely due to recent editing feature launch causing confusion"

Explanation:
"""
```

---

## 9. Data Transformation Points

### Intercom Response → Internal Format

**Input (from Intercom API):**
```python
{
    'id': '215471377705486',
    'created_at': 1760998808,  # Unix timestamp
    'conversation_parts': {
        'conversation_parts': [
            {'author': {'type': 'user', 'email': None}, 'body': 'I want a refund'}
        ]
    }
}
```

**Transform (src/agents/topic_orchestrator.py lines 42-65):**
```python
def _extract_customer_messages(conversations):
    for conv in conversations:
        customer_msgs = []
        
        # Extract from conversation_parts
        for part in conv.get('conversation_parts', {}).get('conversation_parts', []):
            if part.get('author', {}).get('type') == 'user':
                body = part.get('body', '').strip()
                if body:
                    customer_msgs.append(body)
        
        # Also check source (initial message)
        source = conv.get('source', {})
        if source.get('author', {}).get('type') == 'user':
            body = source.get('body', '').strip()
            if body:
                customer_msgs.insert(0, body)
        
        conv['customer_messages'] = customer_msgs
    
    return conversations
```

**Output (enriched):**
```python
{
    'id': '215471377705486',
    'created_at': 1760998808,
    'customer_messages': ['I want a refund for my subscription'],  # ← Added
    'conversation_parts': {...}  # Original preserved
}
```

### Agent Results → Formatted Output

**Agent Outputs:**
```python
topic_sentiments = {
    'Billing': {
        'data': {
            'sentiment_insight': "Customers frustrated with charges BUT appreciate refunds"
        }
    }
}

topic_examples = {
    'Billing': {
        'data': {
            'examples': [
                {'preview': 'I want a refund...', 'intercom_url': 'https://...'},
                {'preview': 'Why was I charged...', 'intercom_url': 'https://...'}
            ]
        }
    }
}
```

**Transform (OutputFormatterAgent lines 111-138):**
```python
for topic_name, topic_stats in sorted_topics:
    sentiment = topic_sentiments[topic_name]['data']['sentiment_insight']
    examples = topic_examples[topic_name]['data']['examples']
    
    card = f"""### {topic_name}
**{topic_stats['volume']} tickets / {topic_stats['percentage']}% of weekly volume**

**Sentiment**: {sentiment}

**Examples**:
"""
    
    for i, example in enumerate(examples, 1):
        card += f"{i}. \"{example['preview']}\" - [View]({example['intercom_url']})\n"
    
    card += "\n---\n"
```

**Final Markdown:**
```markdown
# Voice of Customer Analysis - Week 2025-W42

## Customer Topics (Paid Tier - Human Support)

### Billing
**239 tickets / 23.4% of weekly volume**
**Detection Method**: Intercom conversation attribute

**Sentiment**: Customers frustrated with unexpected charges BUT appreciate prompt refund process

**Examples**:
1. "I want a refund for my subscription. I was charged £75..." - [View](https://app.intercom.com/a/inbox/inbox/215471377705486)
2. "Why was I charged when I cancelled last week..." - [View](https://app.intercom.com/a/inbox/inbox/215471376230298)
...

---

### Bug
**14 tickets / 1.4% of weekly volume**
...

---

## Fin AI Performance

**159 conversations handled by Fin**

**AI Performance Insights**:
Fin demonstrates strong performance on routine account questions (78% resolution) but struggles with billing edge cases (62%). Recommend expanding billing knowledge base.

...
```

---

## 10. Error Handling & Edge Cases

### Empty Conversation Handling

**Problem:**
```python
customer_msgs = conv.get('customer_messages', [])
if customer_msgs:
    sample.append({'customer_message': customer_msgs[0][:200]})
```

If `customer_messages` is empty, sample is empty, prompt has no data.

**Current State:** Agents return "cannot verify" for empty samples

**Better Fix:**
```python
if not customer_msgs or len(customer_msgs[0]) < 10:
    continue  # Skip this conversation entirely
```

### Timestamp Conversion

**Problem:**
```python
# created_at can be:
# - int/float (Unix timestamp): 1760998808
# - datetime object
# - ISO string: "2025-10-21T14:23:45"

conv['created_at'].isoformat()  # ❌ Crashes if int
```

**Fix:**
```python
created_at = conv['created_at']
if isinstance(created_at, (int, float)):
    created_at_str = datetime.fromtimestamp(created_at).isoformat()
elif isinstance(created_at, datetime):
    created_at_str = created_at.isoformat()
else:
    created_at_str = str(created_at)
```

### Null/None Propagation

**Problem:**
```python
sentiment = topic_sentiments[topic_name]['data']['sentiment_insight']
# ❌ KeyError if topic_name not in topic_sentiments
# ❌ KeyError if 'data' not present
# ❌ KeyError if 'sentiment_insight' not present
```

**Fix:**
```python
sentiment = topic_sentiments.get(topic_name, {}).get('data', {}).get('sentiment_insight', 'No analysis available')
```

---

## 11. Configuration & Environment

**Required Environment Variables:**
```bash
# Intercom
INTERCOM_ACCESS_TOKEN=xxxxx
INTERCOM_WORKSPACE_ID=99cd7132_0d87_4553_b1a4_f53e87069b6c

# OpenAI
OPENAI_API_KEY=sk-xxxxx

# Gamma
GAMMA_API_KEY=sk-gamma-xxxxx

# Optional
ANTHROPIC_API_KEY=sk-ant-xxxxx  # For Claude fallback
CANNY_API_KEY=xxxxx              # For Canny integration
```

**Settings (src/config/settings.py):**
```python
class Settings(BaseSettings):
    # Intercom
    intercom_access_token: str
    intercom_base_url: str = "https://api.intercom.io"
    intercom_api_version: str = "2.11"
    
    # OpenAI
    openai_api_key: str
    openai_model: str = "gpt-4o"
    openai_temperature: float = 0.3
    openai_max_tokens: int = 500
    
    # Gamma
    gamma_api_key: str
    
    # Timezone
    timezone: str = "America/Los_Angeles"  # Pacific Time
```

---

# What to Review

## Critical Questions for QA

1. **Does the complete pipeline work end-to-end?**
   - UI → Backend → CLI → Fetch → Agents → Format → Gamma

2. **Do examples actually appear in the output?**
   - Check both markdown and Gamma presentation

3. **Does Horatio detection work?**
   - Should show horatio count > 0 in logs

4. **Does Gamma generation succeed?**
   - Should return URL and create presentation

5. **Are sentiment insights actually nuanced?**
   - Not generic "negative sentiment"
   - Show "appreciate X BUT frustrated by Y" pattern

## Specific Code to Review

1. **ExampleExtractionAgent line 265-280** - Timestamp handling
2. **TopicOrchestrator lines 155-157** - Empty topic skipping
3. **SegmentationAgent lines 198-220** - Horatio email extraction
4. **Gamma client lines 115-150** - API request construction
5. **Main.py line 2463** - Import path (should be `src.services`)

## Test Commands

```bash
# Minimal test (fake data)
test-mode --test-type topic-based --num-conversations 50

# Real data test (small)
voice-of-customer --time-period yesterday

# Full test with Gamma
voice-of-customer --time-period yesterday --generate-gamma

# Agent performance
agent-performance --agent horatio --time-period week
```

---

# Summary for External Reviewer

This is a complex multi-agent AI system with:
- 7 specialized agents (5 use LLMs)
- 3 API integrations (Intercom, OpenAI, Gamma)
- Parallel processing for speed
- Executive report generation

**Main concerns:**
1. Examples extraction may be broken (timestamp bug - fixed but needs verification)
2. Horatio detection returns 0 (email extraction - fixed but needs testing)
3. Empty topics waste LLM calls (fixed - skip logic added)
4. Gamma generation success unknown (multiple fixes applied)
5. Import paths may still have issues (fixed 5 instances)

**Recommendation:** Test the `test-mode` command first to verify agents work with controlled data before testing with real Intercom data.

The codebase is large but the core pipeline is straightforward. If any agent fails, the whole pipeline fails. Focus testing on:
1. Does each agent return valid data?
2. Do agents handle edge cases (empty data, missing fields)?
3. Does the final output match expectations?
