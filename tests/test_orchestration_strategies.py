"""
Unit tests for core orchestration strategies backed by UnifiedOrchestrator.
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock

import pytest

from src.agents.base_agent import AgentContext
from src.services.strategies.comprehensive import ComprehensiveStrategy
from src.services.strategies.multi_agent import MultiAgentStrategy
from src.services.strategies.story_driven import StoryDrivenStrategy


@pytest.fixture
def sample_context():
    """Minimal AgentContext used across strategy tests."""
    now = datetime.utcnow()
    return AgentContext(
        analysis_id="test-analysis",
        analysis_type="integration",
        start_date=now - timedelta(days=7),
        end_date=now,
        conversations=[{"id": "conv-1"}],
        metadata={"canny_posts": []},
    )


@pytest.mark.asyncio
async def test_comprehensive_strategy_execute_success(monkeypatch, sample_context):
    strategy = ComprehensiveStrategy()
    fake_results = {
        "validation": {"data_quality_score": 0.92, "warnings": []},
        "summary": {"ok": True},
    }
    monkeypatch.setattr(
        strategy,
        "run_comprehensive_analysis",
        AsyncMock(return_value=fake_results),
    )

    result = await strategy.execute(sample_context, options={"max_conversations": 50})

    assert result.success is True
    assert result.agent_name == "ComprehensiveStrategy"
    assert result.data == fake_results
    assert result.confidence == pytest.approx(0.92, rel=1e-3)
    assert result.confidence_level == "high"


@pytest.mark.asyncio
async def test_comprehensive_strategy_execute_error(monkeypatch, sample_context):
    strategy = ComprehensiveStrategy()
    error_payload = {"error": "No conversations"}
    monkeypatch.setattr(
        strategy,
        "run_comprehensive_analysis",
        AsyncMock(return_value=error_payload),
    )

    result = await strategy.execute(sample_context, options={})

    assert result.success is False
    assert result.error_message == "No conversations"
    assert result.data == error_payload
    assert result.confidence == 0.0
    assert result.confidence_level == "low"


@pytest.mark.asyncio
async def test_multi_agent_strategy_execute_success(monkeypatch, sample_context):
    strategy = MultiAgentStrategy()
    workflow_state = {
        "status": "completed",
        "agent_results": {
            "DataAgent": {"confidence": 0.9},
            "InsightAgent": {"confidence": 0.8},
        },
        "total_execution_time": 1.25,
        "errors": [],
    }
    monkeypatch.setattr(
        strategy,
        "_run_workflow",
        AsyncMock(return_value=workflow_state),
    )

    result = await strategy.execute(sample_context, generate_gamma=False)

    assert result.success is True
    assert result.data == workflow_state
    assert result.confidence == pytest.approx(0.85, rel=1e-3)
    assert result.confidence_level == "high"
    assert result.execution_time == workflow_state["total_execution_time"]


@pytest.mark.asyncio
async def test_multi_agent_strategy_execute_failure(monkeypatch, sample_context):
    strategy = MultiAgentStrategy()
    failure_state = {
        "status": "failed",
        "agent_results": {},
        "errors": ["DataAgent failed"],
        "total_execution_time": 2.0,
    }
    monkeypatch.setattr(
        strategy,
        "_run_workflow",
        AsyncMock(return_value=failure_state),
    )

    result = await strategy.execute(sample_context, generate_gamma=True)

    assert result.success is False
    assert "DataAgent failed" in result.error_message
    assert result.data == failure_state
    assert result.confidence == 0.0
    assert result.confidence_level == "low"


@pytest.mark.asyncio
async def test_story_driven_strategy_execute_success(monkeypatch, sample_context):
    strategy = StoryDrivenStrategy()
    story_results = {
        "actionable_insights": {
            "insight_confidence": {"overall_confidence": 0.83}
        },
        "journey_stories": {"journey_analysis": "Narrative"},
    }
    monkeypatch.setattr(
        strategy,
        "run_story_driven_analysis",
        AsyncMock(return_value=story_results),
    )

    result = await strategy.execute(sample_context, options={"generate_gamma_presentation": False})

    assert result.success is True
    assert result.data == story_results
    assert result.confidence == pytest.approx(0.83, rel=1e-3)
    assert result.confidence_level == "high"


@pytest.mark.asyncio
async def test_story_driven_strategy_execute_failure(monkeypatch, sample_context):
    strategy = StoryDrivenStrategy()
    monkeypatch.setattr(
        strategy,
        "run_story_driven_analysis",
        AsyncMock(return_value={"error": "LLM failure"}),
    )

    result = await strategy.execute(sample_context)

    assert result.success is False
    assert result.error_message == "LLM failure"
    assert result.confidence == 0.0
    assert result.confidence_level == "low"

