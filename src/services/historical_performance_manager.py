"""
Historical Performance Manager

Stores and compares agent performance metrics across time periods
to track improvements and identify trends.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from pathlib import Path

from src.models.agent_performance_models import IndividualAgentMetrics
from src.services.duckdb_storage import DuckDBStorage

logger = logging.getLogger(__name__)


class HistoricalPerformanceManager:
    """Manage historical agent performance data for trend analysis"""
    
    def __init__(self, storage: Optional[DuckDBStorage] = None):
        """
        Initialize historical performance manager.
        
        Args:
            storage: Optional DuckDBStorage instance (creates new if not provided)
        """
        self.storage = storage or DuckDBStorage()
        self.logger = logging.getLogger(__name__)
        self._ensure_schema()
    
    def _ensure_schema(self):
        """Ensure the historical performance schema exists"""
        try:
            self.storage.conn.execute("""
                CREATE TABLE IF NOT EXISTS agent_weekly_snapshots (
                    vendor TEXT,
                    agent_id TEXT,
                    agent_name TEXT,
                    agent_email TEXT,
                    week_start DATE,
                    week_end DATE,
                    
                    -- Performance metrics
                    total_conversations INTEGER,
                    fcr_rate REAL,
                    escalation_rate REAL,
                    median_resolution_hours REAL,
                    median_response_hours REAL,
                    
                    -- CSAT metrics
                    csat_score REAL,
                    csat_survey_count INTEGER,
                    negative_csat_count INTEGER,
                    
                    -- Metadata
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    
                    PRIMARY KEY (vendor, agent_id, week_start)
                )
            """)
            self.logger.info("Historical performance schema ready")
        except Exception as e:
            self.logger.error(f"Failed to create historical schema: {e}")
    
    async def store_weekly_snapshot(
        self, 
        vendor: str,
        week_start: datetime,
        week_end: datetime,
        agent_metrics: List[IndividualAgentMetrics]
    ) -> bool:
        """
        Store a weekly snapshot of agent performance.
        
        Args:
            vendor: Vendor name (horatio, boldr)
            week_start: Start of analysis period
            week_end: End of analysis period
            agent_metrics: List of agent performance metrics
            
        Returns:
            True if successful
        """
        try:
            for agent in agent_metrics:
                # Upsert (replace if exists)
                self.storage.conn.execute("""
                    INSERT OR REPLACE INTO agent_weekly_snapshots (
                        vendor, agent_id, agent_name, agent_email,
                        week_start, week_end,
                        total_conversations, fcr_rate, escalation_rate,
                        median_resolution_hours, median_response_hours,
                        csat_score, csat_survey_count, negative_csat_count
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, [
                    vendor,
                    agent.agent_id,
                    agent.agent_name,
                    agent.agent_email,
                    week_start.date(),
                    week_end.date(),
                    agent.total_conversations,
                    agent.fcr_rate,
                    agent.escalation_rate,
                    agent.median_resolution_hours,
                    agent.median_response_hours,
                    agent.csat_score,
                    agent.csat_survey_count,
                    agent.negative_csat_count
                ])
            
            self.logger.info(
                f"Stored weekly snapshot for {len(agent_metrics)} {vendor} agents "
                f"(week {week_start.date()} to {week_end.date()})"
            )
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to store weekly snapshot: {e}")
            return False
    
    async def get_week_over_week_comparison(
        self, 
        vendor: str,
        current_week_start: datetime
    ) -> Dict[str, Dict[str, float]]:
        """
        Get week-over-week changes for all agents.
        
        Args:
            vendor: Vendor name
            current_week_start: Start date of current week
            
        Returns:
            {
                'agent_id': {
                    'fcr_change': +0.05,  # 5% improvement
                    'csat_change': -0.2,  # 0.2 point decline
                    'escalation_change': +0.03,  # 3% increase (bad)
                    'conversations_change': +5  # 5 more conversations
                }
            }
        """
        try:
            # Calculate previous week date
            previous_week_start = current_week_start - timedelta(weeks=1)
            
            # Query current week data
            current_data = self._query_weekly_data(vendor, current_week_start)
            
            # Query previous week data
            previous_data = self._query_weekly_data(vendor, previous_week_start)
            
            # Calculate deltas
            comparisons = {}
            for agent_id in current_data:
                if agent_id in previous_data:
                    curr = current_data[agent_id]
                    prev = previous_data[agent_id]
                    
                    comparisons[agent_id] = {
                        'agent_name': curr['agent_name'],
                        'fcr_change': curr['fcr_rate'] - prev['fcr_rate'],
                        'csat_change': curr['csat_score'] - prev['csat_score'],
                        'escalation_change': curr['escalation_rate'] - prev['escalation_rate'],
                        'conversations_change': curr['total_conversations'] - prev['total_conversations'],
                        'response_time_change': curr['median_response_hours'] - prev['median_response_hours'],
                        # Store current values for context
                        'current_fcr': curr['fcr_rate'],
                        'current_csat': curr['csat_score'],
                        'current_escalation': curr['escalation_rate'],
                        'previous_fcr': prev['fcr_rate'],
                        'previous_csat': prev['csat_score'],
                        'previous_escalation': prev['escalation_rate']
                    }
                else:
                    # New agent (no previous week data)
                    curr = current_data[agent_id]
                    comparisons[agent_id] = {
                        'agent_name': curr['agent_name'],
                        'is_new': True,
                        'current_fcr': curr['fcr_rate'],
                        'current_csat': curr['csat_score'],
                        'current_escalation': curr['escalation_rate']
                    }
            
            self.logger.info(
                f"Calculated WoW comparison for {len(comparisons)} agents "
                f"({len([c for c in comparisons.values() if not c.get('is_new')])} with history)"
            )
            
            return comparisons
            
        except Exception as e:
            self.logger.error(f"Failed to calculate week-over-week comparison: {e}")
            return {}
    
    def _query_weekly_data(self, vendor: str, week_start: datetime) -> Dict[str, Dict]:
        """Query weekly snapshot data for a specific week"""
        try:
            result = self.storage.conn.execute("""
                SELECT 
                    agent_id,
                    agent_name,
                    total_conversations,
                    fcr_rate,
                    escalation_rate,
                    median_resolution_hours,
                    median_response_hours,
                    csat_score,
                    csat_survey_count,
                    negative_csat_count
                FROM agent_weekly_snapshots
                WHERE vendor = ?
                  AND week_start = ?
            """, [vendor, week_start.date()]).fetchall()
            
            # Convert to dict
            data = {}
            for row in result:
                data[row[0]] = {
                    'agent_name': row[1],
                    'total_conversations': row[2],
                    'fcr_rate': row[3],
                    'escalation_rate': row[4],
                    'median_resolution_hours': row[5],
                    'median_response_hours': row[6],
                    'csat_score': row[7],
                    'csat_survey_count': row[8],
                    'negative_csat_count': row[9]
                }
            
            return data
            
        except Exception as e:
            self.logger.error(f"Failed to query weekly data: {e}")
            return {}
    
    async def get_multi_week_trends(
        self,
        vendor: str,
        agent_id: str,
        weeks_back: int = 6
    ) -> List[Dict[str, Any]]:
        """
        Get multi-week trend data for a specific agent (like Horatio's 6-week chart).
        
        Args:
            vendor: Vendor name
            agent_id: Agent ID
            weeks_back: Number of weeks to retrieve
            
        Returns:
            List of weekly snapshots (newest first)
        """
        try:
            result = self.storage.conn.execute("""
                SELECT 
                    week_start,
                    week_end,
                    total_conversations,
                    fcr_rate,
                    escalation_rate,
                    csat_score,
                    csat_survey_count,
                    negative_csat_count
                FROM agent_weekly_snapshots
                WHERE vendor = ?
                  AND agent_id = ?
                ORDER BY week_start DESC
                LIMIT ?
            """, [vendor, agent_id, weeks_back]).fetchall()
            
            trends = []
            for row in result:
                trends.append({
                    'week_start': row[0],
                    'week_end': row[1],
                    'total_conversations': row[2],
                    'fcr_rate': row[3],
                    'escalation_rate': row[4],
                    'csat_score': row[5],
                    'csat_survey_count': row[6],
                    'negative_csat_count': row[7]
                })
            
            return trends
            
        except Exception as e:
            self.logger.error(f"Failed to get multi-week trends: {e}")
            return []
    
    def format_trend_indicator(self, change: float, metric_type: str = 'positive') -> str:
        """
        Format a trend indicator with arrow and color.
        
        Args:
            change: Numeric change value
            metric_type: 'positive' (higher is better) or 'negative' (lower is better)
            
        Returns:
            Formatted string like "↑ +5%" or "↓ -0.3"
        """
        if change == 0:
            return "→ 0"
        
        # Determine if this is good or bad
        is_improvement = (change > 0 and metric_type == 'positive') or \
                        (change < 0 and metric_type == 'negative')
        
        # Format value
        if abs(change) >= 0.01:  # Show percentages
            value = f"{change:+.1%}" if abs(change) < 1 else f"{change:+.0%}"
        else:
            value = f"{change:+.2f}"
        
        # Choose arrow
        if change > 0:
            arrow = "↑" if is_improvement else "⚠️↑"
        else:
            arrow = "↓" if is_improvement else "⚠️↓"
        
        return f"{arrow} {value}"

