"""
TopicOrchestrator: Coordinates the topic-based multi-agent workflow.

Purpose:
- Orchestrate all topic-based agents
- Process each topic independently
- Combine results into Hilary's format
- Handle errors gracefully
"""

import logging
import asyncio
from typing import Dict, Any, List
from datetime import datetime

from src.agents.base_agent import AgentContext
from src.agents.segmentation_agent import SegmentationAgent
from src.agents.topic_detection_agent import TopicDetectionAgent
from src.agents.topic_sentiment_agent import TopicSentimentAgent
from src.agents.example_extraction_agent import ExampleExtractionAgent
from src.agents.fin_performance_agent import FinPerformanceAgent
from src.agents.trend_agent import TrendAgent
from src.agents.output_formatter_agent import OutputFormatterAgent

logger = logging.getLogger(__name__)


class TopicOrchestrator:
    """Orchestrates topic-based multi-agent workflow"""
    
    def __init__(self):
        self.segmentation_agent = SegmentationAgent()
        self.topic_detection_agent = TopicDetectionAgent()
        self.topic_sentiment_agent = TopicSentimentAgent()
        self.example_extraction_agent = ExampleExtractionAgent()
        self.fin_performance_agent = FinPerformanceAgent()
        self.trend_agent = TrendAgent()
        self.output_formatter_agent = OutputFormatterAgent()
        
        self.logger = logging.getLogger(__name__)
    
    async def execute_weekly_analysis(
        self,
        conversations: List[Dict],
        week_id: str = None,
        start_date: datetime = None,
        end_date: datetime = None
    ) -> Dict[str, Any]:
        """
        Execute complete weekly VoC analysis
        
        Args:
            conversations: All conversations for the week
            week_id: Week identifier (e.g., '2024-W42')
            start_date: Week start date
            end_date: Week end date
        
        Returns:
            Complete analysis in Hilary's format
        """
        if not week_id:
            week_id = datetime.now().strftime('%Y-W%W')
        
        start_time = datetime.now()
        self.logger.info(f"🤖 TopicOrchestrator: Starting weekly analysis for {week_id}")
        self.logger.info(f"   Total conversations: {len(conversations)}")
        
        # Create context
        context = AgentContext(
            analysis_id=f"weekly_{week_id}",
            analysis_type="weekly_voc",
            start_date=start_date or datetime.now(),
            end_date=end_date or datetime.now(),
            conversations=conversations,
            metadata={'week_id': week_id}
        )
        
        workflow_results = {}
        
        try:
            # PHASE 1: Segment conversations (paid vs free)
            self.logger.info("📊 Phase 1: Segmentation (Paid vs Free)")
            segmentation_result = await self.segmentation_agent.execute(context)
            workflow_results['SegmentationAgent'] = segmentation_result.dict()
            
            paid_conversations = segmentation_result.data.get('paid_customer_conversations', [])
            free_conversations = segmentation_result.data.get('free_customer_conversations', [])
            
            self.logger.info(f"   ✅ Paid: {len(paid_conversations)}, Free: {len(free_conversations)}")
            
            # PHASE 2: Detect topics (on paid conversations)
            self.logger.info("🏷️  Phase 2: Topic Detection")
            context.conversations = paid_conversations
            topic_detection_result = await self.topic_detection_agent.execute(context)
            workflow_results['TopicDetectionAgent'] = topic_detection_result.dict()
            
            topic_dist = topic_detection_result.data.get('topic_distribution', {})
            self.logger.info(f"   ✅ Detected {len(topic_dist)} topics")
            
            # PHASE 3: Analyze each topic
            self.logger.info("💭 Phase 3: Per-Topic Analysis")
            topic_sentiments = {}
            topic_examples = {}
            
            for topic_name, topic_stats in topic_dist.items():
                # Get conversations for this topic
                topic_convs = [
                    c for c in paid_conversations
                    if any(t['topic'] == topic_name 
                          for t in topic_detection_result.data['topics_by_conversation'].get(c.get('id'), []))
                ]
                
                # Sentiment for this topic
                topic_context = context.model_copy()
                topic_context.metadata = {
                    'current_topic': topic_name,
                    'topic_conversations': topic_convs,
                    'sentiment_insight': ''  # Will be filled
                }
                
                sentiment_result = await self.topic_sentiment_agent.execute(topic_context)
                topic_sentiments[topic_name] = sentiment_result.dict()
                
                # Examples for this topic
                topic_context.metadata['sentiment_insight'] = sentiment_result.data.get('sentiment_insight', '')
                examples_result = await self.example_extraction_agent.execute(topic_context)
                topic_examples[topic_name] = examples_result.dict()
                
                self.logger.info(f"   ✅ {topic_name}: Sentiment + {len(examples_result.data.get('examples', []))} examples")
            
            # PHASE 4: Fin Analysis (on free conversations)
            self.logger.info("🤖 Phase 4: Fin AI Performance Analysis")
            fin_context = context.model_copy()
            fin_context.metadata = {'fin_conversations': free_conversations}
            fin_result = await self.fin_performance_agent.execute(fin_context)
            workflow_results['FinPerformanceAgent'] = fin_result.dict()
            
            self.logger.info(f"   ✅ Fin analysis complete")
            
            # PHASE 5: Trend Analysis
            self.logger.info("📈 Phase 5: Trend Analysis")
            trend_context = context.model_copy()
            trend_context.metadata = {
                'current_week_results': {
                    'topic_distribution': topic_dist,
                    'topic_sentiments': {k: v['data'] for k, v in topic_sentiments.items()}
                },
                'week_id': week_id
            }
            trend_result = await self.trend_agent.execute(trend_context)
            workflow_results['TrendAgent'] = trend_result.dict()
            
            self.logger.info(f"   ✅ Trend analysis complete")
            
            # PHASE 6: Format Output
            self.logger.info("📝 Phase 6: Output Formatting")
            output_context = context.model_copy()
            output_context.previous_results = {
                'SegmentationAgent': segmentation_result,
                'TopicDetectionAgent': topic_detection_result,
                'TopicSentiments': topic_sentiments,
                'TopicExamples': topic_examples,
                'FinPerformanceAgent': fin_result,
                'TrendAgent': trend_result
            }
            output_context.metadata = {'week_id': week_id}
            
            formatter_result = await self.output_formatter_agent.execute(output_context)
            workflow_results['OutputFormatterAgent'] = formatter_result.dict()
            
            self.logger.info(f"   ✅ Output formatted")
            
            # Calculate summary
            total_time = (datetime.now() - start_time).total_seconds()
            
            final_output = {
                'week_id': week_id,
                'formatted_report': formatter_result.data.get('formatted_output', ''),
                'summary': {
                    'total_conversations': len(conversations),
                    'paid_conversations': len(paid_conversations),
                    'free_conversations': len(free_conversations),
                    'topics_analyzed': len(topic_dist),
                    'total_execution_time': total_time,
                    'agents_completed': len(workflow_results)
                },
                'agent_results': workflow_results
            }
            
            self.logger.info(f"🎉 TopicOrchestrator: Complete in {total_time:.1f}s")
            self.logger.info(f"   Topics: {len(topic_dist)}, Paid: {len(paid_conversations)}, Free: {len(free_conversations)}")
            
            return final_output
            
        except Exception as e:
            self.logger.error(f"TopicOrchestrator error: {e}")
            raise

