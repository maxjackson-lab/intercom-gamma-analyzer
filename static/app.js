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
                    
                    // Parse and populate tabs
                    updateAnalysisTabs(fullOutput);
                    
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


// Form-based analysis execution handler
function runAnalysis() {
    // Get form values with validation
    const analysisType = document.getElementById('analysisType');
    const timePeriod = document.getElementById('timePeriod');
    const dataSource = document.getElementById('dataSource');
    const taxonomyFilter = document.getElementById('taxonomyFilter');
    const outputFormat = document.getElementById('outputFormat');
    
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
    
    // Build command based on analysis type
    let command = '';
    let args = [];
    
    // Map analysis type to command
    if (analysisValue === 'voice-of-customer-hilary') {
        command = 'voice-of-customer';
        args.push('--multi-agent', '--analysis-type', 'topic-based');
    } else if (analysisValue === 'voice-of-customer-synthesis') {
        command = 'voice-of-customer';
        args.push('--multi-agent', '--analysis-type', 'synthesis');
    } else if (analysisValue === 'voice-of-customer-complete') {
        command = 'voice-of-customer';
        args.push('--multi-agent', '--analysis-type', 'complete');
    } else if (analysisValue === 'agent-performance-horatio') {
        command = 'agent-performance';
        args.push('--agent', 'horatio');
    } else if (analysisValue === 'agent-performance-boldr') {
        command = 'agent-performance';
        args.push('--agent', 'boldr');
    } else {
        command = analysisValue;
    }
    
    // Add time period or custom dates
    if (timeValue === 'custom') {
        const startDate = document.getElementById('startDate');
        const endDate = document.getElementById('endDate');
        
        if (!startDate || !endDate || !startDate.value || !endDate.value) {
            alert('Please select both start and end dates');
            return;
        }
        
        args.push('--start-date', startDate.value, '--end-date', endDate.value);
    } else {
        args.push('--time-period', timeValue);
    }
    
    // Add data source flags
    if (sourceValue === 'canny') {
        command = 'canny-analysis';
    } else if (sourceValue === 'both') {
        args.push('--include-canny');
    }
    
    // Add taxonomy filter if selected
    if (filterValue) {
        args.push('--focus-areas', filterValue);
    }
    
    // Add output format
    if (formatValue === 'gamma') {
        args.push('--generate-gamma');
    }
    
    // Show terminal container and execute
    const terminalContainer = document.getElementById('terminalContainer');
    const tabNavigation = document.getElementById('tabNavigation');
    
    if (terminalContainer) terminalContainer.style.display = 'block';
    if (tabNavigation) tabNavigation.style.display = 'flex';
    
    // Execute the command using the existing executeCommand function
    executeCommand(command, args);
}

// Update analysis tabs with parsed content
function updateAnalysisTabs(output) {
    try {
        // Parse Gamma URL
        const gammaUrlMatch = output.match(/(?:Gamma URL|📊 Gamma URL):\s*(https:\/\/gamma\.app\/[^\s]+)/i);
        if (gammaUrlMatch) {
            const gammaUrl = gammaUrlMatch[1];
            const gammaContent = document.getElementById('gamma-content');
            if (gammaContent) {
                // Parse additional Gamma metadata
                const creditsMatch = output.match(/(?:Credits used|💳 Credits used):\s*(\d+)/i);
                const timeMatch = output.match(/(?:Generation time|⏱️\s+Generation time):\s*([\d.]+)s/i);
                
                gammaContent.innerHTML = `
                    <div class="tab-section">
                        <h3>🎨 Gamma Presentation Generated</h3>
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
                    </div>
                `;
            }
        }
        
        // Parse Output Files
        const outputMatches = output.matchAll(/(?:📁|saved to|Report saved|Full results):\s*([^\n]+\.(json|md))/gi);
        const outputFiles = [];
        for (const match of outputMatches) {
            const filePath = match[1].trim();
            const fileType = match[2].toUpperCase();
            outputFiles.push({ path: filePath, type: fileType });
        }
        
        if (outputFiles.length > 0) {
            const outputContent = document.getElementById('output-content');
            if (outputContent) {
                // Get the main JSON file (usually the first or most recent)
                const mainFile = outputFiles.find(f => f.type === 'JSON') || outputFiles[0];
                const fileName = mainFile.path.split('/').pop();
                
                outputContent.innerHTML = `
                    <div class="tab-section">
                        <h3>📄 Analysis Results</h3>
                        <div class="file-primary">
                            <div class="file-icon">${mainFile.type === 'JSON' ? '📊' : '📝'}</div>
                            <div class="file-info">
                                <div class="file-name">${fileName}</div>
                                <div class="file-path"><code>${mainFile.path}</code></div>
                            </div>
                        </div>
                        <div class="file-actions">
                            <button onclick="downloadFile('${mainFile.path}')" class="action-btn primary">
                                📥 Download ${mainFile.type}
                            </button>
                            ${mainFile.type === 'JSON' ? `<button onclick="viewJSON('${mainFile.path}')" class="action-btn secondary">👁️ View Data</button>` : ''}
                        </div>
                    </div>
                `;
            }
        }
        
        // Parse Download Links (all files)
        const allFileMatches = output.matchAll(/(?:📁|saved|exported|generated).*?:\s*([^\n]+\.(json|md|txt|pdf|csv))/gi);
        const allFiles = [];
        for (const match of allFileMatches) {
            const filePath = match[1].trim();
            const ext = match[2].toUpperCase();
            const fileName = filePath.split('/').pop();
            allFiles.push({ path: filePath, type: ext, name: fileName });
        }
        
        if (allFiles.length > 0) {
            const downloadContent = document.getElementById('download-content');
            if (downloadContent) {
                // Group files by type
                const filesByType = {
                    'JSON': allFiles.filter(f => f.type === 'JSON'),
                    'MD': allFiles.filter(f => f.type === 'MD'),
                    'TXT': allFiles.filter(f => f.type === 'TXT'),
                    'PDF': allFiles.filter(f => f.type === 'PDF'),
                    'CSV': allFiles.filter(f => f.type === 'CSV')
                };
                
                let html = '<div class="tab-section"><h3>📦 All Generated Files</h3>';
                
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
                downloadContent.innerHTML = html;
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
            alert('Failed to load JSON file');
        }
    } catch (error) {
        console.error('View JSON error:', error);
        alert('Error viewing JSON file');
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
});
