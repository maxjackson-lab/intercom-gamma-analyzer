"""
Deprecated AnalysisOrchestrator wrapper that delegates to the unified orchestration layer.

THIS MODULE EXISTS ONLY FOR BACKWARD COMPATIBILITY AND WILL BE REMOVED SOON.
"""

from __future__ import annotations

import logging
import warnings
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from src.agents.base_agent import AgentContext
from src.services.unified_orchestrator import UnifiedOrchestrator
from src.services.strategies import ComprehensiveStrategy

_DEPRECATION_MESSAGE = (
    "AnalysisOrchestrator is deprecated and will be removed in a future release. "
    "Instantiate UnifiedOrchestrator(strategy=ComprehensiveStrategy()) and call "
    "execute(AgentContext, options=...) instead."
)


class AnalysisOrchestrator:
    """
    Legacy orchestrator retained for backward compatibility. Prefer:

        from src.agents.base_agent import AgentContext
        from src.services.unified_orchestrator import UnifiedOrchestrator
        from src.services.strategies import ComprehensiveStrategy

        context = AgentContext(
            analysis_id="comprehensive_20240101",
            analysis_type="comprehensive",
            start_date=start,
            end_date=end,
        )
        strategy = ComprehensiveStrategy()
        orchestrator = UnifiedOrchestrator(strategy=strategy)
        result = await orchestrator.execute(context, options=options)
    """

    def __init__(self, checkpoint_dir: Optional[Path] = None) -> None:
        self.logger = logging.getLogger(__name__)
        self.logger.error(_DEPRECATION_MESSAGE)
        self._emit_deprecation_warning(stacklevel=3)
        self._strategy = ComprehensiveStrategy()
        self._orchestrator = UnifiedOrchestrator(
            strategy=self._strategy,
            checkpoint_dir=checkpoint_dir,
        )

    def _emit_deprecation_warning(self, stacklevel: int = 2) -> None:
        warnings.warn(_DEPRECATION_MESSAGE, DeprecationWarning, stacklevel=stacklevel)

    async def run_comprehensive_analysis(
        self,
        start_date: datetime,
        end_date: datetime,
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Run comprehensive analysis through the unified orchestrator."""
        self._emit_deprecation_warning()
        context = AgentContext(
            analysis_id=f"comprehensive_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            analysis_type="comprehensive",
            start_date=start_date,
            end_date=end_date,
        )

        result = await self._orchestrator.execute(context, options=options or {})
        return result.data

    async def run_category_analysis(
        self,
        category: str,
        start_date: datetime,
        end_date: datetime,
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Delegate category-only analysis to the comprehensive strategy helper."""
        self._emit_deprecation_warning()
        return await self._strategy.run_category_analysis(
            category=category,
            start_date=start_date,
            end_date=end_date,
            options=options or {},
        )

    async def run_specialized_analysis(
        self,
        analysis_type: str,
        start_date: datetime,
        end_date: datetime,
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Delegate specialized analyses to the comprehensive strategy helper."""
        self._emit_deprecation_warning()
        return await self._strategy.run_specialized_analysis(
            analysis_type=analysis_type,
            start_date=start_date,
            end_date=end_date,
            options=options or {},
        )

    async def run_story_driven_analysis(
        self,
        conversations: list[Dict[str, Any]],
        canny_posts: list[Dict[str, Any]],
        start_date: datetime,
        end_date: datetime,
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Maintain compatibility by delegating to the dedicated StoryDrivenOrchestrator wrapper.
        """
        self._emit_deprecation_warning()
        from src.services.story_driven_orchestrator import StoryDrivenOrchestrator

        orchestrator = StoryDrivenOrchestrator()
        return await orchestrator.run_story_driven_analysis(
            conversations=conversations,
            canny_posts=canny_posts,
            start_date=start_date,
            end_date=end_date,
            options=options or {},
        )

