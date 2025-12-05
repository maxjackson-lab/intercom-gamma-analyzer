"""
LangChain-compatible tool wrapper for OutputFormatterAgent.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

from pydantic import ValidationError

from src.agents.base_agent import AgentContext
from src.agents.output_formatter_agent import OutputFormatterAgent
from src.agents.tools.base_tool import BaseTool, ToolDefinition, ToolParameter, ToolResult
from src.schemas import FormatterInput, FormatterOutput


class OutputFormatterTool(BaseTool):
    """Expose OutputFormatterAgent as a LangChain tool."""

    def __init__(self) -> None:
        super().__init__(
            name="format_analysis_output",
            description=(
                "Format aggregated agent results into an executive-ready Markdown report with "
                "topic cards, quality summaries, and detection provenance."
            ),
        )
        self.agent = OutputFormatterAgent(use_llm_formatting=True)

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name=self.name,
            description=self.description,
            parameters=[
                ToolParameter(
                    name="previous_results",
                    type="object",
                    description="Dictionary containing upstream agent outputs (TopicDetectionAgent, InsightAgent, EditorAgent, etc.)",
                    required=True,
                ),
                ToolParameter(
                    name="conversations",
                    type="array",
                    description="Raw conversation payloads for quoting and provenance",
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
            payload = FormatterInput(**kwargs)
        except ValidationError as exc:
            self.logger.error("OutputFormatterTool: input validation failed: %s", exc)
            return ToolResult(success=False, data=None, error_message=f"Invalid input: {exc}")

        prev_results = payload.previous_results or {}
        required_keys: List[str] = ["TopicDetectionAgent", "InsightAgent", "EditorAgent"]
        missing = [key for key in required_keys if key not in prev_results]
        if missing:
            return ToolResult(
                success=False,
                data=None,
                error_message=f"previous_results missing required keys: {', '.join(missing)}",
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
            self.logger.error(
                "OutputFormatterTool: agent execution failed: %s", agent_result.error_message
            )
            return ToolResult(
                success=False,
                data=agent_result.data,
                error_message=agent_result.error_message or "FormatterAgent failed",
            )

        try:
            output = FormatterOutput(**agent_result.data)
        except ValidationError as exc:
            self.logger.error("OutputFormatterTool: output validation failed: %s", exc)
            return ToolResult(
                success=False,
                data=agent_result.data,
                error_message=f"Agent output failed schema validation: {exc}",
            )

        self.logger.info(
            "OutputFormatterTool: generated %d topics, markdown chars=%d",
            output.total_topics,
            len(output.formatted_output),
        )
        return ToolResult(success=True, data=output.model_dump())


