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
    app = FastAPI(
        title="Intercom Analysis Tool - Chat Interface",
        description="Natural language interface for generating analysis reports",
        version="1.0.0"
    )
    
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
        <title>Intercom Analysis Tool - Chat Interface v2.0</title>
        <script src="https://cdn.jsdelivr.net/npm/ansi_up@5.2.1/ansi_up.min.js"></script>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                background: #0a0a0a;
                min-height: 100vh;
                color: #e5e7eb;
                padding: 40px 20px;
                line-height: 1.6;
            }
            
            .container {
                max-width: 900px;
                margin: 0 auto;
                background: #111111;
                border-radius: 16px;
                padding: 48px;
                box-shadow: 0 4px 24px rgba(0, 0, 0, 0.4);
                border: 1px solid #222222;
            }
            
            h1 {
                color: #ffffff;
                text-align: center;
                font-size: 28px;
                font-weight: 600;
                margin-bottom: 40px;
                letter-spacing: -0.3px;
            }
            .chat-container {
                border: 1px solid #222222;
                border-radius: 12px;
                height: 450px;
                overflow-y: auto;
                padding: 24px;
                margin-bottom: 24px;
                background: #0a0a0a;
            }
            .chat-container::-webkit-scrollbar {
                width: 8px;
            }
            .chat-container::-webkit-scrollbar-track {
                background: #0a0a0a;
                border-radius: 4px;
            }
            .chat-container::-webkit-scrollbar-thumb {
                background: #333333;
                border-radius: 4px;
            }
            .chat-container::-webkit-scrollbar-thumb:hover {
                background: #444444;
            }
            .message {
                margin-bottom: 16px;
                padding: 14px 18px;
                border-radius: 12px;
                animation: slideIn 0.3s ease-out;
            }
            @keyframes slideIn {
                from {
                    opacity: 0;
                    transform: translateY(10px);
                }
                to {
                    opacity: 1;
                    transform: translateY(0);
                }
            }
            .user-message {
                background: #1a1a1a;
                border: 1px solid #2a2a2a;
                margin-left: 40px;
                color: #ffffff;
            }
            .bot-message {
                background: #151515;
                border: 1px solid #252525;
                margin-right: 40px;
                color: #e5e7eb;
            }
            .bot-message code {
                background: #1a1a1a;
                padding: 3px 8px;
                border-radius: 4px;
                font-family: 'Consolas', 'Monaco', monospace;
                color: #60a5fa;
                border: 1px solid #2a2a2a;
            }
            .input-container {
                display: flex;
                gap: 12px;
                margin-bottom: 24px;
            }
            input[type="text"] {
                flex: 1;
                padding: 14px 18px;
                background: #0a0a0a;
                border: 1px solid #2a2a2a;
                border-radius: 8px;
                font-size: 15px;
                color: #e5e7eb;
                transition: all 0.2s ease;
            }
            input[type="text"]:focus {
                outline: none;
                border-color: #3a3a3a;
                background: #0f0f0f;
            }
            input[type="text"]::placeholder {
                color: #666666;
            }
            button {
                padding: 14px 28px;
                background: #ffffff;
                color: #0a0a0a;
                border: none;
                border-radius: 8px;
                cursor: pointer;
                font-size: 15px;
                font-weight: 600;
                transition: all 0.2s ease;
            }
            button:hover {
                background: #f5f5f5;
                transform: translateY(-1px);
            }
            button:active {
                transform: translateY(0);
            }
            button:disabled {
                background: #333333;
                color: #666666;
                cursor: not-allowed;
                transform: none;
            }
            .status {
                text-align: center;
                margin-top: 20px;
                padding: 12px;
                border-radius: 12px;
                font-weight: 500;
            }
            .status.success {
                background: rgba(16, 185, 129, 0.15);
                color: #10b981;
                border: 1px solid rgba(16, 185, 129, 0.3);
            }
            .status.error {
                background: rgba(239, 68, 68, 0.15);
                color: #ef4444;
                border: 1px solid rgba(239, 68, 68, 0.3);
            }
            .examples {
                margin-top: 32px;
                padding: 24px;
                background: #0a0a0a;
                border-radius: 12px;
                border: 1px solid #222222;
            }
            .examples h3 {
                margin: 0 0 16px 0;
                color: #ffffff;
                font-size: 16px;
                font-weight: 600;
            }
            .example {
                margin: 8px 0;
                padding: 12px 16px;
                background: #151515;
                border-radius: 8px;
                cursor: pointer;
                border: 1px solid #2a2a2a;
                transition: all 0.2s ease;
                color: #e5e7eb;
            }
            .example:hover {
                background: #1a1a1a;
                border-color: #3a3a3a;
            }
            
            /* Terminal and Rich library-inspired styles */
            .terminal-container {
                display: none;
                margin-top: 24px;
                background: #0a0a0a;
                border-radius: 12px;
                overflow: hidden;
                box-shadow: 0 4px 24px rgba(0, 0, 0, 0.4);
                border: 1px solid #222222;
                animation: slideIn 0.3s ease-out;
            }
            .terminal-header {
                background: #151515;
                padding: 14px 20px;
                border-bottom: 1px solid #222222;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            .terminal-title {
                color: #d4d4d4;
                font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
                font-size: 13px;
                font-weight: bold;
            }
            .terminal-controls {
                display: flex;
                gap: 8px;
            }
            .terminal-output {
                background: #0a0a0a;
                color: #e5e7eb;
                font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
                font-size: 13px;
                padding: 20px;
                max-height: 500px;
                overflow-y: auto;
                line-height: 1.7;
                white-space: pre-wrap;
                word-wrap: break-word;
            }
            .terminal-output::-webkit-scrollbar {
                width: 8px;
            }
            .terminal-output::-webkit-scrollbar-track {
                background: #0a0a0a;
            }
            .terminal-output::-webkit-scrollbar-thumb {
                background: #333333;
                border-radius: 4px;
            }
            .terminal-output::-webkit-scrollbar-thumb:hover {
                background: #444444;
            }
            .terminal-line {
                margin: 2px 0;
            }
            .terminal-line.stdout {
                color: #d4d4d4;
            }
            .terminal-line.stderr {
                color: #ef4444;
            }
            .terminal-line.status {
                color: #10b981;
                font-weight: bold;
            }
            .terminal-line.error {
                color: #ef4444;
                font-weight: bold;
            }
            
            /* Progress indicators */
            .progress-container {
                margin: 10px 0;
                padding: 10px;
                background: #2d2d2d;
                border-radius: 6px;
            }
            .progress-bar-wrapper {
                background: #3d3d3d;
                height: 20px;
                border-radius: 10px;
                overflow: hidden;
                margin: 5px 0;
            }
            .progress-bar {
                background: linear-gradient(90deg, #10b981 0%, #059669 100%);
                height: 100%;
                transition: width 0.3s ease;
                display: flex;
                align-items: center;
                justify-content: center;
                color: white;
                font-size: 11px;
                font-weight: bold;
            }
            .spinner {
                display: inline-block;
                width: 16px;
                height: 16px;
                border: 2px solid #3d3d3d;
                border-top-color: #10b981;
                border-radius: 50%;
                animation: spin 0.6s linear infinite;
                margin-right: 8px;
                vertical-align: middle;
            }
            @keyframes spin {
                to { transform: rotate(360deg); }
            }
            
            /* Rich panel styles */
            .panel {
                border: 2px solid #3d3d3d;
                border-radius: 8px;
                margin: 10px 0;
                overflow: hidden;
            }
            .panel-header {
                background: #2d2d2d;
                padding: 8px 12px;
                border-bottom: 1px solid #3d3d3d;
                color: #10b981;
                font-weight: bold;
                font-size: 14px;
            }
            .panel-content {
                padding: 12px;
                background: #1e1e1e;
                color: #d4d4d4;
            }
            .panel.success .panel-header {
                color: #10b981;
                border-left: 4px solid #10b981;
            }
            .panel.error .panel-header {
                color: #ef4444;
                border-left: 4px solid #ef4444;
            }
            .panel.warning .panel-header {
                color: #f59e0b;
                border-left: 4px solid #f59e0b;
            }
            .panel.info .panel-header {
                color: #3b82f6;
                border-left: 4px solid #3b82f6;
            }
            
            /* Execution controls */
            .execution-controls {
                display: flex;
                gap: 10px;
                margin-top: 15px;
                align-items: center;
            }
            .btn-execute {
                background: #ffffff;
                color: #0a0a0a;
                border: none;
                padding: 12px 24px;
                border-radius: 8px;
                cursor: pointer;
                font-weight: 600;
                transition: all 0.2s ease;
                font-size: 14px;
            }
            .btn-execute:hover {
                background: #f5f5f5;
                transform: translateY(-1px);
            }
            .btn-execute:active {
                transform: translateY(0);
            }
            .btn-execute:disabled {
                background: #333333;
                color: #666666;
                cursor: not-allowed;
                transform: none;
            }
            .btn-cancel {
                background: #ef4444;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
                cursor: pointer;
                font-weight: 600;
                transition: all 0.2s;
            }
            .btn-cancel:hover {
                background: #dc2626;
            }
            .btn-download {
                background: #3b82f6;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 6px;
                cursor: pointer;
                font-weight: 600;
                text-decoration: none;
                display: inline-block;
                transition: all 0.2s;
            }
            .btn-download:hover {
                background: #2563eb;
            }
            
            /* Status badges */
            .status-badge {
                display: inline-block;
                padding: 4px 12px;
                border-radius: 12px;
                font-size: 12px;
                font-weight: 600;
                text-transform: uppercase;
            }
            .status-badge.running {
                background: #dbeafe;
                color: #1e40af;
            }
            .status-badge.completed {
                background: #d1fae5;
                color: #065f46;
            }
            .status-badge.failed {
                background: #fee2e2;
                color: #991b1b;
            }
            .status-badge.queued {
                background: #fef3c7;
                color: #92400e;
            }
            
            /* Analysis Summary Styles */
            .summary-container {
                margin-top: 24px;
                background: #0a0a0a;
                border-radius: 12px;
                padding: 20px;
                border: 1px solid #222222;
                animation: slideIn 0.3s ease-out;
            }
            .summary-container h3 {
                color: #d4d4d4;
                margin: 0 0 16px 0;
                font-size: 16px;
                font-weight: 600;
            }
            .summary-cards {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 16px;
            }
            .summary-card {
                background: #151515;
                border-radius: 8px;
                padding: 16px;
                border: 1px solid #333333;
            }
            .card-title {
                color: #9ca3af;
                font-size: 12px;
                font-weight: 500;
                text-transform: uppercase;
                letter-spacing: 0.5px;
                margin-bottom: 8px;
            }
            .card-value {
                color: #d4d4d4;
                font-size: 18px;
                font-weight: 600;
            }
            .download-link {
                color: #60a5fa;
                text-decoration: none;
                display: inline-flex;
                align-items: center;
                gap: 6px;
            }
            .download-link:hover {
                color: #93c5fd;
                text-decoration: underline;
            }
            
            /* Gamma Links Styles */
            .gamma-container {
                margin-top: 24px;
                background: #0a0a0a;
                border-radius: 12px;
                padding: 20px;
                border: 1px solid #222222;
                animation: slideIn 0.3s ease-out;
            }
            .gamma-container h3 {
                color: #d4d4d4;
                margin: 0 0 16px 0;
                font-size: 16px;
                font-weight: 600;
            }
            .gamma-link {
                display: inline-flex;
                align-items: center;
                gap: 12px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                text-decoration: none;
                padding: 16px 24px;
                border-radius: 8px;
                font-weight: 600;
                font-size: 16px;
                transition: all 0.2s ease;
                box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
            }
            .gamma-link:hover {
                transform: translateY(-2px);
                box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
                color: white;
                text-decoration: none;
            }
            .gamma-icon {
                font-size: 20px;
            }
            
            /* Tab Navigation Styles */
            .tab-navigation {
                background: #151515;
                border-bottom: 1px solid #222222;
                display: flex;
                padding: 0;
            }
            .tab-button {
                background: transparent;
                border: none;
                color: #9ca3af;
                padding: 12px 20px;
                cursor: pointer;
                font-size: 14px;
                font-weight: 500;
                border-bottom: 2px solid transparent;
                transition: all 0.2s ease;
            }
            .tab-button:hover {
                color: #d4d4d4;
                background: rgba(255, 255, 255, 0.05);
            }
            .tab-button.active {
                color: #60a5fa;
                border-bottom-color: #60a5fa;
                background: rgba(96, 165, 250, 0.1);
            }
            
            /* Tab Content Styles */
            .tab-content {
                position: relative;
            }
            .tab-pane {
                display: none;
                padding: 20px;
                min-height: 200px;
            }
            .tab-pane.active {
                display: block;
            }
            
            /* Files Container Styles */
            .files-container {
                background: #0a0a0a;
                border-radius: 12px;
                padding: 20px;
                border: 1px solid #222222;
            }
            .files-container h3 {
                color: #d4d4d4;
                margin: 0 0 16px 0;
                font-size: 16px;
                font-weight: 600;
            }
            .files-list {
                display: flex;
                flex-direction: column;
                gap: 12px;
            }
            .file-item {
                background: #151515;
                border-radius: 8px;
                padding: 16px;
                border: 1px solid #333333;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            .file-info {
                display: flex;
                flex-direction: column;
            }
            .file-name {
                color: #d4d4d4;
                font-weight: 600;
                font-size: 14px;
            }
            .file-meta {
                color: #9ca3af;
                font-size: 12px;
                margin-top: 4px;
            }
            .file-download {
                background: #60a5fa;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 6px;
                font-size: 12px;
                font-weight: 500;
                cursor: pointer;
                text-decoration: none;
                transition: background 0.2s ease;
            }
            .file-download:hover {
                background: #3b82f6;
                color: white;
                text-decoration: none;
            }
        </style>
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

        <script>
            // Check system status and load recent jobs on page load
            window.onload = function() {
                checkSystemStatus();
                loadRecentJobs();
            };
            
            async function checkSystemStatus() {
                try {
                    const response = await fetch('/health');
                    const data = await response.json();
                    
                    const statusMessage = document.getElementById('statusMessage');
                    const statusText = document.getElementById('statusText');
                    
                    if (!data.chat_interface) {
                        statusText.innerHTML = '⚠️ Chat interface is not available due to missing dependencies. You can still execute CLI commands directly below.';
                        statusMessage.style.display = 'block';
                        statusMessage.style.background = 'rgba(245, 158, 11, 0.1)';
                        statusMessage.style.border = '1px solid rgba(245, 158, 11, 0.3)';
                        statusMessage.style.color = '#fbbf24';
                        
                        // Show direct CLI input when chat is not available
                        showDirectCLIInput();
                    } else {
                        statusText.innerHTML = '✅ Chat interface is ready! You can start asking questions.';
                        statusMessage.style.display = 'block';
                        statusMessage.style.background = 'rgba(34, 197, 94, 0.1)';
                        statusMessage.style.border = '1px solid rgba(34, 197, 94, 0.3)';
                        statusMessage.style.color = '#ffffff';
                    }
                } catch (error) {
                    console.error('Failed to check system status:', error);
                }
            }
            
            async function loadRecentJobs() {
                try {
                    const response = await fetch('/execute/list?limit=10');
                    const data = await response.json();
                    
                    if (data.executions && data.executions.length > 0) {
                        const recentJobs = document.getElementById('recentJobs');
                        const jobsList = document.getElementById('jobsList');
                        
                        jobsList.innerHTML = data.executions.map(job => `
                            <div class="example" onclick="resumeJob('${job.execution_id}')" style="display: flex; justify-content: space-between; align-items: center;">
                                <div>
                                    <div style="font-weight: 600;">${job.command} ${job.args.slice(0, 3).join(' ')}...</div>
                                    <div style="font-size: 12px; color: #666; margin-top: 4px;">
                                        Started: ${new Date(job.start_time).toLocaleString()}
                                    </div>
                                </div>
                                <span class="status-badge ${job.status}">${job.status}</span>
                            </div>
                        `).join('');
                        
                        recentJobs.style.display = 'block';
                    }
                } catch (error) {
                    console.error('Failed to load recent jobs:', error);
                }
            }
            
            async function resumeJob(executionId) {
                try {
                    currentExecutionId = executionId;
                    
                    // Fetch current status
                    const response = await fetch(`/execute/status/${executionId}`);
                    const data = await response.json();
                    
                    console.log('Resume job data:', data);
                    console.log('Output array:', data.output);
                    console.log('Output length:', data.output_length);
                    
                    // Show terminal
                    const terminalContainer = document.getElementById('terminalContainer');
                    const terminalOutput = document.getElementById('terminalOutput');
                    const terminalTitle = document.getElementById('terminalTitle');
                    const executionStatus = document.getElementById('executionStatus');
                    const executionSpinner = document.getElementById('executionSpinner');
                    const cancelButton = document.getElementById('cancelButton');
                    
                    terminalContainer.style.display = 'block';
                    terminalOutput.innerHTML = '';
                    terminalTitle.textContent = `Job: ${data.command} (ID: ${executionId.substring(0, 8)}...)`;
                    executionStatus.style.display = 'inline-block';
                    executionStatus.className = `status-badge ${data.status}`;
                    executionStatus.textContent = data.status.charAt(0).toUpperCase() + data.status.slice(1);
                    
                    // Display all output
                    outputIndex = 0;
                    if (data.output && data.output.length > 0) {
                        console.log(`Displaying ${data.output.length} output items`);
                        data.output.forEach((outputItem, index) => {
                            console.log(`Output item ${index}:`, outputItem);
                            appendTerminalOutput(outputItem);
                        });
                        outputIndex = data.output_length;
                    } else {
                        console.log('No output available yet');
                        terminalOutput.innerHTML = '<div style="color: #666; padding: 20px;">No output available yet. Job may still be starting...</div>';
                    }
                    
                    // If still running, start polling
                    if (data.status === 'running' || data.status === 'starting' || data.status === 'queued') {
                        executionSpinner.style.display = 'inline-block';
                        cancelButton.style.display = 'inline-block';
                        startPolling();
                    } else if (data.status === 'completed') {
                        showDownloadLinks();
                    }
                } catch (error) {
                    console.error('Resume job error:', error);
                    alert(`Failed to load job: ${error.message}`);
                }
            }
            
            function setQuery(query) {
                document.getElementById('queryInput').value = query;
            }
            
            function showDirectCLIInput() {
                // Hide the chat interface and show direct CLI input
                const chatContainer = document.getElementById('chatContainer');
                const inputContainer = document.querySelector('.input-container');
                const queryInput = document.getElementById('queryInput');
                const sendButton = document.getElementById('sendButton');
                
                // Update the interface for direct CLI commands
                chatContainer.innerHTML = `
                    <div class="message bot-message">
                        <strong>System:</strong> Chat interface is not available, but you can execute CLI commands directly. Try commands like:
                        <br>• <code>voice-of-customer --generate-gamma</code>
                        <br>• <code>billing-analysis --generate-gamma</code>
                        <br>• <code>canny-analysis --generate-gamma --start-date 2024-10-01 --end-date 2024-10-31</code>
                        <br>• <code>tech-analysis --days 7</code>
                        <br>• <code>api-analysis --generate-gamma</code>
                    </div>
                `;
                
                queryInput.placeholder = "Enter CLI command (e.g., voice-of-customer --generate-gamma)";
                sendButton.textContent = "Execute";
                
                // Update the examples section for CLI commands
                const examplesSection = document.getElementById('examplesSection');
                examplesSection.innerHTML = `
                    <h3>💡 Example CLI Commands</h3>
                    <div class="example" onclick="setQuery('voice-of-customer --generate-gamma')">
                        voice-of-customer --generate-gamma
                    </div>
                    <div class="example" onclick="setQuery('billing-analysis --generate-gamma')">
                        billing-analysis --generate-gamma
                    </div>
                    <div class="example" onclick="setQuery('canny-analysis --generate-gamma --start-date 2024-10-01 --end-date 2024-10-31')">
                        canny-analysis --generate-gamma
                    </div>
                    <div class="example" onclick="setQuery('tech-analysis --days 7')">
                        tech-analysis --days 7
                    </div>
                    <div class="example" onclick="setQuery('api-analysis --generate-gamma')">
                        api-analysis --generate-gamma
                    </div>
                `;
                
                // Update the sendMessage function to handle direct CLI commands
                window.sendMessage = async function() {
                    const input = document.getElementById('queryInput');
                    const button = document.getElementById('sendButton');
                    const chatContainer = document.getElementById('chatContainer');
                    
                    const command = input.value.trim();
                    if (!command) return;
                    
                    // Disable input and show loading
                    input.disabled = true;
                    button.disabled = true;
                    button.textContent = 'Executing...';
                    
                    // Add user message
                    addMessage('user', `CLI Command: <code>${command}</code>`);
                    input.value = '';
                    
                    // Parse command and args
                    const parts = command.split(' ');
                    const cmd = parts[0];
                    const args = parts.slice(1);
                    
                    try {
                        // Execute the command directly
                        await executeCommand(cmd, args);
                    } catch (error) {
                        addMessage('bot', `Error: ${error.message}`);
                    } finally {
                        // Re-enable input
                        input.disabled = false;
                        button.disabled = false;
                        button.textContent = 'Execute';
                    }
                };
            }
            
            function handleKeyPress(event) {
                if (event.key === 'Enter') {
                    sendMessage();
                }
            }
            
            let currentExecutionId = null;
            let currentEventSource = null;
            const ansiUp = new AnsiUp();
            
            async function sendMessage() {
                const input = document.getElementById('queryInput');
                const button = document.getElementById('sendButton');
                const chatContainer = document.getElementById('chatContainer');
                const status = document.getElementById('status');
                
                const query = input.value.trim();
                if (!query) return;
                
                // Disable input and show loading
                input.disabled = true;
                button.disabled = true;
                button.textContent = 'Sending...';
                
                // Add user message
                addMessage('user', query);
                input.value = '';
                
                try {
                    const response = await fetch('/chat', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({ query: query })
                    });
                    
                    const data = await response.json();
                    
                    // DEBUG: Log the actual response structure
                    console.log('Full response:', JSON.stringify(data, null, 2));
                    console.log('data.data:', data.data);
                    console.log('data.data.translation:', data.data?.translation);
                    
                    if (data.success) {
                        addMessage('bot', data.message);
                        if (data.data && data.data.translation) {
                            const translation = data.data.translation;
                            console.log('translation object:', translation);
                            console.log('translation.translation:', translation.translation);
                            if (translation.translation) {
                                const cmd = translation.translation;
                                
                                // Show command and explanation
                                const commandText = `${cmd.command} ${cmd.args ? cmd.args.join(' ') : ''}`;
                                addMessage('bot', `Command: <code>${commandText}</code>`);
                                addMessage('bot', `Explanation: ${cmd.explanation}`);
                                
                                // Add execute button
                                const executeButton = document.createElement('div');
                                executeButton.className = 'execution-controls';
                                executeButton.innerHTML = `
                                    <button class="btn-execute" onclick="executeCommand('${cmd.command}', ${JSON.stringify(cmd.args || []).replace(/"/g, '&quot;')})">
                                        Execute Command
                                    </button>
                                `;
                                chatContainer.appendChild(executeButton);
                                chatContainer.scrollTop = chatContainer.scrollHeight;
                            }
                        }
                        showStatus('success', 'Query processed successfully!');
                    } else {
                        addMessage('bot', `Error: ${data.message}`);
                        showStatus('error', 'Query failed');
                    }
                } catch (error) {
                    addMessage('bot', `Error: ${error.message}`);
                    showStatus('error', 'Network error');
                } finally {
                    // Re-enable input
                    input.disabled = false;
                    button.disabled = false;
                    button.textContent = 'Send';
                }
            }
            
            let pollingInterval = null;
            let outputIndex = 0;
            
            async function executeCommand(command, args) {
                try {
                    // Convert CLI command to full python execution
                    // voice-of-customer → python src/main.py voice-of-customer
                    const fullCommand = 'python';
                    const fullArgs = ['src/main.py', command, ...args];
                    
                    // Start execution and get execution ID
                    const startResponse = await fetch(`/execute/start?command=${encodeURIComponent(fullCommand)}&args=${encodeURIComponent(JSON.stringify(fullArgs))}`, {
                        method: 'POST'
                    });
                    
                    const startData = await startResponse.json();
                    currentExecutionId = startData.execution_id;
                    outputIndex = 0;
                    
                    // Show terminal container
                    const terminalContainer = document.getElementById('terminalContainer');
                    const terminalOutput = document.getElementById('terminalOutput');
                    const terminalTitle = document.getElementById('terminalTitle');
                    const executionSpinner = document.getElementById('executionSpinner');
                    const executionStatus = document.getElementById('executionStatus');
                    const cancelButton = document.getElementById('cancelButton');
                    
                    terminalContainer.style.display = 'block';
                    terminalOutput.innerHTML = '';
                    terminalTitle.textContent = `Executing: ${command}`;
                    executionSpinner.style.display = 'inline-block';
                    executionStatus.style.display = 'inline-block';
                    executionStatus.className = 'status-badge running';
                    executionStatus.textContent = 'Running';
                    cancelButton.style.display = 'inline-block';
                    
                    // Start polling for updates
                    startPolling();
                    
                } catch (error) {
                    console.error('Execution error:', error);
                    addMessage('bot', `Failed to start execution: ${error.message}`);
                }
            }
            
            function startPolling() {
                // Poll every 1 second for updates
                pollingInterval = setInterval(async () => {
                    try {
                        const response = await fetch(`/execute/status/${currentExecutionId}?since=${outputIndex}`);
                        const data = await response.json();
                        
                        // Update output
                        if (data.output && data.output.length > 0) {
                            data.output.forEach(outputItem => {
                                appendTerminalOutput(outputItem);
                            });
                            outputIndex = data.output_length;
                        }
                        
                        // Check if execution is complete
                        if (data.status === 'completed' || data.status === 'failed' || data.status === 'error' || data.status === 'cancelled') {
                            stopPolling();
                            
                            const executionSpinner = document.getElementById('executionSpinner');
                            const executionStatus = document.getElementById('executionStatus');
                            const cancelButton = document.getElementById('cancelButton');
                            
                            executionSpinner.style.display = 'none';
                            cancelButton.style.display = 'none';
                            
                            if (data.status === 'completed') {
                                executionStatus.className = 'status-badge completed';
                                executionStatus.textContent = 'Completed';
                                showDownloadLinks();
                                
                                // Show tab navigation
                                const tabNavigation = document.getElementById('tabNavigation');
                                if (tabNavigation) {
                                    tabNavigation.style.display = 'flex';
                                }
                                
                                // Parse and display analysis summary
                                const terminalOutput = document.getElementById('terminalOutput');
                                const fullOutput = terminalOutput.textContent;
                                
                                // Parse Gamma links
                                const gammaUrls = parseGammaLinks(fullOutput);
                                showGammaLinks(gammaUrls);
                                
                                // Parse and show analysis summary
                                const summary = parseAnalysisSummary(fullOutput);
                                showAnalysisSummary(summary);
                                
                            } else {
                                executionStatus.className = 'status-badge failed';
                                executionStatus.textContent = data.status.charAt(0).toUpperCase() + data.status.slice(1);
                            }
                        }
                    } catch (error) {
                        console.error('Polling error:', error);
                        // Continue polling despite errors
                    }
                }, 1000); // Poll every 1 second
            }
            
            function stopPolling() {
                if (pollingInterval) {
                    clearInterval(pollingInterval);
                    pollingInterval = null;
                }
            }
            
            function appendTerminalOutput(data) {
                const terminalOutput = document.getElementById('terminalOutput');
                const executionSpinner = document.getElementById('executionSpinner');
                const executionStatus = document.getElementById('executionStatus');
                const cancelButton = document.getElementById('cancelButton');
                
                // Create line element
                const line = document.createElement('div');
                line.className = `terminal-line ${data.type}`;
                
                // Convert ANSI codes to HTML
                const htmlContent = ansiUp.ansi_to_html(data.data || '');
                line.innerHTML = htmlContent;
                
                terminalOutput.appendChild(line);
                terminalOutput.scrollTop = terminalOutput.scrollHeight;
                
                // Update status based on output type
                if (data.type === 'status') {
                    if (data.data.includes('completed successfully')) {
                        executionSpinner.style.display = 'none';
                        executionStatus.className = 'status-badge completed';
                        executionStatus.textContent = 'Completed';
                        cancelButton.style.display = 'none';
                        
                        // Close SSE connection
                        if (currentEventSource) {
                            currentEventSource.close();
                            currentEventSource = null;
                        }
                        
                        // Show download links
                        showDownloadLinks();
                    }
                } else if (data.type === 'error') {
                    executionSpinner.style.display = 'none';
                    executionStatus.className = 'status-badge failed';
                    executionStatus.textContent = 'Failed';
                    cancelButton.style.display = 'none';
                    
                    if (currentEventSource) {
                        currentEventSource.close();
                        currentEventSource = null;
                    }
                }
            }
            
            async function cancelExecution() {
                if (!currentExecutionId) return;
                
                try {
                    stopPolling();
                    
                    await fetch(`/execute/cancel/${currentExecutionId}`, {
                        method: 'POST'
                    });
                    
                    const executionSpinner = document.getElementById('executionSpinner');
                    const executionStatus = document.getElementById('executionStatus');
                    const cancelButton = document.getElementById('cancelButton');
                    
                    executionSpinner.style.display = 'none';
                    executionStatus.className = 'status-badge';
                    executionStatus.textContent = 'Cancelled';
                    cancelButton.style.display = 'none';
                    
                    appendTerminalOutput({
                        type: 'status',
                        data: 'Execution cancelled by user'
                    });
                } catch (error) {
                    console.error('Cancel error:', error);
                }
            }
            
            function showDownloadLinks() {
                const executionResults = document.getElementById('executionResults');
                const downloadLinks = document.getElementById('downloadLinks');
                
                // TODO: Fetch actual file list from execution results
                // For now, show a generic message
                downloadLinks.innerHTML = `
                    <div class="panel success">
                        <div class="panel-header">✓ Execution Complete</div>
                        <div class="panel-content">
                            <p>Command executed successfully! Generated files are available in the outputs directory.</p>
                            <p>Check the command output above for Gamma presentation URLs and file locations.</p>
                        </div>
                    </div>
                `;
                executionResults.style.display = 'block';
            }
            
            function parseGammaLinks(output) {
                // Look for Gamma URLs in the output
                const gammaRegex = /https:\/\/gamma\.app\/docs\/[a-zA-Z0-9-]+/g;
                const matches = output.match(gammaRegex);
                return matches || [];
            }
            
            function showGammaLinks(gammaUrls) {
                if (gammaUrls.length === 0) return;
                
                const gammaContainer = document.getElementById('gammaLinks');
                if (!gammaContainer) return;
                
                gammaContainer.innerHTML = gammaUrls.map(url => `
                    <a href="${url}" target="_blank" class="gamma-link">
                        <span class="gamma-icon">📊</span>
                        Open Gamma Presentation
                    </a>
                `).join('');
                gammaContainer.style.display = 'block';
            }
            
            function parseAnalysisSummary(output) {
                // Try to extract key metrics from the output
                const summary = {
                    conversations: 0,
                    dateRange: '',
                    topCategories: [],
                    sentiment: '',
                    keyInsights: []
                };
                
                // Extract conversation count
                const convMatch = output.match(/(\d{1,3}(?:,\d{3})*)\s+conversations?/i);
                if (convMatch) {
                    summary.conversations = parseInt(convMatch[1].replace(/,/g, ''));
                }
                
                // Extract date range
                const dateMatch = output.match(/(\d{4}-\d{2}-\d{2})\s+to\s+(\d{4}-\d{2}-\d{2})/);
                if (dateMatch) {
                    summary.dateRange = `${dateMatch[1]} to ${dateMatch[2]}`;
                }
                
                // Extract CSV export path
                const csvMatch = output.match(/CSV Export:\s*([^\n]+)/);
                if (csvMatch) {
                    summary.csvPath = csvMatch[1].trim();
                }
                
                return summary;
            }
            
            function showAnalysisSummary(summary) {
                const summaryContainer = document.getElementById('analysisSummary');
                if (!summaryContainer) return;
                
                let html = '<div class="summary-cards">';
                
                if (summary.conversations > 0) {
                    html += `
                        <div class="summary-card">
                            <div class="card-title">Conversations Analyzed</div>
                            <div class="card-value">${summary.conversations.toLocaleString()}</div>
                        </div>
                    `;
                }
                
                if (summary.dateRange) {
                    html += `
                        <div class="summary-card">
                            <div class="card-title">Date Range</div>
                            <div class="card-value">${summary.dateRange}</div>
                        </div>
                    `;
                }
                
                if (summary.csvPath) {
                    const fileName = summary.csvPath.split('/').pop();
                    html += `
                        <div class="summary-card">
                            <div class="card-title">Data Export</div>
                            <div class="card-value">
                                <a href="/outputs/${summary.csvPath}" download class="download-link">
                                    📄 ${fileName}
                                </a>
                            </div>
                        </div>
                    `;
                }
                
                html += '</div>';
                summaryContainer.innerHTML = html;
                summaryContainer.style.display = 'block';
            }
            
            function switchTab(tabName) {
                // Hide all tab panes
                document.querySelectorAll('.tab-pane').forEach(pane => {
                    pane.classList.remove('active');
                });
                
                // Remove active class from all tab buttons
                document.querySelectorAll('.tab-button').forEach(button => {
                    button.classList.remove('active');
                });
                
                // Show selected tab pane
                const targetPane = document.getElementById(tabName + 'TabContent');
                if (targetPane) {
                    targetPane.classList.add('active');
                }
                
                // Add active class to selected tab button
                const targetButton = document.getElementById(tabName + 'Tab');
                if (targetButton) {
                    targetButton.classList.add('active');
                }
                
                // Load files if switching to files tab
                if (tabName === 'files') {
                    loadFilesList();
                }
            }
            
            async function loadFilesList() {
                try {
                    const response = await fetch('/outputs');
                    const data = await response.json();
                    
                    const filesList = document.querySelector('.files-list');
                    if (!filesList) return;
                    
                    if (data.files && data.files.length > 0) {
                        filesList.innerHTML = data.files.map(file => `
                            <div class="file-item">
                                <div class="file-info">
                                    <div class="file-name">${file.name}</div>
                                    <div class="file-meta">
                                        ${(file.size / 1024).toFixed(1)} KB • 
                                        ${new Date(file.modified).toLocaleDateString()}
                                    </div>
                                </div>
                                <a href="/outputs/${file.path}" download class="file-download">
                                    Download
                                </a>
                            </div>
                        `).join('');
                    } else {
                        filesList.innerHTML = '<div style="color: #9ca3af; text-align: center; padding: 20px;">No files found</div>';
                    }
                } catch (error) {
                    console.error('Error loading files:', error);
                    const filesList = document.querySelector('.files-list');
                    if (filesList) {
                        filesList.innerHTML = '<div style="color: #ef4444; text-align: center; padding: 20px;">Error loading files</div>';
                    }
                }
            }
            
            function addMessage(type, content) {
                const chatContainer = document.getElementById('chatContainer');
                const messageDiv = document.createElement('div');
                messageDiv.className = `message ${type}-message`;
                messageDiv.innerHTML = `<strong>${type === 'user' ? 'You' : 'Bot'}:</strong> ${content}`;
                chatContainer.appendChild(messageDiv);
                chatContainer.scrollTop = chatContainer.scrollHeight;
            }
            
            function showStatus(type, message) {
                const status = document.getElementById('status');
                status.className = `status ${type}`;
                status.textContent = message;
                setTimeout(() => {
                    status.textContent = '';
                    status.className = 'status';
                }, 3000);
            }
        </script>
    </body>
    </html>
        """
        return html_content

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

    @app.get("/api/commands")
    async def get_commands():
        """Get available commands."""
        if not chat_interface:
            raise HTTPException(status_code=500, detail="Chat interface not initialized")
        
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
