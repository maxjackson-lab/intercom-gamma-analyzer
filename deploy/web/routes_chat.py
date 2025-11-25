"""Natural language chat routes for the Railway web server."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from deploy.web.routes_execution import RateLimiter
from src.cli.schema import CANONICAL_COMMAND_MAPPINGS

try:
    from src.chat.chat_interface import ChatInterface  # type: ignore
    HAS_CHAT_DEPS = True
except ImportError:  # pragma: no cover - optional dependency
    ChatInterface = None  # type: ignore
    HAS_CHAT_DEPS = False

logger = logging.getLogger(__name__)

chat_router = APIRouter()
_chat_rate_limiter = RateLimiter(max_requests=60, window_seconds=60)


class ChatRequest(BaseModel):
    query: str
    context: Dict[str, Any] = {}


class ChatResponse(BaseModel):
    success: bool
    message: str
    data: Dict[str, Any] = {}


async def _check_chat_rate_limit(request: Request) -> None:
    client_ip = request.client.host if request.client else "unknown"
    if not _chat_rate_limiter.is_allowed(client_ip):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded: 60 chat requests per minute per IP",
        )


def _require_chat_interface(request: Request) -> Optional[Any]:
    chat_interface = getattr(request.app.state, "chat_interface", None)
    return chat_interface


@chat_router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(payload: ChatRequest, request: Request) -> ChatResponse:
    """Process chat queries via ChatInterface."""
    await _check_chat_rate_limit(request)
    chat_interface = _require_chat_interface(request)
    if not chat_interface:
        return ChatResponse(
            success=False,
            message="Chat interface not available. This is likely due to missing dependencies that are too large for Railway deployment.",
            data={"error_type": "dependencies_missing"},
        )

    try:
        result = chat_interface.process_query(payload.query, payload.context)
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.error("Chat processing error: %s", exc, exc_info=True)
        return ChatResponse(success=False, message=f"Internal error: {exc}", data={})

    if result.get("success"):
        return ChatResponse(success=True, message="Query processed successfully", data=result)

    return ChatResponse(
        success=False,
        message=result.get("error", "Unknown error"),
        data=result,
    )


@chat_router.get("/api/commands")
async def get_commands():
    """Expose canonical command mappings for the UI."""
    return JSONResponse(
        content={
            "version": "1.0",
            "commands": CANONICAL_COMMAND_MAPPINGS,
            "generated_at": datetime.now().isoformat(),
        },
        headers={
            "Cache-Control": "public, max-age=300",
            "Content-Type": "application/json",
        },
    )


@chat_router.get("/api/filters")
async def get_filters(request: Request):
    """Return supported chat filters."""
    await _check_chat_rate_limit(request)
    chat_interface = _require_chat_interface(request)
    if not chat_interface:
        raise HTTPException(status_code=500, detail="Chat interface not initialized")
    try:
        filters = chat_interface.get_supported_filters()
    except Exception as exc:  # pragma: no cover
        logger.error("Failed to fetch filters: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"filters": filters}


@chat_router.get("/api/stats")
async def get_stats(request: Request):
    """Return chat performance statistics."""
    await _check_chat_rate_limit(request)
    chat_interface = _require_chat_interface(request)
    if not chat_interface:
        raise HTTPException(status_code=500, detail="Chat interface not initialized")
    try:
        stats = chat_interface.get_performance_stats()
    except Exception as exc:  # pragma: no cover
        logger.error("Failed to fetch stats: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"stats": stats}

