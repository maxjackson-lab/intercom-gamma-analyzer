# Master System Optimization Prompt

**Role:** Senior AI Architect & Engineering Lead
**Traycer Mode Recommendation:** Use **"Phases"** mode.
*Why?* This is a massive, multi-system refactor. "Phases" mode will correctly break this down into manageable chunks (Upstream Core, Downstream Output, Legacy Modernization) rather than trying to generate a brittle 50-file plan in one shot.

**Task:** Execute a comprehensive system-wide optimization of the Intercom Analysis Tool, covering upstream detection logic, downstream output generation, and legacy agent modernization.

---

## Part 1: Upstream Core Optimizations
**Context:** We have refactored `TopicDetectionAgent` and `TopicSentimentAgent` for high accuracy and efficiency. Now we must ensure these improvements are fully realized and hardened.

### 1.1 Dynamic Topic Ranking (Self-Learning)
**File:** `src/agents/topic_detection_agent.py`
**Logic:**
- Query DuckDB for real-time topic counts (`_get_dynamic_ranking`).
- Merge dynamic stats with static "expert knowledge".
- Sort topics by frequency to optimize LLM prompt attention.
**Action:** Verify robust handling of missing/locked DB states (`read_only=True`).

### 1.2 Confidence-Based Routing (Cost Optimization)
**File:** `src/agents/topic_detection_agent.py`
**Logic:**
- Calculate keyword/SDK confidence score.
- **Optimization:** If `confidence > 0.85`, skip LLM call (target: 30% cost reduction).
- **Metrics:** Track `high_confidence_skip_count` and log estimated savings.
**Action:** Ensure metrics are aggregated in `execute()` and visible in run logs.

### 1.3 Adaptive Few-Shot & Chain-of-Thought
**File:** `src/agents/topic_detection_agent.py`
**Logic:**
- **Smart Prompting:** Inject few-shot examples only when keyword signals are weak.
- **Chain-of-Thought:** Trigger `low_confidence_mode` (explain reasoning first) for ambiguous cases (<0.6 confidence).
**Action:** Verify prompt injection doesn't break JSON parsing.

### 1.4 Multi-Language Support
**File:** `src/config/taxonomy.py`
**Logic:**
- Extend `Account`, `Billing`, `Bug`, etc., with high-signal Russian/Korean keywords based on real data (~14% of volume).
**Action:** Validate keyword matching works for non-ASCII characters.

---

## Part 2: Downstream Output Optimization
**Context:** Upstream agents now produce rich, nuanced data (e.g., "Users love X but hate Y"). Downstream agents must preserve this fidelity.

### 2.1 PresentationAgent (`src/agents/presentation_agent.py`)
**Action:** Stop re-writing sentiment insights.
- **Logic:** Extract `sentiment_insight` from `TopicSentimentAgent` results and use it **verbatim** in Gamma slides.
- **Visuals:** Add "Methodology" slide showcasing "Analysis Confidence" and "Optimization Efficiency" (from `fallback_metrics`).

### 2.2 Gamma Generator (`src/services/gamma_generator.py`)
**Action:** Visualize Subtopics.
- **Logic:** Group category bullets by specific `subtopic` (e.g., "Refund Requests (30%)" instead of generic "Billing Issues").

### 2.3 InsightAgent (`src/agents/insight_agent.py`)
**Action:** Qualify insights with detection method.
- **Logic:** Tag findings: "(Verified by AI Analysis)" vs "(Trend detected via keyword patterns)" based on `detection_method`.

---

## Part 3: Legacy Agent Modernization
**Context:** Ensure the *Standard* workflow doesn't lag behind the *Topic* workflow.

### 3.1 SentimentAgent (`src/agents/sentiment_agent.py`)
**Upgrade Plan:**
- Enforce "Hilary-style" (nuanced, actionable) output in `get_agent_specific_instructions`.
- Forbid generic "mixed sentiment" or "positive/negative" labels.
- Inject global sentiment examples.

### 3.2 ChurnRiskAgent (`src/agents/churn_risk_agent.py`)
**Upgrade Plan:**
- **Structured Output:** Force LLM to return JSON (`risk_assessment`, `key_concern`, `suggested_action`).
- **Few-Shot:** Differentiate "Explicit Churn" vs "Empty Threat" with examples.

### 3.3 CategoryAgent (`src/agents/category_agent.py`)
**Status:** **DEPRECATION**
- **Action:** Add `DeprecationWarning` to `__init__`. Advise use of `TopicDetectionAgent`.

---

## Verification Plan
1.  **Run Sample Analysis:** `python src/main.py sample-mode --count 50 --save-to-file`
2.  **Check Logs:** Look for "Confidence Routing: Skipped LLM for X conversations".
3.  **Check JSON:** Confirm `sentiment_insight` contains nuanced sentences, not generic labels.
4.  **Check Presentation:** Verify slide headers match the nuanced sentiment verbatim.
5.  **Run Tests:** Ensure `tests/test_prompt_optimization.py` passes.

## Goal
A unified, high-performance agent system where upstream intelligence flows losslessly to executive deliverables, with transparent cost/quality metrics.

