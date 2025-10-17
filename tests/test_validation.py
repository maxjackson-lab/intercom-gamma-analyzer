"""
Tests for data validation functionality.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from services.orchestrator import AnalysisOrchestrator
from services.gamma_generator import GammaGenerator


class TestDataValidation:
    """Test data validation functionality."""

    @pytest.fixture
    def orchestrator(self):
        """Fixture to provide an AnalysisOrchestrator instance."""
        return AnalysisOrchestrator()

    @pytest.fixture
    def gamma_generator(self):
        """Fixture to provide a GammaGenerator instance."""
        return GammaGenerator()

    @pytest.fixture
    def sample_conversations(self):
        """Sample conversations for testing."""
        return [
            {
                'id': 'conv_1',
                'created_at': '2024-01-01T10:00:00Z',
                'tags': {'tags': [{'name': 'Billing'}]},
                'source': {'body': 'Billing issue'}
            },
            {
                'id': 'conv_2',
                'created_at': '2024-01-15T11:00:00Z',  # Spread out dates
                'tags': {'tags': [{'name': 'API'}]},
                'source': {'body': 'API problem'}
            },
            {
                'id': 'conv_3',
                'created_at': '2024-01-30T12:00:00Z',  # Spread out dates
                'tags': {'tags': [{'name': 'Product Question'}]},
                'source': {'body': 'Product question'}
            }
        ]

    @pytest.mark.asyncio
    async def test_validate_data_completeness_good_data(self, orchestrator, sample_conversations):
        """Test validation with good data."""
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 31)
        
        validation_results = await orchestrator._validate_data_completeness(
            sample_conversations,
            max_conversations=10,  # More reasonable for test data
            start_date=start_date,
            end_date=end_date
        )
        
        assert validation_results['passed'] is True
        assert validation_results['completeness_ratio'] > 0
        assert validation_results['data_quality_score'] > 0
        assert len(validation_results['warnings']) == 0

    @pytest.mark.asyncio
    async def test_validate_data_completeness_insufficient_data(self, orchestrator, sample_conversations):
        """Test validation with insufficient data."""
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 31)
        
        validation_results = await orchestrator._validate_data_completeness(
            sample_conversations,
            max_conversations=100,  # Much higher than actual count
            start_date=start_date,
            end_date=end_date
        )
        
        assert validation_results['passed'] is False
        assert validation_results['completeness_ratio'] < 0.8
        assert len(validation_results['warnings']) > 0
        assert any('Only retrieved' in warning for warning in validation_results['warnings'])

    @pytest.mark.asyncio
    async def test_validate_data_completeness_dominant_category(self, orchestrator):
        """Test validation with dominant single category."""
        conversations = [
            {'tags': {'tags': [{'name': 'Billing'}]}, 'created_at': '2024-01-01T10:00:00Z'},
            {'tags': {'tags': [{'name': 'Billing'}]}, 'created_at': '2024-01-02T10:00:00Z'},
            {'tags': {'tags': [{'name': 'Billing'}]}, 'created_at': '2024-01-03T10:00:00Z'},
            {'tags': {'tags': [{'name': 'Billing'}]}, 'created_at': '2024-01-04T10:00:00Z'},
            {'tags': {'tags': [{'name': 'API'}]}, 'created_at': '2024-01-05T10:00:00Z'},
        ]
        
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 31)
        
        validation_results = await orchestrator._validate_data_completeness(
            conversations,
            max_conversations=100,
            start_date=start_date,
            end_date=end_date
        )
        
        # Should warn about dominant category
        assert any('dominates dataset' in warning for warning in validation_results['warnings'])

    @pytest.mark.asyncio
    async def test_validate_data_completeness_date_coverage(self, orchestrator):
        """Test validation with poor date coverage."""
        conversations = [
            {'tags': {'tags': [{'name': 'Billing'}]}, 'created_at': '2024-01-01T10:00:00Z'},
            {'tags': {'tags': [{'name': 'API'}]}, 'created_at': '2024-01-02T10:00:00Z'},
        ]
        
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 31)  # 30-day range but only 2 days of data
        
        validation_results = await orchestrator._validate_data_completeness(
            conversations,
            max_conversations=100,
            start_date=start_date,
            end_date=end_date
        )
        
        # Should warn about date coverage
        assert any('Date range coverage' in warning for warning in validation_results['warnings'])

    def test_gamma_input_validation_good_input(self, gamma_generator):
        """Test Gamma input validation with good input."""
        input_text = """
        # Executive Summary
        This is a comprehensive analysis of customer support data with detailed insights and findings.
        
        # Analysis
        We found several key patterns in the data including billing issues, API problems, and product questions.
        The analysis covers multiple categories and provides actionable insights for improvement.
        
        # Recommendations
        Based on our analysis, we recommend the following actions to improve customer support effectiveness.
        These recommendations are based on data-driven insights and will help optimize our support processes.
        """
        
        analysis_results = {
            'conversations': [{'id': 'conv_1'}, {'id': 'conv_2'}],
            'category_results': {'Billing': {'count': 10}}
        }
        
        errors = gamma_generator._validate_gamma_input(input_text, analysis_results)
        assert len(errors) == 0

    def test_gamma_input_validation_empty_input(self, gamma_generator):
        """Test Gamma input validation with empty input."""
        input_text = ""
        analysis_results = {'conversations': [], 'category_results': {}}
        
        errors = gamma_generator._validate_gamma_input(input_text, analysis_results)
        assert len(errors) > 0
        assert any('Input text is empty' in error for error in errors)

    def test_gamma_input_validation_too_long(self, gamma_generator):
        """Test Gamma input validation with input too long."""
        input_text = "x" * 800000  # Over 750k limit
        analysis_results = {'conversations': [{'id': 'conv_1'}], 'category_results': {}}
        
        errors = gamma_generator._validate_gamma_input(input_text, analysis_results)
        assert len(errors) > 0
        assert any('too long' in error for error in errors)

    def test_gamma_input_validation_missing_sections(self, gamma_generator):
        """Test Gamma input validation with missing required sections."""
        input_text = "This is just some text without proper sections."
        analysis_results = {'conversations': [{'id': 'conv_1'}], 'category_results': {}}
        
        errors = gamma_generator._validate_gamma_input(input_text, analysis_results)
        assert len(errors) > 0
        assert any('Missing required section' in error for error in errors)

    def test_gamma_input_validation_no_conversations(self, gamma_generator):
        """Test Gamma input validation with no conversations."""
        input_text = """
        # Executive Summary
        Analysis summary.
        
        # Analysis
        Data analysis.
        
        # Recommendations
        Action items.
        """
        analysis_results = {'conversations': [], 'category_results': {}}
        
        errors = gamma_generator._validate_gamma_input(input_text, analysis_results)
        assert len(errors) > 0
        assert any('No conversations provided' in error for error in errors)

    def test_gamma_input_validation_malformed_urls(self, gamma_generator):
        """Test Gamma input validation with malformed Intercom URLs."""
        input_text = """
        # Executive Summary
        Analysis summary with malformed Intercom URL: https://bad-intercom-url.com
        
        # Analysis
        Data analysis with proper Intercom URL: https://app.intercom.com/a/apps/123/inbox/inbox/conv_456
        
        # Recommendations
        Action items.
        """
        analysis_results = {'conversations': [{'id': 'conv_1'}], 'category_results': {}}
        
        errors = gamma_generator._validate_gamma_input(input_text, analysis_results)
        # Should not have URL validation errors since there is a proper Intercom URL
        assert not any('Intercom URLs may be malformed' in error for error in errors)

    def test_gamma_input_validation_too_short(self, gamma_generator):
        """Test Gamma input validation with input too short."""
        input_text = "Short text"
        analysis_results = {'conversations': [{'id': 'conv_1'}], 'category_results': {}}
        
        errors = gamma_generator._validate_gamma_input(input_text, analysis_results)
        assert len(errors) > 0
        assert any('too short' in error for error in errors)
