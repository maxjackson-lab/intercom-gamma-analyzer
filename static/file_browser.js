/**
 * File Browser - Auto-loads and displays all available output files
 * 
 * Loads immediately on page load so user can see past analysis files
 * WITHOUT needing to run a new analysis first.
 */

console.log('📁 File browser loading...');

async function loadAllAvailableFiles() {
    console.log('📂 Fetching all available output files...');
    
    try {
        const response = await fetch('/api/browse-files');
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        const data = await response.json();
        
        console.log(`✅ Found ${data.total_files} files across ${data.directories} directories`);
        
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
    
    let html = '<div style="margin-bottom: 20px;">';
    html += `<p style="color: #22c55e; font-weight: 600;">Found ${data.total_files} files</p>`;
    html += '</div>';
    
    // Group by directory
    const byDirectory = data.files_by_directory;
    
    for (const [dirName, files] of Object.entries(byDirectory)) {
        html += `
            <div style="margin-bottom: 30px; padding: 15px; background: rgba(59, 130, 246, 0.05); border-radius: 8px; border: 1px solid rgba(59, 130, 246, 0.2);">
                <h4 style="color: #60a5fa; margin: 0 0 10px 0;">
                    📂 ${dirName.replace(/_/g, ' ')}
                </h4>
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
                    <button onclick="downloadFile('${file.name}')" 
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

// Auto-load files when page loads
document.addEventListener('DOMContentLoaded', () => {
    console.log('🚀 Page loaded, loading available files...');
    loadAllAvailableFiles();
    
    // Refresh files every 30 seconds
    setInterval(loadAllAvailableFiles, 30000);
});

// Export to global scope
window.loadAllAvailableFiles = loadAllAvailableFiles;

console.log('✅ File browser loaded');

