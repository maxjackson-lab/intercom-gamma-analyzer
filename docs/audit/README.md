# Agent Audit System

This directory contains audit reports and documentation for the VoC pipeline agent validation system.

## Overview

The audit system validates all 15 agents in the VoC pipeline to detect:
- **Hallucinations**: Generic language, contradictions, unsupported claims, fabricated data
- **Quality Issues**: Low specificity, missing evidence, inconsistent outputs
- **Logic Errors**: Incorrect calculations, faulty reasoning, missing validations

## Running Audits

### Quick Audit (10 conversations)
```bash
python -m src.cli.main sample-mode --count 10 --audit-mode --test-all-agents
```

### Full Audit (100 conversations)
```bash
python -m src.cli.main sample-mode --count 100 --audit-mode --test-all-agents --save-to-file
```

### Audit with Agent Thinking Logs
```bash
python -m src.cli.main sample-mode --count 100 --audit-mode --test-all-agents --show-agent-thinking
```

## Audit Reports

### Generated Reports
- `agent_audit_report_{timestamp}.md` - Human-readable audit report with Pass/Fail scorecard
- `agent_audit_results_{timestamp}.json` - Structured audit data for analysis

### Phase-Specific Audits
- `core_pipeline_audit.md` - Segmentation, Topic, SubTopic, Sentiment, Examples (Phase 2)
- `performance_agents_audit.md` - Fin, BPO performance analysis (Phase 3)
- `analytical_agents_audit.md` - Correlation, Quality, Churn, Confidence (Phase 4)
- `output_trend_audit.md` - Formatter, Trend, Optional agents (Phase 5)

## Quality Scoring

Each agent receives a quality score (0.0-1.0) based on:
- **Specificity** (0.3): Are insights specific or generic?
- **Evidence** (0.3): Are claims backed by data?
- **Consistency** (0.2): Are outputs consistent with input and metrics?
- **Completeness** (0.2): Are all expected fields present?

**Pass Threshold**: 0.6 or higher

**Note**: Agents without a specific auditor implementation are marked as **Not Audited** and receive a failing/neutral score to ensure they are not mistakenly considered validated.

## Hallucination Detection

The system detects:
1. **Generic Language**: "customers are frustrated", "users want", "people need"
2. **Contradictions**: "high satisfaction" but CSAT=2, positive sentiment with many pain points
3. **Unsupported Claims**: "trending up" without historical data, "significant increase" without numbers
4. **Fabricated Data**: Fake conversation IDs, URLs, timestamps not present in the source data
5. **Missing Citations**: Claims without evidence

## Agent-Specific Checks

See individual audit reports for agent-specific validation criteria.

## Troubleshooting

If an agent fails audit:
1. Check `agent_thinking_{timestamp}.log` for LLM prompts/responses
2. Review `agent_audit_results_{timestamp}.json` for detailed findings
3. Look at `issues_found` and `recommendations` in the audit report
4. Compare agent output to input data to identify discrepancies

## Next Steps

After running audits:
1. Review Pass/Fail scorecard
2. Prioritize failed agents for refactoring
3. Implement recommended fixes
4. Re-run audit to validate improvements
