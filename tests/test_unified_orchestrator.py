"""
Tests for unified orchestrator and base orchestrator utilities.
"""

import asyncio
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from src.agents.base_agent import AgentContext, AgentMetrics, AgentResult, ConfidenceLevel
from src.services.base_orchestrator import BaseOrchestrator
from src.services.unified_orchestrator import OrchestrationStrategy, UnifiedOrchestrator


@pytest.fixture
def agent_context():
    return AgentContext(
        analysis_id="test",
        analysis_type="unit",
        start_date=datetime.utcnow(),
        end_date=datetime.utcnow() + timedelta(days=1),
    )


class DummyStrategy(OrchestrationStrategy):
    def __init__(self, result: AgentResult):
        super().__init__()
        self._result = result

    async def execute(self, context: AgentContext, **kwargs):
        return self._result

    def get_strategy_name(self) -> str:
        return "DummyStrategy"


class DummyFailingStrategy(OrchestrationStrategy):
    def __init__(self):
        super().__init__()

    async def execute(self, context: AgentContext, **kwargs):
        raise RuntimeError("boom")

    def get_strategy_name(self) -> str:
        return "FailingStrategy"


@pytest.mark.asyncio
async def test_unified_orchestrator_execute_success(agent_context):
    result = AgentResult(
        agent_name="DummyStrategy",
        success=True,
        data={"value": 1},
        confidence=0.9,
        confidence_level=ConfidenceLevel.HIGH,
    )
    orchestrator = UnifiedOrchestrator(strategy=DummyStrategy(result))

    response = await orchestrator.execute(agent_context)

    assert response.success
    assert response.execution_time > 0


@pytest.mark.asyncio
async def test_unified_orchestrator_execute_failure(agent_context):
    orchestrator = UnifiedOrchestrator(strategy=DummyFailingStrategy())

    response = await orchestrator.execute(agent_context)

    assert not response.success
    assert response.error_message == "boom"


class DummyBaseOrchestrator(BaseOrchestrator):
    pass


@pytest.mark.asyncio
async def test_execute_with_timeout_success(agent_context):
    orchestrator = DummyBaseOrchestrator()

    class FastAgent:
        async def execute(self, context):
            return AgentResult(
                agent_name="FastAgent",
                success=True,
                data={},
                confidence=0.8,
                confidence_level=ConfidenceLevel.HIGH,
            )

    result = await orchestrator._execute_with_timeout(FastAgent(), agent_context, timeout=1)
    assert result.success


@pytest.mark.asyncio
async def test_execute_with_timeout_timeout(agent_context):
    orchestrator = DummyBaseOrchestrator()

    class SlowAgent:
        async def execute(self, context):
            await asyncio.sleep(0.2)
            return AgentResult(
                agent_name="SlowAgent",
                success=True,
                data={},
                confidence=0.8,
                confidence_level=ConfidenceLevel.HIGH,
            )

    result = await orchestrator._execute_with_timeout(SlowAgent(), agent_context, timeout=0.01)
    assert not result.success
    assert "timed out" in result.error_message


def test_checkpoint_save_and_load(tmp_path):
    orchestrator = DummyBaseOrchestrator(checkpoint_dir=tmp_path)
    data = {"agent_name": "Test", "success": True, "data": {"value": 1}}

    orchestrator._save_checkpoint("analysis", "agent", data)
    loaded = orchestrator._load_checkpoint("analysis", "agent")

    assert loaded == data


@pytest.mark.asyncio
async def test_aggregate_results():
    orchestrator = DummyBaseOrchestrator()
    results = [
        AgentResult(
            agent_name="A",
            success=True,
            data={"a": 1},
            confidence=0.9,
            confidence_level=ConfidenceLevel.HIGH,
            metrics=AgentMetrics(execution_time=1, llm_calls=1),
        ),
        AgentResult(
            agent_name="B",
            success=False,
            data={"b": 2},
            confidence=0.5,
            confidence_level=ConfidenceLevel.LOW,
            metrics=AgentMetrics(execution_time=2, llm_calls=2),
        ),
    ]

    aggregated = await orchestrator._aggregate_results(results)

    assert aggregated.data["A"]["a"] == 1
    assert aggregated.metrics.llm_calls == 3
    assert not aggregated.success


def test_confidence_level_from_score():
    orchestrator = DummyBaseOrchestrator()
    assert orchestrator._confidence_level_from_score(0.85) == ConfidenceLevel.HIGH
    assert orchestrator._confidence_level_from_score(0.65) == ConfidenceLevel.MEDIUM
    assert orchestrator._confidence_level_from_score(0.2) == ConfidenceLevel.LOW

