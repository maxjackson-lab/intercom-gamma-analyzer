"""
TopicDetectionAgent: Hybrid topic detection using Intercom attributes + keywords.

Purpose:
- Detect topics from Intercom conversation attributes
- Fallback to keyword detection when attributes missing
- Flag which method was used for transparency
- Support custom topic definitions
"""

import logging
import re
from typing import Dict, Any, List, Tuple
from datetime import datetime

from src.agents.base_agent import BaseAgent, AgentResult, AgentContext, ConfidenceLevel
from src.utils.ai_client_helper import get_ai_client

logger = logging.getLogger(__name__)


class TopicDetectionAgent(BaseAgent):
    """Agent specialized in hybrid topic detection with LLM enhancement"""
    
    def __init__(self):
        super().__init__(
            name="TopicDetectionAgent",
            model="gpt-4o-mini",
            temperature=0.1
        )
        self.ai_client = get_ai_client()
        
        # Topic definitions (hybrid: attribute + keywords)
        self.topics = {
            "Credits": {
                "attribute": "Credits",
                "keywords": ["credit", "credits", "out of credits", "buy credits", "credit model"],
                "priority": 1
            },
            "Agent/Buddy": {
                "attribute": None,
                "keywords": ["buddy", "agent", "ai assistant", "copilot", "editing"],
                "priority": 1
            },
            "Workspace Templates": {
                "attribute": "Workspace Templates",
                "keywords": ["template", "workspace template", "starting point", "template api"],
                "priority": 1
            },
            "Billing": {
                "attribute": "Billing",
                "keywords": ["refund", "cancel", "subscription", "payment", "invoice", "charge"],
                "priority": 2
            },
            "Bug": {
                "attribute": "Bug",
                "keywords": ["bug", "broken", "not working", "error", "crash", "glitch"],
                "priority": 2
            },
            "Account": {
                "attribute": "Account",
                "keywords": ["account", "login", "password", "email change", "settings"],
                "priority": 3
            },
            "API": {
                "attribute": "API",
                "keywords": ["api", "integration", "webhook", "developer", "endpoint"],
                "priority": 3
            },
            "Product Question": {
                "attribute": "Product Question",
                "keywords": ["how to", "how do i", "question", "help with"],
                "priority": 4
            }
        }
    
    def get_agent_specific_instructions(self) -> str:
        """Topic detection agent specific instructions"""
        return """
TOPIC DETECTION AGENT SPECIFIC RULES:

1. Use HYBRID detection method:
   - First: Check Intercom conversation attributes
   - Second: Check keyword patterns in conversation text
   - Flag which method was used for each topic

2. Multiple topics per conversation are allowed:
   - A conversation can be about both "Credits" AND "Billing"
   - Tag with all applicable topics

3. Confidence scoring:
   - Attribute match: 1.0 confidence
   - 3+ keyword matches: 0.9 confidence
   - 2 keyword matches: 0.7 confidence
   - 1 keyword match: 0.5 confidence

4. Unknown/Other category:
   - If no topics match, classify as "Other"
   - Track these for potential new topic identification
"""
    
    def get_task_description(self, context: AgentContext) -> str:
        """Describe the topic detection task"""
        return f"""
Detect topics for {len(context.conversations)} conversations using hybrid method.

Available topics:
{self._format_topic_definitions()}

For each conversation:
1. Check if Intercom attributes contain topic name
2. If not, check for keyword matches
3. Return all matching topics with detection method
4. Calculate confidence score
"""
    
    def _format_topic_definitions(self) -> str:
        """Format topic definitions for prompt"""
        formatted = []
        for topic_name, config in self.topics.items():
            attr_str = f"Attribute: '{config['attribute']}'" if config['attribute'] else "No attribute"
            keywords_str = f"Keywords: {', '.join(config['keywords'][:3])}"
            formatted.append(f"  - {topic_name}: {attr_str}, {keywords_str}")
        return '\n'.join(formatted)
    
    def format_context_data(self, context: AgentContext) -> str:
        """Format context for prompt"""
        return f"Conversations to process: {len(context.conversations)}"
    
    def validate_input(self, context: AgentContext) -> bool:
        """Validate input"""
        if not context.conversations:
            raise ValueError("No conversations to detect topics from")
        return True
    
    def validate_output(self, result: Dict[str, Any]) -> bool:
        """Validate topic detection results"""
        if 'topics_by_conversation' not in result:
            return False
        if 'topic_distribution' not in result:
            return False
        return True
    
    async def execute(self, context: AgentContext) -> AgentResult:
        """Execute topic detection"""
        start_time = datetime.now()
        
        try:
            self.validate_input(context)
            
            conversations = context.conversations
            self.logger.info(f"TopicDetectionAgent: Detecting topics for {len(conversations)} conversations")
            
            # Detect topics for each conversation
            topics_by_conversation = {}
            all_topic_assignments = []
            
            for conv in conversations:
                detected = self._detect_topics_for_conversation(conv)
                conv_id = conv.get('id', 'unknown')
                topics_by_conversation[conv_id] = detected
                all_topic_assignments.extend(detected)
            
            # Calculate topic distribution
            topic_counts = {}
            detection_methods = {}
            
            for assignment in all_topic_assignments:
                topic = assignment['topic']
                topic_counts[topic] = topic_counts.get(topic, 0) + 1
                
                if topic not in detection_methods:
                    detection_methods[topic] = {'attribute': 0, 'keyword': 0}
                detection_methods[topic][assignment['method']] += 1
            
            # Group conversations by topic
            conversations_by_topic = {}
            for conv in conversations:
                conv_id = conv.get('id', 'unknown')
                detected_topics = topics_by_conversation.get(conv_id, [])
                
                for topic_assignment in detected_topics:
                    topic = topic_assignment['topic']
                    if topic not in conversations_by_topic:
                        conversations_by_topic[topic] = []
                    conversations_by_topic[topic].append(conv)
            
            # Calculate percentages
            total_conversations = len(conversations)
            topic_distribution = {}
            
            for topic, count in topic_counts.items():
                primary_method = 'attribute' if detection_methods[topic]['attribute'] > detection_methods[topic]['keyword'] else 'keyword'
                
                topic_distribution[topic] = {
                    'volume': count,
                    'percentage': round(count / total_conversations * 100, 1),
                    'detection_method': primary_method,
                    'attribute_count': detection_methods[topic]['attribute'],
                    'keyword_count': detection_methods[topic]['keyword']
                }
            
            # LLM Enhancement: Discover additional semantic topics
            self.logger.info("Enhancing with LLM for semantic topic discovery...")
            llm_topics, llm_token_count = await self._enhance_with_llm(conversations, topic_distribution)
            if llm_topics:
                self.logger.info(f"Rescanning conversations for {len(llm_topics)} LLM-discovered topics...")
                # Rescan conversations to assign matches to LLM-discovered topics
                for topic_name, topic_info in llm_topics.items():
                    if topic_name not in topic_distribution:
                        # Add to topic definitions for keyword matching
                        topic_keywords = topic_info.get('keywords', [topic_name.lower()])
                        
                        # Scan all conversations for this new topic
                        matched_count = 0
                        for conv in conversations:
                            conv_id = conv.get('id', 'unknown')
                            text = conv.get('full_text', '').lower()
                            
                            # Check if any keyword matches
                            if any(keyword in text for keyword in topic_keywords):
                                matched_count += 1
                                # Add to topics_by_conversation
                                if conv_id not in topics_by_conversation:
                                    topics_by_conversation[conv_id] = []
                                topics_by_conversation[conv_id].append({
                                    'topic': topic_name,
                                    'method': 'llm_semantic',
                                    'confidence': 0.7
                                })
                                
                                # Add to conversations_by_topic
                                if topic_name not in conversations_by_topic:
                                    conversations_by_topic[topic_name] = []
                                conversations_by_topic[topic_name].append(conv)
                        
                        # Update topic distribution with actual counts
                        topic_distribution[topic_name] = {
                            'volume': matched_count,
                            'percentage': round(matched_count / total_conversations * 100, 1) if total_conversations > 0 else 0,
                            'detection_method': topic_info['method'],
                            'attribute_count': 0,
                            'keyword_count': matched_count,
                            'llm_discovered': True
                        }
                        
                        self.logger.info(f"   LLM topic '{topic_name}': matched {matched_count} conversations")
            
            # Prepare result
            result_data = {
                'topics_by_conversation': topics_by_conversation,
                'topic_distribution': topic_distribution,
                'conversations_by_topic': {k: len(v) for k, v in conversations_by_topic.items()},
                'total_conversations': total_conversations,
                'conversations_with_topics': sum(1 for v in topics_by_conversation.values() if v),
                'conversations_without_topics': sum(1 for v in topics_by_conversation.values() if not v)
            }
            
            self.validate_output(result_data)
            
            # Calculate confidence
            coverage = result_data['conversations_with_topics'] / total_conversations
            confidence = coverage  # Higher coverage = higher confidence
            confidence_level = (ConfidenceLevel.HIGH if confidence > 0.9 
                              else ConfidenceLevel.MEDIUM if confidence > 0.7 
                              else ConfidenceLevel.LOW)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            self.logger.info(f"TopicDetectionAgent: Completed in {execution_time:.2f}s")
            self.logger.info(f"   Topics detected: {len(topic_distribution)}")
            self.logger.info(f"   Coverage: {coverage:.1%}")
            self.logger.info(f"   Top topics: {sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)[:5]}")
            
            return AgentResult(
                agent_name=self.name,
                success=True,
                data=result_data,
                confidence=confidence,
                confidence_level=confidence_level,
                limitations=[f"{result_data['conversations_without_topics']} conversations had no detected topics"] if result_data['conversations_without_topics'] > 0 else [],
                sources=["Intercom conversation attributes", "Keyword pattern matching"],
                execution_time=execution_time,
                token_count=llm_token_count
            )
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            self.logger.error(f"TopicDetectionAgent error: {e}")
            
            return AgentResult(
                agent_name=self.name,
                success=False,
                data={},
                confidence=0.0,
                confidence_level=ConfidenceLevel.LOW,
                error_message=str(e),
                execution_time=execution_time
            )
    
    def _detect_topics_for_conversation(self, conv: Dict) -> List[Dict]:
        """
        Detect all topics for a single conversation
        
        Returns:
            List of {topic, method, confidence}
        """
        detected = []
        
        # Get conversation data
        attributes = conv.get('custom_attributes', {})
        tags = [tag.get('name', tag) if isinstance(tag, dict) else tag 
                for tag in conv.get('tags', {}).get('tags', [])]
        text = conv.get('full_text', '').lower()
        
        for topic_name, config in self.topics.items():
            # Method 1: Check Intercom attribute
            if config['attribute']:
                if config['attribute'] in attributes or config['attribute'] in tags:
                    detected.append({
                        'topic': topic_name,
                        'method': 'attribute',
                        'confidence': 1.0
                    })
                    continue  # Don't check keywords if attribute matched
            
            # Method 2: Check keywords
            keyword_matches = sum(1 for keyword in config['keywords'] if keyword in text)
            
            if keyword_matches > 0:
                confidence = min(0.9, 0.5 + (keyword_matches * 0.15))
                detected.append({
                    'topic': topic_name,
                    'method': 'keyword',
                    'confidence': confidence
                })
        
        return detected
    
    async def _enhance_with_llm(self, conversations: List[Dict], initial_topics: Dict) -> Tuple[Dict, int]:
        """
        Use LLM to discover additional semantic topics not caught by keywords
        
        Args:
            conversations: Sample of conversations
            initial_topics: Topics already detected by rules
            
        Returns:
            Tuple of (additional topics discovered by LLM, token count)
        """
        token_count = 0
        
        # Sample 20 conversations for LLM analysis
        sample = conversations[:20]
        
        # Build prompt
        conv_summaries = []
        for i, conv in enumerate(sample, 1):
            customer_msgs = conv.get('customer_messages', [])
            if customer_msgs:
                conv_summaries.append(f"{i}. {customer_msgs[0][:200]}")
        
        if not conv_summaries:
            return {}, token_count
        
        prompt = f"""
Analyze these customer support conversations and identify ANY additional topics not in the predefined list.

Already detected topics: {', '.join(initial_topics.keys())}

Sample conversations:
{chr(10).join(conv_summaries)}

Instructions:
1. Look for semantic themes, not just keywords
2. Only suggest topics that appear in 3+ conversations
3. Return topics as a JSON object with topic names and keywords: {{"Topic Name": ["keyword1", "keyword2"]}}
4. If no new topics, return empty object: {{}}

Additional topics:"""
        
        try:
            # Make the LLM call directly to get the full response object with usage stats
            response = await self.ai_client.client.chat.completions.create(
                model=self.ai_client.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert data analyst specializing in customer support analytics. You provide clear, actionable insights based on conversation data."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=self.ai_client.max_tokens,
                temperature=self.ai_client.temperature
            )
            
            # Extract token usage defensively
            if hasattr(response, 'usage') and response.usage:
                token_count = getattr(response.usage, 'total_tokens', 0)
                self.logger.info(f"LLM topic enhancement used {token_count} tokens")
            
            # Extract the response content
            response_text = response.choices[0].message.content
            
            # Parse JSON from response
            import json
            # Try to extract JSON object from response
            if '{' in response_text and '}' in response_text:
                start = response_text.index('{')
                end = response_text.rindex('}') + 1
                topics_json = response_text[start:end]
                new_topics = json.loads(topics_json)
                
                self.logger.info(f"LLM discovered {len(new_topics)} additional topics: {list(new_topics.keys())}")
                return {
                    topic: {
                        'method': 'llm_semantic', 
                        'confidence': 0.7,
                        'keywords': keywords if isinstance(keywords, list) else [topic.lower()]
                    } 
                    for topic, keywords in new_topics.items()
                }, token_count
        except Exception as e:
            self.logger.warning(f"LLM topic enhancement failed: {e}")
        
        return {}, token_count

