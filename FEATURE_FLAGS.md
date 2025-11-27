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

### enable_canny (Default: True)

**What it does:** Controls whether Canny feature request integration is enabled

**When enabled (default):**
- Phase 2.6: Maps Canny posts to taxonomy categories
- Phase 4.6: Analyzes correlations between Intercom issues and Canny requests
- Provides unified priority recommendations combining support volume + feature votes

**When disabled:**
- Skips all Canny-related analysis phases
- Reduces analysis time and LLM costs
- Use when Canny data is not available or not relevant

**How to configure:**

In `config/analysis_modes.yaml`:
```yaml
features:
  enable_canny: false  # Disable Canny integration
```

**Why you might disable this:**
- ✅ No Canny account or feature request data
- ✅ Reduce analysis cost (saves 2 LLM calls per run)
- ✅ Faster analysis when cross-platform insights not needed
- ✅ Simplify reports for teams not using Canny

**Why you might keep it enabled:**
- Unified view of support issues + feature demand
- Identify which features would reduce support volume
- Prioritize roadmap based on actual customer pain
- Gracefully skips if no Canny data provided

### Phase 4.5 Insight Agent Flags (Defaults: True)

The TopicOrchestrator now exposes fine-grained toggles for the analytical insight agents executed during Phase 4.5. Each flag can be controlled via `config/analysis_modes.yaml`, CLI (`--enable-*` / `--disable-*`), or the Railway/Web UI checkboxes.

| Flag | Purpose | When to disable |
|------|---------|-----------------|
| `enable_correlation_analysis` | Runs `CorrelationAgent` (tier/topic vs CSAT/reopen correlations) | When you only need per-topic stories without cross-metric overlays |
| `enable_quality_insights` | Runs `QualityInsightsAgent` (FCR/reopen anomalies, exceptional convos) | When FCR data is sparse or you're running a quick volume-only pass |
| `enable_churn_detection` | Runs `ChurnRiskAgent` (high-risk accounts + signals) | When you already have a churn watchlist and want to save LLM calls |
| `enable_confidence_meta` | Runs `ConfidenceMetaAgent` (data coverage + limitations) | When prototyping and you don't need confidence narratives |

**Configuration example:**
```yaml
features:
  enable_correlation_analysis: true
  enable_quality_insights: true
  enable_churn_detection: true
  enable_confidence_meta: true
```

**CLI / UI usage:**
```
python src/main.py voice-of-customer --disable-churn-detection
python src/main.py voice-of-customer --enable-quality-insights
```
The Railway/Web UI exposes matching checkboxes (Phase 4.5 Insight Agents) so PMs can experiment without touching YAML.

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
| `enable_canny` | `True` | Enable Canny feature request integration |
| `enable_correlation_analysis` | `True` | Run Phase 4.5 `CorrelationAgent` |
| `enable_quality_insights` | `True` | Run Phase 4.5 `QualityInsightsAgent` |
| `enable_churn_detection` | `True` | Run Phase 4.5 `ChurnRiskAgent` |
| `enable_confidence_meta` | `True` | Run Phase 4.5 `ConfidenceMetaAgent` |

---

**Note:** All flags default to `False` to maintain current behavior.
New features are opt-in, not forced.

