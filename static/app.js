// Dynamic version loaded from server
console.log('✅ JavaScript loaded successfully');

// Global command schema from server
let commandSchema = null;

// Global version info
let versionInfo = null;

// Global error handler - catch all JavaScript errors and display them
window.onerror = function(msg, url, lineNo, columnNo, error) {
    console.error('🚨 Global JavaScript Error:', msg, 'at line', lineNo);
    const errorDiv = document.createElement('div');
    errorDiv.style = 'position:fixed;top:0;left:0;right:0;background:#ff0000;color:#fff;padding:20px;z-index:99999;font-family:monospace;';
    errorDiv.innerHTML = `<strong>JavaScript Error:</strong> ${msg}<br><strong>Line:</strong> ${lineNo}:${columnNo}`;
    document.body.prepend(errorDiv);
    return false;
};

// Check system status and load recent jobs on page load
window.onload = function() {
    loadCommandSchema();
    loadVersionInfo();
    checkSystemStatus();
    loadRecentJobs();
};

async function loadCommandSchema() {
    try {
        console.log('📡 Fetching command schema from server...');
        const response = await fetch('/api/commands');
        const data = await response.json();
        commandSchema = data.commands;
        console.log('✅ Loaded command schema:', commandSchema);
        console.log(`📊 Schema version: ${data.version}, generated at: ${data.generated_at}`);
    } catch (error) {
        console.error('❌ Failed to load command schema:', error);
        console.warn('⚠️  Falling back to hard-coded command logic');
        // commandSchema will remain null, triggering fallback behavior
    }
}

async function loadVersionInfo() {
    try {
        console.log('📡 Fetching version info from server...');
        const response = await fetch('/debug/version');
        const version = await response.json();
        versionInfo = version;
        
        // Display in footer
        const footer = document.getElementById('version-footer');
        if (footer) {
            footer.innerHTML = `
                <span class="version-info" title="Version: ${version.version}, Commit: ${version.commit}, Build: ${version.build_date}">
                    v${version.version} (${version.commit_short})
                </span>
            `;
        }
        
        // Log to console
        console.log(`✅ App Version: ${version.version} (${version.commit_short})`);
        console.log(`📅 Build Date: ${version.build_date}`);
        console.log(`⏱️  Uptime: ${(version.uptime_seconds / 3600).toFixed(1)} hours`);
        console.log(`🐍 Python: ${version.python_version.split(' ')[0]}`);
        console.log(`🌍 Environment: ${version.environment}`);
        
    } catch (error) {
        console.error('❌ Failed to load version info:', error);
        // Keep the hardcoded version in the footer if fetch fails
    }
}

async function checkSystemStatus() {
    try {
        const response = await fetch('/health');
        const data = await response.json();
        
        console.log('System status:', data);
        
        // Status checking is optional - only update UI if elements exist
        const statusMessage = document.getElementById('statusMessage');
        const statusText = document.getElementById('statusText');
        
        if (!statusMessage || !statusText) {
            console.log('Status elements not found - skipping status UI update');
            return;
        }
        
        if (!data.chat_interface) {
            statusText.innerHTML = '⚠️ Chat interface is not available due to missing dependencies. You can still execute CLI commands.';
            statusMessage.style.display = 'block';
            statusMessage.style.background = 'rgba(245, 158, 11, 0.1)';
            statusMessage.style.border = '1px solid rgba(245, 158, 11, 0.3)';
            statusMessage.style.color = '#fbbf24';
        } else {
            statusText.innerHTML = '✅ System ready';
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
        
        const recentJobs = document.getElementById('recentJobs');
        const jobsList = document.getElementById('jobsList');
        
        // Validate elements exist before updating
        if (!recentJobs || !jobsList) {
            console.log('Recent jobs elements not found - skipping recent jobs UI');
            return;
        }
        
        if (data.executions && data.executions.length > 0) {
            jobsList.innerHTML = data.executions.map(job => `
                <div class="example" onclick="resumeJob('${job.execution_id}')" style="display: flex; justify-content: space-between; align-items: center; cursor: pointer;">
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
        } else {
            jobsList.innerHTML = '<div style="color: #9ca3af; text-align: center; padding: 20px;">No recent jobs</div>';
        }
    } catch (error) {
        console.error('Failed to load recent jobs:', error);
    }
}

async function resumeJob(executionId) {
    if (!executionId) {
        console.error('resumeJob called without execution ID');
        return;
    }
    
    try {
        currentExecutionId = executionId;
        
        // Fetch current status
        const response = await fetch(`/execute/status/${executionId}`);
        if (!response.ok) {
            if (response.status === 401) {
                showAuthError('Authentication required. Please provide valid credentials.');
                return;
            }
            throw new Error(`Failed to fetch job status: ${response.status}`);
        }
        
        const data = await response.json();
        
        console.log('Resume job data:', data);
        
        // Validate required elements exist
        const terminalContainer = document.getElementById('terminalContainer');
        const terminalOutput = document.getElementById('terminalOutput');
        const terminalTitle = document.getElementById('terminalTitle');
        const executionStatus = document.getElementById('executionStatus');
        const executionSpinner = document.getElementById('executionSpinner');
        const cancelButton = document.getElementById('cancelButton');
        
        if (!terminalContainer || !terminalOutput || !terminalTitle) {
            console.error('Required terminal elements not found in DOM');
            return;
        }
        
        terminalContainer.style.display = 'block';
        terminalOutput.innerHTML = '';
        terminalTitle.textContent = `Job: ${data.command} (ID: ${executionId.substring(0, 8)}...)`;
        
        if (executionStatus) {
            executionStatus.style.display = 'inline-block';
            executionStatus.className = `status-badge ${data.status}`;
            executionStatus.textContent = data.status.charAt(0).toUpperCase() + data.status.slice(1);
        }
        
        // Display all output
        outputIndex = 0;
        if (data.output && data.output.length > 0) {
            console.log(`Displaying ${data.output.length} output items`);
            data.output.forEach((outputItem, index) => {
                appendTerminalOutput(outputItem);
            });
            outputIndex = data.output_length || data.output.length;
        } else {
            terminalOutput.innerHTML = '<div style="color: #666; padding: 20px;">No output available yet...</div>';
        }
        
        // If still running, start polling
        if (data.status === 'running' || data.status === 'starting' || data.status === 'queued') {
            if (executionSpinner) executionSpinner.style.display = 'inline-block';
            if (cancelButton) cancelButton.style.display = 'inline-block';
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

// Legacy function - no longer used with form-based interface
// Kept for backwards compatibility if needed
function showDirectCLIInput() {
    console.log('showDirectCLIInput() called - this function is deprecated in form-based interface');
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
    
    // Handle help queries directly if chat interface might fail
    const lowerQuery = query.toLowerCase();
    if (lowerQuery.includes('help') || lowerQuery.includes('available commands') || lowerQuery.includes('what commands')) {
        input.disabled = false;
        button.disabled = false;
        button.textContent = 'Send';
        
        addMessage('bot', `            <strong>📚 Available Analysis Commands:</strong><br><br>
            
            <strong>Main Analysis:</strong><br>
            • <code>voice-of-customer --start-date YYYY-MM-DD --end-date YYYY-MM-DD --generate-gamma</code><br>
            &nbsp;&nbsp;Comprehensive VoC analysis with topic detection<br>
            &nbsp;&nbsp;<em>Note: Dates interpreted as Pacific Time (America/Los_Angeles)</em><br><br>
            
            <strong>Category-Specific:</strong><br>
            • <code>billing-analysis --generate-gamma</code> - Billing, refunds, subscriptions<br>
            • <code>tech-analysis --days 7</code> - Technical troubleshooting patterns<br>
            • <code>api-analysis --generate-gamma</code> - API integration issues<br>
            • <code>product-analysis --generate-gamma</code> - Product questions and features<br>
            • <code>sites-analysis --generate-gamma</code> - Sites/workspace issues<br><br>
            
            <strong>Feedback Analysis:</strong><br>
            • <code>canny-analysis --generate-gamma --start-date YYYY-MM-DD --end-date YYYY-MM-DD</code><br>
            &nbsp;&nbsp;Analyze Canny feature requests and votes<br><br>
            
            <strong>🏷️ Topics Detected (via Taxonomy):</strong><br>
            • <strong>Credits</strong> - Credit usage, purchasing, credit model<br>
            • <strong>Agent/Buddy</strong> - AI assistant behavior and editing<br>
            • <strong>Workspace Templates</strong> - Template usage and API access<br>
            • <strong>Billing</strong> - Refunds, subscriptions, payments<br>
            • <strong>Bug</strong> - Technical issues and errors<br>
            • <strong>Account</strong> - Login, password, email changes<br>
            • <strong>API</strong> - Integration and developer issues<br>
            • <strong>Product Question</strong> - How-to and feature questions<br>
            • Plus 5+ more subcategories...<br><br>
            
            <strong>🤖 Analysis Modes (use dropdown above):</strong><br>
            • <strong>Topic-Based</strong> - Hilary's VoC card format<br>
            &nbsp;&nbsp;Per-topic sentiment, Paid/Free separation, 3-10 examples, Fin analysis<br>
            • <strong>Synthesis</strong> - Strategic insights and recommendations<br>
            &nbsp;&nbsp;Cross-category patterns, Operational metrics (FCR, resolution time)<br>
            • <strong>Complete</strong> - Both formats in one analysis<br>
            &nbsp;&nbsp;Topic cards + Synthesis insights (recommended)<br><br>
            
            <strong>💡 Natural Language Examples:</strong><br>
            • "Give me last week's voice of customer report"<br>
            • "Show me billing analysis for this month with Gamma"<br>
            • "Analyze Canny feedback from October"<br>
            • "Create VoC analysis for the past 7 days"`);
        return;
    }
    
    try {
        const response = await fetch('/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ query: query })
        });
        
        if (response.status === 401) {
            showAuthError('Authentication required. Please provide valid credentials.');
            input.disabled = false;
            button.disabled = false;
            button.textContent = 'Send';
            return;
        }
        
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
                    const executeBtn = document.createElement('button');
                    executeBtn.className = 'btn-execute';
                    executeBtn.textContent = 'Execute Command';
                    executeBtn.onclick = () => executeCommand(cmd.command, cmd.args || []);
                    executeButton.appendChild(executeBtn);
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
    if (!command) {
        console.error('executeCommand called without command');
        return;
    }
    
    // Validate args is an array
    if (!Array.isArray(args)) {
        console.error('executeCommand args must be an array');
        args = [];
    }
    
    try {
        // Convert CLI command to full python execution
        const fullCommand = 'python';
        let fullArgs = ['src/main.py', command, ...args];
        
        // Validate fullArgs before sending
        if (fullArgs.some(arg => typeof arg !== 'string')) {
            throw new Error('All arguments must be strings');
        }
        
        // Start execution and get execution ID
        const startResponse = await fetch(`/execute/start?command=${encodeURIComponent(fullCommand)}&args=${encodeURIComponent(JSON.stringify(fullArgs))}`, {
            method: 'POST'
        });
        
        if (startResponse.status === 401) {
            showAuthError('Authentication required. Please provide valid credentials.');
            return;
        }
        
        if (startResponse.status === 429) {
            showRateLimitError('Too many requests. Please wait before trying again.');
            return;
        }
        
        if (!startResponse.ok) {
            const errorData = await startResponse.json();
            throw new Error(errorData.detail || `Start execution failed: ${startResponse.status}`);
        }
        
        const startData = await startResponse.json();
        currentExecutionId = startData.execution_id;
        outputIndex = 0;
        
        // Validate required elements
        const terminalContainer = document.getElementById('terminalContainer');
        const terminalOutput = document.getElementById('terminalOutput');
        const terminalTitle = document.getElementById('terminalTitle');
        const executionSpinner = document.getElementById('executionSpinner');
        const executionStatus = document.getElementById('executionStatus');
        const cancelButton = document.getElementById('cancelButton');
        
        if (!terminalContainer || !terminalOutput || !terminalTitle) {
            console.error('Required terminal elements not found');
            return;
        }
        
        terminalContainer.style.display = 'block';
        terminalOutput.innerHTML = '';
        terminalTitle.textContent = `Executing: ${command}`;
        
        if (executionSpinner) executionSpinner.style.display = 'inline-block';
        if (executionStatus) {
            executionStatus.style.display = 'inline-block';
            executionStatus.className = 'status-badge running';
            executionStatus.textContent = 'Running';
        }
        if (cancelButton) cancelButton.style.display = 'inline-block';
        
        // Start polling for updates
        startPolling();
        
    } catch (error) {
        console.error('Execution error:', error);
        
        // Try to show error in chat if available
        const chatContainer = document.getElementById('chatContainer');
        if (chatContainer && typeof addMessage === 'function') {
            addMessage('bot', `Failed to start execution: ${error.message}`);
        } else {
            alert(`Failed to start execution: ${error.message}`);
        }
    }
}

let lastActivityTime = Date.now();

function startPolling() {
    // Reset last activity time
    lastActivityTime = Date.now();
    
    // Poll every 1 second for updates
    pollingInterval = setInterval(async () => {
        try {
            const response = await fetch(`/execute/status/${currentExecutionId}?since=${outputIndex}`);
            
            if (response.status === 401) {
                stopPolling();
                showAuthError('Authentication session expired. Please refresh and try again.');
                return;
            }
            
            const data = await response.json();
            
            // Update output
            if (data.output && data.output.length > 0) {
                data.output.forEach(outputItem => {
                    appendTerminalOutput(outputItem);
                });
                outputIndex = data.output_length;
                lastActivityTime = Date.now();
            }
            
            // Check if execution is complete
            if (data.status === 'completed' || data.status === 'failed' || data.status === 'error' || data.status === 'cancelled' || data.status === 'timeout') {
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
                    
                    // Parse and populate tabs
                    updateAnalysisTabs(fullOutput);
                    
                    // Parse and display agent results in Summary tab
                    updateAgentResultsSummary(fullOutput);
                    
                    // Check for audit trail files and display them
                    displayAuditTrailBadge(fullOutput);
                    
                } else if (data.status === 'timeout') {
                    executionStatus.className = 'status-badge failed';
                    executionStatus.textContent = 'Timeout';
                    showTimeoutError(data.error_message || 'Execution exceeded maximum duration. Increase MAX_EXECUTION_DURATION if needed.');
                } else if (data.status === 'cancelled') {
                    executionStatus.className = 'status-badge warning';
                    executionStatus.textContent = 'Cancelled';
                    showCancelledMessage('Execution was cancelled.');
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
    
    // Monitor for stalled connections
    const stallCheckInterval = setInterval(() => {
        if (!pollingInterval) {
            clearInterval(stallCheckInterval);
            return;
        }
        
        const timeSinceActivity = Date.now() - lastActivityTime;
        if (timeSinceActivity > 60000) {  // 1 minute without activity
            console.warn('No activity for 1 minute, connection may be stalled');
            // Could show warning or attempt reconnect
        }
    }, 10000); // Check every 10 seconds
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
    
    // Handle timeout status
    if (data.type === 'timeout' || data.status === 'timeout') {
        executionSpinner.style.display = 'none';
        executionStatus.className = 'status-badge failed';
        executionStatus.textContent = 'Timeout';
        cancelButton.style.display = 'none';
        
        showTimeoutError(data.message || 'Execution exceeded maximum duration. Increase MAX_EXECUTION_DURATION if needed.');
        
        if (currentEventSource) {
            currentEventSource.close();
            currentEventSource = null;
        }
        stopPolling();
        return;
    }
    
    // Handle cancelled status
    if (data.type === 'cancelled' || data.status === 'cancelled') {
        executionSpinner.style.display = 'none';
        executionStatus.className = 'status-badge warning';
        executionStatus.textContent = 'Cancelled';
        cancelButton.style.display = 'none';
        
        showCancelledMessage(data.message || 'Execution was cancelled');
        
        if (currentEventSource) {
            currentEventSource.close();
            currentEventSource = null;
        }
        stopPolling();
        return;
    }
    
    // Create line element
    const line = document.createElement('div');
    line.className = `terminal-line ${data.type}`;
    
    // Add truncation indicator if present
    if (data.truncated) {
        line.className += ' truncated';
    }
    
    // Convert ANSI codes to HTML
    const htmlContent = ansiUp.ansi_to_html(data.data || '');
    line.innerHTML = htmlContent;
    
    terminalOutput.appendChild(line);
    terminalOutput.scrollTop = terminalOutput.scrollHeight;
    
    // Update last activity time
    lastActivityTime = Date.now();
    
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
        
        const response = await fetch(`/execute/cancel/${currentExecutionId}`, {
            method: 'POST'
        });
        
        if (response.status === 401) {
            showAuthError('Authentication required to cancel execution.');
            return;
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
    
    // Show generic success message (file list available via Files tab)
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

function showAuthError(message) {
    const terminalOutput = document.getElementById('terminalOutput');
    if (terminalOutput) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'terminal-line error';
        errorDiv.style.cssText = 'background: rgba(239, 68, 68, 0.1); border-left: 3px solid #ef4444; padding: 12px; margin: 10px 0; border-radius: 4px;';
        errorDiv.innerHTML = `<strong>🔐 Authentication Error:</strong> ${message}`;
        terminalOutput.appendChild(errorDiv);
        terminalOutput.scrollTop = terminalOutput.scrollHeight;
    }
    
    const executionStatus = document.getElementById('executionStatus');
    if (executionStatus) {
        executionStatus.className = 'status-badge failed';
        executionStatus.textContent = 'Auth Failed';
    }
}

function showRateLimitError(message) {
    const terminalOutput = document.getElementById('terminalOutput');
    if (terminalOutput) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'terminal-line error';
        errorDiv.style.cssText = 'background: rgba(245, 158, 11, 0.1); border-left: 3px solid #f59e0b; padding: 12px; margin: 10px 0; border-radius: 4px;';
        errorDiv.innerHTML = `<strong>⏱️ Rate Limit:</strong> ${message}`;
        terminalOutput.appendChild(errorDiv);
        terminalOutput.scrollTop = terminalOutput.scrollHeight;
    }
}

function showTimeoutError(message) {
    const terminalOutput = document.getElementById('terminalOutput');
    if (terminalOutput) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'terminal-line error';
        errorDiv.style.cssText = 'background: rgba(239, 68, 68, 0.1); border-left: 3px solid #ef4444; padding: 12px; margin: 10px 0; border-radius: 4px;';
        
        let htmlContent = `<strong>⏰ Timeout:</strong> ${message}`;
        
        // Add configuration tips if the message mentions exceeded limit
        if (message && message.includes('exceeded')) {
            htmlContent += `<br><br><div style="margin-top: 10px; padding: 10px; background: rgba(59, 130, 246, 0.1); border-left: 3px solid #3b82f6; border-radius: 4px;">
                <strong>💡 Tip:</strong> Set MAX_EXECUTION_DURATION environment variable to a higher value for large datasets.<br>
                <strong>Example:</strong> MAX_EXECUTION_DURATION=7200 (for 2 hours)<br><br>
                <strong>Recommended Timeouts:</strong><br>
                • Small (&lt; 1,000 conversations): 1800 (30 min)<br>
                • Medium (1,000-5,000): 3600 (60 min)<br>
                • Large (5,000-10,000): 7200 (2 hours)<br>
                • Very Large (&gt; 10,000): 14400 (4 hours)
            </div>`;
        }
        
        errorDiv.innerHTML = htmlContent;
        terminalOutput.appendChild(errorDiv);
        terminalOutput.scrollTop = terminalOutput.scrollHeight;
    }
}

function showCancelledMessage(message) {
    const terminalOutput = document.getElementById('terminalOutput');
    if (terminalOutput) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'terminal-line warning';
        messageDiv.style.cssText = 'background: rgba(245, 158, 11, 0.1); border-left: 3px solid #f59e0b; padding: 12px; margin: 10px 0; border-radius: 4px;';
        messageDiv.innerHTML = `<strong>🚫 Cancelled:</strong> ${message}`;
        terminalOutput.appendChild(messageDiv);
        terminalOutput.scrollTop = terminalOutput.scrollHeight;
    }
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
        paidConversations: 0,
        freeConversations: 0,
        topicsAnalyzed: 0,
        dateRange: '',
        executionTime: 0,
        agentsCompleted: 0,
        topCategories: [],
        sentiment: '',
        keyInsights: []
    };
    
    // Extract total conversations (look for specific patterns from topic-based output)
    const totalConvMatch = output.match(/(?:Total conversations|📊 Total conversations):\s*(\d{1,3}(?:,\d{3})*)/i);
    if (totalConvMatch) {
        summary.conversations = parseInt(totalConvMatch[1].replace(/,/g, ''));
    } else {
        // Fallback: look for "Fetched X conversations"
        const fetchedMatch = output.match(/Fetched\s+(\d{1,3}(?:,\d{3})*)\s+conversations/i);
        if (fetchedMatch) {
            summary.conversations = parseInt(fetchedMatch[1].replace(/,/g, ''));
        }
    }
    
    // Extract paid/free breakdown
    const paidMatch = output.match(/Paid customers.*?:\s*(\d{1,3}(?:,\d{3})*)/i);
    if (paidMatch) {
        summary.paidConversations = parseInt(paidMatch[1].replace(/,/g, ''));
    }
    
    const freeMatch = output.match(/Free customers.*?:\s*(\d{1,3}(?:,\d{3})*)/i);
    if (freeMatch) {
        summary.freeConversations = parseInt(freeMatch[1].replace(/,/g, ''));
    }
    
    // Extract topics analyzed
    const topicsMatch = output.match(/(?:Topics analyzed|🏷️\s+Topics analyzed):\s*(\d+)/i);
    if (topicsMatch) {
        summary.topicsAnalyzed = parseInt(topicsMatch[1]);
    }
    
    // Extract execution time
    const timeMatch = output.match(/(?:Total time|⏱️\s+Total time):\s*([\d.]+)s/i);
    if (timeMatch) {
        summary.executionTime = parseFloat(timeMatch[1]);
    }
    
    // Extract agents completed
    const agentsMatch = output.match(/(?:Agents completed|🤖 Agents completed):\s*(\d+)/i);
    if (agentsMatch) {
        summary.agentsCompleted = parseInt(agentsMatch[1]);
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
    const summaryCardsContainer = document.querySelector('#analysisSummary .summary-cards');
    if (!summaryCardsContainer) return;
    
    let html = '';
    
    // Main metrics
    if (summary.conversations > 0) {
        html += `
            <div class="summary-card">
                <div class="card-title">Total Conversations</div>
                <div class="card-value">${summary.conversations.toLocaleString()}</div>
            </div>
        `;
    }
    
    if (summary.paidConversations > 0) {
        html += `
            <div class="summary-card">
                <div class="card-title">Paid Customers</div>
                <div class="card-value">${summary.paidConversations.toLocaleString()}</div>
            </div>
        `;
    }
    
    if (summary.freeConversations > 0) {
        html += `
            <div class="summary-card">
                <div class="card-title">Free Customers</div>
                <div class="card-value">${summary.freeConversations.toLocaleString()}</div>
            </div>
        `;
    }
    
    if (summary.topicsAnalyzed > 0) {
        html += `
            <div class="summary-card">
                <div class="card-title">Topics Analyzed</div>
                <div class="card-value">${summary.topicsAnalyzed}</div>
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
    
    if (summary.executionTime > 0) {
        html += `
            <div class="summary-card">
                <div class="card-title">Execution Time</div>
                <div class="card-value">${summary.executionTime.toFixed(1)}s</div>
            </div>
        `;
    }
    
    if (summary.agentsCompleted > 0) {
        html += `
            <div class="summary-card">
                <div class="card-title">Agents Completed</div>
                <div class="card-value">${summary.agentsCompleted}/7</div>
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
    
    summaryCardsContainer.innerHTML = html;
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


// Toggle test mode options visibility
function toggleTestModeOptions() {
    const testMode = document.getElementById('testMode');
    const testModeOptions = document.getElementById('testModeOptions');
    if (testMode && testModeOptions) {
        testModeOptions.style.display = testMode.checked ? 'block' : 'none';
    }
}

// Attach event listener when page loads
document.addEventListener('DOMContentLoaded', function() {
    const testMode = document.getElementById('testMode');
    if (testMode) {
        testMode.addEventListener('change', toggleTestModeOptions);
    }
});

function validateAgainstSchema(analysisTypeKey, flags) {
    /**
     * Validate command flags against server schema.
     *
     * @param {string} analysisTypeKey - Schema key for analysis type
     * @param {Object} flags - Flags to validate
     * @returns {Object} {valid: boolean, error: string|null}
     */
    if (!commandSchema) {
        console.warn('⚠️  Schema not loaded, skipping validation');
        return {valid: true}; // Allow execution if schema not loaded
    }
    
    if (!commandSchema[analysisTypeKey]) {
        return {valid: false, error: `Unknown analysis type: ${analysisTypeKey}`};
    }
    
    const config = commandSchema[analysisTypeKey];
    const allowedFlags = config.allowed_flags;
    
    // Check for unknown flags
    for (const flagName of Object.keys(flags)) {
        if (!(flagName in allowedFlags)) {
            return {valid: false, error: `Unknown flag: ${flagName} for ${analysisTypeKey}`};
        }
    }
    
    // Check required flags
    for (const [flagName, flagSchema] of Object.entries(allowedFlags)) {
        if (flagSchema.required && !(flagName in flags)) {
            return {valid: false, error: `Missing required flag: ${flagName}`};
        }
    }
    
    // Validate flag values
    for (const [flagName, flagValue] of Object.entries(flags)) {
        const flagSchema = allowedFlags[flagName];
        
        if (flagSchema.type === 'enum' && !flagSchema.values.includes(flagValue)) {
            return {
                valid: false,
                error: `Invalid value '${flagValue}' for ${flagName}. Must be one of: ${flagSchema.values.join(', ')}`
            };
        }
        
        if (flagSchema.type === 'integer') {
            const val = parseInt(flagValue);
            if (isNaN(val)) {
                return {valid: false, error: `Invalid integer value for ${flagName}`};
            }
            if (flagSchema.min !== undefined && val < flagSchema.min) {
                return {valid: false, error: `${flagName} must be at least ${flagSchema.min}`};
            }
            if (flagSchema.max !== undefined && val > flagSchema.max) {
                return {valid: false, error: `${flagName} must be at most ${flagSchema.max}`};
            }
        }
        
        if (flagSchema.type === 'date') {
            // Basic date format validation
            if (!/^\d{4}-\d{2}-\d{2}$/.test(flagValue)) {
                return {valid: false, error: `Invalid date format for ${flagName}. Expected YYYY-MM-DD`};
            }
        }
    }
    
    return {valid: true};
}

// Form-based analysis execution handler
function runAnalysis() {
    // Get form values with validation
    const analysisType = document.getElementById('analysisType');
    const timePeriod = document.getElementById('timePeriod');
    const dataSource = document.getElementById('dataSource');
    const taxonomyFilter = document.getElementById('taxonomyFilter');
    const outputFormat = document.getElementById('outputFormat');
    const testMode = document.getElementById('testMode');
    const testDataCount = document.getElementById('testDataCount');
    const verboseLogging = document.getElementById('verboseLogging');
    const auditMode = document.getElementById('auditMode');
    
    if (!analysisType || !timePeriod || !dataSource || !outputFormat) {
        console.error('Missing required form elements');
        alert('Form elements not found. Please refresh the page.');
        return;
    }
    
    const analysisValue = analysisType.value;
    const timeValue = timePeriod.value;
    const sourceValue = dataSource.value;
    const filterValue = taxonomyFilter ? taxonomyFilter.value : '';
    const formatValue = outputFormat.value;
    const isTestMode = testMode ? testMode.checked : false;
    const testCount = testDataCount ? testDataCount.value : '100';
    const isVerbose = verboseLogging ? verboseLogging.checked : false;
    const isAuditMode = auditMode ? auditMode.checked : false;
    
    // Map UI analysis type to schema key
    const analysisTypeMap = {
        'voice-of-customer-hilary': 'voice_of_customer',
        'voice-of-customer-synthesis': 'voice_of_customer',
        'voice-of-customer-complete': 'voice_of_customer',
        'agent-performance-horatio-team': 'agent_performance',
        'agent-performance-boldr-team': 'agent_performance',
        'agent-performance-horatio-individual': 'agent_performance',
        'agent-performance-boldr-individual': 'agent_performance',
        'agent-performance-escalated': 'agent_performance',
        'agent-coaching-horatio': 'agent_coaching',
        'agent-coaching-boldr': 'agent_coaching',
        'analyze-billing': 'category_billing',
        'analyze-product': 'category_product',
        'analyze-api': 'category_api',
        'analyze-escalations': 'category_escalations',
        'tech-analysis': 'tech_troubleshooting',
        'analyze-all-categories': 'all_categories',
        'canny-analysis': 'canny_analysis'
    };
    
    const schemaKey = analysisTypeMap[analysisValue];
    if (!schemaKey) {
        alert(`Unknown analysis type: ${analysisValue}`);
        return;
    }
    
    // Build flags object for validation
    const flags = {};
    
    // Build command based on analysis type
    let command = '';
    let args = [];
    
    // Map analysis type to command (keeping existing logic for now)
    if (analysisValue === 'voice-of-customer-hilary') {
        command = 'voice-of-customer';
        flags['--multi-agent'] = true;
        flags['--analysis-type'] = 'topic-based';
    } else if (analysisValue === 'voice-of-customer-synthesis') {
        command = 'voice-of-customer';
        flags['--multi-agent'] = true;
        flags['--analysis-type'] = 'synthesis';
    } else if (analysisValue === 'voice-of-customer-complete') {
        command = 'voice-of-customer';
        flags['--multi-agent'] = true;
        flags['--analysis-type'] = 'complete';
    } else if (analysisValue === 'agent-performance-horatio-team') {
        command = 'agent-performance';
        flags['--agent'] = 'horatio';
    } else if (analysisValue === 'agent-performance-boldr-team') {
        command = 'agent-performance';
        flags['--agent'] = 'boldr';
    } else if (analysisValue === 'agent-performance-horatio-individual') {
        command = 'agent-performance';
        flags['--agent'] = 'horatio';
        flags['--individual-breakdown'] = true;
    } else if (analysisValue === 'agent-performance-boldr-individual') {
        command = 'agent-performance';
        flags['--agent'] = 'boldr';
        flags['--individual-breakdown'] = true;
    } else if (analysisValue === 'agent-coaching-horatio') {
        command = 'agent-coaching-report';
        flags['--vendor'] = 'horatio';
    } else if (analysisValue === 'agent-coaching-boldr') {
        command = 'agent-coaching-report';
        flags['--vendor'] = 'boldr';
    } else if (analysisValue === 'agent-performance-escalated') {
        command = 'agent-performance';
        flags['--agent'] = 'escalated';
    } else {
        command = analysisValue;
    }
    
    // Add time period flags
    if (timeValue === 'custom') {
        const startDate = document.getElementById('startDate');
        const endDate = document.getElementById('endDate');
        
        if (!startDate || !endDate || !startDate.value || !endDate.value) {
            alert('Please select both start and end dates');
            return;
        }
        
        flags['--start-date'] = startDate.value;
        flags['--end-date'] = endDate.value;
    } else {
        // Check if command supports --time-period or --days
        const supportsTimePeriod = ['voice-of-customer', 'agent-performance', 'agent-coaching-report', 'canny-analysis'];
        const categoryDeepDiveCommands = ['analyze-billing', 'analyze-product', 'analyze-api', 'analyze-sites', 'analyze-escalations', 'tech-analysis', 'analyze-all-categories'];
        
        if (supportsTimePeriod.includes(command)) {
            flags['--time-period'] = timeValue;
        } else if (categoryDeepDiveCommands.includes(command)) {
            const dayMap = {'yesterday': 1, 'week': 7, 'month': 30};
            flags['--days'] = dayMap[timeValue] || 7;
        } else {
            flags['--time-period'] = timeValue;
        }
    }
    
    // Add data source flags
    if (sourceValue === 'canny') {
        command = 'canny-analysis';
    } else if (sourceValue === 'both') {
        flags['--include-canny'] = true;
    }
    
    // Add taxonomy filter if selected
    if (filterValue) {
        flags['--focus-areas'] = filterValue;
    }
    
    // Add output format
    if (formatValue === 'gamma') {
        flags['--generate-gamma'] = true;
    }
    
    // Add test mode flags
    if (isTestMode) {
        flags['--test-mode'] = true;
        flags['--test-data-count'] = parseInt(testCount);
    }
    
    // Add verbose logging
    if (isVerbose) {
        flags['--verbose'] = true;
    }
    
    // Add audit trail mode
    if (isAuditMode) {
        flags['--audit-trail'] = true;
    }
    
    // Validate flags against schema
    const validation = validateAgainstSchema(schemaKey, flags);
    if (!validation.valid) {
        alert(`Validation Error: ${validation.error}`);
        console.error('❌ Validation failed:', validation.error);
        return;
    }
    
    // Convert flags object to args array
    // Each flag with a value must be immediately followed by its value
    args = [];
    for (const [flagName, flagValue] of Object.entries(flags)) {
        if (typeof flagValue === 'boolean') {
            if (flagValue) {
                args.push(flagName);
            }
        } else {
            args.push(flagName);
            args.push(String(flagValue));
        }
    }
    
    console.log('✅ Validation passed. Executing command:', command, args);
    
    // Show terminal container and execute
    const terminalContainer = document.getElementById('terminalContainer');
    const tabNavigation = document.getElementById('tabNavigation');
    
    if (terminalContainer) terminalContainer.style.display = 'block';
    if (tabNavigation) tabNavigation.style.display = 'flex';
    
    // Execute the command using the existing executeCommand function
    executeCommand(command, args);
}

// Update agent results in Summary tab
function updateAgentResultsSummary(output) {
    try {
        const summaryContainer = document.getElementById('analysisSummary');
        if (!summaryContainer) return;
        
        // Parse agent results from rich terminal output
        // Look for agent result panels (the ones from agent_output_display.py)
        const agentResultPattern = /(?:✅|❌)\s+(\w+Agent)\s+Result.*?Confidence:\s*([\d.]+)%.*?Execution Time:\s*([\d.]+)s/gs;
        const agentMatches = [...output.matchAll(agentResultPattern)];
        
        if (agentMatches.length > 0) {
            let html = '<div class="agent-results-section">';
            html += '<h3 style="color:#fff;margin-bottom:20px;">🤖 Multi-Agent Workflow Results</h3>';
            html += '<div class="agent-results-grid">';
            
            agentMatches.forEach(match => {
                const agentName = match[1];
                const confidence = parseFloat(match[2]);
                const executionTime = parseFloat(match[3]);
                const success = output.includes(`✅ ${agentName}`);
                
                const confidenceColor = confidence >= 90 ? '#10b981' : confidence >= 70 ? '#f59e0b' : '#ef4444';
                const statusIcon = success ? '✅' : '❌';
                
                html += `
                    <div class="agent-result-card">
                        <div class="agent-header">
                            <span class="agent-status">${statusIcon}</span>
                            <span class="agent-name">${agentName}</span>
                        </div>
                        <div class="agent-metrics">
                            <div class="metric">
                                <span class="metric-label">Confidence</span>
                                <span class="metric-value" style="color:${confidenceColor}">${confidence.toFixed(1)}%</span>
                            </div>
                            <div class="metric">
                                <span class="metric-label">Time</span>
                                <span class="metric-value">${executionTime.toFixed(2)}s</span>
                            </div>
                        </div>
                    </div>
                `;
            });
            
            html += '</div></div>';
            
            // Prepend to summary container
            const tempDiv = document.createElement('div');
            tempDiv.innerHTML = html;
            summaryContainer.insertBefore(tempDiv.firstChild, summaryContainer.firstChild);
        }
        
        // Also parse the summary table if present
        const summaryTableMatch = output.match(/Analysis Complete.*?\n([\s\S]*?)(?:\n\n|$)/);
        if (summaryTableMatch) {
            // Add a visual representation of the agent summary table
            const tableSection = document.createElement('div');
            tableSection.className = 'agent-summary-table';
            tableSection.innerHTML = '<h4 style="color:#9ca3af;margin:20px 0 10px 0;">Agent Execution Summary</h4><pre style="background:#0a0a0a;padding:15px;border-radius:8px;overflow-x:auto;font-size:12px;">' + summaryTableMatch[1] + '</pre>';
            summaryContainer.appendChild(tableSection);
        }
        
    } catch (error) {
        console.error('Error updating agent results summary:', error);
    }
}

// Update analysis tabs with parsed content
function updateAnalysisTabs(output) {
    try {
        // Parse Gamma URL
        const gammaUrlMatch = output.match(/(?:Gamma URL|📊 Gamma URL):\s*(https:\/\/gamma\.app\/[^\s]+)/i);
        if (gammaUrlMatch) {
            const gammaUrl = gammaUrlMatch[1];
            const gammaLinksContainer = document.querySelector('#gammaLinks .gamma-links');
            if (gammaLinksContainer) {
                // Parse additional Gamma metadata
                const creditsMatch = output.match(/(?:Credits used|💳 Credits used):\s*(\d+)/i);
                const timeMatch = output.match(/(?:Generation time|⏱️\s+Generation time):\s*([\d.]+)s/i);
                
                gammaLinksContainer.innerHTML = `
                    <a href="${gammaUrl}" target="_blank" class="gamma-link-large">
                        <span class="gamma-icon">📊</span>
                        <span>Open Gamma Presentation</span>
                        <span class="arrow">→</span>
                    </a>
                    <div class="gamma-meta">
                        ${creditsMatch ? `<div class="meta-item"><strong>Credits used:</strong> ${creditsMatch[1]}</div>` : ''}
                        ${timeMatch ? `<div class="meta-item"><strong>Generation time:</strong> ${timeMatch[1]}s</div>` : ''}
                    </div>
                    <div class="url-copy">
                        <code>${gammaUrl}</code>
                        <button onclick="copyToClipboard('${gammaUrl}')" class="copy-btn">📋 Copy</button>
                    </div>
                `;
            }
        }
        
        // Parse and populate Files tab
        const allFileMatches = output.matchAll(/(?:📁|saved|exported|generated).*?:\s*([^\n]+\.(json|md|txt|pdf|csv))/gi);
        const allFiles = [];
        const auditFiles = [];
        
        for (const match of allFileMatches) {
            const filePath = match[1].trim();
            const ext = match[2].toUpperCase();
            const fileName = filePath.split('/').pop();
            const fileInfo = { path: filePath, type: ext, name: fileName };
            
            // Check if this is an audit trail file
            if (fileName.includes('audit_trail')) {
                auditFiles.push(fileInfo);
            }
            
            allFiles.push(fileInfo);
        }
        
        if (allFiles.length > 0) {
            const filesListContainer = document.querySelector('#filesList .files-list');
            if (filesListContainer) {
                let html = '';
                
                // Show audit trail section first if available
                if (auditFiles.length > 0) {
                    html += `
                        <div class="tab-section audit-trail-section">
                            <h3>📋 Audit Trail</h3>
                            <p class="audit-description" style="color: #a78bfa; font-size: 13px; margin-bottom: 15px;">
                                Detailed execution log with decisions, data quality checks, and timestamps.
                            </p>
                            <div class="file-list">
                    `;
                    
                    auditFiles.forEach(file => {
                        html += `
                            <div class="download-item" style="background: rgba(139, 92, 246, 0.1); border-left: 3px solid #8b5cf6;">
                                <div class="file-details">
                                    <span class="file-icon-small">📋</span>
                                    <span class="file-name-small">${file.name}</span>
                                </div>
                                <div style="display: flex; gap: 8px;">
                                    <button onclick="downloadFile('${file.path}')" class="download-btn-small">
                                        📥 Download
                                    </button>
                                    <a href="/outputs/${file.path}" target="_blank" class="download-btn-small" style="text-decoration: none;">
                                        👁️ View
                                    </a>
                                </div>
                            </div>
                        `;
                    });
                    
                    html += '</div></div>';
                }
                
                // Group remaining files by type (excluding audit trails)
                const regularFiles = allFiles.filter(f => !f.name.includes('audit_trail'));
                const filesByType = {
                    'JSON': regularFiles.filter(f => f.type === 'JSON'),
                    'MD': regularFiles.filter(f => f.type === 'MD'),
                    'TXT': regularFiles.filter(f => f.type === 'TXT'),
                    'PDF': regularFiles.filter(f => f.type === 'PDF'),
                    'CSV': regularFiles.filter(f => f.type === 'CSV')
                };
                
                html += '<div class="tab-section"><h3>📦 All Generated Files</h3>';
                
                for (const [type, files] of Object.entries(filesByType)) {
                    if (files.length > 0) {
                        html += `<div class="file-group">
                            <h4 class="file-group-title">${type} Files (${files.length})</h4>
                            <div class="file-list">`;
                        
                        files.forEach(file => {
                            const icon = type === 'JSON' ? '📊' : type === 'MD' ? '📝' : type === 'TXT' ? '📄' : type === 'PDF' ? '📑' : '📎';
                            html += `
                                <div class="download-item">
                                    <div class="file-details">
                                        <span class="file-icon-small">${icon}</span>
                                        <span class="file-name-small">${file.name}</span>
                                    </div>
                                    <button onclick="downloadFile('${file.path}')" class="download-btn-small">
                                        📥 Download
                                    </button>
                                </div>
                            `;
                        });
                        
                        html += '</div></div>';
                    }
                }
                
                html += '</div>';
                filesListContainer.innerHTML = html;
            }
        }
        
    } catch (error) {
        console.error('Error updating analysis tabs:', error);
    }
}

// Copy to clipboard helper
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        alert('URL copied to clipboard!');
    }).catch(err => {
        console.error('Failed to copy:', err);
        alert('Failed to copy URL');
    });
}

// Download file function
async function downloadFile(filePath) {
    try {
        const response = await fetch(`/download?file=${encodeURIComponent(filePath)}`);
        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filePath.split('/').pop();
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
        } else {
            alert('Failed to download file');
        }
    } catch (error) {
        console.error('Download error:', error);
        alert('Error downloading file');
    }
}

// View JSON file function
async function viewJSON(filePath) {
    try {
        const response = await fetch(`/download?file=${encodeURIComponent(filePath)}`);
        if (response.ok) {
            const jsonText = await response.text();
            const jsonData = JSON.parse(jsonText);
            
            // Create modal to display JSON
            const modal = document.createElement('div');
            modal.style = 'position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.8);display:flex;align-items:center;justify-content:center;z-index:10000;';
            modal.innerHTML = `
                <div style="background:#1a1a1a;padding:30px;border-radius:10px;max-width:90%;max-height:90%;overflow:auto;color:#fff;">
                    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;">
                        <h3 style="margin:0;">📊 ${filePath.split('/').pop()}</h3>
                        <button onclick="this.parentElement.parentElement.parentElement.remove()" style="background:#dc2626;color:#fff;border:none;padding:8px 16px;border-radius:6px;cursor:pointer;">Close</button>
                    </div>
                    <pre style="background:#0d0d0d;padding:20px;border-radius:6px;overflow:auto;max-height:70vh;"><code>${JSON.stringify(jsonData, null, 2)}</code></pre>
                </div>
            `;
            document.body.appendChild(modal);
            modal.onclick = (e) => { if (e.target === modal) modal.remove(); };
        } else {

// Display audit trail badge if audit files are detected
function displayAuditTrailBadge(output) {
    try {
        // Look for audit trail file mentions in output
        const auditMatch = output.match(/audit_trail_[^\s]+\.md/i);
        if (auditMatch) {
            const terminalTitle = document.getElementById('terminalTitle');
            if (terminalTitle && !terminalTitle.querySelector('.audit-badge')) {
                const badge = document.createElement('span');
                badge.className = 'badge audit-badge';
                badge.style.cssText = 'background: rgba(139, 92, 246, 0.2); color: #a78bfa; margin-left: 10px; padding: 4px 12px; border-radius: 12px; font-size: 11px; font-weight: 600;';
                badge.textContent = '📋 Audit Trail Available';
                badge.title = 'Detailed execution audit trail generated';
                terminalTitle.appendChild(badge);
            }
        }
    } catch (error) {
        console.error('Error displaying audit trail badge:', error);
    }
}
            alert('Failed to load JSON file');
        }
    } catch (error) {
        console.error('View JSON error:', error);
        alert('Error viewing JSON file');
    }
}

// Update analysis info panels based on selected type
function updateAnalysisOptions() {
    const analysisType = document.getElementById('analysisType');
    const individualInfo = document.getElementById('individualBreakdownInfo');
    const coachingInfo = document.getElementById('coachingReportInfo');
    const teamInfo = document.getElementById('teamOverviewInfo');
    
    if (!analysisType) return;
    
    const value = analysisType.value;
    
    // Hide all info panels first
    if (individualInfo) individualInfo.style.display = 'none';
    if (coachingInfo) coachingInfo.style.display = 'none';
    if (teamInfo) teamInfo.style.display = 'none';
    
    // Show relevant panel based on selection
    if (value.includes('individual')) {
        if (individualInfo) individualInfo.style.display = 'block';
    } else if (value.includes('coaching')) {
        if (coachingInfo) coachingInfo.style.display = 'block';
    } else if (value.includes('team') || value === 'agent-performance-escalated') {
        if (teamInfo) teamInfo.style.display = 'block';
    }
}

// Event listener for custom date inputs
document.addEventListener('DOMContentLoaded', function() {
    const timePeriodSelect = document.getElementById('timePeriod');
    if (timePeriodSelect) {
        timePeriodSelect.addEventListener('change', function() {
            const customInputs = document.getElementById('customDateInputs');
            if (customInputs) {
                customInputs.style.display = this.value === 'custom' ? 'block' : 'none';
            }
        });
    }
    
    // Initialize analysis options visibility
    updateAnalysisOptions();
});
