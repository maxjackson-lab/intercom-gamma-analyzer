# Traycer Architecture Review: Intercom Analysis Tool

**Context:**
We are building a multi-agent ETL system to analyze weekly customer support conversations (Intercom). The system uses a Unified Orchestrator with pluggable strategies (`Comprehensive`, `MultiAgent`, `StoryDriven`) to coordinate ~10 specialized agents (Segmentation, TopicDetection, FinPerformance, BPO, etc.).

**The Problem:**
We have persistent "silent failures" where agents run successfully but their output doesn't make it to the final report (Gamma presentation). Specifically:
1. **Metadata Drop-off:** `SegmentationAgent` produces `agent_assignments` (vendor data), but `BpoPerformanceAgent` downstream fails with "missing metadata," despite passing through `TopicOrchestrator`.
2. **Presentation Truncation:** `NarrativeFormatterAgent` generates a full markdown report, but the `GammaGenerator` often renders only the first slide, ignoring the rest.
3. **Observability Gaps:** We have to manually inspect `agent_debug_report.txt` to prove agents ran; the logs don't clearly signal "Agent X produced 0 records" vs "Agent X failed."

**The Request:**
Review the `src/agents/topic_orchestrator.py`, `src/services/gamma_generator.py`, and `src/agents/base_agent.py` architecture.

**Key Questions:**
1. **Data Flow:** How can we enforce a strict contract for metadata passing between agents (e.g., `AgentContext` immutability vs. copying)? Why is `agent_assignments` dropping?
2. **Gamma Integration:** Is the "Markdown -> Gamma" translation layer (`generate_from_markdown`) robust enough for structured multi-slide decks? Should we move to a structured JSON payload for Gamma instead of raw Markdown splitting?
3. **Orchestration:** Are we over-complicating the dependency graph? Should `BpoPerformanceAgent` run *inside* `SegmentationAgent` or be its own independent phase with a hard database read?
4. **Resilience:** How do we fail *loudly* when a critical section (like "Vendor Snapshot") is empty, rather than generating a "No data available" placeholder that looks like a bug to the user?

**Goal:**
A concrete refactoring plan to ensure:
- 100% data persistence between agents.
- Guaranteed multi-slide generation in Gamma.
- "Loud" failures for missing critical sections.

