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
            args.push('sample-mode');
            args.push('--count', sampleCount);
            args.push('--time-period', sampleTimePeriod);
            
        } else if (analysisType === 'voice-of-customer-hilary') {
            args.push('voice-of-customer');
            args.push('--analysis-type', 'topic-based');
            args.push('--multi-agent');
            
        } else if (analysisType === 'voice-of-customer-synthesis') {
            args.push('voice-of-customer');
            args.push('--analysis-type', 'synthesis');
            args.push('--multi-agent');
            
        } else if (analysisType === 'voice-of-customer-complete') {
            args.push('voice-of-customer');
            args.push('--analysis-type', 'complete');
            args.push('--multi-agent');
            
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
        
        // Add time period (unless it's sample-mode)
        if (analysisType !== 'sample-mode') {
            if (timePeriod === 'custom' && startDate && endDate) {
                args.push('--start-date', startDate);
                args.push('--end-date', endDate);
            } else if (timePeriod !== 'custom' && timePeriod) {
                args.push('--time-period', timePeriod);
            }
        }
        
        // Add AI model
        if (aiModel && analysisType !== 'sample-mode') {
            args.push('--ai-model', aiModel);
        }
        
        // Add output format / generate gamma
        if (outputFormat === 'gamma') {
            args.push('--generate-gamma');
        } else if (outputFormat && analysisType !== 'sample-mode') {
            args.push('--output-format', outputFormat);
        }
        
        // Add test mode flags
        if (testMode) {
            args.push('--test-mode');
            if (testDataCount) {
                args.push('--test-data-count', testDataCount);
            }
        }
        
        // Add verbose flag
        if (verboseLogging || (testMode && verboseLogging)) {
            args.push('--verbose');
        }
        
        // Add audit trail
        if (auditMode) {
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
        
        eventSource.onmessage = function(event) {
            try {
                const data = JSON.parse(event.data);
                console.log('Received SSE:', data);
                
                // Append output to terminal
                if (data.type === 'stdout' || data.type === 'stderr' || data.type === 'status') {
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
                
                // Handle errors
                if (data.type === 'error' || data.status === 'failed') {
                    if (spinner) spinner.style.display = 'none';
                    if (status) {
                        status.textContent = 'Failed ✗';
                        status.className = 'status-badge status-error';
                    }
                    if (cancelBtn) cancelBtn.style.display = 'none';
                    eventSource.close();
                    showToast('Analysis failed: ' + (data.message || 'Unknown error'), 'error');
                }
                
                // Handle timeout
                if (data.type === 'timeout' || data.status === 'timeout') {
                    if (spinner) spinner.style.display = 'none';
                    if (status) {
                        status.textContent = 'Timeout ⏱';
                        status.className = 'status-badge status-error';
                    }
                    if (cancelBtn) cancelBtn.style.display = 'none';
                    eventSource.close();
                    showToast('Analysis timed out', 'error');
                }
                
            } catch (e) {
                console.error('Error parsing SSE data:', e, 'Raw data:', event.data);
            }
        };
        
        eventSource.onerror = function(error) {
            console.error('EventSource error:', error);
            if (spinner) spinner.style.display = 'none';
            if (status) {
                status.textContent = 'Error ✗';
                status.className = 'status-badge status-error';
            }
            if (cancelBtn) cancelBtn.style.display = 'none';
            eventSource.close();
            showToast('Connection error. Check console for details.', 'error');
        };
        
    } catch (error) {
        console.error('Error in runAnalysis():', error);
        showToast('Error starting analysis: ' + error.message, 'error');
    }
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
    
    // Show/hide time period selector for sample mode
    const timePeriodLabel = document.getElementById('timePeriodLabel');
    const timePeriodSelect = document.getElementById('timePeriod');
    if (analysisType === 'sample-mode') {
        if (timePeriodLabel) timePeriodLabel.style.display = 'none';
        if (timePeriodSelect) timePeriodSelect.style.display = 'none';
    } else {
        if (timePeriodLabel) timePeriodLabel.style.display = 'block';
        if (timePeriodSelect) timePeriodSelect.style.display = 'block';
    }
    
    // Restrict Data Source control to VoC only (Comment 2)
    const dataSourceLabel = document.querySelector('label[for="dataSource"]');
    const dataSourceSelect = document.getElementById('dataSource');
    const isVoC = analysisType && analysisType.startsWith('voice-of-customer');
    
    if (dataSourceLabel) {
        dataSourceLabel.style.display = isVoC ? 'block' : 'none';
    }
    if (dataSourceSelect) {
        dataSourceSelect.style.display = isVoC ? 'block' : 'none';
        // Reset to default if not VoC
        if (!isVoC) {
            dataSourceSelect.value = 'intercom';
        }
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
        const response = await fetch(`/api/executions/${currentExecutionId}/cancel`, {
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
    
    console.log('✅ Analysis form initialized');
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
    
    // Detect summary sections (e.g., lines starting with ## or **Summary**)
    if (outputText.match(/^##\s+/m) || outputText.match(/\*\*Summary\*\*/i)) {
        // Summary content detected - could be parsed further if needed
        console.log('Detected summary content');
    }
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

// Export functions to window for onclick handlers
window.runAnalysis = runAnalysis;
window.updateAnalysisOptions = updateAnalysisOptions;
window.switchTab = switchTab;
window.cancelExecution = cancelExecution;
window.appendToTerminal = appendToTerminal;

console.log('✅ Analysis form functions loaded');
