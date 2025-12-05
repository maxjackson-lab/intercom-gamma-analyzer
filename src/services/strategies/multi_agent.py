"""
Multi-Agent Orchestrator: Coordinates the 5-agent workflow.

Workflow:
1. DataAgent: Fetch and validate data
2. CategoryAgent || SentimentAgent: Parallel classification (future)
3. InsightAgent: Synthesize cross-agent insights
4. PresentationAgent: Generate Gamma presentation

Features:
- Sequential execution (POC)
- Error handling with fallbacks
- Checkpointing for long-running analyses
- Comprehensive metrics tracking
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path

from src.agents.base_agent import BaseAgent, AgentContext, AgentResult, ConfidenceLevel
from src.agents.data_agent import DataAgent
from src.agents.category_agent import CategoryAgent
from src.agents.sentiment_agent import SentimentAgent
from src.agents.insight_agent import InsightAgent
from src.agents.presentation_agent import PresentationAgent
from src.services.unified_orchestrator import OrchestrationStrategy

logger = logging.getLogger(__name__)


from src.agents.editor_agent import EditorAgent

class MultiAgentStrategy(OrchestrationStrategy):
    """
    Orchestrates the multi-agent analysis workflow.
    
    Coordinates 5 specialized agents in a sequential (POC) or parallel workflow.
    """
    
    def __init__(self, checkpoint_dir: Optional[Path] = None):
        super().__init__(checkpoint_dir=checkpoint_dir)
        
        # Initialize agents
        self.data_agent = DataAgent()
        self.category_agent = CategoryAgent()
        self.sentiment_agent = SentimentAgent()
        self.insight_agent = InsightAgent()
        self.presentation_agent = PresentationAgent()
        self.editor_agent = EditorAgent()
        
        self.logger = logging.getLogger(__name__)

    def get_strategy_name(self) -> str:
        return "MultiAgentStrategy"

    async def execute(
        self,
        context: AgentContext,
        generate_gamma: bool = True,
        **kwargs
    ) -> AgentResult:
        workflow_state = await self._run_workflow(
            context=context,
            generate_gamma=generate_gamma,
            **kwargs
        )

        success = workflow_state.get('status') == 'completed'
        confidence = self._derive_confidence(workflow_state)
        confidence_level = self._confidence_level_from_score(confidence)
        error_message = None if success else "; ".join(workflow_state.get('errors', []))

        return AgentResult(
            agent_name=self.get_strategy_name(),
            success=success,
            data=workflow_state,
            confidence=confidence,
            confidence_level=confidence_level,
            error_message=error_message,
            execution_time=workflow_state.get('total_execution_time', 0.0)
        )

    async def _run_workflow(
        self,
        context: AgentContext,
        generate_gamma: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute complete multi-agent analysis workflow.
        
        Args:
            analysis_type: Type of analysis (voice-of-customer, billing, etc.)
            start_date: Start date for analysis
            end_date: End date for analysis
            generate_gamma: Whether to generate Gamma presentation
            **kwargs: Additional parameters
            
        Returns:
            Complete analysis results with all agent outputs
        """
        analysis_id = context.analysis_id or f"multi_agent_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        context.analysis_id = analysis_id
        start_time = datetime.now()
        
        analysis_type = context.analysis_type
        start_date = context.start_date
        end_date = context.end_date

        self.logger.info(f"🤖 MultiAgentStrategy: Starting analysis {analysis_id}")
        self.logger.info(f"   Analysis type: {analysis_type}")
        self.logger.info(f"   Date range: {start_date} to {end_date}")
        self.logger.info(f"   Generate Gamma: {generate_gamma}")
        
        # Initialize workflow state
        workflow_state = {
            'analysis_id': analysis_id,
            'analysis_type': analysis_type,
            'start_time': start_time.isoformat(),
            'agent_results': {},
            'errors': [],
            'status': 'running'
        }
        
        try:
            # PHASE 1: Data Collection
            self.logger.info("📊 Phase 1: Data Collection (DataAgent)")
            data_result = await self._execute_agent_with_checkpoint(
                self.data_agent,
                context,
                workflow_state,
                analysis_id
            )
            
            if not data_result.success:
                raise Exception(f"DataAgent failed: {data_result.error_message}")
            
            # Update context with fetched data
            context.conversations = data_result.data.get('conversations', [])
            workflow_state['agent_results']['DataAgent'] = data_result.dict()
            
            self.logger.info(f"   ✅ DataAgent: Fetched {len(context.conversations)} conversations")
            
            # PHASE 2: Analysis (Sequential for POC, can be parallel later)
            self.logger.info("🔍 Phase 2: Category & Sentiment Analysis")
            
            # CategoryAgent
            try:
                category_result = await self._execute_agent_with_checkpoint(
                    self.category_agent,
                    context,
                    workflow_state,
                    analysis_id
                )
            except Exception as e:
                self.logger.warning(f"   ⚠️ CategoryAgent failed: {e}")
                category_result = AgentResult(agent_name='CategoryAgent', success=False, data={}, confidence=0.0, confidence_level=ConfidenceLevel.LOW, error_message=str(e))
            
            if category_result.success:
                context.previous_results['CategoryAgent'] = category_result.dict()
                workflow_state['agent_results']['CategoryAgent'] = category_result.dict()
                self.logger.info(f"   ✅ CategoryAgent: Classified {category_result.data.get('total_classified', 0)} conversations")
            else:
                self.logger.warning(f"   ⚠️ CategoryAgent failed: {category_result.error_message}")
                workflow_state['errors'].append(f"CategoryAgent: {category_result.error_message}")
                # Fallback for CategoryAgent failure if needed

            
            # SentimentAgent
            sentiment_result = await self._execute_agent_with_checkpoint(
                self.sentiment_agent,
                context,
                workflow_state,
                analysis_id
            )
            
            if sentiment_result.success:
                context.previous_results['SentimentAgent'] = sentiment_result.dict()
                workflow_state['agent_results']['SentimentAgent'] = sentiment_result.dict()
                self.logger.info(f"   ✅ SentimentAgent: Analyzed {sentiment_result.data.get('total_analyzed', 0)} conversations")
            else:
                self.logger.warning(f"   ⚠️ SentimentAgent failed: {sentiment_result.error_message}")
                workflow_state['errors'].append(f"SentimentAgent: {sentiment_result.error_message}")
            
            # PHASE 3: Insight Synthesis
            self.logger.info("💡 Phase 3: Insight Synthesis (InsightAgent)")
            
            insight_result = await self._execute_agent_with_checkpoint(
                self.insight_agent,
                context,
                workflow_state,
                analysis_id
            )
            
            if insight_result.success:
                context.previous_results['InsightAgent'] = insight_result.dict()
                workflow_state['agent_results']['InsightAgent'] = insight_result.dict()
                self.logger.info(f"   ✅ InsightAgent: Generated {len(insight_result.data.get('major_themes', []))} major themes")
            else:
                self.logger.warning(f"   ⚠️ InsightAgent failed: {insight_result.error_message}")
                workflow_state['errors'].append(f"InsightAgent: {insight_result.error_message}")
            
            # PHASE 4: Presentation Generation (if requested)
            if generate_gamma:
                self.logger.info("📊 Phase 4: Presentation Generation (PresentationAgent)")
                
                presentation_result = await self._execute_agent_with_checkpoint(
                    self.presentation_agent,
                    context,
                    workflow_state,
                    analysis_id
                )
                
                if presentation_result.success:
                    workflow_state['agent_results']['PresentationAgent'] = presentation_result.dict()
                    gamma_url = presentation_result.data.get('gamma_url')
                    self.logger.info(f"   ✅ PresentationAgent: Generated presentation at {gamma_url}")
                else:
                    self.logger.warning(f"   ⚠️ PresentationAgent failed: {presentation_result.error_message}")
                    workflow_state['errors'].append(f"PresentationAgent: {presentation_result.error_message}")
            
            # Calculate total execution time
            total_time = (datetime.now() - start_time).total_seconds()
            
            # Compile final results
            workflow_state['status'] = 'completed'
            workflow_state['end_time'] = datetime.now().isoformat()
            workflow_state['total_execution_time'] = total_time
            workflow_state['summary'] = self._generate_summary(workflow_state)
            
            self.logger.info(f"🎉 MultiAgentStrategy: Completed in {total_time:.2f}s")
            self.logger.info(f"   Agents: {len(workflow_state['agent_results'])}/5 successful")
            self.logger.info(f"   Errors: {len(workflow_state['errors'])}")
            
            # Cleanup checkpoint
            self._cleanup_checkpoint(analysis_id)
            
            return workflow_state
            
        except Exception as e:
            total_time = (datetime.now() - start_time).total_seconds()
            self.logger.error(f"MultiAgentStrategy error: {e}")
            
            workflow_state['status'] = 'failed'
            workflow_state['end_time'] = datetime.now().isoformat()
            workflow_state['total_execution_time'] = total_time
            workflow_state['errors'].append(str(e))
            
            return workflow_state
    
    async def _execute_agent_with_checkpoint(
        self,
        agent: BaseAgent,
        context: AgentContext,
        workflow_state: Dict[str, Any],
        analysis_id: str,
    ) -> AgentResult:
        """Execute agent with checkpointing and timeout for recovery"""
        try:
            # Check for existing checkpoint
            checkpoint = self._load_checkpoint(analysis_id, agent.name)
            if checkpoint:
                self.logger.info(f"   📂 Resuming {agent.name} from checkpoint")
                return AgentResult(**checkpoint)

            result = await self._execute_with_timeout(agent, context)

            # Save checkpoint
            self._save_checkpoint(analysis_id, agent.name, result.dict())

            return result

        except Exception as e:
            self.logger.error(f"Agent execution error: {e}")
            raise

    
    def _cleanup_checkpoint(self, analysis_id: str):
        """Remove checkpoints after successful completion"""
        for checkpoint_file in self.checkpoint_dir.glob(f"{analysis_id}_*.json"):
            checkpoint_file.unlink()

    def _derive_confidence(self, workflow_state: Dict[str, Any]) -> float:
        """Aggregate confidence from individual agent outputs."""
        agent_results = workflow_state.get('agent_results', {})
        if not agent_results:
            return 0.6 if workflow_state.get('status') == 'completed' else 0.0

        confidences = []
        for result in agent_results.values():
            if isinstance(result, dict):
                confidences.append(result.get('confidence', 0.0))

        if not confidences:
            return 0.6 if workflow_state.get('status') == 'completed' else 0.0

        avg_conf = sum(confidences) / len(confidences)
        return max(0.0, min(1.0, avg_conf))
    
    def _generate_summary(self, workflow_state: Dict[str, Any]) -> Dict[str, Any]:
        """Generate summary of multi-agent execution"""
        agent_results = workflow_state['agent_results']
        
        total_time = sum(
            result.get('execution_time', 0)
            for result in agent_results.values()
        )
        
        total_tokens = sum(
            result.get('token_count', 0)
            for result in agent_results.values()
        )
        
        avg_confidence = sum(
            result.get('confidence', 0)
            for result in agent_results.values()
        ) / len(agent_results) if agent_results else 0
        
        return {
            'total_agents': len(agent_results),
            'successful_agents': sum(1 for r in agent_results.values() if r.get('success')),
            'total_execution_time': total_time,
            'total_tokens': total_tokens,
            'average_confidence': round(avg_confidence, 2),
            'errors_count': len(workflow_state['errors'])
        }

