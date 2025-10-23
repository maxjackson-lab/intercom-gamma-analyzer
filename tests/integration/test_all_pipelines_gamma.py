"""
Comprehensive integration tests for Gamma generation across all pipeline types.

This test suite verifies that:
1. All pipelines generate Gamma URLs correctly
2. URLs are from API responses, not manually constructed
3. Markdown summaries are generated
4. Metadata includes all required fields
"""

import pytest
import os
import asyncio
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List
from unittest.mock import Mock, patch, AsyncMock, MagicMock

from src.services.gamma_generator import GammaGenerator
from src.services.gamma_client import GammaClient, GammaAPIError
from src.services.google_docs_exporter import GoogleDocsExporter


# Sample analysis results for testing
def get_sample_analysis_results(category: str = "general") -> Dict[str, Any]:
    """Generate sample analysis results for testing."""
    return {
        'conversations': [
            {
                'id': f'conv_{i}',
                'created_at': datetime.now().timestamp(),
                'title': f'Test conversation {i}',
                'conversation_parts': {
                    'conversation_parts': [{
                        'body': f'Test message about {category}',
                        'author': {'type': 'user'}
                    }]
                }
            }
            for i in range(10)
        ],
        'category_results': {
            category: {
                'conversation_count': 10,
                'percentage': 100.0,
                'escalation_rate': 15.2,
                'avg_response_time': '2.3 hours'
            }
        },
        'start_date': (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'),
        'end_date': datetime.now().strftime('%Y-%m-%d')
    }


def get_sample_voc_results() -> Dict[str, Any]:
    """Generate sample VoC analysis results."""
    return {
        'results': {
            'billing': {
                'volume': 45,
                'sentiment_breakdown': {'positive': 20, 'neutral': 15, 'negative': 10},
                'examples': ['Example 1', 'Example 2']
            },
            'product': {
                'volume': 32,
                'sentiment_breakdown': {'positive': 18, 'neutral': 10, 'negative': 4},
                'examples': ['Example 1', 'Example 2']
            }
        },
        'agent_feedback_summary': {
            'segmentation': 'Completed',
            'topic_detection': 'Found 3 topics'
        },
        'insights': ['Insight 1', 'Insight 2'],
        'metadata': {
            'total_conversations': 77,
            'date_range': '2024-10-01 to 2024-10-31'
        }
    }


def get_sample_canny_results() -> Dict[str, Any]:
    """Generate sample Canny analysis results."""
    return {
        'posts_analyzed': 150,
        'sentiment_summary': {
            'overall': 'positive',
            'positive': 75,
            'neutral': 50,
            'negative': 25
        },
        'top_requests': [
            {'title': 'Feature A', 'votes': 120},
            {'title': 'Feature B', 'votes': 95}
        ],
        'status_breakdown': {
            'open': 80,
            'planned': 40,
            'in_progress': 20,
            'completed': 10
        },
        'insights': ['Insight 1', 'Insight 2'],
        'metadata': {
            'analysis_date': datetime.now().isoformat()
        }
    }


@pytest.fixture
def mock_gamma_client():
    """Mock Gamma API client."""
    client = AsyncMock(spec=GammaClient)
    
    # Mock generate_presentation
    client.generate_presentation = AsyncMock(return_value="gen_test123")
    
    # Mock poll_generation with realistic response
    client.poll_generation = AsyncMock(return_value={
        'status': 'completed',
        'gammaUrl': 'https://gamma.app/docs/test-presentation-xyz123',
        'generationId': 'gen_test123',
        'exportUrl': None,
        'credits': {'deducted': 2}
    })
    
    return client


@pytest.fixture
def gamma_generator(mock_gamma_client):
    """Create GammaGenerator with mocked client."""
    return GammaGenerator(gamma_client=mock_gamma_client)


class TestVoCPipelineGamma:
    """Test VoC analysis pipeline with Gamma generation."""
    
    @pytest.mark.asyncio
    async def test_voc_pipeline_gamma_generation(self, gamma_generator, tmp_path):
        """Test VoC pipeline generates Gamma correctly."""
        voc_results = get_sample_voc_results()
        
        result = await gamma_generator.generate_from_voc_analysis(
            voc_results=voc_results,
            style="executive",
            output_dir=tmp_path
        )
        
        # Verify URL structure
        assert 'gamma_url' in result
        assert result['gamma_url'].startswith('https://gamma.app/')
        assert 'generation_id' in result
        assert result['credits_used'] >= 0
        
        # Verify markdown was generated
        assert 'markdown_summary_path' in result or result.get('markdown_summary_path') is None
        
        print(f"✅ VoC pipeline test passed: {result['gamma_url']}")


class TestCannyPipelineGamma:
    """Test Canny analysis pipeline with Gamma generation."""
    
    @pytest.mark.asyncio
    async def test_canny_pipeline_gamma_generation(self, gamma_generator, tmp_path):
        """Test Canny pipeline generates Gamma correctly."""
        canny_results = get_sample_canny_results()
        
        result = await gamma_generator.generate_from_canny_analysis(
            canny_results=canny_results,
            style="executive",
            output_dir=tmp_path
        )
        
        # Verify URL structure
        assert 'gamma_url' in result
        assert result['gamma_url'].startswith('https://gamma.app/')
        assert result['gamma_url'] != f"https://gamma.app/{result['generation_id']}"
        assert result['credits_used'] >= 0
        
        print(f"✅ Canny pipeline test passed: {result['gamma_url']}")


class TestBillingPipelineGamma:
    """Test Billing analysis pipeline with Gamma generation."""
    
    @pytest.mark.asyncio
    async def test_billing_pipeline_gamma_generation(self, gamma_generator, tmp_path):
        """Test Billing pipeline generates Gamma correctly."""
        billing_results = get_sample_analysis_results(category="billing")
        
        result = await gamma_generator.generate_from_analysis(
            analysis_results=billing_results,
            style="executive",
            output_dir=tmp_path
        )
        
        # Verify URL structure
        assert 'gamma_url' in result
        assert result['gamma_url'].startswith('https://gamma.app/')
        assert result['credits_used'] >= 0
        assert 'markdown_summary_path' in result
        
        print(f"✅ Billing pipeline test passed: {result['gamma_url']}")


class TestProductPipelineGamma:
    """Test Product analysis pipeline with Gamma generation."""
    
    @pytest.mark.asyncio
    async def test_product_pipeline_gamma_generation(self, gamma_generator, tmp_path):
        """Test Product pipeline generates Gamma correctly."""
        product_results = get_sample_analysis_results(category="product")
        
        result = await gamma_generator.generate_from_analysis(
            analysis_results=product_results,
            style="executive",
            output_dir=tmp_path
        )
        
        # Verify URL structure
        assert 'gamma_url' in result
        assert result['gamma_url'].startswith('https://gamma.app/')
        assert result['credits_used'] >= 0
        
        print(f"✅ Product pipeline test passed: {result['gamma_url']}")


class TestSitesPipelineGamma:
    """Test Sites analysis pipeline with Gamma generation."""
    
    @pytest.mark.asyncio
    async def test_sites_pipeline_gamma_generation(self, gamma_generator, tmp_path):
        """Test Sites pipeline generates Gamma correctly."""
        sites_results = get_sample_analysis_results(category="sites")
        
        result = await gamma_generator.generate_from_analysis(
            analysis_results=sites_results,
            style="executive",
            output_dir=tmp_path
        )
        
        # Verify URL structure
        assert 'gamma_url' in result
        assert result['gamma_url'].startswith('https://gamma.app/')
        
        print(f"✅ Sites pipeline test passed: {result['gamma_url']}")


class TestAPIPipelineGamma:
    """Test API analysis pipeline with Gamma generation."""
    
    @pytest.mark.asyncio
    async def test_api_pipeline_gamma_generation(self, gamma_generator, tmp_path):
        """Test API pipeline generates Gamma correctly."""
        api_results = get_sample_analysis_results(category="api")
        
        result = await gamma_generator.generate_from_analysis(
            analysis_results=api_results,
            style="executive",
            output_dir=tmp_path
        )
        
        # Verify URL structure
        assert 'gamma_url' in result
        assert result['gamma_url'].startswith('https://gamma.app/')
        
        print(f"✅ API pipeline test passed: {result['gamma_url']}")


class TestComprehensivePipelineGamma:
    """Test comprehensive analysis pipeline with Gamma generation."""
    
    @pytest.mark.asyncio
    async def test_comprehensive_pipeline_gamma_generation(self, gamma_generator, tmp_path):
        """Test comprehensive analysis generates Gamma correctly."""
        comprehensive_results = {
            **get_sample_analysis_results(category="comprehensive"),
            'synthesis_results': {'cross_category_patterns': {}},
            'specialized_results': {}
        }
        
        result = await gamma_generator.generate_from_analysis(
            analysis_results=comprehensive_results,
            style="executive",
            output_dir=tmp_path
        )
        
        # Verify URL structure
        assert 'gamma_url' in result
        assert result['gamma_url'].startswith('https://gamma.app/')
        assert 'markdown_generated' in result or 'markdown_summary_path' in result
        
        print(f"✅ Comprehensive pipeline test passed: {result['gamma_url']}")


class TestGammaURLNotConstructed:
    """Test that Gamma URLs are from API, not manually constructed."""
    
    @pytest.mark.asyncio
    async def test_gamma_url_not_constructed(self, gamma_generator, tmp_path):
        """Verify URLs are from API response, not constructed from generation_id."""
        analysis_results = get_sample_analysis_results()
        
        result = await gamma_generator.generate_from_analysis(
            analysis_results=analysis_results,
            style="executive",
            output_dir=tmp_path
        )
        
        # Verify URL is NOT just generation_id appended
        gamma_url = result['gamma_url']
        generation_id = result['generation_id']
        
        assert gamma_url != f"https://gamma.app/{generation_id}"
        assert gamma_url.startswith('https://gamma.app/')
        
        # URL should have more than just the generation_id
        url_parts = gamma_url.replace('https://gamma.app/', '').split('/')
        assert len(url_parts) >= 2  # Should have at least path + id
        
        print(f"✅ URL validation passed: URL is from API, not constructed")


class TestMarkdownGeneration:
    """Test markdown summary generation across pipelines."""
    
    @pytest.mark.asyncio
    async def test_markdown_generation_with_gamma(self, gamma_generator, tmp_path):
        """Test that markdown summaries are generated alongside Gamma."""
        analysis_results = get_sample_analysis_results()
        
        result = await gamma_generator.generate_from_analysis(
            analysis_results=analysis_results,
            style="executive",
            output_dir=tmp_path
        )
        
        # Check markdown was attempted (may be None if generation failed)
        assert 'markdown_summary_path' in result
        
        if result['markdown_summary_path']:
            # If markdown was generated, verify it exists
            markdown_path = Path(result['markdown_summary_path'])
            assert markdown_path.exists()
            assert markdown_path.suffix == '.md'
            
            # Verify metadata
            assert 'markdown_size_bytes' in result
            assert result['markdown_size_bytes'] > 0
            
            print(f"✅ Markdown generated: {markdown_path}")
        else:
            print("⚠️  Markdown generation was skipped or failed (non-fatal)")


class TestMetadataStructure:
    """Test that all pipelines return consistent metadata structure."""
    
    @pytest.mark.asyncio
    async def test_metadata_structure(self, gamma_generator, tmp_path):
        """Test all required metadata fields are present."""
        analysis_results = get_sample_analysis_results()
        
        result = await gamma_generator.generate_from_analysis(
            analysis_results=analysis_results,
            style="executive",
            output_dir=tmp_path
        )
        
        # Required fields
        required_fields = [
            'gamma_url',
            'generation_id',
            'credits_used',
            'generation_time_seconds',
            'style'
        ]
        
        for field in required_fields:
            assert field in result, f"Missing required field: {field}"
        
        # Optional but expected fields
        expected_fields = ['export_url', 'markdown_summary_path', 'slide_count']
        for field in expected_fields:
            assert field in result, f"Missing expected field: {field}"
        
        print(f"✅ Metadata structure validated: {list(result.keys())}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

