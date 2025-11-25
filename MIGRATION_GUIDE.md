# Migration Guide

Structured instructions for extending the Intercom Analysis Tool without reintroducing the failure
patterns that motivated the CLI/web refactor. Pair this document with:

- `SYSTEM_ARCHITECTURE_GUIDE.md` for the big-picture view
- `CLI_WEB_ALIGNMENT_CHECKLIST.md` for the 3-layer contract details
- `docs/CLI_COMMAND_INVENTORY.md` for the current command catalog
- `.cursorrules` for the enforcement rules baked into automation

---

## 1. Adding or Updating CLI Commands

1. **Implement the business logic in `src/cli/<domain>_commands.py`.**
   - Functions should be `async` and never perform Click I/O directly.
   - Input parameters must have defaults that keep backward compatibility.
2. **Expose the command in `src/main.py`.**
   - Add/modify the `@click.command` decorator.
   - Every option must be mirrored in the function signature and actually used.
3. **Extend `src/cli/schema.py`.**
   - Update `CANONICAL_COMMAND_MAPPINGS` with the new flag metadata.
   - Run `python scripts/check_cli_web_alignment.py` to confirm schema parity.
4. **Update the front-end contract.**
   - Add UI controls in `deploy/web/templates` (form HTML) and wire them in `static/app.js`.
   - Remember that `WebCommandExecutor` derives its whitelist from the schema automatically.
5. **Document the change.**
   - Update the relevant entry in `docs/CLI_COMMAND_INVENTORY.md`.
   - Capture behavioural notes in `README.md` or a focused guide if needed.

✅ **Tests to add/update**
- Command-level unit tests (e.g., `tests/test_voc_commands.py` or new `tests/test_<command>_commands.py`)
- Alignment script (`scripts/check_cli_web_alignment.py`) must stay green.

---

## 2. Adding a New Orchestration Strategy

1. **Create the strategy under `src/services/strategies/`.**
   - Inherit from `OrchestrationStrategy`.
   - Return an `AgentResult` with confidence metadata and structured `data`.
   - Reuse `BaseOrchestrator` utilities for timeouts, checkpoints, and aggregation.
2. **Register usage.**
   - Prefer direct instantiation via `UnifiedOrchestrator` rather than legacy wrappers.
   - Update callers (CLI commands, services, or automation) to pass an `AgentContext`.
3. **Expose configuration flags (if needed).**
   - Follow the CLI contract process outlined above.
4. **Write targeted tests.**
   - Add unit tests to `tests/test_orchestration_strategies.py` to cover success and failure shapes.
   - If the strategy introduces new services, add dedicated unit tests for them as well.

---

## 3. Adding FastAPI Routes or Web Features

1. **Decide the router module.**
   - `deploy/web/routes_execution.py` for SSE/background jobs.
   - `deploy/web/routes_timeline.py` for historical data.
   - `deploy/web/routes_chat.py` for schema/chat metadata.
   - `deploy/web/routes_files.py` for file handling.
2. **Use the app factory.**
   - Register new routers in `deploy/web/app_factory.py::_include_routers`.
   - Keep initialization logic inside the factory to reuse Railway + local setups.
3. **Mock dependencies for tests.**
   - Extend the shared fixtures in `tests/conftest.py` if new services are introduced.
4. **Add route tests.**
   - Execution flows → `tests/test_routes_execution.py`
   - Timeline APIs → `tests/test_routes_timeline.py`
   - Chat/schema endpoints → `tests/test_routes_chat.py`
   - File browsing/downloading → `tests/test_routes_files.py`

---

## 4. Common Patterns & Gotchas

- **AgentContext In → AgentResult Out**: All agents and strategies must respect the typed contract defined in `src/agents/base_agent.py`.
- **Async-Only**: Never block the event loop. Use `await` everywhere and `asyncio.to_thread` for unavoidable sync calls.
- **Safe Nested Access**: Intercom payloads are inconsistent. Always guard `.get()` chains or normalize in `intercom_sdk_service`.
- **One LLM mechanism at a time**: Follow `DEVELOPMENT_STANDARDS.md` when tuning timeouts, chunking, or retries.
- **Logs-first debugging**: Persist console output via `output_manager` (see `.cursorrules` for the resiliency requirement).

---

## 5. Testing Requirements

| Change Type | Required Tests |
|-------------|----------------|
| CLI command/flag | Command unit tests + alignment script |
| Orchestration strategy | `tests/test_orchestration_strategies.py` + integration path exercising `UnifiedOrchestrator` |
| Web route | Appropriate `tests/test_routes_*.py` module |
| File/system utilities | Add/extend a focused `tests/test_<domain>.py` |

Additionally:
- Run `./scripts/run_all_checks.sh` before every commit (per `.cursorrules`).
- Capture real-data validation with `python src/main.py sample-mode --count 50 --save-to-file` for any LLM-touching change.

---

## 6. Pre-Commit Checklist (Abbreviated)

1. **Audit the change** (Steps 1–6 in `.cursorrules`)
2. **Run `./scripts/run_all_checks.sh`**
3. **Stage & commit** only after the above succeed
4. **Push** after verifying the commit hook output

Use this document as the tactical playbook while the architecture guide provides the strategic map. Keep both updated whenever a migration task is completed so new contributors can follow the same path.

