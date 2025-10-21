"""
Railway web server for Intercom Analysis Tool Chat Interface.
Provides a web-based chat interface for natural language command translation.
"""

import os
import sys
import json
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

# Silence tokenizers parallelism warning
os.environ.setdefault('TOKENIZERS_PARALLELISM', 'false')

# Verify Python path setup
print(f"🔧 PYTHONPATH: {os.environ.get('PYTHONPATH', 'Not set')}")
print(f"🔧 Current working directory: {os.getcwd()}")
print(f"🔧 Script location: {__file__}")

# Add parent directory to path for imports (since we're in deploy/)
parent_dir = str(Path(__file__).parent.parent)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
    print(f"🔧 Added parent to path: {parent_dir}")

# Test src import
try:
    import src
    print(f"✅ Successfully imported src module")
except ImportError as e:
    print(f"❌ Failed to import src: {e}")
    print(f"🔧 sys.path: {sys.path[:3]}")  # Show first 3 entries

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
    print("✅ Chat dependencies imported successfully")
except ImportError as e:
    HAS_CHAT = False
    print(f"❌ Chat dependencies import failed: {e}")
    print("   This is likely due to missing heavy dependencies (sentence-transformers, faiss-cpu)")
    print("   The web interface will still work, but chat features will be limited")

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
                status_code=403,
                detail="Authentication required. Please provide a valid bearer token."
            )
        
        # Validate the token
        if credentials.credentials != expected_token:
            raise HTTPException(
                status_code=403,
                detail="Invalid authentication credentials"
            )
        
        return credentials.credentials
    
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

def initialize_chat():
    """Initialize the chat interface."""
    global chat_interface, command_executor, state_manager
    if not HAS_CHAT:
        print("❌ Chat interface dependencies not available")
        return False
    
    try:
        print("🔧 Checking environment variables...")
        
        # Check for required environment variables
        required_vars = ["INTERCOM_ACCESS_TOKEN", "OPENAI_API_KEY"]
        missing_vars = []
        
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            print(f"⚠️ Missing required environment variables: {missing_vars}")
            print("   Chat interface will not be available until these are set")
            return False
        
        print("🔧 Initializing settings...")
        settings = Settings()
        print("✅ Settings loaded successfully")
        
        print("🔧 Initializing chat interface...")
        chat_interface = ChatInterface(settings)
        print("✅ Chat interface initialized successfully")
        
        print("🔧 Initializing command executor...")
        command_executor = WebCommandExecutor()
        print("✅ Command executor initialized successfully")
        
        print("🔧 Initializing state manager...")
        state_manager = ExecutionStateManager(max_concurrent=5, max_queue_size=20)
        print("✅ State manager initialized successfully")
        
        return True
    except Exception as e:
        print(f"❌ Failed to initialize chat interface: {e}")
        import traceback
        traceback.print_exc()
        return False

if HAS_FASTAPI:
    @app.get("/", response_class=HTMLResponse)
    async def root():
        """Serve the chat interface HTML."""
        html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Intercom Analysis Tool v3.1.0 [EXTERNAL-JS]</title>
        <script src="https://cdn.jsdelivr.net/npm/ansi_up@5.2.1/ansi_up.min.js"></script>
        <link rel="stylesheet" href="/static/styles.css?v=3.1.0">
    </head>
    <body>
        <div class="container">
            <h1>🤖 Intercom Analysis Tool - Chat Interface</h1>
            
            <div class="chat-container" id="chatContainer">
                <div class="message bot-message">
                    <strong>Bot:</strong> Hello! I can help you generate analysis reports using natural language. Try asking me something like "Give me last week's voice of customer report" or "Show me billing analysis for this month".
                </div>
                <div class="message bot-message" id="statusMessage" style="display: none;">
                    <strong>System:</strong> <span id="statusText"></span>
                </div>
            </div>
            
            <div class="input-container">
                <input type="text" id="queryInput" placeholder="Ask me to generate an analysis report..." onkeypress="handleKeyPress(event)">
                <button onclick="sendMessage()" id="sendButton">Send</button>
            </div>
            
            <div style="margin-bottom: 20px; padding: 12px; background: rgba(102, 126, 234, 0.1); border-radius: 8px; border: 1px solid rgba(102, 126, 234, 0.3);">
                <div style="margin-bottom: 12px;">
                    <label style="display: block; color: #e5e7eb; font-weight: 500; margin-bottom: 8px;">Analysis Mode:</label>
                    <select id="analysisMode" style="width: 100%; padding: 8px; background: #1a1a1a; border: 1px solid #3a3a3a; border-radius: 6px; color: #e5e7eb; font-size: 14px;">
                        <option value="standard">Standard (Single-Agent)</option>
                        <option value="topic-based" selected>🤖 Topic-Based (Hilary's VoC Cards)</option>
                        <option value="synthesis">🧠 Synthesis (Strategic Insights)</option>
                        <option value="complete">🎯 Complete (Topic Cards + Synthesis)</option>
                    </select>
                </div>
                <div style="font-size: 11px; color: #6b7280;">
                    <strong>Topic-Based:</strong> Per-topic sentiment, Paid/Free separation, Fin analysis, Examples<br>
                    <strong>Synthesis:</strong> Cross-category patterns, Strategic recommendations, Operational insights<br>
                    <strong>Complete:</strong> Both formats in one analysis
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
            
            <div class="examples" id="examplesSection">
                <h3>💡 Example Queries</h3>
                <div class="example" onclick="setQuery('Give me last week\\'s voice of customer report')">
                    Give me last week's voice of customer report
                </div>
                <div class="example" onclick="setQuery('Show me billing analysis for this month with Gamma presentation')">
                    Show me billing analysis for this month with Gamma presentation
                </div>
                <div class="example" onclick="setQuery('Analyze Canny feature requests from last week with Gamma presentation')">
                    Analyze Canny feature requests from last week with Gamma presentation
                </div>
                <div class="example" onclick="setQuery('Create a combined Intercom + Canny feedback analysis')">
                    Create a combined Intercom + Canny feedback analysis
                </div>
                <div class="example" onclick="setQuery('Help me understand what commands are available')">
                    Help me understand what commands are available
                </div>
            </div>
        </div>
        
        <!-- Version marker for cache verification -->
        <div style="position: fixed; bottom: 5px; right: 5px; background: rgba(0,0,0,0.7); color: #0f0; padding: 3px 8px; font-size: 10px; border-radius: 3px; font-family: monospace; z-index: 9999;">
            v3.0.2-736b1d4
        </div>

        <script src="/static/app.js?v=3.1.0"></script>
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
        token: str = Depends(verify_token)  # Require authentication
    ):
        """
        Stream command execution output via Server-Sent Events.
        
        Security: This endpoint requires bearer token authentication.
        Set EXECUTION_API_TOKEN environment variable to enable authentication.
        """
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
            """Generate SSE events from command output."""
            try:
                async for output in command_executor.execute_command(
                    command, validated_args, execution_id=execution_id
                ):
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
                    
                    # Yield as SSE event
                    yield {
                        "event": "message",
                        "data": json.dumps(output)
                    }
                
            except asyncio.CancelledError:
                # Client disconnected
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
    async def start_execution(command: str, args: str):
        """Start a new command execution as a background task."""
        if not command_executor or not state_manager:
            raise HTTPException(status_code=500, detail="Execution services not available")
        
        try:
            # Parse args
            args_list = json.loads(args) if args else []
            
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
    async def cancel_execution(execution_id: str):
        """Cancel a running or queued execution."""
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
    async def get_execution_status(execution_id: str, since: int = 0):
        """
        Get the status and output of an execution.
        
        Args:
            execution_id: The execution ID
            since: Return only output after this index (for polling)
        """
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
    async def list_executions(limit: int = 50):
        """Get list of recent executions."""
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
    async def serve_output_file(file_path: str):
        """Serve files from the outputs directory."""
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
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid file path")
        
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
    async def list_output_files():
        """List all files in the outputs directory."""
        import os
        from pathlib import Path
        
        outputs_dir = Path("/app/outputs")
        if not outputs_dir.exists():
            return {"files": []}
        
        files = []
        for file_path in outputs_dir.rglob("*"):
            if file_path.is_file():
                relative_path = file_path.relative_to(outputs_dir)
                files.append({
                    "name": file_path.name,
                    "path": str(relative_path),
                    "size": file_path.stat().st_size,
                    "modified": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat(),
                    "type": file_path.suffix
                })
        
        # Sort by modification time (newest first)
        files.sort(key=lambda x: x["modified"], reverse=True)
        
        return {"files": files}
    
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
        """Debug endpoint to verify which code is deployed."""
        import subprocess
        try:
            # Get actual git commit hash
            git_hash = subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD'], 
                                              cwd='/app', stderr=subprocess.DEVNULL).decode().strip()
        except:
            git_hash = "unknown"
        
        return {
            "version": "3.0.2",
            "commit": git_hash,
            "expected_commit": "736b1d4",
            "timestamp": datetime.now().isoformat(),
            "deployment_id": os.getenv("RAILWAY_DEPLOYMENT_ID", "unknown"),
            "fixes_included": [
                "JavaScript regex syntax error fixed (line 1185)",
                "Cache-control headers added",
                "Version marker added to HTML",
                "Canny imports fixed",
                "Datetime bugs fixed"
            ]
        }
    
    @app.get("/api/commands")
    async def get_commands():
        """Get available commands."""
        if not chat_interface:
            # Fallback: return basic command list when chat is unavailable
            return {
                "commands": [
                    {"name": "voice-of-customer", "description": "Voice of Customer analysis", "example": "voice-of-customer --generate-gamma"},
                    {"name": "billing-analysis", "description": "Billing-specific analysis", "example": "billing-analysis --generate-gamma"},
                    {"name": "tech-analysis", "description": "Technical troubleshooting analysis", "example": "tech-analysis --days 7"},
                    {"name": "api-analysis", "description": "API-related issues analysis", "example": "api-analysis --generate-gamma"},
                    {"name": "product-analysis", "description": "Product questions analysis", "example": "product-analysis --generate-gamma"},
                    {"name": "sites-analysis", "description": "Sites-related issues analysis", "example": "sites-analysis --generate-gamma"},
                    {"name": "canny-analysis", "description": "Canny feedback analysis", "example": "canny-analysis --generate-gamma --start-date 2024-10-01 --end-date 2024-10-31"}
                ]
            }
        
        try:
            commands = chat_interface.get_available_commands()
            return {"commands": commands}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

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
        print("❌ FastAPI not available. Install with: pip install fastapi uvicorn")
        sys.exit(1)
    
    print("🚀 Starting Intercom Analysis Tool Chat Interface...")
    
    # Try to initialize chat interface (but don't fail if it doesn't work)
    print("🔧 Attempting to initialize chat interface...")
    chat_init_success = initialize_chat()
    
    if chat_init_success:
        print("✅ Chat interface initialized successfully")
    else:
        print("⚠️ Chat interface initialization failed, but server will start anyway")
        print("   The health endpoint will still work, but chat features may be limited")
    
    # Get port from Railway environment
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    
    print(f"🌐 Starting web server on {host}:{port}")
    print(f"📊 Health check available at: http://{host}:{port}/health")
    
    # Start the server
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info"
    )

if __name__ == "__main__":
    main()
