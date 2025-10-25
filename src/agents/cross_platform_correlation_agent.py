"""
Cross-Platform Correlation Agent for analyzing relationships between Intercom and Canny data.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict, Counter
from datetime import datetime

from src.agents.base_agent import BaseAgent
from src.services.ai_model_factory import AIModelFactory, AIModel
from src.models.canny_models import CannyCrossPlatformInsight


logger = logging.getLogger(__name__)


class CrossPlatformCorrelationAgent(BaseAgent):
    """
    Agent for analyzing correlations between Intercom support conversations and Canny feature requests.
    
    Identifies patterns where:
    - Support issues correlate with feature requests
    - Customer pain points drive feature demand
    - Feature requests correlate with support volume
    """
    
    def __init__(self, ai_factory: AIModelFactory):
        super().__init__(ai_factory)
        self.logger = logging.getLogger(__name__)
    
    async def analyze_correlations(
        self,
        intercom_conversations: List[Dict[str, Any]],
        canny_posts: List[Dict[str, Any]],
        ai_model: AIModel,
        enable_fallback: bool = True
    ) -> Dict[str, Any]:
        """
        Analyze correlations between Intercom and Canny data.
        
        Args:
            intercom_conversations: Preprocessed Intercom conversations
            canny_posts: Preprocessed Canny posts
            ai_model: AI model to use for analysis
            enable_fallback: Whether to use fallback AI model
            
        Returns:
            Dictionary containing correlation insights and recommendations
        """
        self.logger.info(
            f"Starting cross-platform correlation analysis: "
            f"{len(intercom_conversations)} conversations, {len(canny_posts)} Canny posts"
        )
        
        try:
            # Extract topics from both sources
            intercom_topics = self._extract_intercom_topics(intercom_conversations)
            canny_topics = self._extract_canny_topics(canny_posts)
            
            # Find semantic matches between topics
            topic_matches = await self._find_topic_matches(
                intercom_topics,
                canny_topics,
                ai_model,
                enable_fallback
            )
            
            # Calculate correlation strength
            correlations = self._calculate_correlations(
                intercom_conversations,
                canny_posts,
                topic_matches
            )
            
            # Generate unified priorities
            unified_priorities = self._generate_unified_priorities(correlations)
            
            # Generate insights
            insights = self._generate_correlation_insights(
                correlations,
                intercom_topics,
                canny_topics
            )
            
            self.logger.info(f"Found {len(correlations)} cross-platform correlations")
            
            return {
                'correlations': correlations,
                'unified_priorities': unified_priorities,
                'insights': insights,
                'intercom_topic_count': len(intercom_topics),
                'canny_topic_count': len(canny_topics),
                'correlation_count': len(correlations),
                'metadata': {
                    'analysis_date': datetime.now().isoformat(),
                    'intercom_conversations': len(intercom_conversations),
                    'canny_posts': len(canny_posts)
                }
            }
            
        except Exception as e:
            self.logger.error(f"Cross-platform correlation analysis failed: {e}")
            raise
    
    def _extract_intercom_topics(
        self,
        conversations: List[Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Extract topics and metadata from Intercom conversations.
        
        Returns:
            Dictionary mapping topic names to topic metadata
        """
        topics = defaultdict(lambda: {
            'conversations': [],
            'volume': 0,
            'sentiment_counts': Counter(),
            'keywords': set()
        })
        
        for conv in conversations:
            # Extract primary category/topic
            topic = conv.get('primary_category') or conv.get('topic') or 'Unknown'
            
            topics[topic]['conversations'].append(conv)
            topics[topic]['volume'] += 1
            
            # Track sentiment
            sentiment = conv.get('sentiment', 'neutral')
            topics[topic]['sentiment_counts'][sentiment] += 1
            
            # Extract keywords
            text = conv.get('full_text', '')
            if text:
                # Simple keyword extraction (first 5 significant words)
                words = [w.lower() for w in text.split() if len(w) > 4][:5]
                topics[topic]['keywords'].update(words)
        
        # Calculate average sentiment per topic
        for topic_data in topics.values():
            total = sum(topic_data['sentiment_counts'].values())
            if total > 0:
                topic_data['avg_sentiment'] = {
                    'positive': topic_data['sentiment_counts']['positive'] / total,
                    'negative': topic_data['sentiment_counts']['negative'] / total,
                    'neutral': topic_data['sentiment_counts']['neutral'] / total
                }
        
        return dict(topics)
    
    def _extract_canny_topics(
        self,
        posts: List[Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Extract topics and metadata from Canny posts.
        
        Returns:
            Dictionary mapping topic names to topic metadata
        """
        topics = defaultdict(lambda: {
            'posts': [],
            'total_votes': 0,
            'total_comments': 0,
            'avg_engagement': 0.0,
            'status_counts': Counter(),
            'keywords': set()
        })
        
        for post in posts:
            # Extract category as topic
            topic = post.get('category') or 'Uncategorized'
            
            topics[topic]['posts'].append(post)
            topics[topic]['total_votes'] += post.get('score', 0)
            topics[topic]['total_comments'] += post.get('commentCount', 0)
            
            # Track status
            status = post.get('status', 'open')
            topics[topic]['status_counts'][status] += 1
            
            # Extract keywords from title
            title = post.get('title', '')
            if title:
                words = [w.lower() for w in title.split() if len(w) > 4]
                topics[topic]['keywords'].update(words)
        
        # Calculate averages
        for topic_data in topics.values():
            post_count = len(topic_data['posts'])
            if post_count > 0:
                topic_data['avg_engagement'] = (
                    topic_data['total_votes'] * 2 + topic_data['total_comments']
                ) / post_count
        
        return dict(topics)
    
    async def _find_topic_matches(
        self,
        intercom_topics: Dict[str, Dict],
        canny_topics: Dict[str, Dict],
        ai_model: AIModel,
        enable_fallback: bool
    ) -> List[Tuple[str, str, float]]:
        """
        Find semantic matches between Intercom and Canny topics using AI.
        
        Returns:
            List of tuples: (intercom_topic, canny_topic, similarity_score)
        """
        self.logger.info("Finding topic matches using AI")
        
        matches = []
        
        # Build prompt for AI to match topics
        intercom_topic_list = list(intercom_topics.keys())
        canny_topic_list = list(canny_topics.keys())
        
        if not intercom_topic_list or not canny_topic_list:
            return matches
        
        prompt = f"""Analyze these two lists of topics and identify semantic matches.

Intercom Support Topics:
{', '.join(intercom_topic_list)}

Canny Feature Request Topics:
{', '.join(canny_topic_list)}

For each Intercom topic, identify which Canny topic(s) it might relate to and rate the similarity from 0.0 to 1.0.
Consider:
- Semantic similarity (e.g., "API Issues" matches "API Integration")
- Cause-effect relationships (e.g., "Export Problems" might drive "CSV Export" requests)
- Common pain points

Return as JSON array:
[{{"intercom_topic": "...", "canny_topic": "...", "similarity": 0.8, "reason": "..."}}]

Only include matches with similarity >= 0.5.
"""
        
        try:
            # Use AI to find matches
            response = await self.ai_factory.generate_response(
                prompt=prompt,
                model=ai_model,
                temperature=0.3,  # Lower temperature for more consistent matching
                enable_fallback=enable_fallback
            )
            
            # Parse AI response (assuming JSON format)
            import json
            try:
                # Try to extract JSON from response
                response_text = response if isinstance(response, str) else response.get('content', '')
                
                # Find JSON array in response
                start = response_text.find('[')
                end = response_text.rfind(']') + 1
                if start >= 0 and end > start:
                    json_text = response_text[start:end]
                    ai_matches = json.loads(json_text)
                    
                    for match in ai_matches:
                        matches.append((
                            match['intercom_topic'],
                            match['canny_topic'],
                            match['similarity']
                        ))
            except (json.JSONDecodeError, KeyError) as e:
                self.logger.warning(f"Failed to parse AI response as JSON: {e}")
                # Fall back to simple keyword matching
                matches = self._fallback_keyword_matching(intercom_topics, canny_topics)
        
        except Exception as e:
            self.logger.warning(f"AI topic matching failed: {e}, using keyword fallback")
            matches = self._fallback_keyword_matching(intercom_topics, canny_topics)
        
        return matches
    
    def _fallback_keyword_matching(
        self,
        intercom_topics: Dict[str, Dict],
        canny_topics: Dict[str, Dict]
    ) -> List[Tuple[str, str, float]]:
        """
        Fallback method for matching topics based on keyword overlap.
        
        Returns:
            List of tuples: (intercom_topic, canny_topic, similarity_score)
        """
        matches = []
        
        for intercom_topic, intercom_data in intercom_topics.items():
            intercom_keywords = intercom_data.get('keywords', set())
            
            for canny_topic, canny_data in canny_topics.items():
                canny_keywords = canny_data.get('keywords', set())
                
                # Calculate Jaccard similarity
                if intercom_keywords and canny_keywords:
                    intersection = len(intercom_keywords & canny_keywords)
                    union = len(intercom_keywords | canny_keywords)
                    similarity = intersection / union if union > 0 else 0.0
                    
                    # Also check for simple name similarity
                    name_similarity = 0.0
                    if intercom_topic.lower() in canny_topic.lower() or canny_topic.lower() in intercom_topic.lower():
                        name_similarity = 0.7
                    
                    # Combined score
                    final_similarity = max(similarity, name_similarity)
                    
                    if final_similarity >= 0.3:
                        matches.append((intercom_topic, canny_topic, final_similarity))
        
        return matches
    
    def _calculate_correlations(
        self,
        conversations: List[Dict],
        posts: List[Dict],
        topic_matches: List[Tuple[str, str, float]]
    ) -> List[CannyCrossPlatformInsight]:
        """
        Calculate correlation strength and generate insights for each match.
        
        Returns:
            List of CannyCrossPlatformInsight objects
        """
        correlations = []
        
        for intercom_topic, canny_topic, similarity in topic_matches:
            # Count volumes
            intercom_volume = sum(
                1 for conv in conversations
                if conv.get('primary_category') == intercom_topic or conv.get('topic') == intercom_topic
            )
            
            canny_votes = sum(
                post.get('score', 0) for post in posts
                if post.get('category') == canny_topic
            )
            
            # Calculate correlation strength (weighted by volume and similarity)
            # Normalize by total volume
            total_conversations = len(conversations)
            total_votes = sum(post.get('score', 0) for post in posts)
            
            volume_factor = intercom_volume / total_conversations if total_conversations > 0 else 0
            vote_factor = canny_votes / total_votes if total_votes > 0 else 0
            
            correlation_strength = (similarity * 0.4) + (volume_factor * 0.3) + (vote_factor * 0.3)
            
            # Calculate combined priority score
            # Higher score = more important to address
            combined_priority = (
                (intercom_volume * 2) +  # Support volume is important
                (canny_votes * 1) +      # Votes show demand
                (similarity * 50)         # Strong correlation matters
            )
            
            # Generate recommendation
            recommendation = self._generate_recommendation(
                intercom_topic,
                canny_topic,
                intercom_volume,
                canny_votes,
                correlation_strength
            )
            
            insight = CannyCrossPlatformInsight(
                intercom_issue=intercom_topic,
                canny_request=canny_topic,
                correlation_strength=round(correlation_strength, 3),
                intercom_volume=intercom_volume,
                canny_votes=canny_votes,
                combined_priority_score=round(combined_priority, 2),
                recommendation=recommendation
            )
            
            correlations.append(insight)
        
        # Sort by priority score
        correlations.sort(key=lambda x: x.combined_priority_score, reverse=True)
        
        return correlations
    
    def _generate_recommendation(
        self,
        intercom_topic: str,
        canny_topic: str,
        intercom_volume: int,
        canny_votes: int,
        correlation_strength: float
    ) -> str:
        """Generate actionable recommendation based on correlation data."""
        
        if correlation_strength > 0.7 and intercom_volume > 20:
            return (
                f"HIGH PRIORITY: Strong correlation between '{intercom_topic}' support issues "
                f"({intercom_volume} conversations) and '{canny_topic}' feature request "
                f"({canny_votes} votes). Implementing this feature could significantly "
                f"reduce support volume."
            )
        elif correlation_strength > 0.5 and canny_votes > 50:
            return (
                f"MEDIUM PRIORITY: '{canny_topic}' feature request ({canny_votes} votes) "
                f"relates to '{intercom_topic}' support issues ({intercom_volume} conversations). "
                f"Consider for roadmap prioritization."
            )
        elif intercom_volume > 10:
            return (
                f"INVESTIGATE: '{intercom_topic}' has {intercom_volume} support conversations. "
                f"Related '{canny_topic}' request has {canny_votes} votes. "
                f"May indicate a gap in product functionality."
            )
        else:
            return (
                f"MONITOR: Moderate correlation between '{intercom_topic}' and '{canny_topic}'. "
                f"Track over time to see if this becomes a larger issue."
            )
    
    def _generate_unified_priorities(
        self,
        correlations: List[CannyCrossPlatformInsight]
    ) -> List[Dict[str, Any]]:
        """
        Generate unified priority list combining Intercom and Canny data.
        
        Returns:
            List of prioritized items with combined scoring
        """
        priorities = []
        
        for correlation in correlations[:10]:  # Top 10
            priority_level = "HIGH" if correlation.combined_priority_score > 100 else \
                           "MEDIUM" if correlation.combined_priority_score > 50 else "LOW"
            
            priorities.append({
                'rank': len(priorities) + 1,
                'intercom_issue': correlation.intercom_issue,
                'canny_request': correlation.canny_request,
                'priority_score': correlation.combined_priority_score,
                'priority_level': priority_level,
                'support_volume': correlation.intercom_volume,
                'feature_votes': correlation.canny_votes,
                'correlation_strength': correlation.correlation_strength,
                'recommendation': correlation.recommendation
            })
        
        return priorities
    
    def _generate_correlation_insights(
        self,
        correlations: List[CannyCrossPlatformInsight],
        intercom_topics: Dict[str, Dict],
        canny_topics: Dict[str, Dict]
    ) -> List[str]:
        """Generate high-level insights from correlation analysis."""
        insights = []
        
        if not correlations:
            insights.append("No significant correlations found between Intercom issues and Canny requests.")
            return insights
        
        # High correlation insights
        high_correlations = [c for c in correlations if c.correlation_strength > 0.7]
        if high_correlations:
            insights.append(
                f"Found {len(high_correlations)} strong correlations between support issues "
                f"and feature requests, indicating clear product-market fit opportunities."
            )
        
        # High support volume insights
        high_volume = [c for c in correlations if c.intercom_volume > 20]
        if high_volume:
            top_issue = high_volume[0]
            insights.append(
                f"'{top_issue.intercom_issue}' is driving {top_issue.intercom_volume} support "
                f"conversations and correlates with '{top_issue.canny_request}' feature request. "
                f"Addressing this could significantly reduce support load."
            )
        
        # High vote insights
        high_votes = [c for c in correlations if c.canny_votes > 50]
        if high_votes:
            insights.append(
                f"{len(high_votes)} highly-voted feature requests correlate with active support issues, "
                f"suggesting strong user demand backed by pain points."
            )
        
        # Priority recommendations
        if correlations:
            top_priority = correlations[0]
            insights.append(
                f"TOP RECOMMENDATION: {top_priority.recommendation}"
            )
        
        return insights


if __name__ == "__main__":
    # Basic test
    pass

