# Ready-to-Add .cursorrules Enhancements

**Copy-paste these sections directly into `.cursorrules`**

---

## Add After "CLI ↔ Web UI ↔ Railway Alignment" Section

```markdown
## Function Parameter Safety

**CRITICAL:** When adding/modifying function parameters, update BOTH signature AND all callers.

### Verification Steps (MANDATORY):

1. **Search for ALL callers before committing:**
   ```bash
   # Find every place the function is called
   grep -rn "function_name(" src/ tests/
   ```

2. **Update function signature with default value:**
   ```python
   # ✅ GOOD - Backward compatible
   async def analyze(data: Dict, new_param: bool = True):
       ...
   
   # ❌ BAD - Breaks existing callers
   async def analyze(data: Dict, new_param: bool):
       ...
   ```

3. **Update ALL callers to pass new parameter:**
   ```python
   # Before fix:
   await analyze(data)  # ❌ Missing new_param
   
   # After fix:
   await analyze(data, new_param=include_it)  # ✅ Explicit
   ```

4. **Verify parameter is USED in function body:**
   ```python
   def my_func(..., new_param: bool = True):
       # ✅ Actually use it!
       if new_param:
           do_something()
       
       # ❌ Don't just accept and ignore it
   ```

### Common Errors:
- ❌ Adding param to signature but forgetting to update callers → TypeError
- ❌ Adding param but not using it in function → Dead code
- ❌ Variable name mismatch (param vs local variable) → NameError

### Recent Examples:
- Nov 10, 2025: `_analyze_sample()` called with `include_hierarchy` but didn't accept it
- Nov 4, 2025: `paid_fin_resolved_conversations` vs `paid_fin_only_conversations` mismatch

### Auto-Check (to be implemented):
```bash
python scripts/check_function_signatures.py
```
```

---

## Add After "Async Patterns" Section

```markdown
## Async/Await Safety Rules

### Rule 1: ALWAYS await async function calls

```python
# ❌ WRONG - Returns coroutine, not result
async def process():
    result = fetch_data()  # Forgot await!
    return result  # This is a coroutine object, not data!

# ✅ CORRECT
async def process():
    result = await fetch_data()
    return result
```

### Rule 2: NEVER use blocking I/O in async functions

```python
# ❌ WRONG - Blocks entire event loop
async def process():
    time.sleep(5)  # Freezes all async tasks!
    data = requests.get(url)  # Blocks!
    with open('file.txt') as f:  # Blocks!
        content = f.read()

# ✅ CORRECT - Non-blocking alternatives
async def process():
    await asyncio.sleep(5)
    async with httpx.AsyncClient() as client:
        data = await client.get(url)
    async with aiofiles.open('file.txt') as f:
        content = await f.read()
```

### Rule 3: Wrap sync DB operations in executors

```python
# ❌ WRONG - DuckDB is sync, blocks event loop
async def save():
    storage.save_snapshot(data)  # Blocks all async tasks!

# ✅ CORRECT - Use async wrapper or executor
async def save():
    # Option A: Use async wrapper if available
    await storage.save_snapshot_async(data)
    
    # Option B: Use executor
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, storage.save_snapshot, data)
```

### Rule 4: Add timeouts to prevent hangs

```python
# ❌ RISKY - Could hang forever on API failure
async def enrich():
    results = await asyncio.gather(*[fetch(id) for id in ids])

# ✅ SAFE - Timeout protection
async def enrich():
    try:
        results = await asyncio.wait_for(
            asyncio.gather(*[fetch(id) for id in ids]),
            timeout=60
        )
    except asyncio.TimeoutError:
        logger.error("Enrichment timed out after 60s")
        return []  # Graceful degradation
```

### Rule 5: Use semaphores for concurrency control

```python
# ❌ RISKY - Unlimited concurrent API calls
async def enrich_all(conversations):
    tasks = [enrich(conv) for conv in conversations]
    return await asyncio.gather(*tasks)  # Could spawn 1000s of tasks!

# ✅ SAFE - Limited concurrency
async def enrich_all(conversations):
    semaphore = asyncio.Semaphore(5)  # Max 5 concurrent
    
    async def enrich_with_limit(conv):
        async with semaphore:
            return await enrich(conv)
    
    tasks = [enrich_with_limit(conv) for conv in conversations]
    return await asyncio.gather(*tasks)
```

### Recent Bugs This Prevents:
- Nov 10, 2025: SSE timeout due to blocking enrichment
- Nov 4, 2025: DuckDB blocking async pipeline
- Oct 29, 2025: httpx client initialization in sync context

### Auto-Check (to be implemented):
```bash
python scripts/check_async_patterns.py
```
```

---

## Add After "Data Validation" Section

```markdown
## Safe Nested Field Access

### NEVER assume Intercom fields exist - they're inconsistent!

**Known unreliable fields** (ALWAYS use defensive access):
- `custom_attributes` - Often missing or empty
- `conversation_parts` - Can be list OR dict
- `source.author` - May be null
- `contacts.contacts[0]` - Array may be empty
- `sla_applied` - Only on paid tiers
- `conversation_rating` - Only if customer rated
- `ai_agent` - Only for Fin conversations
- `statistics.*` - Often missing nested fields

### Defensive Access Pattern:

```python
# ❌ DANGEROUS - Will crash if ANY field missing
email = conv['source']['author']['email']
category = conv['custom_attributes']['Category']
sla_name = conv['sla_applied']['sla_name']

# ✅ SAFE - Graceful degradation
email = conv.get('source', {}).get('author', {}).get('email')
category = conv.get('custom_attributes', {}).get('Category')
sla_data = conv.get('sla_applied') or {}
sla_name = sla_data.get('sla_name') if isinstance(sla_data, dict) else None
```

### Normalization at Boundary:

**Best practice:** Normalize SDK data IMMEDIATELY after fetch, not everywhere downstream:

```python
# In intercom_sdk_service.py (SDK boundary):

def _normalize_conversation(self, conv: Dict) -> Dict:
    """Single source of truth for normalization."""
    
    # Ensure conversation_parts is dict-wrapped
    if 'conversation_parts' in conv:
        parts = conv['conversation_parts']
        if isinstance(parts, list):
            conv['conversation_parts'] = {'conversation_parts': parts}
        elif not isinstance(parts, dict):
            conv['conversation_parts'] = {'conversation_parts': []}
    
    # Ensure conversation_rating is dict or None
    if 'conversation_rating' in conv:
        rating = conv['conversation_rating']
        if not isinstance(rating, dict):
            if isinstance(rating, (int, float)):
                conv['conversation_rating'] = {'rating': rating}
            else:
                conv['conversation_rating'] = None
    
    # Ensure custom_attributes is dict
    if 'custom_attributes' in conv and not isinstance(conv['custom_attributes'], dict):
        conv['custom_attributes'] = {}
    
    return conv

# Then in fetch_conversations_by_date_range():
async for conversation in pager:
    conv_dict = self._model_to_dict(conversation)
    conv_dict = self._normalize_conversation(conv_dict)  # ← Do it HERE
    all_conversations.append(conv_dict)

# Now downstream code can safely assume:
# - conversation_parts is always dict
# - custom_attributes is always dict
# - No isinstance() checks needed!
```

### Principle:
> **"Normalize at the boundary, assume safety downstream"**

### Recent Bugs This Prevents:
- Nov 4, 2025: conversation_parts list vs dict crashes
- Oct 28, 2025: Rating type inconsistencies
- Multiple: KeyError on nested field access

### Auto-Check (to be implemented):
```bash
python scripts/check_null_safety.py
```
```

---

## Add New Section: "Output File Resilience"

```markdown
## Output File Resilience

### ALWAYS save complete console output to downloadable file

**Why:** SSE connections disconnect frequently. Users lose all terminal output.

**Solution:** Record and save complete output to .log file

### Pattern to Follow:

```python
# In service classes (sample_mode.py, voc_service.py, etc.):

class YourService:
    async def run_analysis(...):
        # Enable Rich console recording
        console.record = True
        
        # Run analysis (all console.print() calls captured)
        result = await self._do_analysis(...)
        
        # Export complete output as plain text
        log_output = console.export_text(clear=True)
        console.record = False
        
        # Save to file alongside JSON
        if save_to_file:
            log_file = output_file.with_suffix('.log')
            with open(log_file, 'w', encoding='utf-8') as f:
                f.write(log_output)
            
            console.print(f"📋 Complete log saved to: {log_file}")
            console.print("   (Download from Files tab - has EVERYTHING even if terminal disconnects)")
```

### Benefits:
- ✅ Terminal can disconnect, output is safe
- ✅ Users can download and share complete analysis
- ✅ Searchable with grep/Ctrl+F
- ✅ Complete audit trail preserved

### Commands Requiring This:
- ✅ sample-mode (implemented Nov 10, 2025)
- ⚠️ voice-of-customer (needs implementation)
- ⚠️ agent-performance (needs implementation)
- ⚠️ agent-coaching-report (needs implementation)
- ⚠️ comprehensive-analysis (needs implementation)

### Recent Impact:
- Nov 10, 2025: Solved schema-dump terminal disconnect issues
```

---

## Add to "Common Mistakes to Avoid" Section

```markdown
### Additional Common Mistakes:

**Function Parameters:**
- ❌ Adding parameter to signature but not updating all callers
- ❌ Using parameter name that differs from variable name
- ❌ Accepting parameter but never using it in function body

**Async/Await:**
- ❌ Forgetting `await` before async function calls
- ❌ Using `time.sleep()` instead of `asyncio.sleep()` in async functions
- ❌ Using blocking I/O (requests, open()) in async functions
- ❌ No timeout on `asyncio.gather()` or long-running operations

**Data Access:**
- ❌ Direct bracket access to optional Intercom fields: `conv['field']['nested']`
- ❌ Assuming SDK data structure is consistent
- ❌ Not normalizing data at SDK boundary
- ❌ Using `isinstance()` checks downstream instead of normalizing upstream

**SSE/Background:**
- ❌ Cancelling background jobs when SSE disconnects
- ❌ Using SSE for long-running tasks (>2 minutes)
- ❌ Not sending keepalives during silent periods
- ❌ Not saving complete output to file

**Testing:**
- ❌ Only testing with mock data, not real Intercom data
- ❌ Not running sample-mode to validate changes
- ❌ Assuming test data represents all edge cases
```

---

## Replace Existing "Testing Patterns" Section

```markdown
## Testing Patterns (ENHANCED)

### 3-Tier Testing Approach:

**Tier 1: Unit Tests (Fast, Isolated)**
- Mock external dependencies
- Test single functions in isolation
- Run on every commit

**Tier 2: Integration Tests (Moderate, Realistic)**
- Use test data (test_data.py)
- Test multiple components together
- Run before merge

**Tier 3: Real Data Validation (Slow, Ground Truth) - REQUIRED**
```bash
# ALWAYS run before marking feature "complete"
python src/main.py sample-mode --count 50 --save-to-file

# Then validate with real data:
python scripts/validate_data_schemas.py
python scripts/check_double_counting.py
```

### Real Data Test Checklist:

Before considering ANY feature complete:
- [ ] Ran with real Intercom data (not just test mode)
- [ ] Checked output files for completeness
- [ ] Verified no crashes on missing/malformed fields
- [ ] Confirmed metrics look sensible (no 300% percentages!)
- [ ] Tested edge cases (empty results, single result, max results)

### Why This Matters:
- Test data is clean and consistent
- Real data is messy with missing fields
- Edge cases appear in production, not mocks
- Type inconsistencies only show up with real SDK responses

### Pattern from Recent Bugs:
- ✅ Unit tests passed (mocked data had field)
- ❌ Production crashed (real data missing field)
- **Solution:** Test with sample-mode before deployment
```

---

## 📋 Complete Updated .cursorrules Structure

```markdown
# Cursor Rules for Intercom Analysis Tool

## Project Context
[Keep existing section]

## Code Style & Patterns
[Keep existing section]

## Error Handling
[Keep existing section]

## Async Patterns (ENHANCED)
[Replace with enhanced async rules above]

## Data Validation (ENHANCED)
[Add safe field access patterns]

## Function Parameter Safety (NEW)
[Add function parameter safety section]

## Safe Nested Field Access (NEW)
[Add defensive access patterns]

## Output File Resilience (NEW)
[Add console recording pattern]

## Hallucination Prevention
[Keep existing section]

## File Organization
[Keep existing section]

## API Integration Patterns
[Keep existing section]

## Testing Patterns (ENHANCED)
[Replace with 3-tier testing approach]

## Common Mistakes to Avoid (ENHANCED)
[Add additional common mistakes]

## Prompting Guidelines for Cursor
[Keep existing section]

## Performance Considerations
[Keep existing section]

## Security & Best Practices
[Keep existing section]

## CLI ↔ Web UI ↔ Railway Alignment (ENHANCED)
[Keep existing, add stricter verification steps]

## SSE and Background Execution (NEW)
[Add SSE resilience rules]

## Pre-Commit Validation (NEW)
Before ANY commit, run:
```bash
python scripts/check_cli_web_alignment.py
# Future: Add more validation scripts
```
```

---

## 🚀 How to Integrate

### Step 1: Backup Current .cursorrules
```bash
cp .cursorrules .cursorrules.backup
```

### Step 2: Add New Sections

Open `.cursorrules` and:
1. Add "Function Parameter Safety" after "Async Patterns"
2. Add "Safe Nested Field Access" after "Data Validation"
3. Add "Output File Resilience" as new section
4. Enhance "Testing Patterns" with 3-tier approach
5. Add items to "Common Mistakes to Avoid"
6. Add "Pre-Commit Validation" at end

### Step 3: Test with Cursor

Ask Cursor to:
```
"Add a new parameter 'include_details' to the analyze_topics function"
```

Cursor should now:
- ✅ Add parameter with default value
- ✅ Search for all callers
- ✅ Update all callers to pass the parameter
- ✅ Remind you to verify with function signature checker

### Step 4: Validate

After a few PRs, check if bugs decreased:
- Track # of parameter mismatch bugs
- Track # of async/await bugs
- Track # of KeyError crashes
- **Expected:** 50-70% reduction

---

## 📊 Metrics to Track

### Before Enhanced Rules:
- Parameter mismatch bugs: 2-3/week
- Async/await bugs: 1-2/week
- KeyError crashes: 3-4/week
- Total debugging time: 8-15 hours/week

### After Enhanced Rules (Expected):
- Parameter mismatch bugs: 0-1/week (-70%)
- Async/await bugs: 0-1/week (-60%)
- KeyError crashes: 1-2/week (-50%)
- Total debugging time: 3-6 hours/week (-60%)

---

## 🎯 Success Criteria

### Week 1:
- [ ] New rules added to .cursorrules
- [ ] Tested with Cursor on sample tasks
- [ ] Team trained on new patterns

### Month 1:
- [ ] 50% reduction in parameter mismatch bugs
- [ ] 40% reduction in async/await bugs
- [ ] 30% reduction in KeyError crashes

### Month 3:
- [ ] Automated checks implemented (scripts/)
- [ ] Pre-commit hooks enforcing checks
- [ ] CI/CD running full validation suite
- [ ] 70% overall bug reduction

---

**Ready to copy-paste into `.cursorrules`!** Start with the sections marked (NEW) and (ENHANCED) for immediate impact.


