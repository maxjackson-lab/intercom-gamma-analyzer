"""
LangChain-compatible tool wrapper for TopicDetectionAgent.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from pydantic import ValidationError

from src.agents.base_agent import AgentContext
from src.agents.topic_detection_agent import TopicDetectionAgent
from src.agents.tools.base_tool import BaseTool, ToolDefinition, ToolParameter, ToolResult
from src.schemas import TopicDetectionInput, TopicDetectionOutput


class TopicDetectionTool(BaseTool):
    """Expose TopicDetectionAgent as a LangChain tool."""

    def __init__(self) -> None:
        super().__init__(
            name="detect_topics",
            description=(
                "Detect topics from Intercom conversations using the hybrid LLM + keyword "
                "pipeline. Returns per-topic distribution, assignments, and detection provenance."
            ),
        )
        self.agent = TopicDetectionAgent()

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name=self.name,
            description=self.description,
            parameters=[
                ToolParameter(
                    name="conversations",
                    type="array",
                    description="Intercom conversation payloads to classify",
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
                    name="analysis_id",
                    type="string",
                    description="Unique analysis identifier used for logging",
                    required=True,
                ),
                ToolParameter(
                    name="metadata",
                    type="object",
                    description="Optional metadata bag forwarded to the agent context",
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
            payload = TopicDetectionInput(**kwargs)
        except ValidationError as exc:
            self.logger.error("TopicDetectionTool: input validation failed: %s", exc)
            return ToolResult(success=False, data=None, error_message=f"Invalid input: {exc}")

        context = AgentContext(
            analysis_id=payload.analysis_id,
            analysis_type="voice_of_customer",
            start_date=payload.start_date,
            end_date=payload.end_date,
            conversations=payload.conversations,
            previous_results={},
            metadata=payload.metadata or {},
        )

        agent_result = await self.agent.execute(context)
        if not agent_result.success:
            self.logger.error(
                "TopicDetectionTool: agent execution failed: %s", agent_result.error_message
            )
            return ToolResult(
                success=False,
                data=agent_result.data,
                error_message=agent_result.error_message or "Topic detection failed",
            )

        try:
            output = TopicDetectionOutput(**agent_result.data)
        except ValidationError as exc:
            self.logger.error("TopicDetectionTool: output validation failed: %s", exc)
            return ToolResult(
                success=False,
                data=agent_result.data,
                error_message=f"Agent output failed schema validation: {exc}",
            )

        total_topics = len(output.topic_distribution)
        self.logger.info(
            "TopicDetectionTool: processed %d conversations across %d topics",
            output.total_conversations or len(payload.conversations),
            total_topics,
        )
        return ToolResult(success=True, data=output.model_dump())


