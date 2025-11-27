# Output Agent Optimization Prompt

**Role:** Senior AI Engineer & Product Architect
**Task:** Audit and update all "outputter" agents (Presentation, Insight, Report, Narrative) to fully utilize the rich metadata and optimization gains from the upstream `TopicDetectionAgent` and `TopicSentimentAgent`.

## Context
We have successfully refactored the upstream detection and sentiment agents to be:
1.  **More Accurate:** Using "Smart LLM" classification with hints and few-shot prompting.
2.  **More Efficient:** Skipping LLM calls for high-confidence keywords (saving ~30% cost).
3.  **More Nuanced:** Producing "Hilary-style" sentiment insights (e.g., "Users love X but hate Y").
4.  **Better Structured:** Returning strict JSON with confidence scores, detection methods, and specific subtopics.

**Current Problem:** The downstream output agents (`PresentationAgent`, `InsightAgent`, `GammaGenerator`) are likely still treating the input data as generic blobs. They are re-summarizing already perfect sentiment sentences into generic bullet points, ignoring confidence scores, and failing to highlight the efficiency/accuracy of the analysis.

## Objectives
Update the following agents to **pass-through** and **highlight** the upstream intelligence rather than flattening it.

### 1. PresentationAgent (`src/agents/presentation_agent.py`)
- **Action:** Stop re-writing sentiment insights.
- **Implementation:**
    - Extract `sentiment_insight` from `TopicSentimentAgent` results and use it **verbatim** in Gamma slides as the "Key Takeaway" or "Customer Voice" header.
    - *Why:* The sentiment agent now produces "Users love the export feature but are confused by format options". If PresentationAgent rewrites this to "Export feature sentiment is mixed", we lose the value.
- **Action:** Visualize Confidence & Efficiency.
    - In the "Methodology" or "Appendix" slide, include:
        - "Analysis Confidence: {confidence_level}"
        - "Optimization: {skip_pct}% of tickets resolved via high-confidence patterns (Efficiency Saving)"
    - *Source:* `TopicDetectionAgent` -> `fallback_metrics` and `confidence` fields.

### 2. Gamma Generator (`src/services/gamma_generator.py` / prompts)
- **Action:** Use specific Subtopics.
- **Implementation:**
    - When generating slide bullets for a category (e.g., "Billing"), look for the `subtopic` or `specific_label` field from the detection results.
    - Instead of 5 bullets of "Billing Issues", group them: "Refund Requests (30%)", "Invoice Clarity (20%)".
    - *Source:* `TopicDetectionAgent` -> `topics_by_conversation` -> `subtopic` field.

### 3. InsightAgent (`src/agents/insight_agent.py`)
- **Action:** Qualify insights with detection method.
- **Implementation:**
    - If a finding relies heavily on "Keyword" detection (low confidence), tag it: "(Trend detected via keyword patterns)".
    - If a finding relies on "LLM Smart" (high confidence), tag it: "(Verified by AI Analysis)".
    - *Source:* `topic_distribution` -> `detection_method`.

### 4. NarrativeFormatterAgent (if applicable)
- **Action:** Preserve the "Hilary Tone".
- **Implementation:** Ensure the narrative arc uses the specific emotional words ("frustrated", "delighted", "confused") found in the `TopicSentimentAgent` output, rather than neutralizing them to "negative" or "positive".

## Implementation Checklist
For each agent, verify:
1.  [ ] **Input Validation:** Are we checking for the new fields (`sentiment_insight`, `subtopic`, `detection_method`)?
2.  [ ] **Prompt Update:** Have we updated the system instructions to say "Use provided sentiment insights verbatim"?
3.  [ ] **Data Passing:** Are the `fallback_metrics` being passed through `AgentContext` to the final report?
4.  [ ] **Visuals:** Does the final output (Gamma/PDF) visually distinguish between high-confidence and standard findings?

## Verification
- Run a full analysis (`python src/main.py comprehensive ...`).
- Inspect the Gamma presentation.
- **Success Criteria:**
    - Slide headers use the specific "Hilary-style" sentiment sentences.
    - Methodology slide mentions "Hybrid Detection" or efficiency stats.
    - Subtopics are visible in category breakdowns.
    - No generic "mixed sentiment" bullets.

## Command to Run
To validate these changes, use the sample mode and check the intermediate JSON outputs before generating the presentation:
```bash
python src/main.py sample-mode --count 50 --save-to-file
# Then inspect outputs/latest_run/results.json for the new fields
```

