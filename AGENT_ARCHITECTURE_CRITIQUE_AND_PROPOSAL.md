# Agent Architecture Critique & Proposal

## 1. Executive Summary

Recent production runs of the Voice of Customer pipeline have highlighted two distinct but related issues: **System Fragility** and **Analytical Stagnation**.

1.  **Fragility (Dec 2 Run)**: A crash in `TopicDetectionAgent` caused the entire pipeline to abort, resulting in empty reports. This exposes the weakness of our rigid linear architecture.
2.  **Quality (Dec 3 Run)**: While technically successful, the output was qualitatively repetitive ("Customers are experiencing severe frustration..." used verbatim across multiple topics) and lacked depth in high-volume categories like "Product Question".

This report proposes shifting to a **Supervisor-Worker** pattern (inspired by LangGraph) to address both issues simultaneously: providing resilience against crashes and enabling iterative quality refinement.

## 2. Failure Analysis

### A. The Crash (Dec 2 Run)
*   **Symptom**: Empty output files (0 bytes).
*   **Cause**: `TopicDetectionAgent` returned `success: False`. The orchestrator (`VoiceOfCustomerStrategy`) treats this as a fatal error, aborting downstream steps.
*   **Architectural Flaw**: **Linear Dependency Chain**. `Data -> Topic -> Sentiment -> Format`. If one link breaks, the chain snaps.

### B. The Quality Gap (Dec 3 Run)
*   **Symptom**: Report generated, but user "unhappy".
*   **Evidence**:
    *   **Repetitive Sentiment**: The phrase *"Customers are experiencing severe/moderate frustration..."* appears verbatim in 5 out of 8 topic cards.
    *   **Vague Insights**: "Product Question" accounts for 35% of volume but the insight is generic ("functionality... API-generated slides").
    *   **Math Error**: Logs show a critical error: `Topic percentages sum to 99.90%... indicates a fundamental math bug`.
*   **Architectural Flaw**: **One-Shot Execution**. The agents generate content once. There is no "Critic" or "Editor" step to review the output for repetition or depth before finalizing.

## Phase 0: Evidence & Baseline Metrics

We now have automated telemetry via `scripts/parse_production_runs.py` and `scripts/validate_phase0_metrics.py`. Parsed artifacts are saved to `outputs/baseline_metrics/production_run_analysis.json` and `outputs/baseline_metrics/sample_mode_baseline_*.json` for trend analysis.

### A. Production Run Statistics (Dec 1–3, 2025)

| Run Folder | Conversations | Topics Detected | Status | Notes |
| --- | ---:| ---:| --- | --- |
| `voice-of-customer_Last-Week_dec-1-6-41pm` | 6,439 | 0 | **Degraded** | `voc_topic_based_*.md` is empty → formatter received no topic payloads |
| `voice-of-customer_Last-Week_dec-1-6-43pm` | 6,439 | 0 | **Degraded** | Duplicate audit trails but still zero topic markdown output |
| `voice-of-customer_Last-Week_dec-2-1-43am` | 6,562 | 0 | **Degraded** | Same blank topic outputs; audit trail only logs CSAT warnings |
| `voice-of-customer_Last-Week_dec-2-1-44am` | 6,562 | 0 | **Degraded** | Redundant rerun still missing topic payloads |
| `voice-of-customer_Last-Week_dec-2-4-5pm` | 6,259 | 0 | **Degraded** | Only audit data present, no insights |

All five runs completed data fetch + validation but never produced topic markdown. The new parser records this explicitly, turning qualitative complaints into quantitative signal (`total_topics=0` in `production_run_analysis.json`).

### B. Quantified Quality Issues

- **CSAT coverage stuck at ~4 %** across paid and free tiers (`audit_trail_*` excerpts captured in `data_quality_notes`). This confirms that the pipeline is unaware of its own blind spots.
- **Zero-topic outputs** mean downstream agents fabricate “generic” summaries. This aligns with user feedback (“Customers are experiencing severe frustration…” reused verbatim) and explains why duplicate detection must move upstream.
- **No metric references captured** because InsightAgent never annotated duplicates or references—our telemetry now exposes this gap rather than hiding it.
- **Fallback reliance invisible**: without topic payloads we cannot count fallback cards, hence the need for OutputFormatter instrumentation.

### C. Baseline Metrics (Sample-Mode Validation)

`scripts/validate_phase0_metrics.py` now snapshots each sample-mode run. The latest artifact (`outputs/baseline_metrics/sample_mode_baseline_20251204_180242.json`) shows:

- **Conversation count**: 100 conversations processed (from `sample_mode_Dec-01-2025_10-16AM.json`).
- **Stage metrics**: missing because legacy logs never emitted `STAGE METRIC` lines—telemetry now highlights this absence.
- **Agent metrics**: missing InsightAgent duplicate data, triggering the warning `InsightAgent metric references below target (<2)`.

This baseline intentionally surfaces the “unknowns” we must fix (no stage counts, no agent metrics) before moving to Phase 1.

### D. Phase 1 Success Criteria

To graduate out of Phase 0 we must hit measurable targets:

1. **Duplicate ratio**: reduce from “undefined / 0 topics” to `< 0.15` per topic by enforcing metric logging in InsightAgent + Editor refinement.
2. **Metric references**: raise InsightAgent output to `≥ 5` quantified call-outs per run.
3. **Fallback usage**: keep OutputFormatter `topic_fallback_used` at `0` (anything >0 now pages telemetry).
4. **Stage telemetry**: log `Post-Insights` counts on every VoC orchestrator path (now implemented) and store them in baseline snapshots.
5. **CSAT visibility**: lift CSAT coverage from ~4 % by flagging low coverage as a blocker instead of burying it inside audit notes.

These targets turn qualitative frustration into concrete engineering KPIs, closing the loop between production evidence and Phase 1 remediation.

## 3. Research: LangChain & LangGraph Patterns

Research into LangChain's 2025 ecosystem highlights the **Supervisor** pattern as the standard for resilient, high-quality agent systems.

| Feature | Current (`VoiceOfCustomerStrategy`) | Proposed (`SupervisorStrategy`) |
| :--- | :--- | :--- |
| **Control Flow** | Hardcoded sequence (A -> B -> C) | Dynamic State Machine (Supervisor decides next step) |
| **Error Handling** | Exception catching & abort | **Conditional Routing**: If Topic AI fails -> Route to Keyword Fallback |
| **Quality Control** | None (First draft is final) | **Reflection Loop**: Critic Agent reviews output -> Sends back to Writer if repetitive |
| **State** | `AgentContext` (passed blindly) | Shared Graph State (persisted & inspectable) |

## 4. Proposal: The "Easy to Implement" Supervisor

We can implement a lightweight version of this pattern immediately without a full rewrite.

### The Supervisor Loop Strategy

Instead of a linear script, the `Orchestrate` method becomes a loop:

```python
while not state.is_complete:
    # 1. Supervisor decides next step
    next_agent = supervisor.decide(state)
    
    # 2. Execute Agent
    result = await agents[next_agent].execute(state)
    
    # 3. Update State & Handle Failures
    if not result.success:
        if next_agent == "TopicDetection":
            # RESILIENCE: Dynamic reroute
            next_agent = "KeywordFallback" 
        else:
            state.add_error(result)
```

### Concrete Implementation Plan

#### Phase 1: Immediate Fixes (Today)
1.  **Resilience**: Patch `VoiceOfCustomerStrategy` (and `MultiAgentStrategy`) to wrap `TopicDetectionAgent` in a try/catch. If it fails, synthesize a "Fallback Topic" result using existing keyword logic so the pipeline continues.
2.  **Soft Fail**: Update `OutputFormatterAgent` to accept "partial" data (missing topics) without crashing.
3.  **Math Fix**: Fix the normalization bug in `TopicDetectionAgent` to prevent the 99.9% error log.

#### Phase 2: Quality Refinement (Next Sprint)
1.  **Add "Editor" Agent**: A lightweight LLM step inserted before `OutputFormatter`. It reads the raw insights and checks for:
    *   Repetitive phrasing.
    *   Vague claims.
    *   If found, it rewrites them *before* formatting.
2.  **Recursive Depth**: For large topics (like "Product Question"), trigger a *recursive* sub-analysis (spawn a new analysis just for that topic) to get deeper granular insights.

## 5. Recommendation

**Adopt Phase 1 immediately**. The system must produce *some* value even if one agent fails. 

**Action Items:**
1.  [ ] Patch `VoiceOfCustomerStrategy` to catch `TopicDetectionAgent` failures.
2.  [ ] Implement simple fallback logic (use tags/keywords if AI topics fail).
3.  [ ] Fix the 99.9% math bug in `TopicDetectionAgent`.

## Phase 5: DeepAgents Adoption Decision

**Status:** [PENDING / IN_PROGRESS / COMPLETE]

**Pilot Execution**

- [ ] Pilot suite executed via `scripts/run_pilot_suite.py`
- [ ] ≥3 completed runs per orchestrator (legacy + deep)
- [ ] Analysis generated with `scripts/analyze_deepagents_pilot.py`
- [ ] Decision written to `docs/LANGCHAIN_ARCHITECTURE_MIGRATION.md`

**Key Findings** _(fill after analysis completes)_

- Composite critic score improvement: _TBD_%
- Runtime penalty: _TBD_%
- Token efficiency delta: _TBD_%
- Success rate: legacy _TBD_%, deep _TBD_%

**Decision:** [ADOPT / DEFER / REJECT]

**Rationale:** _Summarize why the recommendation meets (or misses) thresholds._

**Next Steps:** _Outline rollout or re-evaluation plan based on the decision, referencing `docs/PHASE_5_ROLLOUT_CHECKLIST.md` when ADOPT._
