# Developer Onboarding

Welcome to the Intercom Analysis Tool. This handbook compresses the must-know context from the
broader documentation set so you can ship safely during your first week.

Pair this with:
- `SYSTEM_ARCHITECTURE_GUIDE.md` – deep dive into the data/agent orchestration pipeline
- `MIGRATION_GUIDE.md` – tactical steps for adding commands, strategies, or web routes
- `CLI_WEB_ALIGNMENT_CHECKLIST.md` – enforced 3-layer contract for CLI ↔ Schema ↔ Frontend
- `.cursorrules` – governance rules executed by automation and reviewers

---

## 1. System Overview

The platform ingests Intercom conversations, runs multi-agent analyses, and surfaces insights via CLI
commands and a unified FastAPI UI. Core layers:

1. **ETL & Normalization** (`src/services`)
2. **Agents** (`src/agents`) producing `AgentResult` objects
3. **Strategies** (`src/services/strategies`) orchestrated by `UnifiedOrchestrator`
4. **CLI Contract** (`src/main.py`, `src/cli/*`, `src/cli/schema.py`)
5. **Web Interface** (`deploy/web/*`, `static/app.js`)

---

## 2. Quick Start

1. **Clone & install**
   ```bash
   git clone <repo>
   cd Intercom Analysis Tool
   pip install -r requirements.txt
   ```
2. **Configure environment**
   - Copy `.env.example` → `.env`
   - Set `INTERCOM_ACCESS_TOKEN`, `OPENAI_API_KEY`, `GAMMA_API_KEY` (optional)
3. **Bootstrap outputs**
   ```bash
   mkdir -p outputs
   ```
4. **Run smoke tests**
   ```bash
   python -m pytest tests/test_system_commands.py -k sanity
   python src/main.py sample-mode --count 50 --save-to-file
   ```
5. **Launch the web UI (optional)**
   ```bash
   uvicorn deploy.web.app_factory:create_app --factory --reload
   ```

---

## 3. Key Concepts

- **AgentContext**: Pydantic model that carries analysis metadata, conversation batches, and prior results between agents.
- **AgentResult**: Typed output with `success`, `confidence`, `confidence_level`, and structured `data`.
- **UnifiedOrchestrator**: Delegates to pluggable strategies (`ComprehensiveStrategy`, `MultiAgentStrategy`, `StoryDrivenStrategy`) and enforces checkpoint/timeout logic from `BaseOrchestrator`.
- **3-Layer CLI Contract**:
  1. `src/main.py` – Click definitions and true business logic
  2. `src/cli/schema.py` – `CANONICAL_COMMAND_MAPPINGS` that auto-generate executor validation
  3. `static/app.js` – UI argument builder that must mirror the schema

---

## 4. Development Workflow

1. **Design**: Capture the change in the relevant guide (`MIGRATION_GUIDE.md` for structural work).
2. **Implement**: Favor async functions, safe dict access, and reuse of shared utilities.
3. **Self-audit (per `.cursorrules`)**
   - Read back the edits (`read_file`)
   - `read_lints ["<file>"]`
   - `python3 -m py_compile <file>` for every modified Python file
   - Verify imports exist and callers are updated
   - Re-read surrounding context to ensure logical integration
4. **Validate**
   ```bash
   ./scripts/run_all_checks.sh
   ```
5. **Smoke with real data for LLM changes**
   ```bash
   python src/main.py sample-mode --count 50 --save-to-file
   ```
6. **Commit & push** once the above pass.

---

## 5. Common Tasks (and where to look)

| Task | Reference |
|------|-----------|
| Add/modify CLI command | `MIGRATION_GUIDE.md` §1 |
| Implement new orchestration strategy | `MIGRATION_GUIDE.md` §2 + `tests/test_orchestration_strategies.py` |
| Add FastAPI route | `MIGRATION_GUIDE.md` §3 + `tests/test_routes_*.py` |
| Update docs | `README.md`, `SYSTEM_ARCHITECTURE_GUIDE.md`, `docs/CLI_COMMAND_INVENTORY.md` |

---

## 6. Testing Strategy

1. **Unit tests** (`tests/test_*`). Targeted coverage for CLI helpers, strategies, and services.
2. **Web route tests** (new suites under `tests/test_routes_*.py`) ensure FastAPI endpoints remain stable.
3. **Integration / sample-mode**: `python src/main.py sample-mode --count 50 --save-to-file`.
4. **Automated checks**: `./scripts/run_all_checks.sh` (alignment, async safety, schema validation, etc.).

_Coverage Targets_: Critical modules (CLI commands, orchestration strategies, web routes) must have at
least one direct unit test plus representation in the alignment/validation scripts.

---

## 7. Common Pitfalls

- **Skipping `py_compile`**: Async errors (e.g., `await` in non-async functions) slip past linting.
- **Unsafely accessing Intercom fields**: Always use `.get()` or normalize at the service boundary.
- **Forgetting the schema layer**: Adding a CLI flag without updating `src/cli/schema.py` or `static/app.js` triggers validation failures.
- **Blocking the event loop**: Never call synchronous networking or file APIs from async code without using `asyncio.to_thread`.
- **Neglecting log export**: Long-running analyses must write complete logs to disk (see `.cursorrules` section “Output File Resilience”).

---

## 8. Additional Resources

- `SYSTEM_ARCHITECTURE_GUIDE.md` – deeper architecture phases and diagrams
- `MIGRATION_GUIDE.md` – playbook for structured changes
- `CLI_WEB_ALIGNMENT_CHECKLIST.md` – reference & testing notes (Phase 5 updates)
- `docs/CLI_COMMAND_INVENTORY.md` – canonical list of supported commands/flags
- `DEVELOPMENT_STANDARDS.md` – broader engineering principles (LLM controls, logging, etc.)

Welcome aboard! Treat this guide as your day-zero compass and keep it updated whenever onboarding questions surface.

