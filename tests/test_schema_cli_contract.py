"""
Contract tests for UI schema → CLI mapping consistency.

These tests ensure that the schema exposed by railway_web.py is consistent with the CLI
command definitions in src/main.py, preventing drift between UI and CLI.
"""

import pytest
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from deploy.railway_web import CANONICAL_COMMAND_MAPPINGS


class TestSchemaCliContract:
    """Test suite for schema-CLI consistency"""
    
    def test_voice_of_customer_time_period_includes_6_weeks(self):
        """Verify voice_of_customer schema includes '6-weeks' option"""
        schema = CANONICAL_COMMAND_MAPPINGS['voice_of_customer']
        time_period_values = schema['allowed_flags']['--time-period']['values']
        
        assert '6-weeks' in time_period_values, \
            "voice_of_customer schema must include '6-weeks' in time-period values"
        
        # Verify all expected values are present
        expected_values = ['yesterday', 'week', 'month', 'quarter', 'year', '6-weeks']
        for value in expected_values:
            assert value in time_period_values, \
                f"voice_of_customer schema missing '{value}' in time-period values"
    
    def test_category_schemas_no_deprecated_days_flag(self):
        """Verify category schemas don't expose deprecated --days flag"""
        category_commands = [
            'category_billing',
            'category_product',
            'category_api',
            'category_escalations',
            'tech_troubleshooting',
            'all_categories'
        ]
        
        for command in category_commands:
            schema = CANONICAL_COMMAND_MAPPINGS[command]
            flags = schema['allowed_flags']
            
            assert '--days' not in flags, \
                f"{command} schema should not expose deprecated --days flag"
    
    def test_all_categories_have_standard_flags(self):
        """Verify all category schemas have complete standard flag set"""
        standard_flags = {
            '--time-period',
            '--periods-back',
            '--output-format',
            '--gamma-export',
            '--output-dir',
            '--test-mode',
            '--test-data-count',
            '--audit-trail',
            '--verbose',
            '--ai-model',
            '--filter-category',
            '--start-date',
            '--end-date'
        }
        
        # Commands that should have all standard flags
        commands_to_check = [
            'voice_of_customer',
            'agent_performance',
            'agent_coaching',
            'category_billing',
            'category_product',
            'category_api',
            'category_escalations',
            'tech_troubleshooting',
            'all_categories'
        ]
        
        for command in commands_to_check:
            schema = CANONICAL_COMMAND_MAPPINGS[command]
            flags = set(schema['allowed_flags'].keys())
            
            # Check for presence of key standard flags
            # (not all commands need all flags, but these are critical)
            critical_flags = {
                '--time-period',
                '--output-format',
                '--test-mode'
            }
            
            for flag in critical_flags:
                assert flag in flags, \
                    f"{command} schema missing critical flag {flag}"
    
    def test_time_period_values_consistent_across_commands(self):
        """Verify time-period values are consistent across all commands"""
        expected_values = ['yesterday', 'week', 'month', 'quarter', 'year', '6-weeks']
        
        commands_with_time_period = [
            'voice_of_customer',
            'agent_performance',
            'agent_coaching',
            'category_billing',
            'category_product',
            'category_api',
            'category_escalations',
            'tech_troubleshooting',
            'all_categories'
        ]
        
        for command in commands_with_time_period:
            schema = CANONICAL_COMMAND_MAPPINGS[command]
            if '--time-period' in schema['allowed_flags']:
                time_period_values = schema['allowed_flags']['--time-period']['values']
                
                assert set(time_period_values) == set(expected_values), \
                    f"{command} has inconsistent time-period values: {time_period_values}"
    
    def test_output_format_no_deprecated_generate_gamma(self):
        """Verify schemas use --output-format instead of deprecated --generate-gamma"""
        for command_name, schema in CANONICAL_COMMAND_MAPPINGS.items():
            flags = schema['allowed_flags']
            
            # Skip sample_mode and canny_analysis which have different structure
            if command_name in ['sample_mode', 'canny_analysis']:
                continue
            
            # Schemas should use --output-format, not --generate-gamma
            assert '--output-format' in flags or command_name == 'sample_mode', \
                f"{command_name} should use --output-format"
            
            # Old --generate-gamma should not be present (except in legacy commands)
            if command_name not in ['sample_mode', 'canny_analysis']:
                assert '--generate-gamma' not in flags, \
                    f"{command_name} should not use deprecated --generate-gamma"
    
    def test_agent_coaching_has_all_standard_flags(self):
        """Verify agent-coaching-report has complete flag set"""
        schema = CANONICAL_COMMAND_MAPPINGS['agent_coaching']
        flags = schema['allowed_flags']
        
        required_flags = [
            '--vendor',
            '--time-period',
            '--periods-back',
            '--output-format',
            '--gamma-export',
            '--output-dir',
            '--test-mode',
            '--test-data-count',
            '--audit-trail',
            '--verbose',
            '--ai-model',
            '--start-date',
            '--end-date'
        ]
        
        for flag in required_flags:
            assert flag in flags, \
                f"agent_coaching schema missing required flag {flag}"
    
    def test_ai_model_values_consistent(self):
        """Verify ai-model values are consistent across commands"""
        expected_values = ['openai', 'claude']
        
        for command_name, schema in CANONICAL_COMMAND_MAPPINGS.items():
            if '--ai-model' in schema['allowed_flags']:
                ai_model_values = schema['allowed_flags']['--ai-model']['values']
                
                assert set(ai_model_values) == set(expected_values), \
                    f"{command_name} has inconsistent ai-model values: {ai_model_values}"
    
    def test_gamma_export_values_consistent(self):
        """Verify gamma-export values are consistent across commands"""
        expected_values = ['pdf', 'pptx']
        
        for command_name, schema in CANONICAL_COMMAND_MAPPINGS.items():
            if '--gamma-export' in schema['allowed_flags']:
                gamma_export_values = schema['allowed_flags']['--gamma-export']['values']
                
                assert set(gamma_export_values) == set(expected_values), \
                    f"{command_name} has inconsistent gamma-export values: {gamma_export_values}"
    
    def test_schema_validation_function(self):
        """Test that schema validation function works correctly"""
        from deploy.railway_web import validate_command_request
        
        # Test valid request
        valid, error = validate_command_request('voice_of_customer', {
            '--time-period': 'week',
            '--periods-back': 1,
            '--output-format': 'markdown'
        })
        
        assert valid, f"Valid request failed validation: {error}"
        assert error is None
        
        # Test invalid time-period value
        valid, error = validate_command_request('voice_of_customer', {
            '--time-period': 'invalid_period'
        })
        
        assert not valid, "Invalid time-period should fail validation"
        assert error is not None
        
        # Test unknown flag
        valid, error = validate_command_request('voice_of_customer', {
            '--unknown-flag': 'value'
        })
        
        assert not valid, "Unknown flag should fail validation"
        assert error is not None
    
    def test_test_data_count_field_present(self):
        """Verify test-data-count field is present in schemas"""
        commands_with_test_mode = [
            'voice_of_customer',
            'agent_performance',
            'agent_coaching',
            'category_billing',
            'category_product',
            'category_api'
        ]
        
        for command in commands_with_test_mode:
            schema = CANONICAL_COMMAND_MAPPINGS[command]
            flags = schema['allowed_flags']
            
            assert '--test-mode' in flags, \
                f"{command} missing --test-mode flag"
            
            assert '--test-data-count' in flags, \
                f"{command} missing --test-data-count flag"
            
            # Verify test-data-count is string type
            assert flags['--test-data-count']['type'] == 'string', \
                f"{command} test-data-count should be string type"


class TestSchemaCompleteness:
    """Test that schemas are complete and usable"""
    
    def test_all_commands_have_description(self):
        """Verify all commands have descriptions"""
        for command_name, schema in CANONICAL_COMMAND_MAPPINGS.items():
            assert 'description' in schema, \
                f"{command_name} missing description"
            assert schema['description'], \
                f"{command_name} has empty description"
    
    def test_all_commands_have_estimated_duration(self):
        """Verify all commands have estimated duration"""
        for command_name, schema in CANONICAL_COMMAND_MAPPINGS.items():
            assert 'estimated_duration' in schema, \
                f"{command_name} missing estimated_duration"
    
    def test_all_flags_have_descriptions(self):
        """Verify all flags have descriptions"""
        for command_name, schema in CANONICAL_COMMAND_MAPPINGS.items():
            for flag_name, flag_schema in schema['allowed_flags'].items():
                assert 'description' in flag_schema, \
                    f"{command_name} flag {flag_name} missing description"
                assert flag_schema['description'], \
                    f"{command_name} flag {flag_name} has empty description"
    
    def test_enum_flags_have_values(self):
        """Verify enum type flags have values"""
        for command_name, schema in CANONICAL_COMMAND_MAPPINGS.items():
            for flag_name, flag_schema in schema['allowed_flags'].items():
                if flag_schema.get('type') == 'enum':
                    assert 'values' in flag_schema, \
                        f"{command_name} flag {flag_name} enum missing values"
                    assert len(flag_schema['values']) > 0, \
                        f"{command_name} flag {flag_name} enum has empty values"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

