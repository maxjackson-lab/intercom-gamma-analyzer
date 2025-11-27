# Legacy Agent Optimization Prompt

**Role:** Senior AI Architect
**Task:** Audit and upgrade the "legacy" agents (`SentimentAgent`, `ChurnRiskAgent`) to match the new high standards set by `TopicDetectionAgent`.

## Context
We have optimized the core topic detection and sentiment analysis for the *Topic-Based* workflow. However, the *Standard* Multi-Agent workflow relies on older agents that use generic prompts, lack cost optimization, and produce flatter insights.

## Targets for Upgrade

### 1. SentimentAgent (`src/agents/sentiment_agent.py`)
**Current State:**
- Uses generic "Positive/Negative/Neutral" classification.
- Lacks the "Hilary-style" nuance (e.g., "Users appreciate X but are frustrated by Y").
- No few-shot examples or cost optimization metrics.

**Upgrade Plan:**
- **Adhere to Style:** Update `get_agent_specific_instructions` to enforce the "one-sentence, nuanced, actionable" style used in `TopicSentimentAgent`.
- **Global vs. Local:** Adapt the style to apply *globally* (e.g., "Overall, users are satisfied with stability but increasingly vocal about billing transparency").
- **Prompt Hardening:** Inject few-shot examples of *global* sentiment summaries.
- **Metrics:** Track token usage and execution time explicitly.

### 2. ChurnRiskAgent (`src/agents/churn_risk_agent.py`)
**Current State:**
- Uses regex (good) + generic LLM prompt (weak).
- "Analyze this customer conversation..." is too broad.

**Upgrade Plan:**
- **Structured Output:** Force the LLM to return a JSON object with `risk_assessment`, `key_concern`, and `suggested_action` instead of free text.
- **Few-Shot:** Provide examples of "Explicit Churn" vs. "Empty Threat" to reduce false positives.
- **Cost Control:** Ensure LLM is ONLY called when regex signals are found (current logic does this, but verify).

### 3. CategoryAgent (`src/agents/category_agent.py`)
**Status:** **DEPRECATION WARNING**
- This agent appears redundant with the new, superior `TopicDetectionAgent`.
- **Action:** Do NOT optimize. Instead, add a `DeprecationWarning` to the `__init__` method advising use of `TopicDetectionAgent` for future workflows.

## Implementation Checklist
1.  [ ] **SentimentAgent:** Update prompt to forbid "mixed sentiment" and require specific "X but Y" structure.
2.  [ ] **ChurnRiskAgent:** Update `_analyze_conversation_with_llm` to use a strict JSON schema (or structured prompt) and retries.
3.  [ ] **Verification:** Run `python src/main.py multi-agent ...` and check if the sentiment output in the logs/report improves.

## Goal
Ensure that users running the *Standard* workflow get 80% of the quality benefits of the *Topic* workflow without a full rewrite.



