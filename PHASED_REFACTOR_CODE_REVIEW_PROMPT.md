# Phased Refactor Code Review Prompt

Use this prompt when requesting a reviewer to propose a staged migration plan for a large-scale refactor (e.g., CLI/railway/agent orchestration split). It guides reviewers to recommend incremental steps, validation gates, and ownership assignments before any code moves.

---

## Reviewer Instructions

1. **Context Recap**
   - Summarize the current architecture, major problem areas, and why a refactor is needed now.
   - Call out modules with the highest coupling or risk (e.g., `src/main.py`, `deploy/railway_web.py`).

2. **Phase Proposal (Repeat for each phase)**
   - **Phase Name & Goal**
   - **Scope**: Files/modules touched; what is *not* in scope.
   - **Dependencies / Prereqs**
   - **Implementation Outline**
   - **Validation Checklist** (scripts/tests/sample-mode requirements)
   - **Risk Mitigation / Rollback Plan**
   - **Definition of Done** (including documentation + ownership updates)

3. **Cross-Phase Guardrails**
   - Ensure each phase keeps CLI ↔ Schema ↔ Railway alignment passing (`scripts/run_all_checks.sh --p0`).
   - Require audit checklist completion (readback, lint, `py_compile`, import checks) before merging a phase.
   - Maintain async/service layering order: models/agents → services → CLI/schema → Railway/web.

4. **Ownership & Communication**
   - Identify code owners for new modules (CLI, services, deploy/web).
   - Specify documentation that must be updated per phase (`SYSTEM_ARCHITECTURE_GUIDE.md`, `CLI_WEB_ALIGNMENT_CHECKLIST.md`, etc.).

5. **Reviewer Deliverable**
   - Provide a numbered phase list (Phase 0, Phase 1, …) each with:
     ```
     ## Phase N: Title
     - Goal:
     - Scope:
     - Key Tasks:
     - Validation Gates:
     - Risks & Mitigations:
     - Owners / Reviewers:
     ```
   - Highlight any open questions or blockers before implementation begins.

---

### Prompt Template

```
You are reviewing the Intercom Analysis Tool refactor.
Please:
1. Summarize current pain points.
2. Propose a phased migration plan (Phase 0 … N) using the structure above.
3. Call out validation gates, async safety requirements, and sample-mode expectations per phase.
4. Note required doc/ownership updates.
5. Flag any prerequisites or sequencing risks.
```

Copy this section into the PR description or review request to ensure reviewers deliver actionable, phased guidance.*** End Patch













