"""Command execution and SSE streaming routes for the Railway web server."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
import re
from typing import Any, AsyncGenerator, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sse_starlette import EventSourceResponse

try:
    from src.utils.timezone_utils import get_pacific_time, datetime_to_pacific
except Exception:  # pragma: no cover - fallback used in limited environments
    def get_pacific_time() -> datetime:
        return datetime.now()

    def datetime_to_pacific(dt: datetime) -> datetime:
        return dt

from src.services.execution_state_manager import ExecutionStateManager, ExecutionStatus
from src.services.web_command_executor import WebCommandExecutor

logger = logging.getLogger(__name__)

execution_router = APIRouter()
security = HTTPBearer(auto_error=False)


class RateLimiter:
    """Simple in-memory rate limiter for per-IP requests."""

    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Dict[str, List[float]] = {}

    def is_allowed(self, client_ip: str) -> bool:
        now = time.time()
        cutoff = now - self.window_seconds
        history = self.requests.setdefault(client_ip, [])
        self.requests[client_ip] = [req for req in history if req > cutoff]
        if len(self.requests[client_ip]) >= self.max_requests:
            return False
        self.requests[client_ip].append(now)
        return True


rate_limiter = RateLimiter(max_requests=100, window_seconds=60)

MAX_REQUEST_SIZE = 10 * 1024 * 1024  # 10MB
MAX_EXECUTION_DURATION = int(os.getenv("MAX_EXECUTION_DURATION", 60 * 60))
SSE_KEEPALIVE_INTERVAL = int(os.getenv("SSE_KEEPALIVE_INTERVAL", 15))
MAX_SSE_DURATION = int(os.getenv("MAX_SSE_DURATION", os.getenv("MAX_EXECUTION_DURATION", 60 * 60)))
MAX_SSE_CHUNK_SIZE = 10 * 1024  # 10KB

logger.info(
    "SSE Configuration: keepalive_interval=%ss, max_duration=%ss",
    SSE_KEEPALIVE_INTERVAL,
    MAX_SSE_DURATION,
)
if SSE_KEEPALIVE_INTERVAL < 5 or SSE_KEEPALIVE_INTERVAL > 300:
    logger.warning(
        "SSE_KEEPALIVE_INTERVAL=%ss is outside recommended range (5-300s)",
        SSE_KEEPALIVE_INTERVAL,
    )
if MAX_SSE_DURATION < 60 or MAX_SSE_DURATION > 7200:
    logger.warning(
        "MAX_SSE_DURATION=%ss is outside recommended range (60-7200s)",
        MAX_SSE_DURATION,
    )

ALLOWED_COMMANDS = {
    "python",
    "python3",
    "voice-of-customer",
    "sample-mode",
    "billing-analysis",
    "product-analysis",
    "sites-analysis",
    "api-analysis",
    "canny-analysis",
    "trend-analysis",
}
MAX_ARG_LENGTH = 1024
MAX_ARGS_COUNT = 100
MAX_ARGS_TOTAL_LENGTH = 8192


def truncate_chunk(chunk: str, max_size: int = MAX_SSE_CHUNK_SIZE) -> str:
    """Ensure SSE chunks stay within the configured size limit."""
    if len(chunk) <= max_size:
        return chunk
    truncated = chunk[:max_size]
    last_newline = truncated.rfind("\n")
    if last_newline > max_size * 0.8:
        truncated = truncated[:last_newline]
    return truncated + "\n... [output truncated, see full logs]"


@lru_cache(maxsize=1)
def _primary_outputs_path() -> Path:
    volume_path = os.getenv("RAILWAY_VOLUME_MOUNT_PATH")
    base_path = Path(volume_path) / "outputs" if volume_path else Path("/app/outputs")
    base_path.mkdir(parents=True, exist_ok=True)
    return base_path


@lru_cache(maxsize=1)
def _all_output_paths() -> tuple[Path, ...]:
    paths: List[Path] = []
    volume_path = os.getenv("RAILWAY_VOLUME_MOUNT_PATH")
    if volume_path:
        volume_outputs = Path(volume_path) / "outputs"
        volume_outputs.mkdir(parents=True, exist_ok=True)
        paths.append(volume_outputs)
    container_outputs = Path("/app/outputs")
    container_outputs.mkdir(parents=True, exist_ok=True)
    if container_outputs not in paths:
        paths.append(container_outputs)
    return tuple(paths)


def _get_execution_base_path() -> Path:
    base = _primary_outputs_path() / "executions"
    base.mkdir(parents=True, exist_ok=True)
    return base


def _format_pacific_timestamp_from_epoch(epoch_seconds: float) -> str:
    utc_dt = datetime.fromtimestamp(epoch_seconds, tz=timezone.utc)
    pacific_dt = datetime_to_pacific(utc_dt)
    return pacific_dt.isoformat()


def get_output_paths() -> tuple[Path, ...]:
    """Expose all known output directories for other modules."""
    return _all_output_paths()


def format_timestamp_from_epoch(epoch_seconds: float) -> str:
    """Public helper for formatting timestamps in Pacific time."""
    return _format_pacific_timestamp_from_epoch(epoch_seconds)


def get_primary_outputs_path() -> Path:
    """Expose the primary outputs directory."""
    return _primary_outputs_path()


async def check_rate_limit(request: Request):
    client_ip = request.client.host if request.client else "unknown"
    if not rate_limiter.is_allowed(client_ip):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded: 100 requests per minute per IP",
        )


async def check_request_size(request: Request):
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > MAX_REQUEST_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"Request payload too large (max {MAX_REQUEST_SIZE / 1024 / 1024:.0f}MB)",
        )


async def verify_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    expected_token = os.getenv("EXECUTION_API_TOKEN")
    if not expected_token:
        return "development"
    if not credentials:
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Please provide a valid bearer token.",
        )
    if credentials.credentials != expected_token:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    return credentials.credentials


def _require_command_executor(request: Request) -> WebCommandExecutor:
    executor = getattr(request.app.state, "command_executor", None)
    if not executor:
        raise HTTPException(status_code=500, detail="Execution services not available")
    return executor


def _require_state_manager(request: Request) -> ExecutionStateManager:
    manager = getattr(request.app.state, "state_manager", None)
    if not manager:
        raise HTTPException(status_code=500, detail="Execution state manager not available")
    return manager


def generate_execution_directory_name(args_list: List[str], execution_id: str) -> str:
    """
    Generate a human-readable execution directory name.

    Format: {mode}_{date-description}_{time}
    """
    mode = "unknown"
    if len(args_list) > 1:
        mode = args_list[1].replace(".py", "").replace("src/main.py", "").strip()
        if not mode:
            mode = args_list[0] if args_list else "unknown"

    date_desc = "unknown-date"
    if "--time-period" in args_list:
        idx = args_list.index("--time-period")
        if idx + 1 < len(args_list):
            period = args_list[idx + 1]
            period_map = {
                "yesterday": "Yesterday",
                "week": "Last-Week",
                "month": "Last-Month",
                "quarter": "Last-Quarter",
                "year": "Last-Year",
                "6-weeks": "Last-6-Weeks",
            }
            date_desc = period_map.get(period, period)
    elif "--start-date" in args_list and "--end-date" in args_list:
        start_idx = args_list.index("--start-date")
        end_idx = args_list.index("--end-date")
        if start_idx + 1 < len(args_list) and end_idx + 1 < len(args_list):
            start_date = args_list[start_idx + 1]
            end_date = args_list[end_idx + 1]
            try:
                start_obj = datetime.fromisoformat(start_date)
                end_obj = datetime.fromisoformat(end_date)
                start_str = start_obj.strftime("%b-%d")
                end_str = end_obj.strftime("%b-%d")
                date_desc = f"{start_str}-to-{end_str}"
            except Exception:
                date_desc = f"{start_date}-to-{end_date}"
    elif "--days" in args_list:
        idx = args_list.index("--days")
        if idx + 1 < len(args_list):
            date_desc = f"Last-{args_list[idx + 1]}-Days"

    now = get_pacific_time()
    time_str = now.strftime("%b-%d-%I-%M%p").replace("-0", "-").lower()
    dir_name = f"{mode}_{date_desc}_{time_str}"
    dir_name = re.sub(r"[^\w\-]", "-", dir_name)
    dir_name = re.sub(r"-+", "-", dir_name)
    return dir_name[:200]


async def _discover_execution_files() -> List[Dict[str, Any]]:
    """Discover files associated with a specific execution."""
    files: List[Dict[str, Any]] = []
    seen_paths = set()

    for outputs_base in _all_output_paths():
        executions_base = outputs_base / "executions"
        if not executions_base.exists():
            continue

        for exec_dir in executions_base.iterdir():
            if not exec_dir.is_dir():
                continue

            for file_path in exec_dir.rglob("*"):
                if not file_path.is_file():
                    continue

                rel_path = file_path.relative_to(outputs_base)
                rel_path_str = str(rel_path)
                if rel_path_str in seen_paths:
                    continue

                seen_paths.add(rel_path_str)
                stat = file_path.stat()
                files.append(
                    {
                        "name": file_path.name,
                        "path": rel_path_str,
                        "size": stat.st_size,
                        "created_at": _format_pacific_timestamp_from_epoch(stat.st_mtime),
                        "directory": exec_dir.name,
                    }
                )

    if files:
        logger.info(
            "📂 Found %s files across %s execution directories",
            len(files),
            len({f["directory"] for f in files}),
        )
        return files

    for outputs_base in _all_output_paths():
        for file_path in outputs_base.glob("*"):
            if not file_path.is_file():
                continue
            rel_path = file_path.relative_to(outputs_base)
            rel_path_str = str(rel_path)
            if rel_path_str in seen_paths:
                continue
            seen_paths.add(rel_path_str)
            stat = file_path.stat()
            files.append(
                {
                    "name": file_path.name,
                    "path": rel_path_str,
                    "size": stat.st_size,
                    "created_at": _format_pacific_timestamp_from_epoch(stat.st_mtime),
                    "directory": "root",
                }
            )

    logger.info("📂 Found %s total output files (legacy scan)", len(files))
    return files


async def discover_output_files() -> List[Dict[str, Any]]:
    """Public helper for browsing output files across all executions."""
    return await _discover_execution_files()


async def run_command_in_background(
    state_manager: ExecutionStateManager,
    command_executor: WebCommandExecutor,
    execution_id: str,
    command: str,
    args: List[str],
    execution_dir: Optional[str] = None,
) -> None:
    """Execute command asynchronously and persist logs."""
    log_file_path: Optional[Path] = None
    try:
        await state_manager.start_execution(execution_id)
        await state_manager.update_execution_status(execution_id, ExecutionStatus.RUNNING)

        env_vars: Dict[str, str] = {}
        if execution_dir:
            env_vars["EXECUTION_OUTPUT_DIR"] = execution_dir
            logger.info("📁 Execution %s will output to: %s", execution_id, execution_dir)
            log_filename = (
                f"execution_{execution_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
            )
            log_file_path = Path(execution_dir) / log_filename

        async for output in command_executor.execute_command(
            command, args, execution_id=execution_id, env_vars=env_vars
        ):
            await state_manager.add_output(execution_id, output)
            output_type = output.get("type")
            if output_type == "status" and "completed successfully" in output.get("data", ""):
                await state_manager.update_execution_status(
                    execution_id, ExecutionStatus.COMPLETED, return_code=0
                )
            elif output_type == "error":
                await state_manager.update_execution_status(
                    execution_id, ExecutionStatus.FAILED, error_message=output.get("data")
                )
    except Exception as exc:
        await state_manager.update_execution_status(
            execution_id, ExecutionStatus.ERROR, error_message=str(exc)
        )
        logger.error("Background execution error for %s: %s", execution_id, exc, exc_info=True)
    finally:
        if log_file_path and execution_dir:
            try:
                execution = await state_manager.get_execution(execution_id)
                if execution and execution.output_buffer:
                    output_lines: List[str] = []
                    for entry in execution.output_buffer:
                        entry_type = entry.get("type", "unknown")
                        entry_data = entry.get("data", "")
                        timestamp = entry.get("timestamp", "")
                        prefix = f"[{timestamp}] " if timestamp else ""
                        type_prefix = f"[{entry_type.upper()}] " if entry_type != "stdout" else ""
                        output_lines.append(f"{prefix}{type_prefix}{entry_data}")
                    log_file_path.parent.mkdir(parents=True, exist_ok=True)
                    with open(log_file_path, "w", encoding="utf-8") as log_file:
                        log_file.write("\n".join(output_lines))
                    logger.info("📋 Saved execution log to: %s (even on failure)", log_file_path)
            except Exception as save_error:
                logger.error(
                    "Failed to save execution log for %s: %s", execution_id, save_error, exc_info=True
                )


@execution_router.get("/execute")
async def execute_command_stream(
    command: str,
    args: str,
    execution_id: str,
    request: Request,
):
    """Execute a command with Server-Sent Events streaming."""
    await check_rate_limit(request)
    await check_request_size(request)

    command_executor = _require_command_executor(request)
    state_manager = _require_state_manager(request)

    if command not in ALLOWED_COMMANDS:
        raise HTTPException(
            status_code=400,
            detail=f"Command '{command}' is not allowed. Permitted commands: {', '.join(sorted(ALLOWED_COMMANDS))}",
        )

    try:
        args_list = json.loads(args) if args else []
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Invalid args format: must be valid JSON array") from exc

    if not isinstance(args_list, list):
        raise HTTPException(status_code=400, detail="Args must be a JSON array")
    if len(args_list) > MAX_ARGS_COUNT:
        raise HTTPException(
            status_code=400,
            detail=f"Too many arguments (max {MAX_ARGS_COUNT})",
        )

    total_length = 0
    validated_args: List[str] = []
    for idx, arg in enumerate(args_list):
        if not isinstance(arg, str):
            raise HTTPException(
                status_code=400,
                detail=f"Argument {idx} must be a string, got {type(arg).__name__}",
            )
        if len(arg) > MAX_ARG_LENGTH:
            raise HTTPException(
                status_code=400,
                detail=f"Argument {idx} exceeds maximum length of {MAX_ARG_LENGTH} characters",
            )
        total_length += len(arg)
        validated_args.append(arg)

    if total_length > MAX_ARGS_TOTAL_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"Total argument length exceeds maximum of {MAX_ARGS_TOTAL_LENGTH} characters",
        )

    try:
        await state_manager.create_execution(execution_id, command, args_list)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        started = await state_manager.start_execution(execution_id)
        if not started:
            raise HTTPException(status_code=429, detail="Too many concurrent executions")
    except ValueError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc

    async def event_generator() -> AsyncGenerator[Dict[str, Any], None]:
        start_time = time.time()
        last_output_time = time.time()
        first_output_received = False
        output_count = 0
        keepalive_count = 0

        logger.info(
            "[SSE] Connection established for execution %s | Command: %s | Args: %s | Keepalive interval: %ss | Max duration: %ss",
            execution_id,
            command,
            len(validated_args),
            SSE_KEEPALIVE_INTERVAL,
            MAX_SSE_DURATION,
        )

        yield {
            "event": "message",
            "data": json.dumps(
                {
                    "type": "status",
                    "data": f"[SSE] Connection established | Execution ID: {execution_id} | Command: {command}",
                    "execution_id": execution_id,
                    "timestamp": datetime.now().isoformat(),
                    "log_level": "info",
                }
            ),
        }

        try:
            cwd = (
                command_executor._get_project_root()
                if hasattr(command_executor, "_get_project_root")
                else Path.cwd()
            )
            logger.info(
                "[EXEC] Starting command execution %s | Command: %s | Args: %s... (%s total) | Working dir: %s",
                execution_id,
                command,
                validated_args[:3],
                len(validated_args),
                cwd,
            )

            iterator_start = time.time()
            output_iterator = command_executor.execute_command(
                command, validated_args, execution_id=execution_id
            )
            iterator_creation_time = time.time() - iterator_start

            logger.info(
                "[EXEC] Command executor returned iterator in %.3fs | Execution ID: %s",
                iterator_creation_time,
                execution_id,
            )

            output_iter = output_iterator.__aiter__()
            init_message = {
                "type": "status",
                "data": f"Starting analysis... | Execution ID: {execution_id} | Iterator created in {iterator_creation_time:.3f}s",
                "execution_id": execution_id,
                "timestamp": datetime.now().isoformat(),
                "log_level": "info",
            }
            yield {"event": "message", "data": json.dumps(init_message)}
            logger.debug("[SSE] Sent initial 'Starting...' message for %s", execution_id)

            while True:
                try:
                    wait_start = time.time()
                    time_since_last_output = time.time() - last_output_time
                    if time_since_last_output > 5:
                        logger.debug(
                            "[SSE] Waiting for output from %s | Time since last output: %.1fs | Output count: %s | Keepalives: %s",
                            execution_id,
                            time_since_last_output,
                            output_count,
                            keepalive_count,
                        )

                    output = await asyncio.wait_for(
                        output_iter.__anext__(),
                        timeout=SSE_KEEPALIVE_INTERVAL,
                    )

                    wait_duration = time.time() - wait_start
                    if wait_duration > 1.0:
                        logger.debug(
                            "[SSE] Received output after %.3fs wait | Execution ID: %s | Type: %s",
                            wait_duration,
                            execution_id,
                            output.get("type", "unknown"),
                        )
                except asyncio.TimeoutError:
                    keepalive_count += 1
                    elapsed_since_start = time.time() - start_time
                    time_since_last_output = time.time() - last_output_time

                    logger.debug(
                        "[SSE] Keepalive timeout for %s | Elapsed: %.1fs | Time since last output: %.1fs | First output received: %s | Keepalive count: %s",
                        execution_id,
                        elapsed_since_start,
                        time_since_last_output,
                        first_output_received,
                        keepalive_count,
                    )

                    if not first_output_received:
                        progress_msg = f"Initializing... ({int(elapsed_since_start)}s elapsed, {keepalive_count} keepalives)"
                        logger.info(
                            "[SSE] Sending initialization progress for %s | %s",
                            execution_id,
                            progress_msg,
                        )
                        yield {
                            "event": "message",
                            "data": json.dumps(
                                {
                                    "type": "status",
                                    "data": progress_msg,
                                    "execution_id": execution_id,
                                    "timestamp": datetime.now().isoformat(),
                                    "log_level": "info",
                                    "keepalive_count": keepalive_count,
                                }
                            ),
                        }
                    else:
                        logger.debug("[SSE] Sending keepalive #%s for %s", keepalive_count, execution_id)
                        yield {"event": "comment", "data": f"keepalive-{keepalive_count}"}
                    continue
                except StopAsyncIteration:
                    elapsed_total = time.time() - start_time
                    logger.info(
                        "[SSE] Iterator exhausted normally for %s | Total time: %.2fs | Output chunks: %s | Keepalives: %s | First output delay: %.2fs",
                        execution_id,
                        elapsed_total,
                        output_count,
                        keepalive_count,
                        last_output_time - start_time,
                    )
                    yield {
                        "event": "message",
                        "data": json.dumps(
                            {
                                "type": "status",
                                "data": f"[SSE] Iterator completed | Total time: {elapsed_total:.2f}s | Output chunks: {output_count}",
                                "execution_id": execution_id,
                                "timestamp": datetime.now().isoformat(),
                                "log_level": "info",
                            }
                        ),
                    }
                    break

                elapsed = time.time() - start_time
                if elapsed > MAX_SSE_DURATION:
                    timeout_minutes = MAX_SSE_DURATION / 60
                    logger.warning(
                        "Execution %s exceeded timeout of %ss",
                        execution_id,
                        MAX_EXECUTION_DURATION,
                    )
                    await command_executor.cancel_execution(execution_id)
                    await state_manager.update_execution_status(
                        execution_id,
                        ExecutionStatus.TIMEOUT,
                        error_message=f"Execution exceeded {timeout_minutes:.0f} minute limit",
                    )
                    yield {
                        "event": "message",
                        "data": json.dumps(
                            {
                                "type": "timeout",
                                "status": "timeout",
                                "message": f"Execution exceeded {timeout_minutes:.0f} minute limit. Increase MAX_EXECUTION_DURATION if needed.",
                                "execution_id": execution_id,
                            }
                        ),
                    }
                    break

                if await request.is_disconnected():
                    logger.info(
                        "[SSE] Client disconnected for execution %s - continuing in background",
                        execution_id,
                    )
                    await state_manager.update_execution_status(
                        execution_id, ExecutionStatus.RUNNING
                    )
                    yield {
                        "event": "message",
                        "data": json.dumps(
                            {
                                "type": "status",
                                "status": "running",
                                "message": "Client disconnected. Job continues running in background. Resume from Files tab or status endpoint.",
                                "execution_id": execution_id,
                                "timestamp": datetime.now().isoformat(),
                            }
                        ),
                    }
                    break

                output_count += 1
                output_type = output.get("type", "unknown")
                output_size = len(str(output.get("data", "")))
                time_since_start = time.time() - start_time

                logger.debug(
                    "[SSE] Output #%s received for %s | Type: %s | Size: %s bytes | Elapsed: %.2fs | Time since last: %.2fs",
                    output_count,
                    execution_id,
                    output_type,
                    output_size,
                    time_since_start,
                    time.time() - last_output_time,
                )

                if output.get("data") and len(output["data"]) > MAX_SSE_CHUNK_SIZE:
                    original_size = len(output["data"])
                    output["data"] = truncate_chunk(output["data"], MAX_SSE_CHUNK_SIZE)
                    output["truncated"] = True
                    logger.warning(
                        "[SSE] Truncated large output chunk for %s | Original: %s bytes | Truncated to: %s bytes",
                        execution_id,
                        original_size,
                        MAX_SSE_CHUNK_SIZE,
                    )
                    output["_truncation_info"] = {
                        "original_size": original_size,
                        "truncated_size": len(output["data"]),
                    }

                await state_manager.add_output(execution_id, output)

                if output.get("type") == "status":
                    if "completed successfully" in output.get("data", ""):
                        await state_manager.update_execution_status(
                            execution_id, ExecutionStatus.COMPLETED, return_code=0
                        )
                    elif "Starting" in output.get("data", ""):
                        await state_manager.update_execution_status(
                            execution_id, ExecutionStatus.RUNNING
                        )
                elif output.get("type") == "error":
                    await state_manager.update_execution_status(
                        execution_id,
                        ExecutionStatus.FAILED,
                        error_message=output.get("data"),
                    )
                elif output.get("type") == "timeout":
                    await state_manager.update_execution_status(
                        execution_id,
                        ExecutionStatus.TIMEOUT,
                        error_message=output.get("message", "Execution timeout"),
                    )

                yield {"event": "message", "data": json.dumps(output)}

                if not first_output_received:
                    first_output_received = True
                    first_output_delay = time.time() - start_time
                    logger.info(
                        "[SSE] First real output received for %s | Delay: %.2fs | Type: %s | Keepalives before output: %s",
                        execution_id,
                        first_output_delay,
                        output_type,
                        keepalive_count,
                    )
                    yield {
                        "event": "message",
                        "data": json.dumps(
                            {
                                "type": "status",
                                "data": f"[SSE] First output received after {first_output_delay:.2f}s | Keepalives: {keepalive_count}",
                                "execution_id": execution_id,
                                "timestamp": datetime.now().isoformat(),
                                "log_level": "info",
                            }
                        ),
                    }

                last_output_time = time.time()

        except asyncio.CancelledError:
            elapsed_total = time.time() - start_time
            logger.warning(
                "[SSE] Stream for %s ended via CancelledError | Elapsed: %.2fs | Output chunks: %s | Keepalives: %s | First output received: %s",
                execution_id,
                elapsed_total,
                output_count,
                keepalive_count,
                first_output_received,
            )
            await state_manager.update_execution_status(execution_id, ExecutionStatus.RUNNING)
            return
        except json.JSONDecodeError as exc:
            await state_manager.update_execution_status(
                execution_id, ExecutionStatus.ERROR, error_message=f"JSON encoding error: {exc}"
            )
            yield {
                "event": "error",
                "data": json.dumps({"type": "error", "data": "Output encoding error"}),
            }
        except ValueError as exc:
            await state_manager.update_execution_status(
                execution_id, ExecutionStatus.ERROR, error_message=str(exc)
            )
            yield {"event": "error", "data": json.dumps({"type": "error", "data": str(exc)})}
        except RuntimeError as exc:
            await state_manager.update_execution_status(
                execution_id, ExecutionStatus.ERROR, error_message=str(exc)
            )
            yield {
                "event": "error",
                "data": json.dumps({"type": "error", "data": "Command execution failed"}),
            }
        except Exception as exc:  # pragma: no cover - defensive logging
            elapsed_total = time.time() - start_time
            error_type = type(exc).__name__
            logger.error(
                "[SSE] Unexpected error in execution %s | Error type: %s | Error message: %s | Elapsed: %.2fs | Output chunks: %s | Keepalives: %s | First output received: %s",
                execution_id,
                error_type,
                exc,
                elapsed_total,
                output_count,
                keepalive_count,
                first_output_received,
                exc_info=True,
            )
            await state_manager.update_execution_status(
                execution_id, ExecutionStatus.ERROR, error_message=str(exc)
            )
            yield {
                "event": "error",
                "data": json.dumps(
                    {
                        "type": "error",
                        "data": f"Internal server error: {error_type}",
                        "execution_id": execution_id,
                        "timestamp": datetime.now().isoformat(),
                        "log_level": "error",
                        "_debug": {
                            "elapsed_seconds": elapsed_total,
                            "output_count": output_count,
                            "keepalive_count": keepalive_count,
                            "first_output_received": first_output_received,
                        },
                    }
                ),
            }
        finally:
            elapsed_total = time.time() - start_time
            first_output_delay_str = (
                f"{last_output_time - start_time:.2f}s" if first_output_received else "N/A"
            )
            logger.info(
                "[SSE] Connection cleanup for %s | Total duration: %.2fs | Output chunks streamed: %s | Keepalives sent: %s | First output delay: %s",
                execution_id,
                elapsed_total,
                output_count,
                keepalive_count,
                first_output_delay_str,
            )

    return EventSourceResponse(
        event_generator(),
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        media_type="text/event-stream; charset=utf-8",
    )


@execution_router.post("/execute/start")
async def start_execution(
    command: str,
    args: str,
    request: Request,
    token: str = Depends(verify_token),
):
    """Start a new command execution as a background task."""
    _ = token
    await check_rate_limit(request)
    await check_request_size(request)

    command_executor = _require_command_executor(request)
    state_manager = _require_state_manager(request)

    if command not in ALLOWED_COMMANDS:
        raise HTTPException(
            status_code=400,
            detail=f"Command '{command}' is not allowed. Permitted commands: {', '.join(sorted(ALLOWED_COMMANDS))}",
        )

    try:
        args_list = json.loads(args) if args else []
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Invalid args format: must be valid JSON array") from exc

    if not isinstance(args_list, list):
        raise HTTPException(status_code=400, detail="Args must be a JSON array")
    if len(args_list) > MAX_ARGS_COUNT:
        raise HTTPException(
            status_code=400,
            detail=f"Too many arguments (max {MAX_ARGS_COUNT})",
        )
    total_length = 0
    for idx, arg in enumerate(args_list):
        if not isinstance(arg, str):
            raise HTTPException(status_code=400, detail=f"Argument {idx} must be a string")
        if len(arg) > MAX_ARG_LENGTH:
            raise HTTPException(status_code=400, detail=f"Argument {idx} exceeds maximum length")
        total_length += len(arg)
    if total_length > MAX_ARGS_TOTAL_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"Total argument length exceeds maximum of {MAX_ARGS_TOTAL_LENGTH} characters",
        )

    try:
        execution_id = command_executor.generate_execution_id()
    except Exception as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=500, detail=f"Failed to generate execution ID: {exc}") from exc

    exec_dir_name = generate_execution_directory_name(args_list, execution_id)
    exec_dir_path = _get_execution_base_path() / exec_dir_name
    exec_dir_path.mkdir(parents=True, exist_ok=True)
    logger.info("📁 Created execution directory: %s", exec_dir_name)

    execution = await state_manager.create_execution(execution_id, command, args_list)
    if hasattr(execution, "output_files"):
        execution.output_files = [exec_dir_name]

    asyncio.create_task(
        run_command_in_background(
            state_manager,
            command_executor,
            execution_id,
            command,
            args_list,
            str(exec_dir_path),
        )
    )

    return {
        "execution_id": execution_id,
        "status": execution.status.value,
        "queue_position": execution.queue_position,
        "message": "Execution started in background",
    }


@execution_router.post("/execute/cancel/{execution_id}")
async def cancel_execution(
    execution_id: str,
    request: Request,
    token: str = Depends(verify_token),
):
    """Cancel a running or queued execution."""
    _ = token
    await check_rate_limit(request)

    command_executor = _require_command_executor(request)
    state_manager = _require_state_manager(request)

    cancelled = await state_manager.cancel_execution(execution_id)
    if not cancelled:
        raise HTTPException(status_code=404, detail="Execution not found or already completed")

    await command_executor.cancel_execution(execution_id)
    return {"message": "Execution cancelled successfully"}


@execution_router.get("/execute/status/{execution_id}")
async def get_execution_status(
    execution_id: str,
    request: Request,
    since: int = 0,
):
    """Get the status and output of an execution."""
    await check_rate_limit(request)
    state_manager = _require_state_manager(request)

    execution = await state_manager.get_execution(execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")

    try:
        output_list = list(execution.output_buffer) if execution.output_buffer else []
        output_buffer = output_list[since:] if since < len(output_list) else []
    except Exception:  # pragma: no cover - defensive
        output_list = []
        output_buffer = []

    files = await _discover_execution_files()

    return {
        "execution_id": execution.execution_id,
        "command": execution.command,
        "args": execution.args,
        "status": execution.status.value,
        "start_time": execution.start_time.isoformat(),
        "end_time": execution.end_time.isoformat() if execution.end_time else None,
        "queue_position": execution.queue_position,
        "error_message": execution.error_message,
        "return_code": execution.return_code,
        "output": output_buffer,
        "output_length": len(output_list),
        "files": files,
        "gamma_metadata": getattr(execution, "gamma_metadata", None),
    }


@execution_router.get("/execute/list")
async def list_executions(request: Request, limit: int = 50):
    """Get recent executions with debug metadata."""
    await check_rate_limit(request)
    state_manager = _require_state_manager(request)

    executions = await state_manager.get_all_executions(limit=limit)
    persistence_dir = _primary_outputs_path() / "jobs"
    debug_info = {
        "persistence_dir_exists": persistence_dir.exists(),
        "persistence_dir_path": str(persistence_dir),
        "files_in_dir": [str(f) for f in persistence_dir.glob("*.json")] if persistence_dir.exists() else [],
        "total_executions_in_memory": len(state_manager._executions),
    }

    return {
        "executions": [
            {
                "execution_id": exec.execution_id,
                "command": exec.command,
                "args": exec.args,
                "status": exec.status.value,
                "start_time": exec.start_time.isoformat(),
                "end_time": exec.end_time.isoformat() if exec.end_time else None,
                "error_message": exec.error_message,
                "return_code": exec.return_code,
                "output_files": getattr(exec, "output_files", []),
            }
            for exec in executions
        ],
        "debug": debug_info,
    }


# Route implementations from deploy/railway_web.py will be migrated below.


