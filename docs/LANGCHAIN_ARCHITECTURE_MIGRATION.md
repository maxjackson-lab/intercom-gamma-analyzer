# LangChain Architecture Migration Guide

**Status:** Implementation Complete
**Source Material:** [LangChain Supervisor Pattern](https://docs.langchain.com/oss/python/langchain/supervisor), [Multi-Agent Systems](https://docs.langchain.com/oss/python/langchain/multi-agent)

## 1. The "Supervisor" Pattern (Recommended)

Our current `MultiAgentStrategy` is a linear chain (`A -> B -> C`). This is fragile because if `A` fails, the whole chain stops.

The **Supervisor Pattern** (LangChain's standard for orchestration) replaces this with a central "Supervisor Agent" that acts as a router.

### Concept
Instead of hardcoded steps, the Supervisor:
1.  Receives the user request (or current state).
2.  Decides which "worker" agent to call next (Topic, Sentiment, Trends).
3.  Consumes the worker's output.
4.  Decides the *next* step (or finishes).

### Why This Fits Us
*   **Resilience:** If `TopicDetection` fails, the Supervisor can catch the error and route to `KeywordFallback` instead of crashing.
*   **Flexibility:** We can skip `Sentiment` if the topic is "Unknown", or loop back to `DataAgent` if data is missing.
*   **State Management:** LangGraph's `StateGraph` persists the conversation state, allowing us to resume interrupted runs (crucial for our long-running batch jobs).

## 2. Architecture Gap Analysis

| Feature | Current (`UnifiedOrchestrator`) | LangChain Supervisor (`LangGraph`) |
| :--- | :--- | :--- |
| **Control Flow** | Linear Script (Python `await` sequence) | Cyclic Graph (Nodes & Edges) |
| **Routing** | Hardcoded (`if feature_flag: run()`) | Dynamic (`supervisor.decide(state)`) |
| **State** | Mutable `AgentContext` object | Immutable `State` with reducers |
| **Persistence** | Manual JSON checkpoints | Native `checkpointer` (Postgres/SQLite) |
| **Error Recovery** | Try/Except blocks | Conditional Edges (e.g. `retry` node) |

## 3. Implementation Plan

We can adopt these patterns **without** immediately adding the heavy `langgraph` dependency. We will implement the *pattern* first, then the *library* later.

### Phase 1: Logical Supervisor (Current Sprint)
Refactor `VoiceOfCustomerStrategy` to behave like a Supervisor:

```python
# Conceptual Pseudo-code
while not state.is_complete:
    # 1. Router Logic
    next_step = decide_next_step(state)
    
    # 2. Execution
    if next_step == "topic_detection":
        result = await topic_agent.execute(state)
        if result.failed:
            state.next_step = "keyword_fallback" # Dynamic recovery!
        else:
            state.update(result)
            state.next_step = "sentiment_analysis"
```

### Phase 2: LangGraph Adoption (Future)
Once the logic is proven, we replace our custom loop with `StateGraph`:

```python
# Future LangGraph Implementation
from langgraph.graph import StateGraph, END

workflow = StateGraph(AgentState)
workflow.add_node("supervisor", supervisor_node)
workflow.add_node("topic_detection", topic_agent)
workflow.add_node("fallback", keyword_fallback)

# Edges define the resilience logic
workflow.add_conditional_edges(
    "supervisor",
    lambda state: state.next_agent
)
```

## 4. Key Takeaways for Development Standards

1.  **Agents as Tools:** Design agents to be stateless functions that take `State` and return `Update`.
2.  **Centralized Routing:** Move logic out of `execute()` methods and into the Orchestrator/Supervisor.
3.  **State Schema:** Formalize `AgentContext` into a rigid schema (like Pydantic or TypedDict) that defines exactly what keys exist.

## 5. Phase 2: Tool Wrappers & Schema Contracts (Completed)

**Status:** Implementation Complete  
**Goal:** Prepare existing agents to be called as LangChain/LangGraph tools without modifying their internals.

### Agent ↔ Tool ↔ Schema Mapping

| Agent | Tool Name | Input Schema | Output Schema | Purpose |
| --- | --- | --- | --- | --- |
| `TopicDetectionAgent` | `detect_topics` | `TopicDetectionInput` | `TopicDetectionOutput` | Hybrid LLM + keyword topic detection with provenance |
| `InsightAgent` | `generate_insights` | `InsightInput` | `InsightOutput` | Synthesize strategic insights from topic/sentiment data |
| `EditorAgent` | `critique_and_edit_insights` | `EditorInput` | `EditorOutput` | Quality control: score and rewrite insights |
| `OutputFormatterAgent` | `format_analysis_output` | `FormatterInput` | `FormatterOutput` | Produce executive markdown with topic cards + QC summary |

### Schema Definitions

All schemas live in `src/schemas/agent_io.py` so LangChain, LangGraph, and DeepAgents share a single source of truth.

**Input Schemas**
- `TopicDetectionInput`: conversations, date range, analysis_id, metadata
- `InsightInput`: previous_results (TopicDetection + TopicSentiments), date range, optional conversations
- `EditorInput`: previous_results (InsightAgent), date range, optional conversations
- `FormatterInput`: previous_results (full workflow), conversations, date range, metadata

**Output Schemas**
- `TopicDetectionOutput`: topic_distribution, topics_by_conversation, detection mix, fallback metrics
- `InsightOutput`: executive_summary, themes, recommendations, duplicate ratio, metric references, detection provenance
- `EditorOutput`: critic scores (5 dimensions + composite), rewrite flag, revised insights payload
- `FormatterOutput`: formatted markdown, structured topic cards, quality telemetry, fallback counters

### Tool Wrapper Pattern

Every wrapper follows the same structure and uses an adapter pattern for LangChain integration. Since these classes do not subclass `langchain_core.tools.BaseTool` directly (to avoid heavy dependencies in the core project), they are designed to be wrapped by a lightweight adapter if direct LangChain usage is required. The `_arun` method is therefore not implemented on these classes but is expected to be handled by the adapter.

```python
class AgentTool(BaseTool):
    def __init__(self):
        super().__init__(name="tool_name", description="...")

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(name=self.name, description=self.description, parameters=[...])

    async def execute(self, **kwargs) -> ToolResult:
        # Explicit date conversion ensures Pydantic compatibility
        for field in ["start_date", "end_date"]:
            if isinstance(kwargs.get(field), str):
                 kwargs[field] = datetime.fromisoformat(kwargs[field])

        payload = InputSchema(**kwargs)
        context = AgentContext(...)
        result = await self.agent.execute(context)
        output = OutputSchema(**result.data)
        return ToolResult(success=True, data=output.model_dump())
```

### Date Handling Convention

While the Pydantic schemas (`TopicDetectionInput`, etc.) use `datetime` types, the tool parameter definitions (`get_definition()`) advertise `string` types for `start_date` and `end_date` to be compatible with OpenAI/Anthropic JSON schemas.

- **External Consumers:** Pass ISO8601 strings (e.g., `"2023-10-27T10:00:00"`).
- **Internal Logic:** The `execute()` method explicitly converts these strings to `datetime` objects before schema validation.
- **Schemas:** `src/schemas/agent_io.py` relies on standard `datetime` types.

The input/output validation prevents schema drift and provides OpenAI/Anthropic-compatible parameter metadata via `ToolDefinition.to_openai_format()`.

### Integration with DeepAgents (Phase 3)

1. **Discovery** – Supervisor calls `ToolRegistry.get_tool_definitions()` and feeds the schemas to the model.
2. **Execution** – Supervisor calls `ToolRegistry.execute_tool(name, **kwargs)` and receives validated payloads.
3. **State Updates** – Outputs map back to the canonical schemas, making it trivial to update LangGraph state.
4. **Retries** – Because wrappers use `safe_execute`, DeepAgents can retry failed tools without bespoke glue code.

### Validation

`scripts/run_tool_wrappers.py` exercises each tool against sample data from `reference_data/voice-of-customer_Last-Week_dec-1-6-41pm/`.

```
python scripts/run_tool_wrappers.py
# Expected console:
# ✅ TopicDetectionTool passed
# ✅ InsightTool passed
# ✅ EditorTool passed
# ✅ OutputFormatterTool passed
```

The script stubs topic sentiments, Insight/Editor results, and minimal fin/bpo data so we can verify schema round-trips without launching the full orchestrator.

### Phase 3: DeepAgents Supervisor Pilot (Implemented)

- Added optional `deepagents` dependency (commented in `requirements.txt`) with guarded imports.
- Introduced `src/orchestration/deep_supervisor.py` and package init to wrap Phase 2 tools with streaming support.
- Added `--orchestrator {legacy,deep}` flag across CLI (`src/main.py`, `src/cli/voc_commands.py`), schema, and web UI (`static/app.js`, `deploy/web/templates.py`).
- Feature flag `ENABLE_DEEP_ORCHESTRATOR` (default False) toggles deep as the default orchestrator.
- Pilot runner `scripts/run_deepagents_pilot.py` archives paired runs to `outputs/deepagents_pilot/`.
- Validation updated in `scripts/run_all_checks.sh` to enforce orchestrator flag alignment and surface cache-bust warnings.

**Usage Examples**

```bash
# CLI: run deep supervisor
python src/main.py voice-of-customer --time-period week --orchestrator deep

# Web UI: check "DeepAgents Supervisor" toggle (VoC only)

# Pilot comparison
python scripts/run_deepagents_pilot.py --time-period week --count 50
```

Pilot outputs now include critic scores and token usage for both orchestrators, and the Markdown report shows deltas (composite critic score and total tokens) to support go/no-go decisions.

### Phase 4: Review Packet & Optional Escalation (Implemented)

**Status**: Implementation Complete  
**Goal**: Provide lightweight human escalation path without blocking standard runs.

**Review Packet Pattern**
- Generated when quality KPIs fail (composite_score < 0.60, duplicate_ratio > 0.15, metric_refs < 5, topic fallback usage, analytics coverage gaps *only when the formatter marks analytics data as available*).
- Persisted to `outputs/<run>/review_packet.md` with structured summary.
- Includes failed KPIs table, detailed findings, artifact links, recommended actions.
- Execution continues by default; never blocks unless approval flag is set.

**SSE Notification**
- New `review_required` event emitted via `ExecutionStateManager`.
- Surfaces in CLI logs and web UI with warning badge + expandable details.
- Payload: `{"type": "review_required", "data": {"severity": "warning|critical", "failed_kpis": [...], "packet_path": "executions/<id>/review_packet_<analysis>.md", "web_path": "executions/<id>/review_packet_<analysis>.md"}}`.

**Optional Approval Gate**
- `--require-approval` CLI flag (and `REQUIRE_APPROVAL` env var) pauses after packet generation. This gate applies to Voice-of-Customer runs only; sample-mode executes a synthetic review packet for validation but never blocks or exposes approval toggles.
- Waits for manual confirmation via `approve_execution()` (timeout configurable by `APPROVAL_TIMEOUT_SECONDS`, default 300s).
- Disabled by default to keep automation fast.

**Integration**
- `src/services/strategies/voc_strategy.py`: evaluates KPIs after EditorAgent, generates packet, emits SSE.
- `src/agents/output_formatter_agent.py`: surfaces review metadata in "Quality Control Summary".
- `src/services/execution_state_manager.py`: tracks review packet metadata + approval signals.
- `src/utils/review_packet_generator.py`: central packet builder.
- Web UI: Displays `review_required` events with expandable details.

**Validation**
- Run `scripts/validate_phase4_review_packets.py` to execute a VoC test-mode run with forced KPI failure (ensures the real orchestrator emits the review packet + SSE event) followed by a separate helper validation of `ReviewPacketGenerator`.
- Confirm artifacts include analytics KPIs and SSE/log highlights.
- Test `--require-approval` flag pauses and resumes correctly (VoC only; sample-mode remains ungated).

## Phase 5: Adoption Decision & Rollout (Status: [PENDING])

**Decision Date:** _TBD_  
**Reviewers:** _TBD_  
**Recommendation:** [ADOPT / DEFER / REJECT]

### Pilot Execution Summary

| Timestamp | Configuration | Status | Notes |
|-----------|---------------|--------|-------|
| _TBD_ | test-mode (50 conversations, OpenAI) | _TBD_ | Populate after pilot runs |
| _TBD_ | test-mode (100 conversations, Claude) | _TBD_ | Populate after pilot runs |
| _TBD_ | Real data (last week, OpenAI) | _TBD_ | Populate after pilot runs |
| _TBD_ | Real data (last 2 weeks, digest) | _TBD_ | Populate after pilot runs |

- Decision analysis: `outputs/deepagents_pilot/phase5_decision_analysis.md`
- Metrics summary: `outputs/deepagents_pilot/phase5_metrics_summary.json`

### Metrics Analysis

| Metric | Legacy Mean | Deep Mean | Δ % | Notes |
|--------|-------------|-----------|-----|-------|
| Composite Critic Score | _TBD_ | _TBD_ | _TBD_ | Use analyzer output |
| Runtime (seconds) | _TBD_ | _TBD_ | _TBD_ | Target penalty ≤25% |
| Tokens / Conversation | _TBD_ | _TBD_ | _TBD_ | Prefer neutral/improved |
| Success Rate | _TBD_ | _TBD_ | _TBD_ | Target ≥95% both |

Per-dimension critic scores (specificity, metric density, repetition, distinctness, actionability) are captured in the metrics summary file. Update this table with actual means once pilots complete.

### Threshold Evaluation

- Critic score improvement ≥20% → _TBD_
- Runtime penalty ≤25% → _TBD_
- Token efficiency maintained or improved → _TBD_
- Success rate ≥95% per orchestrator → _TBD_
- No critical regressions across critic dimensions → _TBD_

### Decision Rationale

- **Quality Impact:** _Describe critic score uplift, reduced dilution, evidence from report._
- **Performance Trade-offs:** _Document runtime/tokens deltas and infra impact._
- **Risk Assessment:** _Detail deepagents dependency, migration complexity, fallback plans._
- **Stakeholder Feedback:** _Summarize product + engineering review notes._

### Recommendation

- **Recommendation:** [ADOPT / DEFER / REJECT]
- **Rationale:** _Summarize why recommendation meets thresholds or why it does not._
- **Re-evaluation Conditions (if DEFER):** _E.g., rerun after deepagents v2.0 or new telemetry._
- **Alternatives (if REJECT):** _Outline fallback orchestration strategies._

### Rollout Plan (if ADOPT)

1. **Phase 5.1 – Soft Launch (Weeks 1-2)**
   - Keep `enable_deep_orchestrator=False`.
   - Document `--orchestrator=deep` usage (CLI + UI).
   - Monitor telemetry for pilot usage; gather qualitative feedback.

2. **Phase 5.2 – Gradual Rollout (Weeks 3-6)**
   - Enable deep orchestrator for internal/test accounts.
   - Flip `ENABLE_DEEP_ORCHESTRATOR=true` in Railway staging.
   - Run weekly pilot comparisons to catch regressions.
   - Update web UI to highlight orchestrator selection.

3. **Phase 5.3 – Full Adoption (Weeks 7-8)**
   - Set deep orchestrator as CLI default (`enable_deep_orchestrator=True`).
   - Deploy Railway production with new defaults.
   - Announce change to all users; provide rollback instructions.

4. **Phase 5.4 – Cleanup (Week 9+)**
   - Keep legacy orchestrator available for one release.
   - Archive `TopicOrchestratorV2` + `MultiAgentStrategy` into `legacy/`.
   - Update documentation/training to deep-first patterns.
   - Remove `--orchestrator` flag once comfortable (deep only).

See `docs/PHASE_5_ROLLOUT_CHECKLIST.md` for detailed, box-by-box tracking.

### Monitoring & Dashboards

- Grafana/Railway widgets: orchestrator usage split, critic score distributions, runtime deltas, error rates.
- Alerting: runtime regression >30%, critic score < Phase 1 baseline, error rate delta >5%.
- Dependency health: monitor deepagents releases + security advisories.

### Backlog Items

1. [TASK-001] Update CLI help text to recommend deep orchestrator.
2. [TASK-002] Expose Railway `ENABLE_DEEP_ORCHESTRATOR` environment variable.
3. [TASK-003] Build orchestrator monitoring dashboards.
4. [TASK-004] Deprecate `MultiAgentStrategy` (move to `legacy/`).
5. [TASK-005] Update `DEVELOPER_ONBOARDING.md` with deep orchestrator guidance.
6. [TASK-006] Add integration tests covering deep orchestrator edge cases.
