# Aggressive Documentation Cleanup Plan

**Current:** 106 markdown files  
**Target:** ~40-50 essential files  
**Remove:** ~50-60 redundant files

---

## DELETE Category 1: Old Fix/Summary Documents (October)

These are historical implementation notes - the code is done, Git has the history:

- [ ] `ALL_FIXES_COMPREHENSIVE_SUMMARY.md` - Generic October summary
- [ ] `BUG_FIXES_SUMMARY.md` - Old bug fixes
- [ ] `DATE_RANGE_FIX_SUMMARY.md` - Date range fix (done)
- [ ] `CATEGORY_DEEP_DIVE_FIX.md` - Category fix (done)
- [ ] `FIN_TOPIC_BREAKDOWN_FIX.md` - Fin topic fix (done)
- [ ] `GAMMA_URL_FIX.md` - Gamma URL fix (done)
- [ ] `IMPORT_FIXES_SUMMARY.md` - Import fixes (done)
- [ ] `PYDANTIC_WARNINGS_FIX.md` - Warnings fix (done)
- [ ] `RACE_CONDITION_FIX_SUMMARY.md` - Race condition fix (done)
- [ ] `SAL_VS_HUMAN_FIX.md` - Sal detection fix (done)
- [ ] `TIMEOUT_FIX_DIAGRAM.md` - Timeout diagram (historical)
- [ ] `VOC_BRIDGE_SUMMARY.md` - VOC bridge summary
- [ ] `IMPORT_AUDIT_AND_TEST_MODE_SUMMARY.md` - Import audit

**Count:** 13 files

---

## DELETE Category 2: Old Status/Audit Reports (October)

Point-in-time reports that are no longer relevant:

- [ ] `DEPLOYMENT_STATUS_OCTOBER_25.md` - October deployment status
- [ ] `FINAL_SUMMARY_OCTOBER_25.md` - October summary
- [ ] `FIXES_SESSION_OCTOBER_27.md` - October 27 session
- [ ] `PATH_B_STABILIZATION_STATUS.md` - Old stabilization status
- [ ] `CONSISTENCY_VERIFICATION_SUMMARY.md` - Old verification
- [ ] `VALIDATION_AUDIT_REPORT.md` - Old audit
- [ ] `TODO_AUDIT_REPORT.md` - Old TODO audit
- [ ] `FRONTEND_FUNCTIONALITY_AUDIT.md` - Frontend audit
- [ ] `FIN_DETECTION_AUDIT.md` - Fin detection audit
- [ ] `SDK_MIGRATION_AUDIT.md` - SDK migration audit
- [ ] `DOCUMENTATION_AUDIT_CSAT_TROUBLESHOOTING.md` - Documentation audit
- [ ] `SDK_COMPLETE_AUDIT_SUMMARY.md` - SDK audit summary
- [ ] `CANNY_INTEGRATION_AUDIT.md` - Canny audit

**Count:** 13 files

---

## DELETE Category 3: Redundant Implementation Summaries

Multiple summaries saying the same thing:

- [ ] `IMPLEMENTATION_SUMMARY.md` - Generic implementation
- [ ] `TODAY_IMPLEMENTATION_SUMMARY.md` - "Today" (what day?)
- [ ] `PHASE1_QA_METRICS_IMPLEMENTATION.md` - Phase 1
- [ ] `PHASE2_COMPLETE_SUMMARY.md` - Phase 2
- [ ] `PHASE_2_TRENDS_IMPLEMENTATION.md` - Phase 2 trends
- [ ] `REVIEW_COMMENTS_IMPLEMENTATION.md` - Review comments
- [ ] `INTERCOM_LINKS_UI_IMPROVEMENTS.md` - UI improvements
- [ ] `WEB_UI_AGENT_COACHING_INTEGRATION.md` - UI integration

**Count:** 8 files

---

## DELETE Category 4: Duplicate Canny Docs

Keep one comprehensive, delete the rest:

**KEEP:** `CANNY_COMPLETE_IMPLEMENTATION.md` (most complete)

**DELETE:**
- [ ] `CANNY_INTEGRATION_SUMMARY.md` - Duplicate
- [ ] `CANNY_QUICK_STATUS.md` - Status doc

**Count:** 2 files

---

## DELETE Category 5: Duplicate Audit Trail Docs

**KEEP:** `AUDIT_TRAIL_IMPLEMENTATION.md`

**DELETE:**
- [ ] `AUDIT_TRAIL_STATUS.md` - Just status

**Count:** 1 file

---

## DELETE Category 6: Redundant Fin Analysis Docs

We have too many Fin docs. Consolidate:

**KEEP:** 
- `FINAL_FIN_FIX_COMPLETE.md` - Complete implementation
- `FIN_RESOLUTION_LOGIC_REDESIGN.md` - Logic contract
- `FIN_AND_POLLING_FIXES_IMPLEMENTED.md` - Nov 4 changes (recent)

**DELETE:**
- [ ] `FIN_ANALYSIS_ROOT_CAUSE.md` - Historical analysis
- [ ] `FIN_ATTRIBUTION_QUESTION.md` - Old question doc
- [ ] `FIN_VS_HUMAN_ATTRIBUTION.md` - Old attribution doc
- [ ] `FIN_ANALYSIS_FIX_NUANCED.md` - Design doc (implemented in FIN_AND_POLLING_FIXES)

**Count:** 4 files

---

## DELETE Category 7: Old Research/Question Docs

- [ ] `CLAUDE_RESEARCH_QUESTIONS.md` - Research questions (answered)
- [ ] `CHURN_CORRELATION_RESEARCH.md` - Research (implemented)
- [ ] `CODERABBIT_REVIEW.md` - Code review (historical)

**Count:** 3 files

---

## DELETE Category 8: Generic/Vague Improvement Docs

- [ ] `CODE_IMPROVEMENTS.md` - Vague improvements
- [ ] `CODE_QUALITY_IMPROVEMENTS.md` - Vague quality doc

**Count:** 2 files

---

## DELETE Category 9: Old Plan Documents

- [ ] `CSAT_AND_TRENDS_IMPLEMENTATION_PLAN.md` - Old plan (implemented)
- [ ] `UI_AND_TRENDS_IMPLEMENTATION_PLAN.md` - Old plan (implemented)
- [ ] `CLI_FLAGS_UNIFICATION_PLAN.md` - Old plan

**Count:** 3 files

---

## DELETE Category 10: Old Deployment/Testing Docs

- [ ] `intercom-links-and-ui-improvements.plan.md` - Old plan file

**Count:** 1 file

---

## TOTAL DELETIONS: 50 files

**Current:** 106 files  
**After cleanup:** ~56 files  
**Reduction:** 47%

---

## What STAYS (Essential Documentation)

### Core System Docs (5 files):
- `README.md` - User documentation
- `QUICKSTART.md` - Quick start
- `APP_OVERVIEW.md` - What the app does
- `SYSTEM_ARCHITECTURE_GUIDE.md` - PM-level architecture (Nov 4)
- `INSIGHT_SYSTEM_REDESIGN_COMPLETE.md` - Insight redesign plan (Nov 4)

### Recent Implementation (Nov 4) (6 files):
- `COMPREHENSIVE_FIX_SUMMARY_NOV4.md` - Today's changes
- `FIN_AND_POLLING_FIXES_IMPLEMENTED.md` - Fin + polling fixes
- `SCHEMA_IMPROVEMENTS_IMPLEMENTATION.md` - Schema review
- `IMPLEMENTATION_CHECKLIST.md` - Verification
- `STRIPE_AS_SOURCE_OF_TRUTH.md` - Tier detection
- `TIER_SEGMENTATION_CLARIFICATION.md` - Tier explanation

### Feature Guides (~15 files):
- `VOC_GUIDE.md`, `GAMMA_GUIDE.md`, `COACHING_QUICK_REFERENCE.md`
- `INDIVIDUAL_AGENT_PERFORMANCE_GUIDE.md`, `SEGMENTATION_VALIDATION_GUIDE.md`
- `EXAMPLE_EXTRACTION_VALIDATION_GUIDE.md`, `ESCALATION_TRACKING_GUIDE.md`
- `SAMPLE_MODE_GUIDE.md`, `TEST_MODE_GUIDE.md`, `EXPORT_GUIDE.md`
- `VOC_GAMMA_VALIDATION_GUIDE.md`, `VOC_DEVELOPER_GUIDE.md`
- `FRONTEND_UI_GUIDE.md`, `DEPLOYMENT_GUIDE.md`
- `WORST_CSAT_EXAMPLES_FEATURE.md`

### Key Implementation Docs (~10 files):
- `FINAL_FIN_FIX_COMPLETE.md` - Fin logic
- `FIN_RESOLUTION_LOGIC_REDESIGN.md` - Fin contract
- `AGENT_COACHING_IMPLEMENTATION_SUMMARY.md` - Coaching
- `AGENT_PERFORMANCE_IMPLEMENTATION_COMPLETE.md` - Performance
- `CANNY_COMPLETE_IMPLEMENTATION.md` - Canny integration
- `CSAT_INTEGRATION_COMPLETE.md` - CSAT
- `QA_METRICS_FULL_INTEGRATION_SUMMARY.md` - QA metrics
- `AUDIT_TRAIL_IMPLEMENTATION.md` - Audit trail
- `CHURN_CORRELATION_IMPLEMENTATION.md` - Churn analysis
- `STORY_DRIVEN_ANALYSIS_IMPLEMENTATION.md` - Story-driven
- `VOC_TAXONOMY_IMPLEMENTATION.md` - Taxonomy

### Schema/Technical Docs (~5 files):
- `INTERCOM_SCHEMA_ANALYSIS.md` - Field analysis
- `SDK_IMPLEMENTATION_REVIEW.md` - SDK review
- `SDK_REVIEW_IMPLEMENTATIONS.md` - SDK implementations
- `DEVELOPMENT_STANDARDS.md` - Dev standards
- `TESTING.md` - Testing guide

### Misc Keep (~10 files):
- `FEATURE_FLAGS.md`, `HORATIO_NOT_FOUND_DIAGNOSIS.md`
- `PIPELINE_GAMMA_INTEGRATION.md`, `POLLING_ERROR_STATUS_BUG_FIX.md`
- `RAILWAY_TROUBLESHOOTING.md`, `MULTI_AGENT_QA_CHECKLIST.md`
- `HYBRID_TOPIC_DETECTION_APPROACH.md`, `TEST_UNIFIED_FLAGS.md`
- `FIN_ATTRIBUTION_QUESTION.md` (actually useful reference)
- Other specific technical references

**Total Keep:** ~56 files

---

## Proceed with Deletion?

This will remove 50 files (mostly October summaries and old fix docs).

