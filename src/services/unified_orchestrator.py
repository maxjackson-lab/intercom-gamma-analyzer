"""
Unified orchestration entry point built on pluggable strategies.
"""

from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Optional

from src.agents.base_agent import AgentContext, AgentResult, ConfidenceLevel
from src.services.base_orchestrator import BaseOrchestrator


class OrchestrationStrategy(BaseOrchestrator, ABC):
    """Interface implemented by orchestration strategies."""

    @abstractmethod
    async def execute(self, context: AgentContext, **kwargs: Any) -> AgentResult:
        """Execute the orchestration flow for the supplied context."""

    @abstractmethod
    def get_strategy_name(self) -> str:
        """Return human-friendly strategy name for logging/metrics."""


class UnifiedOrchestrator:
    """
    Coordinates analysis execution using a configured orchestration strategy.

    Responsible for validation, execution tracking, and uniform error handling.
    """

    def __init__(
        self,
        strategy: OrchestrationStrategy,
        checkpoint_dir: Optional[Path] = None,
    ) -> None:
        self.strategy = strategy
        if checkpoint_dir:
            self.strategy.checkpoint_dir = Path(checkpoint_dir)
            self.strategy.checkpoint_dir.mkdir(parents=True, exist_ok=True)

        self.logger = logging.getLogger(__name__)

    async def execute(self, context: AgentContext, **kwargs: Any) -> AgentResult:
        """
        Execute the configured strategy and return an AgentResult.
        """
        if not isinstance(context, AgentContext):
            raise ValueError("context must be an AgentContext instance")

        start_time = time.time()
        try:
            result = await self.strategy.execute(context=context, **kwargs)
            if result.execution_time == 0.0:
                result.execution_time = time.time() - start_time
            return result
        except Exception as exc:  # pylint: disable=broad-except
            self.logger.error(
                "UnifiedOrchestrator execution failed for %s: %s",
                self.strategy.get_strategy_name(),
                exc,
                exc_info=True,
            )
            return AgentResult(
                agent_name=self.strategy.get_strategy_name(),
                success=False,
                data={},
                confidence=0.0,
                confidence_level=ConfidenceLevel.LOW,
                error_message=str(exc),
            )

