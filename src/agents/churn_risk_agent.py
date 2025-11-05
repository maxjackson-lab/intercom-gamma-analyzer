"""
ChurnRiskAgent - Detects explicit churn signals in conversation content

This agent flags conversations with explicit churn indicators (cancellation language, 
competitor mentions, frustration patterns) for human review. Uses LLM for nuanced 
understanding of customer sentiment and intent.
"""

import logging
import re
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta

from src.agents.base_agent import BaseAgent, AgentResult, ConfidenceLevel, AgentContext
from src.utils.conversation_utils import extract_customer_messages
from src.config.settings import settings


logger = logging.getLogger(__name__)


class ChurnRiskAgent(BaseAgent):
    """Agent that detects explicit churn signals in conversations"""

    # Churn signal patterns
    CANCELLATION_PATTERNS = [
        r'\bcancel(?:ing|lation)?\s+(?:my\s+)?subscription',
        r'\b(?:close|end|terminate)\s+(?:my\s+)?account',
        r'\bunsubscribe',
        r'\brefund\s+(?:and\s+)?cancel',
        r'\bcancel(?:ing|lation)?\s+(?:my\s+)?plan',
    ]
    
    COMPETITOR_NAMES = [
        'Pitch', 'Canva', 'Beautiful.ai', 'Prezi', 'Slides', 
        'Google Slides', 'PowerPoint', 'Keynote'
    ]
    
    FRUSTRATION_PHRASES = [
        'switching to', 'moving to', 'trying', 'considering', 
        'fed up', 'had enough', 'done with', 'looking at'
    ]

    def __init__(self, ai_client=None):
        super().__init__(
            name="ChurnRiskAgent",
            model="gpt-4o",
            temperature=0.3
        )
        self.ai_client = ai_client
        
        # Compile regex patterns for efficiency
        self.cancellation_regex = [re.compile(pattern, re.IGNORECASE) for pattern in self.CANCELLATION_PATTERNS]

    def get_agent_specific_instructions(self) -> str:
        """Return instructions for churn detection"""
        return """
You are analyzing customer conversations for explicit churn signals. Your role is to:

1. **Flag explicit signals** - Detect clear indicators of churn intent (cancellation, competitors, frustration)
2. **Prioritize high-value customers** - Business/Ultra tier customers get highest priority
3. **Provide quotes for evidence** - Include exact customer language showing the signal
4. **Don't predict probability** - Report signals detected, not churn likelihood
5. **Maintain objectivity** - Focus on observable signals, not assumptions

Your goal is to flag conversations that warrant human review and potential intervention.
"""

    def get_task_description(self, context: AgentContext) -> str:
        """Describe the churn detection task"""
        total_convs = len(context.conversations) if context.conversations else 0
        
        # Get tier distribution if available
        segmentation = context.previous_results.get('SegmentationAgent', {}).get('data', {})
        tier_dist = segmentation.get('tier_distribution', {})
        high_value_count = tier_dist.get('business', 0) + tier_dist.get('ultra', 0)
        
        return f"Detect explicit churn signals in {total_convs} conversations ({high_value_count} high-value customers)"

    def format_context_data(self, context: AgentContext) -> Dict[str, Any]:
        """Format summary of available data"""
        conversations = context.conversations or []
        
        # Calculate tier coverage
        tier_coverage = sum(1 for c in conversations if c.get('tier') and c.get('tier') != 'unknown') / len(conversations) if conversations else 0
        csat_coverage = sum(1 for c in conversations if c.get('conversation_rating')) / len(conversations) if conversations else 0
        
        return {
            'total_conversations': len(conversations),
            'tier_coverage': round(tier_coverage, 2),
            'csat_coverage': round(csat_coverage, 2)
        }

    def validate_input(self, context: AgentContext) -> bool:
        """Ensure required data is available"""
        if not context.conversations:
            raise ValueError("No conversations provided for churn analysis")
        
        return True

    def validate_output(self, result: Dict[str, Any]) -> bool:
        """Ensure output contains required fields"""
        required_fields = ['high_risk_conversations', 'risk_breakdown']
        for field in required_fields:
            if field not in result:
                raise ValueError(f"Output missing '{field}' field")
        
        return True

    async def execute(self, context: AgentContext) -> AgentResult:
        """Main execution method for churn detection"""
        start_time = datetime.now()
        
        try:
            # Validate input
            try:
                self.validate_input(context)
            except ValueError as e:
                return AgentResult(
                    agent_name=self.name,
                    success=False,
                    data={'error': str(e)},
                    confidence=0.0,
                    confidence_level=ConfidenceLevel.LOW,
                    limitations=[str(e)],
                    sources=[],
                    execution_time=0.0
                )
            
            # Extract data from context
            conversations = context.conversations
            segmentation_data = context.previous_results.get('SegmentationAgent', {}).get('data', {})
            
            logger.info(f"Scanning {len(conversations)} conversations for churn signals")
            
            # Scan each conversation for churn signals
            high_risk_conversations = []
            signal_distribution = {
                'cancellation_language': 0,
                'competitor_mentioned': 0,
                'frustration_pattern': 0,
                'resolution_failure': 0
            }
            
            for conv in conversations:
                signals, quotes = self._detect_churn_signals(conv)
                
                if signals:
                    # Calculate risk score
                    tier = conv.get('tier', 'free')
                    csat = conv.get('conversation_rating')
                    reopens = conv.get('statistics', {}).get('count_reopens', 0)
                    
                    risk_score = self._calculate_risk_score(signals, tier, csat, reopens)
                    priority = self._determine_priority(tier, risk_score)
                    
                    # Use LLM to analyze nuance if available
                    if self.ai_client:
                        llm_analysis = await self._analyze_conversation_with_llm(conv, signals, quotes)
                    else:
                        llm_analysis = None
                    
                    high_risk_conversations.append({
                        'conversation_id': conv.get('id'),
                        'risk_score': risk_score,
                        'tier': tier,
                        'signals': signals,
                        'quotes': quotes,
                        'intercom_url': self._build_intercom_url(conv.get('id')),
                        'priority': priority,
                        'created_at': conv.get('created_at'),
                        'reopens': reopens,
                        'csat': csat,
                        'llm_analysis': llm_analysis
                    })
                    
                    # Update signal distribution
                    for signal in signals:
                        if signal in signal_distribution:
                            signal_distribution[signal] += 1
            
            # Sort by priority and risk score
            priority_order = {'immediate': 0, 'high': 1, 'medium': 2, 'low': 3}
            high_risk_conversations.sort(
                key=lambda x: (priority_order.get(x['priority'], 4), -x['risk_score'])
            )
            
            # Build risk breakdown by tier
            risk_breakdown = {
                'high_value_at_risk': sum(1 for c in high_risk_conversations if c['tier'] in ['business', 'ultra']),
                'medium_value_at_risk': sum(1 for c in high_risk_conversations if c['tier'] in ['team', 'pro']),
                'low_value_at_risk': sum(1 for c in high_risk_conversations if c['tier'] == 'free'),
                'total_risk_signals': sum(signal_distribution.values())
            }
            
            # Build result
            result_data = {
                'high_risk_conversations': high_risk_conversations,
                'risk_breakdown': risk_breakdown,
                'signal_distribution': signal_distribution
            }
            
            # Validate output
            try:
                self.validate_output(result_data)
            except ValueError as e:
                logger.error(f"Output validation failed: {e}")
                return AgentResult(
                    agent_name=self.name,
                    success=False,
                    data={'error': str(e)},
                    confidence=0.0,
                    confidence_level=ConfidenceLevel.LOW,
                    limitations=[str(e)],
                    sources=[],
                    execution_time=0.0
                )
            
            # Calculate confidence
            tier_coverage = sum(1 for c in conversations if c.get('tier') and c.get('tier') != 'unknown') / len(conversations)
            overall_confidence = 0.9 if tier_coverage > 0.7 else 0.7
            confidence_level = self._calculate_confidence_level(overall_confidence)
            
            # Build limitations
            limitations = []
            if tier_coverage < 0.7:
                limitations.append(f"Tier data only available for {int(tier_coverage*100)}% of conversations")
            if len(high_risk_conversations) == 0:
                limitations.append("No explicit churn signals detected")
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return AgentResult(
                agent_name=self.name,
                success=True,
                data=result_data,
                confidence=round(overall_confidence, 2),
                confidence_level=confidence_level,
                limitations=limitations,
                sources=['conversation_content', 'customer_messages'],
                execution_time=execution_time
            )
            
        except Exception as e:
            logger.error(f"ChurnRiskAgent execution failed: {e}", exc_info=True)
            execution_time = (datetime.now() - start_time).total_seconds()
            return AgentResult(
                agent_name=self.name,
                success=False,
                data={'error': str(e)},
                confidence=0.0,
                confidence_level=ConfidenceLevel.LOW,
                limitations=[f"Execution failed: {str(e)}"],
                sources=[],
                execution_time=execution_time
            )

    def _detect_churn_signals(self, conversation: Dict) -> Tuple[List[str], List[str]]:
        """Detect churn signals in conversation content"""
        try:
            signals = []
            quotes = []
            
            # Extract customer messages
            customer_messages = extract_customer_messages(conversation)
            full_text = " ".join(customer_messages).lower()
            
            # 1. Check for cancellation language
            for pattern in self.cancellation_regex:
                match = pattern.search(full_text)
                if match:
                    signals.append('cancellation_language')
                    quote = self._extract_sentence_context(full_text, match.start())
                    quotes.append(quote)
                    break
            
            # 2. Check for competitor mentions
            for competitor in self.COMPETITOR_NAMES:
                if competitor.lower() in full_text:
                    # Check if in context of switching/comparing
                    for phrase in self.FRUSTRATION_PHRASES:
                        if phrase in full_text and competitor.lower() in full_text:
                            signals.append('competitor_mentioned')
                            # Extract quote showing competitor mention
                            idx = full_text.find(competitor.lower())
                            quote = self._extract_sentence_context(full_text, idx)
                            quotes.append(quote)
                            break
                    break
            
            # 3. Check for frustration + high-value pattern
            csat = conversation.get('conversation_rating')
            reopens = conversation.get('statistics', {}).get('count_reopens', 0)
            tier = conversation.get('tier', 'free')
            
            if csat and csat < 3 and reopens > 1 and tier in ['business', 'ultra']:
                signals.append('frustration_pattern')
                # Extract frustrated language
                for phrase in self.FRUSTRATION_PHRASES:
                    if phrase in full_text:
                        idx = full_text.find(phrase)
                        quote = self._extract_sentence_context(full_text, idx)
                        quotes.append(quote)
                        break
            
            # 4. Check for resolution failure
            state = conversation.get('state')
            created_at = conversation.get('created_at')
            
            if reopens > 2 and state != 'closed':
                # Check if conversation is older than 7 days
                if created_at:
                    if isinstance(created_at, int):
                        created_dt = datetime.fromtimestamp(created_at)
                    else:
                        created_dt = datetime.fromisoformat(str(created_at).replace('Z', '+00:00'))
                    
                    days_old = (datetime.now(created_dt.tzinfo) - created_dt).days
                    if days_old > 7:
                        signals.append('resolution_failure')
                        quotes.append(f"Multiple reopens ({reopens}) over {days_old} days without resolution")
            
            return signals, quotes
            
        except Exception as e:
            logger.warning(f"Churn signal detection failed: {e}")
            return [], []

    def _extract_sentence_context(self, text: str, position: int, max_length: int = 150) -> str:
        """Extract sentence containing the match position"""
        try:
            # Find sentence boundaries
            start = max(0, text.rfind('.', 0, position) + 1)
            end = text.find('.', position)
            if end == -1:
                end = len(text)
            else:
                end += 1
            
            sentence = text[start:end].strip()
            
            # Truncate if too long
            if len(sentence) > max_length:
                sentence = sentence[:max_length] + "..."
            
            return sentence
            
        except Exception as e:
            logger.warning(f"Sentence extraction failed: {e}")
            return text[max(0, position-75):position+75]

    def _calculate_risk_score(
        self, 
        signals: List[str], 
        tier: str, 
        csat: Optional[int], 
        reopens: int
    ) -> float:
        """Calculate risk score based on signals and context"""
        base_score = 0.0
        
        # Add points for each signal
        if 'cancellation_language' in signals:
            base_score += 0.4
        if 'competitor_mentioned' in signals:
            base_score += 0.3
        if 'frustration_pattern' in signals:
            base_score += 0.2
        if 'resolution_failure' in signals:
            base_score += 0.2
        
        # Add points for bad CSAT
        if csat and csat < 3:
            base_score += 0.2
        
        # Add points for multiple reopens
        if reopens > 1:
            base_score += min(0.3, reopens * 0.15)
        
        # Apply tier multiplier
        tier_multipliers = {
            'ultra': 1.5,
            'business': 1.5,
            'pro': 1.2,
            'team': 1.2,
            'free': 1.0
        }
        multiplier = tier_multipliers.get(tier, 1.0)
        
        risk_score = min(1.0, base_score * multiplier)
        
        return round(risk_score, 2)

    def _determine_priority(self, tier: str, risk_score: float) -> str:
        """Determine priority level based on tier and risk score"""
        if tier in ['business', 'ultra']:
            if risk_score > 0.7:
                return 'immediate'
            elif risk_score > 0.5:
                return 'high'
            else:
                return 'medium'
        elif tier in ['team', 'pro']:
            if risk_score > 0.7:
                return 'high'
            elif risk_score > 0.5:
                return 'medium'
            else:
                return 'low'
        else:
            if risk_score > 0.7:
                return 'medium'
            else:
                return 'low'

    async def _analyze_conversation_with_llm(
        self, 
        conversation: Dict, 
        signals: List[str], 
        quotes: List[str]
    ) -> Optional[str]:
        """Use LLM to provide nuanced analysis of churn signals"""
        try:
            # Extract customer messages
            customer_messages = extract_customer_messages(conversation)
            
            # Build prompt
            prompt = f"""Analyze this customer conversation for churn risk:

**Detected Signals:** {', '.join(signals)}

**Key Quotes:**
{chr(10).join(f"- {quote}" for quote in quotes)}

**Customer Messages:**
{chr(10).join(customer_messages[:3])}  

Provide:
1. Assessment of churn intent (explicit vs. frustrated exploration)
2. Key concerns expressed by the customer

Keep response concise (3-4 sentences).
"""
            
            messages = [
                {"role": "system", "content": self.get_agent_specific_instructions()},
                {"role": "user", "content": prompt}
            ]
            
            response = await self.ai_client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.warning(f"LLM analysis failed: {e}")
            return None

    def _build_intercom_url(self, conversation_id: str) -> str:
        """Build Intercom URL for conversation"""
        workspace_id = getattr(settings, 'intercom_workspace_id', 'your_workspace')
        return f"https://app.intercom.com/a/apps/{workspace_id}/inbox/inbox/{conversation_id}"

    def _calculate_confidence_level(self, confidence: float) -> ConfidenceLevel:
        """Convert numeric confidence to ConfidenceLevel enum"""
        if confidence >= 0.8:
            return ConfidenceLevel.HIGH
        elif confidence >= 0.6:
            return ConfidenceLevel.MEDIUM
        else:
            return ConfidenceLevel.LOW

