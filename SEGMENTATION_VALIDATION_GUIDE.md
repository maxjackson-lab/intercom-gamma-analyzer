# Segmentation Validation Guide: Horatio Agent Detection

## Overview

This guide helps you manually validate that Horatio agent detection works correctly with real Intercom data in your Railway deployment.

### What Was Fixed

The Horatio agent detection system now extracts admin emails from three sources:
1. **`conversation_parts.conversation_parts[].author.email`** - Admin replies in the conversation thread
2. **`source.author.email`** - Initial message if sent by an admin
3. **`assignee.email`** - Assigned agent email

The system uses exact domain matching with `endswith('@hirehoratio.co')` to identify Horatio agents.

### Expected Outcome

After validation, you should see **non-zero Horatio counts** in your agent distribution logs, such as:
```
Agent distribution: {'escalated': 2, 'horatio': 15, 'boldr': 3, 'fin_ai': 25, 'unknown': 5}
```

---

## Prerequisites

Before starting validation:

- ✅ Railway deployment is running
- ✅ Access to Railway logs (via Railway dashboard or CLI)
- ✅ Intercom access token is configured in Railway environment variables
- ✅ At least some conversations with Horatio agents exist in your Intercom data

---

## Quick Validation Test (5 minutes)

This is the fastest way to verify the fix works.

### Step 1: Run a Small Test on Railway

1. **Access your Railway deployment:**
   - Use the Railway web interface at https://railway.app
   - Or use Railway CLI: `railway logs --follow`

2. **Trigger an analysis:**
   - Use the web interface or API endpoint
   - Select "VoC: Hilary Format" mode (uses SegmentationAgent)
   - Choose "Yesterday" date range
   - Limit to 50 conversations for speed

3. **Example API call (if using CLI):**
   ```bash
   curl -X POST https://your-railway-app.up.railway.app/analyze \
     -H "Content-Type: application/json" \
     -d '{
       "analysis_type": "voc_hilary",
       "date_range": "yesterday",
       "max_conversations": 50
     }'
   ```

### Step 2: Check Railway Logs

1. **Look for SegmentationAgent logs:**
   ```
   SegmentationAgent: Completed in 0.45s
   Paid: 25 (50.0%)
   Free: 20 (40.0%)
   Agent distribution: {'escalated': 2, 'horatio': 15, 'boldr': 3, 'fin_ai': 20, 'unknown': 5}
   ```

2. **Key indicators:**
   - ✅ `'horatio': 15` (or any non-zero number)
   - ✅ No errors or exceptions in logs
   - ✅ Total percentages add up to ~100%

### Step 3: Verify Results

**If `'horatio': 0`:**
- ❌ Detection is still broken → Proceed to [Detailed Validation Test](#detailed-validation-test-15-minutes)

**If `'horatio': > 0`:**
- ✅ Detection is working! → Proceed to [Expected Results](#expected-results)

### Step 4: Check Debug Logs (Optional)

If you enabled debug logging (see [Enable Debug Logging](#enable-debug-logging)), look for:

```
DEBUG: Classifying conversation conv_123: admin_assignee_id=456, ai_participated=False
DEBUG: Found 2 admin emails: ['agent@hirehoratio.co', 'support@example.com']
DEBUG: Horatio agent detected via email: agent@hirehoratio.co
```

These logs confirm:
- Emails are being extracted correctly
- The Horatio domain is being matched
- Classification is returning the correct agent type

---

## Detailed Validation Test (15 minutes)

For thorough validation when Quick Test shows issues.

### Step 1: Enable Debug Logging

1. **Set environment variable in Railway:**
   - Go to your Railway project → Variables
   - Add or update: `LOG_LEVEL=DEBUG`
   - Redeploy or restart the service

2. **Verify debug logging is active:**
   - Check logs for `DEBUG:` level messages
   - Should see detailed classification logs

### Step 2: Find a Known Horatio Conversation

1. **Use Intercom UI to find a Horatio conversation:**
   - Go to Intercom inbox
   - Find a conversation handled by a Horatio agent
   - Note the conversation ID (e.g., `12345678`)
   - Note the agent's email (should end in `@hirehoratio.co`)

2. **Identify the date range:**
   - Note when the conversation was created
   - Use this date range for your test

### Step 3: Run Analysis with Known Data

1. **Run analysis for the specific date range:**
   ```bash
   curl -X POST https://your-railway-app.up.railway.app/analyze \
     -H "Content-Type: application/json" \
     -d '{
       "analysis_type": "voc_hilary",
       "start_date": "2024-01-15",
       "end_date": "2024-01-15",
       "max_conversations": 100
     }'
   ```

2. **Search logs for the conversation ID:**
   - Use Railway logs search: `conv_12345678`
   - Look for debug logs showing email extraction
   - Verify the Horatio email was found

### Step 4: Verify Classification

**Expected log output:**
```
DEBUG: Classifying conversation conv_12345678: admin_assignee_id=456, ai_participated=False
DEBUG: Found 1 admin emails: ['agent@hirehoratio.co']
DEBUG: Horatio agent detected via email: agent@hirehoratio.co
```

**If you don't see these logs:**
- Check that the conversation was included in the date range
- Verify the conversation ID is correct
- Check if the email field exists in the Intercom API response

### Step 5: Verify Agent Distribution

1. **Check final distribution:**
   ```
   Agent distribution: {'escalated': 2, 'horatio': 15, 'boldr': 3, 'fin_ai': 25, 'unknown': 5}
   ```

2. **Calculate percentages:**
   - Total conversations: 50
   - Horatio: 15 (30%)
   - Expected if Horatio is your primary Tier 1: 20-40%

3. **Compare with Intercom UI:**
   - Manually count Horatio conversations in Intercom
   - Compare with logged counts
   - Small differences (<5%) are acceptable due to filtering

---

## Troubleshooting

### If Horatio Count is Still 0

#### A. Check if Horatio Agents Exist in Date Range

1. **Use Intercom UI search:**
   - Go to Intercom → Inbox
   - Search for conversations with Horatio agents
   - Filter by your test date range

2. **If no Horatio conversations found:**
   - ✅ Detection is working correctly (0 is accurate)
   - Try a wider date range (e.g., "Last 7 days")
   - Use "All Time" to find any Horatio conversations

#### B. Check Email Domain

1. **Verify Horatio agents use `@hirehoratio.co`:**
   - Check several Horatio agent emails in Intercom
   - If they use a different domain (e.g., `@horatio.com`):
     - Update line 250 in `src/agents/segmentation_agent.py`:
       ```python
       if email.endswith('@horatio.com'):  # Change from @hirehoratio.co
       ```
     - Also update line 28 in `src/agents/agent_performance_agent.py`

2. **Redeploy after changes:**
   ```bash
   git add src/agents/segmentation_agent.py src/agents/agent_performance_agent.py
   git commit -m "Update Horatio email domain"
   git push
   ```

#### C. Check Conversation Data Structure

1. **Add temporary logging to dump conversation JSON:**
   - In `src/agents/segmentation_agent.py`, add at line 200:
     ```python
     if 'horatio' in conv.get('full_text', '').lower():
         self.logger.debug(f"Sample conversation JSON: {json.dumps(conv, indent=2)}")
     ```

2. **Run analysis and check logs for JSON output**

3. **Verify structure matches expectations:**
   - `conversation_parts.conversation_parts` exists
   - `author.email` field is present
   - `author.type` is 'admin'

4. **Compare with Intercom API docs:**
   - https://developers.intercom.com/docs/references/rest-api/api.intercom.io/Conversations/conversation/

#### D. Check for Data Preprocessing Issues

1. **Verify `src/services/data_preprocessor.py` isn't stripping emails:**
   - Search for any code that removes or modifies email fields
   - Check if `conversation_parts` is being filtered

2. **Check if `full_text` generation includes admin emails:**
   - It shouldn't need to, but verify it's not interfering
   - Horatio detection should work via email fields only

### If Horatio Count is Unexpectedly Low

#### A. Check for Mixed Agent Types

1. **Escalation takes priority:**
   - If a Horatio conversation was escalated to Max/Dae-Ho/Hilary
   - It will be classified as 'escalated', not 'horatio'
   - This is correct behavior

2. **Check escalation logs:**
   ```
   DEBUG: Escalated conversation detected via email: max.jackson@example.com
   ```

#### B. Check for Missing Email Fields

1. **Some Horatio agents may not have emails in API response:**
   - Check if `admin_assignee_id` exists but no email
   - These will be classified as `('paid', 'unknown')`

2. **Example log:**
   ```
   DEBUG: Found 0 admin emails
   DEBUG: Generic paid customer detected (unknown agent type) in conversation conv_123
   ```

3. **Solution:**
   - This is a limitation of the Intercom API data
   - Consider using text pattern matching as fallback
   - Current implementation already has text fallback at line 258

---

## Expected Results

For a typical dataset with Horatio as primary Tier 1 support:

| Agent Type | Expected % | Example Count (100 convs) |
|------------|------------|---------------------------|
| Horatio    | 20-40%     | 25                        |
| Boldr      | 10-20%     | 15                        |
| Escalated  | 5-10%      | 7                         |
| Fin AI     | 30-50%     | 40                        |
| Unknown    | <10%       | 13                        |

### Interpreting Your Results

**If your distribution is very different:**

1. **Horatio: 0-5%**
   - Detection may be broken (if you know Horatio handles many conversations)
   - OR your support model has changed (AI-first approach)

2. **Horatio: 60-80%**
   - You may have limited Fin AI deployment
   - OR the date range is during a high-volume period

3. **Unknown: >20%**
   - Many conversations lack clear agent identification
   - Consider improving Intercom tagging practices

4. **Fin AI: 70-90%**
   - Strong AI-first support model
   - Paid customers may be rare in your dataset

### Validation Checklist

- [ ] Ran analysis with "Yesterday" date range
- [ ] Checked Railway logs for "Agent distribution" line
- [ ] Verified Horatio count is > 0
- [ ] Enabled debug logging and verified email extraction logs
- [ ] Tested with a known Horatio conversation ID
- [ ] Verified percentages add up to 100%
- [ ] Checked that paid + free + unknown = total conversations
- [ ] Compared results with Intercom UI data (sample check)
- [ ] Documented any discrepancies or issues

---

## Next Steps

### If Validation Successful

1. **Disable debug logging:**
   - Set `LOG_LEVEL=INFO` in Railway environment
   - Redeploy to reduce log volume

2. **Run full analysis:**
   - Use larger date ranges (e.g., "Last 30 days")
   - Remove conversation limits
   - Generate comprehensive reports

3. **Generate Horatio performance reports:**
   - Use `analysis_type: "agent_performance"`
   - Filter by `agent_filter: "horatio"`
   - Analyze FCR, resolution time, escalation patterns

4. **Monitor agent distribution trends:**
   - Run weekly or monthly analyses
   - Track changes in Horatio usage over time
   - Compare with business metrics

### If Issues Remain

1. **Document specific error messages:**
   - Copy exact error text from logs
   - Note the conversation IDs that failed
   - Screenshot relevant Intercom UI data

2. **Provide sample conversation JSON:**
   - Use debug logging to capture a sanitized conversation
   - Remove customer PII (names, emails)
   - Share structure for review

3. **Determine if issue is data-specific or code-specific:**
   - Does it happen with all Horatio conversations?
   - Or only specific ones?
   - Can you reproduce with test data?

4. **Review test files:**
   - Run `pytest tests/test_segmentation_agent.py -v`
   - Check if unit tests pass locally
   - Compare test fixtures with real data structure

---

## Reference Files

Key files involved in Horatio detection:

| File | Lines | Purpose |
|------|-------|---------|
| `src/agents/segmentation_agent.py` | 185-278 | Main classification logic, email extraction |
| `src/agents/agent_performance_agent.py` | 26-41 | Agent patterns, uses segmentation results |
| `src/agents/topic_orchestrator.py` | - | Calls SegmentationAgent in multi-agent pipeline |
| `src/services/orchestrator.py` | - | Orchestrates multi-agent analysis |
| `tests/test_segmentation_agent.py` | - | Unit tests for segmentation logic |
| `tests/integration/test_segmentation_integration.py` | - | Integration tests with realistic data |
| `scripts/test_horatio_detection.py` | - | Standalone test script for quick validation |

---

## Contact & Support

If validation fails or you need help:

1. **Run local tests:**
   ```bash
   pytest tests/test_segmentation_agent.py -v
   python scripts/test_horatio_detection.py
   ```

2. **Check implementation:**
   - Review `src/agents/segmentation_agent.py` lines 209-255
   - Verify email extraction logic matches your Intercom data

3. **Verify Intercom API structure:**
   - Compare your Intercom data with API documentation
   - Check if field names or structure has changed

4. **Enable comprehensive logging:**
   - Set `LOG_LEVEL=DEBUG`
   - Run with small dataset (10-20 conversations)
   - Review logs line-by-line for classification decisions

---

## Appendix: Command Reference

### Railway CLI Commands

```bash
# Follow logs in real-time
railway logs --follow

# Search logs for specific conversation
railway logs | grep "conv_12345678"

# Set environment variable
railway variables set LOG_LEVEL=DEBUG

# Redeploy
railway up
```

### API Test Commands

```bash
# Quick test with yesterday's data
curl -X POST https://your-app.up.railway.app/analyze \
  -H "Content-Type: application/json" \
  -d '{"analysis_type": "voc_hilary", "date_range": "yesterday", "max_conversations": 50}'

# Test with specific date range
curl -X POST https://your-app.up.railway.app/analyze \
  -H "Content-Type: application/json" \
  -d '{"analysis_type": "voc_hilary", "start_date": "2024-01-15", "end_date": "2024-01-15"}'
```

### Local Test Commands

```bash
# Run unit tests
pytest tests/test_segmentation_agent.py -v

# Run integration tests
pytest tests/integration/test_segmentation_integration.py -v

# Run standalone test script
python scripts/test_horatio_detection.py

# Run with verbose output
python scripts/test_horatio_detection.py --verbose
```

---

**Last Updated:** October 23, 2025  
**Version:** 1.0
