"""
SegmentationAgent: Separates paid customers (human support) from free customers (AI-only).

Purpose:
- Identify conversations with human agent involvement
- Separate Fin AI-only conversations
- Detect agent types (Horatio, Boldr, Escalated)
"""

import logging
import re
from typing import Dict, Any, List
from datetime import datetime

from src.agents.base_agent import BaseAgent, AgentResult, AgentContext, ConfidenceLevel

logger = logging.getLogger(__name__)


class SegmentationAgent(BaseAgent):
    """Agent specialized in customer tier and agent type segmentation"""
    
    def __init__(self):
        super().__init__(
            name="SegmentationAgent",
            model="gpt-4o-mini",  # Simple classification task
            temperature=0.1
        )
        
        # Agent patterns
        self.escalation_names = ['dae-ho', 'max jackson', 'hilary']
        self.tier1_patterns = {
            'horatio': r'horatio|@horatio\.com',
            'boldr': r'boldr|@boldr'
        }
    
    def get_agent_specific_instructions(self) -> str:
        """Segmentation agent specific instructions"""
        return """
SEGMENTATION AGENT SPECIFIC RULES:

1. Accurately classify each conversation by support tier:
   - PAID: Has human agent involvement (Horatio, Boldr, or senior staff)
   - FREE: AI-only (Fin) with no human involvement
   - UNKNOWN: Cannot determine

2. Identify agent types:
   - ESCALATED: Dae-Ho Chung, Max Jackson, or Hilary Dudek
   - TIER1: Horatio or Boldr agents
   - FIN_AI: Fin AI only, no human
   
3. Never invent agent assignments - use only data provided

4. Flag detection confidence:
   - HIGH: Clear admin_assignee_id or explicit mentions
   - MEDIUM: Keyword matches only
   - LOW: Uncertain classification
"""
    
    def get_task_description(self, context: AgentContext) -> str:
        """Describe the segmentation task"""
        return f"""
Segment {len(context.conversations)} conversations by customer tier and agent type.

Classification rules:
- PAID customer: admin_assignee_id exists OR mentions Horatio/Boldr/senior staff
- FREE customer: ai_agent_participated=true AND no human involvement
- Agent type: Horatio, Boldr, Escalated (Dae-Ho/Max/Hilary), or Fin

Output: Segmented conversations with agent type labels
"""
    
    def format_context_data(self, context: AgentContext) -> str:
        """Format context for prompt"""
        return f"Total conversations to segment: {len(context.conversations)}"
    
    def validate_input(self, context: AgentContext) -> bool:
        """Validate input"""
        if not context.conversations:
            raise ValueError("No conversations to segment")
        return True
    
    def validate_output(self, result: Dict[str, Any]) -> bool:
        """Validate segmentation results"""
        required_keys = ['paid_customer_conversations', 'free_customer_conversations']
        for key in required_keys:
            if key not in result:
                self.logger.warning(f"Missing key: {key}")
                return False
        return True
    
    async def execute(self, context: AgentContext) -> AgentResult:
        """Execute conversation segmentation"""
        start_time = datetime.now()
        
        try:
            self.validate_input(context)
            
            conversations = context.conversations
            self.logger.info(f"SegmentationAgent: Segmenting {len(conversations)} conversations")
            
            # Segment conversations
            paid_customers = []
            free_customers = []
            unknown = []
            
            agent_distribution = {
                'escalated': [],
                'horatio': [],
                'boldr': [],
                'fin_ai': [],
                'unknown': []
            }
            
            for conv in conversations:
                segment, agent_type = self._classify_conversation(conv)
                
                if segment == 'paid':
                    paid_customers.append(conv)
                elif segment == 'free':
                    free_customers.append(conv)
                else:
                    unknown.append(conv)
                
                agent_distribution[agent_type].append(conv)
            
            # Prepare result
            result_data = {
                'paid_customer_conversations': paid_customers,
                'free_customer_conversations': free_customers,
                'unknown_tier': unknown,
                'agent_distribution': {
                    k: len(v) for k, v in agent_distribution.items()
                },
                'segmentation_summary': {
                    'paid_count': len(paid_customers),
                    'paid_percentage': round(len(paid_customers) / len(conversations) * 100, 1),
                    'free_count': len(free_customers),
                    'free_percentage': round(len(free_customers) / len(conversations) * 100, 1),
                    'unknown_count': len(unknown)
                }
            }
            
            self.validate_output(result_data)
            
            # Calculate confidence
            confidence = 1.0 - (len(unknown) / len(conversations)) if conversations else 0
            confidence_level = (ConfidenceLevel.HIGH if confidence > 0.9 
                              else ConfidenceLevel.MEDIUM if confidence > 0.7 
                              else ConfidenceLevel.LOW)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            self.logger.info(f"SegmentationAgent: Completed in {execution_time:.2f}s")
            self.logger.info(f"   Paid: {len(paid_customers)} ({result_data['segmentation_summary']['paid_percentage']}%)")
            self.logger.info(f"   Free: {len(free_customers)} ({result_data['segmentation_summary']['free_percentage']}%)")
            self.logger.info(f"   Agent distribution: {result_data['agent_distribution']}")
            
            return AgentResult(
                agent_name=self.name,
                success=True,
                data=result_data,
                confidence=confidence,
                confidence_level=confidence_level,
                limitations=[f"{len(unknown)} conversations could not be classified"] if unknown else [],
                sources=["Intercom admin_assignee_id", "Conversation text analysis"],
                execution_time=execution_time,
                token_count=0  # Rule-based, no LLM
            )
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            self.logger.error(f"SegmentationAgent error: {e}")
            
            return AgentResult(
                agent_name=self.name,
                success=False,
                data={},
                confidence=0.0,
                confidence_level=ConfidenceLevel.LOW,
                error_message=str(e),
                execution_time=execution_time
            )
    
    def _classify_conversation(self, conv: Dict) -> tuple[str, str]:
        """
        Classify conversation by tier and agent type
        
        Returns:
            (segment, agent_type) where:
            segment: 'paid', 'free', 'unknown'
            agent_type: 'escalated', 'horatio', 'boldr', 'fin_ai', 'unknown'
        """
        text = conv.get('full_text', '').lower()
        assignee = str(conv.get('admin_assignee_id', '')).lower()
        ai_participated = conv.get('ai_agent_participated', False)
        
        # Check for escalation (senior staff)
        for name in self.escalation_names:
            if name in text or name in assignee:
                return 'paid', 'escalated'
        
        # Check for Tier 1 agents
        if re.search(self.tier1_patterns['horatio'], text) or 'horatio' in assignee:
            return 'paid', 'horatio'
        
        if re.search(self.tier1_patterns['boldr'], text) or 'boldr' in assignee:
            return 'paid', 'boldr'
        
        # Check for human admin (generic)
        if conv.get('admin_assignee_id'):
            return 'paid', 'unknown'  # Has human but can't identify which
        
        # AI-only conversation
        if ai_participated and not conv.get('admin_assignee_id'):
            return 'free', 'fin_ai'
        
        # Cannot determine
        return 'unknown', 'unknown'

