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
    
    def _extract_customer_messages(self, conversations: List[Dict]) -> List[Dict]:
        """Extract and add customer_messages to conversations from raw Intercom data"""
        for conv in conversations:
            # Extract customer messages from conversation_parts
            customer_msgs = []
            parts = conv.get('conversation_parts', {}).get('conversation_parts', [])
            
            for part in parts:
                author = part.get('author', {})
                if author.get('type') == 'user':  # Customer message
                    body = part.get('body', '').strip()
                    if body:
                        customer_msgs.append(body)
            
            # Also check source (initial message)
            source = conv.get('source', {})
            if source.get('author', {}).get('type') == 'user':
                body = source.get('body', '').strip()
                if body:
                    customer_msgs.insert(0, body)  # Add at beginning
            
            conv['customer_messages'] = customer_msgs
        
        return conversations
    
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
        
        # Preprocess: Extract customer messages from raw Intercom data
        conversations = self._extract_customer_messages(conversations)
        
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
            
            # First, get the actual conversations_by_topic from detection result
            # The detection agent returns conversation IDs mapped to topics
            # We need to build a map of topic -> actual conversation objects
            conversations_by_topic_full = {}
            topics_by_conv_id = topic_detection_result.data.get('topics_by_conversation', {})
            
            for conv in paid_conversations:
                conv_id = conv.get('id')
                topics_for_conv = topics_by_conv_id.get(conv_id, [])
                
                for topic_assignment in topics_for_conv:
                    topic_name = topic_assignment['topic']
                    if topic_name not in conversations_by_topic_full:
                        conversations_by_topic_full[topic_name] = []
                    conversations_by_topic_full[topic_name].append(conv)
            
            # Process all topics in parallel for efficiency
            async def process_topic(topic_name: str, topic_stats: Dict):
                """Process a single topic with sentiment + examples"""
                topic_convs = conversations_by_topic_full.get(topic_name, [])
                
                # Skip topics with no conversations
                if len(topic_convs) == 0:
                    self.logger.info(f"   Skipping {topic_name}: 0 conversations")
                    return topic_name, None, None
                
                self.logger.info(f"   Processing {topic_name}: {len(topic_convs)} conversations")
                
                # Sentiment for this topic
                topic_context = context.model_copy()
                topic_context.metadata = {
                    'current_topic': topic_name,
                    'topic_conversations': topic_convs,
                    'sentiment_insight': ''
                }
                
                sentiment_result = await self.topic_sentiment_agent.execute(topic_context)
                
                # Examples for this topic
                topic_context.metadata['sentiment_insight'] = sentiment_result.data.get('sentiment_insight', '')
                examples_result = await self.example_extraction_agent.execute(topic_context)
                
                self.logger.info(f"   ✅ {topic_name}: Sentiment + {len(examples_result.data.get('examples', []))} examples")
                
                return topic_name, sentiment_result, examples_result
            
            # Process all topics in parallel (skip zero-volume topics)
            self.logger.info(f"   Processing {len(topic_dist)} topics in parallel...")
            topic_tasks = []
            for name, stats in topic_dist.items():
                volume = stats.get('volume', 0)
                if volume == 0:
                    self.logger.info(f"   ⏭️  Skipping topic '{name}': zero volume (LLM-discovered with no matches)")
                    continue
                topic_tasks.append(process_topic(name, stats))
            
            self.logger.info(f"   Created {len(topic_tasks)} topic processing tasks")
            topic_results = await asyncio.gather(*topic_tasks, return_exceptions=True)
            
            # Initialize per-topic tracking
            if 'TopicProcessing' not in workflow_results:
                workflow_results['TopicProcessing'] = {}
            
            # Collect results with per-topic error handling
            topic_names_to_process = [name for name, stats in topic_dist.items() if stats.get('volume', 0) > 0]
            
            for idx, result in enumerate(topic_results):
                # Determine topic name from task index
                topic_name = topic_names_to_process[idx] if idx < len(topic_names_to_process) else f"unknown_topic_{idx}"
                
                if isinstance(result, Exception):
                    error_msg = str(result)
                    self.logger.error(f"Topic '{topic_name}' processing failed: {error_msg}", exc_info=result)
                    # Add structured error entry
                    workflow_results['TopicProcessing'][topic_name] = {
                        'success': False,
                        'error_message': error_msg,
                        'error_type': type(result).__name__
                    }
                    continue
                
                # Unpack successful result
                result_topic_name, sentiment_result, examples_result = result
                
                # Skip if topic was empty
                if sentiment_result is None or examples_result is None:
                    workflow_results['TopicProcessing'][result_topic_name] = {
                        'success': False,
                        'error_message': 'Empty topic - no conversations matched'
                    }
                    continue
                
                # Success case
                topic_sentiments[result_topic_name] = sentiment_result.dict()
                topic_examples[result_topic_name] = examples_result.dict()
                workflow_results['TopicProcessing'][result_topic_name] = {
                    'success': True,
                    'sentiment_confidence': sentiment_result.confidence,
                    'examples_count': len(examples_result.data.get('examples', []))
                }
            
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
                'SegmentationAgent': segmentation_result.dict(),
                'TopicDetectionAgent': topic_detection_result.dict(),
                'TopicSentiments': topic_sentiments,  # Already dict
                'TopicExamples': topic_examples,  # Already dict
                'FinPerformanceAgent': fin_result.dict(),
                'TrendAgent': trend_result.dict()
            }
            output_context.metadata = {'week_id': week_id}
            
            formatter_result = await self.output_formatter_agent.execute(output_context)
            workflow_results['OutputFormatterAgent'] = formatter_result.dict()
            
            self.logger.info(f"   ✅ Output formatted")
            
            # Calculate summary and aggregate metrics
            total_time = (datetime.now() - start_time).total_seconds()
            
            # Aggregate metrics from all agents
            metrics = self._aggregate_metrics(workflow_results, topic_sentiments, topic_examples, total_time)
            
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
                'metrics': metrics,
                'agent_results': workflow_results
            }
            
            self.logger.info(f"🎉 TopicOrchestrator: Complete in {total_time:.1f}s")
            self.logger.info(f"   Topics: {len(topic_dist)}, Paid: {len(paid_conversations)}, Free: {len(free_conversations)}")
            
            return final_output
            
        except Exception as e:
            self.logger.error(f"TopicOrchestrator error: {e}")
            raise
    
    def _aggregate_metrics(
        self,
        workflow_results: Dict,
        topic_sentiments: Dict,
        topic_examples: Dict,
        total_time: float
    ) -> Dict[str, Any]:
        """
        Aggregate metrics from all agents for dashboard reporting.
        
        Returns structured metrics with per-agent timing, LLM calls, and counts.
        """
        metrics = {
            'total_execution_time': total_time,
            'agent_timings': {},
            'llm_stats': {
                'total_calls': 0,
                'total_tokens': 0
            },
            'per_topic_metrics': {},
            'overall_stats': {
                'topics_processed': 0,
                'examples_selected': 0,
                'errors': 0
            }
        }
        
        # Aggregate from main workflow agents
        for agent_name, result_data in workflow_results.items():
            if agent_name == 'TopicProcessing':
                continue  # Handle separately
                
            execution_time = result_data.get('execution_time', 0)
            token_count = result_data.get('token_count', 0)
            
            metrics['agent_timings'][agent_name] = {
                'execution_time': execution_time,
                'success': result_data.get('success', False)
            }
            
            if token_count > 0:
                metrics['llm_stats']['total_calls'] += 1
                metrics['llm_stats']['total_tokens'] += token_count
        
        # Aggregate per-topic metrics
        for topic_name, sentiment_result in topic_sentiments.items():
            examples_result = topic_examples.get(topic_name, {})
            
            topic_metrics = {
                'sentiment_execution_time': sentiment_result.get('execution_time', 0),
                'sentiment_confidence': sentiment_result.get('confidence', 0),
                'examples_count': len(examples_result.get('data', {}).get('examples', [])),
                'examples_execution_time': examples_result.get('execution_time', 0),
                'total_time': sentiment_result.get('execution_time', 0) + examples_result.get('execution_time', 0)
            }
            
            # Count LLM calls for this topic
            if sentiment_result.get('token_count', 0) > 0:
                topic_metrics['llm_calls'] = 1
                metrics['llm_stats']['total_tokens'] += sentiment_result.get('token_count', 0)
            else:
                topic_metrics['llm_calls'] = 0
            
            metrics['per_topic_metrics'][topic_name] = topic_metrics
            metrics['overall_stats']['topics_processed'] += 1
            metrics['overall_stats']['examples_selected'] += topic_metrics['examples_count']
        
        # Count errors from TopicProcessing
        topic_processing = workflow_results.get('TopicProcessing', {})
        for topic_name, status in topic_processing.items():
            if not status.get('success', True):
                metrics['overall_stats']['errors'] += 1
        
        # Add phase breakdown
        metrics['phase_breakdown'] = {
            'segmentation': metrics['agent_timings'].get('SegmentationAgent', {}).get('execution_time', 0),
            'topic_detection': metrics['agent_timings'].get('TopicDetectionAgent', {}).get('execution_time', 0),
            'per_topic_analysis': sum(m['total_time'] for m in metrics['per_topic_metrics'].values()),
            'fin_analysis': metrics['agent_timings'].get('FinPerformanceAgent', {}).get('execution_time', 0),
            'trend_analysis': metrics['agent_timings'].get('TrendAgent', {}).get('execution_time', 0),
            'output_formatting': metrics['agent_timings'].get('OutputFormatterAgent', {}).get('execution_time', 0)
        }
        
        self.logger.info(f"📊 Metrics Summary:")
        self.logger.info(f"   Total LLM calls: {metrics['llm_stats']['total_calls']}")
        self.logger.info(f"   Total tokens: {metrics['llm_stats']['total_tokens']}")
        self.logger.info(f"   Topics processed: {metrics['overall_stats']['topics_processed']}")
        self.logger.info(f"   Examples selected: {metrics['overall_stats']['examples_selected']}")
        self.logger.info(f"   Errors: {metrics['overall_stats']['errors']}")
        
        return metrics

