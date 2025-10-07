"""
Aggregate trend analysis for Intercom conversations.
"""

import logging
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

class TrendAnalyzer:
    """Analyzer for conversation trends and patterns."""
    
    @staticmethod
    def conversations_by_date(conversations: List[Dict]) -> pd.DataFrame:
        """
        Group conversations by date.
        
        Args:
            conversations: List of conversation objects
            
        Returns:
            DataFrame with date and count columns
        """
        dates = []
        
        for conv in conversations:
            created_at = conv.get('created_at')
            if created_at:
                try:
                    date = datetime.fromtimestamp(created_at).date()
                    dates.append(date)
                except (ValueError, OSError) as e:
                    logger.warning(f"Invalid timestamp {created_at}: {e}")
                    continue
                    
        if not dates:
            logger.warning("No valid dates found in conversations")
            return pd.DataFrame(columns=['date', 'count'])
            
        date_counts = Counter(dates)
        
        df = pd.DataFrame(
            list(date_counts.items()),
            columns=['date', 'count']
        ).sort_values('date')
        
        logger.info(f"Created date analysis for {len(df)} unique dates")
        return df
        
    @staticmethod
    def conversations_by_hour(conversations: List[Dict]) -> pd.DataFrame:
        """
        Group conversations by hour of day.
        
        Args:
            conversations: List of conversation objects
            
        Returns:
            DataFrame with hour and count columns
        """
        hours = []
        
        for conv in conversations:
            created_at = conv.get('created_at')
            if created_at:
                try:
                    hour = datetime.fromtimestamp(created_at).hour
                    hours.append(hour)
                except (ValueError, OSError) as e:
                    logger.warning(f"Invalid timestamp {created_at}: {e}")
                    continue
                    
        if not hours:
            logger.warning("No valid timestamps found in conversations")
            return pd.DataFrame(columns=['hour', 'count'])
            
        hour_counts = Counter(hours)
        
        df = pd.DataFrame(
            list(hour_counts.items()),
            columns=['hour', 'count']
        ).sort_values('hour')
        
        logger.info(f"Created hourly analysis for {len(df)} hours")
        return df
        
    @staticmethod
    def conversations_by_state(conversations: List[Dict]) -> Dict[str, int]:
        """
        Count conversations by state (open, closed, snoozed).
        
        Args:
            conversations: List of conversation objects
            
        Returns:
            Dict mapping state to count
        """
        states = [conv.get('state', 'unknown') for conv in conversations]
        state_counts = dict(Counter(states))
        
        logger.info(f"State breakdown: {state_counts}")
        return state_counts
        
    @staticmethod
    def conversations_by_source_type(conversations: List[Dict]) -> Dict[str, int]:
        """
        Count conversations by source type (email, chat, etc.).
        
        Args:
            conversations: List of conversation objects
            
        Returns:
            Dict mapping source type to count
        """
        sources = [
            conv.get('source', {}).get('type', 'unknown') 
            for conv in conversations
        ]
        source_counts = dict(Counter(sources))
        
        logger.info(f"Source type breakdown: {source_counts}")
        return source_counts
        
    @staticmethod
    def pattern_analysis(
        conversations: List[Dict],
        patterns: List[str],
        case_sensitive: bool = False
    ) -> Dict[str, int]:
        """
        Count how many conversations mention specific patterns.
        
        Args:
            conversations: List of conversation objects
            patterns: List of keywords/phrases to search for
            case_sensitive: Whether to perform case-sensitive matching
            
        Returns:
            Dict mapping pattern to count
        """
        pattern_counts = defaultdict(int)
        total_conversations = len(conversations)
        
        logger.info(f"Analyzing {len(patterns)} patterns across {total_conversations} conversations")
        
        for i, conv in enumerate(conversations):
            if (i + 1) % 100 == 0:
                logger.debug(f"Processed {i + 1}/{total_conversations} conversations")
                
            # Extract text from conversation
            source_body = conv.get('source', {}).get('body', '')
            
            # Get conversation parts
            parts = conv.get('conversation_parts', {}).get('conversation_parts', [])
            part_bodies = ' '.join([
                p.get('body', '') 
                for p in parts
            ])
            
            # Get notes
            notes = conv.get('notes', {}).get('notes', [])
            note_bodies = ' '.join([
                n.get('body', '') 
                for n in notes
            ])
            
            full_text = f"{source_body} {part_bodies} {note_bodies}"
            
            if not case_sensitive:
                full_text = full_text.lower()
                
            # Check for each pattern
            for pattern in patterns:
                search_pattern = pattern if case_sensitive else pattern.lower()
                if search_pattern in full_text:
                    pattern_counts[pattern] += 1
                    
        result = dict(pattern_counts)
        logger.info(f"Pattern analysis complete: {result}")
        return result
        
    @staticmethod
    def agent_response_analysis(conversations: List[Dict]) -> pd.DataFrame:
        """
        Analyze agent response patterns.
        
        Args:
            conversations: List of conversation objects
            
        Returns:
            DataFrame with agent statistics
        """
        agents = []
        response_times = []
        
        for conv in conversations:
            parts = conv.get('conversation_parts', {}).get('conversation_parts', [])
            
            for part in parts:
                author = part.get('author', {})
                if author.get('type') == 'admin':
                    agent_email = author.get('email', 'unknown')
                    agents.append(agent_email)
                    
                    # Calculate response time if possible
                    created_at = part.get('created_at')
                    if created_at:
                        try:
                            response_times.append(created_at)
                        except (ValueError, OSError):
                            continue
                            
        if not agents:
            logger.warning("No agent responses found")
            return pd.DataFrame(columns=['agent_email', 'response_count'])
            
        agent_counts = Counter(agents)
        
        df = pd.DataFrame(
            list(agent_counts.items()),
            columns=['agent_email', 'response_count']
        ).sort_values('response_count', ascending=False)
        
        logger.info(f"Agent analysis complete: {len(df)} agents found")
        return df
        
    @staticmethod
    def conversation_length_analysis(conversations: List[Dict]) -> Dict[str, Any]:
        """
        Analyze conversation length patterns.
        
        Args:
            conversations: List of conversation objects
            
        Returns:
            Dict with length statistics
        """
        lengths = []
        
        for conv in conversations:
            # Count conversation parts
            parts = conv.get('conversation_parts', {}).get('conversation_parts', [])
            length = len(parts) + 1  # +1 for initial message
            lengths.append(length)
            
        if not lengths:
            return {
                'total_conversations': 0,
                'average_length': 0,
                'median_length': 0,
                'max_length': 0,
                'min_length': 0
            }
            
        return {
            'total_conversations': len(lengths),
            'average_length': np.mean(lengths),
            'median_length': np.median(lengths),
            'max_length': max(lengths),
            'min_length': min(lengths),
            'std_length': np.std(lengths)
        }
        
    @staticmethod
    def response_time_analysis(conversations: List[Dict]) -> Dict[str, Any]:
        """
        Analyze response time patterns.
        
        Args:
            conversations: List of conversation objects
            
        Returns:
            Dict with response time statistics
        """
        response_times = []
        
        for conv in conversations:
            created_at = conv.get('created_at')
            if not created_at:
                continue
                
            parts = conv.get('conversation_parts', {}).get('conversation_parts', [])
            
            for part in parts:
                author = part.get('author', {})
                if author.get('type') == 'admin':
                    part_created_at = part.get('created_at')
                    if part_created_at:
                        try:
                            response_time = part_created_at - created_at
                            if response_time > 0:  # Only positive response times
                                response_times.append(response_time / 3600)  # Convert to hours
                        except (ValueError, OSError):
                            continue
                            
        if not response_times:
            return {
                'total_responses': 0,
                'average_response_time_hours': 0,
                'median_response_time_hours': 0,
                'max_response_time_hours': 0,
                'min_response_time_hours': 0
            }
            
        return {
            'total_responses': len(response_times),
            'average_response_time_hours': np.mean(response_times),
            'median_response_time_hours': np.median(response_times),
            'max_response_time_hours': max(response_times),
            'min_response_time_hours': min(response_times),
            'std_response_time_hours': np.std(response_times)
        }
        
    @staticmethod
    def weekly_trends(conversations: List[Dict]) -> pd.DataFrame:
        """
        Analyze weekly conversation trends.
        
        Args:
            conversations: List of conversation objects
            
        Returns:
            DataFrame with weekly statistics
        """
        weekly_data = defaultdict(list)
        
        for conv in conversations:
            created_at = conv.get('created_at')
            if created_at:
                try:
                    dt = datetime.fromtimestamp(created_at)
                    week_start = dt - timedelta(days=dt.weekday())
                    week_key = week_start.strftime('%Y-%W')
                    weekly_data[week_key].append(dt)
                except (ValueError, OSError):
                    continue
                    
        if not weekly_data:
            return pd.DataFrame(columns=['week', 'count', 'week_start'])
            
        weekly_counts = []
        for week, dates in weekly_data.items():
            week_start = min(dates)
            weekly_counts.append({
                'week': week,
                'count': len(dates),
                'week_start': week_start.date()
            })
            
        df = pd.DataFrame(weekly_counts).sort_values('week_start')
        
        logger.info(f"Weekly trends analysis complete: {len(df)} weeks")
        return df
        
    @staticmethod
    def customer_satisfaction_analysis(conversations: List[Dict]) -> Dict[str, Any]:
        """
        Analyze customer satisfaction indicators.
        
        Args:
            conversations: List of conversation objects
            
        Returns:
            Dict with satisfaction metrics
        """
        satisfaction_keywords = {
            'positive': ['thank', 'thanks', 'great', 'excellent', 'perfect', 'love', 'amazing', 'helpful'],
            'negative': ['terrible', 'awful', 'hate', 'horrible', 'frustrated', 'angry', 'disappointed', 'useless'],
            'resolution': ['solved', 'fixed', 'resolved', 'working', 'corrected', 'repaired']
        }
        
        results = {
            'total_conversations': len(conversations),
            'positive_sentiment': 0,
            'negative_sentiment': 0,
            'resolution_mentioned': 0
        }
        
        for conv in conversations:
            text = conv.get('source', {}).get('body', '').lower()
            
            # Check for sentiment keywords
            if any(keyword in text for keyword in satisfaction_keywords['positive']):
                results['positive_sentiment'] += 1
                
            if any(keyword in text for keyword in satisfaction_keywords['negative']):
                results['negative_sentiment'] += 1
                
            if any(keyword in text for keyword in satisfaction_keywords['resolution']):
                results['resolution_mentioned'] += 1
                
        # Calculate percentages
        total = results['total_conversations']
        if total > 0:
            results['positive_percentage'] = (results['positive_sentiment'] / total) * 100
            results['negative_percentage'] = (results['negative_sentiment'] / total) * 100
            results['resolution_percentage'] = (results['resolution_mentioned'] / total) * 100
            
        logger.info(f"Satisfaction analysis complete: {results}")
        return results


