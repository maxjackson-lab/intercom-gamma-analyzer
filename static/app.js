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
