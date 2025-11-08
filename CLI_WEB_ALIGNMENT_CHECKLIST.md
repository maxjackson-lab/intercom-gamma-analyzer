# CLI ↔ Web UI ↔ Railway Alignment Checklist

## The Fundamental Problem

**Every command has 3 implementations that MUST match:**

1. **CLI** (`src/main.py`) - The actual command logic
2. **Railway Validation** (`deploy/railway_web.py`) - What flags are allowed
3. **Frontend** (`static/app.js`) - What the UI sends

**If these don't align → Validation errors, ignored flags, broken features**

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

**Step 2: Railway Validation (`deploy/railway_web.py`)**

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
│ LAYER 2: Railway (deploy/railway_web.py)   │
│ - Validates flags match CLI                │
│ - Prevents invalid flags from reaching CLI │
│ - MUST mirror CLI exactly                  │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│ LAYER 3: Frontend (static/app.js)          │
│ - Builds args array from UI inputs         │
│ - Sends only flags that CLI accepts        │
│ - MUST know Railway's validation rules     │
└─────────────────────────────────────────────┘
```

**Rule:** CLI is the source of truth. Railway and Frontend must match it.

---

## Testing the Alignment

### Manual Test (Do this EVERY time)

1. **Check CLI accepts the flag:**
   ```bash
   python src/main.py your-command --help
   # Should list --your-flag
   ```

2. **Check Railway validates it:**
   ```python
   # In deploy/railway_web.py
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
    from deploy.railway_web import CANONICAL_COMMAND_MAPPINGS
    
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

- [ ] **2. Added to Railway** (`deploy/railway_web.py`)
  - [ ] In `CANONICAL_COMMAND_MAPPINGS[command]['allowed_flags']`
  - [ ] Type matches CLI (enum/boolean/integer/date)
  - [ ] Values match CLI choices
  - [ ] Default matches CLI default

- [ ] **3. Added to Frontend** (`static/app.js`)
  - [ ] HTML element exists (if needed)
  - [ ] Value read from element
  - [ ] Added to args array
  - [ ] Only added when appropriate (check conditionals)

- [ ] **4. Tested**
  - [ ] CLI help shows flag: `python src/main.py command --help`
  - [ ] Web UI doesn't error on submit
  - [ ] Flag value is actually used (check logs)

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
2. Railway second (mirrors CLI)
3. Frontend last (uses Railway's validation)

---

## Verification Script

Add this to pre-commit or CI:

```python
#!/usr/bin/env python3
"""Verify CLI ↔ Railway ↔ Frontend alignment."""

def check_alignment():
    from src.main import cli
    from deploy.railway_web import CANONICAL_COMMAND_MAPPINGS
    
    errors = []
    
    for cmd_name, cmd_obj in cli.commands.items():
        # Get CLI params
        cli_params = {p.name.replace('_', '-') for p in cmd_obj.params}
        
        # Get Railway flags (convert sample-mode → sample_mode)
        railway_key = cmd_name.replace('-', '_')
        if railway_key not in CANONICAL_COMMAND_MAPPINGS:
            continue  # Some CLI commands not in Railway
        
        railway_flags = set(CANONICAL_COMMAND_MAPPINGS[railway_key]['allowed_flags'].keys())
        railway_flags = {f.replace('--', '') for f in railway_flags}
        
        # Compare
        cli_only = cli_params - railway_flags
        railway_only = railway_flags - cli_params
        
        if cli_only:
            errors.append(f"{cmd_name}: CLI has {cli_only} but Railway doesn't")
        if railway_only:
            errors.append(f"{cmd_name}: Railway has {railway_only} but CLI doesn't")
    
    if errors:
        print("❌ Alignment errors found:")
        for error in errors:
            print(f"  - {error}")
        return False
    else:
        print("✅ All commands aligned!")
        return True

if __name__ == '__main__':
    import sys
    sys.exit(0 if check_alignment() else 1)
```

---

## Summary

**The 3-Layer Alignment Rule:**

> When you add/change ANY flag, update ALL 3 layers in this order:
> 1. CLI (source of truth)
> 2. Railway (validation layer)
> 3. Frontend (sender layer)
>
> Use the checklist above. No exceptions.

**Add this to your .cursorrules or agent instructions!**

