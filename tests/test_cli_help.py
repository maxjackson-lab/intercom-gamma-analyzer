"""
Unit tests for CLI help system.
"""

import pytest
from unittest.mock import patch, MagicMock
from io import StringIO

from utils.cli_help import CLIHelpSystem


class TestCLIHelpSystem:
    """Test cases for CLI help system."""
    
    def test_initialization(self):
        """Test CLI help system initialization."""
        help_system = CLIHelpSystem()
        
        assert help_system.commands is not None
        assert len(help_system.commands) > 0
        
        # Check that all expected command categories exist
        categories = set(cmd['category'] for cmd in help_system.commands.values())
        expected_categories = {'Primary', 'Secondary', 'Advanced', 'Utility'}
        
        for category in expected_categories:
            assert category in categories
    
    def test_primary_commands_exist(self):
        """Test that primary commands exist."""
        help_system = CLIHelpSystem()
        
        primary_commands = [
            'tech-analysis',
            'find-macros', 
            'fin-escalations',
            'analyze-agent'
        ]
        
        for command in primary_commands:
            assert command in help_system.commands
            assert help_system.commands[command]['category'] == 'Primary'
    
    def test_secondary_commands_exist(self):
        """Test that secondary commands exist."""
        help_system = CLIHelpSystem()
        
        secondary_commands = [
            'analyze-category',
            'analyze-all-categories',
            'analyze-subcategory'
        ]
        
        for command in secondary_commands:
            assert command in help_system.commands
            assert help_system.commands[command]['category'] == 'Secondary'
    
    def test_advanced_commands_exist(self):
        """Test that advanced commands exist."""
        help_system = CLIHelpSystem()
        
        advanced_commands = [
            'synthesize',
            'analyze-custom-tag',
            'analyze-escalations',
            'analyze-pattern'
        ]
        
        for command in advanced_commands:
            assert command in help_system.commands
            assert help_system.commands[command]['category'] == 'Advanced'
    
    def test_utility_commands_exist(self):
        """Test that utility commands exist."""
        help_system = CLIHelpSystem()
        
        utility_commands = [
            'help',
            'interactive',
            'list-commands',
            'examples',
            'show-categories',
            'show-tags',
            'show-agents',
            'sync-taxonomy'
        ]
        
        for command in utility_commands:
            assert command in help_system.commands
            assert help_system.commands[command]['category'] == 'Utility'
    
    def test_show_main_help(self, capsys):
        """Test main help display."""
        help_system = CLIHelpSystem()
        
        # This would normally print to console, but we can't easily test that
        # Instead, we'll test that the method doesn't raise exceptions
        try:
            help_system.show_main_help()
        except Exception as e:
            pytest.fail(f"show_main_help raised an exception: {e}")
    
    def test_show_command_help_existing(self, capsys):
        """Test command help for existing command."""
        help_system = CLIHelpSystem()
        
        # Test with existing command
        try:
            help_system.show_command_help('tech-analysis')
        except Exception as e:
            pytest.fail(f"show_command_help raised an exception: {e}")
    
    def test_show_command_help_nonexistent(self, capsys):
        """Test command help for nonexistent command."""
        help_system = CLIHelpSystem()
        
        # Test with nonexistent command
        try:
            help_system.show_command_help('nonexistent-command')
        except Exception as e:
            pytest.fail(f"show_command_help raised an exception: {e}")
    
    def test_show_examples(self, capsys):
        """Test examples display."""
        help_system = CLIHelpSystem()
        
        try:
            help_system.show_examples()
        except Exception as e:
            pytest.fail(f"show_examples raised an exception: {e}")
    
    def test_show_categories(self, capsys):
        """Test categories display."""
        help_system = CLIHelpSystem()
        
        try:
            help_system.show_categories()
        except Exception as e:
            pytest.fail(f"show_categories raised an exception: {e}")
    
    def test_interactive_mode(self, capsys):
        """Test interactive mode (without actual interaction)."""
        help_system = CLIHelpSystem()
        
        # Mock the interactive methods to avoid actual user input
        with patch.object(help_system, '_interactive_technical_analysis') as mock_tech, \
             patch.object(help_system, '_interactive_category_analysis') as mock_cat, \
             patch.object(help_system, '_interactive_fin_analysis') as mock_fin, \
             patch.object(help_system, '_interactive_agent_analysis') as mock_agent, \
             patch.object(help_system, '_interactive_pattern_search') as mock_pattern, \
             patch.object(help_system, '_interactive_complete_analysis') as mock_complete:
            
            # Test that interactive mode doesn't crash
            try:
                help_system.interactive_mode()
            except Exception as e:
                pytest.fail(f"interactive_mode raised an exception: {e}")
    
    def test_interactive_technical_analysis(self, capsys):
        """Test interactive technical analysis setup."""
        help_system = CLIHelpSystem()
        
        try:
            help_system._interactive_technical_analysis()
        except Exception as e:
            pytest.fail(f"_interactive_technical_analysis raised an exception: {e}")
    
    def test_interactive_category_analysis(self, capsys):
        """Test interactive category analysis setup."""
        help_system = CLIHelpSystem()
        
        try:
            help_system._interactive_category_analysis()
        except Exception as e:
            pytest.fail(f"_interactive_category_analysis raised an exception: {e}")
    
    def test_interactive_fin_analysis(self, capsys):
        """Test interactive Fin analysis setup."""
        help_system = CLIHelpSystem()
        
        try:
            help_system._interactive_fin_analysis()
        except Exception as e:
            pytest.fail(f"_interactive_fin_analysis raised an exception: {e}")
    
    def test_interactive_agent_analysis(self, capsys):
        """Test interactive agent analysis setup."""
        help_system = CLIHelpSystem()
        
        try:
            help_system._interactive_agent_analysis()
        except Exception as e:
            pytest.fail(f"_interactive_agent_analysis raised an exception: {e}")
    
    def test_interactive_pattern_search(self, capsys):
        """Test interactive pattern search setup."""
        help_system = CLIHelpSystem()
        
        try:
            help_system._interactive_pattern_search()
        except Exception as e:
            pytest.fail(f"_interactive_pattern_search raised an exception: {e}")
    
    def test_interactive_complete_analysis(self, capsys):
        """Test interactive complete analysis setup."""
        help_system = CLIHelpSystem()
        
        try:
            help_system._interactive_complete_analysis()
        except Exception as e:
            pytest.fail(f"_interactive_complete_analysis raised an exception: {e}")
    
    def test_command_examples_exist(self):
        """Test that command examples exist for key commands."""
        help_system = CLIHelpSystem()
        
        # Check that examples exist for important commands
        commands_with_examples = [
            'tech-analysis',
            'find-macros',
            'analyze-category',
            'synthesize'
        ]
        
        for command in commands_with_examples:
            assert command in help_system.commands
            # The _show_command_examples method should handle these
            try:
                help_system._show_command_examples(command)
            except Exception as e:
                pytest.fail(f"_show_command_examples for {command} raised an exception: {e}")
    
    def test_command_structure(self):
        """Test that all commands have required structure."""
        help_system = CLIHelpSystem()
        
        required_fields = ['category', 'description', 'usage', 'options']
        
        for command_name, command_info in help_system.commands.items():
            for field in required_fields:
                assert field in command_info, f"Command {command_name} missing field {field}"
                assert command_info[field] is not None, f"Command {command_name} has None value for {field}"
    
    def test_usage_format(self):
        """Test that usage strings have correct format."""
        help_system = CLIHelpSystem()
        
        for command_name, command_info in help_system.commands.items():
            usage = command_info['usage']
            assert usage.startswith('python -m src.main'), f"Command {command_name} usage doesn't start correctly"
            assert command_name in usage, f"Command {command_name} not in its own usage string"
    
    def test_options_format(self):
        """Test that options are properly formatted."""
        help_system = CLIHelpSystem()
        
        for command_name, command_info in help_system.commands.items():
            options = command_info['options']
            assert isinstance(options, list), f"Command {command_name} options should be a list"
            
            for option in options:
                assert isinstance(option, str), f"Command {command_name} option should be a string"
                assert option.startswith('--'), f"Command {command_name} option {option} should start with --"
    
    def test_category_grouping(self):
        """Test that commands are properly grouped by category."""
        help_system = CLIHelpSystem()
        
        categories = {}
        for command_name, command_info in help_system.commands.items():
            category = command_info['category']
            if category not in categories:
                categories[category] = []
            categories[category].append(command_name)
        
        # Check that we have commands in each category
        expected_categories = ['Primary', 'Secondary', 'Advanced', 'Utility']
        for category in expected_categories:
            assert category in categories, f"Category {category} has no commands"
            assert len(categories[category]) > 0, f"Category {category} is empty"
    
    def test_help_system_consistency(self):
        """Test that help system is internally consistent."""
        help_system = CLIHelpSystem()
        
        # Check that all commands referenced in examples exist
        for command_name, command_info in help_system.commands.items():
            if 'examples' in command_info:
                # This would need to be implemented if we add examples to command info
                pass
        
        # Check that categories are consistent
        valid_categories = {'Primary', 'Secondary', 'Advanced', 'Utility'}
        for command_name, command_info in help_system.commands.items():
            assert command_info['category'] in valid_categories, f"Command {command_name} has invalid category"






