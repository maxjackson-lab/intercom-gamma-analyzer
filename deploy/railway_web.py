"""
Railway web server for Intercom Analysis Tool Chat Interface.
Provides a web-based chat interface for natural language command translation.
"""

import os
import sys
import json
import asyncio
import logging
import signal
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional
from deploy.web.templates import render_chat_html_v2, render_files_html
from functools import wraps, lru_cache
from collections import defaultdict
import time

# Try to import APScheduler for periodic cleanup
try:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    HAS_APSCHEDULER = True
except ImportError:
    HAS_APSCHEDULER = False
    logger = logging.getLogger(__name__)
    logger.warning("APScheduler not available. Periodic cleanup will not run automatically.")

# Setup logging for deployment diagnostics
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def _default_get_pacific_time() -> datetime:
    return datetime.now()


def _default_datetime_to_pacific(dt: datetime) -> datetime:
    return dt


try:
    from src.utils.timezone_utils import get_pacific_time, datetime_to_pacific  # type: ignore
except Exception:
    logger.warning("timezone_utils not available; falling back to naive timestamps")
    get_pacific_time = _default_get_pacific_time
    datetime_to_pacific = _default_datetime_to_pacific

# Read version information from environment
APP_VERSION = os.getenv('APP_VERSION', 'dev')
GIT_COMMIT = os.getenv('GIT_COMMIT', 'unknown')
BUILD_DATE = os.getenv('BUILD_DATE', datetime.now().isoformat())

# Track application start time for uptime calculation (Pacific time)
app_start_time = get_pacific_time()

# Log version info on startup
logger.info(f"Application Version: {APP_VERSION}")
logger.info(f"Git Commit: {GIT_COMMIT[:8] if GIT_COMMIT != 'unknown' else 'unknown'}")
logger.info(f"Build Date: {BUILD_DATE}")

# Silence tokenizers parallelism warning
os.environ.setdefault('TOKENIZERS_PARALLELISM', 'false')

# Verify Python path setup
logger.info(f"🔧 PYTHONPATH: {os.environ.get('PYTHONPATH', 'Not set')}")
logger.info(f"🔧 Current working directory: {os.getcwd()}")
logger.info(f"🔧 Script location: {__file__}")

# Add parent directory to path for imports (since we're in deploy/)
parent_dir = str(Path(__file__).parent.parent)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
    logger.info(f"🔧 Added parent to path: {parent_dir}")

# Test src import
try:
    import src
    logger.info("✅ Successfully imported src module")
except ImportError as e:
    logger.error(f"❌ Failed to import src: {e}")
    logger.debug(f"🔧 sys.path: {sys.path[:3]}")  # Show first 3 entries

from src.cli.schema import CANONICAL_COMMAND_MAPPINGS, validate_command_request

try:
    from fastapi import FastAPI, HTTPException, Request, Depends
    from fastapi.responses import HTMLResponse, JSONResponse
    from fastapi.staticfiles import StaticFiles
    from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
    from sse_starlette import EventSourceResponse
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel
    import uvicorn
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False

try:
    from src.chat.chat_interface import ChatInterface
    from src.config.settings import Settings
    from src.services.web_command_executor import WebCommandExecutor
    from src.services.execution_state_manager import ExecutionStateManager, ExecutionStatus
    HAS_CHAT = True
    logger.info("✅ Chat dependencies imported successfully")
except ImportError as e:
    HAS_CHAT = False
    logger.error(f"❌ Chat dependencies import failed: {e}")
    logger.warning("   This is likely due to missing heavy dependencies (sentence-transformers, faiss-cpu)")
    logger.warning("   The web interface will still work, but chat features will be limited")

# ============================================================================
# OUTPUT PATH & TIME HELPERS
# ============================================================================

@lru_cache(maxsize=1)
def _primary_outputs_path() -> Path:
    """Return the preferred base outputs directory (volume if available)."""
    volume_path = os.getenv('RAILWAY_VOLUME_MOUNT_PATH')
    base_path = Path(volume_path) / "outputs" if volume_path else Path("/app/outputs")
    base_path.mkdir(parents=True, exist_ok=True)
    return base_path


@lru_cache(maxsize=1)
def _all_output_paths() -> tuple[Path, ...]:
    """Return all output directories to scan (volume first, then container)."""
    paths: List[Path] = []
    volume_path = os.getenv('RAILWAY_VOLUME_MOUNT_PATH')
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
    """Ensure the executions directory exists and return it."""
    base = _primary_outputs_path() / "executions"
    base.mkdir(parents=True, exist_ok=True)
    return base


def _format_pacific_timestamp_from_epoch(epoch_seconds: float) -> str:
    """Convert an epoch timestamp to ISO Pacific time."""
    utc_dt = datetime.fromtimestamp(epoch_seconds, tz=timezone.utc)
    pacific_dt = datetime_to_pacific(utc_dt)
    return pacific_dt.isoformat()


# ============================================================================
# SECURITY: Rate Limiting and Request Tracking
# ============================================================================

class RateLimiter:
    """Simple in-memory rate limiter for per-IP requests."""
    
    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = defaultdict(list)
    
    def is_allowed(self, client_ip: str) -> bool:
        """Check if client is within rate limit."""
        now = time.time()
        cutoff = now - self.window_seconds
        
        # Clean old requests
        self.requests[client_ip] = [
            req_time for req_time in self.requests[client_ip]
            if req_time > cutoff
        ]
        
        # Check limit
        if len(self.requests[client_ip]) >= self.max_requests:
            return False
        
        # Record this request
        self.requests[client_ip].append(now)
        return True

rate_limiter = RateLimiter(max_requests=100, window_seconds=60)

# Maximum request payload size (10MB)
MAX_REQUEST_SIZE = 10 * 1024 * 1024

# ============================================================================
# SSE EXECUTION STREAM CONFIGURATION
# ============================================================================

# Allow configurable timeout via environment variable, default to 60 minutes for large datasets
MAX_EXECUTION_DURATION = int(os.getenv('MAX_EXECUTION_DURATION', 60 * 60))  # Default: 60 minutes

# Comment 5: Read SSE keepalive interval from env with default
SSE_KEEPALIVE_INTERVAL = int(os.getenv('SSE_KEEPALIVE_INTERVAL', 15))
# Comment 5: Read max SSE duration from env with default (reuse MAX_EXECUTION_DURATION name)
MAX_SSE_DURATION = int(os.getenv('MAX_SSE_DURATION', os.getenv('MAX_EXECUTION_DURATION', 60 * 60)))

# Comment 5: Validate and log SSE configuration at startup (after definitions)
logger.info(f"SSE Configuration: keepalive_interval={SSE_KEEPALIVE_INTERVAL}s, max_duration={MAX_SSE_DURATION}s")
if SSE_KEEPALIVE_INTERVAL < 5 or SSE_KEEPALIVE_INTERVAL > 300:
    logger.warning(f"SSE_KEEPALIVE_INTERVAL={SSE_KEEPALIVE_INTERVAL}s is outside recommended range (5-300s)")
if MAX_SSE_DURATION < 60 or MAX_SSE_DURATION > 7200:
    logger.warning(f"MAX_SSE_DURATION={MAX_SSE_DURATION}s is outside recommended range (60-7200s)")

# Maximum size per SSE event (10KB)
MAX_SSE_CHUNK_SIZE = 10 * 1024

def truncate_chunk(chunk: str, max_size: int = MAX_SSE_CHUNK_SIZE) -> str:
    """
    Truncate chunk to max size, preserving valid structure if applicable.
    
    Args:
        chunk: The content to truncate
        max_size: Maximum size in bytes
        
    Returns:
        Truncated chunk with indicator if truncated
    """
    if len(chunk) <= max_size:
        return chunk
    
    # Try to truncate at newline boundary
    truncated = chunk[:max_size]
    last_newline = truncated.rfind('\n')
    if last_newline > max_size * 0.8:  # If found in last 20%
        truncated = truncated[:last_newline]
    
    return truncated + "\n... [output truncated, see full logs]"

# Initialize FastAPI app
if HAS_FASTAPI:
    from fastapi.staticfiles import StaticFiles
    
    app = FastAPI(
        title="Intercom Analysis Tool - Chat Interface",
        description="Natural language interface for generating analysis reports",
        version="1.0.0"
    )
    
    # Mount static files directory
    static_path = Path(__file__).parent.parent / "static"
    static_path.mkdir(parents=True, exist_ok=True)
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

    # Mount new Svelte frontend (REMOVED)
    # frontend_build_path = Path(__file__).parent.parent / "frontend" / "build"
    # if frontend_build_path.exists():
    #     app.mount("/v2", StaticFiles(directory=str(frontend_build_path), html=True), name="frontend_v2")
    #     logger.info(f"✅ Mounted new Svelte frontend at /v2 from {frontend_build_path}")
    # else:
    #     # logger.warning(f"⚠️  New frontend build not found at {frontend_build_path}. /v2 will not be available.")
    #     pass
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # DEBUG ENDPOINT: Inspect the template file content on disk
    @app.get("/debug-template")
    async def debug_template():
        try:
            # deploy/web/templates.py is relative to deploy/railway_web.py
            template_path = Path(__file__).parent / "web" / "templates.py"
            if not template_path.exists():
                return {"error": f"File not found: {template_path}"}
            
            content = template_path.read_text()
            return {
                "path": str(template_path),
                "exists": template_path.exists(),
                "has_marker": "DL_MARKER_VISIBLE_TEST_20251128" in content,
                "content_preview_marker": [line for line in content.splitlines() if "DL_MARKER" in line],
                "content_preview": content[:500]
            }
        except Exception as e:
            return {"error": str(e)}
    
    # Security scheme for bearer token authentication
    security = HTTPBearer(auto_error=False)
    
    async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
        """
        Verify bearer token for command execution endpoints.
        
        This protects sensitive command execution endpoints from unauthorized access.
        Token validation can be customized based on your security requirements.
        """
        # Get the expected token from environment (if not set, allow local development)
        expected_token = os.getenv("EXECUTION_API_TOKEN")
        
        # If no token is configured, allow access (for development/backwards compatibility)
        # In production, you should always set EXECUTION_API_TOKEN
        if not expected_token:
            return "development"
        
        # Check if credentials were provided
        if not credentials:
            raise HTTPException(
                status_code=401,
                detail="Authentication required. Please provide a valid bearer token."
            )
        
        # Validate the token
        if credentials.credentials != expected_token:
            raise HTTPException(
                status_code=401,
                detail="Invalid authentication credentials"
            )
        
        return credentials.credentials
    
    async def check_rate_limit(request: Request):
        """Check rate limit for client IP."""
        client_ip = request.client.host if request.client else "unknown"
        if not rate_limiter.is_allowed(client_ip):
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded: 100 requests per minute per IP"
            )
    
    async def check_request_size(request: Request):
        """Check request payload size."""
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > MAX_REQUEST_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"Request payload too large (max {MAX_REQUEST_SIZE / 1024 / 1024:.0f}MB)"
            )
    
    # Pydantic models
    class ChatRequest(BaseModel):
        query: str
        context: Dict[str, Any] = {}

    class ChatResponse(BaseModel):
        success: bool
        message: str
        data: Dict[str, Any] = {}
else:
    # Fallback for when FastAPI is not available
    app = None
    ChatRequest = None
    ChatResponse = None

# Global chat interface
chat_interface = None
command_executor = None
state_manager = None

# Command whitelist for security - only these commands can be executed
ALLOWED_COMMANDS = {
    "python",
    "python3",
    # Intercom Analysis CLI commands
    "voice-of-customer",
    "sample-mode",  # New: Quick sample of real data
    "billing-analysis",
    "product-analysis",
    "sites-analysis",
    "api-analysis",
    "canny-analysis",
    "trend-analysis",
}

# Maximum argument lengths for security
MAX_ARG_LENGTH = 1024
MAX_ARGS_COUNT = 100
MAX_ARGS_TOTAL_LENGTH = 8192

# ============================================================================
# CANONICAL COMMAND MAPPINGS - Single Source of Truth
# ============================================================================

# Imported from src.cli.schema to keep CLI and Railway aligned

def start_cleanup_scheduler():
    """Start background cleanup task for old executions and files."""
    if not HAS_APSCHEDULER:
        logger.warning("APScheduler not available. Skipping cleanup scheduler setup.")
        return None
    
    if not state_manager:
        logger.warning("State manager not available. Skipping cleanup scheduler setup.")
        return None
    
    try:
        # Get retention configuration from environment
        retention_days = int(os.getenv('AUDIT_RETENTION_DAYS', '14'))
        max_count = int(os.getenv('AUDIT_MAX_COUNT', '50'))
        
        logger.info(f"🧹 Configuring cleanup scheduler: {retention_days} days retention, max {max_count} executions")
        
        scheduler = AsyncIOScheduler()
        
        # Run cleanup daily at 2 AM
        async def cleanup_task():
            try:
                logger.info("🧹 Running scheduled cleanup...")
                result = await state_manager.cleanup_old_executions(
                    max_age_days=retention_days,
                    max_count=max_count,
                    cleanup_files=True
                )
                logger.info(
                    f"✅ Scheduled cleanup complete: "
                    f"deleted {result['deleted_executions']} executions, "
                    f"{result['deleted_files']} files. "
                    f"{result['remaining_executions']} executions remaining."
                )
            except Exception as e:
                logger.error(f"❌ Scheduled cleanup failed: {e}", exc_info=True)
        
        scheduler.add_job(
            cleanup_task,
            trigger='cron',
            hour=2,
            minute=0,
            id='daily_cleanup',
            replace_existing=True
        )
        
        scheduler.start()
        logger.info("✅ Cleanup scheduler started successfully (runs daily at 2 AM)")
        return scheduler
        
    except Exception as e:
        logger.error(f"❌ Failed to start cleanup scheduler: {e}", exc_info=True)
        return None

def initialize_chat():
    """Initialize the chat interface."""
    global chat_interface, command_executor, state_manager
    if not HAS_CHAT:
        logger.error("❌ Chat interface dependencies not available")
        return False
    
    try:
        logger.info("🔧 Checking environment variables...")
        
        # Check for required environment variables
        required_vars = ["INTERCOM_ACCESS_TOKEN", "OPENAI_API_KEY"]
        missing_vars = []
        
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            logger.warning(f"⚠️ Missing required environment variables: {missing_vars}")
            logger.warning("   Chat interface will not be available until these are set")
            return False
        
        logger.info("🔧 Initializing settings...")
        settings = Settings()
        logger.info("✅ Settings loaded successfully")
        
        logger.info("🔧 Initializing chat interface...")
        chat_interface = ChatInterface(settings)
        logger.info("✅ Chat interface initialized successfully")
        
        logger.info("🔧 Initializing command executor...")
        command_executor = WebCommandExecutor()
        logger.info("✅ Command executor initialized successfully")
        
        logger.info("🔧 Initializing state manager...")
        outputs_base_path = _primary_outputs_path()
        state_manager = ExecutionStateManager(
            max_concurrent=5,
            max_queue_size=20,
            persistence_dir=str(outputs_base_path / "jobs"),
            outputs_base_path=str(outputs_base_path)
        )
        logger.info("✅ State manager initialized successfully")
        
        return True
    except Exception as e:
        logger.error(f"❌ Failed to initialize chat interface: {e}", exc_info=True)
        return False

if HAS_FASTAPI:
    @app.get("/files", response_class=HTMLResponse)
    async def files_page():
        """Serve files browser page via templates."""
        cache_bust = f"{APP_VERSION}-{GIT_COMMIT[:8] if GIT_COMMIT != 'unknown' else 'unknown'}"
        return HTMLResponse(
            content=render_files_html(cache_bust=cache_bust),
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )
    
    @app.get("/", response_class=HTMLResponse)
    async def root():
        """Serve the chat interface HTML (delegated to templates)."""
        cache_bust = f"{APP_VERSION}-{GIT_COMMIT[:8] if GIT_COMMIT != 'unknown' else 'unknown'}"
        return HTMLResponse(
            content=render_chat_html_v2(app_version=APP_VERSION, git_commit=GIT_COMMIT, cache_bust=cache_bust),
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )

    @app.post("/chat", response_model=ChatResponse)
    async def chat_endpoint(request: ChatRequest):
        """Process chat queries."""
        if not chat_interface:
            return ChatResponse(
                success=False,
                message="Chat interface not available. This is likely due to missing dependencies (sentence-transformers, faiss-cpu) that are too large for Railway deployment. The basic analysis functionality should still work through the CLI interface.",
                data={"error_type": "dependencies_missing"}
            )
        
        try:
            result = chat_interface.process_query(request.query, request.context)
            
            if result["success"]:
                return ChatResponse(
                    success=True,
                    message="Query processed successfully",
                    data=result
                )
            else:
                return ChatResponse(
                    success=False,
                    message=result.get("error", "Unknown error"),
                    data=result
                )
        except Exception as e:
            return ChatResponse(
                success=False,
                message=f"Internal error: {str(e)}",
                data={}
            )

    @app.get("/execute")
    async def execute_command_stream(
        command: str,
        args: str,
        execution_id: str,
        request: Request
    ):
        """
        Execute a command with Server-Sent Events stream.
        
        **Resource Limits:**
        - Max execution time: Configurable via MAX_EXECUTION_DURATION env var (default: 60 minutes)
        - Keepalive interval: 15 seconds (prevents connection timeout)
        - Max chunk size: 10KB per SSE event (larger chunks truncated)
        - Rate limit: 100 requests per minute per IP
        
        **For Large Datasets:**
        Set MAX_EXECUTION_DURATION environment variable to allow longer execution times.
        Example: MAX_EXECUTION_DURATION=7200 (2 hours)
        
        **⚠️ PRODUCTION RECOMMENDATION:**
        For production workloads (multi-agent analysis, full-week data, Gamma generation):
        - Use /execute/start endpoint for background execution (no SSE timeout)
        - Poll /execute/status/{execution_id} for progress updates
        - This prevents connection timeout issues on long-running tasks
        
        **Timeout Handling:**
        If execution exceeds the max duration, the stream will send a timeout
        status and terminate. For very large datasets, consider using --test-mode
        for faster execution or increase MAX_EXECUTION_DURATION.
        
        **Client Disconnect:**
        If client disconnects, the job continues running in the background.
        You can resume via /execute/status/{execution_id} or the web UI banner.
        
        Security: This endpoint requires bearer token authentication and rate limiting.
        Set EXECUTION_API_TOKEN environment variable to enable authentication.
        """
        # Check rate limit
        await check_rate_limit(request)
        
        if not command_executor or not state_manager:
            raise HTTPException(status_code=500, detail="Execution services not available")
        
        # Validate command whitelist
        if command not in ALLOWED_COMMANDS:
            raise HTTPException(
                status_code=400, 
                detail=f"Command '{command}' is not allowed. Permitted commands: {', '.join(sorted(ALLOWED_COMMANDS))}"
            )
        
        # Parse and validate args from JSON string
        try:
            args_list = json.loads(args) if args else []
        except json.JSONDecodeError as e:
            raise HTTPException(status_code=400, detail="Invalid args format: must be valid JSON array") from e
        
        # Validate args is a list
        if not isinstance(args_list, list):
            raise HTTPException(status_code=400, detail="Args must be a JSON array")
        
        # Validate args count
        if len(args_list) > MAX_ARGS_COUNT:
            raise HTTPException(
                status_code=400, 
                detail=f"Too many arguments (max {MAX_ARGS_COUNT})"
            )
        
        # Validate each arg is a string and enforce length limits
        total_length = 0
        validated_args = []
        for i, arg in enumerate(args_list):
            if not isinstance(arg, str):
                raise HTTPException(
                    status_code=400, 
                    detail=f"Argument {i} must be a string, got {type(arg).__name__}"
                )
            if len(arg) > MAX_ARG_LENGTH:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Argument {i} exceeds maximum length of {MAX_ARG_LENGTH} characters"
                )
            total_length += len(arg)
            validated_args.append(arg)
        
        # Check total length
        if total_length > MAX_ARGS_TOTAL_LENGTH:
            raise HTTPException(
                status_code=400,
                detail=f"Total argument length exceeds maximum of {MAX_ARGS_TOTAL_LENGTH} characters"
            )
        
        # Create the execution
        try:
            execution = await state_manager.create_execution(execution_id, command, args_list)
        except ValueError as e:
            # Domain validation error from state manager
            raise HTTPException(status_code=400, detail=str(e)) from e
        
        # Start the execution (move from queue to active)
        try:
            started = await state_manager.start_execution(execution_id)
            if not started:
                raise HTTPException(status_code=429, detail="Too many concurrent executions")
        except ValueError as e:
            raise HTTPException(status_code=429, detail=str(e)) from e
        
        async def event_generator():
            """Generate SSE events from command output with timeout, keepalive, and disconnect detection."""
            start_time = time.time()
            last_output_time = time.time()
            execution_task = None
            first_output_received = False
            output_count = 0
            keepalive_count = 0
            
            # Rich logging: SSE connection established
            logger.info(
                f"[SSE] Connection established for execution {execution_id} | "
                f"Command: {command} | Args: {len(validated_args)} arguments | "
                f"Keepalive interval: {SSE_KEEPALIVE_INTERVAL}s | Max duration: {MAX_SSE_DURATION}s"
            )
            
            # Stream log to terminal window
            yield {
                "event": "message",
                "data": json.dumps({
                    'type': 'status',
                    'data': f'[SSE] Connection established | Execution ID: {execution_id} | Command: {command}',
                    'execution_id': execution_id,
                    'timestamp': datetime.now().isoformat(),
                    'log_level': 'info'
                })
            }
            
            try:
                # Rich logging: Command execution starting
                cwd = command_executor._get_project_root() if hasattr(command_executor, '_get_project_root') else Path.cwd()
                logger.info(
                    f"[EXEC] Starting command execution {execution_id} | "
                    f"Command: {command} | "
                    f"Args: {validated_args[:3]}... ({len(validated_args)} total) | "
                    f"Working dir: {cwd}"
                )
                
                # Create async iterator from command executor
                iterator_start = time.time()
                output_iterator = command_executor.execute_command(
                    command, validated_args, execution_id=execution_id
                )
                iterator_creation_time = time.time() - iterator_start
                
                logger.info(
                    f"[EXEC] Command executor returned iterator in {iterator_creation_time:.3f}s | "
                    f"Execution ID: {execution_id}"
                )
                
                # Process output with timeout and keepalive
                # Use asyncio.wait_for to implement keepalive during long waits
                output_iter = output_iterator.__aiter__()
                
                # Comment 1: Immediately yield "Starting..." message to prevent SSE stall
                init_message = {
                    'type': 'status',
                    'data': f'Starting analysis... | Execution ID: {execution_id} | Iterator created in {iterator_creation_time:.3f}s',
                    'execution_id': execution_id,
                    'timestamp': datetime.now().isoformat(),
                    'log_level': 'info'
                }
                yield {
                    "event": "message",
                    "data": json.dumps(init_message)
                }
                logger.debug(f"[SSE] Sent initial 'Starting...' message for {execution_id}")
                
                while True:
                    try:
                        # Rich logging: Waiting for output
                        wait_start = time.time()
                        time_since_last_output = time.time() - last_output_time
                        if time_since_last_output > 5:
                            logger.debug(
                                f"[SSE] Waiting for output from {execution_id} | "
                                f"Time since last output: {time_since_last_output:.1f}s | "
                                f"Output count: {output_count} | Keepalives: {keepalive_count}"
                            )
                        
                        # Wait for next output with timeout for keepalive
                        output = await asyncio.wait_for(
                            output_iter.__anext__(),
                            timeout=SSE_KEEPALIVE_INTERVAL
                        )
                        
                        wait_duration = time.time() - wait_start
                        if wait_duration > 1.0:
                            logger.debug(
                                f"[SSE] Received output after {wait_duration:.3f}s wait | "
                                f"Execution ID: {execution_id} | Type: {output.get('type', 'unknown')}"
                            )
                    except asyncio.TimeoutError:
                        # No output for SSE_KEEPALIVE_INTERVAL seconds - send keepalive or progress
                        keepalive_count += 1
                        elapsed_since_start = time.time() - start_time
                        time_since_last_output = time.time() - last_output_time
                        
                        logger.debug(
                            f"[SSE] Keepalive timeout for {execution_id} | "
                            f"Elapsed: {elapsed_since_start:.1f}s | "
                            f"Time since last output: {time_since_last_output:.1f}s | "
                            f"First output received: {first_output_received} | "
                            f"Keepalive count: {keepalive_count}"
                        )
                        
                        if not first_output_received:
                            # Comment 1: Send periodic progress status until first real output
                            progress_msg = f'Initializing... ({int(elapsed_since_start)}s elapsed, {keepalive_count} keepalives)'
                            logger.info(
                                f"[SSE] Sending initialization progress for {execution_id} | "
                                f"{progress_msg}"
                            )
                            yield {
                                "event": "message",
                                "data": json.dumps({
                                    'type': 'status',
                                    'data': progress_msg,
                                    'execution_id': execution_id,
                                    'timestamp': datetime.now().isoformat(),
                                    'log_level': 'info',
                                    'keepalive_count': keepalive_count
                                })
                            }
                        else:
                            # Regular keepalive after first output
                            logger.debug(f"[SSE] Sending keepalive #{keepalive_count} for {execution_id}")
                            yield {"event": "comment", "data": f"keepalive-{keepalive_count}"}
                        continue
                    except StopAsyncIteration:
                        # Iterator exhausted normally
                        elapsed_total = time.time() - start_time
                        logger.info(
                            f"[SSE] Iterator exhausted normally for {execution_id} | "
                            f"Total time: {elapsed_total:.2f}s | "
                            f"Output chunks: {output_count} | "
                            f"Keepalives: {keepalive_count} | "
                            f"First output delay: {last_output_time - start_time:.2f}s"
                        )
                        yield {
                            "event": "message",
                            "data": json.dumps({
                                'type': 'status',
                                'data': f'[SSE] Iterator completed | Total time: {elapsed_total:.2f}s | Output chunks: {output_count}',
                                'execution_id': execution_id,
                                'timestamp': datetime.now().isoformat(),
                                'log_level': 'info'
                            })
                        }
                        break
                    # Check timeout (use MAX_SSE_DURATION)
                    elapsed = time.time() - start_time
                    if elapsed > MAX_SSE_DURATION:
                        timeout_minutes = MAX_SSE_DURATION / 60
                        logger.warning(f"Execution {execution_id} exceeded timeout of {MAX_EXECUTION_DURATION}s")
                        await command_executor.cancel_execution(execution_id)
                        await state_manager.update_execution_status(
                            execution_id, ExecutionStatus.TIMEOUT,
                            error_message=f'Execution exceeded {timeout_minutes:.0f} minute limit'
                        )
                        yield {
                            "event": "message",
                            "data": json.dumps({
                                'type': 'timeout',
                                'status': 'timeout',
                                'message': f'Execution exceeded {timeout_minutes:.0f} minute limit. Increase MAX_EXECUTION_DURATION if needed.',
                                'execution_id': execution_id
                            })
                        }
                        break
                    
                    # Check for client disconnect
                    if await request.is_disconnected():
                        logger.info(f"[SSE] Client disconnected for execution {execution_id} - continuing in background")
                        # Do NOT cancel the running job; leave it running and just end SSE stream.
                        # Update state to running (no change) and emit a final advisory message.
                        await state_manager.update_execution_status(
                            execution_id, ExecutionStatus.RUNNING
                        )
                        yield {
                            "event": "message",
                            "data": json.dumps({
                                'type': 'status',
                                'status': 'running',
                                'message': 'Client disconnected. Job continues running in background. Resume from Files tab or status endpoint.',
                                'execution_id': execution_id,
                                'timestamp': datetime.now().isoformat()
                            })
                        }
                        break
                    
                    # Rich logging: Output received
                    output_count += 1
                    output_type = output.get("type", "unknown")
                    output_size = len(str(output.get("data", "")))
                    time_since_start = time.time() - start_time
                    
                    logger.debug(
                        f"[SSE] Output #{output_count} received for {execution_id} | "
                        f"Type: {output_type} | Size: {output_size} bytes | "
                        f"Elapsed: {time_since_start:.2f}s | "
                        f"Time since last: {time.time() - last_output_time:.2f}s"
                    )
                    
                    # Truncate large chunks
                    if output.get("data") and len(output["data"]) > MAX_SSE_CHUNK_SIZE:
                        original_size = len(output["data"])
                        output["data"] = truncate_chunk(output["data"], MAX_SSE_CHUNK_SIZE)
                        output["truncated"] = True
                        logger.warning(
                            f"[SSE] Truncated large output chunk for {execution_id} | "
                            f"Original: {original_size} bytes | Truncated to: {MAX_SSE_CHUNK_SIZE} bytes"
                        )
                        # Add truncation info to output
                        output["_truncation_info"] = {
                            "original_size": original_size,
                            "truncated_size": len(output["data"])
                        }
                    
                    # Update state manager with output
                    await state_manager.add_output(execution_id, output)
                    
                    # Update status in state manager
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
                            execution_id, ExecutionStatus.FAILED,
                            error_message=output.get("data")
                        )
                    elif output.get("type") == "timeout":
                        await state_manager.update_execution_status(
                            execution_id, ExecutionStatus.TIMEOUT,
                            error_message=output.get("message", "Execution timeout")
                        )
                    
                    # Yield as SSE event
                    yield {
                        "event": "message",
                        "data": json.dumps(output)
                    }
                    
                    # Mark first output received
                    if not first_output_received:
                        first_output_received = True
                        first_output_delay = time.time() - start_time
                        logger.info(
                            f"[SSE] First real output received for {execution_id} | "
                            f"Delay: {first_output_delay:.2f}s | "
                            f"Type: {output_type} | "
                            f"Keepalives sent before first output: {keepalive_count}"
                        )
                        # Stream this milestone to terminal
                        yield {
                            "event": "message",
                            "data": json.dumps({
                                'type': 'status',
                                'data': f'[SSE] First output received after {first_output_delay:.2f}s | Keepalives: {keepalive_count}',
                                'execution_id': execution_id,
                                'timestamp': datetime.now().isoformat(),
                                'log_level': 'info'
                            })
                        }
                    
                    # Update last output time
                    last_output_time = time.time()
                
            except asyncio.CancelledError:
                # Client disconnected or server shut down the connection
                elapsed_total = time.time() - start_time
                logger.warning(
                    f"[SSE] Stream for {execution_id} ended via CancelledError | "
                    f"Elapsed: {elapsed_total:.2f}s | "
                    f"Output chunks: {output_count} | "
                    f"Keepalives: {keepalive_count} | "
                    f"First output received: {first_output_received}"
                )
                # Do NOT cancel the job. Leave it running in background.
                await state_manager.update_execution_status(
                    execution_id, ExecutionStatus.RUNNING
                )
                # Silently end the SSE stream
                return
            except json.JSONDecodeError as e:
                # JSON encoding error
                await state_manager.update_execution_status(
                    execution_id, ExecutionStatus.ERROR, error_message=f"JSON encoding error: {str(e)}"
                )
                yield {
                    "event": "error",
                    "data": json.dumps({"type": "error", "data": "Output encoding error"})
                }
            except ValueError as e:
                # Domain validation error
                await state_manager.update_execution_status(
                    execution_id, ExecutionStatus.ERROR, error_message=str(e)
                )
                yield {
                    "event": "error",
                    "data": json.dumps({"type": "error", "data": str(e)})
                }
            except RuntimeError as e:
                # Operational error
                await state_manager.update_execution_status(
                    execution_id, ExecutionStatus.ERROR, error_message=str(e)
                )
                yield {
                    "event": "error",
                    "data": json.dumps({"type": "error", "data": "Command execution failed"})
                }
            except Exception as e:
                # Unexpected error - log but don't expose details to client
                elapsed_total = time.time() - start_time
                error_type = type(e).__name__
                import traceback
                error_traceback = traceback.format_exc()
                
                logger.error(
                    f"[SSE] Unexpected error in execution {execution_id} | "
                    f"Error type: {error_type} | "
                    f"Error message: {str(e)} | "
                    f"Elapsed: {elapsed_total:.2f}s | "
                    f"Output chunks: {output_count} | "
                    f"Keepalives: {keepalive_count} | "
                    f"First output received: {first_output_received}",
                    exc_info=True
                )
                
                await state_manager.update_execution_status(
                    execution_id, ExecutionStatus.ERROR, error_message=str(e)
                )
                
                # Stream error details to terminal (sanitized)
                yield {
                    "event": "error",
                    "data": json.dumps({
                        "type": "error",
                        "data": f"Internal server error: {error_type}",
                        "execution_id": execution_id,
                        "timestamp": datetime.now().isoformat(),
                        "log_level": "error",
                        "_debug": {
                            "elapsed_seconds": elapsed_total,
                            "output_count": output_count,
                            "keepalive_count": keepalive_count,
                            "first_output_received": first_output_received
                        }
                    })
                }
            finally:
                # Rich logging: Connection cleanup
                elapsed_total = time.time() - start_time
                first_output_delay_str = f"{last_output_time - start_time:.2f}s" if first_output_received else "N/A"
                logger.info(
                    f"[SSE] Connection cleanup for {execution_id} | "
                    f"Total duration: {elapsed_total:.2f}s | "
                    f"Output chunks streamed: {output_count} | "
                    f"Keepalives sent: {keepalive_count} | "
                    f"First output delay: {first_output_delay_str}"
                )
        
        # Comment 6: Construct EventSourceResponse with proper headers for no-buffering
        return EventSourceResponse(
            event_generator(),
            headers={
                'Cache-Control': 'no-cache',
                'X-Accel-Buffering': 'no',
            },
            media_type='text/event-stream; charset=utf-8'
        )
    
    async def run_command_background(execution_id: str, command: str, args: list, execution_dir: str = None):
        """Run command in background and update state."""
        log_file_path = None
        try:
            await state_manager.start_execution(execution_id)
            await state_manager.update_execution_status(execution_id, ExecutionStatus.RUNNING)
            
            # Pass execution directory as environment variable
            env_vars = {}
            if execution_dir:
                env_vars['EXECUTION_OUTPUT_DIR'] = execution_dir
                logger.info(f"📁 Execution {execution_id} will output to: {execution_dir}")
                
                # Prepare log file path for failure case
                log_filename = f"execution_{execution_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
                log_file_path = Path(execution_dir) / log_filename
            
            async for output in command_executor.execute_command(command, args, execution_id=execution_id, env_vars=env_vars):
                # Update state manager with output
                await state_manager.add_output(execution_id, output)
                
                # Update status based on output type
                if output.get("type") == "status":
                    if "completed successfully" in output.get("data", ""):
                        await state_manager.update_execution_status(
                            execution_id, ExecutionStatus.COMPLETED, return_code=0
                        )
                elif output.get("type") == "error":
                    await state_manager.update_execution_status(
                        execution_id, ExecutionStatus.FAILED, 
                        error_message=output.get("data")
                    )
        except Exception as e:
            await state_manager.update_execution_status(
                execution_id, ExecutionStatus.ERROR, error_message=str(e)
            )
            logger.error(f"Background execution error for {execution_id}: {e}", exc_info=True)
        finally:
            # Save logs to file even on failure
            if log_file_path and execution_dir:
                try:
                    execution = await state_manager.get_execution(execution_id)
                    if execution and execution.output_buffer:
                        # Get all output from buffer
                        output_lines = []
                        for entry in execution.output_buffer:
                            entry_type = entry.get("type", "unknown")
                            entry_data = entry.get("data", "")
                            timestamp = entry.get("timestamp", "")
                            
                            # Format: [timestamp] [type] data
                            prefix = f"[{timestamp}] " if timestamp else ""
                            type_prefix = f"[{entry_type.upper()}] " if entry_type != "stdout" else ""
                            output_lines.append(f"{prefix}{type_prefix}{entry_data}")
                        
                        # Write to log file
                        log_file_path.parent.mkdir(parents=True, exist_ok=True)
                        with open(log_file_path, 'w', encoding='utf-8') as f:
                            f.write("\n".join(output_lines))
                        
                        logger.info(f"📋 Saved execution log to: {log_file_path} (even on failure)")
                except Exception as save_error:
                    logger.error(f"Failed to save execution log for {execution_id}: {save_error}", exc_info=True)
    
    # ============================================================================
    # EXECUTION DIRECTORY HELPERS
    # ============================================================================
    
    def _generate_execution_directory_name(args_list: list[str], execution_id: str) -> str:
        """
        Generate human-readable directory name for execution.
        
        Format: {mode}_{date-description}_{time}
        Examples:
            sample-mode_Last-Week_Nov-13-5-27pm
            voice-of-customer_Nov-6-to-Nov-13_Nov-13-6-00pm
            agent-performance_November-2025_Nov-10-2-30pm
        """
        from datetime import datetime
        import re
        
        # Parse mode from args
        mode = "unknown"
        if len(args_list) > 1:
            mode = args_list[1].replace('.py', '').replace('src/main.py', '').strip()
            if not mode:
                mode = args_list[0] if args_list else "unknown"
        
        # Parse date description from args
        date_desc = "unknown-date"
        
        # Look for --time-period flag
        if '--time-period' in args_list:
            idx = args_list.index('--time-period')
            if idx + 1 < len(args_list):
                period = args_list[idx + 1]
                # Convert to readable format
                period_map = {
                    'yesterday': 'Yesterday',
                    'week': 'Last-Week',
                    'month': 'Last-Month',
                    'quarter': 'Last-Quarter',
                    'year': 'Last-Year',
                    '6-weeks': 'Last-6-Weeks'
                }
                date_desc = period_map.get(period, period)
        
        # Look for --start-date and --end-date
        elif '--start-date' in args_list and '--end-date' in args_list:
            start_idx = args_list.index('--start-date')
            end_idx = args_list.index('--end-date')
            if start_idx + 1 < len(args_list) and end_idx + 1 < len(args_list):
                start_date = args_list[start_idx + 1]
                end_date = args_list[end_idx + 1]
                
                # Convert YYYY-MM-DD to Nov-6
                try:
                    start_obj = datetime.fromisoformat(start_date)
                    end_obj = datetime.fromisoformat(end_date)
                    start_str = start_obj.strftime('%b-%d')
                    end_str = end_obj.strftime('%b-%d')
                    date_desc = f"{start_str}-to-{end_str}"
                except:
                    date_desc = f"{start_date}-to-{end_date}"
        
        # Look for --days flag
        elif '--days' in args_list:
            idx = args_list.index('--days')
            if idx + 1 < len(args_list):
                days = args_list[idx + 1]
                date_desc = f"Last-{days}-Days"
        
        # Current timestamp in human-readable format (Pacific)
        now = get_pacific_time()
        time_str = now.strftime('%b-%d-%I-%M%p').replace('-0', '-').lower()  # Nov-13-5-27pm
        
        # Combine: mode_date-description_time
        dir_name = f"{mode}_{date_desc}_{time_str}"
        
        # Sanitize for filesystem (remove special chars, limit length)
        dir_name = re.sub(r'[^\w\-]', '-', dir_name)  # Replace special chars with -
        dir_name = re.sub(r'-+', '-', dir_name)  # Collapse multiple dashes
        dir_name = dir_name[:200]  # Limit length
        
        return dir_name
    
    async def _discover_execution_files(execution) -> list[dict]:
        """
        Discover all output files for an execution.
        
        Returns list of {name, size, path, created_at}
        """
        files = []
        seen_paths = set()
        
        # Strategy 1: Scan execution directories on all known bases
        for outputs_base in _all_output_paths():
            executions_base = outputs_base / "executions"
            if not executions_base.exists():
                continue
            
            for exec_dir in executions_base.iterdir():
                if not exec_dir.is_dir():
                    continue
                
                for file_path in exec_dir.rglob('*'):
                    if not file_path.is_file():
                        continue
                    
                    rel_path = file_path.relative_to(outputs_base)
                    rel_path_str = str(rel_path)
                    if rel_path_str in seen_paths:
                        continue
                    
                    seen_paths.add(rel_path_str)
                    stat = file_path.stat()
                    files.append({
                        'name': file_path.name,
                        'path': rel_path_str,
                        'size': stat.st_size,
                        'created_at': _format_pacific_timestamp_from_epoch(stat.st_mtime),
                        'directory': exec_dir.name
                    })
        
        if files:
            logger.info(
                f"📂 Found {len(files)} files across "
                f"{len(set(f['directory'] for f in files))} execution directories"
            )
            return files
        
        # Strategy 2: Scan flat outputs/ directory (legacy)
        for outputs_base in _all_output_paths():
            for file_path in outputs_base.glob('*'):
                if not file_path.is_file():
                    continue
                
                rel_path = file_path.relative_to(outputs_base)
                rel_path_str = str(rel_path)
                if rel_path_str in seen_paths:
                    continue
                
                seen_paths.add(rel_path_str)
                stat = file_path.stat()
                files.append({
                    'name': file_path.name,
                    'path': rel_path_str,
                    'size': stat.st_size,
                    'created_at': _format_pacific_timestamp_from_epoch(stat.st_mtime),
                    'directory': 'root'
                })
        
        logger.info(f"📂 Found {len(files)} total output files (legacy scan)")
        return files
    
    @app.post("/execute/start")
    async def start_execution(command: str, args: str, request: Request, token: str = Depends(verify_token)):
        """
        Start a new command execution as a background task (RECOMMENDED FOR PRODUCTION).
        
        **Use this endpoint for:**
        - Multi-agent analysis (voice-of-customer with --multi-agent)
        - Full week/month/quarter analysis with Gamma generation
        - Any task expected to run longer than 5-10 minutes
        - Production workloads where connection stability matters
        
        **Workflow:**
        1. POST to /execute/start to queue the task (returns execution_id immediately)
        2. Poll GET /execute/status/{execution_id} for progress updates
        3. Access results via /execute/output/{execution_id} or download files
        
        **Benefits:**
        - No SSE connection timeout issues
        - Task continues even if client disconnects
        - Queryable status and resumable results
        - Better for mobile/unstable connections
        
        **Note:** Returns immediately with execution_id. Task runs in background.
        """
        # Check rate limit
        await check_rate_limit(request)
        
        if not command_executor or not state_manager:
            raise HTTPException(status_code=500, detail="Execution services not available")
        
        try:
            # Parse and validate args
            args_list = json.loads(args) if args else []
            
            # Validate args is a list
            if not isinstance(args_list, list):
                raise HTTPException(status_code=400, detail="Args must be a JSON array")
            
            # Validate each arg is a string and within reasonable bounds
            for i, arg in enumerate(args_list):
                if not isinstance(arg, str):
                    raise HTTPException(status_code=400, detail=f"Argument {i} must be a string")
                if len(arg) > 1024:  # Match MAX_ARG_LENGTH
                    raise HTTPException(status_code=400, detail=f"Argument {i} exceeds maximum length")
            
            # Generate execution ID
            execution_id = command_executor.generate_execution_id()
            
            # Generate human-readable execution directory name
            exec_dir_name = _generate_execution_directory_name(args_list, execution_id)
            exec_dir_path = _get_execution_base_path() / exec_dir_name
            exec_dir_path.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"📁 Created execution directory: {exec_dir_name}")
            
            # Create execution state (store directory name for later retrieval)
            execution = await state_manager.create_execution(
                execution_id, command, args_list
            )
            
            # Store the execution directory name in execution state
            # (We'll need this later for file discovery)
            if hasattr(execution, 'output_files'):
                execution.output_files = [exec_dir_name]  # Store dir name as first entry
            
            # Start background task (pass execution directory)
            asyncio.create_task(run_command_background(execution_id, command, args_list, str(exec_dir_path)))
            
            return {
                "execution_id": execution_id,
                "status": execution.status.value,
                "queue_position": execution.queue_position,
                "message": "Execution started in background"
            }
        except ValueError as e:
            raise HTTPException(status_code=429, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to start execution: {str(e)}")
    
    @app.post("/execute/cancel/{execution_id}")
    async def cancel_execution(execution_id: str, request: Request, token: str = Depends(verify_token)):
        """Cancel a running or queued execution."""
        # Check rate limit
        await check_rate_limit(request)
        
        if not command_executor or not state_manager:
            raise HTTPException(status_code=500, detail="Execution services not available")
        
        # Cancel in state manager
        cancelled = await state_manager.cancel_execution(execution_id)
        if not cancelled:
            raise HTTPException(status_code=404, detail="Execution not found or already completed")
        
        # Cancel in executor if running
        await command_executor.cancel_execution(execution_id)
        
        return {"message": "Execution cancelled successfully"}
    
    @app.get("/execute/status/{execution_id}")
    async def get_execution_status(execution_id: str, since: int = 0, request: Request = None):
        """
        Get the status and output of an execution.
        
        Args:
            execution_id: The execution ID
            since: Return only output after this index (for polling)
        """
        # Check rate limit if request available
        if request:
            await check_rate_limit(request)
        
        if not state_manager:
            raise HTTPException(status_code=500, detail="State manager not available")
        
        execution = await state_manager.get_execution(execution_id)
        if not execution:
            raise HTTPException(status_code=404, detail="Execution not found")
        
        # Convert deque to list and slice
        try:
            output_list = list(execution.output_buffer) if execution.output_buffer else []
            output_buffer = output_list[since:] if since < len(output_list) else []
        except Exception as e:
            # If conversion fails, return empty list
            output_buffer = []
            output_list = []
        
        # Discover output files for this execution
        files = await _discover_execution_files(execution)
        
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
            "gamma_metadata": execution.gamma_metadata
        }

    @app.get("/execute/list")
    async def list_executions(limit: int = 50, request: Request = None):
        """Get list of recent executions."""
        # Check rate limit if request available
        if request:
            await check_rate_limit(request)
        
        if not state_manager:
            raise HTTPException(status_code=500, detail="State manager not available")
        
        executions = await state_manager.get_all_executions(limit=limit)
        
        # Debug: Check persistence directory
        import os
        from pathlib import Path
        persistence_dir = _primary_outputs_path() / "jobs"
        debug_info = {
            "persistence_dir_exists": persistence_dir.exists(),
            "persistence_dir_path": str(persistence_dir),
            "files_in_dir": [str(f) for f in persistence_dir.glob("*.json")] if persistence_dir.exists() else [],
            "total_executions_in_memory": len(state_manager._executions)
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
                    "output_files": exec.output_files if hasattr(exec, 'output_files') else []
                }
                for exec in executions
            ],
            "debug": debug_info
        }
    
    @app.get("/api/browse-files")
    async def browse_all_files(request: Request = None):
        """
        Browse ALL available output files (no execution ID needed).
        
        Returns all files currently in the outputs directory (volume or container) organized by directory.
        Use this to see what files exist from past runs.
        """
        if request:
            await check_rate_limit(request)
        
        all_files: List[Dict[str, Any]] = []
        seen_paths = set()
        
        # Scan all known output bases so persistent volumes + container agree
        for outputs_base in _all_output_paths():
            executions_base = outputs_base / "executions"
            if not executions_base.exists():
                continue
            
            logger.debug(f"Browsing files from base: {outputs_base}")
            for exec_dir in executions_base.iterdir():
                if not exec_dir.is_dir():
                    continue
                
                for file_path in exec_dir.rglob('*'):
                    if not file_path.is_file():
                        continue
                    
                    rel_path = file_path.relative_to(outputs_base)
                    rel_str = str(rel_path)
                    if rel_str in seen_paths:
                        continue
                    
                    seen_paths.add(rel_str)
                    stat = file_path.stat()
                    all_files.append({
                        'name': file_path.name,
                        'path': rel_str,
                        'size': stat.st_size,
                        'created_at': _format_pacific_timestamp_from_epoch(stat.st_ctime),
                        'modified_at': _format_pacific_timestamp_from_epoch(stat.st_mtime),
                        'created_epoch': stat.st_ctime,  # For sorting
                        'directory': exec_dir.name,
                        'type': file_path.suffix[1:] if file_path.suffix else 'unknown',
                        'base_path': str(outputs_base)
                    })
        
        # Sort all files by creation time (newest first)
        all_files.sort(key=lambda x: x['created_epoch'], reverse=True)
        
        # Group by directory
        by_directory = {}
        for file_info in all_files:
            dir_name = file_info['directory']
            if dir_name not in by_directory:
                by_directory[dir_name] = []
            by_directory[dir_name].append(file_info)
        
        # Sort each directory's files by creation time
        for dir_files in by_directory.values():
            dir_files.sort(key=lambda x: x['created_epoch'], reverse=True)
        
        return {
            'total_files': len(all_files),
            'directories': len(by_directory),
            'files_by_directory': by_directory,
            'all_files': all_files
        }
    
    @app.get("/outputs/{file_path:path}")
    async def serve_output_file(file_path: str, request: Request = None):
        """Serve files from the outputs directory."""
        # Check rate limit if request available
        if request:
            await check_rate_limit(request)
        
        import os
        from pathlib import Path
        
        # Security: Prevent path traversal
        if ".." in file_path or file_path.startswith("/"):
            raise HTTPException(status_code=400, detail="Invalid file path")
        
        # Resolve file relative to any known outputs base
        full_path: Optional[Path] = None
        for base_path in _all_output_paths():
            try:
                candidate = (base_path / file_path).resolve()
                base_resolved = base_path.resolve()
                if not str(candidate).startswith(str(base_resolved)):
                    continue
            except (OSError, ValueError, RuntimeError):
                continue
            
            if candidate.exists() and candidate.is_file():
                full_path = candidate
                break
        
        if not full_path:
            raise HTTPException(status_code=404, detail="File not found")
        
        # Determine content type with UTF-8 encoding
        content_type = "application/octet-stream"
        filename = full_path.name.lower()
        if filename.endswith(".json"):
            content_type = "application/json; charset=utf-8"
        elif filename.endswith(".csv"):
            content_type = "text/csv; charset=utf-8"
        elif filename.endswith(".md"):
            content_type = "text/markdown; charset=utf-8"
        elif filename.endswith(".txt") or filename.endswith(".log"):
            content_type = "text/plain; charset=utf-8"
        
        # Return file
        from fastapi.responses import FileResponse
        return FileResponse(
            path=str(full_path),
            media_type=content_type,
            filename=full_path.name
        )
    
    @app.get("/api/download-zip")
    async def download_outputs_zip(
        execution_id: str = None,
        file_type: str = "all",
        request: Request = None
    ):
        """
        Download output files as a ZIP archive.
        
        Query params:
        - execution_id: Filter by execution ID (optional)
        - file_type: Filter by type ('audit', 'analysis', 'all') [default: all]
        
        Returns a ZIP file containing all matching files with their directory structure preserved.
        """
        # Check rate limit
        if request:
            await check_rate_limit(request)
        
        import zipfile
        import io
        from pathlib import Path
        from fastapi.responses import StreamingResponse
        
        # Create in-memory ZIP
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            file_count = 0
            seen_paths = set()
            
            for outputs_dir in _all_output_paths():
                if not outputs_dir.exists():
                    continue
                
                for file_path in outputs_dir.rglob("*"):
                    if not file_path.is_file():
                        continue
                    
                    relative_path = file_path.relative_to(outputs_dir)
                    rel_str = str(relative_path)
                    
                    # Avoid duplicates
                    if rel_str in seen_paths:
                        continue
                    
                    file_name = file_path.name
                    
                    # Apply filters
                    is_audit = 'audit_trail' in file_name.lower()
                    
                    if file_type == 'audit' and not is_audit:
                        continue
                    if file_type == 'analysis' and is_audit:
                        continue
                    
                    if execution_id and execution_id not in file_name and execution_id not in rel_str:
                        continue
                    
                    # Add to ZIP with directory structure preserved
                    zip_file.write(file_path, arcname=rel_str)
                    seen_paths.add(rel_str)
                    file_count += 1
        
        if file_count == 0:
            raise HTTPException(status_code=404, detail="No files found matching criteria")
        
        # Prepare response
        zip_buffer.seek(0)
        
        # Generate filename
        from src.utils.timezone_utils import get_pacific_time
        timestamp = get_pacific_time().strftime("%Y%m%d_%H%M%S")
        
        if execution_id:
            zip_filename = f"outputs_{execution_id}_{timestamp}.zip"
        else:
            zip_filename = f"outputs_{file_type}_{timestamp}.zip"
        
        return StreamingResponse(
            iter([zip_buffer.getvalue()]),
            media_type="application/zip",
            headers={
                "Content-Disposition": f"attachment; filename={zip_filename}",
                "Content-Length": str(len(zip_buffer.getvalue()))
            }
        )
    
    @app.get("/api/download-folder-zip")
    async def download_folder_zip(
        folder: str,
        request: Request = None
    ):
        """
        Download a specific execution folder as a ZIP archive.
        
        Query params:
        - folder: The folder/directory name to download (required)
        
        Returns a ZIP file containing all files from that specific folder.
        """
        # Check rate limit
        if request:
            await check_rate_limit(request)
        
        import zipfile
        import io
        from pathlib import Path
        from fastapi.responses import StreamingResponse
        
        logger.info(f"Download folder ZIP requested: {folder}")
        
        # Create in-memory ZIP
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            file_count = 0
            
            for outputs_dir in _all_output_paths():
                logger.info(f"Checking outputs path: {outputs_dir}")
                if not outputs_dir.exists():
                    logger.warning(f"Outputs dir does not exist: {outputs_dir}")
                    continue
                
                # Look for the specific folder (could be in executions/ or directly in outputs/)
                target_dirs = [
                    outputs_dir / "executions" / folder,
                    outputs_dir / folder
                ]
                
                for target_dir in target_dirs:
                    logger.info(f"Checking target dir: {target_dir}")
                    if not target_dir.exists() or not target_dir.is_dir():
                        logger.debug(f"Target dir not found or not a directory: {target_dir}")
                        continue
                    
                    logger.info(f"Found target directory: {target_dir}")
                    # Add all files from this directory
                    for file_path in target_dir.rglob("*"):
                        if not file_path.is_file():
                            continue
                        
                        # Get path relative to the target folder (not outputs root)
                        relative_path = file_path.relative_to(target_dir)
                        
                        # Add to ZIP with folder structure
                        zip_file.write(file_path, arcname=str(relative_path))
                        file_count += 1
                        logger.debug(f"Added file to ZIP: {relative_path}")
        
        logger.info(f"ZIP created with {file_count} files")
        
        if file_count == 0:
            raise HTTPException(status_code=404, detail=f"Folder '{folder}' not found or contains no files")
        
        # Prepare response
        zip_buffer.seek(0)
        
        # Generate filename (sanitize folder name for safe filename)
        safe_folder = folder.replace('/', '_').replace('\\', '_')
        zip_filename = f"{safe_folder}.zip"
        
        return StreamingResponse(
            iter([zip_buffer.getvalue()]),
            media_type="application/zip",
            headers={
                "Content-Disposition": f"attachment; filename={zip_filename}",
                "Content-Length": str(len(zip_buffer.getvalue()))
            }
        )
    
    @app.get("/outputs")
    async def list_output_files(
        file_type: str = "all",
        execution_id: str = None,
        limit: int = 100,
        request: Request = None
    ):
        """
        List files in the outputs directory with optional filtering.
        
        Query params:
        - file_type: Filter by type ('audit', 'analysis', 'all') [default: all]
        - execution_id: Filter by execution ID
        - limit: Max files to return [default: 100]
        """
        # Check rate limit if request available
        if request:
            await check_rate_limit(request)
        
        import os
        from pathlib import Path
        
        files = []
        seen_paths = set()
        for outputs_dir in _all_output_paths():
            if not outputs_dir.exists():
                continue
            
            logger.debug(f"Listing output files from path: {outputs_dir}")
            for file_path in outputs_dir.rglob("*"):
                if not file_path.is_file():
                    continue
                
                relative_path = file_path.relative_to(outputs_dir)
                rel_str = str(relative_path)
                if rel_str in seen_paths:
                    continue
                
                file_name = file_path.name
                
                # Determine if this is an audit trail file
                is_audit = 'audit_trail' in file_name.lower()
                
                # Apply type filter
                if file_type == 'audit' and not is_audit:
                    continue
                if file_type == 'analysis' and is_audit:
                    continue
                
                # Apply execution_id filter
                if execution_id and execution_id not in file_name and execution_id not in rel_str:
                    continue
                
                stat = file_path.stat()
                files.append({
                    "name": file_name,
                    "path": rel_str,
                    "size": stat.st_size,
                    "modified": _format_pacific_timestamp_from_epoch(stat.st_mtime),
                    "modified_epoch": stat.st_mtime,  # For sorting
                    "created": _format_pacific_timestamp_from_epoch(stat.st_ctime),
                    "created_epoch": stat.st_ctime,  # For sorting
                    "type": 'audit' if is_audit else 'analysis',
                    "extension": file_path.suffix,
                    "base_path": str(outputs_dir)
                })
                seen_paths.add(rel_str)
        
        # Sort by creation time (newest first) - chronological order
        files.sort(key=lambda x: x["created_epoch"], reverse=True)
        
        # Apply limit
        limited_files = files[:limit]
        
        return {
            "files": limited_files,
            "total": len(files),
            "filtered_count": len(limited_files)
        }
    
    @app.get("/health")
    async def health_check():
        """Health check endpoint for Railway."""
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "chat_interface": chat_interface is not None,
            "command_executor": command_executor is not None,
            "state_manager": state_manager is not None,
            "fastapi": HAS_FASTAPI,
            "chat_deps": HAS_CHAT
        }
    
    @app.get("/debug/version")
    async def get_version():
        """
        Get application version information.
        
        Returns:
            JSON with version, commit, build date, uptime, and environment info
        """
        uptime_seconds = (datetime.now() - app_start_time).total_seconds()
        
        return {
            "version": APP_VERSION,
            "commit": GIT_COMMIT,
            "commit_short": GIT_COMMIT[:8] if GIT_COMMIT != 'unknown' else 'unknown',
            "build_date": BUILD_DATE,
            "uptime_seconds": uptime_seconds,
            "python_version": sys.version,
            "environment": os.getenv('RAILWAY_ENVIRONMENT', 'local'),
            "deployment_id": os.getenv("RAILWAY_DEPLOYMENT_ID", "unknown"),
            "timestamp": datetime.now().isoformat()
        }
    
    @app.get("/api/commands")
    async def get_commands():
        """
        Get canonical command schema.
        
        Returns complete schema for all available commands including:
        - Command structure
        - Allowed flags with types and validation rules
        - Descriptions and estimated durations
        
        This endpoint is public (no authentication required) and fast (< 100ms).
        """
        return JSONResponse(
            content={
                'version': '1.0',
                'commands': CANONICAL_COMMAND_MAPPINGS,
                'generated_at': datetime.now().isoformat()
            },
            headers={
                'Cache-Control': 'public, max-age=300',  # Cache for 5 minutes
                'Content-Type': 'application/json'
            }
        )

    @app.get("/api/filters")
    async def get_filters():
        """Get supported filters."""
        if not chat_interface:
            raise HTTPException(status_code=500, detail="Chat interface not initialized")
        
        try:
            filters = chat_interface.get_supported_filters()
            return {"filters": filters}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/stats")
    async def get_stats():
        """Get performance statistics."""
        if not chat_interface:
            raise HTTPException(status_code=500, detail="Chat interface not initialized")
        
        try:
            stats = chat_interface.get_performance_stats()
            return {"stats": stats}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/api/notify-completion")
    async def notify_completion(
        request: Request,
        execution_id: str = None,
        status: str = None,
        duration_seconds: int = None
    ):
        """
        Send completion notification via Slack webhook (optional).
        
        To enable Slack notifications:
        1. Ask a Slack admin or channel member to create an Incoming Webhook
        2. Set SLACK_WEBHOOK_URL environment variable on Railway
        3. Notifications will be sent automatically when jobs complete
        
        Browser notifications work automatically (no setup needed).
        """
        # Parse JSON body if sent
        try:
            body = await request.json()
            execution_id = body.get('execution_id', execution_id)
            status = body.get('status', status)
            duration_seconds = body.get('duration_seconds', duration_seconds)
        except Exception:
            pass  # Use query params instead
        
        slack_webhook_url = os.getenv('SLACK_WEBHOOK_URL')
        
        if not slack_webhook_url:
            # Slack not configured - return success silently
            return {"message": "Slack webhook not configured (optional)", "notified": False}
        
        try:
            import httpx
            
            minutes = duration_seconds // 60 if duration_seconds else 0
            seconds = duration_seconds % 60 if duration_seconds else 0
            time_str = f"{minutes}m {seconds}s"
            
            # Build Slack message
            if status == 'completed':
                text = f"✅ *Analysis Completed!*\n\nExecution ID: `{execution_id}`\nDuration: {time_str}\n\n<{os.getenv('RAILWAY_PUBLIC_DOMAIN', 'https://agile-exploration-production.up.railway.app')}|View Results>"
                color = "#10b981"  # Green
            else:
                text = f"❌ *Analysis {status.title()}*\n\nExecution ID: `{execution_id}`\nDuration: {time_str}\n\n<{os.getenv('RAILWAY_PUBLIC_DOMAIN', 'https://agile-exploration-production.up.railway.app')}|View Logs>"
                color = "#ef4444"  # Red
            
            # Send to Slack
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    slack_webhook_url,
                    json={
                        "text": text,
                        "attachments": [{
                            "color": color,
                            "fields": [
                                {"title": "Status", "value": status.title(), "short": True},
                                {"title": "Duration", "value": time_str, "short": True}
                            ]
                        }]
                    }
                )
            
            if response.status_code == 200:
                logger.info(f"Slack notification sent for execution {execution_id}")
                return {"message": "Slack notification sent", "notified": True}
            else:
                logger.warning(f"Slack notification failed: {response.status_code}")
                return {"message": "Slack notification failed", "notified": False}
                
        except Exception as e:
            logger.error(f"Failed to send Slack notification: {e}")
            return {"message": f"Slack notification error: {str(e)}", "notified": False}
    
    @app.get("/history", response_class=HTMLResponse)
    async def historical_timeline_redirect():
        """
        Redirect to historical timeline UI.
        
        Note: The historical timeline is served by railway_web.py on a different port.
        In production, this should be configured to redirect to the proper URL.
        For local development, run: python railway_web.py
        """
        # Get the historical service URL from environment or construct it
        historical_url = os.getenv("HISTORICAL_UI_URL", "http://localhost:8000")
        
        # If no environment variable set, provide helpful instructions
        if historical_url == "http://localhost:8000":
            return HTMLResponse(content=f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Historical Analysis - Setup Required</title>
    <link rel="stylesheet" href="/static/styles.css">
</head>
<body>
    <div class="container">
        <h1>📊 Historical Analysis Timeline</h1>
        
        <div style="margin: 30px 0; padding: 20px; background: rgba(245, 158, 11, 0.1); border-radius: 12px; border: 1px solid rgba(245, 158, 11, 0.3);">
            <h3 style="color: #f59e0b; margin-top: 0;">⚠️ Setup Required</h3>
            <p style="color: #d1d5db; line-height: 1.8;">
                The Historical Analysis Timeline UI needs to be started separately or deployed as an additional service.
            </p>
            
            <h4 style="color: #e5e7eb; margin-top: 20px;">For Local Development:</h4>
            <pre style="background: #0a0a0a; padding: 15px; border-radius: 8px; overflow-x: auto;"><code style="color: #10b981;">python railway_web.py</code></pre>
            <p style="color: #9ca3af; font-size: 14px;">Then visit: <a href="http://localhost:8000" style="color: #667eea;">http://localhost:8000</a></p>
            
            <h4 style="color: #e5e7eb; margin-top: 20px;">For Production Deployment:</h4>
            <p style="color: #9ca3af; line-height: 1.8;">
                Set the <code style="background: #1a1a1a; padding: 2px 6px; border-radius: 4px; color: #f59e0b;">HISTORICAL_UI_URL</code> 
                environment variable to point to your deployed historical timeline service URL.
            </p>
            
            <div style="margin-top: 30px;">
                <a href="/" style="padding: 12px 24px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; text-decoration: none; border-radius: 8px; font-weight: 600; display: inline-block;">
                    ← Back to Main Interface
                </a>
            </div>
        </div>
        
        <div style="margin-top: 30px; padding: 20px; background: rgba(16, 185, 129, 0.1); border-radius: 12px; border: 1px solid rgba(16, 185, 129, 0.3);">
            <h3 style="color: #10b981; margin-top: 0;">✨ Features Available in Historical Timeline:</h3>
            <ul style="color: #d1d5db; line-height: 2;">
                <li><strong>Timeline View:</strong> Browse weekly, monthly, and quarterly analysis snapshots</li>
                <li><strong>Visual Indicators:</strong> Reviewed snapshots, current period, future periods</li>
                <li><strong>Review Management:</strong> Mark snapshots as reviewed with notes</li>
                <li><strong>Trend Visualization:</strong> Chart.js charts show topic volume trends</li>
                <li><strong>Comparison View:</strong> Side-by-side comparison of any two periods</li>
                <li><strong>Snapshot Details:</strong> View full analysis reports for any period</li>
            </ul>
        </div>
    </div>
</body>
</html>
            """)
        
        # If environment variable is set, redirect there
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url=historical_url)

def main():
    """Main entrypoint for Railway web server."""
    if not HAS_FASTAPI:
        logger.error("❌ FastAPI not available. Install with: pip install fastapi uvicorn")
        sys.exit(1)
    
    logger.info("🚀 Starting Intercom Analysis Tool Chat Interface...")
    
    # Try to initialize chat interface (but don't fail if it doesn't work)
    logger.info("🔧 Attempting to initialize chat interface...")
    chat_init_success = initialize_chat()
    
    if chat_init_success:
        logger.info("✅ Chat interface initialized successfully")
        
        # Start cleanup scheduler if state manager is available
        logger.info("🔧 Starting cleanup scheduler...")
        scheduler = start_cleanup_scheduler()
        if scheduler:
            logger.info("✅ Cleanup scheduler initialized")
        else:
            logger.warning("⚠️ Cleanup scheduler not started (will rely on manual cleanup)")
    else:
        logger.warning("⚠️ Chat interface initialization failed, but server will start anyway")
        logger.warning("   The health endpoint will still work, but chat features may be limited")
    
    # Get port from Railway environment
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    
    # Get retention configuration
    retention_days = int(os.getenv('AUDIT_RETENTION_DAYS', '14'))
    max_count = int(os.getenv('AUDIT_MAX_COUNT', '50'))
    
    logger.info(f"🌐 Starting web server on {host}:{port}")
    logger.info(f"📊 Health check available at: http://{host}:{port}/health")
    logger.info(f"🔒 Security: Rate limiting enabled (100 requests/min per IP)")
    logger.info(f"🔒 Security: Authentication required for /execute endpoints (set EXECUTION_API_TOKEN)")
    logger.info(f"🔒 Security: Max request size: {MAX_REQUEST_SIZE / 1024 / 1024:.0f}MB")
    logger.info(f"🧹 Retention: {retention_days} days, max {max_count} executions (set AUDIT_RETENTION_DAYS, AUDIT_MAX_COUNT)")
    
    # Start the server
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info"
    )

if __name__ == "__main__":
    main()
