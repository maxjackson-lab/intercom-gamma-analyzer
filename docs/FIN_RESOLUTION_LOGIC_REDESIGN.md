# Fin Resolution Logic Redesign

## Soft Failure Detection and True Resolution Rate

### Problem Statement
We identified a "100% Resolution" bug where conversations were marked as resolved by Intercom (and our legacy logic) simply because they were closed without human admin intervention. However, a deeper analysis revealed that many of these "resolved" tickets actually contained explicit escalation requests or frustration signals from customers, such as:
- "I need a human"
- "Still broken"
- "Didn't fix"
- "Useless"

This led to inflated resolution rates that didn't accurately reflect the customer experience or the true effectiveness of the Fin AI agent.

### Solution
We have enhanced the `FinPerformanceAgent` to explicitly track "Soft Failures" and calculate a "True Resolution Rate".

**Soft Failures** are defined as conversations that:
1. Meet technical resolution criteria (Closed state, no human admin response).
2. Contain negative sentiment or explicit escalation keywords in the customer's messages.

### Implementation Details

#### detection Logic
The detection uses `detect_soft_failure()` from `src/services/fin_escalation_analyzer.py`. It scans customer messages for patterns including:
- **Escalation Requests:** "need human", "want agent", "talk to person", "customer support"
- **Unresolved Issues:** "still broken", "didn't fix", "same issue", "doesn't work"
- **Frustration:** "useless", "waste of time", "bad bot", "never mind"
- **Explicit Negation:** "not helpful", "wrong", "incorrect"

#### New Metrics
The following metrics have been added to the tier-based analysis output:

1.  **`soft_failure_count`**: The number of conversations that were technically resolved but contained soft failure signals.
2.  **`soft_failure_rate`**: The percentage of total conversations identified as soft failures.
3.  **`true_resolution_rate`**: The resolution rate excluding soft failures.
    *   Formula: `(Resolved Count - Soft Failure Count) / Total Conversations`
    *   This provides a quality-adjusted view of Fin's performance.
4.  **`soft_failure_examples`**: A list of up to 3 example conversations (ID, preview, URL) to help audit these failures.

### Integration with LLM Insights
The `_generate_tier_insights()` method has been updated to include these new metrics in the prompt sent to the LLM. The LLM is explicitly instructed to:
- Highlight soft failure patterns.
- Discuss their impact on true resolution quality.
- Differentiate between "Intercom Resolution" (technical) and "True Resolution" (quality).

### Testing
New test cases in `tests/test_fin_performance_agent.py` validate:
- Detection of specific keywords ("still broken", "I need a human").
- Correct calculation of `true_resolution_rate`.
- Structure of the `soft_failure_examples` list.

### Example Output Structure
```json
{
  "total_conversations": 100,
  "resolution_rate": 0.75,          // 75 technically resolved
  "resolved_count": 75,
  "soft_failure_count": 10,         // 10 of those 75 were actually soft failures
  "soft_failure_rate": 0.10,
  "true_resolution_rate": 0.65,     // (75 - 10) / 100 = 65%
  "soft_failure_examples": [
    {
      "id": "123",
      "preview": "I tried that but it is still broken...",
      "intercom_url": "..."
    }
  ]
}
```



