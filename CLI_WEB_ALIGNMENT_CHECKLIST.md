# CLI ↔ Web UI ↔ Railway Alignment Checklist

## The Fundamental Problem

**Every command has 3 implementations that MUST match:**

1. **CLI** (`src/main.py`) - The actual command logic
2. **Schema** (`src/cli/schema.py`) - CANONICAL_COMMAND_MAPPINGS (source of truth)
3. **Frontend** (`static/app.js`) - What the UI sends

**Previously (4-layer contract):**
- WebCommandExecutor (`src/services/web_command_executor.py`) had a separate hardcoded whitelist
- This "hidden Layer 3" was frequently forgotten, causing validation errors

**Now (3-layer contract):**
- WebCommandExecutor schema is **AUTO-GENERATED** from CANONICAL_COMMAND_MAPPINGS
- No manual maintenance required for executor whitelist
- If these don't align → Validation errors, ignored flags, broken features

---

## MANDATORY CHECKLIST - Use This EVERY TIME

### When Adding a New Flag to ANY Command

**Step 1: CLI (`src/main.py`)**
```python
@cli.command(name='your-command')
@click.option('--your-flag', type=click.Choice(['val1', 'val2']), default='val1',
              help='Your flag description')
def your_command(..., your_flag: str):  # ← Add to function signature!
    # Actually use the flag in the implementation
    if your_flag == 'val1':
        do_something()
```

✅ **Verification:**
- [ ] Flag is in `@click.option`
- [ ] Flag is in function signature
- [ ] Flag is actually USED in the function body (not just accepted)

---

**Step 2: Schema (`src/cli/schema.py`)**

Find the command in `CANONICAL_COMMAND_MAPPINGS`:
```python
'your_command': {
    'command': 'python',
    'args': ['src/main.py', 'your-command'],
    'allowed_flags': {
        '--your-flag': {
            'type': 'enum',  # or 'boolean', 'integer', 'date', 'string'
            'values': ['val1', 'val2'],  # for enum
            'default': 'val1',
            'description': 'Your flag description'
        }
    }
}
```

✅ **Verification:**
- [ ] Flag is in `allowed_flags`
- [ ] Type matches CLI type (enum = Choice, boolean = is_flag, etc.)
- [ ] Values match CLI choices EXACTLY
- [ ] Default matches CLI default
- [ ] ✅ WebCommandExecutor schema auto-generated (no manual step needed!)

---

**Step 3: Frontend (`static/app.js`)**

In `runAnalysis()` function:
```javascript
if (analysisType === 'your-command') {
    args.push('your-command');
    
    // Get value from UI
    const yourFlagValue = document.getElementById('yourFlagDropdown')?.value;
    if (yourFlagValue) {
        args.push('--your-flag', yourFlagValue);
    }
}
```

✅ **Verification:**
- [ ] UI element exists in HTML (deploy/railway_web.py template)
- [ ] Value is read from correct element ID
- [ ] Flag is added to args array
- [ ] Conditional logic matches when flag should be sent

---

## Common Mismatches (Check These!)

### ❌ **Mismatch Type 1: Flag in Railway but NOT in CLI**
```python
# Railway: allowed_flags has '--test-llm'
# CLI: No @click.option('--test-llm')
# Result: Railway validates ✅, CLI rejects ❌
```

### ❌ **Mismatch Type 2: Flag in CLI but NOT in Railway**
```python
# CLI: @click.option('--ai-model')
# Railway: No '--ai-model' in allowed_flags
# Result: Railway rejects ❌, CLI never sees it
```

### ❌ **Mismatch Type 3: Different Types**
```python
# Railway: 'type': 'boolean'
# CLI: type=click.Choice(['true', 'false'])  # Should be is_flag=True
# Result: Type validation fails
```

### ❌ **Mismatch Type 4: Different Values**
```python
# Railway: 'values': ['quick', 'standard']
# CLI: type=click.Choice(['fast', 'full'])  # Different names!
# Result: Validation fails
```

### ❌ **Mismatch Type 5: Frontend Sends Wrong Flags**
```python
# Frontend adds --verbose to ALL commands
# But sample-mode doesn't have --verbose in CLI
# Result: Validation error
```

---

## The 3-Layer Contract

```
┌─────────────────────────────────────────────┐
│ LAYER 1: CLI (src/main.py)                 │
│ - Defines what flags exist                 │
│ - Defines flag types and defaults          │
│ - ACTUALLY USES the flag values            │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│ LAYER 2: Schema (src/cli/schema.py)        │
│ - CANONICAL_COMMAND_MAPPINGS               │
│ - Source of truth for all flags            │
│ - AUTO-GENERATES WebCommandExecutor schema │
│ - MUST mirror CLI exactly                  │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│ LAYER 3: Frontend (static/app.js)          │
│ - Builds args array from UI inputs         │
│ - Sends only flags that CLI accepts        │
│ - MUST know Schema's validation rules      │
└─────────────────────────────────────────────┘
```

**Rule:** CLI is the source of truth. Schema mirrors CLI. Frontend uses Schema.
**WebCommandExecutor:** Auto-generated from Schema (no manual maintenance).

> **Phase 5: Testing & Documentation Complete**  
> Alignment is now enforced by both automation (`scripts/check_cli_web_alignment.py`) and dedicated
> test suites covering CLI handlers (`tests/test_*_commands.py`), orchestration strategies
> (`tests/test_orchestration_strategies.py`, `tests/test_unified_orchestrator.py`), and FastAPI routes
> (`tests/test_routes_*.py`). Keep these suites updated whenever you add a new flag or command.

---

## Testing the Alignment

### Manual Test (Do this EVERY time)

1. **Check CLI accepts the flag:**
   ```bash
   python src/main.py your-command --help
   # Should list --your-flag
   ```

2. **Check Schema validates it:**
   ```python
   # In src/cli/schema.py
   CANONICAL_COMMAND_MAPPINGS['your_command']['allowed_flags']
   # Should have '--your-flag'
   ```

3. **Check Frontend sends it:**
   ```javascript
   // In static/app.js runAnalysis()
   console.log('Args:', args);
   // Should include '--your-flag' when appropriate
   ```

4. **Test in web UI:**
   - Select the analysis type
   - Set the flag value
   - Click Run
   - Should NOT get "flag not allowed" error

### Automated Test (Add to test_schema_cli_contract.py)

```python
def test_flag_alignment_your_command():
    """Test that your-command flags align across CLI, Railway, Frontend."""
    from src.main import cli
    from src.cli.schema import CANONICAL_COMMAND_MAPPINGS
    
    # Get CLI flags
    cli_command = cli.commands['your-command']
    cli_params = {p.name for p in cli_command.params}
    
    # Get Railway flags
    railway_flags = set(CANONICAL_COMMAND_MAPPINGS['your_command']['allowed_flags'].keys())
    railway_flags = {f.replace('--', '').replace('-', '_') for f in railway_flags}
    
    # They should match!
    assert cli_params == railway_flags, f"Mismatch: CLI={cli_params}, Railway={railway_flags}"
```

---

## Quick Reference Table

| Command | CLI File | Railway Key | Frontend Handler |
|---------|----------|-------------|------------------|
| `sample-mode` | Line 4205 | `sample_mode` | Line 288 |
| `voice-of-customer` | Line 4378 | `voice_of_customer` | Line 299 |
| `agent-performance` | Line 2695 | `agent_performance_*` | Line 308 |
| `canny-analysis` | Line 4074 | `canny_analysis` | Line 335 |
| `tech-analysis` | Line 484 | `tech_analysis` | Line 342 |

---

## When You Add/Change a Flag

**Use this checklist EVERY TIME:**

### ✅ Checklist

- [ ] **1. Added to CLI** (`src/main.py`)
  - [ ] `@click.option` decorator
  - [ ] Function signature parameter
  - [ ] Actually USED in function body

- [ ] **2. Added to Schema** (`src/cli/schema.py`)
  - [ ] In `CANONICAL_COMMAND_MAPPINGS[command]['allowed_flags']`
  - [ ] Type matches CLI (enum/boolean/integer/date)
  - [ ] Values match CLI choices
  - [ ] Default matches CLI default
  - [ ] ✅ WebCommandExecutor schema auto-generated (no manual step)

- [ ] **3. Added to Frontend** (`static/app.js`)
  - [ ] HTML element exists (if needed)
  - [ ] Value read from element
  - [ ] Added to args array
  - [ ] Only added when appropriate (check conditionals)

- [ ] **4. Tested**
  - [ ] CLI help shows flag: `python src/main.py command --help`
  - [ ] Web UI doesn't error on submit
  - [ ] Flag value is actually used (check logs)
  - [ ] Run `./scripts/check_cli_web_alignment.py` (verifies auto-generation)

---

## Auto-Generation Details (Phase 3 Complete)

**What Changed:**
- WebCommandExecutor schema is now auto-generated from `CANONICAL_COMMAND_MAPPINGS`
- Function: `src/cli/schema.py::generate_executor_schema()`
- Called at module load time in `src/services/web_command_executor.py`

**Benefits:**
- ✅ Eliminates manual maintenance of executor whitelist
- ✅ Reduces 4-layer contract to 3 layers
- ✅ Prevents "forgot to update executor" errors
- ✅ Single source of truth (CANONICAL_COMMAND_MAPPINGS)

**Verification:**
- Run `./scripts/check_cli_web_alignment.py` to verify auto-generation works
- Script checks that generated schema has all expected flags
- No manual WebCommandExecutor updates needed

---

## Common Commands and Their Flag Patterns

### Sample Mode / Schema Dump (Diagnostic Tools)
**Valid Flags:**
- `--count`, `--time-period`, `--start-date`, `--end-date`
- `--save-to-file`, `--test-llm`, `--schema-mode`
- `--ai-model` (for LLM test), `--verbose`

**Invalid Flags:**
- ❌ `--output-format` (diagnostics → terminal)
- ❌ `--generate-gamma` (diagnostics → terminal)
- ❌ `--test-mode` (diagnostics ARE the test)
- ❌ `--audit-trail` (diagnostics have own logging)

### Voice of Customer (Production Analysis)
**Valid Flags:**
- `--time-period`, `--periods-back`, `--start-date`, `--end-date`
- `--ai-model`, `--multi-agent`, `--analysis-type`
- `--generate-gamma`, `--test-mode`, `--audit-trail`
- `--include-canny`, `--verbose`

**Invalid Flags:**
- ❌ `--count` (fetches all in date range)
- ❌ `--schema-mode` (not a diagnostic)

### Agent Performance
**Valid Flags:**
- `--time-period`, `--agent`, `--individual-breakdown`
- `--ai-model`, `--output-format`, `--test-mode`

---

## The "Schema Dump Mistake" Pattern

**What Happened:**
1. Added `--test-llm` and `--schema-mode` to Railway ✅
2. Added to Frontend ✅
3. **Forgot to add to CLI** ❌
4. Result: Validation error

**Prevention:**
Always follow the checklist in ORDER:
1. CLI first (source of truth)
2. Schema second (mirrors CLI, auto-generates executor)
3. Frontend last (uses Schema's validation)

---

## Verification Script

Run this to verify all layers are aligned:

```bash
./scripts/check_cli_web_alignment.py
```

The script verifies:
1. CLI ↔ Schema alignment (flags match)
2. WebCommandExecutor auto-generation (schema generated correctly)
3. Frontend consistency (no obvious flag issues)

## Testing

Automated verification is backed by targeted pytest suites:

| Scope | Tests |
|-------|-------|
| CLI command handlers | `tests/test_voc_commands.py`, `tests/test_system_commands.py`, `tests/test_export_commands.py`, etc. |
| Orchestrators & strategies | `tests/test_unified_orchestrator.py`, `tests/test_orchestration_strategies.py` |
| FastAPI routes | `tests/test_routes_execution.py`, `tests/test_routes_timeline.py`, `tests/test_routes_chat.py`, `tests/test_routes_files.py` |

**Coverage expectations**
- Every user-facing command must have at least one unit test covering the handler path.
- New orchestration strategies require success + failure cases in `tests/test_orchestration_strategies.py`.
- Any new route must be represented in the appropriate `tests/test_routes_*.py` file.

**Sample commands to run**
```bash
python -m pytest tests/test_voc_commands.py
python -m pytest tests/test_routes_execution.py
```

---

## Summary

**The 3-Layer Alignment Rule:**

> When you add/change ANY flag, update the layers in this order:
> 1. CLI (source of truth)
> 2. Schema (mirrors CLI, auto-generates executor)
> 3. Frontend (sender layer)
>
> Automation + tests enforce the rule: the alignment script validates metadata while the pytest
> suites ensure behaviour across commands, orchestrators, and web routes.

**Add this to your .cursorrules or agent instructions!**
