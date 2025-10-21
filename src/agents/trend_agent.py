"""
TrendAgent: Week-over-week trend analysis.

Purpose:
- Compare current week with previous weeks
- Identify volume changes
- Track sentiment shifts
- Flag trending topics (up/down)
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import json
from pathlib import Path

from src.agents.base_agent import BaseAgent, AgentResult, AgentContext, ConfidenceLevel

logger = logging.getLogger(__name__)


class TrendAgent(BaseAgent):
    """Agent specialized in week-over-week trend analysis"""
    
    def __init__(self, historical_data_dir: Optional[Path] = None):
        super().__init__(
            name="TrendAgent",
            model="gpt-4o-mini",
            temperature=0.1
        )
        self.historical_dir = historical_data_dir or Path("outputs/weekly_history")
        self.historical_dir.mkdir(parents=True, exist_ok=True)
    
    def get_agent_specific_instructions(self) -> str:
        """Trend agent instructions"""
        return """
TREND AGENT SPECIFIC RULES:

1. Compare current week with previous weeks:
   - Volume changes (↑ 12% vs last week)
   - Sentiment shifts (improving/worsening/stable)
   - New topics emerging
   - Declining topics

2. Use clear trend indicators:
   - ↑ for increasing
   - ↓ for decreasing
   - → for stable
   - 🚨 for significant changes (>20%)

3. Be honest about data availability:
   - First week: "No historical data - establishing baseline"
   - Second week: "Limited trend data - one week comparison only"
   - 4+ weeks: "Robust trend analysis available"

4. Focus on actionable trends:
   - NOT: "Volume increased"
   - YES: "Agent/Buddy complaints ↑ 23% (500 → 615 tickets) 🚨 Trending up"
"""
    
    def get_task_description(self, context: AgentContext) -> str:
        """Describe trend analysis task"""
        return """
Compare current analysis with historical data to identify trends.

Output trends for:
- Topic volumes (which topics increasing/decreasing)
- Sentiment changes (which topics getting better/worse)
- New topics (what's emerging)
- Overall patterns
"""
    
    def format_context_data(self, context: AgentContext) -> str:
        """Format current and historical data"""
        current = context.metadata.get('current_week_results', {})
        return f"Current week topics: {len(current)}"
    
    def validate_input(self, context: AgentContext) -> bool:
        """Validate input"""
        if 'current_week_results' not in context.metadata:
            raise ValueError("current_week_results not provided")
        return True
    
    def validate_output(self, result: Dict[str, Any]) -> bool:
        """Validate trend results"""
        return 'trends' in result
    
    async def execute(self, context: AgentContext) -> AgentResult:
        """Execute trend analysis"""
        start_time = datetime.now()
        
        try:
            self.validate_input(context)
            
            current_results = context.metadata.get('current_week_results', {})
            week_id = context.metadata.get('week_id', datetime.now().strftime('%Y-W%W'))
            
            self.logger.info(f"TrendAgent: Analyzing trends for week {week_id}")
            
            # Load historical data
            historical_data = self._load_historical_data()
            
            if not historical_data:
                # First week - no trends available
                result_data = {
                    'trends': {},
                    'week_id': week_id,
                    'note': 'First analysis - establishing baseline. Trends will be available next week.',
                    'historical_weeks_available': 0
                }
                
                # Save current week as baseline
                self._save_week_data(week_id, current_results)
            else:
                # Calculate trends
                trends = self._calculate_trends(current_results, historical_data)
                
                result_data = {
                    'trends': trends,
                    'week_id': week_id,
                    'historical_weeks_available': len(historical_data),
                    'comparison_week': historical_data[-1]['week_id'] if historical_data else None
                }
                
                # Save current week
                self._save_week_data(week_id, current_results)
            
            self.validate_output(result_data)
            
            confidence = min(1.0, len(historical_data) / 4) if historical_data else 0.5
            confidence_level = (ConfidenceLevel.HIGH if len(historical_data) >= 4
                              else ConfidenceLevel.MEDIUM if len(historical_data) >= 2
                              else ConfidenceLevel.LOW)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            self.logger.info(f"TrendAgent: Completed in {execution_time:.2f}s")
            self.logger.info(f"   Historical weeks: {len(historical_data)}")
            
            return AgentResult(
                agent_name=self.name,
                success=True,
                data=result_data,
                confidence=confidence,
                confidence_level=confidence_level,
                limitations=[f"Only {len(historical_data)} weeks of historical data"] if len(historical_data) < 4 else [],
                sources=["Historical weekly data", "Current week results"],
                execution_time=execution_time,
                token_count=0
            )
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            self.logger.error(f"TrendAgent error: {e}")
            
            return AgentResult(
                agent_name=self.name,
                success=False,
                data={},
                confidence=0.0,
                confidence_level=ConfidenceLevel.LOW,
                error_message=str(e),
                execution_time=execution_time
            )
    
    def _load_historical_data(self) -> List[Dict]:
        """Load previous weeks' data"""
        historical = []
        
        for file in sorted(self.historical_dir.glob("week_*.json")):
            try:
                with open(file, 'r') as f:
                    week_data = json.load(f)
                    historical.append(week_data)
            except Exception as e:
                self.logger.warning(f"Could not load {file}: {e}")
        
        return historical
    
    def _save_week_data(self, week_id: str, results: Dict):
        """Save current week data for future comparisons"""
        filename = self.historical_dir / f"week_{week_id.replace('-', '_')}.json"
        
        with open(filename, 'w') as f:
            json.dump({
                'week_id': week_id,
                'timestamp': datetime.now().isoformat(),
                'results': results
            }, f, indent=2, default=str)
    
    def _calculate_trends(self, current: Dict, historical: List[Dict]) -> Dict:
        """Calculate week-over-week trends"""
        if not historical:
            return {}
        
        # Compare with most recent week
        previous = historical[-1]['results']
        trends = {}
        
        # Topic volume trends
        current_topics = current.get('topic_distribution', {})
        previous_topics = previous.get('topic_distribution', {})
        
        for topic, current_stats in current_topics.items():
            current_vol = current_stats.get('volume', 0)
            previous_vol = previous_topics.get(topic, {}).get('volume', 0)
            
            if previous_vol > 0:
                pct_change = ((current_vol - previous_vol) / previous_vol) * 100
                direction = '↑' if pct_change > 5 else ('↓' if pct_change < -5 else '→')
                
                # Flag significant changes
                alert = '🚨' if abs(pct_change) > 20 else ''
                
                trends[topic] = {
                    'volume_change': round(pct_change, 1),
                    'direction': direction,
                    'alert': alert,
                    'current_volume': current_vol,
                    'previous_volume': previous_vol,
                    'interpretation': self._interpret_trend(pct_change)
                }
            else:
                trends[topic] = {
                    'note': 'New topic this week',
                    'current_volume': current_vol
                }
        
        return trends
    
    def _interpret_trend(self, pct_change: float) -> str:
        """Interpret what the trend means"""
        if abs(pct_change) < 5:
            return "Stable"
        elif pct_change > 20:
            return "Significantly increasing"
        elif pct_change > 5:
            return "Increasing"
        elif pct_change < -20:
            return "Significantly decreasing"
        elif pct_change < -5:
            return "Decreasing"
        return "Stable"

