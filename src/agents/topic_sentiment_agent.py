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

1. Generate ONE-SENTENCE sentiment insights that are:
   - Specific to the topic
   - Nuanced (show complexity: "appreciative BUT frustrated")
   - Actionable (tells us what to fix)
   - Natural language (how a human analyst would say it)

2. GOOD EXAMPLES (match this style):
   ✓ "Users are appreciative of the ability to buy more credits, but frustrated that Gamma moved to a credit model"
   ✓ "Users hate buddy so much"
   ✓ "Users think templates are rad but want to be able to use them with API"
   ✓ "Customers love the export feature but are confused by format options"

3. BAD EXAMPLES (avoid these):
   ✗ "Negative sentiment detected"
   ✗ "Users are frustrated with this feature"
   ✗ "Mixed sentiment with both positive and negative elements"
   ✗ "Customers express dissatisfaction"

4. Capture the SPECIFIC sentiment:
   - What do users LIKE? (be specific)
   - What do users HATE? (be specific)
   - What's the tension/nuance?

5. Use strong, clear language:
   - "hate" if users really hate it
   - "love" if users really love it
   - "rad" if users think it's cool
   - "frustrated" for specific frustrations
   - "confused" for clarity issues

6. Base ONLY on the conversations provided:
   - Quote actual customer language when possible
   - Don't invent sentiment not present in data
"""
    
    def get_task_description(self, context: AgentContext) -> str:
        """Describe the topic sentiment analysis task"""
        topic_name = context.metadata.get('current_topic')
        conv_count = len(context.metadata.get('topic_conversations', []))
        
        return f"""
Analyze sentiment for the topic: {topic_name}

You have {conv_count} conversations tagged with this topic.

Generate ONE SENTENCE that:
1. Captures the specific sentiment for THIS topic
2. Shows nuance (e.g., "love X BUT want Y")
3. Uses natural, conversational language
4. Is immediately actionable

Examples to match:
- "Users hate buddy so much"
- "Users are appreciative of the ability to buy more credits, but frustrated that Gamma moved to a credit model"
- "Users think templates are rad but want to be able to use them with API"
"""
    
    def format_context_data(self, context: AgentContext) -> str:
        """Format topic conversations for analysis"""
        topic_conversations = context.metadata.get('topic_conversations', [])
        
        # Sample 10 conversations for the prompt
        sample = []
        for conv in topic_conversations[:10]:
            # Extract customer messages
            customer_msgs = conv.get('customer_messages', [])
            if customer_msgs:
                sample.append({
                    'id': conv.get('id'),
                    'customer_message': customer_msgs[0][:200],  # First message, truncated
                    'rating': conv.get('conversation_rating')
                })
        
        return f"""
Sample conversations for this topic (showing {len(sample)} of {len(topic_conversations)}):
{json.dumps(sample, indent=2)}

Analyze ALL {len(topic_conversations)} conversations to generate your insight.
"""
    
    def validate_input(self, context: AgentContext) -> bool:
        """Validate input"""
        if 'current_topic' not in context.metadata:
            raise ValueError("current_topic not specified in metadata")
        if 'topic_conversations' not in context.metadata:
            raise ValueError("topic_conversations not provided in metadata")
        return True
    
    def validate_output(self, result: Dict[str, Any]) -> bool:
        """Validate sentiment insight"""
        if 'sentiment_insight' not in result:
            return False
        
        insight = result['sentiment_insight']
        
        # Check for bad patterns
        bad_patterns = [
            'negative sentiment',
            'positive sentiment',
            'mixed sentiment',
            'users are frustrated',  # Too generic
            'customers express'
        ]
        
        if any(pattern in insight.lower() for pattern in bad_patterns):
            self.logger.warning(f"Generic sentiment detected: {insight}")
        
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
            
            # Build prompt
            prompt = self.build_prompt(context)
            
            # Generate sentiment insight
            insight = await self.ai_client.generate_analysis(prompt)
            insight = insight.strip().strip('"').strip()  # Clean up formatting
            
            # Prepare result
            result_data = {
                'topic': topic_name,
                'sentiment_insight': insight,
                'conversation_count': len(topic_conversations),
                'sample_quotes': self._extract_sample_quotes(topic_conversations[:5])
            }
            
            self.validate_output(result_data)
            
            # Calculate confidence based on sample size
            confidence = min(1.0, 0.6 + (len(topic_conversations) / 100))  # More convos = higher confidence
            confidence_level = (ConfidenceLevel.HIGH if len(topic_conversations) >= 50
                              else ConfidenceLevel.MEDIUM if len(topic_conversations) >= 20
                              else ConfidenceLevel.LOW)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            token_count = len(prompt) // 4 + len(insight) // 4
            
            self.logger.info(f"TopicSentimentAgent: Generated insight for '{topic_name}'")
            self.logger.info(f"   Insight: {insight}")
            
            return AgentResult(
                agent_name=self.name,
                success=True,
                data=result_data,
                confidence=confidence,
                confidence_level=confidence_level,
                limitations=[f"Based on {len(topic_conversations)} conversations"] if len(topic_conversations) < 20 else [],
                sources=[f"{len(topic_conversations)} conversations about {topic_name}"],
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
    
    def _extract_sample_quotes(self, conversations: List[Dict]) -> List[str]:
        """Extract sample quotes for verification"""
        quotes = []
        for conv in conversations[:3]:
            customer_msgs = conv.get('customer_messages', [])
            if customer_msgs:
                quote = customer_msgs[0][:100] + "..." if len(customer_msgs[0]) > 100 else customer_msgs[0]
                quotes.append(quote)
        return quotes

