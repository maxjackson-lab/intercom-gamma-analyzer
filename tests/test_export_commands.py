"""
Tests for export CLI commands.
"""

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.cli import export_commands


@pytest.fixture(autouse=True)
def prevent_exit(monkeypatch):
    """Never let commands terminate the interpreter."""

    def fake_exit(code=0):
        raise SystemExit(code)

    monkeypatch.setattr(export_commands.sys, "exit", fake_exit)


@pytest.fixture
def capture_console(monkeypatch):
    outputs = []

    def fake_print(*args, **kwargs):
        outputs.append(" ".join(str(arg) for arg in args))

    monkeypatch.setattr(export_commands.console, "print", fake_print)
    return outputs


@pytest.mark.asyncio
async def test_run_data_export_success(monkeypatch, capture_console):
    conversations = [{"id": 1}, {"id": 2}]

    class DummyIntercom:
        async def fetch_conversations_by_date_range(self, *_, **__):
            return conversations

    class DummyExporter:
        def __init__(self):
            self.called_formats = []

        def export_conversations_to_excel(self, convs, prefix, include_metrics=False):
            self.called_formats.append("excel")
            return f"{prefix}.xlsx"

        def export_conversations_to_csv(self, convs, prefix):
            self.called_formats.append("csv")
            return [f"{prefix}.csv"]

        def export_raw_data_to_json(self, convs, prefix):
            self.called_formats.append("json")
            return f"{prefix}.json"

        def export_to_parquet(self, convs, prefix):
            self.called_formats.append("parquet")
            return f"{prefix}.parquet"

    exporter = DummyExporter()
    monkeypatch.setattr(export_commands, "IntercomSDKService", lambda: DummyIntercom())
    monkeypatch.setattr(export_commands, "DataExporter", lambda: exporter)

    await export_commands.run_data_export(
        start_date=datetime(2024, 1, 1),
        end_date=datetime(2024, 1, 2),
        export_format="all",
        max_pages=10,
        include_metrics=True,
    )

    assert set(exporter.called_formats) == {"excel", "csv", "json", "parquet"}
    assert any("Export completed successfully" in line for line in capture_console)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "export_format,expected_methods",
    [
        ("excel", ["excel"]),
        ("csv", ["csv"]),
        ("json", ["json"]),
        ("parquet", ["parquet"]),
    ],
)
async def test_run_data_export_each_format(monkeypatch, export_format, expected_methods):
    conversations = [{"id": 1}]

    class DummyIntercom:
        async def fetch_conversations_by_date_range(self, *_, **__):
            return conversations

    class DummyExporter:
        def __init__(self):
            self.called = []

        def export_conversations_to_excel(self, *args, **kwargs):
            self.called.append("excel")
            return "file.xlsx"

        def export_conversations_to_csv(self, *args, **kwargs):
            self.called.append("csv")
            return ["file.csv"]

        def export_raw_data_to_json(self, *args, **kwargs):
            self.called.append("json")
            return "file.json"

        def export_to_parquet(self, *args, **kwargs):
            self.called.append("parquet")
            return "file.parquet"

    exporter = DummyExporter()
    monkeypatch.setattr(export_commands, "IntercomSDKService", lambda: DummyIntercom())
    monkeypatch.setattr(export_commands, "DataExporter", lambda: exporter)

    await export_commands.run_data_export(
        start_date=datetime(2024, 1, 1),
        end_date=datetime(2024, 1, 1),
        export_format=export_format,
        max_pages=None,
        include_metrics=False,
    )

    assert exporter.called == expected_methods


@pytest.mark.asyncio
async def test_run_data_export_invalid_format():
    with pytest.raises(SystemExit):
        await export_commands.run_data_export(
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 2),
            export_format="xml",
            max_pages=None,
            include_metrics=False,
        )


@pytest.mark.asyncio
async def test_run_general_query_success(monkeypatch, capture_console):
    class DummyQueryService:
        def __init__(self, *_):
            self.executed = False

        def build_suggested_query(self, query_type, suggestion):
            return {"type": query_type, "suggestion": suggestion}

        async def execute_query(self, query, **kwargs):
            self.executed = True
            return {
                "total_conversations": 5,
                "export_results": {"json": "file.json"},
            }

    monkeypatch.setattr(export_commands, "IntercomSDKService", lambda: object())
    monkeypatch.setattr(export_commands, "DataExporter", lambda: object())
    monkeypatch.setattr(export_commands, "GeneralQueryService", DummyQueryService)

    await export_commands.run_general_query(
        query_type="topics",
        suggestion="billing",
        custom_query=None,
        export_format="json",
        max_pages=5,
    )

    assert any("Query executed successfully" in line for line in capture_console)


@pytest.mark.asyncio
async def test_run_general_query_invalid_json(monkeypatch):
    monkeypatch.setattr(export_commands, "IntercomSDKService", lambda: object())
    monkeypatch.setattr(export_commands, "DataExporter", lambda: object())
    monkeypatch.setattr(export_commands, "GeneralQueryService", lambda *_: None)

    with pytest.raises(SystemExit):
        await export_commands.run_general_query(
            query_type=None,
            suggestion=None,
            custom_query="{bad json",
            export_format="json",
            max_pages=None,
        )


@pytest.mark.asyncio
async def test_run_custom_analysis_success(monkeypatch, capture_console):
    request = export_commands.AnalysisRequest(
        mode=export_commands.AnalysisMode.CUSTOM,
        start_date=datetime(2024, 1, 1).date(),
        end_date=datetime(2024, 1, 2).date(),
    )

    class DummyResult:
        analysis_duration_seconds = 1.23
        total_conversations_analyzed = 42
        analysis_content = "# Test"

        def dict(self):
            return {"ok": True}

    analyzer = AsyncMock()
    analyzer.analyze.return_value = DummyResult()

    monkeypatch.setattr(export_commands, "IntercomSDKService", lambda: object())
    monkeypatch.setattr(export_commands, "MetricsCalculator", lambda: object())
    monkeypatch.setattr(export_commands, "OpenAIClient", lambda: object())
    monkeypatch.setattr(export_commands, "TrendAnalyzer", lambda *args: analyzer)
    monkeypatch.setattr(export_commands, "save_markdown_output", MagicMock())
    monkeypatch.setattr(export_commands, "generate_gamma_presentation", AsyncMock())

    await export_commands.run_custom_analysis(
        request=request,
        generate_gamma=False,
        output_format="markdown",
    )

    analyzer.analyze.assert_awaited()
    export_commands.save_markdown_output.assert_called_once()
    export_commands.generate_gamma_presentation.assert_not_called()
    assert any("Analysis completed successfully" in line for line in capture_console)


@pytest.mark.asyncio
async def test_run_custom_analysis_with_gamma(monkeypatch):
    request = export_commands.AnalysisRequest(
        mode=export_commands.AnalysisMode.CUSTOM,
        start_date=datetime(2024, 1, 1).date(),
        end_date=datetime(2024, 1, 2).date(),
    )

    class DummyResult:
        analysis_duration_seconds = 0.5
        total_conversations_analyzed = 10
        analysis_content = "Body"

        def dict(self):
            return {}

    analyzer = AsyncMock()
    analyzer.analyze.return_value = DummyResult()
    gamma_mock = AsyncMock()

    monkeypatch.setattr(export_commands, "IntercomSDKService", lambda: object())
    monkeypatch.setattr(export_commands, "MetricsCalculator", lambda: object())
    monkeypatch.setattr(export_commands, "OpenAIClient", lambda: object())
    monkeypatch.setattr(export_commands, "TrendAnalyzer", lambda *args: analyzer)
    monkeypatch.setattr(export_commands, "save_markdown_output", MagicMock())
    monkeypatch.setattr(export_commands, "generate_gamma_presentation", gamma_mock)

    await export_commands.run_custom_analysis(
        request=request,
        generate_gamma=True,
        output_format="markdown",
    )

    gamma_mock.assert_awaited()

