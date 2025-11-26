# Urgent Investigation Brief

## Executive Summary
This document summarizes the investigation and resolution of four critical issues in the Intercom Analysis Tool:
1.  **Fin Tier Segmentation**: Billing conversations from free users were misclassified.
2.  **Topic Normalization**: LLM-detected topics were being rejected by the normalization layer.
3.  **Date Range Flexibility**: UI hid custom date inputs despite backend support.
4.  **ZIP Download**: Lack of logging and error handling made debugging difficult.

All issues have been addressed with surgical fixes that maintain backward compatibility.

---

## Issue 1: Fin Tier Segmentation

### Problem
Billing conversations from free users were correctly identified as "Free" tier but then labeled as "Fin-only" because no human agent was assigned. This is technically correct but misleading for billing disputes that require human attention (even if not yet assigned).

### Root Cause
Tier classification happened *before* topic detection, and the "Free" tier logic didn't account for high-intent keywords like "refund" or "charge".

### Solution
Modified `SegmentationAgent._extract_customer_tier` to include a keyword check for "Free" tier conversations. If billing keywords (`refund`, `charge`, `invoice`, etc.) are found, the conversation is promoted to `TEAM` (paid) tier to ensure it flows through the paid support logic.

**Files Modified:** `src/agents/segmentation_agent.py`

---

## Issue 2: Topic Normalization Fallbacks

### Problem
The `TopicDetectionAgent` was rejecting valid LLM outputs like "Refund Request" because they didn't exactly match the canonical "Billing" topic. This caused the system to fall back to keyword matching, ignoring the LLM's semantic understanding.

### Root Cause
The `_normalize_llm_topic` method had a limited semantic map.

### Solution
1.  Expanded the `semantic_map` with 30+ new mappings (e.g., `issue` -> `Bug`, `how do` -> `Product Question`).
2.  Added instrumentation to log raw LLM topics and count normalization failures.
3.  Added `_suggest_keyword_expansions` helper to analyze unmapped topics.

**Files Modified:** `src/agents/topic_detection_agent.py`

---

## Issue 3: Date Range Flexibility

### Problem
The backend supported custom date ranges (`--start-date`, `--end-date`), but the Web UI only showed the "Time Period" dropdown, hiding the custom date inputs.

### Root Cause
`app.js` lacked logic to toggle the visibility of the custom date input container based on the dropdown selection.

### Solution
1.  Updated `app.js` to show/hide `customDateInputs` when "Custom Range" is selected.
2.  Added validation to ensure start date <= end date.
3.  Added warnings for large date ranges (>31 days).
4.  Updated CLI output to show the custom range clearly.
5.  Added optional `VOC_STRICT_DATE_LIMITS=1` environment variable to enforce a 90-day ceiling for automation pipelines that require hard limits.

**Files Modified:** `static/app.js`, `src/cli/voc_commands.py`

---

## Issue 4: ZIP Download

### Problem
ZIP downloads would sometimes fail silently or generically, making it hard to know if the issue was missing files, permissions, or timeouts.

### Root Cause
Lack of detailed logging and specific error handling in the API routes and frontend.

### Solution
1.  Added detailed logging to `download_outputs_zip` and `download_folder_zip` (scanning paths, file counts).
2.  Added robust error handling for `FileNotFound` and `BadZipFile` errors.
3.  Added a `downloadWithRetry` helper in the frontend to handle transient network issues.

**Files Modified:** `static/file_browser.js`, `deploy/web/routes_files.py`

---

## Testing Recommendations

1.  **Segmentation**: Run `sample-mode` on a known free user billing conversation. Verify it is classified as `TEAM` (Paid).
2.  **Topic Normalization**: Check logs for `Top unmapped LLM topics`.
3.  **Date Range**: Select "Custom Range" in UI and verify date inputs appear. Run a 35-day analysis and check for the warning.
4.  **ZIP**: Try downloading a non-existent folder ZIP via API to verify error handling.

## Future Enhancements

*   **Deep Topic Dives**: Add `--focus-topic` flag to run analysis only on specific topics.
*   **Temporal Rollups**: Add monthly aggregation for long-term trend analysis.
*   **BPO Agent Reviews**: Integrate BPO agent performance data into the main dashboard.
