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

# Check Python path setup
print(f"🔧 PYTHONPATH: {os.environ.get('PYTHONPATH', 'Not set')}")
print(f"🔧 Current working directory: {os.getcwd()}")
print(f"🔧 Script location: {__file__}")
print(f"🔧 Expected src path: {Path(__file__).parent.parent / 'src'}")

# Ensure src is in Python path (fallback if PYTHONPATH not set)
src_path = str(Path(__file__).parent.parent / "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)
    print(f"🔧 Added src to Python path: {src_path}")
else:
    print(f"🔧 src already in Python path: {src_path}")

# Test if we can find the src directory and key files
src_dir = Path(__file__).parent.parent / "src"
print(f"🔧 src directory exists: {src_dir.exists()}")
if src_dir.exists():
    print(f"🔧 src directory contents: {list(src_dir.iterdir())}")
    
    chat_dir = src_dir / "chat"
    print(f"🔧 chat directory exists: {chat_dir.exists()}")
    if chat_dir.exists():
        print(f"🔧 chat directory contents: {list(chat_dir.iterdir())}")

# Let's also check the entire app directory structure
print(f"🔧 App directory contents: {list(Path('/app').iterdir())}")
print(f"🔧 Current script parent contents: {list(Path(__file__).parent.iterdir())}")
print(f"🔧 Current script parent parent contents: {list(Path(__file__).parent.parent.iterdir())}")

# Try to import directly to see the exact error
try:
    import src
    print(f"✅ Successfully imported src module")
    print(f"🔧 src module location: {src.__file__}")
except ImportError as e:
    print(f"❌ Failed to import src: {e}")
    print(f"🔧 sys.path: {sys.path[:5]}")  # Show first 5 entries

try:
    from fastapi import FastAPI, HTTPException, Request
    from fastapi.responses import HTMLResponse, JSONResponse
    from fastapi.staticfiles import StaticFiles
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

def initialize_chat():
    """Initialize the chat interface."""
    global chat_interface
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
            
            <div class="examples">
                <h3>💡 Example Queries</h3>
                <div class="example" onclick="setQuery('Give me last week\\'s voice of customer report')">
                    Give me last week's voice of customer report
                </div>
                <div class="example" onclick="setQuery('Show me billing analysis for this month with Gamma presentation')">
                    Show me billing analysis for this month with Gamma presentation
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
                    
                    if (data.success) {
                        addMessage('bot', data.message);
                        if (data.data && data.data.translation) {
                            const translation = data.data.translation;
                            if (translation.translation) {
                                const cmd = translation.translation;
                                addMessage('bot', `Command: ${cmd.command} ${cmd.args ? cmd.args.join(' ') : ''}`);
                                addMessage('bot', `Explanation: ${cmd.explanation}`);
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

    @app.get("/health")
    async def health_check():
        """Health check endpoint for Railway."""
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "chat_interface": chat_interface is not None,
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
