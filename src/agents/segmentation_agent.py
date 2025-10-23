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
from src.models.analysis_models import CustomerTier

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
            'horatio': r'horatio|@horatio\.com|@hirehoratio\.co',
            'boldr': r'\bboldr\b|@boldrimpact\.com'
        }

    def _extract_customer_tier(self, conv: Dict) -> CustomerTier:
        """
        Extract and validate customer tier from conversation data.

        Checks validated tier first, then falls back to manual extraction.
        Defaults to FREE if tier is missing or invalid.

        Args:
            conv: Conversation dictionary

        Returns:
            CustomerTier enum instance (FREE, PRO, PLUS, or ULTRA)
        """
        conv_id = conv.get('id', 'unknown')

        # Primary source: Pre-validated tier from ConversationSchema
        tier = conv.get('tier')
        if isinstance(tier, CustomerTier):
            self.logger.debug(f"Extracted tier {tier.value} for conversation {conv_id}")
            return tier

        # Handle top-level string tier before falling back to custom attributes
        if tier and isinstance(tier, str) and tier.strip():
            try:
                tier_string_lower = tier.strip().lower()
                for tier_enum in CustomerTier:
                    if tier_enum.value.lower() == tier_string_lower:
                        self.logger.debug(f"Extracted tier {tier_enum.value} from top-level string for conversation {conv_id}")
                        return tier_enum
                # If no match found, log and continue to fallback
                self.logger.debug(f"Top-level tier string '{tier}' did not match any CustomerTier enum for conversation {conv_id}")
            except Exception as e:
                self.logger.debug(f"Error processing top-level tier string for conversation {conv_id}: {e}")

        # Fallback: Manual extraction for backward compatibility
        tier_string = None

        # Check contact-level custom attributes (prioritized)
        contacts_data = conv.get('contacts', {})
        if contacts_data and isinstance(contacts_data, dict):
            contacts_list = contacts_data.get('contacts', [])
            if contacts_list and len(contacts_list) > 0:
                contact = contacts_list[0]
                custom_attrs = contact.get('custom_attributes', {})
                tier_string = custom_attrs.get('tier')

        # Fallback to conversation-level custom attributes
        if not tier_string:
            custom_attrs = conv.get('custom_attributes', {})
            tier_string = custom_attrs.get('tier')

        # Try to match tier string to enum
        if tier_string:
            try:
                tier_string_lower = str(tier_string).lower()
                for tier_enum in CustomerTier:
                    if tier_enum.value.lower() == tier_string_lower:
                        self.logger.debug(f"Extracted tier {tier_enum.value} for conversation {conv_id}")
                        return tier_enum

                # Unknown tier value
                self.logger.debug(f"Unknown tier value '{tier_string}' for conversation {conv_id}, defaulting to FREE")
            except Exception as e:
                self.logger.debug(f"Error matching tier for conversation {conv_id}: {e}, defaulting to FREE")
        else:
            self.logger.warning(f"No tier found for conversation {conv_id}, defaulting to FREE")

        # Default to FREE
        return CustomerTier.FREE

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
                'fin_resolved': [],  # Paid customers resolved by Fin only
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

                # Guard against unexpected agent_type keys
                if agent_type not in agent_distribution:
                    self.logger.warning(f"Unknown agent_type '{agent_type}' for conversation {conv.get('id')}, defaulting to 'unknown' bucket")
                    agent_type = 'unknown'
                
                agent_distribution[agent_type].append(conv)

            # Tier distribution tracking
            tier_distribution = {'free': 0, 'pro': 0, 'plus': 0, 'ultra': 0, 'unknown': 0}
            for conv in conversations:
                tier = self._extract_customer_tier(conv)
                if tier == CustomerTier.FREE:
                    tier_distribution['free'] += 1
                elif tier == CustomerTier.PRO:
                    tier_distribution['pro'] += 1
                elif tier == CustomerTier.PLUS:
                    tier_distribution['plus'] += 1
                elif tier == CustomerTier.ULTRA:
                    tier_distribution['ultra'] += 1
                else:
                    tier_distribution['unknown'] += 1

            # Log tier distribution
            total = len(conversations)
            if total > 0:
                free_pct = round(tier_distribution['free'] / total * 100, 1)
                pro_pct = round(tier_distribution['pro'] / total * 100, 1)
                plus_pct = round(tier_distribution['plus'] / total * 100, 1)
                ultra_pct = round(tier_distribution['ultra'] / total * 100, 1)

                self.logger.info(f"Tier distribution: {tier_distribution}")
                self.logger.info(
                    f"   Free: {tier_distribution['free']} ({free_pct}%), "
                    f"Pro: {tier_distribution['pro']} ({pro_pct}%), "
                    f"Plus: {tier_distribution['plus']} ({plus_pct}%), "
                    f"Ultra: {tier_distribution['ultra']} ({ultra_pct}%)"
                )

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
        Classify conversation by customer tier and agent type.

        Tier-first classification:
        1. Extract customer tier (Free/Pro/Plus/Ultra)
        2. Free tier → always ('free', 'fin_ai') regardless of admin assignment
        3. Paid tier → check for admin involvement:
           - Has admin reply → ('paid', <agent_type>)
           - AI-only → ('paid', 'fin_resolved')

        Returns:
            (segment, agent_type) where:
            segment: 'paid', 'free', 'unknown'
            agent_type: 'escalated', 'horatio', 'boldr', 'fin_ai', 'fin_resolved', 'unknown'
        """
        conv_id = conv.get('id', 'unknown')

        # Step 1: Extract tier FIRST (tier-first classification)
        tier = self._extract_customer_tier(conv)
        self.logger.debug(f"Conversation {conv_id} tier: {tier.value}")

        # Step 2: Free tier early return
        # Free tier customers can ONLY interact with Fin AI (no human escalation possible)
        if tier == CustomerTier.FREE:
            # Edge case: Free tier with admin assignment (abuse/trust & safety)
            admin_assignee_id = conv.get('admin_assignee_id')
            if admin_assignee_id:
                self.logger.warning(
                    f"Free tier customer {conv_id} has admin_assignee_id={admin_assignee_id} "
                    f"- likely abuse/trust & safety case"
                )
            return ('free', 'fin_ai')

        # Step 3: Paid tier classification (only reached for PRO/PLUS/ULTRA)
        text = conv.get('full_text', '').lower()
        ai_participated = conv.get('ai_agent_participated', False)

        # Log conversation data for debugging
        self.logger.debug(
            f"Classifying paid tier conversation {conv_id}: "
            f"admin_assignee_id={conv.get('admin_assignee_id')}, "
            f"ai_participated={ai_participated}"
        )
        
        # Extract admin emails from conversation parts and any assignee fields
        admin_emails = []
        
        # Check conversation parts for admin emails (handle None case)
        conversation_parts_data = conv.get('conversation_parts', {})
        if conversation_parts_data is None:
            conversation_parts_data = {}
        conv_parts = conversation_parts_data.get('conversation_parts', [])
        for part in conv_parts:
            author = part.get('author', {})
            if author.get('type') == 'admin':
                email = author.get('email', '')
                if email:
                    admin_emails.append(email.lower())
        
        # Check source/initial message for admin email
        source = conv.get('source', {})
        if source.get('author', {}).get('type') == 'admin':
            email = source.get('author', {}).get('email', '')
            if email:
                admin_emails.append(email.lower())
        
        # Check top-level assignee email if available
        assignee_data = conv.get('assignee') or {}
        assignee_email = assignee_data.get('email', '')
        if assignee_email:
            admin_emails.append(assignee_email.lower())
        
        # Log extracted admin emails for debugging
        if admin_emails:
            self.logger.debug(f"Found {len(admin_emails)} admin emails: {admin_emails}")
        else:
            self.logger.debug("No admin emails found in conversation")
        
        # Check for escalation (senior staff)
        for name in self.escalation_names:
            if name in text:
                return 'paid', 'escalated'
            # Also check admin emails
            for email in admin_emails:
                if name.replace(' ', '.') in email or name.replace(' ', '') in email:
                    return 'paid', 'escalated'
        
        # Check for Tier 1 agents via email domains (use endswith for exact matching)
        for email in admin_emails:
            if email.endswith('@hirehoratio.co'):
                self.logger.debug(f"Horatio agent detected via email: {email}")
                return 'paid', 'horatio'
            if email.endswith('@boldrimpact.com'):
                self.logger.debug(f"Boldr agent detected via email: {email}")
                return 'paid', 'boldr'
        
        # Fallback to text patterns
        if re.search(self.tier1_patterns['horatio'], text):
            self.logger.debug(f"Horatio agent detected via text pattern in conversation {conv_id}")
            return 'paid', 'horatio'
        
        if re.search(self.tier1_patterns['boldr'], text):
            self.logger.debug(f"Boldr agent detected via text pattern in conversation {conv_id}")
            return 'paid', 'boldr'
        
        # Check for human admin (generic)
        if conv.get('admin_assignee_id') or admin_emails:
            self.logger.debug(f"Generic paid customer detected (unknown agent type) in conversation {conv_id}")
            return 'paid', 'unknown'  # Has human but can't identify which

        # AI-only conversation (paid tier)
        if ai_participated:
            self.logger.debug(f"Paid tier customer {conv_id} resolved by Fin AI only (no human escalation)")
            return 'paid', 'fin_resolved'

        # Cannot determine
        self.logger.debug(f"Unable to classify conversation {conv_id} - insufficient data")
        return 'unknown', 'unknown'

