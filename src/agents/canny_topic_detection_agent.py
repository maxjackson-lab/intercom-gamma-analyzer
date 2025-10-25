"""
Canny Topic Detection Agent for mapping Canny posts to taxonomy categories.
"""

import logging
from typing import Dict, List, Optional, Any
from collections import defaultdict, Counter

from src.agents.base_agent import BaseAgent, AgentResult, AgentContext, ConfidenceLevel
from src.services.ai_model_factory import AIModelFactory, AIModel


logger = logging.getLogger(__name__)


class CannyTopicDetectionAgent(BaseAgent):
    """
    Agent for detecting and categorizing topics from Canny feature requests.
    
    Maps Canny posts to the existing taxonomy structure to enable unified analysis
    with Intercom conversations.
    """
    
    def __init__(self, ai_factory: AIModelFactory):
        super().__init__(
            name="CannyTopicDetectionAgent",
            model="gpt-4o-mini",
            temperature=0.2
        )
        self.ai_factory = ai_factory
        self.logger = logging.getLogger(__name__)
    
    def get_agent_specific_instructions(self) -> str:
        """Get agent-specific instructions for Canny topic detection"""
        return """
Classify Canny feature requests into taxonomy categories.
Map posts to appropriate categories based on content.
"""
    
    def get_task_description(self, context: AgentContext) -> str:
        """Describe the Canny topic detection task"""
        canny_posts = context.metadata.get('canny_posts', [])
        return f"Classify {len(canny_posts)} Canny posts into taxonomy categories"
    
    def format_context_data(self, context: AgentContext) -> str:
        """Format context data for Canny posts"""
        canny_posts = context.metadata.get('canny_posts', [])
        return f"Canny posts: {len(canny_posts)}"
    
    def validate_input(self, context: AgentContext) -> bool:
        """Validate input has Canny posts"""
        canny_posts = context.metadata.get('canny_posts', [])
        return isinstance(canny_posts, list)
    
    def validate_output(self, result: Dict[str, Any]) -> bool:
        """Validate output contains topic groups"""
        return 'topic_groups' in result
    
    async def execute(self, context: AgentContext) -> AgentResult:
        """Execute Canny topic detection"""
        from datetime import datetime
        start_time = datetime.now()
        
        try:
            canny_posts = context.metadata.get('canny_posts', [])
            
            if not canny_posts:
                return AgentResult(
                    agent_name=self.name,
                    success=True,
                    data={'topic_groups': {}},
                    confidence=1.0,
                    confidence_level=ConfidenceLevel.HIGH,
                    execution_time=0.0
                )
            
            # Detect topics
            topic_groups = await self.detect_topics(canny_posts)
            
            # Get summary
            summary = self.get_topic_summary(topic_groups)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return AgentResult(
                agent_name=self.name,
                success=True,
                data={'topic_groups': topic_groups, 'summary': summary},
                confidence=1.0,
                confidence_level=ConfidenceLevel.HIGH,
                execution_time=execution_time
            )
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            self.logger.error(f"Canny topic detection failed: {e}")
            return AgentResult(
                agent_name=self.name,
                success=False,
                data={},
                confidence=0.0,
                confidence_level=ConfidenceLevel.LOW,
                error_message=str(e),
                execution_time=execution_time
            )
    
    async def detect_topics(
        self,
        canny_posts: List[Dict[str, Any]],
        taxonomy: Optional[Dict[str, Any]] = None,
        ai_model: AIModel = AIModel.OPENAI_GPT4,
        enable_fallback: bool = True
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Detect topics from Canny posts and map to taxonomy.
        
        Args:
            canny_posts: List of preprocessed Canny posts
            taxonomy: Optional taxonomy structure for mapping
            ai_model: AI model to use for classification
            enable_fallback: Whether to enable AI fallback
            
        Returns:
            Dictionary mapping topic names to lists of posts
        """
        self.logger.info(f"Starting topic detection for {len(canny_posts)} Canny posts")
        
        if not canny_posts:
            return {}
        
        try:
            # Use default taxonomy if not provided
            if taxonomy is None:
                taxonomy = self._get_default_taxonomy()
            
            # Classify posts using AI
            classified_posts = await self._classify_posts_with_ai(
                canny_posts,
                taxonomy,
                ai_model,
                enable_fallback
            )
            
            # Group posts by detected topic
            topic_groups = self._group_posts_by_topic(classified_posts)
            
            # Add metadata to each group
            enriched_groups = self._enrich_topic_groups(topic_groups)
            
            self.logger.info(f"Detected {len(enriched_groups)} topics from Canny posts")
            
            return enriched_groups
            
        except Exception as e:
            self.logger.error(f"Canny topic detection failed: {e}")
            # Fall back to category-based grouping
            return self._fallback_category_grouping(canny_posts)
    
    def _get_default_taxonomy(self) -> Dict[str, Any]:
        """
        Get default taxonomy structure for topic mapping.
        
        Returns:
            Dictionary with taxonomy categories
        """
        return {
            'Billing': {
                'description': 'Payment, subscriptions, credits, refunds',
                'keywords': ['payment', 'billing', 'subscription', 'charge', 'refund', 'credit', 'invoice']
            },
            'Bug': {
                'description': 'Technical issues, errors, broken features',
                'keywords': ['bug', 'error', 'broken', 'issue', 'problem', 'crash', 'fix']
            },
            'Product Question': {
                'description': 'How-to questions, feature usage',
                'keywords': ['how', 'question', 'help', 'guide', 'tutorial', 'understand']
            },
            'Account': {
                'description': 'Login, password, email, account settings',
                'keywords': ['account', 'login', 'password', 'email', 'profile', 'settings']
            },
            'API': {
                'description': 'API integration, webhooks, technical integration',
                'keywords': ['api', 'integration', 'webhook', 'developer', 'endpoint', 'authentication']
            },
            'Feedback': {
                'description': 'Feature requests, suggestions, improvements',
                'keywords': ['feature', 'request', 'suggestion', 'improve', 'enhancement', 'add', 'wish']
            },
            'Agent/Buddy': {
                'description': 'AI assistant features and behavior',
                'keywords': ['agent', 'buddy', 'ai', 'assistant', 'chatbot', 'automation']
            },
            'Workspace': {
                'description': 'Team collaboration, sharing, permissions',
                'keywords': ['workspace', 'team', 'collaborate', 'share', 'permission', 'member']
            },
            'Privacy': {
                'description': 'Privacy, security, data protection',
                'keywords': ['privacy', 'security', 'data', 'protection', 'gdpr', 'confidential']
            },
            'Export': {
                'description': 'Export, download, data extraction',
                'keywords': ['export', 'download', 'extract', 'save', 'backup', 'csv', 'pdf']
            }
        }
    
    async def _classify_posts_with_ai(
        self,
        posts: List[Dict[str, Any]],
        taxonomy: Dict[str, Any],
        ai_model: AIModel,
        enable_fallback: bool
    ) -> List[Dict[str, Any]]:
        """
        Classify posts into taxonomy categories using AI.
        
        Returns:
            List of posts with 'detected_topic' field added
        """
        self.logger.info("Classifying Canny posts with AI")
        
        # Build taxonomy description for prompt
        taxonomy_desc = "\n".join([
            f"- {category}: {data['description']}"
            for category, data in taxonomy.items()
        ])
        
        classified_posts = []
        
        # Process in batches to avoid token limits
        batch_size = 10
        for i in range(0, len(posts), batch_size):
            batch = posts[i:i + batch_size]
            
            try:
                # Build prompt with post titles and details
                post_summaries = []
                for idx, post in enumerate(batch):
                    title = post.get('title', '')
                    details = post.get('details', '')[:200]  # Limit details length
                    post_summaries.append(f"{idx}. Title: {title}\n   Details: {details}")
                
                prompt = f"""Classify these Canny feature requests into categories based on the taxonomy below.

TAXONOMY:
{taxonomy_desc}

POSTS:
{chr(10).join(post_summaries)}

For each post (by number), assign the most appropriate category. If multiple categories fit, choose the primary one.

Return as JSON array:
[{{"post_index": 0, "category": "Feedback", "confidence": 0.9}}, ...]
"""
                
                # Get AI classification
                response = await self.ai_factory.generate_response(
                    prompt=prompt,
                    model=ai_model,
                    temperature=0.2,  # Lower temperature for consistent classification
                    enable_fallback=enable_fallback
                )
                
                # Parse response
                classifications = self._parse_ai_classification_response(response)
                
                # Apply classifications to posts
                for classification in classifications:
                    post_idx = classification.get('post_index', -1)
                    if 0 <= post_idx < len(batch):
                        post = batch[post_idx]
                        post['detected_topic'] = classification.get('category', 'Unknown')
                        post['topic_confidence'] = classification.get('confidence', 0.5)
                        classified_posts.append(post)
                
            except Exception as e:
                self.logger.warning(f"AI classification failed for batch: {e}, using fallback")
                # Use fallback keyword matching
                for post in batch:
                    topic = self._fallback_keyword_classification(post, taxonomy)
                    post['detected_topic'] = topic
                    post['topic_confidence'] = 0.6  # Lower confidence for fallback
                    classified_posts.append(post)
        
        return classified_posts
    
    def _parse_ai_classification_response(self, response: Any) -> List[Dict[str, Any]]:
        """Parse AI classification response to extract classifications."""
        import json
        
        try:
            # Handle different response formats
            response_text = response if isinstance(response, str) else response.get('content', '')
            
            # Find JSON array in response
            start = response_text.find('[')
            end = response_text.rfind(']') + 1
            
            if start >= 0 and end > start:
                json_text = response_text[start:end]
                classifications = json.loads(json_text)
                return classifications
            
        except (json.JSONDecodeError, AttributeError) as e:
            self.logger.warning(f"Failed to parse AI response: {e}")
        
        return []
    
    def _fallback_keyword_classification(
        self,
        post: Dict[str, Any],
        taxonomy: Dict[str, Any]
    ) -> str:
        """
        Fallback classification using keyword matching.
        
        Returns:
            Category name
        """
        # Combine title and details for matching
        text = (post.get('title', '') + ' ' + post.get('details', '')).lower()
        
        # Also check existing category
        existing_category = post.get('category', '').lower()
        
        # Score each taxonomy category
        scores = {}
        for category, data in taxonomy.items():
            score = 0
            keywords = data.get('keywords', [])
            
            # Check keyword matches
            for keyword in keywords:
                if keyword in text:
                    score += 2
                if keyword in existing_category:
                    score += 3
            
            # Check for category name in text
            if category.lower() in text or category.lower() in existing_category:
                score += 5
            
            scores[category] = score
        
        # Return category with highest score
        if scores:
            best_category = max(scores.items(), key=lambda x: x[1])
            if best_category[1] > 0:
                return best_category[0]
        
        # Default to Feedback for feature requests
        return 'Feedback'
    
    def _group_posts_by_topic(
        self,
        classified_posts: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Group classified posts by detected topic.
        
        Returns:
            Dictionary mapping topic names to lists of posts
        """
        groups = defaultdict(list)
        
        for post in classified_posts:
            topic = post.get('detected_topic', 'Unknown')
            groups[topic].append(post)
        
        return dict(groups)
    
    def _enrich_topic_groups(
        self,
        topic_groups: Dict[str, List[Dict[str, Any]]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Add metadata to each topic group.
        
        Returns:
            Enriched topic groups with metadata
        """
        enriched = {}
        
        for topic, posts in topic_groups.items():
            # Calculate aggregate metrics
            total_votes = sum(post.get('score', 0) for post in posts)
            total_comments = sum(post.get('commentCount', 0) for post in posts)
            avg_engagement = sum(post.get('engagement_score', 0) for post in posts) / len(posts) if posts else 0
            
            # Count statuses
            status_counts = Counter(post.get('status', 'open') for post in posts)
            
            # Sort posts by engagement
            sorted_posts = sorted(posts, key=lambda p: p.get('engagement_score', 0), reverse=True)
            
            enriched[topic] = {
                'posts': sorted_posts,
                'count': len(posts),
                'total_votes': total_votes,
                'total_comments': total_comments,
                'avg_engagement': round(avg_engagement, 2),
                'status_breakdown': dict(status_counts),
                'top_post': sorted_posts[0] if sorted_posts else None
            }
        
        return enriched
    
    def _fallback_category_grouping(
        self,
        posts: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Fallback grouping based on existing Canny categories.
        
        Returns:
            Dictionary mapping categories to posts
        """
        groups = defaultdict(list)
        
        for post in posts:
            category = post.get('category') or 'Uncategorized'
            post['detected_topic'] = category
            post['topic_confidence'] = 0.5
            groups[category].append(post)
        
        return self._enrich_topic_groups(dict(groups))
    
    def get_topic_summary(
        self,
        topic_groups: Dict[str, List[Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """
        Generate summary statistics for detected topics.
        
        Returns:
            Dictionary with summary metrics
        """
        total_posts = sum(group['count'] for group in topic_groups.values())
        total_votes = sum(group['total_votes'] for group in topic_groups.values())
        
        # Find most active topic
        most_active = max(
            topic_groups.items(),
            key=lambda x: x[1]['count']
        ) if topic_groups else (None, None)
        
        # Find highest voted topic
        highest_voted = max(
            topic_groups.items(),
            key=lambda x: x[1]['total_votes']
        ) if topic_groups else (None, None)
        
        return {
            'total_topics': len(topic_groups),
            'total_posts': total_posts,
            'total_votes': total_votes,
            'average_posts_per_topic': round(total_posts / len(topic_groups), 2) if topic_groups else 0,
            'most_active_topic': most_active[0] if most_active[0] else None,
            'most_active_count': most_active[1]['count'] if most_active[1] else 0,
            'highest_voted_topic': highest_voted[0] if highest_voted[0] else None,
            'highest_voted_count': highest_voted[1]['total_votes'] if highest_voted[1] else 0
        }


if __name__ == "__main__":
    # Basic test
    pass

