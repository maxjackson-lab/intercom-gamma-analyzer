"""
ExampleExtractionAgent: Selects 3-10 best representative conversations per topic.

Purpose:
- Score conversations by relevance to sentiment
- Select diverse, readable examples
- Include Intercom conversation links
- Prioritize recent, clear examples
"""

import logging
from typing import Dict, Any, List
from datetime import datetime

from src.agents.base_agent import BaseAgent, AgentResult, AgentContext, ConfidenceLevel

logger = logging.getLogger(__name__)


class ExampleExtractionAgent(BaseAgent):
    """Agent specialized in extracting representative conversation examples"""
    
    def __init__(self):
        super().__init__(
            name="ExampleExtractionAgent",
            model="gpt-4o-mini",
            temperature=0.1
        )
    
    def get_agent_specific_instructions(self) -> str:
        """Example extraction agent specific instructions"""
        return """
EXAMPLE EXTRACTION AGENT SPECIFIC RULES:

1. Select 3-10 BEST conversations that demonstrate the topic sentiment
2. Prioritize conversations that:
   - Have clear, readable customer messages
   - Demonstrate the sentiment described
   - Are recent (prefer last 7 days)
   - Show diversity (different aspects of the sentiment)

3. For each example, provide:
   - Brief preview (first 50-100 chars of customer message)
   - Intercom conversation link
   - Why this example demonstrates the sentiment

4. Quality over quantity:
   - 3 excellent examples > 10 mediocre ones
   - Skip examples with unclear or very short messages
"""
    
    def get_task_description(self, context: AgentContext) -> str:
        """Describe the example extraction task"""
        topic = context.metadata.get('current_topic')
        sentiment = context.metadata.get('sentiment_insight')
        count = len(context.metadata.get('topic_conversations', []))
        
        return f"""
Select 3-10 best conversation examples for topic: {topic}

Sentiment to demonstrate: "{sentiment}"

Available: {count} conversations

Selection criteria:
1. Clearly demonstrates the sentiment
2. Readable customer message
3. Recent (prefer last 7 days)
4. Diverse (show different aspects)
"""
    
    def format_context_data(self, context: AgentContext) -> str:
        """Format conversations for selection"""
        conversations = context.metadata.get('topic_conversations', [])
        return f"Total conversations available: {len(conversations)}"
    
    def validate_input(self, context: AgentContext) -> bool:
        """Validate input"""
        if 'topic_conversations' not in context.metadata:
            raise ValueError("topic_conversations not provided")
        return True
    
    def validate_output(self, result: Dict[str, Any]) -> bool:
        """Validate extracted examples"""
        if 'examples' not in result:
            return False
        
        examples = result['examples']
        if len(examples) < 1 or len(examples) > 10:
            self.logger.warning(f"Unusual number of examples: {len(examples)}")
        
        return True
    
    async def execute(self, context: AgentContext) -> AgentResult:
        """Execute example extraction"""
        start_time = datetime.now()
        
        try:
            self.validate_input(context)
            
            topic = context.metadata.get('current_topic')
            sentiment = context.metadata.get('sentiment_insight', '')
            conversations = context.metadata.get('topic_conversations', [])
            
            self.logger.info(f"ExampleExtractionAgent: Selecting examples for '{topic}'")
            
            # Score and rank conversations
            scored_conversations = []
            
            for conv in conversations:
                score = self._score_conversation(conv, sentiment)
                scored_conversations.append((score, conv))
            
            # Sort by score (highest first)
            scored_conversations.sort(reverse=True, key=lambda x: x[0])
            
            # Select top 3-10 based on scores
            # Take top scorers, but ensure minimum quality threshold
            MIN_SCORE = 2.0
            selected = [
                conv for score, conv in scored_conversations
                if score >= MIN_SCORE
            ][:10]  # Max 10
            
            # If we don't have at least 3, lower the threshold
            if len(selected) < 3:
                selected = [conv for score, conv in scored_conversations[:7]]
            
            # Format examples
            examples = []
            for conv in selected:
                example = self._format_example(conv)
                if example:
                    examples.append(example)
            
            # Prepare result
            result_data = {
                'topic': topic,
                'examples': examples,
                'total_available': len(conversations),
                'selected_count': len(examples)
            }
            
            self.validate_output(result_data)
            
            confidence = min(1.0, len(examples) / 7)  # 7 is ideal count
            confidence_level = (ConfidenceLevel.HIGH if len(examples) >= 5
                              else ConfidenceLevel.MEDIUM if len(examples) >= 3
                              else ConfidenceLevel.LOW)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            self.logger.info(f"ExampleExtractionAgent: Selected {len(examples)} examples for '{topic}'")
            
            return AgentResult(
                agent_name=self.name,
                success=True,
                data=result_data,
                confidence=confidence,
                confidence_level=confidence_level,
                limitations=[f"Only {len(examples)} quality examples found"] if len(examples) < 5 else [],
                sources=[f"{len(conversations)} conversations about {topic}"],
                execution_time=execution_time,
                token_count=0
            )
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            self.logger.error(f"ExampleExtractionAgent error: {e}")
            
            return AgentResult(
                agent_name=self.name,
                success=False,
                data={},
                confidence=0.0,
                confidence_level=ConfidenceLevel.LOW,
                error_message=str(e),
                execution_time=execution_time
            )
    
    def _score_conversation(self, conv: Dict, sentiment: str) -> float:
        """Score conversation for example quality"""
        score = 0.0
        
        # Has clear customer message
        customer_msgs = conv.get('customer_messages', [])
        if customer_msgs:
            msg_length = len(customer_msgs[0])
            if msg_length >= 50:
                score += 2.0
            elif msg_length >= 20:
                score += 1.0
        else:
            return 0.0  # No customer message = not usable
        
        # Matches sentiment keywords
        text = conv.get('full_text', '').lower()
        
        if 'hate' in sentiment.lower() and 'hate' in text:
            score += 2.0
        if 'love' in sentiment.lower() and any(word in text for word in ['love', 'great', 'excellent']):
            score += 2.0
        if 'frustrated' in sentiment.lower() and 'frustrat' in text:
            score += 1.5
        if 'appreciative' in sentiment.lower() and any(word in text for word in ['thank', 'appreciate']):
            score += 1.5
        if 'confused' in sentiment.lower() and any(word in text for word in ['confus', 'unclear', 'don\'t understand']):
            score += 1.5
        
        # Has conversation rating (shows engagement)
        if conv.get('conversation_rating'):
            score += 1.0
        
        # Recency (prefer recent conversations)
        created_at = conv.get('created_at')
        if created_at:
            # Convert unix timestamp to datetime if needed
            if isinstance(created_at, (int, float)):
                created_dt = datetime.fromtimestamp(created_at)
            else:
                created_dt = created_at
            
            days_ago = (datetime.now() - created_dt).days
            if days_ago <= 3:
                score += 1.5
            elif days_ago <= 7:
                score += 1.0
            elif days_ago <= 14:
                score += 0.5
        
        # Readability (not too long, not too short)
        if customer_msgs:
            msg_length = len(customer_msgs[0])
            if 50 <= msg_length <= 200:
                score += 1.0
        
        return score
    
    def _format_example(self, conv: Dict) -> Dict[str, str]:
        """Format conversation into example with preview and link"""
        customer_msgs = conv.get('customer_messages', [])
        if not customer_msgs:
            return None
        
        # Get preview (first 80 chars)
        preview = customer_msgs[0][:80]
        if len(customer_msgs[0]) > 80:
            preview += "..."
        
        # Build Intercom URL
        conv_id = conv.get('id', 'unknown')
        # Note: workspace_id would come from settings in real implementation
        intercom_url = f"https://app.intercom.com/a/inbox/inbox/{conv_id}"
        
        return {
            'preview': preview,
            'intercom_url': intercom_url,
            'conversation_id': conv_id,
            'created_at': conv.get('created_at').isoformat() if conv.get('created_at') else None
        }

