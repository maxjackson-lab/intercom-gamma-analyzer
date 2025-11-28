"""
Legacy MultiAgentOrchestrator wrapper retained for backward compatibility.

New code should instantiate UnifiedOrchestrator with MultiAgentStrategy
directly instead of using this adapter.
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from src.agents.base_agent import AgentContext
from src.services.unified_orchestrator import UnifiedOrchestrator
from src.services.strategies import MultiAgentStrategy


class MultiAgentOrchestrator:
    """
    Deprecated orchestrator wrapper that delegates to the unified orchestration layer.

    The class preserves the previous interface so callers can migrate gradually.
    """

    def __init__(self, checkpoint_dir: Optional[Path] = None) -> None:
        self.logger = logging.getLogger(__name__)
        self.logger.warning(
            "MultiAgentOrchestrator is deprecated. "
            "Use UnifiedOrchestrator with MultiAgentStrategy instead."
        )
        self._strategy = MultiAgentStrategy(checkpoint_dir=checkpoint_dir)
        self._orchestrator = UnifiedOrchestrator(strategy=self._strategy)

    async def execute_analysis(
        self,
        analysis_type: str,
        start_date: datetime,
        end_date: datetime,
        generate_gamma: bool = True,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Execute the multi-agent workflow and return raw data for legacy callers.
        """
        analysis_id = kwargs.pop(
            "analysis_id", f"multi_agent_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )

        context = AgentContext(
            analysis_id=analysis_id,
            analysis_type=analysis_type,
            start_date=start_date,
            end_date=end_date,
            conversations=kwargs.pop("conversations", None),
            previous_results=kwargs.pop("previous_results", {}),
            metadata=kwargs.pop("metadata", {}),
        )

        result = await self._orchestrator.execute(
            context,
            generate_gamma=generate_gamma,
            **kwargs,
        )
        return result.data






