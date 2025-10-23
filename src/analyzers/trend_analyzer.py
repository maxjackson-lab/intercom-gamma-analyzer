"""
Trend analyzer for general purpose analysis.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from src.analyzers.base_analyzer import BaseAnalyzer
from src.models.analysis_models import AnalysisRequest, TrendAnalysisResults
from src.config.prompts import PromptTemplates

logger = logging.getLogger(__name__)


class TrendAnalyzer(BaseAnalyzer):
    """Analyzer for general purpose trend analysis."""
    
    async def analyze(self, request: AnalysisRequest) -> TrendAnalysisResults:
        """Perform trend analysis."""
        start_time = datetime.now()
        self.logger.info(f"Starting trend analysis for {request.start_date} to {request.end_date}")
        
        # Validate request
        if not request.start_date or not request.end_date:
            raise ValueError("Start date and end date are required for trend analysis")
        
        # Fetch conversations
        conversations = await self.fetch_conversations(request)
        self.logger.info(f"Fetched {len(conversations)} conversations")
        
        if len(conversations) < 10:
            self.logger.warning(f"Low conversation count: {len(conversations)}. Analysis may be less reliable.")
        
        # Calculate metrics
        metrics = await self.calculate_metrics(conversations, request)
        
        # Generate AI insights
        ai_insights = await self.generate_ai_insights(conversations, metrics, request)
        
        # Calculate trend data
        trend_data = await self._calculate_trend_data(conversations, metrics)
        
        # Identify key trends
        key_trends = await self._identify_key_trends(trend_data, metrics)
        
        # Generate trend explanations
        trend_explanations = await self._generate_trend_explanations(key_trends)
        
        # Generate trend implications
        trend_implications = await self._generate_trend_implications(key_trends, metrics)
        
        # Calculate analysis duration
        analysis_duration = self._calculate_analysis_duration(start_time)
        
        # Create results
        results = TrendAnalysisResults(
            request=request,
            analysis_date=datetime.now(),
            volume_trends=trend_data.get("volume_trends", {}),
            response_time_trends=trend_data.get("response_time_trends", {}),
            satisfaction_trends=trend_data.get("satisfaction_trends", {}),
            topic_trends=trend_data.get("topic_trends", {}),
            keyword_trends=trend_data.get("keyword_trends", {}),
            sentiment_trends=trend_data.get("sentiment_trends", {}),
            key_trends=key_trends,
            trend_explanations=trend_explanations,
            trend_implications=trend_implications,
            total_conversations_analyzed=len(conversations),
            analysis_duration_seconds=analysis_duration
        )
        
        self.logger.info(f"Trend analysis completed in {analysis_duration:.2f} seconds")
        return results
    
    async def _calculate_trend_data(self, conversations: List[Dict], metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate trend data from conversations and metrics."""
        self.logger.info("Calculating trend data")
        
        trend_data = {
            "volume_trends": {},
            "response_time_trends": {},
            "satisfaction_trends": {},
            "topic_trends": {},
            "keyword_trends": {},
            "sentiment_trends": {}
        }
        
        # Volume trends
        trend_data["volume_trends"] = self._calculate_volume_trends(conversations)
        
        # Response time trends
        trend_data["response_time_trends"] = self._calculate_response_time_trends(conversations)
        
        # Satisfaction trends
        trend_data["satisfaction_trends"] = self._calculate_satisfaction_trends(conversations)
        
        # Topic trends
        trend_data["topic_trends"] = self._calculate_topic_trends(conversations)
        
        # Keyword trends
        trend_data["keyword_trends"] = self._calculate_keyword_trends(conversations)
        
        # Sentiment trends
        trend_data["sentiment_trends"] = self._calculate_sentiment_trends(conversations)
        
        return trend_data
    
    def _calculate_volume_trends(self, conversations: List[Dict]) -> Dict[str, Any]:
        """Calculate volume trends over time."""
        from collections import defaultdict
        import numpy as np
        
        daily_volumes = defaultdict(int)
        hourly_volumes = defaultdict(int)
        
        for conv in conversations:
            created_at = conv.get('created_at')
            if created_at:
                dt = datetime.fromtimestamp(created_at)
                daily_volumes[dt.date()] += 1
                hourly_volumes[dt.hour] += 1
        
        # Calculate trends
        daily_values = list(daily_volumes.values())
        hourly_values = list(hourly_volumes.values())
        
        return {
            "daily_volumes": dict(daily_volumes),
            "hourly_volumes": dict(hourly_volumes),
            "average_daily_volume": np.mean(daily_values) if daily_values else 0,
            "peak_hour": max(hourly_volumes.items(), key=lambda x: x[1])[0] if hourly_volumes else 0,
            "volume_variance": np.var(daily_values) if daily_values else 0
        }
    
    def _calculate_response_time_trends(self, conversations: List[Dict]) -> Dict[str, Any]:
        """Calculate response time trends."""
        import numpy as np
        
        response_times = []
        response_times_by_day = defaultdict(list)
        
        for conv in conversations:
            created_at = conv.get('created_at')
            if not created_at:
                continue
            
            parts = conv.get('conversation_parts', {}).get('conversation_parts', [])
            for part in parts:
                if part.get('author', {}).get('type') == 'admin':
                    response_time = part.get('created_at') - created_at
                    response_times.append(response_time)
                    
                    dt = datetime.fromtimestamp(created_at)
                    response_times_by_day[dt.date()].append(response_time)
                    break
        
        # Calculate trends
        avg_response_times_by_day = {
            date: np.mean(times) for date, times in response_times_by_day.items()
        }
        
        return {
            "response_times": response_times,
            "average_response_time": np.mean(response_times) if response_times else 0,
            "median_response_time": np.median(response_times) if response_times else 0,
            "response_time_trend": avg_response_times_by_day,
            "response_time_variance": np.var(response_times) if response_times else 0
        }
    
    def _calculate_satisfaction_trends(self, conversations: List[Dict]) -> Dict[str, Any]:
        """Calculate satisfaction trends."""
        import numpy as np
        
        ratings = []
        ratings_by_day = defaultdict(list)
        
        for conv in conversations:
            rating = conv.get('conversation_rating')
            if rating:
                ratings.append(rating)
                
                created_at = conv.get('created_at')
                if created_at:
                    dt = datetime.fromtimestamp(created_at)
                    ratings_by_day[dt.date()].append(rating)
        
        # Calculate trends
        avg_ratings_by_day = {
            date: np.mean(day_ratings) for date, day_ratings in ratings_by_day.items()
        }
        
        return {
            "ratings": ratings,
            "average_rating": np.mean(ratings) if ratings else 0,
            "rating_trend": avg_ratings_by_day,
            "rating_variance": np.var(ratings) if ratings else 0,
            "satisfaction_score": (np.mean(ratings) / 5.0 * 100) if ratings else 0
        }
    
    def _calculate_topic_trends(self, conversations: List[Dict]) -> Dict[str, Any]:
        """Calculate topic trends over time."""
        from collections import defaultdict, Counter
        
        topics_by_day = defaultdict(Counter)
        
        for conv in conversations:
            created_at = conv.get('created_at')
            if not created_at:
                continue
            
            # Extract topics (simplified)
            text = self._extract_conversation_text(conv)
            topics = self._extract_topics(text)
            
            dt = datetime.fromtimestamp(created_at)
            for topic in topics:
                topics_by_day[dt.date()][topic] += 1
        
        # Calculate trending topics
        all_topics = Counter()
        for day_topics in topics_by_day.values():
            all_topics.update(day_topics)
        
        trending_topics = all_topics.most_common(10)
        
        return {
            "topics_by_day": {str(date): dict(topics) for date, topics in topics_by_day.items()},
            "trending_topics": [{"topic": topic, "count": count} for topic, count in trending_topics],
            "total_unique_topics": len(all_topics)
        }
    
    def _calculate_keyword_trends(self, conversations: List[Dict]) -> Dict[str, Any]:
        """Calculate keyword frequency trends."""
        from collections import Counter
        
        all_keywords = []
        keywords_by_day = defaultdict(Counter)
        
        for conv in conversations:
            created_at = conv.get('created_at')
            if not created_at:
                continue
            
            text = self._extract_conversation_text(conv)
            keywords = self._extract_keywords(text)
            
            all_keywords.extend(keywords)
            
            dt = datetime.fromtimestamp(created_at)
            for keyword in keywords:
                keywords_by_day[dt.date()][keyword] += 1
        
        # Calculate keyword frequency
        keyword_freq = Counter(all_keywords)
        top_keywords = keyword_freq.most_common(20)
        
        return {
            "keyword_frequency": dict(keyword_freq),
            "top_keywords": [{"keyword": kw, "count": count} for kw, count in top_keywords],
            "keywords_by_day": {str(date): dict(keywords) for date, keywords in keywords_by_day.items()},
            "total_unique_keywords": len(keyword_freq)
        }
    
    def _calculate_sentiment_trends(self, conversations: List[Dict]) -> Dict[str, Any]:
        """Calculate sentiment trends over time."""
        from collections import defaultdict
        
        sentiment_by_day = defaultdict(lambda: {"positive": 0, "negative": 0, "neutral": 0})
        
        for conv in conversations:
            created_at = conv.get('created_at')
            if not created_at:
                continue
            
            text = self._extract_conversation_text(conv)
            sentiment = self._analyze_sentiment(text)
            
            dt = datetime.fromtimestamp(created_at)
            sentiment_by_day[dt.date()][sentiment] += 1
        
        # Calculate sentiment trends
        total_sentiment = {"positive": 0, "negative": 0, "neutral": 0}
        for day_sentiment in sentiment_by_day.values():
            for sentiment, count in day_sentiment.items():
                total_sentiment[sentiment] += count
        
        return {
            "sentiment_by_day": {str(date): sentiment for date, sentiment in sentiment_by_day.items()},
            "overall_sentiment": total_sentiment,
            "sentiment_distribution": {
                sentiment: count / sum(total_sentiment.values()) * 100
                for sentiment, count in total_sentiment.items()
            } if sum(total_sentiment.values()) > 0 else {}
        }
    
    async def _identify_key_trends(self, trend_data: Dict[str, Any], metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify key trends from the data."""
        trends = []
        
        # Volume trends
        volume_trends = trend_data.get("volume_trends", {})
        if volume_trends.get("average_daily_volume", 0) > 0:
            trends.append({
                "name": "Conversation Volume",
                "description": f"Average daily volume: {volume_trends['average_daily_volume']:.1f} conversations",
                "type": "volume",
                "significance": "high" if volume_trends['average_daily_volume'] > 50 else "medium"
            })
        
        # Response time trends
        response_trends = trend_data.get("response_time_trends", {})
        avg_response_time = response_trends.get("average_response_time", 0)
        if avg_response_time > 0:
            trends.append({
                "name": "Response Time Performance",
                "description": f"Average response time: {avg_response_time/3600:.1f} hours",
                "type": "efficiency",
                "significance": "high" if avg_response_time > 7200 else "medium"
            })
        
        # Satisfaction trends
        satisfaction_trends = trend_data.get("satisfaction_trends", {})
        avg_rating = satisfaction_trends.get("average_rating", 0)
        if avg_rating > 0:
            trends.append({
                "name": "Customer Satisfaction",
                "description": f"Average rating: {avg_rating:.1f}/5.0",
                "type": "satisfaction",
                "significance": "high" if avg_rating > 4.0 else "medium"
            })
        
        # Topic trends
        topic_trends = trend_data.get("topic_trends", {})
        trending_topics = topic_trends.get("trending_topics", [])
        if trending_topics:
            top_topic = trending_topics[0]
            trends.append({
                "name": "Top Support Topic",
                "description": f"Most common topic: {top_topic['topic']} ({top_topic['count']} mentions)",
                "type": "topics",
                "significance": "medium"
            })
        
        # Sentiment trends
        sentiment_trends = trend_data.get("sentiment_trends", {})
        sentiment_dist = sentiment_trends.get("sentiment_distribution", {})
        if sentiment_dist:
            dominant_sentiment = max(sentiment_dist.items(), key=lambda x: x[1])
            trends.append({
                "name": "Customer Sentiment",
                "description": f"Dominant sentiment: {dominant_sentiment[0]} ({dominant_sentiment[1]:.1f}%)",
                "type": "sentiment",
                "significance": "high" if dominant_sentiment[0] == "positive" else "medium"
            })
        
        return trends
    
    async def _generate_trend_explanations(self, key_trends: List[Dict[str, Any]]) -> Dict[str, str]:
        """Generate explanations for key trends."""
        explanations = {}
        
        for trend in key_trends:
            trend_name = trend["name"]
            trend_type = trend["type"]
            
            if trend_type == "volume":
                explanations[trend_name] = "This trend indicates the overall level of customer engagement and support demand."
            elif trend_type == "efficiency":
                explanations[trend_name] = "This trend reflects the speed and effectiveness of support response."
            elif trend_type == "satisfaction":
                explanations[trend_name] = "This trend shows customer satisfaction with support interactions."
            elif trend_type == "topics":
                explanations[trend_name] = "This trend reveals the most common customer concerns and support needs."
            elif trend_type == "sentiment":
                explanations[trend_name] = "This trend indicates the overall emotional tone of customer interactions."
            else:
                explanations[trend_name] = "This trend provides insights into customer support patterns."
        
        return explanations
    
    async def _generate_trend_implications(self, key_trends: List[Dict[str, Any]], metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate implications and recommendations based on trends."""
        implications = []
        
        for trend in key_trends:
            trend_name = trend["name"]
            trend_type = trend["type"]
            significance = trend["significance"]
            
            if trend_type == "volume" and significance == "high":
                implications.append({
                    "trend": trend_name,
                    "implication": "High conversation volume may indicate increased customer needs or product issues",
                    "recommendation": "Consider scaling support resources or investigating root causes"
                })
            elif trend_type == "efficiency" and significance == "high":
                implications.append({
                    "trend": trend_name,
                    "implication": "Long response times may impact customer satisfaction",
                    "recommendation": "Optimize support processes and consider automation"
                })
            elif trend_type == "satisfaction" and significance == "high":
                implications.append({
                    "trend": trend_name,
                    "implication": "High satisfaction indicates effective support delivery",
                    "recommendation": "Maintain current support quality and share best practices"
                })
            elif trend_type == "topics":
                implications.append({
                    "trend": trend_name,
                    "implication": "Common topics may indicate areas for product improvement",
                    "recommendation": "Review product documentation and consider feature enhancements"
                })
            elif trend_type == "sentiment" and significance == "high":
                implications.append({
                    "trend": trend_name,
                    "implication": "Positive sentiment indicates good customer experience",
                    "recommendation": "Continue current support approach and monitor for changes"
                })
        
        return implications
    
    # Helper methods
    def _extract_conversation_text(self, conversation: Dict) -> str:
        """Extract all text from a conversation."""
        texts = []
        
        # Source body
        source_body = conversation.get('source', {}).get('body', '')
        if source_body:
            texts.append(source_body)
        
        # Conversation parts
        parts = conversation.get('conversation_parts', {}).get('conversation_parts', [])
        for part in parts:
            part_body = part.get('body', '')
            if part_body:
                texts.append(part_body)
        
        return ' '.join(texts)
    
    def _extract_topics(self, text: str) -> List[str]:
        """Extract topics from text (simplified)."""
        # This is a simplified topic extraction
        # In production, you'd use more sophisticated NLP
        topics = []
        
        if any(word in text.lower() for word in ['billing', 'payment', 'charge']):
            topics.append('billing')
        if any(word in text.lower() for word in ['bug', 'error', 'issue', 'problem']):
            topics.append('technical_issues')
        if any(word in text.lower() for word in ['feature', 'how to', 'tutorial']):
            topics.append('product_questions')
        if any(word in text.lower() for word in ['account', 'login', 'password']):
            topics.append('account_management')
        
        return topics
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text (simplified)."""
        import re
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
        return [word for word in words if len(word) > 3]
    
    def _analyze_sentiment(self, text: str) -> str:
        """Basic sentiment analysis."""
        positive_words = ['good', 'great', 'excellent', 'amazing', 'love', 'perfect', 'helpful', 'thanks']
        negative_words = ['bad', 'terrible', 'awful', 'hate', 'horrible', 'frustrated', 'angry', 'disappointed']
        
        text_lower = text.lower()
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        
        if positive_count > negative_count:
            return 'positive'
        elif negative_count > positive_count:
            return 'negative'
        else:
            return 'neutral'

