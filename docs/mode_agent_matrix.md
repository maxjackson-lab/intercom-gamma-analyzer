# Mode ↔ Agent Matrix

This document summarizes which multi-agent pipelines power each analysis mode and
what artifacts each mode emits. Every mode now writes through
`src/utils/output_manager.py`, so files land in the execution-specific output
directory (and always include a matching `.log` file with the complete console
stream).

| Mode / UI Option | CLI Command & Key Flags | Primary Agents / Services | Outputs (always via `output_manager`) | Notes |
| --- | --- | --- | --- | --- |
| Sample Mode (Schema Validation) | `python src/main.py sample-mode --schema-mode <depth> [--count N]` | ChunkedFetcher → SampleMode analyzer stack (LLM spot checks optional) | `sample_mode_*.json`, `.log`, optional thinking logs | Best way to see real Intercom schema; honors `--count`, `--llm-topic-detection`, hierarchy toggle |
| VoC – Hilary Topic Cards | `voice-of-customer --analysis-type topic-based` | TopicOrchestrator (Segmentation, TopicDetection, Sentiment, Examples, Fin/BPO) | Markdown report, structured JSON, `.log`, optional Gamma deck | Legacy Hilary cards; use when you specifically need the original slide layout |
| VoC – Narrative V2 *(default)* | `voice-of-customer --analysis-type narrative-v2` | TopicOrchestratorV2 → SynthesisEngine → NarrativeFormatterAgent | Markdown report, structured JSON, synthesis metadata, `.log`, optional Gamma deck | Default pipeline; accepts `--include-canny` to blend Snowflake-backed Canny posts |
| VoC – Synthesis Only | `voice-of-customer --analysis-type synthesis` | TopicOrchestratorV2 → SynthesisEngine → NarrativeFormatterAgent | Markdown report + structured JSON focused on cross-cutting insights | Uses same formatting stack as Narrative V2 but omits topic cards |
| VoC – Complete | `voice-of-customer --analysis-type complete` | TopicOrchestrator (cards) + TopicOrchestratorV2 (synthesis) → NarrativeFormatterAgent | Combined markdown, structured data, synthesis dump, `.log`, optional Gamma | Best for weekly exec packets; `--digest-mode` trims to quick exec read |
| Category Deep Dives (Billing/Product/API/Sites) | `analyze-billing` / `analyze-product` / `analyze-api` / `analyze-sites` | ChunkedFetcher + CategoryFilters → TopicOrchestrator → NarrativeFormatterAgent | Markdown + structured JSON + `.log` | Mirror Narrative V2 focusing only on selected taxonomy |
| Technical Troubleshooting | `tech-analysis [--filter-category Bug|API|…]` | ChunkedFetcher + CategoryFilters (+ optional Canny Snowflake feed) → TopicOrchestrator → NarrativeFormatterAgent | Markdown narrative + structured JSON + `.log` | Replaces the old ELT-only tooling; honors taxonomy filter and Snowflake Canny ingestion |
| Agent Performance | `agent-performance --agent <vendor>` (+ `--analyze-troubleshooting`) | ChunkedFetcher + AgentPerformanceAgent (+ optional troubleshooting agent) | Markdown/JSON exports + `.log` | Taxonomy filter maps to `--focus-categories`; troubleshooting walks diagnostic loops |
| Agent Coaching | `agent-coaching-report --vendor <vendor>` | ChunkedFetcher + AgentCoaching engine | Coaching markdown + `.log` (+ optional Gamma) | Emphasizes priorities and development plans |
| Canny Feedback (standalone) | `canny-analysis` | CannyClient → CannyAnalyzer → (optional) GammaGenerator | JSON analysis + `.log`, optional Gamma metadata/URL | Uses output manager and saves complete log even for API-only runs |

## Canny + Snowflake integration

- `CannyWarehouseService` (Snowflake connector) normalizes warehouse rows into
  Intercom-shaped “conversations”.  
- `--include-canny` on `voice-of-customer` and the modernized `tech-analysis`
  command now blend those conversations directly into the TopicOrchestrator
  pipeline, so NarrativeFormatterAgent can cite both Intercom and Canny data.
- If Snowflake credentials are missing, the helper logs a dim informational
  message and the run proceeds with Intercom-only data—no retries needed.

## Logging & Resilience

- All multi-agent modes (including Canny-only, category deep dives, technical
  troubleshooting, and VoC variants) enable `console.record` and emit a
  `.log` file next to the main artifact.  
- SSE/Web runs therefore survive disconnects, and CLI runs always have a
  download-friendly transcript for audits or debugging.

## Taxonomy Reference

These are the canonical `--filter-category` / `--focus-categories` values. The
web UI uses the same labels, and `intercom_analysis.py show-categories` will
print the same table.

| Value | Description |
| --- | --- |
| Billing | Refunds, invoices, subscriptions, payment methods |
| Bug | Product defects, broken features, crashes, errors |
| API | API/endpoint failures, auth, rate limits, SDK issues |
| Product Question | How-to questions, feature discovery, education |
| Account | Login, profile, permissions, domain/workspace setup |
| Feedback | Feature requests, improvements, general feedback |
| Agent/Buddy | Fin / bot interactions, training, escalation loops |
| Workspace | Workspace configuration, team management, roles |
| Privacy | GDPR/CCPA, data deletion, consent, legal |
| Chargeback | Charge disputes, fraud investigations |
| Partnerships | Partnership / business development inquiries |
| Promotions | Promo codes, discounts, marketing campaigns |
| Abuse | Spam, harassment, DMCA, malicious content |
| Unknown | Catch-all / unclassified tickets (triage queue) |

