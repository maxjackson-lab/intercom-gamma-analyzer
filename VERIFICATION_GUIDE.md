## Verification Guide

### 1. Overview
- Confidence-based routing (>=0.85) must skip LLM calls when keyword/taxonomy scores are high while logging `high_confidence_skip_count`, `llm_calls`, and detection method breakdowns.
- Sentiment insights from TopicSentimentAgent/SentimentAgent must flow verbatim through OutputFormatterAgent into PresentationBuilder (Hilary-style, nuanced, no generic labels).
- Metrics visibility: `fallback_metrics`, optimization efficiency, detection method tagging, and subtopic percentages must appear in JSON, logs, and presentation methodology appendices.
- Multi-language support: Russian/Korean keywords must classify conversations via TaxonomyManager and TopicDetectionAgent with correct detection method annotations.

### 2. Prerequisites
- Python 3.11+, Poetry or pip with `requirements.txt`.
- Intercom + LLM credentials in environment (`INTERCOM_ACCESS_TOKEN`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`).
- DuckDB file `conversations.duckdb` populated or mock dataset.
- Access to `outputs/` directory for generated JSON/log/presentation artifacts.
- Recommended virtualenv:
  ```
  python3 -m venv .venv
  source .venv/bin/activate
  pip install -r requirements.txt
  ```

### 3. Test Suite Verification
- Command: `pytest tests/test_prompt_optimization.py -v`
- Expected result: all 1278 lines of tests pass with 0 failures, 0 errors, 0 xfails.
- Optional targeted subsets:
  - `pytest tests/test_prompt_optimization.py -k "confidence_routing"`
  - `pytest tests/test_prompt_optimization.py -k "sentiment"`
- Captured metrics should reference `TopicDetectionAgent`, `TopicSentimentAgent`, and `PresentationBuilder` improvements.

### 4. Sample Mode Verification
1. Seed sample mode with 50 conversations:
   ```
   python src/main.py sample-mode --count 50 --save-to-file
   ```
2. Ensure output artifacts saved to `outputs/sample_mode_<timestamp>/`.
3. Confirm console states:
   - `Confidence routing enabled (threshold=0.85)`
   - `High-confidence skips: <value>`
   - `LLM calls executed: <value>`
4. Verify generated files:
   - `analysis.json`
   - `analysis.log`
   - `presentation.md`

### 5. Log Analysis Guide
- File path: latest `outputs/*/analysis.log`.
- Key regex patterns:
  - `Skipped LLM for (?P<count>\d+)(?:/(?P<total>\d+))? conversations`
  - `Confidence Routing Metrics: (?P<skips>\d+) skips.*?, (?P<llm>\d+) LLM calls`
  - `Detection methods:.*llm_smart=`
  - `Optimization Efficiency:\s*(?P<value>\d+\.\d+)%`
  - `Sentiment Quality:\s*Score=(?P<score>\d+\.\d+)`
- Confirm `fallback_metrics` summary logs contain:
  - `high_confidence_skip_count`
  - `llm_calls`
  - `keyword_matches` (via Detection methods summary)
  - `hybrid_detections` (via Detection methods summary)
- Ensure sentiment nuance logs highlight Hilary-style phrasing.

### 6. Output Validation
- JSON (`analysis.json`):
  - Each topic entry includes `detection_method` (or `detection_method_tag`).
  - `sentiment_insight` checked for generic phrasing ONLY if present.
  - `fallback_metrics` object contains `total_conversations`, `llm_calls`, `high_confidence_skip_count`.
  - Subtopics contain `percentage` fields (e.g., `0.32` → 32%).
  - Verification snippet:
    ```json
    {
      "topic": "Billing Pain",
      "detection_method_tag": "(Verified by AI Analysis)",
      "sentiment_insight": "Customers appreciate refunds but highlight delays...",
      "fallback_metrics": {
        "high_confidence_skip_count": 18,
        "llm_calls": 32,
        "optimization_rate": 36.0
      }
    }
    ```
- Presentation markdown:
  - Sentiment sections should match JSON verbatim.
  - Methodology appendix contains table with headers `Metric | Value`.
  - Subtopic sections show `Label (XX%)`.

### 7. Multi-Language Testing
- Use `scripts/test_multi_language_keywords.py --language all`.
- Expected matches:
  - Russian: `аккаунт` → Account Access, `оплата/возврат` → Billing, `ошибка` → Bug.
  - Korean: `계정` → Account, `결제/환불` → Billing, `오류` → Bug.
- Verify detection method logs show `keyword` or `hybrid`.
- Confidence scores should exceed 0.6 for direct keyword hits.

### 8. Troubleshooting
- **Missing metrics**: Re-run sample mode with `--verbose`, ensure `fallback_metrics` populated by agents.
- **No presentation output**: Confirm Gamma API credentials; fallback markdown should still exist in `outputs/`.
- **LLM overuse**: Adjust threshold in `TopicDetectionAgent` (`confidence_threshold`), re-run tests.
- **Encoding issues**: Ensure terminal environment uses UTF-8 (`export PYTHONUTF8=1`).

### 9. Success Criteria Checklist
- [ ] `pytest tests/test_prompt_optimization.py -v` passes with zero failures.
- [ ] Sample mode run with 50 conversations completes successfully with saved artifacts.
- [ ] Logs show confidence routing, detection method breakdowns, sentiment quality scores.
- [ ] JSON output contains sentiment insights, fallback metrics, detection method tags, subtopic percentages.
- [ ] Presentation markdown preserves verbatim sentiment insights and includes methodology metrics table.
- [ ] Multi-language script confirms Russian/Korean keyword coverage with confidence >0.6.
- [ ] No unresolved issues in troubleshooting section after verification cycle.

