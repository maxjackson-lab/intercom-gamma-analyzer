# Agent Output Visibility Implementation

## Overview
This document describes the implementation of agent output visibility features that provide real-time insights into multi-agent analysis workflows and Gamma API calls.

## Implementation Date
October 24, 2025

## Features Implemented

### 1. **Agent Output Display Module** (`src/utils/agent_output_display.py`)
A comprehensive display system using the `rich` library for beautiful terminal formatting.

**Key Components:**
- `AgentOutputDisplay` class: Main display handler
- Individual display methods for different output types
- Configurable enable/disable via feature flags
- Global singleton pattern for easy access

**Display Methods:**
- `display_agent_result()`: Shows agent execution results with:
  - Success/failure status with emoji indicators
  - Confidence score with color coding (green ≥90%, yellow ≥70%, red <70%)
  - Execution time
  - Token usage (when available)
  - Error messages (on failure)
  - Limitations warnings
  - Data summary tailored to agent type
  - Optional full data output (JSON syntax highlighted)

- `display_markdown_preview()`: Shows formatted markdown report with:
  - Rich markdown rendering
  - Configurable line truncation
  - Line count summary

- `display_gamma_api_call()`: Shows Gamma API call details with:
  - Endpoint information
  - Parameters table
  - Input text statistics (lines, words, characters)
  - Optional full input text preview

- `display_all_agent_results()`: Summary table with:
  - All agent statuses
  - Confidence scores
  - Execution times
  - Token counts

### 2. **Feature Flags** (`config/analysis_modes.yaml`)
Fine-grained control over display behavior:

```yaml
features:
  # Agent Output Visibility Settings
  enable_agent_output_display: true          # Master switch
  show_full_agent_data: false                # Show full JSON vs summary
  show_markdown_preview: true                # Preview formatted report
  markdown_preview_max_lines: 50             # Lines to show (null = all)
  show_full_gamma_input: false               # Show full Gamma input text
  show_agent_summary_table: true             # Show final summary table
```

### 3. **Configuration Integration** (`src/config/modes.py`)
Added `get_visibility_setting()` method to `AnalysisModeConfig`:
- Reads visibility settings from config
- Provides defaults
- Supports environment variable overrides

### 4. **TopicOrchestrator Integration** (`src/agents/topic_orchestrator.py`)
Updated to display agent outputs in real-time:

**Display Points:**
1. After SegmentationAgent execution
2. After TopicDetectionAgent execution  
3. After FinPerformanceAgent execution
4. After TrendAgent execution
5. After OutputFormatterAgent execution
6. Summary table at workflow completion
7. Markdown preview before Gamma generation

### 5. **Gamma Generator Integration** (`src/services/gamma_generator.py`)
Added Gamma API call preview before sending:
- Shows all API parameters
- Displays input text statistics
- Optionally shows full markdown content
- Respects feature flags

## Display Examples

### Agent Result Display
```
╭─────────────────── ✅ SegmentationAgent Result ────────────────────╮
│ Status: Success                                                     │
│ Confidence: 95.5% (HIGH)                                           │
│ Execution Time: 2.34s                                              │
│                                                                     │
│ Data Summary:                                                       │
│   • Paid: 150 (65.2%)                                             │
│   • Free: 80 (34.8%)                                              │
│   • Tier breakdown: {'free': 80, 'pro': 120, 'plus': 30}        │
╰────────────────────────────────────────────────────────────────────╯
```

### Gamma API Call Display
```
╭─────────────────────── 🚀 Gamma API Call ──────────────────────────╮
│ Endpoint: /api/generate                                             │
│                                                                     │
│ Parameters:                                                         │
│   format              presentation                                  │
│   num_cards           10                                           │
│   text_mode           generate                                     │
│   theme_name          stockholm                                    │
│                                                                     │
│ Input Text Statistics:                                             │
│   Lines               245                                          │
│   Words               3,421                                        │
│   Characters          21,456                                       │
╰────────────────────────────────────────────────────────────────────╯
```

### Summary Table
```
                    Analysis Complete - 2024-W42
┌──────────────────────┬────────┬────────────┬──────────┬─────────┐
│ Agent                │ Status │ Confidence │ Time (s) │  Tokens │
├──────────────────────┼────────┼────────────┼──────────┼─────────┤
│ SegmentationAgent    │   ✅   │   95.5%    │   2.34   │       - │
│ TopicDetectionAgent  │   ✅   │   88.2%    │  12.45   │   2,341 │
│ FinPerformanceAgent  │   ✅   │   92.0%    │   8.67   │   1,823 │
│ TrendAgent           │   ✅   │   85.4%    │   5.23   │   1,456 │
│ OutputFormatterAgent │   ✅   │   98.1%    │   3.12   │     892 │
└──────────────────────┴────────┴────────────┴──────────┴─────────┘
```

## Usage

### Default Behavior
The visibility features are **enabled by default** but can be controlled via configuration.

### Disabling Display
1. **Via Configuration File:**
   ```yaml
   # config/analysis_modes.yaml
   features:
     enable_agent_output_display: false
   ```

2. **Programmatically:**
   ```python
   from src.utils.agent_output_display import set_display_enabled
   set_display_enabled(False)
   ```

3. **Via Environment Variable:**
   ```bash
   export ENABLE_AGENT_OUTPUT_DISPLAY=false
   ```

### Customizing Display
Adjust individual settings in `config/analysis_modes.yaml`:

```yaml
features:
  # Show everything
  enable_agent_output_display: true
  show_full_agent_data: true
  show_markdown_preview: true
  markdown_preview_max_lines: null  # Show all lines
  show_full_gamma_input: true
  show_agent_summary_table: true
```

## Benefits

### 1. **Transparency**
- See exactly what each agent produces
- Understand data transformations
- Verify agent behavior

### 2. **Debugging**
- Quickly identify which agent fails
- See error messages immediately
- Understand confidence levels

### 3. **Monitoring**
- Track execution times
- Monitor token usage
- Assess analysis quality

### 4. **Quality Assurance**
- Preview markdown before sending to Gamma
- Verify API call parameters
- Catch issues early

### 5. **User Experience**
- Beautiful, readable terminal output
- Progress visibility during long analyses
- Professional presentation

## Technical Details

### Dependencies
- **rich**: Terminal formatting library (≥13.0.0)
  - Already included in `requirements.txt`
  - No additional dependencies needed

### Performance Impact
- **Minimal**: Display operations are fast
- **Non-blocking**: Doesn't slow down analysis
- **Optional**: Can be disabled entirely
- **Memory efficient**: No data duplication

### Thread Safety
- Uses global singleton pattern
- Safe for concurrent access
- Display operations are atomic

## Rollback Plan
If you need to disable or remove the feature:

1. **Disable via config:**
   ```yaml
   features:
     enable_agent_output_display: false
   ```

2. **Remove display calls:**
   - Comment out `display.display_agent_result()` calls
   - Comment out `display.display_gamma_api_call()` calls
   - No breaking changes to existing functionality

3. **Remove module** (optional):
   - Delete `src/utils/agent_output_display.py`
   - Remove imports from orchestrators and services

## Future Enhancements

Potential improvements:
1. **Export to HTML**: Save formatted output to HTML files
2. **JSON Export**: Export structured agent results
3. **Dashboard Integration**: Real-time web dashboard
4. **Slack/Discord Notifications**: Send summaries to team channels
5. **Custom Themes**: User-defined color schemes
6. **Log File Integration**: Append to structured logs
7. **Progress Bars**: Visual progress for long-running agents
8. **Interactive Mode**: Pause/inspect/continue workflow

## Testing

To test the implementation:

```bash
# Run a topic-based analysis and observe the output
python -m src.main topic-based --start-date 2024-10-17 --end-date 2024-10-24

# Or run with Gamma generation
python -m src.main topic-based --start-date 2024-10-17 --end-date 2024-10-24 --generate-gamma
```

Expected output:
1. Individual agent result panels as each agent completes
2. Summary table after all agents finish
3. Markdown preview before Gamma generation
4. Gamma API call details before submission

## Files Modified

1. **New Files:**
   - `src/utils/agent_output_display.py` (380 lines)

2. **Modified Files:**
   - `config/analysis_modes.yaml` (added visibility settings)
   - `src/config/modes.py` (added `get_visibility_setting()`)
   - `src/agents/topic_orchestrator.py` (added display calls)
   - `src/services/gamma_generator.py` (added Gamma preview)

## Summary

This implementation provides comprehensive visibility into multi-agent analysis workflows with:
- ✅ Beautiful terminal formatting via `rich`
- ✅ Configurable via feature flags
- ✅ Zero breaking changes
- ✅ Easy rollback
- ✅ Minimal performance impact
- ✅ Production-ready

The feature is **ready for use** and can be toggled on/off as needed.

