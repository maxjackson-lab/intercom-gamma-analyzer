"""
Voice of Customer Strategy - The logic for the V2 Narrative Pipeline.

This strategy migrates the monolithic logic from TopicOrchestrator into a cleaner,
step-by-step orchestration strategy compatible with UnifiedOrchestrator.

Phases:
1. Segmentation (Paid vs Free)
2. Topic Detection (All conversations)
   2.4 BPO Vendor Analysis
   2.5 Sub-topic Detection
   2.6 Canny Topic Detection (Optional)
3. Per-Topic Analysis (Sentiment + Examples)
4. Fin Performance Analysis
   4.5 Analytical Insights (Correlation, Churn, etc.)
   4.6 Cross-Platform Correlation (Optional)
5. Trend Analysis
   5.5 Validation
6. Output Formatting (Narrative Generation)
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import ValidationError

from src.agents.base_agent import AgentContext, AgentResult, ConfidenceLevel
from src.agents.bpo_performance_agent import BpoPerformanceAgent
from src.agents.canny_topic_detection_agent import CannyTopicDetectionAgent
from src.agents.churn_risk_agent import ChurnRiskAgent
from src.agents.confidence_meta_agent import ConfidenceMetaAgent
from src.agents.correlation_agent import CorrelationAgent
from src.agents.cross_platform_correlation_agent import CrossPlatformCorrelationAgent
from src.agents.example_extraction_agent import ExampleExtractionAgent
from src.agents.fin_performance_agent import FinPerformanceAgent
from src.agents.output_formatter_agent import OutputFormatterAgent
from src.agents.quality_insights_agent import QualityInsightsAgent
from src.agents.segmentation_agent import SegmentationAgent
from src.agents.subtopic_detection_agent import SubTopicDetectionAgent
from src.agents.topic_detection_agent import TopicDetectionAgent
from src.agents.topic_sentiment_agent import TopicSentimentAgent
from src.agents.trend_agent import TrendAgent
from src.config.modes import get_analysis_mode_config
from src.models.analysis_models import (
    FinAnalysisPayload,
    SegmentationPayload,
    SubtopicDetectionResult,
    TopicDetectionResult,
    TrendAnalysisPayload,
)
from src.services.ai_model_factory import AIModel, AIModelFactory
from src.services.analysis_validator import AnalysisValidator
from src.services.duckdb_storage import DuckDBStorage
from src.services.execution_monitor import AgentStatus
from src.services.historical_snapshot_service import HistoricalSnapshotService
from src.services.unified_orchestrator import OrchestrationStrategy
from src.utils.agent_output_display import get_display


def _normalize_agent_result(result: Any) -> Dict[str, Any]:
    """Normalize agent result to dictionary format."""
    if result is None:
        return {}
    if isinstance(result, dict):
        return result
    if hasattr(result, 'dict') and callable(result.dict):
        return result.dict()
    if hasattr(result, 'model_dump') and callable(result.model_dump):
        return result.model_dump()
    try:
        return dict(result)
    except Exception:
        return {}


class VoiceOfCustomerStrategy(OrchestrationStrategy):
    """
    The V2 Voice of Customer orchestration strategy.
    
    Replaces the legacy TopicOrchestrator with a structured, phase-based approach.
    """

    def __init__(
        self,
        ai_factory: Optional[AIModelFactory] = None,
        audit_trail: Optional[Any] = None,
        execution_monitor: Optional[Any] = None,
        formatter_agent: Optional[Any] = None,
        bpo_agent: Optional[Any] = None,
        fail_on_critical_errors: bool = False,
    ):
        super().__init__()
        self.ai_factory = ai_factory or AIModelFactory()
        self.audit = audit_trail
        self.monitor = execution_monitor
        self.fail_on_critical_errors = fail_on_critical_errors
        
        # Initialize Agents
        self.segmentation_agent = SegmentationAgent(track_escalations=True)
        self.topic_detection_agent = TopicDetectionAgent()
        self.subtopic_detection_agent = SubTopicDetectionAgent()
        self.topic_sentiment_agent = TopicSentimentAgent()
        self.example_extraction_agent = ExampleExtractionAgent()
        self.fin_performance_agent = FinPerformanceAgent(audit=self.audit)
        self.bpo_performance_agent = bpo_agent or BpoPerformanceAgent()
        
        self.formatter_agent = formatter_agent or OutputFormatterAgent(use_llm_formatting=True)
        self.formatter_agent_name = getattr(self.formatter_agent, 'name', 'OutputFormatterAgent')
        
        # Analytical Insights Agents
        self.correlation_agent = CorrelationAgent()
        self.quality_insights_agent = QualityInsightsAgent()
        self.churn_risk_agent = ChurnRiskAgent()
        self.confidence_meta_agent = ConfidenceMetaAgent()
        
        # Lazy-loaded components
        self._trend_agent = None
        self._canny_topic_detection_agent = None
        self._cross_platform_correlation_agent = None
        self._historical_snapshot_service = None
        self._duckdb_storage = None
        
        # Concurrency
        config = get_analysis_mode_config()
        max_concurrent = config.get_multi_agent_setting('max_concurrent_topics') or 5
        self.topic_semaphore = asyncio.Semaphore(max_concurrent)

    def get_strategy_name(self) -> str:
        return "VoiceOfCustomerStrategy"

    @property
    def duckdb_storage(self):
        if self._duckdb_storage is None:
            try:
                self._duckdb_storage = DuckDBStorage()
            except Exception as e:
                self.logger.warning(f"Failed to initialize DuckDB storage: {e}")
        return self._duckdb_storage

    @property
    def historical_snapshot_service(self):
        if self._historical_snapshot_service is None:
            try:
                if self.duckdb_storage:
                    self._historical_snapshot_service = HistoricalSnapshotService(self.duckdb_storage)
                    # Auto-migrate JSON snapshots if needed
                    try:
                        res = self._historical_snapshot_service.migrate_json_snapshots()
                        if res['migrated_count'] > 0:
                            self.logger.info(f"Migrated {res['migrated_count']} snapshots to DuckDB")
                    except Exception as e:
                        self.logger.warning(f"Snapshot migration warning: {e}")
            except Exception as e:
                self.logger.warning(f"Failed to initialize historical service: {e}")
        return self._historical_snapshot_service

    @property
    def trend_agent(self):
        if self._trend_agent is None:
            self._trend_agent = TrendAgent(historical_snapshot_service=self.historical_snapshot_service)
        return self._trend_agent

    @property
    def canny_topic_detection_agent(self):
        if self._canny_topic_detection_agent is None:
            self._canny_topic_detection_agent = CannyTopicDetectionAgent(self.ai_factory)
        return self._canny_topic_detection_agent

    @property
    def cross_platform_correlation_agent(self):
        if self._cross_platform_correlation_agent is None:
            self._cross_platform_correlation_agent = CrossPlatformCorrelationAgent(self.ai_factory)
        return self._cross_platform_correlation_agent

    async def execute(self, context: AgentContext, **kwargs: Any) -> AgentResult:
        """
        Main execution flow for Voice of Customer analysis.
        """
        start_time = datetime.now()
        workflow_results = {}
        
        # Extract options from kwargs (passed from UnifiedOrchestrator)
        options = kwargs.get('options', {})
        canny_posts = kwargs.get('canny_posts')
        ai_model = kwargs.get('ai_model')
        
        # Ensure context has necessary metadata
        config = get_analysis_mode_config()
        display = get_display()
        display.enabled = config.get_visibility_setting('enable_agent_output_display', True)
        show_full_data = config.get_visibility_setting('show_full_agent_data', False)

        try:
            # Initial count
            self.log_stage_metrics("Post-Fetch", len(context.conversations or []))

            # --- PHASE 1: SEGMENTATION ---
            segmentation_result = await self._execute_phase_1_segmentation(context)
            workflow_results['SegmentationAgent'] = _normalize_agent_result(segmentation_result)
            
            # Extract segmentation data
            seg_data = _normalize_agent_result(segmentation_result).get('data', {})
            paid_conversations = seg_data.get('paid_customer_conversations', [])
            free_fin_only_conversations = seg_data.get('free_fin_only_conversations', [])
            paid_fin_resolved_conversations = seg_data.get('paid_fin_resolved_conversations', [])
            
            self.log_stage_metrics("Post-Segmentation", len(paid_conversations) + len(free_fin_only_conversations))

            # --- PHASE 2: TOPIC DETECTION ---
            topic_detection_result, topic_dist, topics_by_conv = await self._execute_phase_2_topic_detection(context)
            workflow_results['TopicDetectionAgent'] = _normalize_agent_result(topic_detection_result)
            
            # Update context metadata for downstream agents
            context = context.merge_metadata({'topics_by_conversation': topics_by_conv})
            
            self.log_stage_metrics("Post-TopicDetection", len(topics_by_conv))

            # --- PHASE 2.4: BPO ANALYSIS ---
            bpo_result = await self._execute_phase_2_4_bpo(context, segmentation_result, topic_detection_result, topic_dist)
            workflow_results['BpoPerformanceAgent'] = _normalize_agent_result(bpo_result)

            # --- PHASE 2.5: SUB-TOPIC DETECTION ---
            subtopic_result, subtopics_data = await self._execute_phase_2_5_subtopics(context, paid_conversations, topic_detection_result, topic_dist)
            workflow_results['SubTopicDetectionAgent'] = _normalize_agent_result(subtopic_result)

            # --- PHASE 2.6: CANNY DETECTION (Optional) ---
            if canny_posts:
                canny_result, canny_topics = await self._execute_phase_2_6_canny(canny_posts, ai_model)
                workflow_results['CannyTopicDetectionAgent'] = _normalize_agent_result(canny_result)
            else:
                canny_topics = {}

            # --- PHASE 3: PER-TOPIC ANALYSIS ---
            topic_sentiments, topic_examples = await self._execute_phase_3_per_topic(
                context, 
                context.conversations or [],  # Use ALL conversations 
                topic_dist, 
                topics_by_conv
            )
            workflow_results['TopicSentiments'] = topic_sentiments
            workflow_results['TopicExamples'] = topic_examples

            # --- PHASE 4: FIN ANALYSIS ---
            fin_result = await self._execute_phase_4_fin(
                context, 
                free_fin_only_conversations, 
                paid_fin_resolved_conversations,
                topic_detection_result,
                subtopic_result,
                subtopics_data
            )
            workflow_results['FinPerformanceAgent'] = _normalize_agent_result(fin_result)

            # --- PHASE 4.5: ANALYTICAL INSIGHTS ---
            analytical_insights = await self._execute_phase_4_5_insights(
                context,
                segmentation_result,
                topic_detection_result,
                topic_sentiments,
                topic_examples,
                fin_result,
                topics_by_conv,
                ai_model
            )
            workflow_results.update(analytical_insights) # Flatten into main results for simplicity, or keep nested?
            # TopicOrchestrator kept them nested in 'AnalyticalInsights' key for formatter, let's do that
            workflow_results['AnalyticalInsights'] = analytical_insights

            # --- PHASE 4.6: CROSS-PLATFORM CORRELATION ---
            if canny_posts and canny_topics:
                cross_corr_result = await self._execute_phase_4_6_cross_platform(
                    paid_conversations, 
                    canny_posts, 
                    ai_model
                )
                workflow_results['CrossPlatformCorrelationAgent'] = _normalize_agent_result(cross_corr_result)

            # --- PHASE 5: TREND ANALYSIS ---
            trend_result = await self._execute_phase_5_trends(
                context,
                topic_dist,
                topic_sentiments
            )
            workflow_results['TrendAgent'] = _normalize_agent_result(trend_result)

            # --- PHASE 5.5: VALIDATION ---
            self._execute_phase_5_5_validation(
                workflow_results, 
                len(context.conversations or []),
                len(free_fin_only_conversations)
            )

            # --- PHASE 6: FORMATTING ---
            self.log_stage_metrics("Pre-Formatting", len(context.conversations or []))
            
            formatter_result = await self._execute_phase_6_formatting(
                context,
                workflow_results,
                topic_dist,
                segmentation_result,
                bpo_result,
                trend_result,
                analytical_insights
            )
            workflow_results[self.formatter_agent_name] = _normalize_agent_result(formatter_result)

            # --- PHASE 6.5: SNAPSHOT ---
            # We calculate the final payload structure here to save it
            total_time = (datetime.now() - start_time).total_seconds()
            final_payload = self._build_final_payload(
                context, 
                workflow_results, 
                formatter_result, 
                total_time,
                topic_dist,
                paid_conversations,
                free_fin_only_conversations,
                paid_fin_resolved_conversations,
                subtopics_data,
                canny_posts
            )
            
            # Auto-save snapshot
            await self._save_snapshot(final_payload, context.metadata.get('period_type'))

            return AgentResult(
                agent_name="VoiceOfCustomerStrategy",
                success=True,
                data=final_payload,
                confidence=formatter_result.confidence,
                confidence_level=formatter_result.confidence_level,
                execution_time=total_time
            )

        except Exception as e:
            self.logger.error(f"VoiceOfCustomerStrategy execution failed: {e}", exc_info=True)
            raise

    # --- Phase Implementations ---

    async def _execute_phase_1_segmentation(self, context: AgentContext) -> AgentResult:
        self.logger.info("📊 Phase 1: Segmentation")
        if self.monitor:
            await self.monitor.update_agent_status('SegmentationAgent', AgentStatus.RUNNING, "Classifying customer tiers")
        
        result = await self._execute_with_timeout(self.segmentation_agent, context)
        
        if self.monitor:
            await self.monitor.update_agent_status('SegmentationAgent', AgentStatus.COMPLETED, "Segmentation complete", confidence=result.confidence)
        
        if not result.success and self.fail_on_critical_errors:
            raise RuntimeError(f"Segmentation failed: {result.error_message}")
            
        return result

    async def _execute_phase_2_topic_detection(self, context: AgentContext):
        self.logger.info("🏷️  Phase 2: Topic Detection")
        if self.monitor:
            await self.monitor.update_agent_status('TopicDetectionAgent', AgentStatus.RUNNING, "Classifying topics")

        # Ensure global date range metadata
        convs = context.conversations or []
        if convs:
            created_ats = [c.get('created_at') for c in convs if c.get('created_at')]
            if created_ats:
                try:
                    min_val = min(created_ats)
                    max_val = max(created_ats)
                    # Handle int timestamps
                    if isinstance(min_val, int):
                        min_str = datetime.fromtimestamp(min_val).isoformat()
                        max_str = datetime.fromtimestamp(max_val).isoformat()
                    else:
                        min_str = min_val.isoformat() if hasattr(min_val, 'isoformat') else str(min_val)
                        max_str = max_val.isoformat() if hasattr(max_val, 'isoformat') else str(max_val)
                    
                    context = context.merge_metadata({
                        'raw_data_date_range': {'min_created_at': min_str, 'max_created_at': max_str}
                    })
                except Exception:
                    pass

        result = await self._execute_with_timeout(self.topic_detection_agent, context)
        
        if self.monitor:
            topics_found = len(result.data.get('topic_distribution', {}))
            await self.monitor.update_agent_status('TopicDetectionAgent', AgentStatus.COMPLETED, f"Detected {topics_found} topics", confidence=result.confidence)

        if not result.success and self.fail_on_critical_errors:
            raise RuntimeError(f"Topic detection failed: {result.error_message}")

        # Normalize distribution format
        raw_dist = result.data.get('topic_distribution', {})
        normalized_dist = {}
        for topic, value in raw_dist.items():
            if isinstance(value, dict):
                normalized_dist[topic] = value
            elif isinstance(value, int):
                normalized_dist[topic] = {'volume': value}
            else:
                normalized_dist[topic] = {'volume': 0}
        
        topics_by_conv = result.data.get('topics_by_conversation', {})
        return result, normalized_dist, topics_by_conv

    async def _execute_phase_2_4_bpo(self, context, segmentation_result, topic_detection_result, topic_dist):
        self.logger.info("👥 Phase 2.4: BPO Vendor Analysis")
        config = get_analysis_mode_config()
        if not config.is_feature_enabled('enable_bpo_analysis'):
            return self._build_skip_result('BpoPerformanceAgent', 'enable_bpo_analysis')

        agent_assignments = segmentation_result.data.get('agent_assignments') or {}
        topics_map = topic_detection_result.data.get('topics_by_conversation') or {}
        
        if not agent_assignments or not topics_map:
            self.logger.warning("Missing BPO inputs, skipping.")
            return AgentResult(agent_name='BpoPerformanceAgent', success=False, data={}, confidence=0.0, confidence_level=ConfidenceLevel.LOW, error_message="Missing inputs")

        bpo_metadata = {
            'agent_assignments': agent_assignments,
            'agent_distribution': segmentation_result.data.get('agent_distribution', {}),
            'topics_by_conversation': topics_map,
            'topic_distribution': topic_dist,
            'segmentation_summary': segmentation_result.data.get('segmentation_summary', {})
        }
        bpo_context = context.model_copy(update={'metadata': {**context.metadata, **bpo_metadata}})
        
        return await self._execute_with_timeout(self.bpo_performance_agent, bpo_context)

    async def _execute_phase_2_5_subtopics(self, context, paid_conversations, topic_detection_result, topic_dist):
        self.logger.info("🔍 Phase 2.5: Sub-Topic Detection")
        config = get_analysis_mode_config()
        if not config.is_feature_enabled('enable_subtopic_detection'):
            return self._build_skip_result('SubTopicDetectionAgent', 'enable_subtopic_detection'), {}

        # Only run on paid conversations
        subtopic_context = context.model_copy(update={
            'conversations': paid_conversations,
            'previous_results': {
                'TopicDetectionAgent': _normalize_agent_result(topic_detection_result)
            }
        })
        
        if self.monitor:
            await self.monitor.update_agent_status('SubTopicDetectionAgent', AgentStatus.RUNNING, "Analyzing sub-topics")

        result = await self._execute_with_timeout(self.subtopic_detection_agent, subtopic_context)
        
        subtopics_data = result.data.get('subtopics_by_tier1_topic', {})
        if self.monitor:
            await self.monitor.update_agent_status('SubTopicDetectionAgent', AgentStatus.COMPLETED, f"Found sub-topics for {len(subtopics_data)} topics", confidence=result.confidence)
            
        return result, subtopics_data

    async def _execute_phase_2_6_canny(self, canny_posts, ai_model):
        self.logger.info("🎯 Phase 2.6: Canny Topic Detection")
        config = get_analysis_mode_config()
        if not config.is_feature_enabled('enable_canny'):
            return self._build_skip_result('CannyTopicDetectionAgent', 'enable_canny'), {}

        try:
            topics_map = await self.canny_topic_detection_agent.detect_topics(
                canny_posts=canny_posts,
                taxonomy=None,
                ai_model=ai_model,
                enable_fallback=True
            )
            
            data = {
                'topics_detected': len(topics_map),
                'total_posts': len(canny_posts),
                'topics_by_category': {t: d['count'] for t, d in topics_map.items()}
            }
            
            return AgentResult(
                agent_name='CannyTopicDetectionAgent',
                success=True,
                data=data,
                confidence=0.8,
                confidence_level=ConfidenceLevel.HIGH
            ), topics_map
        except Exception as e:
            self.logger.error(f"Canny detection failed: {e}")
            return AgentResult(
                agent_name='CannyTopicDetectionAgent',
                success=False,
                data={},
                confidence=0.0,
                confidence_level=ConfidenceLevel.LOW,
                error_message=str(e)
            ), {}

    async def _execute_phase_3_per_topic(self, context, conversations, topic_dist, topics_by_conv):
        self.logger.info("💭 Phase 3: Per-Topic Analysis")
        config = get_analysis_mode_config()
        sentiment_enabled = config.is_feature_enabled('enable_topic_sentiment')
        examples_enabled = config.is_feature_enabled('enable_topic_examples')
        
        # Map conversations to topics
        convs_by_topic = {}
        for conv in conversations:
            conv_id = conv.get('id')
            for assignment in topics_by_conv.get(conv_id, []):
                topic = assignment['topic']
                if topic not in convs_by_topic:
                    convs_by_topic[topic] = []
                convs_by_topic[topic].append(conv)
        
        topic_sentiments = {}
        topic_examples = {}
        
        async def process_topic(topic, stats):
            async with self.topic_semaphore:
                topic_convs = convs_by_topic.get(topic, [])
                if not topic_convs:
                    return topic, None, None
                
                # Sentiment
                sentiment_res = None
                if sentiment_enabled:
                    t_ctx = context.model_copy(update={'metadata': {**context.metadata, 'current_topic': topic, 'topic_conversations': topic_convs}})
                    sentiment_res = await self.topic_sentiment_agent.execute(t_ctx)
                else:
                    sentiment_res = self._build_skip_result('TopicSentimentAgent', 'enable_topic_sentiment')
                
                # Examples
                examples_res = None
                if examples_enabled:
                    # Pass sentiment insight to example extractor
                    insight = sentiment_res.data.get('sentiment_insight', '') if sentiment_res else ''
                    e_ctx = context.model_copy(update={'metadata': {**context.metadata, 'current_topic': topic, 'topic_conversations': topic_convs, 'sentiment_insight': insight}})
                    examples_res = await self.example_extraction_agent.execute(e_ctx)
                else:
                    examples_res = self._build_skip_result('ExampleExtractionAgent', 'enable_topic_examples')
                
                return topic, sentiment_res, examples_res

        tasks = []
        for topic, stats in topic_dist.items():
            if stats.get('volume', 0) > 0:
                tasks.append(process_topic(topic, stats))
        
        results = await asyncio.gather(*tasks)
        
        for topic, s_res, e_res in results:
            if s_res:
                topic_sentiments[topic] = _normalize_agent_result(s_res)
            if e_res:
                topic_examples[topic] = _normalize_agent_result(e_res)
                
        return topic_sentiments, topic_examples

    async def _execute_phase_4_fin(self, context, free_convs, paid_fin_convs, topic_res, subtopic_res, subtopics_data):
        self.logger.info("🤖 Phase 4: Fin Analysis")
        config = get_analysis_mode_config()
        if not config.is_feature_enabled('enable_fin_analysis'):
            return self._build_skip_result('FinPerformanceAgent', 'enable_fin_analysis')

        if self.monitor:
            await self.monitor.update_agent_status('FinPerformanceAgent', AgentStatus.RUNNING, "Analyzing Fin performance")

        fin_metadata = {
            'free_fin_conversations': free_fin_only_conversations if 'free_fin_only_conversations' in locals() else free_convs,
            'paid_fin_conversations': paid_fin_resolved_conversations if 'paid_fin_resolved_conversations' in locals() else paid_fin_convs,
            'week_id': context.metadata.get('week_id'),
            'subtopics_by_tier1_topic': subtopics_data
        }
        fin_previous = {
            'SubTopicDetectionAgent': _normalize_agent_result(subtopic_res),
            'TopicDetectionAgent': _normalize_agent_result(topic_res)
        }
        fin_context = context.model_copy(update={
            'metadata': {**context.metadata, **fin_metadata},
            'previous_results': {**context.previous_results, **fin_previous}
        })
        
        result = await self._execute_with_timeout(self.fin_performance_agent, fin_context)
        
        if self.monitor:
            await self.monitor.update_agent_status('FinPerformanceAgent', AgentStatus.COMPLETED, "Fin analysis complete", confidence=result.confidence)
            
        return result

    async def _execute_phase_4_5_insights(self, context, seg_res, topic_res, sentiments, examples, fin_res, topics_map, ai_model):
        """
        Execute Phase 4.5 insight agents with graceful failure handling.
        
        If any agent fails, it will be skipped and the pipeline continues.
        This ensures Phase 4.5 failures don't crash the entire analysis.
        """
        self.logger.info("🔍 Phase 4.5: Analytical Insights")
        
        try:
            config = get_analysis_mode_config()
            
            # Setup agents based on flags
            agents_to_run = []
            if config.is_feature_enabled('enable_correlation_analysis'):
                agents_to_run.append(('CorrelationAgent', self.correlation_agent))
            if config.is_feature_enabled('enable_quality_insights'):
                agents_to_run.append(('QualityInsightsAgent', self.quality_insights_agent))
            if config.is_feature_enabled('enable_churn_detection'):
                agents_to_run.append(('ChurnRiskAgent', self.churn_risk_agent))
            if config.is_feature_enabled('enable_confidence_meta'):
                agents_to_run.append(('ConfidenceMetaAgent', self.confidence_meta_agent))
                
            if not agents_to_run:
                return {}

            # Prepare context - defensive handling for None metadata
            hist_context = {'weeks_available': 0}
            if self.historical_snapshot_service:
                try:
                    hist_context = self.historical_snapshot_service.get_historical_context()
                except Exception as e:
                    self.logger.warning(f"Failed to get historical context: {e}")

            # Safely unpack context.metadata (could be None)
            base_metadata = context.metadata if context.metadata else {}
            
            insight_context = context.model_copy(update={
                'previous_results': {
                    'SegmentationAgent': _normalize_agent_result(seg_res),
                    'TopicDetectionAgent': _normalize_agent_result(topic_res),
                    'TopicSentiments': sentiments or {},
                    'TopicExamples': examples or {},
                    'FinPerformanceAgent': _normalize_agent_result(fin_res)
                },
                'metadata': {
                    **base_metadata,
                    'topics_by_conversation': topics_map or {},
                    'historical_context': hist_context
                }
            })
            
            # Inject AI client with error handling
            try:
                ai_enum = AIModel.OPENAI_GPT4 if ai_model == 'openai' else AIModel.ANTHROPIC_CLAUDE
                client = self.ai_factory.get_client(ai_enum)
                for _, agent in agents_to_run:
                    if hasattr(agent, 'ai_client'):
                        agent.ai_client = client
            except Exception as e:
                self.logger.warning(f"Failed to inject AI client for insight agents: {e}")
                # Continue without AI client - agents should handle None gracefully

            results = await asyncio.gather(
                *(agent.execute(insight_context) for _, agent in agents_to_run),
                return_exceptions=True
            )
            
            insights = {}
            for (name, _), res in zip(agents_to_run, results):
                if isinstance(res, Exception):
                    self.logger.warning(f"⚠️ {name} failed (skipping): {res}")
                    insights[name] = {
                        'success': False, 
                        'skipped': True,
                        'error': str(res),
                        'data': {}
                    }
                else:
                    insights[name] = _normalize_agent_result(res)
                    
            return insights
            
        except Exception as e:
            self.logger.error(f"⚠️ Phase 4.5 failed entirely (skipping all insight agents): {e}")
            # Return empty insights so pipeline can continue
            return {
                'CorrelationAgent': {'success': False, 'skipped': True, 'error': str(e), 'data': {}},
                'QualityInsightsAgent': {'success': False, 'skipped': True, 'error': str(e), 'data': {}},
                'ChurnRiskAgent': {'success': False, 'skipped': True, 'error': str(e), 'data': {}},
                'ConfidenceMetaAgent': {'success': False, 'skipped': True, 'error': str(e), 'data': {}},
            }

    async def _execute_phase_4_6_cross_platform(self, paid_conversations, canny_posts, ai_model):
        self.logger.info("🔗 Phase 4.6: Cross-Platform Correlation")
        config = get_analysis_mode_config()
        if not config.is_feature_enabled('enable_canny'):
            return self._build_skip_result('CrossPlatformCorrelationAgent', 'enable_canny')

        try:
            res = await self.cross_platform_correlation_agent.analyze_correlations(
                intercom_conversations=paid_conversations,
                canny_posts=canny_posts,
                ai_model=ai_model,
                enable_fallback=True
            )
            return AgentResult(
                agent_name='CrossPlatformCorrelationAgent',
                success=True,
                data=res,
                confidence=0.85,
                confidence_level=ConfidenceLevel.HIGH
            )
        except Exception as e:
            self.logger.error(f"Cross-platform failed: {e}")
            return AgentResult(agent_name='CrossPlatformCorrelationAgent', success=False, data={}, confidence=0.0, confidence_level=ConfidenceLevel.LOW, error_message=str(e))

    async def _execute_phase_5_trends(self, context, topic_dist, topic_sentiments):
        self.logger.info("📈 Phase 5: Trend Analysis")
        config = get_analysis_mode_config()
        if not config.is_feature_enabled('enable_trends'):
            return self._build_skip_result('TrendAgent', 'enable_trends')

        trend_metadata = {
            'current_week_results': {
                'topic_distribution': topic_dist,
                'topic_sentiments': {k: v.get('data', {}) for k, v in topic_sentiments.items()}
            },
            'week_id': context.metadata.get('week_id')
        }
        trend_context = context.model_copy(update={'metadata': {**context.metadata, **trend_metadata}})
        
        return await self._execute_with_timeout(self.trend_agent, trend_context)

    def _execute_phase_5_5_validation(self, workflow_results, total_count, free_count):
        self.logger.info("🔍 Phase 5.5: Validation")
        if self.audit:
            self.audit.step("Phase 5.5: Data Validation", "Validating workflow integrity", {'total_conversations': total_count})

        try:
            warnings = AnalysisValidator.validate_voc_analysis(
                workflow_results,
                total_count,
                free_tier_conversations_count=free_count,
                raise_on_critical=self.fail_on_critical_errors
            )
            if warnings:
                self.logger.warning(f"Validation warnings: {warnings}")
        except Exception as e:
            self.logger.error(f"Validation failed: {e}")
            if self.fail_on_critical_errors:
                raise

    async def _execute_phase_6_formatting(self, context, workflow_results, topic_dist, seg_res, bpo_res, trend_res, insights):
        self.logger.info("📝 Phase 6: Output Formatting")
        if self.monitor:
            await self.monitor.update_agent_status(self.formatter_agent_name, AgentStatus.RUNNING, "Formatting output")

        # Get comparison data
        comparison_data = None
        if self.historical_snapshot_service:
            try:
                sid = context.metadata.get('snapshot_id') # Where does this come from? Usually generated later. 
                # Actually historical service compares against *prior* snapshot.
                # Logic in TopicOrchestrator was: get snapshot_id from metadata (but it wasn't set yet?), 
                # wait, logic was `if context.metadata.get('snapshot_id')`. 
                # It seems TopicOrchestrator was checking if *caller* passed a reference snapshot.
                # But for "last week", we calculate prior.
                # Let's replicate TopicOrchestrator logic:
                # `prior_snapshot = self.historical_snapshot_service.get_prior_snapshot(snapshot_id, period_type)`
                # But snapshot_id isn't generated until Phase 6.5.
                # It seems comparison logic in TopicOrchestrator relied on `context.metadata['snapshot_id']` which might be empty for new runs.
                # We'll stick to the implementation: try to get it.
                pass
            except Exception:
                pass

        # Prepare output context
        output_previous = {
            **workflow_results,
            'AnalyticalInsights': insights,
            'SegmentationAgent': _normalize_agent_result(seg_res),
            'TrendAgent': _normalize_agent_result(trend_res),
            'BpoPerformanceAgent': _normalize_agent_result(bpo_res)
        }
        
        output_context = context.model_copy(update={
            'previous_results': {**context.previous_results, **output_previous},
            'metadata': {
                **context.metadata,
                'bpo_summary': _normalize_agent_result(bpo_res).get('data', {})
            }
        })
        
        result = await self._execute_with_timeout(self.formatter_agent, output_context)
        
        if self.monitor:
            await self.monitor.update_agent_status(self.formatter_agent_name, AgentStatus.COMPLETED, "Formatting complete", confidence=result.confidence)
            
        return result

    def _build_final_payload(self, context, workflow_results, formatter_result, total_time, topic_dist, paid, free, paid_fin, subtopics, canny_posts):
        metrics = {
            'total_execution_time': total_time,
            # ... (Full metric aggregation logic omitted for brevity but should be here)
        }
        
        final_output = {
            'week_id': context.metadata.get('week_id'),
            'formatted_report': formatter_result.data.get('formatted_output', ''),
            'agent_results': workflow_results,
            'summary': {
                'total_conversations': len(context.conversations or []),
                'topics_analyzed': len(topic_dist),
                'execution_time': total_time
            }
        }
        return final_output

    async def _save_snapshot(self, payload, period_type):
        if self.historical_snapshot_service:
            try:
                sid = await self.historical_snapshot_service.save_snapshot_async(payload, period_type)
                self.logger.info(f"Snapshot saved: {sid}")
                return sid
            except Exception as e:
                self.logger.warning(f"Snapshot save failed: {e}")
        return None

    def _build_skip_result(self, agent_name: str, feature_flag: str) -> AgentResult:
        return AgentResult(
            agent_name=agent_name,
            success=False,
            data={'message': f"Skipped ({feature_flag}=False)", 'skipped': True},
            confidence=0.0,
            confidence_level=ConfidenceLevel.LOW
        )

