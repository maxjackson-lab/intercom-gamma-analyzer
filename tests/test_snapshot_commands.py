"""
Tests for snapshot CLI commands.
"""

import json
from pathlib import Path
from typing import Dict, List

import pytest

from src.cli import snapshot_commands


@pytest.fixture
def capture_console(monkeypatch):
    """Capture console output from the snapshot commands module."""
    outputs = []

    def fake_print(*args, **kwargs):
        outputs.append(" ".join(str(arg) for arg in args))

    monkeypatch.setattr(snapshot_commands.console, "print", fake_print)
    return outputs


class DummyStorage:
    """Simple in-memory snapshot storage for testing."""

    def __init__(self, snapshots: Dict[str, Dict]):
        self._snapshots = snapshots

    def get_analysis_snapshot(self, snapshot_id: str):
        return self._snapshots.get(snapshot_id)


def configure_service(monkeypatch, snapshots: List[Dict], context: Dict, comparison: Dict = None):
    """Patch HistoricalSnapshotService with deterministic behaviour."""

    class DummyService:
        def __init__(self, storage):
            self.storage = storage

        def list_snapshots(self, analysis_type, limit):
            return snapshots[:limit]

        def get_historical_context(self):
            return context

        def calculate_comparison(self, current, prior):
            return comparison or {}

    monkeypatch.setattr(snapshot_commands, "HistoricalSnapshotService", DummyService)


@pytest.mark.asyncio
async def test_list_snapshots_success(monkeypatch, capture_console):
    snapshots = [
        {
            "snapshot_id": "weekly_1",
            "analysis_type": "weekly",
            "date_range_label": "Week 1",
            "total_conversations": 100,
            "reviewed": True,
            "reviewed_by": "alex",
        }
    ]
    context = {
        "weeks_available": 6,
        "has_baseline": True,
        "can_do_trends": True,
        "can_do_seasonality": False,
    }

    configure_service(monkeypatch, snapshots, context)
    monkeypatch.setattr(snapshot_commands, "DuckDBStorage", lambda: DummyStorage({}))

    result = await snapshot_commands.list_snapshots(
        analysis_type=None, limit=10, show_reviewed=True, show_unreviewed=True
    )

    assert result["total_count"] == 1
    assert any("weekly_1" in line for line in capture_console)


@pytest.mark.asyncio
async def test_list_snapshots_empty(monkeypatch, capture_console):
    configure_service(
        monkeypatch,
        snapshots=[],
        context={
            "weeks_available": 0,
            "has_baseline": False,
            "can_do_trends": False,
            "can_do_seasonality": False,
        },
    )
    monkeypatch.setattr(snapshot_commands, "DuckDBStorage", lambda: DummyStorage({}))

    result = await snapshot_commands.list_snapshots(
        analysis_type=None, limit=5, show_reviewed=False, show_unreviewed=False
    )

    assert result["total_count"] == 0
    assert any("No snapshots found" in line for line in capture_console)


@pytest.mark.asyncio
async def test_export_snapshot_schema(monkeypatch, tmp_path, capture_console):
    snapshot_schema = {"fields": ["a"]}
    comparison_schema = {"fields": ["b"]}

    monkeypatch.setattr(
        snapshot_commands.HistoricalSnapshotService,
        "get_snapshot_json_schema",
        classmethod(lambda cls, mode="validation": snapshot_schema),
    )
    monkeypatch.setattr(
        snapshot_commands.HistoricalSnapshotService,
        "get_comparison_json_schema",
        classmethod(lambda cls: comparison_schema),
    )

    output_file = tmp_path / "schema.json"
    result = await snapshot_commands.export_snapshot_schema(str(output_file), schema_type="all")

    assert json.loads(output_file.read_text())["SnapshotData"] == snapshot_schema
    assert result["schema"]["ComparisonData"] == comparison_schema
    assert any("Schema exported" in line for line in capture_console)


@pytest.mark.asyncio
async def test_compare_snapshots_success(monkeypatch, capture_console):
    snapshots = {
        "cur": {"snapshot_id": "cur", "total_conversations": 120, "topic_volumes": {"Billing": 10}},
        "prev": {"snapshot_id": "prev", "total_conversations": 100, "topic_volumes": {"Billing": 5}},
    }
    comparison = {
        "volume_changes": {
            "Billing": {"current": 10, "prior": 5, "change": 5, "pct": 0.5},
        },
        "significant_changes": [{"topic": "Billing", "change": 5, "pct": 0.5, "direction": "up"}],
    }
    configure_service(monkeypatch, snapshots=[], context={}, comparison=comparison)
    monkeypatch.setattr(snapshot_commands, "DuckDBStorage", lambda: DummyStorage(snapshots))

    result = await snapshot_commands.compare_snapshots("cur", "prev", show_details=False)

    assert "comparison" in result
    assert any("Week-over-Week" in line for line in capture_console)


@pytest.mark.asyncio
async def test_compare_snapshots_missing_current(monkeypatch, capture_console):
    configure_service(monkeypatch, snapshots=[], context={}, comparison={})
    monkeypatch.setattr(snapshot_commands, "DuckDBStorage", lambda: DummyStorage({"prev": {}}))

    result = await snapshot_commands.compare_snapshots("missing", "prev", show_details=False)

    assert "error" in result
    assert "missing" in result["error"]
    assert any("not found" in line for line in capture_console)


@pytest.mark.asyncio
async def test_compare_snapshots_missing_prior(monkeypatch, capture_console):
    configure_service(monkeypatch, snapshots=[], context={}, comparison={})
    monkeypatch.setattr(snapshot_commands, "DuckDBStorage", lambda: DummyStorage({"cur": {}}))

    result = await snapshot_commands.compare_snapshots("cur", "missing", show_details=True)

    assert "error" in result
    assert "missing" in result["error"]


@pytest.mark.asyncio
async def test_compare_snapshots_with_details(monkeypatch, capture_console):
    snapshots = {
        "cur": {"snapshot_id": "cur", "total_conversations": 120, "topic_volumes": {"Billing": 12}},
        "prev": {"snapshot_id": "prev", "total_conversations": 100, "topic_volumes": {"Billing": 8}},
    }
    comparison = {
        "volume_changes": {"Billing": {"current": 12, "prior": 8, "change": 4, "pct": 0.5}},
        "significant_changes": [{"topic": "Billing", "change": 4}],
    }
    configure_service(monkeypatch, snapshots=[], context={}, comparison=comparison)
    monkeypatch.setattr(snapshot_commands, "DuckDBStorage", lambda: DummyStorage(snapshots))

    result = await snapshot_commands.compare_snapshots("cur", "prev", show_details=True)

    assert "comparison" in result
    assert result["comparison"]["volume_changes"]["Billing"]["change"] == 4
    assert any("Billing" in line for line in capture_console)
