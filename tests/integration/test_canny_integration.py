"""
Integration tests for complete Canny workflow.
"""

import pytest
import asyncio
from datetime import datetime, timedelta, date
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, List

from src.services.canny_client import CannyClient
from src.services.canny_preprocessor import CannyPreprocessor
from src.analyzers.canny_analyzer import CannyAnalyzer
from src.agents.canny_topic_detection_agent import CannyTopicDetectionAgent
from src.agents.cross_platform_correlation_agent import CrossPlatformCorrelationAgent
from src.agents.topic_orchestrator import TopicOrchestrator
from src.services.ai_model_factory import AIModelFactory, AIModel
from src.services.duckdb_storage import DuckDBStorage


@pytest.fixture
def sample_canny_api_response():
    """Sample API response from Canny."""
    return {
        'posts': [
            {
                'id': 'post1',
                'title': 'Add dark mode',
                'details': 'Would love dark mode support',
                'board': {'id': 'board1', 'name': 'Features'},
                'author': {'id': 'user1', 'name': 'John Doe', 'email': 'john@test.com'},
                'category': 'UI/UX',
                'created': '2024-10-15T10:30:00Z',
                'status': 'planned',
                'score': 100,
                'commentCount': 10,
                'url': 'https://feedback.example.com/post/1'
            },
            {
                'id': 'post2',
                'title': 'API rate limit increase',
                'details': 'Need higher API rate limits for integration',
                'board': {'id': 'board1', 'name': 'Features'},
                'author': {'id': 'user2', 'name': 'Jane Smith', 'email': 'jane@test.com'},
                'category': 'API',
                'created': '2024-10-14T09:00:00Z',
                'status': 'open',
                'score': 50,
                'commentCount': 5,
                'url': 'https://feedback.example.com/post/2'
            }
        ]
    }


@pytest.fixture
def sample_intercom_conversations():
    """Sample Intercom conversations for correlation."""
    return [
        {
            'id': 'conv1',
            'primary_category': 'API',
            'topic': 'API',
            'sentiment': 'negative',
            'full_text': 'Having issues with API rate limits',
            'created_at': datetime(2024, 10, 15)
        },
        {
            'id': 'conv2',
            'primary_category': 'Bug',
            'topic': 'Bug',
            'sentiment': 'negative',
            'full_text': 'Dark mode not working properly',
            'created_at': datetime(2024, 10, 14)
        }
    ]


@pytest.mark.asyncio
class TestCannyIntegration:
    """End-to-end integration tests for Canny workflow."""
    
    async def test_complete_canny_analysis_workflow(self, sample_canny_api_response):
        """Test complete Canny analysis from API fetch to storage."""
        # Setup mocks
        mock_ai_factory = MagicMock(spec=AIModelFactory)
        mock_ai_factory.analyze_sentiment = AsyncMock(return_value={
            'sentiment': 'positive',
            'confidence': 0.9,
            'analysis': 'User is excited',
            'emotional_indicators': ['excited'],
            'model': 'openai'
        })
        
        mock_duckdb = MagicMock(spec=DuckDBStorage)
        mock_duckdb.store_canny_posts = MagicMock()
        mock_duckdb.store_canny_weekly_snapshot = MagicMock()
        
        # Create analyzer
        analyzer = CannyAnalyzer(mock_ai_factory, mock_duckdb)
        preprocessor = CannyPreprocessor()
        
        # Preprocess raw posts
        raw_posts = sample_canny_api_response['posts']
        processed_posts = preprocessor.preprocess_posts(raw_posts)
        
        # Run analysis
        results = await analyzer.analyze_canny_sentiment(
            posts=processed_posts,
            ai_model=AIModel.OPENAI_GPT4,
            enable_fallback=True
        )
        
        # Verify results
        assert results['posts_analyzed'] == 2
        assert 'sentiment_summary' in results
        assert 'top_requests' in results
        assert 'insights' in results
        
        # Verify DuckDB storage was called
        mock_duckdb.store_canny_posts.assert_called_once()
        mock_duckdb.store_canny_weekly_snapshot.assert_called_once()
    
    async def test_canny_topic_detection(self, sample_canny_api_response):
        """Test Canny topic detection agent."""
        mock_ai_factory = MagicMock(spec=AIModelFactory)
        mock_ai_factory.generate_response = AsyncMock(return_value="""
        [
            {"post_index": 0, "category": "Feedback", "confidence": 0.9},
            {"post_index": 1, "category": "API", "confidence": 0.85}
        ]
        """)
        
        agent = CannyTopicDetectionAgent(mock_ai_factory)
        preprocessor = CannyPreprocessor()
        
        # Preprocess posts
        processed_posts = preprocessor.preprocess_posts(sample_canny_api_response['posts'])
        
        # Detect topics
        topic_groups = await agent.detect_topics(
            canny_posts=processed_posts,
            taxonomy=None,
            ai_model=AIModel.OPENAI_GPT4,
            enable_fallback=True
        )
        
        # Verify topic detection
        assert len(topic_groups) > 0
        for topic, data in topic_groups.items():
            assert 'posts' in data
            assert 'count' in data
            assert 'total_votes' in data
            assert data['count'] > 0
    
    async def test_cross_platform_correlation(
        self,
        sample_canny_api_response,
        sample_intercom_conversations
    ):
        """Test cross-platform correlation agent."""
        mock_ai_factory = MagicMock(spec=AIModelFactory)
        mock_ai_factory.generate_response = AsyncMock(return_value="""
        [
            {
                "intercom_topic": "API",
                "canny_topic": "API",
                "similarity": 0.9,
                "reason": "Both relate to API functionality"
            }
        ]
        """)
        
        agent = CrossPlatformCorrelationAgent(mock_ai_factory)
        preprocessor = CannyPreprocessor()
        
        # Preprocess Canny posts
        canny_posts = preprocessor.preprocess_posts(sample_canny_api_response['posts'])
        
        # Run correlation analysis
        results = await agent.analyze_correlations(
            intercom_conversations=sample_intercom_conversations,
            canny_posts=canny_posts,
            ai_model=AIModel.OPENAI_GPT4,
            enable_fallback=True
        )
        
        # Verify correlation results
        assert 'correlations' in results
        assert 'unified_priorities' in results
        assert 'insights' in results
        assert results['correlation_count'] >= 0
    
    async def test_topic_orchestrator_with_canny(
        self,
        sample_canny_api_response,
        sample_intercom_conversations
    ):
        """Test TopicOrchestrator with Canny integration."""
        mock_ai_factory = MagicMock(spec=AIModelFactory)
        mock_ai_factory.analyze_sentiment = AsyncMock(return_value={
            'sentiment': 'positive',
            'confidence': 0.85,
            'analysis': 'Positive',
            'emotional_indicators': [],
            'model': 'openai'
        })
        mock_ai_factory.generate_response = AsyncMock(return_value="""
        [{"post_index": 0, "category": "Feedback", "confidence": 0.9}]
        """)
        
        orchestrator = TopicOrchestrator(mock_ai_factory)
        preprocessor = CannyPreprocessor()
        
        # Preprocess Canny posts
        canny_posts = preprocessor.preprocess_posts(sample_canny_api_response['posts'])
        
        # Note: This is a simplified test; full orchestrator test would require more mocking
        # Test that Canny agents are initialized
        assert orchestrator.canny_topic_detection_agent is not None
        assert orchestrator.cross_platform_correlation_agent is not None
    
    async def test_duckdb_storage_round_trip(self):
        """Test storing and retrieving Canny data from DuckDB."""
        # Create temporary DuckDB instance
        storage = DuckDBStorage(":memory:")  # In-memory database for testing
        
        # Sample post data
        posts = [
            {
                'id': 'test1',
                'title': 'Test Post',
                'details': 'Test details',
                'board': {'id': 'board1', 'name': 'Test Board'},
                'author': {'id': 'user1', 'name': 'Test User', 'email': 'test@example.com'},
                'category': 'Feature',
                'created': datetime(2024, 10, 15),
                'status': 'open',
                'score': 10,
                'commentCount': 2,
                'url': 'https://test.com/1',
                'engagement_score': 22,
                'vote_velocity': 1.0,
                'comment_velocity': 0.2,
                'is_trending': False,
                'tags': ['feature', 'ui'],
                'comments': [],
                'votes': [],
                'sentiment_analysis': {
                    'sentiment': 'positive',
                    'confidence': 0.85,
                    'model': 'openai'
                }
            }
        ]
        
        # Store posts
        storage.store_canny_posts(posts)
        
        # Retrieve posts
        start_date = date(2024, 10, 1)
        end_date = date(2024, 10, 31)
        retrieved = storage.get_canny_posts_by_date_range(start_date, end_date)
        
        # Verify retrieval
        assert len(retrieved) > 0
        
        # Store snapshot
        snapshot = {
            'snapshot_date': date(2024, 10, 15),
            'total_posts': 1,
            'open_posts': 1,
            'planned_posts': 0,
            'in_progress_posts': 0,
            'completed_posts': 0,
            'closed_posts': 0,
            'total_votes': 10,
            'total_comments': 2,
            'sentiment_breakdown': {'positive': 100},
            'top_requests': [{'id': 'test1', 'title': 'Test Post'}],
            'engagement_trends': {'high': 0, 'medium': 1, 'low': 0}
        }
        storage.store_canny_weekly_snapshot(snapshot)
        
        # Test trend retrieval
        trends = storage.get_canny_trends(weeks=4)
        assert 'weeks_analyzed' in trends
        assert 'snapshots' in trends
    
    async def test_error_handling_in_workflow(self):
        """Test error handling throughout the Canny workflow."""
        # Test with invalid API key
        with patch('src.services.canny_client.settings') as mock_settings:
            mock_settings.canny_api_key = None
            
            with pytest.raises(ValueError, match="CANNY_API_KEY is required"):
                CannyClient()
        
        # Test with empty posts
        mock_ai_factory = MagicMock(spec=AIModelFactory)
        analyzer = CannyAnalyzer(mock_ai_factory)
        
        results = await analyzer.analyze_canny_sentiment(
            posts=[],
            ai_model=AIModel.OPENAI_GPT4,
            enable_fallback=True
        )
        
        assert results['posts_analyzed'] == 0
        assert results['insights'] == ["No posts available for analysis"]
    
    async def test_preprocessing_pipeline(self, sample_canny_api_response):
        """Test the complete preprocessing pipeline."""
        preprocessor = CannyPreprocessor()
        
        # Preprocess posts
        raw_posts = sample_canny_api_response['posts']
        processed = preprocessor.preprocess_posts(raw_posts)
        
        # Verify preprocessing
        assert len(processed) == 2
        for post in processed:
            assert 'engagement_score' in post
            assert 'vote_velocity' in post
            assert 'comment_velocity' in post
            assert 'is_trending' in post
            assert 'content_for_analysis' in post
            
            # Verify HTML was removed
            assert '<' not in post['details']
            assert '>' not in post['details']
        
        # Test categorization
        categories = preprocessor.categorize_posts(processed)
        assert 'by_status' in categories
        assert 'by_engagement' in categories
        assert 'trending' in categories


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

