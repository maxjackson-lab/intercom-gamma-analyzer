# Phase 3 Resilience Standardization

> **Status:** ✅ Complete (December 2025)  
> **Scope:** Universal semaphore controls, timeout governance, and data-quality gates across all orchestrators/agents.

## 1. Executive Summary

| Problem | Phase 2 Reality | Phase 3 Fix |
| --- | --- | --- |
| Concurrency drift | Agents hardcoded `asyncio.Semaphore(5)` regardless of provider limits → Anthropic Tier 1 (50 RPM) thrashed at 5 concurrent calls | `settings.py` defines provider quotas (Anthropic=2, OpenAI=20) and `get_recommended_semaphore()` enforces them everywhere |
| Timeout chaos | Agents used 30s, 60s, 300s (copy/paste) with no orchestration buffer | Per-agent timeouts live in `settings.py`; `BaseOrchestrator._get_agent_timeout()` multiplies by 3× for orchestration |
| Silent data loss | Segmentation/Topic detection drops quietly cascaded to formatter → “diluted gibberish” reports | `BaseOrchestrator.log_stage_metrics()` watches stage counts and emits warnings on >10% drops; strategies log at mandatory checkpoints |

**Benefits:** predictable rate-limit behavior, tunable timeouts via env vars, and early detection of data starvation before executive output dilution.

## 2. Semaphore Standardization

### Configuration

`src/config/settings.py`

| Setting | Default | Env Var | Notes |
| --- | --- | --- | --- |
| `openai_concurrency` | `20` | `OPENAI_CONCURRENCY` | Matches GPT-4o 600 RPM limit with healthy buffer |
| `anthropic_concurrency` | `2` | `ANTHROPIC_CONCURRENCY` | Anthropic Tier 1 = 50 RPM ⇒ 0.8 RPS ⇒ max 2 concurrent |

### Usage Pattern

```python
from src.utils.ai_client_helper import get_ai_client, get_recommended_semaphore

self.ai_client = get_ai_client()
self.llm_semaphore = get_recommended_semaphore(self.ai_client)
```

- Agents **never** instantiate `asyncio.Semaphore` directly.
- `get_recommended_semaphore()` inspects the provider (OpenAI vs. Claude) and returns the configured limit.
- Env overrides let ops dial concurrency without code changes:
  ```bash
  export ANTHROPIC_CONCURRENCY=1   # SLA-driven slowdown
  export OPENAI_CONCURRENCY=10     # Temporary reduction
  ```

### Rationale

Anthropic Tier 1 (50 RPM) translates to ~0.8 requests/second. Without semaphores, bursty orchestrators triggered 429s and backoff storms. Provider-aware semaphores ensure all agents—especially `OutputFormatterAgent`, `TopicDetectionAgent`, and `TrendAgent`—respect live limits.

## 3. Timeout Standardization

### Configuration

`settings.py` exposes per-agent LLM timeouts (`topic_detection_timeout`, `subtopic_detection_timeout`, `output_formatter_timeout`, etc.) plus `llm_timeout_default`.

```python
class Settings(BaseSettings):
    llm_timeout_default: int = Field(60, env="LLM_TIMEOUT_DEFAULT")
    topic_detection_timeout: int = Field(180, env="TOPIC_DETECTION_TIMEOUT")
    output_formatter_timeout: int = Field(120, env="OUTPUT_FORMATTER_TIMEOUT")
    # ...
```

### Orchestrator Multiplier

`BaseOrchestrator._get_agent_timeout()` enforces:

```
orchestrator_timeout = agent_timeout * 3
```

Example:

- TopicDetectionAgent → 180s agent timeout → 540s orchestrator window
- OutputFormatterAgent → 120s agent timeout → 360s orchestrator window

This buffer absorbs SDK retries, network jitter, and multi-call agents without prematurely failing the pipeline.

### Overrides

```bash
export TOPIC_DETECTION_TIMEOUT=90
export OUTPUT_FORMATTER_TIMEOUT=180
export LLM_TIMEOUT_DEFAULT=75
```

No code change required; restart process to pick up new env vars (or rely on hot reload in dev).

## 4. Data Quality Gates

### Mechanism

`BaseOrchestrator.log_stage_metrics(stage_name, count)` tracks record counts between pipeline stages:

1. Logs `STAGE METRIC: <stage> = <count>`
2. Compares to previous stage
3. Emits 🚨 warning if drop >10%

```python
self.log_stage_metrics("Post-Segmentation", len(paid) + len(free_fin))
```

### Mandatory Checkpoints (VOC Strategy)

`VoiceOfCustomerStrategy` logs four canonical checkpoints:

1. **Post-Fetch** – immediately after pulling Intercom conversations
2. **Post-Segmentation** – after SegmentationAgent splits paid/free
3. **Post-TopicDetection** – after assigning conversations to topics
4. **Pre-Formatting** – right before OutputFormatterAgent consumes results

These guardrails ensure downstream agents never ingest dramatically fewer conversations than upstream phases produced.

### Alert Example

```
🚨 DATA DROP ALERT: Post-Segmentation dropped 15 items (15.0%) from previous stage (100 -> 85)
```

Actionable steps appear in the Failure Mode Runbook (see §8).

## 5. Configuration Reference

| Category | Setting | Default | Env Var |
| --- | --- | --- | --- |
| Concurrency | `openai_concurrency` | 20 | `OPENAI_CONCURRENCY` |
|  | `anthropic_concurrency` | 2 | `ANTHROPIC_CONCURRENCY` |
| Timeouts | `llm_timeout_default` | 60s | `LLM_TIMEOUT_DEFAULT` |
|  | `topic_detection_timeout` | 180s | `TOPIC_DETECTION_TIMEOUT` |
|  | `output_formatter_timeout` | 120s | `OUTPUT_FORMATTER_TIMEOUT` |
|  | `subtopic_detection_timeout` | 60s | `SUBTOPIC_DETECTION_TIMEOUT` |
|  | `sentiment_timeout` | 60s | `SENTIMENT_TIMEOUT` |
| Data Gates | (no env) | governed by orchestrator | — |

## 6. Testing & Verification

1. **Unit Tests** – `tests/test_resilience_standardization.py`
   - Validates semaphores, timeouts, stage metrics, and integration behavior.
2. **Validation Script** – `python scripts/validate_resilience_standards.py`
   - Detects hardcoded semaphores/timeouts and missing quality gates.
3. **Sample Mode** – `python src/main.py sample-mode --count 100 --test-all-agents --save-to-file`
   - Confirms real Intercom runs respect limits (watch `.log` for 429s/timeouts).
4. **Observability** – Analyze `outputs/*observability.json` for timeout/rate-limit spikes.

## 7. Migration Guide

### Agents

**Before**
```python
self.llm_semaphore = asyncio.Semaphore(5)
```

**After**
```python
self.ai_client = get_ai_client()
self.llm_semaphore = get_recommended_semaphore(self.ai_client)
```

### Orchestrators / Strategies

1. Insert `self.log_stage_metrics("Stage Name", count)` after each major transformation.
2. Rely on `_execute_with_timeout()` to wrap agent calls; never call `asyncio.wait_for` manually.
3. If a new agent needs a unique timeout, add `X_timeout` to `settings.py` and reference it in `_get_agent_timeout`.

## 8. Troubleshooting

| Symptom | Checklist |
| --- | --- |
| 429 / rate limit errors | Verify `settings.anthropic_concurrency` and `settings.openai_concurrency`. Run `python scripts/validate_resilience_standards.py` to ensure no hardcoded semaphores remain. Lower env overrides if necessary. |
| Frequent agent timeouts | Increase relevant timeout env var (`TOPIC_DETECTION_TIMEOUT`, etc.). Confirm `_get_agent_timeout` already applies 3× buffer. |
| `DATA DROP ALERT` warnings | Inspect stage referenced in log. Review upstream agent outputs for filtering bugs or invalid schema assumptions. Add missing `log_stage_metrics()` calls if the stage is invisible to the gate. |
| Silent quality degradation | Ensure Stage metrics never drop >10%; run validation script to confirm gates exist. Execute sample-mode to reproduce with real data. |

## 9. References

- `src/utils/ai_client_helper.py`
- `src/config/settings.py`
- `src/services/base_orchestrator.py`
- `src/services/strategies/voc_strategy.py`
- `docs/LLM_RATE_LIMITING_IMPLEMENTATION.md`
- `docs/ORCHESTRATOR_CONSOLIDATION.md`
- `FAILURE_MODE_RUNBOOK.md`

