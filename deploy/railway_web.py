"""
Railway web server for Intercom Analysis Tool Chat Interface.
Provides a web-based chat interface for natural language command translation.
"""

import os
import sys
import json
import asyncio
import logging
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

# Send keepalive every 15 seconds when no output
SSE_KEEPALIVE_INTERVAL = 15

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
    'voice_of_customer': {
        'command': 'python',
        'args': ['src/main.py', 'voice-of-customer'],
        'display_name': 'Voice of Customer Analysis',
        'description': 'Analyze customer sentiment and feedback trends',
        'allowed_flags': {
            '--time-period': {
                'type': 'enum',
                'values': ['yesterday', 'week', 'month', 'quarter'],
                'default': 'week',
                'description': 'Time period for analysis'
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
            '--generate-gamma': {
                'type': 'boolean',
                'default': False,
                'description': 'Generate Gamma presentation'
            },
            '--test-mode': {
                'type': 'boolean',
                'default': False,
                'description': 'Use test data for faster execution'
            },
            '--test-data-count': {
                'type': 'integer',
                'default': 100,
                'min': 10,
                'max': 25000,
                'description': 'Number of test conversations to generate'
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
            '--focus-areas': {
                'type': 'string',
                'description': 'Filter by taxonomy category'
            },
            '--include-canny': {
                'type': 'boolean',
                'default': False,
                'description': 'Include Canny feedback data'
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
                'values': ['yesterday', 'week', 'month', 'quarter'],
                'default': 'week',
                'description': 'Time period for analysis'
            },
            '--individual-breakdown': {
                'type': 'boolean',
                'default': False,
                'description': 'Include per-agent metrics and taxonomy breakdown'
            },
            '--generate-gamma': {
                'type': 'boolean',
                'default': False,
                'description': 'Generate Gamma presentation'
            },
            '--test-mode': {
                'type': 'boolean',
                'default': False,
                'description': 'Use test data'
            },
            '--test-data-count': {
                'type': 'integer',
                'default': 100,
                'min': 10,
                'max': 25000,
                'description': 'Number of test conversations'
            },
            '--audit-trail': {
                'type': 'boolean',
                'default': False,
                'description': 'Generate audit trail'
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
                'values': ['yesterday', 'week', 'month', 'quarter'],
                'default': 'week',
                'description': 'Time period for analysis'
            },
            '--generate-gamma': {
                'type': 'boolean',
                'default': False,
                'description': 'Generate Gamma presentation'
            },
            '--test-mode': {
                'type': 'boolean',
                'default': False,
                'description': 'Use test data'
            },
            '--test-data-count': {
                'type': 'integer',
                'default': 100,
                'min': 10,
                'max': 25000,
                'description': 'Number of test conversations'
            },
            '--audit-trail': {
                'type': 'boolean',
                'default': False,
                'description': 'Generate audit trail'
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
            '--days': {
                'type': 'integer',
                'default': 7,
                'min': 1,
                'max': 90,
                'description': 'Number of days to analyze'
            },
            '--generate-gamma': {
                'type': 'boolean',
                'default': False,
                'description': 'Generate Gamma presentation'
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
            '--days': {
                'type': 'integer',
                'default': 7,
                'min': 1,
                'max': 90,
                'description': 'Number of days to analyze'
            },
            '--generate-gamma': {
                'type': 'boolean',
                'default': False,
                'description': 'Generate Gamma presentation'
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
            '--days': {
                'type': 'integer',
                'default': 7,
                'min': 1,
                'max': 90,
                'description': 'Number of days to analyze'
            },
            '--generate-gamma': {
                'type': 'boolean',
                'default': False,
                'description': 'Generate Gamma presentation'
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
            '--days': {
                'type': 'integer',
                'default': 7,
                'min': 1,
                'max': 90,
                'description': 'Number of days to analyze'
            },
            '--generate-gamma': {
                'type': 'boolean',
                'default': False,
                'description': 'Generate Gamma presentation'
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
            '--days': {
                'type': 'integer',
                'default': 7,
                'min': 1,
                'max': 90,
                'description': 'Number of days to analyze'
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
            '--days': {
                'type': 'integer',
                'default': 7,
                'min': 1,
                'max': 90,
                'description': 'Number of days to analyze'
            },
            '--generate-gamma': {
                'type': 'boolean',
                'default': False,
                'description': 'Generate Gamma presentation'
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
                'required': True,
                'description': 'Start date for analysis'
            },
            '--end-date': {
                'type': 'date',
                'format': 'YYYY-MM-DD',
                'required': True,
                'description': 'End date for analysis'
            },
            '--generate-gamma': {
                'type': 'boolean',
                'default': False,
                'description': 'Generate Gamma presentation'
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
            <h1>🤖 Intercom Analysis Tool - Chat Interface</h1>
            
            <!-- Simple Dropdown Form -->
            <div class="analysis-form">
                <h2>Configure Analysis</h2>
                
                <label>Analysis Type:</label>
                <select id="analysisType" onchange="updateAnalysisOptions()">
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
                
                <label>Time Period:</label>
                <select id="timePeriod">
                    <option value="yesterday">Yesterday (fast - ~1k conversations)</option>
                    <option value="week" selected>Last Week (~7k conversations)</option>
                    <option value="month">Last Month (full analysis)</option>
                    <option value="custom">Custom Date Range...</option>
                </select>
                
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
                
                <button onclick="runAnalysis()" class="run-button">▶️ Run Analysis</button>
            </div>
            
            <!-- Old chat input removed - use form wizard above -->
            
            <div style="margin-bottom: 20px; padding: 12px; background: rgba(102, 126, 234, 0.1); border-radius: 8px; border: 1px solid rgba(102, 126, 234, 0.3); display:none;">
                <div style="margin-bottom: 12px;">
                    <label style="display: block; color: #e5e7eb; font-weight: 500; margin-bottom: 8px;">🤖 Multi-Agent Analysis Mode:</label>
                    <select id="analysisMode" style="width: 100%; padding: 8px; background: #1a1a1a; border: 1px solid #3a3a3a; border-radius: 6px; color: #e5e7eb; font-size: 14px;">
                        <option value="topic-based" selected>📋 Topic-Based (Hilary's VoC Cards)</option>
                        <option value="synthesis">🧠 Synthesis (Strategic Insights)</option>
                        <option value="complete">🎯 Complete (Both Formats)</option>
                    </select>
                </div>
                <div style="font-size: 11px; color: #6b7280;">
                    <strong>Topic-Based:</strong> Per-topic sentiment cards, Paid/Free separation, Fin analysis, 3-10 examples<br>
                    <strong>Synthesis:</strong> Cross-category patterns, Operational metrics (FCR, resolution time), Strategic recommendations<br>
                    <strong>Complete:</strong> Both Hilary's cards AND synthesis insights (recommended)
                </div>
                <div style="margin-top: 8px; padding: 8px; background: rgba(34, 197, 94, 0.1); border-radius: 4px; font-size: 11px; color: #10b981;">
                    ℹ️ This branch is multi-agent only. For single-agent analysis, use the main branch.
                </div>
            </div>
            
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
        request: Request,
        token: str = Depends(verify_token)
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
        
        **Timeout Handling:**
        If execution exceeds the max duration, the stream will send a timeout
        status and terminate. For very large datasets, consider using --test-mode
        for faster execution or increase MAX_EXECUTION_DURATION.
        
        **Client Disconnect:**
        If client disconnects, background task is automatically cancelled
        and resources are cleaned up.
        
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
        
        # Check execution state
        try:
            execution_state = await state_manager.get_execution(execution_id)
            if not execution_state:
                raise HTTPException(status_code=404, detail="Execution not found")
        except ValueError as e:
            # Domain validation error from state manager
            raise HTTPException(status_code=429, detail=str(e)) from e
        
        # Start the execution
        try:
            started = await state_manager.start_execution(execution_id)
            if not started:
                raise HTTPException(status_code=429, detail="Too many concurrent executions")
        except ValueError as e:
            raise HTTPException(status_code=429, detail=str(e)) from e
        
        async def event_generator():
            """Generate SSE events from command output with timeout, keepalive, and disconnect detection."""
            start_time = time.time()
            last_keepalive = time.time()
            execution_task = None
            
            try:
                # Create async iterator from command executor
                output_iterator = command_executor.execute_command(
                    command, validated_args, execution_id=execution_id
                )
                
                # Process output with timeout and keepalive
                async for output in output_iterator:
                    # Check timeout
                    elapsed = time.time() - start_time
                    if elapsed > MAX_EXECUTION_DURATION:
                        timeout_minutes = MAX_EXECUTION_DURATION / 60
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
                        logger.info(f"Client disconnected for execution {execution_id}")
                        await command_executor.cancel_execution(execution_id)
                        await state_manager.update_execution_status(
                            execution_id, ExecutionStatus.CANCELLED,
                            error_message='Client disconnected'
                        )
                        yield {
                            "event": "message",
                            "data": json.dumps({
                                'type': 'cancelled',
                                'status': 'cancelled',
                                'message': 'Client disconnected',
                                'execution_id': execution_id
                            })
                        }
                        break
                    
                    # Truncate large chunks
                    if output.get("data") and len(output["data"]) > MAX_SSE_CHUNK_SIZE:
                        output["data"] = truncate_chunk(output["data"], MAX_SSE_CHUNK_SIZE)
                        output["truncated"] = True
                    
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
                    
                    # Update last keepalive time when we send output
                    last_keepalive = time.time()
                    
                    # Send keepalive if needed (check between outputs)
                    if time.time() - last_keepalive > SSE_KEEPALIVE_INTERVAL:
                        yield {"event": "comment", "data": "keepalive"}
                        last_keepalive = time.time()
                
            except asyncio.CancelledError:
                # Client disconnected or cancelled
                logger.info(f"Execution {execution_id} cancelled")
                await state_manager.update_execution_status(
                    execution_id, ExecutionStatus.CANCELLED
                )
                await command_executor.cancel_execution(execution_id)
                raise
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
                import logging
                logging.getLogger(__name__).exception(f"Unexpected error in execution {execution_id}")
                await state_manager.update_execution_status(
                    execution_id, ExecutionStatus.ERROR, error_message=str(e)
                )
                yield {
                    "event": "error",
                    "data": json.dumps({"type": "error", "data": "Internal server error during execution"})
                }
            finally:
                # Cleanup
                pass
        
        return EventSourceResponse(event_generator())
    
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
        """Start a new command execution as a background task."""
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
