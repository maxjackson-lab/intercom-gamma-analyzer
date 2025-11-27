# Post-Refactor Audit Protocol: VoC Pipeline & UX Improvements

**Context:**
You are auditing the completion of the "VoC Pipeline & UX Improvements" refactor. The goal is to verify that the Segmentation logic, Topic Normalization, Date Range selection, and File downloads are functioning correctly and that no regressions were introduced.

### Phase 1: Fin Tier Segmentation Verification
**Objective:** Ensure Billing/Refund conversations from paying customers are no longer mislabeled as "Free Fin-only".

1. **Run Analysis:**
   ```bash
   # Run a test mode analysis with verbose logging
   python src/main.py voice-of-customer --time-period week --test-mode --count 50 --verbose
   ```
2. **Inspect Logs (`segmentation_agent.log` or console output):**
   - Search for conversations containing keywords: "invoice", "charged", "subscription", "refund".
   - **Verify:** Are these marked as `is_paid: True`?
   - **Check:** Did the heuristic override missing plan metadata?
3. **Inspect Output Report:**
   - Look at the "Fin Overview" section.
   - **Verify:** Does the "Free Fin-only Volume" seem proportionate? (Should not be dominated by billing issues).

### Phase 2: Topic Normalization Efficiency
**Objective:** Confirm that "Could not normalize" warnings have decreased significantly.

1. **Log Analysis:**
   - Check the logs from the run in Phase 1.
   - **Grep:** `grep "Could not normalize" outputs/*.log`
   - **Verify:** Are common terms like "Business Plan Inquiry" now successfully mapping to canonical topics (e.g., "Billing", "Product Question")?
2. **Keyword Validation:**
   - Inspect `src/agents/topic_detection_agent.py` (or the new config file).
   - **Verify:** Are the new synonyms present?

### Phase 3: Custom Date Range Functional Test
**Objective:** Verify the end-to-end custom date picker flow.

1. **CLI Verification:**
   ```bash
   # Try running with explicit dates
   python src/main.py voice-of-customer --start-date 2025-11-01 --end-date 2025-11-03
   ```
   - **Verify:** Does it run without error? Does the output cover *only* those 3 days?
2. **UI Verification (Manual):**
   - Open Web UI.
   - Select "Custom" time period.
   - **Verify:** Do Date inputs appear?
   - **Verify:** Does clicking "Run" send the correct `--start-date` and `--end-date` flags to the backend? (Check browser network tab or server logs).
3. **Intercom Fetcher Check:**
   - **Verify:** Did `IntercomSDKService` respect the range? (Check logs for "Fetching conversations from 2025-11-01 to 2025-11-03").

### Phase 4: System Health & UX (ZIP & CLI)
**Objective:** Fix broken download and maintain CLI alignment.

1. **ZIP Download Test:**
   - Navigate to `/files` in the Web UI.
   - Click "Download ZIP" for a recent run.
   - **Verify:** Does a `.zip` file download? Can you unzip it and see the contents (Markdown, Logs, JSON)?
2. **CLI/Web Alignment:**
   - **Run:** `python scripts/check_cli_web_alignment.py`
   - **Verify:** Are the new `--start-date` and `--end-date` flags correctly mapped in `src/cli/schema.py` and `static/app.js`?

### Phase 5: Regression Check (The "Do No Harm" Test)
1. **Sample Mode:**
   - Run `python src/main.py sample-mode --count 20`
   - **Verify:** No crashes, schema validation passes.
2. **Standard Workflow:**
   - Run `python src/main.py voice-of-customer --time-period week` (standard dropdown).
   - **Verify:** Defaults still work (i.e., user doesn't *have* to provide custom dates).

### Deliverables Checklist
- [ ] Segmentation logic correctly identifies paid intent in absence of metadata.
- [ ] "Could not normalize" warnings reduced by >90%.
- [ ] Custom date ranges work via CLI and UI.
- [ ] ZIP downloads function correctly.
- [ ] No regressions in standard weekly workflows.



