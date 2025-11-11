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
from typing import Dict, Any, Optional
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
    """
    
    _instance = None
    _enabled = False
    _console = Console()
    _log_file = None
    
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
        
        if output_file:
            # Create file and write header
            output_file.parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, 'w') as f:
                f.write("="*80 + "\n")
                f.write("AGENT THINKING LOG\n")
                f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
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
        
        timestamp = datetime.now().strftime('%H:%M:%S')
        
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
        
        timestamp = datetime.now().strftime('%H:%M:%S')
        
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

