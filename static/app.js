/**
 * app.js - Shared Utilities
 * 
 * This file contains reusable utility functions for the Intercom Analysis Tool.
 * Timeline-specific logic is in timeline.js
 */

console.log('✅ Shared utilities loaded successfully');

// Global error handler - catch all JavaScript errors and display them
window.onerror = function(msg, url, lineNo, columnNo, error) {
    console.error('🚨 Global JavaScript Error:', msg, 'at line', lineNo);
    return false; // Let browser handle it
};

/**
 * Copy text to clipboard
 */
function copyToClipboard(text) {
    if (!text) {
        console.error('copyToClipboard called with no text');
            return;
        }
        
    navigator.clipboard.writeText(text).then(() => {
        console.log('Copied to clipboard:', text);
        showToast('Copied to clipboard!', 'success');
    }).catch(err => {
        console.error('Failed to copy:', err);
        showToast('Failed to copy to clipboard', 'error');
    });
}

/**
 * Download file from server
 */
async function downloadFile(filename) {
    if (!filename) {
        console.error('downloadFile called with no filename');
        return;
    }
    
    try {
        const response = await fetch(`/download?file=${encodeURIComponent(filename)}`);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename.split('/').pop(); // Get just the filename
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        
        console.log('Downloaded file:', filename);
        showToast('File downloaded successfully', 'success');
    } catch (error) {
        console.error('Download error:', error);
        showToast(`Failed to download file: ${error.message}`, 'error');
    }
}

/**
 * View JSON in modal
 */
async function viewJsonFile(filename) {
    if (!filename) {
        console.error('viewJsonFile called with no filename');
        return;
    }
    
    try {
        const response = await fetch(`/download?file=${encodeURIComponent(filename)}`);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const jsonText = await response.text();
        const jsonData = JSON.parse(jsonText);
        
        // Create modal to display JSON
        const modal = document.createElement('div');
        modal.className = 'modal-overlay';
        modal.innerHTML = `
            <div class="modal-content">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;">
                    <h3 style="margin:0;color:#fff;">📊 ${filename.split('/').pop()}</h3>
                    <button class="modal-close" onclick="this.parentElement.parentElement.parentElement.remove()">×</button>
            </div>
                <pre style="background:#0a0a0a;padding:20px;border-radius:8px;overflow:auto;max-height:70vh;color:#e5e7eb;"><code>${JSON.stringify(jsonData, null, 2)}</code></pre>
        </div>
    `;
        document.body.appendChild(modal);
        
        // Close modal when clicking outside
        modal.onclick = (e) => {
            if (e.target === modal) {
                modal.remove();
            }
        };
        
    } catch (error) {
        console.error('View JSON error:', error);
        showToast(`Failed to load JSON file: ${error.message}`, 'error');
    }
}

/**
 * Show toast message
 */
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 16px 24px;
        background: ${type === 'success' ? '#10b981' : type === 'error' ? '#ef4444' : '#3b82f6'};
        color: white;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
        z-index: 10000;
        font-size: 14px;
        font-weight: 500;
        animation: slideInRight 0.3s ease-out;
    `;
    toast.textContent = message;
    
    document.body.appendChild(toast);
    
    // Auto-remove after 3 seconds
    setTimeout(() => {
        toast.style.animation = 'slideOutRight 0.3s ease-out';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

/**
 * Format date to readable string
 */
function formatDate(dateString) {
    if (!dateString) return 'Unknown';
    
    const date = new Date(dateString);
    const options = { year: 'numeric', month: 'short', day: 'numeric' };
    return date.toLocaleDateString('en-US', options);
}

/**
 * Format number with K/M suffixes
 */
function formatNumber(num) {
    if (num >= 1000000) {
        return (num / 1000000).toFixed(1) + 'M';
    } else if (num >= 1000) {
        return (num / 1000).toFixed(1) + 'K';
    }
    return num.toString();
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return text.replace(/[&<>"']/g, m => map[m]);
}

/**
 * Parse query string parameters
 */
function getQueryParams() {
    const params = {};
    const queryString = window.location.search.substring(1);
    const pairs = queryString.split('&');
    
    for (const pair of pairs) {
        if (pair) {
            const [key, value] = pair.split('=');
            params[decodeURIComponent(key)] = decodeURIComponent(value || '');
        }
    }
    
    return params;
}

// Export functions to window for global access
window.copyToClipboard = copyToClipboard;
window.downloadFile = downloadFile;
window.viewJsonFile = viewJsonFile;
window.showToast = showToast;
window.formatDate = formatDate;
window.formatNumber = formatNumber;
window.escapeHtml = escapeHtml;
window.getQueryParams = getQueryParams;

// Add CSS for toast animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideInRight {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes slideOutRight {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);

console.log('✅ Shared utilities initialized');

/**
 * ============================================================================
 * Analysis Form Management
 * Functions for running analysis and managing the web UI form
 * ============================================================================
 */

// Store current execution ID
let currentExecutionId = null;

/**
 * Main function to run analysis from form
 */
async function runAnalysis() {
    console.log('🚀 runAnalysis() called');
    
    try {
        // Get form values
        const analysisType = document.getElementById('analysisType')?.value;
        const timePeriod = document.getElementById('timePeriod')?.value;
        const dataSource = document.getElementById('dataSource')?.value;
        const taxonomyFilter = document.getElementById('taxonomyFilter')?.value;
        const outputFormat = document.getElementById('outputFormat')?.value;
        const aiModel = document.getElementById('aiModel')?.value;
        const testMode = document.getElementById('testMode')?.checked || false;
        const auditMode = document.getElementById('auditMode')?.checked || false;
        
        // Get test mode options if enabled
        const testDataCount = document.getElementById('testDataCount')?.value || '100';
        const verboseLogging = document.getElementById('verboseLogging')?.checked || false;
        
        // Get sample mode options if sample-mode selected
        const sampleCount = document.getElementById('sampleCount')?.value || '50';
        const sampleTimePeriod = document.getElementById('sampleTimePeriod')?.value || 'week';
        
        // Get custom dates if "custom" time period selected
        const startDate = document.getElementById('startDate')?.value || null;
        const endDate = document.getElementById('endDate')?.value || null;
        
        console.log('Form values:', {
            analysisType, timePeriod, dataSource, outputFormat, 
            aiModel, testMode, auditMode, taxonomyFilter
        });
        
        // Build command based on analysis type
        let command = 'python';
        let args = ['src/main.py'];
        
        // Map web UI analysis types to CLI commands
        if (analysisType === 'sample-mode') {
            const schemaMode = document.getElementById('schemaMode')?.value || 'standard';
            const sampleTimePeriod = document.getElementById('sampleTimePeriod')?.value || 'week';
            const sampleAiModel = document.getElementById('sampleAiModel')?.value || 'openai';
            const includeHierarchy = document.getElementById('includeHierarchy')?.checked ?? true;
            const testAllAgents = document.getElementById('testAllAgents')?.checked ?? false;
            const showAgentThinking = document.getElementById('showAgentThinking')?.checked ?? false;
            const llmTopicDetection = document.getElementById('llmTopicDetection')?.checked ?? false;
            
            args.push('sample-mode');
            args.push('--time-period', sampleTimePeriod);
            args.push('--save-to-file');  // Always save JSON and .log file
            args.push('--test-llm');  // Always run LLM sentiment test
            args.push('--schema-mode', schemaMode);  // User-selected depth
            args.push('--ai-model', sampleAiModel);  // AI model for LLM test (from sample-mode panel)
            
            // Add hierarchy flag (only send --no-hierarchy if unchecked, since default is true)
            if (!includeHierarchy) {
                args.push('--no-hierarchy');
            }
            
            // Add test-all-agents flag if checked
            if (testAllAgents) {
                args.push('--test-all-agents');
            }
            
            // Add show-agent-thinking flag if checked
            if (showAgentThinking) {
                args.push('--show-agent-thinking');
            }
            
            // Add llm-topic-detection flag if checked
            if (llmTopicDetection) {
                args.push('--llm-topic-detection');
            }
            
        } else if (analysisType === 'voice-of-customer-hilary') {
            args.push('voice-of-customer');
            args.push('--analysis-type', 'topic-based');
            args.push('--multi-agent');
            
            // LLM topic detection if checkbox enabled
            const llmTopicDetectionVoc = document.getElementById('llmTopicDetectionVoc')?.checked ?? false;
            if (llmTopicDetectionVoc) {
                args.push('--llm-topic-detection');
            }
            
        } else if (analysisType === 'voice-of-customer-synthesis') {
            args.push('voice-of-customer');
            args.push('--analysis-type', 'synthesis');
            args.push('--multi-agent');
            
            // LLM topic detection if checkbox enabled
            const llmTopicDetectionVoc = document.getElementById('llmTopicDetectionVoc')?.checked ?? false;
            if (llmTopicDetectionVoc) {
                args.push('--llm-topic-detection');
            }
            
        } else if (analysisType === 'voice-of-customer-complete') {
            args.push('voice-of-customer');
            args.push('--analysis-type', 'complete');
            args.push('--multi-agent');
            
            // LLM topic detection if checkbox enabled
            const llmTopicDetectionVoc = document.getElementById('llmTopicDetectionVoc')?.checked ?? false;
            if (llmTopicDetectionVoc) {
                args.push('--llm-topic-detection');
            }
            
        } else if (analysisType.startsWith('agent-performance-')) {
            args.push('agent-performance');
            
            // Extract agent type
            if (analysisType.includes('horatio')) {
                args.push('--agent', 'horatio');
            } else if (analysisType.includes('boldr')) {
                args.push('--agent', 'boldr');
            } else if (analysisType.includes('escalated')) {
                args.push('--agent', 'escalated');
            }
            
            // Check if individual breakdown
            if (analysisType.includes('individual')) {
                args.push('--individual-breakdown');
            }
            
        } else if (analysisType.startsWith('agent-coaching-')) {
            args.push('agent-coaching-report');
            
            // Extract vendor
            if (analysisType.includes('horatio')) {
                args.push('--vendor', 'horatio');
            } else if (analysisType.includes('boldr')) {
                args.push('--vendor', 'boldr');
            }
            
        } else if (analysisType === 'canny-analysis') {
            args.push('canny-analysis');
            
        } else if (analysisType.startsWith('analyze-')) {
            // Category commands: analyze-billing, analyze-product, etc.
            args.push(analysisType);
            
        } else if (analysisType === 'tech-analysis') {
            args.push('tech-analysis');
            
        } else {
            showToast('Unknown analysis type: ' + analysisType, 'error');
            return;
        }
        
        // Add time period (unless it's sample-mode - it handles it internally)
        if (analysisType !== 'sample-mode') {
            if (timePeriod === 'custom' && startDate && endDate) {
                args.push('--start-date', startDate);
                args.push('--end-date', endDate);
            } else if (timePeriod !== 'custom' && timePeriod) {
                args.push('--time-period', timePeriod);
            }
        }
        
        // Add AI model (skip for sample-mode - it handles it internally)
        if (aiModel && analysisType !== 'sample-mode') {
            args.push('--ai-model', aiModel);
        }
        
        // Add output format / generate gamma (skip for sample-mode)
        if (analysisType !== 'sample-mode') {
            if (outputFormat === 'gamma') {
                args.push('--generate-gamma');
            } else if (outputFormat && !analysisType.startsWith('voice-of-customer')) {
                args.push('--output-format', outputFormat);
            }
        }
        
        // Add test mode flags (skip for sample-mode)
        if (testMode && analysisType !== 'sample-mode') {
            args.push('--test-mode');
            if (testDataCount) {
                args.push('--test-data-count', testDataCount);
            }
        }
        
        // Add verbose flag (skip for sample-mode - it has its own verbosity)
        if (verboseLogging && analysisType !== 'sample-mode') {
            args.push('--verbose');
        }
        
        // Add audit trail (skip for sample-mode - diagnostic tool only)
        if (auditMode && analysisType !== 'sample-mode') {
            args.push('--audit-trail');
        }
        
        // Handle data source
        if (dataSource === 'canny' && analysisType.startsWith('voice-of-customer')) {
            // Switch to canny-analysis
            args = ['src/main.py', 'canny-analysis'];
            if (timePeriod !== 'custom') {
                args.push('--time-period', timePeriod);
            }
        } else if (dataSource === 'both' && analysisType.startsWith('voice-of-customer')) {
            args.push('--include-canny');
        }
        
        // Add taxonomy filter if specified (now supported in CLI)
        if (taxonomyFilter && taxonomyFilter !== '') {
            // Apply to voice-of-customer, agent-performance, and category commands
            if (analysisType.startsWith('voice-of-customer') || 
                analysisType.startsWith('agent-performance') ||
                analysisType.startsWith('analyze-')) {
                args.push('--filter-category', taxonomyFilter);
                console.log('Applied taxonomy filter:', taxonomyFilter);
            }
        }
        
        console.log('Executing command:', command, args);
        
        // Generate execution ID
        currentExecutionId = 'exec_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
        
        // Show terminal container
        const terminalContainer = document.getElementById('terminalContainer');
        if (terminalContainer) {
            terminalContainer.style.display = 'block';
        }
        
        // Clear previous output
        const terminalOutput = document.getElementById('terminalOutput');
        if (terminalOutput) {
            terminalOutput.innerHTML = '<div class="terminal-line">Starting analysis...</div>';
        }
        
        // Show spinner and status
        const spinner = document.getElementById('executionSpinner');
        const status = document.getElementById('executionStatus');
        const cancelBtn = document.getElementById('cancelButton');
        const tabNav = document.getElementById('tabNavigation');
        
        if (spinner) spinner.style.display = 'inline-block';
        if (status) {
            status.textContent = 'Running';
            status.className = 'status-badge';
            status.style.display = 'inline-block';
        }
        if (cancelBtn) cancelBtn.style.display = 'inline-block';
        if (tabNav) tabNav.style.display = 'flex';
        
        // Switch to terminal tab
        switchTab('terminal');
        
        // Determine if this is a long-running task that should use background execution
        const isLongRunning = shouldUseBackgroundExecution(args, timePeriod);
        
        if (isLongRunning) {
            // Use background execution for long-running tasks
            console.log('🔄 Using background execution (long-running task detected)');
            appendToTerminal('ℹ️ Long-running task detected - using background execution mode\n', 'status');
            await runBackgroundExecution(command, args);
        } else {
            // Use SSE streaming for quick tasks
            console.log('⚡ Using SSE streaming (quick task)');
            await runSSEExecution(command, args);
        }
        
        
    } catch (error) {
        console.error('Error in runAnalysis():', error);
        showToast('Error starting analysis: ' + error.message, 'error');
    }
}

/**
 * Determine if task should use background execution based on command args
 */
function shouldUseBackgroundExecution(args, timePeriod) {
    // Check for long-running indicators
    const hasMultiAgent = args.includes('--multi-agent');
    const hasGamma = args.includes('--generate-gamma') || args.includes('--output-format') && args.includes('gamma');
    const isLongPeriod = ['week', 'month', 'quarter', '6-weeks'].includes(timePeriod);
    const isVoC = args.includes('voice-of-customer');
    const isAgentPerformance = args.includes('agent-performance') || args.includes('agent-coaching-report');
    const isSampleMode = args.includes('sample-mode');
    const schemaMode = args.includes('--schema-mode') ? args[args.indexOf('--schema-mode') + 1] : null;
    const isSchemaDumpPath = isSampleMode && args.includes('--schema-mode') && args.includes('--save-to-file') && args.includes('--test-llm');
    
    // Use background execution if:
    // 1. Multi-agent analysis (always long-running)
    // 2. Week or longer with Gamma generation
    // 3. Agent performance/coaching (database-heavy)
    // 4. Sample-mode in deep/comprehensive mode (enrichment takes long)
    if (hasMultiAgent) {
        console.log('→ Background mode: multi-agent analysis detected');
        return true;
    }
    
    if (isLongPeriod && hasGamma) {
        console.log('→ Background mode: long period + Gamma generation');
        return true;
    }
    
    if (isAgentPerformance && isLongPeriod) {
        console.log('→ Background mode: agent performance on long period');
        return true;
    }
    
    if (isSchemaDumpPath) {
        console.log('→ Background mode: schema dump detected (always background)');
        return true;
    }
    
    if (isSampleMode && schemaMode && ['deep', 'comprehensive'].includes(schemaMode)) {
        console.log(`→ Background mode: sample-mode in ${schemaMode} mode (long enrichment)`);
        return true;
    }
    
    // Default to SSE for quick tasks
    console.log('→ SSE mode: quick task');
    return false;
}

/**
 * Run command using background execution (recommended for production)
 */
async function runBackgroundExecution(command, args) {
    try {
        const token = localStorage.getItem('api_token') || '';
        
        // Start background task using query parameters (matching /execute/start endpoint)
        const params = new URLSearchParams({
            command: command,
            args: JSON.stringify(args)
        });
        
        const response = await fetch(`/execute/start?${params}`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (!response.ok) {
            throw new Error(`Failed to start execution: ${response.status}`);
        }
        
        const result = await response.json();
        currentExecutionId = result.execution_id;
        
        // Save execution ID to localStorage for recovery after page refresh
        localStorage.setItem('active_execution_id', currentExecutionId);
        localStorage.setItem('active_execution_start', Date.now());
        
        appendToTerminal(`✓ Task queued with ID: ${currentExecutionId}\n`, 'status');
        appendToTerminal('⏳ Polling for status updates...\n\n', 'status');
        appendToTerminal('💡 Tip: You can close this window - the task will continue running\n', 'status');
        
        // Request notification permission for completion alerts
        requestNotificationPermission();
        
        // Poll for status updates
        await pollExecutionStatus(currentExecutionId, token);
        
    } catch (error) {
        console.error('Background execution error:', error);
        appendToTerminal(`\n❌ Failed to start background execution: ${error.message}`, 'error');
        showToast('Failed to start analysis: ' + error.message, 'error');
        
        const spinner = document.getElementById('executionSpinner');
        const status = document.getElementById('executionStatus');
        if (spinner) spinner.style.display = 'none';
        if (status) {
            status.textContent = 'Failed ✗';
            status.className = 'status-badge status-error';
        }
    }
}

/**
 * Poll execution status until completion
 */
async function pollExecutionStatus(executionId, token) {
    const pollInterval = 3000; // 3 seconds
    let lastDuration = 0;
    let lastOutputIndex = 0; // Track which outputs we've already displayed
    
    while (true) {
        try {
            // Fetch status with incremental output using 'since' parameter
            const response = await fetch(`/execute/status/${executionId}?since=${lastOutputIndex}`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            
            if (!response.ok) {
                throw new Error(`Status check failed: ${response.status}`);
            }
            
            const statusData = await response.json();
            const currentStatus = statusData.status;
            const duration = statusData.duration_seconds || 0;
            const newOutput = statusData.output || []; // Fixed: API returns 'output' not 'output_buffer'
            
            // Display new output in real-time (shows "Fetching X conversations..." etc.)
            if (newOutput.length > 0) {
                newOutput.forEach(outputItem => {
                    const outputText = outputItem.data || outputItem.message || '';
                    const outputType = outputItem.type || 'stdout';
                    
                    if (outputText) {
                        appendToTerminal(outputText, outputType);
                        parseOutputForTabs(outputText);
                    }
                });
                
                // Update index to avoid showing same output again
                lastOutputIndex += newOutput.length;
            }
            
            // Show heartbeat progress (only if no new output and duration changed significantly)
            if (newOutput.length === 0 && duration - lastDuration >= 10) {
                const minutes = Math.floor(duration / 60);
                const seconds = duration % 60;
                appendToTerminal(
                    `⏱ Running... ${minutes}m ${seconds}s elapsed (status: ${currentStatus})\n`,
                    'status'
                );
                lastDuration = duration;
            }
            
            // Check if completed
            if (currentStatus === 'completed') {
                // Fetch any remaining output we might have missed
                if (statusData.output_length > lastOutputIndex) {
                    const finalResponse = await fetch(`/execute/status/${executionId}?since=${lastOutputIndex}`, {
                        headers: { 'Authorization': `Bearer ${token}` }
                    });
                    if (finalResponse.ok) {
                        const finalData = await finalResponse.json();
                        const finalOutput = finalData.output || []; // Fixed: API returns 'output' not 'output_buffer'
                        finalOutput.forEach(outputItem => {
                            const outputText = outputItem.data || outputItem.message || '';
                            if (outputText) {
                                appendToTerminal(outputText, outputItem.type || 'stdout');
                                parseOutputForTabs(outputText);
                            }
                        });
                    }
                }
                
                appendToTerminal('\n✅ Analysis completed successfully!\n', 'status');
                
                // Send completion notifications
                await sendCompletionNotifications(executionId, statusData, 'completed');
                
                // Save last completed job (don't clear immediately)
                localStorage.setItem('last_completed_job', executionId);
                localStorage.setItem('last_completed_time', Date.now());
                
                // Clear active execution ID (job is done)
                localStorage.removeItem('active_execution_id');
                localStorage.removeItem('active_execution_start');
                
                const spinner = document.getElementById('executionSpinner');
                const status = document.getElementById('executionStatus');
                const cancelBtn = document.getElementById('cancelButton');
                
                if (spinner) spinner.style.display = 'none';
                if (status) {
                    status.textContent = 'Completed ✓';
                    status.className = 'status-badge status-success';
                }
                if (cancelBtn) cancelBtn.style.display = 'none';
                
                showToast('Analysis completed successfully!', 'success');
                loadOutputFiles();
                break;
            }
            
            // Check for errors
            if (['failed', 'timeout', 'error'].includes(currentStatus)) {
                const errorMsg = statusData.error_message || 'Unknown error';
                appendToTerminal(`\n❌ Analysis ${currentStatus}: ${errorMsg}\n`, 'error');
                
                // Send failure notifications
                await sendCompletionNotifications(executionId, statusData, currentStatus);
                
                // Clear saved execution ID
                localStorage.removeItem('active_execution_id');
                localStorage.removeItem('active_execution_start');
                
                const spinner = document.getElementById('executionSpinner');
                const status = document.getElementById('executionStatus');
                const cancelBtn = document.getElementById('cancelButton');
                
                if (spinner) spinner.style.display = 'none';
                if (status) {
                    status.textContent = currentStatus === 'timeout' ? 'Timeout ⏱' : 'Failed ✗';
                    status.className = 'status-badge status-error';
                }
                if (cancelBtn) cancelBtn.style.display = 'none';
                
                showToast(`Analysis ${currentStatus}`, 'error');
                break;
            }
            
            // Continue polling
            await new Promise(resolve => setTimeout(resolve, pollInterval));
            
        } catch (error) {
            console.error('Status polling error:', error);
            appendToTerminal(`\n❌ Failed to check status: ${error.message}\n`, 'error');
            showToast('Status check failed: ' + error.message, 'error');
            break;
        }
    }
}

// Note: loadBackgroundOutput removed - we now stream output incrementally during polling

/**
 * Run command using SSE streaming (for quick interactive tasks)
 */
async function runSSEExecution(command, args) {
    // Build query string for /execute endpoint
    const params = new URLSearchParams({
        command: command,
        args: JSON.stringify(args),
        execution_id: currentExecutionId
    });
    
    // Get token if available
    const token = localStorage.getItem('api_token') || '';
    
    // Call /execute with SSE streaming
    const url = `/execute?${params}`;
    console.log('Opening EventSource:', url);
    
    const eventSource = new EventSource(url);
    
    const spinner = document.getElementById('executionSpinner');
    const status = document.getElementById('executionStatus');
    const cancelBtn = document.getElementById('cancelButton');
    
    eventSource.onmessage = function(event) {
        try {
            const data = JSON.parse(event.data);
            console.log('Received SSE:', data);
            
            // Append output to terminal
            if (data.type === 'stdout' || data.type === 'stderr' || data.type === 'status' || data.type === 'error') {
                const outputText = data.data || data.message || '';
                appendToTerminal(outputText, data.type);
                
                // Parse output for tab population (Comment 16)
                parseOutputForTabs(outputText);
            }
            
            // Handle completion
            if (data.type === 'complete' || data.status === 'completed') {
                if (spinner) spinner.style.display = 'none';
                if (status) {
                    status.textContent = 'Completed ✓';
                    status.className = 'status-badge status-success';
                }
                if (cancelBtn) cancelBtn.style.display = 'none';
                eventSource.close();
                showToast('Analysis completed successfully!', 'success');
                
                // Load output files after completion
                loadOutputFiles();
            }
            
            // Handle errors - display in terminal first, then close
            if (data.type === 'error' || data.status === 'failed') {
                // Display error message prominently in terminal if not already shown
                const errorMessage = data.data || data.message || 'Unknown error occurred';
                if (data.type !== 'error' || !data.data) {
                    // Only append if we haven't already appended it above
                    appendToTerminal(`\n❌ ERROR: ${errorMessage}`, 'error');
                }
                
                if (spinner) spinner.style.display = 'none';
                if (status) {
                    status.textContent = 'Failed ✗';
                    status.className = 'status-badge status-error';
                }
                if (cancelBtn) cancelBtn.style.display = 'none';
                
                // Show toast notification
                showToast('Analysis failed: ' + errorMessage, 'error');
                
                // Close connection after a brief delay to ensure error is displayed
                setTimeout(() => {
                    eventSource.close();
                }, 500);
            }
            
            // Handle timeout
            if (data.type === 'timeout' || data.status === 'timeout') {
                const timeoutMessage = data.data || data.message || 'Execution timed out';
                appendToTerminal(`\n⏱ TIMEOUT: ${timeoutMessage}`, 'error');
                
                if (spinner) spinner.style.display = 'none';
                if (status) {
                    status.textContent = 'Timeout ⏱';
                    status.className = 'status-badge status-error';
                }
                if (cancelBtn) cancelBtn.style.display = 'none';
                showToast('Analysis timed out', 'error');
                
                setTimeout(() => {
                    eventSource.close();
                }, 500);
            }
            
        } catch (e) {
            console.error('Error parsing SSE data:', e, 'Raw data:', event.data);
        }
    };
    
    eventSource.onerror = function(error) {
        console.error('EventSource error:', error);
        
        // Display connection error in terminal
        const terminalOutput = document.getElementById('terminalOutput');
        if (terminalOutput) {
            appendToTerminal('\n❌ Connection Error: Lost connection to server. Check your network connection.', 'error');
        }
        
        if (spinner) spinner.style.display = 'none';
        if (status) {
            status.textContent = 'Error ✗';
            status.className = 'status-badge status-error';
        }
        if (cancelBtn) cancelBtn.style.display = 'none';
        eventSource.close();
        showToast('Connection error. Check terminal for details.', 'error');
    };
}

/**
 * Append text to terminal output with ANSI color support
 */
function appendToTerminal(text, type) {
    const terminalOutput = document.getElementById('terminalOutput');
    if (!terminalOutput) return;
    
    // Use ansi_up if available for color support
    let formattedText = escapeHtml(text);
    if (typeof ansi_up !== 'undefined' && ansi_up.ansi_to_html) {
        try {
            const ansi = new ansi_up.default();
            formattedText = ansi.ansi_to_html(text);
        } catch (e) {
            console.warn('ansi_up failed, using plain text:', e);
        }
    }
    
    const line = document.createElement('div');
    line.className = `terminal-line terminal-${type}`;
    line.innerHTML = formattedText;
    
    terminalOutput.appendChild(line);
    
    // Auto-scroll to bottom
    terminalOutput.scrollTop = terminalOutput.scrollHeight;
}

/**
 * Update analysis options based on selected analysis type
 */
function updateAnalysisOptions() {
    const analysisType = document.getElementById('analysisType')?.value;
    if (!analysisType) return;
    
    console.log('updateAnalysisOptions() called, type:', analysisType);
    
    // Show/hide sample mode options
    const sampleModeOptions = document.getElementById('sampleModeOptions');
    if (sampleModeOptions) {
        sampleModeOptions.style.display = (analysisType === 'sample-mode') ? 'block' : 'none';
    }
    
    // Show/hide individual breakdown info
    const individualInfo = document.getElementById('individualBreakdownInfo');
    if (individualInfo) {
        const showIndividual = analysisType.includes('individual');
        individualInfo.style.display = showIndividual ? 'block' : 'none';
    }
    
    // Show/hide coaching report info
    const coachingInfo = document.getElementById('coachingReportInfo');
    if (coachingInfo) {
        const showCoaching = analysisType.includes('coaching');
        coachingInfo.style.display = showCoaching ? 'block' : 'none';
    }
    
    // Show/hide team overview info
    const teamInfo = document.getElementById('teamOverviewInfo');
    if (teamInfo) {
        const showTeam = analysisType.includes('team');
        teamInfo.style.display = showTeam ? 'block' : 'none';
    }
    
    // Determine if this is a diagnostic mode
    const isDiagnostic = analysisType === 'sample-mode';
    const isVoC = analysisType && analysisType.startsWith('voice-of-customer');
    
    // Show/hide LLM topic detection for VOC
    const llmTopicDetectionVocContainer = document.getElementById('llmTopicDetectionVocContainer');
    if (llmTopicDetectionVocContainer) {
        llmTopicDetectionVocContainer.style.display = isVoC ? 'block' : 'none';
    }
    
    // Hide/show Time Period (hide for sample-mode - it has its own)
    const timePeriodLabel = document.getElementById('timePeriodLabel');
    const timePeriodSelect = document.getElementById('timePeriod');
    const showTimePeriod = analysisType !== 'sample-mode';  // Sample-mode handles internally
    if (timePeriodLabel) {
        timePeriodLabel.style.display = showTimePeriod ? 'block' : 'none';
    }
    if (timePeriodSelect) {
        timePeriodSelect.style.display = showTimePeriod ? 'block' : 'none';
    }
    
    // Hide/show Data Source (only for VoC)
    const dataSourceLabel = document.querySelector('label[for="dataSource"]');
    const dataSourceSelect = document.getElementById('dataSource');
    if (dataSourceLabel) {
        dataSourceLabel.style.display = isVoC ? 'block' : 'none';
    }
    if (dataSourceSelect) {
        dataSourceSelect.style.display = isVoC ? 'block' : 'none';
        if (!isVoC) {
            dataSourceSelect.value = 'intercom';
        }
    }
    
    // Hide Taxonomy Filter for diagnostic modes
    const taxonomyLabel = document.querySelector('label[for="taxonomyFilter"]');
    const taxonomySelect = document.getElementById('taxonomyFilter');
    if (taxonomyLabel) {
        taxonomyLabel.style.display = isDiagnostic ? 'none' : 'block';
    }
    if (taxonomySelect) {
        taxonomySelect.style.display = isDiagnostic ? 'none' : 'block';
    }
    
    // Hide Output Format for diagnostic modes
    const outputFormatLabel = document.querySelector('label[for="outputFormat"]');
    const outputFormatSelect = document.getElementById('outputFormat');
    if (outputFormatLabel) {
        outputFormatLabel.style.display = isDiagnostic ? 'none' : 'block';
    }
    if (outputFormatSelect) {
        outputFormatSelect.style.display = isDiagnostic ? 'none' : 'block';
    }
    
    // Hide AI Model for sample-mode (it has its own in the options panel)
    const aiModelLabel = document.querySelector('label[for="aiModel"]');
    const aiModelSelect = document.getElementById('aiModel');
    const showAIModel = !isDiagnostic;
    if (aiModelLabel) {
        aiModelLabel.style.display = showAIModel ? 'block' : 'none';
    }
    if (aiModelSelect) {
        aiModelSelect.style.display = showAIModel ? 'block' : 'none';
    }
    
    // Hide Test Mode checkbox for diagnostic modes (they're already diagnostic)
    const testModeContainer = document.querySelector('div:has(> #testMode)');
    if (testModeContainer) {
        testModeContainer.style.display = isDiagnostic ? 'none' : 'block';
    }
    
    // Hide Audit Trail for diagnostic modes
    const auditModeContainer = document.querySelector('div:has(> #auditMode)');
    if (auditModeContainer) {
        auditModeContainer.style.display = isDiagnostic ? 'none' : 'block';
    }
    
    // Show/hide test mode options when checkbox changes
    updateTestModeOptions();
}

/**
 * Update test mode options visibility
 */
function updateTestModeOptions() {
    const testModeCheckbox = document.getElementById('testMode');
    const testModeOptions = document.getElementById('testModeOptions');
    
    if (testModeOptions && testModeCheckbox) {
        testModeOptions.style.display = testModeCheckbox.checked ? 'block' : 'none';
    }
}

/**
 * Update custom date inputs visibility
 */
function updateCustomDateInputs() {
    const timePeriodSelect = document.getElementById('timePeriod');
    const customDateInputs = document.getElementById('customDateInputs');
    
    if (customDateInputs && timePeriodSelect) {
        customDateInputs.style.display = (timePeriodSelect.value === 'custom') ? 'block' : 'none';
    }
}

/**
 * Switch between tabs (Terminal, Summary, Files, Gamma)
 */
function switchTab(tabName) {
    console.log('switchTab() called:', tabName);
    
    // Hide all tab panes
    const tabPanes = document.querySelectorAll('.tab-pane');
    tabPanes.forEach(pane => {
        pane.classList.remove('active');
    });
    
    // Remove active class from all tab buttons
    const tabButtons = document.querySelectorAll('.tab-button');
    tabButtons.forEach(btn => {
        btn.classList.remove('active');
    });
    
    // Show selected tab pane
    const targetPane = document.getElementById(tabName + 'TabContent');
    if (targetPane) {
        targetPane.classList.add('active');
    }
    
    // Activate selected tab button
    const targetButton = document.getElementById(tabName + 'Tab');
    if (targetButton) {
        targetButton.classList.add('active');
    }
}

/**
 * Cancel running execution
 */
async function cancelExecution() {
    if (!currentExecutionId) {
        showToast('No execution to cancel', 'info');
        return;
    }
    
    try {
        console.log('Cancelling execution:', currentExecutionId);
        
        const token = localStorage.getItem('api_token') || '';
        const response = await fetch(`/execute/cancel/${currentExecutionId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (response.ok) {
            showToast('Execution cancelled', 'info');
            const spinner = document.getElementById('executionSpinner');
            const status = document.getElementById('executionStatus');
            const cancelBtn = document.getElementById('cancelButton');
            
            if (spinner) spinner.style.display = 'none';
            if (status) {
                status.textContent = 'Cancelled';
                status.className = 'status-badge status-warning';
            }
            if (cancelBtn) cancelBtn.style.display = 'none';
        } else {
            throw new Error('Failed to cancel execution');
        }
    } catch (error) {
        console.error('Cancel error:', error);
        showToast('Failed to cancel execution', 'error');
    }
}

// Initialize form on page load
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeAnalysisForm);
} else {
    initializeAnalysisForm();
}

function initializeAnalysisForm() {
    console.log('Initializing analysis form...');
    
    // Set up event listeners
    const testModeCheckbox = document.getElementById('testMode');
    if (testModeCheckbox) {
        testModeCheckbox.addEventListener('change', updateTestModeOptions);
    }
    
    const timePeriodSelect = document.getElementById('timePeriod');
    if (timePeriodSelect) {
        timePeriodSelect.addEventListener('change', updateCustomDateInputs);
    }
    
    // Initial update
    updateAnalysisOptions();
    
    // Check for active execution on page load (resume after refresh)
    resumeActiveExecution();
    
    console.log('✅ Analysis form initialized');
}

/**
 * Resume polling for active execution after page refresh
 */
async function resumeActiveExecution() {
    const activeExecutionId = localStorage.getItem('active_execution_id');
    const executionStart = localStorage.getItem('active_execution_start');
    
    if (!activeExecutionId) {
        return; // No active execution
    }
    
    console.log('🔄 Found active execution, checking status:', activeExecutionId);
    
    try {
        const token = localStorage.getItem('api_token') || '';
        
        // Check if execution is still running
        const response = await fetch(`/execute/status/${activeExecutionId}`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        
        if (!response.ok) {
            // Execution not found - clear storage
            localStorage.removeItem('active_execution_id');
            localStorage.removeItem('active_execution_start');
            return;
        }
        
        const statusData = await response.json();
        const currentStatus = statusData.status;
        
        // Show active job banner if still running
        if (['running', 'queued'].includes(currentStatus)) {
            const elapsed = Math.floor((Date.now() - parseInt(executionStart)) / 1000);
            const minutes = Math.floor(elapsed / 60);
            const seconds = elapsed % 60;
            
            const banner = document.getElementById('activeJobBanner');
            const info = document.getElementById('activeJobInfo');
            
            if (banner && info) {
                info.innerHTML = `
                    Job started ${minutes}m ${seconds}s ago • Status: ${currentStatus} • ID: ${activeExecutionId.substring(0, 20)}...
                `;
                banner.style.display = 'block';
            }
            
            // Don't auto-resume - let user click "View Progress" button
            console.log('ℹ️ Active job detected - banner shown. Click "View Progress" to resume.');
            return;
        }
        
        // If completed, show notification but don't auto-resume
        if (currentStatus === 'completed') {
            showToast('Previous job completed! Check Files tab for results.', 'success');
            localStorage.removeItem('active_execution_id');
            localStorage.removeItem('active_execution_start');
            return;
        }
        
        // If failed, clear storage
        if (['failed', 'timeout', 'error'].includes(currentStatus)) {
            localStorage.removeItem('active_execution_id');
            localStorage.removeItem('active_execution_start');
            return;
        }
        
    } catch (error) {
        console.error('Failed to check active execution:', error);
        // Don't clear - might be temporary network issue
    }
}

/**
 * Resume execution from banner click
 */
async function resumeFromBanner() {
    const activeExecutionId = localStorage.getItem('active_execution_id');
    const executionStart = localStorage.getItem('active_execution_start');
    
    if (!activeExecutionId) {
        showToast('No active job found', 'info');
        return;
    }
    
    try {
        const token = localStorage.getItem('api_token') || '';
        currentExecutionId = activeExecutionId;
        
        // Show terminal container
        const terminalContainer = document.getElementById('terminalContainer');
        if (terminalContainer) {
            terminalContainer.style.display = 'block';
        }
        
        // Clear and show resume message
        const terminalOutput = document.getElementById('terminalOutput');
        if (terminalOutput) {
            terminalOutput.innerHTML = '';
        }
        
        appendToTerminal('🔄 Resuming active execution\n', 'status');
        appendToTerminal(`📌 Execution ID: ${activeExecutionId}\n`, 'status');
        
        const elapsed = Math.floor((Date.now() - parseInt(executionStart)) / 1000);
        const minutes = Math.floor(elapsed / 60);
        const seconds = elapsed % 60;
        appendToTerminal(`⏱ Task has been running for ${minutes}m ${seconds}s\n`, 'status');
        appendToTerminal('⏳ Fetching current progress...\n\n', 'status');
        
        // Show UI elements
        const spinner = document.getElementById('executionSpinner');
        const status = document.getElementById('executionStatus');
        const cancelBtn = document.getElementById('cancelButton');
        const tabNav = document.getElementById('tabNavigation');
        
        if (spinner) spinner.style.display = 'inline-block';
        if (status) {
            status.textContent = 'Running';
            status.className = 'status-badge';
            status.style.display = 'inline-block';
        }
        if (cancelBtn) cancelBtn.style.display = 'inline-block';
        if (tabNav) tabNav.style.display = 'flex';
        
        // Switch to terminal tab
        switchTab('terminal');
        
        // Hide banner
        const banner = document.getElementById('activeJobBanner');
        if (banner) banner.style.display = 'none';
        
        // Resume polling
        await pollExecutionStatus(activeExecutionId, token);
        
    } catch (error) {
        console.error('Failed to resume execution:', error);
        showToast('Failed to resume job: ' + error.message, 'error');
    }
}

/**
 * Parse terminal output for special markers and populate tabs (Comment 16)
 */
function parseOutputForTabs(outputText) {
    if (!outputText) return;
    
    // Detect Gamma URL
    const gammaMatch = outputText.match(/Gamma (?:URL|presentation):\s*(https?:\/\/[^\s]+)/i);
    if (gammaMatch) {
        const gammaUrl = gammaMatch[1];
        console.log('Detected Gamma URL:', gammaUrl);
        addGammaLink(gammaUrl);
    }
    
    // Detect file outputs
    const fileMatch = outputText.match(/(?:Saved|Generated|Output).*?:\s*([^\s]+\.(md|json|csv|xlsx|pdf|pptx))/i);
    if (fileMatch) {
        const filePath = fileMatch[1];
        console.log('Detected output file:', filePath);
        // Files will be loaded via loadOutputFiles() after completion
    }
    
    // Detect metrics for summary tab
    const convCountMatch = outputText.match(/(?:Found|Fetched|total.*:)\s*(\d+,?\d*)\s*conversations/i);
    if (convCountMatch) {
        const count = convCountMatch[1].replace(',', '');
        updateSummaryMetric('conversations', count);
    }
    
    const topicsMatch = outputText.match(/(\d+)\s*topics?\s*(?:detected|identified|found)/i);
    if (topicsMatch) {
        updateSummaryMetric('topics', topicsMatch[1]);
    }
    
    // Detect summary sections (e.g., lines starting with ## or **Summary**)
    if (outputText.match(/^##\s+/m) || outputText.match(/\*\*Summary\*\*/i)) {
        // Summary content detected - could be parsed further if needed
        console.log('Detected summary content');
    }
}

/**
 * Update summary tab with metrics
 */
function updateSummaryMetric(metric, value) {
    const summaryCards = document.querySelector('.summary-cards');
    if (!summaryCards) return;
    
    // Check if card already exists
    let card = summaryCards.querySelector(`[data-metric="${metric}"]`);
    
    if (!card) {
        card = document.createElement('div');
        card.setAttribute('data-metric', metric);
        card.style.cssText = 'padding: 15px; background: rgba(59, 130, 246, 0.1); border-radius: 8px; border: 1px solid rgba(59, 130, 246, 0.3); margin: 10px 0;';
        summaryCards.appendChild(card);
    }
    
    const labels = {
        'conversations': '💬 Conversations',
        'topics': '🎯 Topics Detected',
        'agents': '🤖 Agents Used',
        'duration': '⏱️ Duration'
    };
    
    card.innerHTML = `
        <div style="font-size: 12px; color: #9ca3af; margin-bottom: 5px;">${labels[metric] || metric}</div>
        <div style="font-size: 24px; font-weight: 600; color: #3b82f6;">${value}</div>
    `;
}

/**
 * Add a Gamma link to the Gamma tab
 */
function addGammaLink(url) {
    const gammaContainer = document.querySelector('#gammaLinks .gamma-links');
    if (!gammaContainer) return;
    
    // Check if already added
    const existing = gammaContainer.querySelector(`a[href="${url}"]`);
    if (existing) return;
    
    const linkElement = document.createElement('div');
    linkElement.style.cssText = 'margin: 10px 0; padding: 12px; background: rgba(59, 130, 246, 0.1); border-radius: 6px; border: 1px solid rgba(59, 130, 246, 0.3);';
    linkElement.innerHTML = `
        <a href="${url}" target="_blank" style="color: #3b82f6; text-decoration: none; font-weight: 500;">
            📊 View Gamma Presentation
        </a>
        <div style="font-size: 12px; color: #9ca3af; margin-top: 4px;">
            ${url}
        </div>
    `;
    
    gammaContainer.appendChild(linkElement);
    
    // Show gamma tab if hidden
    const gammaTab = document.getElementById('gammaTab');
    if (gammaTab) {
        gammaTab.style.display = 'inline-block';
    }
}

/**
 * Load output files from the server
 */
async function loadOutputFiles() {
    try {
        const response = await fetch('/outputs?limit=10');
        if (!response.ok) return;
        
        const data = await response.json();
        const files = data.files || [];
        
        if (files.length === 0) return;
        
        const filesContainer = document.querySelector('#filesList .files-list');
        if (!filesContainer) return;
        
        filesContainer.innerHTML = '';
        
        files.forEach(file => {
            const fileElement = document.createElement('div');
            fileElement.style.cssText = 'margin: 8px 0; padding: 10px; background: rgba(16, 185, 129, 0.1); border-radius: 6px; border: 1px solid rgba(16, 185, 129, 0.3);';
            
            const icon = file.extension === '.md' ? '📄' : 
                        file.extension === '.json' ? '📋' :
                        file.extension === '.xlsx' ? '📊' :
                        file.extension === '.csv' ? '📈' : '📁';
            
            fileElement.innerHTML = `
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <span style="font-size: 16px;">${icon}</span>
                        <a href="/outputs/${file.path}" target="_blank" style="color: #10b981; text-decoration: none; margin-left: 8px;">
                            ${file.name}
                        </a>
                    </div>
                    <span style="color: #9ca3af; font-size: 12px;">${formatFileSize(file.size)}</span>
                </div>
            `;
            
            filesContainer.appendChild(fileElement);
        });
        
        // Show files tab if hidden
        const filesTab = document.getElementById('filesTab');
        if (filesTab) {
            filesTab.style.display = 'inline-block';
        }
        
    } catch (error) {
        console.error('Error loading output files:', error);
    }
}

/**
 * Format file size for display
 */
function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

/**
 * Request browser notification permission
 */
function requestNotificationPermission() {
    if (!('Notification' in window)) {
        console.log('Browser notifications not supported');
        return;
    }
    
    if (Notification.permission === 'default') {
        Notification.requestPermission().then(permission => {
            if (permission === 'granted') {
                appendToTerminal('🔔 Notifications enabled - you\'ll be notified when the job completes\n', 'status');
            }
        });
    }
}

/**
 * Send completion notifications (browser + Slack)
 */
async function sendCompletionNotifications(executionId, statusData, finalStatus) {
    const duration = statusData.duration_seconds || 0;
    const minutes = Math.floor(duration / 60);
    const seconds = duration % 60;
    const timeStr = `${minutes}m ${seconds}s`;
    
    // Browser notification
    if ('Notification' in window && Notification.permission === 'granted') {
        const title = finalStatus === 'completed' 
            ? '✅ Analysis Completed!' 
            : `❌ Analysis ${finalStatus}`;
        
        const body = finalStatus === 'completed'
            ? `Your analysis finished in ${timeStr}. Click to view results.`
            : `Analysis ${finalStatus} after ${timeStr}. ${statusData.error_message || ''}`;
        
        const notification = new Notification(title, {
            body: body,
            icon: '/static/favicon.ico',
            badge: '/static/favicon.ico',
            tag: executionId, // Prevent duplicates
            requireInteraction: finalStatus === 'completed' // Keep notification visible for success
        });
        
        notification.onclick = function() {
            window.focus();
            this.close();
        };
        
        console.log('📱 Browser notification sent:', title);
    }
    
    // Slack notification (if webhook URL configured on server)
    try {
        const token = localStorage.getItem('api_token') || '';
        await fetch('/api/notify-completion', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                execution_id: executionId,
                status: finalStatus,
                duration_seconds: duration
            })
        });
    } catch (error) {
        // Silently fail - Slack is optional
        console.log('Slack notification not sent (webhook not configured or error):', error.message);
    }
}

// Make tabs visible immediately on page load (so user can browse files without running analysis)
document.addEventListener('DOMContentLoaded', () => {
    const tabNav = document.getElementById('tabNavigation');
    if (tabNav) {
        tabNav.style.display = 'flex';  // Show tabs immediately
        console.log('✅ Tabs made visible on page load');
    }
    // Switch to Files tab by default
    switchTab('files');
});

// Export functions to window for onclick handlers
window.runAnalysis = runAnalysis;
window.updateAnalysisOptions = updateAnalysisOptions;
window.switchTab = switchTab;
window.cancelExecution = cancelExecution;
window.appendToTerminal = appendToTerminal;
window.resumeFromBanner = resumeFromBanner;

// ============================================================================
// EXECUTION HISTORY MANAGEMENT
// ============================================================================

/**
 * Refresh the execution history dropdown
 */
async function refreshExecutionHistory() {
    console.log('🔄 Refreshing execution history...');
    
    try {
        const response = await fetch('/execute/list?limit=50');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        const executions = data.executions || [];
        
        console.log(`📂 Found ${executions.length} past executions`);
        
        // Populate dropdown
        const select = document.getElementById('executionHistorySelect');
        if (!select) return;
        
        // Keep "Current Execution" option
        select.innerHTML = '<option value="">-- Current Execution --</option>';
        
        // Add past executions (newest first)
        executions.forEach(exec => {
            const startTime = new Date(exec.start_time);
            const duration = exec.end_time ? 
                Math.round((new Date(exec.end_time) - startTime) / 1000) : 
                'running';
            
            const option = document.createElement('option');
            option.value = exec.execution_id;
            
            // Status icon
            const statusIcon = exec.status === 'completed' ? '✅' :
                             exec.status === 'failed' ? '❌' : 
                             exec.status === 'running' ? '⏳' : '⏸️';
            
            // Try to extract human-readable directory name from output_files
            let displayName = '';
            if (exec.output_files && exec.output_files.length > 0) {
                // First entry is the human-readable directory name
                displayName = exec.output_files[0];
                // Make it even prettier: replace underscores with spaces in the middle part
                displayName = displayName.replace(/_/g, ' ');
            } else {
                // Fallback to command + time ago
                const commandShort = exec.command.replace('src/main.py', '').trim().split(' ')[0] || exec.command;
                const timeAgo = getTimeAgo(startTime);
                displayName = `${commandShort} (${timeAgo}, ${duration}s)`;
            }
            
            option.textContent = `${statusIcon} ${displayName}`;
            
            select.appendChild(option);
        });
        
        showToast(`Loaded ${executions.length} past executions`, 'success');
        
    } catch (error) {
        console.error('❌ Failed to load execution history:', error);
        showToast('Failed to load execution history', 'error');
    }
}

/**
 * Load a historical execution's files
 */
async function loadHistoricalExecution() {
    const select = document.getElementById('executionHistorySelect');
    if (!select) return;
    
    const executionId = select.value;
    
    // If "Current Execution" selected, do nothing
    if (!executionId) {
        console.log('📍 Switched back to current execution');
        return;
    }
    
    console.log(`📂 Loading historical execution: ${executionId}`);
    
    try {
        // Fetch execution details
        const response = await fetch(`/execute/status/${executionId}?since=0`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        // Update Files tab with historical files
        const filesContent = document.getElementById('filesContent');
        if (filesContent && data.files && data.files.length > 0) {
            let filesHTML = '<h3>📁 Output Files</h3><ul class="file-list">';
            
            data.files.forEach(file => {
                filesHTML += `
                    <li>
                        <span class="file-name">${file.name}</span>
                        <span class="file-size">(${formatFileSize(file.size)})</span>
                        <button onclick="downloadFile('${file.name}')" class="btn-download">📥 Download</button>
                    </li>
                `;
            });
            
            filesHTML += '</ul>';
            filesContent.innerHTML = filesHTML;
            
            // Switch to Files tab
            switchTab('files');
            
            showToast(`Loaded ${data.files.length} files from past execution`, 'success');
        } else {
            filesContent.innerHTML = '<p>No files found for this execution</p>';
            showToast('No files found for this execution', 'warning');
        }
        
    } catch (error) {
        console.error('❌ Failed to load historical execution:', error);
        showToast('Failed to load execution files', 'error');
    }
}

/**
 * Format time ago (e.g., "2 min ago")
 */
function getTimeAgo(date) {
    const seconds = Math.floor((new Date() - date) / 1000);
    
    if (seconds < 60) return `${seconds}s ago`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
    return `${Math.floor(seconds / 86400)}d ago`;
}

/**
 * Format file size (bytes to human readable)
 */
function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / 1048576).toFixed(1) + ' MB';
}

// Auto-load execution history when page loads
document.addEventListener('DOMContentLoaded', () => {
    // Show history panel after 1 second (after any active execution loads)
    setTimeout(() => {
        const panel = document.getElementById('executionHistoryPanel');
        if (panel) {
            panel.style.display = 'block';
            refreshExecutionHistory();
        }
    }, 1000);
});

// Export functions to global scope
window.refreshExecutionHistory = refreshExecutionHistory;
window.loadHistoricalExecution = loadHistoricalExecution;

console.log('✅ Analysis form functions loaded');
