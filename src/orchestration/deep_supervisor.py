"""
DeepAgents-based supervisor for Voice of Customer orchestration (Phase 3 pilot).

This wrapper keeps DeepAgents optional and streams outputs through the
ExecutionStateManager when available.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

try:
    from deepagents import create_deep_agent
except ImportError:  # pragma: no cover - optional dependency
    create_deep_agent = None  # type: ignore

from src.agents.base_agent import AgentResult, ConfidenceLevel
from src.agents.tools import BaseTool, ToolRegistry
from src.services.execution_state_manager import ExecutionStateManager


class DeepSupervisor:
    """
    Wraps DeepAgents to orchestrate Phase 2 tools with streaming support.

    - Tools: TopicDetectionTool, InsightTool, EditorTool, OutputFormatterTool
    - Streaming: emits chunks to ExecutionStateManager for SSE/UI parity
    - Optional: gracefully errors when deepagents is not installed
    """

    def __init__(
        self,
        tools: List[BaseTool],
        system_prompt: str,
        execution_state_manager: Optional[ExecutionStateManager] = None,
    ):
        if not create_deep_agent:
            raise ImportError(
                "DeepAgents is not installed. Uncomment deepagents in requirements.txt "
                "and run `pip install -r requirements.txt` to enable --orchestrator=deep."
            )

        if not tools:
            raise ValueError("DeepSupervisor requires at least one tool to orchestrate.")

        if not system_prompt or not isinstance(system_prompt, str):
            raise ValueError("DeepSupervisor requires a non-empty system prompt.")

        self.logger = logging.getLogger(__name__)
        self.execution_state_manager = execution_state_manager
        self.tool_registry = ToolRegistry(enable_caching=True)
        for tool in tools:
            self.tool_registry.register(tool)

        # DeepAgents expects tool/function schemas plus a supervising prompt
        tool_definitions = self.tool_registry.get_tool_definitions()
        self.agent = create_deep_agent(tools=tool_definitions, system_prompt=system_prompt)
        self.system_prompt = system_prompt

    def build_request(self, request: Dict[str, Any]) -> str:
        """
        Convert a request dict into a natural language instruction for the supervisor.
        """
        conversations = request.get("conversations") or []
        start_date = request.get("start_date")
        end_date = request.get("end_date")
        period_label = request.get("period_label") or ""
        analysis_id = request.get("analysis_id") or ""
        meta = request.get("metadata") or {}

        return (
            f"Voice of Customer analysis {analysis_id}: "
            f"analyze {len(conversations)} conversations from {start_date} to {end_date} "
            f"({period_label}). "
            "Detect topics, synthesize insights, critique quality, and format an executive report. "
            f"Metadata: {json.dumps(meta, default=str)}"
        )

    def _determine_event_type(self, chunk: Any) -> str:
        """
        Map DeepAgents chunk payloads to semantic event types for observability.
        """
        try:
            if isinstance(chunk, dict):
                level = str(chunk.get("level", "")).lower()
                event_hint = str(chunk.get("event_type", "")).lower()

                if chunk.get("error") or level in {"error", "exception", "critical"}:
                    return "error"
                if event_hint in {"status", "state", "transition"}:
                    return "status"
                if "tool" in chunk or "tool_call" in chunk or event_hint in {"tool", "tool_run"}:
                    return "tool"
                if "metrics" in chunk or event_hint in {"telemetry"}:
                    return "telemetry"
            return "stdout"
        except Exception:
            return "stdout"

    def _coerce_event_payload(self, chunk: Any) -> str:
        """
        Convert a streamed chunk into a safe string for SSE/UI consumption.
        """
        if isinstance(chunk, str):
            return chunk
        if isinstance(chunk, (int, float, bool)):
            return str(chunk)
        try:
            return json.dumps(chunk, default=str)
        except Exception:
            return str(chunk)

    def _extract_structured_output(
        self, stream_buffer: List[Any], request: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Convert streamed chunks into the VoC result schema expected downstream.
        """
        formatted_report: Optional[str] = None
        period_label = request.get("period_label") or ""
        metadata: Dict[str, Any] = {}
        text_fragments: List[str] = []

        def _get_text_from_chunk(chunk: Dict[str, Any]) -> Optional[str]:
            for key in (
                "formatted_report",
                "formatted_output",
                "report",
                "report_markdown",
                "content",
                "data",
                "message",
                "output",
            ):
                value = chunk.get(key)
                if isinstance(value, str) and value.strip():
                    return value
            return None

        for chunk in stream_buffer:
            if isinstance(chunk, dict):
                if not formatted_report:
                    candidate = _get_text_from_chunk(chunk)
                    if candidate:
                        formatted_report = candidate.strip()

                if not period_label:
                    period_label = chunk.get("period_label") or period_label

                if not metadata:
                    meta_candidate = chunk.get("metadata") or chunk.get("meta")
                    if isinstance(meta_candidate, dict):
                        metadata = meta_candidate

                text_candidate = _get_text_from_chunk(chunk)
                if text_candidate:
                    text_fragments.append(text_candidate)

            elif isinstance(chunk, str):
                text_fragments.append(chunk)

        if not formatted_report and text_fragments:
            formatted_report = "\n".join([frag for frag in text_fragments if frag.strip()])

        return {
            "formatted_report": formatted_report or "",
            "period_label": period_label or "",
            "metadata": metadata,
            "raw_stream": stream_buffer,
        }

    async def run(
        self,
        request: Dict[str, Any],
        execution_id: Optional[str] = None,
    ) -> AgentResult:
        """
        Execute the DeepAgents supervisor and stream outputs if an ExecutionStateManager is provided.
        """
        payload = {
            "messages": [{"role": "user", "content": self.build_request(request)}],
            "tools": self.tool_registry.get_tool_definitions(),
        }

        stream_buffer: List[Any] = []
        try:
            async for chunk in self.agent.astream(payload, stream_mode="values"):
                stream_buffer.append(chunk)

                if self.execution_state_manager and execution_id:
                    event_type = self._determine_event_type(chunk)
                    safe_chunk = self._coerce_event_payload(chunk)
                    await self.execution_state_manager.add_output(
                        execution_id,
                        {"type": event_type, "data": safe_chunk},
                    )

            # Aggregate final data
            structured_data = self._extract_structured_output(stream_buffer, request)
            return AgentResult(
                agent_name="DeepSupervisor",
                success=True,
                data=structured_data,
                confidence=0.8,
                confidence_level=ConfidenceLevel.HIGH,
                limitations=[],
                sources=["deepagents"],
                verification_passed=True,
                execution_time=0.0,
                token_count=0,
            )
        except Exception as exc:  # pragma: no cover - defensive logging
            self.logger.exception("DeepSupervisor execution failed: %s", exc)
            if self.execution_state_manager and execution_id:
                await self.execution_state_manager.add_output(
                    execution_id,
                    {"type": "error", "data": str(exc)},
                )
            return AgentResult(
                agent_name="DeepSupervisor",
                success=False,
                data=self._extract_structured_output(stream_buffer, request),
                confidence=0.0,
                confidence_level=ConfidenceLevel.LOW,
                limitations=[str(exc)],
                sources=["deepagents"],
                verification_passed=False,
                execution_time=0.0,
                token_count=0,
                error_message=str(exc),
            )

