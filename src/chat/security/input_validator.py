"""
Input validation for natural language commands.

Implements pattern matching and semantic analysis to detect injection attacks,
role modification attempts, and other security threats.
"""

import re
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ThreatLevel(Enum):
    """Threat level classification."""
    SAFE = "safe"
    SUSPICIOUS = "suspicious"
    DANGEROUS = "dangerous"
    CRITICAL = "critical"


@dataclass
class ValidationResult:
    """Result of input validation."""
    is_valid: bool
    threat_level: ThreatLevel
    risk_score: float  # 0-10 scale
    detected_patterns: List[str]
    sanitized_input: str
    explanation: str


class InputValidator:
    """
    Validates user input against known attack patterns.
    
    Implements defense against:
    - Prompt injection attacks
    - Command injection via special characters
    - Role modification attempts
    - Jailbreak patterns
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # OWASP LLM Top 10 injection patterns
        self.injection_patterns = [
            r"ignore\s+previous\s+instructions",
            r"disregard\s+constraints",
            r"forget\s+everything",
            r"you\s+are\s+now\s+",
            r"system\s+prompt",
            r"jailbreak",
            r"developer\s+mode",
            r"admin\s+mode",
            r"bypass\s+security",
            r"override\s+restrictions",
            r"pretend\s+to\s+be",
            r"act\s+as\s+if",
            r"roleplay\s+as",
            r"simulate\s+being",
        ]
        
        # Command injection patterns
        self.command_injection_patterns = [
            r"[;&|`$]",
            r"\$\{.*\}",
            r"`.*`",
            r"\|\s*\w+",
            r"&&\s*\w+",
            r";\s*\w+",
            r"rm\s+-rf",
            r"sudo\s+",
            r"chmod\s+777",
            r"wget\s+",
            r"curl\s+",
            r"nc\s+",
            r"python\s+-c",
            r"bash\s+-c",
        ]
        
        # Role modification patterns
        self.role_modification_patterns = [
            r"you\s+are\s+(?:now\s+)?(?:a\s+)?(?:different\s+)?(?:ai\s+)?(?:assistant\s+)?(?:model\s+)?",
            r"from\s+now\s+on",
            r"change\s+your\s+role",
            r"switch\s+to\s+",
            r"become\s+",
            r"act\s+as\s+(?:a\s+)?(?:different\s+)?",
            r"pretend\s+you\s+are",
            r"imagine\s+you\s+are",
        ]
        
        # Compile patterns for efficiency
        self.compiled_injection = [re.compile(pattern, re.IGNORECASE) for pattern in self.injection_patterns]
        self.compiled_command = [re.compile(pattern, re.IGNORECASE) for pattern in self.command_injection_patterns]
        self.compiled_role = [re.compile(pattern, re.IGNORECASE) for pattern in self.role_modification_patterns]
    
    def validate(self, user_input: str) -> ValidationResult:
        """
        Validate user input against security patterns.
        
        Args:
            user_input: The user's natural language input
            
        Returns:
            ValidationResult with threat assessment and sanitized input
        """
        if not user_input or not user_input.strip():
            return ValidationResult(
                is_valid=False,
                threat_level=ThreatLevel.SUSPICIOUS,
                risk_score=1.0,
                detected_patterns=["empty_input"],
                sanitized_input="",
                explanation="Empty input detected"
            )
        
        detected_patterns = []
        risk_score = 0.0
        
        # Check for injection patterns
        injection_matches = self._check_patterns(user_input, self.compiled_injection, "injection")
        if injection_matches:
            detected_patterns.extend(injection_matches)
            risk_score += 3.0
        
        # Check for command injection
        command_matches = self._check_patterns(user_input, self.compiled_command, "command_injection")
        if command_matches:
            detected_patterns.extend(command_matches)
            risk_score += 4.0
        
        # Check for role modification
        role_matches = self._check_patterns(user_input, self.compiled_role, "role_modification")
        if role_matches:
            detected_patterns.extend(role_matches)
            risk_score += 2.5
        
        # Check for unusual character patterns
        unusual_chars = self._check_unusual_characters(user_input)
        if unusual_chars:
            detected_patterns.append("unusual_characters")
            risk_score += 1.0
        
        # Check for excessive length (potential payload)
        if len(user_input) > 2000:
            detected_patterns.append("excessive_length")
            risk_score += 1.5
        
        # Determine threat level
        threat_level = self._calculate_threat_level(risk_score)
        
        # Sanitize input
        sanitized = self._sanitize_input(user_input)
        
        # Determine if valid - be more strict
        is_valid = threat_level == ThreatLevel.SAFE
        
        explanation = self._generate_explanation(detected_patterns, threat_level)
        
        self.logger.info(f"Input validation: {threat_level.value}, risk_score={risk_score:.1f}, patterns={detected_patterns}")
        
        return ValidationResult(
            is_valid=is_valid,
            threat_level=threat_level,
            risk_score=risk_score,
            detected_patterns=detected_patterns,
            sanitized_input=sanitized,
            explanation=explanation
        )
    
    def _check_patterns(self, text: str, compiled_patterns: List[re.Pattern], pattern_type: str) -> List[str]:
        """Check text against compiled regex patterns."""
        matches = []
        for pattern in compiled_patterns:
            if pattern.search(text):
                matches.append(f"{pattern_type}:{pattern.pattern}")
        return matches
    
    def _check_unusual_characters(self, text: str) -> bool:
        """Check for unusual character frequency patterns."""
        # Count special characters
        special_chars = sum(1 for c in text if not c.isalnum() and not c.isspace())
        total_chars = len(text)
        
        if total_chars == 0:
            return False
        
        special_ratio = special_chars / total_chars
        
        # Flag if more than 30% special characters
        return special_ratio > 0.3
    
    def _calculate_threat_level(self, risk_score: float) -> ThreatLevel:
        """Calculate threat level based on risk score."""
        if risk_score >= 7.0:
            return ThreatLevel.CRITICAL
        elif risk_score >= 5.0:
            return ThreatLevel.DANGEROUS
        elif risk_score >= 2.0:
            return ThreatLevel.SUSPICIOUS
        else:
            return ThreatLevel.SAFE
    
    def _sanitize_input(self, text: str) -> str:
        """Sanitize input by removing or escaping dangerous characters."""
        # Remove null bytes and control characters
        sanitized = ''.join(char for char in text if ord(char) >= 32 or char in '\n\t')
        
        # Escape shell metacharacters
        dangerous_chars = ['&', '|', ';', '$', '`', '(', ')', '<', '>', '/']
        for char in dangerous_chars:
            sanitized = sanitized.replace(char, f'\\{char}')
        
        return sanitized.strip()
    
    def _generate_explanation(self, patterns: List[str], threat_level: ThreatLevel) -> str:
        """Generate human-readable explanation of validation result."""
        if threat_level == ThreatLevel.SAFE:
            return "Input appears safe"
        elif threat_level == ThreatLevel.SUSPICIOUS:
            return f"Suspicious patterns detected: {', '.join(patterns[:3])}"
        elif threat_level == ThreatLevel.DANGEROUS:
            return f"Dangerous patterns detected: {', '.join(patterns[:3])}"
        else:
            return f"Critical security threat detected: {', '.join(patterns[:3])}"
