"""
Tests for category CLI commands.
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.cli import category_commands


@pytest.fixture
def capture_console(monkeypatch):
    outputs = []

    def fake_print(*args, **kwargs):
        outputs.append(" ".join(str(arg) for arg in args))

    monkeypatch.setattr(category_commands.console, "print", fake_print)
    return outputs


@pytest.mark.asyncio
async def test_run_category_deep_dive_filters(monkeypatch):
    conversations = [{"id": 1}, {"id": 2}, {"id": 3}]
    filtered = [{"id": 1}, {"id": 2}]

    monkeypatch.setattr(
        category_commands,
        "fetch_conversations_for_range",
        AsyncMock(return_value=conversations),
    )

    class DummyFilters:
        category_patterns = {"Billing": ["refund"]}

        def filter_by_category(self, convs, category, include_subcategories=True):
            return filtered

    monkeypatch.setattr(category_commands, "CategoryFilters", lambda: DummyFilters())
    run_analysis = AsyncMock(return_value={"ok": True})
    monkeypatch.setattr(category_commands, "run_voc_narrative_analysis", run_analysis)

    result = await category_commands._run_category_deep_dive(
        category_name="Billing",
        start_date=datetime(2024, 1, 1),
        end_date=datetime(2024, 1, 2),
        generate_gamma=False,
        audit_trail=False,
        max_conversations=None,
        output_slug="slug",
        analysis_mode="mode",
    )

    assert result == {"ok": True}
    run_analysis.assert_awaited_once()


@pytest.mark.asyncio
async def test_run_category_deep_dive_no_matches(monkeypatch, capture_console):
    monkeypatch.setattr(
        category_commands,
        "fetch_conversations_for_range",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(
        category_commands,
        "CategoryFilters",
        lambda: MagicMock(category_patterns={"Billing": []}, filter_by_category=lambda *args, **kwargs: []),
    )

    result = await category_commands._run_category_deep_dive(
        category_name="Billing",
        start_date=datetime(2024, 1, 1),
        end_date=datetime(2024, 1, 2),
        generate_gamma=False,
        audit_trail=False,
        max_conversations=None,
        output_slug="slug",
        analysis_mode="mode",
    )

    assert result == {}
    assert any("No conversations found" in line for line in capture_console)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "func,expected_mode",
    [
        (category_commands.run_billing_analysis, "category_billing"),
        (category_commands.run_product_analysis, "category_product"),
        (category_commands.run_sites_analysis, "category_sites"),
        (category_commands.run_api_analysis, "category_api"),
    ],
)
async def test_category_wrappers(monkeypatch, func, expected_mode):
    runner = AsyncMock()
    monkeypatch.setattr(category_commands, "_run_category_deep_dive", runner)

    await func(
        start_date=datetime(2024, 1, 1),
        end_date=datetime(2024, 1, 2),
        generate_gamma=False,
        max_conversations=None,
    )

    call = runner.await_args
    assert call.kwargs["analysis_mode"] == expected_mode


@pytest.mark.asyncio
async def test_run_all_categories_analysis_v2_success(monkeypatch, tmp_path, capture_console):
    class DummyFetcher:
        async def fetch_conversations_chunked(self, *args, **kwargs):
            return [{"id": 1}, {"id": 2}]

    class DummyPreprocessor:
        def preprocess_conversations(self, conversations, options):
            return conversations, {"stats": True}

    class DummyAnalyzer:
        async def analyze_category(self, *args, **kwargs):
            return {"data_summary": {"filtered_conversations": 2}}

    monkeypatch.setattr(category_commands, "ChunkedFetcher", lambda: DummyFetcher())
    monkeypatch.setattr(category_commands, "DataPreprocessor", lambda: DummyPreprocessor())
    monkeypatch.setattr(category_commands, "BillingAnalyzer", DummyAnalyzer)
    monkeypatch.setattr(category_commands, "ProductAnalyzer", DummyAnalyzer)
    monkeypatch.setattr(category_commands, "SitesAnalyzer", DummyAnalyzer)
    monkeypatch.setattr(category_commands, "ApiAnalyzer", DummyAnalyzer)
    monkeypatch.setattr(
        category_commands,
        "get_output_directory",
        lambda: tmp_path,
    )
    gamma_generator = AsyncMock()
    gamma_generator.generate_multi_category_presentation.return_value = {"url": "https://gamma"}
    monkeypatch.setattr(category_commands, "GammaGenerator", lambda: gamma_generator)

    await category_commands.run_all_categories_analysis_v2(
        start_date=datetime(2024, 1, 1),
        end_date=datetime(2024, 1, 2),
        generate_gamma=True,
        parallel=False,
        max_conversations=100,
    )

    assert any("All Categories Analysis Completed" in line for line in capture_console)
    gamma_generator.generate_multi_category_presentation.assert_awaited()


@pytest.mark.asyncio
async def test_run_all_categories_analysis_v2_no_conversations(monkeypatch, capture_console):
    class EmptyFetcher:
        async def fetch_conversations_chunked(self, *args, **kwargs):
            return []

    monkeypatch.setattr(category_commands, "ChunkedFetcher", lambda: EmptyFetcher())
    monkeypatch.setattr(category_commands, "DataPreprocessor", lambda: MagicMock())
    monkeypatch.setattr(category_commands, "GammaGenerator", lambda: MagicMock())

    await category_commands.run_all_categories_analysis_v2(
        start_date=datetime(2024, 1, 1),
        end_date=datetime(2024, 1, 2),
        generate_gamma=False,
        parallel=False,
        max_conversations=None,
    )

    assert any("No conversations found" in line for line in capture_console)

