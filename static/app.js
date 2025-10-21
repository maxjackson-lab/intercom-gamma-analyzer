// VERSION MARKER: v3.0.2-f5d29d0 - If you see this, the latest code is deployed
console.log('✅ JavaScript v3.0.2-f5d29d0 loaded successfully');

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
    
    // Handle help queries directly if chat interface might fail
    const lowerQuery = query.toLowerCase();
    if (lowerQuery.includes('help') || lowerQuery.includes('available commands') || lowerQuery.includes('what commands')) {
        input.disabled = false;
        button.disabled = false;
        button.textContent = 'Send';
        
        addMessage('bot', `<strong>Available Commands:</strong><br>
            • voice-of-customer --start-date YYYY-MM-DD --end-date YYYY-MM-DD --generate-gamma<br>
            • billing-analysis --generate-gamma<br>
            • tech-analysis --days 7<br>
            • api-analysis --generate-gamma<br>
            • canny-analysis --generate-gamma --start-date YYYY-MM-DD --end-date YYYY-MM-DD<br><br>
            <strong>Analysis Modes:</strong><br>
            Use the dropdown above to choose: Topic-Based (Hilary's format), Synthesis (Insights), or Complete (Both)`);
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
    try {
        // Get analysis mode selection
        const analysisModeSelect = document.getElementById('analysisMode');
        const analysisMode = analysisModeSelect ? analysisModeSelect.value : 'topic-based';
        
        // Convert CLI command to full python execution
        // voice-of-customer → python src/main.py voice-of-customer
        const fullCommand = 'python';
        let fullArgs = ['src/main.py', command, ...args];
        
        // Always add multi-agent flags on this branch
        fullArgs.push('--multi-agent');
        fullArgs.push('--analysis-type');
        fullArgs.push(analysisMode);
        
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
