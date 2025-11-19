# Observability Quick Start - Find LLM Failures Fast

**Problem:** "I can't see why LLM calls are failing"  
**Solution:** Structured JSON export + analysis script (ZERO risk, additive only)

---

## 🚀 How It Works (Automatic!)

**When you run analysis with `--show-agent-thinking`:**

1. ✅ Every LLM call is captured (prompt, response, tokens, model)
2. ✅ Errors are logged with context (timeout? rate limit? validation?)
3. ✅ Auto-exports to `.observability.json` file
4. ✅ Analysis script shows patterns and recommendations

**No code changes needed - just enable the flag!**

---

## 📋 Step-by-Step Usage

### **Step 1: Run Analysis with Agent Thinking Enabled**

**In Railway UI:**
- ✅ Check **"🧠 Show Agent Thinking"**
- ✅ Run your analysis (sample-mode or VOC)

**In CLI:**
```bash
python src/main.py voice-of-customer --time-period week --show-agent-thinking
```

### **Step 2: Find the Observability File**

**After run completes, look for:**
```
outputs/executions/<id>/agent_thinking_*.observability.json
```

**Or check console output:**
```
📊 Observability data exported: agent_thinking_Nov-18-2025_11-42PM.observability.json
```

### **Step 3: Analyze the Data**

```bash
python scripts/analyze_observability.py outputs/executions/.../agent_thinking_*.observability.json
```

**Output shows:**
- ✅ Success rate (how many LLM calls worked)
- ✅ Error breakdown (timeouts? rate limits? validation?)
- ✅ Agent performance (which agents failing most)
- ✅ Token usage (cost tracking)
- ✅ Recommendations (what to fix)

---

## 📊 Example Output

```
================================================================================
AGENT OBSERVABILITY ANALYSIS
================================================================================

📊 OVERALL STATISTICS:
   Total Events: 150
   Success Rate: 95.3%
   Errors: 7
   Total Tokens: 45,230

📋 EVENTS BY TYPE:
   prompt: 75
   response: 68
   error: 7

❌ ERROR ANALYSIS (7 errors):
   Error Types:
      timeout: 5
      validation: 2
   
   Errors by Agent:
      TopicDetectionAgent: 5
      SubTopicDetectionAgent: 2

   Sample Errors:
      1. [TopicDetectionAgent] timeout
         LLM call exceeded 30s timeout
      2. [TopicDetectionAgent] validation
         LLM returned invalid topic format

RECOMMENDATIONS:
❌ ERRORS DETECTED:
   1. Review error messages above
   2. Check if errors are timeouts (increase timeout)
   3. Check if errors are rate limits (reduce concurrency)
```

---

## 🔍 What This Tells You

### **If Success Rate < 95%:**
- **Timeouts:** Increase `llm_timeout` or reduce prompt size
- **Rate Limits:** Reduce `llm_semaphore` (fewer concurrent calls)
- **Validation Errors:** Fix prompts or response parsing

### **If Specific Agent Failing:**
- **TopicDetectionAgent:** Check fuzzy matching logic
- **SubTopicDetectionAgent:** Check LLM validation
- **Any Agent:** Review that agent's prompts/responses

### **If High Token Usage:**
- Shows cost per agent
- Identify expensive agents
- Optimize prompts to reduce tokens

---

## 🎯 Next Steps After Analysis

1. **If timeouts:** Increase timeout in agent config
2. **If rate limits:** Reduce semaphore (concurrent calls)
3. **If validation:** Check prompt format or response parsing
4. **If specific agent:** Review that agent's code

**All fixes are targeted - you know EXACTLY what to fix!**

---

## 💡 Pro Tips

**For Railway runs:**
- Files auto-save to execution directory
- Download `.observability.json` file
- Run analysis script locally
- Fix issues based on recommendations

**For debugging:**
- Compare observability files across runs
- Track success rate over time
- Identify regressions quickly

---

## 🚨 About Your Current Run

**Your completed VOC run:**
- Files ARE created (in `/app/outputs/` root)
- Browser can't find them (wrong directory - fixed in next deploy!)
- Use Railway CLI to retrieve (see `RAILWAY_FILE_ACCESS.md`)

**Next run (after deploy):**
- Files will be in execution directory ✅
- Visible in browser ✅
- Observability JSON included ✅


