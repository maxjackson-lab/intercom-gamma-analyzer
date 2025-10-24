"""
SubTopicDetectionAgent: Creates 3-tier sub-topic hierarchy from Intercom data.

Purpose:
- Extract Tier 2 sub-topics from Intercom structured data (custom_attributes, tags, topics)
- Discover Tier 3 emerging themes via LLM analysis
- Build hierarchical breakdown within each Tier 1 topic category
"""

import logging
import json
from typing import Dict, Any, List, Tuple
from datetime import datetime
from collections import defaultdict

from src.agents.base_agent import BaseAgent, AgentResult, AgentContext, ConfidenceLevel
from src.services.openai_client import OpenAIClient

logger = logging.getLogger(__name__)


class SubTopicDetectionAgent(BaseAgent):
    """Agent specialized in creating 3-tier sub-topic hierarchy"""
    
    def __init__(self):
        super().__init__(
            name="SubTopicDetectionAgent",
            model="gpt-4o",
            temperature=0.3
        )
        self.openai_client = OpenAIClient()
    
    def get_agent_specific_instructions(self) -> str:
        """Sub-topic detection agent specific instructions"""
        return """
SUBTOPIC DETECTION AGENT SPECIFIC RULES:

1. Create 3-tier hierarchy:
   - Tier 1: Existing taxonomy from TopicDetectionAgent
   - Tier 2: Extract from Intercom structured data (custom_attributes, tags, topics)
   - Tier 3: LLM-discovered emerging themes not captured by Tier 2

2. For Tier 2 extraction:
   - Filter custom_attributes for topic-relevant keys
   - Extract tag names from tags.tags array
   - Extract topic names from topics.topics or conversation_topics

3. For Tier 3 discovery:
   - Use LLM to identify themes not in Tier 2
   - Sample conversations for analysis
   - Rescan all conversations for matches

4. Calculate percentages relative to Tier 1 category volume

5. Track token usage from LLM calls
"""
    
    def get_task_description(self, context: AgentContext) -> str:
        """Describe the sub-topic detection task"""
        topic_dist = context.previous_results.get('TopicDetectionAgent', {}).get('data', {}).get('topic_distribution', {})
        num_topics = len(topic_dist)
        return f"Analyze {num_topics} Tier 1 topics to create 3-tier sub-topic hierarchy with Tier 2 from Intercom data and Tier 3 from LLM discovery."
    
    def format_context_data(self, context: AgentContext) -> str:
        """Format Tier 1 topic distribution for prompt"""
        topic_dist = context.previous_results.get('TopicDetectionAgent', {}).get('data', {}).get('topic_distribution', {})
        formatted = "\n".join([f"- {topic}: {info['volume']} conversations ({info['percentage']}%)" for topic, info in topic_dist.items()])
        return f"Tier 1 Topic Distribution:\n{formatted}"
    
    def validate_input(self, context: AgentContext) -> bool:
        """Validate input"""
        if 'TopicDetectionAgent' not in context.previous_results:
            raise ValueError("TopicDetectionAgent results not found in previous_results")
        data = context.previous_results['TopicDetectionAgent'].get('data', {})
        if 'topic_distribution' not in data or 'topics_by_conversation' not in data:
            raise ValueError("TopicDetectionAgent results missing required keys: topic_distribution and topics_by_conversation")
        return True
    
    def validate_output(self, result: Dict[str, Any]) -> bool:
        """Validate sub-topic detection results"""
        if 'subtopics_by_tier1_topic' not in result:
            return False
        for tier1, subtopics in result['subtopics_by_tier1_topic'].items():
            if 'tier2' not in subtopics or 'tier3' not in subtopics:
                return False
        return True
    
    async def execute(self, context: AgentContext) -> AgentResult:
        """Execute sub-topic detection"""
        start_time = datetime.now()
        
        try:
            self.validate_input(context)
            
            topic_dist = context.previous_results['TopicDetectionAgent']['data']['topic_distribution']
            topics_by_conv = context.previous_results['TopicDetectionAgent']['data']['topics_by_conversation']
            
            # Rebuild conversations by topic
            conversations_by_topic = {}
            for conv in context.conversations:
                conv_id = conv.get('id')
                if conv_id in topics_by_conv:
                    for topic_assign in topics_by_conv[conv_id]:
                        topic = topic_assign['topic']
                        if topic not in conversations_by_topic:
                            conversations_by_topic[topic] = []
                        conversations_by_topic[topic].append(conv)
            
            subtopics_by_tier1_topic = {}
            total_token_count = 0
            
            for tier1_topic, convs in conversations_by_topic.items():
                self.logger.info(f"Processing Tier 1 topic: {tier1_topic} ({len(convs)} conversations)")
                
                # Detect Tier 2 sub-topics
                tier2_subtopics = self._detect_tier2_subtopics(convs, tier1_topic)
                
                # Discover Tier 3 themes
                tier3_themes, token_count = await self._discover_tier3_themes(convs, tier1_topic, tier2_subtopics)
                total_token_count += token_count
                
                # Store results
                subtopics_by_tier1_topic[tier1_topic] = {
                    'tier2': tier2_subtopics,
                    'tier3': tier3_themes
                }
            
            # Calculate confidence based on coverage
            total_convs = len(context.conversations)
            covered_convs = sum(len(convs) for convs in conversations_by_topic.values())
            coverage = covered_convs / total_convs if total_convs > 0 else 0
            confidence = coverage
            confidence_level = (ConfidenceLevel.HIGH if confidence > 0.9 
                              else ConfidenceLevel.MEDIUM if confidence > 0.7 
                              else ConfidenceLevel.LOW)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            self.logger.info(f"SubTopicDetectionAgent: Completed in {execution_time:.2f}s")
            self.logger.info(f"   Tier 1 topics processed: {len(subtopics_by_tier1_topic)}")
            self.logger.info(f"   Coverage: {coverage:.1%}")
            self.logger.info(f"   Total token count: {total_token_count}")
            
            return AgentResult(
                agent_name=self.name,
                success=True,
                data={'subtopics_by_tier1_topic': subtopics_by_tier1_topic},
                confidence=confidence,
                confidence_level=confidence_level,
                limitations=[f"{total_convs - covered_convs} conversations not covered by any Tier 1 topic"] if total_convs - covered_convs > 0 else [],
                sources=["Intercom conversation data", "LLM semantic analysis"],
                execution_time=execution_time,
                token_count=total_token_count
            )
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            self.logger.error(f"SubTopicDetectionAgent error: {e}")
            
            return AgentResult(
                agent_name=self.name,
                success=False,
                data={},
                confidence=0.0,
                confidence_level=ConfidenceLevel.LOW,
                error_message=str(e),
                execution_time=execution_time
            )
    
    def _detect_tier2_subtopics(self, conversations: List[Dict], tier1_topic: str) -> Dict[str, Dict[str, Any]]:
        """
        Extract Tier 2 sub-topics from Intercom structured data
        
        Args:
            conversations: Conversations for this Tier 1 topic
            tier1_topic: The Tier 1 topic name
            
        Returns:
            Dict of subtopic_name -> {'volume': int, 'percentage': float, 'source': str}
        """
        subtopic_counts = defaultdict(int)
        
        for conv in conversations:
            # Custom attributes
            custom_attrs = conv.get('custom_attributes', {})
            for key, value in custom_attrs.items():
                if isinstance(value, str) and len(value.strip()) > 0:
                    subtopic_counts[value.strip()] += 1
            
            # Tags
            tags = conv.get('tags', {}).get('tags', [])
            for tag in tags:
                tag_name = tag.get('name', tag) if isinstance(tag, dict) else str(tag)
                if tag_name:
                    subtopic_counts[tag_name] += 1
            
            # Topics
            topics = conv.get('topics', {}).get('topics', []) or conv.get('conversation_topics', [])
            for topic in topics:
                topic_name = topic.get('name', topic) if isinstance(topic, dict) else str(topic)
                if topic_name:
                    subtopic_counts[topic_name] += 1
        
        total_convs = len(conversations)
        tier2_dict = {}
        
        for subtopic, count in subtopic_counts.items():
            percentage = (count / total_convs * 100) if total_convs > 0 else 0
            tier2_dict[subtopic] = {
                'volume': count,
                'percentage': round(percentage, 1),
                'source': 'intercom_data'
            }
        
        self.logger.debug(f"Tier 2 sub-topics for {tier1_topic}: {len(tier2_dict)} found")
        return tier2_dict
    
    async def _discover_tier3_themes(self, conversations: List[Dict], tier1_topic: str, tier2_subtopics: Dict) -> Tuple[Dict[str, Dict[str, Any]], int]:
        """
        Discover Tier 3 emerging themes using LLM
        
        Args:
            conversations: Conversations for this Tier 1 topic
            tier1_topic: The Tier 1 topic name
            tier2_subtopics: Existing Tier 2 sub-topics
            
        Returns:
            Tuple of (tier3_themes_dict, token_count)
        """
        token_count = 0
        
        # Sample up to 30 conversations
        sample = conversations[:30]
        
        # Build prompt
        tier2_names = list(tier2_subtopics.keys())
        conv_summaries = []
        for i, conv in enumerate(sample, 1):
            customer_msgs = conv.get('customer_messages', [])
            if customer_msgs:
                conv_summaries.append(f"{i}. {customer_msgs[0][:200]}")
        
        if not conv_summaries:
            return {}, token_count
        
        prompt = f"""
Analyze these customer support conversations for Tier 1 topic '{tier1_topic}' and identify emerging themes NOT captured by existing Tier 2 sub-topics.

Existing Tier 2 sub-topics: {', '.join(tier2_names)}

Sample conversations:
{chr(10).join(conv_summaries)}

Instructions:
1. Identify semantic themes that appear in 3+ conversations
2. Themes should be different from the Tier 2 sub-topics listed
3. Return as JSON: {{"Theme Name": ["keyword1", "keyword2"]}}
4. If no new themes, return {{}}

Emerging themes:"""
        
        try:
            # Make LLM call
            response = await self.openai_client.client.chat.completions.create(
                model=self.openai_client.model,
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
                max_tokens=self.openai_client.max_tokens,
                temperature=self.openai_client.temperature
            )
            
            # Extract token usage
            if hasattr(response, 'usage') and response.usage:
                token_count = getattr(response.usage, 'total_tokens', 0)
            
            # Parse response
            response_text = response.choices[0].message.content
            if '{' in response_text and '}' in response_text:
                start = response_text.index('{')
                end = response_text.rindex('}') + 1
                themes_json = response_text[start:end]
                themes = json.loads(themes_json)
                
                # Rescan conversations for matches
                tier3_dict = {}
                for theme_name, keywords in themes.items():
                    if not isinstance(keywords, list):
                        keywords = [theme_name.lower()]
                    
                    count = 0
                    for conv in conversations:
                        text = conv.get('full_text', '').lower()
                        if any(kw in text for kw in keywords):
                            count += 1
                    
                    total_convs = len(conversations)
                    percentage = (count / total_convs * 100) if total_convs > 0 else 0
                    
                    tier3_dict[theme_name] = {
                        'volume': count,
                        'percentage': round(percentage, 1),
                        'keywords': keywords,
                        'method': 'llm_semantic'
                    }
                
                self.logger.debug(f"Tier 3 themes for {tier1_topic}: {len(tier3_dict)} discovered")
                return tier3_dict, token_count
        
        except Exception as e:
            self.logger.warning(f"LLM tier3 discovery failed for {tier1_topic}: {e}")
        
        return {}, token_count
    
    def _build_intercom_url(self, conversation_id: str) -> str:
        """Build Intercom conversation URL with workspace ID"""
        from src.config.settings import settings
        workspace_id = settings.intercom_workspace_id
        
        if not workspace_id or workspace_id == "your-workspace-id-here":
            return f"https://app.intercom.com/a/apps/[WORKSPACE_ID]/inbox/inbox/{conversation_id}"
        return f"https://app.intercom.com/a/apps/{workspace_id}/inbox/inbox/{conversation_id}"