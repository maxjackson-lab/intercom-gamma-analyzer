# VoC Quality Rescue – Phased Execution Plan

This plan is tailored for Traycer (or other planning agents) so it can decompose the Voice of Customer (VoC) quality rescue into concrete workstreams. It references only files and directories that currently exist in the repo.

---

## 0. Context & Source Material

| Area | Paths / Links |
| --- | --- |
| Failure/Postmortem Evidence | `AGENT_ARCHITECTURE_CRITIQUE_AND_PROPOSAL.md`, `docs/LANGCHAIN_ARCHITECTURE_MIGRATION.md`, `docs/QUALITY_FIRST_MIGRATION_PLAN.md` |
| Current Orchestrators | `src/services/unified_orchestrator.py`, `src/services/strategies/voc_strategy.py`, `src/services/strategies/multi_agent.py` |
| Key Agents | `src/agents/topic_detection_agent.py`, `src/agents/insight_agent.py`, `src/agents/output_formatter_agent.py` |
| Production Runs | `reference_data/voice-of-customer_Last-Week_dec-1-6-41pm/`, `reference_data/voice-of-customer_Last-Week_dec-2-4-5pm/`, `reference_data/voice-of-customer_Last-Week_dec-3-1-13am/` |
| External Patterns | LangChain Supervisor & guardrails ([link](https://docs.langchain.com/oss/python/langchain/supervisor), [link](https://docs.langchain.com/oss/python/langchain/guardrails)), LangGraph interrupts ([link](https://docs.langchain.com/oss/python/langgraph/functional-api)), DeepAgents on PyPI ([link](https://pypi.org/project/deepagents/)) |

**Observed Issues (Dec 1–3 runs):**
- `TopicDetectionAgent` still returns `success=False` intermittently (see `reference_data/voice-of-customer_Last-Week_dec-2-4-5pm/execution_*.log`), causing downstream soft-fail reports.
- `InsightAgent` produces repetitive, generic paragraphs (see Markdown outputs in referenced folders).
- `OutputFormatterAgent` digests >30k tokens of undifferentiated context and outputs “Unknown” topic sections after soft-fail fallback.
- No automated critic or human escalation loop, so regressions slip through quietly.

**Baseline KPIs for Critic/Supervisor Rebuild**
- **Accuracy of totals** – topic percentages must sum to 100 ± 1 % and emit `Post-Insights` counts, otherwise the pipeline blocks delivery.
- **Specificity & tone** – InsightAgent duplicate ratio < 0.15 and ≥ 5 metric references per report; critic rejects melodramatic/generic copy.
- **Readable data breakdowns** – every report surfaces a topic table (volume, sentiment, trend) plus CSAT/resolution coverage so ops can see gaps.
- **BPO transparency** – vendor workload/pressure + inline callouts are mandatory; missing data increments the placeholder KPI.
- **Finn usefulness** – free vs paid tier stats and escalation drivers must be explained (no “100% solved” without context).
- **Historical story** – reports include week-over-week deltas so trends aren’t guesswork; missing comparisons flag the critic.
- **Escalation signals (non-blocking)** – the critic/supervisor loop records KPI failures (review packets + SSE events) so humans can react, but it never halts execution on its own.
- **Analytics signal coverage** – align with industry VoC decks by tracking: topic concentration (top-3 share), detection-method mix (LLM vs keyword vs fallback), CSAT coverage %, average resolution time deltas, Fin deflection rate (Fin vs Human split), and churn-risk correlation counts. These become mandatory stats inside the formatter output and telemetry snapshots.

---

## Phase 0 – Evidence & Instrumentation

**Goal:** Capture quantitative proof of the “goo” problem and add telemetry needed for later phases.

- **Tasks**
  1. Parse the Markdown + log files in `reference_data/voice-of-customer_Last-Week_dec-*` folders. Record per-topic stats (volume, duplicate phrase count, success flag) inside `AGENT_ARCHITECTURE_CRITIQUE_AND_PROPOSAL.md`.
  2. In `src/agents/insight_agent.py`, log metrics such as `insight_duplicate_ratio`, total tokens used, and detected metric references.
  3. In `src/agents/output_formatter_agent.py`, log `topic_fallback_used` and resulting placeholder volume.
  4. Ensure `src/services/strategies/voc_strategy.py` emits `log_stage_metrics("Post-Insights", …)` so we can graph improvements.

- **Validation**
  - `python src/main.py sample-mode --count 50 --save-to-file`
  - `read_lints` + `python3 -m py_compile` on touched files
  - Archive new telemetry snapshots to `outputs/baseline_metrics/*.json`

- **Risks**
  - Missing Intercom fields → follow defensive `.get()` patterns from `DEVELOPMENT_STANDARDS.md`
  - Metric overload → gate logging behind `if self.monitor`

---

## Phase 1 – Critic/Editor Guardrail (LangChain Pattern)

**Goal:** Add an automated reviewer that scores insights for specificity, metrics, and novelty before formatting.

- **Tasks**
  1. Document a critic rubric + prompt snippet in `docs/QUALITY_FIRST_MIGRATION_PLAN.md` (include scoring scales and failure thresholds).
  2. Create `src/agents/editor_agent.py`. It should:
     - Build a critic prompt referencing Insight outputs.
     - Call the configured LLM (smaller model acceptable) and parse JSON schema.
     - When `rewrite_needed` is `True`, issue a short rewrite prompt referencing the critic feedback.
  3. Wire the agent inside `src/services/strategies/voc_strategy.py` after Insight generation:
     ```python
     editor_result = await self._execute_agent_with_checkpoint(self.editor_agent, context, workflow_state, analysis_id)
     if editor_result.success and editor_result.data.get("revised_insights"):
         context.previous_results["InsightAgent"]["data"] = editor_result.data["revised_insights"]
     context.previous_results["EditorAgent"] = editor_result.dict()
     ```
  4. Update `src/agents/output_formatter_agent.py` to surface critic scores (e.g., “Critic Summary” section) and to tag reports with “Partial” when editor flagged issues.

- **Validation**
  - Sample-mode run (`python src/main.py sample-mode --count 50 --save-to-file`)
  - Compare critic score histograms before/after (store under `outputs/critic_scores/`)
  - `./scripts/run_all_checks.sh`

- **Risks & Mitigations**
  - Increased token cost → use concise prompts, limit rewrites to 2 passes.
  - Longer runtime → rely on existing `log_stage_metrics` to monitor duration deltas.

---

## Phase 2 – Tool Wrappers & Schema Contracts

**Goal:** Prepare existing agents to be called as LangChain/LangGraph tools without rewriting their internals.

- **Tasks**
  1. Create `src/schemas/agent_io.py` with Pydantic models for TopicDetection, Insights, Editor, Formatter inputs/outputs (re-use structures from `AgentResult.data`).
  2. Add wrappers under `src/agents/tools/`:
     - `topic_detection_tool.py`
     - `insight_tool.py`
     - `editor_tool.py`
     - `output_formatter_tool.py`
     Each wrapper should convert LangChain tool args → `AgentContext` and back.
  3. Write `scripts/run_tool_wrappers.py` that loads a small subset from `reference_data/voice-of-customer_Last-Week_dec-1-6-41pm/` and exercises each tool in isolation.
  4. Document the mapping table (Agent ↔ Tool ↔ Schema) in `docs/LANGCHAIN_ARCHITECTURE_MIGRATION.md`.

- **Validation**
  - Run the wrapper harness on sample data.
  - Add unit tests for schema round-trips if feasible.

- **Risks**
  - Event-loop misuse → implement `_arun` methods so async execution is preserved.
  - Schema drift → keep models single-sourced in `agent_io.py`.

---

## Phase 3 – DeepAgents Supervisor Pilot

**Goal:** Use DeepAgents (LangGraph-based supervisor) to orchestrate existing tools, enabling planning, retries, and sub-agent spawning.

- **Tasks**
  1. Add optional dependency `deepagents` (document install steps in `README.md`; guard imports).
  2. Create `src/orchestration/deep_supervisor.py`:
     ```python
     class DeepSupervisor:
         def __init__(self, tools: list[BaseTool], system_prompt: str):
             self.agent = create_deep_agent(tools=tools, system_prompt=system_prompt)
         async def run(self, request: VoiceOfCustomerRequest):
             payload = {"messages": [{"role": "user", "content": build_request(request)}]}
             async for chunk in self.agent.astream(payload, stream_mode="values"):
                 yield chunk
     ```
  3. Update `src/cli/voc_commands.py` to accept `--orchestrator {legacy,deep}` (also update `src/cli/schema.py` and `static/app.js` per CLI/Web alignment rules).
  4. Add feature flag in settings to switch orchestrators without CLI.
  5. Run paired sample-mode analyses (legacy vs deep) and store results in `outputs/deepagents_pilot/`.

- **Validation**
  - `python src/main.py voice-of-customer ... --orchestrator=deep --save-to-file`
  - `./scripts/run_all_checks.sh`
  - Compare runtime, critic scores, token usage vs legacy runs.

- **Risks**
  - Dependency bloat → keep DeepAgents optional.
  - Observability differences → ensure Deep supervisor streams output through `ExecutionStateManager`.

---

## Phase 4 – Reviewer Packet & Optional Escalation

**Goal:** Give humans a lightweight approval path without blocking every run; critic/supervisor supplies the context, humans decide when to act.

- **Tasks**
  1. **Critic Review Packet** – when KPIs miss, persist `outputs/<run>/review_packet.md` that summarizes failed metrics (duplicate ratio, topic coverage, CSAT gaps, Fin/BPO stats) plus direct links to logs/JSON. This mirrors the “review bundle” pattern common in LangChain/DeepAgents supervisor deployments.
  2. **Streaming Notifications** – add a structured SSE/log event (e.g., `REVIEW_REQUIRED`) so CLI/Web users see the critic feedback inline, but the pipeline still completes and returns artifacts.
  3. **Optional Approval Flag** – document and wire a `--require-approval` CLI flag (and matching env var) for teams that explicitly want to stop after the review packet. Keep it **disabled by default** so standard runs never pause.
  4. Update `docs/LANGCHAIN_ARCHITECTURE_MIGRATION.md`, `DEVELOPMENT_STANDARDS.md`, and onboarding notes so everyone knows how to consume the packet and opt into approval mode.

- **Validation**
  - Run a degraded sample-mode scenario to produce a review packet; confirm the artifacts include the new analytics KPIs and that SSE/log output highlights the issues.

- **Risks**
  - Humans ignoring packets → mitigate by embedding clear next steps (“rerun with --override once reviewed”).
  - CLI flag drift → ensure schema/frontend alignment when a UI toggle eventually lands, but default to CLI-only for now.

---

## Phase 5 – Adoption Decision & Rollout

**Goal:** Decide whether DeepAgents becomes the default orchestrator or remains optional, then execute a structured rollout if the decision is ADOPT.

### Tasks

1. **Execute Pilot Suite**
   - Run `python scripts/run_pilot_suite.py --full` to collect at least four comparison scenarios (two test-mode, two real data).
   - Ensure ≥3 successful runs per orchestrator; rerun failed scenarios until data suffices.
   - Verify timestamped folders exist under `outputs/deepagents_pilot/<scenario>/<timestamp>/`.

2. **Analyze Pilot Results**
   - Run `python scripts/analyze_deepagents_pilot.py` (use `--strict` to fail when thresholds miss).
   - Review generated artifacts:
     - Markdown report: `outputs/deepagents_pilot/phase5_decision_analysis.md`
     - JSON summary: `outputs/deepagents_pilot/phase5_metrics_summary.json`
   - Confirm analyzer covers:
     - Composite critic uplift (target ≥20%)
     - Runtime delta (target penalty ≤25%)
     - Token efficiency (tokens/conversation non-increasing)
     - Success rate (≥95% per orchestrator)

3. **Document Decision**
   - Update `docs/LANGCHAIN_ARCHITECTURE_MIGRATION.md` Phase 5 section with:
     - Pilot execution table (timestamps, configs, statuses)
     - Metrics comparison tables and threshold evaluation (✅/❌)
     - Qualitative rationale (quality vs cost, risks, stakeholder feedback)
     - Recommendation: ADOPT / DEFER / REJECT
   - If ADOPT, flesh out rollout plan subsections (soft launch → cleanup) and link to checklist.
   - If DEFER/REJECT, record conditions for re-entry or alternative strategies.

4. **Validate Documentation**
   - Run `python scripts/validate_phase5_decision.py` to ensure artifacts, metrics, and docs stay in sync.
   - Fix reported gaps before moving forward.

5. **If Greenlit (ADOPT)**
   - Maintain `docs/PHASE_5_ROLLOUT_CHECKLIST.md` and work through:
     - CLI default switch + `settings.enable_deep_orchestrator`
     - Railway staging → production flips
     - Monitoring dashboard creation
     - Deprecation backlog (MultiAgentStrategy relocation, TopicOrchestratorV2 archival)
   - Coordinate announcements, training, and rollback plan.

### Validation

- Peer review of decision artifacts (minimum two reviewers).
- `python scripts/validate_phase5_decision.py` passes (artifacts aligned).
- `./scripts/run_all_checks.sh` runs clean with Phase 5 validation warnings resolved.

### Risks

- **Analysis paralysis:** Avoid by enforcing hard thresholds (≥20% critic uplift, ≤25% runtime penalty).
- **Insufficient pilot data:** Block recommendation until ≥3 runs per orchestrator succeed.
- **Rollback complexity:** Keep legacy orchestrator available for one release cycle; document rollback steps in `docs/PHASE_5_ROLLOUT_CHECKLIST.md`.
- **Dependency drift:** Monitor deepagents package health/security advisories before flipping defaults.

### Success Criteria

- Decision documented with rationale, peer review, and stakeholder approval.
- Analyzer shows required improvements and exposes any penalties transparently.
- If ADOPT: rollout checklist tracked to completion, defaults flipped without regressions.
- If DEFER/REJECT: re-entry criteria or alternative plan captured for future teams.

---

## Cross-Phase Requirements

- **Audit workflow:** For every code change follow repo rules (read back diff, `read_lints`, `python3 -m py_compile`, import verification, context check, `./scripts/run_all_checks.sh`).
- **Sample-mode real data:** Required after Phases 1, 3, and 4.
- **Documentation updates:** Keep `AGENT_ARCHITECTURE_CRITIQUE_AND_PROPOSAL.md`, `docs/LANGCHAIN_ARCHITECTURE_MIGRATION.md`, and `docs/QUALITY_FIRST_MIGRATION_PLAN.md` in sync with implementation progress.

---

## Implementation Checklist (For Traycer or Engineers)

- [ ] Phase 0 metrics captured and logged.
- [ ] Phase 1 critic/editor agent live; formatter reflects critic results.
- [ ] Phase 2 tool wrappers + schemas implemented and tested.
- [ ] Phase 3 DeepAgents supervisor pilot executed; outputs archived.
- [ ] Phase 4 escalation loop documented and tested.
- [ ] Phase 5 decision recorded with go/no-go criteria.
- [ ] All phases validated via sample-mode runs and `./scripts/run_all_checks.sh`.

This Markdown file can be fed directly to Traycer so it can generate detailed task plans without referencing non-existent paths.


