# Feature Flags - Control New Features

**Purpose:** Toggle new features on/off without code changes

---

## Available Flags

### USE_DUAL_FIN_METRICS (Default: False)

**What it does:** Shows both Intercom-compatible and Quality-adjusted Fin metrics

**When enabled:**
```
Fin Performance:
├─ Intercom-Compatible: 74% deflection (matches Intercom reports)
├─ Quality-Adjusted: 23% resolution (strict "truly helpful" criteria)
└─ Gap Analysis: 51% stopped responding but may not be satisfied
```

**When disabled (default):**
```
Fin Performance:
└─ Resolution: 23% (current strict criteria only)
```

**How to enable:**

Add to your `.env` file:
```bash
USE_DUAL_FIN_METRICS=true
```

Or set environment variable before running:
```bash
export USE_DUAL_FIN_METRICS=true
```

**Why you might want this:**
- ✅ Validate against Intercom's native reports
- ✅ Explain why numbers differ (methodology transparency)
- ✅ Show where Fin deflected vs truly helped
- ✅ Stakeholder clarity

**Why you might not:**
- Adds complexity to reports
- Two numbers might confuse non-technical readers
- Current single metric is simpler

---

## How to Add More Flags

In `src/config/settings.py`:
```python
# Feature Flags
use_new_feature: bool = Field(False, env="USE_NEW_FEATURE")
```

In `.env`:
```bash
USE_NEW_FEATURE=true
```

In code:
```python
from src.config.settings import settings

if settings.use_dual_fin_metrics:
    # New behavior
else:
    # Current behavior
```

---

## Current Flags

| Flag | Default | Purpose |
|------|---------|---------|
| `USE_DUAL_FIN_METRICS` | `False` | Show Intercom-compatible + Quality metrics |

---

**Note:** All flags default to `False` to maintain current behavior.
New features are opt-in, not forced.

