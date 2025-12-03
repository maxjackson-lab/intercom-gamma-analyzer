# Failure Mode Runbook

**Consolidated troubleshooting guide for Intercom Analysis Tool failures**

This runbook consolidates failure modes from:
- `COMPREHENSIVE_FAILURE_AUDIT.md` (47 critical questions)
- `URGENT_INVESTIGATION_BRIEF.md` (topic detection failures)
- `DEVELOPMENT_STANDARDS.md` (error-log-first debugging workflow)

---

## 🔍 Error-Log-First Debugging Workflow

**CRITICAL: Always retrieve and analyze logs BEFORE adjusting code or configuration.**

### Workflow:
1. **Retrieve full `.log` file** (not just console output)
   - Files: `outputs/executions/<execution_id>/*.log`
   - Contains complete error tracebacks and provider error codes
2. **Identify primary error codes** (400, 429, timeout, parsing errors)
3. **Map error to root cause** using diagnostic table below
4. **Make targeted fix** (not random guessing)
5. **Validate fix** via sample-mode: `python src/main.py sample-mode --count 50 --save-to-file`
6. **Check new log** to confirm resolution

### Why Logs First?
- Console output may be truncated on SSE disconnect
- Log files persist complete output via `output_manager.py`
- Contains full error tracebacks and provider error codes
- Prevents guesswork and random config changes

---

## 🚨 Failure Mode: Rate Limit Errors (429)

### Symptoms
- High timeout rate (>10%)
- Slow processing (requests queued)
- "Other" topics inflated (LLM fallbacks to keywords)
- Console shows: "Rate limit exceeded" or "429 Too Many Requests"

### Diagnosis
1. **Check observability JSON** (`agent_metrics_*.json`):
   ```json
   {
     "summary": {
       "error_count": 45,
       "errors": [
         {"error_type": "rate_limit", "agent": "TopicDetectionAgent", ...}
       ]
     }
   }
   ```
2. **Check fallback metrics** in topic detection results:
   ```json
   {
     "fallback_metrics": {
       "timeout_count": 120,
       "keyword_fallback_count": 95
     }
   }
   ```
3. **Check provider**:
   - Anthropic: Tier 1 limit = 50 RPM → max 2 concurrent
   - OpenAI: Higher limits → max 10 concurrent

### Fix
**Anthropic (Claude):**
```bash
# Reduce concurrency to 2 (default)
export ANTHROPIC_CONCURRENCY=2

# Or in code:
settings.anthropic_concurrency = 2
```

**OpenAI:**
```bash
# Reduce concurrency if hitting limits
export OPENAI_CONCURRENCY=5  # Default is 10
```

**Verification:**
```bash
python src/main.py sample-mode --count 50 --save-to-file
# Check .log file for rate_limit_errors count (should be 0)
```

### Phase 3 Resilience Check

**Verify Semaphore Configuration**
```bash
python -c "from src.config.settings import settings; print(f'Anthropic: {settings.anthropic_concurrency}, OpenAI: {settings.openai_concurrency}')"
```
- Expected default → Anthropic: `2`, OpenAI: `20`. Adjust env vars if drifted.

**Verify No Hardcoded Semaphores**
```bash
python scripts/validate_resilience_standards.py
```
- Fix any "Hardcoded Semaphore" violations before rerunning.

**Lower Concurrency if Needed**
```bash
export ANTHROPIC_CONCURRENCY=1   # Tier 1 emergency mode
export OPENAI_CONCURRENCY=10     # Temporary slowdown
```
- Re-run sample-mode and confirm rate-limit errors disappear.

### Prevention
- Use provider-specific concurrency limits (already implemented)
- Monitor `X-RateLimit-Remaining` headers
- Implement exponential backoff (already implemented)

---

## ⏱️ Failure Mode: Timeout Errors

### Symptoms
- High fallback to keywords (>20%)
- Thin topic distribution (many "Unknown/unresponsive")
- Console shows: "LLM timeout for conversation X, falling back to keywords"
- Observability JSON shows high `timeout_count`

### Diagnosis
1. **Check observability JSON**:
   ```json
   {
     "summary": {
       "error_count": 80,
       "errors": [
         {"error_type": "timeout", "agent": "TopicDetectionAgent", ...}
       ]
     }
   }
   ```
2. **Check fallback metrics**:
   ```json
   {
     "fallback_metrics": {
       "timeout_count": 150,
       "total_conversations": 500,
       "timeout_rate": 0.30  # 30% timeout rate!
     }
   }
   ```
3. **Check timeout configuration**:
   ```bash
   # Current timeout settings
echo $TOPIC_DETECTION_TIMEOUT  # Default: 180s
   echo $LLM_CLIENT_TIMEOUT       # Default: 60s
   ```

### Fix
**Increase timeout for slow providers:**
```bash
# Anthropic (slower responses)
export TOPIC_DETECTION_TIMEOUT=240
export LLM_CLIENT_TIMEOUT=90

# OpenAI (faster, but increase if needed)
export TOPIC_DETECTION_TIMEOUT=180
export LLM_CLIENT_TIMEOUT=60
```

**Or adjust in code:**
```python
# settings.py
topic_detection_timeout: int = Field(180, env="TOPIC_DETECTION_TIMEOUT")
llm_client_timeout: int = Field(90, env="LLM_CLIENT_TIMEOUT")
```

**Verification:**
```bash
python src/main.py sample-mode --count 50 --save-to-file
# Check .log for timeout_rate (should be <10%)
```

### Phase 3 Timeout Configuration

**Check Current Timeouts**
```bash
python -c "from src.config.settings import settings; print(f'Default: {settings.llm_timeout_default}s, Topic: {settings.topic_detection_timeout}s, Formatter: {settings.output_formatter_timeout}s')"
```
- Defaults: Topic = 180s, Formatter = 120s, Orchestrator window = 3× agent timeout.

**Increase Timeout for Specific Agent**
```bash
export TOPIC_DETECTION_TIMEOUT=240
export OUTPUT_FORMATTER_TIMEOUT=180
```
- Update `settings.py` only if adding a brand-new agent timeout.

**Verify No Hardcoded Timeouts**
```bash
python scripts/validate_resilience_standards.py
```
- Ensure all LLM calls pull from `settings.*_timeout`.

### Prevention
- Use configurable timeouts (already implemented)
- Monitor timeout rate in observability JSON
- Increase timeout if timeout rate > 10%

---

## 📉 Failure Mode: Data Loss / Silent Failures

### Symptoms
- OutputFormatterAgent returns generic summaries or empty sections despite successful upstream agents.
- Logs show `🚨 DATA DROP ALERT` warnings.
- Final topic volumes far lower than raw conversation counts.

### Diagnosis
1. **Scan logs for alerts**
   ```bash
   grep "DATA DROP ALERT" intercom_analysis.log
   ```
2. **Identify the stage name** in the warning (e.g., `Post-Segmentation`, `Post-TopicDetection`).
3. **Inspect upstream agent outputs** (Segmentation, TopicDetection) for filtering bugs or validation errors.
4. **Confirm `log_stage_metrics()` is called** in the relevant strategy.

### Fix
- Address the agent that dropped records (e.g., relax validation, handle missing fields, ensure context metadata is carried forward).
- Add missing `self.log_stage_metrics(stage_name, count)` calls if the stage was invisible to the gate.
- Re-run the pipeline with debug logging enabled to confirm counts remain stable.

### Phase 3 Data Quality Checklist
- Run `python scripts/validate_resilience_standards.py` to ensure the strategy uses `log_stage_metrics()` at every major stage.
- If alerts persist, add instrumentation to log why items were filtered (e.g., missing `topic_id`, invalid segmentation).
- Only mark the issue resolved once sample-mode completes with **no** `DATA DROP ALERT` warnings.

---

## 📁 Failure Mode: Missing Files

### Symptoms
- Files not visible in Railway Files tab
- Console says "Files saved" but browser shows empty
- Old files disappeared after deploy

### Diagnosis
1. **Check file location**:
   ```bash
   # Should be in executions/ subdirectory
   railway run ls -la /app/outputs/executions/
   ```
2. **Check if using output_manager**:
   ```python
   # ❌ WRONG - May save to wrong location
   output_file = Path(settings.effective_output_directory) / "file.json"
   
   # ✅ CORRECT - Always uses execution directory
   from src.utils.output_manager import get_output_file_path
   output_file = get_output_file_path("file.json")
   ```
3. **Check environment variables**:
   ```bash
   echo $EXECUTION_OUTPUT_DIR  # Should be set in web context
   echo $RAILWAY_VOLUME_MOUNT_PATH  # Optional persistent volume
   ```

### Fix
**Use output_manager helpers:**
```python
from src.utils.output_manager import get_output_file_path

# All file saves should use this
output_file = get_output_file_path("voice_of_customer_report.md")
with open(output_file, 'w') as f:
    f.write(report)
```

**Verify paths:**
- Web executions: `outputs/executions/<execution_id>/`
- CLI executions: `outputs/`
- Persistent volume: `/mnt/persistent/outputs/executions/<execution_id>/`

### Prevention
- Always use `get_output_file_path()` for human-facing artifacts
- Never use bare `Path("outputs/")` in web context
- Check `RAILWAY_FILE_ACCESS.md` for file location patterns

---

## 📊 Failure Mode: Thin Data Distribution

### Symptoms
- Topics show very low counts (<5% each)
- High "Unknown/unresponsive" percentage (>30%)
- Distribution doesn't match expected patterns

### Diagnosis
1. **Check stage-level metrics** (in console output):
   ```
   Preprocessing: 7381 → 7171 valid (97.2% kept, 210 dropped)
   Deduplication: 7171 → 7150 unique (99.7% kept, 21 duplicates removed)
   ```
2. **Check fallback metrics**:
   ```json
   {
     "fallback_metrics": {
       "llm_success_count": 200,
       "keyword_fallback_count": 300,
       "timeout_count": 150,
       "unknown_count": 50,
       "total_conversations": 700
     }
   }
   ```
3. **Check topic distribution**:
   ```json
   {
     "topic_distribution": {
       "Billing": {"volume": 5, "percentage": 0.7},
       "Bug": {"volume": 3, "percentage": 0.4},
       "Unknown/unresponsive": {"volume": 692, "percentage": 98.9}
     }
   }
   ```

### Fix
**If high timeout rate:**
- Increase timeout (see "Timeout Errors" section above)
- Reduce concurrency (see "Rate Limit Errors" section above)

**If high keyword fallback:**
- Check keyword coverage: `src/config/taxonomy.py`
- Verify keywords match actual conversation text
- Consider expanding keyword list

**If high unknown rate:**
- Review conversations marked "Unknown" in logs
- Add keywords for common patterns
- Consider lowering LLM confidence threshold

**Verification:**
```bash
python src/main.py sample-mode --count 50 --save-to-file
# Check topic_distribution in JSON output
# Should see reasonable distribution (top 3 topics >10% each)
```

### Prevention
- Monitor fallback metrics in observability JSON
- Track stage-level metrics (preprocessing, deduplication)
- Review "Unknown" conversations periodically to improve keywords

---

## 🔴 Failure Mode: LLM Validation Errors (400)

### Symptoms
- LLM API returns 400 Bad Request
- Console shows: "OpenAI API error: 400 Bad Request"
- Observability JSON shows validation errors

### Diagnosis
1. **Check observability JSON**:
   ```json
   {
     "summary": {
       "error_count": 25,
       "errors": [
         {
           "error_type": "validation",
           "error_message": "400 Bad Request: allOf is not permitted",
           "agent": "TopicDetectionAgent"
         }
       ]
     }
   }
   ```
2. **Check for Structured Outputs usage**:
   - Structured Outputs with Pydantic Enums cause 400 errors
   - Error: "allOf is not permitted" in JSON schema
   - Solution: Use simple text parsing instead

### Fix
**If using Structured Outputs:**
- **DO NOT** use Structured Outputs with Pydantic Enums
- Use simple text parsing (already implemented)
- Parse JSON from LLM text response

**If schema validation fails:**
- Check Pydantic model for incompatible fields
- Remove `allOf` from JSON schema (Pydantic generates this for Enums)
- Use simple text parsing instead

**Verification:**
```bash
python src/main.py sample-mode --count 50 --save-to-file
# Check .log for 400 errors (should be 0)
```

### Prevention
- Never use Structured Outputs with Pydantic Enums
- Use simple text parsing for LLM responses
- Test with real data before deploying

---

## 🔌 Failure Mode: Circuit Breaker Open

### Symptoms
- All LLM calls fail immediately
- Console shows: "Circuit breaker is OPEN"
- No retries attempted

### Diagnosis
1. **Check circuit breaker state**:
   ```python
   from src.services.openai_client import OpenAIClient
   client = OpenAIClient()
   stats = client.circuit_breaker.get_stats()
   print(stats)  # Shows state: 'open', 'closed', or 'half_open'
   ```
2. **Check failure count**:
   - Circuit opens after 5 consecutive failures
   - Stays open for 60 seconds (default)
   - Then transitions to half-open for testing

### Fix
**Wait for recovery:**
- Circuit breaker auto-recovers after timeout (60s default)
- Or manually reset:
  ```python
  client.circuit_breaker.reset()
  ```

**Fix underlying issue:**
- If rate limits: Reduce concurrency (see "Rate Limit Errors")
- If timeouts: Increase timeout (see "Timeout Errors")
- If API key invalid: Fix API key (see "Startup Validation")

**Verification:**
```bash
python src/main.py sample-mode --count 50 --save-to-file
# Check .log for circuit breaker state
```

### Prevention
- Monitor circuit breaker stats in observability JSON
- Fix root cause (rate limits, timeouts, invalid keys)
- Circuit breaker prevents cascading failures

---

## 🔑 Failure Mode: Invalid API Keys

### Symptoms
- Startup fails with "Configuration Error"
- Console shows: "API key invalid" or "Missing API key"
- Test connection fails

### Diagnosis
1. **Check startup validation**:
   ```
   ❌ Configuration Error: Critical API keys missing or invalid: OpenAI, Intercom
   ```
2. **Check environment variables**:
   ```bash
   echo $OPENAI_API_KEY        # Should be set
   echo $INTERCOM_ACCESS_TOKEN # Should be set
   echo $ANTHROPIC_API_KEY     # Optional
   ```
3. **Check for placeholders**:
   ```bash
   # Placeholder values indicate misconfiguration
   echo $INTERCOM_WORKSPACE_ID  # Should not be "your-workspace-id-here"
   ```

### Fix
**Set valid API keys:**
```bash
# Railway: Set in environment variables
railway variables set OPENAI_API_KEY=sk-...
railway variables set INTERCOM_ACCESS_TOKEN=dG9r...

# Local: Set in .env file
echo "OPENAI_API_KEY=sk-..." >> .env
echo "INTERCOM_ACCESS_TOKEN=dG9r..." >> .env
```

**Verify keys:**
```bash
python src/main.py test  # Tests all API connections
```

### Prevention
- Startup validation catches invalid keys immediately
- Use `--skip-validation` flag only for testing
- Check for placeholder values in environment variables

---

## 📉 Failure Mode: Data Loss Between Stages

### Symptoms
- Topics detected but not in final output
- Gamma presentation shows boilerplate (no topic cards)
- Console shows topics but JSON output is empty

### Diagnosis
1. **Check stage-level metrics**:
   ```
   Preprocessing: 1000 → 950 valid (95% kept)
   Topic Detection: 950 → 800 with topics (84% coverage)
   Output Formatting: 800 → 0 topics (100% loss!)
   ```
2. **Check data flow**:
   - TopicDetectionAgent returns `topic_distribution`
   - OutputFormatterAgent receives `context.previous_results`
   - Verify data structure matches expected format

### Fix
**Check data structure:**
```python
# In OutputFormatterAgent
topic_dist = context.previous_results.get('TopicDetectionAgent', {}).get('data', {}).get('topic_distribution', {})
if not topic_dist:
    logger.error("🚨 CRITICAL: topic_dist is EMPTY")
    # Check previous_results structure
```

**Verify normalization:**
- Check `_normalize_agent_result()` doesn't strip nested data
- Ensure `AgentResult.data` is preserved through pipeline

**Verification:**
```bash
python src/main.py sample-mode --count 50 --save-to-file
# Check JSON output for topic_distribution (should not be empty)
```

### Prevention
- Add logging at each pipeline stage
- Verify data structure matches expected format
- Test with real data before deploying

---

## 🔧 Diagnostic Commands

### Quick Health Check
```bash
# Test all API connections
python src/main.py test

# Run sample-mode with observability
python src/main.py sample-mode --count 50 --save-to-file --show-agent-thinking

# Analyze observability JSON
python scripts/analyze_observability.py outputs/executions/*/agent_metrics_*.json
```

### Check Configuration
```bash
# Validate API keys (on startup)
python src/main.py --skip-validation=false

# Check timeout settings
python -c "from src.config.settings import settings; print(f'Topic timeout: {settings.topic_detection_timeout}s')"

# Check concurrency settings
python -c "from src.config.settings import settings; print(f'OpenAI: {settings.openai_concurrency}, Anthropic: {settings.anthropic_concurrency}')"
```

### Check File Locations
```bash
# List execution directories
railway run ls -la /app/outputs/executions/

# Find specific files
railway run find /app/outputs -name "*voice_of_customer*"

# Check file permissions
railway run ls -la /app/outputs/executions/*/
```

---

## 📚 Reference Documents

- **COMPREHENSIVE_FAILURE_AUDIT.md**: Detailed 47-question analysis
- **URGENT_INVESTIGATION_BRIEF.md**: Topic detection failure investigation
- **DEVELOPMENT_STANDARDS.md**: Error-log-first debugging workflow
- **RAILWAY_FILE_ACCESS.md**: File location patterns and access methods
- **SAMPLE_MODE_GUIDE.md**: Sample-mode usage and interpretation

---

## 🎯 Success Criteria

After fixing any failure mode:
- ✅ Observability JSON shows error_count = 0 (or acceptable level)
- ✅ Fallback metrics show timeout_rate < 10%
- ✅ Topic distribution shows reasonable spread (top 3 topics >10% each)
- ✅ Files visible in Railway Files tab
- ✅ Sample-mode runs successfully with real data

---

## 🆘 Emergency Contacts

**If all else fails:**
1. Check `.log` file for complete error traceback
2. Review observability JSON for error patterns
3. Run sample-mode to reproduce issue
4. Check `FAILURE_MODE_RUNBOOK.md` (this file) for specific failure mode
5. Review `COMPREHENSIVE_FAILURE_AUDIT.md` for detailed analysis

