# Traycer Code Review Prompt: CLI Flags & Web UI Integration

**Context**: The Intercom Analysis Tool has multiple analysis modes with extensive CLI flags. The web UI is currently broken and flags are inconsistently applied across commands.

**Your Task**: Review the codebase for flag completeness and web UI integration issues, then provide recommendations.

---

## 🎯 What to Review

### 1. **Web UI Broken Button (CRITICAL)**

**File**: `deploy/railway_web.py` line 1108

**Problem**: Button calls JavaScript functions that don't exist:

```html
<button onclick="runAnalysis()" class="run-button">▶️ Run Analysis</button>
```

**Functions Called But Missing**:
- `runAnalysis()` - Not defined anywhere
- `updateAnalysisOptions()` - Not defined anywhere  
- `switchTab('terminal')` - Not defined anywhere

**Where They Should Be**: `static/app.js`

**What to Check**:
1. Search all JavaScript files for these function definitions
2. If not found, they need to be created
3. Review `/execute` endpoint in `deploy/railway_web.py` (line 1245) to understand how commands should be executed
4. Review `COMMAND_SCHEMAS` dict (lines 429-700) to see how commands map to CLI

**Expected Behavior**:
- `runAnalysis()` should:
  1. Read form values (analysisType, timePeriod, aiModel, etc.)
  2. Map to appropriate CLI command + flags
  3. Call `/execute` endpoint with SSE streaming
  4. Display output in terminal tab
  
- `updateAnalysisOptions()` should:
  1. Show/hide form sections based on selected analysis type
  2. Example: Show `sampleModeOptions` div when "sample-mode" selected

- `switchTab()` should:
  1. Hide all tab panes
  2. Show selected tab pane
  3. Update active button styling

---

### 2. **CLI Flag Completeness**

**File**: `src/main.py`

**Standard Flag Groups** (lines 61-105):
- DEFAULT_FLAGS: start-date, end-date, time-period
- OUTPUT_FLAGS: generate-gamma, output-format, output-dir
- TEST_FLAGS: test-mode, test-data-count
- DEBUG_FLAGS: verbose, audit-trail
- ANALYSIS_FLAGS: multi-agent, analysis-type, ai-model

**What to Check**:

#### Commands with MISSING FLAGS (need review):

**`sample-mode`** (line 3913):
- ❌ Missing: `--verbose`, `--audit-trail`
- Why it matters: Debugging tool should have debug flags
- Recommendation: Add DEBUG_FLAGS

**`agent-coaching-report`** (line 4385):
- ❌ Missing: `--test-mode`, `--test-data-count`, `--output-dir`, `--output-format`
- ❌ Missing: `--start-date`, `--end-date` (only has `--time-period`)
- Why it matters: Cannot test this command easily
- Recommendation: Add TEST_FLAGS, DEFAULT_FLAGS, OUTPUT_FLAGS

**`comprehensive-analysis`** (line 3018):
- ❌ Missing: `--time-period`, `--test-mode`, `--test-data-count`, `--ai-model`
- Why it matters: Hardest to test, no quick shortcuts
- Recommendation: Add TEST_FLAGS, time-period support, ai-model

**Category Commands** (`analyze-billing`, `analyze-product`, etc.) (lines 2308-2412):
- ❌ Missing: Almost all standard flags except `--generate-gamma`
- ❌ Missing: `--verbose`, `--audit-trail`, `--test-mode`, `--ai-model`
- Why it matters: These are heavily used but hard to debug/test
- Recommendation: Apply all standard flag groups

**`fin-escalations`** (line 484):
- ❌ Missing: `--output-dir`, `--ai-model`
- Why it matters: Inconsistent with other commands
- Recommendation: Add missing OUTPUT_FLAGS, ANALYSIS_FLAGS

**`tech-analysis`** (line 429):
- ❌ Missing: `--time-period`, `--test-mode`, `--ai-model`, `--output-format`
- ❌ Has: `--generate-ai-report` (inconsistent with `--generate-gamma`)
- Recommendation: Standardize naming, add missing flags

**Questions to Answer**:
1. Why are flag groups defined but not applied to all commands?
2. Should we create a decorator that automatically applies standard flags?
3. Are there commands that intentionally exclude certain flags? (Document why)

---

### 3. **Web UI Form → CLI Mapping**

**File**: `deploy/railway_web.py` lines 881-1108

**Form Fields to Audit**:

| Form Field | Current Mapping | Issues to Check |
|------------|-----------------|-----------------|
| `analysisType` | Maps to command name | ✅ Check all 18 options map correctly |
| `timePeriod` | Maps to `--time-period` | ✅ Verify all commands support it |
| `dataSource` | Maps to `--include-canny`? | ⚠️ **UNCLEAR** - How does "both" work? |
| `taxonomyFilter` | Maps to nothing | 🔴 **NOT IMPLEMENTED** |
| `outputFormat` | Maps to `--output-format` + `--generate-gamma` | ✅ Verify logic is correct |
| `aiModel` | Maps to `--ai-model` | ✅ Check all commands have this flag |
| `testMode` checkbox | Maps to `--test-mode` | ✅ Check |
| `testDataCount` | Maps to `--test-data-count` | ✅ Check |
| `verboseLogging` checkbox | Maps to `--verbose` | ✅ Check |
| `auditMode` checkbox | Maps to `--audit-trail` | ✅ Check |

**Specific Issues to Investigate**:

1. **Taxonomy Filter (line 1028-1044)**:
   ```html
   <select id="taxonomyFilter">
       <option value="" selected>All Categories</option>
       <option value="Billing">Billing</option>
       ...
   </select>
   ```
   - This dropdown exists in UI but has NO mapping to any CLI flag
   - **Question**: Should this add `--filter-category` flag to commands?
   - **Question**: Which commands should support category filtering?

2. **Data Source (line 1022-1026)**:
   ```html
   <select id="dataSource">
       <option value="intercom" selected>Intercom Only</option>
       <option value="canny">Canny Only</option>
       <option value="both">Both Sources</option>
   </select>
   ```
   - How does "both" map to CLI?
   - Should it add `--include-canny` flag?
   - Should it switch to `canny-analysis` command?
   - **Check**: Is this logic implemented in the (missing) runAnalysis() function?

3. **Sample Mode Options (lines 976-1014)**:
   - Has custom fields: `sampleCount`, `sampleTimePeriod`
   - Should only show when "sample-mode" is selected
   - **Check**: Is visibility logic in updateAnalysisOptions()?

---

### 4. **Command Schema Completeness**

**File**: `deploy/railway_web.py` lines 429-700

**Schema Dict**: `COMMAND_SCHEMAS`

**What to Check**:

1. **Does every web UI option have a schema entry?**
   - Compare lines 885-920 (dropdown options) with schema keys
   - Missing schemas:
     - ❌ `voice-of-customer-hilary`
     - ❌ `voice-of-customer-synthesis`
     - ❌ `voice-of-customer-complete`
     - ❌ `agent-performance-horatio-team`
     - ❌ `agent-performance-boldr-team`
     - ❌ `agent-performance-escalated`
     - ❌ `agent-performance-horatio-individual`
     - ❌ `agent-performance-boldr-individual`
     - ❌ `agent-coaching-horatio`
     - ❌ `agent-coaching-boldr`

2. **Do all schema entries match actual CLI commands?**
   - Check each schema's `'command'` and `'args'` values
   - Verify against `src/main.py` @cli.command decorators
   - Check flag names match exactly

3. **Are allowed_flags complete and accurate?**
   - Compare schema's `'allowed_flags'` with actual CLI flags
   - Example: Check if `all_categories` schema (line 647) has all flags that `analyze-all-categories` command actually supports

---

### 5. **Analysis Type Consistency**

**Files**: 
- `src/config/analysis_modes.py` (lines 19-27)
- `src/config/modes.py` (lines 34-40, 104-171)
- `src/models/analysis_models.py` (lines 11-16)

**Analysis Types Defined**:
- `standard` - Single-pass analysis
- `topic-based` - Hilary's VoC cards
- `synthesis` - Cross-cutting insights
- `complete` - All modes combined

**What to Check**:

1. **Are these used consistently**?
   - `src/config/analysis_modes.py`: `ANALYSIS_TYPES = ['standard', 'topic-based', 'synthesis', 'complete']`
   - `src/models/analysis_models.py`: `AnalysisMode` enum
   - `src/config/modes.py`: `AnalysisMode` enum
   - **Question**: Are there two different AnalysisMode enums? (lines show different locations)

2. **Web UI Hidden Dropdown** (deploy/railway_web.py line 1116):
   ```html
   <select id="analysisMode" style="display:none;">
       <option value="topic-based">...</option>
       <option value="synthesis">...</option>
       <option value="complete">...</option>
   </select>
   ```
   - Why is this hidden (`display:none`)?
   - Should this be removed or made visible?
   - Is it redundant with the main `analysisType` dropdown?

3. **Multi-Agent vs Analysis Type**:
   - `--multi-agent` flag forces multi-agent mode
   - `--analysis-type` chooses which type
   - **Question**: What happens if you set `--analysis-type synthesis` without `--multi-agent`?
   - **Check**: `src/config/modes.py` lines 104-171 for logic

---

### 6. **Test Mode Data Presets**

**Locations**:
- `src/main.py` multiple commands define these presets
- Example: lines 3847-3854 (canny-analysis)

**Presets Defined**:
```python
'micro': 100
'small': 500
'medium': 1000
'large': 5000
'xlarge': 10000
'xxlarge': 20000
```

**What to Check**:
1. Are these presets consistent across ALL commands that have `--test-data-count`?
2. Do web UI dropdown values (line 1067-1075) match these presets?
   - Web: 50, 100, 500, 1000, 5000, 10000, 20000
   - Presets: 100, 500, 1000, 5000, 10000, 20000
   - **Discrepancy**: Web has "50" but preset doesn't have 'tiny' or similar
3. Should presets be centralized in config file?

---

### 7. **Time Period Handling**

**Multiple Approaches Found**:

**Approach 1: time-period with periods-back**
```bash
--time-period week --periods-back 3  # Last 3 weeks
```
Used by: `voice-of-customer`

**Approach 2: time-period only**
```bash
--time-period week  # Just last week
```
Used by: `fin-escalations`, `canny-analysis`, `agent-performance`, `agent-coaching-report`

**Approach 3: days**
```bash
--days 30  # Last 30 days
```
Used by: Category commands, `tech-analysis`, `fin-escalations` (also!)

**Approach 4: start-date + end-date required**
```bash
--start-date 2024-01-01 --end-date 2024-01-31  # Required
```
Used by: `comprehensive-analysis`, `export`

**What to Check**:
1. Is this intentional diversity or should it be unified?
2. Do all approaches correctly calculate date ranges?
3. Check date calculation logic in each command for consistency
4. **Special**: voice-of-customer supports "yesterday" - do others need this?

---

### 8. **Config File vs Environment Variables**

**Files**:
- `config/analysis_modes.yaml` - Analysis mode defaults
- `src/config/modes.py` - Mode selection logic
- `src/config/settings.py` - Main settings

**Environment Variables** (from `config/analysis_modes.yaml` line 87):
- `ANALYSIS_MODE` - Force specific mode
- `FORCE_MULTI_AGENT` - Force multi-agent
- `FORCE_STANDARD` - Force standard
- `AI_MODEL` - Default AI model

**What to Check**:
1. Do CLI flags override environment variables correctly?
2. Do environment variables override config file?
3. Order of precedence documented anywhere?
4. Check `src/config/modes.py` lines 104-171 for precedence logic
5. Are there conflicts between:
   - `--multi-agent` CLI flag
   - `FORCE_MULTI_AGENT` env var
   - `default_mode: multi-agent` in YAML

---

### 9. **Audit Trail Integration**

**Flag**: `--audit-trail` (appears in 11+ commands)

**What to Check**:
1. Does every command that has `--audit-trail` actually USE it?
2. Search for: `if audit_trail:` or `audit_trail=True` in command handlers
3. Check if AuditTrail service is initialized when flag is set
4. Example to verify: `voice-of-customer` line 4104 has flag - does implementation use it?
5. Look for pattern: `show_audit_trail_enabled()` calls (line 52)

**Files to Check**:
- Command handlers in `src/main.py`
- AuditTrail service usage in agent execution
- Verify audit output actually appears in console

---

### 10. **Output Format Consistency**

**Three Different Patterns Found**:

**Pattern 1**: `--output-format <gamma|markdown|json|excel>`
- Used by: voice-of-customer, canny-analysis, fin-escalations

**Pattern 2**: `--generate-gamma` + `--gamma-export <pdf|pptx>`
- Used by: comprehensive-analysis

**Pattern 3**: `--generate-ai-report` (boolean only)
- Used by: tech-analysis

**What to Check**:
1. Why three different patterns?
2. Can output-format be standardized to one pattern?
3. When `--output-format gamma` is set, is `--generate-gamma` also needed?
4. What happens if you set conflicting options?
5. Check output generation code for handling of these flags

---

## 🔍 Specific Code Locations to Review

### CLI Command Definitions
```
src/main.py:
- Lines 61-105: Flag group definitions (DEFAULT_FLAGS, OUTPUT_FLAGS, etc.)
- Lines 3913-3968: sample-mode command
- Lines 4075-4273: voice-of-customer command (reference implementation)
- Lines 4275-4382: agent-performance command  
- Lines 4385-4414: agent-coaching-report command
- Lines 3782-3910: canny-analysis command
- Lines 484-568: fin-escalations command
- Lines 3018-3162: comprehensive-analysis command
- Lines 429-458: tech-analysis command
- Lines 2308-2411: Category commands (analyze-billing, etc.)
```

### Web UI Integration
```
deploy/railway_web.py:
- Lines 429-700: COMMAND_SCHEMAS dict
- Lines 881-1108: HTML form with dropdowns
- Line 1108: Broken runAnalysis() button
- Lines 1245-1496: /execute endpoint (how commands run)
- Line 1200: Script include that should have functions
```

### JavaScript Files
```
static/app.js: Should contain runAnalysis(), updateAnalysisOptions(), switchTab()
static/preview.js: Markdown rendering (correct, no issues)
static/timeline.js: Timeline visualization (correct, no issues)
```

### Configuration
```
config/analysis_modes.yaml: Mode defaults and feature flags
src/config/modes.py: Mode selection logic and precedence
src/config/analysis_modes.py: Analysis type constants
src/models/analysis_models.py: AnalysisMode enum
```

---

## 🎯 Key Questions to Answer

### 1. Web UI
- [ ] Where should `runAnalysis()`, `updateAnalysisOptions()`, and `switchTab()` be defined?
- [ ] What is the correct flow from button click → command execution?
- [ ] How should form values map to CLI flags?
- [ ] Should `taxonomyFilter` dropdown work? If so, what flag should it set?

### 2. Flag Standardization
- [ ] Should ALL commands have --verbose and --audit-trail?
- [ ] Should ALL commands have --test-mode?
- [ ] Why do some commands use --days vs --time-period?
- [ ] Should comprehensive-analysis have --time-period support?

### 3. Analysis Types
- [ ] Why are there two AnalysisMode enums? (models/analysis_models.py vs config/modes.py)
- [ ] Is the hidden analysisMode dropdown (line 1116) needed or should it be removed?
- [ ] What's the relationship between --multi-agent flag and analysis-type?

### 4. Test Mode Coverage
- [ ] Which commands MUST support test-mode for dev workflow?
- [ ] Which commands can skip test-mode (if any)?
- [ ] Are test data presets consistent across all commands?

### 5. Output Handling
- [ ] Should --output-format be standardized across all commands?
- [ ] What's the difference between --generate-gamma and --output-format gamma?
- [ ] When should --gamma-export (pdf/pptx) be used vs --export-as?

---

## 💡 Recommendations to Validate

After reviewing, please validate these recommendations:

### Immediate Fixes

1. **Create missing JavaScript functions** in `static/app.js`:
   ```javascript
   async function runAnalysis() { /* implementation */ }
   function updateAnalysisOptions() { /* implementation */ }
   function switchTab(tabName) { /* implementation */ }
   ```

2. **Add standard flags to incomplete commands**:
   - sample-mode: Add `--verbose`, `--audit-trail`
   - agent-coaching-report: Add `--test-mode`, `--test-data-count`, `--output-dir`
   - Category commands: Add DEBUG_FLAGS, TEST_FLAGS, OUTPUT_FLAGS
   - comprehensive-analysis: Add `--test-mode`, `--time-period`, `--ai-model`

### Medium-Term Improvements

3. **Implement taxonomy filtering**:
   - Add `--filter-category <name>` flag to voice-of-customer
   - Wire up web UI taxonomyFilter dropdown

4. **Standardize time period handling**:
   - Replace --days with --time-period everywhere
   - Add --periods-back support where needed
   - Deprecate --days parameter

5. **Standardize output flags**:
   - Use --output-format consistently
   - Merge --gamma-export into --output-format options
   - Replace --generate-ai-report with standard pattern

### Long-Term Quality

6. **Apply decorator pattern for standard flags**:
   - Create @standard_flags decorator
   - Automatically apply DEFAULT_FLAGS + OUTPUT_FLAGS + TEST_FLAGS + DEBUG_FLAGS
   - Allow commands to opt-out if needed

7. **Centralize test data presets**:
   - Move to config/test_data.py
   - Reference from all commands
   - Add 'tiny': 50 preset for web UI

8. **Update web UI command schemas**:
   - Add all missing VoC variants
   - Add all agent performance variants
   - Ensure flags match CLI exactly

---

## 📝 Code Pattern Examples to Check

### Example 1: Flag Application Pattern

**Good Example** (voice-of-customer, line 4075):
```python
@cli.command(name='voice-of-customer')
@click.option('--time-period', ...)
@click.option('--start-date', ...)
@click.option('--end-date', ...)
@click.option('--test-mode', ...)
@click.option('--test-data-count', ...)
@click.option('--verbose', ...)
@click.option('--audit-trail', ...)
@click.option('--ai-model', ...)
@click.option('--output-dir', ...)
# ... 17 flags total, very thorough
```

**Bad Example** (analyze-billing, line 2308):
```python
@cli.command(name='analyze-billing')
@click.option('--days', ...)
@click.option('--start-date', ...)
@click.option('--end-date', ...)
@click.option('--generate-gamma', ...)
# ... only 4 flags, missing verbose, test-mode, ai-model, etc.
```

**Check**: Why the inconsistency? Is there a reason or was it overlooked?

### Example 2: Test Data Preset Parsing

**Pattern Used** (multiple commands):
```python
test_data_presets = {
    'micro': 100,
    'small': 500,
    'medium': 1000,
    'large': 5000,
    'xlarge': 10000,
    'xxlarge': 20000
}

if test_data_count.lower() in test_data_presets:
    test_data_count_int = test_data_presets[test_data_count.lower()]
```

**Check**:
- Is this code duplicated across multiple commands?
- Should it be a shared utility function?
- Are presets identical everywhere?

### Example 3: Time Period Calculation

**Pattern in voice-of-customer** (line 4155+):
```python
if time_period:
    end_dt = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    end_dt = end_dt - timedelta(days=1)  # End yesterday
    
    if time_period == 'week':
        start_dt = end_dt - timedelta(days=6)  # Exactly 7 days
```

**Check**:
- Is this logic duplicated in other commands?
- Do all commands that use --time-period calculate dates the same way?
- Should this be a shared utility function?

---

## 🎯 Deliverables Expected

After your review, please provide:

### 1. **Root Cause Analysis**
- Why is the web UI button broken?
- Why are flags inconsistently applied?
- Are there architectural reasons or just oversight?

### 2. **Implementation Plan**
- Step-by-step fix for web UI button
- Priority order for adding missing flags
- Refactoring recommendations for shared logic

### 3. **Code Examples**
- Working `runAnalysis()` function implementation
- Decorator pattern for standard flags
- Shared date calculation utility

### 4. **Migration Guide**
- How to safely add flags to existing commands
- Backward compatibility considerations
- Testing strategy for flag additions

### 5. **Risk Assessment**
- What breaks if we add flags to commands?
- Do existing users/scripts rely on current behavior?
- Are there commands that intentionally have fewer flags?

---

## 🔬 Testing Checklist

Please verify these scenarios work:

### Web UI
- [ ] Button click triggers command execution
- [ ] Form values correctly map to CLI flags
- [ ] All 18 analysis type options execute correct commands
- [ ] Test mode checkbox adds --test-mode flag
- [ ] Verbose checkbox adds --verbose flag
- [ ] Audit checkbox adds --audit-trail flag

### CLI Commands
- [ ] voice-of-customer with all 17 flags works
- [ ] sample-mode executes and respects new debug flags
- [ ] Category commands work with added flags
- [ ] No regressions in existing functionality

### Flag Precedence
- [ ] CLI flags override environment variables
- [ ] Environment variables override config file
- [ ] Conflicting flags handled gracefully

---

## 📚 Related Documentation

These docs may have relevant context:
- `TEST_MODE_GUIDE.md` - Test mode documentation
- `SAMPLE_MODE_GUIDE.md` - Sample mode documentation
- `QUICKSTART.md` - User-facing command examples
- `DEVELOPMENT_STANDARDS.md` - Dev standards
- `TESTING.md` - Testing guidelines
- `TEST_UNIFIED_FLAGS.md` - Flag unification work

---

## 🎬 Summary for Traycer

**What I need you to do**:

1. **Find and fix the broken web UI button**
   - Locate where runAnalysis(), updateAnalysisOptions(), switchTab() should be defined
   - Implement these functions
   - Test that button actually works

2. **Audit flag completeness across all 18+ commands**
   - Use the flag groups (DEFAULT_FLAGS, OUTPUT_FLAGS, etc.) as reference
   - Identify which commands are missing which flags
   - Explain WHY some commands have fewer flags (intentional vs oversight)

3. **Review web UI → CLI mapping**
   - Verify all 18 dropdown options map to correct commands
   - Check taxonomyFilter dropdown - should this work or be removed?
   - Verify dataSource dropdown logic

4. **Check for code duplication**
   - Test data preset parsing (repeated in many commands)
   - Time period calculation (repeated in many commands)
   - Flag validation logic
   - Recommend shared utilities

5. **Document findings**
   - List all gaps and inconsistencies
   - Prioritize fixes (critical → nice-to-have)
   - Provide code examples for fixes

**Focus Areas** (in priority order):
1. 🔴 **Web UI broken button** (blocks all web usage)
2. ⚠️ **Category commands missing standard flags** (poor DX)
3. ⚠️ **agent-coaching-report missing test mode** (hard to test)
4. ⚠️ **comprehensive-analysis missing test mode** (hard to test)
5. ℹ️ **Flag standardization** (code quality)
6. ℹ️ **Shared utilities** (reduce duplication)

**Expected Output**: Detailed analysis with specific line numbers, code examples, and actionable recommendations.

---

**End of Review Prompt**

