# Phase 1 Black Box Audit: Execution Guide

## References
- `src/main.py`
- `src/cli/sample_commands.py`
- `src/services/sample_mode.py`
- `src/utils/agent_audit.py`
- `scripts/analyze_observability.py`

This guide details the comprehensive execution of the Phase 1 Black Box Audit, designed to validate the performance, quality, and reliability of the 11 production agents using real Intercom data.

## Section 1: Pre-Execution Checklist

Before running the audit, ensure the following:

1. **Environment Setup**:
   ```bash
   export PYTHONPATH=$PYTHONPATH:.
   ```

2. **Credentials**:
   - Check `.env` has valid `INTERCOM_ACCESS_TOKEN` and `OPENAI_API_KEY`.

3. **Resources**:
   - Ensure sufficient Intercom API quota (fetches 100 conversations).
   - Ensure sufficient OpenAI API quota (approx. 50 complex LLM calls).
   - Verify disk space for output files (~50MB expected).

## Section 2: Command Execution

Run the following command from the project root:

```bash
PYTHONPATH=. python src/main.py sample-mode --count 100 --test-all-agents --save-to-file --show-agent-thinking --audit-mode
```

### Execution Flow
1. **Ingestion**: Fetches 100 conversations from Intercom (defaulting to the last 7 days).
2. **Segmentation**: Classifies conversations (Paid vs. Free, Vendor detection).
3. **Topic Detection**: Identifies primary topics for each conversation.
4. **Agent Pipeline**: Executes 9 additional agents:
   - SubTopic Detection
   - Topic Sentiment
   - Example Extraction
   - Fin Performance
   - Correlation Analysis
   - Quality Assessment
   - Churn Risk
   - Confidence Scoring
   - BPO Workload Analysis
5. **Audit Validation**: Runs automated validation logic on all outputs.
6. **Reporting**: Generates audit reports and observability JSON files.

**Runtime**: Expect 5-10 minutes depending on API latency and LLM response times.
**Console Output**: Displays progress bars and ✅/❌ status for each agent.

## Section 3: Output Files Analysis

The audit generates four key files in the `outputs/` directory. Replace `{timestamp}` with the actual runtime string.

| File | Description |
|------|-------------|
| `agent_thinking_{timestamp}.log` | **Human-Readable Log**: Contains full LLM prompts, responses, and agent reasoning. Use this to spot check "reasoning chains". |
| `agent_thinking_{timestamp}.observability.json` | **Structured Data**: Metrics on token usage, error rates, success rates, and event tracking. |
| `agent_audit_report_{timestamp}.md` | **Scorecard**: A markdown report with Quality Scores (0.0-1.0), Pass/Fail status, and specific issues found. |
| `agent_audit_results_{timestamp}.json` | **Raw Audit Data**: Detailed machine-readable validation results. |

### Analyzing Observability Data
Run the analysis script to visualize performance patterns:

```bash
python scripts/analyze_observability.py outputs/agent_thinking_{timestamp}.observability.json
```

**Key Metrics:**
- **Overall Statistics**: Total events, global success rate, total errors, total tokens.
- **Events by Type**: Breakdown of prompts vs. responses vs. errors.
- **Events by Agent**: Identifying which agents are most active or error-prone.
- **Error Analysis**: Counts of timeouts, rate limits (429), and validation failures.
- **Agent Performance**: Individual success rates and token consumption.

## Section 4: Interpreting Audit Results

### Audit Scorecard
- **Quality Score**: 0.0 to 1.0.
  - **≥ 0.8**: ✅ PASS
  - **0.6 - 0.79**: ⚠️ RISK (Requires improvement)
  - **< 0.6**: ❌ FAIL (Critical issues)
- **Status**: Pass/Fail based on score.
- **Issues Found**: Specific validation errors (e.g., "Missing required field 'reasoning'").
- **Hallucination Flags**: Detections of generic language, contradictions, or fabricated data points.

### Critical Flags
- **Quality Score < 0.6**: Immediate investigation required.
- **Hallucination Flags**: Indicates the agent is guessing rather than analyzing data.
- **High Error Rates**: Check observability JSON for timeouts or rate limits.
- **Prompt/Response Mismatch**: Often indicates timeouts or silent failures.

## Section 5: Common Failure Patterns

1. **Timeouts**:
   - *Symptom*: Prompts logged but no matching response.
   - *Fix*: Adjust `llm_timeout` or reduce batch size.

2. **Rate Limit Thrashing**:
   - *Symptom*: Multiple 429 errors in observability logs.
   - *Fix*: Check semaphore configuration or increase backoff settings.

3. **Prompt Refusals**:
   - *Symptom*: LLM returns safety refusals or "I cannot answer".
   - *Fix*: Review prompt engineering for sensitive terms or complexity.

4. **Hallucinations**:
   - *Symptom*: Generic phrases like "customers are frustrated" without specifics.
   - *Fix*: Strengthen "grounding" instructions in system prompts.

5. **Data Drops**:
   - *Symptom*: Agents return success but output is empty.
   - *Fix*: Check input validation and filtering logic.

6. **Double-Counting**:
   - *Symptom*: Topic detection assigns >2 topics per conversation, inflating volume.
   - *Fix*: Tune topic overlap thresholds.

## Section 6: Next Steps

1. **Immediate Review**: Open `agent_audit_report_{timestamp}.md`.
2. **Systemic Analysis**: Run `scripts/analyze_observability.py`.
3. **Consolidation**: Run `scripts/consolidate_audit_results.py` to update the master record.
   ```bash
   python scripts/consolidate_audit_results.py \
     --audit-report outputs/agent_audit_report_{timestamp}.md \
     --observability outputs/agent_thinking_{timestamp}.observability.json \
     --output docs/AGENT_AUDIT_RESULTS.md
   ```
4. **Prioritization**:
   - **P0**: Fix failing agents (< 0.6 score).
   - **P1**: Address hallucination flags.
   - **P2**: Optimize high error rate agents.
   - **P3**: Improve data quality (drops/inflation).

