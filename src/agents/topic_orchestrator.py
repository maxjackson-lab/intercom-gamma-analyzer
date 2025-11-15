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
from typing import Dict, Any, List, Optional
from datetime import datetime
from pydantic import ValidationError

from src.agents.base_agent import AgentContext
from src.agents.segmentation_agent import SegmentationAgent
from src.agents.topic_detection_agent import TopicDetectionAgent
from src.agents.subtopic_detection_agent import SubTopicDetectionAgent
from src.agents.topic_sentiment_agent import TopicSentimentAgent
from src.agents.example_extraction_agent import ExampleExtractionAgent
from src.agents.fin_performance_agent import FinPerformanceAgent
from src.agents.trend_agent import TrendAgent
from src.agents.output_formatter_agent import OutputFormatterAgent
from src.agents.canny_topic_detection_agent import CannyTopicDetectionAgent
from src.agents.cross_platform_correlation_agent import CrossPlatformCorrelationAgent
from src.agents.correlation_agent import CorrelationAgent
from src.agents.quality_insights_agent import QualityInsightsAgent
from src.agents.churn_risk_agent import ChurnRiskAgent
from src.agents.confidence_meta_agent import ConfidenceMetaAgent
from src.services.ai_model_factory import AIModelFactory, AIModel
from src.services.duckdb_storage import DuckDBStorage
from src.services.historical_snapshot_service import HistoricalSnapshotService
from src.utils.agent_output_display import get_display
from src.config.modes import get_analysis_mode_config
from src.models.analysis_models import (
    SegmentationPayload,
    TopicDetectionResult,
    SubtopicDetectionResult,
    FinAnalysisPayload,
    TrendAnalysisPayload
)

logger = logging.getLogger(__name__)


def _normalize_agent_result(result: Any) -> Dict[str, Any]:
    """
    Normalize agent result to dictionary format.
    
    Handles both Pydantic models and plain dict returns safely.
    
    Args:
        result: Agent result (either Pydantic AgentResult or dict)
        
    Returns:
        Dictionary representation of the result
    """
    if result is None:
        return {}
    
    # If it's already a dict, return as-is
    if isinstance(result, dict):
        return result
    
    # If it has a .dict() method (Pydantic), use it
    if hasattr(result, 'dict') and callable(result.dict):
        try:
            return result.dict()
        except Exception as e:
            logger.warning(f"Failed to call .dict() on result: {e}")
            return {}
    
    # If it has a model_dump method (Pydantic v2), use it
    if hasattr(result, 'model_dump') and callable(result.model_dump):
        try:
            return result.model_dump()
        except Exception as e:
            logger.warning(f"Failed to call .model_dump() on result: {e}")
            return {}
    
    # Fallback: try to convert to dict
    try:
        return dict(result)
    except Exception as e:
        logger.warning(f"Could not convert result to dict: {e}")
        return {}


class TopicOrchestrator:
    """Orchestrates topic-based multi-agent workflow"""
    
    def __init__(self, ai_factory: AIModelFactory = None, audit_trail=None, execution_monitor=None):
        #Audit trail for detailed narration
        self.audit = audit_trail
        
        # Execution monitor for real-time status (optional)
        self.monitor = execution_monitor
        
        # Enable escalation tracking to track Fin → Vendor → Senior Staff escalations
        self.segmentation_agent = SegmentationAgent(track_escalations=True)
        self.topic_detection_agent = TopicDetectionAgent()
        self.subtopic_detection_agent = SubTopicDetectionAgent()
        self.topic_sentiment_agent = TopicSentimentAgent()
        self.example_extraction_agent = ExampleExtractionAgent()
        self.fin_performance_agent = FinPerformanceAgent(audit=self.audit)
        # TrendAgent will get historical_snapshot_service via lazy property when needed
        self._trend_agent = None
        self.output_formatter_agent = OutputFormatterAgent()
        
        # Analytical insight agents (Phase 4.5)
        self.correlation_agent = CorrelationAgent()
        self.quality_insights_agent = QualityInsightsAgent()
        self.churn_risk_agent = ChurnRiskAgent()
        self.confidence_meta_agent = ConfidenceMetaAgent()
        
        # Canny integration agents (lazy-initialized only when needed)
        self.ai_factory = ai_factory or AIModelFactory()
        self._canny_topic_detection_agent = None
        self._cross_platform_correlation_agent = None
        
        self.logger = logging.getLogger(__name__)
        self.logger.info("Analytical insight agents initialized: Correlation, QualityInsights, ChurnRisk, ConfidenceMeta")
        
        # Concurrency control
        config = get_analysis_mode_config()
        max_concurrent = config.get_multi_agent_setting('max_concurrent_topics') or 5
        self.topic_semaphore = asyncio.Semaphore(max_concurrent)
        self.logger.info(f"Topic processing concurrency limit: {max_concurrent}")
        
        # Historical snapshot service (lazy initialization)
        self._historical_snapshot_service = None
        self._duckdb_storage = None
    
    @property
    def duckdb_storage(self):
        """Lazy-initialize DuckDB storage"""
        if self._duckdb_storage is None:
            try:
                self._duckdb_storage = DuckDBStorage()
            except Exception as e:
                self.logger.warning(f"Failed to initialize DuckDB storage: {e}")
        return self._duckdb_storage
    
    @property
    def historical_snapshot_service(self):
        """Lazy-initialize historical snapshot service with migration on first access"""
        if self._historical_snapshot_service is None:
            try:
                if self.duckdb_storage is not None:
                    self._historical_snapshot_service = HistoricalSnapshotService(self.duckdb_storage)
                    # Run migration on first initialization
                    try:
                        migration_result = self._historical_snapshot_service.migrate_json_snapshots()
                        if migration_result['migrated_count'] > 0:
                            self.logger.info(
                                f"Migrated {migration_result['migrated_count']} JSON snapshots to DuckDB"
                            )
                    except Exception as e:
                        self.logger.warning(f"Snapshot migration failed: {e}")
            except Exception as e:
                self.logger.warning(f"Failed to initialize historical snapshot service: {e}")
        return self._historical_snapshot_service
    
    @property
    def trend_agent(self):
        """Lazy-initialize TrendAgent with historical snapshot service"""
        if self._trend_agent is None:
            self._trend_agent = TrendAgent(
                historical_snapshot_service=self.historical_snapshot_service
            )
        return self._trend_agent
    
    @property
    def canny_topic_detection_agent(self):
        """Lazy-initialize Canny topic detection agent only when needed"""
        if self._canny_topic_detection_agent is None:
            self._canny_topic_detection_agent = CannyTopicDetectionAgent(self.ai_factory)
        return self._canny_topic_detection_agent
    
    @property
    def cross_platform_correlation_agent(self):
        """Lazy-initialize cross-platform correlation agent only when needed"""
        if self._cross_platform_correlation_agent is None:
            self._cross_platform_correlation_agent = CrossPlatformCorrelationAgent(self.ai_factory)
        return self._cross_platform_correlation_agent
    
    async def execute_weekly_analysis(
        self,
        conversations: List[Dict],
        week_id: str = None,
        start_date: datetime = None,
        end_date: datetime = None,
        period_type: str = None,
        period_label: str = None,
        canny_posts: List[Dict] = None,
        ai_model: AIModel = AIModel.OPENAI_GPT4
    ) -> Dict[str, Any]:
        """
        Execute complete weekly VoC analysis with optional Canny integration.
        
        Args:
            conversations: All conversations for the week
            week_id: Week identifier (e.g., '2024-W42')
            start_date: Week start date
            end_date: Week end date
            period_type: Period type (e.g., 'week', 'month', 'custom')
            period_label: Human-readable period label
            canny_posts: Optional list of Canny feature request posts
            ai_model: AI model to use for analysis
        
        Returns:
            Complete analysis in Hilary's format with optional Canny correlation
        """
        if not week_id:
            week_id = datetime.now().strftime('%Y-W%W')
        
        start_time = datetime.now()
        self.logger.info(f"🤖 TopicOrchestrator: Starting weekly analysis for {week_id}")
        self.logger.info(f"   Total conversations: {len(conversations)}")
        
        # Note: conversations should already have customer_messages from DataPreprocessor
        # If not present, add empty list to avoid errors (for backward compatibility)
        for conv in conversations:
            if 'customer_messages' not in conv:
                conv['customer_messages'] = []
        
        # Create context
        context = AgentContext(
            analysis_id=f"weekly_{week_id}",
            analysis_type="weekly_voc",
            start_date=start_date or datetime.now(),
            end_date=end_date or datetime.now(),
            conversations=conversations,
            metadata={
                'week_id': week_id,
                'period_type': period_type,
                'period_label': period_label
            }
        )
        
        workflow_results = {}
        
        # Initialize display with config settings
        config = get_analysis_mode_config()
        display = get_display()
        display.enabled = config.get_visibility_setting('enable_agent_output_display', True)
        show_full_data = config.get_visibility_setting('show_full_agent_data', False)
        
        try:
            # PHASE 1: Segment conversations (paid vs free)
            self.logger.info("📊 Phase 1: Segmentation (Paid vs Free)")
            
            if self.audit:
                self.audit.step("Phase 1: Segmentation", "Starting customer tier classification", {
                    'agent': 'SegmentationAgent',
                    'total_conversations': len(conversations),
                    'method': 'Tier-first classification (Free/Paid/Unknown)'
                })
            
            # Report agent start
            if self.monitor:
                from src.services.execution_monitor import AgentStatus
                await self.monitor.update_agent_status('SegmentationAgent', AgentStatus.RUNNING, 
                                                      f"Classifying {len(conversations)} conversations into Free/Paid tiers")
            
            segmentation_result = await self.segmentation_agent.execute(context)
            workflow_results['SegmentationAgent'] = _normalize_agent_result(segmentation_result)
            
            # Report agent completion
            if self.monitor:
                await self.monitor.update_agent_status('SegmentationAgent', AgentStatus.COMPLETED,
                                                      f"Classified {segmentation_result.data.get('paid_count', 0)} paid, {segmentation_result.data.get('free_count', 0)} free",
                                                      confidence=segmentation_result.confidence)

            # Record tool calls from agent if audit is enabled
            if self.audit:
                if hasattr(self.audit, 'record_tool_calls_from_agent'):
                    self.audit.record_tool_calls_from_agent(segmentation_result)

            # Display agent result
            try:
                display.display_agent_result('SegmentationAgent', _normalize_agent_result(segmentation_result), show_full_data)
            except Exception as e:
                logger.warning(f"Failed to display SegmentationAgent result: {e}")
            
            # Validate and parse segmentation result with typed payload
            try:
                segmentation_payload = SegmentationPayload(**segmentation_result.data)
                self.logger.debug("✅ SegmentationPayload validation passed")
            except ValidationError as e:
                self.logger.warning(f"⚠️ SegmentationPayload validation failed: {e}")
                # Continue with raw data but log warning
                segmentation_payload = None
            
            # Extract data (use typed payload if available, otherwise raw data)
            if segmentation_payload:
                paid_conversations = segmentation_payload.paid_customer_conversations
                free_fin_only_conversations = segmentation_payload.free_fin_only_conversations
                paid_fin_resolved_conversations = segmentation_payload.paid_fin_resolved_conversations
            else:
                paid_conversations = segmentation_result.data.get('paid_customer_conversations', [])
                free_fin_only_conversations = segmentation_result.data.get('free_fin_only_conversations', [])
                paid_fin_resolved_conversations = segmentation_result.data.get('paid_fin_resolved_conversations', [])

            self.logger.info(f"   ✅ Paid: {len(paid_conversations)} (Human: {len(paid_conversations) - len(paid_fin_resolved_conversations)}, Fin-resolved: {len(paid_fin_resolved_conversations)})")
            self.logger.info(f"   ✅ Free (Fin-only): {len(free_fin_only_conversations)}")
            
            if self.audit:
                self.audit.step("Phase 1: Segmentation", "Completed customer tier classification", {
                    'paid_conversations': len(paid_conversations),
                    'free_conversations': len(free_fin_only_conversations),
                    'paid_fin_resolved': len(paid_fin_resolved_conversations),
                    'paid_human_handled': len(paid_conversations) - len(paid_fin_resolved_conversations),
                    'execution_time_seconds': segmentation_result.execution_time
                })
                
                self.audit.decision(
                    "How were conversations segmented by tier?",
                    "Tier-first classification using custom_attributes['tier'] field",
                    "Free tier customers can only interact with Fin AI. Paid tier can escalate to humans.",
                    {
                        'free_tier_count': len(free_fin_only_conversations),
                        'paid_tier_count': len(paid_conversations),
                        'free_percentage': f"{len(free_fin_only_conversations)/len(conversations)*100:.1f}%",
                        'paid_percentage': f"{len(paid_conversations)/len(conversations)*100:.1f}%"
                    }
                )
            
            # PHASE 2: Detect topics (on ALL conversations - paid AND free)
            # We need topics for both paid tier (for cards) and free tier (for Fin analysis)
            self.logger.info("🏷️  Phase 2: Topic Detection")
            self.logger.info(f"   Running topic detection on ALL {len(conversations)} conversations (paid + free)")
            
            if self.audit:
                self.audit.step("Phase 2: Topic Detection", "Starting AI-based topic classification", {
                    'agent': 'TopicDetectionAgent',
                    'conversations_to_classify': len(conversations),
                    'taxonomy_categories': 12,
                    'method': 'AI classification with keyword fallback'
                })
            
            context.conversations = conversations  # Changed: detect topics for ALL conversations
            
            # Report agent start
            if self.monitor:
                await self.monitor.update_agent_status('TopicDetectionAgent', AgentStatus.RUNNING,
                                                      f"Classifying {len(conversations)} conversations into topics")
            
            topic_detection_result = await self.topic_detection_agent.execute(context)
            workflow_results['TopicDetectionAgent'] = _normalize_agent_result(topic_detection_result)
            
            # Report agent completion
            if self.monitor:
                topics_found = len(topic_detection_result.data.get('topic_distribution', {}))
                await self.monitor.update_agent_status('TopicDetectionAgent', AgentStatus.COMPLETED,
                                                      f"Detected {topics_found} topics",
                                                      token_usage={'total': topic_detection_result.token_count},
                                                      confidence=topic_detection_result.confidence)

            # Record tool calls from agent if audit is enabled
            if self.audit:
                if hasattr(self.audit, 'record_tool_calls_from_agent'):
                    self.audit.record_tool_calls_from_agent(topic_detection_result)

            # Display agent result
            try:
                display.display_agent_result('TopicDetectionAgent', _normalize_agent_result(topic_detection_result), show_full_data)
            except Exception as e:
                logger.warning(f"Failed to display TopicDetectionAgent result: {e}")
            
            # Validate and parse topic detection result with typed payload
            try:
                topic_payload = TopicDetectionResult(**topic_detection_result.data)
                self.logger.debug("✅ TopicDetectionResult validation passed")
            except ValidationError as e:
                self.logger.warning(f"⚠️ TopicDetectionResult validation failed: {e}")
                topic_payload = None
            
            # Extract data (use typed payload if available, otherwise raw data)
            if topic_payload:
                topic_dist = topic_payload.topic_distribution
                topics_by_conv = topic_payload.topics_by_conversation
            else:
                topic_dist = topic_detection_result.data.get('topic_distribution', {})
                topics_by_conv = topic_detection_result.data.get('topics_by_conversation', {})
            
            self.logger.info(f"   ✅ Detected {len(topic_dist)} topics across all tiers")
            
            # Normalize topic_distribution to ensure consistent structure
            # TopicDetectionAgent can return either:
            # - Proper format: {topic: {'volume': N, ...}}
            # - Legacy format: {topic: N}
            # We need dict format for downstream processing
            normalized_topic_dist = {}
            for topic, value in topic_dist.items():
                if isinstance(value, dict):
                    # Already correct format
                    normalized_topic_dist[topic] = value
                elif isinstance(value, int):
                    # Convert int to dict format
                    normalized_topic_dist[topic] = {'volume': value}
                else:
                    self.logger.warning(f"Unexpected topic value type for {topic}: {type(value)}")
                    normalized_topic_dist[topic] = {'volume': 0}
            
            topic_dist = normalized_topic_dist
            
            if self.audit:
                # Get top topics (now all values are dicts with 'volume' key)
                try:
                    top_topics_list = list(sorted(
                        topic_dist.items(), 
                        key=lambda x: x[1].get('volume', 0), 
                        reverse=True
                    )[:5])
                    # Format for audit log (topic, volume)
                    top_topics_list = [(topic, stats.get('volume', 0)) for topic, stats in top_topics_list]
                except Exception as e:
                    self.logger.warning(f"Could not sort top topics: {e}")
                    top_topics_list = []
                
                self.audit.step("Phase 2: Topic Detection", f"Completed topic classification - {len(topic_dist)} topics detected", {
                    'topics_detected': len(topic_dist),
                    'conversations_classified': len(topics_by_conv),
                    'top_topics': top_topics_list,
                    'execution_time_seconds': topic_detection_result.execution_time
                })
            
            # Apply detected topics back to ALL conversation objects
            # CRITICAL: Need to apply to BOTH the original list AND the segmented lists
            # because segmentation returns copies, not references!
            
            def apply_topics_to_list(conv_list, topics_map):
                """Helper to apply topics to a list of conversations."""
                applied_count = 0
                for conv in conv_list:
                    conv_id = conv.get('id')
                    if conv_id in topics_map:
                        conv['detected_topics'] = [t['topic'] for t in topics_map[conv_id]]
                        applied_count += 1
                    else:
                        conv['detected_topics'] = []
                return applied_count
            
            # Apply to all lists
            original_applied = apply_topics_to_list(conversations, topics_by_conv)
            free_applied = apply_topics_to_list(free_fin_only_conversations, topics_by_conv)
            paid_applied = apply_topics_to_list(paid_conversations, topics_by_conv)
            paid_fin_applied = apply_topics_to_list(paid_fin_resolved_conversations, topics_by_conv)
            
            self.logger.info(f"   Topics applied: Original={original_applied}, Free={free_applied}, Paid={paid_applied}, PaidFin={paid_fin_applied}")
            
            # ALSO pass topics_by_conversation to metadata for agents that need it
            context.metadata['topics_by_conversation'] = topics_by_conv
            
            # PHASE 2.5: Sub-Topic Detection
            self.logger.info("🔍 Phase 2.5: Sub-Topic Detection")
            subtopics_data = {}
            subtopic_detection_result = None
            subtopic_payload: Optional[SubtopicDetectionResult] = None
            subtopic_start_time = datetime.now()
            try:
                subtopic_context = context.model_copy()
                subtopic_context.previous_results = {
                    'TopicDetectionAgent': _normalize_agent_result(topic_detection_result)
                }
                subtopic_context.conversations = paid_conversations
                
                # Report agent start
                if self.monitor:
                    await self.monitor.update_agent_status('SubTopicDetectionAgent', AgentStatus.RUNNING,
                                                          f"Analyzing {len(topic_dist)} topics for sub-categories")
                
                subtopic_detection_result = await self.subtopic_detection_agent.execute(subtopic_context)
                workflow_results['SubTopicDetectionAgent'] = _normalize_agent_result(subtopic_detection_result)
                
                # Report agent completion
                if self.monitor:
                    await self.monitor.update_agent_status('SubTopicDetectionAgent', AgentStatus.COMPLETED,
                                                          f"Found {len(subtopic_detection_result.data.get('subtopics_by_tier1_topic', {}))} topic hierarchies",
                                                          token_usage={'total': subtopic_detection_result.token_count},
                                                          confidence=subtopic_detection_result.confidence)

                # Record tool calls from agent if audit is enabled
                if self.audit:
                    if hasattr(self.audit, 'record_tool_calls_from_agent'):
                        self.audit.record_tool_calls_from_agent(subtopic_detection_result)

                # Display agent result
                try:
                    display.display_agent_result('SubTopicDetectionAgent', _normalize_agent_result(subtopic_detection_result), show_full_data)
                except Exception as e:
                    logger.warning(f"Failed to display SubTopicDetectionAgent result: {e}")
                
                # Validate and parse subtopic detection result with typed payload
                try:
                    subtopic_payload = SubtopicDetectionResult(**subtopic_detection_result.data)
                    self.logger.debug("✅ SubtopicDetectionResult validation passed")
                    subtopics_data = subtopic_payload.subtopics_by_tier1_topic
                except ValidationError as e:
                    self.logger.warning(f"⚠️ SubtopicDetectionResult validation failed: {e}")
                    subtopics_data = subtopic_detection_result.data.get('subtopics_by_tier1_topic', {})
                
                self.logger.info(f"   ✅ Detected sub-topics for {len(subtopics_data)} Tier 1 topics")
            except Exception as e:
                self.logger.error(f"   ❌ SubTopicDetectionAgent failed: {e}", exc_info=True)
                subtopics_data = {}
                # Record failed result for metrics and visibility
                subtopic_execution_time = (datetime.now() - subtopic_start_time).total_seconds()
                workflow_results['SubTopicDetectionAgent'] = {
                    'agent_name': 'SubTopicDetectionAgent',
                    'success': False,
                    'error_message': str(e),
                    'execution_time': subtopic_execution_time,
                    'confidence': 0.0,
                    'data': {}
                }
            
            # PHASE 2.6: Canny Topic Detection (if Canny posts provided)
            canny_topics_by_category = {}
            if canny_posts:
                self.logger.info("🎯 Phase 2.6: Canny Topic Detection")
                self.logger.info(f"   Mapping {len(canny_posts)} Canny posts to taxonomy")
                canny_topic_start_time = datetime.now()
                try:
                    canny_topics_by_category = await self.canny_topic_detection_agent.detect_topics(
                        canny_posts=canny_posts,
                        taxonomy=None,  # Use default taxonomy
                        ai_model=ai_model,
                        enable_fallback=True
                    )
                    
                    canny_topic_execution_time = (datetime.now() - canny_topic_start_time).total_seconds()
                    workflow_results['CannyTopicDetectionAgent'] = {
                        'agent_name': 'CannyTopicDetectionAgent',
                        'success': True,
                        'execution_time': canny_topic_execution_time,
                        'confidence': 0.8,
                        'data': {
                            'topics_detected': len(canny_topics_by_category),
                            'total_posts': len(canny_posts),
                            'topics_by_category': {
                                topic: data['count'] for topic, data in canny_topics_by_category.items()
                            }
                        }
                    }
                    
                    # Display agent result
                    try:
                        display.display_agent_result('CannyTopicDetectionAgent', workflow_results['CannyTopicDetectionAgent'], show_full_data)
                    except Exception as e:
                        logger.warning(f"Failed to display CannyTopicDetectionAgent result: {e}")
                    
                    self.logger.info(f"   ✅ Detected {len(canny_topics_by_category)} Canny topics")
                    
                except Exception as e:
                    self.logger.error(f"   ❌ CannyTopicDetectionAgent failed: {e}", exc_info=True)
                    canny_topic_execution_time = (datetime.now() - canny_topic_start_time).total_seconds()
                    workflow_results['CannyTopicDetectionAgent'] = {
                        'agent_name': 'CannyTopicDetectionAgent',
                        'success': False,
                        'error_message': str(e),
                        'execution_time': canny_topic_execution_time,
                        'confidence': 0.0,
                        'data': {}
                    }
            else:
                self.logger.info("⏭️  Phase 2.6: Skipping Canny Topic Detection (no Canny posts provided)")
            
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
            
            # Process all topics in parallel for efficiency with concurrency control
            async def process_topic_with_semaphore(
                topic_name: str,
                topic_stats: Dict,
                topic_num: int,
                total_topics: int
            ):
                """
                Process a single topic with sentiment + examples using concurrency control.
                Always returns (topic_name, result, result) or (topic_name, exception, None).
                """
                async with self.topic_semaphore:
                    # Log when topic starts (indicates queueing if delayed)
                    self.logger.info(
                        f"   Processing topic {topic_num}/{total_topics}: {topic_name}"
                    )
                    
                    try:
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
                        
                        self.logger.info(f"   ✅ Completed topic {topic_num}/{total_topics}: {topic_name} - {len(examples_result.data.get('examples', []))} examples")
                        
                        return topic_name, sentiment_result, examples_result
                    except Exception as e:
                        # Wrap exception to preserve topic_name
                        self.logger.error(f"   ❌ {topic_name}: Processing failed - {e}", exc_info=True)
                        return topic_name, e, None
            
            # Process all topics in parallel (skip zero-volume topics) with concurrency control
            self.logger.info(f"   Processing {len(topic_dist)} topics in parallel (max {self.topic_semaphore._value} concurrent)...")
            topic_tasks = []
            topic_num = 0
            for name, stats in topic_dist.items():
                volume = stats.get('volume', 0)
                if volume == 0:
                    self.logger.info(f"   ⏭️  Skipping topic '{name}': zero volume (LLM-discovered with no matches)")
                    continue
                topic_num += 1
                topic_tasks.append(process_topic_with_semaphore(name, stats, topic_num, len(topic_dist)))
            
            self.logger.info(f"   Created {len(topic_tasks)} topic processing tasks (concurrency limit: {self.topic_semaphore._value})")
            topic_results = await asyncio.gather(*topic_tasks)
            
            # Initialize per-topic tracking
            if 'TopicProcessing' not in workflow_results:
                workflow_results['TopicProcessing'] = {}
            
            # Collect results with per-topic error handling
            # Note: process_topic now always returns (topic_name, sentiment_result, examples_result)
            # even on exceptions, where sentiment_result is the exception and examples_result is None
            for result in topic_results:
                # Unpack result - topic_name is always first element
                result_topic_name, sentiment_result, examples_result = result
                
                # Check if sentiment_result is an exception
                if isinstance(sentiment_result, Exception):
                    error_msg = str(sentiment_result)
                    self.logger.error(f"Topic '{result_topic_name}' processing failed: {error_msg}", exc_info=sentiment_result)
                    # Add structured error entry
                    workflow_results['TopicProcessing'][result_topic_name] = {
                        'success': False,
                        'error_message': error_msg,
                        'error_type': type(sentiment_result).__name__
                    }
                    continue
                
                # Skip if topic was empty (both None)
                if sentiment_result is None and examples_result is None:
                    workflow_results['TopicProcessing'][result_topic_name] = {
                        'success': False,
                        'error_message': 'Empty topic - no conversations matched'
                    }
                    continue
                
                # Success case
                topic_sentiments[result_topic_name] = _normalize_agent_result(sentiment_result)
                topic_examples[result_topic_name] = _normalize_agent_result(examples_result)
                workflow_results['TopicProcessing'][result_topic_name] = {
                    'success': True,
                    'sentiment_confidence': sentiment_result.confidence,
                    'examples_count': len(examples_result.data.get('examples', []))
                }
            
            # PHASE 4: Fin Analysis (on free and paid fin-resolved conversations)
            self.logger.info("🤖 Phase 4: Fin AI Performance Analysis")
            
            if self.audit:
                self.audit.step(
                    "Phase 4: Fin Analysis",
                    f"Starting Fin AI performance evaluation on {len(free_fin_only_conversations) + len(paid_fin_resolved_conversations)} conversations",
                    {
                        'free_tier_conversations': len(free_fin_only_conversations),
                        'paid_tier_conversations': len(paid_fin_resolved_conversations),
                        'total_fin_conversations': len(free_fin_only_conversations) + len(paid_fin_resolved_conversations)
                    }
                )
            
            fin_start_time = datetime.now()
            fin_context = context.model_copy()
            fin_context.metadata = {
                'free_fin_conversations': free_fin_only_conversations,
                'paid_fin_conversations': paid_fin_resolved_conversations,
                'week_id': week_id,
                'subtopics_by_tier1_topic': subtopics_data
            }
            # Pass sub-topic data via previous_results for compatibility
            fin_context.previous_results = {
                'SubTopicDetectionAgent': _normalize_agent_result(subtopic_detection_result) if subtopic_detection_result and (subtopic_detection_result.success if hasattr(subtopic_detection_result, 'success') else _normalize_agent_result(subtopic_detection_result).get('success', False)) else {},
                'TopicDetectionAgent': _normalize_agent_result(topic_detection_result)
            }
            # Report agent start
            if self.monitor:
                await self.monitor.update_agent_status('FinPerformanceAgent', AgentStatus.RUNNING,
                                                      f"Analyzing Fin AI performance")
            
            fin_result = await self.fin_performance_agent.execute(fin_context)
            workflow_results['FinPerformanceAgent'] = _normalize_agent_result(fin_result)
            
            # Report agent completion
            if self.monitor:
                await self.monitor.update_agent_status('FinPerformanceAgent', AgentStatus.COMPLETED,
                                                      "Fin performance analysis complete",
                                                      confidence=fin_result.confidence)
            
            fin_execution_time = (datetime.now() - fin_start_time).total_seconds()
            
            # Validate and parse Fin analysis result with typed payload
            fin_payload: Optional[FinAnalysisPayload] = None
            try:
                fin_payload = FinAnalysisPayload(**fin_result.data)
                self.logger.debug("✅ FinAnalysisPayload validation passed")
            except ValidationError as e:
                self.logger.warning(f"⚠️ FinAnalysisPayload validation failed: {e}")
            
            if self.audit:
                fin_data = _normalize_agent_result(fin_result).get('data', {})
                self.audit.step(
                    "Phase 4: Fin Analysis",
                    f"Completed Fin AI performance evaluation in {fin_execution_time:.1f}s",
                    {
                        'execution_time_seconds': fin_execution_time,
                        'total_analyzed': fin_data.get('total_fin_conversations', 0),
                        'free_tier_resolution_rate': fin_data.get('free_tier', {}).get('resolution_rate', 0),
                        'paid_tier_resolution_rate': fin_data.get('paid_tier', {}).get('resolution_rate', 0),
                        'success': fin_result.success if hasattr(fin_result, 'success') else True,
                        'payload_validation': 'passed' if fin_payload else 'failed'
                    }
                )
            
            # Display agent result
            try:
                display.display_agent_result('FinPerformanceAgent', _normalize_agent_result(fin_result), show_full_data)
            except Exception as e:
                logger.warning(f"Failed to display FinPerformanceAgent result: {e}")

            self.logger.info(f"   ✅ Fin analysis complete")
            
            # PHASE 4.5: Analytical Insights
            self.logger.info("🔍 Phase 4.5: Analytical Insights (Correlation, Quality, Churn Risk, Confidence)")
            
            if self.audit:
                self.audit.step(
                    "Phase 4.5: Analytical Insights",
                    "Starting pattern detection and quality analysis",
                    {
                        'agents': ['CorrelationAgent', 'QualityInsightsAgent', 'ChurnRiskAgent', 'ConfidenceMetaAgent'],
                        'total_conversations': len(conversations)
                    }
                )
            
            analytical_start_time = datetime.now()
            analytical_insights = {}
            
            try:
                # Build analytical context with all necessary data
                analytical_context = context.model_copy()
                analytical_context.conversations = conversations
                analytical_context.previous_results = {
                    'SegmentationAgent': _normalize_agent_result(segmentation_result),
                    'TopicDetectionAgent': _normalize_agent_result(topic_detection_result),
                    'TopicSentiments': topic_sentiments,
                    'TopicExamples': topic_examples,
                    'FinPerformanceAgent': _normalize_agent_result(fin_result)
                }
                analytical_context.metadata = {
                    'week_id': week_id,
                    'topics_by_conversation': topics_by_conv,
                    'historical_context': self.historical_snapshot_service.get_historical_context() if self.historical_snapshot_service else {'weeks_available': 0}
                }
                
                # Pass AI client to agents for LLM enrichment
                from src.services.ai_model_factory import AIModel
                ai_model_enum = AIModel.OPENAI_GPT4 if ai_model == 'openai' else AIModel.ANTHROPIC_CLAUDE
                client = self.ai_factory.get_client(ai_model_enum)
                self.correlation_agent.ai_client = client
                self.quality_insights_agent.ai_client = client
                self.churn_risk_agent.ai_client = client
                self.confidence_meta_agent.ai_client = client
                
                # Run 4 agents in parallel using asyncio.gather()
                correlation_result, quality_result, churn_result, confidence_result = await asyncio.gather(
                    self.correlation_agent.execute(analytical_context),
                    self.quality_insights_agent.execute(analytical_context),
                    self.churn_risk_agent.execute(analytical_context),
                    self.confidence_meta_agent.execute(analytical_context),
                    return_exceptions=True
                )
                
                # Handle exceptions from gather
                if isinstance(correlation_result, Exception):
                    self.logger.error(f"CorrelationAgent failed: {correlation_result}")
                    correlation_result = type('ErrorResult', (), {'success': False, 'data': {'error': str(correlation_result)}, 'confidence': 0.0})()
                
                if isinstance(quality_result, Exception):
                    self.logger.error(f"QualityInsightsAgent failed: {quality_result}")
                    quality_result = type('ErrorResult', (), {'success': False, 'data': {'error': str(quality_result)}, 'confidence': 0.0})()
                
                if isinstance(churn_result, Exception):
                    self.logger.error(f"ChurnRiskAgent failed: {churn_result}")
                    churn_result = type('ErrorResult', (), {'success': False, 'data': {'error': str(churn_result)}, 'confidence': 0.0})()
                
                if isinstance(confidence_result, Exception):
                    self.logger.error(f"ConfidenceMetaAgent failed: {confidence_result}")
                    confidence_result = type('ErrorResult', (), {'success': False, 'data': {'error': str(confidence_result)}, 'confidence': 0.0})()
                
                # Store results in workflow_results
                workflow_results['CorrelationAgent'] = _normalize_agent_result(correlation_result)
                workflow_results['QualityInsightsAgent'] = _normalize_agent_result(quality_result)
                workflow_results['ChurnRiskAgent'] = _normalize_agent_result(churn_result)
                workflow_results['ConfidenceMetaAgent'] = _normalize_agent_result(confidence_result)
                
                # Combine into AnalyticalInsights dict
                analytical_insights = {
                    'CorrelationAgent': _normalize_agent_result(correlation_result),
                    'QualityInsightsAgent': _normalize_agent_result(quality_result),
                    'ChurnRiskAgent': _normalize_agent_result(churn_result),
                    'ConfidenceMetaAgent': _normalize_agent_result(confidence_result)
                }
                
                # Display agent results
                for agent_name in ['CorrelationAgent', 'QualityInsightsAgent', 'ChurnRiskAgent', 'ConfidenceMetaAgent']:
                    try:
                        display.display_agent_result(agent_name, workflow_results[agent_name], show_full_data)
                    except Exception as e:
                        logger.warning(f"Failed to display {agent_name} result: {e}")
                
                # Calculate phase execution time
                analytical_execution_time = (datetime.now() - analytical_start_time).total_seconds()
                
                # Extract metrics for summary
                correlations_count = workflow_results['CorrelationAgent'].get('data', {}).get('total_correlations_found', 0)
                churn_signals_count = workflow_results['ChurnRiskAgent'].get('data', {}).get('risk_breakdown', {}).get('total_risk_signals', 0)
                anomalies_count = len(workflow_results['QualityInsightsAgent'].get('data', {}).get('anomalies', []))
                overall_confidence = workflow_results['ConfidenceMetaAgent'].get('data', {}).get('overall_data_quality_score', 0)
                
                # Add audit step for completion
                if self.audit:
                    self.audit.step(
                        "Phase 4.5: Analytical Insights",
                        f"Completed analytical insights in {analytical_execution_time:.1f}s",
                        {
                            'execution_time_seconds': analytical_execution_time,
                            'correlations_found': correlations_count,
                            'churn_signals': churn_signals_count,
                            'anomalies_detected': anomalies_count,
                            'overall_confidence': overall_confidence
                        }
                    )
                
                self.logger.info(f"   ✅ Analytical insights complete: {correlations_count} correlations, {churn_signals_count} churn signals, {anomalies_count} anomalies")
                
            except Exception as e:
                self.logger.error(f"Phase 4.5 failed: {e}", exc_info=True)
                analytical_execution_time = (datetime.now() - analytical_start_time).total_seconds()
                
                # Create error results for all agents
                for agent_name in ['CorrelationAgent', 'QualityInsightsAgent', 'ChurnRiskAgent', 'ConfidenceMetaAgent']:
                    workflow_results[agent_name] = {
                        'agent_name': agent_name,
                        'success': False,
                        'error_message': str(e),
                        'execution_time': analytical_execution_time / 4,
                        'confidence': 0.0,
                        'data': {}
                    }
                
                analytical_insights = {agent: workflow_results[agent] for agent in ['CorrelationAgent', 'QualityInsightsAgent', 'ChurnRiskAgent', 'ConfidenceMetaAgent']}
            
            # PHASE 4.6: Cross-Platform Correlation (if Canny posts provided)
            cross_platform_insights = {}
            if canny_posts and canny_topics_by_category:
                self.logger.info("🔗 Phase 4.6: Cross-Platform Correlation Analysis")
                self.logger.info(f"   Analyzing correlations between Intercom ({len(conversations)}) and Canny ({len(canny_posts)})")
                correlation_start_time = datetime.now()
                try:
                    correlation_results = await self.cross_platform_correlation_agent.analyze_correlations(
                        intercom_conversations=paid_conversations,  # Use paid conversations for correlation
                        canny_posts=canny_posts,
                        ai_model=ai_model,
                        enable_fallback=True
                    )
                    
                    correlation_execution_time = (datetime.now() - correlation_start_time).total_seconds()
                    workflow_results['CrossPlatformCorrelationAgent'] = {
                        'agent_name': 'CrossPlatformCorrelationAgent',
                        'success': True,
                        'execution_time': correlation_execution_time,
                        'confidence': 0.85,
                        'data': {
                            'correlations_found': correlation_results.get('correlation_count', 0),
                            'intercom_topics': correlation_results.get('intercom_topic_count', 0),
                            'canny_topics': correlation_results.get('canny_topic_count', 0),
                            'unified_priorities': correlation_results.get('unified_priorities', []),
                            'insights': correlation_results.get('insights', [])
                        }
                    }
                    
                    # Display agent result
                    try:
                        display.display_agent_result('CrossPlatformCorrelationAgent', workflow_results['CrossPlatformCorrelationAgent'], show_full_data)
                    except Exception as e:
                        logger.warning(f"Failed to display CrossPlatformCorrelationAgent result: {e}")
                    
                    # Store insights for final output
                    cross_platform_insights = correlation_results
                    
                    self.logger.info(f"   ✅ Found {correlation_results.get('correlation_count', 0)} cross-platform correlations")
                    
                except Exception as e:
                    self.logger.error(f"   ❌ CrossPlatformCorrelationAgent failed: {e}", exc_info=True)
                    correlation_execution_time = (datetime.now() - correlation_start_time).total_seconds()
                    workflow_results['CrossPlatformCorrelationAgent'] = {
                        'agent_name': 'CrossPlatformCorrelationAgent',
                        'success': False,
                        'error_message': str(e),
                        'execution_time': correlation_execution_time,
                        'confidence': 0.0,
                        'data': {}
                    }
            else:
                if not canny_posts:
                    self.logger.info("⏭️  Phase 4.6: Skipping Cross-Platform Correlation (no Canny posts)")
                else:
                    self.logger.info("⏭️  Phase 4.6: Skipping Cross-Platform Correlation (Canny topic detection failed)")
            
            # PHASE 5: Trend Analysis
            self.logger.info("📈 Phase 5: Trend Analysis")
            
            if self.audit:
                self.audit.step(
                    "Phase 5: Trend Analysis",
                    "Starting historical trend analysis",
                    {
                        'current_week': week_id,
                        'topics_to_analyze': len(topic_dist)
                    }
                )
            
            trend_start_time = datetime.now()
            trend_context = context.model_copy()
            trend_context.metadata = {
                'current_week_results': {
                    'topic_distribution': topic_dist,
                    'topic_sentiments': {k: v['data'] for k, v in topic_sentiments.items()}
                },
                'week_id': week_id
            }
            trend_result = await self.trend_agent.execute(trend_context)
            workflow_results['TrendAgent'] = _normalize_agent_result(trend_result)
            
            trend_execution_time = (datetime.now() - trend_start_time).total_seconds()
            
            # Validate and parse trend analysis result with typed payload
            trend_payload: Optional[TrendAnalysisPayload] = None
            try:
                trend_payload = TrendAnalysisPayload(**trend_result.data)
                self.logger.debug("✅ TrendAnalysisPayload validation passed")
            except ValidationError as e:
                self.logger.warning(f"⚠️ TrendAnalysisPayload validation failed: {e}")
            
            if self.audit:
                trend_data = _normalize_agent_result(trend_result).get('data', {})
                self.audit.step(
                    "Phase 5: Trend Analysis",
                    f"Completed trend analysis in {trend_execution_time:.1f}s",
                    {
                        'execution_time_seconds': trend_execution_time,
                        'trends_identified': len(trend_data.get('trends', [])),
                        'success': trend_result.success if hasattr(trend_result, 'success') else True,
                        'payload_validation': 'passed' if trend_payload else 'failed'
                    }
                )
            
            # Display agent result
            try:
                display.display_agent_result('TrendAgent', _normalize_agent_result(trend_result), show_full_data)
            except Exception as e:
                logger.warning(f"Failed to display TrendAgent result: {e}")
            
            self.logger.info(f"   ✅ Trend analysis complete")
            
            # PHASE 6: Format Output
            self.logger.info("📝 Phase 6: Output Formatting")
            
            if self.audit:
                self.audit.step(
                    "Phase 6: Output Formatting",
                    "Starting final output formatting",
                    {
                        'agents_completed': len(workflow_results),
                        'topics_processed': len(topic_dist)
                    }
                )
            
            output_start_time = datetime.now()
            output_context = context.model_copy()
            # Ensure OutputFormatterAgent receives full conversation set
            output_context.conversations = conversations
            output_context.previous_results = {
                'SegmentationAgent': _normalize_agent_result(segmentation_result),
                'TopicDetectionAgent': _normalize_agent_result(topic_detection_result),
                'SubTopicDetectionAgent': _normalize_agent_result(subtopic_detection_result) if subtopic_detection_result and (subtopic_detection_result.success if hasattr(subtopic_detection_result, 'success') else _normalize_agent_result(subtopic_detection_result).get('success', False)) else {},
                'TopicSentiments': topic_sentiments,  # Already normalized dicts
                'TopicExamples': topic_examples,  # Already normalized dicts
                'FinPerformanceAgent': _normalize_agent_result(fin_result),
                'TrendAgent': _normalize_agent_result(trend_result),
                'AnalyticalInsights': analytical_insights  # Phase 4.5 results
            }
            # Get historical context for "What We Cannot Determine" section
            historical_context = {'weeks_available': 0}
            if self.historical_snapshot_service:
                try:
                    historical_context = self.historical_snapshot_service.get_historical_context()
                except Exception as e:
                    self.logger.warning(f"Error getting historical context: {e}")
            
            # Get comparison data if prior snapshot exists
            comparison_data = None
            if self.historical_snapshot_service and context.metadata.get('snapshot_id'):
                try:
                    snapshot_id = context.metadata['snapshot_id']
                    prior_snapshot = self.historical_snapshot_service.get_prior_snapshot(snapshot_id, period_type)
                    if prior_snapshot:
                        current_snapshot_data = {
                            'topic_distribution': topic_dist,
                            'segmentation_summary': segmentation_result.data if segmentation_result and segmentation_result.success else {}
                        }
                        comparison_data = self.historical_snapshot_service.calculate_comparison(current_snapshot_data, prior_snapshot)
                except Exception as e:
                    self.logger.warning(f"Error getting comparison data: {e}")
            
            output_context.metadata = {
                'week_id': week_id,
                'period_type': period_type,
                'period_label': period_label,
                'historical_context': historical_context,
                'comparison_data': comparison_data
            }
            
            # Report agent start
            if self.monitor:
                await self.monitor.update_agent_status('OutputFormatterAgent', AgentStatus.RUNNING,
                                                      "Formatting analysis for Gamma presentation")
            
            formatter_result = await self.output_formatter_agent.execute(output_context)
            workflow_results['OutputFormatterAgent'] = _normalize_agent_result(formatter_result)
            
            # 📋 SAVE AGENT DEBUG REPORT (Human-Readable Summary of All Agent Outputs)
            try:
                from src.utils.agent_debug_reporter import create_agent_debug_report
                from pathlib import Path
                import os
                
                # Get output directory (respects persistent volume if available)
                volume_path = os.getenv('RAILWAY_VOLUME_MOUNT_PATH')
                if volume_path:
                    debug_report_path = Path(volume_path) / "outputs" / f"agent_debug_report_{week_id}.txt"
                else:
                    from src.config.settings import settings
                    debug_report_path = Path(settings.effective_output_directory) / f"agent_debug_report_{week_id}.txt"
                
                # Create debug report showing ALL agent outputs
                create_agent_debug_report(workflow_results, debug_report_path)
                self.logger.info(f"📋 Agent debug report saved: {debug_report_path}")
                
            except Exception as e:
                self.logger.warning(f"Failed to create agent debug report: {e}")
            
            # Report agent completion
            if self.monitor:
                await self.monitor.update_agent_status('OutputFormatterAgent', AgentStatus.COMPLETED,
                                                      "Formatted output ready",
                                                      confidence=formatter_result.confidence)
            
            output_execution_time = (datetime.now() - output_start_time).total_seconds()
            
            if self.audit:
                self.audit.step(
                    "Phase 6: Output Formatting",
                    f"Completed output formatting in {output_execution_time:.1f}s",
                    {
                        'execution_time_seconds': output_execution_time,
                        'success': formatter_result.success if hasattr(formatter_result, 'success') else True
                    }
                )
            
            # Display agent result
            try:
                display.display_agent_result('OutputFormatterAgent', _normalize_agent_result(formatter_result), show_full_data)
            except Exception as e:
                logger.warning(f"Failed to display OutputFormatterAgent result: {e}")
            
            self.logger.info(f"   ✅ Output formatted")
            
            # Calculate summary and aggregate metrics
            total_time = (datetime.now() - start_time).total_seconds()
            
            # Aggregate metrics from all agents
            metrics = self._aggregate_metrics(workflow_results, topic_sentiments, topic_examples, total_time)
            
            final_output = {
                'week_id': week_id,
                'period_type': period_type,
                'period_label': period_label,
                'period_start': context.period_start if hasattr(context, 'period_start') else None,
                'period_end': context.period_end if hasattr(context, 'period_end') else None,
                'formatted_report': formatter_result.data.get('formatted_output', ''),
                'summary': {
                    'total_conversations': len(conversations),
                    'paid_conversations': len(paid_conversations),
                    'paid_human_conversations': len(paid_conversations) - len(paid_fin_resolved_conversations),
                    'paid_fin_resolved_conversations': len(paid_fin_resolved_conversations),
                    'free_fin_only_conversations': len(free_fin_only_conversations),
                    'topics_analyzed': len(topic_dist),
                    'subtopics_analyzed': len(subtopics_data) if 'subtopics_data' in locals() else 0,
                    'total_execution_time': total_time,
                    'agents_completed': len(workflow_results)
                },
                'metrics': metrics,
                'agent_results': workflow_results
            }
            
            # PHASE 6.5: Auto-save analysis snapshot (async to prevent blocking)
            self.logger.info("💾 Phase 6.5: Auto-saving analysis snapshot...")
            snapshot_id = None
            try:
                if self.historical_snapshot_service is not None:
                    # Use async method to prevent blocking event loop during DuckDB operations
                    snapshot_id = await self.historical_snapshot_service.save_snapshot_async(final_output, period_type)
                    self.logger.info(f"   ✅ Snapshot saved: {snapshot_id}")
                    
                    # Add to audit trail if enabled
                    if self.audit:
                        self.audit.step(
                            "Phase 6.5: Snapshot Auto-Save",
                            f"Saved analysis snapshot: {snapshot_id}",
                            {'snapshot_id': snapshot_id, 'analysis_type': period_type}
                        )
                else:
                    self.logger.warning("   ⚠️ Historical snapshot service not available")
            except Exception as e:
                self.logger.warning(f"   ⚠️ Failed to auto-save snapshot: {e}")
                # Continue execution - snapshot failure is non-critical
            
            # Add snapshot_id to final_output
            if snapshot_id:
                final_output['snapshot_id'] = snapshot_id
            
            # Display summary table of all agent results
            if config.get_visibility_setting('show_agent_summary_table', True):
                try:
                    display.display_all_agent_results(workflow_results, f"Analysis Complete - {week_id}")
                except Exception as e:
                    logger.warning(f"Failed to display all agent results: {e}")
            
            # Display markdown preview if enabled
            if config.get_visibility_setting('show_markdown_preview', True):
                try:
                    formatted_report = formatter_result.data.get('formatted_output', '') if hasattr(formatter_result, 'data') else _normalize_agent_result(formatter_result).get('data', {}).get('formatted_output', '')
                    max_lines = config.get_visibility_setting('markdown_preview_max_lines', 50)
                    display.display_markdown_preview(
                        formatted_report,
                        title=f"Formatted Report - {period_label or week_id}",
                        max_lines=max_lines
                    )
                except Exception as e:
                    logger.warning(f"Failed to display markdown preview: {e}")
            
            self.logger.info(f"🎉 TopicOrchestrator: Complete in {total_time:.1f}s")
            self.logger.info(f"   Topics: {len(topic_dist)}, Paid: {len(paid_conversations)}, Free: {len(free_fin_only_conversations)}")
            
            # Save audit report at completion
            if self.audit:
                try:
                    audit_path = self.audit.save_report()
                    self.logger.info(f"📋 Audit trail saved to: {audit_path}")
                except Exception as e:
                    self.logger.warning(f"Failed to save audit report: {e}")
            
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
        
        # Aggregate sub-topic statistics if available
        if 'SubTopicDetectionAgent' in workflow_results:
            subtopic_result = workflow_results['SubTopicDetectionAgent']
            if subtopic_result.get('success', False):
                subtopics_by_tier1 = subtopic_result.get('data', {}).get('subtopics_by_tier1_topic', {})
                
                total_tier2 = 0
                total_tier3 = 0
                for topic_name, topic_data in subtopics_by_tier1.items():
                    tier2_subtopics = topic_data.get('tier2', {})
                    tier3_themes = topic_data.get('tier3', {})
                    total_tier2 += len(tier2_subtopics)
                    total_tier3 += len(tier3_themes)
                
                metrics['subtopic_stats'] = {
                    'tier1_topics_analyzed': len(subtopics_by_tier1),
                    'tier2_subtopics_found': total_tier2,
                    'tier3_themes_discovered': total_tier3
                }
        
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
            'subtopic_detection': metrics['agent_timings'].get('SubTopicDetectionAgent', {}).get('execution_time', 0),
            'per_topic_analysis': sum(m['total_time'] for m in metrics['per_topic_metrics'].values()),
            'fin_analysis': metrics['agent_timings'].get('FinPerformanceAgent', {}).get('execution_time', 0),
            'analytical_insights': (
                metrics['agent_timings'].get('CorrelationAgent', {}).get('execution_time', 0) +
                metrics['agent_timings'].get('QualityInsightsAgent', {}).get('execution_time', 0) +
                metrics['agent_timings'].get('ChurnRiskAgent', {}).get('execution_time', 0) +
                metrics['agent_timings'].get('ConfidenceMetaAgent', {}).get('execution_time', 0)
            ),
            'trend_analysis': metrics['agent_timings'].get('TrendAgent', {}).get('execution_time', 0),
            'output_formatting': metrics['agent_timings'].get('OutputFormatterAgent', {}).get('execution_time', 0)
        }
        
        self.logger.info(f"📊 Metrics Summary:")
        self.logger.info(f"   Total LLM calls: {metrics['llm_stats']['total_calls']}")
        self.logger.info(f"   Total tokens: {metrics['llm_stats']['total_tokens']}")
        self.logger.info(f"   Topics processed: {metrics['overall_stats']['topics_processed']}")
        self.logger.info(f"   Examples selected: {metrics['overall_stats']['examples_selected']}")
        self.logger.info(f"   Errors: {metrics['overall_stats']['errors']}")
        
        # Log sub-topic stats if available
        if 'subtopic_stats' in metrics:
            self.logger.info(f"   Sub-topics: Tier 2={metrics['subtopic_stats']['tier2_subtopics_found']}, Tier 3={metrics['subtopic_stats']['tier3_themes_discovered']}")
        
        return metrics

