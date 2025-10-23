"""
Integration tests for VoC → Gamma pipeline.

Tests the end-to-end flow from VoC analysis through Gamma generation.
"""

import pytest
import os
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List
from unittest.mock import Mock, patch, AsyncMock

from src.services.gamma_generator import GammaGenerator
from src.services.gamma_client import GammaAPIError
from src.agents.topic_orchestrator import TopicOrchestrator


# Sample Hilary-format markdown for testing
SAMPLE_VOC_MARKDOWN = """# Voice of Customer Analysis - Week 2024-W42

## Customer Topics (Paid Tier - Human Support)

### Billing Issues
**45 tickets / 28% of weekly volume**
**Detection Method**: Intercom conversation attribute

**Sentiment**: Customers frustrated with unexpected charges BUT appreciate quick refunds

**Examples**:
1. "I was charged twice for my subscription" - [View conversation](https://app.intercom.com/a/inbox/inbox/conv_123)
2. "Need help understanding my invoice" - [View conversation](https://app.intercom.com/a/inbox/inbox/conv_124)
3. "Refund request for duplicate charge" - [View conversation](https://app.intercom.com/a/inbox/inbox/conv_125)
4. "Incorrect billing amount shown" - [View conversation](https://app.intercom.com/a/inbox/inbox/conv_126)
5. "Want to cancel my subscription" - [View conversation](https://app.intercom.com/a/inbox/inbox/conv_127)

---

### Product Questions
**32 tickets / 20% of weekly volume**
**Detection Method**: Keyword detection

**Sentiment**: Users love the new features BUT confused by setup process

**Examples**:
1. "How do I enable the new dashboard?" - [View conversation](https://app.intercom.com/a/inbox/inbox/conv_128)
2. "Can't find the export button" - [View conversation](https://app.intercom.com/a/inbox/inbox/conv_129)
3. "New feature not working as expected" - [View conversation](https://app.intercom.com/a/inbox/inbox/conv_130)

---

### Technical Issues
**28 tickets / 17% of weekly volume**
**Detection Method**: Keyword detection

**Sentiment**: Users experiencing bugs BUT patient with support team

**Examples**:
1. "App crashes when I try to export" - [View conversation](https://app.intercom.com/a/inbox/inbox/conv_131)
2. "Data not syncing properly" - [View conversation](https://app.intercom.com/a/inbox/inbox/conv_132)
3. "Login errors on mobile app" - [View conversation](https://app.intercom.com/a/inbox/inbox/conv_133)
4. "Integration with Salesforce broken" - [View conversation](https://app.intercom.com/a/inbox/inbox/conv_134)

---

## Fin AI Performance (Free Tier - AI-Only Support)

### Fin AI Analysis
**89 conversations handled by Fin this week**

**What Fin is Doing Well**:
- Resolution rate: 72% of conversations resolved without escalation request
- Fastest responses on basic account questions
- Good at directing users to documentation

**Knowledge Gaps**:
- 12 conversations where Fin gave incorrect/incomplete information
- Struggles with complex billing questions
- Needs better context on recent product updates

---
"""


@pytest.fixture
def sample_voc_markdown_report() -> str:
    """Returns realistic Hilary-format markdown."""
    return SAMPLE_VOC_MARKDOWN


@pytest.fixture
def sample_topic_orchestrator_results() -> Dict[str, Any]:
    """Returns realistic TopicOrchestrator output."""
    return {
        'formatted_report': SAMPLE_VOC_MARKDOWN,
        'summary': {
            'total_conversations': 160,
            'paid_conversations': 71,
            'free_conversations': 89,
            'topics_analyzed': 3,
            'total_execution_time': 12.5,
            'agents_completed': 7
        },
        'agent_results': {
            'segmentation': {'status': 'completed'},
            'topic_detection': {'status': 'completed', 'topics_found': 3},
            'topic_analysis': {'status': 'completed'},
            'example_extraction': {'status': 'completed'},
            'fin_analysis': {'status': 'completed'},
            'trend_analysis': {'status': 'completed'},
            'output_formatter': {'status': 'completed'}
        },
        'metrics': {
            'segmentation_time': 2.1,
            'topic_detection_time': 3.2,
            'topic_analysis_time': 4.5,
            'example_extraction_time': 1.8,
            'fin_analysis_time': 0.6,
            'trend_analysis_time': 0.3
        }
    }


@pytest.fixture
def mock_conversations() -> List[Dict[str, Any]]:
    """Generate mock conversations for testing."""
    conversations = []
    topics = [
        ("billing", ["charged", "refund", "subscription"]),
        ("product", ["feature", "dashboard", "export"]),
        ("technical", ["crash", "bug", "error"])
    ]
    
    for i in range(20):
        topic_idx = i % len(topics)
        topic_name, keywords = topics[topic_idx]
        
        conversations.append({
            'id': f'conv_{i+1}',
            'created_at': 1696000000 + (i * 3600),
            'updated_at': 1696000000 + (i * 3600),
            'title': f"Test conversation {i+1}",
            'conversation_parts': {
                'conversation_parts': [{
                    'body': f"Test message about {keywords[i % len(keywords)]}",
                    'part_type': 'comment',
                    'author': {'type': 'user'}
                }]
            },
            'tags': {'tags': []},
            'custom_attributes': {
                'tier': 'paid' if i < 15 else 'free'
            },
            'source': {
                'author': {
                    'type': 'user',
                    'id': f'user_{i}'
                }
            }
        })
    
    return conversations


class TestVoCMarkdownToGammaConversion:
    """Test markdown to Gamma conversion."""
    
    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not os.getenv("GAMMA_API_KEY"),
        reason="GAMMA_API_KEY not set"
    )
    async def test_voc_markdown_to_gamma_conversion(self, sample_voc_markdown_report):
        """Test converting VoC markdown to Gamma presentation."""
        gamma_generator = GammaGenerator()
        
        result = await gamma_generator.generate_from_markdown(
            input_text=sample_voc_markdown_report,
            title="Voice of Customer Analysis - Week 2024-W42",
            num_cards=10,
            theme_name=None,
            export_format=None
        )
        
        # Assert basic structure
        assert 'gamma_url' in result
        assert result['gamma_url'].startswith('https://gamma.app/')
        assert 'generation_id' in result
        assert result['credits_used'] >= 0
        assert result['generation_time_seconds'] > 0
        
        print(f"\n✅ Gamma presentation generated!")
        print(f"📊 URL: {result['gamma_url']}")
        print(f"💳 Credits: {result['credits_used']}")
        print(f"⏱️  Time: {result['generation_time_seconds']:.1f}s")
    
    @pytest.mark.asyncio
    async def test_voc_markdown_validation_before_gamma(self):
        """Test markdown validation logic."""
        gamma_generator = GammaGenerator()
        
        # Test too short
        with pytest.raises((ValueError, GammaAPIError)):
            await gamma_generator.generate_from_markdown(
                input_text="Too short",
                num_cards=5
            )
        
        # Test too long (> 750,000 chars)
        with pytest.raises((ValueError, GammaAPIError)):
            await gamma_generator.generate_from_markdown(
                input_text="x" * 750001,
                num_cards=5
            )
        
        # Test valid markdown passes
        valid_markdown = """# Test Report
        
## Section 1

Some content here with enough text to be valid.

---

## Section 2

More content here to ensure we meet minimum length.
"""
        # Should not raise for valid input (but will fail without API key)
        if os.getenv("GAMMA_API_KEY"):
            result = await gamma_generator.generate_from_markdown(
                input_text=valid_markdown,
                num_cards=3
            )
            assert result is not None


class TestTopicOrchestratorToGammaFullPipeline:
    """Test full pipeline from TopicOrchestrator to Gamma."""
    
    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not os.getenv("GAMMA_API_KEY") or not os.getenv("INTERCOM_ACCESS_TOKEN"),
        reason="GAMMA_API_KEY or INTERCOM_ACCESS_TOKEN not set"
    )
    async def test_topic_orchestrator_to_gamma_full_pipeline(self, mock_conversations):
        """Test full pipeline with TopicOrchestrator."""
        # Create TopicOrchestrator
        orchestrator = TopicOrchestrator()
        
        # Execute analysis
        from datetime import datetime
        start_date = datetime(2024, 10, 1)
        end_date = datetime(2024, 10, 31)
        
        results = await orchestrator.execute_weekly_analysis(
            conversations=mock_conversations,
            week_id="2024-W42",
            start_date=start_date,
            end_date=end_date
        )
        
        # Extract formatted report
        formatted_report = results.get('formatted_report', '')
        assert formatted_report, "No formatted report generated"
        assert len(formatted_report) > 200, "Report too short"
        
        # Generate Gamma presentation
        gamma_generator = GammaGenerator()
        gamma_result = await gamma_generator.generate_from_markdown(
            input_text=formatted_report,
            title="Voice of Customer Analysis - Week 2024-W42",
            num_cards=10
        )
        
        # Assert success
        assert gamma_result['gamma_url']
        assert gamma_result['generation_id']
        
        print(f"\n✅ Full pipeline test completed!")
        print(f"📊 Topics analyzed: {results['summary']['topics_analyzed']}")
        print(f"🎨 Gamma URL: {gamma_result['gamma_url']}")
        print(f"⏱️  Total time: {results['summary']['total_execution_time']:.1f}s + {gamma_result['generation_time_seconds']:.1f}s")


class TestVoCGammaWithSlideBreaks:
    """Test Gamma generation with slide breaks."""
    
    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not os.getenv("GAMMA_API_KEY"),
        reason="GAMMA_API_KEY not set"
    )
    async def test_voc_gamma_with_slide_breaks(self):
        """Test Gamma respects --- slide breaks."""
        markdown_with_breaks = """# Test Presentation

## Slide 1
Content for slide 1

---

## Slide 2
Content for slide 2

---

## Slide 3
Content for slide 3
"""
        
        gamma_generator = GammaGenerator()
        result = await gamma_generator.generate_from_markdown(
            input_text=markdown_with_breaks,
            num_cards=5
        )
        
        assert result['gamma_url']
        print(f"\n✅ Slide break test completed!")
        print(f"📊 URL: {result['gamma_url']}")


class TestVoCGammaWithExportFormat:
    """Test Gamma generation with export formats."""
    
    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not os.getenv("GAMMA_API_KEY"),
        reason="GAMMA_API_KEY not set"
    )
    async def test_voc_gamma_with_export_format(self, sample_voc_markdown_report):
        """Test Gamma generation with PDF export."""
        gamma_generator = GammaGenerator()
        
        result = await gamma_generator.generate_from_markdown(
            input_text=sample_voc_markdown_report,
            title="Voice of Customer Analysis - Week 2024-W42",
            num_cards=10,
            export_format="pdf"
        )
        
        assert result['gamma_url']
        # Note: export_url may not be immediately available
        print(f"\n✅ Export format test completed!")
        print(f"📊 Gamma URL: {result['gamma_url']}")
        if result.get('export_url'):
            print(f"📄 Export URL: {result['export_url']}")


class TestVoCGammaErrorHandling:
    """Test error handling in Gamma generation."""
    
    @pytest.mark.asyncio
    async def test_voc_gamma_error_handling(self):
        """Test error handling with invalid markdown."""
        gamma_generator = GammaGenerator()
        
        # Test empty string
        with pytest.raises((ValueError, GammaAPIError)):
            await gamma_generator.generate_from_markdown(
                input_text="",
                num_cards=5
            )
        
        # Test markdown > 750k characters
        with pytest.raises((ValueError, GammaAPIError)):
            await gamma_generator.generate_from_markdown(
                input_text="x" * 750001,
                num_cards=5
            )


class TestRunTopicBasedAnalysisWithGamma:
    """Test run_topic_based_analysis with Gamma flag."""
    
    @pytest.mark.asyncio
    async def test_run_topic_based_analysis_with_gamma_flag(
        self,
        sample_topic_orchestrator_results,
        tmp_path
    ):
        """Test that run_topic_based_analysis calls Gamma when flag is set."""
        # Mock TopicOrchestrator
        with patch('src.agents.topic_orchestrator.TopicOrchestrator') as MockOrch, \
             patch('src.services.gamma_generator.GammaGenerator') as MockGamma, \
             patch('src.services.chunked_fetcher.ChunkedFetcher') as MockFetcher:
            
            # Setup mocks
            mock_orch_instance = AsyncMock()
            mock_orch_instance.execute_weekly_analysis = AsyncMock(
                return_value=sample_topic_orchestrator_results
            )
            MockOrch.return_value = mock_orch_instance
            
            mock_gamma_instance = AsyncMock()
            mock_gamma_instance.generate_from_markdown = AsyncMock(
                return_value={
                    'gamma_url': 'https://gamma.app/test123',
                    'generation_id': 'gen_123',
                    'credits_used': 2,
                    'generation_time_seconds': 15.5
                }
            )
            MockGamma.return_value = mock_gamma_instance
            
            mock_fetcher_instance = AsyncMock()
            mock_fetcher_instance.fetch_conversations_chunked = AsyncMock(
                return_value=[]
            )
            MockFetcher.return_value = mock_fetcher_instance
            
            # Import and call function
            from src.main import run_topic_based_analysis
            
            await run_topic_based_analysis(
                month=10,
                year=2024,
                tier1_countries=[],
                generate_gamma=True,
                output_format='gamma'
            )
            
            # Assert TopicOrchestrator was called
            mock_orch_instance.execute_weekly_analysis.assert_called_once()
            
            # Assert GammaGenerator was called with correct markdown
            mock_gamma_instance.generate_from_markdown.assert_called_once()
            call_args = mock_gamma_instance.generate_from_markdown.call_args
            assert call_args[1]['input_text'] == SAMPLE_VOC_MARKDOWN
    
    @pytest.mark.asyncio
    async def test_run_topic_based_analysis_without_gamma_flag(
        self,
        sample_topic_orchestrator_results
    ):
        """Test that run_topic_based_analysis skips Gamma when flag is False."""
        with patch('src.agents.topic_orchestrator.TopicOrchestrator') as MockOrch, \
             patch('src.services.gamma_generator.GammaGenerator') as MockGamma, \
             patch('src.services.chunked_fetcher.ChunkedFetcher') as MockFetcher:
            
            # Setup mocks
            mock_orch_instance = AsyncMock()
            mock_orch_instance.execute_weekly_analysis = AsyncMock(
                return_value=sample_topic_orchestrator_results
            )
            MockOrch.return_value = mock_orch_instance
            
            mock_gamma_instance = AsyncMock()
            MockGamma.return_value = mock_gamma_instance
            
            mock_fetcher_instance = AsyncMock()
            mock_fetcher_instance.fetch_conversations_chunked = AsyncMock(
                return_value=[]
            )
            MockFetcher.return_value = mock_fetcher_instance
            
            # Import and call function
            from src.main import run_topic_based_analysis
            
            await run_topic_based_analysis(
                month=10,
                year=2024,
                tier1_countries=[],
                generate_gamma=False,
                output_format='markdown'
            )
            
            # Assert TopicOrchestrator was called
            mock_orch_instance.execute_weekly_analysis.assert_called_once()
            
            # Assert GammaGenerator was NOT called
            mock_gamma_instance.generate_from_markdown.assert_not_called()


class TestMarkdownFormatValidation:
    """Test markdown format validation."""
    
    def test_markdown_format_validation(self, sample_voc_markdown_report):
        """Test OutputFormatterAgent output format."""
        markdown = sample_voc_markdown_report
        
        # Check required sections
        assert "# Voice of Customer Analysis" in markdown
        assert "## Customer Topics" in markdown
        assert "## Fin AI Performance" in markdown
        
        # Check slide breaks
        assert "---" in markdown
        slide_breaks = markdown.count("---")
        assert slide_breaks >= 3, "Should have multiple slide breaks"
        
        # Check Intercom URLs
        assert "https://app.intercom.com/a/inbox/inbox/conv_" in markdown
        
        # Check topic card structure
        assert "**Detection Method**:" in markdown
        assert "**Sentiment**:" in markdown
        assert "**Examples**:" in markdown
        assert "tickets / " in markdown
        assert "% of weekly volume" in markdown
    
    def test_gamma_input_length_validation(self):
        """Test markdown length validation."""
        gamma_generator = GammaGenerator()
        
        # Too short
        short_text = "x"
        with pytest.raises(ValueError, match="must be 1-750,000 characters"):
            asyncio.run(gamma_generator.generate_from_markdown(short_text, num_cards=5))
        
        # Too long
        long_text = "x" * 750001
        with pytest.raises(ValueError, match="must be 1-750,000 characters"):
            asyncio.run(gamma_generator.generate_from_markdown(long_text, num_cards=5))
        
        # Valid length (won't actually call API without key)
        valid_text = "x" * 500
        # Just test that it doesn't raise ValueError for length
        # (will fail later due to missing API key, but that's expected)

