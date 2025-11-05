"""
ConfidenceMetaAgent - Reports on analysis quality and limitations (self-awareness)

This agent analyzes the analysis itself - reports confidence distribution across agents, 
data quality issues, coverage gaps, and limitations. Provides transparency about what 
the analysis can and cannot determine. Uses LLM for meta-level insights.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

from src.agents.base_agent import BaseAgent, AgentResult, ConfidenceLevel, AgentContext


logger = logging.getLogger(__name__)


class ConfidenceMetaAgent(BaseAgent):
    """Agent that provides meta-analysis of analysis quality and confidence"""

    def __init__(self, ai_client=None):
        super().__init__(
            name="ConfidenceMetaAgent",
            model="gpt-4o",
            temperature=0.3
        )
        self.ai_client = ai_client

    def get_agent_specific_instructions(self) -> str:
        """Return instructions for meta-analysis"""
        return """
You are performing meta-analysis on customer support analysis results. Your role is to:

1. **Be honest about limitations** - Clearly state what the analysis can and cannot determine
2. **Identify data quality issues** - Flag coverage gaps and their impact
3. **Suggest improvements** - Recommend specific actions to increase confidence
4. **Maintain observational tone** - Report objectively without blame
5. **Provide transparency** - Help users understand the reliability of insights

Your goal is to build trust through transparency about analysis quality.
"""

    def get_task_description(self, context: AgentContext) -> str:
        """Describe the meta-analysis task"""
        agent_count = len(context.previous_results) if context.previous_results else 0
        conv_count = len(context.conversations) if context.conversations else 0
        return f"Assess analysis quality, confidence levels, and data coverage limitations ({agent_count} agents, {conv_count} conversations)"

    def format_context_data(self, context: AgentContext) -> Dict[str, Any]:
        """Format summary of available data"""
        return {
            'total_agents': len(context.previous_results) if context.previous_results else 0,
            'total_conversations': len(context.conversations) if context.conversations else 0,
            'data_sources_available': list(context.previous_results.keys()) if context.previous_results else []
        }

    def validate_input(self, context: AgentContext) -> bool:
        """Ensure required data is available"""
        if not context.previous_results:
            raise ValueError("No previous agent results available for meta-analysis")
        
        if 'SegmentationAgent' not in context.previous_results:
            logger.warning("SegmentationAgent results not available for meta-analysis")
        
        if 'TopicDetectionAgent' not in context.previous_results:
            logger.warning("TopicDetectionAgent results not available for meta-analysis")
        
        return True

    def validate_output(self, result: Dict[str, Any]) -> bool:
        """Ensure output contains required fields"""
        required_fields = ['confidence_distribution', 'data_quality', 'limitations', 'what_would_improve_confidence']
        for field in required_fields:
            if field not in result:
                raise ValueError(f"Output missing '{field}' field")
        
        return True

    async def execute(self, context: AgentContext) -> AgentResult:
        """Main execution method for meta-analysis"""
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
                    confidence=1.0,  # Meta-agent is always confident about its assessment
                    confidence_level=ConfidenceLevel.HIGH,
                    limitations=[str(e)],
                    sources=[],
                    execution_time=0.0
                )
            
            # Extract data from context
            conversations = context.conversations or []
            previous_results = context.previous_results
            historical_context = self._get_historical_context(context)
            
            logger.info(f"Performing meta-analysis on {len(previous_results)} agents")
            
            # Analyze confidence distribution
            confidence_distribution = self._analyze_confidence_distribution(previous_results)
            
            # Assess data quality
            data_quality = self._assess_data_quality(conversations, previous_results)
            
            # Identify limitations
            limitations = self._identify_limitations(conversations, previous_results, historical_context)
            
            # Generate improvement suggestions
            improvement_suggestions = self._generate_improvement_suggestions(data_quality, limitations)
            
            # Use LLM to provide rich meta-insights
            if self.ai_client:
                llm_meta_analysis = await self._generate_meta_insights_with_llm(
                    confidence_distribution,
                    data_quality,
                    limitations,
                    improvement_suggestions,
                    context
                )
            else:
                llm_meta_analysis = None
            
            # Calculate overall data quality score
            overall_quality_score = self._calculate_overall_quality_score(data_quality)
            
            # Build result
            result_data = {
                'confidence_distribution': confidence_distribution,
                'data_quality': data_quality,
                'limitations': limitations,
                'what_would_improve_confidence': improvement_suggestions,
                'overall_data_quality_score': overall_quality_score,
                'llm_meta_analysis': llm_meta_analysis
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
                    confidence=1.0,
                    confidence_level=ConfidenceLevel.HIGH,
                    limitations=[str(e)],
                    sources=[],
                    execution_time=0.0
                )
            
            # Meta-agent is always confident about its assessment (self-aware)
            overall_confidence = 1.0
            confidence_level = ConfidenceLevel.HIGH
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return AgentResult(
                agent_name=self.name,
                success=True,
                data=result_data,
                confidence=overall_confidence,
                confidence_level=confidence_level,
                limitations=["Meta-analysis reflects current data state only"],
                sources=['agent_results', 'data_coverage_analysis'],
                execution_time=execution_time
            )
            
        except Exception as e:
            logger.error(f"ConfidenceMetaAgent execution failed: {e}", exc_info=True)
            execution_time = (datetime.now() - start_time).total_seconds()
            return AgentResult(
                agent_name=self.name,
                success=False,
                data={'error': str(e)},
                confidence=1.0,
                confidence_level=ConfidenceLevel.HIGH,
                limitations=[f"Execution failed: {str(e)}"],
                sources=[],
                execution_time=execution_time
            )

    def _analyze_confidence_distribution(self, previous_results: Dict[str, Any]) -> Dict[str, List[Dict]]:
        """Analyze confidence levels across all agents"""
        try:
            high_confidence = []
            medium_confidence = []
            low_confidence = []
            
            for agent_name, result in previous_results.items():
                # Skip if not a proper agent result
                if not isinstance(result, dict):
                    continue
                
                # Extract confidence
                confidence = result.get('confidence', 0.5)
                
                # Extract reason from limitations or data
                limitations = result.get('limitations', [])
                reason = limitations[0] if limitations else "No specific reason provided"
                
                # Categorize confidence
                agent_info = {
                    'agent': agent_name,
                    'confidence': confidence,
                    'reason': reason
                }
                
                if confidence > 0.8:
                    high_confidence.append(agent_info)
                elif confidence >= 0.6:
                    medium_confidence.append(agent_info)
                else:
                    low_confidence.append(agent_info)
            
            return {
                'high_confidence_insights': high_confidence,
                'medium_confidence_insights': medium_confidence,
                'low_confidence_insights': low_confidence
            }
            
        except Exception as e:
            logger.warning(f"Confidence distribution analysis failed: {e}")
            return {
                'high_confidence_insights': [],
                'medium_confidence_insights': [],
                'low_confidence_insights': []
            }

    def _assess_data_quality(
        self, 
        conversations: List[Dict], 
        previous_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Assess data quality and coverage"""
        try:
            if not conversations:
                return {
                    'tier_coverage': 0,
                    'csat_coverage': 0,
                    'conversation_parts_coverage': 0,
                    'statistics_coverage': 0,
                    'impact': 'No conversation data available'
                }
            
            # Calculate coverage metrics
            tier_coverage = self._calculate_tier_coverage(conversations)
            csat_coverage = self._calculate_csat_coverage(conversations)
            conversation_parts_coverage = sum(1 for c in conversations if c.get('conversation_parts')) / len(conversations)
            statistics_coverage = self._calculate_statistics_coverage(conversations)
            
            # Assess impact of gaps
            impact_messages = []
            if tier_coverage < 0.6:
                impact_messages.append("Tier-based analysis has moderate confidence due to incomplete data")
            if csat_coverage < 0.3:
                impact_messages.append("Sentiment analysis limited to text-based detection (low CSAT coverage)")
            if statistics_coverage < 0.5:
                impact_messages.append("Resolution metrics may be incomplete")
            
            impact = "; ".join(impact_messages) if impact_messages else "Data quality is sufficient for analysis"
            
            return {
                'tier_coverage': round(tier_coverage, 2),
                'csat_coverage': round(csat_coverage, 2),
                'conversation_parts_coverage': round(conversation_parts_coverage, 2),
                'statistics_coverage': round(statistics_coverage, 2),
                'impact': impact
            }
            
        except Exception as e:
            logger.warning(f"Data quality assessment failed: {e}")
            return {
                'tier_coverage': 0,
                'csat_coverage': 0,
                'conversation_parts_coverage': 0,
                'statistics_coverage': 0,
                'impact': f"Assessment failed: {str(e)}"
            }

    def _identify_limitations(
        self, 
        conversations: List[Dict], 
        previous_results: Dict[str, Any],
        historical_context: Dict[str, Any]
    ) -> List[str]:
        """Identify limitations in the analysis"""
        try:
            limitations = []
            
            # Check for historical baseline
            if historical_context['weeks_available'] < 4:
                limitations.append("No historical baseline - cannot determine if metrics are normal")
            
            # Check tier coverage
            tier_coverage = self._calculate_tier_coverage(conversations)
            if tier_coverage < 0.8:
                missing_pct = int((1 - tier_coverage) * 100)
                limitations.append(f"Tier detection: {missing_pct}% conversations without tier data")
            
            # Check CSAT coverage
            csat_coverage = self._calculate_csat_coverage(conversations)
            if csat_coverage < 0.3:
                limitations.append(f"CSAT coverage: Only {int(csat_coverage*100)}% of conversations have ratings")
            
            # Check for sentiment limitations
            limitations.append("Sentiment analysis: Based on customer messages only (agent responses not analyzed)")
            
            # Check for small sample sizes in topics
            topic_data = previous_results.get('TopicDetectionAgent', {}).get('data', {})
            topic_dist = topic_data.get('topic_distribution', {})
            small_topics = [topic for topic, count in topic_dist.items() if count < 10]
            if small_topics:
                limitations.append(f"{len(small_topics)} topics have <10 conversations - statistical significance limited")
            
            return limitations
            
        except Exception as e:
            logger.warning(f"Limitations identification failed: {e}")
            return [f"Unable to assess limitations: {str(e)}"]

    def _generate_improvement_suggestions(
        self, 
        data_quality: Dict[str, Any], 
        limitations: List[str]
    ) -> List[str]:
        """Generate improvement suggestions based on identified gaps"""
        try:
            suggestions = []
            
            # Based on tier coverage
            if data_quality.get('tier_coverage', 0) < 0.8:
                suggestions.append("Complete Stripe tier data in Intercom custom attributes")
            
            # Based on historical data
            if any('No historical baseline' in lim for lim in limitations):
                suggestions.append("4+ weeks of historical data for trend confidence")
            
            # Based on CSAT coverage
            if data_quality.get('csat_coverage', 0) < 0.3:
                current_pct = int(data_quality.get('csat_coverage', 0) * 100)
                suggestions.append(f"Higher CSAT response rate (currently {current_pct}%)")
            
            # Based on small sample sizes
            if any('statistical significance limited' in lim for lim in limitations):
                suggestions.append("Longer analysis period to increase sample sizes for rare topics")
            
            # Based on statistics coverage
            if data_quality.get('statistics_coverage', 0) < 0.8:
                suggestions.append("Enable comprehensive conversation statistics tracking in Intercom")
            
            # Limit to top 5 most impactful
            return suggestions[:5]
            
        except Exception as e:
            logger.warning(f"Improvement suggestions generation failed: {e}")
            return ["Unable to generate improvement suggestions"]

    def _calculate_tier_coverage(self, conversations: List[Dict]) -> float:
        """Calculate percentage of conversations with valid tier data"""
        if not conversations:
            return 0.0
        
        valid_tier_count = sum(1 for c in conversations if c.get('tier') and c.get('tier') != 'unknown')
        return valid_tier_count / len(conversations)

    def _calculate_csat_coverage(self, conversations: List[Dict]) -> float:
        """Calculate percentage of conversations with CSAT ratings"""
        if not conversations:
            return 0.0
        
        rated_count = sum(1 for c in conversations if c.get('conversation_rating') is not None)
        return rated_count / len(conversations)

    def _calculate_statistics_coverage(self, conversations: List[Dict]) -> float:
        """Calculate percentage of conversations with statistics data"""
        if not conversations:
            return 0.0
        
        has_stats_count = sum(
            1 for c in conversations 
            if c.get('statistics', {}).get('count_reopens') is not None 
            or c.get('statistics', {}).get('handling_time') is not None
        )
        return has_stats_count / len(conversations)

    def _get_historical_context(self, context: AgentContext) -> Dict[str, Any]:
        """Get historical context from metadata"""
        try:
            if context.metadata and 'historical_context' in context.metadata:
                return context.metadata['historical_context']
            
            # Default: no historical data
            return {
                'weeks_available': 0,
                'can_do_trends': False,
                'can_do_seasonality': False
            }
            
        except Exception as e:
            logger.warning(f"Historical context extraction failed: {e}")
            return {
                'weeks_available': 0,
                'can_do_trends': False,
                'can_do_seasonality': False
            }

    def _calculate_overall_quality_score(self, data_quality: Dict[str, Any]) -> float:
        """Calculate overall data quality score"""
        try:
            # Weighted average of coverage metrics
            tier_weight = 0.3
            csat_weight = 0.2
            parts_weight = 0.2
            stats_weight = 0.3
            
            score = (
                data_quality.get('tier_coverage', 0) * tier_weight +
                data_quality.get('csat_coverage', 0) * csat_weight +
                data_quality.get('conversation_parts_coverage', 0) * parts_weight +
                data_quality.get('statistics_coverage', 0) * stats_weight
            )
            
            return round(score, 2)
            
        except Exception as e:
            logger.warning(f"Overall quality score calculation failed: {e}")
            return 0.5

    async def _generate_meta_insights_with_llm(
        self,
        confidence_distribution: Dict,
        data_quality: Dict,
        limitations: List[str],
        improvements: List[str],
        context: AgentContext
    ) -> Optional[str]:
        """Use LLM to generate rich meta-insights"""
        try:
            # Build prompt with meta-analysis data
            prompt = f"""Provide meta-analysis of this customer support analysis:

**Confidence Distribution:**
- High confidence: {len(confidence_distribution['high_confidence_insights'])} agents
- Medium confidence: {len(confidence_distribution['medium_confidence_insights'])} agents
- Low confidence: {len(confidence_distribution['low_confidence_insights'])} agents

**Data Quality:**
- Tier coverage: {int(data_quality.get('tier_coverage', 0)*100)}%
- CSAT coverage: {int(data_quality.get('csat_coverage', 0)*100)}%
- Statistics coverage: {int(data_quality.get('statistics_coverage', 0)*100)}%
- Overall quality score: {data_quality.get('overall_data_quality_score', 0)}

**Key Limitations:**
{chr(10).join(f"- {lim}" for lim in limitations[:5])}

**Improvement Recommendations:**
{chr(10).join(f"- {imp}" for imp in improvements[:5])}

Provide:
1. Overall assessment of analysis reliability
2. Which insights to trust most/least
3. Priority improvements for better analysis

Keep response concise (4-5 sentences).
"""
            
            messages = [
                {"role": "system", "content": self.get_agent_specific_instructions()},
                {"role": "user", "content": prompt}
            ]
            
            response = await self.ai_client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.warning(f"LLM meta-analysis failed: {e}")
            return None

