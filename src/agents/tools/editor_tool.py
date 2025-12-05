"""
LangChain-compatible tool wrapper for EditorAgent (critic/rewrite loop).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from pydantic import ValidationError

from src.agents.base_agent import AgentContext
from src.agents.editor_agent import EditorAgent
from src.agents.tools.base_tool import BaseTool, ToolDefinition, ToolParameter, ToolResult
from src.schemas import EditorInput, EditorOutput


class EditorTool(BaseTool):
    """Expose EditorAgent as a LangChain tool."""

    def __init__(self) -> None:
        super().__init__(
            name="critique_and_edit_insights",
            description=(
                "Score InsightAgent outputs across specificity, metrics, repetition, distinctness, "
                "and actionability. Optionally rewrite insights when scores fall below thresholds."
            ),
        )
        self.agent = EditorAgent()

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name=self.name,
            description=self.description,
            parameters=[
                ToolParameter(
                    name="previous_results",
                    type="object",
                    description="Dictionary containing InsightAgent results to critique",
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
            payload = EditorInput(**kwargs)
        except ValidationError as exc:
            self.logger.error("EditorTool: input validation failed: %s", exc)
            return ToolResult(success=False, data=None, error_message=f"Invalid input: {exc}")

        prev_results = payload.previous_results or {}
        if "InsightAgent" not in prev_results:
            return ToolResult(
                success=False,
                data=None,
                error_message="previous_results must include InsightAgent output",
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
            self.logger.error("EditorTool: agent execution failed: %s", agent_result.error_message)
            return ToolResult(
                success=False,
                data=agent_result.data,
                error_message=agent_result.error_message or "EditorAgent failed",
            )

        try:
            output = EditorOutput(**agent_result.data)
        except ValidationError as exc:
            self.logger.error("EditorTool: output validation failed: %s", exc)
            return ToolResult(
                success=False,
                data=agent_result.data,
                error_message=f"Agent output failed schema validation: {exc}",
            )

        critic = output.critic_scores
        self.logger.info(
            "EditorTool: composite=%.2f specificity=%.2f rewrite=%s",
            critic.composite_score,
            critic.specificity_score,
            output.rewrite_performed,
        )
        return ToolResult(success=True, data=output.model_dump())

