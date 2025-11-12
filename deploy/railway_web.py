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
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
from functools import wraps
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

# Read version information from environment
APP_VERSION = os.getenv('APP_VERSION', 'dev')
GIT_COMMIT = os.getenv('GIT_COMMIT', 'unknown')
BUILD_DATE = os.getenv('BUILD_DATE', datetime.now().isoformat())

# Track application start time for uptime calculation
app_start_time = datetime.now()

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

# Import with absolute paths to avoid relative import issues
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
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
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

CANONICAL_COMMAND_MAPPINGS = {
    'sample_mode': {
        'command': 'python',
        'args': ['src/main.py', 'sample-mode'],
        'display_name': 'Sample Mode (Quick Data Check)',
        'description': 'Pull 25-100 real conversations with ultra-rich logging for schema validation',
        'allowed_flags': {
            '--count': {
                'type': 'integer',
                'default': 50,
                'min': 10,
                'max': 100,
                'description': 'Number of conversations to pull'
            },
            '--time-period': {
                'type': 'enum',
                'values': ['day', 'week', 'month'],
                'default': 'week',
                'description': 'Time period for sampling'
            },
            '--start-date': {
                'type': 'date',
                'description': 'Start date (YYYY-MM-DD)'
            },
            '--end-date': {
                'type': 'date',
                'description': 'End date (YYYY-MM-DD)'
            },
            '--save-to-file': {
                'type': 'boolean',
                'default': False,
                'description': 'Save raw JSON to outputs/'
            },
            '--test-llm': {
                'type': 'boolean',
                'default': False,
                'description': 'Run actual LLM sentiment test on diverse topics'
            },
            '--test-all-agents': {
                'type': 'boolean',
                'default': False,
                'description': 'Test ALL production agents (SubTopic, Example, Fin, Correlation, Quality, Churn, Confidence)'
            },
            '--show-agent-thinking': {
                'type': 'boolean',
                'default': False,
                'description': 'Show agent LLM prompts, responses, and reasoning (for prompt tuning)'
            },
            '--llm-topic-detection': {
                'type': 'boolean',
                'default': False,
                'description': 'Use LLM-first for topic detection (more accurate, costs ~$1 per 200 convs)'
            },
            '--schema-mode': {
                'type': 'enum',
                'values': ['quick', 'standard', 'deep', 'comprehensive'],
                'default': 'quick',
                'description': 'Analysis depth: quick(50/30s), standard(200/2m), deep(500/5m), comprehensive(1000/10m)'
            },
            '--ai-model': {
                'type': 'enum',
                'values': ['openai', 'claude'],
                'default': 'openai',
                'description': 'AI model for LLM sentiment test (if --test-llm enabled)'
            },
            '--include-hierarchy': {
                'type': 'boolean',
                'default': True,
                'description': 'Show/hide topic hierarchy debugging section'
            },
            '--verbose': {
                'type': 'boolean',
                'default': False,
                'description': 'Enable verbose logging'
            }
        },
        'estimated_duration': '30sec-10min (depends on --schema-mode)'
    },
    'voice_of_customer': {
        'command': 'python',
        'args': ['src/main.py', 'voice-of-customer'],
        'display_name': 'Voice of Customer Analysis',
        'description': 'Analyze customer sentiment and feedback trends',
        'allowed_flags': {
            '--time-period': {
                'type': 'enum',
                'values': ['yesterday', 'week', 'month', 'quarter', 'year', '6-weeks'],
                'default': 'week',
                'description': 'Time period for analysis'
            },
            '--periods-back': {
                'type': 'integer',
                'default': 1,
                'min': 1,
                'max': 12,
                'description': 'Number of periods to analyze'
            },
            '--analysis-type': {
                'type': 'enum',
                'values': ['topic-based', 'synthesis', 'complete'],
                'default': 'topic-based',
                'description': 'Analysis format (topic cards, synthesis, or both)'
            },
            '--multi-agent': {
                'type': 'boolean',
                'default': True,
                'description': 'Use multi-agent workflow'
            },
            '--output-dir': {
                'type': 'string',
                'default': 'outputs',
                'description': 'Output directory for files'
            },
            '--test-mode': {
                'type': 'boolean',
                'default': False,
                'description': 'Use test data for faster execution'
            },
            '--test-data-count': {
                'type': 'string',
                'default': '100',
                'description': 'Test data count (tiny, micro, small, medium, large, xlarge, xxlarge, or number)'
            },
            '--audit-trail': {
                'type': 'boolean',
                'default': False,
                'description': 'Generate detailed audit trail'
            },
            '--verbose': {
                'type': 'boolean',
                'default': False,
                'description': 'Enable verbose logging'
            },
            '--llm-topic-detection': {
                'type': 'boolean',
                'default': False,
                'description': 'Use LLM-first for topic detection (more accurate, costs ~$1 per 200 convs)'
            },
            '--ai-model': {
                'type': 'enum',
                'values': ['openai', 'claude'],
                'default': 'openai',
                'description': 'AI model to use (ChatGPT or Claude)'
            },
            '--start-date': {
                'type': 'date',
                'format': 'YYYY-MM-DD',
                'description': 'Start date for custom range'
            },
            '--end-date': {
                'type': 'date',
                'format': 'YYYY-MM-DD',
                'description': 'End date for custom range'
            },
            '--include-canny': {
                'type': 'boolean',
                'default': False,
                'description': 'Include Canny feedback data'
            },
            '--canny-board-id': {
                'type': 'string',
                'description': 'Specific Canny board ID for combined analysis'
            },
            '--enable-fallback': {
                'type': 'boolean',
                'default': True,
                'description': 'Enable fallback to other AI model if primary fails'
            },
            '--include-trends': {
                'type': 'boolean',
                'default': False,
                'description': 'Include historical trend analysis'
            },
            '--generate-gamma': {
                'type': 'boolean',
                'default': False,
                'description': 'Generate Gamma presentation from results'
            },
            '--separate-agent-feedback': {
                'type': 'boolean',
                'default': True,
                'description': 'Separate feedback by agent type (Finn, Boldr, Horatio, etc.)'
            }
        },
        'estimated_duration': '10-30 minutes'
    },
    'agent_performance': {
        'command': 'python',
        'args': ['src/main.py', 'agent-performance'],
        'display_name': 'Agent Performance Analysis',
        'description': 'Analyze individual agent and team performance',
        'allowed_flags': {
            '--agent': {
                'type': 'enum',
                'values': ['horatio', 'boldr', 'escalated'],
                'required': True,
                'description': 'Agent/vendor to analyze'
            },
            '--time-period': {
                'type': 'enum',
                'values': ['week', 'month', '6-weeks', 'quarter'],
                'default': 'week',
                'description': 'Time period for analysis'
            },
            '--periods-back': {
                'type': 'integer',
                'default': 1,
                'min': 1,
                'max': 12,
                'description': 'Number of periods to analyze'
            },
            '--individual-breakdown': {
                'type': 'boolean',
                'default': False,
                'description': 'Include per-agent metrics and taxonomy breakdown'
            },
            '--output-format': {
                'type': 'enum',
                'values': ['markdown', 'json', 'excel', 'gamma'],
                'default': 'markdown',
                'description': 'Output format for results'
            },
            '--gamma-export': {
                'type': 'enum',
                'values': ['pdf', 'pptx'],
                'description': 'Gamma export format (when output-format=gamma)'
            },
            '--output-dir': {
                'type': 'string',
                'default': 'outputs',
                'description': 'Output directory for files'
            },
            '--test-mode': {
                'type': 'boolean',
                'default': False,
                'description': 'Use test data'
            },
            '--test-data-count': {
                'type': 'string',
                'default': '100',
                'description': 'Test data count (tiny, micro, small, medium, large, xlarge, xxlarge, or number)'
            },
            '--audit-trail': {
                'type': 'boolean',
                'default': False,
                'description': 'Generate audit trail'
            },
            '--verbose': {
                'type': 'boolean',
                'default': False,
                'description': 'Enable verbose logging'
            },
            '--ai-model': {
                'type': 'enum',
                'values': ['openai', 'claude'],
                'default': 'openai',
                'description': 'AI model to use (ChatGPT or Claude)'
            },
            '--filter-category': {
                'type': 'string',
                'description': 'Filter by taxonomy category (focus area)'
            },
            '--start-date': {
                'type': 'date',
                'format': 'YYYY-MM-DD',
                'description': 'Start date for custom range'
            },
            '--end-date': {
                'type': 'date',
                'format': 'YYYY-MM-DD',
                'description': 'End date for custom range'
            }
        },
        'estimated_duration': '5-15 minutes'
    },
    'agent_coaching': {
        'command': 'python',
        'args': ['src/main.py', 'agent-coaching-report'],
        'display_name': 'Agent Coaching Report',
        'description': 'Generate coaching priorities and development areas',
        'allowed_flags': {
            '--vendor': {
                'type': 'enum',
                'values': ['horatio', 'boldr'],
                'required': True,
                'description': 'Vendor to analyze'
            },
            '--time-period': {
                'type': 'enum',
                'values': ['week', 'month'],
                'default': 'week',
                'description': 'Time period for analysis'
            },
            '--periods-back': {
                'type': 'integer',
                'default': 1,
                'min': 1,
                'max': 12,
                'description': 'Number of periods to analyze'
            },
            '--filter-category': {
                'type': 'string',
                'description': 'Filter by taxonomy category (e.g., Billing, Bug, API)'
            },
            '--top-n': {
                'type': 'integer',
                'default': 5,
                'min': 1,
                'max': 20,
                'description': 'Number of top issues to highlight'
            },
            '--output-format': {
                'type': 'enum',
                'values': ['markdown', 'json', 'excel', 'gamma'],
                'default': 'markdown',
                'description': 'Output format for results'
            },
            '--gamma-export': {
                'type': 'enum',
                'values': ['pdf', 'pptx'],
                'description': 'Gamma export format (when output-format=gamma)'
            },
            '--output-dir': {
                'type': 'string',
                'default': 'outputs',
                'description': 'Output directory for files'
            },
            '--test-mode': {
                'type': 'boolean',
                'default': False,
                'description': 'Use test data'
            },
            '--test-data-count': {
                'type': 'string',
                'default': '100',
                'description': 'Test data count (tiny, micro, small, medium, large, xlarge, xxlarge, or number)'
            },
            '--audit-trail': {
                'type': 'boolean',
                'default': False,
                'description': 'Generate audit trail'
            },
            '--verbose': {
                'type': 'boolean',
                'default': False,
                'description': 'Enable verbose logging'
            },
            '--ai-model': {
                'type': 'enum',
                'values': ['openai', 'claude'],
                'default': 'openai',
                'description': 'AI model to use (ChatGPT or Claude)'
            },
            '--start-date': {
                'type': 'date',
                'format': 'YYYY-MM-DD',
                'description': 'Start date for custom range'
            },
            '--end-date': {
                'type': 'date',
                'format': 'YYYY-MM-DD',
                'description': 'End date for custom range'
            }
        },
        'estimated_duration': '5-15 minutes'
    },
    'category_billing': {
        'command': 'python',
        'args': ['src/main.py', 'analyze-billing'],
        'display_name': 'Billing Analysis',
        'description': 'Analyze billing, refunds, and subscription issues',
        'allowed_flags': {
            '--time-period': {
                'type': 'enum',
                'values': ['yesterday', 'week', 'month', 'quarter', 'year', '6-weeks'],
                'description': 'Time period for analysis'
            },
            '--periods-back': {
                'type': 'integer',
                'default': 1,
                'description': 'Number of periods to analyze'
            },
            '--output-format': {
                'type': 'enum',
                'values': ['markdown', 'json', 'excel', 'gamma'],
                'default': 'markdown',
                'description': 'Output format for results'
            },
            '--gamma-export': {
                'type': 'enum',
                'values': ['pdf', 'pptx'],
                'description': 'Gamma export format'
            },
            '--output-dir': {
                'type': 'string',
                'default': 'outputs',
                'description': 'Output directory'
            },
            '--test-mode': {
                'type': 'boolean',
                'default': False,
                'description': 'Use test data'
            },
            '--test-data-count': {
                'type': 'string',
                'default': '100',
                'description': 'Test data count or preset'
            },
            '--audit-trail': {
                'type': 'boolean',
                'default': False,
                'description': 'Generate audit trail'
            },
            '--verbose': {
                'type': 'boolean',
                'default': False,
                'description': 'Enable verbose logging'
            },
            '--ai-model': {
                'type': 'enum',
                'values': ['openai', 'claude'],
                'default': 'openai',
                'description': 'AI model to use'
            },
            '--filter-category': {
                'type': 'string',
                'description': 'Filter by taxonomy category'
            },
            '--start-date': {
                'type': 'date',
                'format': 'YYYY-MM-DD',
                'description': 'Start date for analysis'
            },
            '--end-date': {
                'type': 'date',
                'format': 'YYYY-MM-DD',
                'description': 'End date for analysis'
            }
        },
        'estimated_duration': '3-10 minutes'
    },
    'category_product': {
        'command': 'python',
        'args': ['src/main.py', 'analyze-product'],
        'display_name': 'Product Feedback Analysis',
        'description': 'Analyze product questions and feature requests',
        'allowed_flags': {
            '--time-period': {
                'type': 'enum',
                'values': ['yesterday', 'week', 'month', 'quarter', 'year', '6-weeks'],
                'description': 'Time period for analysis'
            },
            '--periods-back': {
                'type': 'integer',
                'default': 1,
                'description': 'Number of periods to analyze'
            },
            '--output-format': {
                'type': 'enum',
                'values': ['markdown', 'json', 'excel', 'gamma'],
                'default': 'markdown',
                'description': 'Output format for results'
            },
            '--gamma-export': {
                'type': 'enum',
                'values': ['pdf', 'pptx'],
                'description': 'Gamma export format'
            },
            '--output-dir': {
                'type': 'string',
                'default': 'outputs',
                'description': 'Output directory'
            },
            '--test-mode': {
                'type': 'boolean',
                'default': False,
                'description': 'Use test data'
            },
            '--test-data-count': {
                'type': 'string',
                'default': '100',
                'description': 'Test data count or preset'
            },
            '--audit-trail': {
                'type': 'boolean',
                'default': False,
                'description': 'Generate audit trail'
            },
            '--verbose': {
                'type': 'boolean',
                'default': False,
                'description': 'Enable verbose logging'
            },
            '--ai-model': {
                'type': 'enum',
                'values': ['openai', 'claude'],
                'default': 'openai',
                'description': 'AI model to use'
            },
            '--filter-category': {
                'type': 'string',
                'description': 'Filter by taxonomy category'
            },
            '--start-date': {
                'type': 'date',
                'format': 'YYYY-MM-DD',
                'description': 'Start date for analysis'
            },
            '--end-date': {
                'type': 'date',
                'format': 'YYYY-MM-DD',
                'description': 'End date for analysis'
            }
        },
        'estimated_duration': '3-10 minutes'
    },
    'category_api': {
        'command': 'python',
        'args': ['src/main.py', 'analyze-api'],
        'display_name': 'API Issues & Integration',
        'description': 'Analyze API and integration problems',
        'allowed_flags': {
            '--time-period': {
                'type': 'enum',
                'values': ['yesterday', 'week', 'month', 'quarter', 'year', '6-weeks'],
                'description': 'Time period for analysis'
            },
            '--periods-back': {
                'type': 'integer',
                'default': 1,
                'description': 'Number of periods to analyze'
            },
            '--output-format': {
                'type': 'enum',
                'values': ['markdown', 'json', 'excel', 'gamma'],
                'default': 'markdown',
                'description': 'Output format for results'
            },
            '--gamma-export': {
                'type': 'enum',
                'values': ['pdf', 'pptx'],
                'description': 'Gamma export format'
            },
            '--output-dir': {
                'type': 'string',
                'default': 'outputs',
                'description': 'Output directory'
            },
            '--test-mode': {
                'type': 'boolean',
                'default': False,
                'description': 'Use test data'
            },
            '--test-data-count': {
                'type': 'string',
                'default': '100',
                'description': 'Test data count or preset'
            },
            '--audit-trail': {
                'type': 'boolean',
                'default': False,
                'description': 'Generate audit trail'
            },
            '--verbose': {
                'type': 'boolean',
                'default': False,
                'description': 'Enable verbose logging'
            },
            '--ai-model': {
                'type': 'enum',
                'values': ['openai', 'claude'],
                'default': 'openai',
                'description': 'AI model to use'
            },
            '--filter-category': {
                'type': 'string',
                'description': 'Filter by taxonomy category'
            },
            '--start-date': {
                'type': 'date',
                'format': 'YYYY-MM-DD',
                'description': 'Start date for analysis'
            },
            '--end-date': {
                'type': 'date',
                'format': 'YYYY-MM-DD',
                'description': 'End date for analysis'
            }
        },
        'estimated_duration': '3-10 minutes'
    },
    'category_escalations': {
        'command': 'python',
        'args': ['src/main.py', 'analyze-escalations'],
        'display_name': 'Escalations Analysis',
        'description': 'Analyze escalation patterns and causes',
        'allowed_flags': {
            '--time-period': {
                'type': 'enum',
                'values': ['yesterday', 'week', 'month', 'quarter', 'year', '6-weeks'],
                'description': 'Time period for analysis'
            },
            '--periods-back': {
                'type': 'integer',
                'default': 1,
                'description': 'Number of periods to analyze'
            },
            '--output-format': {
                'type': 'enum',
                'values': ['markdown', 'json', 'excel', 'gamma'],
                'default': 'markdown',
                'description': 'Output format for results'
            },
            '--gamma-export': {
                'type': 'enum',
                'values': ['pdf', 'pptx'],
                'description': 'Gamma export format'
            },
            '--output-dir': {
                'type': 'string',
                'default': 'outputs',
                'description': 'Output directory'
            },
            '--test-mode': {
                'type': 'boolean',
                'default': False,
                'description': 'Use test data'
            },
            '--test-data-count': {
                'type': 'string',
                'default': '100',
                'description': 'Test data count or preset'
            },
            '--audit-trail': {
                'type': 'boolean',
                'default': False,
                'description': 'Generate audit trail'
            },
            '--verbose': {
                'type': 'boolean',
                'default': False,
                'description': 'Enable verbose logging'
            },
            '--ai-model': {
                'type': 'enum',
                'values': ['openai', 'claude'],
                'default': 'openai',
                'description': 'AI model to use'
            },
            '--filter-category': {
                'type': 'string',
                'description': 'Filter by taxonomy category'
            },
            '--start-date': {
                'type': 'date',
                'format': 'YYYY-MM-DD',
                'description': 'Start date for analysis'
            },
            '--end-date': {
                'type': 'date',
                'format': 'YYYY-MM-DD',
                'description': 'End date for analysis'
            }
        },
        'estimated_duration': '3-10 minutes'
    },
    'tech_troubleshooting': {
        'command': 'python',
        'args': ['src/main.py', 'tech-analysis'],
        'display_name': 'Technical Troubleshooting Analysis',
        'description': 'Analyze technical issues and support patterns',
        'allowed_flags': {
            '--time-period': {
                'type': 'enum',
                'values': ['yesterday', 'week', 'month', 'quarter', 'year', '6-weeks'],
                'description': 'Time period for analysis'
            },
            '--periods-back': {
                'type': 'integer',
                'default': 1,
                'description': 'Number of periods to analyze'
            },
            '--output-format': {
                'type': 'enum',
                'values': ['markdown', 'json', 'excel', 'gamma'],
                'default': 'markdown',
                'description': 'Output format for results'
            },
            '--gamma-export': {
                'type': 'enum',
                'values': ['pdf', 'pptx'],
                'description': 'Gamma export format'
            },
            '--output-dir': {
                'type': 'string',
                'default': 'outputs',
                'description': 'Output directory'
            },
            '--test-mode': {
                'type': 'boolean',
                'default': False,
                'description': 'Use test data'
            },
            '--test-data-count': {
                'type': 'string',
                'default': '100',
                'description': 'Test data count or preset'
            },
            '--audit-trail': {
                'type': 'boolean',
                'default': False,
                'description': 'Generate audit trail'
            },
            '--verbose': {
                'type': 'boolean',
                'default': False,
                'description': 'Enable verbose logging'
            },
            '--ai-model': {
                'type': 'enum',
                'values': ['openai', 'claude'],
                'default': 'openai',
                'description': 'AI model to use'
            },
            '--filter-category': {
                'type': 'string',
                'description': 'Filter by taxonomy category'
            },
            '--start-date': {
                'type': 'date',
                'format': 'YYYY-MM-DD',
                'description': 'Start date for analysis'
            },
            '--end-date': {
                'type': 'date',
                'format': 'YYYY-MM-DD',
                'description': 'End date for analysis'
            }
        },
        'estimated_duration': '5-15 minutes'
    },
    'all_categories': {
        'command': 'python',
        'args': ['src/main.py', 'analyze-all-categories'],
        'display_name': 'All Categories Analysis',
        'description': 'Comprehensive analysis across all categories',
        'allowed_flags': {
            '--time-period': {
                'type': 'enum',
                'values': ['yesterday', 'week', 'month', 'quarter', 'year', '6-weeks'],
                'description': 'Time period for analysis'
            },
            '--periods-back': {
                'type': 'integer',
                'default': 1,
                'description': 'Number of periods to analyze'
            },
            '--output-format': {
                'type': 'enum',
                'values': ['markdown', 'json', 'excel', 'gamma'],
                'default': 'markdown',
                'description': 'Output format for results'
            },
            '--gamma-export': {
                'type': 'enum',
                'values': ['pdf', 'pptx'],
                'description': 'Gamma export format'
            },
            '--output-dir': {
                'type': 'string',
                'default': 'outputs',
                'description': 'Output directory'
            },
            '--test-mode': {
                'type': 'boolean',
                'default': False,
                'description': 'Use test data'
            },
            '--test-data-count': {
                'type': 'string',
                'default': '100',
                'description': 'Test data count or preset'
            },
            '--audit-trail': {
                'type': 'boolean',
                'default': False,
                'description': 'Generate audit trail'
            },
            '--verbose': {
                'type': 'boolean',
                'default': False,
                'description': 'Enable verbose logging'
            },
            '--ai-model': {
                'type': 'enum',
                'values': ['openai', 'claude'],
                'default': 'openai',
                'description': 'AI model to use'
            },
            '--filter-category': {
                'type': 'string',
                'description': 'Filter by taxonomy category'
            },
            '--start-date': {
                'type': 'date',
                'format': 'YYYY-MM-DD',
                'description': 'Start date for analysis'
            },
            '--end-date': {
                'type': 'date',
                'format': 'YYYY-MM-DD',
                'description': 'End date for analysis'
            }
        },
        'estimated_duration': '15-45 minutes'
    },
    'canny_analysis': {
        'command': 'python',
        'args': ['src/main.py', 'canny-analysis'],
        'display_name': 'Canny Feedback Analysis',
        'description': 'Analyze Canny feature requests and voting patterns',
        'allowed_flags': {
            '--start-date': {
                'type': 'date',
                'format': 'YYYY-MM-DD',
                'description': 'Start date for analysis'
            },
            '--end-date': {
                'type': 'date',
                'format': 'YYYY-MM-DD',
                'description': 'End date for analysis'
            },
            '--time-period': {
                'type': 'enum',
                'values': ['week', 'month', 'quarter'],
                'description': 'Time period shortcut (overrides start/end)'
            },
            '--board-id': {
                'type': 'string',
                'description': 'Specific Canny board ID'
            },
            '--ai-model': {
                'type': 'enum',
                'values': ['openai', 'claude'],
                'default': 'openai',
                'description': 'AI model to use'
            },
            '--enable-fallback': {
                'type': 'boolean',
                'default': True,
                'description': 'Enable fallback to other AI model'
            },
            '--include-comments': {
                'type': 'boolean',
                'default': True,
                'description': 'Include post comments in analysis'
            },
            '--include-votes': {
                'type': 'boolean',
                'default': True,
                'description': 'Include voting patterns'
            },
            '--generate-gamma': {
                'type': 'boolean',
                'default': False,
                'description': 'Generate Gamma presentation'
            },
            '--output-format': {
                'type': 'enum',
                'values': ['gamma', 'markdown', 'json', 'excel'],
                'default': 'markdown',
                'description': 'Output format'
            },
            '--test-mode': {
                'type': 'boolean',
                'default': False,
                'description': 'Use test data'
            },
            '--test-data-count': {
                'type': 'string',
                'default': '100',
                'description': 'Test data count or preset'
            },
            '--verbose': {
                'type': 'boolean',
                'default': False,
                'description': 'Enable verbose logging'
            },
            '--audit-trail': {
                'type': 'boolean',
                'default': False,
                'description': 'Enable audit trail'
            },
            '--output-dir': {
                'type': 'string',
                'default': 'outputs',
                'description': 'Output directory'
            }
        },
        'estimated_duration': '5-15 minutes'
    }
}
def validate_command_request(analysis_type: str, flags: Dict[str, Any]) -> tuple[bool, str]:
    """
    Validate command request against canonical schema.
    
    Args:
        analysis_type: The analysis type key (e.g., 'voice_of_customer')
        flags: Dictionary of flag names and values
        
    Returns:
        (is_valid, error_message) - error_message is None if valid
    """
    if analysis_type not in CANONICAL_COMMAND_MAPPINGS:
        return False, f"Unknown analysis type: {analysis_type}"
    
    schema = CANONICAL_COMMAND_MAPPINGS[analysis_type]
    allowed_flags = schema['allowed_flags']
    
    # Check for unknown flags
    for flag_name in flags.keys():
        if flag_name not in allowed_flags:
            return False, f"Unknown flag '{flag_name}' for {analysis_type}"
    
    # Validate flag values
    for flag_name, flag_value in flags.items():
        flag_schema = allowed_flags[flag_name]
        
        if flag_schema['type'] == 'enum':
            if flag_value not in flag_schema['values']:
                return False, f"Invalid value '{flag_value}' for {flag_name}. Must be one of: {flag_schema['values']}"
        
        elif flag_schema['type'] == 'date':
            # Validate date format
            try:
                from datetime import datetime
                datetime.strptime(flag_value, '%Y-%m-%d')
            except ValueError:
                return False, f"Invalid date format for {flag_name}. Expected YYYY-MM-DD"
        
        elif flag_schema['type'] == 'integer':
            try:
                val = int(flag_value)
                if 'min' in flag_schema and val < flag_schema['min']:
                    return False, f"Value for {flag_name} must be at least {flag_schema['min']}"
                if 'max' in flag_schema and val > flag_schema['max']:
                    return False, f"Value for {flag_name} must be at most {flag_schema['max']}"
            except (ValueError, TypeError):
                return False, f"Invalid integer value for {flag_name}"
        
        elif flag_schema['type'] == 'boolean':
            if not isinstance(flag_value, bool):
                return False, f"Flag {flag_name} must be a boolean"
    
    # Check required flags
    for flag_name, flag_schema in allowed_flags.items():
        if flag_schema.get('required', False) and flag_name not in flags:
            return False, f"Missing required flag: {flag_name}"
    
    return True, None


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
        state_manager = ExecutionStateManager(max_concurrent=5, max_queue_size=20)
        logger.info("✅ State manager initialized successfully")
        
        return True
    except Exception as e:
        logger.error(f"❌ Failed to initialize chat interface: {e}", exc_info=True)
        return False

if HAS_FASTAPI:
    @app.get("/", response_class=HTMLResponse)
    async def root():
        """Serve the chat interface HTML."""
        # Calculate cache-busting hash from version + commit
        cache_bust = f"{APP_VERSION}-{GIT_COMMIT[:8] if GIT_COMMIT != 'unknown' else 'unknown'}"
        
        html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Intercom Analysis Tool v{APP_VERSION}</title>
        <script src="https://cdn.jsdelivr.net/npm/ansi_up@5.2.1/ansi_up.min.js"></script>
        <link rel="stylesheet" href="/static/styles.css?v={cache_bust}">
    </head>
    <body>
        <div class="container">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                <h1 style="margin: 0;">🤖 Intercom Analysis Tool - Chat Interface</h1>
                <a href="/history" style="padding: 10px 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; text-decoration: none; border-radius: 8px; font-weight: 600; box-shadow: 0 4px 6px rgba(0,0,0,0.3); transition: transform 0.2s, box-shadow 0.2s;" onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 6px 12px rgba(0,0,0,0.4)';" onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 4px 6px rgba(0,0,0,0.3)';">
                    📊 View Historical Analysis
                </a>
            </div>
            
            <!-- Active Job Banner (hidden by default, shown by resumeActiveExecution) -->
            <div id="activeJobBanner" style="display: none; margin-bottom: 20px; padding: 15px 20px; background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%); border-radius: 12px; border: 2px solid #fbbf24; box-shadow: 0 4px 12px rgba(245, 158, 11, 0.3);">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <div style="font-weight: 700; font-size: 16px; color: #fff; margin-bottom: 5px;">
                            ⚡ Active Job Running
                        </div>
                        <div id="activeJobInfo" style="font-size: 13px; color: #fef3c7;"></div>
                    </div>
                    <button onclick="resumeFromBanner()" style="padding: 10px 20px; background: #fff; color: #d97706; border: none; border-radius: 6px; font-weight: 600; cursor: pointer; box-shadow: 0 2px 4px rgba(0,0,0,0.2); transition: all 0.2s;" onmouseover="this.style.transform='scale(1.05)'" onmouseout="this.style.transform='scale(1)'">
                        👁️ View Progress
                    </button>
                </div>
            </div>
            
            <!-- Simple Dropdown Form -->
            <div class="analysis-form">
                <h2>Configure Analysis</h2>
                
                <label>Analysis Type:</label>
                <select id="analysisType" onchange="updateAnalysisOptions()">
                    <!-- Quick Diagnostic Tools - Always at Top -->
                    <option value="sample-mode">🔬 Sample Mode / Schema Validation (Quick Debug + Data Structure Analysis)</option>
                    <option disabled>──────────────────────────</option>
                    
                    <optgroup label="Voice of Customer">
                        <option value="voice-of-customer-hilary" selected>VoC: Hilary Format (Topic Cards)</option>
                        <option value="voice-of-customer-synthesis">VoC: Synthesis (Cross-cutting Insights)</option>
                        <option value="voice-of-customer-complete">VoC: Complete (Both Formats)</option>
                    </optgroup>
                    <optgroup label="Category Deep Dives">
                        <option value="analyze-billing">Billing Analysis</option>
                        <option value="analyze-product">Product Feedback</option>
                        <option value="analyze-api">API Issues & Integration</option>
                        <option value="analyze-escalations">Escalations</option>
                        <option value="tech-analysis">Technical Troubleshooting</option>
                    </optgroup>
                    <optgroup label="Combined Analysis">
                        <option value="analyze-all-categories">All Categories</option>
                    </optgroup>
                    <optgroup label="Agent Performance - Team Overview">
                        <option value="agent-performance-horatio-team">Horatio: Team Metrics</option>
                        <option value="agent-performance-boldr-team">Boldr: Team Metrics</option>
                        <option value="agent-performance-escalated">Escalated/Senior Staff Analysis</option>
                    </optgroup>
                    <optgroup label="Agent Performance - Individual Breakdown">
                        <option value="agent-performance-horatio-individual">Horatio: Individual Agents + Taxonomy</option>
                        <option value="agent-performance-boldr-individual">Boldr: Individual Agents + Taxonomy</option>
                    </optgroup>
                    <optgroup label="Agent Coaching Reports">
                        <option value="agent-coaching-horatio">Horatio: Coaching & Development</option>
                        <option value="agent-coaching-boldr">Boldr: Coaching & Development</option>
                    </optgroup>
                    <optgroup label="Other Sources">
                        <option value="canny-analysis">Canny Feedback</option>
                    </optgroup>
                </select>
                
                <!-- Info Panel for Individual Breakdown -->
                <div id="individualBreakdownInfo" style="display:none; margin-top: 15px; padding: 15px; background: rgba(59, 130, 246, 0.1); border-radius: 8px; border: 1px solid rgba(59, 130, 246, 0.3);">
                    <div style="font-size: 12px; color: #3b82f6;">
                        <strong>📊 Individual Agent Breakdown Includes:</strong>
                        <ul style="margin: 8px 0; padding-left: 20px; line-height: 1.6;">
                            <li>Per-agent FCR, escalation, and response time metrics</li>
                            <li>Performance breakdown by taxonomy categories (Billing, Bug, API, etc.)</li>
                            <li>Performance breakdown by subcategories (Billing>Refund, Bug>Export, etc.)</li>
                            <li>Strong and weak areas for each agent</li>
                            <li>Agent rankings and comparisons</li>
                            <li>Example conversations (best and needs-coaching)</li>
                        </ul>
                    </div>
                </div>
                
                <!-- Info Panel for Coaching Reports -->
                <div id="coachingReportInfo" style="display:none; margin-top: 15px; padding: 15px; background: rgba(245, 158, 11, 0.1); border-radius: 8px; border: 1px solid rgba(245, 158, 11, 0.3);">
                    <div style="font-size: 12px; color: #f59e0b;">
                        <strong>🎯 Coaching Report Includes:</strong>
                        <ul style="margin: 8px 0; padding-left: 20px; line-height: 1.6;">
                            <li>Coaching priority (high/medium/low) for each agent</li>
                            <li>Specific coaching focus areas (weak categories/subcategories)</li>
                            <li>Praise-worthy achievements to recognize</li>
                            <li>Top and bottom performers identification</li>
                            <li>Example conversations for coaching sessions</li>
                            <li>Team-wide coaching needs and training recommendations</li>
                        </ul>
                    </div>
                </div>
                
                <!-- Info Panel for Team Overview -->
                <div id="teamOverviewInfo" style="display:none; margin-top: 15px; padding: 15px; background: rgba(16, 185, 129, 0.1); border-radius: 8px; border: 1px solid rgba(16, 185, 129, 0.3);">
                    <div style="font-size: 12px; color: #10b981;">
                        <strong>📈 Team Performance Overview Includes:</strong>
                        <ul style="margin: 8px 0; padding-left: 20px; line-height: 1.6;">
                            <li>Aggregated team FCR and escalation rates</li>
                            <li>Overall team strengths and weaknesses</li>
                            <li>Top categories handled</li>
                            <li>Team highlights and lowlights</li>
                            <li>No individual agent breakdown (use Individual Breakdown for that)</li>
                        </ul>
                    </div>
                </div>
                
                <label id="timePeriodLabel">Time Period:</label>
                <select id="timePeriod">
                    <option value="yesterday">Yesterday (fast - ~1k conversations)</option>
                    <option value="week" selected>Last Week (~7k conversations)</option>
                    <option value="month">Last Month (full analysis)</option>
                    <option value="custom">Custom Date Range...</option>
                </select>
                
                <!-- Sample Mode specific options (hidden by default) -->
                <div id="sampleModeOptions" style="display:none; background: rgba(16, 185, 129, 0.1); padding: 15px; border-radius: 8px; margin-top: 15px; border: 1px solid rgba(16, 185, 129, 0.3);">
                    <div style="margin-bottom: 10px; color: #10b981; font-weight: bold;">
                        🔬 Sample Mode: Schema Validation & Quick Debug
                    </div>
                    <p style="margin: 10px 0; font-size: 14px; color: #d1d5db;">
                        Pulls <strong>real conversations</strong> with ultra-rich logging. Shows exactly what fields 
                        Intercom populates and debugs topic detection issues.
                    </p>
                    
                    <label style="color: #e5e7eb; font-size: 14px; margin-top: 10px; display: block;">Analysis Depth:</label>
                    <select id="schemaMode" style="margin-bottom: 15px; padding: 8px; background: #1a1a1a; border: 1px solid #3a3a3a; border-radius: 4px; color: #e5e7eb; width: 100%;">
                        <option value="quick">⚡ Quick - 50 tickets, 5 samples, 2 LLM tests (~30 sec)</option>
                        <option value="standard" selected>📊 Standard - 200 tickets, 10 samples, 3 LLM tests (~2 min)</option>
                        <option value="deep">🔍 Deep - 500 tickets, 15 samples, 5 LLM tests (~5 min)</option>
                        <option value="comprehensive">🎯 Comprehensive - 1000 tickets, 20 samples, 7 LLM tests (~10 min)</option>
                    </select>
                    
                    <label style="color: #e5e7eb; font-size: 14px; display: block;">Time Period:</label>
                    <select id="sampleTimePeriod" style="margin-bottom: 15px; padding: 8px; background: #1a1a1a; border: 1px solid #3a3a3a; border-radius: 4px; color: #e5e7eb; width: 100%;">
                        <option value="day">Last 24 Hours</option>
                        <option value="week" selected>Last Week ⭐</option>
                        <option value="month">Last Month</option>
                    </select>
                    
                    <div style="margin-bottom: 15px;">
                        <label style="display: flex; align-items: center; cursor: pointer; color: #e5e7eb; font-size: 14px;">
                            <input type="checkbox" id="includeHierarchy" checked style="margin-right: 8px; cursor: pointer;">
                            <span>Show Topic Hierarchy Debug Section</span>
                        </label>
                        <p style="margin: 5px 0 0 24px; font-size: 12px; color: #9ca3af;">
                            Displays topic detection and hierarchy structure debugging information
                        </p>
                    </div>
                    
                    <div style="margin-bottom: 15px;">
                        <label style="display: flex; align-items: center; cursor: pointer; color: #e5e7eb; font-size: 14px;">
                            <input type="checkbox" id="testAllAgents" style="margin-right: 8px; cursor: pointer;">
                            <span>🧪 Test ALL Production Agents</span>
                        </label>
                        <p style="margin: 5px 0 0 24px; font-size: 12px; color: #9ca3af;">
                            Tests 7 agents: SubTopic, Example, Fin, Correlation, Quality, Churn, Confidence (+30s runtime)
                        </p>
                    </div>
                    
                    <div style="margin-bottom: 15px;">
                        <label style="display: flex; align-items: center; cursor: pointer; color: #e5e7eb; font-size: 14px;">
                            <input type="checkbox" id="showAgentThinking" style="margin-right: 8px; cursor: pointer;">
                            <span>🧠 Show Agent Thinking</span>
                        </label>
                        <p style="margin: 5px 0 0 24px; font-size: 12px; color: #9ca3af;">
                            Shows LLM prompts, responses, and agent reasoning - perfect for prompt tuning (+1 min runtime)
                        </p>
                    </div>
                    
                    <div style="margin-bottom: 15px;">
                        <label style="display: flex; align-items: center; cursor: pointer; color: #e5e7eb; font-size: 14px;">
                            <input type="checkbox" id="llmTopicDetection" style="margin-right: 8px; cursor: pointer;">
                            <span>🤖 LLM-First Topic Detection</span>
                        </label>
                        <p style="margin: 5px 0 0 24px; font-size: 12px; color: #9ca3af;">
                            Uses LLM to classify every conversation (more accurate for edge cases, costs ~$1 per 200 convs)
                        </p>
                    </div>
                    
                    <div style="margin-top: 10px; padding: 10px; background: rgba(16, 185, 129, 0.15); border-left: 4px solid #10b981; font-size: 13px; color: #e5e7eb;">
                        <strong style="color: #10b981;">💡 What You'll See:</strong>
                        <ul style="margin: 5px 0 0 20px; padding: 0; color: #d1d5db;">
                            <li><strong>Field Coverage:</strong> % of tickets with custom_attributes, tags, "Reason for contact"</li>
                            <li><strong>Tag Analysis:</strong> What custom tags exist and how often they're used</li>
                            <li><strong>Attribute Breakdown:</strong> All custom_attributes keys and sample values</li>
                            <li><strong>Topic Hierarchy:</strong> How conversations are assigned to categories (toggleable)</li>
                            <li><strong>Full Samples:</strong> Raw schema of real conversations with all fields</li>
                            <li><strong>LLM Sentiment Test:</strong> Actual sentiment generated by agents</li>
                        </ul>
                    </div>
                    <div style="margin-top: 10px; font-size: 12px; color: #9ca3af;">
                        <strong>Output:</strong> Terminal + JSON + Complete .log file (download from Files tab)
                    </div>
                </div>
                
                <div id="customDateInputs" style="display:none; margin-top: 10px;">
                    <label>Start Date: <input type="date" id="startDate"></label>
                    <label>End Date: <input type="date" id="endDate"></label>
                </div>
                
                <label>Data Source:</label>
                <select id="dataSource">
                    <option value="intercom" selected>Intercom Only</option>
                    <option value="canny">Canny Only</option>
                    <option value="both">Both Sources</option>
                </select>
                
                <label>Filter by Taxonomy (optional):</label>
                <select id="taxonomyFilter">
                    <option value="" selected>All Categories</option>
                    <option value="Billing">Billing</option>
                    <option value="Bug">Bug Reports</option>
                    <option value="Product Question">Product Questions</option>
                    <option value="Account">Account Issues</option>
                    <option value="Feedback">Feature Requests</option>
                    <option value="Agent/Buddy">Agent/Buddy Issues</option>
                    <option value="Workspace">Workspace/Team</option>
                    <option value="Privacy">Privacy/Security</option>
                    <option value="Chargeback">Chargebacks</option>
                    <option value="Partnerships">Partnerships</option>
                    <option value="Promotions">Promotions</option>
                    <option value="Abuse">Abuse Reports</option>
                    <option value="Unknown">Unclassified</option>
                </select>
                
                <label>Output Format:</label>
                <select id="outputFormat">
                    <option value="markdown" selected>Markdown Report</option>
                    <option value="gamma">Gamma Presentation</option>
                </select>
                
                <label>AI Model:</label>
                <select id="aiModel">
                    <option value="openai" selected>ChatGPT (GPT-4o) - Faster, Good Quality</option>
                    <option value="claude">Claude (Sonnet 3.5) - Slower, Higher Quality</option>
                </select>
                
                <!-- Test Mode Options -->
                <div style="margin-top: 20px; padding: 15px; background: rgba(245, 158, 11, 0.1); border-radius: 8px; border: 1px solid rgba(245, 158, 11, 0.3);">
                    <label style="display: flex; align-items: center; cursor: pointer;">
                        <input type="checkbox" id="testMode" style="margin-right: 10px; width: 18px; height: 18px; cursor: pointer;">
                        <span style="font-weight: 600; color: #f59e0b;">🧪 Test Mode (Use Mock Data)</span>
                    </label>
                    <div id="testModeOptions" style="display: none; margin-top: 12px; padding-left: 28px;">
                        <label style="display: block; margin-bottom: 8px; font-size: 13px;">
                            Test Data Volume:
                            <select id="testDataCount" style="margin-left: 8px; padding: 4px; background: #1a1a1a; border: 1px solid #3a3a3a; border-radius: 4px; color: #e5e7eb;">
                                <option value="50">50 conversations (quick test)</option>
                                <option value="100" selected>100 conversations (1 hour)</option>
                                <option value="500">500 conversations (few hours)</option>
                                <option value="1000">1,000 conversations (~1 day)</option>
                                <option value="5000">5,000 conversations (~1 week) ⭐</option>
                                <option value="10000">10,000 conversations (2 weeks)</option>
                                <option value="20000">20,000 conversations (1 month)</option>
                            </select>
                        </label>
                        <label style="display: flex; align-items: center; margin-top: 8px; cursor: pointer;">
                            <input type="checkbox" id="verboseLogging" checked style="margin-right: 8px; width: 16px; height: 16px; cursor: pointer;">
                            <span style="font-size: 13px;">Verbose Logging (DEBUG level)</span>
                        </label>
                        <div style="font-size: 11px; color: #f59e0b; margin-top: 10px; line-height: 1.5;">
                            <strong>ℹ️ Test Mode Benefits:</strong><br>
                            • No API calls - runs instantly<br>
                            • Realistic data distribution (tiers, topics, languages)<br>
                            • DEBUG logs show agent decision-making<br>
                            • Perfect for testing changes before production
                        </div>
                    </div>
                </div>
                
                <!-- Audit Trail Mode -->
                <div style="margin-top: 15px; padding: 15px; background: rgba(139, 92, 246, 0.1); border-radius: 8px; border: 1px solid rgba(139, 92, 246, 0.3);">
                    <label style="display: flex; align-items: center; cursor: pointer;">
                        <input type="checkbox" id="auditMode" style="margin-right: 10px; width: 18px; height: 18px; cursor: pointer;">
                        <span style="font-weight: 600; color: #a78bfa;">📋 Audit Trail Mode (Show Your Work)</span>
                    </label>
                    <div style="font-size: 11px; color: #a78bfa; margin-top: 10px; line-height: 1.5;">
                        <strong>ℹ️ Audit Trail Benefits:</strong><br>
                        • Narrates every step of analysis in plain language<br>
                        • Shows all decisions made and why<br>
                        • Documents data quality checks<br>
                        • Generates detailed report for data engineer review<br>
                        • Builds confidence in analysis methodology<br>
                        • Perfect for validation and debugging
                    </div>
                </div>
                
                <!-- LLM-First Topic Detection (VOC only) -->
                <div id="llmTopicDetectionVocContainer" style="margin-top: 15px; padding: 15px; background: rgba(59, 130, 246, 0.1); border-radius: 8px; border: 1px solid rgba(59, 130, 246, 0.3); display: none;">
                    <label style="display: flex; align-items: center; cursor: pointer;">
                        <input type="checkbox" id="llmTopicDetectionVoc" style="margin-right: 10px; width: 18px; height: 18px; cursor: pointer;">
                        <span style="font-weight: 600; color: #3b82f6;">🤖 LLM-First Topic Detection</span>
                    </label>
                    <div style="font-size: 11px; color: #60a5fa; margin-top: 10px; line-height: 1.5;">
                        <strong>ℹ️ Why Use This:</strong><br>
                        • More accurate than keyword matching<br>
                        • Handles nuanced conversations ("credits on invoice" → Credits not Billing)<br>
                        • Not fooled by mis-tagged SDK data<br>
                        • Solves double-counting issues<br>
                        • Cost: ~$1 per 200 conversations<br>
                        • Uses GPT-4o-mini for classification
                    </div>
                </div>
                
                <button onclick="runAnalysis()" class="run-button">▶️ Run Analysis</button>
            </div>
            
            <!-- Old chat input and redundant analysisMode removed -->
            
            <div id="status"></div>
            
            <!-- Terminal output container -->
            <div class="terminal-container" id="terminalContainer">
                <div class="terminal-header">
                    <div class="terminal-title">
                        <span class="spinner" id="executionSpinner" style="display:none;"></span>
                        <span id="terminalTitle">Command Execution</span>
                    </div>
                    <div class="terminal-controls">
                        <span class="status-badge" id="executionStatus" style="display:none;">Running</span>
                        <button class="btn-cancel" id="cancelButton" onclick="cancelExecution()" style="display:none;">Cancel</button>
                    </div>
                </div>
                
                <!-- Tab Navigation -->
                <div class="tab-navigation" id="tabNavigation" style="display: none;">
                    <button class="tab-button active" onclick="switchTab('terminal')" id="terminalTab">Terminal</button>
                    <button class="tab-button" onclick="switchTab('summary')" id="summaryTab">Summary</button>
                    <button class="tab-button" onclick="switchTab('files')" id="filesTab">Files</button>
                    <button class="tab-button" onclick="switchTab('gamma')" id="gammaTab">Gamma</button>
                </div>
                
                <!-- Tab Content -->
                <div class="tab-content">
                    <div class="tab-pane active" id="terminalTabContent">
                        <div class="terminal-output" id="terminalOutput"></div>
                    </div>
                    <div class="tab-pane" id="summaryTabContent">
                        <div id="analysisSummary" class="summary-container">
                            <h3>📊 Analysis Summary</h3>
                            <div class="summary-cards"></div>
                        </div>
                    </div>
                    <div class="tab-pane" id="filesTabContent">
                        <div id="filesList" class="files-container">
                            <h3>📁 Generated Files</h3>
                            <div class="files-list"></div>
                        </div>
                    </div>
                    <div class="tab-pane" id="gammaTabContent">
                        <div id="gammaLinks" class="gamma-container">
                            <h3>📈 Gamma Presentations</h3>
                            <div class="gamma-links"></div>
                        </div>
                    </div>
                </div>
                
                <div id="executionResults" style="padding: 15px; background: #2d2d2d; display: none;">
                    <div id="downloadLinks"></div>
                </div>
            </div>
            
            
            <!-- Recent Jobs -->
            <div id="recentJobs" class="examples" style="display: none;">
                <h3>📋 Recent Jobs</h3>
                <div id="jobsList"></div>
            </div>
            
            <!-- Example queries removed - using simple dropdown form instead -->
        </div>
        
        <!-- Version marker for cache verification -->
        <div id="version-footer" style="position: fixed; bottom: 5px; right: 5px; background: rgba(0,0,0,0.7); color: #0f0; padding: 3px 8px; font-size: 10px; border-radius: 3px; font-family: monospace; z-index: 9999;">
            v{APP_VERSION}-{GIT_COMMIT[:8] if GIT_COMMIT != 'unknown' else 'unknown'}
        </div>

        <script src="/static/app.js?v={cache_bust}"></script>
    </body>
    </html>
        """
        return HTMLResponse(
            content=html_content,
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
    
    async def run_command_background(execution_id: str, command: str, args: list):
        """Run command in background and update state."""
        try:
            await state_manager.start_execution(execution_id)
            await state_manager.update_execution_status(execution_id, ExecutionStatus.RUNNING)
            
            async for output in command_executor.execute_command(command, args, execution_id=execution_id):
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
            
            # Create execution state
            execution = await state_manager.create_execution(
                execution_id, command, args_list
            )
            
            # Start background task
            asyncio.create_task(run_command_background(execution_id, command, args_list))
            
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
            "output_length": len(output_list)
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
        persistence_dir = Path("/app/outputs/jobs")
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
                    "return_code": exec.return_code
                }
                for exec in executions
            ],
            "debug": debug_info
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
        
        # Build full path
        full_path = Path("/app/outputs") / file_path
        
        # Security: Ensure file is within outputs directory
        try:
            full_path = full_path.resolve()
            outputs_dir = Path("/app/outputs").resolve()
            if not str(full_path).startswith(str(outputs_dir)):
                raise HTTPException(status_code=400, detail="Access denied")
        except (OSError, ValueError, RuntimeError) as e:
            raise HTTPException(status_code=400, detail=f"Invalid file path: {e}")
        
        # Check if file exists
        if not full_path.exists() or not full_path.is_file():
            raise HTTPException(status_code=404, detail="File not found")
        
        # Determine content type
        content_type = "application/octet-stream"
        if file_path.endswith(".json"):
            content_type = "application/json"
        elif file_path.endswith(".csv"):
            content_type = "text/csv"
        elif file_path.endswith(".md"):
            content_type = "text/markdown"
        elif file_path.endswith(".txt"):
            content_type = "text/plain"
        
        # Return file
        from fastapi.responses import FileResponse
        return FileResponse(
            path=str(full_path),
            media_type=content_type,
            filename=full_path.name
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
        
        outputs_dir = Path("/app/outputs")
        if not outputs_dir.exists():
            return {"files": [], "total": 0, "filtered_count": 0}
        
        files = []
        for file_path in outputs_dir.rglob("*"):
            if file_path.is_file():
                relative_path = file_path.relative_to(outputs_dir)
                file_name = file_path.name
                
                # Determine if this is an audit trail file
                is_audit = 'audit_trail' in file_name.lower()
                
                # Apply type filter
                if file_type == 'audit' and not is_audit:
                    continue
                if file_type == 'analysis' and is_audit:
                    continue
                
                # Apply execution_id filter
                if execution_id and execution_id not in file_name:
                    continue
                
                files.append({
                    "name": file_name,
                    "path": str(relative_path),
                    "size": file_path.stat().st_size,
                    "modified": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat(),
                    "type": 'audit' if is_audit else 'analysis',
                    "extension": file_path.suffix
                })
        
        # Sort by modification time (newest first)
        files.sort(key=lambda x: x["modified"], reverse=True)
        
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
