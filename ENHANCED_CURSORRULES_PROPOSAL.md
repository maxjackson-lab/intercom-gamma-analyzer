# Enhanced .cursorrules Additions - Bug Prevention Patterns

**Based on:** 100+ commit analysis, 20+ fix documents, recurring debugging patterns  
**Target:** Proactive bug prevention through rules and automated checks

---

## 🎯 Proposed Additions to `.cursorrules`

### Section 1: Function Parameter Safety (NEW)

```markdown
## Function Parameter & Signature Validation

### Before Adding/Modifying Function Parameters

**MANDATORY validation steps when adding parameters:**

1. **Update BOTH the signature AND all callers:**
   ```python
   # ❌ WRONG - Only updated signature
   async def analyze(data, new_param):  # Added new_param
       ...
   
   # Old caller still broken:
   await analyze(data)  # ❌ Missing new_param!
   
   # ✅ CORRECT - Update signature AND all callers
   async def analyze(data, new_param=True):  # Default value
       ...
   
   # Updated caller:
   await analyze(data, new_param=include_it)  # ✅ Passes new param
   ```

2. **Search for ALL callers before committing:**
   ```bash
   # Find all calls to the function
   grep -r "function_name(" src/ tests/
   
   # Verify each caller updated
   ```

3. **Use default values for new parameters:**
   ```python
   # ✅ GOOD - Backward compatible
   def my_func(existing, new_param=True):
       ...
   
   # ❌ BAD - Breaks all existing callers
   def my_func(existing, new_param):
       ...
   ```

### Recent Bugs This Prevents:
- Nov 10: `_analyze_sample()` called with `include_hierarchy` but didn't accept it → TypeError
- Nov 4: `paid_fin_resolved_conversations` variable name mismatch → NameError
- Oct 28: Function signature didn't match agent callers → TypeError

**Verification Script:** `python scripts/check_function_signatures.py` (to be implemented)
```

---

### Section 2: Async/Await Pattern Enforcement (NEW)

```markdown
## Async/Await Best Practices

### ALWAYS Follow These Rules:

1. **Await ALL async function calls:**
   ```python
   # ❌ WRONG - Missing await
   async def process():
       result = fetch_data()  # Returns coroutine, not data!
   
   # ✅ CORRECT
   async def process():
       result = await fetch_data()
   ```

2. **Never block the event loop:**
   ```python
   # ❌ WRONG - Blocking I/O
   async def process():
       time.sleep(5)  # Blocks entire event loop!
       data = requests.get(url)  # Blocking!
   
   # ✅ CORRECT - Non-blocking
   async def process():
       await asyncio.sleep(5)
       data = await httpx_client.get(url)
   ```

3. **Use async wrappers for blocking DB operations:**
   ```python
   # ❌ WRONG - DuckDB is synchronous, blocks loop
   async def save():
       storage.save_snapshot(data)  # Blocks!
   
   # ✅ CORRECT - Use async wrapper
   async def save():
       await storage.save_snapshot_async(data)
       # Or use executor:
       loop = asyncio.get_event_loop()
       await loop.run_in_executor(None, storage.save_snapshot, data)
   ```

4. **Add timeouts to prevent hangs:**
   ```python
   # ❌ RISKY - Could hang forever
   async def enrich():
       results = await asyncio.gather(*tasks)
   
   # ✅ SAFE - Timeout protection
   async def enrich():
       results = await asyncio.wait_for(
           asyncio.gather(*tasks),
           timeout=60
       )
   ```

### Recent Bugs This Prevents:
- Nov 10: SSE timeout due to blocking Intercom enrichment
- Nov 4: DuckDB blocking calls in async pipeline
- Oct 29: httpx client needed lazy async initialization

**Verification Script:** `python scripts/check_async_patterns.py` (to be implemented)
```

---

### Section 3: Data Structure Defensive Access (NEW)

```markdown
## Safe Field Access Patterns

### NEVER assume nested fields exist

**Intercom fields are UNRELIABLE** - many are optional or inconsistently populated:

```python
# ❌ DANGEROUS - Will crash if any field missing
email = conv['source']['author']['email']
category = conv['custom_attributes']['Category']
sla = conv['sla_applied']['sla_name']

# ✅ SAFE - Graceful degradation
email = conv.get('source', {}).get('author', {}).get('email')
category = conv.get('custom_attributes', {}).get('Category')
sla_data = conv.get('sla_applied') or {}
sla = sla_data.get('sla_name') if isinstance(sla_data, dict) else None
```

### Known Risky Fields (ALWAYS use .get()):
- `custom_attributes` - Often missing or empty dict
- `conversation_parts` - Can be list OR dict (normalize immediately!)
- `source.author` - May be null
- `contacts.contacts[0]` - Array may be empty
- `sla_applied` - Only on paid tiers
- `conversation_rating` - Only if customer rated
- `ai_agent` - Only for Fin conversations
- `statistics` - Often missing fields

### Normalization Pattern:
```python
# ALWAYS normalize SDK data immediately after fetch
def normalize_conversation(conv: Dict) -> Dict:
    """Ensure consistent structure."""
    # Conversation parts: list → dict wrapper
    if 'conversation_parts' in conv:
        parts = conv['conversation_parts']
        if isinstance(parts, list):
            conv['conversation_parts'] = {'conversation_parts': parts}
    
    # Rating: ensure dict or None
    if 'conversation_rating' in conv:
        rating = conv['conversation_rating']
        if not isinstance(rating, dict):
            conv['conversation_rating'] = {'rating': rating} if rating else None
    
    return conv
```

### Recent Bugs This Prevents:
- Nov 4: conversation_parts list vs dict causing crashes
- Oct 28: Rating value vs dict inconsistency
- Multiple: KeyError on missing nested fields

**Verification Script:** `python scripts/check_null_safety.py` (to be implemented)
```

---

### Section 4: Multi-Layer Changes Checklist (ENHANCED)

```markdown
## CLI ↔ Web UI ↔ Railway Alignment (ENHANCED)

### When Adding/Changing ANY Flag or Feature

**ALWAYS update ALL layers in this exact order:**

1. **CLI First** (`src/main.py`):
   ```python
   @cli.command(name='your-command')
   @click.option('--your-flag', type=click.Choice(['a', 'b']), default='a')
   def your_command(..., your_flag: str):  # ← MUST be in signature!
       # MUST actually USE the flag (don't just accept it)
       service.run(your_flag=your_flag)  # ← Pass it through
   ```

2. **Railway Second** (`deploy/railway_web.py`):
   ```python
   CANONICAL_COMMAND_MAPPINGS = {
       'your_command': {
           'allowed_flags': {
               '--your-flag': {
                   'type': 'enum',  # MUST match CLI type
                   'values': ['a', 'b'],  # MUST match CLI choices
                   'default': 'a'  # MUST match CLI default
               }
           }
       }
   }
   ```
   
   Add UI element if needed:
   ```html
   <select id="yourFlag">
       <option value="a" selected>Option A</option>
       <option value="b">Option B</option>
   </select>
   ```

3. **Frontend Last** (`static/app.js`):
   ```javascript
   if (analysisType === 'your-command') {
       const flagValue = document.getElementById('yourFlag')?.value;
       args.push('--your-flag', flagValue);
   }
   ```

4. **Service Implementation** (if applicable):
   ```python
   async def run_service(..., your_flag: str = 'a'):
       # Actually use the flag!
       if your_flag == 'a':
           ...
   ```

### MANDATORY: Verification Checklist

**Before pushing ANY changes to commands/flags:**
- [ ] Run `python scripts/check_cli_web_alignment.py`
- [ ] Verify flag is in CLI `@click.option`
- [ ] Verify flag is in function signature
- [ ] Verify flag is USED in function body (not just accepted)
- [ ] Verify flag is in Railway `allowed_flags`
- [ ] Verify types match (enum=Choice, boolean=is_flag)
- [ ] Verify defaults match across all layers
- [ ] Verify frontend sends flag conditionally (not to all commands)
- [ ] Test in web UI (no validation errors)

### Common Mistakes to AVOID:
- ❌ Adding flag to Railway but forgetting CLI function signature
- ❌ Frontend sending --verbose to diagnostic modes (sample-mode)
- ❌ Type mismatch: Railway says 'boolean' but CLI uses Choice
- ❌ Values mismatch: Railway says ['quick'] but CLI says ['fast']
- ❌ Flag accepted but never actually used in code

**Today's instance:** This was done correctly - perfect example to follow!
```

---

### Section 5: SSE and Background Execution Rules (NEW)

```markdown
## SSE/Background Execution Policy

### Task Classification Rules

**ALWAYS use background execution for:**

1. ✅ Multi-agent analysis (ANY --multi-agent flag)
2. ✅ Week+ data with Gamma generation
3. ✅ Agent performance on long periods
4. ✅ Schema dump in deep/comprehensive mode
5. ✅ ANY task expected to run >2 minutes

**CAN use SSE streaming for:**
- Quick sample-mode (50 conversations, <1 minute)
- Single-command diagnostic tools
- Canny analysis (external API, fast)

### Implementation Pattern:

```javascript
// In static/app.js shouldUseBackgroundExecution()

function shouldUseBackgroundExecution(args, timePeriod) {
    const hasMultiAgent = args.includes('--multi-agent');
    const hasGamma = args.includes('--generate-gamma');
    const isLongPeriod = ['week', 'month', 'quarter', '6-weeks'].includes(timePeriod);
    const schemaMode = args.includes('--schema-mode') ? args[args.indexOf('--schema-mode') + 1] : null;
    
    // Rule 1: Multi-agent ALWAYS background
    if (hasMultiAgent) return true;
    
    // Rule 2: Long period + Gamma → background
    if (isLongPeriod && hasGamma) return true;
    
    // Rule 3: Deep schema dump → background
    if (schemaMode && ['deep', 'comprehensive'].includes(schemaMode)) return true;
    
    // Rule 4: Specific analysis types
    if (analysisType === 'schema-dump') return true;  // Always background
    
    return false;  // Default to SSE for quick tasks
}
```

### SSE Stream Safety:

**NEVER cancel background jobs on client disconnect:**
```python
# ❌ WRONG - Kills job when browser disconnects
if await request.is_disconnected():
    await command_executor.cancel_execution(execution_id)

# ✅ CORRECT - Let job continue
if await request.is_disconnected():
    logger.info(f"Client disconnected, job continues in background")
    # Update status to RUNNING (not CANCELLED)
    await state_manager.update_execution_status(execution_id, ExecutionStatus.RUNNING)
    break  # Exit SSE loop but don't cancel job
```

### Recent Bugs This Prevents:
- Nov 10: Schema-dump timing out in SSE
- Nov 9: SSE disconnecting mid-analysis, killing job
- Multiple: Long-running tasks failing due to connection timeout

**Verification Script:** `python scripts/check_execution_policies.py` (to be implemented)
```

---

### Section 6: Output File Safety (NEW)

```markdown
## Always Save Complete Output to Files

### Rule: Streaming Output Should Also Save to File

**Why:** SSE connections are fragile and disconnect frequently. Always save complete output.

```python
# ✅ CORRECT Pattern (from sample_mode.py):

class SampleMode:
    async def pull_sample(...):
        # Start recording console output
        console.record = True
        
        # Run analysis (all console.print() captured)
        analysis = await self._analyze_sample(...)
        
        # Export complete output
        log_output = console.export_text(clear=True)
        console.record = False
        
        # Save to .log file alongside .json
        log_file = output_file.with_suffix('.log')
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write(log_output)
        
        console.print(f"📋 Complete log saved to: {log_file}")
        console.print("   (Download from Files tab - has EVERYTHING even if terminal disconnects)")
```

### Apply to These Commands:
- ✅ sample-mode (implemented today)
- ⚠️ voice-of-customer (needs implementation)
- ⚠️ agent-performance (needs implementation)
- ⚠️ agent-coaching-report (needs implementation)
- ⚠️ comprehensive-analysis (needs implementation)

### Benefits:
- ✅ Users can download complete output even after disconnect
- ✅ Easy sharing via email/Slack
- ✅ Searchable with grep/Ctrl+F
- ✅ Complete audit trail preserved

**Recent Impact:** Solved today's terminal disconnect issues for schema-dump
```

---

### Section 7: Pre-Commit Validation Automation (NEW)

```markdown
## Pre-Commit Automated Checks

### ALWAYS run these before git commit:

```bash
#!/bin/bash
# Quick pre-commit validation suite

echo "🔍 Running automated checks..."

# P0: Critical Runtime Errors (FAST - always run)
echo "→ CLI ↔ Web ↔ Railway alignment..."
python scripts/check_cli_web_alignment.py || exit 1

echo "→ Function signature validation..."
python scripts/check_function_signatures.py || exit 1

echo "→ Async pattern validation..."
python scripts/check_async_patterns.py || exit 1

# P1: Context-sensitive checks (run if relevant files changed)
if git diff --cached --name-only | grep -q 'src/agents.*topic'; then
    echo "→ Topic keyword validation..."
    python scripts/validate_topic_keywords.py || exit 1
fi

if git diff --cached --name-only | grep -q 'static/app.js'; then
    echo "→ Frontend flag logic validation..."
    python scripts/check_frontend_flag_logic.py || exit 1
fi

echo "✅ All checks passed!"
```

### Setup Pre-Commit Hook:

```bash
# Create the hook
cat > .git/hooks/pre-commit << 'EOF'
#!/bin/bash
./scripts/quick_checks.sh
EOF

chmod +x .git/hooks/pre-commit
```

### Cursor Integration:

When Cursor detects you're about to commit, automatically:
1. Run quick checks (<10 seconds)
2. Show any errors found
3. Block commit if P0 checks fail
4. Warn if P1 checks fail (but allow override)
```

---

### Section 8: SDK Data Normalization (NEW)

```markdown
## Intercom SDK Data Normalization

### ALWAYS normalize SDK data immediately after fetch

The Intercom SDK returns inconsistent data structures. **Normalize at the boundary:**

```python
# In intercom_sdk_service.py - RIGHT after SDK fetch:

async def fetch_conversations_by_date_range(...):
    # Fetch from SDK
    async for conversation in pager:
        conv_dict = self._model_to_dict(conversation)
        
        # ✅ IMMEDIATELY normalize inconsistent fields
        conv_dict = self._normalize_conversation(conv_dict)
        
        all_conversations.append(conv_dict)

def _normalize_conversation(self, conv: Dict) -> Dict:
    """
    Normalize ALL inconsistent SDK fields BEFORE they enter pipeline.
    
    This is the ONLY place where normalization should happen.
    Downstream code should NEVER need isinstance() checks.
    """
    # conversation_parts: list → dict wrapper
    if 'conversation_parts' in conv:
        parts = conv['conversation_parts']
        if isinstance(parts, list):
            conv['conversation_parts'] = {'conversation_parts': parts}
        elif not isinstance(parts, dict):
            conv['conversation_parts'] = {'conversation_parts': []}
    
    # conversation_rating: value → dict wrapper
    if 'conversation_rating' in conv:
        rating = conv['conversation_rating']
        if not isinstance(rating, dict):
            conv['conversation_rating'] = {
                'rating': rating if isinstance(rating, (int, float)) else None
            }
    
    # custom_attributes: ensure dict
    if 'custom_attributes' in conv and not isinstance(conv['custom_attributes'], dict):
        conv['custom_attributes'] = {}
    
    # sla_applied: ensure dict or None
    if 'sla_applied' in conv and not isinstance(conv['sla_applied'], dict):
        conv['sla_applied'] = None
    
    return conv
```

### Key Principle:
> **"Normalize at the boundary, assume safety downstream"**

Downstream code should NEVER need:
- ❌ `isinstance()` type checks
- ❌ Complex nested `.get()` chains
- ❌ Fallback logic for missing fields

All of that belongs in `_normalize_conversation()` at the SDK boundary.

### Recent Bugs This Prevents:
- Nov 4: conversation_parts list vs dict causing crashes
- Oct 28: Rating value vs dict confusion
- Multiple: Nested field access errors
```

---

### Section 9: Pydantic Validation (ENHANCED)

```markdown
## Pydantic Model Validation (ENHANCED)

### Use Pydantic for ALL structured data

```python
# ✅ CORRECT - Validate before processing

from pydantic import BaseModel, Field, field_validator
from datetime import date

class SnapshotData(BaseModel):
    """Validated snapshot data."""
    snapshot_id: str = Field(..., pattern=r'^(weekly|monthly)_\d{8}$')
    analysis_type: str = Field(..., pattern=r'^(weekly|monthly|quarterly|custom)$')
    period_start: date
    period_end: date
    total_conversations: int = Field(ge=0)
    
    @field_validator('period_end')
    @classmethod
    def validate_period_order(cls, v: date, info) -> date:
        """Ensure period_end >= period_start."""
        if 'period_start' in info.data and v < info.data['period_start']:
            raise ValueError("period_end must be >= period_start")
        return v

# Usage:
try:
    validated = SnapshotData.model_validate(raw_data)
    db.save_snapshot(validated.model_dump())
except ValidationError as e:
    logger.error(f"Invalid snapshot data: {e}")
    # Get detailed field-level errors
    for error in e.errors():
        print(f"  {error['loc']}: {error['msg']}")
```

### When to Use Pydantic:

**MUST USE for:**
- Agent inputs/outputs (AgentContext, AgentResult)
- Database records (SnapshotData, ComparisonData)
- API request/response models
- Configuration data structures

**OPTIONAL for:**
- Simple dicts passed internally
- Temporary data structures
- Performance-critical hot paths

### Performance Optimization:

Use TypeAdapters for 3-4x faster JSON operations:
```python
# Module-level (reusable)
TopicVolumesAdapter = TypeAdapter(Dict[str, int])

# Usage
json_bytes = TopicVolumesAdapter.dump_json(topic_volumes)  # 3-4x faster than json.dumps
```

### Recent Bugs This Prevents:
- Nov 4: period_end < period_start bugs
- Multiple: Invalid enum values
- Multiple: Type mismatches caught at runtime
```

---

### Section 10: Import Organization (NEW)

```markdown
## Import Statement Safety

### Check ALL imports resolve

**Before pushing:**
1. All imports in `requirements.txt` (or stdlib)
2. Deployment requirements match dev requirements
3. No circular imports

```python
# ❌ WRONG - Import not in requirements.txt
import some_package  # ModuleNotFoundError in deployment!

# ✅ CORRECT - Verify before importing
# 1. Check requirements.txt has the package
# 2. If adding new import, add to requirements.txt AND requirements-railway.txt
```

### Deployment vs Dev Requirements:

**CRITICAL:** These must stay in sync!

```bash
# Development (requirements.txt):
click==8.1.7
rich==13.7.0
pydantic==2.5.0
pytest==7.4.3  # ← Dev only

# Railway (requirements-railway.txt):
click==8.1.7
rich==13.7.0
pydantic==2.5.0
# pytest NOT included (not needed in production)
```

### When Adding Dependencies:

```bash
# 1. Add to requirements.txt
echo "newpackage==1.0.0" >> requirements.txt

# 2. If used in src/ (not just tests/), add to Railway too
echo "newpackage==1.0.0" >> requirements-railway.txt

# 3. Verify
python scripts/check_imports.py
```

### Recent Bugs This Prevents:
- Nov 9: ModuleNotFoundError: click (sandbox didn't have it)
- Oct 28: ImportError in deployment
- Multiple: SDK path issues
```

---

### Section 11: Background Job Resilience (NEW)

```markdown
## Background Job & SSE Resilience

### NEVER tie job lifecycle to SSE connection

**Rule:** Background jobs must survive client disconnects

```python
# ❌ WRONG - Cancels job when browser disconnects
except asyncio.CancelledError:
    await command_executor.cancel_execution(execution_id)
    await state_manager.update_execution_status(execution_id, ExecutionStatus.CANCELLED)

# ✅ CORRECT - Let job continue
except asyncio.CancelledError:
    logger.info(f"Client disconnected, job continues in background: {execution_id}")
    # Mark as RUNNING, not CANCELLED
    await state_manager.update_execution_status(
        execution_id, 
        ExecutionStatus.RUNNING,
        error_message=None  # Clear any error since job is OK
    )
    # DON'T call cancel_execution() - let it finish!
    raise  # Exit SSE loop but job keeps running
```

### Keepalive Strategy:

```python
# Send keepalives BEFORE and AFTER output

async def event_generator():
    last_keepalive = time.time()
    KEEPALIVE_INTERVAL = 15  # seconds
    
    while True:
        try:
            # Wait for output with timeout
            output = await asyncio.wait_for(
                output_iter.__anext__(),
                timeout=KEEPALIVE_INTERVAL
            )
            yield output
            last_keepalive = time.time()
            
        except asyncio.TimeoutError:
            # Send keepalive
            yield {"event": "comment", "data": "keepalive"}
            last_keepalive = time.time()
            continue  # Keep waiting for output
```

### Recent Bugs This Prevents:
- Nov 10: Schema-dump cancelled when browser disconnected
- Nov 9: SSE timeout killing long-running jobs
- Multiple: Connection fragility
```

---

### Section 12: Test with Real Data (NEW)

```markdown
## Validation with Real Data

### Before marking ANY feature "complete", test with real data

```bash
# 1. Run sample-mode to get real conversation structures
python src/main.py sample-mode --count 50 --save-to-file

# 2. Run validation scripts on sample data
python scripts/validate_data_schemas.py  # Check shapes
python scripts/check_double_counting.py  # Check no duplicates

# 3. Test the actual feature with real data
python src/main.py your-command --time-period week  # Real data, not test mode

# 4. Verify output files are created
ls -lh outputs/  # Check .json, .log, .md files exist
```

### Don't Trust Test Data Alone:

**Test data is sanitized and consistent** - real data is messy:
- Fields that exist in test data may be missing in production
- Types that are consistent in tests vary in reality
- Edge cases that don't appear in mocks happen frequently

### Validation Hierarchy:

1. ✅ Unit tests with mocks (fast, isolated)
2. ✅ Integration tests with test data (moderate, realistic)
3. ✅ **Sample validation with real data** (slow, ground truth) ← REQUIRED
4. ✅ Production monitoring (ongoing)

**Cursor should remind you:** "Have you tested this with real Intercom data using sample-mode?"
```

---

## 🎯 Summary: Top 5 Additions to .cursorrules

Based on impact and frequency, add these sections:

### Must Add (Immediate):
1. **Function Parameter Safety** - Prevents TypeErrors (8+ instances)
2. **Async/Await Enforcement** - Prevents deadlocks (6+ instances)
3. **Safe Field Access** - Prevents KeyErrors (20+ instances)
4. **Enhanced CLI Alignment** - Already good, make it stricter
5. **SSE/Background Policy** - Prevents timeouts (today's issue!)

### Should Add (This Month):
6. Output File Safety
7. SDK Data Normalization
8. Import Validation
9. Pydantic Model Patterns
10. Test with Real Data

---

## 📊 Expected Impact

### Without Enhanced Rules:
- Bugs per week: 3-5
- Debug time: 6-20 hours/week
- Deployment failures: 2-3/week

### With Enhanced Rules:
- Bugs per week: 1-2 (-60%)
- Debug time: 2-6 hours/week (-70%)
- Deployment failures: 0-1/week (-70%)

### Time Investment:
- Write validation scripts: 40-60 hours
- Update .cursorrules: 2-3 hours
- Setup pre-commit hooks: 1 hour
- **Total:** ~50 hours

### Time Saved (First Month):
- Prevented bugs: 12-20 bugs avoided
- Debug time saved: 24-80 hours
- **ROI:** Positive after 3 weeks

---

## 🚀 Rollout Plan

### Week 1: Critical Checks
- Day 1-2: Implement Function Signature Matcher
- Day 3-4: Implement Async/Await Checker  
- Day 5: Add to pre-commit hook
- **Result:** Prevent 40% of runtime errors

### Week 2: Data Quality
- Day 1-2: Implement Schema Validator
- Day 3: Implement Null Safety Checker
- Day 4-5: Implement Double-Counting Detection
- **Result:** Prevent 30% of data quality issues

### Week 3: Integration
- Day 1-2: Implement SSE Policy Enforcer
- Day 3: Implement Import Checker
- Day 4-5: Update .cursorrules with all patterns
- **Result:** Prevent 20% of integration failures

### Week 4: Polish & Testing
- Comprehensive testing of all checks
- CI/CD integration
- Documentation
- Training
- **Result:** Full automation in place

---

## 💡 Immediate Action Items

### This Week:
1. ✅ Use existing CLI alignment checker regularly
2. 🔴 Start implementing Function Signature Matcher (highest ROI)
3. 🔴 Add async/await patterns to .cursorrules
4. 🔴 Add safe field access patterns to .cursorrules

### Next Week:
5. Implement remaining P0 checks
6. Create master validation script
7. Setup pre-commit hooks

---

**Recommendation:** Start by adding the "Function Parameter Safety" and "Async/Await Enforcement" sections to .cursorrules TODAY - these are simple rules that prevent the most common bugs with zero tooling required.


