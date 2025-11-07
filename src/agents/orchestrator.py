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
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path
import json

from src.agents.base_agent import BaseAgent, AgentContext, AgentResult
from src.agents.data_agent import DataAgent
from src.agents.category_agent import CategoryAgent
from src.agents.sentiment_agent import SentimentAgent
from src.agents.insight_agent import InsightAgent
from src.agents.presentation_agent import PresentationAgent

logger = logging.getLogger(__name__)


class MultiAgentOrchestrator:
    """
    Orchestrates the multi-agent analysis workflow.
    
    Coordinates 5 specialized agents in a sequential (POC) or parallel workflow.
    """
    
    def __init__(self, checkpoint_dir: Optional[Path] = None):
        self.checkpoint_dir = checkpoint_dir or Path("outputs/checkpoints")
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize agents
        self.data_agent = DataAgent()
        self.category_agent = CategoryAgent()
        self.sentiment_agent = SentimentAgent()
        self.insight_agent = InsightAgent()
        self.presentation_agent = PresentationAgent()
        
        self.logger = logging.getLogger(__name__)
    
    async def execute_analysis(
        self,
        analysis_type: str,
        start_date: datetime,
        end_date: datetime,
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
        analysis_id = f"multi_agent_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        start_time = datetime.now()
        
        self.logger.info(f"🤖 MultiAgentOrchestrator: Starting analysis {analysis_id}")
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
            # Create initial context
            context = AgentContext(
                analysis_id=analysis_id,
                analysis_type=analysis_type,
                start_date=start_date,
                end_date=end_date
            )
            
            # PHASE 1: Data Collection
            self.logger.info("📊 Phase 1: Data Collection (DataAgent)")
            data_result = await self._execute_agent_with_checkpoint(
                self.data_agent,
                context,
                workflow_state
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
            category_result = await self._execute_agent_with_checkpoint(
                self.category_agent,
                context,
                workflow_state
            )
            
            if category_result.success:
                context.previous_results['CategoryAgent'] = category_result.dict()
                workflow_state['agent_results']['CategoryAgent'] = category_result.dict()
                self.logger.info(f"   ✅ CategoryAgent: Classified {category_result.data.get('total_classified', 0)} conversations")
            else:
                self.logger.warning(f"   ⚠️ CategoryAgent failed: {category_result.error_message}")
                workflow_state['errors'].append(f"CategoryAgent: {category_result.error_message}")
            
            # SentimentAgent
            sentiment_result = await self._execute_agent_with_checkpoint(
                self.sentiment_agent,
                context,
                workflow_state
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
                workflow_state
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
                    workflow_state
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
            
            self.logger.info(f"🎉 MultiAgentOrchestrator: Completed in {total_time:.2f}s")
            self.logger.info(f"   Agents: {len(workflow_state['agent_results'])}/5 successful")
            self.logger.info(f"   Errors: {len(workflow_state['errors'])}")
            
            # Cleanup checkpoint
            self._cleanup_checkpoint(analysis_id)
            
            return workflow_state
            
        except Exception as e:
            total_time = (datetime.now() - start_time).total_seconds()
            self.logger.error(f"MultiAgentOrchestrator error: {e}")
            
            workflow_state['status'] = 'failed'
            workflow_state['end_time'] = datetime.now().isoformat()
            workflow_state['total_execution_time'] = total_time
            workflow_state['errors'].append(str(e))
            
            return workflow_state
    
    async def _execute_agent_with_checkpoint(
        self,
        agent: BaseAgent,
        context: AgentContext,
        workflow_state: Dict[str, Any]
    ) -> AgentResult:
        """Execute agent with checkpointing and timeout for recovery"""
        import asyncio

        try:
            # Check for existing checkpoint
            checkpoint = self._load_checkpoint(context.analysis_id, agent.name)
            if checkpoint:
                self.logger.info(f"   📂 Resuming {agent.name} from checkpoint")
                return AgentResult(**checkpoint)

            # Get timeout for this agent (default 300 seconds = 5 minutes)
            timeout = self._get_agent_timeout(agent.name)

            try:
                # Execute agent with timeout
                self.logger.debug(f"Executing {agent.name} with {timeout}s timeout")
                result = await asyncio.wait_for(
                    agent.execute(context),
                    timeout=timeout
                )

                # Save checkpoint
                self._save_checkpoint(context.analysis_id, agent.name, result.dict())

                return result

            except asyncio.TimeoutError:
                self.logger.error(
                    f"Agent {agent.name} timed out after {timeout}s",
                    extra={
                        "agent": agent.name,
                        "timeout_seconds": timeout,
                        "status": "timeout"
                    }
                )
                # Return partial result with timeout status
                return AgentResult(
                    status="timeout",
                    data={"error": f"Agent timed out after {timeout}s"},
                    metadata={"agent": agent.name, "timeout": timeout},
                    confidence=0.0
                )

        except Exception as e:
            self.logger.error(f"Agent execution error: {e}")
            raise

    def _get_agent_timeout(self, agent_name: str) -> float:
        """
        Get timeout for specific agent from config or default.

        Agent names match their class names (DataAgent, CategoryAgent, etc.).
        """
        # Default timeouts per agent type (in seconds)
        # Keys must match agent.name which is typically the class name
        default_timeouts = {
            'DataAgent': 180,                          # 3 minutes for data fetching
            'CategoryAgent': 300,                       # 5 minutes for categorization
            'SentimentAgent': 300,                      # 5 minutes for sentiment analysis
            'InsightAgent': 300,                        # 5 minutes for insights
            'PresentationAgent': 600,                   # 10 minutes for presentation generation
            'SegmentationAgent': 300,                   # 5 minutes for segmentation
            'TrendAgent': 240,                          # 4 minutes for trends
            'TopicDetectionAgent': 300,                 # 5 minutes for topic detection
            'SubTopicDetectionAgent': 300,              # 5 minutes for subtopic detection
            'ExampleExtractionAgent': 240,              # 4 minutes for examples
            'AgentPerformanceAgent': 240,               # 4 minutes for agent performance
            'FinPerformanceAgent': 240,                 # 4 minutes for Fin performance
            'TopicSentimentAgent': 300,                 # 5 minutes for topic sentiment
            'OutputFormatterAgent': 180,                # 3 minutes for output formatting
            'CrossPlatformCorrelationAgent': 300,       # 5 minutes for correlation
            'CannyTopicDetectionAgent': 300,            # 5 minutes for Canny topics
        }

        # Try to get from settings/config
        from src.config.settings import settings
        if hasattr(settings, 'agent_timeouts'):
            return settings.agent_timeouts.get(agent_name, default_timeouts.get(agent_name, 300))

        return default_timeouts.get(agent_name, 300)
    
    def _save_checkpoint(self, analysis_id: str, agent_name: str, result: Dict[str, Any]):
        """
        Save agent result as checkpoint with atomic write and size/retention management.

        Uses atomic write (temp file + rename) to prevent partial writes.
        Enforces retention policy to prevent disk bloat.
        """
        from src.config.settings import settings
        import tempfile

        checkpoint_file = self.checkpoint_dir / f"{analysis_id}_{agent_name}.json"

        try:
            # Atomic write: write to temp file then rename
            with tempfile.NamedTemporaryFile(
                mode='w',
                dir=self.checkpoint_dir,
                delete=False,
                suffix='.tmp'
            ) as tmp_file:
                json.dump(result, tmp_file, indent=2, default=str)
                tmp_path = Path(tmp_file.name)

            # Atomic rename
            tmp_path.replace(checkpoint_file)

            self.logger.debug(f"Checkpoint saved: {checkpoint_file}")

            # Enforce retention policy
            max_checkpoints = getattr(settings, 'max_checkpoints', 100)
            self._prune_old_checkpoints(max_checkpoints)

        except Exception as e:
            self.logger.error(f"Failed to save checkpoint {checkpoint_file}: {e}")
            # Clean up temp file if it exists
            if 'tmp_path' in locals() and tmp_path.exists():
                tmp_path.unlink()
            raise
    
    def _load_checkpoint(self, analysis_id: str, agent_name: str) -> Optional[Dict[str, Any]]:
        """
        Load agent result from checkpoint with schema validation.

        Returns:
            Checkpoint data if valid, None otherwise
        """
        checkpoint_file = self.checkpoint_dir / f"{analysis_id}_{agent_name}.json"

        if not checkpoint_file.exists():
            return None

        try:
            data = json.loads(checkpoint_file.read_text())

            # Validate basic schema
            required_keys = ['agent_name', 'success', 'data']
            if not all(key in data for key in required_keys):
                self.logger.warning(f"Invalid checkpoint schema: {checkpoint_file}")
                return None

            self.logger.debug(f"Checkpoint loaded: {checkpoint_file}")
            return data

        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse checkpoint {checkpoint_file}: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Failed to load checkpoint {checkpoint_file}: {e}")
            return None

    def _prune_old_checkpoints(self, max_checkpoints: int):
        """
        Remove old checkpoints to enforce retention policy.

        Keeps the most recent max_checkpoints files based on modification time.
        """
        try:
            checkpoints = sorted(
                self.checkpoint_dir.glob("*.json"),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )

            if len(checkpoints) > max_checkpoints:
                to_remove = checkpoints[max_checkpoints:]
                for checkpoint in to_remove:
                    checkpoint.unlink()
                    self.logger.debug(f"Pruned old checkpoint: {checkpoint}")

                self.logger.info(f"Pruned {len(to_remove)} old checkpoints (max={max_checkpoints})")

        except Exception as e:
            self.logger.warning(f"Failed to prune checkpoints: {e}")
    
    def _cleanup_checkpoint(self, analysis_id: str):
        """Remove checkpoints after successful completion"""
        for checkpoint_file in self.checkpoint_dir.glob(f"{analysis_id}_*.json"):
            checkpoint_file.unlink()
    
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

