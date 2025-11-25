"""
Deprecated AnalysisOrchestrator wrapper that delegates to the unified orchestration layer.
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from src.agents.base_agent import AgentContext
from src.services.unified_orchestrator import UnifiedOrchestrator
from src.services.strategies import ComprehensiveStrategy


class AnalysisOrchestrator:
    """
    Legacy orchestrator retained for backward compatibility.

    New code should instantiate UnifiedOrchestrator with ComprehensiveStrategy directly.
    """

    def __init__(self, checkpoint_dir: Optional[Path] = None) -> None:
        self.logger = logging.getLogger(__name__)
        self.logger.warning(
            "AnalysisOrchestrator is deprecated. "
            "Use UnifiedOrchestrator with ComprehensiveStrategy instead."
        )
        self._strategy = ComprehensiveStrategy()
        self._orchestrator = UnifiedOrchestrator(
            strategy=self._strategy,
            checkpoint_dir=checkpoint_dir,
        )

    async def run_comprehensive_analysis(
        self,
        start_date: datetime,
        end_date: datetime,
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Run comprehensive analysis through the unified orchestrator."""
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
        from src.services.story_driven_orchestrator import StoryDrivenOrchestrator

        orchestrator = StoryDrivenOrchestrator()
        return await orchestrator.run_story_driven_analysis(
            conversations=conversations,
            canny_posts=canny_posts,
            start_date=start_date,
            end_date=end_date,
            options=options or {},
        )

