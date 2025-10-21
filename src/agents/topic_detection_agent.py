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

logger = logging.getLogger(__name__)


class TopicDetectionAgent(BaseAgent):
    """Agent specialized in hybrid topic detection"""
    
    def __init__(self):
        super().__init__(
            name="TopicDetectionAgent",
            model="gpt-4o-mini",
            temperature=0.1
        )
        
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
                token_count=0
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

