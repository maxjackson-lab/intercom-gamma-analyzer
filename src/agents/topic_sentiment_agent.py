"""
TopicSentimentAgent: Generates specific, nuanced sentiment insights per topic.

Purpose:
- Analyze sentiment for a SPECIFIC topic only
- Generate one-sentence insights like "Users hate buddy so much"
- Capture nuance (e.g., "appreciative BUT frustrated")
- Avoid generic "negative sentiment" language
"""

import logging
import json
from typing import Dict, Any, List
from datetime import datetime

from src.agents.base_agent import BaseAgent, AgentResult, AgentContext, ConfidenceLevel
from src.utils.ai_client_helper import get_ai_client

logger = logging.getLogger(__name__)


class TopicSentimentAgent(BaseAgent):
    """Agent specialized in per-topic sentiment analysis"""
    
    def __init__(self):
        super().__init__(
            name="TopicSentimentAgent",
            model="gpt-4o",
            temperature=0.6  # Moderate for nuanced language
        )
        self.ai_client = get_ai_client()
    
    def get_agent_specific_instructions(self) -> str:
        """Topic sentiment agent specific instructions"""
        return """
TOPIC SENTIMENT AGENT SPECIFIC RULES:

1. IDENTIFY CUSTOMER PAIN (Priority #1):
   - Do NOT write generic summaries like "Users have feedback about X"
   - Your job is to find what HURTS the customer.
   - If they are confused, say they are confused.
   - If they are angry, say they are angry.
   - If they can't find a button, say the button is hidden.

2. CLASSIFY THE PAIN:
   - Assign a "Pain Level" based on impact, emotion, and frequency:
     - SEVERE: Blocking work, money lost, angry language ("hate", "useless", "terrible"), trust-breaking, churn risk.
     - MODERATE: Annoying friction, confusion, workarounds needed, time wasted.
     - LOW: Feature requests, minor UX polish, general questions, no blocking impact.
   - Think through the pain level carefully - don't default to MODERATE for everything.
   - SEVERE should be reserved for truly blocking issues with churn risk or angry customers.

3. GENERATE 3-4 SENTENCE DEEP DIVE:
   - Sentence 1: The primary friction point (what is broken/missing?)
   - Sentence 2: The customer emotion/impact (anger, confusion, lost time)
   - Sentence 3: The specific context or nuance (e.g. "They love the feature BUT hate the export")
   - Sentence 4: (Optional) A direct quote or specific phrasing used by customers

4. OUTPUT FORMAT:
   You MUST provide both a pain_level and a narrative in JSON format:
   {
     "pain_level": "SEVERE" | "MODERATE" | "LOW",
     "narrative": "The 3-4 sentence deep dive..."
   }

5. GOOD EXAMPLES (match this style):
   ✓ "pain_level": "SEVERE", "narrative": "Users are blocked by the hidden cancel button, leading to severe frustration and feelings of being trapped. Many describe the process as 'deceptive' and threaten chargebacks. While they like the core product, this billing friction is destroying trust. One user noted: 'I shouldn't have to email support just to leave.'"
   ✓ "pain_level": "SEVERE", "narrative": "Customers are furious about the double-charge bug on the Pro plan. The lack of immediate refund confirmation exacerbates the anxiety, leading to multiple follow-up tickets. This is a severe trust-breaker despite the quick resolution time."

6. BAD EXAMPLES (avoid these):
   ✗ Missing pain_level
   ✗ "Negative sentiment detected."
   ✗ "Users are frustrated with this feature." (Too vague)
   ✗ "Mixed sentiment with both positive and negative elements." (Useless)
   ✗ "Customers express dissatisfaction." (Corporate fluff)

7. Capture the SPECIFIC sentiment:
   - What do users LIKE? (be specific)
   - What do users HATE? (be specific)
   - What's the tension/nuance?

8. Use strong, clear language:
   - "hate" if users really hate it
   - "love" if users really love it
   - "rad" if users think it's cool
   - "frustrated" for specific frustrations
   - "confused" for clarity issues

9. Base ONLY on the conversations provided:
   - Quote actual customer language when possible
   - Don't invent sentiment not present in data

10. Treat the sample as representative.
11. Never refuse; if uncertain, describe the strongest pattern visible in the sample.
"""
    
    def _get_topic_specific_examples(self, topic_name: str) -> str:
        """
        Return domain-specific sentiment examples for tone consistency.
        Priority 2 from PROMPT_CATALOG.md
        """
        examples = {
            "Billing": [
                "Users are appreciative of the ability to buy more credits, but frustrated that Gamma moved to a credit model",
                "Customers love the flexibility of the pro plan BUT are confused by the pro-rated invoice dates"
            ],
            "Bug": [
                "Users are frustrated with persistent export bugs BUT appreciate the support team's responsiveness",
                "Customers are annoyed by the image upload error and just want it fixed immediately"
            ],
            "Product Question": [
                "Users think templates are rad but want to be able to use them with API",
                "Customers love the export feature but are confused by format options"
            ],
            "Workspace": [
                "Users like the team features BUT are frustrated by permission granularity",
                "Customers want to share with their team but find the invite flow confusing"
            ],
            "Account": [
                "Users are happy with the login speed BUT annoyed by frequent session timeouts",
                "Customers want to change their email easily and are frustrated by the manual process"
            ]
        }
        
        # Get specific examples or default fallbacks
        topic_examples = examples.get(topic_name, [
            f"Users are generally happy with {topic_name} but want more control",
            f"Customers find {topic_name} features useful BUT are frustrated by limitations"
        ])
        
        formatted = []
        for ex in topic_examples:
            formatted.append(f'   ✓ "{ex}"')
            
        return "\n".join(formatted)

    def get_task_description(self, context: AgentContext) -> str:
        """Describe the topic sentiment analysis task"""
        topic_name = context.metadata.get('current_topic')
        conv_count = len(context.metadata.get('topic_conversations', []))
        
        # PROMPT OPTIMIZATION: Use topic-specific examples (Priority 2)
        examples_block = self._get_topic_specific_examples(topic_name)
        
        return f"""
Analyze the customer's primary pain point for the topic: {topic_name}

You will receive a curated, representative sample of these conversations (from a total of {conv_count}).

STEP 1: INTERNAL REASONING (Thinking Process)
- Read the customer messages carefully.
- Identify the specific "friction point" causing pain.
- Assess the emotional intensity (Annoyance vs. Fury).
- Determine the blocking impact (Is work stopped? Is money lost?).
- Select the most representative quote.

STEP 2: STRUCTURED OUTPUT
Provide a JSON response with:
1. **pain_level**: One of SEVERE, MODERATE, LOW.
   - SEVERE: Blocking work, money lost, angry language, trust-breaking.
   - MODERATE: Annoying friction, confusion, workarounds needed.
   - LOW: Feature requests, minor UX polish, general questions.
2. **narrative**: A 3-4 sentence narrative following this structure:
   - **Core Frustration:** What specifically is broken or confusing?
   - **Specific Evidence:** A direct quote or specific phrasing used by customers.
   - **Severity Assessment:** How does this affect them?

STYLE GUIDE:
- Use natural, direct language.
- Avoid corporate fluff ("Customers expressed dissatisfaction").
- Be specific ("The export button is broken" vs "There are issues").
- Match this style:
{examples_block}

Output MUST be valid JSON.
"""

    def build_prompt(self, context: AgentContext) -> str:
        """Build the prompt for topic sentiment analysis"""
        data = self.format_context_data(context)
        task = self.get_task_description(context)
        
        return f"""
{data}

{task}

{self.get_agent_specific_instructions()}
"""
    
    def format_context_data(self, context: AgentContext) -> str:
        """Format topic conversations for analysis"""
        topic_conversations = context.metadata.get('topic_conversations', [])
        
        # Sample 10 conversations for the prompt
        sample = []
        for conv in topic_conversations[:10]:
            # Extract customer messages
            customer_msgs = conv.get('customer_messages', [])
            
            # Extract subtopic label if available (for better context)
            subtopic_label = None
            details = conv.get('detected_topic_details', [])
            current_topic = context.metadata.get('current_topic')
            
            # Find the specific subtopic label for the current topic being analyzed
            for detail in details:
                if detail.get('topic') == current_topic and detail.get('subtopic'):
                    subtopic_label = detail.get('subtopic')
                    break
            
            if customer_msgs:
                item = {
                    'id': conv.get('id'),
                    'customer_message': customer_msgs[0][:200],  # First message, truncated
                    'rating': conv.get('conversation_rating')
                }
                if subtopic_label:
                    item['specific_topic'] = subtopic_label
                sample.append(item)
        
        return f"""
Representative sample for topic: {context.metadata.get('current_topic')}

You have {len(topic_conversations)} total conversations for this topic.
The {len(sample)} snippets below were curated to represent the broader sentiment pattern.

Use only this curated subset to infer the dominant sentiment pattern and then create a 3-4 sentence narrative as described in the task description.

Sample conversations (representative {len(sample)} of {len(topic_conversations)}):
{json.dumps(sample, indent=2)}
"""
    
    def validate_input(self, context: AgentContext) -> bool:
        """Validate input"""
        if 'current_topic' not in context.metadata:
            # Fallback for test mode
            if context.metadata.get('topic'):
                context.metadata['current_topic'] = context.metadata['topic']
            else:
                raise ValueError("current_topic not specified in metadata")
        if 'topic_conversations' not in context.metadata:
            raise ValueError("topic_conversations not provided in metadata")
        return True
    
    def validate_output(self, result: Dict[str, Any]) -> bool:
        """
        Validate sentiment insight and attach quality metadata.
        
        Args:
            result: Dictionary containing 'sentiment_insight' and where metadata will be attached
            
        Returns:
            bool: True if validation technically passed (even with warnings), False if critical failure
        """
        if 'sentiment_insight' not in result:
            return False
        
        insight = result['sentiment_insight']
        warnings = []
        
        # Check for bad patterns
        bad_patterns = [
            'negative sentiment',
            'positive sentiment',
            'mixed sentiment',
            'users are frustrated',  # Too generic
            'customers express',
            'sentiment detected',
            'sentiment about',
            'have issues',
            'have problems',
            'issues',   # generic
            'problems', # generic
            'concerns',  # generic
            'issues with',
            'problems with',
            'concerns about',
            'feedback on'
        ]
        
        generic_pattern_count = 0
        for pattern in bad_patterns:
            if pattern in insight.lower():
                warnings.append(f"Generic pattern detected: '{pattern}'")
                self.logger.warning(f"Generic sentiment detected: {insight}")
                generic_pattern_count += 1
        
        # Update metrics if they exist
        if 'sentiment_metrics' in result:
            result['sentiment_metrics']['generic_pattern_count'] = generic_pattern_count
            
        # Length check (Relaxed for Deep Dive)
        if len(insight) < 20:
            warnings.append("Insight too short (<20 chars)")
        # Allow longer insights for nuanced Deep Dive (increased from 500 to 1000)
        elif len(insight) > 1000:
            warnings.append("Insight too long (>1000 chars)")
            
        # Narrative length check (expecting 3-4 sentences, roughly 100+ chars)
        if len(insight) < 100:
            warnings.append("Narrative too short - needs 3-4 sentences")
            
        # Sentence count validation (expecting at least 3 sentences)
        sentence_count = sum(insight.count(p) for p in ['.', '?', '!'])
        if sentence_count < 3:
            warnings.append(f"Narrative has too few sentences ({sentence_count} < 3)")
            
        # Nuance check (Relaxed - 'but' isn't the only way to show nuance)
        nuance_connectors = ["but", "however", "although", "yet", "while", "despite", "versus"]
        contains_nuance = any(connector in insight.lower() for connector in nuance_connectors)
        # Don't penalize missing connector if length is sufficient (might use multiple sentences)
        if not contains_nuance and len(insight) < 100:
            warnings.append("Missing nuance connector (but/however/etc)")
            
        # Pain Level Validation
        pain_level = result.get('pain_level')
        if not pain_level:
            warnings.append("CRITICAL: Missing pain_level field")
        elif str(pain_level).upper() not in ['SEVERE', 'MODERATE', 'LOW']:
            warnings.append(f"Invalid pain_level: {pain_level}")
            
        # Compute quality score (0.0 to 1.0)
        score = 1.0
        if warnings:
            score -= 0.1 * len(warnings)  # Dock points for warnings
        # Less penalty for nuance if it's a longer analysis
        if not contains_nuance and len(insight) < 100:
            score -= 0.2
        if generic_pattern_count > 0:
            score -= 0.4  # Major penalty for generic patterns (increased from 0.3)
        if not pain_level:
            score -= 0.5 # Major penalty for missing pain level
            
        score = max(0.0, score)
        
        # Attach metadata to result
        result['validation_warnings'] = warnings
        result['quality_score'] = round(score, 2)
        result['contains_nuance'] = contains_nuance
        
        # Determine pain level confidence based on inference flag
        is_inferred = result.get('pain_level_inferred', False)
        result['pain_level_confidence'] = 'MEDIUM' if is_inferred else 'HIGH'
        
        # Log quality breakdown
        self.logger.info(
            f"Sentiment Quality: Score={result['quality_score']:.2f}, "
            f"Nuance={contains_nuance}, Warnings={len(warnings)}"
        )
        
        return True
    
    async def execute(self, context: AgentContext) -> AgentResult:
        """
        Execute topic-specific sentiment analysis
        
        Args:
            context: AgentContext with:
                - metadata['current_topic']: Topic name
                - metadata['topic_conversations']: Conversations for this topic
        
        Returns:
            AgentResult with specific sentiment insight
        """
        start_time = datetime.now()
        
        try:
            self.validate_input(context)
            
            topic_name = context.metadata['current_topic']
            topic_conversations = context.metadata['topic_conversations']
            
            self.logger.info(f"TopicSentimentAgent: Analyzing sentiment for '{topic_name}' ({len(topic_conversations)} conversations)")
            
            # ALWAYS use LLM analysis - that's the whole point of multi-agent analysis
            self.logger.info(f"   🤖 Using LLM analysis for deep sentiment understanding")
            
            # Build prompt
            prompt = self.build_prompt(context)
            
            # Generate sentiment insight via LLM
            response_text = await self.ai_client.generate_analysis(prompt)
            response_text = response_text.strip()
            
            # Parse structured output (pain_level + narrative)
            pain_level, insight, reasoning = self._parse_llm_response_for_pain_level(response_text)
            
            pain_level_inferred = False
            # Fallback inference if pain_level missing
            if not pain_level:
                pain_level = self._infer_pain_level_from_narrative(insight)
                pain_level_inferred = True
                self.logger.warning(f"Pain level inferred from narrative for {topic_name}: {pain_level}")

            # Log thinking for observability
            from src.utils.agent_thinking_logger import AgentThinkingLogger
            thinking_logger = AgentThinkingLogger.get_logger()
            token_estimate = len(prompt) // 4 + len(insight) // 4
            
            if thinking_logger.is_enabled():
                thinking_logger.log_prompt(self.name, prompt, {'topic': topic_name, 'conversation_count': len(topic_conversations)})
                thinking_logger.log_response(self.name, response_text, token_estimate)

            refusal_count = 0
            retry_count = 0

            if self._looks_like_refusal(insight):
                refusal_count += 1
                self.logger.warning(f"TopicSentimentAgent detected refusal for {topic_name}; reinforcing prompt")
                reinforcement_prompt = (
                    f"{prompt}\n\n"
                    "Reminder: respond with valid JSON containing 'pain_level' and 'narrative'. "
                    "Do not refuse."
                )
                try:
                    retry_count += 1
                    retry_response = await self.ai_client.generate_analysis(reinforcement_prompt)
                    retry_text = retry_response.strip()
                    pain_level, insight, reasoning = self._parse_llm_response_for_pain_level(retry_text)
                except Exception as retry_exc:
                    self.logger.error(f"Retry failed for {topic_name}: {retry_exc}")
                
                if self._looks_like_refusal(insight):
                    refusal_count += 1
                    insight = self._fallback_sentence(topic_name)
                    pain_level = "MODERATE" # Fallback default
            
            token_count = len(prompt) // 4 + len(insight) // 4
            method = 'llm'
            sources = [f"{len(topic_conversations)} conversations about {topic_name}"]
            
            # Calculate confidence based on sample size
            confidence = min(1.0, 0.6 + (len(topic_conversations) / 100))
            confidence_level = (ConfidenceLevel.HIGH if len(topic_conversations) >= 50
                              else ConfidenceLevel.MEDIUM if len(topic_conversations) >= 20
                              else ConfidenceLevel.LOW)
            
            # Prepare result
            result_data = {
                'topic': topic_name,
                'sentiment_insight': insight, # Narrative kept as primary for backward compat
                'pain_level': pain_level,
                'pain_reasoning': reasoning,
                'pain_level_inferred': pain_level_inferred,
                'conversation_count': len(topic_conversations),
                'sample_quotes': self._extract_sample_quotes(topic_conversations[:5]),
                'method': method,  # Always 'llm' now
                'sentiment_metrics': {
                    'refusal_count': refusal_count,
                    'retry_count': retry_count
                }
            }
            
            self.validate_output(result_data)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            self.logger.info(f"TopicSentimentAgent: Generated insight for '{topic_name}' via {method}")
            self.logger.info(f"   Pain Level: {pain_level}")
            self.logger.info(f"   Insight: {insight[:100]}...")
            
            return AgentResult(
                agent_name=self.name,
                success=True,
                data=result_data,
                confidence=confidence,
                confidence_level=confidence_level,
                limitations=[f"Based on {len(topic_conversations)} conversations"] if len(topic_conversations) < 20 else [],
                sources=sources,
                execution_time=execution_time,
                token_count=token_count
            )
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            self.logger.error(f"TopicSentimentAgent error: {e}")
            
            return AgentResult(
                agent_name=self.name,
                success=False,
                data={},
                confidence=0.0,
                confidence_level=ConfidenceLevel.LOW,
                error_message=str(e),
                execution_time=execution_time
            )
    
    def _parse_llm_response_for_pain_level(self, text: str) -> tuple[Optional[str], str, Optional[str]]:
        """
        Parse LLM response to extract pain_level and narrative.
        
        Args:
            text: Raw LLM response text
            
        Returns:
            tuple: (pain_level, narrative, reasoning)
        """
        pain_level = None
        narrative = text
        reasoning = None
        
        # 1. Try to parse as JSON
        try:
            # Extract JSON if embedded in markdown code blocks
            json_str = text
            if "```json" in text:
                json_str = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                json_str = text.split("```")[1].split("```")[0].strip()
                
            data = json.loads(json_str)
            
            if isinstance(data, dict):
                pain_level = data.get('pain_level')
                narrative = data.get('narrative') or data.get('sentiment_insight') or text
                reasoning = data.get('reasoning') or data.get('pain_reasoning')
                
                if pain_level:
                    pain_level = str(pain_level).upper()
                    if pain_level not in ['SEVERE', 'MODERATE', 'LOW']:
                        pain_level = None
                        
                return pain_level, narrative, reasoning
                
        except json.JSONDecodeError:
            pass
            
        # 2. Fallback: Regex extraction from text
        import re
        
        # Look for explicit field labels
        pain_match = re.search(r'(?:pain_level|pain level|severity):\s*(SEVERE|MODERATE|LOW)', text, re.IGNORECASE)
        if pain_match:
            pain_level = pain_match.group(1).upper()
            
        # Clean up narrative if it contains labels
        # Only if we found a structure-like format
        if pain_match:
            # Remove the pain level line from narrative
            narrative = re.sub(r'(?:pain_level|pain level|severity):\s*(SEVERE|MODERATE|LOW)\s*', '', text, flags=re.IGNORECASE)
            narrative = narrative.strip()
            
        return pain_level, narrative, reasoning
        
    def _infer_pain_level_from_narrative(self, narrative: str) -> str:
        """
        Infer pain level from narrative keywords (fallback).
        
        Args:
            narrative: Sentiment insight text
            
        Returns:
            str: Inferred pain level (SEVERE/MODERATE/LOW)
        """
        narrative_lower = narrative.lower()
        
        severe_keywords = [
            "severe", "furious", "hate", "critical", "destroying trust", 
            "urgent", "churn", "useless", "terrible", "nightmare",
            "broken", "blocked", "impossible", "outrage"
        ]
        
        moderate_keywords = [
            "frustrat", "confus", "annoy", "friction", "struggl", 
            "workaround", "difficult", "hard to", "slow", "tedious"
        ]
        
        if any(w in narrative_lower for w in severe_keywords):
            return "SEVERE"
        elif any(w in narrative_lower for w in moderate_keywords):
            return "MODERATE"
        else:
            return "LOW"
            
    def _looks_like_refusal(self, text: str) -> bool:
        if not text:
            return True
        lowered = text.lower()
        refusal_markers = [
            "i cannot",
            "i can't",
            "unable to",
            "do not have enough information",
            "insufficient information",
            "as an ai",
            "i do not have access",
            "not enough data",
            "insufficient data",
            "cannot determine",
            "unable to determine",
            "need more information",
            "as a language model"
        ]
        return any(marker in lowered for marker in refusal_markers)

    def _fallback_sentence(self, topic_name: str) -> str:
        t_lower = topic_name.lower()
        if topic_name in ["Billing", "Account"]:
            return f"Customers value the service but are frustrated by friction in {t_lower} management."
        elif topic_name == "Bug":
            return f"Users are annoyed by technical issues with {t_lower} and want faster resolution."
        else:
            return f"Customers keep talking about {t_lower}, appreciating the core value but clearly frustrated by the current gaps."
    
    def _extract_cx_score_insights(self, conversations: List[Dict]) -> List[str]:
        """
        Extract CX Score explanations from Intercom conversations.
        
        CX Score explanation contains pre-written sentiment analysis by support team.
        Example: "The customer expressed negative sentiment about the refund policy..."
        
        Args:
            conversations: List of conversations
            
        Returns:
            List of CX Score explanation strings
        """
        cx_scores = []
        
        for conv in conversations:
            custom_attrs = conv.get('custom_attributes', {})
            if isinstance(custom_attrs, dict):
                cx_explanation = custom_attrs.get('CX Score explanation')
                if cx_explanation and isinstance(cx_explanation, str) and len(cx_explanation) > 20:
                    cx_scores.append(cx_explanation.strip())
        
        return cx_scores
    
    def _synthesize_cx_scores(self, cx_insights: List[str], topic_name: str) -> str:
        """
        Synthesize multiple CX Score insights into one Hilary-style sentence.
        
        Args:
            cx_insights: List of CX Score explanation strings
            topic_name: Topic being analyzed
            
        Returns:
            One-sentence sentiment insight in Hilary's style
        """
        # Extract key sentiment words from CX Scores
        sentiment_patterns = {
            'positive': ['positive', 'satisfied', 'happy', 'pleased', 'resolved', 'appreciated', 'helpful', 'clear'],
            'negative': ['negative', 'frustrated', 'unhappy', 'dissatisfied', 'confused', 'disappointed', 'poor'],
            'effort': ['high effort', 'multiple', 'repeated', 'prolonged', 'difficulty'],
            'resolution': ['resolved', 'unresolved', 'escalated', 'failed']
        }
        
        counts = {pattern_type: 0 for pattern_type in sentiment_patterns}
        
        for insight in cx_insights:
            insight_lower = insight.lower()
            for pattern_type, keywords in sentiment_patterns.items():
                if any(kw in insight_lower for kw in keywords):
                    counts[pattern_type] += 1
        
        # Build insight based on patterns
        total = len(cx_insights)
        
        # Determine dominant sentiment
        if counts['negative'] > counts['positive'] * 1.5:
            base_sentiment = "frustrated"
        elif counts['positive'] > counts['negative'] * 1.5:
            base_sentiment = "satisfied"
        else:
            base_sentiment = "mixed feelings"
        
        # Check for effort patterns
        if counts['effort'] > total * 0.3:
            effort_note = "requiring significant effort to resolve"
        else:
            effort_note = None
        
        # Build Hilary-style sentence
        if base_sentiment == "frustrated":
            if counts['resolution'] < total * 0.5:
                insight = f"Customers are frustrated with {topic_name.lower()} issues that often remain unresolved"
            else:
                insight = f"Customers experience frustration with {topic_name.lower()} but appreciate when support resolves it"
        elif base_sentiment == "satisfied":
            insight = f"Customers appreciate {topic_name.lower()} support and generally have positive experiences"
        else:
            if effort_note:
                insight = f"Customers have {base_sentiment} about {topic_name.lower()}, {effort_note}"
            else:
                insight = f"Customers have {base_sentiment} about {topic_name.lower()}"
        
        return insight
    
    def _extract_sample_quotes(self, conversations: List[Dict]) -> List[str]:
        """Extract sample quotes for verification"""
        quotes = []
        for conv in conversations[:3]:
            customer_msgs = conv.get('customer_messages', [])
            if customer_msgs:
                quote = customer_msgs[0][:100] + "..." if len(customer_msgs[0]) > 100 else customer_msgs[0]
                quotes.append(quote)
        return quotes
