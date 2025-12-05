"""
LangChain-compatible tool wrapper for InsightAgent.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from pydantic import ValidationError

from src.agents.base_agent import AgentContext
from src.agents.insight_agent import InsightAgent
from src.agents.tools.base_tool import BaseTool, ToolDefinition, ToolParameter, ToolResult
from src.schemas import InsightInput, InsightOutput


class InsightTool(BaseTool):
    """Expose InsightAgent as a LangChain tool."""

    def __init__(self) -> None:
        super().__init__(
            name="generate_insights",
            description=(
                "Synthesize executive-ready insights, themes, and recommendations using "
                "TopicDetection + TopicSentiment outputs."
            ),
        )
        self.agent = InsightAgent()

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name=self.name,
            description=self.description,
            parameters=[
                ToolParameter(
                    name="previous_results",
                    type="object",
                    description="Dictionary of upstream agent results (TopicDetectionAgent + TopicSentimentAgent required)",
                    required=True,
                ),
                ToolParameter(
                    name="analysis_id",
                    type="string",
                    description="Unique analysis identifier used for logging",
                    required=True,
                ),
                ToolParameter(
                    name="start_date",
                    type="string",
                    description="ISO8601 analysis start date",
                    required=True,
                ),
                ToolParameter(
                    name="end_date",
                    type="string",
                    description="ISO8601 analysis end date",
                    required=True,
                ),
                ToolParameter(
                    name="conversations",
                    type="array",
                    description="Optional raw conversation payloads for additional context",
                    required=False,
                ),
                ToolParameter(
                    name="metadata",
                    type="object",
                    description="Optional metadata forwarded to the agent context",
                    required=False,
                ),
            ],
        )

    async def execute(self, **kwargs: Dict[str, Any]) -> ToolResult:
        # Explicitly convert date strings to datetime objects to ensure clarity
        # and compatibility with Pydantic models expecting datetime.
        for date_field in ["start_date", "end_date"]:
            if date_field in kwargs and isinstance(kwargs[date_field], str):
                try:
                    kwargs[date_field] = datetime.fromisoformat(kwargs[date_field])
                except ValueError:
                    pass  # Let Pydantic validation catch invalid formats

        try:
            payload = InsightInput(**kwargs)
        except ValidationError as exc:
            self.logger.error("InsightTool: input validation failed: %s", exc)
            return ToolResult(success=False, data=None, error_message=f"Invalid input: {exc}")

        prev_results = payload.previous_results or {}
        if "TopicDetectionAgent" not in prev_results:
            return ToolResult(
                success=False,
                data=None,
                error_message="previous_results must include TopicDetectionAgent output",
            )
        if not any(key in prev_results for key in ("TopicSentimentAgent", "TopicSentiments")):
            return ToolResult(
                success=False,
                data=None,
                error_message="previous_results must include TopicSentimentAgent or TopicSentiments output",
            )

        context = AgentContext(
            analysis_id=payload.analysis_id,
            analysis_type="voice_of_customer",
            start_date=payload.start_date,
            end_date=payload.end_date,
            conversations=payload.conversations,
            previous_results=prev_results,
            metadata=payload.metadata or {},
        )

        agent_result = await self.agent.execute(context)
        if not agent_result.success:
            self.logger.error("InsightTool: agent execution failed: %s", agent_result.error_message)
            return ToolResult(
                success=False,
                data=agent_result.data,
                error_message=agent_result.error_message or "Insight synthesis failed",
            )

        try:
            output = InsightOutput(**agent_result.data)
        except ValidationError as exc:
            self.logger.error("InsightTool: output validation failed: %s", exc)
            return ToolResult(
                success=False,
                data=agent_result.data,
                error_message=f"Agent output failed schema validation: {exc}",
            )

        self.logger.info(
            "InsightTool: synthesized %d themes, duplicate_ratio=%.3f, metric_refs=%d",
            len(output.major_themes),
            output.insight_duplicate_ratio,
            output.metric_references_count,
        )
        return ToolResult(success=True, data=output.model_dump())


