"""
Command whitelist for secure command execution.

Defines allowed commands and flags, implements parameter validation,
and provides risk assessment for command execution.
"""

import logging
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class CommandRisk(Enum):
    """Command risk levels."""
    SAFE = "safe"           # Read-only operations
    LOW = "low"             # Non-destructive writes
    MEDIUM = "medium"       # File modifications
    HIGH = "high"           # System changes
    CRITICAL = "critical"   # Destructive operations


@dataclass
class CommandRule:
    """Rule definition for a command."""
    command: str
    allowed_flags: Set[str]
    dangerous_flags: Set[str]
    required_flags: Set[str]
    risk_level: CommandRisk
    requires_confirmation: bool
    max_args: int
    description: str


@dataclass
class ValidationResult:
    """Result of command validation."""
    is_allowed: bool
    risk_level: CommandRisk
    requires_confirmation: bool
    sanitized_command: List[str]
    explanation: str
    warnings: List[str]


class CommandWhitelist:
    """
    Whitelist of allowed commands with security validation.
    
    Implements defense-in-depth by:
    - Explicit allowlist of commands and flags
    - Parameter validation and sanitization
    - Risk assessment for approval workflows
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Define allowed commands with their security rules
        self.command_rules = {
            "voice-of-customer": CommandRule(
                command="voice-of-customer",
                allowed_flags={
                    "--time-period", "--start-date", "--end-date",
                    "--include-canny", "--generate-gamma", "--ai-model",
                    "--enable-fallback", "--max-conversations", "--output-format"
                },
                dangerous_flags=set(),
                required_flags=set(),
                risk_level=CommandRisk.SAFE,
                requires_confirmation=False,
                max_args=10,
                description="Voice of Customer analysis"
            ),
            
            "comprehensive-analysis": CommandRule(
                command="comprehensive-analysis",
                allowed_flags={
                    "--start-date", "--end-date", "--max-conversations",
                    "--generate-gamma", "--gamma-style", "--gamma-export",
                    "--export-docs", "--ai-model", "--enable-fallback"
                },
                dangerous_flags={"--force-delete", "--overwrite"},
                required_flags=set(),
                risk_level=CommandRisk.LOW,
                requires_confirmation=True,
                max_args=15,
                description="Comprehensive analysis with file generation"
            ),
            
            "billing-analysis": CommandRule(
                command="billing-analysis",
                allowed_flags={
                    "--start-date", "--end-date", "--output-format",
                    "--include-details", "--ai-model"
                },
                dangerous_flags=set(),
                required_flags=set(),
                risk_level=CommandRisk.SAFE,
                requires_confirmation=False,
                max_args=8,
                description="Billing and subscription analysis"
            ),
            
            "tech-analysis": CommandRule(
                command="tech-analysis",
                allowed_flags={
                    "--category", "--start-date", "--end-date",
                    "--output-format", "--ai-model", "--max-conversations"
                },
                dangerous_flags=set(),
                required_flags=set(),
                risk_level=CommandRisk.SAFE,
                requires_confirmation=False,
                max_args=10,
                description="Technical troubleshooting analysis"
            ),
            
            "product-analysis": CommandRule(
                command="product-analysis",
                allowed_flags={
                    "--category", "--start-date", "--end-date",
                    "--output-format", "--ai-model", "--include-feedback"
                },
                dangerous_flags=set(),
                required_flags=set(),
                risk_level=CommandRisk.SAFE,
                requires_confirmation=False,
                max_args=10,
                description="Product question analysis"
            ),
            
            "sites-analysis": CommandRule(
                command="sites-analysis",
                allowed_flags={
                    "--start-date", "--end-date", "--output-format",
                    "--ai-model", "--include-details"
                },
                dangerous_flags=set(),
                required_flags=set(),
                risk_level=CommandRisk.SAFE,
                requires_confirmation=False,
                max_args=8,
                description="Sites and account analysis"
            ),
            
            "chat": CommandRule(
                command="chat",
                allowed_flags={
                    "--model", "--enable-cache", "--railway",
                    "--help", "--version"
                },
                dangerous_flags=set(),
                required_flags=set(),
                risk_level=CommandRisk.SAFE,
                requires_confirmation=False,
                max_args=5,
                description="Interactive chat interface"
            ),
        }
        
        # Dangerous command patterns that should never be allowed
        self.forbidden_patterns = {
            "rm", "del", "delete", "format", "fdisk", "mkfs",
            "sudo", "su", "chmod", "chown", "passwd", "useradd",
            "wget", "curl", "nc", "netcat", "telnet", "ssh",
            "python -c", "bash -c", "sh -c", "cmd /c",
            "eval", "exec", "system", "popen", "subprocess",
        }
    
    def validate_command(self, command_parts: List[str]) -> ValidationResult:
        """
        Validate a command against the whitelist.
        
        Args:
            command_parts: List of command parts (e.g., ["voice-of-customer", "--time-period", "week"])
            
        Returns:
            ValidationResult with validation status and sanitized command
        """
        if not command_parts:
            return ValidationResult(
                is_allowed=False,
                risk_level=CommandRisk.CRITICAL,
                requires_confirmation=True,
                sanitized_command=[],
                explanation="Empty command",
                warnings=["Empty command provided"]
            )
        
        command_name = command_parts[0]
        
        # Check if command is in whitelist
        if command_name not in self.command_rules:
            return ValidationResult(
                is_allowed=False,
                risk_level=CommandRisk.CRITICAL,
                requires_confirmation=True,
                sanitized_command=[],
                explanation=f"Command '{command_name}' not in whitelist",
                warnings=[f"Unknown command: {command_name}"]
            )
        
        rule = self.command_rules[command_name]
        
        # Check for forbidden patterns in the command (but allow dangerous flags in allowed commands)
        command_text = " ".join(command_parts).lower()
        for forbidden in self.forbidden_patterns:
            # Skip check for dangerous flags if they're in the allowed dangerous_flags set
            if forbidden in rule.dangerous_flags:
                continue
            # Check for exact word matches to avoid false positives
            import re
            if re.search(r'\b' + re.escape(forbidden) + r'\b', command_text):
                return ValidationResult(
                    is_allowed=False,
                    risk_level=CommandRisk.CRITICAL,
                    requires_confirmation=True,
                    sanitized_command=[],
                    explanation=f"Forbidden pattern detected: {forbidden}",
                    warnings=[f"Dangerous pattern: {forbidden}"]
                )
        
        # Validate flags and arguments
        flags, args, warnings = self._parse_and_validate_flags(command_parts[1:], rule)
        
        # Check argument count (count all parts, not just args)
        total_parts = len(flags) + len(args)
        if total_parts > rule.max_args:
            return ValidationResult(
                is_allowed=False,
                risk_level=CommandRisk.HIGH,
                requires_confirmation=True,
                sanitized_command=[],
                explanation=f"Too many arguments: {total_parts} > {rule.max_args}",
                warnings=[f"Excessive arguments: {total_parts}"]
            )
        
        # Build sanitized command
        sanitized = [command_name] + flags + args
        
        # Check if any dangerous flags are present
        dangerous_flags_present = any(flag in rule.dangerous_flags for flag in flags)
        if dangerous_flags_present:
            warnings.append("Dangerous flags detected")
        
        # Determine if confirmation is required
        requires_confirmation = rule.requires_confirmation or dangerous_flags_present
        
        return ValidationResult(
            is_allowed=True,
            risk_level=rule.risk_level,
            requires_confirmation=requires_confirmation,
            sanitized_command=sanitized,
            explanation=f"Command validated: {rule.description}",
            warnings=warnings
        )
    
    def _parse_and_validate_flags(self, parts: List[str], rule: CommandRule) -> tuple[List[str], List[str], List[str]]:
        """Parse and validate command flags and arguments."""
        flags = []
        args = []
        warnings = []
        
        i = 0
        while i < len(parts):
            part = parts[i]
            
            if part.startswith("--"):
                # It's a flag
                if part in rule.allowed_flags:
                    flags.append(part)
                    
                    # Check if flag requires a value
                    if i + 1 < len(parts) and not parts[i + 1].startswith("--"):
                        # Next part is likely the flag value
                        i += 1
                        if i < len(parts):
                            args.append(parts[i])
                elif part in rule.dangerous_flags:
                    flags.append(part)
                    warnings.append(f"Dangerous flag used: {part}")
                else:
                    warnings.append(f"Unknown flag: {part}")
            else:
                # It's an argument
                args.append(part)
            
            i += 1
        
        return flags, args, warnings
    
    def get_command_info(self, command_name: str) -> Optional[CommandRule]:
        """Get information about a specific command."""
        return self.command_rules.get(command_name)
    
    def list_allowed_commands(self) -> List[str]:
        """Get list of all allowed commands."""
        return list(self.command_rules.keys())
    
    def is_command_allowed(self, command_name: str) -> bool:
        """Check if a command is in the whitelist."""
        return command_name in self.command_rules
