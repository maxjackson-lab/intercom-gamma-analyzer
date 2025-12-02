"""
Tests covering Phase 3 resilience standardization:
- Provider-aware semaphores
- Timeout configuration
- Data quality gates
- Unified orchestrator integration
"""

import asyncio
import types
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.agents.base_agent import AgentContext, AgentResult, ConfidenceLevel
from src.agents.output_formatter_agent import OutputFormatterAgent
from src.config.settings import Settings, settings
from src.services.base_orchestrator import BaseOrchestrator
from src.services.strategies.voc_strategy import VoiceOfCustomerStrategy
from src.services.unified_orchestrator import OrchestrationStrategy, UnifiedOrchestrator
from src.utils.ai_client_helper import get_recommended_semaphore


def _make_context(conversation_count: int = 0) -> AgentContext:
    """Helper to build AgentContext objects for tests."""
    conversations = [
        {"id": f"conv_{idx}", "created_at": datetime.utcnow()}
        for idx in range(conversation_count)
    ]
    now = datetime.utcnow()
    return AgentContext(
        analysis_id="test-analysis",
        analysis_type="voc",
        start_date=now - timedelta(days=7),
        end_date=now,
        conversations=conversations,
    )


def _agent_result(name: str, data: dict | None = None) -> AgentResult:
    """Helper to build AgentResult instances."""
    return AgentResult(
        agent_name=name,
        success=True,
        data=data or {},
        confidence=0.9,
        confidence_level=ConfidenceLevel.HIGH,
    )


def test_get_recommended_semaphore_openai():
    original = settings.openai_concurrency
    settings.openai_concurrency = 15
    try:
        semaphore = get_recommended_semaphore(object())
        assert semaphore._value == 15
    finally:
        settings.openai_concurrency = original


def test_get_recommended_semaphore_anthropic(monkeypatch):
    class DummyClaude:
        pass

    monkeypatch.setattr("src.services.claude_client.ClaudeClient", DummyClaude)
    dummy_client = DummyClaude()
    original = settings.anthropic_concurrency
    settings.anthropic_concurrency = 3
    try:
        semaphore = get_recommended_semaphore(dummy_client)
        assert semaphore._value == 3
    finally:
        settings.anthropic_concurrency = original


def test_semaphore_respects_env_overrides(monkeypatch):
    monkeypatch.setenv("OPENAI_CONCURRENCY", "17")
    monkeypatch.setenv("ANTHROPIC_CONCURRENCY", "4")

    test_settings = Settings(
        intercom_access_token="test-token",
        openai_api_key="test-openai",
    )

    assert test_settings.openai_concurrency == 17
    assert test_settings.anthropic_concurrency == 4


def test_output_formatter_uses_recommended_semaphore(monkeypatch):
    dummy_client = object()
    captured_clients = []

    def fake_get_ai_client():
        return dummy_client

    async_semaphore = asyncio.Semaphore(11)

    def fake_get_semaphore(client):
        captured_clients.append(client)
        return async_semaphore

    monkeypatch.setattr(
        "src.agents.output_formatter_agent.get_ai_client",
        lambda: fake_get_ai_client(),
    )
    monkeypatch.setattr(
        "src.agents.output_formatter_agent.get_recommended_semaphore",
        fake_get_semaphore,
    )

    agent = OutputFormatterAgent(use_llm_formatting=False)

    assert captured_clients == [dummy_client]
    assert agent.llm_semaphore is async_semaphore


def test_base_orchestrator_timeout_mapping():
    orchestrator = BaseOrchestrator()
    original_topic = settings.topic_detection_timeout
    original_formatter = settings.output_formatter_timeout
    original_default = settings.llm_timeout_default

    settings.topic_detection_timeout = 70
    settings.output_formatter_timeout = 110
    settings.llm_timeout_default = 50

    try:
        assert orchestrator._get_agent_timeout("TopicDetectionAgent") == 210
        assert orchestrator._get_agent_timeout("OutputFormatterAgent") == 330
        assert orchestrator._get_agent_timeout("UnknownAgent") == 300  # default fallback
    finally:
        settings.topic_detection_timeout = original_topic
        settings.output_formatter_timeout = original_formatter
        settings.llm_timeout_default = original_default


def test_timeout_env_overrides(monkeypatch):
    monkeypatch.setenv("TOPIC_DETECTION_TIMEOUT", "95")

    custom_settings = Settings(
        intercom_access_token="test-token",
        openai_api_key="test-openai",
    )

    assert custom_settings.topic_detection_timeout == 95


def test_orchestrator_timeout_multiplier():
    orchestrator = BaseOrchestrator()
    original_topic = settings.topic_detection_timeout
    settings.topic_detection_timeout = 55
    try:
        assert orchestrator._get_agent_timeout("TopicDetectionAgent") == 165
    finally:
        settings.topic_detection_timeout = original_topic


def test_log_stage_metrics_tracks_counts(caplog):
    orchestrator = BaseOrchestrator()
    with caplog.at_level("INFO"):
        orchestrator.log_stage_metrics("Post-Fetch", 100)
    assert "Post-Fetch = 100" in caplog.text


def test_data_drop_alert_triggers(caplog):
    orchestrator = BaseOrchestrator()
    with caplog.at_level("WARNING"):
        orchestrator.log_stage_metrics("Stage A", 100)
        orchestrator.log_stage_metrics("Stage B", 85)
    assert "DATA DROP ALERT" in caplog.text


def test_data_drop_alert_no_false_positives(caplog):
    orchestrator = BaseOrchestrator()
    with caplog.at_level("WARNING"):
        orchestrator.log_stage_metrics("Stage A", 100)
        orchestrator.log_stage_metrics("Stage B", 95)
    assert "DATA DROP ALERT" not in caplog.text


def test_data_expansion_no_alert(caplog):
    orchestrator = BaseOrchestrator()
    with caplog.at_level("WARNING"):
        orchestrator.log_stage_metrics("Stage A", 80)
        orchestrator.log_stage_metrics("Stage B", 120)
    assert "DATA DROP ALERT" not in caplog.text


@pytest.mark.asyncio
async def test_voc_strategy_checkpoints(monkeypatch):
    formatter_agent = MagicMock()
    formatter_agent.name = "OutputFormatterAgent"
    strategy = VoiceOfCustomerStrategy(formatter_agent=formatter_agent)

    paid_data = {
        "paid_customer_conversations": [{"id": "p1"}],
        "free_fin_only_conversations": [{"id": "f1"}],
        "paid_fin_resolved_conversations": [],
    }

    strategy._execute_phase_1_segmentation = AsyncMock(
        return_value=_agent_result("SegmentationAgent", data=paid_data)
    )
    topic_dist = {"Billing": {"volume": 1, "percentage": 100}}
    topics_by_conv = {"conv_1": "Billing"}
    strategy._execute_phase_2_topic_detection = AsyncMock(
        return_value=(
            _agent_result("TopicDetectionAgent", data={"topic_distribution": topic_dist}),
            topic_dist,
            topics_by_conv,
        )
    )
    strategy._execute_phase_2_4_bpo = AsyncMock(return_value=_agent_result("BPO", {}))
    strategy._execute_phase_2_5_subtopics = AsyncMock(
        return_value=(
            _agent_result("Subtopics", data={"subtopics_by_tier1_topic": {}}),
            {},
        )
    )
    strategy._execute_phase_3_per_topic = AsyncMock(
        return_value=({"Billing": {}}, {"Billing": []})
    )
    strategy._execute_phase_4_fin = AsyncMock(
        return_value=_agent_result("FinPerformanceAgent", {})
    )
    strategy._execute_phase_4_5_insights = AsyncMock(
        return_value={"CorrelationAgent": {"data": {}}, "QualityInsightsAgent": {"data": {}}}
    )
    strategy._execute_phase_5_trends = AsyncMock(
        return_value=_agent_result("TrendAgent", {})
    )
    strategy._execute_phase_5_5_validation = lambda *args, **kwargs: None
    strategy._execute_phase_6_formatting = AsyncMock(
        return_value=_agent_result("OutputFormatterAgent", {"formatted_output": "ok"})
    )
    strategy._build_final_payload = MagicMock(return_value={"formatted_output": "ok"})
    strategy._save_snapshot = AsyncMock(return_value=None)

    recorded_stages: list[str] = []

    def capture_log(self, stage_name, count):
        recorded_stages.append(stage_name)
        return BaseOrchestrator.log_stage_metrics(self, stage_name, count)

    strategy.log_stage_metrics = types.MethodType(capture_log, strategy)

    context = _make_context(conversation_count=5)
    result = await strategy.execute(context)

    assert result.success
    assert recorded_stages == [
        "Post-Fetch",
        "Post-Segmentation",
        "Post-TopicDetection",
        "Pre-Formatting",
    ]


class DummyLLMAgent:
    """Minimal agent that uses provider-aware semaphore."""

    name = "TopicDetectionAgent"

    def __init__(self):
        self.ai_client = object()
        self.llm_semaphore = get_recommended_semaphore(self.ai_client)

    async def execute(self, context: AgentContext) -> AgentResult:
        async with self.llm_semaphore:
            await asyncio.sleep(0)
        return _agent_result(self.name, {"topics": 1})


class DummyResilienceStrategy(OrchestrationStrategy):
    """Strategy that exercises timeout, semaphore, and data quality gates."""

    def __init__(self):
        super().__init__()
        self.agent = DummyLLMAgent()
        self.stage_history: list[str] = []

    def get_strategy_name(self) -> str:
        return "DummyResilienceStrategy"

    async def execute(self, context: AgentContext, **kwargs):
        self.log_stage_metrics("Post-Fetch", len(context.conversations or []))
        self.stage_history.append("Post-Fetch")

        agent_result = await self._execute_with_timeout(self.agent, context)

        self.log_stage_metrics("Pre-Formatting", len(context.conversations or []))
        self.stage_history.append("Pre-Formatting")

        return AgentResult(
            agent_name=self.get_strategy_name(),
            success=agent_result.success,
            data={"agent": agent_result.data},
            confidence=agent_result.confidence,
            confidence_level=agent_result.confidence_level,
        )


@pytest.mark.asyncio
async def test_end_to_end_resilience(caplog):
    strategy = DummyResilienceStrategy()
    orchestrator = UnifiedOrchestrator(strategy=strategy)

    context = _make_context(conversation_count=10)

    with caplog.at_level("WARNING"):
        result = await orchestrator.execute(context)

    assert result.success
    assert strategy.stage_history == ["Post-Fetch", "Pre-Formatting"]
    assert strategy.agent.llm_semaphore._value == settings.openai_concurrency
    assert "DATA DROP ALERT" not in caplog.text

