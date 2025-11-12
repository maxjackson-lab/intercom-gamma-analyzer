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
from src.utils.conversation_utils import extract_conversation_text
from src.utils.subcategory_mapper import SubcategoryMapper
from src.config.taxonomy import TaxonomyManager

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
    
    def __init__(self, llm_validate_tier2: bool = None):
        super().__init__(
            name="SubTopicDetectionAgent",
            model="gpt-4o",
            temperature=0.3
        )
        self.ai_client = get_ai_client()
        
        # Determine which models to use based on AI client type
        from src.services.claude_client import ClaudeClient
        if isinstance(self.ai_client, ClaudeClient):
            # Claude: Use Haiku 4.5 for quick, Sonnet 4.5 for intensive
            self.quick_model = "claude-haiku-4-5-20250514"
            self.intensive_model = "claude-sonnet-4-5-20250514"
            self.client_type = "claude"
        else:
            # OpenAI: Use GPT-4o-mini for quick, GPT-4o for intensive  
            self.quick_model = "gpt-4o-mini"
            self.intensive_model = "gpt-4o"
            self.client_type = "openai"
        
        # Initialize SubcategoryMapper for clean taxonomy mapping
        taxonomy_manager = TaxonomyManager()
        self.subcategory_mapper = SubcategoryMapper(taxonomy_manager)
        
        # LLM Tier 2 Validation: Validate SDK subcategories with LLM
        # Can be controlled via:
        # 1. Constructor parameter: SubTopicDetectionAgent(llm_validate_tier2=True)
        # 2. Environment variable: LLM_VALIDATE_TIER2=true
        # 3. Default: False (trust SDK subcategories)
        import os
        if llm_validate_tier2 is not None:
            self.llm_validate_tier2 = llm_validate_tier2
        else:
            self.llm_validate_tier2 = os.getenv('LLM_VALIDATE_TIER2', 'false').lower() == 'true'
        
        if self.llm_validate_tier2:
            logger.info("🤖 SubTopicDetectionAgent: Tier 2 LLM validation ENABLED")
        
        logger.info("SubTopicDetectionAgent initialized with SubcategoryMapper")
    
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
            
            # Rebuild conversations by topic (ONLY PRIMARY TOPIC - NO DOUBLE COUNTING)
            conversations_by_topic = {}
            for conv in context.conversations:
                conv_id = conv.get('id')
                if conv_id in topics_by_conv:
                    # Only use the FIRST (highest confidence) topic assignment
                    # This prevents conversations from being counted in multiple categories
                    topic_assigns = topics_by_conv[conv_id]
                    if topic_assigns:
                        primary_topic_assign = topic_assigns[0]  # Highest confidence
                        topic = primary_topic_assign['topic']
                        if topic not in conversations_by_topic:
                            conversations_by_topic[topic] = []
                        conversations_by_topic[topic].append(conv)
            
            subtopics_by_tier1_topic = {}
            total_token_count = 0
            
            for tier1_topic, convs in conversations_by_topic.items():
                self.logger.info(f"Processing Tier 1 topic: {tier1_topic} ({len(convs)} conversations)")
                
                # Detect Tier 2 sub-topics
                tier2_subtopics = self._detect_tier2_subtopics(convs, tier1_topic)
                
                # Optionally validate Tier 2 with LLM
                if self.llm_validate_tier2 and tier2_subtopics:
                    tier2_subtopics = await self._validate_tier2_with_llm(tier1_topic, tier2_subtopics, convs)
                
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
        Extract Tier 2 sub-topics using CLEAN hierarchical mapping to Hilary's taxonomy.
        
        Uses SubcategoryMapper to:
        - Map SDK values to canonical Hilary taxonomy names
        - Deduplicate: refund, Refund, Refund - Requests → "Refund"
        - Filter out off-topic items (only shows subcategories in Hilary's taxonomy)
        - Preserve source tracking for transparency
        
        Args:
            conversations: Conversations for this Tier 1 topic
            tier1_topic: The Tier 1 topic name (e.g., "Billing")
            
        Returns:
            Dict of subtopic_name -> {'volume': int, 'percentage': float, 'source': str, 'sources': list}
        """
        self.logger.info(f"Extracting CLEAN Tier 2 subcategories for {tier1_topic} using SubcategoryMapper...")
        
        # Use SubcategoryMapper for clean hierarchical extraction
        result = self.subcategory_mapper.extract_hierarchical_subcategories(
            tier1_topic,
            conversations
        )
        
        # Convert to expected format
        subtopic_dict = {}
        for subcat in result['subcategories']:
            subtopic_dict[subcat['name']] = {
                'volume': subcat['count'],
                'percentage': subcat['percentage'],
                'source': subcat['sources'][0] if subcat['sources'] else 'unknown',  # Primary source
                'sources': subcat['sources'],  # All sources
                'raw_names_merged': subcat.get('raw_names', [])  # Show what was deduplicated
            }
        
        self.logger.info(
            f"   ✅ {tier1_topic}: Found {len(subtopic_dict)} CLEAN subcategories "
            f"(filtered and deduplicated from {result.get('raw_count', 'unknown')} raw items)"
        )
        
        return subtopic_dict
    
    async def _validate_tier2_with_llm(self, tier1_topic: str, tier2_subtopics: Dict, conversations: List[Dict]) -> Dict[str, Dict[str, Any]]:
        """
        Use LLM to validate/correct Tier 2 subcategories extracted from SDK.
        
        Problem: SDK subcategories may be mis-tagged by agents
        Solution: LLM validates each subcategory by reading actual conversations
        
        Args:
            tier1_topic: Tier 1 topic name (e.g., "Billing")
            tier2_subtopics: Subcategories extracted from SDK
            conversations: All conversations for this topic
            
        Returns:
            Validated/corrected subcategory dict
        """
        from src.utils.agent_thinking_logger import AgentThinkingLogger
        thinking = AgentThinkingLogger.get_logger()
        
        validated_subtopics = {}
        
        for subcat_name, subcat_data in tier2_subtopics.items():
            # Sample conversations tagged with this subcategory (max 5)
            sample_convs = conversations[:5]
            
            # Extract text from samples
            samples_text = []
            for conv in sample_convs:
                text = extract_conversation_text(conv, clean_html=True)
                samples_text.append(text[:200])
            
            if not samples_text:
                # No conversations to validate, keep as-is
                validated_subtopics[subcat_name] = subcat_data
                continue
            
            # Ask LLM to validate
            prompt = f"""You are validating customer support subcategory classifications.

TIER 1 TOPIC: {tier1_topic}
TIER 2 SUBCATEGORY: {subcat_name}

SAMPLE CONVERSATIONS:
{chr(10).join(f"{i+1}. {text}" for i, text in enumerate(samples_text))}

TASK: Are these conversations truly about "{subcat_name}"?
- Answer YES if subcategory matches the conversations
- Answer NO if subcategory seems wrong
- If NO, suggest a better subcategory name from the {tier1_topic} taxonomy

Respond with: YES or NO: [reason]"""

            thinking.log_prompt(
                "SubTopicDetectionAgent",
                prompt,
                {
                    "tier1": tier1_topic,
                    "tier2": subcat_name,
                    "sample_count": len(samples_text)
                }
            )
            
            try:
                # Use appropriate API based on client type
                if self.client_type == "claude":
                    response = await self.ai_client.client.messages.create(
                        model=self.quick_model,
                        max_tokens=100,
                        temperature=0.1,
                        messages=[{"role": "user", "content": prompt}]
                    )
                    response_text = response.content[0].text.strip()
                    tokens_used = response.usage.input_tokens + response.usage.output_tokens if hasattr(response, 'usage') else None
                else:
                    response = await self.ai_client.client.chat.completions.create(
                        model=self.quick_model,
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.1,
                        max_tokens=100
                    )
                    response_text = response.choices[0].message.content.strip()
                    tokens_used = response.usage.total_tokens if hasattr(response, 'usage') else None
                
                thinking.log_response(
                    "SubTopicDetectionAgent",
                    response_text,
                    tokens_used=tokens_used,
                    model=self.quick_model
                )
                
                # Parse response
                is_valid = response_text.upper().startswith('YES')
                
                if is_valid:
                    # LLM validated - keep subcategory
                    validated_subtopics[subcat_name] = subcat_data
                    thinking.log_validation(
                        "SubTopicDetectionAgent",
                        f"Tier 2: {subcat_name}",
                        True,
                        "LLM confirmed subcategory matches conversations"
                    )
                else:
                    # LLM rejected - log but keep (SDK might be right, LLM might be wrong)
                    self.logger.warning(f"   ⚠️ LLM validation failed for {subcat_name}: {response_text}")
                    validated_subtopics[subcat_name] = {
                        **subcat_data,
                        'llm_warning': response_text
                    }
                    thinking.log_validation(
                        "SubTopicDetectionAgent",
                        f"Tier 2: {subcat_name}",
                        False,
                        f"LLM flagged as potentially incorrect: {response_text}"
                    )
                    
            except Exception as e:
                # LLM validation failed - keep original
                self.logger.warning(f"LLM validation error for {subcat_name}: {e}")
                validated_subtopics[subcat_name] = subcat_data
        
        return validated_subtopics
    
    def _detect_tier2_subtopics_OLD_SCATTER_SHOT(self, conversations: List[Dict], tier1_topic: str) -> Dict[str, Dict[str, Any]]:
        """
        OLD SCATTER SHOT METHOD - REPLACED BY CLEAN MAPPER ABOVE
        
        This method grabbed everything from everywhere creating messy output.
        Kept for reference but no longer used.
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
            # Use intensive model for complex theme discovery
            if self.client_type == "claude":
                response = await self.ai_client.client.messages.create(
                    model=self.intensive_model,
                    max_tokens=self.ai_client.max_tokens,
                    temperature=self.ai_client.temperature,
                    system="You are an expert data analyst specializing in customer support analytics. You provide clear, actionable insights based on conversation data.",
                    messages=[
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ]
                )
                token_count = response.usage.input_tokens + response.usage.output_tokens if hasattr(response, 'usage') else 0
                response_text = response.content[0].text
            else:
                response = await self.ai_client.client.chat.completions.create(
                    model=self.intensive_model,
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
                        text = extract_conversation_text(conv, clean_html=True).lower()
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