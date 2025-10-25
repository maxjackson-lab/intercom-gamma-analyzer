"""
Unit tests for CannyPreprocessor.
"""

import pytest
from datetime import datetime, timedelta
from typing import Dict, List

from src.services.canny_preprocessor import CannyPreprocessor
from src.models.canny_models import CannyPostStatus


@pytest.fixture
def preprocessor():
    """Create CannyPreprocessor instance for testing."""
    return CannyPreprocessor()


@pytest.fixture
def sample_post():
    """Create a sample Canny post for testing."""
    return {
        'id': 'post123',
        'title': 'Add dark mode',
        'details': '<p>Would love to see a dark mode feature!</p>',
        'board': {'id': 'board1', 'name': 'Feature Requests'},
        'author': {
            'id': 'user1',
            'name': 'John Doe',
            'email': 'john@example.com'
        },
        'category': 'UI/UX',
        'created': '2024-10-15T10:30:00Z',
        'status': 'planned',
        'score': 234,
        'commentCount': 15,
        'url': 'https://feedback.example.com/post/123',
        'tags': ['ui', 'design'],
        'comments': [],
        'votes': []
    }


class TestCannyPreprocessor:
    """Test suite for CannyPreprocessor."""
    
    def test_clean_text_removes_html(self, preprocessor):
        """Test HTML tag removal from text."""
        text = "<p>This is <strong>bold</strong> text with <a href='#'>links</a></p>"
        cleaned = preprocessor._clean_text(text)
        assert cleaned == "This is bold text with links"
        assert "<" not in cleaned
        assert ">" not in cleaned
    
    def test_clean_text_normalizes_whitespace(self, preprocessor):
        """Test whitespace normalization."""
        text = "This   has    multiple     spaces\nand\nnewlines"
        cleaned = preprocessor._clean_text(text)
        assert cleaned == "This has multiple spaces and newlines"
    
    def test_clean_text_removes_excessive_punctuation(self, preprocessor):
        """Test excessive punctuation removal."""
        text = "This is amazing!!!!!! Really????? Yes!!"
        cleaned = preprocessor._clean_text(text)
        assert cleaned == "This is amazing! Really? Yes!"
    
    def test_clean_text_empty_string(self, preprocessor):
        """Test cleaning empty string."""
        assert preprocessor._clean_text("") == ""
        assert preprocessor._clean_text(None) == ""
    
    def test_parse_date_iso_format(self, preprocessor):
        """Test parsing ISO format dates."""
        date_str = "2024-10-15T10:30:00Z"
        parsed = preprocessor._parse_date(date_str)
        assert isinstance(parsed, datetime)
        assert parsed.year == 2024
        assert parsed.month == 10
        assert parsed.day == 15
    
    def test_parse_date_invalid(self, preprocessor):
        """Test parsing invalid date returns current date."""
        result = preprocessor._parse_date("invalid_date")
        assert isinstance(result, datetime)
        # Should return current date
        assert (datetime.now() - result).total_seconds() < 1
    
    def test_normalize_status_standard(self, preprocessor):
        """Test status normalization for standard values."""
        assert preprocessor._normalize_status('open') == CannyPostStatus.OPEN.value
        assert preprocessor._normalize_status('planned') == CannyPostStatus.PLANNED.value
        assert preprocessor._normalize_status('complete') == CannyPostStatus.COMPLETE.value
        assert preprocessor._normalize_status('closed') == CannyPostStatus.CLOSED.value
    
    def test_normalize_status_variants(self, preprocessor):
        """Test status normalization for variant forms."""
        assert preprocessor._normalize_status('NEW') == CannyPostStatus.OPEN.value
        assert preprocessor._normalize_status('planning') == CannyPostStatus.PLANNED.value
        assert preprocessor._normalize_status('working') == CannyPostStatus.IN_PROGRESS.value
        assert preprocessor._normalize_status('completed') == CannyPostStatus.COMPLETE.value
        assert preprocessor._normalize_status('done') == CannyPostStatus.COMPLETE.value
        assert preprocessor._normalize_status('cancelled') == CannyPostStatus.CLOSED.value
    
    def test_normalize_status_default(self, preprocessor):
        """Test unknown status defaults to open."""
        assert preprocessor._normalize_status('unknown_status') == CannyPostStatus.OPEN.value
        assert preprocessor._normalize_status(None) == CannyPostStatus.OPEN.value
    
    def test_calculate_engagement_score(self, preprocessor):
        """Test engagement score calculation."""
        # votes * 2 + comments
        assert preprocessor._calculate_engagement_score(10, 5) == 25
        assert preprocessor._calculate_engagement_score(100, 50) == 250
        assert preprocessor._calculate_engagement_score(0, 0) == 0
    
    def test_calculate_vote_velocity(self, preprocessor):
        """Test vote velocity calculation."""
        post = {
            'created': (datetime.now() - timedelta(days=10)).isoformat(),
            'score': 100
        }
        velocity = preprocessor._calculate_vote_velocity(post)
        assert velocity == pytest.approx(10.0, abs=0.5)  # ~10 votes per day
    
    def test_calculate_vote_velocity_recent_post(self, preprocessor):
        """Test vote velocity for very recent post."""
        post = {
            'created': datetime.now().isoformat(),
            'score': 50
        }
        velocity = preprocessor._calculate_vote_velocity(post)
        assert velocity == 0.0  # Created today = 0 days
    
    def test_calculate_comment_velocity(self, preprocessor):
        """Test comment velocity calculation."""
        post = {
            'created': (datetime.now() - timedelta(days=20)).isoformat(),
            'commentCount': 40
        }
        velocity = preprocessor._calculate_comment_velocity(post)
        assert velocity == pytest.approx(2.0, abs=0.2)  # ~2 comments per day
    
    def test_is_trending_post_high_velocity(self, preprocessor):
        """Test trending detection for high velocity post."""
        post = {
            'created': (datetime.now() - timedelta(days=5)).isoformat(),
            'score': 10,  # 2 votes/day = trending
            'commentCount': 5  # 1 comment/day
        }
        assert preprocessor._is_trending_post(post, threshold=1.0) is True
    
    def test_is_trending_post_low_velocity(self, preprocessor):
        """Test trending detection for low velocity post."""
        post = {
            'created': (datetime.now() - timedelta(days=100)).isoformat(),
            'score': 10,  # 0.1 votes/day = not trending
            'commentCount': 5  # 0.05 comments/day
        }
        assert preprocessor._is_trending_post(post, threshold=1.0) is False
    
    def test_prepare_content_for_analysis(self, preprocessor):
        """Test content preparation for AI analysis."""
        title = "Add dark mode"
        details = "Would love to see this feature"
        comments = [
            {'content_for_analysis': "Great idea!"},
            {'content_for_analysis': "I need this too"},
            {'content_for_analysis': "Yes please"},
            {'content_for_analysis': "Fourth comment"}  # Should be excluded (limit 3)
        ]
        
        content = preprocessor._prepare_content_for_analysis(title, details, comments)
        
        assert "Title: Add dark mode" in content
        assert "Details: Would love to see this feature" in content
        assert "Comments:" in content
        assert "Great idea!" in content
        assert "Fourth comment" not in content  # Only first 3 comments
    
    def test_prepare_content_empty(self, preprocessor):
        """Test content preparation with empty inputs."""
        content = preprocessor._prepare_content_for_analysis("", "", [])
        assert content == ""
    
    def test_extract_tags_list(self, preprocessor):
        """Test tag extraction from list."""
        post = {'tags': ['ui', 'design', 'feature']}
        tags = preprocessor._extract_tags(post)
        assert tags == ['ui', 'design', 'feature']
    
    def test_extract_tags_dict(self, preprocessor):
        """Test tag extraction from dict objects."""
        post = {'tags': [{'name': 'ui'}, {'name': 'design'}]}
        tags = preprocessor._extract_tags(post)
        assert tags == ['ui', 'design']
    
    def test_extract_tags_empty(self, preprocessor):
        """Test tag extraction with no tags."""
        post = {'tags': []}
        tags = preprocessor._extract_tags(post)
        assert tags == []
    
    def test_extract_category(self, preprocessor):
        """Test category extraction."""
        post = {'category': 'UI/UX'}
        category = preprocessor._extract_category(post)
        assert category == 'UI/UX'
    
    def test_extract_category_from_dict(self, preprocessor):
        """Test category extraction from dict."""
        post = {'category': {'name': 'Feature Request'}}
        category = preprocessor._extract_category(post)
        assert category == 'Feature Request'
    
    def test_extract_category_from_tags(self, preprocessor):
        """Test category extraction fallback to first tag."""
        post = {'tags': ['ui', 'design']}
        category = preprocessor._extract_category(post)
        assert category == 'ui'
    
    def test_preprocess_single_post(self, preprocessor, sample_post):
        """Test preprocessing a single post."""
        processed = preprocessor._preprocess_single_post(sample_post)
        
        assert processed is not None
        assert processed['id'] == 'post123'
        assert processed['title'] == 'Add dark mode'
        assert 'Would love to see a dark mode feature!' in processed['details']
        assert '<p>' not in processed['details']  # HTML removed
        assert processed['status'] == 'planned'
        assert processed['score'] == 234
        assert processed['engagement_score'] == 483  # 234*2 + 15
        assert 'content_for_analysis' in processed
    
    def test_preprocess_single_post_missing_id(self, preprocessor):
        """Test preprocessing post without ID."""
        post = {'title': 'Test'}
        result = preprocessor._preprocess_single_post(post)
        assert result is None
    
    def test_preprocess_single_post_no_content(self, preprocessor):
        """Test preprocessing post with no content."""
        post = {'id': 'test123', 'title': '', 'details': ''}
        result = preprocessor._preprocess_single_post(post)
        assert result is None
    
    def test_preprocess_posts(self, preprocessor, sample_post):
        """Test preprocessing multiple posts."""
        posts = [
            sample_post,
            {**sample_post, 'id': 'post2', 'title': 'Export to CSV'},
            {**sample_post, 'id': 'post3', 'title': 'API Integration'}
        ]
        
        processed = preprocessor.preprocess_posts(posts)
        
        assert len(processed) == 3
        assert all('engagement_score' in p for p in processed)
        assert all('content_for_analysis' in p for p in processed)
    
    def test_preprocess_posts_filters_invalid(self, preprocessor, sample_post):
        """Test preprocessing filters out invalid posts."""
        posts = [
            sample_post,
            {'id': 'invalid1'},  # No content
            {'title': 'No ID'},  # No ID
            {**sample_post, 'id': 'post2'}
        ]
        
        processed = preprocessor.preprocess_posts(posts)
        
        assert len(processed) == 2  # Only valid posts
        assert processed[0]['id'] == 'post123'
        assert processed[1]['id'] == 'post2'
    
    def test_categorize_posts_by_status(self, preprocessor, sample_post):
        """Test categorizing posts by status."""
        posts = [
            {**preprocessor._preprocess_single_post(sample_post), 'status': 'open'},
            {**preprocessor._preprocess_single_post(sample_post), 'id': 'post2', 'status': 'planned'},
            {**preprocessor._preprocess_single_post(sample_post), 'id': 'post3', 'status': 'open'}
        ]
        
        categories = preprocessor.categorize_posts(posts)
        
        assert 'by_status' in categories
        assert len(categories['by_status']['open']) == 2
        assert len(categories['by_status']['planned']) == 1
    
    def test_categorize_posts_by_engagement(self, preprocessor):
        """Test categorizing posts by engagement level."""
        posts = [
            {'id': '1', 'engagement_score': 50, 'status': 'open', 'category': 'test', 'is_trending': False, 'content_for_analysis': ''},
            {'id': '2', 'engagement_score': 10, 'status': 'open', 'category': 'test', 'is_trending': False, 'content_for_analysis': ''},
            {'id': '3', 'engagement_score': 2, 'status': 'open', 'category': 'test', 'is_trending': False, 'content_for_analysis': ''}
        ]
        
        categories = preprocessor.categorize_posts(posts)
        
        assert len(categories['by_engagement']['high']) == 1  # >20
        assert len(categories['by_engagement']['medium']) == 1  # 5-20
        assert len(categories['by_engagement']['low']) == 1  # <5
    
    def test_categorize_posts_trending(self, preprocessor):
        """Test identifying trending posts."""
        posts = [
            {'id': '1', 'is_trending': True, 'engagement_score': 30, 'status': 'open', 'category': 'test', 'content_for_analysis': ''},
            {'id': '2', 'is_trending': False, 'engagement_score': 10, 'status': 'open', 'category': 'test', 'content_for_analysis': ''},
            {'id': '3', 'is_trending': True, 'engagement_score': 25, 'status': 'open', 'category': 'test', 'content_for_analysis': ''}
        ]
        
        categories = preprocessor.categorize_posts(posts)
        
        assert len(categories['trending']) == 2
        assert categories['trending'][0]['id'] in ['1', '3']
    
    def test_categorize_posts_feature_vs_bug(self, preprocessor):
        """Test classification of feature requests vs bug reports."""
        posts = [
            {'id': '1', 'content_for_analysis': 'Add dark mode feature', 'engagement_score': 10, 'status': 'open', 'category': 'test', 'is_trending': False},
            {'id': '2', 'content_for_analysis': 'Bug: Export is broken', 'engagement_score': 10, 'status': 'open', 'category': 'test', 'is_trending': False},
            {'id': '3', 'content_for_analysis': 'Error when loading page', 'engagement_score': 10, 'status': 'open', 'category': 'test', 'is_trending': False}
        ]
        
        categories = preprocessor.categorize_posts(posts)
        
        assert len(categories['bug_reports']) == 2
        assert len(categories['feature_requests']) == 1
    
    def test_preprocess_comments(self, preprocessor):
        """Test preprocessing comments data."""
        comments = [
            {
                'id': 'comment1',
                'author': {'id': 'user1', 'name': 'John', 'email': 'john@test.com'},
                'value': '<p>Great idea!</p>',
                'created': '2024-10-15T10:30:00Z'
            },
            {
                'id': 'comment2',
                'author': {'id': 'user2', 'name': 'Jane'},
                'value': 'I agree  with this',
                'created': '2024-10-16T11:00:00Z'
            }
        ]
        
        processed = preprocessor._preprocess_comments(comments)
        
        assert len(processed) == 2
        assert processed[0]['id'] == 'comment1'
        assert processed[0]['value'] == 'Great idea!'  # HTML removed
        assert processed[1]['value'] == 'I agree with this'  # Whitespace normalized
    
    def test_preprocess_votes(self, preprocessor):
        """Test preprocessing votes data."""
        votes = [
            {
                'id': 'vote1',
                'voter': {'id': 'user1', 'name': 'John', 'email': 'john@test.com'},
                'created': '2024-10-15T10:30:00Z'
            },
            {
                'id': 'vote2',
                'voter': {'id': 'user2', 'name': 'Jane'},
                'created': '2024-10-16T11:00:00Z'
            }
        ]
        
        processed = preprocessor._preprocess_votes(votes)
        
        assert len(processed) == 2
        assert processed[0]['id'] == 'vote1'
        assert processed[0]['voter']['name'] == 'John'
        assert processed[1]['voter']['email'] is None  # No email provided


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

