"""
QualityInsightsAgent - Resolution quality metrics + statistical anomaly detection

This agent analyzes resolution effectiveness (FCR, reopens, multi-touch) AND flags 
statistical outliers (volume spikes, exceptional conversations, temporal clustering) 
in a single comprehensive quality assessment. Uses LLM for rich contextual insights.
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from collections import defaultdict
import numpy as np
from scipy import stats as scipy_stats

from src.agents.base_agent import BaseAgent, AgentResult, ConfidenceLevel, AgentContext
from src.utils.conversation_utils import extract_customer_messages
from src.utils.time_utils import format_duration
from src.utils.ai_client_helper import get_recommended_semaphore
from src.config.settings import settings


logger = logging.getLogger(__name__)


class QualityInsightsAgent(BaseAgent):
    """Agent that analyzes resolution quality and detects statistical anomalies"""

    def __init__(self, ai_client=None):
        super().__init__(
            name="QualityInsightsAgent",
            model="gpt-4o",
            temperature=0.3
        )
        # Get AI client if not provided
        if ai_client is None:
            from src.utils.ai_client_helper import get_ai_client
            self.ai_client = get_ai_client()
        else:
            self.ai_client = ai_client
        
        # Determine which models to use based on AI client type (STRATEGIC TRENDS → use Sonnet!)
        from src.services.claude_client import ClaudeClient
        if isinstance(self.ai_client, ClaudeClient):
            # Claude: Use Sonnet 4.5 for strategic quality insights
            self.quick_model = "claude-haiku-4-5-20251001"
            self.intensive_model = "claude-sonnet-4-5-20250929"
            self.client_type = "claude"
        else:
            # OpenAI: Use GPT-4o for quality insights
            self.quick_model = "gpt-4o-mini"
            self.intensive_model = "gpt-4o"
            self.client_type = "openai"
        
        # RATE LIMITING: Provider-specific concurrency limits
        # OpenAI: Default 10 concurrent (configurable via OPENAI_CONCURRENCY)
        # Anthropic: Default 2 concurrent (configurable via ANTHROPIC_CONCURRENCY, Tier 1: 50 RPM)
        # Source: https://docs.anthropic.com/en/api/rate-limits
        self.llm_semaphore = get_recommended_semaphore(self.ai_client)  # Provider-specific semaphore
        self.llm_timeout = settings.quality_insights_timeout  # Configurable timeout from settings

    def get_agent_specific_instructions(self) -> str:
        """Return instructions for quality analysis"""
        return """
You are analyzing resolution quality and detecting anomalies in customer support data. Your role is to:

1. **Measure effectiveness without blame** - Report metrics objectively
2. **Flag outliers for study** - Highlight exceptional conversations (both positive and negative)
3. **Use observational tone** - "This pattern suggests..." not "You must fix..."
4. **Identify learning opportunities** - Exceptional cases are chances to learn
5. **Provide statistical context** - Explain significance of anomalies

Focus on patterns that help teams improve their support quality and identify edge cases.
"""

    def get_task_description(self, context: AgentContext) -> str:
        """Describe the quality analysis task"""
        total_convs = len(context.conversations) if context.conversations else 0
        topics_detected = len(context.previous_results.get('TopicDetectionAgent', {}).get('data', {}).get('topic_distribution', {}))
        return f"Analyze resolution quality metrics and detect statistical anomalies ({total_convs} conversations, {topics_detected} topics)"

    def format_context_data(self, context: AgentContext) -> Dict[str, Any]:
        """Format summary of available data"""
        conversations = context.conversations or []
        csat_coverage = sum(1 for c in conversations if c.get('conversation_rating')) / len(conversations) if conversations else 0
        stats_coverage = sum(1 for c in conversations if c.get('statistics', {}).get('count_reopens') is not None) / len(conversations) if conversations else 0
        
        return {
            'total_conversations': len(conversations),
            'csat_coverage': round(csat_coverage, 2),
            'statistics_coverage': round(stats_coverage, 2)
        }

    def validate_input(self, context: AgentContext) -> bool:
        """Ensure required data is available"""
        if not context.conversations:
            raise ValueError("No conversations provided for quality analysis")
        
        if 'TopicDetectionAgent' not in context.previous_results:
            raise ValueError("TopicDetectionAgent results required")
        
        return True

    def validate_output(self, result: Dict[str, Any]) -> bool:
        """Ensure output contains required fields"""
        required_fields = ['fcr_by_topic', 'reopen_patterns', 'anomalies', 'exceptional_conversations']
        for field in required_fields:
            if field not in result:
                raise ValueError(f"Output missing '{field}' field")
        
        return True

    async def execute(self, context: AgentContext) -> AgentResult:
        """Main execution method for quality analysis"""
        start_time = datetime.now()
        
        try:
            # Validate input
            try:
                self.validate_input(context)
            except ValueError as e:
                return AgentResult(
                    agent_name=self.name,
                    success=False,
                    data={'error': str(e)},
                    confidence=0.0,
                    confidence_level=ConfidenceLevel.LOW,
                    limitations=[str(e)],
                    sources=[],
                    execution_time=0.0
                )
            
            # Extract data from context
            conversations = context.conversations
            topic_data = context.previous_results.get('TopicDetectionAgent', {}).get('data', {})
            topic_dist = topic_data.get('topic_distribution', {})
            topics_by_conv = context.metadata.get('topics_by_conversation', {}) if context.metadata else {}
            
            logger.info(f"Analyzing quality metrics across {len(conversations)} conversations")
            
            # Resolution Quality Analysis
            fcr_by_topic = self._calculate_fcr_by_topic(conversations, topics_by_conv)
            reopen_patterns = self._calculate_reopen_rates(conversations, topics_by_conv)
            multi_touch_analysis = self._calculate_multi_touch_patterns(conversations, topics_by_conv)
            resolution_distribution = self._calculate_resolution_distribution(conversations)
            
            # Anomaly Detection
            volume_anomalies = self._detect_volume_anomalies(topic_dist)
            resolution_outliers = self._detect_resolution_outliers(conversations)
            csat_outliers = self._detect_csat_outliers(conversations)
            temporal_clustering = self._detect_temporal_clustering(conversations, topics_by_conv)
            
            # Combine all anomalies
            all_anomalies = volume_anomalies + resolution_outliers + csat_outliers
            exceptional_conversations = self._format_exceptional_conversations(resolution_outliers, csat_outliers)
            
            # Use LLM to provide richer insights
            if self.ai_client:
                enriched_insights = await self._enrich_insights_with_llm(
                    fcr_by_topic, 
                    reopen_patterns, 
                    all_anomalies,
                    context
                )
            else:
                enriched_insights = None
            
            # Build result
            result_data = {
                'fcr_by_topic': fcr_by_topic,
                'reopen_patterns': reopen_patterns,
                'multi_touch_analysis': multi_touch_analysis,
                'resolution_distribution': resolution_distribution,
                'anomalies': all_anomalies,
                'exceptional_conversations': exceptional_conversations,
                'temporal_clustering': temporal_clustering,
                'llm_insights': enriched_insights
            }
            
            # Validate output
            try:
                self.validate_output(result_data)
            except ValueError as e:
                logger.error(f"Output validation failed: {e}")
                return AgentResult(
                    agent_name=self.name,
                    success=False,
                    data={'error': str(e)},
                    confidence=0.0,
                    confidence_level=ConfidenceLevel.LOW,
                    limitations=[str(e)],
                    sources=[],
                    execution_time=0.0
                )
            
            # Calculate confidence
            stats_coverage = sum(1 for c in conversations if c.get('statistics', {}).get('count_reopens') is not None) / len(conversations)
            csat_coverage = sum(1 for c in conversations if c.get('conversation_rating')) / len(conversations)
            overall_confidence = stats_coverage * 0.6 + csat_coverage * 0.4
            confidence_level = self._calculate_confidence_level(overall_confidence)
            
            # Build limitations
            limitations = []
            if stats_coverage < 0.8:
                limitations.append(f"Statistics data only available for {int(stats_coverage*100)}% of conversations")
            if csat_coverage < 0.3:
                limitations.append(f"CSAT data only available for {int(csat_coverage*100)}% of conversations")
            if len(all_anomalies) == 0:
                limitations.append("No statistical anomalies detected in current data")
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return AgentResult(
                agent_name=self.name,
                success=True,
                data=result_data,
                confidence=round(overall_confidence, 2),
                confidence_level=confidence_level,
                limitations=limitations,
                sources=['statistical_analysis', 'conversation_metadata'],
                execution_time=execution_time
            )
            
        except Exception as e:
            logger.error(f"QualityInsightsAgent execution failed: {e}", exc_info=True)
            execution_time = (datetime.now() - start_time).total_seconds()
            return AgentResult(
                agent_name=self.name,
                success=False,
                data={'error': str(e)},
                confidence=0.0,
                confidence_level=ConfidenceLevel.LOW,
                limitations=[f"Execution failed: {str(e)}"],
                sources=[],
                execution_time=execution_time
            )

    def _calculate_fcr_by_topic(
        self, 
        conversations: List[Dict], 
        topics_by_conv: Dict[str, List[str]]
    ) -> Dict[str, Dict[str, Any]]:
        """Calculate First Contact Resolution by topic"""
        try:
            fcr_results = {}
            
            # Group conversations by topic
            topic_conversations = defaultdict(list)
            for conv_id, topics in topics_by_conv.items():
                for conv in conversations:
                    if conv.get('id') == conv_id:
                        for topic in topics:
                            topic_conversations[topic].append(conv)
                        break
            
            # Calculate FCR for each topic
            for topic, convs in topic_conversations.items():
                closed_convs = [c for c in convs if c.get('state') == 'closed']
                if len(closed_convs) < 5:  # Skip topics with too few closed conversations
                    continue
                
                fcr_count = sum(1 for c in closed_convs if c.get('statistics', {}).get('count_reopens', 0) == 0)
                fcr_rate = fcr_count / len(closed_convs)
                
                # Add observation based on FCR
                if fcr_rate > 0.7:
                    observation = "Healthy FCR - most issues resolved on first contact"
                elif fcr_rate > 0.5:
                    observation = "Moderate FCR - some multi-touch resolution needed"
                else:
                    observation = "Concerning FCR - high rate of multi-touch interactions"
                
                fcr_results[topic] = {
                    'fcr': round(fcr_rate, 2),
                    'sample_size': len(closed_convs),
                    'observation': observation
                }
            
            return fcr_results
            
        except Exception as e:
            logger.warning(f"FCR calculation failed: {e}")
            return {}

    def _calculate_reopen_rates(
        self, 
        conversations: List[Dict], 
        topics_by_conv: Dict[str, List[str]]
    ) -> Dict[str, Dict[str, Any]]:
        """Calculate reopen rates by topic"""
        try:
            reopen_results = {}
            
            # Group conversations by topic
            topic_conversations = defaultdict(list)
            for conv_id, topics in topics_by_conv.items():
                for conv in conversations:
                    if conv.get('id') == conv_id:
                        for topic in topics:
                            topic_conversations[topic].append(conv)
                        break
            
            # Calculate reopen rate for each topic
            for topic, convs in topic_conversations.items():
                if len(convs) < 5:  # Skip topics with too few conversations
                    continue
                
                reopened_count = sum(1 for c in convs if c.get('statistics', {}).get('count_reopens', 0) > 0)
                reopen_rate = reopened_count / len(convs)
                
                # Add observation based on reopen rate
                if reopen_rate > 0.15:
                    observation = f"{int(reopen_rate*100)}% reopen rate suggests knowledge gap or process issue"
                elif reopen_rate > 0.10:
                    observation = f"{int(reopen_rate*100)}% reopen rate - moderate follow-up needed"
                else:
                    observation = f"{int(reopen_rate*100)}% reopen rate - low follow-up required"
                
                reopen_results[topic] = {
                    'reopen_rate': round(reopen_rate, 2),
                    'observation': observation
                }
            
            return reopen_results
            
        except Exception as e:
            logger.warning(f"Reopen rate calculation failed: {e}")
            return {}

    def _calculate_multi_touch_patterns(
        self, 
        conversations: List[Dict], 
        topics_by_conv: Dict[str, List[str]]
    ) -> Dict[str, Dict[str, Any]]:
        """Calculate multi-touch patterns by topic"""
        try:
            multi_touch_results = {}
            
            # Calculate overall average
            all_touch_counts = []
            for conv in conversations:
                touch_count = self._get_touch_count(conv)
                all_touch_counts.append(touch_count)
            
            overall_avg = np.mean(all_touch_counts) if all_touch_counts else 1
            
            # Group conversations by topic
            topic_conversations = defaultdict(list)
            for conv_id, topics in topics_by_conv.items():
                for conv in conversations:
                    if conv.get('id') == conv_id:
                        for topic in topics:
                            topic_conversations[topic].append(conv)
                        break
            
            # Calculate average touches for each topic
            for topic, convs in topic_conversations.items():
                if len(convs) < 5:  # Skip topics with too few conversations
                    continue
                
                touch_counts = [self._get_touch_count(c) for c in convs]
                avg_touches = np.mean(touch_counts)
                ratio = avg_touches / overall_avg if overall_avg > 0 else 1
                
                # Add observation based on ratio
                if ratio > 2.0:
                    observation = f"Requires {ratio:.1f}x more interactions - inherent complexity"
                elif ratio > 1.5:
                    observation = f"Moderate complexity - {ratio:.1f}x average interactions"
                else:
                    observation = "Standard interaction pattern"
                
                multi_touch_results[topic] = {
                    'avg_touches': round(avg_touches, 1),
                    'vs_overall': round(overall_avg, 1),
                    'observation': observation
                }
            
            return multi_touch_results
            
        except Exception as e:
            logger.warning(f"Multi-touch calculation failed: {e}")
            return {}

    def _get_touch_count(self, conv: Dict) -> int:
        """Get touch count from conversation"""
        # Try statistics field first (safe access)
        count = conv.get('statistics', {}).get('count_conversation_parts')
        if count:
            return count
        
        # Fallback to conversation_parts length (safe access)
        parts = conv.get('conversation_parts', {}).get('conversation_parts', [])
        if parts and isinstance(parts, list):
            return len(parts)
        
        return 1

    def _calculate_resolution_distribution(self, conversations: List[Dict]) -> Dict[str, Any]:
        """Calculate resolution time distribution"""
        try:
            resolution_times = []
            
            for conv in conversations:
                handling_time = conv.get('statistics', {}).get('handling_time')
                if handling_time:
                    resolution_times.append(handling_time / 3600)  # Convert to hours
            
            if not resolution_times:
                return {'under_24h': 0, '24_48h': 0, 'over_48h': 0, 'median_hours': 0}
            
            # Calculate distribution
            under_24h = sum(1 for t in resolution_times if t < 24) / len(resolution_times)
            between_24_48 = sum(1 for t in resolution_times if 24 <= t < 48) / len(resolution_times)
            over_48h = sum(1 for t in resolution_times if t >= 48) / len(resolution_times)
            median_hours = np.median(resolution_times)
            
            return {
                'under_24h': round(under_24h, 2),
                '24_48h': round(between_24_48, 2),
                'over_48h': round(over_48h, 2),
                'median_hours': round(median_hours, 1)
            }
            
        except Exception as e:
            logger.warning(f"Resolution distribution calculation failed: {e}")
            return {'under_24h': 0, '24_48h': 0, 'over_48h': 0, 'median_hours': 0}

    def _detect_volume_anomalies(self, topic_dist: Dict[str, int]) -> List[Dict[str, Any]]:
        """Detect topic volume outliers using Z-score"""
        try:
            if len(topic_dist) < 3:
                return []
            
            volumes = list(topic_dist.values())
            mean_volume = np.mean(volumes)
            std_volume = np.std(volumes)
            
            if std_volume == 0:
                return []
            
            anomalies = []
            for topic, volume in topic_dist.items():
                z_score = (volume - mean_volume) / std_volume
                
                # Flag if |Z-score| > 2.0 (2 standard deviations)
                if abs(z_score) > 2.0:
                    deviation_pct = int(((volume - mean_volume) / mean_volume) * 100)
                    anomalies.append({
                        'type': 'volume_spike' if z_score > 0 else 'volume_drop',
                        'topic': topic,
                        'expected': int(mean_volume),
                        'actual': volume,
                        'deviation_pct': abs(deviation_pct),
                        'statistical_significance': round(abs(z_score), 1),
                        'observation': f"Unusual {'concentration' if z_score > 0 else 'scarcity'}",
                        'confidence': min(0.95, 0.7 + abs(z_score) * 0.1)
                    })
            
            return anomalies
            
        except Exception as e:
            logger.warning(f"Volume anomaly detection failed: {e}")
            return []

    def _detect_resolution_outliers(self, conversations: List[Dict]) -> List[Dict[str, Any]]:
        """Detect resolution time outliers using IQR"""
        try:
            # Extract resolution times
            resolution_data = []
            for conv in conversations:
                handling_time = conv.get('statistics', {}).get('handling_time')
                if handling_time:
                    resolution_data.append({
                        'conversation_id': conv.get('id'),
                        'time_hours': handling_time / 3600,
                        'time_seconds': handling_time
                    })
            
            if len(resolution_data) < 10:
                return []
            
            times = [d['time_hours'] for d in resolution_data]
            q1 = np.percentile(times, 25)
            q3 = np.percentile(times, 75)
            iqr = q3 - q1
            median = np.median(times)
            
            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr
            
            outliers = []
            for data in resolution_data:
                time_h = data['time_hours']
                if time_h < lower_bound:
                    # Exceptionally fast - calculate deviation from median
                    deviation = abs(time_h - median)
                    outliers.append({
                        'conversation_id': data['conversation_id'],
                        'exceptional_in': 'resolution_speed',
                        'time_hours': time_h,
                        'deviation': deviation,
                        'metric': f"{int(time_h * 60)} minutes" if time_h < 1 else f"{time_h:.1f} hours",
                        'vs_median': f"{median:.1f} hours",
                        'recommendation': 'Study as efficiency example',
                        'intercom_url': self._build_intercom_url(data['conversation_id'])
                    })
                elif time_h > upper_bound:
                    # Exceptionally slow - calculate deviation from median
                    deviation = abs(time_h - median)
                    outliers.append({
                        'conversation_id': data['conversation_id'],
                        'exceptional_in': 'resolution_delay',
                        'time_hours': time_h,
                        'deviation': deviation,
                        'metric': f"{time_h:.1f} hours",
                        'vs_median': f"{median:.1f} hours",
                        'recommendation': 'Review for process bottlenecks',
                        'intercom_url': self._build_intercom_url(data['conversation_id'])
                    })
            
            # Sort by deviation (largest deviations first) and limit to top 5
            return sorted(outliers, key=lambda x: x['deviation'], reverse=True)[:5]
            
        except Exception as e:
            logger.warning(f"Resolution outlier detection failed: {e}")
            return []

    def _detect_csat_outliers(self, conversations: List[Dict]) -> List[Dict[str, Any]]:
        """Detect CSAT outliers"""
        try:
            # Get conversations with CSAT
            rated_convs = [c for c in conversations if c.get('conversation_rating') is not None]
            
            if len(rated_convs) < 10:
                return []
            
            # Calculate median CSAT
            csat_values = [c.get('conversation_rating') for c in rated_convs]
            median_csat = np.median(csat_values)
            
            outliers = []
            for conv in rated_convs:
                rating = conv.get('conversation_rating')
                
                # Exceptional positive (5 stars when median is low)
                if rating == 5 and median_csat < 3.5:
                    outliers.append({
                        'conversation_id': conv.get('id'),
                        'exceptional_in': 'positive_csat',
                        'metric': f"{rating} stars",
                        'vs_median': f"{median_csat:.1f} stars",
                        'recommendation': 'Study what went right',
                        'intercom_url': self._build_intercom_url(conv.get('id'))
                    })
                
                # Exceptional negative (1 star when median is high)
                elif rating == 1 and median_csat > 3.5:
                    outliers.append({
                        'conversation_id': conv.get('id'),
                        'exceptional_in': 'negative_csat',
                        'metric': f"{rating} star",
                        'vs_median': f"{median_csat:.1f} stars",
                        'recommendation': 'Review what went wrong',
                        'intercom_url': self._build_intercom_url(conv.get('id'))
                    })
            
            # Limit to top 6 (3 positive, 3 negative)
            positive = [o for o in outliers if o['exceptional_in'] == 'positive_csat'][:3]
            negative = [o for o in outliers if o['exceptional_in'] == 'negative_csat'][:3]
            
            return positive + negative
            
        except Exception as e:
            logger.warning(f"CSAT outlier detection failed: {e}")
            return []

    def _detect_temporal_clustering(
        self, 
        conversations: List[Dict], 
        topics_by_conv: Dict[str, List[str]]
    ) -> List[Dict[str, Any]]:
        """Detect temporal clustering of conversations"""
        try:
            # Group conversations by topic and day
            topic_day_counts = defaultdict(lambda: defaultdict(int))
            
            for conv_id, topics in topics_by_conv.items():
                for conv in conversations:
                    if conv.get('id') == conv_id:
                        created_at = conv.get('created_at')
                        if created_at:
                            # Parse timestamp and get day-of-week
                            if isinstance(created_at, int):
                                dt = datetime.fromtimestamp(created_at)
                            else:
                                dt = datetime.fromisoformat(str(created_at).replace('Z', '+00:00'))
                            
                            day_key = f"{dt.strftime('%Y-%m-%d')} ({dt.strftime('%a')})"
                            
                            for topic in topics:
                                topic_day_counts[topic][day_key] += 1
                        break
            
            # Detect clustering
            clustering = []
            for topic, day_counts in topic_day_counts.items():
                total_convs = sum(day_counts.values())
                
                if total_convs < 10:  # Skip topics with too few conversations
                    continue
                
                # Find top 2 days
                sorted_days = sorted(day_counts.items(), key=lambda x: x[1], reverse=True)
                top_2_count = sum(count for _, count in sorted_days[:2])
                clustering_pct = top_2_count / total_convs
                
                # Flag if >50% occurred in 2-day window
                if clustering_pct > 0.5:
                    day_list = ", ".join([day for day, _ in sorted_days[:2]])
                    clustering.append({
                        'topic': topic,
                        'observation': f"{top_2_count} of {total_convs} occurred on {day_list}",
                        'clustering_pct': round(clustering_pct, 2),
                        'interpretation': 'Temporal concentration detected'
                    })
            
            return clustering
            
        except Exception as e:
            logger.warning(f"Temporal clustering detection failed: {e}")
            return []

    def _format_exceptional_conversations(
        self, 
        resolution_outliers: List[Dict], 
        csat_outliers: List[Dict]
    ) -> List[Dict[str, Any]]:
        """Combine and format exceptional conversations"""
        return resolution_outliers + csat_outliers

    def _build_intercom_url(self, conversation_id: str) -> str:
        """Build Intercom URL for conversation"""
        workspace_id = getattr(settings, 'intercom_workspace_id', 'your_workspace')
        return f"https://app.intercom.com/a/apps/{workspace_id}/inbox/inbox/{conversation_id}"

    async def _enrich_insights_with_llm(
        self, 
        fcr_by_topic: Dict,
        reopen_patterns: Dict,
        anomalies: List[Dict],
        context: AgentContext
    ) -> str:
        """Use LLM to provide richer contextual insights"""
        try:
            # Build prompt with quality metrics
            prompt = f"""Analyze these quality metrics and anomalies from customer support data:

**First Contact Resolution by Topic:**
{self._format_fcr_for_llm(fcr_by_topic)}

**Reopen Patterns:**
{self._format_reopens_for_llm(reopen_patterns)}

**Anomalies Detected:**
{self._format_anomalies_for_llm(anomalies)}

Provide:
1. Key quality insights (what's working well, what needs attention)
2. Interpretation of anomalies (what might explain these patterns)
3. Observational recommendations for investigation

Keep insights concise, actionable, and focused on learning opportunities.
"""
            
            messages = [
                {"role": "system", "content": self.get_agent_specific_instructions()},
                {"role": "user", "content": prompt}
            ]
            
            # Use intensive model for strategic quality insights
            if self.client_type == "claude":
                response = await self.ai_client.client.messages.create(
                    model=self.intensive_model,
                    max_tokens=4000,
                    temperature=self.temperature,
                    system=self.get_agent_specific_instructions(),
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )
                return response.content[0].text
            else:
                response = await self.ai_client.client.chat.completions.create(
                    model=self.intensive_model,
                messages=messages,
                temperature=self.temperature
            )
            return response.choices[0].message.content
            
        except Exception as e:
            logger.warning(f"LLM enrichment failed: {e}")
            return None

    def _format_fcr_for_llm(self, fcr_by_topic: Dict) -> str:
        """Format FCR data for LLM"""
        lines = []
        for topic, data in fcr_by_topic.items():
            lines.append(f"- {topic}: {int(data['fcr']*100)}% FCR ({data['sample_size']} conversations)")
        return "\n".join(lines) if lines else "No FCR data available"

    def _format_reopens_for_llm(self, reopen_patterns: Dict) -> str:
        """Format reopen data for LLM"""
        lines = []
        for topic, data in reopen_patterns.items():
            lines.append(f"- {topic}: {int(data['reopen_rate']*100)}% reopen rate")
        return "\n".join(lines) if lines else "No reopen data available"

    def _format_anomalies_for_llm(self, anomalies: List[Dict]) -> str:
        """Format anomalies for LLM"""
        lines = []
        for anomaly in anomalies:
            if anomaly['type'] == 'volume_spike':
                lines.append(f"- Volume Spike: {anomaly['topic']} ({anomaly['actual']} vs {anomaly['expected']} expected, {anomaly['deviation_pct']}% deviation)")
            elif anomaly['type'] == 'volume_drop':
                lines.append(f"- Volume Drop: {anomaly['topic']} ({anomaly['actual']} vs {anomaly['expected']} expected)")
        return "\n".join(lines) if lines else "No anomalies detected"

    def _calculate_confidence_level(self, confidence: float) -> ConfidenceLevel:
        """Convert numeric confidence to ConfidenceLevel enum"""
        if confidence >= 0.8:
            return ConfidenceLevel.HIGH
        elif confidence >= 0.6:
            return ConfidenceLevel.MEDIUM
        else:
            return ConfidenceLevel.LOW

