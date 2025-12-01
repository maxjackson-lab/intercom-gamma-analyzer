<!-- f4f84cc0-1c55-4717-b15a-748569e47de8 e3fd147f-5350-42bf-8257-6875c4e54002 -->
# Systemic "Black Box" Audit & Refactor Plan

## Objective

Break open the "black box" of the VoC pipeline. Audit **every single agent** (not just the ones you complained about) to determine if they are generating real insight or just "diluted gibberish." Fix the known issues (Fin/Sentiment) and any hidden failures discovered.

## Phase 1: The "Black Box" Audit (Systemic Review)

Run `sample-mode` with `--count 100`, `--test-all-agents`, `--save-to-file`, and `--show-agent-thinking` to generate a complete observability trace.

**Audit Checklist for EACH Agent:**

1. **SegmentationAgent:** Does it actually detect "Horatio" vs "Boldr" correctly from email domains, or is it defaulting?
2. **TopicDetectionAgent:** Is it relying on keywords (fast) or LLM (smart)? Is it missing nuance?
3. **SubTopicDetectionAgent:** Are "Tier 3" themes real, or LLM hallucinations based on 3 samples?
4. **ExampleExtractionAgent:** Does it pick *good* quotes, or just the first 3 it finds?
5. **FinPerformanceAgent:** (Known issue: Logic update required).
6. **BpoPerformanceAgent:** Is it actually calculating "pressure points" or just counting tickets?
7. **TrendAgent:** Is it comparing real historical data, or hallucinating trends from a single run?
8. **Correlation/Quality/Churn (Phase 4.5):** Are these adding value or noise? Are they receiving enough context to find real patterns?
9. **OutputFormatterAgent:** What valid data is it *dropping* on the floor?

## Phase 2: The "No-Nonsense" Code Refactor (Known Fixes)

Apply the agreed-upon fixes immediately to unblock the obvious pain:

1. **Sentiment:** Pivot to "IDENTIFY CUSTOMER PAIN" (3-4 sentence deep dive). Uncap length.
2. **Fin:** Implement "Soft Failure" detection (scan all user messages). Fix "100% resolution" bug.
3. **Formatter:** Rewrite Executive Summary to "Headline the FIRES". Force BPO section visibility.

## Phase 3: The "Hidden Failures" Fixes (New Findings)

Based on Phase 1 audit:

- **Disable/Kill** agents that are proven to be "useless gibberish" (likely Phase 4.5).
- **Refactor** agents that have potential but bad prompting (e.g., `ExampleExtraction`).
- **Enhance** input data flow for agents that are "starved" of context.

## Phase 4: Reporting & Verification

Generate `docs/AGENT_AUDIT_RESULTS.md`:

- **Agent Scorecard:** Pass/Fail for every agent.
- **Context Loss Map:** Diagram showing exactly where detail is lost in the pipeline.
- **Actionable Insights:** What the *fixed* system actually found in the 100-ticket sample.