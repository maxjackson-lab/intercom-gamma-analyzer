"""
Wrapper orchestrator for VOC-V2 narrative reports.

This thin wrapper configures TopicOrchestrator with the NarrativeFormatterAgent
and BpoPerformanceAgent so the rest of the pipeline can remain unchanged.
"""

from typing import Optional

from src.agents.topic_orchestrator import TopicOrchestrator
from src.agents.narrative_formatter_agent import NarrativeFormatterAgent
from src.agents.bpo_performance_agent import BpoPerformanceAgent
from src.services.ai_model_factory import AIModelFactory


class TopicOrchestratorV2:
    """Configure TopicOrchestrator to produce VOC-V2 narratives."""

    def __init__(self, ai_factory: Optional[AIModelFactory] = None, audit_trail=None, execution_monitor=None):
        self._orchestrator = TopicOrchestrator(
            ai_factory=ai_factory,
            audit_trail=audit_trail,
            execution_monitor=execution_monitor,
            formatter_agent=NarrativeFormatterAgent(),
            bpo_agent=BpoPerformanceAgent(),
            report_type="voc_v2"
        )

    async def execute_weekly_analysis(self, *args, **kwargs):
        return await self._orchestrator.execute_weekly_analysis(*args, **kwargs)

