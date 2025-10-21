"""
FinPerformanceAgent: Dedicated analysis of Fin AI performance.

Purpose:
- Analyze Fin AI resolution rate
- Identify knowledge gaps
- Detect unnecessary escalations
- Performance by topic
"""

import logging
from typing import Dict, Any, List
from datetime import datetime

from src.agents.base_agent import BaseAgent, AgentResult, AgentContext, ConfidenceLevel
from src.services.openai_client import OpenAIClient

logger = logging.getLogger(__name__)


class FinPerformanceAgent(BaseAgent):
    """Agent specialized in Fin AI performance analysis with LLM insights"""
    
    def __init__(self):
        super().__init__(
            name="FinPerformanceAgent",
            model="gpt-4o",
            temperature=0.4
        )
        self.openai_client = OpenAIClient()
    
    def get_agent_specific_instructions(self) -> str:
        """Fin performance agent instructions"""
        return """
FIN PERFORMANCE AGENT SPECIFIC RULES:

1. Analyze Fin AI performance objectively:
   - What Fin is doing well
   - Where Fin has knowledge gaps
   - Unnecessary escalations to humans
   - Performance by topic

2. Focus on metrics, not emotions:
   - Resolution rate (% resolved without human request)
   - Knowledge gap frequency
   - Topic-specific performance differences

3. Identify patterns:
   - Which topics Fin handles well
   - Which topics Fin struggles with
   - Common knowledge gaps

4. Be honest about limitations:
   - Fin is AI - has inherent limitations
   - Some topics naturally require human expertise
"""
    
    def get_task_description(self, context: AgentContext) -> str:
        """Describe Fin analysis task"""
        fin_conversations = context.metadata.get('fin_conversations', [])
        return f"""
Analyze Fin AI performance across {len(fin_conversations)} AI-only conversations.

Calculate:
1. Resolution rate (no escalation requested)
2. Knowledge gaps (incorrect/incomplete answers)
3. Unnecessary escalations
4. Performance by topic
"""
    
    def format_context_data(self, context: AgentContext) -> str:
        """Format Fin conversations"""
        fin_convs = context.metadata.get('fin_conversations', [])
        return f"Fin AI conversations: {len(fin_convs)}"
    
    def validate_input(self, context: AgentContext) -> bool:
        """Validate input"""
        if 'fin_conversations' not in context.metadata:
            raise ValueError("fin_conversations not provided")
        return True
    
    def validate_output(self, result: Dict[str, Any]) -> bool:
        """Validate Fin analysis results"""
        required = ['resolution_rate', 'knowledge_gaps_count', 'performance_by_topic']
        return all(k in result for k in required)
    
    async def execute(self, context: AgentContext) -> AgentResult:
        """Execute Fin performance analysis"""
        start_time = datetime.now()
        
        try:
            self.validate_input(context)
            
            fin_conversations = context.metadata.get('fin_conversations', [])
            self.logger.info(f"FinPerformanceAgent: Analyzing {len(fin_conversations)} Fin conversations")
            
            # Calculate metrics
            total = len(fin_conversations)
            if total == 0:
                result_data = {'note': 'No Fin AI conversations found'}
            else:
                # Resolution rate
                escalation_phrases = ['speak to human', 'talk to agent', 'real person', 'human support']
                resolved_by_fin = [
                    c for c in fin_conversations
                    if not any(phrase in c.get('full_text', '').lower() for phrase in escalation_phrases)
                ]
                resolution_rate = len(resolved_by_fin) / total
                
                # Knowledge gaps
                knowledge_gap_phrases = ['incorrect', 'wrong', 'not helpful', 'didn\'t answer', 'not what i asked']
                knowledge_gaps = [
                    c for c in fin_conversations
                    if any(phrase in c.get('full_text', '').lower() for phrase in knowledge_gap_phrases)
                ]
                
                # Unnecessary escalations (requested human but Fin was right)
                # This would require manual review - placeholder for now
                unnecessary_escalations = []  # TODO: Implement with human feedback data
                
                # Performance by topic
                from collections import defaultdict
                topic_performance = defaultdict(lambda: {'total': 0, 'resolved': 0})
                
                for conv in fin_conversations:
                    topics = conv.get('detected_topics', ['Other'])
                    resolved = conv not in [c for c in fin_conversations if c in resolved_by_fin]
                    
                    for topic in topics:
                        topic_performance[topic]['total'] += 1
                        if resolved:
                            topic_performance[topic]['resolved'] += 1
                
                # Calculate rates
                topic_performance_dict = {}
                for topic, stats in topic_performance.items():
                    if stats['total'] >= 5:  # Only include topics with meaningful sample size
                        topic_performance_dict[topic] = {
                            'total': stats['total'],
                            'resolution_rate': stats['resolved'] / stats['total'] if stats['total'] > 0 else 0
                        }
                
                result_data = {
                    'total_fin_conversations': total,
                    'resolution_rate': resolution_rate,
                    'resolved_count': len(resolved_by_fin),
                    'knowledge_gaps_count': len(knowledge_gaps),
                    'knowledge_gap_examples': [
                        {
                            'id': c.get('id'),
                            'preview': c.get('customer_messages', [''])[0][:100]
                        }
                        for c in knowledge_gaps[:5]
                    ],
                    'unnecessary_escalations_count': len(unnecessary_escalations),
                    'performance_by_topic': topic_performance_dict,
                    'top_performing_topics': sorted(
                        topic_performance_dict.items(),
                        key=lambda x: x[1]['resolution_rate'],
                        reverse=True
                    )[:3],
                    'struggling_topics': sorted(
                        topic_performance_dict.items(),
                        key=lambda x: x[1]['resolution_rate']
                    )[:3]
                }
            
            # Add LLM interpretation of Fin performance
            if total > 0:
                self.logger.info("Generating nuanced Fin performance insights with LLM...")
                llm_insights = await self._generate_fin_insights(result_data)
                result_data['llm_insights'] = llm_insights
            
            self.validate_output(result_data)
            
            confidence = resolution_rate if total > 0 else 0.5
            confidence_level = (ConfidenceLevel.HIGH if total >= 100
                              else ConfidenceLevel.MEDIUM if total >= 30
                              else ConfidenceLevel.LOW)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            self.logger.info(f"FinPerformanceAgent: Completed in {execution_time:.2f}s")
            if total > 0:
                self.logger.info(f"   Resolution rate: {resolution_rate:.1%}")
                self.logger.info(f"   Knowledge gaps: {len(knowledge_gaps)}")
            
            return AgentResult(
                agent_name=self.name,
                success=True,
                data=result_data,
                confidence=confidence,
                confidence_level=confidence_level,
                limitations=[f"Based on {total} Fin conversations"] if total < 100 else [],
                sources=["Fin AI conversations", "Escalation pattern analysis"],
                execution_time=execution_time,
                token_count=0
            )
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            self.logger.error(f"FinPerformanceAgent error: {e}")
            
            return AgentResult(
                agent_name=self.name,
                success=False,
                data={},
                confidence=0.0,
                confidence_level=ConfidenceLevel.LOW,
                error_message=str(e),
                execution_time=execution_time
            )
    
    async def _generate_fin_insights(self, metrics: Dict) -> str:
        """
        Use LLM to generate nuanced insights about Fin's performance
        
        Args:
            metrics: Calculated Fin performance metrics
            
        Returns:
            Nuanced performance insights
        """
        resolution_rate = metrics.get('resolution_rate', 0)
        knowledge_gaps = metrics.get('knowledge_gaps_count', 0)
        total = metrics.get('total_fin_conversations', 0)
        top_topics = metrics.get('top_performing_topics', [])
        struggling = metrics.get('struggling_topics', [])
        
        prompt = f"""
Analyze Fin AI's performance and provide nuanced, actionable insights.

Metrics:
- Total Fin conversations: {total}
- Resolution rate: {resolution_rate:.1%}
- Knowledge gaps: {knowledge_gaps} conversations

Top performing topics: {', '.join([f"{t[0]} ({t[1]['resolution_rate']:.1%})" for t in top_topics])}
Struggling topics: {', '.join([f"{t[0]} ({t[1]['resolution_rate']:.1%})" for t in struggling])}

Instructions:
1. Provide 2-3 specific insights about Fin's performance
2. Be dramatic and specific, not generic
3. Identify patterns in what Fin does well vs struggles with
4. Suggest WHY Fin might be struggling (knowledge gaps, complex topics, etc.)
5. Keep it under 150 words, conversational tone

Insights:"""
        
        try:
            insights = await self.openai_client.generate_analysis(prompt)
            return insights.strip()
        except Exception as e:
            self.logger.warning(f"LLM insights generation failed: {e}")
            return f"Fin resolved {resolution_rate:.1%} of conversations with {knowledge_gaps} knowledge gaps detected."

