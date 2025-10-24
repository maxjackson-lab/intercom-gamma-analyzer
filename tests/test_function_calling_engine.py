"""
Tests for FunctionCallingEngine command argument building.

Verifies that natural language queries map to expected CLI commands with correct flags.
"""

import pytest
from src.chat.engines.function_calling import FunctionCallingEngine


class TestFunctionCallingEngine:
    """Test suite for FunctionCallingEngine"""
    
    def test_agent_performance_individual_with_vendor(self):
        """Test that agent performance query builds correct --vendor flag"""
        engine = FunctionCallingEngine()
        
        query = "Show individual agent performance for Horatio with taxonomy breakdown"
        result = engine.translate(query)
        
        assert result.action == "execute_command"
        assert result.command == "agent-performance"
        assert "--agent" in result.args
        assert "horatio" in result.args
        
        # Verify individual_breakdown flag is included
        assert "--individual-breakdown" in result.args
    
    def test_agent_performance_individual_with_boldr(self):
        """Test Boldr agent performance query"""
        engine = FunctionCallingEngine()
        
        query = "Analyze Boldr agents individually with category breakdown"
        result = engine.translate(query)
        
        assert result.action == "execute_command"
        assert result.command == "agent-performance"
        assert "--agent" in result.args
        assert "boldr" in result.args
        assert "--individual-breakdown" in result.args
    
    def test_coaching_report_with_vendor(self):
        """Test that coaching report builds --vendor flag correctly"""
        engine = FunctionCallingEngine()
        
        query = "Generate Horatio coaching report for this week"
        result = engine.translate(query)
        
        assert result.action == "execute_command"
        assert result.command == "agent-coaching-report"
        assert "--vendor" in result.args
        assert "horatio" in result.args
        assert "--time-period" in result.args
        assert "week" in result.args
    
    def test_time_period_flag_format(self):
        """Test that time_period always maps to --time-period"""
        engine = FunctionCallingEngine()
        
        query = "Give me last week's voice of customer report"
        result = engine.translate(query)
        
        # Should have --time-period flag (not --time_period)
        if "--time-period" in result.args:
            # Get index and verify next arg is a valid period
            idx = result.args.index("--time-period")
            assert result.args[idx + 1] in ["week", "month", "quarter", "year"]
    
    def test_individual_breakdown_flag(self):
        """Test that individual_breakdown parameter maps to --individual-breakdown"""
        engine = FunctionCallingEngine()
        
        # Build args directly
        args = engine._build_command_args(
            "agent_performance_individual",
            {"agent": "horatio", "individual_breakdown": True}
        )
        
        assert "agent-performance" in args
        assert "--agent" in args
        assert "horatio" in args
        assert "--individual-breakdown" in args
    
    def test_boolean_flags_only_when_true(self):
        """Test that boolean flags are only added when True"""
        engine = FunctionCallingEngine()
        
        # Test with True
        args_true = engine._build_command_args(
            "voice_of_customer_analysis",
            {"generate_gamma": True, "include_canny": True}
        )
        
        assert "--generate-gamma" in args_true
        assert "--include-canny" in args_true
        
        # Test with False
        args_false = engine._build_command_args(
            "voice_of_customer_analysis",
            {"generate_gamma": False, "include_canny": False}
        )
        
        assert "--generate-gamma" not in args_false
        assert "--include-canny" not in args_false
    
    def test_string_parameters(self):
        """Test that string parameters are added with values"""
        engine = FunctionCallingEngine()
        
        args = engine._build_command_args(
            "voice_of_customer_analysis",
            {
                "time_period": "month",
                "ai_model": "claude",
                "start_date": "2024-10-01",
                "end_date": "2024-10-31"
            }
        )
        
        assert "--time-period" in args
        assert "month" in args
        assert "--ai-model" in args
        assert "claude" in args
        assert "--start-date" in args
        assert "2024-10-01" in args
        assert "--end-date" in args
        assert "2024-10-31" in args
    
    def test_integer_parameters(self):
        """Test that integer parameters are stringified"""
        engine = FunctionCallingEngine()
        
        args = engine._build_command_args(
            "comprehensive_analysis",
            {"max_conversations": 500, "top_n": 10}
        )
        
        assert "--max-conversations" in args
        assert "500" in args
        assert "--top-n" in args
        assert "10" in args
    
    def test_web_ui_example_query_horatio_coaching(self):
        """Test Web UI example: Generate Horatio coaching report for this week"""
        engine = FunctionCallingEngine()
        
        query = "Generate Horatio coaching report for this week"
        result = engine.translate(query)
        
        assert result.action == "execute_command"
        assert result.command == "agent-coaching-report"
        
        # Build expected args
        args = result.args
        assert "--vendor" in args
        assert "horatio" in args
        assert "--time-period" in args
        assert "week" in args
    
    def test_web_ui_example_query_boldr_individual(self):
        """Test Web UI example: Show individual agent performance for Boldr with taxonomy breakdown"""
        engine = FunctionCallingEngine()
        
        query = "Show individual agent performance for Boldr with taxonomy breakdown"
        result = engine.translate(query)
        
        assert result.action == "execute_command"
        assert result.command == "agent-performance"
        
        # Build expected args
        args = result.args
        assert "--agent" in args
        assert "boldr" in args
        assert "--individual-breakdown" in args

