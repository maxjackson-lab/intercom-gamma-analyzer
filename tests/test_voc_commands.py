"""
Tests for Voice of Customer CLI commands.
"""

import json
import sys
import types
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.cli import voc_commands


@pytest.fixture
def capture_console(monkeypatch):
    outputs = []

    def fake_print(*args, **kwargs):
        outputs.append(" ".join(str(arg) for arg in args))

    monkeypatch.setattr(voc_commands.console, "print", fake_print)
    return outputs


@pytest.fixture
def topic_analysis_env(monkeypatch, tmp_path):
    """Patch heavy dependencies for topic analysis flows."""
    voc_commands.console.record = False

    class DummyTopicOrchestrator:
        def __init__(self, audit_trail=None, execution_monitor=None):
            self.audit_trail = audit_trail
            self.execution_monitor = execution_monitor

        async def execute_weekly_analysis(
            self,
            conversations,
            week_id,
            start_date,
            end_date,
            period_type,
            period_label,
            digest_mode=False,
        ):
            return {
                "formatted_report": "# Report",
                "period_label": period_label,
                "analysis_metadata": {"conversations": len(conversations)},
            }

    chunk_module = types.SimpleNamespace()

    class DummyFetcher:
        async def fetch_conversations_chunked(self, start, end):
            return [{"id": "conv"}]

    chunk_module.ChunkedFetcher = DummyFetcher
    monkeypatch.setitem(sys.modules, "src.services.chunked_fetcher", chunk_module)

    topic_module = types.SimpleNamespace(TopicOrchestrator=DummyTopicOrchestrator)
    monkeypatch.setitem(sys.modules, "src.agents.topic_orchestrator", topic_module)

    audit_module = types.SimpleNamespace(
        AuditTrail=type(
            "AuditTrail",
            (),
            {
                "__init__": lambda self, output_dir: None,
                "step": lambda *args, **kwargs: None,
                "decision": lambda *args, **kwargs: None,
                "save_report": lambda self: tmp_path / "audit.md",
                "save_json": lambda self: tmp_path / "audit.json",
            },
        )
    )
    monkeypatch.setitem(sys.modules, "src.services.audit_trail", audit_module)

    time_module = types.SimpleNamespace(
        detect_period_type=lambda start, end: ("weekly", "Week 1"),
        generate_descriptive_filename=lambda prefix, sd, ed, file_type="txt", period_label="Custom": f"{prefix}.{file_type}",
    )
    monkeypatch.setitem(sys.modules, "src.utils.time_utils", time_module)

    exec_monitor = types.SimpleNamespace(
        get_execution_monitor=lambda: types.SimpleNamespace(
            start_execution=AsyncMock()
        )
    )
    monkeypatch.setitem(sys.modules, "src.services.execution_monitor", exec_monitor)

    test_data_module = types.SimpleNamespace(
        TestDataGenerator=type(
            "TestDataGenerator",
            (),
            {"generate_conversations": lambda self, count, start_date, end_date: [{"id": i} for i in range(count)]},
        )
    )
    monkeypatch.setitem(sys.modules, "src.services.test_data_generator", test_data_module)

    output_module = types.SimpleNamespace(
        get_output_file_path=lambda filename: tmp_path / filename,
        get_output_directory=lambda: tmp_path,
    )
    monkeypatch.setitem(sys.modules, "src.utils.output_manager", output_module)

    return tmp_path


@pytest.mark.asyncio
async def test_run_topic_based_analysis_test_mode(topic_analysis_env, capture_console):
    await voc_commands.run_topic_based_analysis_custom(
        start_date=datetime(2024, 1, 1),
        end_date=datetime(2024, 1, 2),
        generate_gamma=False,
        test_mode=True,
        test_data_count="3",
    )

    assert any("Topic-based analysis" in line or "Report" in line for line in capture_console)
    files = list(topic_analysis_env.iterdir())
    assert files, "Expected report file to be created"


@pytest.mark.asyncio
async def test_run_topic_based_analysis_with_gamma(monkeypatch, topic_analysis_env):
    class DummyGammaClient:
        def __init__(self):
            self.calls = []

        async def generate_presentation(self, input_text, **kwargs):
            self.calls.append(("generate", input_text))
            return "gen-123"

        async def poll_generation(self, generation_id, **kwargs):
            return {"status": "completed", "gammaUrl": "https://gamma.example/p/abc"}

    gamma_module = types.SimpleNamespace(GammaClient=DummyGammaClient)
    monkeypatch.setitem(sys.modules, "src.services.gamma_client", gamma_module)

    await voc_commands.run_topic_based_analysis_custom(
        start_date=datetime(2024, 1, 1),
        end_date=datetime(2024, 1, 2),
        generate_gamma=True,
        test_mode=True,
        test_data_count="2",
    )

    gamma_files = list(topic_analysis_env.glob("**/*Gamma_URL_Topic*.txt"))
    assert gamma_files, "Gamma URL file should be saved"


@pytest.mark.asyncio
async def test_run_voice_of_customer_analysis_topic(monkeypatch):
    # Patch time helpers
    time_module = types.SimpleNamespace(
        calculate_date_range=lambda **kwargs: (datetime(2024, 1, 1), datetime(2024, 1, 7)),
        format_date_range_for_display=lambda start, end: "Jan 1 - Jan 7",
    )
    monkeypatch.setitem(sys.modules, "src.utils.time_utils", time_module)

    tz_module = types.SimpleNamespace(
        get_date_range_pacific=lambda start, end: (datetime(2024, 1, 1), datetime(2024, 1, 7))
    )
    monkeypatch.setitem(sys.modules, "src.utils.timezone_utils", tz_module)

    runner = AsyncMock()
    monkeypatch.setattr(voc_commands, "run_topic_based_analysis_custom", runner)
    monkeypatch.setattr(voc_commands, "run_synthesis_analysis_custom", AsyncMock())
    monkeypatch.setattr(voc_commands, "run_complete_analysis_custom", AsyncMock())
    monkeypatch.setattr(voc_commands, "fetch_canny_conversations_from_warehouse", AsyncMock(return_value=[]))

    await voc_commands.run_voice_of_customer_analysis(
        time_period="week",
        periods_back=1,
        start_date=None,
        end_date=None,
        ai_model="gpt-test",
        enable_fallback=True,
        include_trends=False,
        include_canny=False,
        llm_topic_detection=False,
        canny_board_id=None,
        generate_gamma=False,
        test_mode=True,
        test_data_count="small",
        verbose=False,
        analysis_type="topic-based",
        audit_trail=False,
        output_dir="outputs",
        digest_mode=False,
    )

    runner.assert_awaited()


@pytest.mark.asyncio
async def test_run_voice_of_customer_analysis_synthesis(monkeypatch):
    time_module = types.SimpleNamespace(
        calculate_date_range=lambda **kwargs: (datetime(2024, 2, 1), datetime(2024, 2, 7)),
        format_date_range_for_display=lambda start, end: "Feb 1 - Feb 7",
    )
    monkeypatch.setitem(sys.modules, "src.utils.time_utils", time_module)
    tz_module = types.SimpleNamespace(
        get_date_range_pacific=lambda start, end: (datetime(2024, 2, 1), datetime(2024, 2, 7))
    )
    monkeypatch.setitem(sys.modules, "src.utils.timezone_utils", tz_module)

    synth_runner = AsyncMock()
    monkeypatch.setattr(voc_commands, "run_synthesis_analysis_custom", synth_runner)
    monkeypatch.setattr(voc_commands, "run_topic_based_analysis_custom", AsyncMock())
    monkeypatch.setattr(voc_commands, "run_complete_analysis_custom", AsyncMock())
    monkeypatch.setattr(voc_commands, "fetch_canny_conversations_from_warehouse", AsyncMock(return_value=[{"id": 1}]))

    await voc_commands.run_voice_of_customer_analysis(
        time_period="week",
        periods_back=1,
        start_date=None,
        end_date=None,
        ai_model="gpt-test",
        enable_fallback=False,
        include_trends=False,
        include_canny=True,
        llm_topic_detection=False,
        canny_board_id="board",
        generate_gamma=False,
        test_mode=False,
        test_data_count="100",
        verbose=False,
        analysis_type="synthesis",
        audit_trail=False,
        output_dir="outputs",
        digest_mode=False,
    )

    synth_runner.assert_awaited()


@pytest.mark.asyncio
async def test_run_voice_of_customer_analysis_complete_branch(monkeypatch):
    time_module = types.SimpleNamespace(
        calculate_date_range=lambda **kwargs: (datetime(2024, 4, 1), datetime(2024, 4, 7)),
        format_date_range_for_display=lambda start, end: "Apr 1 - Apr 7",
    )
    monkeypatch.setitem(sys.modules, "src.utils.time_utils", time_module)
    tz_module = types.SimpleNamespace(
        get_date_range_pacific=lambda start, end: (datetime(2024, 4, 1), datetime(2024, 4, 7))
    )
    monkeypatch.setitem(sys.modules, "src.utils.timezone_utils", tz_module)

    complete_runner = AsyncMock()
    monkeypatch.setattr(voc_commands, "run_complete_analysis_custom", complete_runner)
    monkeypatch.setattr(voc_commands, "run_topic_based_analysis_custom", AsyncMock())
    monkeypatch.setattr(voc_commands, "run_synthesis_analysis_custom", AsyncMock())
    monkeypatch.setattr(voc_commands, "fetch_canny_conversations_from_warehouse", AsyncMock(return_value=[]))

    await voc_commands.run_voice_of_customer_analysis(
        time_period="week",
        periods_back=1,
        start_date=None,
        end_date=None,
        ai_model="gpt-4o",
        enable_fallback=False,
        include_trends=True,
        include_canny=False,
        llm_topic_detection=False,
        canny_board_id=None,
        generate_gamma=True,
        test_mode=False,
        test_data_count="micro",
        verbose=False,
        analysis_type="complete",
        audit_trail=True,
        output_dir="outputs",
        digest_mode=True,
    )

    complete_runner.assert_awaited_once()
    _, kwargs = complete_runner.await_args
    assert kwargs["digest_mode"] is True


@pytest.mark.asyncio
async def test_run_voice_of_customer_analysis_narrative_v2(monkeypatch):
    time_module = types.SimpleNamespace(
        calculate_date_range=lambda **kwargs: (datetime(2024, 6, 1), datetime(2024, 6, 7)),
        format_date_range_for_display=lambda start, end: "Jun 1 - Jun 7",
    )
    monkeypatch.setitem(sys.modules, "src.utils.time_utils", time_module)
    tz_module = types.SimpleNamespace(
        get_date_range_pacific=lambda start, end: (datetime(2024, 6, 1), datetime(2024, 6, 7))
    )
    monkeypatch.setitem(sys.modules, "src.utils.timezone_utils", tz_module)

    topic_runner = AsyncMock()
    monkeypatch.setattr(voc_commands, "run_topic_based_analysis_custom", topic_runner)
    monkeypatch.setattr(voc_commands, "run_complete_analysis_custom", AsyncMock())
    monkeypatch.setattr(voc_commands, "run_synthesis_analysis_custom", AsyncMock())
    monkeypatch.setattr(voc_commands, "fetch_canny_conversations_from_warehouse", AsyncMock(return_value=[]))

    fake_orchestrator = object()
    monkeypatch.setattr(voc_commands, "TopicOrchestratorV2", fake_orchestrator)

    await voc_commands.run_voice_of_customer_analysis(
        time_period="week",
        periods_back=1,
        start_date=None,
        end_date=None,
        ai_model="gpt-test",
        enable_fallback=True,
        include_trends=False,
        include_canny=True,
        llm_topic_detection=False,
        canny_board_id="canny",
        generate_gamma=False,
        test_mode=True,
        test_data_count="small",
        verbose=False,
        analysis_type="narrative-v2",
        audit_trail=False,
        output_dir="outputs",
        digest_mode=False,
    )

    topic_runner.assert_awaited_once()
    _, kwargs = topic_runner.await_args
    assert kwargs["orchestrator_cls"] is fake_orchestrator
    assert kwargs["mode_label"] == "VoC Narrative V2"
    assert kwargs["output_slug"] == "narrative_v2"


@pytest.mark.asyncio
async def test_run_comprehensive_analysis_success(monkeypatch, tmp_path, capture_console):
    time_module = types.SimpleNamespace(
        calculate_date_range=lambda **kwargs: (datetime(2024, 3, 1), datetime(2024, 3, 7))
    )
    monkeypatch.setitem(sys.modules, "src.utils.time_utils", time_module)

    test_data_module = types.SimpleNamespace(
        parse_test_data_count=lambda value: (100, "small"),
        get_preset_display_name=lambda count, preset: f"{count} ({preset})",
    )
    monkeypatch.setitem(sys.modules, "src.config.test_data", test_data_module)

    agent_result = types.SimpleNamespace(data={"analysis_metadata": {"total_conversations": 10}})

    class DummyOrchestrator:
        def __init__(self, strategy):
            self.strategy = strategy

        async def execute(self, context, options):
            return agent_result

    monkeypatch.setattr(voc_commands, "UnifiedOrchestrator", lambda strategy: DummyOrchestrator(strategy))
    monkeypatch.setattr(voc_commands, "ComprehensiveStrategy", lambda: object())

    await voc_commands.run_comprehensive_analysis(
        start_date="2024-03-01",
        end_date="2024-03-07",
        time_period=None,
        periods_back=1,
        output_format="json",
        gamma_export=None,
        output_dir=str(tmp_path),
        test_mode=True,
        test_data_count="small",
        verbose=False,
        audit_trail=False,
        ai_model=None,
        filter_category=None,
        max_conversations=500,
        gamma_style="night",
        export_docs=False,
        include_fin_analysis=True,
        include_technical_analysis=False,
        include_macro_analysis=False,
    )

    saved_files = list(Path(tmp_path).glob("comprehensive_analysis_*.json"))
    assert saved_files, "Expected results file"
    assert any("Comprehensive Analysis Completed" in line for line in capture_console)

