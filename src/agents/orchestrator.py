"""
Legacy MultiAgentOrchestrator wrapper retained for backward compatibility.

THIS MODULE IS DEPRECATED. Use UnifiedOrchestrator + MultiAgentStrategy directly.
"""

from __future__ import annotations

import logging
import warnings
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, TYPE_CHECKING

from src.agents.base_agent import AgentContext
from src.services.unified_orchestrator import UnifiedOrchestrator

if TYPE_CHECKING:
    from src.services.strategies import MultiAgentStrategy

_DEPRECATION_MESSAGE = (
    "MultiAgentOrchestrator is deprecated. Instantiate UnifiedOrchestrator with "
    "MultiAgentStrategy instead."
)


class MultiAgentOrchestrator:
    """
    Deprecated orchestrator wrapper that delegates to the unified orchestration layer.

    Migration example:

        # OLD
        orchestrator = MultiAgentOrchestrator()
        await orchestrator.execute_analysis(...)

        # NEW
        strategy = MultiAgentStrategy()
        orchestrator = UnifiedOrchestrator(strategy=strategy)
        context = AgentContext(...)
        result = await orchestrator.execute(context, ...)

    The class preserves the previous interface so callers can migrate gradually.
    """

    def __init__(self, checkpoint_dir: Optional[Path] = None) -> None:
        from src.services.strategies import MultiAgentStrategy as _MultiAgentStrategy

        self.logger = logging.getLogger(__name__)
        self.logger.error(_DEPRECATION_MESSAGE)
        self._emit_deprecation_warning(stacklevel=3)
        self._strategy = _MultiAgentStrategy(checkpoint_dir=checkpoint_dir)
        self._orchestrator = UnifiedOrchestrator(strategy=self._strategy)

    def _emit_deprecation_warning(self, stacklevel: int = 2) -> None:
        warnings.warn(_DEPRECATION_MESSAGE, DeprecationWarning, stacklevel=stacklevel)

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
        self._emit_deprecation_warning()
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








