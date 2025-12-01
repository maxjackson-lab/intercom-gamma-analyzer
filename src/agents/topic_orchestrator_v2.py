"""
Wrapper orchestrator for VOC-V2 narrative reports.

This wrapper now uses the UnifiedOrchestrator with VoiceOfCustomerStrategy,
replacing the legacy TopicOrchestrator monolith while maintaining the same API.
"""

from datetime import datetime
from typing import Optional

from src.agents.base_agent import AgentContext
from src.services.ai_model_factory import AIModelFactory
from src.services.unified_orchestrator import UnifiedOrchestrator
from src.services.strategies.voc_strategy import VoiceOfCustomerStrategy


class TopicOrchestratorV2:
    """
    Configure UnifiedOrchestrator with VoiceOfCustomerStrategy.
    
    This replaces the legacy TopicOrchestrator while keeping the API compatible
    with existing callers in src/cli/voc_commands.py.
    """

    def __init__(self, ai_factory: Optional[AIModelFactory] = None, audit_trail=None, execution_monitor=None):
        strategy = VoiceOfCustomerStrategy(
            ai_factory=ai_factory,
            audit_trail=audit_trail,
            execution_monitor=execution_monitor
        )
        self._orchestrator = UnifiedOrchestrator(strategy=strategy)

    async def execute_weekly_analysis(
        self,
        conversations,
        week_id=None,
        start_date=None,
        end_date=None,
        period_type=None,
        period_label=None,
        canny_posts=None,
        ai_model=None,
        digest_mode=False,
        detail_level="standard"
    ):
        """
        Execute analysis using the UnifiedOrchestrator.
        
        Maps arguments to AgentContext and options dict expected by VoiceOfCustomerStrategy.
        """
        # Build context
        context = AgentContext(
            analysis_id=f"voc_v2_{week_id or 'custom'}",
            analysis_type="voc_v2",
            start_date=start_date or datetime.now(),
            end_date=end_date or datetime.now(),
            conversations=conversations,
            metadata={
                'week_id': week_id,
                'period_type': period_type,
                'period_label': period_label,
                'digest_mode': digest_mode,
                'detail_level': detail_level
            }
        )
        
        # Pass specialized arguments via kwargs
        kwargs = {
            'canny_posts': canny_posts,
            'ai_model': ai_model
        }
        
        # Execute via strategy
        result = await self._orchestrator.execute(context, **kwargs)
        
        # Return the data payload (matching legacy return type Dict[str, Any])
        return result.data
