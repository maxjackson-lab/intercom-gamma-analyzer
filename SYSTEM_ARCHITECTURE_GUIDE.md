# System Architecture Guide
## ETL Pipeline & Multi-Agent Network Implementation

**Audience:** Product Managers, Technical Leadership  
**Last Updated:** November 4, 2025  
**Version:** 2.0 (Post-Schema Improvements)

---

## Table of Contents
1. [System Overview](#system-overview)
2. [ETL Pipeline Architecture](#etl-pipeline-architecture)
3. [Multi-Agent Network](#multi-agent-network)
4. [Data Flow & Coordination](#data-flow--coordination)
5. [Key Design Decisions](#key-design-decisions)
6. [Assumptions & Constraints](#assumptions--constraints)

---

## System Overview

### What This System Does

This is a **data analysis platform** that:
1. **Extracts** customer conversation data from Intercom
2. **Transforms** raw conversations into structured insights
3. **Loads** data into an analytical database (DuckDB)
4. **Analyzes** conversations using specialized AI agents
5. **Generates** actionable reports and presentations

### Why It's Built This Way

**Traditional approach** (what we replaced):
- Single monolithic script
- Linear processing (one step after another)
- No specialization (everything in one place)
- Hard to debug, harder to improve
- **Result:** Brittle, slow, difficult to maintain

**Our approach** (current architecture):
- **ETL Pipeline** for data management
- **Multi-Agent Network** for specialized analysis
- **Modular components** that can be improved independently
- **Clear separation of concerns**
- **Result:** Reliable, scalable, maintainable

---

## ETL Pipeline Architecture

### The Three Phases

#### 1. **Extract** (Data Collection)
**What it does:** Pulls conversation data from Intercom's API

**Key components:**
- `IntercomSDKService` - Official Intercom SDK wrapper
- Rate limiting & retry logic
- Incremental fetch (date-based)
- Enrichment (fetches additional details per conversation)

**Data collected:**
- Conversation metadata (ID, dates, state)
- Customer messages
- Agent responses
- CSAT ratings
- Custom attributes (tier, language, topic tags)
- **New:** SLA data, channel info, wait times, Fin content sources

**Why enrichment matters:**
- Initial API call gives basic data
- Enrichment fetches `conversation_parts` (full message history)
- Enrichment fetches contact details (customer tier, segments)
- **Trade-off:** 150 API calls for 50 conversations (1 search + 50 convs + 50 contacts + 50 segments)

#### 2. **Transform** (Data Cleaning & Normalization)
**What it does:** Standardizes data for analysis

**Key operations:**
```
Raw Data → Validation → Normalization → Cleaning → Storage-Ready
```

**Specific transformations:**
- **Timestamp normalization** - Converts Unix timestamps to timezone-aware UTC datetimes
- **conversation_parts shape normalization** - SDK returns inconsistent formats (list vs dict), we standardize to `{'conversation_parts': [...]}`
- **HTML cleaning** - Removes HTML tags from message bodies
- **Field extraction** - Pulls nested data (e.g., `conversation_rating.remark`, `ai_agent.content_sources[]`)
- **Default handling** - Ensures missing fields don't break downstream analysis

**Why this matters:**
- Intercom's SDK has inconsistencies (we discovered `conversation_parts` shape issue)
- CSAT ratings can be dict `{'rating': 5, 'remark': '...'}` or direct int `5`
- Missing SLA data shouldn't crash the pipeline
- Clean data = reliable analysis

#### 3. **Load** (Storage)
**What it does:** Stores processed data in DuckDB (analytical database)

**Schema design:**
```sql
conversations (main table)
├─ Basic fields (id, dates, state, priority)
├─ Performance metrics (response time, resolution time)
├─ CSAT data (rating + remark text)
├─ AI fields (Fin resolution state, content sources)
└─ New fields (SLA, channel, wait times, assignments)

conversation_tags (normalized)
conversation_topics (normalized)
conversation_categories (normalized)
technical_patterns (extracted)
escalations (tracked)
```

**Why DuckDB?**
- **Analytical workload optimized** (vs transactional like PostgreSQL)
- **Columnar storage** = fast aggregations
- **Embedded** = no separate database server
- **SQL interface** = familiar query language
- **Trade-off:** Not for real-time updates, but perfect for batch analysis

**Storage workflow:**
1. Batch insert (1000 conversations at a time)
2. Normalize related data (tags, topics, categories)
3. Extract patterns (cache clearing, escalations)
4. Index for query performance

---

## Multi-Agent Network

### Design Philosophy

**Problem:** Complex analysis requires multiple perspectives  
**Solution:** Specialized agents, each expert in one domain  
**Benefit:** Modular, maintainable, improvable

### Agent Roster & Responsibilities

#### **Tier 1: Data & Foundation Agents**

##### 1. **DataAgent** 
**Role:** Data Acquisition Specialist

**Responsibilities:**
- Orchestrates ETL pipeline
- Validates data quality (checks for missing fields)
- Calculates confidence scores (how complete is our data?)
- Provides data to downstream agents

**Output:**
```json
{
  "conversations": [...],
  "stats": {
    "conversations_count": 150,
    "extraction_time": 45.2,
    "data_quality_score": 0.95
  },
  "missing_fields": ["conversation_rating: 30%"]
}
```

**Why it exists:** Separate data concerns from analysis concerns. If Intercom API changes, we only update DataAgent.

##### 2. **SegmentationAgent**
**Role:** Customer Classification Specialist

**Responsibilities:**
- Segments by customer tier (Free, Pro, Enterprise)
- Tracks agent attribution (Fin AI vs Horatio vs Boldr vs Sal)
- Identifies escalation patterns (Fin → Vendor → Senior Staff)
- Flags VIP customers

**Output:**
```json
{
  "tier_breakdown": {
    "enterprise": {"count": 50, "percentage": 33.3},
    "pro": {"count": 75, "percentage": 50.0},
    "free": {"count": 25, "percentage": 16.7}
  },
  "agent_attribution": {
    "fin_ai": 60,
    "horatio": 40,
    "boldr": 30,
    "sal": 10,
    "gamma_cx": 10
  }
}
```

**Why it exists:** Customer context matters. Enterprise customers with bad CSAT = critical. Free tier with bad CSAT = less urgent. Agent performance varies by vendor.

#### **Tier 2: Analysis Agents**

##### 3. **TopicDetectionAgent**
**Role:** Topic Classification Specialist

**Responsibilities:**
- Classifies conversations into taxonomy (Billing, API, Sites, etc.)
- Detects subtopics (e.g., Billing → Refund, Billing → Invoice)
- Uses both tags (reliable) and AI classification (flexible)
- Calculates confidence per classification

**Method:**
1. Check Intercom tags first (high confidence: 0.9)
2. Check custom attributes `Reason for contact` (high confidence: 0.85)
3. If neither exist, use AI classification (medium confidence: 0.7)

**Why it exists:** Topics drive everything. "What are customers talking about?" is the first question. Without accurate topic detection, all downstream analysis is unreliable.

##### 4. **SubTopicDetectionAgent**
**Role:** Deep Classification Specialist

**Responsibilities:**
- Drills deeper into topics (Billing → Refund → Subscription Cancellation)
- Identifies 2-3 tier topic hierarchies
- Cross-references with multiple signals (tags, custom attrs, text)

**Example hierarchy:**
```
Billing (Tier 1)
├─ Refund (Tier 2)
│  ├─ Subscription Cancellation (Tier 3)
│  └─ Partial Refund Request (Tier 3)
└─ Invoice (Tier 2)
   ├─ Missing Invoice (Tier 3)
   └─ Incorrect Amount (Tier 3)
```

**Why it exists:** Surface-level topics aren't actionable. "We have billing issues" → useless. "We have subscription cancellation refund issues in enterprise tier" → actionable.

##### 5. **TopicSentimentAgent**
**Role:** Sentiment Analysis Specialist

**Responsibilities:**
- Analyzes sentiment per topic (not overall)
- Extracts customer emotion (frustrated, satisfied, confused)
- Handles 46+ languages
- Provides confidence scores

**Method:**
1. Extract customer messages only (ignore agent responses)
2. Send to OpenAI/Claude with topic context
3. Get sentiment + confidence + reasoning
4. Cross-reference with CSAT if available

**Output:**
```json
{
  "topic": "Billing",
  "sentiment": "negative",
  "confidence": 0.85,
  "reasoning": "Customer expressed frustration about unexpected charges",
  "emotion_indicators": ["frustrated", "disappointed"],
  "csat_alignment": true
}
```

**Why it exists:** Sentiment drives prioritization. High-volume topic with negative sentiment = urgent. Low-volume with negative sentiment = monitor. CSAT alone misses nuance (only 10-20% of conversations get rated).

##### 6. **ExampleExtractionAgent**
**Role:** Evidence Curator

**Responsibilities:**
- Finds representative quotes per topic
- Extracts "worst" and "best" examples
- Validates quotes are real (no hallucinations)
- Provides conversation links

**Selection criteria:**
- Representative (typical of the topic)
- Impactful (shows the issue clearly)
- Concise (readable in reports)
- Verified (actually from the conversation)

**Why it exists:** Numbers without stories are forgettable. "CSAT dropped 15%" → abstract. "CSAT dropped 15% - customer said 'I've been waiting 3 days for a response'" → concrete and actionable.

##### 7. **FinPerformanceAgent**
**Role:** AI Agent Performance Analyst

**Responsibilities:**
- Analyzes Fin AI (Intercom's chatbot) performance
- Categorizes outcomes: **resolved / escalated / failed**
- Identifies knowledge gaps (what Fin can't answer)
- Recommends training content

**New nuanced logic** (as of Nov 4, 2025):
```
✅ Resolved (35%): Fin handled alone, customer satisfied
   - No human admin involved
   - Closed or low engagement
   - No bad CSAT
   - Confidence: 0.85

❓ Escalated (45%): Passed to human - ambiguous outcome
   - Human admin involved
   - Fin routed to team OR customer asked for human
   - We can't determine if escalation was "correct"
   - Confidence: 0.65

❌ Failed (20%): Fin tried but bad outcome
   - Bad CSAT (< 3 stars)
   - Multiple reopens
   - Customer frustrated
   - Confidence: 0.80
```

**Why it exists:** 
- Fin handles 50-70% of conversations
- Understanding what Fin can/can't do = cost savings
- **Critical insight:** We're honest about uncertainty (escalations are ambiguous, not "successes")
- Knowledge gap detection drives Fin training priorities

##### 8. **TrendAgent**
**Role:** Time-Series Pattern Analyst

**Responsibilities:**
- Tracks metrics over time (day, week, month)
- Identifies trends (increasing, decreasing, stable)
- Detects anomalies (spikes, drops)
- Compares periods (week-over-week, month-over-month)

**Output:**
```json
{
  "volume_trend": {
    "direction": "increasing",
    "change_pct": 15.3,
    "significance": "high",
    "insight": "Billing conversations increased 15% week-over-week"
  },
  "sentiment_trend": {
    "direction": "declining",
    "change_pct": -8.2,
    "significance": "medium",
    "insight": "API sentiment declining, investigate recent changes"
  }
}
```

**Why it exists:** Point-in-time snapshots miss the story. "100 billing issues" → is that normal? "100 billing issues, up 50% from last week" → urgent investigation needed.

#### **Tier 3: Synthesis & Output Agents**

##### 9. **InsightAgent**
**Role:** Cross-Agent Synthesis Specialist

**Responsibilities:**
- Combines outputs from all analysis agents
- Identifies cross-cutting patterns (e.g., Enterprise tier + Billing + Negative sentiment)
- Generates actionable recommendations
- Prioritizes issues by impact

**Synthesis example:**
```
Input:
- TopicDetectionAgent: Billing volume = 50 conversations
- SegmentationAgent: 80% are Enterprise tier
- SentimentAgent: 85% negative sentiment
- FinPerformanceAgent: Fin escalation rate = 90%
- TrendAgent: Volume up 40% week-over-week

Output:
Priority: CRITICAL
Issue: Enterprise billing escalations spiking
Impact: High-value customers experiencing issues Fin can't resolve
Recommendation: 
1. Immediate: Review recent billing changes
2. Short-term: Train Fin on new billing scenarios
3. Long-term: Improve enterprise billing documentation
```

**Why it exists:** Individual agents see trees, InsightAgent sees the forest. Human analysts would do this synthesis manually - we automate it while maintaining transparency about reasoning.

##### 10. **OutputFormatterAgent**
**Role:** Report Generation Specialist

**Responsibilities:**
- Formats analysis for different audiences (executive, detailed, coaching)
- Generates Gamma presentation markdown
- Creates Excel/CSV exports
- Structures JSON for API consumption

**Output formats:**
- **Executive:** High-level metrics, key insights, recommendations (1-2 pages)
- **Detailed:** Full analysis with examples, breakdowns, confidence scores (10-20 pages)
- **Coaching:** Agent performance by topic, improvement areas, training needs
- **Data:** Raw JSON, CSV for further analysis

**Why it exists:** Same analysis, different audiences. Executives want summary, analysts want details, trainers want coaching insights. One analysis, multiple perspectives.

---

## Data Flow & Coordination

### Sequential Workflow (Current Implementation)

```
┌─────────────────────────────────────────────────────────┐
│                   USER INITIATES ANALYSIS                │
│   (CLI command or Railway web interface)                │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│  PHASE 1: DATA COLLECTION                               │
│  ┌──────────────────────────────────────────────────┐  │
│  │  DataAgent                                        │  │
│  │  • Extracts from Intercom (50-500 convs/min)    │  │
│  │  • Enriches with conversation_parts              │  │
│  │  • Transforms (normalize, clean, validate)       │  │
│  │  • Loads into DuckDB                            │  │
│  │  Duration: 30-120s for 150 conversations        │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                          ↓
                   conversations[]
                          ↓
┌─────────────────────────────────────────────────────────┐
│  PHASE 2: SEGMENTATION & CLASSIFICATION                 │
│  ┌──────────────────────────────────────────────────┐  │
│  │  SegmentationAgent                                │  │
│  │  • Customer tier breakdown                        │  │
│  │  • Agent attribution                              │  │
│  │  • Escalation tracking                            │  │
│  │  Duration: 2-5s                                  │  │
│  └──────────────────────────────────────────────────┘  │
│                          ↓                              │
│  ┌──────────────────────────────────────────────────┐  │
│  │  TopicDetectionAgent                             │  │
│  │  • Primary topic classification                   │  │
│  │  • Confidence scoring                             │  │
│  │  Duration: 5-15s (AI calls)                      │  │
│  └──────────────────────────────────────────────────┘  │
│                          ↓                              │
│  ┌──────────────────────────────────────────────────┐  │
│  │  SubTopicDetectionAgent                          │  │
│  │  • Tier 2 & 3 classification                      │  │
│  │  • Subtopic hierarchy                             │  │
│  │  Duration: 10-20s (AI calls)                     │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                          ↓
              conversations[] + topics + tiers
                          ↓
┌─────────────────────────────────────────────────────────┐
│  PHASE 3: ANALYSIS                                       │
│  ┌──────────────────────────────────────────────────┐  │
│  │  TopicSentimentAgent                             │  │
│  │  • Per-topic sentiment analysis                   │  │
│  │  • Customer emotion extraction                    │  │
│  │  • 46+ languages supported                        │  │
│  │  Duration: 15-30s (AI calls)                     │  │
│  └──────────────────────────────────────────────────┘  │
│                          ↓                              │
│  ┌──────────────────────────────────────────────────┐  │
│  │  ExampleExtractionAgent                          │  │
│  │  • Representative quotes                          │  │
│  │  • Best/worst examples                            │  │
│  │  Duration: 10-20s (AI calls)                     │  │
│  └──────────────────────────────────────────────────┘  │
│                          ↓                              │
│  ┌──────────────────────────────────────────────────┐  │
│  │  FinPerformanceAgent                             │  │
│  │  • Fin outcome categorization (resolved/esc/fail) │  │
│  │  • Knowledge gap detection                        │  │
│  │  Duration: 5-10s                                 │  │
│  └──────────────────────────────────────────────────┘  │
│                          ↓                              │
│  ┌──────────────────────────────────────────────────┐  │
│  │  TrendAgent                                       │  │
│  │  • Time-series analysis                           │  │
│  │  • Pattern detection                              │  │
│  │  Duration: 5-10s                                 │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                          ↓
              all_agent_results{}
                          ↓
┌─────────────────────────────────────────────────────────┐
│  PHASE 4: SYNTHESIS & OUTPUT                            │
│  ┌──────────────────────────────────────────────────┐  │
│  │  InsightAgent                                     │  │
│  │  • Cross-agent synthesis                          │  │
│  │  • Prioritization                                 │  │
│  │  • Recommendations                                │  │
│  │  Duration: 10-15s (AI calls)                     │  │
│  └──────────────────────────────────────────────────┘  │
│                          ↓                              │
│  ┌──────────────────────────────────────────────────┐  │
│  │  OutputFormatterAgent                            │  │
│  │  • Generate Gamma markdown                        │  │
│  │  • Create Excel/CSV exports                       │  │
│  │  • Structure JSON output                          │  │
│  │  Duration: 2-5s                                  │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│  DELIVERY                                                │
│  • Gamma presentation (if enabled)                      │
│  • JSON file (always)                                   │
│  • Excel/CSV (optional)                                 │
│  • CLI summary (always)                                 │
└─────────────────────────────────────────────────────────┘
```

**Total duration:** 90-180 seconds for 150 conversations

### Why Sequential (Not Parallel)?

**Current:** Agents run one after another  
**Alternative:** Run agents in parallel (faster)

**Why we chose sequential:**
1. **Dependencies:** SentimentAgent needs TopicDetectionAgent's output
2. **API rate limits:** Parallel AI calls could hit OpenAI rate limits
3. **Debugging:** Easier to trace issues when execution is linear
4. **Cost:** Parallel = higher concurrent API calls = higher cost risk

**Future:** Can parallelize independent agents (TopicSentiment + ExampleExtraction + Fin Performance)

### Agent Communication Protocol

**Method:** Shared context object (AgentContext)

```python
class AgentContext:
    analysis_id: str
    start_date: datetime
    end_date: datetime
    conversations: List[Dict]  # Shared data
    results: Dict[str, Any]    # Agent outputs accumulate here
```

**Flow:**
1. Agent receives context
2. Agent processes data
3. Agent adds results to context.results['AgentName']
4. Next agent receives updated context
5. Repeat

**Why this approach:**
- **Simple:** No message queues, no event buses
- **Transparent:** Easy to inspect state at any point
- **Testable:** Each agent is pure function (input → output)
- **Trade-off:** Not async, but simplicity > speed for our scale

---

## Key Design Decisions

### 1. **ELT vs ETL**

**Choice:** ELT (Extract-Load-Transform)  
**Alternative:** ETL (Extract-Transform-Load)

**Rationale:**
- **Load raw data first** → Can re-transform without re-fetching from Intercom
- **DuckDB** handles transformations efficiently (SQL-based)
- **Flexibility** → Add new transformations without re-extraction
- **Backup** → Raw JSON stored for debugging

**Trade-off:** More storage space (raw + transformed) but worth it for flexibility

### 2. **DuckDB vs PostgreSQL/MySQL**

**Choice:** DuckDB  
**Alternative:** Traditional RDBMS

**Rationale:**
- **Analytical workload** (aggregations, not transactions)
- **Embedded** (no separate server process)
- **Columnar storage** (10x faster for our queries)
- **Development simplicity** (SQLite-like, single file)

**Trade-off:** Not suitable for concurrent writes, but we're batch-processing

### 3. **Custom Agents vs Framework (LangChain/AutoGen)**

**Choice:** Custom implementation  
**Alternative:** Agent framework

**Rationale:**
- **Control:** Know exactly what happens at each step
- **Minimal dependencies:** Frameworks add 50+ packages
- **Railway deployment:** Smaller Docker image, faster cold starts
- **Debugging:** No framework magic to debug
- **Learning curve:** Team doesn't need to learn framework

**Trade-off:** We implement orchestration manually, but it's only 200 lines

### 4. **Sequential vs Parallel Agent Execution**

**Choice:** Sequential (for now)  
**Alternative:** Parallel execution

**Rationale:**
- **Dependencies:** Many agents need previous agent outputs
- **Rate limits:** OpenAI has per-minute limits
- **Simplicity:** Linear flow easier to debug
- **Cost control:** Prevents parallel API call spikes

**Future:** Hybrid (parallel where possible, sequential where needed)

### 5. **Fin Analysis: Three-Way Categorization**

**Choice:** Resolved / Escalated / Failed  
**Alternative:** Binary (Resolved / Not Resolved)

**Rationale:**
- **Honest about uncertainty:** Escalations are ambiguous
- **Confidence levels:** Show 0.6-0.9 to indicate certainty
- **Not overcorrecting:** Don't claim escalations are "correct"
- **Actionable:** "Escalated" flags cases for manual review

**Key principle:** "Don't hide the unknown - make it part of the story"

### 6. **Conversation Parts Normalization**

**Choice:** Always normalize to `{'conversation_parts': [...]}`  
**Alternative:** Handle both formats everywhere

**Rationale:**
- **SDK inconsistency:** Sometimes returns list, sometimes dict
- **Defensive programming:** Normalize at entry point (SDK service)
- **Downstream simplicity:** All code assumes consistent shape
- **Error prevention:** One place to handle edge cases

**Implementation:** Two normalization points (SDK service + preprocessor)

### 7. **Priority-Based Status Updates (Railway)**

**Choice:** Status priority system  
**Alternative:** Last-write-wins

**Rationale:**
- **Intermediate errors:** Warnings shouldn't overwrite success
- **Status hierarchy:** COMPLETED > ERROR > RUNNING > PENDING
- **User experience:** Don't show "ERROR" for successful executions
- **Transparency:** Log when updates are skipped

**Example:** Command completes (COMPLETED), cleanup logs error → status stays COMPLETED

---

## Assumptions & Constraints

### Core Assumptions (From Feedback & Codebase)

#### 1. **Intercom as Source of Truth**
**Assumption:** Intercom's data is authoritative and complete  
**Validation:** We check data quality but don't dispute Intercom's records  
**Risk:** If Intercom has data issues, we'll propagate them  
**Mitigation:** Data quality scoring, confidence levels, validation checks

#### 2. **Fin Escalation ≠ Fin Failure**
**Feedback received:** "Fin solves NOTHING - you're treating escalation as failure but it's just Fin knowing its limits"  
**Assumption corrected:** Escalations are ambiguous, not failures  
**Implementation:** Three-way categorization (resolved/escalated/failed) with confidence  
**Philosophy:** Be honest about what we don't know rather than overcorrecting

#### 3. **CSAT is Sparse**
**Observed:** Only 10-20% of conversations get rated  
**Assumption:** Missing CSAT ≠ neutral sentiment  
**Implementation:** Use AI sentiment analysis for all conversations, cross-reference with CSAT when available  
**Risk:** AI sentiment may not match customer's true feeling

#### 4. **Agent Attribution Matters**
**Feedback pattern:** Distinguish between Fin AI, Sal, Horatio, Boldr, Gamma CX  
**Assumption:** Performance varies by agent/vendor  
**Implementation:** SegmentationAgent tracks attribution, performance calculated per agent  
**Use case:** Vendor performance comparison, Fin training prioritization

#### 5. **Customer Tier Drives Prioritization**
**Observed:** Enterprise issues mentioned more urgently  
**Assumption:** Enterprise tier issues are higher priority than Free tier  
**Implementation:** Tier-based segmentation, weighted prioritization  
**Validation:** Explicitly stated in coaching reports ("Enterprise customers experiencing...")

#### 6. **Topics from Tags > AI Classification**
**Observed:** Intercom tags are manually curated by support team  
**Assumption:** Human-tagged topics are more reliable than AI classification  
**Implementation:** Check tags first (confidence 0.9), fall back to AI (confidence 0.7)  
**Risk:** Untagged conversations get lower-confidence classification

#### 7. **conversation_parts is Critical**
**Discovery:** Search API doesn't return full conversation messages  
**Assumption:** Need full message history for accurate analysis  
**Implementation:** Per-conversation fetch to get conversation_parts (151 API calls for 50 conversations)  
**Trade-off:** 3x more API calls but necessary for Sal detection, topic detection, sentiment analysis

#### 8. **Polling Can Show False Failures**
**Observed:** Successful operations showing as "ERROR" in Railway UI  
**Assumption:** Intermediate errors (warnings, cleanup) shouldn't override final success status  
**Implementation:** Priority-based status updates (COMPLETED can't be overwritten by ERROR)  
**Use case:** Gamma generation completes successfully, cleanup logs warning → still shows COMPLETED

#### 9. **Multi-Language Support is Table Stakes**
**Implicit from 46+ languages:** Customers communicate in many languages  
**Assumption:** AI can handle multilingual sentiment analysis accurately  
**Implementation:** No language pre-filtering, let AI detect and analyze  
**Validation:** Confidence scores show AI is 80-90% accurate across languages

#### 10. **Trends Matter More Than Point-in-Time**
**Feedback pattern:** "Is this normal?" questions  
**Assumption:** Without historical context, metrics are meaningless  
**Implementation:** TrendAgent tracks week-over-week, month-over-month  
**Example:** "100 billing issues" → "100 billing issues, up 40% from last week"

### Technical Constraints

#### 1. **Intercom API Rate Limits**
**Official limit:** 10,000 calls/minute (private app)  
**Practical limit:** ~83 operations per 10 seconds (distributed)  
**Impact:** Enrichment takes 20+ seconds for 50 conversations  
**Mitigation:** Semaphore-based concurrency control, request pacing

#### 2. **OpenAI Rate Limits**
**Tier-dependent:** Varies by account tier  
**Typical:** 3,500 requests/minute  
**Impact:** Can't parallelize all AI agent calls  
**Mitigation:** Sequential execution, fallback to Claude if OpenAI fails

#### 3. **Railway Deployment**
**Memory:** 512MB default (can scale)  
**CPU:** Shared (not dedicated)  
**Cold starts:** 2-3 seconds  
**Impact:** Keep Docker image small, minimize dependencies  
**Mitigation:** Custom agents (not frameworks), lazy initialization

#### 4. **DuckDB Single-Writer**
**Constraint:** Only one write process at a time  
**Impact:** Can't have concurrent analysis runs  
**Mitigation:** Analysis runs are sequential anyway, not an issue for our use case

#### 5. **Gamma API is Asynchronous**
**Constraint:** Generate → Poll → Wait (can take 2-5 minutes)  
**Impact:** User sees "Generating..." for several minutes  
**Mitigation:** SSE (Server-Sent Events) for real-time updates, status tracking

### Data Quality Constraints

#### 1. **Conversation Parts Shape Inconsistency**
**Issue:** SDK returns different shapes (list vs dict)  
**Impact:** Code breaks if not normalized  
**Solution:** Normalize at two points (SDK service + preprocessor)

#### 2. **Missing Custom Attributes**
**Issue:** Not all conversations have `Reason for contact`, tier, language  
**Impact:** Topic detection, segmentation less accurate  
**Solution:** Confidence scoring, multiple signals (tags + custom attrs + AI)

#### 3. **SLA Data is Optional**
**Issue:** `sla_applied` may be null  
**Impact:** Can't always track SLA performance  
**Solution:** Graceful handling, report coverage percentage

#### 4. **Fin Resolution State is Metadata**
**Issue:** `ai_agent.resolution_state` is Intercom's classification, not ground truth  
**Impact:** We trust Intercom's categorization of "routed_to_team"  
**Solution:** Cross-validate with other signals (human admin parts, CSAT)

### Business Assumptions

#### 1. **Analysis is Batch, Not Real-Time**
**Assumption:** Users run analysis weekly/daily, not continuously  
**Impact:** Optimize for thoroughness over speed  
**Validation:** CLI tool design (run → wait → results), not streaming

#### 2. **Reports are Human-Consumed**
**Assumption:** Output is for people (PMs, executives, trainers), not machines  
**Impact:** Prioritize readability, insights, recommendations over raw data  
**Implementation:** Executive summaries, coaching insights, example quotes

#### 3. **Cost Matters**
**Assumption:** Keep AI costs reasonable (OpenAI charges per token)  
**Impact:** Don't over-analyze, use caching where possible  
**Implementation:** Field selection (only fetch needed Intercom fields), prompt optimization

#### 4. **Trust is Earned**
**Assumption:** Users won't trust "black box" AI analysis  
**Impact:** Show confidence scores, reasoning, source data  
**Implementation:** Confidence levels (0.6-0.9), Intercom links, example quotes, signal transparency

---

## Summary

### What Makes This Architecture Work

1. **Clear Separation of Concerns**
   - ETL handles data (extraction, transformation, loading)
   - Agents handle analysis (specialized, focused)
   - Orchestrator handles coordination (workflow, checkpoints)

2. **Modularity**
   - Replace TopicDetectionAgent without touching SentimentAgent
   - Improve Fin logic without touching ETL pipeline
   - Add new agents without rewriting existing ones

3. **Transparency**
   - Confidence scores show certainty
   - Example quotes show evidence
   - Intercom links show source data
   - Reasoning explains decisions

4. **Honest About Uncertainty**
   - Escalations are ambiguous (not "success")
   - Low confidence scores flag uncertain analysis
   - Missing data reported explicitly

5. **Built for Maintenance**
   - Each component is <1000 lines
   - Clear interfaces (AgentContext in → AgentResult out)
   - Testable (unit tests per agent)
   - Debuggable (linear workflow, clear logs)

### Key Principles

1. **Don't hide the unknown - make it part of the story**
2. **Automate what machines do well, assist where humans excel**
3. **Fast enough is better than perfect**
4. **Confidence matters as much as the answer**
5. **Context drives everything (tier, topic, trend)**

---

**Version:** 2.0 (Post-Schema Improvements + Fin Nuance + Polling Fix)  
**Last Updated:** November 4, 2025

