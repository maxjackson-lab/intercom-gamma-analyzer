"""
Historical data manager for storing and retrieving VoC analysis snapshots.
"""

import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path

from src.config.settings import settings

logger = logging.getLogger(__name__)


class HistoricalDataManager:
    """Manages historical data snapshots for trend analysis."""

    def __init__(self, storage_dir: str = None, retention_weeks: int = None):
        """
        Initialize Historical Data Manager.

        Args:
            storage_dir: Directory for storing snapshots
            retention_weeks: Number of weeks to retain snapshots (default from settings or 52)
        """
        self.storage_dir = Path(storage_dir or settings.output_directory) / "historical_data"
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(__name__)

        # Get retention period from parameter, settings, or default to 52 weeks
        if retention_weeks is not None:
            self.retention_weeks = retention_weeks
        elif hasattr(settings, 'historical_data_retention_weeks'):
            self.retention_weeks = settings.historical_data_retention_weeks
        else:
            self.retention_weeks = 52

        self.logger.info(
            f"HistoricalDataManager initialized with storage: {self.storage_dir}, "
            f"retention: {self.retention_weeks} weeks"
        )
    
    async def store_weekly_snapshot(
        self, 
        week_start: datetime, 
        analysis_results: Dict[str, Any]
    ) -> str:
        """
        Store weekly VoC analysis snapshot.
        
        Args:
            week_start: Start date of the week
            analysis_results: VoC analysis results
        
        Returns:
            Path to stored snapshot
        """
        self.logger.info(f"Storing weekly snapshot for week starting {week_start.date()}")
        
        snapshot_data = {
            'snapshot_type': 'weekly',
            'week_start': week_start.isoformat(),
            'created_at': datetime.now().isoformat(),
            'analysis_results': analysis_results,
            'metadata': {
                'total_conversations': analysis_results.get('metadata', {}).get('total_conversations', 0),
                'ai_model_used': analysis_results.get('metadata', {}).get('ai_model', 'unknown')
            }
        }
        
        filename = f"weekly_snapshot_{week_start.strftime('%Y%m%d')}.json"
        filepath = self.storage_dir / filename
        
        with open(filepath, 'w') as f:
            json.dump(snapshot_data, f, indent=2)
        
        self.logger.info(f"Weekly snapshot stored: {filepath}")
        return str(filepath)
    
    async def store_monthly_snapshot(
        self, 
        month_start: datetime, 
        analysis_results: Dict[str, Any]
    ) -> str:
        """
        Store monthly VoC analysis snapshot.
        
        Args:
            month_start: Start date of the month
            analysis_results: VoC analysis results
        
        Returns:
            Path to stored snapshot
        """
        self.logger.info(f"Storing monthly snapshot for month starting {month_start.date()}")
        
        snapshot_data = {
            'snapshot_type': 'monthly',
            'month_start': month_start.isoformat(),
            'created_at': datetime.now().isoformat(),
            'analysis_results': analysis_results,
            'metadata': {
                'total_conversations': analysis_results.get('metadata', {}).get('total_conversations', 0),
                'ai_model_used': analysis_results.get('metadata', {}).get('ai_model', 'unknown')
            }
        }
        
        filename = f"monthly_snapshot_{month_start.strftime('%Y%m%d')}.json"
        filepath = self.storage_dir / filename
        
        with open(filepath, 'w') as f:
            json.dump(snapshot_data, f, indent=2)
        
        self.logger.info(f"Monthly snapshot stored: {filepath}")
        return str(filepath)
    
    async def store_quarterly_snapshot(
        self, 
        quarter_start: datetime, 
        analysis_results: Dict[str, Any]
    ) -> str:
        """
        Store quarterly VoC analysis snapshot.
        
        Args:
            quarter_start: Start date of the quarter
            analysis_results: VoC analysis results
        
        Returns:
            Path to stored snapshot
        """
        self.logger.info(f"Storing quarterly snapshot for quarter starting {quarter_start.date()}")
        
        snapshot_data = {
            'snapshot_type': 'quarterly',
            'quarter_start': quarter_start.isoformat(),
            'created_at': datetime.now().isoformat(),
            'analysis_results': analysis_results,
            'metadata': {
                'total_conversations': analysis_results.get('metadata', {}).get('total_conversations', 0),
                'ai_model_used': analysis_results.get('metadata', {}).get('ai_model', 'unknown')
            }
        }
        
        filename = f"quarterly_snapshot_{quarter_start.strftime('%Y%m%d')}.json"
        filepath = self.storage_dir / filename
        
        with open(filepath, 'w') as f:
            json.dump(snapshot_data, f, indent=2)
        
        self.logger.info(f"Quarterly snapshot stored: {filepath}")
        return str(filepath)
    
    def get_historical_trends(
        self, 
        weeks_back: int = 12,
        snapshot_type: str = 'weekly'
    ) -> List[Dict[str, Any]]:
        """
        Get historical trends for the specified period.
        
        Args:
            weeks_back: Number of weeks to look back
            snapshot_type: Type of snapshots to retrieve ('weekly', 'monthly', 'quarterly')
        
        Returns:
            List of historical snapshots
        """
        self.logger.info(f"Retrieving {snapshot_type} trends for {weeks_back} periods back")
        
        snapshots = []
        cutoff_date = datetime.now() - timedelta(weeks=weeks_back)
        
        # Find all snapshot files
        pattern = f"{snapshot_type}_snapshot_*.json"
        snapshot_files = list(self.storage_dir.glob(pattern))
        
        for filepath in sorted(snapshot_files):
            try:
                with open(filepath, 'r') as f:
                    snapshot_data = json.load(f)
                
                # Parse the date from filename or data
                snapshot_date = self._parse_snapshot_date(snapshot_data, filepath.name)
                
                if snapshot_date >= cutoff_date:
                    snapshots.append(snapshot_data)
                    
            except Exception as e:
                self.logger.warning(f"Failed to load snapshot {filepath}: {e}")
        
        self.logger.info(f"Retrieved {len(snapshots)} {snapshot_type} snapshots")
        return snapshots
    
    def _parse_snapshot_date(self, snapshot_data: Dict, filename: str) -> datetime:
        """Parse date from snapshot data or filename."""
        # Try to get date from snapshot data first
        for date_field in ['week_start', 'month_start', 'quarter_start']:
            if date_field in snapshot_data:
                return datetime.fromisoformat(snapshot_data[date_field])
        
        # Fallback to parsing filename
        try:
            date_str = filename.split('_')[-1].replace('.json', '')
            return datetime.strptime(date_str, '%Y%m%d')
        except:
            return datetime.now()
    
    def get_trend_analysis(
        self, 
        weeks_back: int = 12,
        snapshot_type: str = 'weekly'
    ) -> Dict[str, Any]:
        """
        Get trend analysis from historical data.
        
        Args:
            weeks_back: Number of weeks to analyze
            snapshot_type: Type of snapshots to analyze
        
        Returns:
            Trend analysis results
        """
        self.logger.info(f"Generating trend analysis for {weeks_back} {snapshot_type} periods")
        
        snapshots = self.get_historical_trends(weeks_back, snapshot_type)
        
        if not snapshots:
            return {
                'trends': {},
                'insights': ['No historical data available for trend analysis'],
                'periods_analyzed': 0
            }
        
        # Analyze trends by category
        category_trends = {}
        
        for snapshot in snapshots:
            results = snapshot.get('analysis_results', {}).get('results', {})
            
            for category, data in results.items():
                if category not in category_trends:
                    category_trends[category] = {
                        'volumes': [],
                        'sentiments': [],
                        'dates': []
                    }
                
                category_trends[category]['volumes'].append(data.get('volume', 0))
                category_trends[category]['sentiments'].append(
                    data.get('sentiment_breakdown', {})
                )
                category_trends[category]['dates'].append(
                    self._parse_snapshot_date(snapshot, '')
                )
        
        # Generate insights
        insights = self._generate_trend_insights(category_trends)
        
        return {
            'trends': category_trends,
            'insights': insights,
            'periods_analyzed': len(snapshots),
            'date_range': {
                'start': min(s['dates'][0] for s in category_trends.values()) if category_trends else None,
                'end': max(s['dates'][-1] for s in category_trends.values()) if category_trends else None
            }
        }
    
    def _generate_trend_insights(self, category_trends: Dict) -> List[str]:
        """Generate insights from trend data."""
        insights = []
        
        for category, trend_data in category_trends.items():
            volumes = trend_data['volumes']
            if len(volumes) >= 2:
                # Volume trend
                if volumes[-1] > volumes[0] * 1.2:
                    insights.append(f"{category} volume increased significantly over the period")
                elif volumes[-1] < volumes[0] * 0.8:
                    insights.append(f"{category} volume decreased significantly over the period")
                
                # Recent trend
                if len(volumes) >= 3:
                    recent_avg = sum(volumes[-3:]) / 3
                    earlier_volumes = volumes[:-3]
                    if earlier_volumes:  # Avoid division by zero
                        earlier_avg = sum(earlier_volumes) / len(earlier_volumes)
                        
                        if recent_avg > earlier_avg * 1.1:
                            insights.append(f"{category} showing recent upward trend")
                        elif recent_avg < earlier_avg * 0.9:
                            insights.append(f"{category} showing recent downward trend")
        
        return insights
    
    def cleanup_old_snapshots(self, keep_weeks: int = None) -> int:
        """
        Clean up old snapshots to save space.

        Args:
            keep_weeks: Number of weeks of data to keep (default: self.retention_weeks)

        Returns:
            Number of files deleted
        """
        keep_weeks = keep_weeks or self.retention_weeks
        self.logger.info(f"Cleaning up snapshots older than {keep_weeks} weeks")

        cutoff_date = datetime.now() - timedelta(weeks=keep_weeks)
        deleted_count = 0
        
        for filepath in self.storage_dir.glob("*.json"):
            try:
                with open(filepath, 'r') as f:
                    snapshot_data = json.load(f)
                
                snapshot_date = self._parse_snapshot_date(snapshot_data, filepath.name)
                
                if snapshot_date < cutoff_date:
                    filepath.unlink()
                    deleted_count += 1
                    self.logger.debug(f"Deleted old snapshot: {filepath}")
                    
            except Exception as e:
                self.logger.warning(f"Failed to process snapshot {filepath}: {e}")
        
        self.logger.info(f"Cleaned up {deleted_count} old snapshots")
        return deleted_count
