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
import asyncio
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime

from src.agents.base_agent import BaseAgent, AgentResult, AgentContext, ConfidenceLevel
from src.utils.ai_client_helper import get_ai_client
from src.utils.conversation_utils import extract_conversation_text, extract_customer_messages
from src.config.taxonomy import TaxonomyManager

logger = logging.getLogger(__name__)


class TopicDetectionAgent(BaseAgent):
    """Agent specialized in hybrid topic detection with LLM enhancement"""
    
    def __init__(self, llm_first: bool = None):
        super().__init__(
            name="TopicDetectionAgent",
            model="gpt-4o-mini",
            temperature=0.1
        )
        self.ai_client = get_ai_client()
        
        # Determine which models to use based on AI client type
        from src.services.claude_client import ClaudeClient
        if isinstance(self.ai_client, ClaudeClient):
            # Claude: Use Haiku 4.5 for quick, Sonnet 4.5 for intensive
            self.quick_model = "claude-haiku-4-5-20251001"
            self.intensive_model = "claude-sonnet-4-5-20250929"
            self.client_type = "claude"
        else:
            # OpenAI: Use GPT-4o-mini for quick, GPT-4o for intensive
            self.quick_model = "gpt-4o-mini"
            self.intensive_model = "gpt-4o"
            self.client_type = "openai"
        
        # RATE LIMITING: Per Anthropic/OpenAI docs
        # Tier 1: 50 RPM limit for both providers
        # Using Semaphore(10) = max 10 concurrent requests = safe for 50 RPM
        # Source: https://docs.anthropic.com/en/api/rate-limits
        import asyncio
        self.llm_semaphore = asyncio.Semaphore(10)  # Limit concurrent LLM calls
        self.llm_timeout = 30  # 30 second timeout per LLM call (prevents hangs)
        
        # NEW: Use full TaxonomyManager for rich categorization (13 categories + 100+ subcategories)
        self.taxonomy_manager = TaxonomyManager()
        
        # Build topic definitions from TaxonomyManager
        self.topics = self._build_topics_from_taxonomy()
        
        # LLM-First Mode: DEFAULT TRUE - Accuracy over cost
        # LLM classifies EVERY conversation for maximum accuracy
        # Can be disabled via: TopicDetectionAgent(llm_first=False) or env var LLM_TOPIC_DETECTION=false
        import os
        if llm_first is not None:
            self.llm_first = llm_first
        else:
            # DEFAULT: TRUE (LLM-first for production accuracy)
            self.llm_first = os.getenv('LLM_TOPIC_DETECTION', 'true').lower() == 'true'
        
        if self.llm_first:
            self.logger.info("🤖 TopicDetectionAgent: LLM-FIRST mode enabled (uses LLM for every conversation)")
        else:
            self.logger.info("⚡ TopicDetectionAgent: KEYWORD-FIRST mode (LLM fallback for low-confidence only)")
    
    async def _call_llm_with_retry(self, prompt: str, max_tokens: int = 50) -> tuple:
        """
        Call LLM with exponential backoff retry.
        
        Per OpenAI official docs: https://platform.openai.com/docs/guides/rate-limits
        "Use tenacity library with wait_random_exponential(min=1, max=60)"
        
        Returns: (response_text, tokens_used) or raises Exception after 6 retries
        """
        from tenacity import retry, wait_random_exponential, stop_after_attempt, retry_if_exception_type
        
        @retry(
            wait=wait_random_exponential(min=1, max=60),  # Exponential backoff
            stop=stop_after_attempt(6),  # OpenAI recommendation
            retry=retry_if_exception_type((Exception,)),
            reraise=True
        )
        async def _retry_wrapper():
            if self.client_type == "claude":
                response = await self.ai_client.client.messages.create(
                    model=self.quick_model,
                    max_tokens=max_tokens,
                    temperature=0.1,
                    messages=[{"role": "user", "content": prompt}]
                )
                text = response.content[0].text.strip()
                tokens = response.usage.input_tokens + response.usage.output_tokens if hasattr(response, 'usage') else None
                return (text, tokens)
            else:
                response = await self.ai_client.client.chat.completions.create(
                    model=self.quick_model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.1,
                    max_tokens=max_tokens
                )
                text = response.choices[0].message.content.strip()
                tokens = response.usage.total_tokens if hasattr(response, 'usage') else None
                return (text, tokens)
        
        return await _retry_wrapper()
    
    def _build_topics_from_taxonomy(self) -> Dict:
        """Build topic definitions from TaxonomyManager (full 13 categories + subcategories)"""
        # LEGACY: Keep old simple topics as fallback documentation
        # (not used, but preserved for reference)
        self.legacy_simple_topics = {
            "Abuse": {
                "attribute": "Abuse",
                "keywords": ["abuse", "harmful", "offensive", "inappropriate", "violation", "terms of service", 
                           "not shareable", "link not working", "sharing issue", "spam", "harassment",
                           "abusive", "report", "complaint", "violate", "policy", 
                           "suspend", "suspended", "ban", "banned", "disabled", "blocked"],
                "priority": 1
            },
            "Account": {
                "attribute": "Account",
                "keywords": ["account", "login", "password", "email change", "settings", "access", 
                           "credits", "account email", "sign in", "signin", "log in",
                           "authentication", "verify", "verification", "reset password", "can't access",
                           "cant access", "locked", "locked out", "cannot sign in", "forgot password",
                           "username", "unauthorized"],
                "priority": 2
            },
            "Billing": {
                "attribute": "Billing",
                "keywords": ["invoice", "payment", "subscription", "billing", "charge", "refund", 
                           "cancel", "payment method", "plan", "charged", "bill", "subscribe", 
                           "unsubscribe", "renew", "renewal", "paid", "pay", "credit card",
                           "paypal", "stripe", "receipt", "transaction", "cost", "price", "pricing"],
                "priority": 2
            },
            "Bug": {
                "attribute": "Bug",
                "keywords": ["bug", "error", "glitch", "broken", "not working", "crash", "unexpected",
                           "issue", "problem", "doesn't work", "doesnt work", "failed", "failing",
                           "malfunction", "wrong", "incorrect", "weird behavior", "strange"],
                "priority": 2
            },
            "Chargeback": {
                "attribute": "Chargeback",
                "keywords": ["chargeback", "dispute", "unauthorized charge", "contested", "fraudulent"],
                "priority": 1
            },
            "Feedback": {
                "attribute": "Feedback",
                "keywords": ["feature request", "suggestion", "improvement", "wish", "would be nice", 
                           "could you add", "functionality", "doesn't exist", "feedback", "recommend",
                           "should add", "please add", "missing", "would like", "enhancement",
                           "idea", "propose", "request"],
                "priority": 3
            },
            "Partnerships": {
                "attribute": "Partnerships",
                "keywords": ["partnership", "collaboration", "integration", "affiliate", "business opportunity",
                           "partner", "collab"],
                "priority": 4
            },
            "Privacy & Security": {
                "attribute": "Privacy & Security",
                "keywords": ["privacy", "security", "data protection", "terms of service", "privacy policy",
                           "unauthorized access", "breach", "gdpr", "data"],
                "priority": 1
            },
            "Product Question": {
                "attribute": "Product Question",
                "keywords": ["how to", "how do i", "question", "help with", "what is", "can i", "feature",
                           "how can", "help me", "need help", "where is", "where do", "when can",
                           "tutorial", "guide", "instructions", "explain", "understand", "confused"],
                "priority": 3
            },
            "Promotions": {
                "attribute": "Promotions",
                "keywords": ["discount", "coupon", "promo", "code", "special offer", "deal", "promotion"],
                "priority": 3
            },
            "Unknown/unresponsive": {
                "attribute": "Unknown/unresponsive",
                "keywords": ["no response", "unresponsive", "didn't specify", "unclear"],
                "priority": 5
            },
            "Workspace": {
                "attribute": "Workspace",
                "keywords": ["workspace", "member", "permission", "team", "workspace settings", 
                           "invite", "share workspace"],
                "priority": 2
            }
        }
    
    def _build_topics_from_taxonomy(self) -> Dict:
        """
        Build topic definitions from TaxonomyManager for detection.
        
        Converts TaxonomyManager's Category objects into the format needed
        for topic detection while preserving subcategory information.
        
        Returns:
            Dict mapping topic names to {attribute, keywords, priority, subcategories}
        """
        topics = {}
        
        for category_name, category in self.taxonomy_manager.categories.items():
            # Extract all keywords from category and subcategories
            all_keywords = list(category.keywords)  # Category-level keywords
            
            # Add subcategory keywords for better detection
            for subcat in category.subcategories:
                all_keywords.extend(subcat.keywords)
            
            # Remove duplicates while preserving order
            seen = set()
            unique_keywords = []
            for kw in all_keywords:
                if kw.lower() not in seen:
                    seen.add(kw.lower())
                    unique_keywords.append(kw.lower())
            
            topics[category_name] = {
                'attribute': category_name,  # Look for category name in Intercom attributes
                'keywords': unique_keywords,
                'priority': 2,  # Default priority
                'subcategories': [
                    {
                        'name': subcat.name,
                        'description': subcat.description,
                        'keywords': subcat.keywords,
                        'confidence_threshold': subcat.confidence_threshold
                    }
                    for subcat in category.subcategories
                ],
                'category_obj': category  # Keep reference to full category object
            }
        
        self.logger.info(f"Built {len(topics)} topics from TaxonomyManager with subcategories")
        for topic_name, config in topics.items():
            self.logger.info(f"   {topic_name}: {len(config['keywords'])} keywords, {len(config['subcategories'])} subcategories")
        
        return topics
    
    def _get_topic_priority_order(self) -> List[str]:
        """
        Return topics in priority order: specific → generic.
        
        This ensures specific topics are checked first to prevent misclassification.
        For example, "how do I refund" should match "Billing" before "Product Question".
        
        Returns:
            List of topic names in priority order (highest priority first)
        """
        return [
            # Priority 1: Most specific topics (should always be checked first)
            'Chargeback',      # Very specific - charge disputes
            'Abuse',           # Specific - policy violations
            'Partnerships',    # Specific - business inquiries
            'Promotions',      # Specific - discount codes
            
            # Priority 2: Domain-specific topics
            'Billing',         # Money-related issues
            'Bug',             # Technical problems
            'Account',         # User account issues
            'Workspace',       # Team/collaboration
            'Privacy',         # Data/security concerns
            'Agent/Buddy',     # AI assistant questions
            'Credits',         # Credit balance/usage
            'Export',          # File export questions
            
            # Priority 3: Generic topics (check last)
            'Feedback',        # Feature requests
            'Product Question', # General "how do I..." questions
            
            # Priority 4: Catch-all
            'Unknown'          # No matches
        ]
    
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
            
            # CONCURRENT PROCESSING WITH RATE LIMITING
            # Per OpenAI/Anthropic docs: Use semaphore to limit concurrent requests
            # Tier 1: 50 RPM limit → 10 concurrent = safe buffer
            # Source: https://docs.anthropic.com/en/api/rate-limits
            
            async def process_conversation_with_limit(conv, idx):
                """Process single conversation with rate limit + timeout"""
                async with self.llm_semaphore:  # Limits to 10 concurrent
                    try:
                        # Add timeout per OpenAI best practices
                        detected = await asyncio.wait_for(
                            self._detect_topics_for_conversation(conv),
                            timeout=self.llm_timeout
                        )
                        
                        # Progress logging every 25 conversations
                        if (idx + 1) % 25 == 0:
                            self.logger.info(f"Progress: {idx + 1}/{len(conversations)} conversations processed")
                        
                        return (conv.get('id', 'unknown'), detected, None)
                        
                    except asyncio.TimeoutError:
                        self.logger.warning(f"LLM timeout for conversation {conv.get('id')}, falling back to keywords")
                        # Return empty to trigger fallback
                        return (conv.get('id', 'unknown'), [], 'timeout')
                    except Exception as e:
                        self.logger.warning(f"LLM error for conversation {conv.get('id')}: {e}")
                        return (conv.get('id', 'unknown'), [], str(e))
            
            # Process all conversations concurrently with rate limiting
            tasks = [process_conversation_with_limit(conv, i) for i, conv in enumerate(conversations)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Unpack results
            topics_by_conversation = {}
            all_topic_assignments = []
            primary_topic_assignments = []
            
            for result in results:
                if isinstance(result, Exception):
                    self.logger.error(f"Unexpected error in topic detection: {result}")
                    continue
                    
                conv_id, detected, error = result
                
                # Store ALL detected topics for context
                topics_by_conversation[conv_id] = detected
                all_topic_assignments.extend(detected)
                
                # Select PRIMARY topic (highest confidence) for counting
                if detected:
                    primary = max(detected, key=lambda x: x.get('confidence', 0))
                    primary_topic_assignments.append(primary)
                else:
                    # Fallback if no topics detected
                    primary_topic_assignments.append({
                        'topic': 'Unknown/unresponsive',
                        'method': 'fallback',
                        'confidence': 0.1
                    })
            
            # Calculate topic distribution using PRIMARY topics only (prevents double-counting)
            topic_counts = {}
            detection_methods = {}
            
            for assignment in primary_topic_assignments:  # ← Changed from all_topic_assignments
                topic = assignment['topic']
                topic_counts[topic] = topic_counts.get(topic, 0) + 1
                
                if topic not in detection_methods:
                    detection_methods[topic] = {
                        'hybrid': 0,       # Keyword + SDK agree (best)
                        'keyword': 0,      # Keyword only (good)
                        'sdk_only': 0,     # SDK only (caution)
                        'llm_smart': 0,    # LLM with hints (NEW!)
                        'llm_only': 0,     # LLM without hints (NEW!)
                        'fallback': 0      # Unknown fallback
                    }
                
                # Track method
                method = assignment.get('method', 'keyword')
                if method in detection_methods[topic]:
                    detection_methods[topic][method] += 1
                else:
                    # Unknown method - log warning and count as fallback
                    self.logger.warning(f"Unknown detection method '{method}' for topic {topic} - counting as fallback")
                    detection_methods[topic]['fallback'] += 1
            
            # DEBUG: Log HYBRID detection method breakdown (including LLM methods!)
            self.logger.info("📊 HYBRID Topic Detection Breakdown (incl. LLM):")
            for topic, methods in sorted(detection_methods.items(), key=lambda x: topic_counts[x[0]], reverse=True)[:10]:
                count = topic_counts[topic]
                llm_smart_pct = round(methods.get('llm_smart', 0) / count * 100, 1) if count > 0 else 0
                llm_only_pct = round(methods.get('llm_only', 0) / count * 100, 1) if count > 0 else 0
                hybrid_pct = round(methods['hybrid'] / count * 100, 1) if count > 0 else 0
                kw_pct = round(methods['keyword'] / count * 100, 1) if count > 0 else 0
                sdk_pct = round(methods['sdk_only'] / count * 100, 1) if count > 0 else 0
                fallback_pct = round(methods['fallback'] / count * 100, 1) if count > 0 else 0
                
                log_parts = [f"{topic}: {count} total"]
                
                # Show LLM methods first (highest priority)
                if methods.get('llm_smart', 0) > 0:
                    log_parts.append(f"LLM-Smart: {methods['llm_smart']} ({llm_smart_pct}%)")
                if methods.get('llm_only', 0) > 0:
                    log_parts.append(f"LLM-Only: {methods['llm_only']} ({llm_only_pct}%)")
                
                # Then traditional methods
                if methods['hybrid'] > 0:
                    log_parts.append(f"Hybrid: {methods['hybrid']} ({hybrid_pct}%)")
                if methods['keyword'] > 0:
                    log_parts.append(f"Keyword: {methods['keyword']} ({kw_pct}%)")
                if methods['sdk_only'] > 0:
                    log_parts.append(f"SDK-only: {methods['sdk_only']} ({sdk_pct}%)")
                if methods['fallback'] > 0:
                    log_parts.append(f"Fallback: {methods['fallback']} ({fallback_pct}%)")
                
                self.logger.info(f"   {' | '.join(log_parts)}")
            
            # Group conversations by PRIMARY topic only (prevents double-counting)
            conversations_by_topic = {}
            for conv in conversations:
                conv_id = conv.get('id', 'unknown')
                detected_topics = topics_by_conversation.get(conv_id, [])
                
                # Only use PRIMARY topic (highest confidence) to prevent double-counting
                if detected_topics:
                    primary_topic = max(detected_topics, key=lambda x: x.get('confidence', 0))
                    topic = primary_topic['topic']
                    if topic not in conversations_by_topic:
                        conversations_by_topic[topic] = []
                    conversations_by_topic[topic].append(conv)
            
            # Calculate percentages with HYBRID tracking
            total_conversations = len(conversations)
            topic_distribution = {}
            
            for topic, count in topic_counts.items():
                methods = detection_methods[topic]
                
                # Determine primary method (priority order: llm > hybrid > keyword > sdk > fallback)
                if methods.get('llm_smart', 0) > 0:
                    primary_method = 'llm_smart'
                elif methods.get('llm_only', 0) > 0:
                    primary_method = 'llm_only'
                elif methods['hybrid'] > 0:
                    primary_method = 'hybrid'
                elif methods['keyword'] > 0:
                    primary_method = 'keyword'
                elif methods['sdk_only'] > 0:
                    primary_method = 'sdk_only'
                else:
                    primary_method = 'fallback'
                
                topic_distribution[topic] = {
                    'volume': count,
                    'percentage': round(count / total_conversations * 100, 1),
                    'detection_method': primary_method,
                    'llm_smart_count': methods.get('llm_smart', 0),  # NEW!
                    'llm_only_count': methods.get('llm_only', 0),    # NEW!
                    'hybrid_count': methods['hybrid'],
                    'keyword_count': methods['keyword'],
                    'sdk_only_count': methods['sdk_only'],
                    'fallback_count': methods.get('fallback', 0)
                }
            
            # LLM Enhancement: DISABLED - was discovering duplicates of existing subcategories
            # e.g., "Invoice/Receipt Issues" when Invoice is already a Billing subcategory
            # The full taxonomy already covers all needed topics
            self.logger.info("LLM topic discovery disabled (using full taxonomy instead)")
            llm_topics = {}
            llm_token_count = 0
            if False and llm_topics:
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
                            # Extract actual conversation text
                            text = extract_conversation_text(conv, clean_html=True).lower()
                            
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
    
    async def _detect_topics_for_conversation(self, conv: Dict) -> List[Dict]:
        """
        HYBRID DETECTION: SDK Enrichment + Keyword Detection
        
        Strategy:
        1. PRIMARY: Keyword detection (reliable, always works)
        2. ENRICHMENT: SDK attributes boost confidence when they agree
        3. VALIDATION: SDK attributes can catch missed keywords
        
        Returns:
            List of {topic, method, confidence, sdk_validated}
        """
        detected = []
        conv_id = conv.get('id', 'unknown')
        
        # Get conversation data
        attributes = conv.get('custom_attributes', {})
        tags = [tag.get('name', tag) if isinstance(tag, dict) else tag 
                for tag in conv.get('tags', {}).get('tags', [])]
        
        # Extract actual conversation text using utility function
        text = extract_conversation_text(conv, clean_html=True).lower()
        
        # DEBUG: Log what we're working with (first 5 convs only to avoid spam)
        if conv_id.endswith(('0', '1', '2', '3', '4')):  # Sample ~10% of conversations
            self.logger.debug(f"🔍 Hybrid Topic Detection for {conv_id}:")
            self.logger.debug(f"   SDK Attributes: {attributes}")
            self.logger.debug(f"   SDK Tags: {tags}")
            self.logger.debug(f"   Text Length: {len(text)} chars")
        
        # ===== LLM-FIRST MODE =====
        # If enabled, use LLM as primary classification method with SDK/keywords as hints
        if self.llm_first:
            # Get SDK hint
            sdk_hint = attributes.get('Reason for contact') if isinstance(attributes, dict) else None
            
            # Do quick keyword scan for hints (don't wait for full detection)
            quick_keywords = []
            for topic_name in self._get_topic_priority_order()[:5]:  # Just check top 5 topics
                if topic_name in self.topics:
                    config = self.topics[topic_name]
                    for kw in config['keywords'][:3]:  # Just first 3 keywords per topic
                        pattern = r'\b' + re.escape(kw) + r'\b'
                        if re.search(pattern, text):
                            quick_keywords.append(kw)
                            break
            
            # Classify with LLM using hints
            llm_result = await self._classify_with_llm_smart(text, sdk_hint=sdk_hint, keywords_hint=quick_keywords if quick_keywords else None)
            
            if llm_result:
                # LLM successfully classified
                return [llm_result]
            else:
                # LLM failed - fall back to keyword detection
                self.logger.warning(f"LLM classification failed for {conv_id}, falling back to keywords")
        
        # Track topics by detection method for hybrid scoring
        keyword_detections = {}
        sdk_detections = {}
        
        # PRIORITY SYSTEM: Check specific topics before generic ones
        # This prevents "how do I refund" from being classified as Product Question
        # Order: High-specificity topics first, then general ones
        topic_priority_order = self._get_topic_priority_order()
        
        for topic_name in topic_priority_order:
            # Skip if topic not in our configuration
            if topic_name not in self.topics:
                continue
                
            config = self.topics[topic_name]
            
            # ===== STEP 1: KEYWORD DETECTION (PRIMARY) =====
            matched_keywords = []
            for kw in config['keywords']:
                # Use word boundary regex: \b ensures keyword is a complete word
                pattern = r'\b' + re.escape(kw) + r'\b'
                if re.search(pattern, text):
                    matched_keywords.append(kw)
            
            if matched_keywords:
                keyword_detections[topic_name] = {
                    'keywords': matched_keywords,
                    'count': len(matched_keywords),
                    'confidence': min(0.9, 0.5 + (len(matched_keywords) * 0.15))
                }
            
            # ===== STEP 2: SDK ATTRIBUTE DETECTION (ENRICHMENT) =====
            if config['attribute']:
                sdk_matched = False
                match_source = None
                
                # Check "Reason for contact" (Intercom standard field)
                if attributes and isinstance(attributes, dict):
                    reason_for_contact = attributes.get('Reason for contact')
                    if reason_for_contact == config['attribute']:
                        sdk_matched = True
                        match_source = 'Reason for contact'
                
                # Check any custom_attributes values
                if not sdk_matched and attributes and isinstance(attributes, dict):
                    if config['attribute'] in attributes.values():
                        sdk_matched = True
                        match_source = 'custom_attributes'
                
                # Check tags
                if not sdk_matched and config['attribute'] in tags:
                    sdk_matched = True
                    match_source = 'tags'
                
                if sdk_matched:
                    sdk_detections[topic_name] = {
                        'source': match_source,
                        'value': config['attribute']
                    }
        
        # ===== STEP 3: HYBRID SCORING WITH PRIORITY =====
        # Combine keyword + SDK detections with smart confidence scoring
        # Process in priority order and stop at first high-confidence match
        
        all_detected_topics = set(list(keyword_detections.keys()) + list(sdk_detections.keys()))
        
        # Sort by priority order
        sorted_topics = [t for t in topic_priority_order if t in all_detected_topics]
        sorted_topics.extend([t for t in all_detected_topics if t not in topic_priority_order])
        
        for topic_name in sorted_topics:
            has_keywords = topic_name in keyword_detections
            has_sdk = topic_name in sdk_detections
            
            if has_keywords and has_sdk:
                # BEST CASE: Both agree - high confidence
                keyword_data = keyword_detections[topic_name]
                sdk_data = sdk_detections[topic_name]
                
                detected.append({
                    'topic': topic_name,
                    'method': 'hybrid',  # Both keyword + SDK
                    'confidence': 0.95,  # Very high - both sources agree
                    'sdk_validated': True,
                    'keywords': keyword_data['keywords'][:3],
                    'sdk_source': sdk_data['source']
                })
                
                if conv_id.endswith(('0', '1', '2', '3', '4')):
                    self.logger.debug(
                        f"   ✅ HYBRID '{topic_name}': "
                        f"Keywords={keyword_data['keywords'][:3]} + "
                        f"SDK={sdk_data['source']}"
                    )
            
            elif has_keywords:
                # GOOD: Keywords detected (reliable)
                keyword_data = keyword_detections[topic_name]
                
                detected.append({
                    'topic': topic_name,
                    'method': 'keyword',
                    'confidence': keyword_data['confidence'],
                    'sdk_validated': False,
                    'keywords': keyword_data['keywords'][:3]
                })
                
                if conv_id.endswith(('0', '1', '2', '3', '4')):
                    self.logger.debug(
                        f"   ✅ KEYWORD '{topic_name}': "
                        f"{keyword_data['keywords'][:3]} ({keyword_data['count']} matches)"
                    )
            
            elif has_sdk:
                # CAUTION: SDK only (no keyword validation)
                # This catches conversations where keywords missed it
                # But lower confidence since we can't validate against text
                sdk_data = sdk_detections[topic_name]
                
                detected.append({
                    'topic': topic_name,
                    'method': 'sdk_only',
                    'confidence': 0.7,  # Medium confidence - unvalidated
                    'sdk_validated': True,
                    'sdk_source': sdk_data['source']
                })
                
                if conv_id.endswith(('0', '1', '2', '3', '4')):
                    self.logger.debug(
                        f"   ⚠️  SDK_ONLY '{topic_name}': "
                        f"Source={sdk_data['source']} (no keyword validation)"
                    )
        
        # ===== STEP 4: LLM VALIDATION FOR LOW-CONFIDENCE MATCHES =====
        # If we have matches but they're all low confidence (<0.7), use LLM to validate
        if detected:
            max_confidence = max(d.get('confidence', 0) for d in detected)
            if max_confidence < 0.7:
                self.logger.info(f"🤖 Low confidence ({max_confidence:.2f}) for {conv_id} - validating with LLM")
                llm_topic = await self._validate_topic_with_llm(text, detected)
                if llm_topic:
                    # LLM validated/corrected the topic
                    detected = [llm_topic]
        
        # ===== STEP 5: FALLBACK TO UNKNOWN =====
        if not detected:
            text_length = len(text)
            has_attrs = bool(attributes)
            has_tags = bool(tags)
            
            # For truly unknown conversations, try LLM as last resort
            if text_length > 100:  # Only if there's actual content
                self.logger.info(f"🤖 NO TOPICS DETECTED for {conv_id} - trying LLM")
                llm_topic = await self._classify_with_llm(text)
                if llm_topic and llm_topic['topic'] != 'Unknown/unresponsive':
                    detected.append(llm_topic)
            
            # If still nothing, mark as Unknown
            if not detected:
                # Log Unknown assignments for diagnostics
                self.logger.warning(
                    f"⚠️ NO TOPICS DETECTED for {conv_id} - TRUE UNKNOWN:"
                )
                self.logger.warning(f"   Text: {text_length} chars")
                self.logger.warning(f"   SDK Attributes: {attributes}")
                self.logger.warning(f"   SDK Tags: {tags}")
                if text_length > 0:
                    self.logger.warning(f"   Preview: {text[:150]}...")
                    self.logger.warning(f"   💡 Consider adding keywords for this pattern")
                
                detected.append({
                    'topic': 'Unknown/unresponsive',
                    'method': 'fallback',
                    'confidence': 0.1,
                    'sdk_validated': False
                })
        
        # Sort by confidence (highest first) to ensure primary topic is first
        # This is critical for preventing double-counting in downstream agents
        return sorted(detected, key=lambda x: x.get('confidence', 0), reverse=True)
    
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
            # Extract customer messages using utility function
            customer_msgs = extract_customer_messages(conv, clean_html=True)
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
            # Use intensive model for complex analysis
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
                self.logger.info(f"LLM topic enhancement used {token_count} tokens (Claude {self.intensive_model})")
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
                # Extract token usage defensively
                if hasattr(response, 'usage') and response.usage:
                    token_count = getattr(response.usage, 'total_tokens', 0)
                    self.logger.info(f"LLM topic enhancement used {token_count} tokens (OpenAI {self.intensive_model})")
            
            # Extract the response content based on client type
            if self.client_type == "claude":
                response_text = response.content[0].text
            else:
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
    
    async def _classify_with_llm_smart(self, text: str, sdk_hint: Optional[str] = None, keywords_hint: Optional[List[str]] = None) -> Optional[Dict]:
        """
        LLM-FIRST classification with SDK and keyword hints.
        
        This is the primary classification method when LLM-first mode is enabled.
        Uses SDK attributes and keywords as HINTS, not truth.
        
        Args:
            text: Conversation text
            sdk_hint: SDK "Reason for contact" value (may be wrong!)
            keywords_hint: Keywords that matched (for validation)
            
        Returns:
            Topic dict with high confidence or None
        """
        try:
            from src.utils.agent_thinking_logger import AgentThinkingLogger
            thinking = AgentThinkingLogger.get_logger()
            
            topic_list = ', '.join(self._get_topic_priority_order()[:10])
            
            # Build context-aware prompt
            hint_section = ""
            if sdk_hint:
                hint_section += f"\n⚠️ HINT (may be incorrect): Intercom tagged this as '{sdk_hint}'\n"
            if keywords_hint:
                hint_section += f"⚠️ HINT: Keywords matched: {', '.join(keywords_hint[:5])}\n"
            
            prompt = f"""You are analyzing a customer support conversation to determine its PRIMARY topic.

AVAILABLE TOPICS: {topic_list}
{hint_section}
CONVERSATION TEXT:
{text[:1500]}

TASK: 
1. Read the conversation carefully
2. Identify the customer's MAIN issue/question
3. Choose ONE topic from the available list that best matches
4. Ignore the hints if they don't match the actual conversation content
5. If conversation is unclear/unresponsive, choose "Unknown/unresponsive"

Respond with ONLY the topic name, nothing else."""

            # Log prompt
            thinking.log_prompt(
                "TopicDetectionAgent",
                prompt,
                {
                    "method": "llm_smart",
                    "sdk_hint": sdk_hint,
                    "keywords_matched": keywords_hint,
                    "text_length": len(text),
                    "client_type": self.client_type,
                    "model": self.quick_model
                }
            )

            # Call LLM with retry + exponential backoff
            try:
                topic_name, tokens_used = await self._call_llm_with_retry(prompt, max_tokens=50)
            except Exception as e:
                self.logger.warning(f"LLM smart classification failed after 6 retries: {e}")
                return None
            
            # Log response
            thinking.log_response(
                "TopicDetectionAgent",
                topic_name,
                tokens_used=tokens_used,
                model=self.quick_model
            )
            
            # Validate it's a real topic
            if topic_name in self.topics or topic_name == 'Unknown/unresponsive':
                # Check if LLM agreed with hints
                agreed_with_sdk = (topic_name == sdk_hint) if sdk_hint else None
                confidence = 0.90 if agreed_with_sdk else 0.80  # Higher if validates hint
                
                thinking.log_reasoning(
                    "TopicDetectionAgent",
                    f"Classified as '{topic_name}'",
                    f"LLM analyzed text context. SDK hint: {sdk_hint or 'none'}. " +
                    f"{'Agreed with SDK' if agreed_with_sdk else 'Corrected SDK' if sdk_hint else 'No SDK hint'}",
                    {
                        "llm_result": topic_name,
                        "sdk_hint": sdk_hint,
                        "agreed_with_sdk": agreed_with_sdk,
                        "keywords_hint": keywords_hint,
                        "confidence": confidence
                    }
                )
                
                thinking.log_validation(
                    "TopicDetectionAgent",
                    "SDK Hint Validation",
                    agreed_with_sdk if sdk_hint else True,
                    f"LLM {'confirmed' if agreed_with_sdk else 'corrected'} SDK hint" if sdk_hint else "No SDK hint to validate"
                )
                
                return {
                    'topic': topic_name,
                    'method': 'llm_smart',
                    'confidence': confidence,
                    'sdk_validated': agreed_with_sdk if sdk_hint else False,
                    'sdk_hint': sdk_hint,
                    'llm_correction': sdk_hint if (sdk_hint and not agreed_with_sdk) else None
                }
            else:
                self.logger.warning(f"   ⚠️ LLM returned invalid topic: {topic_name}")
                thinking.log_validation(
                    "TopicDetectionAgent",
                    "Topic Validation",
                    False,
                    f"LLM returned '{topic_name}' which is not in topic list"
                )
                return None
                
        except Exception as e:
            self.logger.warning(f"LLM smart classification failed: {e}")
            return None
    
    async def _validate_topic_with_llm(self, text: str, candidate_topics: List[Dict]) -> Optional[Dict]:
        """
        Use LLM to validate/correct low-confidence topic matches.
        
        Args:
            text: Conversation text
            candidate_topics: List of topics detected with low confidence
            
        Returns:
            Validated topic dict or None
        """
        try:
            from src.utils.agent_thinking_logger import AgentThinkingLogger
            thinking = AgentThinkingLogger.get_logger()
            
            # Build list of candidate topic names
            candidate_names = [t['topic'] for t in candidate_topics]
            topic_list = ', '.join(self._get_topic_priority_order()[:10])  # Top 10 topics only
            
            prompt = f"""You are analyzing a customer support conversation to validate its topic classification.

CANDIDATE TOPICS (from keyword matching): {', '.join(candidate_names)}

AVAILABLE TOPICS: {topic_list}

CONVERSATION TEXT:
{text[:1000]}

TASK: Which topic best describes this conversation? Choose ONE topic from the available list.
If none fit well, respond with "Unknown/unresponsive".

Respond with ONLY the topic name, nothing else."""

            # Log prompt if thinking mode enabled
            thinking.log_prompt(
                "TopicDetectionAgent",
                prompt,
                {
                    "method": "llm_validation",
                    "candidates": candidate_names,
                    "text_length": len(text),
                    "client_type": self.client_type,
                    "model": self.quick_model
                }
            )

            # Call LLM with retry + exponential backoff (reuses helper method)
            topic_name, tokens_used = await self._call_llm_with_retry(prompt, max_tokens=50)
            
            # Log response
            thinking.log_response(
                "TopicDetectionAgent",
                topic_name,
                tokens_used=tokens_used,
                model=self.quick_model
            )
            
            # Validate it's a real topic
            if topic_name in self.topics or topic_name == 'Unknown/unresponsive':
                self.logger.info(f"   ✅ LLM validated topic: {topic_name}")
                
                # Was it a correction?
                was_corrected = topic_name != candidate_names[0] if candidate_names else False
                
                thinking.log_reasoning(
                    "TopicDetectionAgent",
                    f"Validated as '{topic_name}'",
                    f"LLM {'corrected' if was_corrected else 'confirmed'} keyword detection",
                    {
                        "original_candidate": candidate_names[0] if candidate_names else None,
                        "llm_result": topic_name,
                        "was_corrected": was_corrected,
                        "confidence": 0.85
                    }
                )
                
                return {
                    'topic': topic_name,
                    'method': 'llm_validated',
                    'confidence': 0.85,
                    'sdk_validated': False,
                    'llm_correction': candidate_names[0] if candidate_names and was_corrected else None
                }
            else:
                self.logger.warning(f"   ⚠️ LLM returned invalid topic: {topic_name}")
                thinking.log_validation(
                    "TopicDetectionAgent",
                    "Topic Validation",
                    False,
                    f"LLM returned '{topic_name}' which is not in topic list"
                )
                return None
                
        except Exception as e:
            self.logger.warning(f"LLM validation failed: {e}")
            return None
    
    async def _classify_with_llm(self, text: str) -> Optional[Dict]:
        """
        Use LLM to classify conversation when no keywords match.
        
        Args:
            text: Conversation text
            
        Returns:
            Topic dict or None
        """
        try:
            from src.utils.agent_thinking_logger import AgentThinkingLogger
            thinking = AgentThinkingLogger.get_logger()
            
            topic_list = ', '.join(self._get_topic_priority_order()[:10])
            
            prompt = f"""You are analyzing a customer support conversation to determine its topic.

AVAILABLE TOPICS: {topic_list}

CONVERSATION TEXT:
{text[:1000]}

TASK: What is the PRIMARY topic of this conversation? Choose ONE topic from the list.
If the conversation is unclear or has no clear topic, respond with "Unknown/unresponsive".

Respond with ONLY the topic name, nothing else."""

            # Log prompt if thinking mode enabled
            thinking.log_prompt(
                "TopicDetectionAgent",
                prompt,
                {
                    "method": "llm_only",
                    "text_length": len(text),
                    "client_type": self.client_type,
                    "model": self.quick_model
                }
            )

            # Call LLM with retry + exponential backoff (reuses helper method)
            topic_name, tokens_used = await self._call_llm_with_retry(prompt, max_tokens=50)
            
            # Log response
            thinking.log_response(
                "TopicDetectionAgent",
                topic_name,
                tokens_used=tokens_used,
                model=self.quick_model
            )
            
            # Validate it's a real topic
            if topic_name in self.topics or topic_name == 'Unknown/unresponsive':
                self.logger.info(f"   ✅ LLM classified as: {topic_name}")
                
                thinking.log_reasoning(
                    "TopicDetectionAgent",
                    f"Classified as '{topic_name}'",
                    "No keywords matched, LLM classified from text context",
                    {"confidence": 0.75, "method": "llm_only"}
                )
                
                return {
                    'topic': topic_name,
                    'method': 'llm_only',
                    'confidence': 0.75,
                    'sdk_validated': False
                }
            else:
                self.logger.warning(f"   ⚠️ LLM returned invalid topic: {topic_name}")
                thinking.log_validation(
                    "TopicDetectionAgent",
                    "Topic Validation",
                    False,
                    f"LLM returned '{topic_name}' which is not in topic list"
                )
                return None
                
        except Exception as e:
            self.logger.warning(f"LLM classification failed: {e}")
            return None

