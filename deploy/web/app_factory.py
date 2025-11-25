"""FastAPI application factory for the consolidated Railway web server."""

from __future__ import annotations

import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

try:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler

    HAS_APSCHEDULER = True
except ImportError:
    HAS_APSCHEDULER = False

try:
    from src.chat.chat_interface import ChatInterface
    from src.config.settings import Settings
    HAS_CHAT_DEPS = True
except ImportError as exc:  # pragma: no cover - optional dependency
    HAS_CHAT_DEPS = False
    ChatInterface = None  # type: ignore
    Settings = None  # type: ignore
    logging.getLogger(__name__).warning(
        "Chat dependencies unavailable (%s). Chat features will be disabled.", exc
    )

from src.services.duckdb_storage import DuckDBStorage
from src.services.historical_snapshot_service import HistoricalSnapshotService
from src.services.execution_state_manager import ExecutionStateManager
from src.services.web_command_executor import WebCommandExecutor

from deploy.web import routes_chat, routes_execution, routes_files, routes_timeline
from deploy.web.routes_execution import get_primary_outputs_path
from deploy.web.templates import render_chat_html, render_files_html

logger = logging.getLogger(__name__)

APP_VERSION = os.getenv("APP_VERSION", "dev")
GIT_COMMIT = os.getenv("GIT_COMMIT", "unknown")
BUILD_DATE = os.getenv("BUILD_DATE", datetime.utcnow().isoformat())
APP_START_TIME = datetime.utcnow()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Intercom Analysis Tool - Web Interface",
        description="Web server providing chat, execution, files, and historical timeline interfaces.",
        version=APP_VERSION,
    )

    _configure_middleware(app)
    _mount_static(app)
    _include_routers(app)
    _register_routes(app)
    _register_lifecycle_events(app)

    return app


def _configure_middleware(app: FastAPI) -> None:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


def _mount_static(app: FastAPI) -> None:
    project_root = Path(__file__).resolve().parents[2]
    static_path = project_root / "static"
    static_path.mkdir(parents=True, exist_ok=True)
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")


def _include_routers(app: FastAPI) -> None:
    app.include_router(routes_timeline.timeline_router)
    app.include_router(routes_execution.execution_router)
    app.include_router(routes_chat.chat_router)
    app.include_router(routes_files.files_router)


def _register_routes(app: FastAPI) -> None:
    git_short = GIT_COMMIT[:8] if GIT_COMMIT != "unknown" else "unknown"
    cache_bust = f"{APP_VERSION}-{git_short}"

    @app.get("/", response_class=HTMLResponse)
    async def chat_ui():
        return HTMLResponse(
            render_chat_html(app_version=APP_VERSION, git_commit=GIT_COMMIT),
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0",
            },
        )

    @app.get("/files", response_class=HTMLResponse)
    async def files_page():
        return HTMLResponse(
            render_files_html(cache_bust),
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0",
            },
        )

    @app.get("/health")
    async def health_check():
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "chat_interface": bool(getattr(app.state, "chat_interface", None)),
            "command_executor": bool(getattr(app.state, "command_executor", None)),
            "state_manager": bool(getattr(app.state, "state_manager", None)),
            "duckdb_storage": bool(getattr(app.state, "duckdb_storage", None)),
            "historical_service": bool(getattr(app.state, "historical_service", None)),
            "version": APP_VERSION,
        }

    @app.get("/debug/version")
    async def get_version():
        uptime_seconds = (datetime.utcnow() - APP_START_TIME).total_seconds()
        return {
            "version": APP_VERSION,
            "commit": GIT_COMMIT,
            "commit_short": git_short,
            "build_date": BUILD_DATE,
            "uptime_seconds": uptime_seconds,
            "python_version": sys.version,
            "environment": os.getenv("RAILWAY_ENVIRONMENT", "local"),
            "deployment_id": os.getenv("RAILWAY_DEPLOYMENT_ID", "unknown"),
            "timestamp": datetime.utcnow().isoformat(),
        }

    @app.post("/api/notify-completion")
    async def notify_completion(request: Request):
        """Send completion notifications via Slack (optional)."""
        payload = await _parse_notify_payload(request)
        slack_webhook_url = os.getenv("SLACK_WEBHOOK_URL")
        if not slack_webhook_url:
            return {"message": "Slack webhook not configured (optional)", "notified": False}

        execution_id = payload.get("execution_id", "unknown")
        status = payload.get("status", "completed")
        duration_seconds = payload.get("duration_seconds", 0) or 0
        minutes = duration_seconds // 60
        seconds = duration_seconds % 60
        time_str = f"{minutes}m {seconds}s"
        base_url = os.getenv(
            "RAILWAY_PUBLIC_DOMAIN",
            os.getenv("PUBLIC_WEB_URL", "https://railway.app"),
        )

        if status == "completed":
            text = (
                f"✅ *Analysis Completed!*\n\nExecution ID: `{execution_id}`\nDuration: {time_str}\n\n<{base_url}|View Results>"
            )
            color = "#10b981"
        else:
            text = (
                f"❌ *Analysis {status.title()}*\n\nExecution ID: `{execution_id}`\nDuration: {time_str}\n\n<{base_url}|View Logs>"
            )
            color = "#ef4444"

        try:
            import httpx

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    slack_webhook_url,
                    json={
                        "text": text,
                        "attachments": [
                            {
                                "color": color,
                                "fields": [
                                    {"title": "Status", "value": status.title(), "short": True},
                                    {"title": "Duration", "value": time_str, "short": True},
                                ],
                            }
                        ],
                    },
                )
            if response.status_code == 200:
                logger.info("Slack notification sent for execution %s", execution_id)
                return {"message": "Slack notification sent", "notified": True}
            logger.warning("Slack notification failed: %s", response.status_code)
            return {"message": "Slack notification failed", "notified": False}
        except Exception as exc:  # pragma: no cover
            logger.error("Failed to send Slack notification: %s", exc)
            return {"message": f"Slack notification error: {exc}", "notified": False}


def _register_lifecycle_events(app: FastAPI) -> None:
    @app.on_event("startup")
    async def startup_event():
        logger.info("🚀 Starting Intercom Analysis Web Server v%s", APP_VERSION)
        _ensure_outputs_dirs()
        _initialize_execution_services(app)
        _initialize_duckdb_services(app)
        if HAS_CHAT_DEPS:
            _initialize_chat_interface(app)
        else:
            app.state.chat_interface = None
        if HAS_APSCHEDULER:
            app.state.cleanup_scheduler = _start_cleanup_scheduler(app)
        else:
            app.state.cleanup_scheduler = None

    @app.on_event("shutdown")
    async def shutdown_event():
        scheduler: Optional[AsyncIOScheduler] = getattr(app.state, "cleanup_scheduler", None)
        if scheduler:
            scheduler.shutdown(wait=False)


def _ensure_outputs_dirs() -> None:
    get_primary_outputs_path()


def _initialize_execution_services(app: FastAPI) -> None:
    if getattr(app.state, "command_executor", None) and getattr(app.state, "state_manager", None):
        return

    outputs_base_path = get_primary_outputs_path()
    app.state.command_executor = WebCommandExecutor()
    app.state.state_manager = ExecutionStateManager(
        max_concurrent=int(os.getenv("MAX_CONCURRENT_EXECUTIONS", "5")),
        max_queue_size=int(os.getenv("MAX_EXECUTION_QUEUE", "20")),
        persistence_dir=str(outputs_base_path / "jobs"),
        outputs_base_path=str(outputs_base_path),
    )


def _initialize_duckdb_services(app: FastAPI) -> None:
    """
    Initialize DuckDB storage and historical snapshot services.
    
    This function attempts to initialize DuckDB for historical data storage.
    If initialization fails, the services are set to None and timeline/history
    features will return HTTP 503 errors to distinguish from transient 500s.
    
    Configuration:
    - DUCKDB_DATABASE_PATH: Custom path for the DuckDB database file
    - RAILWAY_VOLUME_MOUNT_PATH: Railway persistent storage path (auto-detected)
    
    Production Considerations:
    - Ensure the database path is writable
    - For Railway deployments, use a persistent volume
    - DuckDB files are locked during writes; avoid concurrent writer processes
    """
    db_path = os.getenv("DUCKDB_DATABASE_PATH")
    volume_path = os.getenv("RAILWAY_VOLUME_MOUNT_PATH")
    
    # Log configuration for debugging
    logger.info(
        "📊 Initializing DuckDB services | Configured DB path: %s | Volume mount: %s",
        db_path or "(default)",
        volume_path or "(not set)",
    )
    
    try:
        storage = DuckDBStorage()
        historical_service = HistoricalSnapshotService(storage)
        app.state.duckdb_storage = storage
        app.state.historical_service = historical_service
        
        # Log the actual path used for verification
        actual_path = getattr(storage, 'db_path', None) or getattr(storage, 'database_path', None)
        logger.info(
            "✅ Historical snapshot services initialized | Actual DB path: %s",
            actual_path or "(in-memory or default)",
        )
    except PermissionError as exc:  # pragma: no cover
        app.state.duckdb_storage = None
        app.state.historical_service = None
        logger.error(
            "❌ DuckDB initialization failed due to PERMISSION ERROR: %s | "
            "Ensure the database path is writable. Historical features will be UNAVAILABLE. "
            "Configure DUCKDB_DATABASE_PATH or check volume permissions.",
            exc,
            exc_info=True,
        )
    except FileNotFoundError as exc:  # pragma: no cover
        app.state.duckdb_storage = None
        app.state.historical_service = None
        logger.error(
            "❌ DuckDB initialization failed due to MISSING DIRECTORY: %s | "
            "Ensure the parent directory exists. Historical features will be UNAVAILABLE.",
            exc,
            exc_info=True,
        )
    except Exception as exc:  # pragma: no cover
        app.state.duckdb_storage = None
        app.state.historical_service = None
        logger.error(
            "❌ DuckDB initialization failed: %s (%s) | "
            "Historical features (timeline, snapshots) will be UNAVAILABLE. "
            "This may indicate misconfiguration or a transient issue. "
            "Check DUCKDB_DATABASE_PATH and volume permissions.",
            type(exc).__name__,
            exc,
            exc_info=True,
        )


def _initialize_chat_interface(app: FastAPI) -> None:
    required_vars = ["INTERCOM_ACCESS_TOKEN", "OPENAI_API_KEY"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        logger.warning(
            "⚠️ Missing required environment variables for chat interface: %s",
            missing_vars,
        )
        app.state.chat_interface = None
        return

    try:
        settings = Settings() if Settings else None
        chat_interface = ChatInterface(settings) if ChatInterface and settings else None
        app.state.chat_interface = chat_interface
        logger.info("✅ Chat interface initialized successfully")
    except Exception as exc:  # pragma: no cover
        app.state.chat_interface = None
        logger.error("❌ Failed to initialize chat interface: %s", exc, exc_info=True)


def _start_cleanup_scheduler(app: FastAPI) -> Optional[AsyncIOScheduler]:
    state_manager: Optional[ExecutionStateManager] = getattr(app.state, "state_manager", None)
    if not HAS_APSCHEDULER or not state_manager:
        return None

    retention_days = int(os.getenv("AUDIT_RETENTION_DAYS", "14"))
    max_count = int(os.getenv("AUDIT_MAX_COUNT", "50"))
    scheduler = AsyncIOScheduler()

    async def cleanup_task():
        try:
            logger.info("🧹 Running scheduled cleanup...")
            result = await state_manager.cleanup_old_executions(
                max_age_days=retention_days,
                max_count=max_count,
                cleanup_files=True,
            )
            logger.info(
                "✅ Scheduled cleanup complete: deleted %(deleted_executions)s executions, "
                "%(deleted_files)s files. %(remaining_executions)s executions remaining.",
                result,
            )
        except Exception as exc:  # pragma: no cover
            logger.error("❌ Scheduled cleanup failed: %s", exc, exc_info=True)

    scheduler.add_job(
        cleanup_task,
        trigger="cron",
        hour=2,
        minute=0,
        id="daily_cleanup",
        replace_existing=True,
    )
    scheduler.start()
    logger.info(
        "🧹 Cleanup scheduler configured: %s days retention, max %s executions",
        retention_days,
        max_count,
    )
    return scheduler


async def _parse_notify_payload(request: Request) -> Dict[str, Optional[str]]:
    try:
        body = await request.json()
        return {
            "execution_id": body.get("execution_id"),
            "status": body.get("status"),
            "duration_seconds": body.get("duration_seconds"),
        }
    except Exception:
        return {
            "execution_id": request.query_params.get("execution_id"),
            "status": request.query_params.get("status"),
            "duration_seconds": request.query_params.get("duration_seconds"),
        }

