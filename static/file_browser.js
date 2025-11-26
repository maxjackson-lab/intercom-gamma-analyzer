/**
 * File Browser - Auto-loads and displays all available output files
 * 
 * Loads immediately on page load so user can see past analysis files
 * WITHOUT needing to run a new analysis first.
 */

const FILE_BROWSER_DEBUG = typeof window !== 'undefined' && window.FILE_BROWSER_DEBUG === true;
function debugLog(...args) {
    if (FILE_BROWSER_DEBUG) {
        console.log(...args);
    }
}

function notifyZipStatus(message, type = 'info') {
    if (typeof window !== 'undefined' && typeof window.showToast === 'function') {
        window.showToast(message, type);
    } else {
        debugLog(message);
    }
}

let allZipDownloadInProgress = false;
const folderZipDownloadsInProgress = new Set();

function setButtonState(button, downloading, busyLabel) {
    if (!button) return;
    if (downloading) {
        if (!button.dataset.defaultLabel) {
            button.dataset.defaultLabel = button.textContent.trim();
        }
        button.disabled = true;
        button.textContent = busyLabel;
    } else {
        button.disabled = false;
        const label = button.dataset.defaultLabel || button.textContent;
        button.textContent = label;
    }
}

function setAllZipButtonState(downloading) {
    const button = document.getElementById('downloadAllZipButton');
    setButtonState(button, downloading, '⏳ Preparing ZIP...');
}

function setFolderZipButtonState(folderName, downloading) {
    const button = document.querySelector(`button[data-folder-zip-button="${folderName}"]`);
    setButtonState(button, downloading, '⏳ Preparing...');
}

debugLog('📁 File browser loading...');

async function loadAllAvailableFiles() {
    debugLog('📂 Fetching all available output files...');
    
    try {
        const response = await fetch('/api/browse-files');
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        const data = await response.json();
        
        debugLog(`✅ Found ${data.total_files} files across ${data.directories} directories`);
        
        displayAllFiles(data);
        
    } catch (error) {
        console.error('❌ Failed to load files:', error);
        const filesContent = document.getElementById('filesContent');
        if (filesContent) {
            filesContent.innerHTML = `
                <p style="color: #f87171;">Failed to load files: ${error.message}</p>
                <p style="color: #9ca3af; font-size: 12px;">Try refreshing the page.</p>
            `;
        }
    }
}

function displayAllFiles(data) {
    const filesContent = document.getElementById('filesContent');
    if (!filesContent) return;
    
    if (data.total_files === 0) {
        filesContent.innerHTML = `
            <p style="color: #9ca3af;">No output files found.</p>
            <p style="color: #60a5fa; font-size: 12px;">
                Run an analysis to generate files.
            </p>
        `;
        return;
    }
    
    let html = '<div style="margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center;">';
    html += `<p style="color: #22c55e; font-weight: 600; margin: 0;">Found ${data.total_files} files</p>`;
    html += `
        <button id="downloadAllZipButton" data-default-label="📦 Download All as ZIP" onclick="downloadAllAsZip()" 
                style="padding: 8px 16px; background: rgba(34, 197, 94, 0.2); border: 1px solid rgba(34, 197, 94, 0.5); border-radius: 6px; color: #22c55e; cursor: pointer; font-weight: 600; font-size: 13px; display: flex; align-items: center; gap: 6px;">
            📦 Download All as ZIP
        </button>
    `;
    html += '</div>';
    
    // Group by directory
    const byDirectory = data.files_by_directory;
    
    for (const [dirName, files] of Object.entries(byDirectory)) {
        html += `
            <div style="margin-bottom: 30px; padding: 15px; background: rgba(59, 130, 246, 0.05); border-radius: 8px; border: 1px solid rgba(59, 130, 246, 0.2);">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                    <h4 style="color: #60a5fa; margin: 0;">
                        📂 ${dirName.replace(/_/g, ' ')}
                    </h4>
                    <button data-folder-zip-button="${dirName}" data-default-label="📦 Download Folder" onclick="downloadFolderAsZip('${dirName}')" 
                            style="padding: 6px 12px; background: rgba(139, 92, 246, 0.2); border: 1px solid rgba(139, 92, 246, 0.5); border-radius: 4px; color: #a78bfa; cursor: pointer; font-size: 12px; font-weight: 600;">
                        📦 Download Folder
                    </button>
                </div>
                <div style="margin-left: 10px;">
        `;
        
        // Sort files: .log first, then .json, then others
        const sortedFiles = files.sort((a, b) => {
            const order = { 'log': 0, 'json': 1 };
            const aOrder = order[a.type] ?? 2;
            const bOrder = order[b.type] ?? 2;
            return aOrder - bOrder;
        });
        
        for (const file of sortedFiles) {
            const icon = getFileIcon(file.type);
            const sizeStr = formatFileSize(file.size);
            const dateStr = new Date(file.created_at).toLocaleString();
            
            html += `
                <div style="display: flex; align-items: center; padding: 8px; border-bottom: 1px solid rgba(59, 130, 246, 0.1);">
                    <span style="font-size: 18px; margin-right: 10px;">${icon}</span>
                    <div style="flex: 1;">
                        <div style="color: #e5e7eb; font-weight: 500;">${file.name}</div>
                        <div style="color: #9ca3af; font-size: 11px;">${sizeStr} • ${dateStr}</div>
                    </div>
                    <button onclick="downloadFileFromBrowser('${file.path}')" 
                            style="padding: 6px 12px; background: rgba(59, 130, 246, 0.2); border: 1px solid rgba(59, 130, 246, 0.5); border-radius: 4px; color: #60a5fa; cursor: pointer; font-size: 12px;">
                        📥 Download
                    </button>
                </div>
            `;
        }
        
        html += '</div></div>';
    }
    
    filesContent.innerHTML = html;
}

function getFileIcon(type) {
    const icons = {
        'log': '📋',
        'json': '📄',
        'csv': '📊',
        'md': '📝',
        'txt': '📃'
    };
    return icons[type] || '📎';
}

function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / 1048576).toFixed(1) + ' MB';
}

async function downloadFileFromBrowser(filePath) {
    if (!filePath) {
        console.error('downloadFileFromBrowser called with no path');
        return;
    }
    
    debugLog(`📥 Downloading file: ${filePath}`);
    
    try {
        const response = await fetch(`/outputs/${filePath}`);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filePath.split('/').pop(); // Get just the filename
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        
        debugLog(`✅ Download started: ${filePath}`);
    } catch (error) {
        console.error(`❌ Download failed: ${error.message}`);
        notifyZipStatus(`Failed to download file: ${error.message}`, 'error');
    }
}

// Auto-load files when page loads
document.addEventListener('DOMContentLoaded', () => {
    debugLog('🚀 Page loaded, loading available files...');
    loadAllAvailableFiles();
    
    // Refresh files every 30 seconds
    setInterval(loadAllAvailableFiles, 30000);
});

async function downloadAllAsZip() {
    if (allZipDownloadInProgress) {
        notifyZipStatus('A ZIP download is already running.', 'warning');
        return;
    }
    allZipDownloadInProgress = true;
    setAllZipButtonState(true);
    debugLog('📦 Requesting ZIP download from /api/download-zip?file_type=all');
    
    const performDownload = async () => {
        const response = await fetch('/api/download-zip?file_type=all');
        
        debugLog('Response status:', response.status, response.statusText);
        
        if (!response.ok) {
            const errorText = await response.text();
            console.error('ZIP download error response:', errorText);
            const error = new Error(`${response.status} ${response.statusText}\n\n${errorText}`);
            if (response.status >= 400 && response.status < 500 && response.status !== 429) {
                error.nonRetryable = true;
            }
            throw error;
        }
        
        return response;
    };

    try {
        const response = await downloadWithRetry(performDownload);
        
        // Get filename from response headers
        const contentDisposition = response.headers.get('Content-Disposition');
        let filename = 'outputs.zip';
        if (contentDisposition) {
            const match = contentDisposition.match(/filename=(.+)/);
            if (match) {
                filename = match[1].replace(/['"]/g, '');
            }
        }
        
        // Download the ZIP
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        
        debugLog(`✅ ZIP download started: ${filename}`);
    } catch (error) {
        console.error(`❌ ZIP download failed: ${error.message}`);
        notifyZipStatus(`Failed to download ZIP: ${error.message}`, 'error');
    } finally {
        allZipDownloadInProgress = false;
        setAllZipButtonState(false);
    }
}

async function downloadFolderAsZip(folderName) {
    if (folderZipDownloadsInProgress.has(folderName)) {
        notifyZipStatus(`A ZIP download for ${folderName} is already running.`, 'warning');
        return;
    }
    folderZipDownloadsInProgress.add(folderName);
    setFolderZipButtonState(folderName, true);
    debugLog('Requesting folder ZIP:', folderName);
    const fullUrl = '/api/download-folder-zip?folder=' + encodeURIComponent(folderName);
    debugLog('Full URL:', fullUrl);
    
    const performDownload = async () => {
        const response = await fetch(fullUrl);
        
        debugLog('Response status:', response.status, response.statusText);
        
        if (!response.ok) {
            const errorText = await response.text();
            console.error('ZIP download error response:', errorText);
            const error = new Error(`${response.status} ${response.statusText}\n\n${errorText}`);
            if (response.status >= 400 && response.status < 500 && response.status !== 429) {
                error.nonRetryable = true;
            }
            throw error;
        }
        
        return response;
    };
    
    try {
        const response = await downloadWithRetry(performDownload);
        
        // Get filename from response headers
        const contentDisposition = response.headers.get('Content-Disposition');
        let filename = `${folderName}.zip`;
        if (contentDisposition) {
            const match = contentDisposition.match(/filename=(.+)/);
            if (match) {
                filename = match[1].replace(/['"]/g, '');
            }
        }
        
        // Download the ZIP
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        
        debugLog(`✅ Folder ZIP download started: ${filename}`);
    } catch (error) {
        console.error(`❌ Folder ZIP download failed: ${error.message}`);
        notifyZipStatus(`Failed to download folder ZIP: ${error.message}`, 'error');
    } finally {
        folderZipDownloadsInProgress.delete(folderName);
        setFolderZipButtonState(folderName, false);
    }
}

/**
 * Retry helper for downloads
 */
async function downloadWithRetry(fn, retries = 3, delay = 1000) {
    let lastError;
    
    for (let i = 0; i < retries; i++) {
        try {
            return await fn();
        } catch (error) {
            console.warn(`Download attempt ${i + 1} failed:`, error);
            lastError = error;
            if (error && error.nonRetryable) {
                break;
            }
            if (i < retries - 1) {
                await new Promise(resolve => setTimeout(resolve, delay));
            }
        }
    }
    
    throw lastError;
}

// Export to global scope
window.loadAllAvailableFiles = loadAllAvailableFiles;
window.downloadFileFromBrowser = downloadFileFromBrowser;
window.downloadAllAsZip = downloadAllAsZip;
window.downloadFolderAsZip = downloadFolderAsZip;

debugLog('✅ File browser loaded');

