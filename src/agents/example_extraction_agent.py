"""
ExampleExtractionAgent: Selects 5-15 best representative conversations per topic.

Purpose:
- Score conversations by relevance to sentiment
- Select diverse, readable examples
- Include Intercom conversation links
- Prioritize recent, clear examples
"""

import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from src.agents.base_agent import BaseAgent, AgentResult, AgentContext, ConfidenceLevel
from src.utils.ai_client_helper import get_ai_client
from src.services.quote_translator import QuoteTranslator
from src.utils.conversation_utils import extract_conversation_text

logger = logging.getLogger(__name__)


class ExampleExtractionAgent(BaseAgent):
    """Agent specialized in extracting representative conversation examples with LLM selection"""
    
    def __init__(self):
        super().__init__(
            name="ExampleExtractionAgent",
            model="gpt-4o",
            temperature=0.3
        )
        self.ai_client = get_ai_client()
        self.translator = QuoteTranslator()
    
    def _to_datetime_utc(self, value: Any) -> Optional[datetime]:
        """
        Convert various timestamp formats to UTC-aware datetime.
        
        Args:
            value: Can be int, float, datetime, or ISO string
            
        Returns:
            UTC-aware datetime or None if conversion fails
        """
        if value is None:
            return None
        
        try:
            # Handle Unix timestamp (int or float)
            if isinstance(value, (int, float)):
                return datetime.fromtimestamp(value, tz=timezone.utc)
            
            # Handle datetime object
            elif isinstance(value, datetime):
                if value.tzinfo is None:
                    return value.replace(tzinfo=timezone.utc)
                else:
                    return value.astimezone(timezone.utc)
            
            # Handle ISO string
            elif isinstance(value, str):
                # Replace 'Z' with '+00:00' for fromisoformat compatibility
                if value.endswith('Z'):
                    value = value[:-1] + '+00:00'
                dt = datetime.fromisoformat(value)
                # Ensure UTC timezone
                if dt.tzinfo is None:
                    return dt.replace(tzinfo=timezone.utc)
                else:
                    return dt.astimezone(timezone.utc)
            
            else:
                self.logger.warning(f"Unknown timestamp type: {type(value)}")
                return None
                
        except (ValueError, OSError, OverflowError) as e:
            self.logger.warning(f"Failed to convert timestamp {value}: {e}")
            return None
    
    def _to_iso_utc(self, value: Any) -> Optional[str]:
        """
        Convert various timestamp formats to ISO UTC string.
        
        Args:
            value: Can be int, float, datetime, or ISO string
            
        Returns:
            ISO format string or None if conversion fails
        """
        try:
            dt = self._to_datetime_utc(value)
            return dt.isoformat() if dt else None
        except Exception as e:
            self.logger.warning(f"Failed to convert to ISO string {value}: {e}")
            return None
    
    def get_agent_specific_instructions(self) -> str:
        """Example extraction agent specific instructions"""
        return """
EXAMPLE EXTRACTION AGENT SPECIFIC RULES:

1. Select 5-15 BEST conversations that demonstrate the topic sentiment
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
Select 5-15 best conversation examples for topic: {topic}

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
        if len(examples) < 1 or len(examples) > 15:
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
            
            # Select top candidates (top 20) for LLM refinement
            MIN_SCORE = 2.0
            candidates = [
                conv for score, conv in scored_conversations
                if score >= MIN_SCORE
            ][:20]  # Top 20 candidates
            
            # If we don't have at least 10 candidates, lower the threshold
            if len(candidates) < 10:
                candidates = [conv for score, conv in scored_conversations[:15]]
            
            # Use LLM to select the most representative examples
            self.logger.info(f"Using LLM to select best examples from {len(candidates)} candidates...")
            selected = await self._llm_select_examples(candidates, topic, sentiment, target_count=10)
            
            # Fallback to rule-based if LLM fails
            if not selected:
                self.logger.warning("LLM selection failed, using top scored examples")
                selected = [conv for score, conv in scored_conversations[:10]]
            
            # Format examples
            examples = []
            for conv in selected:
                example = self._format_example(conv)
                if example:
                    examples.append(example)
            
            # Translate non-English examples
            self.logger.info(f"Translating {len([e for e in examples if e.get('language') != 'English'])} non-English quotes...")
            translated_examples = await self._translate_examples(examples)
            
            # Prepare result
            result_data = {
                'topic': topic,
                'examples': translated_examples,
                'total_available': len(conversations),
                'selected_count': len(translated_examples)
            }
            
            self.validate_output(result_data)
            
            confidence = min(1.0, len(examples) / 10)  # 10 is ideal count
            confidence_level = (ConfidenceLevel.HIGH if len(examples) >= 8
                              else ConfidenceLevel.MEDIUM if len(examples) >= 5
                              else ConfidenceLevel.LOW)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            self.logger.info(f"ExampleExtractionAgent: Selected {len(examples)} examples for '{topic}'")
            
            return AgentResult(
                agent_name=self.name,
                success=True,
                data=result_data,
                confidence=confidence,
                confidence_level=confidence_level,
                limitations=[f"Only {len(examples)} quality examples found"] if len(examples) < 8 else [],
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
        
        # Has clear customer message (with type validation)
        customer_msgs = conv.get('customer_messages', [])
        if not isinstance(customer_msgs, list):
            return 0.0  # Invalid format
        
        if customer_msgs and customer_msgs[0]:
            msg_length = len(str(customer_msgs[0]))
            if msg_length >= 50:
                score += 2.0
            elif msg_length >= 20:
                score += 1.0
        else:
            return 0.0  # No customer message = not usable
        
        # Matches sentiment keywords (extract actual conversation text)
        text = extract_conversation_text(conv, clean_html=True).lower()
        
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
        if created_at is not None:
            try:
                # Use helper to convert to UTC-aware datetime
                created_dt = self._to_datetime_utc(created_at)
                
                if created_dt:
                    now_utc = datetime.now(timezone.utc)
                    days_ago = (now_utc - created_dt).days
                    if days_ago <= 3:
                        score += 1.5
                    elif days_ago <= 7:
                        score += 1.0
                    elif days_ago <= 14:
                        score += 0.5
            except Exception as e:
                # Skip recency scoring on failure
                self.logger.debug(f"Skipping recency score for conv {conv.get('id')}: {e}")
        
        # Readability (not too long, not too short)
        if customer_msgs:
            # Coerce to string if not already a string
            first_msg = customer_msgs[0]
            safe_msg = first_msg if isinstance(first_msg, str) else str(first_msg) if first_msg is not None else ''
            msg_length = len(safe_msg)
            if 50 <= msg_length <= 200:
                score += 1.0
        
        return score
    
    def _format_example(self, conv: Dict) -> Dict[str, str]:
        """Format conversation into example with preview, link, and language info"""
        # Validate customer_messages with type check
        customer_msgs = conv.get('customer_messages', [])
        if not isinstance(customer_msgs, list) or not customer_msgs or not customer_msgs[0]:
            return None
        
        # Get preview (first 80 chars) with type validation
        first_msg = customer_msgs[0]
        if isinstance(first_msg, str):
            safe_msg = first_msg
        else:
            # Coerce non-string values to string, default to empty string
            safe_msg = str(first_msg) if first_msg is not None else ""
        
        if not safe_msg.strip():  # Skip empty messages
            return None
        
        preview = safe_msg[:80]
        if len(safe_msg) > 80:
            preview += "..."
        
        # Build Intercom URL with validation
        conv_id = conv.get('id')
        if not conv_id:
            return None  # Cannot build link without ID
        
        # Build proper Intercom URL with workspace_id
        from src.config.settings import settings
        workspace_id = settings.intercom_workspace_id
        
        if not workspace_id or workspace_id == "your-workspace-id-here":
            intercom_url = f"https://app.intercom.com/a/apps/[WORKSPACE_ID]/inbox/inbox/{conv_id}"
        else:
            intercom_url = f"https://app.intercom.com/a/apps/{workspace_id}/inbox/inbox/{conv_id}"
        
        # Handle created_at - use helper to convert to ISO UTC string
        created_at = conv.get('created_at')
        created_at_str = None
        if created_at is not None:  # Explicitly check for None to handle epoch 0
            created_at_str = self._to_iso_utc(created_at)
        
        # Get language from conversation
        language = conv.get('custom_attributes', {}).get('Language', 'English')
        
        return {
            'preview': preview,
            'intercom_url': intercom_url,
            'conversation_id': str(conv_id),
            'created_at': created_at_str,
            'language': language
        }
    
    async def _translate_examples(self, examples: List[Dict]) -> List[Dict]:
        """
        Translate non-English example quotes to English.
        
        Args:
            examples: List of example dicts with 'preview' and 'language'
            
        Returns:
            List of examples with 'translation' field added for non-English quotes
        """
        translated_examples = []
        
        for example in examples:
            language = example.get('language', 'English')
            preview = example.get('preview', '')
            
            # Skip translation for English or very short quotes
            if language == 'English' or len(preview.strip()) < 10:
                example['translation'] = None
                example['needs_translation'] = False
                translated_examples.append(example)
                continue
            
            # Translate using the translator service
            try:
                translation_result = await self.translator.translate_quote(preview, language)
                example['translation'] = translation_result.get('translation')
                example['needs_translation'] = translation_result.get('needs_translation', False)
                example['detected_language'] = translation_result.get('language', language)
                translated_examples.append(example)
                
            except Exception as e:
                self.logger.warning(f"Translation failed for {language} quote: {e}")
                example['translation'] = None
                example['needs_translation'] = False
                translated_examples.append(example)
        
        return translated_examples
    
    async def _llm_select_examples(self, candidates: List[Dict], topic: str, sentiment: str, target_count: int = 10) -> List[Dict]:
        """
        Use LLM to select the most representative and informative examples
        
        Args:
            candidates: Top-scored conversations
            topic: Topic name
            sentiment: Sentiment insight for the topic
            target_count: Number of examples to select
            
        Returns:
            List of selected conversations
        """
        if not candidates:
            return []
        
        # Build prompt with candidate summaries
        candidate_summaries = []
        for i, conv in enumerate(candidates):
            customer_msgs = conv.get('customer_messages', [])
            if customer_msgs:
                msg = customer_msgs[0][:150]
                candidate_summaries.append(f"{i+1}. \"{msg}\"")
        
        prompt = f"""
Select the most representative and informative examples for this topic analysis.

Topic: {topic}
Sentiment Insight: {sentiment}

Candidate conversations (ranked by quality):
{chr(10).join(candidate_summaries)}

Instructions:
1. Select {target_count} examples that are:
   - Most representative (clearly demonstrate the sentiment)
   - Show different aspects/facets of the issue
   - Specific and actionable (provide clear feedback)
   - Professional and informative (suitable for executive reports)

2. Return ONLY the numbers (1-{len(candidates)}) as a JSON array
3. Example: [1, 3, 7, 12, 15, 18, 20]

Selected example numbers:"""

        try:
            response = await self.ai_client.generate_analysis(prompt)
            
            # Parse JSON from response
            if '[' in response and ']' in response:
                start = response.index('[')
                end = response.rindex(']') + 1
                numbers_json = response[start:end]
                selected_numbers = json.loads(numbers_json)
                
                # Convert numbers to conversations (1-indexed to 0-indexed)
                selected = []
                for num in selected_numbers:
                    if 1 <= num <= len(candidates):
                        selected.append(candidates[num - 1])
                
                self.logger.info(f"LLM selected {len(selected)} examples: {selected_numbers}")
                return selected
        except Exception as e:
            self.logger.warning(f"LLM example selection failed: {e}")
        
        return []

