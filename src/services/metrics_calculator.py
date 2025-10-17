"""
Business metrics calculator for Intercom conversation analysis.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from collections import Counter, defaultdict
import pandas as pd
import numpy as np

from config.metrics_config import VOICE_METRICS, TREND_METRICS, MetricCategory
from models.analysis_models import (
    VolumeMetrics, EfficiencyMetrics, SatisfactionMetrics, 
    TopicMetrics, GeographicMetrics, FrictionMetrics, ChannelMetrics
)

logger = logging.getLogger(__name__)


class MetricsCalculator:
    """Calculator for business metrics from Intercom conversation data."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def calculate_volume_metrics(self, conversations: List[Dict]) -> VolumeMetrics:
        """Calculate volume-related metrics."""
        self.logger.info(f"Calculating volume metrics for {len(conversations)} conversations")
        
        total_conversations = len(conversations)
        
        # AI resolution rate (conversations with no human agent responses)
        ai_resolved = 0
        for conv in conversations:
            parts = conv.get('conversation_parts', {}).get('conversation_parts', [])
            has_human_response = any(
                part.get('author', {}).get('type') == 'admin' 
                for part in parts
            )
            if not has_human_response:
                ai_resolved += 1
        
        ai_resolution_rate = (ai_resolved / total_conversations * 100) if total_conversations > 0 else 0
        
        # Time-based breakdowns
        conversations_by_day = self._calculate_daily_breakdown(conversations)
        conversations_by_hour = self._calculate_hourly_breakdown(conversations)
        conversations_by_week = self._calculate_weekly_breakdown(conversations)
        
        return VolumeMetrics(
            total_conversations=total_conversations,
            ai_resolution_rate=round(ai_resolution_rate, 2),
            conversations_by_day=conversations_by_day,
            conversations_by_hour=conversations_by_hour,
            conversations_by_week=conversations_by_week
        )
    
    def calculate_efficiency_metrics(self, conversations: List[Dict]) -> EfficiencyMetrics:
        """Calculate efficiency-related metrics."""
        self.logger.info(f"Calculating efficiency metrics for {len(conversations)} conversations")
        
        response_times = []
        handling_times = []
        resolution_times = []
        response_times_by_channel = defaultdict(list)
        handling_times_by_agent = defaultdict(list)
        
        for conv in conversations:
            created_at = conv.get('created_at')
            if not created_at:
                continue
                
            parts = conv.get('conversation_parts', {}).get('conversation_parts', [])
            source_type = conv.get('source', {}).get('type', 'unknown')
            
            # First response time
            first_agent_response = None
            for part in parts:
                if part.get('author', {}).get('type') == 'admin':
                    first_agent_response = part.get('created_at')
                    break
            
            if first_agent_response:
                response_time = first_agent_response - created_at
                response_times.append(response_time)
                response_times_by_channel[source_type].append(response_time)
            
            # Handling time (time between first and last agent response)
            agent_responses = [
                part.get('created_at') for part in parts
                if part.get('author', {}).get('type') == 'admin'
            ]
            
            if len(agent_responses) > 1:
                handling_time = max(agent_responses) - min(agent_responses)
                handling_times.append(handling_time)
                
                # Agent handling time
                for part in parts:
                    if part.get('author', {}).get('type') == 'admin':
                        agent_email = part.get('author', {}).get('email', 'unknown')
                        handling_times_by_agent[agent_email].append(handling_time)
            
            # Resolution time (time to close)
            if conv.get('state') == 'closed' and conv.get('closed_at'):
                resolution_time = conv.get('closed_at') - created_at
                resolution_times.append(resolution_time)
        
        # Calculate medians
        median_response_time = int(np.median(response_times)) if response_times else None
        median_handling_time = int(np.median(handling_times)) if handling_times else None
        median_resolution_time = int(np.median(resolution_times)) if resolution_times else None
        
        # Response time by channel
        response_time_by_channel = {}
        for channel, times in response_times_by_channel.items():
            if times:
                response_time_by_channel[channel] = int(np.median(times))
        
        # Handling time by agent
        handling_time_by_agent = {}
        for agent, times in handling_times_by_agent.items():
            if times:
                handling_time_by_agent[agent] = int(np.median(times))
        
        # Resolution rate
        closed_conversations = sum(1 for conv in conversations if conv.get('state') == 'closed')
        resolution_rate = (closed_conversations / len(conversations) * 100) if conversations else 0
        
        return EfficiencyMetrics(
            median_first_response_seconds=median_response_time,
            median_handling_time_seconds=median_handling_time,
            median_resolution_time_seconds=median_resolution_time,
            response_time_by_channel=response_time_by_channel,
            handling_time_by_agent=handling_time_by_agent,
            resolution_rate=round(resolution_rate, 2)
        )
    
    def calculate_satisfaction_metrics(self, conversations: List[Dict]) -> SatisfactionMetrics:
        """Calculate satisfaction-related metrics."""
        self.logger.info(f"Calculating satisfaction metrics for {len(conversations)} conversations")
        
        ratings = []
        ratings_by_tier = defaultdict(list)
        ratings_by_channel = defaultdict(list)
        ratings_by_country = defaultdict(list)
        
        positive_sentiment = 0
        negative_sentiment = 0
        neutral_sentiment = 0
        
        for conv in conversations:
            # CSAT ratings
            rating = conv.get('conversation_rating')
            if rating:
                ratings.append(rating)
                
                # By tier
                contact = conv.get('contacts', {}).get('contacts', [{}])[0] if conv.get('contacts', {}).get('contacts') else {}
                user_tier = contact.get('custom_attributes', {}).get('tier', 'unknown')
                ratings_by_tier[user_tier].append(rating)
                
                # By channel
                source_type = conv.get('source', {}).get('type', 'unknown')
                ratings_by_channel[source_type].append(rating)
                
                # By country
                country = contact.get('location', {}).get('country', 'unknown')
                ratings_by_country[country].append(rating)
            
            # Sentiment analysis (basic keyword-based)
            text = self._extract_conversation_text(conv)
            sentiment = self._analyze_sentiment(text)
            if sentiment == 'positive':
                positive_sentiment += 1
            elif sentiment == 'negative':
                negative_sentiment += 1
            else:
                neutral_sentiment += 1
        
        # Calculate overall CSAT
        overall_csat = np.mean(ratings) if ratings else None
        
        # CSAT by tier
        csat_by_tier = {}
        for tier, tier_ratings in ratings_by_tier.items():
            if tier_ratings:
                csat_by_tier[tier] = round(np.mean(tier_ratings), 2)
        
        # CSAT by channel
        csat_by_channel = {}
        for channel, channel_ratings in ratings_by_channel.items():
            if channel_ratings:
                csat_by_channel[channel] = round(np.mean(channel_ratings), 2)
        
        # CSAT by country
        csat_by_country = {}
        for country, country_ratings in ratings_by_country.items():
            if country_ratings:
                csat_by_country[country] = round(np.mean(country_ratings), 2)
        
        return SatisfactionMetrics(
            overall_csat=round(overall_csat, 2) if overall_csat else None,
            csat_by_tier=csat_by_tier,
            csat_by_channel=csat_by_channel,
            csat_by_country=csat_by_country,
            positive_sentiment_count=positive_sentiment,
            negative_sentiment_count=negative_sentiment,
            neutral_sentiment_count=neutral_sentiment
        )
    
    def calculate_topic_metrics(self, conversations: List[Dict]) -> TopicMetrics:
        """Calculate topic-related metrics."""
        self.logger.info(f"Calculating topic metrics for {len(conversations)} conversations")
        
        # Extract keywords and topics
        all_keywords = []
        billing_keywords = []
        product_keywords = []
        account_keywords = []
        
        for conv in conversations:
            text = self._extract_conversation_text(conv)
            keywords = self._extract_keywords(text)
            all_keywords.extend(keywords)
            
            # Categorize by topic
            if self._is_billing_related(text):
                billing_keywords.extend(keywords)
            elif self._is_product_related(text):
                product_keywords.extend(keywords)
            elif self._is_account_related(text):
                account_keywords.extend(keywords)
        
        # Top contact reasons
        keyword_freq = Counter(all_keywords)
        top_contact_reasons = [
            {"keyword": kw, "count": count, "percentage": round(count/len(conversations)*100, 1)}
            for kw, count in keyword_freq.most_common(10)
        ]
        
        # Billing breakdown
        billing_freq = Counter(billing_keywords)
        billing_breakdown = dict(billing_freq.most_common(10))
        
        # Product questions
        product_freq = Counter(product_keywords)
        product_questions = [
            {"topic": kw, "count": count, "percentage": round(count/len(conversations)*100, 1)}
            for kw, count in product_freq.most_common(15)
        ]
        
        # Account questions
        account_freq = Counter(account_keywords)
        account_questions = dict(account_freq.most_common(10))
        
        return TopicMetrics(
            top_contact_reasons=top_contact_reasons,
            billing_breakdown=billing_breakdown,
            product_questions=product_questions,
            account_questions=account_questions,
            keyword_frequency=dict(keyword_freq.most_common(50))
        )
    
    def calculate_geographic_metrics(self, conversations: List[Dict], tier1_countries: List[str]) -> GeographicMetrics:
        """Calculate geographic-related metrics."""
        self.logger.info(f"Calculating geographic metrics for {len(conversations)} conversations")
        
        country_counts = Counter()
        tier1_metrics = {}
        
        for conv in conversations:
            contact = conv.get('contacts', {}).get('contacts', [{}])[0] if conv.get('contacts', {}).get('contacts') else {}
            country = contact.get('location', {}).get('country', 'unknown')
            country_counts[country] += 1
        
        # Tier 1 country analysis
        for country in tier1_countries:
            count = country_counts.get(country, 0)
            percentage = (count / len(conversations) * 100) if conversations else 0
            tier1_metrics[country] = {
                "conversations": count,
                "percentage": round(percentage, 2)
            }
        
        # Top countries
        top_countries = [
            {"country": country, "count": count, "percentage": round(count/len(conversations)*100, 1)}
            for country, count in country_counts.most_common(20)
        ]
        
        return GeographicMetrics(
            tier1_metrics=tier1_metrics,
            country_breakdown=dict(country_counts),
            top_countries=top_countries
        )
    
    def calculate_friction_metrics(self, conversations: List[Dict]) -> FrictionMetrics:
        """Calculate friction-related metrics."""
        self.logger.info(f"Calculating friction metrics for {len(conversations)} conversations")
        
        escalation_patterns = []
        friction_points = []
        common_complaints = []
        resolution_failures = []
        
        for conv in conversations:
            text = self._extract_conversation_text(conv)
            
            # Escalation patterns
            if self._is_escalation(text):
                escalation_patterns.append({
                    "conversation_id": conv.get('id'),
                    "reason": self._identify_escalation_reason(text),
                    "text_preview": text[:200] + "..." if len(text) > 200 else text
                })
            
            # Friction points
            if self._has_friction_indicators(text):
                friction_points.append({
                    "conversation_id": conv.get('id'),
                    "friction_type": self._identify_friction_type(text),
                    "text_preview": text[:200] + "..." if len(text) > 200 else text
                })
            
            # Common complaints
            if self._is_complaint(text):
                common_complaints.append({
                    "conversation_id": conv.get('id'),
                    "complaint_type": self._identify_complaint_type(text),
                    "text_preview": text[:200] + "..." if len(text) > 200 else text
                })
            
            # Resolution failures
            if conv.get('state') != 'closed' and self._is_old_conversation(conv):
                resolution_failures.append({
                    "conversation_id": conv.get('id'),
                    "age_days": self._calculate_conversation_age(conv),
                    "text_preview": text[:200] + "..." if len(text) > 200 else text
                })
        
        return FrictionMetrics(
            escalation_patterns=escalation_patterns[:10],  # Top 10
            friction_points=friction_points[:10],
            common_complaints=common_complaints[:10],
            resolution_failures=resolution_failures[:10]
        )
    
    def calculate_channel_metrics(self, conversations: List[Dict]) -> ChannelMetrics:
        """Calculate channel-related metrics."""
        self.logger.info(f"Calculating channel metrics for {len(conversations)} conversations")
        
        channel_counts = Counter()
        channel_satisfaction = defaultdict(list)
        channel_response_times = defaultdict(list)
        
        for conv in conversations:
            source_type = conv.get('source', {}).get('type', 'unknown')
            channel_counts[source_type] += 1
            
            # Channel satisfaction
            rating = conv.get('conversation_rating')
            if rating:
                channel_satisfaction[source_type].append(rating)
            
            # Channel response times
            created_at = conv.get('created_at')
            if created_at:
                parts = conv.get('conversation_parts', {}).get('conversation_parts', [])
                first_agent_response = None
                for part in parts:
                    if part.get('author', {}).get('type') == 'admin':
                        first_agent_response = part.get('created_at')
                        break
                
                if first_agent_response:
                    response_time = first_agent_response - created_at
                    channel_response_times[source_type].append(response_time)
        
        # Channel performance
        channel_performance = {}
        for channel in channel_counts.keys():
            channel_performance[channel] = {
                "volume": channel_counts[channel],
                "percentage": round(channel_counts[channel] / len(conversations) * 100, 2),
                "avg_satisfaction": round(np.mean(channel_satisfaction[channel]), 2) if channel_satisfaction[channel] else None,
                "avg_response_time": int(np.mean(channel_response_times[channel])) if channel_response_times[channel] else None
            }
        
        # Channel satisfaction
        csat_by_channel = {}
        for channel, ratings in channel_satisfaction.items():
            if ratings:
                csat_by_channel[channel] = round(np.mean(ratings), 2)
        
        # Channel response times
        response_times_by_channel = {}
        for channel, times in channel_response_times.items():
            if times:
                response_times_by_channel[channel] = int(np.mean(times))
        
        return ChannelMetrics(
            channel_performance=channel_performance,
            channel_satisfaction=csat_by_channel,
            channel_volume=dict(channel_counts),
            channel_response_times=response_times_by_channel
        )
    
    # Helper methods
    def _calculate_daily_breakdown(self, conversations: List[Dict]) -> Dict[str, int]:
        """Calculate conversations by day."""
        daily_counts = Counter()
        for conv in conversations:
            created_at = conv.get('created_at')
            if created_at:
                date_str = datetime.fromtimestamp(created_at).strftime('%Y-%m-%d')
                daily_counts[date_str] += 1
        return dict(daily_counts)
    
    def _calculate_hourly_breakdown(self, conversations: List[Dict]) -> Dict[int, int]:
        """Calculate conversations by hour."""
        hourly_counts = Counter()
        for conv in conversations:
            created_at = conv.get('created_at')
            if created_at:
                hour = datetime.fromtimestamp(created_at).hour
                hourly_counts[hour] += 1
        return dict(hourly_counts)
    
    def _calculate_weekly_breakdown(self, conversations: List[Dict]) -> Dict[str, int]:
        """Calculate conversations by week."""
        weekly_counts = Counter()
        for conv in conversations:
            created_at = conv.get('created_at')
            if created_at:
                dt = datetime.fromtimestamp(created_at)
                week_start = dt - timedelta(days=dt.weekday())
                week_str = week_start.strftime('%Y-W%U')
                weekly_counts[week_str] += 1
        return dict(weekly_counts)
    
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
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text (simplified version)."""
        # This is a simplified keyword extraction
        # In production, you'd use YAKE or similar
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
    
    def _is_billing_related(self, text: str) -> bool:
        """Check if text is billing-related."""
        billing_keywords = ['billing', 'payment', 'charge', 'invoice', 'subscription', 'plan', 'price', 'cost']
        return any(keyword in text.lower() for keyword in billing_keywords)
    
    def _is_product_related(self, text: str) -> bool:
        """Check if text is product-related."""
        product_keywords = ['feature', 'bug', 'issue', 'problem', 'error', 'not working', 'how to', 'tutorial']
        return any(keyword in text.lower() for keyword in product_keywords)
    
    def _is_account_related(self, text: str) -> bool:
        """Check if text is account-related."""
        account_keywords = ['account', 'login', 'password', 'profile', 'settings', 'access', 'permission']
        return any(keyword in text.lower() for keyword in account_keywords)
    
    def _is_escalation(self, text: str) -> bool:
        """Check if text indicates escalation."""
        escalation_keywords = ['escalate', 'manager', 'supervisor', 'urgent', 'critical', 'emergency']
        return any(keyword in text.lower() for keyword in escalation_keywords)
    
    def _identify_escalation_reason(self, text: str) -> str:
        """Identify escalation reason."""
        if 'urgent' in text.lower() or 'critical' in text.lower():
            return 'urgency'
        elif 'manager' in text.lower() or 'supervisor' in text.lower():
            return 'authority'
        else:
            return 'general'
    
    def _has_friction_indicators(self, text: str) -> bool:
        """Check if text has friction indicators."""
        friction_keywords = ['frustrated', 'confused', 'difficult', 'complicated', 'not working', 'broken']
        return any(keyword in text.lower() for keyword in friction_keywords)
    
    def _identify_friction_type(self, text: str) -> str:
        """Identify friction type."""
        if 'confused' in text.lower() or 'difficult' in text.lower():
            return 'usability'
        elif 'not working' in text.lower() or 'broken' in text.lower():
            return 'technical'
        else:
            return 'general'
    
    def _is_complaint(self, text: str) -> bool:
        """Check if text is a complaint."""
        complaint_keywords = ['complaint', 'unhappy', 'dissatisfied', 'disappointed', 'poor service']
        return any(keyword in text.lower() for keyword in complaint_keywords)
    
    def _identify_complaint_type(self, text: str) -> str:
        """Identify complaint type."""
        if 'service' in text.lower():
            return 'service'
        elif 'product' in text.lower():
            return 'product'
        else:
            return 'general'
    
    def _is_old_conversation(self, conversation: Dict) -> bool:
        """Check if conversation is old (more than 7 days)."""
        created_at = conversation.get('created_at')
        if not created_at:
            return False
        
        age_days = (datetime.now().timestamp() - created_at) / (24 * 3600)
        return age_days > 7
    
    def _calculate_conversation_age(self, conversation: Dict) -> int:
        """Calculate conversation age in days."""
        created_at = conversation.get('created_at')
        if not created_at:
            return 0
        
        age_days = (datetime.now().timestamp() - created_at) / (24 * 3600)
        return int(age_days)

