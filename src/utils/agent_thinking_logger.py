"""
Agent Thinking Logger

Captures LLM prompts, responses, and agent reasoning for debugging and prompt tuning.

Purpose:
- Show what prompt each agent sends
- Show what LLM responds
- Show agent's reasoning process
- Help tune prompts by seeing what works/doesn't work

Usage:
    from src.utils.agent_thinking_logger import AgentThinkingLogger
    
    # In agent __init__:
    self.thinking_logger = AgentThinkingLogger.get_logger()
    
    # Before LLM call:
    self.thinking_logger.log_prompt(agent_name, prompt, context)
    
    # After LLM call:
    self.thinking_logger.log_response(agent_name, response, tokens_used)
    
    # Agent reasoning:
    self.thinking_logger.log_reasoning(agent_name, decision, rationale)
"""

import logging
import os
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

logger = logging.getLogger(__name__)


class AgentThinkingLogger:
    """
    Singleton logger for capturing agent LLM interactions and reasoning.
    
    When enabled (via --show-agent-thinking flag), logs:
    - Prompts sent to LLMs
    - Responses received
    - Agent reasoning/decisions
    - Validation checks
    
    Also exports structured JSON for observability/analysis.
    """
    
    _instance = None
    _enabled = False
    _console = Console()
    _log_file = None
    _events = []  # Structured events for JSON export
    
    @classmethod
    def get_logger(cls):
        """Get singleton instance"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    @classmethod
    def enable(cls, output_file: Optional[Path] = None):
        """Enable agent thinking logging"""
        cls._enabled = True
        cls._log_file = output_file
        cls._events = []  # Reset events list
        
        if output_file:
            # Create file and write header with PACIFIC TIME
            from src.utils.timezone_utils import get_pacific_time
            pacific_now = get_pacific_time()
            
            output_file.parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, 'w') as f:
                f.write("="*80 + "\n")
                f.write("AGENT THINKING LOG\n")
                f.write(f"Generated: {pacific_now.strftime('%b %d, %Y at %I:%M%p Pacific')}\n")
                f.write("="*80 + "\n\n")
        
        cls._console.print("\n[bold green]🧠 Agent Thinking Logger: ENABLED[/bold green]")
        cls._console.print(f"[dim]Logging to: {output_file}[/dim]\n")
    
    @classmethod
    def disable(cls):
        """Disable agent thinking logging"""
        cls._enabled = False
    
    @classmethod
    def is_enabled(cls):
        """Check if logging is enabled"""
        return cls._enabled
    
    def log_prompt(
        self, 
        agent_name: str, 
        prompt: str, 
        context: Optional[Dict[str, Any]] = None
    ):
        """Log prompt sent to LLM"""
        if not self._enabled:
            return
        
        # Use Pacific time for all timestamps
        from src.utils.timezone_utils import get_pacific_time
        pacific_now = get_pacific_time()
        timestamp = pacific_now.strftime('%I:%M:%S%p')  # "08:45:32PM"
        
        # Console output
        self._console.print(f"\n{'='*80}")
        self._console.print(f"[bold cyan]🤖 {agent_name}: PROMPT[/bold cyan]")
        self._console.print(f"[dim]Time: {timestamp}[/dim]")
        self._console.print(f"{'='*80}\n")
        
        # Show context if provided
        if context:
            self._console.print("[bold]Context:[/bold]")
            for key, value in context.items():
                self._console.print(f"  {key}: {value}")
            self._console.print()
        
        # Show prompt with syntax highlighting
        self._console.print(Panel(
            prompt[:2000] + ("..." if len(prompt) > 2000 else ""),
            title="Prompt",
            border_style="cyan"
        ))
        
        # File output
        if self._log_file:
            with open(self._log_file, 'a') as f:
                f.write(f"\n{'='*80}\n")
                f.write(f"🤖 {agent_name}: PROMPT\n")
                f.write(f"Time: {timestamp}\n")
                f.write(f"{'='*80}\n\n")
                if context:
                    f.write("Context:\n")
                    for key, value in context.items():
                        f.write(f"  {key}: {value}\n")
                    f.write("\n")
                f.write(prompt)
                f.write("\n\n")
        
        # Structured JSON event (for observability)
        if self._enabled:
            from src.utils.timezone_utils import get_pacific_time
            pacific_now = get_pacific_time()
            self._events.append({
                'event_type': 'prompt',
                'agent': agent_name,
                'timestamp': pacific_now.isoformat(),
                'timestamp_readable': timestamp,
                'prompt_length': len(prompt),
                'context': context or {},
                'prompt_preview': prompt[:500]  # First 500 chars for analysis
            })
    
    def log_response(
        self,
        agent_name: str,
        response_text: str,
        tokens_used: Optional[int] = None,
        model: Optional[str] = None
    ):
        """Log LLM response"""
        if not self._enabled:
            return
        
        # Use Pacific time for all timestamps
        from src.utils.timezone_utils import get_pacific_time
        pacific_now = get_pacific_time()
        timestamp = pacific_now.strftime('%I:%M:%S%p')  # "08:45:32PM"
        
        # Console output
        self._console.print(f"\n{'─'*80}")
        self._console.print(f"[bold green]🤖 {agent_name}: LLM RESPONSE[/bold green]")
        if tokens_used:
            cost_estimate = tokens_used * 0.000002  # Rough GPT-4o-mini cost
            self._console.print(f"[dim]Tokens: {tokens_used} (~${cost_estimate:.4f}) | Model: {model or 'unknown'}[/dim]")
        self._console.print(f"{'─'*80}\n")
        
        # Show response
        self._console.print(Panel(
            response_text[:2000] + ("..." if len(response_text) > 2000 else ""),
            title="Response",
            border_style="green"
        ))
        
        # File output
        if self._log_file:
            with open(self._log_file, 'a') as f:
                f.write(f"{'─'*80}\n")
                f.write(f"🤖 {agent_name}: LLM RESPONSE\n")
                if tokens_used:
                    f.write(f"Tokens: {tokens_used} | Model: {model or 'unknown'}\n")
                f.write(f"{'─'*80}\n\n")
                f.write(response_text)
                f.write("\n\n")
        
        # Structured JSON event (for observability)
        if self._enabled:
            from src.utils.timezone_utils import get_pacific_time
            pacific_now = get_pacific_time()
            self._events.append({
                'event_type': 'response',
                'agent': agent_name,
                'timestamp': pacific_now.isoformat(),
                'timestamp_readable': timestamp,
                'tokens_used': tokens_used,
                'model': model,
                'response_length': len(response_text),
                'response_preview': response_text[:500],  # First 500 chars
                'success': True  # Will be False if we detect errors
            })
    
    def log_reasoning(
        self,
        agent_name: str,
        decision: str,
        rationale: str,
        data: Optional[Dict[str, Any]] = None
    ):
        """Log agent's reasoning process"""
        if not self._enabled:
            return
        
        # Console output
        self._console.print(f"\n[bold yellow]💭 {agent_name}: REASONING[/bold yellow]")
        self._console.print(f"[cyan]Decision:[/cyan] {decision}")
        self._console.print(f"[dim]Rationale:[/dim] {rationale}")
        
        if data:
            self._console.print(f"\n[dim]Supporting Data:[/dim]")
            for key, value in data.items():
                self._console.print(f"  {key}: {value}")
        
        self._console.print()
        
        # File output
        if self._log_file:
            with open(self._log_file, 'a') as f:
                f.write(f"💭 {agent_name}: REASONING\n")
                f.write(f"Decision: {decision}\n")
                f.write(f"Rationale: {rationale}\n")
                if data:
                    f.write("\nSupporting Data:\n")
                    for key, value in data.items():
                        f.write(f"  {key}: {value}\n")
                f.write("\n")
    
    def log_validation(
        self,
        agent_name: str,
        check_name: str,
        passed: bool,
        details: Optional[str] = None
    ):
        """Log validation check result"""
        if not self._enabled:
            return
        
        status = "✅ PASSED" if passed else "❌ FAILED"
        color = "green" if passed else "red"
        
        # Console output
        self._console.print(f"[{color}]{status}[/{color}] {check_name}")
        if details:
            self._console.print(f"  [dim]{details}[/dim]")
        
        # File output
        if self._log_file:
            with open(self._log_file, 'a') as f:
                f.write(f"{status} {check_name}\n")
                if details:
                    f.write(f"  {details}\n")
                f.write("\n")
    
    def log_error(
        self,
        agent_name: str,
        error_type: str,
        error_message: str,
        context: Optional[Dict[str, Any]] = None
    ):
        """Log error/exception for observability"""
        if not self._enabled:
            return
        
        from src.utils.timezone_utils import get_pacific_time
        pacific_now = get_pacific_time()
        timestamp = pacific_now.strftime('%I:%M:%S%p')
        
        # Console output
        self._console.print(f"\n[bold red]❌ {agent_name}: ERROR[/bold red]")
        self._console.print(f"[red]Type: {error_type}[/red]")
        self._console.print(f"[red]Message: {error_message}[/red]")
        
        # Structured JSON event
        self._events.append({
            'event_type': 'error',
            'agent': agent_name,
            'timestamp': pacific_now.isoformat(),
            'timestamp_readable': timestamp,
            'error_type': error_type,
            'error_message': error_message,
            'context': context or {},
            'success': False
        })
    
    def export_json(self, output_file: Optional[Path] = None) -> Path:
        """
        Export all events as structured JSON for analysis.
        
        Returns:
            Path to exported JSON file
        """
        if not self._events:
            logger.warning("No events to export")
            return None
        
        if output_file is None:
            # Auto-generate filename based on log file
            if self._log_file:
                output_file = self._log_file.with_suffix('.observability.json')
            else:
                from src.utils.output_manager import get_output_file_path
                from src.utils.timezone_utils import get_pacific_time
                pacific_now = get_pacific_time()
                timestamp = pacific_now.strftime("%b-%d-%Y_%I-%M%p").replace(" ", "")
                output_file = get_output_file_path(f"agent_observability_{timestamp}.json")
        
        # Export summary statistics
        summary = {
            'total_events': len(self._events),
            'events_by_type': {},
            'events_by_agent': {},
            'total_tokens': sum(e.get('tokens_used', 0) for e in self._events if e.get('tokens_used')),
            'errors': [e for e in self._events if e.get('event_type') == 'error'],
            'error_count': len([e for e in self._events if e.get('event_type') == 'error']),
            'success_rate': len([e for e in self._events if e.get('success', True)]) / len(self._events) if self._events else 0
        }
        
        # Count by type
        for event in self._events:
            event_type = event.get('event_type', 'unknown')
            summary['events_by_type'][event_type] = summary['events_by_type'].get(event_type, 0) + 1
            
            agent = event.get('agent', 'unknown')
            summary['events_by_agent'][agent] = summary['events_by_agent'].get(agent, 0) + 1
        
        export_data = {
            'metadata': {
                'exported_at': datetime.now().isoformat(),
                'total_events': len(self._events),
                'log_file': str(self._log_file) if self._log_file else None
            },
            'summary': summary,
            'events': self._events
        }
        
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w') as f:
            json.dump(export_data, f, indent=2, default=str)
        
        logger.info(f"Exported {len(self._events)} events to {output_file}")
        return output_file

