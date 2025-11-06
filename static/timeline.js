/**
 * timeline.js - Historical Insights Timeline UI
 * 
 * Handles all client-side logic for the historical insights timeline interface
 */

// Global state
let currentAnalysisType = 'weekly';
let snapshots = [];
let historicalContext = {};
let trendChart = null;

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    console.log('Timeline UI initialized');
    
    // Set up tab button handlers
    const tabButtons = document.querySelectorAll('.tab-button');
    tabButtons.forEach(button => {
        button.addEventListener('click', function() {
            const type = this.getAttribute('data-type');
            switchTab(type);
        });
    });
    
    // Load initial data (weekly snapshots)
    loadSnapshots('weekly');
});

/**
 * Load snapshots from API
 */
async function loadSnapshots(analysisType = 'weekly') {
    currentAnalysisType = analysisType;
    
    try {
        console.log(`Loading ${analysisType} snapshots...`);
        
        const response = await fetch(`/api/snapshots/list?analysis_type=${analysisType}&limit=20`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        snapshots = data.snapshots || [];
        historicalContext = data.context || {};
        
        console.log(`Loaded ${snapshots.length} snapshots`);
        
        // Render timeline
        renderTimeline();
        
        // Update context banner
        updateContextBanner();
        
        // Render trend chart if applicable
        renderTrendChart();
        
    } catch (error) {
        console.error('Failed to load snapshots:', error);
        showError(`Failed to load snapshots: ${error.message}`);
    }
}

/**
 * Render timeline cards
 */
function renderTimeline() {
    const timelineContainer = document.getElementById('timelineContainer');
    
    if (!timelineContainer) {
        console.error('Timeline container not found');
        return;
    }
    
    // Clear existing content
    timelineContainer.innerHTML = '';
    
    if (snapshots.length === 0) {
        timelineContainer.innerHTML = '<div style="text-align: center; padding: 40px; color: #9ca3af;">No snapshots available for this period</div>';
        return;
    }
    
    // Determine "current" snapshot (most recent with period_end <= today)
    const today = new Date();
    let currentSnapshotIndex = -1;
    
    for (let i = 0; i < snapshots.length; i++) {
        const periodEnd = new Date(snapshots[i].period_end);
        if (periodEnd <= today) {
            currentSnapshotIndex = i;
            break;
        }
    }
    
    // Render each snapshot card
    snapshots.forEach((snapshot, index) => {
        const card = createSnapshotCard(snapshot, index === currentSnapshotIndex);
        timelineContainer.appendChild(card);
    });
}

/**
 * Create a snapshot card element
 */
function createSnapshotCard(snapshot, isCurrent) {
    const card = document.createElement('div');
    const periodEnd = new Date(snapshot.period_end);
    const today = new Date();
    
    // Determine card status
    let status = '';
    let statusBadge = '';
    let checked = '';
    
    if (snapshot.reviewed) {
        status = 'reviewed';
        statusBadge = '<span class="status-badge reviewed">✓ Reviewed</span>';
        checked = 'checked';
    } else if (isCurrent) {
        status = 'current';
        statusBadge = '<span class="status-badge current">⭐ Current</span>';
    } else if (periodEnd > today) {
        status = 'future';
        statusBadge = '<span class="status-badge future">Future</span>';
    }
    
    card.className = `snapshot-card ${status}`;
    card.setAttribute('data-id', snapshot.snapshot_id);
    
    // Calculate change indicator (if available)
    let changeIndicator = '';
    // This would require prior period data - placeholder for now
    
    card.innerHTML = `
        <div class="card-header">
            <input type="checkbox" class="review-checkbox" ${checked} ${status === 'future' ? 'disabled' : ''} 
                   onchange="markReviewed('${snapshot.snapshot_id}')">
            <span class="snapshot-label">${snapshot.date_range_label || 'Unknown Period'}</span>
            ${statusBadge}
        </div>
        <div class="card-summary">${snapshot.insights_summary || 'No summary available'}</div>
        <div class="card-metrics">
            <span>📊 ${(snapshot.total_conversations || 0).toLocaleString()} conversations</span>
            ${changeIndicator}
        </div>
        <div class="card-actions">
            <button onclick="viewSnapshot('${snapshot.snapshot_id}')" class="primary">View Report</button>
            <button onclick="compareSnapshot('${snapshot.snapshot_id}')">Compare</button>
        </div>
    `;
    
    return card;
}

/**
 * Update historical context banner
 */
function updateContextBanner() {
    const banner = document.getElementById('contextBanner');
    
    if (!banner || !historicalContext) {
        return;
    }
    
    const weeksAvailable = historicalContext.weeks_available || 0;
    const canDoTrends = historicalContext.can_do_trends || false;
    const canDoSeasonality = historicalContext.can_do_seasonality || false;
    
    if (weeksAvailable === 0) {
        banner.style.display = 'none';
        return;
    }
    
    let message = `<span class="icon">📈</span> ${weeksAvailable} weeks of data available`;
    
    if (canDoTrends) {
        message += ' - Trend analysis enabled';
    }
    
    if (canDoSeasonality) {
        message += ' - Seasonality detection enabled';
    } else if (weeksAvailable < 12) {
        const weeksUntil = 12 - weeksAvailable;
        message += ` - ${weeksUntil} more weeks until seasonality detection`;
    }
    
    banner.innerHTML = message;
    banner.style.display = 'flex';
}

/**
 * Mark snapshot as reviewed
 */
async function markReviewed(snapshotId) {
    // Check if checkbox is being unchecked (not supported yet)
    const checkbox = document.querySelector(`[data-id="${snapshotId}"] .review-checkbox`);
    if (!checkbox.checked) {
        checkbox.checked = true;
        showError('Cannot unmark as reviewed. Feature not yet implemented.');
        return;
    }
    
    // Prompt for reviewer name
    const reviewerName = prompt('Enter your name:');
    if (!reviewerName) {
        checkbox.checked = false;
        return;
    }
    
    // Optional: Prompt for notes
    const notes = prompt('Optional notes:');
    
    try {
        const response = await fetch(`/api/snapshots/${snapshotId}/review`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                reviewed_by: reviewerName,
                notes: notes || undefined
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const result = await response.json();
        
        if (result.success) {
            // Update card UI
            const card = document.querySelector(`[data-id="${snapshotId}"]`);
            if (card) {
                card.classList.add('reviewed');
                const statusBadge = card.querySelector('.status-badge');
                if (statusBadge) {
                    statusBadge.className = 'status-badge reviewed';
                    statusBadge.textContent = '✓ Reviewed';
                }
            }
            
            showSuccess(`Snapshot marked as reviewed by ${reviewerName}`);
        }
        
    } catch (error) {
        console.error('Failed to mark reviewed:', error);
        checkbox.checked = false;
        showError(`Failed to mark as reviewed: ${error.message}`);
    }
}

/**
 * View snapshot details
 */
async function viewSnapshot(snapshotId) {
    // Navigate to detail view (full page navigation)
    window.location.href = `/analysis/view/${snapshotId}`;
}

/**
 * Compare snapshot with prior period
 */
async function compareSnapshot(currentId) {
    // Find prior snapshot in list
    const currentIndex = snapshots.findIndex(s => s.snapshot_id === currentId);
    
    if (currentIndex === -1 || currentIndex === snapshots.length - 1) {
        showError('No prior period available for comparison');
        return;
    }
    
    const priorId = snapshots[currentIndex + 1].snapshot_id;
    
    // Navigate to comparison view
    window.location.href = `/analysis/compare/${currentId}/${priorId}`;
}

/**
 * Render trend chart
 */
async function renderTrendChart() {
    const chartSection = document.getElementById('trendChartSection');
    const canvas = document.getElementById('volumeTrendChart');
    
    if (!chartSection || !canvas) {
        console.error('Chart elements not found');
        return;
    }
    
    // Check if trend analysis is possible
    if (!historicalContext.can_do_trends) {
        chartSection.style.display = 'none';
        return;
    }
    
    try {
        console.log('Fetching time-series data...');
        
        const response = await fetch(`/api/snapshots/timeseries?analysis_type=${currentAnalysisType}&limit=12`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        if (!data.labels || data.labels.length === 0) {
            chartSection.style.display = 'none';
            return;
        }
        
        // Destroy existing chart if it exists
        if (trendChart) {
            trendChart.destroy();
        }
        
        // Create new chart
        const ctx = canvas.getContext('2d');
        trendChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.labels,
                datasets: data.datasets
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    title: {
                        display: true,
                        text: `${currentAnalysisType.charAt(0).toUpperCase() + currentAnalysisType.slice(1)} Topic Volume Trends`,
                        color: '#e5e7eb',
                        font: {
                            size: 16,
                            weight: '600'
                        }
                    },
                    legend: {
                        position: 'top',
                        labels: {
                            color: '#9ca3af',
                            font: {
                                size: 12
                            },
                            usePointStyle: true,
                            padding: 15
                        }
                    },
                    tooltip: {
                        backgroundColor: 'rgba(17, 17, 17, 0.9)',
                        titleColor: '#e5e7eb',
                        bodyColor: '#9ca3af',
                        borderColor: '#333',
                        borderWidth: 1,
                        padding: 12,
                        displayColors: true
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Conversations',
                            color: '#9ca3af',
                            font: {
                                size: 13
                            }
                        },
                        ticks: {
                            color: '#6b7280',
                            font: {
                                size: 11
                            }
                        },
                        grid: {
                            color: '#222222',
                            drawBorder: false
                        }
                    },
                    x: {
                        ticks: {
                            color: '#6b7280',
                            font: {
                                size: 11
                            }
                        },
                        grid: {
                            color: '#222222',
                            drawBorder: false
                        }
                    }
                }
            }
        });
        
        chartSection.style.display = 'block';
        console.log('Trend chart rendered successfully');
        
    } catch (error) {
        console.error('Failed to render trend chart:', error);
        chartSection.style.display = 'none';
    }
}

/**
 * Switch between analysis type tabs
 */
function switchTab(analysisType) {
    console.log(`Switching to ${analysisType} tab`);
    
    // Update tab button styling
    const tabButtons = document.querySelectorAll('.tab-button');
    tabButtons.forEach(button => {
        if (button.getAttribute('data-type') === analysisType) {
            button.classList.add('active');
        } else {
            button.classList.remove('active');
        }
    });
    
    // Load snapshots for new type
    loadSnapshots(analysisType);
}

/**
 * Show error message
 */
function showError(message) {
    const banner = document.getElementById('contextBanner');
    if (banner) {
        banner.innerHTML = `<span style="color: #ef4444;">❌ ${message}</span>`;
        banner.style.background = 'rgba(239, 68, 68, 0.15)';
        banner.style.border = '1px solid rgba(239, 68, 68, 0.3)';
        banner.style.display = 'flex';
        
        // Auto-hide after 5 seconds
        setTimeout(() => {
            updateContextBanner();
        }, 5000);
    } else {
        alert(message);
    }
}

/**
 * Show success message
 */
function showSuccess(message) {
    const banner = document.getElementById('contextBanner');
    if (banner) {
        const originalHTML = banner.innerHTML;
        const originalBackground = banner.style.background;
        const originalBorder = banner.style.border;
        
        banner.innerHTML = `<span style="color: #10b981;">✓ ${message}</span>`;
        banner.style.background = 'rgba(16, 185, 129, 0.15)';
        banner.style.border = '1px solid rgba(16, 185, 129, 0.3)';
        banner.style.display = 'flex';
        
        // Restore after 3 seconds
        setTimeout(() => {
            banner.innerHTML = originalHTML;
            banner.style.background = originalBackground;
            banner.style.border = originalBorder;
        }, 3000);
    }
}

/**
 * Format date to readable string
 */
function formatDate(dateString) {
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
 * Calculate change indicator
 */
function calculateChangeIndicator(current, prior) {
    if (!prior || !current) {
        return '';
    }
    
    const currentConvs = current.total_conversations || 0;
    const priorConvs = prior.total_conversations || 0;
    
    if (priorConvs === 0) {
        return '';
    }
    
    const percentChange = ((currentConvs - priorConvs) / priorConvs) * 100;
    const sign = percentChange >= 0 ? '+' : '';
    const colorClass = percentChange >= 0 ? 'trend-up' : 'trend-down';
    
    return `<span class="${colorClass}">${sign}${percentChange.toFixed(1)}% vs last period</span>`;
}

// Export functions for inline event handlers
window.switchTab = switchTab;
window.markReviewed = markReviewed;
window.viewSnapshot = viewSnapshot;
window.compareSnapshot = compareSnapshot;

console.log('Timeline UI script loaded successfully');






