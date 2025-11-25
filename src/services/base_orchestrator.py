"""
Base orchestrator providing shared orchestration utilities.

Consolidates timeout management, checkpoint persistence, error handling,
and metrics aggregation so individual orchestration strategies can stay
focused on domain-specific sequencing logic.
"""

from __future__ import annotations

import asyncio
import json
import logging
import tempfile
from abc import ABC
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from src.agents.base_agent import (
    AgentContext,
    AgentMetrics,
    AgentResult,
    ConfidenceLevel,
)
from src.config.settings import settings


class BaseOrchestrator(ABC):
    """Abstract base orchestrator with shared orchestration infrastructure."""

    def __init__(self, checkpoint_dir: Optional[Path] = None) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)
        self.checkpoint_dir = Path(checkpoint_dir or Path("outputs/checkpoints"))
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

    async def _execute_with_timeout(
        self,
        agent: Any,
        context: AgentContext,
        timeout: Optional[float] = None,
        agent_name: Optional[str] = None,
    ) -> AgentResult:
        """
        Execute an agent with timeout handling and structured error responses.

        Args:
            agent: Agent instance with an async execute() method.
            context: AgentContext passed down to the agent.
            timeout: Optional custom timeout override.
            agent_name: Optional override for logging/metrics (defaults to agent.name).
        """
        agent_label = agent_name or getattr(agent, "name", agent.__class__.__name__)
        effective_timeout = timeout or self._get_agent_timeout(agent_label)

        try:
            self.logger.debug(
                "Executing %s with timeout=%ss", agent_label, effective_timeout
            )
            result = await asyncio.wait_for(agent.execute(context), timeout=effective_timeout)
            return result
        except asyncio.TimeoutError:
            self.logger.error(
                "Agent %s timed out after %ss",
                agent_label,
                effective_timeout,
                extra={"agent": agent_label, "timeout_seconds": effective_timeout},
            )
            return AgentResult(
                agent_name=agent_label,
                success=False,
                data={"error": f"Agent timed out after {effective_timeout}s", "status": "timeout"},
                confidence=0.0,
                confidence_level=ConfidenceLevel.LOW,
                error_message=f"Agent timed out after {effective_timeout}s",
            )
        except Exception as exc:  # pylint: disable=broad-except
            self.logger.error(
                "Agent %s execution failed: %s", agent_label, exc, exc_info=True
            )
            return AgentResult(
                agent_name=agent_label,
                success=False,
                data={"error": str(exc)},
                confidence=0.0,
                confidence_level=ConfidenceLevel.LOW,
                error_message=str(exc),
            )

    def _get_agent_timeout(self, agent_name: str) -> float:
        """
        Resolve the orchestrator timeout window for a given agent.

        Policy: Orchestrator timeout = 3x agent-level LLM timeout setting.
        Falls back to conservative defaults for non-LLM agents.
        """
        agent_timeout_map = {
            "TopicDetectionAgent": settings.topic_detection_timeout,
            "SubTopicDetectionAgent": settings.subtopic_detection_timeout,
            "QualityInsightsAgent": settings.quality_insights_timeout,
            "SentimentAgent": settings.sentiment_timeout,
            "OutputFormatterAgent": settings.output_formatter_timeout,
            "CorrelationAgent": settings.correlation_timeout,
            "CrossPlatformCorrelationAgent": settings.correlation_timeout,
        }

        default_timeouts = {
            "DataAgent": 180,
            "CategoryAgent": 300,
            "InsightAgent": 300,
            "PresentationAgent": 600,
            "SegmentationAgent": 300,
            "TrendAgent": 240,
            "ExampleExtractionAgent": 240,
            "AgentPerformanceAgent": 240,
            "FinPerformanceAgent": 240,
            "TopicSentimentAgent": 300,
            "CannyTopicDetectionAgent": 300,
        }

        agent_llm_timeout = agent_timeout_map.get(agent_name, settings.llm_timeout_default)

        if agent_name in agent_timeout_map:
            return agent_llm_timeout * 3

        return default_timeouts.get(agent_name, 300)

    def _save_checkpoint(
        self,
        analysis_id: str,
        agent_name: str,
        result: Dict[str, Any],
    ) -> None:
        """
        Persist a checkpoint using atomic writes and retention enforcement.
        """
        checkpoint_file = self.checkpoint_dir / f"{analysis_id}_{agent_name}.json"

        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                dir=self.checkpoint_dir,
                delete=False,
                suffix=".tmp",
            ) as tmp_file:
                json.dump(result, tmp_file, indent=2, default=str)
                tmp_path = Path(tmp_file.name)

            tmp_path.replace(checkpoint_file)
            self.logger.debug("Checkpoint saved: %s", checkpoint_file)
            self._prune_old_checkpoints(settings.max_checkpoints)
        except Exception as exc:  # pylint: disable=broad-except
            self.logger.error("Failed to save checkpoint %s: %s", checkpoint_file, exc)
            if "tmp_path" in locals() and tmp_path.exists():
                tmp_path.unlink()
            raise

    def _load_checkpoint(self, analysis_id: str, agent_name: str) -> Optional[Dict[str, Any]]:
        """
        Load checkpoint data from disk with lightweight schema validation.
        """
        checkpoint_file = self.checkpoint_dir / f"{analysis_id}_{agent_name}.json"

        if not checkpoint_file.exists():
            return None

        try:
            data = json.loads(checkpoint_file.read_text())
            required_keys = {"agent_name", "success", "data"}
            if not required_keys.issubset(data.keys()):
                self.logger.warning("Invalid checkpoint schema detected: %s", checkpoint_file)
                return None
            return data
        except json.JSONDecodeError as exc:
            self.logger.error("Failed to parse checkpoint %s: %s", checkpoint_file, exc)
            return None
        except Exception as exc:  # pylint: disable=broad-except
            self.logger.error("Failed to load checkpoint %s: %s", checkpoint_file, exc)
            return None

    def _prune_old_checkpoints(self, max_checkpoints: int) -> None:
        """
        Retain the most recent checkpoints based on modification time.
        """
        try:
            checkpoints = sorted(
                self.checkpoint_dir.glob("*.json"),
                key=lambda path: path.stat().st_mtime,
                reverse=True,
            )
            if len(checkpoints) > max_checkpoints:
                for checkpoint in checkpoints[max_checkpoints:]:
                    checkpoint.unlink()
                self.logger.info(
                    "Pruned %s checkpoints (max=%s)", len(checkpoints) - max_checkpoints, max_checkpoints
                )
        except Exception as exc:  # pylint: disable=broad-except
            self.logger.warning("Failed to prune checkpoints: %s", exc)

    async def _aggregate_results(
        self,
        results: Sequence[AgentResult],
        agent_name: str = "AggregatedResult",
    ) -> AgentResult:
        """
        Aggregate a sequence of AgentResults into a single consolidated result.
        """
        if not results:
            return AgentResult(
                agent_name=agent_name,
                success=False,
                data={},
                confidence=0.0,
                confidence_level=ConfidenceLevel.LOW,
                error_message="No results to aggregate",
            )

        aggregated_data = {result.agent_name: result.data for result in results}
        confidence = sum(result.confidence for result in results) / len(results)
        confidence_level = self._confidence_level_from_score(confidence)

        metrics = self._calculate_metrics(results)

        return AgentResult(
            agent_name=agent_name,
            success=all(result.success for result in results),
            data=aggregated_data,
            confidence=confidence,
            confidence_level=confidence_level,
            metrics=metrics,
        )

    def _calculate_metrics(self, results: Sequence[AgentResult]) -> Optional[AgentMetrics]:
        """
        Combine AgentMetrics objects across results for reporting.
        """
        aggregated_metrics = AgentMetrics()

        has_metrics = False
        for result in results:
            if result.metrics:
                has_metrics = True
                aggregated_metrics.execution_time += result.metrics.execution_time
                aggregated_metrics.input_count += result.metrics.input_count
                aggregated_metrics.output_count += result.metrics.output_count
                aggregated_metrics.llm_calls += result.metrics.llm_calls
                aggregated_metrics.token_count += result.metrics.token_count
                aggregated_metrics.selected_examples_count += result.metrics.selected_examples_count
                aggregated_metrics.error_count += result.metrics.error_count
            else:
                aggregated_metrics.execution_time += result.execution_time
                aggregated_metrics.token_count += result.token_count

        return aggregated_metrics if has_metrics else None

    @staticmethod
    def _confidence_level_from_score(score: float) -> ConfidenceLevel:
        """Convert numeric confidence to ConfidenceLevel enum."""
        if score >= 0.8:
            return ConfidenceLevel.HIGH
        if score >= 0.6:
            return ConfidenceLevel.MEDIUM
        return ConfidenceLevel.LOW

