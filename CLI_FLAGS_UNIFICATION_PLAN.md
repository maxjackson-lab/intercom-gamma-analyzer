# CLI Flags Unification Plan

**Goal:** All CLI flags work consistently across all modes and map properly

## Current State Analysis

### Commands and Their Flags

| Command | Flags | Status |
|---------|-------|--------|
| `voice-of-customer` | `--test-mode`, `--test-data-count`, `--verbose`, `--audit-trail`, `--generate-gamma`, `--multi-agent`, `--analysis-type`, `--ai-model` | ✅ Complete |
| `agent-performance` | `--test-mode`, `--test-data-count`, `--verbose`, `--audit-trail`, `--generate-gamma` | ⚠️ Partial |
| `fin-escalations` | `--detailed` | ❌ Minimal |
| `canny-analysis` | None shown | ❌ Minimal |
| `analyze-category` | `--output-format` | ❌ Minimal |
| Other analysis commands | Varied | ❌ Inconsistent |

---

## Core Flag Set (Should Be Universal)

### Analysis Control Flags
```
--start-date DATE              Start date for analysis (YYYY-MM-DD)
--end-date DATE                End date for analysis (YYYY-MM-DD)
--time-period {week|month|quarter}
                               Shortcut for date ranges
```

### Output Control Flags
```
--generate-gamma              Generate Gamma presentation output
--output-format {gamma|markdown|json|excel|csv}
                             Output format for results
--output-dir PATH             Directory for output files
```

### Testing Flags
```
--test-mode                   Use mock data instead of API calls
--test-data-count {preset|number}
                             Data volume: micro(100), small(500), 
                             medium(1000), large(5000), xlarge(10000)
```

### Debugging Flags
```
--verbose                     Enable DEBUG level logging
--audit-trail                 Enable audit trail narration
--dry-run                     Show what would be done without executing
```

### Analysis Mode Flags
```
--multi-agent                 Use multi-agent analysis workflow
--analysis-type {standard|topic-based|synthesis|complete}
                             Type of analysis to perform
--ai-model {openai|claude}   AI model to use for analysis
```

---

## Implementation Plan

### Phase 1: Define Base Command Group (Day 1)

**File:** `src/main.py`

Create decorator groups for reusable flag sets:

```python
# Base flags used everywhere
DEFAULT_FLAGS = [
    click.option('--start-date', help='Start date (YYYY-MM-DD)'),
    click.option('--end-date', help='End date (YYYY-MM-DD)'),
    click.option('--time-period', 
                 type=click.Choice(['week', 'month', 'quarter']),
                 help='Time period shortcut'),
]

OUTPUT_FLAGS = [
    click.option('--generate-gamma', is_flag=True, 
                 help='Generate Gamma presentation'),
    click.option('--output-format', 
                 type=click.Choice(['gamma', 'markdown', 'json', 'excel']),
                 default='markdown'),
    click.option('--output-dir', default='outputs'),
]

TEST_FLAGS = [
    click.option('--test-mode', is_flag=True, 
                 help='Use mock data'),
    click.option('--test-data-count', type=str, default='100',
                 help='Data volume or preset'),
]

DEBUG_FLAGS = [
    click.option('--verbose', is_flag=True, 
                 help='Enable DEBUG logging'),
    click.option('--audit-trail', is_flag=True,
                 help='Enable audit trail'),
]

ANALYSIS_FLAGS = [
    click.option('--multi-agent', is_flag=True,
                 help='Use multi-agent workflow'),
    click.option('--analysis-type',
                 type=click.Choice(['standard', 'topic-based', 'synthesis']),
                 default='topic-based'),
    click.option('--ai-model',
                 type=click.Choice(['openai', 'claude']),
                 default=None),
]
```

### Phase 2: Apply to All Analysis Commands (Day 2)

Apply flags uniformly:

```python
@cli.command(name='voice-of-customer')
@apply_flags(DEFAULT_FLAGS + OUTPUT_FLAGS + TEST_FLAGS + DEBUG_FLAGS + ANALYSIS_FLAGS)
def voice_of_customer_analysis(...):
    ...

@cli.command(name='agent-performance')
@apply_flags(DEFAULT_FLAGS + OUTPUT_FLAGS + TEST_FLAGS + DEBUG_FLAGS + ANALYSIS_FLAGS)
def agent_performance(...):
    ...

@cli.command(name='fin-escalations')
@apply_flags(DEFAULT_FLAGS + OUTPUT_FLAGS + TEST_FLAGS + DEBUG_FLAGS)
def fin_escalations(...):
    ...

@cli.command(name='canny-analysis')
@apply_flags(DEFAULT_FLAGS + OUTPUT_FLAGS + TEST_FLAGS + DEBUG_FLAGS + ANALYSIS_FLAGS)
def canny_analysis(...):
    ...
```

### Phase 3: Standardize Handling in Each Command (Day 3)

Each command processes flags the same way:

```python
async def handle_analysis_command(
    start_date: Optional[str],
    end_date: Optional[str],
    time_period: Optional[str],
    test_mode: bool,
    test_data_count: str,
    verbose: bool,
    audit_trail: bool,
    ai_model: Optional[str],
    generate_gamma: bool,
    output_format: str,
    output_dir: str,
    **kwargs
):
    """Unified handler for all analysis flags"""
    
    # 1. Parse dates
    start_dt, end_dt = parse_date_range(start_date, end_date, time_period)
    
    # 2. Parse test data count (presets or numbers)
    data_count = parse_test_data_count(test_data_count)
    
    # 3. Setup logging
    if verbose:
        setup_debug_logging()
    
    # 4. Setup audit trail
    audit = AuditTrail() if audit_trail else None
    
    # 5. Set AI model
    if ai_model:
        os.environ['AI_MODEL'] = ai_model
    
    # 6. Fetch or generate data
    if test_mode:
        data = generate_test_data(data_count, start_dt, end_dt)
    else:
        data = fetch_real_data(start_dt, end_dt)
    
    # 7. Run analysis (specific to command)
    results = await run_analysis(data, **kwargs)
    
    # 8. Output results
    output_results(results, output_format, output_dir, generate_gamma)
```

---

## Flag Mapping Reference

### voice-of-customer → agent-performance

| Flag | voice-of-customer | agent-performance | Behavior |
|------|-------------------|-------------------|----------|
| `--start-date` | ✅ | ✅ | Start date for analysis window |
| `--end-date` | ✅ | ✅ | End date for analysis window |
| `--time-period` | ✅ | ✅ | Shortcut (week/month/quarter) |
| `--test-mode` | ✅ | ✅ | Use mock data |
| `--test-data-count` | ✅ | ✅ | Data volume (presets or number) |
| `--verbose` | ✅ | ✅ | DEBUG logging |
| `--audit-trail` | ✅ | ✅ | Audit narration |
| `--generate-gamma` | ✅ | ✅ | Gamma output |
| `--output-format` | ✅ | ✅ | Output format |
| `--output-dir` | ✅ | ✅ | Output location |
| `--multi-agent` | ✅ | ✅ | Multi-agent workflow |
| `--analysis-type` | ✅ | ✅ | Analysis type |
| `--ai-model` | ✅ | ✅ | OpenAI or Claude |

---

## Commands That Need Updates

### Priority 1: High-Impact (Analysis Commands)
- [ ] `agent-performance` - Add missing flags
- [ ] `canny-analysis` - Add all core flags
- [ ] `fin-escalations` - Add test/debug flags

### Priority 2: Medium-Impact
- [ ] `analyze-category` - Add output/test flags
- [ ] `analyze-all-categories` - Add output/test flags
- [ ] `fin-escalations` - Add multi-agent support

### Priority 3: Nice-to-Have
- [ ] `analyze-billing`, `analyze-product`, etc. - Add output flags
- [ ] All export commands - Add test-mode

---

## Testing Strategy

### Test Matrix
```bash
# For each command, test these combinations:
1. With real data + all output formats
2. With test-mode=micro
3. With test-mode=large
4. With verbose flag
5. With audit-trail flag
6. With generate-gamma
7. Combinations: test-mode + verbose + audit-trail + generate-gamma
```

### Validation Script
```bash
#!/bin/bash
commands=(
  "voice-of-customer"
  "agent-performance"
  "fin-escalations"
  "canny-analysis"
  "analyze-category"
)

for cmd in "${commands[@]}"; do
  echo "Testing: $cmd"
  python src/main.py $cmd --help | grep -E "(--test-mode|--verbose|--audit-trail|--generate-gamma)" || echo "  Missing flags!"
done
```

---

## Documentation Requirements

### For Each Command
1. List available flags
2. Show flag combinations
3. Example commands
4. Expected outputs

### For Users
1. Flag reference guide
2. Mode selection flowchart
3. FAQ for common flag combinations
4. Troubleshooting guide

---

## Implementation Checklist

- [ ] Define flag groups in src/main.py
- [ ] Create `parse_test_data_count()` helper
- [ ] Create `parse_date_range()` helper
- [ ] Create `handle_analysis_command()` unified handler
- [ ] Update voice-of-customer to use unified handler
- [ ] Update agent-performance to use unified handler
- [ ] Update fin-escalations to use unified handler
- [ ] Update canny-analysis to use unified handler
- [ ] Update remaining analysis commands
- [ ] Add validation tests
- [ ] Update documentation
- [ ] Test all flag combinations
- [ ] Create user guide

---

## Expected Outcome

After implementation:
```bash
# All these work identically across commands
python src/main.py voice-of-customer --test-mode --test-data-count large --verbose --audit-trail
python src/main.py agent-performance --agent horatio --test-mode --test-data-count large --verbose --audit-trail
python src/main.py fin-escalations --test-mode --test-data-count large --verbose --audit-trail
python src/main.py canny-analysis --test-mode --test-data-count large --verbose --audit-trail

# Flags work consistently across all modes
# Output formats are predictable and documented
# Test modes behave identically everywhere
# Debug flags give same information regardless of command
```

---

## Success Criteria

✅ All analysis commands accept same core flags  
✅ Flags behave identically across commands  
✅ Test mode generates consistent data  
✅ Output formats work for all commands  
✅ Documentation is complete  
✅ All flag combinations are tested  
✅ No warnings or errors from unknown flags  
