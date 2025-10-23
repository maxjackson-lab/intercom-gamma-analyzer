"""
Unit tests for GammaGenerator service.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path
import json

from src.services.gamma_generator import GammaGenerator
from src.services.gamma_client import GammaAPIError


class TestGammaGenerator:
    """Test cases for GammaGenerator."""
    
    @pytest.fixture
    def gamma_generator(self):
        """Create a GammaGenerator instance for testing."""
        with patch('services.gamma_generator.GammaClient') as mock_client, \
             patch('services.gamma_generator.PresentationBuilder') as mock_builder:
            
            mock_client_instance = Mock()
            mock_builder_instance = Mock()
            
            return GammaGenerator(
                gamma_client=mock_client_instance,
                presentation_builder=mock_builder_instance
            )
    
    @pytest.fixture
    def sample_analysis_results(self):
        """Create sample analysis results for testing."""
        return {
            'conversations': [
                {
                    'id': 'conv_1',
                    'created_at': '2024-01-01T10:00:00Z',
                    'state': 'closed'
                }
            ],
            'category_results': {
                'Billing': {
                    'conversation_count': 1,
                    'percentage': 50.0
                }
            },
            'start_date': '2024-01-01',
            'end_date': '2024-01-31'
        }
    
    @pytest.fixture
    def mock_gamma_result(self):
        """Create mock Gamma generation result."""
        return {
            'gammaUrl': 'https://gamma.app/p/test_url',
            'generationId': 'test_generation_id',
            'exportUrl': 'https://gamma.app/export/test.pdf',
            'credits': {'deducted': 5}
        }
    
    @pytest.mark.asyncio
    async def test_gamma_generator_initialization(self, gamma_generator):
        """Test GammaGenerator initializes correctly."""
        assert gamma_generator.client is not None
        assert gamma_generator.builder is not None
        assert gamma_generator.prompts is not None
    
    @pytest.mark.asyncio
    async def test_generate_from_analysis_success(self, gamma_generator, sample_analysis_results, mock_gamma_result):
        """Test successful presentation generation."""
        # Mock the builder to return narrative content
        gamma_generator.builder.build_narrative_content.return_value = "Test narrative content"
        
        # Mock the client methods
        gamma_generator.client.generate_presentation.return_value = "test_generation_id"
        gamma_generator.client.poll_generation.return_value = mock_gamma_result
        
        result = await gamma_generator.generate_from_analysis(
            analysis_results=sample_analysis_results,
            style="executive"
        )
        
        assert result['gamma_url'] == 'https://gamma.app/p/test_url'
        assert result['generation_id'] == 'test_generation_id'
        assert result['export_url'] == 'https://gamma.app/export/test.pdf'
        assert result['credits_used'] == 5
        assert result['style'] == 'executive'
        assert result['generation_time_seconds'] > 0
        
        # Verify builder was called
        gamma_generator.builder.build_narrative_content.assert_called_once_with(
            sample_analysis_results, 'executive'
        )
        
        # Verify client was called
        gamma_generator.client.generate_presentation.assert_called_once()
        gamma_generator.client.poll_generation.assert_called_once_with('test_generation_id')
    
    @pytest.mark.asyncio
    async def test_generate_from_analysis_with_export(self, gamma_generator, sample_analysis_results, mock_gamma_result):
        """Test generation with PDF/PPTX export."""
        gamma_generator.builder.build_narrative_content.return_value = "Test content"
        gamma_generator.client.generate_presentation.return_value = "test_generation_id"
        gamma_generator.client.poll_generation.return_value = mock_gamma_result
        
        result = await gamma_generator.generate_from_analysis(
            analysis_results=sample_analysis_results,
            style="detailed",
            export_format="pdf"
        )
        
        assert result['export_format'] == 'pdf'
        
        # Verify export format was passed to client
        call_args = gamma_generator.client.generate_presentation.call_args
        assert call_args[1]['export_as'] == 'pdf'
    
    @pytest.mark.asyncio
    async def test_generate_from_analysis_saves_metadata(self, gamma_generator, sample_analysis_results, mock_gamma_result):
        """Test that generation metadata is saved when output_dir is provided."""
        gamma_generator.builder.build_narrative_content.return_value = "Test content"
        gamma_generator.client.generate_presentation.return_value = "test_generation_id"
        gamma_generator.client.poll_generation.return_value = mock_gamma_result
        
        output_dir = Path('/tmp/test_output')
        output_dir.mkdir(exist_ok=True)
        
        result = await gamma_generator.generate_from_analysis(
            analysis_results=sample_analysis_results,
            style="training",
            output_dir=output_dir
        )
        
        assert result['gamma_url'] == 'https://gamma.app/p/test_url'
        
        # Check that metadata file was created
        metadata_files = list(output_dir.glob('gamma_generation_training_*.json'))
        assert len(metadata_files) == 1
        
        # Verify metadata content
        with open(metadata_files[0], 'r') as f:
            metadata = json.load(f)
        
        assert metadata['generation_metadata']['gamma_url'] == 'https://gamma.app/p/test_url'
        assert metadata['analysis_summary']['conversation_count'] == 1
        assert metadata['style'] == 'training'
    
    @pytest.mark.asyncio
    async def test_generate_executive_presentation(self, gamma_generator, sample_analysis_results, mock_gamma_result):
        """Test executive presentation generation."""
        gamma_generator.builder.build_narrative_content.return_value = "Executive content"
        gamma_generator.client.generate_presentation.return_value = "test_generation_id"
        gamma_generator.client.poll_generation.return_value = mock_gamma_result
        
        result = await gamma_generator.generate_executive_presentation(sample_analysis_results)
        
        assert result['style'] == 'executive'
        gamma_generator.builder.build_narrative_content.assert_called_once_with(
            sample_analysis_results, 'executive'
        )
    
    @pytest.mark.asyncio
    async def test_generate_detailed_presentation(self, gamma_generator, sample_analysis_results, mock_gamma_result):
        """Test detailed presentation generation."""
        gamma_generator.builder.build_narrative_content.return_value = "Detailed content"
        gamma_generator.client.generate_presentation.return_value = "test_generation_id"
        gamma_generator.client.poll_generation.return_value = mock_gamma_result
        
        result = await gamma_generator.generate_detailed_presentation(sample_analysis_results)
        
        assert result['style'] == 'detailed'
        gamma_generator.builder.build_narrative_content.assert_called_once_with(
            sample_analysis_results, 'detailed'
        )
    
    @pytest.mark.asyncio
    async def test_generate_training_presentation(self, gamma_generator, sample_analysis_results, mock_gamma_result):
        """Test training presentation generation."""
        gamma_generator.builder.build_narrative_content.return_value = "Training content"
        gamma_generator.client.generate_presentation.return_value = "test_generation_id"
        gamma_generator.client.poll_generation.return_value = mock_gamma_result
        
        result = await gamma_generator.generate_training_presentation(sample_analysis_results)
        
        assert result['style'] == 'training'
        gamma_generator.builder.build_narrative_content.assert_called_once_with(
            sample_analysis_results, 'training'
        )
    
    @pytest.mark.asyncio
    async def test_generate_all_styles(self, gamma_generator, sample_analysis_results, mock_gamma_result):
        """Test generation of all presentation styles."""
        gamma_generator.builder.build_narrative_content.return_value = "Test content"
        gamma_generator.client.generate_presentation.return_value = "test_generation_id"
        gamma_generator.client.poll_generation.return_value = mock_gamma_result
        
        results = await gamma_generator.generate_all_styles(sample_analysis_results)
        
        assert len(results) == 3
        assert 'executive' in results
        assert 'detailed' in results
        assert 'training' in results
        
        for style, result in results.items():
            assert result['style'] == style
            assert result['gamma_url'] == 'https://gamma.app/p/test_url'
    
    @pytest.mark.asyncio
    async def test_generate_all_styles_with_failures(self, gamma_generator, sample_analysis_results, mock_gamma_result):
        """Test generation of all styles with some failures."""
        gamma_generator.builder.build_narrative_content.return_value = "Test content"
        
        # Mock client to fail for detailed style
        def mock_generate_presentation(*args, **kwargs):
            if kwargs.get('num_cards', 0) == 18:  # detailed style
                raise GammaAPIError("Generation failed")
            return "test_generation_id"
        
        gamma_generator.client.generate_presentation.side_effect = mock_generate_presentation
        gamma_generator.client.poll_generation.return_value = mock_gamma_result
        
        results = await gamma_generator.generate_all_styles(sample_analysis_results)
        
        assert len(results) == 3
        assert results['executive']['gamma_url'] == 'https://gamma.app/p/test_url'
        assert results['detailed']['error'] == 'Generation failed'
        assert results['training']['gamma_url'] == 'https://gamma.app/p/test_url'
    
    @pytest.mark.asyncio
    async def test_handle_gamma_api_timeout(self, gamma_generator, sample_analysis_results):
        """Test handling of API timeout during polling."""
        gamma_generator.builder.build_narrative_content.return_value = "Test content"
        gamma_generator.client.generate_presentation.return_value = "test_generation_id"
        gamma_generator.client.poll_generation.side_effect = GammaAPIError("Polling timeout")
        
        with pytest.raises(GammaAPIError, match="Polling timeout"):
            await gamma_generator.generate_from_analysis(sample_analysis_results)
    
    @pytest.mark.asyncio
    async def test_handle_builder_error(self, gamma_generator, sample_analysis_results):
        """Test handling of presentation builder errors."""
        gamma_generator.builder.build_narrative_content.side_effect = Exception("Builder error")
        
        with pytest.raises(Exception, match="Builder error"):
            await gamma_generator.generate_from_analysis(sample_analysis_results)
    
    @pytest.mark.asyncio
    async def test_credits_tracking(self, gamma_generator, sample_analysis_results, mock_gamma_result):
        """Test Gamma credit usage is logged and returned."""
        gamma_generator.builder.build_narrative_content.return_value = "Test content"
        gamma_generator.client.generate_presentation.return_value = "test_generation_id"
        gamma_generator.client.poll_generation.return_value = mock_gamma_result
        
        result = await gamma_generator.generate_from_analysis(sample_analysis_results)
        
        assert result['credits_used'] == 5
    
    @pytest.mark.asyncio
    async def test_multiple_style_generation(self, gamma_generator, sample_analysis_results, mock_gamma_result):
        """Test all style variants (executive, detailed, training)."""
        gamma_generator.builder.build_narrative_content.return_value = "Test content"
        gamma_generator.client.generate_presentation.return_value = "test_generation_id"
        gamma_generator.client.poll_generation.return_value = mock_gamma_result
        
        styles = ['executive', 'detailed', 'training']
        
        for style in styles:
            result = await gamma_generator.generate_from_analysis(
                sample_analysis_results, 
                style=style
            )
            assert result['style'] == style
    
    def test_get_available_styles(self, gamma_generator):
        """Test getting list of available presentation styles."""
        styles = gamma_generator.get_available_styles()
        
        assert styles == ['executive', 'detailed', 'training']
    
    def test_get_style_description(self, gamma_generator):
        """Test getting description of presentation styles."""
        executive_desc = gamma_generator.get_style_description('executive')
        detailed_desc = gamma_generator.get_style_description('detailed')
        training_desc = gamma_generator.get_style_description('training')
        unknown_desc = gamma_generator.get_style_description('unknown')
        
        assert 'executives' in executive_desc
        assert 'operations teams' in detailed_desc
        assert 'support teams' in training_desc
        assert unknown_desc == 'Unknown presentation style'
    
    @pytest.mark.asyncio
    async def test_test_gamma_connection_success(self, gamma_generator):
        """Test successful Gamma connection test."""
        gamma_generator.client.test_connection.return_value = True
        
        result = await gamma_generator.test_gamma_connection()
        
        assert result is True
        gamma_generator.client.test_connection.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_test_gamma_connection_failure(self, gamma_generator):
        """Test Gamma connection test failure."""
        gamma_generator.client.test_connection.side_effect = Exception("Connection failed")
        
        result = await gamma_generator.test_gamma_connection()
        
        assert result is False
    
    def test_get_generation_statistics_single(self, gamma_generator):
        """Test generation statistics for single result."""
        single_result = {
            'gamma_url': 'https://gamma.app/p/test',
            'credits_used': 5,
            'generation_time_seconds': 10.5,
            'style': 'executive'
        }
        
        stats = gamma_generator.get_generation_statistics(single_result)
        
        assert stats['total_generations'] == 1
        assert stats['successful_generations'] == 1
        assert stats['total_credits_used'] == 5
        assert stats['total_time_seconds'] == 10.5
        assert stats['styles_generated'] == ['executive']
    
    def test_get_generation_statistics_multiple(self, gamma_generator):
        """Test generation statistics for multiple results."""
        multiple_results = {
            'executive': {
                'gamma_url': 'https://gamma.app/p/exec',
                'credits_used': 5,
                'generation_time_seconds': 10.0,
                'style': 'executive'
            },
            'detailed': {
                'gamma_url': 'https://gamma.app/p/det',
                'credits_used': 8,
                'generation_time_seconds': 15.0,
                'style': 'detailed'
            },
            'training': {
                'error': 'Generation failed',
                'style': 'training'
            }
        }
        
        stats = gamma_generator.get_generation_statistics(multiple_results)
        
        assert stats['total_generations'] == 3
        assert stats['successful_generations'] == 2
        assert stats['failed_generations'] == 1
        assert stats['total_credits_used'] == 13
        assert stats['total_time_seconds'] == 25.0
        assert stats['styles_generated'] == ['executive', 'detailed']
        assert stats['failed_styles'] == ['training']
    
    @pytest.mark.asyncio
    async def test_generate_from_analysis_with_output_dir_creation(self, gamma_generator, sample_analysis_results, mock_gamma_result):
        """Test that output directory is created if it doesn't exist."""
        gamma_generator.builder.build_narrative_content.return_value = "Test content"
        gamma_generator.client.generate_presentation.return_value = "test_generation_id"
        gamma_generator.client.poll_generation.return_value = mock_gamma_result
        
        # Use a non-existent directory
        output_dir = Path('/tmp/non_existent_dir')
        
        result = await gamma_generator.generate_from_analysis(
            analysis_results=sample_analysis_results,
            style="executive",
            output_dir=output_dir
        )
        
        assert result['gamma_url'] == 'https://gamma.app/p/test_url'
        assert output_dir.exists()
    
    @pytest.mark.asyncio
    async def test_generate_from_analysis_metadata_save_error(self, gamma_generator, sample_analysis_results, mock_gamma_result):
        """Test handling of metadata save errors."""
        gamma_generator.builder.build_narrative_content.return_value = "Test content"
        gamma_generator.client.generate_presentation.return_value = "test_generation_id"
        gamma_generator.client.poll_generation.return_value = mock_gamma_result
        
        # Mock Path to raise an error
        with patch('pathlib.Path.mkdir', side_effect=PermissionError("Permission denied")):
            # Should not raise an error, just log it
            result = await gamma_generator.generate_from_analysis(
                analysis_results=sample_analysis_results,
                style="executive",
                output_dir=Path('/invalid/path')
            )
            
            assert result['gamma_url'] == 'https://gamma.app/p/test_url'