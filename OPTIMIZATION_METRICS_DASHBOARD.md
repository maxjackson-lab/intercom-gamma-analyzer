## Optimization Metrics Dashboard

### 1. Overview
- **Goal:** Sustain 30%+ reduction in LLM calls via confidence routing while keeping accuracy high.
- **Sentiment Quality:** 100% of TopicSentimentAgent/SentimentAgent outputs must be Hilary-style (no generic labels).
- **Metrics Visibility:** Every analysis output exposes fallback metrics, detection method tags, and subtopic percentages.
- **Multi-Language Coverage:** Russian/Korean keyword integrity with confidence ≥0.6 on dedicated validation runs.

### 2. Current Metrics (Week of {{UPDATE_DATE}})
| Metric | Value | Target | Notes |
| --- | --- | --- | --- |
| Total conversations analyzed | {{TOTAL_CONVERSATIONS}} | — | Sample-mode baseline |
| High-confidence skips | {{HIGH_CONF_SKIPS}} ({{OPTIMIZATION_RATE}}%) | ≥30% | Logged as `high_confidence_skip_count` |
| LLM calls | {{LLM_CALLS}} | — | Includes smart + validation calls |
| Sentiment quality score | {{SENTIMENT_QUALITY}} / 1.0 | ≥0.75 | From SentimentAgent.validate_output |
| Nuanced insights | {{NUANCE_PERCENT}}% | 100% | Hilary-style connectors enforced |
| Generic sentiment detections | {{GENERIC_COUNT}} | 0 | Should remain zero |
| Detection methods (LLM/Hybrid/Keyword/SDK/Fallback) | {{DETECTION_BREAKDOWN}} | Balanced | Track via InsightAgent |
| Russian match rate | {{RU_MATCH_RATE}}% | ≥95% | scripts/test_multi_language_keywords.py |
| Korean match rate | {{KR_MATCH_RATE}}% | ≥95% | scripts/test_multi_language_keywords.py |

### 3. Historical Trends
- **Optimization Rate:** `{{HIST_OPTIMIZATION_SERIES}}`
- **LLM Call Volume:** `{{HIST_LLM_SERIES}}`
- **Sentiment Quality:** `{{HIST_SENTIMENT_SERIES}}`
- **Detection Method Mix:** `{{HIST_DETECTION_SERIES}}`

> Update trends after each weekly verification run using reports from `verification_outputs/`.

### 4. Test Suite Status
- Last run: `{{LAST_TEST_RUN_TIMESTAMP}}`
- Prompt optimization tests: ✅/❌
- End-to-end verification tests: ✅/❌
- Coverage: `{{COVERAGE_PERCENT}}%`
- Recent failures & follow-up: `{{KNOWN_FAILURES}}`

### 5. Known Issues
| ID | Description | Severity | Owner | Status |
| --- | --- | --- | --- | --- |
| {{ISSUE_ID}} | {{ISSUE_DESC}} | {{SEVERITY}} | {{OWNER}} | {{STATUS}} |

### 6. Recent Improvements
- {{DATE}} – Confidence routing telemetry refinements.
- {{DATE}} – SentimentAgent refusal detection + retries.
- {{DATE}} – Methodology appendix now shows optimization metrics table.
- {{DATE}} – Multi-language regression suite automated.

### 7. Verification Checklist
- [ ] `pytest tests/test_prompt_optimization.py -v`
- [ ] `pytest tests/test_end_to_end_verification.py -v`
- [ ] `python src/main.py sample-mode --count 50 --save-to-file`
- [ ] `python scripts/analyze_sample_mode_output.py`
- [ ] `python scripts/test_multi_language_keywords.py --language all`
- [ ] `python scripts/verify_optimizations.py --test-suite --sample-mode --multi-language`

### 8. Performance Benchmarks
| Component | Avg Time (s) | Notes |
| --- | --- | --- |
| TopicDetectionAgent (per 50 conv batch) | {{TD_TIME}} | Includes confidence routing |
| TopicSentimentAgent (per topic) | {{TS_TIME}} | Hilary few-shot prompts |
| SentimentAgent global rollup | {{SA_TIME}} | Includes refusal retry |
| Full sample-mode run (50 conversations) | {{FULL_RUN_TIME}} | Includes presentation generation |

### 9. Cost Analysis
- Tokens last week: `{{TOKEN_COUNT}}`
- Estimated cost: `$ {{ESTIMATED_COST}}`
- Cost per conversation: `$ {{COST_PER_CONV}}`
- Savings from high-confidence skips: `$ {{SAVINGS}}` ({{OPTIMIZATION_RATE}}% reduction vs baseline)

### 10. Next Steps
- [ ] Tune confidence threshold dynamically per topic tier.
- [ ] Expand keyword coverage to Japanese + German.
- [ ] Add caching for DuckDB topic rankings.
- [ ] Auto-ingest verification metrics into Ops dashboard.

> **Update Process:** Run `scripts/verify_optimizations.py` weekly, refresh metric placeholders above, and commit changes with the corresponding verification artifacts. Use reports from GitHub Actions workflow `Verify System Optimizations` for authoritative numbers.






