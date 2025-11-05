"""
Railway web server for Intercom Analysis Tool - Historical Insights Timeline Interface.
Provides a timeline view for exploring historical Voice of Customer analysis snapshots.
"""

import os
import sys
import json
import asyncio
import warnings
from datetime import datetime, date
from pathlib import Path
from typing import Dict, Any, List, Optional

# Suppress Pydantic serializer warnings from Intercom SDK
warnings.filterwarnings('ignore', category=UserWarning, message='.*Pydantic serializer warnings.*')
warnings.filterwarnings('ignore', category=UserWarning, message='.*Expected.*but got.*serialized value.*')

# Verify Python path setup
print(f"🔧 PYTHONPATH: {os.environ.get('PYTHONPATH', 'Not set')}")
print(f"🔧 Current working directory: {os.getcwd()}")
print(f"🔧 Script location: {__file__}")

# Test src import (should work now that script is in project root)
try:
    import src
    print(f"✅ Successfully imported src module")
except ImportError as e:
    print(f"❌ Failed to import src: {e}")
    print(f"🔧 sys.path: {sys.path[:3]}")  # Show first 3 entries

try:
    from fastapi import FastAPI, HTTPException, Request, Depends
    from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
    from fastapi.staticfiles import StaticFiles
    from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel
    import uvicorn
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False

# Import services
try:
    from src.services.duckdb_storage import DuckDBStorage
    from src.services.historical_snapshot_service import HistoricalSnapshotService
    from src.config.settings import Settings
    HAS_SERVICES = True
    print("✅ Service dependencies imported successfully")
except ImportError as e:
    HAS_SERVICES = False
    print(f"❌ Service dependencies import failed: {e}")

# Initialize FastAPI app
if HAS_FASTAPI:
    app = FastAPI(
        title="Intercom Analysis Tool - Historical Insights Timeline",
        description="Timeline interface for exploring historical VoC analysis snapshots",
        version="2.0.0"
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Security scheme for bearer token authentication
    security = HTTPBearer(auto_error=False)
    
    async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
        """
        Verify bearer token for protected endpoints.
        
        This protects sensitive endpoints (like marking snapshots reviewed) from unauthorized access.
        Token validation can be customized based on your security requirements.
        """
        # Get the expected token from environment (if not set, allow local development)
        expected_token = os.getenv("EXECUTION_API_TOKEN")
        
        # If no token is configured, allow access (for development/backwards compatibility)
        # In production, you should always set EXECUTION_API_TOKEN
        if not expected_token:
            return "development"
        
        # Check if credentials were provided
        if not credentials:
            raise HTTPException(
                status_code=403,
                detail="Authentication required. Please provide a valid bearer token."
            )
        
        # Validate the token
        if credentials.credentials != expected_token:
            raise HTTPException(
                status_code=403,
                detail="Invalid authentication credentials"
            )
        
        return credentials.credentials
    
    # Pydantic models for API requests/responses
    class ReviewRequest(BaseModel):
        reviewed_by: str
        notes: Optional[str] = None
else:
    # Fallback for when FastAPI is not available
    app = None
    ReviewRequest = None

# Global service instances
duckdb_storage = None
historical_service = None
logger = None

def initialize_services():
    """Initialize DuckDB and HistoricalSnapshotService."""
    global duckdb_storage, historical_service, logger
    if not HAS_SERVICES:
        print("❌ Service dependencies not available")
        return False
    
    try:
        print("🔧 Initializing DuckDB storage...")
        duckdb_storage = DuckDBStorage()
        print("✅ DuckDB storage initialized successfully")
        
        print("🔧 Initializing Historical Snapshot Service...")
        historical_service = HistoricalSnapshotService(duckdb_storage)
        print("✅ Historical Snapshot Service initialized successfully")
        
        return True
    except Exception as e:
        print(f"❌ Failed to initialize services: {e}")
        import traceback
        traceback.print_exc()
        return False


if HAS_FASTAPI:
    @app.get("/", response_class=HTMLResponse)
    async def root():
        """Serve the timeline interface HTML."""
        html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VoC Historical Insights - Timeline</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <link rel="stylesheet" href="/static/styles.css">
    </head>
    <body>
        <div class="container">
        <h1>📊 Voice of Customer - Historical Insights</h1>
        
        <!-- Historical Context Banner -->
        <div id="contextBanner" class="context-banner" style="display:none;"></div>
        
        <!-- Tab Navigation -->
        <div class="tab-navigation">
            <button class="tab-button active" onclick="switchTab('weekly')" data-type="weekly">Weekly</button>
            <button class="tab-button" onclick="switchTab('monthly')" data-type="monthly">Monthly</button>
            <button class="tab-button" onclick="switchTab('quarterly')" data-type="quarterly">Quarterly</button>
            </div>
            
        <!-- Timeline Container -->
        <div id="timelineContainer" class="timeline-container"></div>
        
        <!-- Trend Chart (shown when ≥4 weeks) -->
        <div id="trendChartSection" class="trend-chart-section" style="display:none;">
            <h3>Topic Volume Trends</h3>
            <canvas id="volumeTrendChart"></canvas>
                </div>
            </div>
            
    <script src="/static/timeline.js"></script>
</body>
</html>
        """
        return html_content
    
    @app.get("/analysis/history", response_class=HTMLResponse)
    async def analysis_history():
        """Serve the timeline interface (same as root)."""
        return await root()
    
    @app.get("/api/snapshots/list")
    async def list_snapshots(analysis_type: Optional[str] = None, limit: int = 20):
        """
        List all snapshots with optional filtering by analysis type.
        
        Query params:
            analysis_type: Filter by type (weekly, monthly, quarterly). If None, returns all.
            limit: Maximum number of snapshots to return (default 20)
        
        Returns:
            {snapshots: [...], context: {...}}
        """
        if not historical_service:
            raise HTTPException(status_code=500, detail="Historical service not available")
        
        try:
            # Fetch snapshots
            snapshots = await historical_service.list_snapshots_async(analysis_type, limit)
            
            # Get historical context (data availability stats)
            context = await historical_service.get_historical_context_async()
            
            # Normalize date/datetime fields in context to ISO strings for JSON serialization
            if 'baseline_date' in context and isinstance(context['baseline_date'], (date, datetime)):
                context['baseline_date'] = context['baseline_date'].isoformat()
            if 'earliest_snapshot' in context and isinstance(context['earliest_snapshot'], (date, datetime)):
                context['earliest_snapshot'] = context['earliest_snapshot'].isoformat()
            if 'latest_snapshot' in context and isinstance(context['latest_snapshot'], (date, datetime)):
                context['latest_snapshot'] = context['latest_snapshot'].isoformat()
            
            # Convert date objects to ISO strings for JSON serialization
            for snapshot in snapshots:
                if 'period_start' in snapshot and isinstance(snapshot['period_start'], date):
                    snapshot['period_start'] = snapshot['period_start'].isoformat()
                if 'period_end' in snapshot and isinstance(snapshot['period_end'], date):
                    snapshot['period_end'] = snapshot['period_end'].isoformat()
                if 'created_at' in snapshot and isinstance(snapshot['created_at'], datetime):
                    snapshot['created_at'] = snapshot['created_at'].isoformat()
                if 'reviewed_at' in snapshot and isinstance(snapshot['reviewed_at'], datetime):
                    snapshot['reviewed_at'] = snapshot['reviewed_at'].isoformat()
            
            return {
                "snapshots": snapshots,
                "context": context
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to fetch snapshots: {str(e)}")
    
    @app.get("/api/snapshots/{snapshot_id}")
    async def get_snapshot(snapshot_id: str):
        """
        Get a single snapshot by ID.
        
        Path param:
            snapshot_id: Snapshot identifier (e.g., 'weekly_20251114')
        
        Returns:
            Snapshot dict or 404 if not found
        """
        if not duckdb_storage:
            raise HTTPException(status_code=500, detail="Storage service not available")
        
        try:
            snapshot = duckdb_storage.get_analysis_snapshot(snapshot_id)
            if not snapshot:
                raise HTTPException(status_code=404, detail=f"Snapshot {snapshot_id} not found")
            
            # Convert date objects to ISO strings
            if 'period_start' in snapshot and isinstance(snapshot['period_start'], date):
                snapshot['period_start'] = snapshot['period_start'].isoformat()
            if 'period_end' in snapshot and isinstance(snapshot['period_end'], date):
                snapshot['period_end'] = snapshot['period_end'].isoformat()
            if 'created_at' in snapshot and isinstance(snapshot['created_at'], datetime):
                snapshot['created_at'] = snapshot['created_at'].isoformat()
            if 'reviewed_at' in snapshot and isinstance(snapshot['reviewed_at'], datetime):
                snapshot['reviewed_at'] = snapshot['reviewed_at'].isoformat()
            
            return snapshot
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to fetch snapshot: {str(e)}")
    
    @app.post("/api/snapshots/{snapshot_id}/review")
    async def mark_reviewed(
        snapshot_id: str,
        review: ReviewRequest,
        token: str = Depends(verify_token)
    ):
        """
        Mark a snapshot as reviewed.
        
        Path param:
            snapshot_id: Snapshot identifier
        
        Body:
            reviewed_by: User who reviewed (required)
            notes: Optional review notes
        
        Requires authentication via bearer token.
        """
        if not duckdb_storage:
            raise HTTPException(status_code=500, detail="Storage service not available")
        
        try:
            success = duckdb_storage.mark_snapshot_reviewed(
                snapshot_id,
                review.reviewed_by,
                review.notes
            )
            
            if not success:
                raise HTTPException(status_code=404, detail=f"Snapshot {snapshot_id} not found")
            
            return {
                "success": True,
                "message": f"Snapshot {snapshot_id} marked as reviewed by {review.reviewed_by}"
            }
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to mark reviewed: {str(e)}")
    
    @app.get("/api/snapshots/timeseries")
    async def get_timeseries(analysis_type: str = 'weekly', limit: int = 12):
        """
        Get time-series data for trend charts.
        
        Query params:
            analysis_type: Type of snapshots (weekly, monthly, quarterly)
            limit: Number of most recent snapshots to include (default 12)
        
        Returns:
            Chart.js compatible format: {labels: [...], datasets: [...]}
        """
        if not historical_service:
            raise HTTPException(status_code=500, detail="Historical service not available")
        
        try:
            # Fetch snapshots
            snapshots = await historical_service.list_snapshots_async(analysis_type, limit)
            
            if not snapshots:
                return {"labels": [], "datasets": []}
            
            # Sort by period_end ascending
            snapshots.sort(key=lambda s: s.get('period_end') or date.min)
            
            # Extract labels (date ranges)
            labels = [s.get('date_range_label', 'Unknown') for s in snapshots]
            
            # Extract topic volumes and create datasets
            topic_volumes_by_name = {}
            
            for snapshot in snapshots:
                topic_vols = snapshot.get('topic_volumes', {})
                if isinstance(topic_vols, dict):
                    for topic_name, volume in topic_vols.items():
                        if topic_name not in topic_volumes_by_name:
                            topic_volumes_by_name[topic_name] = []
                        topic_volumes_by_name[topic_name].append(volume)
            
            # Build Chart.js datasets
            colors = [
                '#667eea', '#764ba2', '#f093fb', '#4facfe',
                '#43e97b', '#fa709a', '#fee140', '#30cfd0'
            ]
            
            datasets = []
            for i, (topic_name, values) in enumerate(topic_volumes_by_name.items()):
                # Pad values if needed (some snapshots might not have all topics)
                padded_values = values + [0] * (len(labels) - len(values))
                
                datasets.append({
                    "label": topic_name,
                    "data": padded_values,
                    "borderColor": colors[i % len(colors)],
                    "backgroundColor": colors[i % len(colors)] + '33',  # Add transparency
                    "tension": 0.4
                })
            
            return {
                "labels": labels,
                "datasets": datasets
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to fetch timeseries: {str(e)}")
    
    @app.get("/analysis/view/{snapshot_id}", response_class=HTMLResponse)
    async def view_snapshot(snapshot_id: str):
        """
        View detailed snapshot report.
        
        Path param:
            snapshot_id: Snapshot identifier
        """
        if not duckdb_storage:
            raise HTTPException(status_code=500, detail="Storage service not available")
        
        try:
            snapshot = duckdb_storage.get_analysis_snapshot(snapshot_id)
            if not snapshot:
                raise HTTPException(status_code=404, detail=f"Snapshot {snapshot_id} not found")
            
            # Build HTML for snapshot detail view
            html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{snapshot.get('date_range_label', 'Snapshot')} - VoC Analysis</title>
    <link rel="stylesheet" href="/static/styles.css">
</head>
<body>
    <div class="container">
        <a href="/" style="color: #667eea; text-decoration: none; display: inline-block; margin-bottom: 20px;">← Back to Timeline</a>
        
        <h1>📊 {snapshot.get('date_range_label', 'Snapshot Details')}</h1>
        
        <div class="summary-container">
            <h3>Analysis Summary</h3>
            <div class="summary-cards">
                <div class="summary-card">
                    <div class="card-title">Type</div>
                    <div class="card-value">{snapshot.get('analysis_type', 'Unknown').title()}</div>
                </div>
                <div class="summary-card">
                    <div class="card-title">Total Conversations</div>
                    <div class="card-value">{snapshot.get('total_conversations', 0):,}</div>
                </div>
                <div class="summary-card">
                    <div class="card-title">Created</div>
                    <div class="card-value">{snapshot.get('created_at', 'Unknown')}</div>
                </div>
            </div>
            
            <div style="margin-top: 20px; padding: 20px; background: #0a0a0a; border-radius: 12px;">
                <h4 style="color: #e5e7eb; margin-bottom: 12px;">Key Insights</h4>
                <p style="color: #9ca3af; line-height: 1.6;">{snapshot.get('insights_summary', 'No summary available')}</p>
            </div>
            
            <div style="margin-top: 20px;">
                <h4 style="color: #e5e7eb; margin-bottom: 12px;">Topic Volumes</h4>
                <div class="summary-cards">
                    {''.join([f'<div class="summary-card"><div class="card-title">{topic}</div><div class="card-value">{vol}</div></div>' for topic, vol in (snapshot.get('topic_volumes', {}) or {}).items()])}
                </div>
            </div>
        </div>
    </div>
    </body>
    </html>
        """
            return html
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to load snapshot: {str(e)}")
    
    @app.get("/analysis/compare/{current_id}/{prior_id}", response_class=HTMLResponse)
    async def compare_snapshots(current_id: str, prior_id: str):
        """
        Compare two snapshots side-by-side.
        
        Path params:
            current_id: Current period snapshot ID
            prior_id: Prior period snapshot ID
        """
        if not historical_service or not duckdb_storage:
            raise HTTPException(status_code=500, detail="Services not available")
        
        try:
            current = duckdb_storage.get_analysis_snapshot(current_id)
            prior = duckdb_storage.get_analysis_snapshot(prior_id)
            
            if not current or not prior:
                raise HTTPException(status_code=404, detail="One or both snapshots not found")
            
            # Calculate comparison
            comparison = historical_service.calculate_comparison(current, prior)
            
            # Build HTML for comparison view
            volume_changes_html = '<br>'.join([
                f"{topic}: {change:+.1f}% ({abs_change:+d} conversations)"
                for topic, change, abs_change in comparison.get('volume_changes', [])
            ])
            
            html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Comparison - VoC Analysis</title>
    <link rel="stylesheet" href="/static/styles.css">
</head>
<body>
    <div class="container">
        <a href="/" style="color: #667eea; text-decoration: none; display: inline-block; margin-bottom: 20px;">← Back to Timeline</a>
        
        <h1>📊 Period Comparison</h1>
        
        <div class="summary-container">
            <h3>Comparing Periods</h3>
            <div class="summary-cards">
                <div class="summary-card">
                    <div class="card-title">Current Period</div>
                    <div class="card-value">{current.get('date_range_label', 'Unknown')}</div>
                </div>
                <div class="summary-card">
                    <div class="card-title">Prior Period</div>
                    <div class="card-value">{prior.get('date_range_label', 'Unknown')}</div>
                </div>
            </div>
            
            <div style="margin-top: 20px; padding: 20px; background: #0a0a0a; border-radius: 12px;">
                <h4 style="color: #e5e7eb; margin-bottom: 12px;">Volume Changes</h4>
                <p style="color: #9ca3af; line-height: 1.8;">{volume_changes_html or 'No significant changes'}</p>
            </div>
            
            <div style="margin-top: 20px; padding: 20px; background: #0a0a0a; border-radius: 12px;">
                <h4 style="color: #e5e7eb; margin-bottom: 12px;">Significant Changes</h4>
                <ul style="color: #9ca3af; line-height: 1.8;">
                    {''.join([f'<li>{change}</li>' for change in comparison.get('significant_changes', [])])}
                </ul>
            </div>
        </div>
    </div>
</body>
</html>
            """
            return html
        except HTTPException:
                raise
            except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to compare snapshots: {str(e)}")

    @app.get("/health")
    async def health_check():
        """Health check endpoint for Railway."""
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "duckdb_storage": duckdb_storage is not None,
            "historical_service": historical_service is not None,
            "fastapi": HAS_FASTAPI,
            "services": HAS_SERVICES
        }
    
    @app.get("/download")
    async def download_file(file: str):
        """
        Download a file from the outputs directory.
        
        Security: Only allows downloading from the outputs directory.
        """
        try:
            # Security: Validate the file path
            file_path = Path(file)
            
            # Ensure the file is in the outputs directory
            if not str(file_path).startswith('outputs/') and not str(file_path).startswith('./outputs/'):
                # Try prepending outputs/
                file_path = Path('outputs') / file_path.name
            
            # Resolve to absolute path and validate
            abs_file_path = file_path.resolve()
            outputs_dir = Path('outputs').resolve()
            
            # Security check: Ensure file is within outputs directory
            try:
                abs_file_path.relative_to(outputs_dir)
            except ValueError:
                raise HTTPException(
                    status_code=403,
                    detail="Access denied: File must be in outputs directory"
                )
            
            # Check if file exists
            if not abs_file_path.exists():
                raise HTTPException(
                    status_code=404,
                    detail=f"File not found: {file_path.name}"
                )
            
            # Check if it's a file (not a directory)
            if not abs_file_path.is_file():
                raise HTTPException(
                    status_code=400,
                    detail="Path is not a file"
                )
            
            # Return the file
            return FileResponse(
                path=abs_file_path,
                filename=abs_file_path.name,
                media_type='application/octet-stream'
            )
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Download error: {str(e)}")
    
    # Mount static files
    try:
        app.mount("/static", StaticFiles(directory="static"), name="static")
    except Exception as e:
        print(f"⚠️  Warning: Could not mount static files directory: {e}")


def main():
    """Main entrypoint for Railway web server."""
    if not HAS_FASTAPI:
        print("❌ FastAPI not available. Install with: pip install fastapi uvicorn")
        sys.exit(1)
    
    print("🚀 Starting Intercom Analysis Tool - Historical Insights Timeline Interface...")
    
    # Try to initialize services (but don't fail if it doesn't work)
    print("🔧 Attempting to initialize services...")
    services_init_success = initialize_services()
    
    if services_init_success:
        print("✅ Services initialized successfully")
    else:
        print("⚠️ Services initialization failed, but server will start anyway")
        print("   The health endpoint will still work, but timeline features may be limited")
    
    # Get port from Railway environment
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    
    print(f"🌐 Starting web server on {host}:{port}")
    print(f"📊 Timeline UI available at: http://{host}:{port}")
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
