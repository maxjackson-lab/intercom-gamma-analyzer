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

# Verify Python path setup
print(f"🔧 PYTHONPATH: {os.environ.get('PYTHONPATH', 'Not set')}")
print(f"🔧 Current working directory: {os.getcwd()}")
print(f"🔧 Script location: {__file__}")

# Test src import (should work now that script is in project root)
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
    "python3.9",
    "python3.10",
    "python3.11",
    "python3.12",
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
        <title>Intercom Analysis Tool - Chat Interface</title>
        <script src="https://cdn.jsdelivr.net/npm/ansi_up@5.2.1/ansi_up.min.js"></script>
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
                background-color: #f5f5f5;
            }
            .container {
                background: white;
                border-radius: 12px;
                padding: 30px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            h1 {
                color: #2563eb;
                text-align: center;
                margin-bottom: 30px;
            }
            .chat-container {
                border: 1px solid #e5e7eb;
                border-radius: 8px;
                height: 400px;
                overflow-y: auto;
                padding: 20px;
                margin-bottom: 20px;
                background-color: #fafafa;
            }
            .message {
                margin-bottom: 15px;
                padding: 10px;
                border-radius: 8px;
            }
            .user-message {
                background-color: #dbeafe;
                margin-left: 20px;
            }
            .bot-message {
                background-color: #f3f4f6;
                margin-right: 20px;
            }
            .input-container {
                display: flex;
                gap: 10px;
            }
            input[type="text"] {
                flex: 1;
                padding: 12px;
                border: 1px solid #d1d5db;
                border-radius: 6px;
                font-size: 16px;
            }
            button {
                padding: 12px 24px;
                background-color: #2563eb;
                color: white;
                border: none;
                border-radius: 6px;
                cursor: pointer;
                font-size: 16px;
            }
            button:hover {
                background-color: #1d4ed8;
            }
            button:disabled {
                background-color: #9ca3af;
                cursor: not-allowed;
            }
            .status {
                text-align: center;
                margin-top: 20px;
                padding: 10px;
                border-radius: 6px;
            }
            .status.success {
                background-color: #d1fae5;
                color: #065f46;
            }
            .status.error {
                background-color: #fee2e2;
                color: #991b1b;
            }
            .examples {
                margin-top: 30px;
                padding: 20px;
                background-color: #f8fafc;
                border-radius: 8px;
            }
            .examples h3 {
                margin-top: 0;
                color: #374151;
            }
            .example {
                margin: 10px 0;
                padding: 8px 12px;
                background-color: white;
                border-radius: 4px;
                cursor: pointer;
                border: 1px solid #e5e7eb;
            }
            .example:hover {
                background-color: #f3f4f6;
            }
            
            /* Terminal and Rich library-inspired styles */
            .terminal-container {
                display: none;
                margin-top: 20px;
                background: #1e1e1e;
                border-radius: 8px;
                overflow: hidden;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
            }
            .terminal-header {
                background: #2d2d2d;
                padding: 10px 15px;
                border-bottom: 1px solid #3d3d3d;
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
                background: #1e1e1e;
                color: #d4d4d4;
                font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
                font-size: 13px;
                padding: 15px;
                max-height: 500px;
                overflow-y: auto;
                line-height: 1.6;
                white-space: pre-wrap;
                word-wrap: break-word;
            }
            .terminal-output::-webkit-scrollbar {
                width: 8px;
            }
            .terminal-output::-webkit-scrollbar-track {
                background: #2d2d2d;
            }
            .terminal-output::-webkit-scrollbar-thumb {
                background: #4d4d4d;
                border-radius: 4px;
            }
            .terminal-output::-webkit-scrollbar-thumb:hover {
                background: #5d5d5d;
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
                background: linear-gradient(135deg, #10b981 0%, #059669 100%);
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
                cursor: pointer;
                font-weight: 600;
                transition: all 0.2s;
            }
            .btn-execute:hover {
                transform: translateY(-1px);
                box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
            }
            .btn-execute:disabled {
                background: #6b7280;
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
            
            /* Gamma URL display styles */
            .gamma-panel {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                border-radius: 12px;
                padding: 20px;
                margin: 20px 0;
                color: white;
                box-shadow: 0 4px 20px rgba(102, 126, 234, 0.4);
                display: none;
            }
            .gamma-panel h3 {
                margin: 0 0 15px 0;
                font-size: 20px;
                display: flex;
                align-items: center;
                gap: 10px;
            }
            .gamma-url-link {
                background: white;
                color: #667eea;
                padding: 15px 25px;
                border-radius: 8px;
                text-decoration: none;
                display: inline-block;
                font-weight: 600;
                margin: 10px 0;
                transition: all 0.2s;
            }
            .gamma-url-link:hover {
                transform: translateY(-2px);
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
            }
            .gamma-copy-btn {
                background: rgba(255, 255, 255, 0.2);
                color: white;
                border: 1px solid white;
                padding: 8px 16px;
                border-radius: 6px;
                cursor: pointer;
                font-weight: 600;
                margin-left: 10px;
                transition: all 0.2s;
            }
            .gamma-copy-btn:hover {
                background: rgba(255, 255, 255, 0.3);
            }
            .gamma-metadata {
                font-size: 14px;
                opacity: 0.9;
                margin-top: 10px;
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
                <div class="terminal-output" id="terminalOutput"></div>
                <div id="executionResults" style="padding: 15px; background: #2d2d2d; display: none;">
                    <div id="downloadLinks"></div>
                </div>
            </div>
            
            <!-- Gamma URL panel -->
            <div class="gamma-panel" id="gammaPanel">
                <h3>
                    🎨 Gamma Presentation Generated!
                </h3>
                <a href="#" id="gammaUrlLink" class="gamma-url-link" target="_blank" rel="noopener">
                    📊 Open Presentation
                </a>
                <button class="gamma-copy-btn" onclick="copyGammaUrl()">Copy URL</button>
                <div class="gamma-metadata" id="gammaMetadata"></div>
                <div class="markdown-summary" id="markdownSummary" style="display:none; margin-top: 15px;">
                    <h4>📄 Markdown Summary</h4>
                    <a href="#" id="markdownLink" class="markdown-download-link" download>
                        📥 Download Markdown
                    </a>
                    <button class="gamma-copy-btn" onclick="copyMarkdownPath()">Copy Path</button>
                </div>
            </div>
            
            <div class="examples">
                <h3>💡 Example Queries</h3>
                <div class="example" onclick="setQuery('Give me last week\\'s voice of customer report')">
                    Give me last week's voice of customer report
                </div>
                <div class="example" onclick="setQuery('Show me billing analysis for this month with Gamma presentation')">
                    Show me billing analysis for this month with Gamma presentation
                </div>
                <div class="example" onclick="setQuery('Generate Horatio coaching report for this week')">
                    Generate Horatio coaching report for this week
                </div>
                <div class="example" onclick="setQuery('Show individual agent performance for Boldr with taxonomy breakdown')">
                    Show individual agent performance for Boldr with taxonomy breakdown
                </div>
                <div class="example" onclick="setQuery('Create a custom report for API tickets by Horatio agents in September')">
                    Create a custom report for API tickets by Horatio agents in September
                </div>
                <div class="example" onclick="setQuery('Help me understand what commands are available')">
                    Help me understand what commands are available
                </div>
            </div>
        </div>

        <script>
            // Check system status on page load
            window.onload = function() {
                checkSystemStatus();
            };
            
            async function checkSystemStatus() {
                try {
                    const response = await fetch('/health');
                    const data = await response.json();
                    
                    const statusMessage = document.getElementById('statusMessage');
                    const statusText = document.getElementById('statusText');
                    
                    if (!data.chat_interface) {
                        statusText.innerHTML = '⚠️ Chat interface is not available. This is likely due to missing heavy dependencies (sentence-transformers, faiss-cpu) that are too large for Railway deployment. The basic analysis functionality should still work through the CLI interface.';
                        statusMessage.style.display = 'block';
                        statusMessage.style.backgroundColor = '#fef3c7';
                        statusMessage.style.borderLeft = '4px solid #f59e0b';
                    } else {
                        statusText.innerHTML = '✅ Chat interface is ready! You can start asking questions.';
                        statusMessage.style.display = 'block';
                        statusMessage.style.backgroundColor = '#d1fae5';
                        statusMessage.style.borderLeft = '4px solid #10b981';
                    }
                } catch (error) {
                    console.error('Failed to check system status:', error);
                }
            }
            
            function setQuery(query) {
                document.getElementById('queryInput').value = query;
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
            
            async function executeCommand(command, args) {
                try {
                    // Start execution and get execution ID
                    const startResponse = await fetch('/execute/start', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/x-www-form-urlencoded',
                        },
                        body: `command=${encodeURIComponent(command)}&args=${encodeURIComponent(JSON.stringify(args))}`
                    });
                    
                    const startData = await startResponse.json();
                    currentExecutionId = startData.execution_id;
                    
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
                    
                    // Start SSE connection
                    const eventSource = new EventSource(`/execute?command=${encodeURIComponent(command)}&args=${encodeURIComponent(JSON.stringify(args))}&execution_id=${currentExecutionId}`);
                    currentEventSource = eventSource;
                    
                eventSource.onmessage = function(event) {
                    const data = JSON.parse(event.data);
                    appendTerminalOutput(data);
                };
                
                // Listen for gamma_url events
                eventSource.addEventListener('gamma_url', function(event) {
                    const data = JSON.parse(event.data);
                    if (data.url) {
                        displayGammaUrl(data.url);
                    }
                });
                    
                    eventSource.addEventListener('error', function(event) {
                        console.error('SSE Error:', event);
                        executionSpinner.style.display = 'none';
                        executionStatus.className = 'status-badge failed';
                        executionStatus.textContent = 'Failed';
                        cancelButton.style.display = 'none';
                        eventSource.close();
                        currentEventSource = null;
                    });
                    
                    eventSource.addEventListener('heartbeat', function(event) {
                        // Keep-alive heartbeat, do nothing
                        console.log('Heartbeat received');
                    });
                    
                } catch (error) {
                    console.error('Execution error:', error);
                    addMessage('bot', `Failed to start execution: ${error.message}`);
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
                    await fetch(`/execute/cancel/${currentExecutionId}`, {
                        method: 'POST'
                    });
                    
                    if (currentEventSource) {
                        currentEventSource.close();
                        currentEventSource = null;
                    }
                    
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

                // Build dynamic download links from artifacts
                let linksHtml = '<div class="panel success"><div class="panel-header">✓ Execution Complete</div><div class="panel-content">';

                if (currentGammaUrl) {
                    linksHtml += `<p><strong>Gamma Presentation:</strong> <a href="${currentGammaUrl}" target="_blank" rel="noopener">${currentGammaUrl}</a></p>`;
                }

                if (currentMarkdownPath) {
                    linksHtml += `<p><strong>Markdown Summary:</strong> ${currentMarkdownPath}</p>`;
                }

                linksHtml += '<p>Generated files are available in the outputs directory. Check the command output above for additional file locations.</p>';
                linksHtml += '</div></div>';

                downloadLinks.innerHTML = linksHtml;
                executionResults.style.display = 'block';
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
            
            // Gamma URL handling
            let currentGammaUrl = null;
            let currentMarkdownPath = null;
            
            function detectGammaUrl(text) {
                // Detect Gamma URL in terminal output
                const urlPattern = /Gamma URL:\s*(https:\/\/gamma\.app\/[^\s]+)/;
                const match = text.match(urlPattern);
                if (match) {
                    return match[1];
                }
                return null;
            }
            
            function displayGammaUrl(url) {
                currentGammaUrl = url;
                const gammaPanel = document.getElementById('gammaPanel');
                const gammaUrlLink = document.getElementById('gammaUrlLink');
                
                gammaUrlLink.href = url;
                gammaPanel.style.display = 'block';
                
                // Scroll to Gamma panel
                gammaPanel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            }
            
            function extractGammaMetadata(text) {
                // Extract credits, generation time, and markdown path from output
                const metadata = {};
                
                const creditsMatch = text.match(/Credits used:\s*(\d+)/);
                if (creditsMatch) {
                    metadata.credits = creditsMatch[1];
                }
                
                const timeMatch = text.match(/Generation time:\s*([\d.]+)s/);
                if (timeMatch) {
                    metadata.time = timeMatch[1];
                }
                
                const markdownMatch = text.match(/Markdown summary:\s*([^\s]+)/);
                if (markdownMatch) {
                    metadata.markdownPath = markdownMatch[1];
                }
                
                return metadata;
            }
            
            function updateGammaMetadata(metadata) {
                const gammaMetadata = document.getElementById('gammaMetadata');
                let metadataHtml = '';
                
                if (metadata.credits) {
                    metadataHtml += `💳 Credits used: ${metadata.credits} &nbsp;&nbsp;`;
                }
                if (metadata.time) {
                    metadataHtml += `⏱️ Generation time: ${metadata.time}s`;
                }
                
                gammaMetadata.innerHTML = metadataHtml;
                
                // Display markdown summary if available
                if (metadata.markdownPath) {
                    displayMarkdownSummary(metadata.markdownPath);
                }
            }
            
            function displayMarkdownSummary(markdownPath) {
                currentMarkdownPath = markdownPath;
                const markdownSummary = document.getElementById('markdownSummary');
                const markdownLink = document.getElementById('markdownLink');
                
                // Extract filename from path
                const filename = markdownPath.split('/').pop();
                markdownLink.textContent = `📥 Download ${filename}`;
                markdownLink.href = `/download/${filename}`;
                markdownSummary.style.display = 'block';
            }
            
            function copyGammaUrl() {
                if (!currentGammaUrl) return;
                
                navigator.clipboard.writeText(currentGammaUrl).then(() => {
                    const btn = event.target;
                    const originalText = btn.textContent;
                    btn.textContent = 'Copied!';
                    setTimeout(() => {
                        btn.textContent = originalText;
                    }, 2000);
                }).catch(err => {
                    console.error('Failed to copy URL:', err);
                });
            }
            
            function copyMarkdownPath() {
                if (!currentMarkdownPath) return;
                
                navigator.clipboard.writeText(currentMarkdownPath).then(() => {
                    const btn = event.target;
                    const originalText = btn.textContent;
                    btn.textContent = 'Copied!';
                    setTimeout(() => {
                        btn.textContent = originalText;
                    }, 2000);
                }).catch(err => {
                    console.error('Failed to copy path:', err);
                });
            }
            
            // Override appendTerminalOutput to detect Gamma URLs
            const originalAppendTerminalOutput = appendTerminalOutput;
            appendTerminalOutput = function(data) {
                // Call original function
                originalAppendTerminalOutput(data);
                
                // Check for Gamma URL in the output
                if (data.type === 'stdout' || data.type === 'status') {
                    const text = data.data;
                    const gammaUrl = detectGammaUrl(text);
                    
                    if (gammaUrl) {
                        displayGammaUrl(gammaUrl);
                        
                        // Extract and display metadata
                        const metadata = extractGammaMetadata(text);
                        if (Object.keys(metadata).length > 0) {
                            updateGammaMetadata(metadata);
                        }
                    }
                }
            };
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
            heartbeat_task = None
            try:
                # Send heartbeat every 30 seconds
                heartbeat_task = asyncio.create_task(heartbeat_generator())
                
                async for output in command_executor.execute_command(
                    command, validated_args, execution_id=execution_id
                ):
                    # Update state manager with output
                    await state_manager.add_output(execution_id, output)
                    
                    # Check for Gamma URL in output and send special event
                    if output.get("type") in ("stdout", "status"):
                        output_text = output.get("data", "")
                        if "Gamma URL:" in output_text:
                            # Extract Gamma URL and metadata
                            import re
                            url_match = re.search(r'Gamma URL:\s*(https://gamma\.app/[^\s]+)', output_text)
                            if url_match:
                                gamma_url = url_match.group(1)
                                
                                # Extract additional metadata
                                credits_match = re.search(r'Credits used:\s*(\d+)', output_text)
                                time_match = re.search(r'Generation time:\s*([\d.]+)s', output_text)
                                markdown_match = re.search(r'Markdown summary:\s*([^\s]+)', output_text)
                                
                                gamma_metadata = {
                                    "type": "gamma_url",
                                    "url": gamma_url,
                                    "timestamp": output.get("timestamp")
                                }
                                
                                if credits_match:
                                    gamma_metadata["credits_used"] = int(credits_match.group(1))
                                if time_match:
                                    gamma_metadata["generation_time"] = float(time_match.group(1))
                                if markdown_match:
                                    gamma_metadata["markdown_path"] = markdown_match.group(1)
                                
                                # Send special gamma_url event with metadata
                                yield {
                                    "event": "gamma_url",
                                    "data": json.dumps(gamma_metadata)
                                }
                    
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
                # Always cleanup heartbeat task
                if heartbeat_task is not None and not heartbeat_task.done():
                    heartbeat_task.cancel()
                    try:
                        await asyncio.wait_for(heartbeat_task, timeout=1.0)
                    except (asyncio.CancelledError, asyncio.TimeoutError):
                        pass  # Expected when cancelling
        
        async def heartbeat_generator():
            """Send heartbeat every 30 seconds to keep connection alive."""
            while True:
                await asyncio.sleep(30)
                yield {"event": "heartbeat", "data": ""}
        
        return EventSourceResponse(event_generator())
    
    @app.post("/execute/start")
    async def start_execution(command: str, args: str):
        """Start a new command execution."""
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
            
            return {
                "execution_id": execution_id,
                "status": execution.status.value,
                "queue_position": execution.queue_position,
                "message": "Execution queued successfully"
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
    async def get_execution_status(execution_id: str):
        """Get the status of an execution."""
        if not state_manager:
            raise HTTPException(status_code=500, detail="State manager not available")
        
        execution = await state_manager.get_execution(execution_id)
        if not execution:
            raise HTTPException(status_code=404, detail="Execution not found")
        
        return {
            "execution_id": execution.execution_id,
            "command": execution.command,
            "args": execution.args,
            "status": execution.status.value,
            "start_time": execution.start_time.isoformat(),
            "end_time": execution.end_time.isoformat() if execution.end_time else None,
            "queue_position": execution.queue_position,
            "error_message": execution.error_message,
            "return_code": execution.return_code
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
    
    @app.post("/api/preview-command")
    async def preview_command(request: ChatRequest):
        """
        Preview the command that would be generated from a query without executing it.
        
        Returns the parsed command and arguments for verification.
        """
        if not chat_interface:
            raise HTTPException(
                status_code=500, 
                detail="Chat interface not initialized"
            )
        
        try:
            result = chat_interface.process_query(request.query, request.context)
            
            if result.get("success") and result.get("data", {}).get("translation"):
                translation = result["data"]["translation"]
                if translation.get("translation"):
                    cmd = translation["translation"]
                    return {
                        "success": True,
                        "command": cmd.get("command"),
                        "args": cmd.get("args", []),
                        "full_command": f"{cmd.get('command')} {' '.join(cmd.get('args', []))}",
                        "explanation": cmd.get("explanation"),
                        "confidence": cmd.get("confidence", 0.0)
                    }
            
            return {
                "success": False,
                "error": "Could not parse command from query"
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Preview failed: {str(e)}")
    
    @app.get("/download")
    async def download_file(file: str):
        """
        Download a file from the outputs directory.
        
        Security: Only allows downloading from the outputs directory.
        """
        try:
            from fastapi.responses import FileResponse
            import os
            
            # Security: Validate the file path
            file_path = Path(file)
            
            # Ensure the file is in the outputs directory
            if not str(file_path).startswith('outputs/') and not str(file_path).startswith('./outputs/'):
                # Try prepending outputs/
                file_path = Path('outputs') / file_path.name
            
            # Resolve to absolute path and validate
            abs_file_path = file_path.resolve()
            outputs_dir = Path('outputs').resolve()
            
            # Security check: Ensure file is within outputs directory
            try:
                abs_file_path.relative_to(outputs_dir)
            except ValueError:
                raise HTTPException(
                    status_code=403,
                    detail="Access denied: File must be in outputs directory"
                )
            
            # Check if file exists
            if not abs_file_path.exists():
                raise HTTPException(
                    status_code=404,
                    detail=f"File not found: {file_path.name}"
                )
            
            # Check if it's a file (not a directory)
            if not abs_file_path.is_file():
                raise HTTPException(
                    status_code=400,
                    detail="Path is not a file"
                )
            
            # Return the file
            return FileResponse(
                path=abs_file_path,
                filename=abs_file_path.name,
                media_type='application/octet-stream'
            )
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Download error: {str(e)}")

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
