# Validation & Configuration Audit Report

**Date:** October 27, 2025  
**Purpose:** Identify all duplicated validation, schemas, enums, and config values across codebase

---

## 🔍 Findings: Configuration Duplication

### 1. **Test Data Count Validation**

**Duplicated in 5 locations:**

| File | Line(s) | Type | Max Value |
|------|---------|------|-----------|
| `src/main.py` | 64, 416, 3668, 4088 | CLI help text | N/A (text) |
| `src/main.py` | 436, 3713, 4024, 4127 | Preset dict | N/A (presets) |
| `deploy/railway_web.py` | 324, 396, 449 | Schema validation | 25000 |
| `src/services/web_command_executor.py` | 84 | Schema validation | 25000 |
| `static/app.js` | (dropdown) | UI options | N/A |

**Presets defined 4 times:**
```python
# All 4 locations have:
'micro': 100, 'small': 500, 'medium': 1000, 
'large': 5000, 'xlarge': 10000, 'xxlarge': 20000
```

**Problem:** If you want to add "xxxlarge: 50000", you'd have to update 9+ places!

---

### 2. **Time Period Options**

**Duplicated in 3+ locations:**

| File | Location | Values |
|------|----------|--------|
| `src/main.py` | Multiple `@click.option` | `['week', 'month', 'quarter']` |
| `deploy/railway_web.py` | Schema | `['yesterday', 'week', 'month', 'quarter', 'year']` |
| `src/services/web_command_executor.py` | Schema | `['yesterday', 'week', 'month', 'quarter', 'year']` |

**Inconsistency:** CLI supports 3 options, Web UI supports 5!

---

### 3. **Agent Type Enums**

**Duplicated in 6+ locations:**

| File | Location | Values |
|------|----------|--------|
| `src/main.py` | `@click.option('--agent')` | `['horatio', 'boldr', 'escalated']` |
| `deploy/railway_web.py` | Schema | `['horatio', 'boldr', 'escalated']` |
| `src/services/web_command_executor.py` | Schema | `['horatio', 'boldr', 'escalated']` |
| `src/agents/segmentation_agent.py` | Agent detection logic | Hardcoded strings |
| `src/services/admin_profile_cache.py` | Agent lookups | Hardcoded strings |
| `src/services/test_data_generator.py` | Test data generation | Hardcoded strings |

**Problem:** If you add "tier1_eu" agent type, you'd update 6+ files!

---

### 4. **Analysis Type Enums**

**Duplicated in 3 locations:**

| File | Location | Values |
|------|----------|--------|
| `src/main.py` | CLI | `['standard', 'topic-based', 'synthesis', 'complete']` |
| `deploy/railway_web.py` | Schema | `['topic-based', 'synthesis', 'complete']` |
| `src/services/web_command_executor.py` | Schema | `['topic-based', 'synthesis', 'complete']` |

**Inconsistency:** CLI has 4 options, Web has 3!

---

### 5. **Output Format Options**

**Duplicated in 3+ locations:**

| File | Values |
|------|--------|
| `src/main.py` | `['gamma', 'markdown', 'json', 'excel']` |
| `src/services/web_command_executor.py` | `['json', 'csv', 'markdown']` |

**Inconsistency:** Different options in different places!

---

### 6. **Vendor Type Enums**

**Duplicated in 3 locations:**

| File | Values |
|------|--------|
| `src/main.py` | `['horatio', 'boldr']` |
| `deploy/railway_web.py` | `['horatio', 'boldr']` |
| `src/services/web_command_executor.py` | `['horatio', 'boldr']` |

---

### 7. **AI Model Options**

**Duplicated in 3 locations:**

| File | Values |
|------|--------|
| `src/main.py` | `['openai', 'claude']` |
| Config files | Probably elsewhere? |

---

### 8. **Category/Taxonomy Enums**

**Found in:**
- `src/services/web_command_executor.py` - 13 hardcoded categories
- `src/agents/topic_detection_agent.py` - Probably different list?
- Various topic files - Probably more lists?

---

## 🚨 Critical Issues Identified

### **Issue 1: No Single Source of Truth**
Every enum/limit is defined inline where it's used. Changes require hunting through files.

### **Issue 2: Inconsistent Values**
- Time periods: CLI has 3, Web has 5
- Analysis types: CLI has 4, Web has 3
- Output formats: Different in CLI vs Web

### **Issue 3: No Validation Tests**
If schemas get out of sync, there's no automated way to catch it.

### **Issue 4: Magic Strings Everywhere**
`'horatio'`, `'boldr'`, `'topic-based'` hardcoded hundreds of times.

### **Issue 5: Documentation Lags Behind**
Multiple .md files have outdated values.

---

## 💡 Solution: Central Configuration

### **Proposed Structure:**

```
src/config/
├── __init__.py
├── validation_schemas.py    # All enums, limits, presets
├── test_data_config.py      # Test data presets and limits
├── agent_types.py           # Agent/vendor enums
├── analysis_modes.py        # Analysis type enums
└── shared_constants.py      # Shared constants
```

### **Example: `test_data_config.py`**

```python
"""
Centralized test data configuration.
Single source of truth for all test data limits and presets.
"""

TEST_DATA_LIMITS = {
    'min': 10,
    'max': 25000,
    'default': 100
}

TEST_DATA_PRESETS = {
    'micro': 100,       # 1 hour
    'small': 500,       # Few hours
    'medium': 1000,     # ~1 day
    'large': 5000,      # ~1 week
    'xlarge': 10000,    # 2 weeks
    'xxlarge': 20000    # 1 month
}

def get_preset_value(name: str) -> int:
    """Get test data count for a preset name."""
    return TEST_DATA_PRESETS.get(name.lower(), TEST_DATA_LIMITS['default'])

def validate_test_data_count(value: int) -> bool:
    """Validate test data count is within limits."""
    return TEST_DATA_LIMITS['min'] <= value <= TEST_DATA_LIMITS['max']
```

### **Example: `agent_types.py`**

```python
"""
Centralized agent type definitions.
"""

AGENT_TYPES = ['horatio', 'boldr', 'escalated']
VENDOR_TYPES = ['horatio', 'boldr']

# For CLI
AGENT_CHOICE_CLI = AGENT_TYPES
VENDOR_CHOICE_CLI = VENDOR_TYPES

# For schemas
AGENT_CHOICE_SCHEMA = {'type': 'enum', 'values': AGENT_TYPES}
VENDOR_CHOICE_SCHEMA = {'type': 'enum', 'values': VENDOR_TYPES}

# Human-readable names
AGENT_DISPLAY_NAMES = {
    'horatio': 'Horatio',
    'boldr': 'Boldr',
    'escalated': 'Senior Staff'
}
```

---

## 📋 Refactoring Checklist

### **Phase 2: Create Config Files**
- [ ] `src/config/test_data_config.py`
- [ ] `src/config/agent_types.py`
- [ ] `src/config/analysis_modes.py`
- [ ] `src/config/time_periods.py`
- [ ] `src/config/output_formats.py`
- [ ] `src/config/validation_schemas.py` (aggregates all)

### **Phase 3: Refactor Code to Use Configs**
- [ ] Update `src/main.py` CLI options (8 locations)
- [ ] Update `deploy/railway_web.py` schemas (3 schemas × many fields)
- [ ] Update `src/services/web_command_executor.py` schemas
- [ ] Update `static/app.js` dropdowns (if possible)
- [ ] Update agent detection logic
- [ ] Update test data generator

### **Phase 4: Add Validation Tests**
- [ ] Test CLI accepts all configured values
- [ ] Test Web UI schemas match CLI
- [ ] Test presets all work end-to-end
- [ ] Test schema validation catches invalid values
- [ ] Integration test: UI → Backend → CLI consistency

---

## 🎯 Expected Outcomes

### **Before (Current State):**
- 9+ places to update for test data changes
- 6+ places to update for agent type changes
- Inconsistent values between CLI and Web
- No way to catch mismatches automatically

### **After (Centralized):**
- 1 place to update for test data changes
- 1 place to update for agent type changes
- Guaranteed consistency (import from same source)
- Tests catch mismatches before deployment

---

## 📊 Impact Analysis

### **Files That Will Change:**
- Core: 3 files (`main.py`, `railway_web.py`, `web_command_executor.py`)
- Agents: 2+ files (segmentation, test generator)
- New: 6 config files (created)
- Tests: 3-5 new test files

### **Time Estimate:**
- Phase 2 (Create configs): 30 minutes
- Phase 3 (Refactor): 1 hour
- Phase 4 (Tests): 30 minutes
- **Total: ~2 hours**

### **Risk:**
- Low: Changes are mechanical (find/replace with imports)
- Can be done incrementally
- Tests will verify correctness

---

## 🚀 Next Steps

1. **Review this audit** - Confirm findings match your experience
2. **Create config files** - Single source of truth
3. **Refactor systematically** - File by file
4. **Add tests** - Prevent regression
5. **Update docs** - Keep in sync

**Expected Result:** No more chasing validation bugs!

