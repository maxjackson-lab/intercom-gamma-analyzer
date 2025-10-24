"""
SubTopicDetectionAgent: Creates 3-tier sub-topic hierarchy from Intercom data.

Purpose:
- Extract Tier 2 sub-topics from Intercom structured data (custom_attributes, tags, topics)
- Discover Tier 3 emerging themes via LLM analysis
- Build hierarchical breakdown within each Tier 1 topic category
"""

import logging
import json
import os
from typing import Dict, Any, List, Tuple, Set
from datetime import datetime
from collections import defaultdict

from src.agents.base_agent import BaseAgent, AgentResult, AgentContext, ConfidenceLevel
from src.utils.ai_client_helper import get_ai_client

logger = logging.getLogger(__name__)

# Whitelist of topic-relevant custom attribute keys to avoid noisy data
CUSTOM_ATTRIBUTE_WHITELIST = {
    'billing_type', 'payment_method', 'plan', 'invoice_type',
    'subscription_status', 'subscription_tier', 'contract_term',
    'account_status', 'feature_flags', 'product_tier', 'usage_tier',
    'industry', 'company_size', 'region', 'segment'
}

# Keys to skip (IDs, timestamps, booleans, noisy data)
CUSTOM_ATTRIBUTE_SKIP_PATTERNS = {
    'id', 'uuid', 'token', 'key', 'secret',
    'created', 'updated', 'modified', 'timestamp', 'date',
    'is_', 'has_', 'can_', 'enable', 'disable',  # booleans
    'admin', 'user', 'password', 'api', 'auth'  # sensitive/noisy
}


class SubTopicDetectionAgent(BaseAgent):
    """Agent specialized in creating 3-tier sub-topic hierarchy"""
    
    def __init__(self):
        super().__init__(
            name="SubTopicDetectionAgent",
            model="gpt-4o",
            temperature=0.3
        )
        self.ai_client = get_ai_client()
        # Honor the agent's model choice by setting it on the client
        if hasattr(self.ai_client, 'model'):
            self.ai_client.model = self.model
    
    def get_agent_specific_instructions(self) -> str:
        """Sub-topic detection agent specific instructions"""
        return """
SUBTOPIC DETECTION AGENT SPECIFIC RULES:

1. Create 3-tier hierarchy:
   - Tier 1: Existing taxonomy from TopicDetectionAgent
   - Tier 2: Extract from Intercom structured data (custom_attributes, tags, topics)
   - Tier 3: LLM-discovered emerging themes not captured by Tier 2

2. For Tier 2 extraction:
   - Filter custom_attributes for topic-relevant keys (whitelist)
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
            
            # Prepare result data for validation
            result_data = {'subtopics_by_tier1_topic': subtopics_by_tier1_topic}
            
            # Validate output before returning (Comment 2)
            if not self.validate_output(result_data):
                raise ValueError("Output validation failed: invalid subtopic structure")
            
            # Calculate confidence based on coverage with unique conversation IDs (Comment 1)
            total_convs = len(context.conversations)
            
            # Build set of unique conversation IDs across all topics
            unique_conv_ids: Set[str] = set()
            for topic, convs in conversations_by_topic.items():
                for conv in convs:
                    unique_conv_ids.add(conv.get('id'))
            
            covered_convs = len(unique_conv_ids)
            coverage = covered_convs / total_convs if total_convs > 0 else 0
            
            # Clamp confidence to maximum of 1.0 (Comment 1)
            confidence = min(coverage, 1.0)
            confidence_level = (ConfidenceLevel.HIGH if confidence > 0.9 
                              else ConfidenceLevel.MEDIUM if confidence > 0.7 
                              else ConfidenceLevel.LOW)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            self.logger.info(f"SubTopicDetectionAgent: Completed in {execution_time:.2f}s")
            self.logger.info(f"   Tier 1 topics processed: {len(subtopics_by_tier1_topic)}")
            self.logger.info(f"   Coverage: {coverage:.1%} ({covered_convs}/{total_convs})")
            self.logger.info(f"   Total token count: {total_token_count}")
            
            return AgentResult(
                agent_name=self.name,
                success=True,
                data=result_data,
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
    
    def _should_skip_custom_attribute(self, key: str) -> bool:
        """Check if a custom attribute key should be skipped (Comment 4)"""
        key_lower = key.lower()
        
        # Skip if matches any skip pattern
        for pattern in CUSTOM_ATTRIBUTE_SKIP_PATTERNS:
            if pattern in key_lower:
                return True
        
        return False
    
    def _is_valid_custom_attribute_value(self, value: Any) -> bool:
        """Check if a custom attribute value is valid and not noisy (Comment 4)"""
        # Skip booleans
        if isinstance(value, bool):
            return False
        
        # Skip empty strings
        if isinstance(value, str):
            if not value.strip():
                return False
            # Skip very long strings (likely free-form text)
            if len(value) > 200:
                return False
            return True
        
        # Skip numeric IDs and timestamps (too long numbers)
        if isinstance(value, (int, float)):
            return False
        
        # Skip lists/dicts
        if isinstance(value, (list, dict)):
            return False
        
        return False
    
    def _detect_tier2_subtopics(self, conversations: List[Dict], tier1_topic: str) -> Dict[str, Dict[str, Any]]:
        """
        Extract Tier 2 sub-topics from Intercom structured data
        
        Tracks source origin for each sub-topic (Comment 3) and filters custom attributes (Comment 4).
        
        Args:
            conversations: Conversations for this Tier 1 topic
            tier1_topic: The Tier 1 topic name
            
        Returns:
            Dict of subtopic_name -> {'volume': int, 'percentage': float, 'source': str, 'sources': list}
        """
        # Track subtopic -> {count: int, sources: set}
        subtopic_data = defaultdict(lambda: {'count': 0, 'sources': set()})
        
        for conv in conversations:
            # Extract from custom attributes (Comment 3 & 4)
            custom_attrs = conv.get('custom_attributes', {})
            for key, value in custom_attrs.items():
                # Skip non-string values and invalid attributes
                if not isinstance(value, str):
                    continue
                
                # Apply whitelist and skip pattern filters (Comment 4)
                key_lower = key.lower()
                in_whitelist = any(wl in key_lower for wl in CUSTOM_ATTRIBUTE_WHITELIST)
                should_skip = self._should_skip_custom_attribute(key)
                
                if should_skip or (not in_whitelist and not any(tier1_topic.lower() in key_lower for tier1_topic_part in tier1_topic.split())):
                    continue
                
                value_clean = value.strip()
                if value_clean:
                    subtopic_data[value_clean]['count'] += 1
                    subtopic_data[value_clean]['sources'].add('custom_attributes')
            
            # Extract from tags (Comment 3)
            tags = conv.get('tags', {}).get('tags', [])
            for tag in tags:
                tag_name = tag.get('name', tag) if isinstance(tag, dict) else str(tag)
                if tag_name:
                    subtopic_data[tag_name]['count'] += 1
                    subtopic_data[tag_name]['sources'].add('tags')
            
            # Extract from topics (Comment 3)
            topics = conv.get('topics', {}).get('topics', []) or conv.get('conversation_topics', [])
            for topic in topics:
                topic_name = topic.get('name', topic) if isinstance(topic, dict) else str(topic)
                if topic_name:
                    subtopic_data[topic_name]['count'] += 1
                    subtopic_data[topic_name]['sources'].add('topics')
        
        total_convs = len(conversations)
        tier2_dict = {}
        
        for subtopic, data in subtopic_data.items():
            count = data['count']
            sources = list(data['sources'])
            percentage = (count / total_convs * 100) if total_convs > 0 else 0
            
            # Prefer strongest source or list them all (Comment 3)
            source_priority = {'tags': 0, 'topics': 1, 'custom_attributes': 2}
            primary_source = min(sources, key=lambda s: source_priority.get(s, 999))
            
            tier2_dict[subtopic] = {
                'volume': count,
                'percentage': round(percentage, 1),
                'source': primary_source,  # Primary source (Comment 3)
                'sources': sources  # All sources this came from
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
            # Make LLM call using configurable client
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