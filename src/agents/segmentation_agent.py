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
from pydantic import ValidationError

from src.agents.base_agent import BaseAgent, AgentResult, AgentContext, ConfidenceLevel
from src.models.analysis_models import CustomerTier, SegmentationPayload

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
            # Check if contact is in "Paid Users" segment or has active Stripe subscription
            if contacts_data and isinstance(contacts_data, dict):
                contacts_list = contacts_data.get('contacts', [])
                if contacts_list and len(contacts_list) > 0:
                    contact = contacts_list[0]
                    
                    # Check if contact has segments information
                    if 'segments' in contact:
                        segments = contact['segments']
                        if 'segments' in segments and len(segments['segments']) > 0:
                            for segment in segments['segments']:
                                if segment.get('name') == 'Paid Users':
                                    self.logger.debug(f"Contact is in 'Paid Users' segment for conversation {conv_id}, defaulting to PRO")
                                    return CustomerTier.PRO
                    
                    # Check Stripe subscription data
                    if 'custom_attributes' in contact:
                        custom_attrs = contact['custom_attributes']
                        
                        # Check for active Stripe subscription
                        stripe_status = custom_attrs.get('stripe_subscription_status')
                        stripe_plan = custom_attrs.get('stripe_plan')
                        
                        if stripe_status == 'active' and stripe_plan:
                            self.logger.debug(f"Contact has active Stripe subscription '{stripe_plan}' for conversation {conv_id}")
                            
                            # Map Stripe plan to CustomerTier
                            plan_lower = stripe_plan.lower()
                            if 'plus' in plan_lower:
                                self.logger.debug(f"Detected PLUS tier from Stripe plan for conversation {conv_id}")
                                return CustomerTier.PLUS
                            elif 'pro' in plan_lower:
                                self.logger.debug(f"Detected PRO tier from Stripe plan for conversation {conv_id}")
                                return CustomerTier.PRO
                            elif 'ultra' in plan_lower:
                                self.logger.debug(f"Detected ULTRA tier from Stripe plan for conversation {conv_id}")
                                return CustomerTier.ULTRA
                            else:
                                # Unknown plan, default to PRO
                                self.logger.debug(f"Unknown Stripe plan '{stripe_plan}', defaulting to PRO for conversation {conv_id}")
                                return CustomerTier.PRO
                    
                    # If no segments info and no Stripe data, check if we can get it from the contact data
                    # This is a fallback for when segments are not included in the contact data
                    self.logger.debug(f"No segments or Stripe information found for conversation {conv_id}, defaulting to FREE")
                else:
                    self.logger.debug(f"No contacts found for conversation {conv_id}, defaulting to FREE")
            else:
                self.logger.debug(f"No contacts data found for conversation {conv_id}, defaulting to FREE")

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
        """
        Validate segmentation results using Pydantic model.
        
        Args:
            result: Raw output dictionary to validate
            
        Returns:
            True if validation passes
            
        Raises:
            ValueError: If validation fails with clear error message
        """
        try:
            # Use Pydantic model for validation
            SegmentationPayload(**result)
            return True
        except ValidationError as e:
            error_msg = f"Segmentation output validation failed: {e}"
            self.logger.error(error_msg)
            raise ValueError(error_msg)
    
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

            # Tier distribution tracking and tier data quality
            tier_distribution = {'free': 0, 'pro': 0, 'plus': 0, 'ultra': 0, 'unknown': 0}
            defaulted_tier_count = 0

            for conv in conversations:
                tier = self._extract_customer_tier(conv)
                if tier == CustomerTier.FREE:
                    tier_distribution['free'] += 1

                    # Check if tier was defaulted (missing from all sources)
                    # Check pre-validated tier
                    has_tier = isinstance(conv.get('tier'), CustomerTier)
                    # Check top-level string tier - must match a valid CustomerTier enum value
                    if not has_tier:
                        top_tier = conv.get('tier')
                        if top_tier and isinstance(top_tier, str) and top_tier.strip():
                            tier_string_lower = top_tier.strip().lower()
                            has_tier = any(tier_enum.value.lower() == tier_string_lower for tier_enum in CustomerTier)
                    # Check contact-level custom attributes - must match a valid CustomerTier enum value
                    if not has_tier:
                        contacts_data = conv.get('contacts', {})
                        if contacts_data and isinstance(contacts_data, dict):
                            contacts_list = contacts_data.get('contacts', [])
                            if contacts_list and len(contacts_list) > 0:
                                contact = contacts_list[0]
                                custom_attrs = contact.get('custom_attributes', {})
                                contact_tier = custom_attrs.get('tier')
                                if contact_tier and isinstance(contact_tier, str) and contact_tier.strip():
                                    tier_string_lower = contact_tier.strip().lower()
                                    has_tier = any(tier_enum.value.lower() == tier_string_lower for tier_enum in CustomerTier)
                    # Check conversation-level custom attributes - must match a valid CustomerTier enum value
                    if not has_tier:
                        custom_attrs = conv.get('custom_attributes', {})
                        conv_tier = custom_attrs.get('tier')
                        if conv_tier and isinstance(conv_tier, str) and conv_tier.strip():
                            tier_string_lower = conv_tier.strip().lower()
                            has_tier = any(tier_enum.value.lower() == tier_string_lower for tier_enum in CustomerTier)

                    if not has_tier:
                        defaulted_tier_count += 1

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

            # Calculate language breakdown
            language_distribution = {}
            for conv in conversations:
                lang = conv.get('custom_attributes', {}).get('Language', 'English')
                language_distribution[lang] = language_distribution.get(lang, 0) + 1
            
            # Sort by count
            sorted_languages = dict(sorted(
                language_distribution.items(),
                key=lambda x: x[1],
                reverse=True
            ))
            
            self.logger.info(f"Language distribution: {sorted_languages}")
            
            # Extract paid_fin_resolved conversations (paid customers resolved by Fin only)
            paid_fin_resolved_conversations = agent_distribution['fin_resolved']

            # Calculate paid_human_conversations (paid customers who escalated to human)
            paid_human_conversations = (
                agent_distribution['escalated'] +
                agent_distribution['horatio'] +
                agent_distribution['boldr'] +
                agent_distribution['unknown']
            )

            # Prepare result
            result_data = {
                # Tier-specific conversation lists
                'paid_customer_conversations': paid_customers,  # All paid tier (for backward compatibility)
                'paid_fin_resolved_conversations': paid_fin_resolved_conversations,  # Paid tier, Fin-only
                'free_fin_only_conversations': free_customers,  # Free tier, Fin-only (renamed)
                'unknown_tier': unknown,

                # Agent distribution (unchanged)
                'agent_distribution': {
                    k: len(v) for k, v in agent_distribution.items()
                },

                # Enhanced segmentation summary
                'segmentation_summary': {
                    # Overall tier breakdown
                    'paid_count': len(paid_customers),
                    'paid_percentage': round(len(paid_customers) / len(conversations) * 100, 1),
                    'free_count': len(free_customers),
                    'free_percentage': round(len(free_customers) / len(conversations) * 100, 1),
                    'unknown_count': len(unknown),

                    # Paid tier breakdown (human vs Fin-resolved)
                    'paid_human_count': len(paid_human_conversations),
                    'paid_human_percentage': round(len(paid_human_conversations) / len(conversations) * 100, 1),
                    'paid_fin_resolved_count': len(paid_fin_resolved_conversations),
                    'paid_fin_resolved_percentage': round(len(paid_fin_resolved_conversations) / len(conversations) * 100, 1),

                    # Free tier breakdown (always Fin-only)
                    'free_fin_only_count': len(free_customers),
                    'free_fin_only_percentage': round(len(free_customers) / len(conversations) * 100, 1),

                    # Tier data quality
                    'tier_distribution': tier_distribution,  # Include tier breakdown in summary
                    
                    # Language/Regional breakdown
                    'language_distribution': sorted_languages,
                    'total_languages': len(sorted_languages),
                    'top_language': list(sorted_languages.keys())[0] if sorted_languages else 'English',
                    'top_language_count': list(sorted_languages.values())[0] if sorted_languages else 0
                }
            }
            
            self.validate_output(result_data)

            # Calculate tier-aware confidence
            # Step 1: Classification confidence (how many conversations were successfully classified)
            classification_confidence = 1.0 - (len(unknown) / len(conversations)) if conversations else 0

            # Step 2: Tier data quality score (how many tiers were defaulted)
            tier_quality_score = 1.0 - (defaulted_tier_count / len(conversations)) if conversations else 0

            # Step 3: Combined confidence (weighted average)
            # Classification success (60%) + Tier data quality (40%)
            final_confidence = (classification_confidence * 0.6) + (tier_quality_score * 0.4)

            # Step 4: Determine confidence level with tier awareness
            if final_confidence > 0.9 and tier_quality_score > 0.9:
                confidence_level = ConfidenceLevel.HIGH
            elif final_confidence > 0.7 or tier_quality_score > 0.7:
                confidence_level = ConfidenceLevel.MEDIUM
            else:
                confidence_level = ConfidenceLevel.LOW

            # Step 5: Build limitations list with tier quality issues
            limitations = []
            if defaulted_tier_count > 0:
                limitations.append(f"{defaulted_tier_count} conversations defaulted to FREE tier (missing tier data)")
            if len(unknown) > 0:
                limitations.append(f"{len(unknown)} conversations could not be classified")
            
            execution_time = (datetime.now() - start_time).total_seconds()

            self.logger.info(f"SegmentationAgent: Completed in {execution_time:.2f}s")
            self.logger.info(f"   Paid Total: {len(paid_customers)} ({result_data['segmentation_summary']['paid_percentage']}%)")
            self.logger.info(f"      - Human Support: {len(paid_human_conversations)} ({result_data['segmentation_summary']['paid_human_percentage']}%)")
            self.logger.info(f"      - Fin Resolved: {len(paid_fin_resolved_conversations)} ({result_data['segmentation_summary']['paid_fin_resolved_percentage']}%)")
            self.logger.info(f"   Free (Fin Only): {len(free_customers)} ({result_data['segmentation_summary']['free_percentage']}%)")
            self.logger.info(f"   Agent distribution: {result_data['agent_distribution']}")
            self.logger.info(f"   Tier data quality: {defaulted_tier_count} conversations defaulted to FREE")

            return AgentResult(
                agent_name=self.name,
                success=True,
                data=result_data,
                confidence=final_confidence,
                confidence_level=confidence_level,
                limitations=limitations,
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

