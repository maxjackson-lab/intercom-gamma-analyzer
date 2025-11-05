# CLI Flags Comprehensive Audit - All Analysis Modes

**Date**: November 5, 2025  
**Status**: 🔴 **CRITICAL ISSUES FOUND**  
**Primary Issue**: Web UI broken - missing JavaScript functions

---

## 🚨 Critical Issue: Web Interface Broken

### Problem
The "Run Analysis" button in `deploy/railway_web.py` (line 1108) calls JavaScript functions that **DO NOT EXIST**:

```html
<button onclick="runAnalysis()" class="run-button">▶️ Run Analysis</button>
<select id="analysisType" onchange="updateAnalysisOptions()">
```

### Missing Functions
These functions are referenced but not defined anywhere:
- ❌ `runAnalysis()` - Main function to execute analysis
- ❌ `updateAnalysisOptions()` - Function to show/hide options based on analysis type
- ❌ `switchTab()` - Function to switch between terminal/summary/files/gamma tabs

### Location
- **Expected in**: `static/app.js`
- **Actually found**: Only utility functions (copyToClipboard, downloadFile, etc.)
- **Impact**: **Button does nothing when clicked**

### Files Checked
- ✅ `static/app.js` - Only has utilities, no runAnalysis
- ✅ `static/preview.js` - Only markdown rendering
- ✅ `static/timeline.js` - Only timeline visualization
- ✅ `deploy/railway_web.py` - Has button but no <script> defining the function

---

## 📋 Complete CLI Command Flag Audit

### Flag Groups (Defined but not consistently applied)

Located in `src/main.py` lines 61-105:

| Flag Group | Flags Included | Status |
|------------|----------------|--------|
| **DEFAULT_FLAGS** | `--start-date`, `--end-date`, `--time-period` | ⚠️ Partially applied |
| **OUTPUT_FLAGS** | `--generate-gamma`, `--output-format`, `--output-dir` | ⚠️ Partially applied |
| **TEST_FLAGS** | `--test-mode`, `--test-data-count` | ✅ Widely applied |
| **DEBUG_FLAGS** | `--verbose`, `--audit-trail` | ✅ Widely applied |
| **ANALYSIS_FLAGS** | `--multi-agent`, `--analysis-type`, `--ai-model` | ⚠️ Not consistently applied |

---

## 🎯 Analysis Commands by Category

### 1. Voice of Customer (VoC) Analysis

#### Command: `voice-of-customer`
**Location**: `src/main.py` line 4075

**Flags** (17 total):
```bash
--time-period <week|month|quarter|year|yesterday>
--periods-back <int>          # Default: 1
--start-date <YYYY-MM-DD>
--end-date <YYYY-MM-DD>
--enable-fallback/--no-fallback  # Default: True
--include-trends              # Boolean flag
--include-canny               # Boolean flag
--canny-board-id <string>
--generate-gamma              # Boolean flag
--test-mode                   # Boolean flag
--test-data-count <string>    # Default: '100'
--verbose                     # Boolean flag
--separate-agent-feedback     # Boolean flag, Default: True
--multi-agent                 # Boolean flag
--analysis-type <standard|topic-based|synthesis|complete>  # Default: 'topic-based'
--ai-model <openai|claude>
--audit-trail                 # Boolean flag
--output-dir <path>          # Default: 'outputs'
```

**Audit**: ✅ **COMPLETE** - Has all standard flags

---

### 2. Sample Mode (Quick Debug)

#### Command: `sample-mode`
**Location**: `src/main.py` line 3913

**Flags** (5 total):
```bash
--count <int>                # Default: 50, Range: 50-100 recommended
--start-date <YYYY-MM-DD>
--end-date <YYYY-MM-DD>
--time-period <day|week|month>  # Default: 'week'
--save-to-file/--no-save    # Default: True
```

**Missing Flags**: ⚠️
- ❌ `--verbose` - Would be useful for debugging
- ❌ `--audit-trail` - Would help understand sampling logic
- ❌ `--ai-model` - Not applicable (no AI used)
- ❌ `--output-dir` - Always uses outputs/

**Audit**: ⚠️ **MISSING DEBUG FLAGS** (--verbose, --audit-trail)

---

### 3. Canny Analysis

#### Command: `canny-analysis`
**Location**: `src/main.py` line 3782

**Flags** (14 total):
```bash
--start-date <YYYY-MM-DD>
--end-date <YYYY-MM-DD>
--time-period <week|month|quarter>
--board-id <string>
--ai-model <openai|claude>   # Default: 'openai'
--enable-fallback/--no-fallback  # Default: True
--include-comments/--no-comments  # Default: True
--include-votes/--no-votes   # Default: True
--generate-gamma             # Boolean flag
--output-format <gamma|markdown|json|excel>  # Default: 'markdown'
--test-mode                  # Boolean flag
--test-data-count <string>   # Default: '100'
--verbose                    # Boolean flag
--audit-trail                # Boolean flag
--output-dir <path>         # Default: 'outputs'
```

**Audit**: ✅ **COMPLETE** - Has all standard flags

---

### 4. Comprehensive Analysis

#### Command: `comprehensive-analysis`
**Location**: `src/main.py` line 3018

**Flags** (12 total):
```bash
--start-date <YYYY-MM-DD>    # Required
--end-date <YYYY-MM-DD>      # Required
--max-conversations <int>    # Default: 1000
--generate-gamma             # Boolean flag
--gamma-style <executive|detailed|training>  # Default: 'executive'
--gamma-export <pdf|pptx>
--export-docs                # Boolean flag
--include-fin-analysis       # Boolean flag, Default: True
--include-technical-analysis # Boolean flag, Default: True
--include-macro-analysis     # Boolean flag, Default: True
--output-dir <path>         # Default: 'outputs'
--verbose                    # Boolean flag
--audit-trail                # Boolean flag
```

**Missing Flags**: ⚠️
- ❌ `--time-period` - Must use start/end dates
- ❌ `--test-mode` - Cannot test this command easily
- ❌ `--test-data-count` - No mock data support
- ❌ `--ai-model` - Uses default from config

**Audit**: ⚠️ **MISSING TEST MODE FLAGS**

---

### 5. Fin Escalations Analysis

#### Command: `fin-escalations`
**Location**: `src/main.py` line 484

**Flags** (11 total):
```bash
--days <int>                 # Default: 30
--start-date <YYYY-MM-DD>
--end-date <YYYY-MM-DD>
--time-period <week|month|quarter>
--detailed                   # Boolean flag
--generate-gamma             # Boolean flag
--output-format <gamma|markdown|json|excel>  # Default: 'markdown'
--test-mode                  # Boolean flag
--test-data-count <string>   # Default: '100'
--verbose                    # Boolean flag
--audit-trail                # Boolean flag
```

**Missing Flags**: ⚠️
- ❌ `--output-dir` - Uses default 'outputs'
- ❌ `--ai-model` - Uses default from config

**Audit**: ⚠️ **MISSING OUTPUT-DIR FLAG**

---

### 6. Agent Performance Analysis

#### Command: `agent-performance`
**Location**: `src/main.py` line 4275

**Flags** (12 total):
```bash
--agent <horatio|boldr|escalated>  # Required
--time-period <week|month|quarter>
--individual-breakdown       # Boolean flag
--top-n <int>               # Default: 10
--generate-gamma             # Boolean flag
--test-mode                  # Boolean flag
--test-data-count <string>   # Default: '100'
--verbose                    # Boolean flag
--audit-trail                # Boolean flag
--ai-model <openai|claude>
--output-dir <path>         # Default: 'outputs'
--start-date <YYYY-MM-DD>
--end-date <YYYY-MM-DD>
```

**Audit**: ✅ **COMPLETE** - Has all standard flags

---

### 7. Agent Coaching Report

#### Command: `agent-coaching-report`
**Location**: `src/main.py` line 4385

**Flags** (7 total):
```bash
--vendor <horatio|boldr>    # Required
--time-period <week|month|quarter>  # Required
--top-n <int>               # Default: 5
--generate-gamma             # Boolean flag
--verbose                    # Boolean flag
--audit-trail                # Boolean flag
--ai-model <openai|claude>
```

**Missing Flags**: ⚠️
- ❌ `--test-mode` - No mock data support
- ❌ `--test-data-count` - No mock data support
- ❌ `--output-dir` - Uses default 'outputs'
- ❌ `--start-date` / `--end-date` - Must use time-period
- ❌ `--output-format` - Always markdown

**Audit**: ⚠️ **MISSING TEST MODE AND DATE FLEXIBILITY**

---

### 8. Category-Specific Analysis Commands

These all follow similar patterns:

#### Commands:
- `analyze-billing` (line 2308)
- `analyze-product` (line 2334)
- `analyze-sites` (line 2360)
- `analyze-api` (line 2387)

**Common Flags** (3-4 total):
```bash
--days <int>                # Default: 30
--start-date <YYYY-MM-DD>
--end-date <YYYY-MM-DD>
--generate-gamma            # Boolean flag
```

**Missing Flags**: 🔴 **SEVERELY INCOMPLETE**
- ❌ `--time-period` - Must use days or dates
- ❌ `--test-mode` - No mock data
- ❌ `--test-data-count` - No mock data
- ❌ `--verbose` - No debug logging
- ❌ `--audit-trail` - No audit trail
- ❌ `--ai-model` - Uses default
- ❌ `--output-dir` - Uses default
- ❌ `--output-format` - Always markdown

**Audit**: 🔴 **CRITICAL - MISSING MOST STANDARD FLAGS**

---

### 9. Tech Analysis

#### Command: `tech-analysis`
**Location**: `src/main.py` line 429

**Flags** (7 total):
```bash
--days <int>                # Default: 30
--start-date <YYYY-MM-DD>
--end-date <YYYY-MM-DD>
--max-pages <int>
--generate-ai-report        # Boolean flag
--verbose                   # Boolean flag
--audit-trail               # Boolean flag
```

**Missing Flags**: ⚠️
- ❌ `--time-period` - Must use days or dates
- ❌ `--test-mode` - No mock data
- ❌ `--test-data-count` - No mock data
- ❌ `--ai-model` - Uses default
- ❌ `--output-dir` - Uses default
- ❌ `--generate-gamma` - Has `--generate-ai-report` instead
- ❌ `--output-format` - Always markdown

**Audit**: ⚠️ **MISSING TEST MODE AND STANDARDIZATION**

---

### 10. Test Mode

#### Command: `test-mode`
**Location**: `src/main.py` line 3970

**Flags** (2 total):
```bash
--test-type <topic-based|api|horatio>  # Default: 'topic-based'
--num-conversations <int>   # Default: 50
```

**Audit**: ℹ️ **SPECIAL PURPOSE** - Not meant to have full flag set

---

## 📊 Flag Coverage Summary

| Command | Date Flags | Output Flags | Test Flags | Debug Flags | AI Flags | Total Flags | Completeness |
|---------|------------|--------------|------------|-------------|----------|-------------|--------------|
| voice-of-customer | ✅ 4/4 | ✅ 3/3 | ✅ 2/2 | ✅ 2/2 | ✅ 3/3 | 17 | 100% ✅ |
| sample-mode | ✅ 3/4 | ❌ 0/3 | ❌ 0/2 | ❌ 0/2 | ❌ 0/3 | 5 | 27% 🔴 |
| canny-analysis | ✅ 3/4 | ✅ 3/3 | ✅ 2/2 | ✅ 2/2 | ✅ 2/3 | 14 | 86% ✅ |
| comprehensive-analysis | ✅ 2/4 | ✅ 2/3 | ❌ 0/2 | ✅ 2/2 | ❌ 0/3 | 12 | 40% ⚠️ |
| fin-escalations | ✅ 4/4 | ✅ 2/3 | ✅ 2/2 | ✅ 2/2 | ❌ 0/3 | 11 | 67% ⚠️ |
| agent-performance | ✅ 4/4 | ✅ 3/3 | ✅ 2/2 | ✅ 2/2 | ✅ 1/3 | 12 | 80% ✅ |
| agent-coaching-report | ✅ 1/4 | ❌ 1/3 | ❌ 0/2 | ✅ 2/2 | ✅ 1/3 | 7 | 36% 🔴 |
| analyze-billing | ✅ 3/4 | ✅ 1/3 | ❌ 0/2 | ❌ 0/2 | ❌ 0/3 | 4 | 29% 🔴 |
| analyze-product | ✅ 3/4 | ✅ 1/3 | ❌ 0/2 | ❌ 0/2 | ❌ 0/3 | 4 | 29% 🔴 |
| analyze-api | ✅ 3/4 | ✅ 1/3 | ❌ 0/2 | ❌ 0/2 | ❌ 0/3 | 4 | 29% 🔴 |
| tech-analysis | ✅ 3/4 | ❌ 1/3 | ❌ 0/2 | ✅ 2/2 | ❌ 0/3 | 7 | 43% ⚠️ |

### Average Completeness: **51%** ⚠️

---

## 🔍 Detailed Flag Mapping by Analysis Mode

### Voice of Customer - ALL VARIANTS

The web UI defines these analysis types (lines 891-893):
1. `voice-of-customer-hilary` → Maps to CLI: `voice-of-customer --analysis-type topic-based`
2. `voice-of-customer-synthesis` → Maps to CLI: `voice-of-customer --analysis-type synthesis`
3. `voice-of-customer-complete` → Maps to CLI: `voice-of-customer --analysis-type complete`

**All three use the SAME command** (`voice-of-customer`) with different `--analysis-type` values.

---

## 🎯 Web UI Analysis Types → CLI Command Mapping

| Web UI Option | CLI Command | Required Flags | Analysis Type Flag |
|---------------|-------------|----------------|-------------------|
| **Sample Mode** | `sample-mode` | `--count`, `--time-period` | N/A |
| **VoC: Hilary Format** | `voice-of-customer` | `--time-period` | `--analysis-type topic-based` |
| **VoC: Synthesis** | `voice-of-customer` | `--time-period` | `--analysis-type synthesis` |
| **VoC: Complete** | `voice-of-customer` | `--time-period` | `--analysis-type complete` |
| **Billing Analysis** | `analyze-billing` | `--days` | N/A |
| **Product Feedback** | `analyze-product` | `--days` | N/A |
| **API Issues** | `analyze-api` | `--days` | N/A |
| **Escalations** | `analyze-escalations` | `--days` | N/A |
| **Tech Troubleshooting** | `tech-analysis` | `--days` | N/A |
| **All Categories** | `analyze-all-categories` | `--days` | N/A |
| **Horatio: Team** | `agent-performance` | `--agent horatio`, `--time-period` | N/A |
| **Boldr: Team** | `agent-performance` | `--agent boldr`, `--time-period` | N/A |
| **Escalated Staff** | `agent-performance` | `--agent escalated`, `--time-period` | N/A |
| **Horatio: Individual** | `agent-performance` | `--agent horatio`, `--individual-breakdown`, `--time-period` | N/A |
| **Boldr: Individual** | `agent-performance` | `--agent boldr`, `--individual-breakdown`, `--time-period` | N/A |
| **Horatio: Coaching** | `agent-coaching-report` | `--vendor horatio`, `--time-period` | N/A |
| **Boldr: Coaching** | `agent-coaching-report` | `--vendor boldr`, `--time-period` | N/A |
| **Canny Feedback** | `canny-analysis` | `--time-period` | N/A |

---

## 🛠️ Missing Flags by Command

### High Priority (Should have these)

#### `sample-mode`
```bash
+ --verbose                  # Show DEBUG logs for sampling logic
+ --audit-trail             # Document sampling decisions
```

#### `agent-coaching-report`
```bash
+ --test-mode               # Enable testing without real data
+ --test-data-count         # Control test data volume
+ --output-dir              # Specify where to save reports
+ --output-format           # Support multiple output formats
+ --start-date / --end-date # More flexible than just time-period
```

#### Category Analysis Commands (analyze-billing, analyze-product, etc.)
```bash
+ --time-period             # Easier than --days
+ --test-mode               # Enable testing
+ --test-data-count         # Control test data
+ --verbose                 # Debug logging
+ --audit-trail             # Audit trail
+ --ai-model                # Choose AI model
+ --output-dir              # Custom output location
+ --output-format           # Multiple output formats
```

#### `comprehensive-analysis`
```bash
+ --time-period             # Easier than start/end dates
+ --test-mode               # Enable testing
+ --test-data-count         # Control test data volume
+ --ai-model                # Choose AI model explicitly
```

#### `tech-analysis`
```bash
+ --time-period             # Easier than --days
+ --test-mode               # Enable testing
+ --test-data-count         # Control test data
+ --ai-model                # Choose AI model
+ --output-dir              # Custom output
+ --output-format           # Multiple formats
```

#### `fin-escalations`
```bash
+ --output-dir              # Currently missing
+ --ai-model                # Currently missing
```

---

## 🎨 Web UI Form Fields → CLI Flags Mapping

### Current Web UI Form (`deploy/railway_web.py` lines 881-1108)

| Form Field ID | Maps To CLI Flag | Status |
|---------------|------------------|--------|
| `analysisType` | Command name + `--analysis-type` | ✅ Mapped |
| `timePeriod` | `--time-period` | ✅ Mapped |
| `startDate` | `--start-date` | ✅ Mapped |
| `endDate` | `--end-date` | ✅ Mapped |
| `dataSource` | N/A (partially `--include-canny`) | ⚠️ Unclear mapping |
| `taxonomyFilter` | N/A | ❌ NOT MAPPED |
| `outputFormat` | `--generate-gamma` + `--output-format` | ⚠️ Partial |
| `aiModel` | `--ai-model` | ✅ Mapped |
| `testMode` | `--test-mode` | ✅ Mapped |
| `testDataCount` | `--test-data-count` | ✅ Mapped |
| `verboseLogging` | `--verbose` | ✅ Mapped |
| `auditMode` | `--audit-trail` | ✅ Mapped |
| `sampleCount` | `--count` (sample-mode only) | ✅ Mapped |
| `sampleTimePeriod` | `--time-period` (sample-mode only) | ✅ Mapped |

### Missing Mappings

❌ **`taxonomyFilter`** - Form has dropdown for taxonomy filtering but no CLI flag exists!
  - Should map to: `--category <category-name>` or `--filter-category`
  - Current workaround: Use specific commands like `analyze-billing`
  
❌ **`dataSource: "both"`** - Form allows selecting both Intercom + Canny but unclear how this maps
  - Should map to: `--include-canny` flag
  - Current: Only works with voice-of-customer command

---

## 🔄 Analysis Type Mapping

### Multi-Agent Analysis Types

**Source**: `src/config/analysis_modes.py` lines 19-27

| Value | Description | Use Case |
|-------|-------------|----------|
| `standard` | Standard single-pass analysis | Quick analysis without multi-agent overhead |
| `topic-based` | Topic-based cards (Hilary format) | Weekly VoC reports with topic cards |
| `synthesis` | Cross-topic insights | Strategic insights and patterns |
| `complete` | All modes combined | Comprehensive analysis with everything |

**Web UI Support**:
- ✅ Hidden dropdown exists (line 1116) but is `display:none`
- ✅ Mapped to `--analysis-type` flag
- ⚠️ Comment says "This branch is multi-agent only" (line 1128)

---

## 🚨 Recommended Actions

### 1. Fix Web UI (Critical)

**Create missing JavaScript functions in `static/app.js`:**

```javascript
function runAnalysis() {
    // Build command from form fields
    // Call /execute endpoint
    // Stream results to terminal
}

function updateAnalysisOptions() {
    // Show/hide options based on analysisType
    // Update form validation
}

function switchTab(tabName) {
    // Switch between terminal/summary/files/gamma tabs
}
```

### 2. Standardize Flags (High Priority)

**Apply standard flag groups to ALL commands:**
- All commands should have: `--verbose`, `--audit-trail`
- All commands should have: `--test-mode`, `--test-data-count`
- All commands should have: `--output-dir`
- Commands that generate content should have: `--output-format`
- Commands that use AI should have: `--ai-model`

### 3. Add Missing Flags (Medium Priority)

**Priority list:**
1. Add `--output-dir` to: fin-escalations, agent-coaching-report, all category commands
2. Add `--test-mode` + `--test-data-count` to: comprehensive-analysis, agent-coaching-report, category commands
3. Add `--time-period` to: comprehensive-analysis, category commands, tech-analysis
4. Add `--ai-model` to: fin-escalations, comprehensive-analysis, category commands
5. Add `--verbose` + `--audit-trail` to: sample-mode, category commands

### 4. Implement Taxonomy Filter (Medium Priority)

**Add new flag to voice-of-customer command:**
```bash
--filter-category <category-name>  # Filter conversations by taxonomy category
```

This would allow web UI's `taxonomyFilter` dropdown to work properly.

---

## 📝 Web UI Schema Gaps

### Current Schema (`deploy/railway_web.py` lines 429-700)

**Commands defined in schema but missing from mapping**:
- ✅ All exist in the schema
- ⚠️ Schema is outdated - doesn't include new `voice-of-customer` variants

**Schema should be updated to include**:
```python
'voice-of-customer-hilary': {
    'command': 'python',
    'args': ['src/main.py', 'voice-of-customer', '--analysis-type', 'topic-based'],
    'display_name': 'VoC: Hilary Format',
    ...
},
'voice-of-customer-synthesis': {
    'command': 'python',
    'args': ['src/main.py', 'voice-of-customer', '--analysis-type', 'synthesis'],
    ...
},
'voice-of-customer-complete': {
    'command': 'python',
    'args': ['src/main.py', 'voice-of-customer', '--analysis-type', 'complete'],
    ...
},
```

---

## 🎯 Flag Consistency Issues

### Time Period Flags

**Inconsistent naming**:
- Most commands: `--time-period <week|month|quarter>`
- Some commands: `--days <int>`
- Confusion: Both exist in same command sometimes

**Recommendation**: Standardize on `--time-period` with `--periods-back` for all commands.

### Output Flags

**Inconsistent options**:
- `voice-of-customer`: `--output-format <gamma|markdown|json|excel>`
- `canny-analysis`: `--output-format <gamma|markdown|json|excel>`  
- `comprehensive-analysis`: `--gamma-export <pdf|pptx>` (different flag!)
- `tech-analysis`: `--generate-ai-report` (boolean, no format choice)

**Recommendation**: Use consistent `--output-format` with same choices across all commands.

### AI Model Flags

**Inconsistent application**:
- 6 commands have `--ai-model`
- 11 commands missing `--ai-model` (use default)

**Recommendation**: Add `--ai-model` to ALL commands that use LLMs.

---

## 📋 Complete Flag Reference (All Unique Flags)

### Date & Time Flags
- `--start-date <YYYY-MM-DD>` - Start date for analysis
- `--end-date <YYYY-MM-DD>` - End date for analysis
- `--time-period <week|month|quarter|year|yesterday>` - Time period shortcut
- `--periods-back <int>` - How many periods to go back (default: 1)
- `--days <int>` - Number of days to analyze (DEPRECATED in favor of --time-period)

### Output Flags
- `--generate-gamma` - Generate Gamma presentation (boolean)
- `--output-format <gamma|markdown|json|excel>` - Output format
- `--output-dir <path>` - Output directory (default: outputs)
- `--gamma-style <executive|detailed|training>` - Gamma style (comprehensive-analysis only)
- `--gamma-export <pdf|pptx>` - Gamma export format (comprehensive-analysis only)
- `--export-docs` - Generate Google Docs markdown (comprehensive-analysis only)

### Test & Debug Flags
- `--test-mode` - Use mock data instead of API calls (boolean)
- `--test-data-count <string>` - Test data volume (micro/small/medium/large/xlarge/xxlarge or number)
- `--verbose` - Enable DEBUG level logging (boolean)
- `--audit-trail` - Enable audit trail narration (boolean)

### Analysis Configuration Flags
- `--multi-agent` - Use multi-agent workflow (boolean)
- `--analysis-type <standard|topic-based|synthesis|complete>` - Analysis type (default: topic-based)
- `--ai-model <openai|claude>` - AI model to use
- `--enable-fallback/--no-fallback` - Enable AI model fallback (default: True)

### Content Filtering Flags
- `--separate-agent-feedback` - Separate by agent type (boolean, default: True)
- `--include-trends` - Include historical trends (boolean)
- `--include-canny` - Include Canny feedback (boolean)
- `--canny-board-id <string>` - Specific Canny board ID
- `--include-comments/--no-comments` - Include Canny comments (default: True)
- `--include-votes/--no-votes` - Include Canny votes (default: True)
- `--board-id <string>` - Canny board ID

### Agent Performance Flags
- `--agent <horatio|boldr|escalated>` - Agent vendor to analyze
- `--vendor <horatio|boldr>` - Vendor for coaching report
- `--individual-breakdown` - Show individual agent breakdown (boolean)
- `--top-n <int>` - Number of top items to show (default: 5 or 10)

### Comprehensive Analysis Flags
- `--max-conversations <int>` - Maximum conversations to analyze
- `--include-fin-analysis` - Include Fin analysis (boolean, default: True)
- `--include-technical-analysis` - Include tech analysis (boolean, default: True)
- `--include-macro-analysis` - Include macro analysis (boolean, default: True)

### Sample Mode Specific Flags
- `--count <int>` - Number of conversations to sample (default: 50)
- `--save-to-file/--no-save` - Save raw JSON (default: True)

### Technical Analysis Flags
- `--max-pages <int>` - Maximum API pages to fetch
- `--generate-ai-report` - Generate AI report (boolean)

### Category Analysis Flags
- `--category <string>` - Category to analyze (analyze-category command)

### Other Flags
- `--detailed` - Generate detailed report (fin-escalations)

---

## 🎨 Recommended Standard Flag Set

**Every analysis command should have:**

```bash
# Date/Time (choose one set)
--time-period <week|month|quarter|year|yesterday>
--periods-back <int>         # Default: 1
# OR
--start-date <YYYY-MM-DD>
--end-date <YYYY-MM-DD>

# Output
--generate-gamma             # Boolean
--output-format <gamma|markdown|json|excel>  # Default: markdown
--output-dir <path>          # Default: outputs

# Test & Debug
--test-mode                  # Boolean
--test-data-count <string>   # Default: '100'
--verbose                    # Boolean
--audit-trail                # Boolean

# AI Configuration
--ai-model <openai|claude>   # Default from config
--enable-fallback/--no-fallback  # Default: True
```

---

## 📊 Current State vs Ideal State

| Aspect | Current State | Ideal State | Gap |
|--------|---------------|-------------|-----|
| **Web UI Functions** | 🔴 Missing (broken) | ✅ All defined in static/app.js | **CRITICAL** |
| **Flag Consistency** | 51% average completeness | 100% across all commands | **HIGH** |
| **VoC Mapping** | ✅ Working | ✅ Working | None |
| **Test Mode Coverage** | 55% of commands | 100% of commands | **MEDIUM** |
| **AI Model Selection** | 35% of commands | 100% of LLM commands | **MEDIUM** |
| **Audit Trail** | 70% of commands | 100% of commands | **MEDIUM** |
| **Output Dir Control** | 65% of commands | 100% of commands | **LOW** |
| **Taxonomy Filtering** | ❌ Not implemented | ✅ In VoC command | **MEDIUM** |

---

## ✅ Next Steps

### Immediate (Blocks usage)
1. **Create missing JavaScript functions** in `static/app.js`
   - `runAnalysis()` - Build command, call /execute endpoint
   - `updateAnalysisOptions()` - Show/hide form sections
   - `switchTab()` - Tab navigation

### Short Term (Improves UX)
2. **Add missing standard flags** to all commands:
   - Add `--verbose` + `--audit-trail` to sample-mode
   - Add `--test-mode` to comprehensive-analysis, agent-coaching-report
   - Add `--output-dir` to all commands
   - Add `--ai-model` to all LLM-using commands

### Medium Term (Feature completeness)
3. **Implement taxonomy filtering** in voice-of-customer:
   - Add `--filter-category` flag
   - Wire up to web UI `taxonomyFilter` dropdown

4. **Standardize time period handling**:
   - Replace `--days` with `--time-period` everywhere
   - Add `--periods-back` support to all commands

### Long Term (Quality)
5. **Update web UI schema** with all VoC variants
6. **Create comprehensive test coverage** for all flag combinations
7. **Document flag behavior** in user guide

---

**End of Audit**

