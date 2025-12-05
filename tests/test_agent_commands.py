"""
Tests for agent CLI commands.
"""

import sys
import types
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from src.cli import agent_commands


@pytest.fixture
def agent_env(monkeypatch, tmp_path):
    """Patch heavy agent dependencies with lightweight stubs."""
    console_output = []

    def fake_print(*args, **kwargs):
        console_output.append(" ".join(str(arg) for arg in args))

    monkeypatch.setattr(agent_commands.console, "print", fake_print)
    monkeypatch.setattr(agent_commands.settings, "effective_output_directory", str(tmp_path))

    # Chunked fetcher stub
    class DummyFetcher:
        async def fetch_conversations_chunked(self, *args, **kwargs):
            return [{"id": "conv", "conversation_parts": {"conversation_parts": []}}]

    chunk_module = types.SimpleNamespace(ChunkedFetcher=DummyFetcher)
    monkeypatch.setitem(sys.modules, "src.services.chunked_fetcher", chunk_module)

    # Test data generator
    class DummyTestDataGenerator:
        def generate_conversations(self, count, start_date, end_date, agent_filter=None):
            return [
                {
                    "id": i,
                    "conversation_parts": {"conversation_parts": []},
                    "tags": {"tags": []},
                }
                for i in range(count)
            ]

    test_data_module = types.SimpleNamespace(TestDataGenerator=DummyTestDataGenerator)
    monkeypatch.setitem(sys.modules, "src.services.test_data_generator", test_data_module)

    # Agent context stub
    class DummyAgentContext:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    base_agent_module = types.SimpleNamespace(AgentContext=DummyAgentContext)
    monkeypatch.setitem(sys.modules, "src.agents.base_agent", base_agent_module)

    # Agent performance agent stub
    agent_instances = []

    class DummyAgentPerformanceAgent:
        def __init__(self, agent_filter=None):
            self.agent_filter = agent_filter

            async def _execute(context, **kwargs):
                if kwargs.get("individual_breakdown"):
                    data = {
                        "team_metrics": {
                            "total_agents": 2,
                            "total_conversations": 10,
                            "team_fcr_rate": 0.8,
                            "team_escalation_rate": 0.1,
                            "team_qa_overall": 0.85,
                            "team_qa_connection": 0.8,
                            "team_qa_communication": 0.82,
                            "team_qa_content": 0.83,
                            "agents_with_qa_metrics": 2,
                        },
                        "agents": [
                            {
                                "agent_name": "Alex",
                                "total_conversations": 5,
                                "fcr_rate": 0.9,
                                "escalation_rate": 0.05,
                                "median_response_hours": 2.0,
                                "fcr_rank": 1,
                                "coaching_priority": "low",
                            }
                        ],
                    }
                else:
                    data = {
                        "total_conversations": 20,
                        "fcr_rate": 0.75,
                        "median_resolution_hours": 4.0,
                        "escalation_rate": 0.2,
                        "avg_qa_overall": 0.7,
                        "avg_qa_connection": 0.68,
                        "avg_qa_communication": 0.7,
                        "performance_by_category": {
                            "Billing": {
                                "volume": 10,
                                "fcr_rate": 0.8,
                                "escalation_rate": 0.15,
                                "median_resolution_hours": 3.5,
                            }
                        },
                        "llm_insights": "Keep investing in training.",
                    }
                return types.SimpleNamespace(
                    success=True,
                    data=data,
                    confidence_level=types.SimpleNamespace(value="HIGH"),
                )

            self.execute = AsyncMock(side_effect=_execute)
            agent_instances.append(self)

    agent_module = types.SimpleNamespace(AgentPerformanceAgent=DummyAgentPerformanceAgent)
    monkeypatch.setitem(sys.modules, "src.agents.agent_performance_agent", agent_module)

    # Data preprocessor stub
    class DummyPreprocessor:
        def preprocess_conversations(self, conversations, options):
            return conversations, {"processed_count": len(conversations)}

    data_pre_module = types.SimpleNamespace(DataPreprocessor=DummyPreprocessor)
    monkeypatch.setitem(sys.modules, "src.services.data_preprocessor", data_pre_module)

    # Gamma generator stub
    gamma_instances = []

    class DummyGammaGenerator:
        def __init__(self):
            self.generate_from_markdown = AsyncMock(
                return_value={"gamma_url": "https://gamma.example/p/123", "generation_id": "gen1"}
            )
            gamma_instances.append(self)

    gamma_module = types.SimpleNamespace(GammaGenerator=DummyGammaGenerator)
    monkeypatch.setitem(sys.modules, "src.services.gamma_generator", gamma_module)

    gamma_client_module = types.SimpleNamespace(GammaAPIError=Exception)
    monkeypatch.setitem(sys.modules, "src.services.gamma_client", gamma_client_module)

    # Test data module for coaching report
    test_data_config = types.SimpleNamespace(
        generate_test_conversations=lambda count: [
            {
                "id": i,
                "conversation_parts": {"conversation_parts": [{"author": {"type": "admin", "email": "agent@hirehoratio.co"}}]},
            }
            for i in range(count)
        ]
    )
    monkeypatch.setitem(sys.modules, "src.config.test_data", test_data_config)

    return {
        "console_output": console_output,
        "tmp_path": tmp_path,
        "agent_instances": agent_instances,
        "gamma_instances": gamma_instances,
    }


@pytest.mark.asyncio
async def test_run_agent_performance_analysis_test_mode(agent_env):
    await agent_commands.run_agent_performance_analysis(
        agent="horatio",
        start_date=datetime(2024, 1, 1),
        end_date=datetime(2024, 1, 7),
        focus_categories=None,
        generate_gamma=True,
        individual_breakdown=False,
        analyze_troubleshooting=False,
        test_mode=True,
        test_data_count=5,
        audit_trail=False,
    )

    saved_files = list(Path(agent_env["tmp_path"]).glob("agent_performance_*.json"))
    assert saved_files, "Results file expected"
    assert agent_env["gamma_instances"], "Gamma generator should be instantiated"
    agent_instance = agent_env["agent_instances"][0]
    agent_instance.execute.assert_awaited()


@pytest.mark.asyncio
async def test_run_agent_coaching_report(agent_env):
    await agent_commands.run_agent_coaching_report(
        vendor="horatio",
        start_date=datetime(2024, 1, 1),
        end_date=datetime(2024, 1, 7),
        top_n=3,
        generate_gamma=False,
        test_mode=True,
        test_data_count=5,
        output_dir=str(agent_env["tmp_path"]),
    )

    assert agent_env["agent_instances"][-1].execute.await_count >= 1










