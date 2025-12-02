"""
Deprecated StoryDrivenOrchestrator wrapper retained for backward compatibility.

THIS MODULE IS A COMPATIBILITY SHIM. USE UnifiedOrchestrator + StoryDrivenStrategy.
"""

from __future__ import annotations

import logging
import warnings
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.agents.base_agent import AgentContext
from src.services.unified_orchestrator import UnifiedOrchestrator
from src.services.strategies import StoryDrivenStrategy

_DEPRECATION_MESSAGE = (
    "StoryDrivenOrchestrator is deprecated. Instantiate UnifiedOrchestrator with "
    "StoryDrivenStrategy instead (see MIGRATION_GUIDE.md)."
)


class StoryDrivenOrchestrator:
    """
    Thin wrapper that delegates work to StoryDrivenStrategy via UnifiedOrchestrator.

    Deprecated usage example:

        # OLD
        orchestrator = StoryDrivenOrchestrator()
        result = await orchestrator.run_story_driven_analysis(...)

        # NEW
        strategy = StoryDrivenStrategy()
        orchestrator = UnifiedOrchestrator(strategy=strategy)
        context = AgentContext(...)
        result = await orchestrator.execute(context, options=options)
    """

    def __init__(self, checkpoint_dir: Optional[Path] = None) -> None:
        self.logger = logging.getLogger(__name__)
        self.logger.error(_DEPRECATION_MESSAGE)
        self._emit_deprecation_warning(stacklevel=3)
        self._strategy = StoryDrivenStrategy()
        self._orchestrator = UnifiedOrchestrator(
            strategy=self._strategy,
            checkpoint_dir=checkpoint_dir,
        )

    def _emit_deprecation_warning(self, stacklevel: int = 2) -> None:
        warnings.warn(_DEPRECATION_MESSAGE, DeprecationWarning, stacklevel=stacklevel)

    async def run_story_driven_analysis(
        self,
        conversations: List[Dict[str, Any]],
        canny_posts: List[Dict[str, Any]],
        start_date: datetime,
        end_date: datetime,
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Execute the unified strategy and return the raw result payload.
        """
        self._emit_deprecation_warning()
        context = AgentContext(
            analysis_id=f"story_driven_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            analysis_type="story_driven",
            start_date=start_date,
            end_date=end_date,
            conversations=conversations,
            metadata={"canny_posts": canny_posts},
        )

        result = await self._orchestrator.execute(context, options=options or {})
        return result.data

    async def run_quick_story_analysis(
        self,
        conversations: List[Dict[str, Any]],
        canny_posts: List[Dict[str, Any]],
        analysis_period: str,
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Preserve direct access to the lightweight quick analysis helper.
        """
        self._emit_deprecation_warning()
        return await self._strategy.run_quick_story_analysis(
            conversations=conversations,
            canny_posts=canny_posts,
            analysis_period=analysis_period,
            options=options or {},
        )