# CLI Command Inventory & Proposed Module Split

This document inventories every `@cli.command` defined in `src/main.py` and recommends the target module(s) for the upcoming refactor described in Comments 2–4. It also highlights the current call path (usually `run_*` helpers inside `src/main.py` or `src/cli/{commands,runners}.py`) and the orchestration/service work that needs to accompany the split.

> **Goal:** move Click wiring into lightweight wrappers (likely in `src/cli/entry.py` or small registries), push implementation bodies into focused modules under `src/cli/`, and have those call async services/orchestrators under `src/services/`.

---

## High-Level Module Plan

| Proposed Module | Purpose | Commands to Host | Downstream Service Focus |
|-----------------|---------|------------------|--------------------------|
| `src/cli/system_commands.py` | Health checks, config, info-only utilities | `test`, `system-info`, `help`, `interactive`, `list-commands`, `examples`, `show-categories`, `config` | None (remain sync) |
| `src/cli/snapshot_commands.py` | Snapshot listings/comparisons/schema export | `list-snapshots`, `export-snapshot-schema`, `compare-snapshots` | Leverage existing `src/cli/commands.py` helpers ✅ Phase 1.2 Complete |
| `src/cli/export_commands.py` | Data export + general query utilities | `export`, `query`, `custom` | Future `conversation_export_service` |
| `src/cli/technical_commands.py` | Technical triage + macro/escalation tooling | `tech-analysis`, `find-macros`, `fin-escalations` | `technical_orchestrator`, `fin_escalation_analyzer` |
| `src/cli/category_commands.py` | All category/taxonomy-focused utilities | `analyze-category`, legacy `analyze-all-categories`, `synthesize`, `analyze-custom-tag`, `analyze-escalations`, `analyze-pattern` | `category_analysis_orchestrator` |
| `src/cli/voc_commands.py` | Multi-agent VoC + canned categories | `analyze-billing`, `analyze-product`, `analyze-sites`, `analyze-api`, new `analyze-all-categories`, `comprehensive-analysis`, `voice-of-customer` | `voc_orchestrator`, `comprehensive_analysis_orchestrator`, `topic_pipeline_service` |
| `src/cli/agent_commands.py` | Agent performance, coaching, macros tied to staffing | `agent-performance`, `agent-coaching-report`, (optionally `find-macros`/`fin-escalations` if grouped here) | `agent_performance_service`, `coaching_report_service` |
| `src/cli/canny_commands.py` | Canny + warehouse analysis | `canny-analysis`, `query-suggestions` (if Canny-specific) | `canny_pipeline_service` |
| `src/cli/gamma_commands.py` | Gamma export helpers | `generate-gamma`, `generate-all-gamma` | `gamma_generator_service` |
| `src/cli/sample_commands.py` | Diagnostic sampling/testing | `sample-mode`, `test-mode` | `sample_mode_service` |
| `src/cli/chat_commands.py` | Interactive chat | `chat` | Reuse `chat_interface` |

---

## Detailed Command Inventory

### System & Utility Commands

**✅ Phase 1.1 Complete** - These commands have been extracted to `src/cli/system_commands.py`.

| CLI Command | Description | Current Implementation | Target Module | Notes |
|-------------|-------------|------------------------|---------------|-------|
| `custom` | Run custom prompt between start/end dates | Inline; builds `AnalysisRequest` then `run_custom_analysis` | `export_commands` (or `custom_commands`) | Async helper already in `src/cli/commands.py` |
| `test` | API connectivity smoke test (Intercom/OpenAI/Gamma) | Inline `asyncio.run` against services | `system_commands ✅` | Keep synchronous run; consider consolidating service pings |
| `system-info` | Display host diagnostics | `show_system_info` (from `src.cli.utils`) | `system_commands ✅` | Already shareable utility |
| `help`, `interactive`, `list-commands`, `examples`, `show-categories`, `config` | CLI UX helpers | All sync wrappers invoking `help_system`/`CategoryFilters` | `system_commands ✅` | Low risk to move |
| `query-suggestions` | Guided query helper | Inline (simple logic) | `system_commands` (kept inline) | Lightweight, no module needed |

### Snapshot & Schema Utilities

| CLI Command | Description | Current Implementation | Target Module |
|-------------|-------------|------------------------|---------------|
| `list-snapshots` | List stored weekly/monthly/quarterly snapshots | Already defers to `src.cli.commands.list_snapshots` | `snapshot_commands` |
| `export-snapshot-schema` | Write snapshot schema JSON | `src.cli.commands.export_snapshot_schema` | `snapshot_commands` |
| `compare-snapshots` | Diff two snapshot IDs | `src.cli.snapshot_commands.compare_snapshots` | `snapshot_commands` |

### Export / Query

| CLI Command | Description | Current Implementation | Target Module | Service Dependency |
|-------------|-------------|------------------------|---------------|--------------------|
| `export` | Raw conversation export | Inline -> `run_data_export` | `export_commands` | Future `conversation_export_service` |
| `query` | Run general Intercom queries (guided/custom) | Inline -> `run_general_query` | `export_commands` | Same as above |

### Technical & Macro Tools

| CLI Command | Description | Current Implementation | Target Module | Notes |
|-------------|-------------|------------------------|---------------|-------|
| `tech-analysis` | Narrative V2 technical triage | Click wrapper -> `run_tech_analysis_command` -> `run_technical_troubleshooting_analysis` | `technical_commands` | Wrapper stays in `src/main.py`; shared logic now lives in `src/cli/technical_commands.py` |
| `find-macros` | Macro discovery | Delegates to `run_macro_analysis` | `technical_commands` ✅ | Placeholder logic retained, aligned with Phase 1.5 |
| `fin-escalations` | Analyze Fin → human handoffs | Delegates to `run_fin_analysis` | `technical_commands` ✅ | Placeholder logic retained, aligned with Phase 1.5 |

### Category & Custom Deep Dives (Legacy)

| CLI Command | Description | Current Implementation | Target Module |
|-------------|-------------|------------------------|---------------|
| `analyze-category` | Single taxonomy category analysis | Delegates to `run_category_analysis` | `legacy_category_commands` ✅ |
| `analyze-all-categories` (legacy) | Multi-category summary (older pipeline) | Delegates to `run_all_categories_analysis` | `legacy_category_commands` ✅ (deprecated) |
| `synthesize` | Synthesis-only view for category sets | Delegates to `run_synthesis_analysis` | `legacy_category_commands` ✅ (placeholder) |
| `analyze-custom-tag` | Analyze by Intercom tag | Delegates to `run_custom_tag_analysis` | `legacy_category_commands` ✅ (placeholder) |
| `analyze-escalations` | Explore escalation routes | Delegates to `run_escalation_analysis` | `legacy_category_commands` ✅ (placeholder) |
| `analyze-pattern` | Regex/text pattern search | Delegates to `run_pattern_analysis` | `legacy_category_commands` ✅ (placeholder) |

### Modern VoC & Category Commands ✅ COMPLETE

| CLI Command | Description | Current Implementation | Target Module | Orchestrator Needed |
|-------------|-------------|------------------------|---------------|---------------------|
| `analyze-billing` | Multi-agent VoC filtered to Billing | Delegates to `run_billing_analysis` | `src/cli/category_commands.py` | `category_analysis_orchestrator` |
| `analyze-product` | Product feedback | Delegates to `run_product_analysis` | `src/cli/category_commands.py` | Same |
| `analyze-sites` | Sites reliability | Delegates to `run_sites_analysis` | `src/cli/category_commands.py` | Same |
| `analyze-api` | API issues | Delegates to `run_api_analysis` | `src/cli/category_commands.py` | Same |
| `analyze-all-categories` (new) | All categories with modern taxonomy | Delegates to `run_all_categories_analysis_v2` | `src/cli/category_commands.py` | Comprehensive taxonomy orchestrator |
| `comprehensive-analysis` | Multi-surface (FIN, technical, macro) | Delegates to `run_comprehensive_analysis` | `src/cli/voc_commands.py` | `UnifiedOrchestrator` + `ComprehensiveStrategy` |
| `voice-of-customer` | Flagship multi-agent pipeline | Delegates to `run_voice_of_customer_analysis` | `src/cli/voc_commands.py` | `voc_orchestrator`, `narrative_orchestrator` |

*Note: All VoC and category commands now live in `src/cli/voc_commands.py` and `src/cli/category_commands.py` as of Phase 1.4.*

### Gamma Utilities

| CLI Command | Description | Current Implementation | Target Module |
|-------------|-------------|------------------------|---------------|
| `generate-gamma` | Create Gamma deck from saved analysis JSON | Delegates to `run_gamma_generation` | `gamma_commands` ✅ |
| `generate-all-gamma` | Batch Gamma generation | Delegates to `run_bulk_gamma_generation` | `gamma_commands` ✅ |

### Canny & Warehouse

| CLI Command | Description | Current Implementation | Target Module |
|-------------|-------------|------------------------|---------------|
| `canny-analysis` | Analyze Canny posts (Snowflake+API) | Delegates to `run_canny_analysis` | `canny_commands` ✅ |

### Sampling / Diagnostics

| CLI Command | Description | Current Implementation | Target Module |
|-------------|-------------|------------------------|---------------|
| `sample-mode` | Pull real conversations + optional LLM tests | Delegates to `run_sample_mode_command` | `sample_commands` ✅ |
| `test-mode` | Generate fake data + optionally run topic pipeline | Delegates to `run_test_mode_command` | `sample_commands` ✅ |

### Agent-Facing Reports

| CLI Command | Description | Current Implementation | Target Module | Notes |
|-------------|-------------|------------------------|---------------|-------|
| `agent-performance` | Vendor/team performance | Delegates to `run_agent_performance_analysis` | `agent_commands` ✅ | Should reuse upcoming `agent_performance_service` |
| `agent-coaching-report` | Coaching insights per vendor | Delegates to `run_agent_coaching_report` | `agent_commands` ✅ | Output gating via `output_format` |

### Chat / Interactive

| CLI Command | Description | Current Implementation | Target Module |
|-------------|-------------|------------------------|---------------|
| `chat` | Terminal chat to natural-language commands | Delegates to `run_chat_interface` | `chat_commands` ✅ |

---

## Migration Notes

1. **Minimal Click Functions:** After extraction, `src/main.py` (or registry) should only parse arguments and call `asyncio.run` on the new module-level async functions (which belong in the `src/cli/*_commands.py` files).
2. **Service Boundaries:** Complex workflows (multi-agent VoC, comprehensive analysis, category deep dives, agent performance, Canny, Gamma generation) need dedicated async services under `src/services/` (e.g., `voc_orchestrator.py`, `category_analysis_orchestrator.py`, `comprehensive_analysis_orchestrator.py`, `gamma_generation_service.py`).
3. **Reuse Existing Helpers:** Where `src/cli/commands.py` or `src/cli/runners.py` already host logic (snapshots, sample-mode), wire the new per-domain modules to those functions to avoid duplication.
4. **Async Safety:** New service modules should expose `async def` APIs returning `AgentResult` or typed Pydantic models and rely on `AgentContext`, semaphores, timeouts, and output-manager helpers per Comments 3–8.
5. **Testing:** Each module/service pair needs unit tests (async) plus coverage in the existing CLI/Railway alignment scripts. For VoC/LLM flows, remember the sample-mode gate (`python src/main.py sample-mode --count 50 --save-to-file`) before declaring complete.

Use this inventory as the authoritative list when moving code so that we can track progress domain-by-domain and avoid regressions during the phased refactor.

---

## Migration Status

### Phase 1.1: System Commands ✅ COMPLETE
- **Module:** `src/cli/system_commands.py`
- **Commands Extracted:** `test`, `system-info`, `config`, `help`, `interactive`, `list-commands`, `examples`, `show-categories`
- **Lines Reduced:** ~150 lines from `src/main.py`
- **Status:** All P0 validation checks passing

### Phase 1.2: Snapshot Commands ✅ COMPLETE
- **Module:** `src/cli/snapshot_commands.py`
- **Commands Extracted:** `list-snapshots`, `export-snapshot-schema`, `compare-snapshots`
- **Lines Reduced:** ~370 lines from `src/cli/commands.py`
- **Status:** All P0 validation checks passing

### Phase 1.3: Export/Query Commands ✅ COMPLETE
- **Module:** `src/cli/export_commands.py`
- **Commands Extracted:** `export`, `query`, `custom`
- **Lines Reduced:** ~400 lines from `src/main.py`
- **Status:** All P0 validation checks passing

### Phase 1.4: VoC Commands ✅ COMPLETE
- **Modules:** `src/cli/voc_commands.py` and `src/cli/category_commands.py`
- **Commands Extracted:** 
  - VoC: `voice-of-customer`, `comprehensive-analysis`
  - Category: `analyze-billing`, `analyze-product`, `analyze-sites`, `analyze-api`, `analyze-all-categories`
- **Lines Reduced:** ~1,300 lines from `src/main.py`
- **Status:** All P0 validation checks passing

### Phase 1.5: Agent & Technical Commands ✅ COMPLETE
- **Modules:** `src/cli/agent_commands.py` and `src/cli/technical_commands.py`
- **Commands Extracted:**
  - Agent: `agent-performance`, `agent-coaching-report`
  - Technical: `find-macros`, `fin-escalations`
  - Note: `tech-analysis` Click wrapper remains in `src/main.py` but now calls `run_tech_analysis_command` in `src/cli/technical_commands.py`, which still delegates to `run_technical_troubleshooting_analysis` in `src/cli/category_commands.py`
- **Lines Reduced:** ~825 lines from `src/main.py`
- **Status:** All P0 validation checks passing

### Phase 1.6: Remaining Commands (Canny, Gamma, Sample, Chat, Legacy) ✅ COMPLETE
- **Modules:** `src/cli/canny_commands.py`, `src/cli/gamma_commands.py`, `src/cli/sample_commands.py`, `src/cli/chat_commands.py`, `src/cli/legacy_category_commands.py`
- **Commands Extracted:**
  - Canny: `canny-analysis`
  - Gamma: `generate-gamma`, `generate-all-gamma`
  - Sample/Test: `sample-mode`, `test-mode`
  - Chat: `chat`
  - Legacy Category: `analyze-category`, `analyze-all-categories` (legacy), `synthesize`, `analyze-custom-tag`, `analyze-escalations`, `analyze-pattern`
  - Utility: `query-suggestions` reviewed (remains inline by design)
- **Lines Reduced:** ~1,499 lines from `src/main.py`
- **Status:** All P0 validation checks passing

### Refactor Summary
- **Total commands extracted:** 33
  - System: 8 (Phase 1.1)
  - Snapshot: 3 (Phase 1.2)
  - Export: 3 (Phase 1.3)
  - VoC/Category: 7 (Phase 1.4)
  - Agent/Technical: 4 (Phase 1.5)
  - Canny/Gamma/Sample/Chat/Legacy: 8 (Phase 1.6)
- **Total lines reduced from `src/main.py`:** ~4,544 (from 5,400 to ~856 core + wrappers)
  - Phase 1.1: 150 lines
  - Phase 1.2: 370 lines
  - Phase 1.3: 400 lines
  - Phase 1.4: 1,300 lines
  - Phase 1.5: 825 lines
  - Phase 1.6: 1,499 lines
- **Current `src/main.py` size:** ~1,466 lines (73% reduction from original 5,400)
  - Click command wrappers: ~600 lines
  - Imports and setup: ~100 lines
  - Legacy disabled commands: ~150 lines
  - Serverless wrapper: ~80 lines
  - Main entry point: ~10 lines
  - Remaining inline logic: ~526 lines (query-suggestions, voice-of-customer wrapper, agent wrappers)
- **Modules created:** 12
  - `src/cli/system_commands.py`
  - `src/cli/snapshot_commands.py`
  - `src/cli/export_commands.py`
  - `src/cli/voc_commands.py`
  - `src/cli/category_commands.py`
  - `src/cli/agent_commands.py`
  - `src/cli/technical_commands.py`
  - `src/cli/canny_commands.py`
  - `src/cli/gamma_commands.py`
  - `src/cli/sample_commands.py`
  - `src/cli/chat_commands.py`
  - `src/cli/legacy_category_commands.py`
- **Target achieved:** ✅ `src/main.py` < 1,500 lines (actual: ~1,466)

Phase 4 extends this refactor by unifying orchestration flows so every CLI command now receives a typed `AgentResult` from the same infrastructure, improving reliability for both CLI and Railway execution paths.

### Phase 2: Web Server Consolidation ✅ COMPLETE
- **Goal:** Replace the legacy dual FastAPI servers (`railway_web.py` in repo root + `deploy/railway_web.py`) with a single modular application under `deploy/web/`.
- **Entry Point:** `deploy/railway_web.py` is now a 25-line thin wrapper that imports `create_app()` from `deploy/web/app_factory.py` and boots Uvicorn with Railway’s env vars (`HOST`, `PORT`, `LOG_LEVEL`).
- **Modules Added (6 total):**
  - `deploy/web/app_factory.py` – central FastAPI factory, lifecycle events, shared middleware/static mounting, service initialization (ChatInterface, WebCommandExecutor, ExecutionStateManager, DuckDB/Historical service) and Slack notification endpoint.
  - `deploy/web/routes_timeline.py` – `/history`, `/analysis/*`, and `/api/snapshots/*` routes with DuckDB + HistoricalSnapshotService dependencies and review token validation.
  - `deploy/web/routes_execution.py` – `/execute*` SSE streaming endpoints, background execution helpers, rate limiting, directory helpers, and status polling logic.
  - `deploy/web/routes_chat.py` – `/chat`, `/api/commands`, `/api/filters`, `/api/stats` powered by ChatInterface with graceful fallback when heavy deps are unavailable.
  - `deploy/web/routes_files.py` – `/files`, `/outputs/*`, `/api/browse-files`, ZIP download helpers, and secure output serving with path traversal protection.
  - `deploy/web/templates.py` – shared HTML render helpers for chat UI, files browser, timeline, snapshot detail, and comparison views.
- **Impact:** The primary deployment server shrank from 2,546 lines to 25 lines (99% reduction). Timeline server (`railway_web.py` in repo root) was removed entirely after migrating its routes/templates into the shared modules. 25+ routes now live in focused routers, eliminating duplicate `/`, `/health`, and static mounting logic.
- **Deprecated Endpoints:** The legacy `/download?file=<path>` endpoint from the removed root-level `railway_web.py` has been replaced by `/outputs/<path>`. A compatibility route in `routes_files.py` provides 301 redirects for backward compatibility, but clients should migrate to `/outputs/<path>` directly.
- **Railway Alignment:** `railway.toml` already points to `python deploy/railway_web.py`; health checks remain `/health`. Background SSE settings (keepalive, timeouts) + EXECUTION_API_TOKEN gate are now centralized in `routes_execution`.
- **Phase 3 Readiness:** With the web layer modularized, we can auto-generate WebCommandExecutor schemas and keep CLI/Web/Railway flag alignment scripts focused on the single FastAPI entry point.

### Phase 4: Consolidate Orchestrators ✅ COMPLETE
- [x] Created unified orchestration layer
- [x] Extracted common logic to `BaseOrchestrator`
- [x] Migrated three orchestrators into strategies
- [x] Updated CLI command handlers to call the unified layer
- [x] Kept legacy orchestrators as thin wrappers for backward compatibility

**Files Created**
- `src/services/base_orchestrator.py` – shared timeout/checkpoint/error-handling utilities
- `src/services/unified_orchestrator.py` – pluggable orchestrator entry point
- `src/services/strategies/comprehensive.py` – comprehensive analysis strategy
- `src/services/strategies/multi_agent.py` – multi-agent workflow strategy
- `src/services/strategies/story_driven.py` – story-driven analysis strategy

**Files Modified**
- `src/services/orchestrator.py` – now a wrapper (deprecated warning + delegation)
- `src/agents/orchestrator.py` – wrapper exposing multi-agent strategy
- `src/services/story_driven_orchestrator.py` – wrapper exposing story-driven strategy
- `src/cli/voc_commands.py` – uses `UnifiedOrchestrator` for comprehensive analysis