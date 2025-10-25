"""
Unit tests for CannyAnalyzer.
"""

import pytest
from datetime import datetime, date
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, List

from src.analyzers.canny_analyzer import CannyAnalyzer
from src.services.ai_model_factory import AIModelFactory, AIModel
from src.services.duckdb_storage import DuckDBStorage


@pytest.fixture
def mock_ai_factory():
    """Mock AI factory for testing."""
    factory = MagicMock(spec=AIModelFactory)
    factory.analyze_sentiment = AsyncMock(return_value={
        'sentiment': 'positive',
        'confidence': 0.85,
        'analysis': 'User is excited about this feature',
        'emotional_indicators': ['excited', 'enthusiastic'],
        'model': 'openai'
    })
    factory.get_client = MagicMock()
    return factory


@pytest.fixture
def mock_duckdb_storage():
    """Mock DuckDB storage for testing."""
    storage = MagicMock(spec=DuckDBStorage)
    storage.store_canny_posts = MagicMock()
    storage.store_canny_weekly_snapshot = MagicMock()
    return storage


@pytest.fixture
def canny_analyzer(mock_ai_factory, mock_duckdb_storage):
    """Create CannyAnalyzer instance for testing."""
    return CannyAnalyzer(mock_ai_factory, mock_duckdb_storage)


@pytest.fixture
def sample_preprocessed_posts():
    """Sample preprocessed posts for testing."""
    return [
        {
            'id': 'post1',
            'title': 'Add dark mode',
            'details': 'Would love to see dark mode',
            'board': {'id': 'board1', 'name': 'Features'},
            'author': {'id': 'user1', 'name': 'John'},
            'category': 'UI',
            'created': datetime(2024, 10, 15),
            'status': 'planned',
            'score': 100,
            'commentCount': 10,
            'url': 'https://feedback.example.com/post/1',
            'engagement_score': 210,
            'vote_velocity': 2.5,
            'comment_velocity': 0.5,
            'is_trending': True,
            'content_for_analysis': 'Title: Add dark mode Details: Would love to see dark mode',
            'comments': [
                {
                    'id': 'comment1',
                    'content_for_analysis': 'Great idea!'
                }
            ]
        },
        {
            'id': 'post2',
            'title': 'Export to CSV',
            'details': 'Need CSV export feature',
            'board': {'id': 'board1', 'name': 'Features'},
            'author': {'id': 'user2', 'name': 'Jane'},
            'category': 'Export',
            'created': datetime(2024, 10, 14),
            'status': 'open',
            'score': 50,
            'commentCount': 5,
            'url': 'https://feedback.example.com/post/2',
            'engagement_score': 105,
            'vote_velocity': 1.0,
            'comment_velocity': 0.2,
            'is_trending': False,
            'content_for_analysis': 'Title: Export to CSV Details: Need CSV export feature',
            'comments': []
        }
    ]


@pytest.mark.asyncio
class TestCannyAnalyzer:
    """Test suite for CannyAnalyzer."""
    
    async def test_analyze_canny_sentiment_success(
        self,
        canny_analyzer,
        mock_ai_factory,
        sample_preprocessed_posts
    ):
        """Test successful Canny sentiment analysis."""
        with patch.object(canny_analyzer.preprocessor, 'preprocess_posts') as mock_preprocess:
            mock_preprocess.return_value = sample_preprocessed_posts
            
            results = await canny_analyzer.analyze_canny_sentiment(
                posts=sample_preprocessed_posts,
                ai_model=AIModel.OPENAI_GPT4,
                enable_fallback=True
            )
            
            assert results['posts_analyzed'] == 2
            assert 'sentiment_summary' in results
            assert 'top_requests' in results
            assert 'insights' in results
            mock_ai_factory.analyze_sentiment.assert_called()
    
    async def test_analyze_canny_sentiment_empty_posts(
        self,
        canny_analyzer,
        mock_ai_factory
    ):
        """Test analysis with empty posts list."""
        with patch.object(canny_analyzer.preprocessor, 'preprocess_posts') as mock_preprocess:
            mock_preprocess.return_value = []
            
            results = await canny_analyzer.analyze_canny_sentiment(
                posts=[],
                ai_model=AIModel.OPENAI_GPT4,
                enable_fallback=True
            )
            
            assert results['posts_analyzed'] == 0
            assert results['insights'] == ["No posts available for analysis"]
    
    async def test_analyze_canny_sentiment_stores_in_duckdb(
        self,
        canny_analyzer,
        mock_duckdb_storage,
        sample_preprocessed_posts
    ):
        """Test that analysis results are stored in DuckDB."""
        with patch.object(canny_analyzer.preprocessor, 'preprocess_posts') as mock_preprocess:
            mock_preprocess.return_value = sample_preprocessed_posts
            
            await canny_analyzer.analyze_canny_sentiment(
                posts=sample_preprocessed_posts,
                ai_model=AIModel.OPENAI_GPT4,
                enable_fallback=True
            )
            
            mock_duckdb_storage.store_canny_posts.assert_called_once()
            mock_duckdb_storage.store_canny_weekly_snapshot.assert_called_once()
    
    async def test_analyze_canny_sentiment_storage_failure_continues(
        self,
        canny_analyzer,
        mock_duckdb_storage,
        sample_preprocessed_posts
    ):
        """Test that analysis continues even if storage fails."""
        mock_duckdb_storage.store_canny_posts.side_effect = Exception("Storage failed")
        
        with patch.object(canny_analyzer.preprocessor, 'preprocess_posts') as mock_preprocess:
            mock_preprocess.return_value = sample_preprocessed_posts
            
            # Should not raise exception
            results = await canny_analyzer.analyze_canny_sentiment(
                posts=sample_preprocessed_posts,
                ai_model=AIModel.OPENAI_GPT4,
                enable_fallback=True
            )
            
            assert results['posts_analyzed'] == 2
    
    def test_calculate_sentiment_summary(self, canny_analyzer):
        """Test sentiment summary calculation."""
        posts = [
            {'sentiment_analysis': {'sentiment': 'positive', 'confidence': 0.9}, 'status': 'open', 'category': 'UI'},
            {'sentiment_analysis': {'sentiment': 'positive', 'confidence': 0.8}, 'status': 'planned', 'category': 'UI'},
            {'sentiment_analysis': {'sentiment': 'negative', 'confidence': 0.7}, 'status': 'open', 'category': 'Export'},
            {'sentiment_analysis': {'sentiment': 'neutral', 'confidence': 0.6}, 'status': 'closed', 'category': 'Other'}
        ]
        
        summary = canny_analyzer._calculate_sentiment_summary(posts)
        
        assert summary['overall'] == 'positive'  # Most common
        assert summary['distribution']['positive'] == 50.0  # 2/4
        assert summary['distribution']['negative'] == 25.0  # 1/4
        assert summary['distribution']['neutral'] == 25.0  # 1/4
        assert summary['average_confidence'] == 0.75
        assert 'by_status' in summary
        assert 'by_category' in summary
    
    def test_calculate_sentiment_summary_empty(self, canny_analyzer):
        """Test sentiment summary with no posts."""
        summary = canny_analyzer._calculate_sentiment_summary([])
        
        assert summary['overall'] == 'neutral'
        assert summary['distribution']['positive'] == 0
        assert summary['average_confidence'] == 0.0
    
    def test_identify_top_requests(self, canny_analyzer):
        """Test identification of top requests by engagement."""
        posts = [
            {
                'id': '1',
                'title': 'Feature A',
                'score': 100,
                'commentCount': 10,
                'engagement_score': 210,
                'sentiment_analysis': {'sentiment': 'positive', 'confidence': 0.9},
                'status': 'planned',
                'category': 'Features',
                'url': 'https://example.com/1',
                'created': datetime(2024, 10, 1),
                'is_trending': True
            },
            {
                'id': '2',
                'title': 'Feature B',
                'score': 50,
                'commentCount': 5,
                'engagement_score': 105,
                'sentiment_analysis': {'sentiment': 'neutral', 'confidence': 0.8},
                'status': 'open',
                'category': 'Features',
                'url': 'https://example.com/2',
                'created': datetime(2024, 10, 2),
                'is_trending': False
            }
        ]
        
        top_requests = canny_analyzer._identify_top_requests(posts, limit=2)
        
        assert len(top_requests) == 2
        assert top_requests[0]['id'] == '1'  # Higher engagement
        assert top_requests[0]['engagement_score'] == 210
        assert top_requests[1]['id'] == '2'
    
    def test_calculate_status_breakdown(self, canny_analyzer):
        """Test status breakdown calculation."""
        posts = [
            {'status': 'open'},
            {'status': 'open'},
            {'status': 'planned'},
            {'status': 'in progress'},
            {'status': 'complete'}
        ]
        
        breakdown = canny_analyzer._calculate_status_breakdown(posts)
        
        assert breakdown['open'] == 2
        assert breakdown['planned'] == 1
        assert breakdown['in progress'] == 1
        assert breakdown['complete'] == 1
    
    def test_calculate_category_breakdown(self, canny_analyzer):
        """Test category breakdown calculation."""
        posts = [
            {'category': 'UI', 'engagement_score': 100},
            {'category': 'UI', 'engagement_score': 200},
            {'category': 'Export', 'engagement_score': 50}
        ]
        
        breakdown = canny_analyzer._calculate_category_breakdown(posts)
        
        assert breakdown['UI']['count'] == 2
        assert breakdown['UI']['average_engagement'] == 150.0
        assert breakdown['UI']['total_engagement'] == 300
        assert breakdown['Export']['count'] == 1
    
    def test_analyze_voting_patterns(self, canny_analyzer):
        """Test voting pattern analysis."""
        posts = [
            {'score': 100, 'status': 'planned'},
            {'score': 50, 'status': 'open'},
            {'score': 25, 'status': 'open'}
        ]
        
        vote_analysis = canny_analyzer._analyze_voting_patterns(posts)
        
        assert vote_analysis['total_votes'] == 175
        assert vote_analysis['average_votes_per_post'] == pytest.approx(58.33, abs=0.1)
        assert vote_analysis['votes_by_status']['planned'] == 100
        assert vote_analysis['votes_by_status']['open'] == 75
        assert vote_analysis['top_voted_posts'] == [100, 50, 25]
    
    def test_calculate_engagement_metrics(self, canny_analyzer):
        """Test engagement metrics calculation."""
        posts = [
            {'score': 100, 'commentCount': 10, 'engagement_score': 210},
            {'score': 50, 'commentCount': 5, 'engagement_score': 105},
            {'score': 25, 'commentCount': 2, 'engagement_score': 52},
            {'score': 200, 'commentCount': 30, 'engagement_score': 430}
        ]
        
        metrics = canny_analyzer._calculate_engagement_metrics(posts)
        
        assert metrics['total_votes'] == 375
        assert metrics['total_comments'] == 47
        assert metrics['total_posts'] == 4
        assert metrics['average_votes_per_post'] == 93.75
        assert metrics['average_comments_per_post'] == pytest.approx(11.75)
        assert metrics['high_engagement_posts'] == 2  # >20
        assert metrics['medium_engagement_posts'] == 1  # 5-20
        assert metrics['low_engagement_posts'] == 1  # <5
    
    def test_identify_trending_posts(self, canny_analyzer):
        """Test trending posts identification."""
        posts = [
            {
                'id': '1',
                'title': 'Trending Post',
                'score': 100,
                'commentCount': 10,
                'vote_velocity': 5.0,
                'comment_velocity': 1.0,
                'sentiment_analysis': {'sentiment': 'positive'},
                'status': 'planned',
                'url': 'https://example.com/1',
                'created': datetime(2024, 10, 1),
                'is_trending': True
            },
            {
                'id': '2',
                'title': 'Not Trending',
                'score': 50,
                'commentCount': 5,
                'vote_velocity': 0.5,
                'comment_velocity': 0.1,
                'sentiment_analysis': {'sentiment': 'neutral'},
                'status': 'open',
                'url': 'https://example.com/2',
                'created': datetime(2024, 10, 2),
                'is_trending': False
            }
        ]
        
        trending = canny_analyzer._identify_trending_posts(posts, limit=5)
        
        assert len(trending) == 1
        assert trending[0]['id'] == '1'
        assert trending[0]['vote_velocity'] == 5.0
    
    def test_generate_insights_positive_sentiment(self, canny_analyzer):
        """Test insight generation for positive sentiment."""
        sentiment_summary = {'overall': 'positive'}
        top_requests = [{'title': 'Dark Mode', 'votes': 234, 'sentiment': 'positive'}]
        status_breakdown = {'open': 20, 'planned': 10}
        category_breakdown = {}
        vote_analysis = {}
        engagement_metrics = {'average_engagement_score': 20}
        
        insights = canny_analyzer._generate_insights(
            sentiment_summary,
            top_requests,
            status_breakdown,
            category_breakdown,
            vote_analysis,
            engagement_metrics
        )
        
        assert any('positive' in insight.lower() for insight in insights)
        assert any('Dark Mode' in insight for insight in insights)
    
    def test_generate_insights_high_open_posts(self, canny_analyzer):
        """Test insight generation for high open post count."""
        sentiment_summary = {'overall': 'neutral'}
        top_requests = []
        status_breakdown = {'open': 100, 'planned': 10}
        category_breakdown = {}
        vote_analysis = {}
        engagement_metrics = {'average_engagement_score': 10}
        
        insights = canny_analyzer._generate_insights(
            sentiment_summary,
            top_requests,
            status_breakdown,
            category_breakdown,
            vote_analysis,
            engagement_metrics
        )
        
        assert any('open requests' in insight.lower() for insight in insights)
        assert any('roadmap planning' in insight.lower() for insight in insights)
    
    def test_generate_insights_high_engagement(self, canny_analyzer):
        """Test insight generation for high engagement."""
        sentiment_summary = {'overall': 'positive'}
        top_requests = []
        status_breakdown = {}
        category_breakdown = {}
        vote_analysis = {}
        engagement_metrics = {
            'average_engagement_score': 20,
            'high_engagement_posts': 10
        }
        
        insights = canny_analyzer._generate_insights(
            sentiment_summary,
            top_requests,
            status_breakdown,
            category_breakdown,
            vote_analysis,
            engagement_metrics
        )
        
        assert any('high' in insight.lower() and 'engagement' in insight.lower() for insight in insights)
    
    def test_create_weekly_snapshot(self, canny_analyzer):
        """Test weekly snapshot creation."""
        results = {
            'posts_analyzed': 50,
            'status_breakdown': {
                'open': 20,
                'planned': 15,
                'in progress': 10,
                'complete': 5,
                'closed': 0
            },
            'vote_analysis': {'total_votes': 1500},
            'engagement_metrics': {
                'total_comments': 300,
                'high_engagement_posts': 10,
                'medium_engagement_posts': 25,
                'low_engagement_posts': 15
            },
            'sentiment_summary': {'overall': 'positive'},
            'top_requests': [
                {'id': '1', 'title': 'Feature A'},
                {'id': '2', 'title': 'Feature B'}
            ]
        }
        posts = []
        
        snapshot = canny_analyzer._create_weekly_snapshot(results, posts)
        
        assert isinstance(snapshot['snapshot_date'], date)
        assert snapshot['total_posts'] == 50
        assert snapshot['open_posts'] == 20
        assert snapshot['planned_posts'] == 15
        assert snapshot['in_progress_posts'] == 10
        assert snapshot['completed_posts'] == 5
        assert snapshot['closed_posts'] == 0
        assert snapshot['total_votes'] == 1500
        assert snapshot['total_comments'] == 300
        assert len(snapshot['top_requests']) == 2
    
    def test_create_empty_results(self, canny_analyzer):
        """Test empty results structure."""
        results = canny_analyzer._create_empty_results()
        
        assert results['posts_analyzed'] == 0
        assert results['sentiment_summary']['overall'] == 'neutral'
        assert results['top_requests'] == []
        assert results['insights'] == ["No posts available for analysis"]
        assert 'metadata' in results


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

