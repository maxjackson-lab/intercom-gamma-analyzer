# Architecture Decision Record: Quality-First Migration

**Status:** Experimentation Phase
**Context:** Recent runs produced empty or repetitive reports.
**Decision:** Prioritize **Quality & Content** over pure Architecture Refactoring.

## The "Goo" Problem
User reports that despite better math/tracking, the output is a "muddled mass of goo." This is likely due to:
1.  **Context Dilution:** `OutputFormatterAgent` receives a 30k+ token dump of all previous results.
2.  **Single-Shot Generation:** It tries to write the entire report in one pass.
3.  **Lack of Critique:** No step validates if the insights are unique vs. repetitive.

## Strategy: Introduce "The Editor" (Supervisor Pattern Lite)

Instead of rewriting the entire orchestrator to LangGraph immediately, we will inject a **Quality Control Loop** into the existing pipeline.

### 1. The Logic
Current: `Data -> Insight -> Format -> Output`
Proposed: `Data -> Insight -> Critic -> (Refine) -> Format -> Output`

### 2. Implementation Plan

**Step 1: Create `EditorAgent`**
- **Role:** Critic & Rewriter.
- **Input:** Raw insights from `InsightAgent` + Raw topic summaries.
- **Instructions:**
    - "Identify repetitive phrases."
    - "Check if 'Product Question' insight is specific or generic."
    - "Rewrite bullet points to be distinct."
- **Output:** Refined JSON.

**Step 2: Manual Integration**
- Insert `EditorAgent` into `VoiceOfCustomerStrategy` *before* `OutputFormatterAgent`.
- If `EditorAgent` flags low quality, we can optionally loop back (later) or just use the rewritten content.

**Step 3: Validate Quality**
- Run `sample-mode`.
- Compare the "Before Editor" vs "After Editor" output.
- Only IF quality improves do we proceed with the full LangGraph migration.

## Why This Path?
- **Addresses the User's Core Pain:** "Output is goo."
- **Low Risk:** Doesn't break the pipeline logic, just adds a refinement step.
- **Proven Pattern:** "Reflection" is the most effective pattern for improving LLM writing (per Andrew Ng / LangChain).


## Phase 1: Critic Rubric & Scoring System

### Quality Dimensions

The EditorAgent evaluates insights across five dimensions, each scored 0.0-1.0:

1. **Specificity Score** (0.0-1.0)
   - 1.0: Concrete details ("API slide generation overflow", "23% escalation rate")
   - 0.5: Generic categories ("Product Questions", "Billing issues")
   - 0.0: Vague placeholders ("Various issues", "Customer concerns")
   - **Threshold**: ≥ 0.6 required

2. **Metric Density Score** (0.0-1.0)
   - Based on `metric_references_count` from InsightAgent
   - 1.0: ≥ 8 quantified metrics per report
   - 0.7: 5-7 metrics
   - 0.4: 2-4 metrics
   - 0.0: < 2 metrics
   - **Threshold**: ≥ 0.5 required (5+ metrics)

3. **Repetition Score** (0.0-1.0)
   - Based on `insight_duplicate_ratio` from InsightAgent
   - 1.0: duplicate_ratio ≤ 0.10 (minimal repetition)
   - 0.7: duplicate_ratio 0.11-0.15 (acceptable)
   - 0.4: duplicate_ratio 0.16-0.30 (concerning)
   - 0.0: duplicate_ratio > 0.30 (excessive)
   - **Threshold**: ≥ 0.7 required (duplicate_ratio ≤ 0.15)

4. **Distinctness Score** (0.0-1.0)
   - Evaluates whether topic insights sound different from each other
   - 1.0: Each topic has unique emotional descriptors and specific issues
   - 0.5: Some overlap in phrasing across topics
   - 0.0: Copy-paste sentiment across all topics
   - **Threshold**: ≥ 0.6 required

5. **Actionability Score** (0.0-1.0)
   - Evaluates whether insights lead to clear next steps
   - 1.0: Specific recommendations with owners/timelines
   - 0.5: General suggestions without specifics
   - 0.0: No actionable guidance
   - **Threshold**: ≥ 0.5 required

### Composite Quality Score

**Formula**: `composite_score = (specificity * 0.25) + (metric_density * 0.25) + (repetition * 0.25) + (distinctness * 0.15) + (actionability * 0.10)`

**Overall Thresholds:**
- **High Quality**: composite_score ≥ 0.75 → No rewrite needed
- **Acceptable**: 0.60 ≤ composite_score < 0.75 → Optional rewrite
- **Needs Improvement**: composite_score < 0.60 → Rewrite required

### Rewrite Decision Logic

```python
rewrite_needed = (
    composite_score < 0.60 or
    specificity_score < 0.6 or
    metric_density_score < 0.5 or
    repetition_score < 0.7
)
```

### Critic Prompt Template

The EditorAgent uses this prompt structure for scoring:

```
You are a Quality Critic evaluating Voice of Customer insights.

Evaluate the following insights across 5 dimensions:
1. Specificity (0.0-1.0): Are insights concrete vs. generic?
2. Metric Density (0.0-1.0): How many quantified metrics are present?
3. Repetition (0.0-1.0): Are phrases reused across topics?
4. Distinctness (0.0-1.0): Does each topic sound unique?
5. Actionability (0.0-1.0): Are recommendations specific?

Return JSON:
{
  "specificity_score": 0.0-1.0,
  "metric_density_score": 0.0-1.0,
  "repetition_score": 0.0-1.0,
  "distinctness_score": 0.0-1.0,
  "actionability_score": 0.0-1.0,
  "composite_score": 0.0-1.0,
  "rewrite_needed": true/false,
  "issues_found": ["list of specific problems"],
  "rewrite_guidance": "specific instructions for improvement"
}
```

### Validation Criteria

Phase 1 is successful when:
- Mean composite_score improves by ≥ 20% vs. Phase 0 baseline
- ≥ 80% of reports score ≥ 0.60 (acceptable or better)
- Duplicate ratio < 0.15 in ≥ 90% of runs
- Metric references ≥ 5 in ≥ 90% of runs
- Topic fallback usage remains at 0

Store validation results in `outputs/critic_scores/phase1_validation_*.json`.

