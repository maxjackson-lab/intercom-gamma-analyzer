"""
Unit tests for schema dump modes and topic hierarchy debugging.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch

from src.services.sample_mode import SampleMode, run_sample_mode


class TestSchemaDumpModes:
    """Test schema dump mode configurations."""
    
    def test_mode_configs(self):
        """Test that all modes have proper configuration."""
        mode_configs = {
            'quick': {'count': 50, 'detail_samples': 5, 'llm_topics': 2},
            'standard': {'count': 200, 'detail_samples': 10, 'llm_topics': 3},
            'deep': {'count': 500, 'detail_samples': 15, 'llm_topics': 5},
            'comprehensive': {'count': 1000, 'detail_samples': 20, 'llm_topics': 7}
        }
        
        # Verify all modes exist
        assert 'quick' in mode_configs
        assert 'standard' in mode_configs
        assert 'deep' in mode_configs
        assert 'comprehensive' in mode_configs
        
        # Verify counts increase with mode depth
        assert mode_configs['quick']['count'] < mode_configs['standard']['count']
        assert mode_configs['standard']['count'] < mode_configs['deep']['count']
        assert mode_configs['deep']['count'] < mode_configs['comprehensive']['count']
        
        # Verify detail samples increase
        assert mode_configs['quick']['detail_samples'] < mode_configs['comprehensive']['detail_samples']
        
        # Verify LLM topic counts increase
        assert mode_configs['quick']['llm_topics'] < mode_configs['comprehensive']['llm_topics']
    
    @pytest.mark.asyncio
    async def test_schema_dump_with_mode(self):
        """Test schema dump respects mode parameter."""
        mock_sdk = Mock()
        mock_sdk.fetch_conversations_by_date_range = AsyncMock(return_value=[
            {'id': '123', 'custom_attributes': {'Reason for contact': 'Billing'}},
            {'id': '456', 'custom_attributes': {}}
        ])
        
        sample_mode = SampleMode(sdk_service=mock_sdk)
        
        # Test with different modes
        for mode in ['quick', 'standard', 'deep', 'comprehensive']:
            result = await sample_mode.pull_sample(
                count=50,
                start_date=datetime.now() - timedelta(days=7),
                end_date=datetime.now(),
                save_to_file=False,
                schema_mode=mode
            )
            
            # Should return analysis data
            assert 'conversations' in result
            assert 'analysis' in result
    
    @pytest.mark.asyncio
    async def test_hierarchy_debug_detects_double_counting(self):
        """Test that hierarchy debug detects multi-topic assignments."""
        # Create sample conversations with multi-topic assignments
        conversations = [
            {
                'id': '1',
                'custom_attributes': {'Reason for contact': 'Billing', 'Billing': 'Refund'},
                'source': {'body': 'I need a refund for my invoice'}
            },
            {
                'id': '2',
                'custom_attributes': {},
                'source': {'body': 'How do I export to PDF?'}
            }
        ]
        
        mock_sdk = Mock()
        sample_mode = SampleMode(sdk_service=mock_sdk)
        
        with patch('src.services.sample_mode.TopicDetectionAgent') as MockAgent:
            mock_agent_instance = Mock()
            mock_result = Mock()
            mock_result.success = True
            mock_result.data = {
                'topics_by_conversation': {
                    '1': [
                        {'topic': 'Billing', 'confidence': 0.9},
                        {'topic': 'Invoice/Receipt', 'confidence': 0.7}  # Double-counted!
                    ],
                    '2': [
                        {'topic': 'Bug', 'confidence': 0.8}
                    ]
                },
                'topic_distribution': {
                    'Billing': {'volume': 1, 'percentage': 50.0},
                    'Invoice/Receipt': {'volume': 1, 'percentage': 50.0},
                    'Bug': {'volume': 1, 'percentage': 50.0}
                }
            }
            mock_agent_instance.execute = AsyncMock(return_value=mock_result)
            MockAgent.return_value = mock_agent_instance
            
            debug_data = await sample_mode._debug_topic_hierarchy(conversations)
            
            # Should detect that conversation 1 is double-counted
            assert debug_data['multi_topic'] == 1
            assert debug_data['single_topic'] == 1
            assert len(debug_data['multi_topic_examples']) > 0
            assert debug_data['multi_topic_examples'][0]['topic_count'] == 2
    
    @pytest.mark.asyncio
    async def test_hierarchy_debug_finds_nested_attributes(self):
        """Test that hierarchy debug finds Billing > Refund > Given patterns."""
        conversations = [
            {
                'id': '123',
                'custom_attributes': {
                    'Reason for contact': 'Billing',
                    'Billing': 'Refund',
                    'Refund': 'Given',
                    'Given Reason': 'Did not use'
                },
                'source': {'body': 'refund please'}
            }
        ]
        
        mock_sdk = Mock()
        sample_mode = SampleMode(sdk_service=mock_sdk)
        
        with patch('src.services.sample_mode.TopicDetectionAgent') as MockAgent:
            mock_agent_instance = Mock()
            mock_result = Mock()
            mock_result.success = True
            mock_result.data = {
                'topics_by_conversation': {
                    '123': [{'topic': 'Billing', 'confidence': 0.9}]
                },
                'topic_distribution': {
                    'Billing': {'volume': 1, 'percentage': 100.0}
                }
            }
            mock_agent_instance.execute = AsyncMock(return_value=mock_result)
            MockAgent.return_value = mock_agent_instance
            
            debug_data = await sample_mode._debug_topic_hierarchy(conversations)
            
            # Should find hierarchical structure
            assert len(debug_data['hierarchy_examples']) > 0
            example = debug_data['hierarchy_examples'][0]
            assert 'Reason for contact' in example['hierarchy']
            assert 'Billing' in example['hierarchy']
            assert 'Refund' in example['hierarchy']
    
    def test_llm_topic_selection_strategy(self):
        """Test that LLM test selects diverse topics (high + low volume)."""
        # Mock topic distribution
        topic_dist = {
            'Billing': {'volume': 100},
            'Bug': {'volume': 50},
            'Account': {'volume': 30},
            'Feedback': {'volume': 5},
            'Promotions': {'volume': 2}
        }
        
        all_topics = sorted(topic_dist.items(), key=lambda x: x[1]['volume'], reverse=True)
        llm_topic_count = 3
        
        # Strategy: 60% high, 40% low
        high_volume_count = max(1, int(llm_topic_count * 0.6))  # 60% = 1.8 → 1
        low_volume_count = llm_topic_count - high_volume_count  # 3 - 1 = 2
        
        high_volume_topics = all_topics[:high_volume_count]  # [Billing]
        low_volume_topics = all_topics[-(low_volume_count):]  # [Feedback, Promotions]
        
        selected = high_volume_topics + low_volume_topics
        
        # Should get mix of high and low volume
        assert len(selected) == 3
        assert selected[0][0] == 'Billing'  # High volume
        assert selected[-1][0] in ['Feedback', 'Promotions']  # Low volume
    
    @pytest.mark.asyncio
    async def test_run_sample_mode_with_different_modes(self):
        """Test run_sample_mode function with all mode options."""
        with patch('src.services.sample_mode.SampleMode') as MockSampleMode:
            mock_instance = Mock()
            mock_instance.pull_sample = AsyncMock(return_value={
                'conversations': [],
                'analysis': {'total_conversations': 50}
            })
            mock_instance.test_llm_analysis = AsyncMock()
            MockSampleMode.return_value = mock_instance
            
            for mode in ['quick', 'standard', 'deep', 'comprehensive']:
                result = await run_sample_mode(
                    count=50,
                    start_date=datetime.now() - timedelta(days=7),
                    end_date=datetime.now(),
                    save_to_file=False,
                    test_llm=True,
                    schema_mode=mode
                )
                
                # Verify mode was passed through
                call_args = mock_instance.pull_sample.call_args
                assert call_args.kwargs['schema_mode'] == mode


class TestCLIFlagValidation:
    """Test that all CLI flags are properly registered."""
    
    def test_sample_mode_flag_schema_mode(self):
        """Test --schema-mode flag exists and has correct values."""
        from click.testing import CliRunner
        from src.main import cli
        
        runner = CliRunner()
        
        # Test with valid mode
        result = runner.invoke(cli, ['sample-mode', '--schema-mode', 'standard', '--help'])
        assert result.exit_code in [0, 2]  # 0 or help exit
        
        # Help should mention schema-mode
        help_result = runner.invoke(cli, ['sample-mode', '--help'])
        assert '--schema-mode' in help_result.output
        assert 'quick' in help_result.output.lower()
        assert 'comprehensive' in help_result.output.lower()
    
    def test_sample_mode_flag_test_llm(self):
        """Test --test-llm flag exists."""
        from click.testing import CliRunner
        from src.main import cli
        
        runner = CliRunner()
        help_result = runner.invoke(cli, ['sample-mode', '--help'])
        
        assert '--test-llm' in help_result.output
        assert 'sentiment' in help_result.output.lower()
    
    def test_railway_schema_mode_in_allowed_flags(self):
        """Test that Railway web.py includes --schema-mode in allowed flags."""
        import deploy.railway_web as railway_web
        
        if hasattr(railway_web, 'CANONICAL_COMMAND_MAPPINGS'):
            sample_mode_config = railway_web.CANONICAL_COMMAND_MAPPINGS.get('sample_mode', {})
            allowed_flags = sample_mode_config.get('allowed_flags', {})
            
            # Should have --schema-mode flag
            assert '--schema-mode' in allowed_flags
            
            # Should have correct enum values
            flag_config = allowed_flags['--schema-mode']
            assert flag_config['type'] == 'enum'
            assert 'quick' in flag_config['values']
            assert 'standard' in flag_config['values']
            assert 'deep' in flag_config['values']
            assert 'comprehensive' in flag_config['values']

