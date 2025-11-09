# --include-hierarchy Flag Quick Reference

## 3-Layer Alignment ✅

```
┌─────────────────────────────────────────────────────────────────┐
│                      LAYER 1: CLI (src/main.py)                 │
├─────────────────────────────────────────────────────────────────┤
│ @click.option('--include-hierarchy/--no-hierarchy',             │
│               default=True)                                      │
│ def sample_mode(..., include_hierarchy: bool, ...):             │
│     run_sample_mode(..., include_hierarchy=include_hierarchy)   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│            LAYER 2: RAILWAY (deploy/railway_web.py)             │
├─────────────────────────────────────────────────────────────────┤
│ CANONICAL_COMMAND_MAPPINGS = {                                  │
│   'sample_mode': {                                              │
│     'allowed_flags': {                                          │
│       '--include-hierarchy': {                                  │
│         'type': 'boolean',                                      │
│         'default': True,  ✅ MATCHES CLI                        │
│       }                                                          │
│     }                                                            │
│   }                                                              │
│ }                                                                │
│                                                                  │
│ HTML:                                                            │
│ <input type="checkbox" id="includeHierarchy" checked>           │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│              LAYER 3: FRONTEND (static/app.js)                  │
├─────────────────────────────────────────────────────────────────┤
│ if (analysisType === 'schema-dump') {                           │
│   const includeHierarchy =                                      │
│     document.getElementById('includeHierarchy')?.checked ?? true│
│                                                                  │
│   if (!includeHierarchy) {  // Only send if false               │
│     args.push('--no-hierarchy');                                │
│   }                                                              │
│ }                                                                │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│      LAYER 4: SERVICE (src/services/sample_mode.py)             │
├─────────────────────────────────────────────────────────────────┤
│ async def run_sample_mode(..., include_hierarchy: bool = True): │
│   await sample_mode.pull_sample(...,                            │
│                                  include_hierarchy=...)          │
│                                                                  │
│ async def pull_sample(..., include_hierarchy: bool = True):     │
│   if include_hierarchy:  # Conditionally display                │
│     console.print("🔍 TOPIC HIERARCHY DEBUG")                   │
│     self._display_hierarchy_debug(hierarchy_debug)              │
└─────────────────────────────────────────────────────────────────┘
```

## Key Design Decisions

### ✅ Default: True (Show Hierarchy)
- Maintains current behavior
- Backward compatible
- Users explicitly opt-out

### ✅ Boolean Toggle Pattern
- CLI: `--include-hierarchy` / `--no-hierarchy`
- Railway: `type: 'boolean'`
- Frontend: Checkbox (checked by default)

### ✅ Conditional Display Only
- Data still computed for JSON export when hidden
- Only affects terminal/console output
- Preserves full functionality

### ✅ Schema-Dump Specific
- Only applies to `schema-dump` analysis type
- Part of diagnostic/debugging tools
- Not sent to other analysis types

## Type Verification

| Layer | Type | Default | Match |
|-------|------|---------|-------|
| CLI | boolean toggle | True | ✅ |
| Railway | boolean | True | ✅ |
| Frontend | checkbox | checked (true) | ✅ |
| Service | bool | True | ✅ |

## Testing Commands

```bash
# CLI - Show hierarchy (default)
python src/main.py sample-mode --schema-mode quick

# CLI - Hide hierarchy
python src/main.py sample-mode --schema-mode quick --no-hierarchy

# CLI - Explicit show
python src/main.py sample-mode --schema-mode quick --include-hierarchy
```

## What Gets Hidden

When `--no-hierarchy` is used or checkbox is unchecked:

```
❌ Hidden from terminal output:
   ================================================================================
   🔍 TOPIC HIERARCHY & DOUBLE-COUNTING DEBUG
   Detecting if conversations are being assigned to multiple topics
   ================================================================================
   
   • Topic coverage statistics
   • Hierarchy examples from custom_attributes
   • Double-counting detection
   
✅ Still computed:
   • hierarchy_debug data in JSON export
   • All other sample mode sections shown
   • Field coverage, samples, LLM tests, etc.
```

## Files Modified

- ✅ `src/main.py` (lines 4218-4224, 4287)
- ✅ `deploy/railway_web.py` (lines 347-351, 1409-1417)
- ✅ `static/app.js` (lines 294-306)
- ✅ `src/services/sample_mode.py` (lines 62-84, 239-251, 1134-1172)

## No Breaking Changes

- ✅ Default behavior unchanged (hierarchy shown)
- ✅ All existing flags still work
- ✅ JSON export format unchanged
- ✅ No impact on other analysis types

