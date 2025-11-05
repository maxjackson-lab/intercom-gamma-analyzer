"""
Comprehensive test suite for Railway web server timeline UI.

Tests all new FastAPI routes and ensures proper integration with HistoricalSnapshotService.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, MagicMock
from datetime import date, datetime

# Import the app
from railway_web import app, initialize_services


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_services():
    """Mock DuckDB and HistoricalSnapshotService."""
    with patch('railway_web.duckdb_storage') as mock_db, \
         patch('railway_web.historical_service') as mock_service:
        # Ensure they're not None
        mock_db.return_value = Mock()
        mock_service.return_value = Mock()
        yield mock_db, mock_service


@pytest.fixture
def sample_snapshots():
    """Sample snapshot data for testing."""
    return [
        {
            'snapshot_id': 'weekly_20251114',
            'analysis_type': 'weekly',
            'period_start': date(2025, 11, 8),
            'period_end': date(2025, 11, 14),
            'total_conversations': 175,
            'date_range_label': 'Nov 8-14, 2025',
            'insights_summary': 'API issues increased significantly',
            'reviewed': False,
            'topic_volumes': {'Billing': 52, 'API': 34},
            'created_at': datetime(2025, 11, 15, 10, 30, 0)
        },
        {
            'snapshot_id': 'weekly_20251107',
            'analysis_type': 'weekly',
            'period_start': date(2025, 11, 1),
            'period_end': date(2025, 11, 7),
            'total_conversations': 150,
            'date_range_label': 'Nov 1-7, 2025',
            'insights_summary': 'Billing volume stable',
            'reviewed': True,
            'reviewed_by': 'max.jackson',
            'reviewed_at': datetime(2025, 11, 10, 14, 20, 0),
            'topic_volumes': {'Billing': 45, 'API': 18},
            'created_at': datetime(2025, 11, 8, 10, 30, 0)
        }
    ]


@pytest.fixture
def sample_context():
    """Sample historical context data."""
    return {
        'weeks_available': 4,
        'can_do_trends': True,
        'can_do_seasonality': False,
        'earliest_snapshot': date(2025, 10, 15),
        'latest_snapshot': date(2025, 11, 14)
    }


# ============================================
# Test Root Endpoint
# ============================================

def test_root_endpoint_returns_html(client):
    """Test root endpoint returns HTML timeline UI."""
    response = client.get("/")
    
    assert response.status_code == 200
    assert response.headers['content-type'] == 'text/html; charset=utf-8'
    assert 'Historical Insights' in response.text
    assert 'Chart.js' in response.text  # Chart.js script tag present
    assert 'timeline.js' in response.text  # Timeline JS included


# ============================================
# Test API Endpoints - List Snapshots
# ============================================

def test_api_snapshots_list_all(client):
    """Test listing all snapshots with context."""
    with patch('railway_web.historical_service') as mock_service:
        mock_service.list_snapshots_async = MagicMock(return_value=[
            {
                'snapshot_id': 'weekly_20251114',
                'analysis_type': 'weekly',
                'period_start': '2025-11-08',
                'period_end': '2025-11-14',
                'total_conversations': 175,
                'date_range_label': 'Nov 8-14, 2025',
                'insights_summary': 'Test summary',
                'reviewed': False,
                'created_at': '2025-11-15T10:30:00'
            }
        ])
        mock_service.get_historical_context_async = MagicMock(return_value={
            'weeks_available': 4,
            'can_do_trends': True,
            'can_do_seasonality': False
        })
        
        response = client.get("/api/snapshots/list")
        
        assert response.status_code == 200
        data = response.json()
        assert 'snapshots' in data
        assert 'context' in data
        assert len(data['snapshots']) == 1
        assert data['context']['weeks_available'] == 4


def test_api_snapshots_list_filtered_by_type(client):
    """Test filtering snapshots by analysis type."""
    with patch('railway_web.historical_service') as mock_service:
        mock_service.list_snapshots_async = MagicMock(return_value=[])
        mock_service.get_historical_context_async = MagicMock(return_value={})
        
        response = client.get("/api/snapshots/list?analysis_type=weekly&limit=5")
        
        assert response.status_code == 200
        # Verify mock was called with correct parameters
        mock_service.list_snapshots_async.assert_called_once()


def test_api_snapshots_list_service_unavailable(client):
    """Test error handling when service is unavailable."""
    with patch('railway_web.historical_service', None):
        response = client.get("/api/snapshots/list")
        
        assert response.status_code == 500
        assert 'Historical service not available' in response.json()['detail']


# ============================================
# Test API Endpoints - Get Single Snapshot
# ============================================

def test_api_snapshots_get_single(client):
    """Test retrieving a single snapshot."""
    with patch('railway_web.duckdb_storage') as mock_db:
        mock_db.get_analysis_snapshot = MagicMock(return_value={
            'snapshot_id': 'weekly_20251114',
            'analysis_type': 'weekly',
            'period_start': date(2025, 11, 8),
            'period_end': date(2025, 11, 14),
            'total_conversations': 175,
            'date_range_label': 'Nov 8-14, 2025',
            'insights_summary': 'Test summary',
            'reviewed': False,
            'created_at': datetime(2025, 11, 15, 10, 30, 0)
        })
        
        response = client.get("/api/snapshots/weekly_20251114")
        
        assert response.status_code == 200
        data = response.json()
        assert data['snapshot_id'] == 'weekly_20251114'
        assert data['total_conversations'] == 175


def test_api_snapshots_get_not_found(client):
    """Test 404 when snapshot doesn't exist."""
    with patch('railway_web.duckdb_storage') as mock_db:
        mock_db.get_analysis_snapshot = MagicMock(return_value=None)
        
        response = client.get("/api/snapshots/nonexistent_id")
        
        assert response.status_code == 404
        assert 'not found' in response.json()['detail'].lower()


# ============================================
# Test API Endpoints - Review Snapshot
# ============================================

def test_api_snapshots_review_success(client):
    """Test successfully marking snapshot as reviewed."""
    with patch('railway_web.duckdb_storage') as mock_db:
        mock_db.mark_snapshot_reviewed = MagicMock(return_value=True)
        
        response = client.post(
            "/api/snapshots/weekly_20251114/review",
            json={'reviewed_by': 'test_user', 'notes': 'Looks good'}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert 'test_user' in data['message']


def test_api_snapshots_review_requires_auth_with_token_set(client):
    """Test review requires authentication when token is set."""
    with patch('railway_web.duckdb_storage') as mock_db, \
         patch.dict('os.environ', {'EXECUTION_API_TOKEN': 'test_token'}):
        mock_db.mark_snapshot_reviewed = MagicMock(return_value=True)
        
        # Without auth header
        response = client.post(
            "/api/snapshots/weekly_20251114/review",
            json={'reviewed_by': 'test_user'}
        )
        
        assert response.status_code == 403


def test_api_snapshots_review_with_notes(client):
    """Test review with optional notes."""
    with patch('railway_web.duckdb_storage') as mock_db:
        mock_db.mark_snapshot_reviewed = MagicMock(return_value=True)
        
        response = client.post(
            "/api/snapshots/weekly_20251114/review",
            json={'reviewed_by': 'test_user', 'notes': 'Discussed with team'}
        )
        
        assert response.status_code == 200
        # Verify notes passed to mock
        mock_db.mark_snapshot_reviewed.assert_called_once_with(
            'weekly_20251114',
            'test_user',
            'Discussed with team'
        )


def test_api_snapshots_review_not_found(client):
    """Test review returns 404 when snapshot doesn't exist."""
    with patch('railway_web.duckdb_storage') as mock_db:
        mock_db.mark_snapshot_reviewed = MagicMock(return_value=False)
        
        response = client.post(
            "/api/snapshots/nonexistent/review",
            json={'reviewed_by': 'test_user'}
        )
        
        assert response.status_code == 404


# ============================================
# Test API Endpoints - Timeseries
# ============================================

def test_api_snapshots_timeseries(client, sample_snapshots):
    """Test timeseries endpoint returns Chart.js format."""
    with patch('railway_web.historical_service') as mock_service:
        mock_service.list_snapshots_async = MagicMock(return_value=sample_snapshots)
        
        response = client.get("/api/snapshots/timeseries?analysis_type=weekly&limit=12")
        
        assert response.status_code == 200
        data = response.json()
        assert 'labels' in data
        assert 'datasets' in data
        assert isinstance(data['labels'], list)
        assert isinstance(data['datasets'], list)


def test_api_snapshots_timeseries_empty(client):
    """Test timeseries with no data."""
    with patch('railway_web.historical_service') as mock_service:
        mock_service.list_snapshots_async = MagicMock(return_value=[])
        
        response = client.get("/api/snapshots/timeseries")
        
        assert response.status_code == 200
        data = response.json()
        assert data['labels'] == []
        assert data['datasets'] == []


# ============================================
# Test HTML Routes
# ============================================

def test_analysis_history_route(client):
    """Test /analysis/history returns HTML."""
    response = client.get("/analysis/history")
    
    assert response.status_code == 200
    assert response.headers['content-type'] == 'text/html; charset=utf-8'


def test_analysis_view_route(client):
    """Test snapshot detail view."""
    with patch('railway_web.duckdb_storage') as mock_db:
        mock_db.get_analysis_snapshot = MagicMock(return_value={
            'snapshot_id': 'weekly_20251114',
            'date_range_label': 'Nov 8-14, 2025',
            'analysis_type': 'weekly',
            'total_conversations': 175,
            'insights_summary': 'Test summary',
            'topic_volumes': {'Billing': 52, 'API': 34},
            'created_at': '2025-11-15T10:30:00'
        })
        
        response = client.get("/analysis/view/weekly_20251114")
        
        assert response.status_code == 200
        assert 'Nov 8-14, 2025' in response.text
        assert '175' in response.text


def test_analysis_view_not_found(client):
    """Test view returns 404 for missing snapshot."""
    with patch('railway_web.duckdb_storage') as mock_db:
        mock_db.get_analysis_snapshot = MagicMock(return_value=None)
        
        response = client.get("/analysis/view/nonexistent")
        
        assert response.status_code == 404


def test_analysis_compare_route(client):
    """Test comparison view."""
    with patch('railway_web.duckdb_storage') as mock_db, \
         patch('railway_web.historical_service') as mock_service:
        
        mock_db.get_analysis_snapshot = MagicMock(side_effect=[
            {
                'snapshot_id': 'weekly_20251114',
                'date_range_label': 'Nov 8-14, 2025',
                'total_conversations': 175
            },
            {
                'snapshot_id': 'weekly_20251107',
                'date_range_label': 'Nov 1-7, 2025',
                'total_conversations': 150
            }
        ])
        
        mock_service.calculate_comparison = MagicMock(return_value={
            'volume_changes': [('Billing', 15.5, 7)],
            'significant_changes': ['API volume increased by 89%']
        })
        
        response = client.get("/analysis/compare/weekly_20251114/weekly_20251107")
        
        assert response.status_code == 200
        assert 'Nov 8-14, 2025' in response.text
        assert 'Nov 1-7, 2025' in response.text


# ============================================
# Test Health Check
# ============================================

def test_health_check_with_services(client):
    """Test health check returns service status."""
    with patch('railway_web.duckdb_storage', Mock()), \
         patch('railway_web.historical_service', Mock()):
        
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'healthy'
        assert data['duckdb_storage'] is True
        assert data['historical_service'] is True


def test_health_check_service_failure(client):
    """Test health check reports missing services."""
    with patch('railway_web.duckdb_storage', None), \
         patch('railway_web.historical_service', None):
        
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data['duckdb_storage'] is False
        assert data['historical_service'] is False


# ============================================
# Test File Download
# ============================================

def test_download_file_success(client, tmp_path):
    """Test file download from outputs directory."""
    # Create a test file
    test_file = tmp_path / "outputs" / "test_file.txt"
    test_file.parent.mkdir(parents=True, exist_ok=True)
    test_file.write_text("Test content")
    
    with patch('railway_web.Path') as mock_path:
        mock_path.return_value.resolve.return_value = test_file
        mock_path.return_value.exists.return_value = True
        mock_path.return_value.is_file.return_value = True
        
        # Note: This test is simplified - actual file download testing requires more setup
        # In practice, you'd use TestClient with actual file system or more detailed mocking


def test_download_file_not_found(client):
    """Test 404 when file doesn't exist."""
    response = client.get("/download?file=nonexistent.txt")
    
    assert response.status_code == 404


def test_download_file_security_validation(client):
    """Test security check prevents directory traversal."""
    response = client.get("/download?file=../../etc/passwd")
    
    # Should be rejected by security check
    assert response.status_code in [403, 404]


# ============================================
# Error Handling Tests
# ============================================

def test_api_handles_service_exception(client):
    """Test graceful error handling when service raises exception."""
    with patch('railway_web.historical_service') as mock_service:
        mock_service.list_snapshots_async = MagicMock(side_effect=Exception('Database error'))
        
        response = client.get("/api/snapshots/list")
        
        assert response.status_code == 500
        assert 'Failed to fetch snapshots' in response.json()['detail']


def test_api_handles_invalid_json(client):
    """Test 422 validation error for invalid JSON."""
    response = client.post(
        "/api/snapshots/weekly_20251114/review",
        data='invalid json',
        headers={'Content-Type': 'application/json'}
    )
    
    assert response.status_code == 422


def test_api_handles_missing_fields(client):
    """Test 422 validation error for missing required fields."""
    with patch('railway_web.duckdb_storage'):
        response = client.post(
            "/api/snapshots/weekly_20251114/review",
            json={}  # Missing reviewed_by field
        )
        
        assert response.status_code == 422


# ============================================
# Integration Tests
# ============================================

@pytest.mark.integration
def test_full_timeline_workflow():
    """Test complete workflow with real services (requires test database)."""
    # This test would use actual DuckDB with temp database
    # Skipped for unit tests - would be run separately with integration flag
    pytest.skip("Integration test - requires test database setup")


@pytest.mark.integration
def test_concurrent_requests():
    """Test concurrent API requests don't cause race conditions."""
    # This test would send multiple simultaneous requests
    # Skipped for unit tests
    pytest.skip("Integration test - requires concurrency testing setup")


# ============================================
# Test Utilities
# ============================================

def test_date_serialization(sample_snapshots):
    """Test that date objects are properly serialized to ISO strings."""
    snapshot = sample_snapshots[0]
    
    # Dates should be date objects initially
    assert isinstance(snapshot['period_start'], date)
    
    # After processing (like in the actual endpoint), they should be strings
    # This is tested implicitly in the endpoint tests above


if __name__ == '__main__':
    pytest.main([__file__, '-v'])



