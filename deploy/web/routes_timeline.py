"""Timeline-related routes for the consolidated Railway web application."""

from __future__ import annotations

import os
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from deploy.web.templates import (
    render_snapshot_comparison_html,
    render_snapshot_detail_html,
    render_timeline_html,
)
from src.services.duckdb_storage import DuckDBStorage
from src.services.historical_snapshot_service import HistoricalSnapshotService


timeline_router = APIRouter()
security = HTTPBearer(auto_error=False)


class ReviewRequest(BaseModel):
    reviewed_by: str
    notes: Optional[str] = None


async def verify_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    """Verify bearer token for protected operations."""
    expected_token = os.getenv("EXECUTION_API_TOKEN")
    if not expected_token:
        return "development"

    if not credentials:
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Please provide a valid bearer token.",
        )

    if credentials.credentials != expected_token:
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication credentials",
        )

    return credentials.credentials


class ServiceUnavailableError(HTTPException):
    """
    Custom exception for unavailable backend services.
    
    Returns HTTP 503 (Service Unavailable) with a consistent JSON structure
    that includes machine-readable error codes for client handling.
    """
    
    def __init__(self, service_name: str, error_code: str, suggestion: str):
        detail = {
            "error": "service_unavailable",
            "error_code": error_code,
            "service": service_name,
            "message": f"{service_name} is not available",
            "suggestion": suggestion,
            "recoverable": True,
        }
        super().__init__(status_code=503, detail=detail)


def _get_historical_service(request: Request) -> HistoricalSnapshotService:
    """
    Retrieve the historical snapshot service from app state.
    
    Raises:
        ServiceUnavailableError: If the service was not initialized (503)
            with machine-readable error_code 'HISTORICAL_SERVICE_UNAVAILABLE'
    """
    service = getattr(request.app.state, "historical_service", None)
    if not service:
        raise ServiceUnavailableError(
            service_name="Historical snapshot service",
            error_code="HISTORICAL_SERVICE_UNAVAILABLE",
            suggestion="Check server logs for DuckDB initialization errors. "
                       "Verify DUCKDB_DATABASE_PATH and volume permissions.",
        )
    return service


def _get_duckdb_storage(request: Request) -> DuckDBStorage:
    """
    Retrieve the DuckDB storage backend from app state.
    
    Raises:
        ServiceUnavailableError: If storage was not initialized (503)
            with machine-readable error_code 'DUCKDB_STORAGE_UNAVAILABLE'
    """
    storage = getattr(request.app.state, "duckdb_storage", None)
    if not storage:
        raise ServiceUnavailableError(
            service_name="DuckDB storage",
            error_code="DUCKDB_STORAGE_UNAVAILABLE",
            suggestion="Check server logs for DuckDB initialization errors. "
                       "This may be due to missing volume mounts or permission issues.",
        )
    return storage


def _isoformat(value: Optional[datetime | date]) -> Optional[str]:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value  # type: ignore[return-value]


@timeline_router.get("/history", response_class=HTMLResponse)
async def timeline_home() -> HTMLResponse:
    """Serve the historical timeline landing page."""
    return HTMLResponse(render_timeline_html())


@timeline_router.get("/analysis/history", response_class=HTMLResponse)
async def analysis_history() -> HTMLResponse:
    """Alias for the timeline landing page."""
    return await timeline_home()


@timeline_router.get("/api/snapshots/list")
async def list_snapshots(
    request: Request,
    analysis_type: Optional[str] = None,
    limit: int = 20,
):
    """List snapshots with optional filtering."""
    historical_service = _get_historical_service(request)

    try:
        snapshots = await historical_service.list_snapshots_async(analysis_type, limit)
        context = await historical_service.get_historical_context_async()

        # Normalize context timestamps
        for key in ("baseline_date", "earliest_snapshot", "latest_snapshot"):
            if key in context:
                context[key] = _isoformat(context.get(key))

        for snapshot in snapshots:
            for key in ("period_start", "period_end", "created_at", "reviewed_at"):
                if key in snapshot:
                    snapshot[key] = _isoformat(snapshot.get(key))

        return {"snapshots": snapshots, "context": context}
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - defensive logging
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch snapshots: {exc}",
        ) from exc


@timeline_router.get("/api/snapshots/{snapshot_id}")
async def get_snapshot(request: Request, snapshot_id: str):
    """Fetch a single snapshot by ID."""
    storage = _get_duckdb_storage(request)

    try:
        snapshot = storage.get_analysis_snapshot(snapshot_id)
        if not snapshot:
            raise HTTPException(status_code=404, detail=f"Snapshot {snapshot_id} not found")

        for key in ("period_start", "period_end", "created_at", "reviewed_at"):
            if key in snapshot:
                snapshot[key] = _isoformat(snapshot.get(key))

        return snapshot
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch snapshot: {exc}",
        ) from exc


@timeline_router.post("/api/snapshots/{snapshot_id}/review")
async def mark_snapshot_reviewed(
    request: Request,
    snapshot_id: str,
    review: ReviewRequest,
    token: str = Depends(verify_token),
):
    """Mark a snapshot as reviewed."""
    _ = token  # token already validated
    storage = _get_duckdb_storage(request)

    try:
        success = storage.mark_snapshot_reviewed(
            snapshot_id,
            review.reviewed_by,
            review.notes,
        )
        if not success:
            raise HTTPException(status_code=404, detail=f"Snapshot {snapshot_id} not found")

        return {
            "success": True,
            "message": f"Snapshot {snapshot_id} marked as reviewed by {review.reviewed_by}",
        }
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover
        raise HTTPException(
            status_code=500,
            detail=f"Failed to mark reviewed: {exc}",
        ) from exc


@timeline_router.get("/api/snapshots/timeseries")
async def get_timeseries(
    request: Request,
    analysis_type: str = "weekly",
    limit: int = 12,
):
    """Return Chart.js compatible data for timeline charts."""
    historical_service = _get_historical_service(request)

    try:
        snapshots = await historical_service.list_snapshots_async(analysis_type, limit)
        if not snapshots:
            return {"labels": [], "datasets": []}

        snapshots.sort(key=lambda snap: snap.get("period_end") or date.min)
        labels = [snap.get("date_range_label", "Unknown") for snap in snapshots]

        topic_volumes_by_name: dict[str, list[int]] = {}
        for snapshot in snapshots:
            topic_volumes = snapshot.get("topic_volumes", {}) or {}
            for topic_name, volume in topic_volumes.items():
                topic_volumes_by_name.setdefault(topic_name, []).append(volume)

        colors = [
            "#667eea",
            "#764ba2",
            "#f093fb",
            "#4facfe",
            "#43e97b",
            "#fa709a",
            "#fee140",
            "#30cfd0",
        ]
        datasets = []
        for index, (topic_name, values) in enumerate(topic_volumes_by_name.items()):
            padded = values + [0] * (len(labels) - len(values))
            color = colors[index % len(colors)]
            datasets.append(
                {
                    "label": topic_name,
                    "data": padded,
                    "borderColor": color,
                    "backgroundColor": f"{color}33",
                    "tension": 0.4,
                }
            )

        return {"labels": labels, "datasets": datasets}
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch timeseries: {exc}",
        ) from exc


@timeline_router.get("/analysis/view/{snapshot_id}", response_class=HTMLResponse)
async def view_snapshot(request: Request, snapshot_id: str) -> HTMLResponse:
    """Render the snapshot detail view."""
    storage = _get_duckdb_storage(request)

    try:
        snapshot = storage.get_analysis_snapshot(snapshot_id)
        if not snapshot:
            raise HTTPException(status_code=404, detail=f"Snapshot {snapshot_id} not found")
        return HTMLResponse(render_snapshot_detail_html(snapshot))
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load snapshot: {exc}",
        ) from exc


@timeline_router.get(
    "/analysis/compare/{current_id}/{prior_id}",
    response_class=HTMLResponse,
)
async def compare_snapshots(
    request: Request,
    current_id: str,
    prior_id: str,
) -> HTMLResponse:
    """Render snapshot comparison between two periods."""
    storage = _get_duckdb_storage(request)
    historical_service = _get_historical_service(request)

    try:
        current = storage.get_analysis_snapshot(current_id)
        prior = storage.get_analysis_snapshot(prior_id)
        if not current or not prior:
            raise HTTPException(status_code=404, detail="One or both snapshots not found")

        comparison = historical_service.calculate_comparison(current, prior)
        return HTMLResponse(
            render_snapshot_comparison_html(current, prior, comparison)
        )
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover
        raise HTTPException(
            status_code=500,
            detail=f"Failed to compare snapshots: {exc}",
        ) from exc

