"""
Unit tests for HistoricalDataManager.
"""

import pytest
import json
import tempfile
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, Mock

from src.services.historical_data_manager import HistoricalDataManager


class TestHistoricalDataManager:
    """Test cases for HistoricalDataManager."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def historical_manager(self, temp_dir):
        """Create a HistoricalDataManager instance for testing."""
        return HistoricalDataManager(storage_dir=temp_dir)
    
    @pytest.fixture
    def sample_analysis_results(self):
        """Create sample analysis results for testing."""
        return {
            'results': {
                'Billing': {
                    'volume': 25,
                    'sentiment_breakdown': {
                        'sentiment': 'positive',
                        'confidence': 0.85
                    }
                },
                'Product Question': {
                    'volume': 15,
                    'sentiment_breakdown': {
                        'sentiment': 'neutral',
                        'confidence': 0.70
                    }
                }
            },
            'metadata': {
                'total_conversations': 40,
                'ai_model': 'openai',
                'execution_time_seconds': 15.5
            }
        }
    
    @pytest.mark.asyncio
    async def test_store_weekly_snapshot(self, historical_manager, sample_analysis_results):
        """Test storing weekly snapshot."""
        week_start = datetime(2024, 1, 15)  # Monday
        
        filepath = await historical_manager.store_weekly_snapshot(week_start, sample_analysis_results)
        
        assert Path(filepath).exists()
        
        # Verify file contents
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        assert data['snapshot_type'] == 'weekly'
        assert data['week_start'] == week_start.isoformat()
        assert data['analysis_results'] == sample_analysis_results
        assert data['metadata']['total_conversations'] == 40
    
    @pytest.mark.asyncio
    async def test_store_monthly_snapshot(self, historical_manager, sample_analysis_results):
        """Test storing monthly snapshot."""
        month_start = datetime(2024, 1, 1)
        
        filepath = await historical_manager.store_monthly_snapshot(month_start, sample_analysis_results)
        
        assert Path(filepath).exists()
        
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        assert data['snapshot_type'] == 'monthly'
        assert data['month_start'] == month_start.isoformat()
    
    @pytest.mark.asyncio
    async def test_store_quarterly_snapshot(self, historical_manager, sample_analysis_results):
        """Test storing quarterly snapshot."""
        quarter_start = datetime(2024, 1, 1)
        
        filepath = await historical_manager.store_quarterly_snapshot(quarter_start, sample_analysis_results)
        
        assert Path(filepath).exists()
        
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        assert data['snapshot_type'] == 'quarterly'
        assert data['quarter_start'] == quarter_start.isoformat()
    
    def test_get_historical_trends(self, historical_manager, sample_analysis_results):
        """Test retrieving historical trends."""
        # Create some test snapshots with recent dates
        from datetime import timedelta
        now = datetime.now()
        week1 = now - timedelta(weeks=1)
        week2 = now - timedelta(weeks=2)
        week3 = now - timedelta(weeks=3)
        
        # Store snapshots (we'll mock the async calls)
        with patch.object(historical_manager, 'store_weekly_snapshot') as mock_store:
            mock_store.return_value = "test_path"
            
            # Create test files manually
            for week_start in [week1, week2, week3]:
                filename = f"weekly_snapshot_{week_start.strftime('%Y%m%d')}.json"
                filepath = historical_manager.storage_dir / filename
                
                snapshot_data = {
                    'snapshot_type': 'weekly',
                    'week_start': week_start.isoformat(),
                    'analysis_results': sample_analysis_results
                }
                
                with open(filepath, 'w') as f:
                    json.dump(snapshot_data, f)
        
        # Test retrieving trends
        trends = historical_manager.get_historical_trends(weeks_back=4, snapshot_type='weekly')
        
        assert len(trends) == 3
        assert all(trend['snapshot_type'] == 'weekly' for trend in trends)
    
    def test_get_trend_analysis(self, historical_manager, sample_analysis_results):
        """Test getting trend analysis."""
        # Create test snapshots with recent dates
        from datetime import timedelta
        now = datetime.now()
        week1 = now - timedelta(weeks=1)
        week2 = now - timedelta(weeks=2)
        
        # Create test files
        for i, week_start in enumerate([week1, week2]):
            filename = f"weekly_snapshot_{week_start.strftime('%Y%m%d')}.json"
            filepath = historical_manager.storage_dir / filename
            
            # Modify volume for trend analysis
            modified_results = sample_analysis_results.copy()
            modified_results['results']['Billing']['volume'] = 25 + (i * 5)
            
            snapshot_data = {
                'snapshot_type': 'weekly',
                'week_start': week_start.isoformat(),
                'analysis_results': modified_results
            }
            
            with open(filepath, 'w') as f:
                json.dump(snapshot_data, f)
        
        # Test trend analysis
        trend_analysis = historical_manager.get_trend_analysis(weeks_back=4, snapshot_type='weekly')
        
        assert 'trends' in trend_analysis
        assert 'insights' in trend_analysis
        assert 'periods_analyzed' in trend_analysis
        assert trend_analysis['periods_analyzed'] == 2
    
    def test_parse_snapshot_date_from_data(self, historical_manager):
        """Test parsing snapshot date from data."""
        snapshot_data = {
            'week_start': '2024-01-15T00:00:00'
        }
        
        date = historical_manager._parse_snapshot_date(snapshot_data, 'test.json')
        assert date == datetime(2024, 1, 15)
    
    def test_parse_snapshot_date_from_filename(self, historical_manager):
        """Test parsing snapshot date from filename."""
        snapshot_data = {}
        filename = 'weekly_snapshot_20240115.json'
        
        date = historical_manager._parse_snapshot_date(snapshot_data, filename)
        assert date == datetime(2024, 1, 15)
    
    def test_cleanup_old_snapshots(self, historical_manager, sample_analysis_results):
        """Test cleaning up old snapshots."""
        # Create old and recent snapshots
        old_date = datetime.now() - timedelta(weeks=60)  # Very old
        recent_date = datetime.now() - timedelta(weeks=2)  # Recent
        
        for date, prefix in [(old_date, 'old'), (recent_date, 'recent')]:
            filename = f"weekly_snapshot_{date.strftime('%Y%m%d')}.json"
            filepath = historical_manager.storage_dir / filename
            
            snapshot_data = {
                'snapshot_type': 'weekly',
                'week_start': date.isoformat(),
                'analysis_results': sample_analysis_results
            }
            
            with open(filepath, 'w') as f:
                json.dump(snapshot_data, f)
        
        # Clean up old snapshots
        deleted_count = historical_manager.cleanup_old_snapshots(keep_weeks=52)
        
        assert deleted_count == 1  # Only the old one should be deleted
        
        # Check that recent snapshot still exists
        recent_filename = f"weekly_snapshot_{recent_date.strftime('%Y%m%d')}.json"
        recent_filepath = historical_manager.storage_dir / recent_filename
        assert recent_filepath.exists()
    
    def test_generate_trend_insights(self, historical_manager):
        """Test generating trend insights."""
        category_trends = {
            'Billing': {
                'volumes': [20, 25, 30],  # Increasing trend (30 > 20 * 1.2 = 24)
                'sentiments': [],
                'dates': []
            },
            'Support': {
                'volumes': [50, 45, 35],  # Decreasing trend (35 < 50 * 0.8 = 40)
                'sentiments': [],
                'dates': []
            }
        }
        
        insights = historical_manager._generate_trend_insights(category_trends)
        
        assert len(insights) > 0
        assert any('Billing' in insight and 'increased' in insight for insight in insights)
        assert any('Support' in insight and 'decreased' in insight for insight in insights)
    
    def test_empty_storage_directory(self, historical_manager):
        """Test handling of empty storage directory."""
        trends = historical_manager.get_historical_trends()
        assert trends == []
        
        trend_analysis = historical_manager.get_trend_analysis()
        assert trend_analysis['periods_analyzed'] == 0
        assert 'No historical data available' in trend_analysis['insights'][0]
    
    def test_corrupted_snapshot_file(self, historical_manager):
        """Test handling of corrupted snapshot files."""
        # Create a corrupted JSON file
        corrupted_file = historical_manager.storage_dir / 'weekly_snapshot_20240101.json'
        with open(corrupted_file, 'w') as f:
            f.write('invalid json content')
        
        # Should not raise exception
        trends = historical_manager.get_historical_trends()
        assert trends == []
    
    def test_missing_date_fields(self, historical_manager):
        """Test handling of snapshots with missing date fields."""
        # Create snapshot without date fields
        filename = 'weekly_snapshot_20240101.json'
        filepath = historical_manager.storage_dir / filename
        
        snapshot_data = {
            'snapshot_type': 'weekly',
            'analysis_results': {}
        }
        
        with open(filepath, 'w') as f:
            json.dump(snapshot_data, f)
        
        # Should fall back to filename parsing
        date = historical_manager._parse_snapshot_date(snapshot_data, filename)
        assert date == datetime(2024, 1, 1)
