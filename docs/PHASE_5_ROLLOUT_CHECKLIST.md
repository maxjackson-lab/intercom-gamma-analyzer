# Phase 5 Rollout Checklist: DeepAgents Adoption

**Status:** NOT_STARTED

This checklist provides step-by-step execution guidance for the DeepAgents orchestrator rollout. Only proceed if Phase 5 decision in `docs/LANGCHAIN_ARCHITECTURE_MIGRATION.md` is **ADOPT**.

---

## Pre-Rollout Validation

- [ ] Phase 5 decision documented in `docs/LANGCHAIN_ARCHITECTURE_MIGRATION.md` with ADOPT recommendation
- [ ] Pilot analysis shows ≥20% critic score improvement and ≤25% runtime penalty
- [ ] `python scripts/validate_phase5_decision.py` passes (exit code 0)
- [ ] Peer review completed (minimum 2 reviewers)
- [ ] Stakeholder approval obtained (product, engineering leads)

---

## Phase 5.1: Soft Launch (Week 1-2)

**Goal:** Make DeepAgents available without changing defaults.

### Configuration

- [ ] Verify `deepagents` dependency is commented in `requirements.txt` (optional install)
- [ ] Confirm `enable_deep_orchestrator` defaults to `False` in `src/config/settings.py`
- [ ] Test installation: uncomment deepagents, run `pip install -r requirements.txt`, verify import

### Documentation

- [ ] Update `README.md` with clear installation instructions for deepagents
- [ ] Add `--orchestrator=deep` examples to CLI help text (`src/main.py --help`)
- [ ] Document orchestrator selection in `DEVELOPER_ONBOARDING.md`
- [ ] Create internal Slack/wiki announcement about pilot availability

### Telemetry & Monitoring

- [ ] Set up telemetry tracking for orchestrator usage (legacy vs deep counts)
- [ ] Configure log aggregation to capture orchestrator selection per run
- [ ] Verify `ExecutionStateManager` logs include orchestrator type

### Validation

- [ ] Run `./scripts/run_all_checks.sh` to ensure no regressions
- [ ] Execute sample-mode with both orchestrators:
  - [ ] `python src/main.py voice-of-customer --time-period week --test-mode --orchestrator legacy`
  - [ ] `python src/main.py voice-of-customer --time-period week --test-mode --orchestrator deep`
- [ ] Deploy to Railway staging with `ENABLE_DEEP_ORCHESTRATOR=false`
- [ ] Monitor staging for 1 week, collect feedback

### Sign-off

- [ ] Phase 5.1 complete, ready for Phase 5.2
- [ ] Date: ____________
- [ ] Reviewer: ____________

---

## Phase 5.2: Gradual Rollout (Week 3-6)

**Goal:** Enable DeepAgents for internal users, gather feedback.

### Internal Enablement

- [ ] Enable deep orchestrator for internal test accounts
- [ ] Update Railway staging environment: `ENABLE_DEEP_ORCHESTRATOR=true`
- [ ] Run weekly pilot comparisons to track quality trends
- [ ] Document any issues discovered during staging (create tickets, prioritize)

### User Interface

- [ ] Update web UI to show orchestrator selection prominently
- [ ] Verify "DeepAgents Supervisor" toggle works correctly in web UI
- [ ] Test toggle saves preference and applies to runs

### Monitoring Dashboard

Create monitoring dashboard (Grafana/Railway) for:

- [ ] Orchestrator usage split (legacy vs deep)
- [ ] Mean critic scores per orchestrator (daily/weekly aggregates)
- [ ] Mean runtime per orchestrator
- [ ] Error rates per orchestrator
- [ ] Token usage comparison

### Feedback & Issues

- [ ] Document known issues and workarounds in `TROUBLESHOOTING.md`
- [ ] Conduct user training session (if needed)
- [ ] Address critical issues before proceeding to Phase 5.3

### Sign-off

- [ ] Phase 5.2 complete, ready for Phase 5.3
- [ ] All critical issues resolved
- [ ] Date: ____________
- [ ] Reviewer: ____________

---

## Phase 5.3: Full Adoption (Week 7-8)

**Goal:** Switch CLI default to DeepAgents orchestrator.

### Configuration Changes

- [ ] Update `src/config/settings.py`: set `enable_deep_orchestrator=True` as default
- [ ] Update CLI default behavior:
  - [ ] `--orchestrator` defaults to `deep` when flag omitted
  - [ ] `--orchestrator=legacy` still available for explicit selection
- [ ] Deploy to Railway production with new defaults

### Communication

- [ ] Send announcement to all users about orchestrator change
- [ ] Include rollback instructions in announcement
- [ ] Update all user-facing documentation (guides, tutorials, examples)

### Production Monitoring

- [ ] Monitor production for 48 hours with on-call coverage
- [ ] Set up alerts for:
  - [ ] Runtime regression >30%
  - [ ] Critic score < Phase 1 baseline
  - [ ] Error rate increase >5%
- [ ] Verify critic scores and runtime metrics remain within thresholds

### Documentation Updates

- [ ] Mark legacy orchestrator as deprecated in code comments
- [ ] Update `src/main.py` help text to indicate deep is default
- [ ] Add deprecation notice to legacy orchestrator classes

### Sign-off

- [ ] Phase 5.3 complete, ready for Phase 5.4
- [ ] Production stable for 48+ hours
- [ ] Date: ____________
- [ ] Reviewer: ____________

---

## Phase 5.4: Cleanup (Week 9+)

**Goal:** Remove legacy code after stability period.

### Waiting Period

- [ ] Wait 1 full release cycle (2-4 weeks) with no critical issues
- [ ] Confirm no users requesting legacy orchestrator rollback
- [ ] Review telemetry: legacy usage should be <5% of runs

### Code Archival

- [ ] Archive `TopicOrchestratorV2` to `src/orchestration/legacy/`
- [ ] Move `MultiAgentStrategy` to `src/services/strategies/legacy/`
- [ ] Update imports in any remaining references to use archived paths
- [ ] Add deprecation warnings to archived classes

### CLI Cleanup

- [ ] Remove legacy orchestrator from CLI options (keep code for emergency rollback)
- [ ] Update `src/cli/schema.py` to remove legacy option
- [ ] Update web UI to remove orchestrator toggle (deep is only option)

### Documentation Cleanup

- [ ] Update `MIGRATION_GUIDE.md` with legacy→deep migration examples
- [ ] Update `DEVELOPER_ONBOARDING.md` to teach deep orchestrator patterns
- [ ] Remove references to legacy orchestrator from user guides
- [ ] Clean up feature flags related to orchestrator selection

### Final Validation

- [ ] Add integration tests for deep orchestrator edge cases
- [ ] Run full test suite: `./scripts/run_all_checks.sh`
- [ ] Verify no regressions in production

### Celebration

- [ ] Celebrate successful migration! 🎉
- [ ] Document lessons learned in postmortem/retrospective
- [ ] Update `docs/LANGCHAIN_ARCHITECTURE_MIGRATION.md` Phase 5 status to COMPLETE

### Sign-off

- [ ] Phase 5.4 complete, rollout finished
- [ ] Date: ____________
- [ ] Reviewer: ____________

---

## Rollback Plan

If critical issues arise during any phase:

### Immediate Actions

1. Set `ENABLE_DEEP_ORCHESTRATOR=false` in Railway environment variables
2. Redeploy previous version if code changes were made
3. Communicate rollback to affected users

### Post-Rollback

4. Document issue in `docs/LANGCHAIN_ARCHITECTURE_MIGRATION.md` Phase 5 section
5. Create incident report with root cause analysis
6. Update Phase 5 decision to DEFERRED with conditions for retry
7. Re-evaluate when conditions are addressed

### Rollback Commands

```bash
# Railway environment
railway variables set ENABLE_DEEP_ORCHESTRATOR=false

# Local testing
export ENABLE_DEEP_ORCHESTRATOR=false
python src/main.py voice-of-customer --orchestrator legacy ...
```

---

## Success Metrics

Track these metrics throughout rollout to confirm success:

| Metric | Target | Phase 5.1 | Phase 5.2 | Phase 5.3 | Phase 5.4 |
|--------|--------|-----------|-----------|-----------|-----------|
| Orchestrator usage (deep %) | >80% by 5.3 | ___% | ___% | ___% | ___% |
| Mean critic score | ≥ baseline | ___ | ___ | ___ | ___ |
| Mean runtime (s) | ≤125% of legacy | ___ | ___ | ___ | ___ |
| Error rate | <5% increase | ___% | ___% | ___% | ___% |
| User complaints | 0 rollback requests | ___ | ___ | ___ | ___ |

---

## References

- Decision documentation: `docs/LANGCHAIN_ARCHITECTURE_MIGRATION.md` (Phase 5)
- Original plan: `docs/VOC_QUALITY_RESCUE_PLAN.md`
- Pilot analysis: `outputs/deepagents_pilot/phase5_decision_analysis.md`
- Metrics summary: `outputs/deepagents_pilot/phase5_metrics_summary.json`
