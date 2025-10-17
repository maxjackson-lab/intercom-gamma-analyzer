"""
Main Chat Interface

Orchestrates all chat components to provide a complete natural language
interface for the Intercom Analysis Tool.
"""

import logging
from typing import Dict, List, Optional, Any

from .hybrid_translator import HybridCommandTranslator
from .suggestion_engine import SuggestionEngine
from .custom_filter_builder import CustomFilterBuilder
from .terminal_ui import TerminalChatUI
from .security import InputValidator, CommandWhitelist, HITLController
from ..config.settings import Settings


class ChatInterface:
    """
    Main chat interface that orchestrates all components.
    
    Provides a complete natural language interface with:
    - Multi-engine command translation
    - Security validation and approval workflows
    - Custom filter building
    - Feature suggestions
    - Rich terminal UI
    """
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Initialize core components
        self.translator = HybridCommandTranslator(settings)
        self.suggestion_engine = SuggestionEngine()
        self.filter_builder = CustomFilterBuilder()
        
        # Initialize security components
        self.input_validator = InputValidator()
        self.command_whitelist = CommandWhitelist()
        self.hitl_controller = HITLController()
        
        # Initialize UI
        self.terminal_ui = TerminalChatUI(self.translator, self.suggestion_engine)
        
        self.logger.info("ChatInterface initialized with all components")
    
    def start_chat(self):
        """Start the interactive chat interface."""
        try:
            self.logger.info("Starting chat interface")
            self.terminal_ui.start()
        except Exception as e:
            self.logger.error(f"Error starting chat interface: {e}")
            raise
    
    def process_query(self, query: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Process a single query and return results.
        
        Args:
            query: User's natural language input
            context: Additional context for processing
            
        Returns:
            Dictionary with processing results
        """
        try:
            # Step 1: Input validation
            validation_result = self.input_validator.validate(query)
            if not validation_result.is_valid:
                return {
                    "success": False,
                    "error": "Input validation failed",
                    "details": validation_result.explanation,
                    "threat_level": validation_result.threat_level.value
                }
            
            # Step 2: Command translation
            translation_result = self.translator.translate(query, context)
            
            # Step 3: Command validation (if it's a command)
            if translation_result.translation.action.value == "EXECUTE_COMMAND":
                command_parts = [translation_result.translation.command] + translation_result.translation.args
                command_validation = self.command_whitelist.validate_command(command_parts)
                
                if not command_validation.is_allowed:
                    return {
                        "success": False,
                        "error": "Command not allowed",
                        "details": command_validation.explanation,
                        "warnings": command_validation.warnings
                    }
                
                # Step 4: Check if human approval is required
                # Convert risk_level to risk_score (0-10 scale)
                risk_score_map = {
                    "safe": 0.0,
                    "low": 2.0,
                    "medium": 4.0,
                    "high": 6.0,
                    "critical": 8.0
                }
                risk_score = risk_score_map.get(command_validation.risk_level.value, 5.0)
                
                requires_approval = self.hitl_controller.should_require_approval(
                    command_parts, 
                    risk_score, 
                    command_validation.warnings
                )
                
                return {
                    "success": True,
                    "translation": translation_result,
                    "command_validation": command_validation,
                    "requires_approval": requires_approval,
                    "security_checks": {
                        "input_validated": True,
                        "command_whitelisted": True,
                        "approval_required": requires_approval
                    }
                }
            
            else:
                # For clarification requests, generate suggestions
                suggestions = self.suggestion_engine.generate_suggestions(query)
                
                return {
                    "success": True,
                    "translation": translation_result,
                    "suggestions": suggestions,
                    "security_checks": {
                        "input_validated": True,
                        "command_whitelisted": False,
                        "approval_required": False
                    }
                }
        
        except Exception as e:
            self.logger.error(f"Error processing query: {e}")
            return {
                "success": False,
                "error": "Processing failed",
                "details": str(e)
            }
    
    def build_custom_filters(self, query: str, context: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """
        Build custom filters from natural language query.
        
        Args:
            query: Natural language description of filters
            context: Additional context for filter building
            
        Returns:
            List of filter specifications
        """
        try:
            filters = self.filter_builder.build_filters(query, context)
            return [filter_spec.__dict__ for filter_spec in filters]
        except Exception as e:
            self.logger.error(f"Error building custom filters: {e}")
            return []
    
    def get_available_commands(self) -> List[str]:
        """Get list of available commands."""
        return self.translator.get_available_commands()
    
    def get_supported_filters(self) -> Dict[str, List[str]]:
        """Get supported filter types and values."""
        return self.filter_builder.get_supported_filters()
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get comprehensive performance statistics."""
        return {
            "translator_stats": self.translator.get_performance_stats(),
            "ui_stats": self.terminal_ui.get_session_stats(),
            "security_stats": {
                "input_validations": "N/A - InputValidator stats not implemented",
                "command_validations": "N/A - CommandWhitelist stats not implemented", 
                "approval_requests": "N/A - HITLController stats not implemented"
            }
        }
    
    def reset_stats(self):
        """Reset all performance statistics."""
        self.translator.reset_stats()
        self.terminal_ui.stats = {
            "total_queries": 0,
            "successful_translations": 0,
            "failed_translations": 0,
            "commands_executed": 0,
            "suggestions_shown": 0
        }
        self.logger.info("All statistics reset")
    
    def get_help_text(self) -> str:
        """Get comprehensive help text."""
        return self.translator.get_help_text()
    
    def get_filter_examples(self) -> List[str]:
        """Get example filter queries."""
        return self.filter_builder.get_filter_examples()
    
    def get_suggestion_examples(self) -> List[str]:
        """Get example suggestion queries."""
        return [
            "I want to export data to CSV",
            "Can you send me notifications when there are issues?",
            "I need to compare reports from different time periods",
            "Can you integrate with our Slack workspace?",
            "I want to create custom dashboards",
            "Can you analyze sentiment trends over time?"
        ]
    
    def configure_security(self, 
                          auto_approve_safe: bool = False,
                          approval_timeout: int = 300,
                          strict_validation: bool = True):
        """
        Configure security settings.
        
        Args:
            auto_approve_safe: Auto-approve safe commands
            approval_timeout: Timeout for approval requests in seconds
            strict_validation: Use strict input validation
        """
        self.terminal_ui.set_auto_approve_safe_commands(auto_approve_safe)
        self.hitl_controller.approval_timeout_seconds = approval_timeout
        
        if strict_validation:
            self.input_validator.strict_mode = True
        
        self.logger.info(f"Security configured: auto_approve_safe={auto_approve_safe}, "
                        f"approval_timeout={approval_timeout}, strict_validation={strict_validation}")
    
    def configure_ui(self, 
                    show_help_on_start: bool = True,
                    show_performance_metrics: bool = True):
        """
        Configure UI settings.
        
        Args:
            show_help_on_start: Show help message on startup
            show_performance_metrics: Show performance metrics
        """
        self.terminal_ui.show_help_on_start = show_help_on_start
        self.terminal_ui.set_show_performance_metrics(show_performance_metrics)
        
        self.logger.info(f"UI configured: show_help_on_start={show_help_on_start}, "
                        f"show_performance_metrics={show_performance_metrics}")
    
    def test_components(self) -> Dict[str, bool]:
        """
        Test all components to ensure they're working correctly.
        
        Returns:
            Dictionary with test results for each component
        """
        results = {}
        
        try:
            # Test translator
            test_result = self.translator.translate("test query")
            results["translator"] = test_result is not None
            
            # Test suggestion engine
            suggestions = self.suggestion_engine.generate_suggestions("test query")
            results["suggestion_engine"] = isinstance(suggestions, list)
            
            # Test filter builder
            filters = self.filter_builder.build_filters("test query")
            results["filter_builder"] = isinstance(filters, list)
            
            # Test input validator
            validation = self.input_validator.validate("test query")
            results["input_validator"] = validation is not None
            
            # Test command whitelist
            command_validation = self.command_whitelist.validate_command(["test"])
            results["command_whitelist"] = command_validation is not None
            
            # Test HITL controller
            approval_required = self.hitl_controller.should_require_approval(command_validation)
            results["hitl_controller"] = isinstance(approval_required, bool)
            
        except Exception as e:
            self.logger.error(f"Component test failed: {e}")
            results["error"] = str(e)
        
        return results
