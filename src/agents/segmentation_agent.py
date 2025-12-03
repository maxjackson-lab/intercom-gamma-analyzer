"""
SegmentationAgent: Separates paid customers (human support) from free customers (AI-only).

Purpose:
- Identify conversations with human agent involvement
- Separate Fin AI-only conversations
- Optionally detect agent types and escalation chains (Horatio, Boldr, Escalated)

Performance Modes:
- track_escalations=False (default): Fast mode for Hilary topic cards
  - Only detects: Paid (Fin-only vs Human) and Free (Fin-only)
  - ~30% faster, skips detailed email parsing
  
- track_escalations=True: Detailed mode for operational metrics
  - Tracks: Fin→Horatio, Fin→Boldr, Fin→Senior, Direct Human
  - Use for: Agent performance analysis, operational reports
  - Slower due to email extraction and pattern matching
"""

import logging
import re
from typing import Dict, Any, List, Optional, Tuple, Callable
from datetime import datetime
from pydantic import ValidationError

from src.agents.base_agent import BaseAgent, AgentResult, AgentContext, ConfidenceLevel
from src.models.analysis_models import CustomerTier, SegmentationPayload
from src.services.fin_escalation_analyzer import is_fin_resolved
from src.utils.conversation_utils import extract_conversation_text

logger = logging.getLogger(__name__)

BILLING_KEYWORD_PATTERNS = {
    'refund': re.compile(r'\brefund(?:ed|s|ing)?\b'),
    'charged': re.compile(r'\bcharg(?:e|ed|es|ing)\b'),
    'invoice': re.compile(r'\binvoice(s)?\b'),
    'chargeback': re.compile(r'\bchargeback(s)?\b'),
    'subscription': re.compile(r'\bsubscription\b'),
    'payment': re.compile(r'\bpayment(?:s)?\b'),
    'billing': re.compile(r'\bbilling\b'),
    'credit card': re.compile(r'\bcredit\s+card\b'),
    'receipt': re.compile(r'\breceipt\b'),
}

STRONG_BILLING_TERMS = {'refund', 'charged', 'invoice', 'chargeback'}


def is_sal_or_fin(author: Dict) -> bool:
    """
    Determine if an admin author is actually Sal/Fin AI (not a human admin).
    
    Sal/Support Sal appears as an 'admin' in Intercom conversation_parts,
    but is actually Fin AI, not a human support agent.
    
    Args:
        author: Author dict with 'name', 'email', 'id' fields
        
    Returns:
        True if this is Sal/Fin AI, False if real human admin
    """
    if not author:
        return False
        
    name = author.get('name', '').lower()
    email = author.get('email', '').lower()
    author_id = str(author.get('id', '')).lower()
    
    # Check for Sal/Finn indicators
    is_sal = (
        'sal' in name or
        'support sal' in name or
        'sal' in email or
        'finn' in name or
        author_id == 'bot'  # Some systems mark Sal as bot
    )
    
    return is_sal


class SegmentationAgent(BaseAgent):
    """
    Agent specialized in customer tier and agent type segmentation.
    
    Note: This agent relies on optional Intercom fields:
    - `ai_agent` object: May be absent; contains optional `resolution_state` field
    - `ai_agent.resolution_state`: Optional field indicating if Fin resolved the conversation
    - `admin_assignee_id`: May be absent for Fin-only conversations
    - `assignee`: Optional top-level field; use AdminProfileCache to resolve admin details
    
    When `ai_agent` or `resolution_state` are absent, agent falls back to heuristics
    based on conversation state, ratings, reopens, and admin participation.
    """
    
    def __init__(self, track_escalations: bool = True):
        """
        Initialize SegmentationAgent.
        
        Args:
            track_escalations: If True (default), tracks detailed escalation chains (Fin→Horatio, etc.)
                              If False, only does basic Paid/Free segmentation
                              Set to False for Hilary topic cards (faster)
                              Set to True for agent performance/operational metrics
        """
        super().__init__(
            name="SegmentationAgent",
            temperature=0.1,
            model_scope="quick",  # Simple classification task
        )
        
        self.track_escalations = track_escalations
        
        # Agent patterns (only used if track_escalations=True)
        self.escalation_names = ['dae-ho', 'max jackson', 'hilary']
        self.tier1_patterns = {
            'horatio': r'horatio|@horatio\.com|@hirehoratio\.co',
            'boldr': r'\bboldr\b|@boldrimpact\.com'
        }
        self._tier_source_keys = [
            'stripe',
            'schema',
            'custom_attribute',
            'segment_paid_users',
            'billing_keyword_promotion',
            'default_free'
        ]
        self._reset_tier_source_counts()

    def _reset_tier_source_counts(self) -> None:
        """Reset tier source counters for a new execution run."""
        self.tier_source_counts = {key: 0 for key in self._tier_source_keys}

    def _track_tier_source(self, source: str) -> None:
        """Track which data source produced a tier classification."""
        if source not in self.tier_source_counts:
            self.tier_source_counts[source] = 0
        self.tier_source_counts[source] += 1

    def _extract_customer_tier(
        self,
        conv: Dict,
        conversation_text_supplier: Optional[Callable[[], str]] = None,
    ) -> Tuple[CustomerTier, str]:
        """
        Extract and validate customer tier from conversation data.

        PRIORITY ORDER (highest to lowest):
        1. Stripe plan (SOURCE OF TRUTH - billing system knows the real plan)
        2. Pre-validated tier from ConversationSchema
        3. custom_attributes.tier (fallback if Stripe unavailable)
        4. Default to FREE

        Args:
            conv: Conversation dictionary

        Returns:
            CustomerTier enum instance (FREE, TEAM, BUSINESS, PRO, PLUS, or ULTRA)
        """
        conv_id = conv.get('id', 'unknown')
        inferred_tier: Optional[CustomerTier] = None
        tier_source: Optional[str] = None

        contacts_data = conv.get('contacts', {})
        contacts_list = []
        if contacts_data and isinstance(contacts_data, dict):
            contacts_list = contacts_data.get('contacts', []) or []

        # PRIORITY 1: Stripe plan (SOURCE OF TRUTH - billing system is authoritative)
        def _set_tier(candidate: CustomerTier, source: str) -> None:
            nonlocal inferred_tier, tier_source
            if inferred_tier is None:
                inferred_tier = candidate
                tier_source = source

        stripe_tier_set = False
        if contacts_list and inferred_tier is None:
            contact = contacts_list[0]
            custom_attrs = contact.get('custom_attributes', {}) or {}

            stripe_status = custom_attrs.get('stripe_subscription_status')
            stripe_plan = custom_attrs.get('stripe_plan')

            if stripe_status == 'active' and stripe_plan:
                self.logger.debug(f"Found active Stripe subscription '{stripe_plan}' for conversation {conv_id}")
                plan_lower = str(stripe_plan).lower()

                if 'team' in plan_lower:
                    self.logger.debug(f"Detected TEAM tier from Stripe plan for conversation {conv_id}")
                    _set_tier(CustomerTier.TEAM, 'stripe')
                    stripe_tier_set = True
                if 'business' in plan_lower:
                    self.logger.debug(f"Detected BUSINESS tier from Stripe plan for conversation {conv_id}")
                    _set_tier(CustomerTier.BUSINESS, 'stripe')
                    stripe_tier_set = True
                if 'plus' in plan_lower:
                    self.logger.debug(f"Detected PLUS tier from Stripe plan for conversation {conv_id}")
                    _set_tier(CustomerTier.PLUS, 'stripe')
                    stripe_tier_set = True
                if 'pro' in plan_lower:
                    self.logger.debug(f"Detected PRO tier from Stripe plan for conversation {conv_id}")
                    _set_tier(CustomerTier.PRO, 'stripe')
                    stripe_tier_set = True
                if 'ultra' in plan_lower:
                    self.logger.debug(f"Detected ULTRA tier from Stripe plan for conversation {conv_id}")
                    _set_tier(CustomerTier.ULTRA, 'stripe')
                    stripe_tier_set = True

                if not stripe_tier_set:
                    self.logger.warning(
                        f"Active Stripe plan '{stripe_plan}' doesn't match known tiers for conversation {conv_id} "
                        f"- defaulting to TEAM"
                    )
                    _set_tier(CustomerTier.TEAM, 'stripe')

        # PRIORITY 2: Pre-validated tier from ConversationSchema (if Stripe not available)
        if inferred_tier is None:
            tier = conv.get('tier')
        else:
            tier = None
        if isinstance(tier, CustomerTier) and inferred_tier is None:
            self.logger.debug(f"No Stripe data, using pre-validated tier {tier.value} for conversation {conv_id}")
            _set_tier(tier, 'schema')
        elif tier and isinstance(tier, str) and tier.strip() and inferred_tier is None:
            matched_tier = self._match_tier_string(tier)
            if matched_tier:
                self.logger.debug(
                    f"No Stripe data, extracted tier {matched_tier.value} from top-level string for conversation {conv_id}"
                )
                _set_tier(matched_tier, 'schema')
            else:
                self.logger.debug(f"Top-level tier string '{tier}' did not match any CustomerTier enum for conversation {conv_id}")

        # PRIORITY 3: custom_attributes.tier string (fallback if Stripe and pre-validated unavailable)
        if inferred_tier is None and contacts_list:
            contact = contacts_list[0]
            custom_attrs = contact.get('custom_attributes', {}) or {}
            contact_tier = custom_attrs.get('tier')
            matched_tier = self._match_tier_string(contact_tier)
            if matched_tier:
                self.logger.debug(f"Extracted tier {matched_tier.value} from contact custom_attributes for conversation {conv_id}")
                _set_tier(matched_tier, 'custom_attribute')

        if inferred_tier is None:
            custom_attrs = conv.get('custom_attributes', {}) or {}
            conv_tier = custom_attrs.get('tier')
            matched_tier = self._match_tier_string(conv_tier)
            if matched_tier:
                self.logger.debug(f"Extracted tier {matched_tier.value} from conversation custom_attributes for conversation {conv_id}")
                _set_tier(matched_tier, 'custom_attribute')
            elif conv_tier:
                self.logger.debug(f"Unknown tier value '{conv_tier}' for conversation {conv_id}, defaulting to FREE baseline")

        # PRIORITY 4: Check "Paid Users" segment as final fallback before FREE
        if inferred_tier is None and contacts_list:
            contact = contacts_list[0]
            segments = contact.get('segments')
            if isinstance(segments, dict):
                segment_entries = segments.get('segments') or []
                for segment in segment_entries:
                    if segment.get('name') == 'Paid Users':
                        self.logger.debug(
                            f"Contact is in 'Paid Users' segment for conversation {conv_id}, defaulting to TEAM (lowest paid tier)"
                        )
                        _set_tier(CustomerTier.TEAM, 'segment_paid_users')
                        break

        if inferred_tier is None:
            self.logger.debug(f"No tier data found for conversation {conv_id}, defaulting to FREE")
            inferred_tier = CustomerTier.FREE
            tier_source = 'default_free'

        if inferred_tier == CustomerTier.FREE:
            return self._apply_billing_keyword_promotion(
                conv_id=conv_id,
                base_tier=inferred_tier,
                tier_source=tier_source or 'default_free',
                conversation_text_supplier=conversation_text_supplier,
            )

        return inferred_tier, tier_source or 'schema'

    def _match_tier_string(self, tier_value: Optional[Any]) -> Optional[CustomerTier]:
        """Helper to normalize arbitrary tier strings into CustomerTier values."""
        if not tier_value or not isinstance(tier_value, str):
            return None
        tier_string_lower = tier_value.strip().lower()
        if not tier_string_lower:
            return None
        for tier_enum in CustomerTier:
            if tier_enum.value == tier_string_lower:
                return tier_enum
        return None

    def _apply_billing_keyword_promotion(
        self,
        *,
        conv_id: str,
        base_tier: CustomerTier,
        tier_source: str,
        conversation_text_supplier: Optional[Callable[[], str]] = None,
    ) -> Tuple[CustomerTier, str]:
        """Promote Free tier conversations to TEAM if strong billing language is detected."""
        if conversation_text_supplier is None:
            return base_tier, tier_source

        text = conversation_text_supplier()
        matched_keyword = self._detect_strong_billing_keyword(text)

        if matched_keyword:
            self.logger.info(
                f"Conversation {conv_id}: tier promotion {base_tier.value}→TEAM "
                f"(original_source={tier_source}, reason=billing_keyword:{matched_keyword})"
            )
            return CustomerTier.TEAM, 'billing_keyword_promotion'

        return base_tier, tier_source

    def _detect_strong_billing_keyword(self, text: str) -> Optional[str]:
        """Return the matched strong billing keyword if present."""
        if not text:
            return None
        for term in STRONG_BILLING_TERMS:
            pattern = BILLING_KEYWORD_PATTERNS.get(term)
            if pattern and pattern.search(text):
                return term
        return None

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
            self._reset_tier_source_counts()
            
            # Segment conversations
            paid_customers = []
            free_customers = []
            unknown = []
            
            agent_distribution = {
                # ESCALATION CHAINS (with Fin)
                'fin_only': [],                    # Just Fin, no escalation
                'fin_to_horatio': [],              # Fin → Horatio
                'fin_to_boldr': [],                # Fin → Boldr
                'fin_to_vendor_to_senior': [],     # Fin → Vendor → Senior Staff
                'fin_to_senior_direct': [],        # Fin → Senior Staff (direct)
                
                # DIRECT HUMAN (no Fin)
                'escalated': [],     # Senior staff only (no Fin)
                'horatio': [],       # Horatio only (no Fin)
                'boldr': [],         # Boldr only (no Fin)
                
                # LEGACY/COMPATIBILITY
                'fin_resolved': [],  # Legacy: Fin AI resolved (paid tier) - map to fin_only
                'fin_ai': [],        # Fin AI only (free tier)
                'unknown': []        # Unclassified
            }
            agent_assignments: Dict[str, Dict[str, Any]] = {}

            conversation_text_cache: Dict[str, str] = {}

            def _get_cached_text(conv_id: str, conv_obj: Dict) -> str:
                cached = conversation_text_cache.get(conv_id)
                if cached is not None:
                    return cached
                text_value = extract_conversation_text(conv_obj, clean_html=True).lower()
                conversation_text_cache[conv_id] = text_value
                return text_value
            
            tier_distribution = {'free': 0, 'team': 0, 'business': 0, 'pro': 0, 'plus': 0, 'ultra': 0, 'unknown': 0}
            defaulted_tier_count = 0

            for conv in conversations:
                conv_id = str(conv.get('id') or len(agent_assignments))

                def _conversation_text_supplier(conv_id: str = conv_id, conv_obj: Dict = conv) -> str:
                    return _get_cached_text(conv_id, conv_obj)

                tier, tier_source = self._extract_customer_tier(
                    conv,
                    conversation_text_supplier=_conversation_text_supplier,
                )
                self._track_tier_source(tier_source)
                if tier_source == 'default_free':
                    defaulted_tier_count += 1

                tier_key = tier.value if isinstance(tier, CustomerTier) else 'unknown'
                if tier_key in tier_distribution:
                    tier_distribution[tier_key] += 1
                else:
                    tier_distribution['unknown'] += 1

                conversation_text_for_classification = (
                    _conversation_text_supplier() if self.track_escalations else None
                )
                segment, agent_type, vendor_label = self._classify_conversation(
                    conv,
                    precomputed_tier=tier,
                    conversation_text=conversation_text_for_classification,
                )

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

                agent_assignments[conv_id] = {
                    'segment': segment,
                    'agent_type': agent_type,
                    'vendor': vendor_label,
                    'tier': tier.value,
                    'tier_source': tier_source
                }

            # Log tier distribution
            total = len(conversations)
            if total > 0:
                free_pct = round(tier_distribution['free'] / total * 100, 1)
                team_pct = round(tier_distribution['team'] / total * 100, 1)
                business_pct = round(tier_distribution['business'] / total * 100, 1)
                pro_pct = round(tier_distribution['pro'] / total * 100, 1)
                plus_pct = round(tier_distribution['plus'] / total * 100, 1)
                ultra_pct = round(tier_distribution['ultra'] / total * 100, 1)
                
                self.logger.info(f"Tier distribution: {tier_distribution}")
                self.logger.info(
                    f"   Free: {tier_distribution['free']} ({free_pct}%), "
                    f"Team: {tier_distribution['team']} ({team_pct}%), "
                    f"Business: {tier_distribution['business']} ({business_pct}%), "
                    f"Pro: {tier_distribution['pro']} ({pro_pct}%), "
                    f"Plus: {tier_distribution['plus']} ({plus_pct}%), "
                    f"Ultra: {tier_distribution['ultra']} ({ultra_pct}%)"
                )
                self.logger.info(f"Tier sources (data provenance): {self.tier_source_counts}")

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
            
            # Extract Fin-only conversations (paid customers resolved by Fin without escalation)
            paid_fin_only_conversations = agent_distribution['fin_only'] + agent_distribution['fin_resolved']  # Include legacy

            # Calculate escalated conversations (Fin → Human chains)
            fin_escalated_conversations = (
                agent_distribution['fin_to_horatio'] +
                agent_distribution['fin_to_boldr'] +
                agent_distribution['fin_to_vendor_to_senior'] +
                agent_distribution['fin_to_senior_direct']
            )
            
            # Calculate direct human conversations (no Fin involvement)
            direct_human_conversations = (
                agent_distribution['escalated'] +
                agent_distribution['horatio'] +
                agent_distribution['boldr'] +
                agent_distribution['unknown']
            )
            
            # Total paid human-involved conversations
            paid_human_conversations = fin_escalated_conversations + direct_human_conversations

            # Prepare result
            result_data = {
                # Tier-specific conversation lists
                'paid_customer_conversations': paid_customers,  # All paid tier (for backward compatibility)
                'paid_fin_resolved_conversations': paid_fin_only_conversations,  # Paid tier, Fin-only (FIXED: was undefined variable)
                'free_fin_only_conversations': free_customers,  # Free tier, Fin-only (renamed)
                'unknown_tier': unknown,

                # Agent distribution (unchanged)
                'agent_distribution': {
                    k: len(v) for k, v in agent_distribution.items()
                },
            'agent_assignments': agent_assignments,

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
                    'paid_fin_resolved_count': len(paid_fin_only_conversations),
                    'paid_fin_resolved_percentage': round(len(paid_fin_only_conversations) / len(conversations) * 100, 1),

                    # Free tier breakdown (always Fin-only)
                    'free_fin_only_count': len(free_customers),
                    'free_fin_only_percentage': round(len(free_customers) / len(conversations) * 100, 1),

                    # Tier data quality
                    'tier_distribution': tier_distribution,  # Include tier breakdown in summary
                    'tier_sources': dict(self.tier_source_counts),

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
            self.logger.info(f"      - Fin Resolved: {len(paid_fin_only_conversations)} ({result_data['segmentation_summary']['paid_fin_resolved_percentage']}%)")
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
    
    def _determine_ai_participation(self, conv: Dict) -> bool:
        """
        Determine if Fin AI participated in conversation using SDK-compliant precedence.
        
        Precedence order (highest to lowest):
        1. ai_agent object presence (SDK spec - most reliable)
        2. ai_agent_participated boolean field (legacy/fallback)
        3. Content heuristic: conversation starts with "Finn" (legacy)
        
        Args:
            conv: Conversation dictionary
            
        Returns:
            True if Fin AI participated, False otherwise
            
        Note:
            Per Intercom SDK spec, ai_agent field is OPTIONAL and may be absent.
            When present, it indicates Fin AI participated regardless of boolean field.
        """
        conv_id = conv.get('id', 'unknown')
        
        # Priority 1: Check for ai_agent object (SDK spec)
        # ai_agent field is OPTIONAL per SDK - may be absent or None
        ai_agent = conv.get('ai_agent')
        if ai_agent is not None:
            # ai_agent object exists -> Fin participated
            self.logger.debug(f"Conversation {conv_id}: ai_agent object present -> Fin participated")
            return True
        
        # Priority 2: Check ai_agent_participated boolean field (fallback)
        ai_participated = conv.get('ai_agent_participated')
        if ai_participated is not None:
            # Use boolean value
            self.logger.debug(f"Conversation {conv_id}: ai_agent_participated={ai_participated}")
            return bool(ai_participated)
        
        # Priority 3: Content heuristic - check if starts with "Finn" (legacy fallback)
        if self._starts_with_finn(conv):
            self.logger.debug(f"Conversation {conv_id}: Starts with 'Finn' -> Fin participated (heuristic)")
            return True
        
        # No evidence of Fin participation
        self.logger.debug(f"Conversation {conv_id}: No Fin participation detected")
        return False
    
    def _starts_with_finn(self, conv: Dict) -> bool:
        """
        Check if conversation starts with "Finn" (reliable indicator of Fin AI).
        
        All Fin conversations in your Intercom data start with "Finn" (two n's).
        This is a reliable fallback when ai_agent_participated might be missing.
        """
        source_body = conv.get('source', {}).get('body', '').strip()
        
        # Check first line/paragraph for "Finn"
        if source_body.lower().startswith('finn'):
            return True
        
        # Also check first conversation part
        parts = conv.get('conversation_parts', {}).get('conversation_parts', [])
        if parts:
            first_part = parts[0].get('body', '').strip()
            if first_part.lower().startswith('finn'):
                return True
        
        return False
    
    def _classify_conversation(
        self,
        conv: Dict,
        precomputed_tier: Optional[CustomerTier] = None,
        conversation_text: Optional[str] = None,
    ) -> tuple[str, str, Optional[str]]:
        """
        Classify conversation by customer tier and optionally ESCALATION CHAIN.

        Detects three escalation scenarios (if track_escalations=True):
        1. JUST FIN - Resolved by Fin alone, no human involvement
        2. FIN → VENDOR - Started with Fin, escalated to Horatio or Boldr
        3. FIN → VENDOR → SENIOR - Started with Fin, escalated through vendor to senior staff

        Tier-first classification:
        1. Extract customer tier (Free/Team/Business/Pro/Plus/Ultra)
        2. Free tier → always ('free', 'fin_ai') regardless of admin assignment
        3. Paid tier → detect escalation chain (if enabled) or simple Paid/Fin split

        Returns:
            (segment, agent_type, vendor_label) where:
            segment: 'paid', 'free', 'unknown'
            agent_type: 'fin_only', 'fin_to_horatio', 'fin_to_boldr', 'fin_to_vendor_to_senior', 
                       'escalated', 'horatio', 'boldr', 'fin_ai', 'unknown'
            vendor_label: 'horatio', 'boldr', 'senior', 'fin', 'mixed', 'team_queue', 'unknown', or None
        """
        conv_id = conv.get('id', 'unknown')
        detected_vendor: Optional[str] = None

        # Step 1: Extract tier FIRST (tier-first classification)
        tier = precomputed_tier or self._extract_customer_tier(conv)[0]
        
        # Paid tiers: TEAM, BUSINESS, PRO, PLUS, ULTRA
        is_paid_tier = tier in [CustomerTier.TEAM, CustomerTier.BUSINESS, CustomerTier.PRO, CustomerTier.PLUS, CustomerTier.ULTRA]
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
            return ('free', 'fin_ai', 'fin')

        # Step 3: Paid tier classification
        
        # FAST PATH: If not tracking escalations, just check if Fin resolved it
        if not self.track_escalations:
            ai_participated = self._determine_ai_participation(conv)
            admin_assignee_id = conv.get('admin_assignee_id')
            
            # Simple logic: Did Fin resolve it without human?
            if ai_participated and not admin_assignee_id:
                # Fin-only (no human)
                return ('paid', 'fin_only', 'fin')
            else:
                # Has human involvement - perform lightweight vendor detection
                # Reuse minimal subset of detailed path logic without regex scanning
                admin_emails = []
                
                # 1. Conversation parts
                conversation_parts_data = conv.get('conversation_parts', {}) or {}
                conv_parts = conversation_parts_data.get('conversation_parts', []) or []
                for part in conv_parts:
                    author = part.get('author', {})
                    if author.get('type') == 'admin':
                        if not is_sal_or_fin(author):
                            email = author.get('email')
                            if email:
                                admin_emails.append(email.lower())
                
                # 2. Source author
                source = conv.get('source', {}) or {}
                source_author = source.get('author', {})
                if source_author.get('type') == 'admin':
                    if not is_sal_or_fin(source_author):
                        email = source_author.get('email')
                        if email:
                            admin_emails.append(email.lower())
                            
                # 3. Assignee
                assignee_data = conv.get('assignee')
                if assignee_data and isinstance(assignee_data, dict):
                    assignee_email = assignee_data.get('email')
                    if assignee_email:
                        admin_emails.append(assignee_email.lower())
                
                # Check for vendor markers
                detected_vendor = 'unknown'
                has_horatio = False
                has_boldr = False
                
                for email in admin_emails:
                    if 'horatio' in email or 'hirehoratio' in email:
                        has_horatio = True
                    if 'boldr' in email:
                        has_boldr = True
                
                if has_horatio and has_boldr:
                    detected_vendor = 'mixed'
                elif has_horatio:
                    detected_vendor = 'horatio'
                elif has_boldr:
                    detected_vendor = 'boldr'
                
                return ('paid', 'unknown', detected_vendor)
        
        # DETAILED PATH: Track full escalation chains
        # Extract actual conversation text for vendor/staff detection
        if conversation_text is None:
            text = extract_conversation_text(conv, clean_html=True).lower()
        else:
            text = conversation_text
        ai_participated = self._determine_ai_participation(conv)
        starts_with_finn = self._starts_with_finn(conv)
        
        # Get ai_agent object with resolution data (per Intercom SDK spec)
        # NOTE: ai_agent field is OPTIONAL - may be absent or None
        ai_agent = conv.get('ai_agent')
        ai_resolution_state = None
        
        # Explicit null checks for optional ai_agent.resolution_state field
        if ai_agent is not None and isinstance(ai_agent, dict):
            ai_resolution_state = ai_agent.get('resolution_state')
            # resolution_state may also be None even when ai_agent exists
            if ai_resolution_state is not None:
                self.logger.debug(f"Conversation {conv_id}: ai_agent.resolution_state = {ai_resolution_state}")
            else:
                self.logger.debug(f"Conversation {conv_id}: ai_agent present but resolution_state is None")
        else:
            self.logger.debug(f"Conversation {conv_id}: ai_agent field is absent or None")

        # Log conversation data for debugging (ai_participated is now from helper)
        self.logger.debug(
            f"Classifying paid tier conversation {conv_id}: "
            f"admin_assignee_id={conv.get('admin_assignee_id')}, "
            f"ai_participated={ai_participated} (via _determine_ai_participation), "
            f"ai_resolution_state={ai_resolution_state}"
        )
        
        # Extract admin emails from conversation parts and any assignee fields
        admin_emails = []
        
        # Check conversation parts for admin emails (handle None case)
        # NOTE: Filter out Sal/Support Sal as Sal is Fin AI, not a human admin
        conversation_parts_data = conv.get('conversation_parts', {})
        if conversation_parts_data is None:
            conversation_parts_data = {}
        conv_parts = conversation_parts_data.get('conversation_parts', [])
        for part in conv_parts:
            author = part.get('author', {})
            if author.get('type') == 'admin':
                # Skip Sal/Support Sal (Fin AI, not human)
                if not is_sal_or_fin(author):
                    email = author.get('email', '')
                    if email:
                        admin_emails.append(email.lower())
        
        # Check source/initial message for admin email
        # NOTE: Filter out Sal/Support Sal as Sal is Fin AI, not a human admin
        source = conv.get('source', {})
        source_author = source.get('author', {})
        if source_author.get('type') == 'admin':
            # Skip Sal/Support Sal (Fin AI, not human)
            if not is_sal_or_fin(source_author):
                email = source_author.get('email', '')
                if email:
                    admin_emails.append(email.lower())
        
        # Check top-level assignee email if available
        # NOTE: `assignee` field may be absent; `assignee.email` is per admin_assignee structure
        # For reliable admin email resolution, use AdminProfileCache with admin_assignee_id
        assignee_data = conv.get('assignee')
        if assignee_data is not None and isinstance(assignee_data, dict):
            assignee_email = assignee_data.get('email')
            if assignee_email:
                admin_emails.append(assignee_email.lower())
                self.logger.debug(f"Conversation {conv_id}: Found assignee email: {assignee_email}")
        
        # Alternative: Resolve admin_assignee_id via AdminProfileCache for reliable email
        # admin_assignee_id = conv.get('admin_assignee_id')
        # if admin_assignee_id:
        #     from src.services.admin_profile_cache import AdminProfileCache
        #     cache = AdminProfileCache()
        #     admin_profile = cache.get_admin_profile(admin_assignee_id)
        #     if admin_profile and admin_profile.get('email'):
        #         admin_emails.append(admin_profile['email'].lower())
        
        # Log extracted admin emails for debugging
        if admin_emails:
            self.logger.debug(f"Conversation {conv_id}: Found {len(admin_emails)} admin emails: {admin_emails}")
        else:
            self.logger.debug(f"Conversation {conv_id}: No admin emails found (might be Support Sal or bot)")
        
        # DETECT ESCALATION CHAIN - Don't return early, collect ALL agents
        has_senior_staff = False
        has_horatio = False
        has_boldr = False
        
        # Check for senior staff (Dae-Ho, Max, Hilary)
        for name in self.escalation_names:
            if name in text:
                has_senior_staff = True
                self.logger.info(f"✓ Senior staff detected via text: {name}")
                break
            # Also check admin emails
            for email in admin_emails:
                if name.replace(' ', '.') in email or name.replace(' ', '') in email:
                    has_senior_staff = True
                    self.logger.info(f"✓ Senior staff detected via email: {email}")
                    break
        
        # Check for vendor agents (Horatio/Boldr) via email domains
        for email in admin_emails:
            self.logger.debug(f"Checking email for agent type: {email}")
            
            # Horatio detection
            if 'horatio' in email or 'hirehoratio' in email:
                has_horatio = True
                self.logger.info(f"✓ Horatio agent detected via email: {email}")
            
            # Boldr detection
            if 'boldr' in email:
                has_boldr = True
                self.logger.info(f"✓ Boldr agent detected via email: {email}")
        
        # Fallback to text patterns for vendor detection
        if not has_horatio and re.search(self.tier1_patterns['horatio'], text):
            has_horatio = True
            self.logger.debug(f"Horatio agent detected via text pattern in conversation {conv_id}")
        
        if not has_boldr and re.search(self.tier1_patterns['boldr'], text):
            has_boldr = True
            self.logger.debug(f"Boldr agent detected via text pattern in conversation {conv_id}")
        
        # Consolidate vendor label if detected
        if has_horatio and has_boldr:
            detected_vendor = 'mixed'
        elif has_horatio:
            detected_vendor = 'horatio'
        elif has_boldr:
            detected_vendor = 'boldr'

        # NOW DETERMINE ESCALATION CHAIN based on detected agents
        # Check if Fin was involved (already determined via _determine_ai_participation)
        fin_involved = ai_participated
        
        if fin_involved:
            self.logger.info(f"Conversation {conv_id}: Fin detected (via _determine_ai_participation: {ai_participated})")
        
        # ESCALATION CHAIN LOGIC:
        # Priority: Senior Staff > Vendor > Fin Only
        
        if fin_involved:
            # Scenario 3: FIN → VENDOR → SENIOR STAFF
            if has_senior_staff and (has_horatio or has_boldr):
                vendor = 'horatio' if has_horatio and not has_boldr else 'boldr' if has_boldr and not has_horatio else detected_vendor
                self.logger.info(f"🔥 ESCALATION CHAIN: Fin → {(vendor or 'vendor').title()} → Senior Staff")
                return 'paid', 'fin_to_vendor_to_senior', vendor or 'senior'
            
            # Scenario 2A: FIN → HORATIO
            elif has_horatio:
                self.logger.info(f"📈 ESCALATION CHAIN: Fin → Horatio")
                return 'paid', 'fin_to_horatio', 'horatio'
            
            # Scenario 2B: FIN → BOLDR
            elif has_boldr:
                self.logger.info(f"📈 ESCALATION CHAIN: Fin → Boldr")
                return 'paid', 'fin_to_boldr', 'boldr'
            
            # Edge case: Fin → Senior Staff directly (skip vendor)
            elif has_senior_staff:
                self.logger.info(f"🔥 ESCALATION CHAIN: Fin → Senior Staff (direct)")
                return 'paid', 'fin_to_senior_direct', 'senior'
            
            # Scenario 1: JUST FIN (no escalation)
            else:
                # CRITICAL FIX: Check resolution state before declaring "Fin Only"
                # If routed to team, it's an escalation even if no human picked it up yet
                if ai_resolution_state and ai_resolution_state.lower() in ['routed_to_team', 'escalated', 'handed_off', 'transferred']:
                     self.logger.info(f"📈 ESCALATION: Fin → Team (Pending Pickup)")
                     # Classify as generic human escalation until picked up
                     return 'paid', 'unknown', 'team_queue'

                self.logger.info(f"✅ NO ESCALATION: Just Fin")
                return 'paid', 'fin_only', 'fin'
        
        # NO FIN DETECTED - Direct human handling
        # This means conversation went straight to human without Fin
        if has_senior_staff:
            self.logger.info(f"Human only: Senior staff (no Fin)")
            return 'paid', 'escalated', 'senior'
        elif has_horatio:
            self.logger.info(f"Human only: Horatio (no Fin)")
            return 'paid', 'horatio', 'horatio'
        elif has_boldr:
            self.logger.info(f"Human only: Boldr (no Fin)")
            return 'paid', 'boldr', 'boldr'
        
        # Check for HUMAN admin response in conversation parts (not Sal)
        # NOTE: Sal/Support Sal is Fin AI, not a human admin
        parts_list = conv.get('conversation_parts', {}).get('conversation_parts', [])
        admin_parts = [p for p in parts_list if p.get('author', {}).get('type') == 'admin']
        bot_parts = [p for p in parts_list if p.get('author', {}).get('type') == 'bot']
        
        # Filter out Sal from admin parts (Sal is Fin AI)
        human_admin_parts = []
        for part in admin_parts:
            author = part.get('author', {})
            # Skip Sal/Support Sal (Fin AI)
            if not is_sal_or_fin(author):
                human_admin_parts.append(part)
        
        has_admin_response = len(human_admin_parts) > 0
        has_bot_response = len(bot_parts) > 0
        
        # Legacy fallback for old data without clear Fin markers
        # ai_participated is already determined via _determine_ai_participation()
        if ai_participated:
            # PRIMARY: Use Intercom's official ai_agent.resolution_state field (SDK spec)
            # This is the authoritative source from Intercom about whether Fin resolved it
            if ai_resolution_state:
                self.logger.debug(f"Paid tier: Using ai_agent.resolution_state={ai_resolution_state}")
                
                # Check if escalated to known human agents first (takes priority)
                # If we already detected Horatio/Boldr/Escalated above, we wouldn't be here
                
                if ai_resolution_state.lower() in ['resolved', 'completed', 'closed']:
                    # Intercom says Fin resolved it - trust the SDK
                    self.logger.debug(f"Paid tier: Fin RESOLVED per Intercom SDK (resolution_state={ai_resolution_state})")
                    return 'paid', 'fin_resolved', 'fin'
                elif ai_resolution_state.lower() in ['escalated', 'handed_off', 'transferred']:
                    # Intercom says it was escalated - check if to known agent or unknown
                    self.logger.debug(f"Paid tier: Escalated per Intercom SDK (resolution_state={ai_resolution_state})")
                    # Check for human admin emails to identify which agent
                    if has_admin_response:
                        for part in human_admin_parts:
                            author_email = part.get('author', {}).get('email', '').lower()
                            if author_email and '@' in author_email:
                                if not any(x in author_email for x in ['support', 'fin', 'bot']):
                                    return 'paid', 'unknown', detected_vendor  # Real human escalation
                    return 'paid', 'unknown', detected_vendor  # Escalated but can't identify agent
                else:
                    # Unknown resolution state - fall back to heuristics
                    self.logger.debug(f"Paid tier: Unknown resolution_state '{ai_resolution_state}', using fallback logic")
            
            # FALLBACK: If no ai_resolution_state, use heuristics (legacy conversations)
            if ai_resolution_state is None:
                self.logger.debug(f"Paid tier: No ai_resolution_state, using fallback heuristics")
                
                # Check state, engagement, CSAT, reopens
                user_parts = [p for p in parts_list if p.get('author', {}).get('type') == 'user']
                is_closed = conv.get('state') == 'closed'
                low_engagement = len(user_parts) <= 2
                
                rating_data = conv.get('conversation_rating')
                if isinstance(rating_data, dict):
                    rating = rating_data.get('rating')
                elif isinstance(rating_data, (int, float)):
                    rating = rating_data
                else:
                    rating = None
                has_bad_rating = rating is not None and rating < 3
                
                stats = conv.get('statistics', {})
                reopens = stats.get('count_reopens', 0) if stats and isinstance(stats, dict) else 0
                
                # Check for human escalation indicators
                if has_admin_response:
                    # Has admin + failed resolution signals = escalated
                    if not is_closed or has_bad_rating or reopens > 1:
                        self.logger.debug(f"Paid tier: Fallback - escalated (admin present, poor resolution signals)")
                        return 'paid', 'unknown', detected_vendor
                
                # No human escalation + good signals = Fin resolved
                if (is_closed or low_engagement) and not has_bad_rating and reopens <= 1:
                    self.logger.debug(f"Paid tier: Fallback - Fin resolved (good resolution signals)")
                    return 'paid', 'fin_resolved', 'fin'
                else:
                    self.logger.debug(f"Paid tier: Fallback - Fin resolved (default, ai_participated via helper=True)")
                    return 'paid', 'fin_resolved', 'fin'
        
        # ai_participated=False (via helper) but has admin response → Real human handled without Fin
        if has_admin_response:
            self.logger.debug(f"Paid customer: Human admin (ai_participated via helper=False)")
            return 'paid', 'unknown', detected_vendor
        
        # No AI, no admin → edge case
        if has_bot_response:
            self.logger.debug(f"Paid tier: Bot response but ai_participated via helper=False")
            return 'paid', 'fin_resolved', 'fin'

        # Cannot determine
        self.logger.debug(f"Unable to classify conversation {conv_id} - insufficient data")
        return 'unknown', 'unknown', detected_vendor

