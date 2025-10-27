# Testing Unified Flags

## ✅ Quick Test Commands

### Test in Web UI (Easiest):

1. **Open:** http://localhost:8000 (or your Railway deployment)
2. **Select:** "Agent Performance: Horatio Team"
3. **Time Period:** "Last Week"
4. **Check:** "🧪 Test Mode (Use Mock Data)"
5. **Check:** "📋 Audit Trail Mode"
6. **Click:** "▶️ Run Analysis"

**Expected Output:**
```
🤖 AI Model: OPENAI (if specified)
🔍 Verbose Logging: ENABLED (DEBUG level)
🧪 Test Mode: ENABLED (100 mock conversations)
   No API calls will be made - using generated test data
📋 Audit Trail Mode: ENABLED
Horatio Performance Analysis
Date Range: 2025-10-20 to 2025-10-27
```

---

### Test in CLI:

```bash
# Test agent-performance with all unified flags
python src/main.py agent-performance \
  --agent horatio \
  --time-period week \
  --test-mode \
  --test-data-count large \
  --verbose \
  --audit-trail \
  --generate-gamma

# Test fin-escalations with unified flags
python src/main.py fin-escalations \
  --time-period month \
  --test-mode \
  --test-data-count medium \
  --verbose \
  --audit-trail

# Test canny-analysis with unified flags
python src/main.py canny-analysis \
  --time-period week \
  --test-mode \
  --test-data-count small \
  --verbose

# Test voice-of-customer (already had unified flags)
python src/main.py voice-of-customer \
  --time-period week \
  --test-mode \
  --test-data-count large \
  --verbose \
  --audit-trail \
  --generate-gamma
```

---

## 🔍 What to Check

### 1. **Flags Accepted**
All commands should accept:
- `--test-mode`
- `--test-data-count` (with presets: micro, small, medium, large, xlarge)
- `--verbose`
- `--audit-trail`
- `--generate-gamma`
- `--output-format`
- `--time-period` (week/month/quarter)
- `--ai-model` (for agent-performance)

### 2. **Preset Parsing**
```bash
--test-data-count micro    # Should show: 100 mock conversations
--test-data-count small    # Should show: 500 mock conversations
--test-data-count medium   # Should show: 1000 mock conversations
--test-data-count large    # Should show: 5000 mock conversations
--test-data-count xlarge   # Should show: 10000 mock conversations
--test-data-count 2500     # Should show: 2500 mock conversations (custom)
```

### 3. **Output Messages**
Look for these indicators:
```
🔍 Verbose Logging: ENABLED (DEBUG level)       ← --verbose works
🧪 Test Mode: ENABLED (5000 mock conversations) ← --test-mode works
📋 Audit Trail Mode: ENABLED                    ← --audit-trail works
🤖 AI Model: CLAUDE                             ← --ai-model works
```

### 4. **Error Handling**
```bash
# Invalid preset
--test-data-count invalid
# Expected: Error message about valid presets

# Missing time-period or dates
canny-analysis (no --time-period or --start-date)
# Expected: Error message asking for time-period or dates
```

---

## 🎯 Validation Checklist

- [ ] All commands accept `--test-mode`
- [ ] All commands accept `--verbose`
- [ ] All commands accept `--audit-trail`
- [ ] All commands accept `--generate-gamma`
- [ ] All commands accept `--output-format`
- [ ] All commands accept `--time-period`
- [ ] Presets work (micro/small/medium/large/xlarge)
- [ ] Custom numbers work (e.g., 2500)
- [ ] Web UI passes flags correctly
- [ ] Error messages are helpful
- [ ] Fin detection fix reduces human agent count

---

## 📊 Expected Results

### Before Fix:
```
Human Support: ~2000+ conversations
```

### After Fix:
```
Human Support: ~200-500 conversations (more realistic)
Fin AI Resolved: ~1500-1800 conversations (increased)
```

The fix should shift many conversations from "unknown human" to "fin_resolved" because they were assigned but had no actual admin response.

---

## 🐛 Known Issues

None at this time. If you encounter errors:

1. **Check Python environment:** Make sure dependencies are installed
2. **Check working directory:** Run from project root
3. **Check imports:** `src/` modules must be importable
4. **Check environment variables:** API keys, etc.

---

## 📝 Notes

- **Web UI:** Already compatible, no changes needed
- **Backward compatible:** Old flags still work
- **Default values:** Same as before
- **Test mode:** Generates fake data, no API calls

---

## ✅ Success Indicators

You'll know it worked if:

1. **No errors** when running commands with new flags
2. **Helpful messages** about test mode, verbose logging, audit trail
3. **Preset parsing** shows correct conversation counts
4. **Web UI** runs analyses without errors
5. **Fin detection** shows more realistic numbers (fewer "unknown" humans)

---

## 🚀 Next Steps After Validation

If everything works:

1. Run actual analysis (without `--test-mode`) to see real Fin detection numbers
2. Compare before/after human agent counts
3. Deploy to production if numbers look correct
4. (Optional) Apply same pattern to remaining commands

If issues found:

1. Document the error
2. Share with me for debugging
3. We'll fix and re-test

