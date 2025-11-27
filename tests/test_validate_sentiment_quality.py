import sys
import os
import pytest
from pathlib import Path

# Add scripts directory to path to import the script
scripts_dir = str(Path(__file__).parent.parent / "scripts")
if scripts_dir not in sys.path:
    sys.path.append(scripts_dir)

try:
    from validate_sentiment_quality import analyze_sentiment_quality
except ImportError:
    # Fallback if running from different context
    pass

def test_analyze_sentiment_quality_success(tmp_path):
    """Test basic functionality with a valid log file"""
    log_content = """
2023-01-01 10:00:00 INFO: TopicSentimentAgent: Generated insight for 'Billing' via llm
2023-01-01 10:00:00 INFO:    Insight: Users love the new feature but hate the price.
2023-01-01 10:00:01 INFO: TopicSentimentAgent: Generated insight for 'Bug' via llm
2023-01-01 10:00:01 INFO:    Insight: Negative sentiment detected regarding bugs.
    """
    log_file = tmp_path / "test.log"
    log_file.write_text(log_content, encoding='utf-8')
    
    stats = analyze_sentiment_quality(str(log_file))
    
    assert stats['total_insights'] == 2
    assert stats['insights_with_nuance'] == 1 # "but"
    assert stats['insights_with_generic_patterns'] == 1 # "Negative sentiment detected"
    assert len(stats['details']) == 2
    
    # Check details for first insight
    insight1 = next(d for d in stats['details'] if "Users love" in d['insight'])
    assert insight1['has_nuance'] is True
    assert insight1['has_generic'] is False
    assert insight1['score'] == 1.0
    
    # Check details for second insight
    insight2 = next(d for d in stats['details'] if "Negative sentiment" in d['insight'])
    assert insight2['has_nuance'] is False
    assert insight2['has_generic'] is True
    # Score calculation: 1.0 - 0.2 (no nuance) - 0.3 (generic) = 0.5
    assert insight2['score'] == 0.5

def test_analyze_sentiment_quality_empty_file(tmp_path):
    """Test with empty log file"""
    log_file = tmp_path / "empty.log"
    log_file.write_text("", encoding='utf-8')
    
    stats = analyze_sentiment_quality(str(log_file))
    assert stats == {}

def test_analyze_sentiment_quality_no_insights(tmp_path):
    """Test log file with no insights"""
    log_content = """
2023-01-01 10:00:00 INFO: Starting analysis
2023-01-01 10:00:01 INFO: Analysis complete
    """
    log_file = tmp_path / "no_insights.log"
    log_file.write_text(log_content, encoding='utf-8')
    
    stats = analyze_sentiment_quality(str(log_file))
    assert stats == {}

def test_analyze_sentiment_quality_missing_file():
    """Test with missing file"""
    stats = analyze_sentiment_quality("nonexistent.log")
    assert stats == {}

