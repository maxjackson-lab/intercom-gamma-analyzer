"""
Tests for FastAPI timeline & snapshot routes.
"""

from datetime import datetime, timedelta


def _add_snapshot(storage, snapshot_id="snap-1"):
    storage.snapshots[snapshot_id] = {
        "snapshot_id": snapshot_id,
        "analysis_type": "weekly",
        "period_start": datetime.utcnow() - timedelta(days=7),
        "period_end": datetime.utcnow(),
        "created_at": datetime.utcnow(),
        "reviewed": False,
        "topic_volumes": {"Billing": 10},
    }
    return storage.snapshots[snapshot_id]


def test_timeline_history_page(web_app):
    client = web_app["client"]
    response = client.get("/history")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_snapshot_list_success(web_app):
    client = web_app["client"]
    history = web_app["historical_service"]
    now = datetime.utcnow()
    history.snapshots = [
        {
            "snapshot_id": "weekly_1",
            "analysis_type": "weekly",
            "period_start": now - timedelta(days=7),
            "period_end": now,
            "created_at": now,
            "topic_volumes": {"Billing": 12},
        }
    ]
    history.context = {
        "baseline_date": now - timedelta(days=30),
        "earliest_snapshot": now - timedelta(days=60),
        "latest_snapshot": now,
    }

    response = client.get("/api/snapshots/list", params={"analysis_type": "weekly", "limit": 5})
    data = response.json()
    assert response.status_code == 200
    assert len(data["snapshots"]) == 1
    assert data["snapshots"][0]["snapshot_id"] == "weekly_1"
    assert "context" in data


def test_snapshot_detail_success_and_review(web_app):
    client = web_app["client"]
    storage = web_app["storage"]
    snapshot = _add_snapshot(storage, "snap-detail")

    detail = client.get("/api/snapshots/snap-detail")
    assert detail.status_code == 200
    assert detail.json()["snapshot_id"] == "snap-detail"

    review = client.post(
        "/api/snapshots/snap-detail/review",
        json={"reviewed_by": "qa@example.com", "notes": "Looks good"},
    )
    assert review.status_code == 200
    assert "marked as reviewed" in review.json()["message"]
    assert storage.snapshots["snap-detail"]["reviewed"] is True


def test_snapshot_detail_not_found(web_app):
    client = web_app["client"]
    response = client.get("/api/snapshots/unknown")
    assert response.status_code == 404


def test_timeseries_endpoint_returns_chart_payload(web_app):
    client = web_app["client"]
    history = web_app["historical_service"]
    now = datetime.utcnow()
    history.snapshots = [
        {
            "snapshot_id": "snap-timeseries",
            "analysis_type": "weekly",
            "period_start": now - timedelta(days=7),
            "period_end": now,
            "topic_volumes": {"Billing": 20, "API": 5},
        }
    ]

    response = client.get("/api/snapshots/timeseries", params={"analysis_type": "weekly", "limit": 3})
    data = response.json()
    assert response.status_code == 200
    assert "labels" in data
    assert "datasets" in data
    assert data["datasets"]


def test_compare_snapshots_view(web_app):
    client = web_app["client"]
    storage = web_app["storage"]
    history = web_app["historical_service"]
    current = _add_snapshot(storage, "current")
    prior = _add_snapshot(storage, "prior")
    history.comparison = {"volume_changes": {"Billing": {"change": 5}}}

    response = client.get("/analysis/compare/current/prior")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_snapshot_routes_return_503_when_service_missing(web_app):
    client = web_app["client"]
    client.app.state.historical_service = None
    response = client.get("/api/snapshots/list")
    assert response.status_code == 503

