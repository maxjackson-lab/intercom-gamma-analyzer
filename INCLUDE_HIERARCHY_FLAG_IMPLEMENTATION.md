# --include-hierarchy Flag Implementation

**Date:** November 8, 2025  
**Feature:** Add optional flag to show/hide topic hierarchy debugging section in schema-dump

## Summary

Added `--include-hierarchy` flag to the `sample-mode` command (used by schema-dump) following the 3-layer contract. The flag defaults to `true`, allowing users to optionally hide the hierarchy debugging section.

## Changes Made

### Layer 1: CLI (src/main.py)

**Lines 4218-4224:**
- Added `@click.option('--include-hierarchy/--no-hierarchy', default=True)`
- Added `include_hierarchy: bool` to function signature
- Passed `include_hierarchy=include_hierarchy` to `run_sample_mode()`

```python
@click.option('--include-hierarchy/--no-hierarchy', default=True,
              help='Show/hide topic hierarchy debugging section (default: show)')
def sample_mode(count: int, start_date: Optional[str], end_date: Optional[str], 
                time_period: str, save_to_file: bool, test_llm: bool, schema_mode: str,
                ai_model: str, include_hierarchy: bool, verbose: bool):
```

### Layer 2: Railway Validation (deploy/railway_web.py)

**Lines 347-351:**
- Added `--include-hierarchy` to `CANONICAL_COMMAND_MAPPINGS['sample_mode']['allowed_flags']`
- Type: `boolean`
- Default: `True`
- Description: "Show/hide topic hierarchy debugging section"

```python
'--include-hierarchy': {
    'type': 'boolean',
    'default': True,
    'description': 'Show/hide topic hierarchy debugging section'
},
```

**Lines 1409-1417:**
- Added checkbox UI element in the Schema Dump info panel
- Element ID: `includeHierarchy`
- Checked by default
- Includes descriptive help text

```html
<div style="margin-bottom: 15px;">
    <label style="display: flex; align-items: center; cursor: pointer; color: #e5e7eb; font-size: 14px;">
        <input type="checkbox" id="includeHierarchy" checked style="margin-right: 8px; cursor: pointer;">
        <span>Show Topic Hierarchy Debug Section</span>
    </label>
    <p style="margin: 5px 0 0 24px; font-size: 12px; color: #9ca3af;">
        Displays topic detection and hierarchy structure debugging information
    </p>
</div>
```

### Layer 3: Frontend (static/app.js)

**Lines 294-306:**
- Read checkbox value: `document.getElementById('includeHierarchy')?.checked ?? true`
- Only send `--no-hierarchy` when checkbox is unchecked (since default is true)

```javascript
} else if (analysisType === 'schema-dump') {
    const schemaMode = document.getElementById('schemaMode')?.value || 'quick';
    const includeHierarchy = document.getElementById('includeHierarchy')?.checked ?? true;
    
    args.push('sample-mode');
    args.push('--time-period', 'week');
    args.push('--save-to-file');
    args.push('--test-llm');
    args.push('--schema-mode', schemaMode);
    
    // Add hierarchy flag (only send --no-hierarchy if unchecked, since default is true)
    if (!includeHierarchy) {
        args.push('--no-hierarchy');
    }
```

### Layer 4: Service Implementation (src/services/sample_mode.py)

**run_sample_mode function (lines 1134-1172):**
- Added `include_hierarchy: bool = True` parameter
- Updated docstring
- Passed to `pull_sample()`

**pull_sample method (lines 62-84):**
- Added `include_hierarchy: bool = True` parameter
- Updated docstring

**Display logic (lines 239-251):**
- Made hierarchy debug section conditional on `include_hierarchy`
- Still computes hierarchy data for JSON export when hidden
- Shows full section when flag is true (default behavior)

```python
# ===== TOPIC HIERARCHY & DOUBLE-COUNTING DEBUG =====
# Only show if include_hierarchy is True (defaults to True)
if include_hierarchy:
    console.print("\n" + "="*80)
    console.print("[bold]🔍 TOPIC HIERARCHY & DOUBLE-COUNTING DEBUG[/bold]")
    console.print("[dim]Detecting if conversations are being assigned to multiple topics[/dim]")
    console.print("="*80 + "\n")
    
    hierarchy_debug = await self._debug_topic_hierarchy(conversations)
    self._display_hierarchy_debug(hierarchy_debug)
else:
    # Still compute for JSON export, but don't display
    hierarchy_debug = await self._debug_topic_hierarchy(conversations)
```

## Verification

✅ **All layers aligned:**
1. CLI flag defined with correct type (boolean toggle)
2. Railway validation includes flag with matching type and default
3. Frontend sends flag conditionally based on checkbox state
4. Service layer accepts and uses flag to control display

✅ **No linter errors** in any modified files

✅ **Default behavior preserved:**
- Default is `true` (show hierarchy section)
- Maintains backward compatibility
- Users explicitly opt-out with `--no-hierarchy` or by unchecking box

## Usage

### CLI Usage
```bash
# Default - shows hierarchy (no flag needed)
python src/main.py sample-mode

# Explicitly show hierarchy
python src/main.py sample-mode --include-hierarchy

# Hide hierarchy section
python src/main.py sample-mode --no-hierarchy

# With schema-dump wrapper
python src/main.py sample-mode --schema-mode deep --no-hierarchy
```

### Web UI Usage
1. Select "Schema Dump" from Analysis Type dropdown
2. Hierarchy checkbox appears in the Schema Dump info panel
3. Check/uncheck "Show Topic Hierarchy Debug Section"
4. Checked by default (matches CLI default)

## Testing Checklist

- [ ] Test CLI with `--include-hierarchy` (should show section - default)
- [ ] Test CLI with `--no-hierarchy` (should hide section)
- [ ] Test Web UI with checkbox checked (should show section - default)
- [ ] Test Web UI with checkbox unchecked (should hide section)
- [ ] Verify JSON export still includes hierarchy data when hidden
- [ ] Run alignment checker: `python scripts/check_cli_web_alignment.py`

## Related Files

- `src/main.py` - CLI command definition
- `deploy/railway_web.py` - Railway validation and HTML UI
- `static/app.js` - Frontend command builder
- `src/services/sample_mode.py` - Service implementation
- `CLI_WEB_ALIGNMENT_CHECKLIST.md` - Reference guide

## Notes

- The hierarchy debugging section helps identify double-counting issues in topic detection
- Hiding it reduces terminal output for cleaner schema dumps
- Data is still computed for JSON export regardless of display flag
- This follows the pattern established by other optional flags like `--test-llm` and `--verbose`

