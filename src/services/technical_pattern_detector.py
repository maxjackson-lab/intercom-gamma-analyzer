"""
Technical pattern detection service for troubleshooting analysis.

This service identifies common technical patterns in support conversations
to help with macro creation, training materials, and AI agent prompting.
"""

import logging
import re
from typing import List, Dict, Any, Tuple, Set
from collections import Counter, defaultdict
from datetime import datetime
import json

logger = logging.getLogger(__name__)


class TechnicalPatternDetector:
    """
    Detects technical patterns in support conversations for troubleshooting analysis.
    
    This service identifies:
    - Common error messages and patterns
    - Technical troubleshooting steps
    - Escalation patterns
    - Resolution patterns
    - Macro opportunities
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Technical pattern definitions
        self.error_patterns = {
            'authentication_errors': [
                r'(?i)(invalid|incorrect|wrong|failed|denied).*(password|login|auth|credential)',
                r'(?i)(unauthorized|forbidden|access.*denied)',
                r'(?i)(token.*expired|session.*expired)',
                r'(?i)(api.*key.*invalid|api.*key.*expired)'
            ],
            'connection_errors': [
                r'(?i)(connection.*failed|connection.*timeout|connection.*refused)',
                r'(?i)(network.*error|network.*unavailable)',
                r'(?i)(dns.*error|dns.*resolution.*failed)',
                r'(?i)(ssl.*error|certificate.*error)'
            ],
            'export_errors': [
                r'(?i)(export.*failed|export.*error|export.*not.*working)',
                r'(?i)(download.*failed|download.*error)',
                r'(?i)(file.*corrupted|file.*damaged)',
                r'(?i)(export.*timeout|export.*stuck)'
            ],
            'performance_issues': [
                r'(?i)(slow|slowly|slow.*loading|loading.*slow)',
                r'(?i)(timeout|timed.*out|taking.*too.*long)',
                r'(?i)(freeze|frozen|stuck|hanging)',
                r'(?i)(crash|crashed|crashing)'
            ],
            'browser_issues': [
                r'(?i)(browser.*not.*working|browser.*error)',
                r'(?i)(chrome|firefox|safari|edge).*(not.*working|error)',
                r'(?i)(javascript.*error|js.*error)',
                r'(?i)(popup.*blocked|ad.*blocker)'
            ],
            'mobile_issues': [
                r'(?i)(mobile.*app.*not.*working|mobile.*error)',
                r'(?i)(ios|android).*(not.*working|error)',
                r'(?i)(app.*crash|app.*freeze)',
                r'(?i)(push.*notification.*not.*working)'
            ]
        }
        
        self.troubleshooting_steps = {
            'cache_clearing': [
                r'(?i)(clear.*cache|clear.*browser.*cache)',
                r'(?i)(hard.*refresh|ctrl.*f5|cmd.*r)',
                r'(?i)(incognito|private.*browsing)'
            ],
            'browser_switching': [
                r'(?i)(try.*different.*browser|use.*chrome|use.*firefox)',
                r'(?i)(browser.*compatibility|browser.*issue)'
            ],
            'connection_troubleshooting': [
                r'(?i)(check.*internet|internet.*connection)',
                r'(?i)(restart.*router|restart.*modem)',
                r'(?i)(wifi.*issue|ethernet.*issue)'
            ],
            'account_troubleshooting': [
                r'(?i)(logout.*login|sign.*out.*sign.*in)',
                r'(?i)(reset.*password|change.*password)',
                r'(?i)(account.*locked|account.*suspended)'
            ],
            'device_troubleshooting': [
                r'(?i)(restart.*device|reboot.*device)',
                r'(?i)(update.*app|app.*update)',
                r'(?i)(reinstall.*app|uninstall.*reinstall)'
            ]
        }
        
        self.escalation_patterns = {
            'technical_escalation': [
                r'(?i)(escalate.*to.*technical|escalate.*to.*engineer)',
                r'(?i)(need.*technical.*support|technical.*issue)',
                r'(?i)(complex.*technical|advanced.*technical)'
            ],
            'manager_escalation': [
                r'(?i)(escalate.*to.*manager|speak.*to.*manager)',
                r'(?i)(supervisor|supervisory)',
                r'(?i)(management.*involvement)'
            ],
            'urgent_escalation': [
                r'(?i)(urgent|asap|immediately|critical)',
                r'(?i)(business.*impact|production.*down)',
                r'(?i)(emergency|emergency.*support)'
            ]
        }
        
        self.resolution_patterns = {
            'successful_resolution': [
                r'(?i)(resolved|fixed|working.*now|solved)',
                r'(?i)(thank.*you|thanks|appreciate)',
                r'(?i)(issue.*resolved|problem.*solved)'
            ],
            'partial_resolution': [
                r'(?i)(partially.*resolved|somewhat.*better)',
                r'(?i)(workaround|temporary.*solution)',
                r'(?i)(still.*having.*issues|still.*problems)'
            ],
            'unresolved': [
                r'(?i)(still.*not.*working|still.*broken)',
                r'(?i)(issue.*persists|problem.*continues)',
                r'(?i)(frustrated|disappointed)'
            ]
        }
        
        # Compile regex patterns for performance
        self._compile_patterns()
        
        self.logger.info("TechnicalPatternDetector initialized with pattern definitions")

    def _compile_patterns(self):
        """Compile regex patterns for better performance."""
        self.compiled_error_patterns = {}
        for category, patterns in self.error_patterns.items():
            self.compiled_error_patterns[category] = [
                re.compile(pattern) for pattern in patterns
            ]
        
        self.compiled_troubleshooting_patterns = {}
        for category, patterns in self.troubleshooting_steps.items():
            self.compiled_troubleshooting_patterns[category] = [
                re.compile(pattern) for pattern in patterns
            ]
        
        self.compiled_escalation_patterns = {}
        for category, patterns in self.escalation_patterns.items():
            self.compiled_escalation_patterns[category] = [
                re.compile(pattern) for pattern in patterns
            ]
        
        self.compiled_resolution_patterns = {}
        for category, patterns in self.resolution_patterns.items():
            self.compiled_resolution_patterns[category] = [
                re.compile(pattern) for pattern in patterns
            ]

    def detect_technical_patterns(self, conversations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Detect technical patterns in a list of conversations.
        
        Args:
            conversations: List of conversation dictionaries
            
        Returns:
            Dictionary containing detected patterns and statistics
        """
        self.logger.info(f"Detecting technical patterns in {len(conversations)} conversations")
        
        results = {
            'error_patterns': self._detect_error_patterns(conversations),
            'troubleshooting_patterns': self._detect_troubleshooting_patterns(conversations),
            'escalation_patterns': self._detect_escalation_patterns(conversations),
            'resolution_patterns': self._detect_resolution_patterns(conversations),
            'macro_opportunities': self._identify_macro_opportunities(conversations),
            'summary': {}
        }
        
        # Generate summary statistics
        results['summary'] = self._generate_pattern_summary(results)
        
        self.logger.info("Technical pattern detection completed")
        return results

    def _detect_error_patterns(self, conversations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Detect error patterns in conversations."""
        error_stats = defaultdict(int)
        error_examples = defaultdict(list)
        conversation_errors = defaultdict(list)
        
        for conv in conversations:
            conv_id = conv.get('id', 'unknown')
            text = self._extract_conversation_text(conv)
            
            for category, patterns in self.compiled_error_patterns.items():
                for pattern in patterns:
                    matches = pattern.findall(text)
                    if matches:
                        error_stats[category] += len(matches)
                        error_examples[category].extend(matches[:3])  # Keep first 3 examples
                        conversation_errors[conv_id].append({
                            'category': category,
                            'matches': matches,
                            'pattern': pattern.pattern
                        })
        
        return {
            'statistics': dict(error_stats),
            'examples': {k: list(set(v)) for k, v in error_examples.items()},
            'conversation_details': dict(conversation_errors)
        }

    def _detect_troubleshooting_patterns(self, conversations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Detect troubleshooting patterns in conversations."""
        troubleshooting_stats = defaultdict(int)
        troubleshooting_examples = defaultdict(list)
        conversation_troubleshooting = defaultdict(list)
        
        for conv in conversations:
            conv_id = conv.get('id', 'unknown')
            text = self._extract_conversation_text(conv)
            
            for category, patterns in self.compiled_troubleshooting_patterns.items():
                for pattern in patterns:
                    matches = pattern.findall(text)
                    if matches:
                        troubleshooting_stats[category] += len(matches)
                        troubleshooting_examples[category].extend(matches[:3])
                        conversation_troubleshooting[conv_id].append({
                            'category': category,
                            'matches': matches,
                            'pattern': pattern.pattern
                        })
        
        return {
            'statistics': dict(troubleshooting_stats),
            'examples': {k: list(set(v)) for k, v in troubleshooting_examples.items()},
            'conversation_details': dict(conversation_troubleshooting)
        }

    def _detect_escalation_patterns(self, conversations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Detect escalation patterns in conversations."""
        escalation_stats = defaultdict(int)
        escalation_examples = defaultdict(list)
        conversation_escalations = defaultdict(list)
        
        for conv in conversations:
            conv_id = conv.get('id', 'unknown')
            text = self._extract_conversation_text(conv)
            
            for category, patterns in self.compiled_escalation_patterns.items():
                for pattern in patterns:
                    matches = pattern.findall(text)
                    if matches:
                        escalation_stats[category] += len(matches)
                        escalation_examples[category].extend(matches[:3])
                        conversation_escalations[conv_id].append({
                            'category': category,
                            'matches': matches,
                            'pattern': pattern.pattern
                        })
        
        return {
            'statistics': dict(escalation_stats),
            'examples': {k: list(set(v)) for k, v in escalation_examples.items()},
            'conversation_details': dict(conversation_escalations)
        }

    def _detect_resolution_patterns(self, conversations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Detect resolution patterns in conversations."""
        resolution_stats = defaultdict(int)
        resolution_examples = defaultdict(list)
        conversation_resolutions = defaultdict(list)
        
        for conv in conversations:
            conv_id = conv.get('id', 'unknown')
            text = self._extract_conversation_text(conv)
            
            for category, patterns in self.compiled_resolution_patterns.items():
                for pattern in patterns:
                    matches = pattern.findall(text)
                    if matches:
                        resolution_stats[category] += len(matches)
                        resolution_examples[category].extend(matches[:3])
                        conversation_resolutions[conv_id].append({
                            'category': category,
                            'matches': matches,
                            'pattern': pattern.pattern
                        })
        
        return {
            'statistics': dict(resolution_stats),
            'examples': {k: list(set(v)) for k, v in resolution_examples.items()},
            'conversation_details': dict(conversation_resolutions)
        }

    def _identify_macro_opportunities(self, conversations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Identify opportunities for creating macros based on common patterns."""
        macro_opportunities = defaultdict(int)
        macro_examples = defaultdict(list)
        
        # Analyze common error + troubleshooting combinations
        for conv in conversations:
            text = self._extract_conversation_text(conv)
            
            # Check for common error-troubleshooting pairs
            error_categories = []
            troubleshooting_categories = []
            
            for category, patterns in self.compiled_error_patterns.items():
                for pattern in patterns:
                    if pattern.search(text):
                        error_categories.append(category)
                        break
            
            for category, patterns in self.compiled_troubleshooting_patterns.items():
                for pattern in patterns:
                    if pattern.search(text):
                        troubleshooting_categories.append(category)
                        break
            
            # Create macro opportunity for common combinations
            if error_categories and troubleshooting_categories:
                for error_cat in error_categories:
                    for troubleshooting_cat in troubleshooting_categories:
                        macro_key = f"{error_cat}_with_{troubleshooting_cat}"
                        macro_opportunities[macro_key] += 1
                        macro_examples[macro_key].append({
                            'conversation_id': conv.get('id', 'unknown'),
                            'error_category': error_cat,
                            'troubleshooting_category': troubleshooting_cat,
                            'text_snippet': text[:200] + "..." if len(text) > 200 else text
                        })
        
        # Sort by frequency and return top opportunities
        sorted_opportunities = sorted(
            macro_opportunities.items(), 
            key=lambda x: x[1], 
            reverse=True
        )
        
        return {
            'top_opportunities': sorted_opportunities[:10],
            'examples': dict(macro_examples),
            'total_opportunities': len(macro_opportunities)
        }

    def _generate_pattern_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate summary statistics for all detected patterns."""
        summary = {
            'total_conversations_analyzed': 0,
            'error_patterns_found': 0,
            'troubleshooting_patterns_found': 0,
            'escalation_patterns_found': 0,
            'resolution_patterns_found': 0,
            'macro_opportunities_identified': 0,
            'most_common_errors': [],
            'most_common_troubleshooting': [],
            'most_common_escalations': [],
            'most_common_resolutions': []
        }
        
        # Count total patterns found
        for category, stats in results['error_patterns']['statistics'].items():
            summary['error_patterns_found'] += stats
        
        for category, stats in results['troubleshooting_patterns']['statistics'].items():
            summary['troubleshooting_patterns_found'] += stats
        
        for category, stats in results['escalation_patterns']['statistics'].items():
            summary['escalation_patterns_found'] += stats
        
        for category, stats in results['resolution_patterns']['statistics'].items():
            summary['resolution_patterns_found'] += stats
        
        summary['macro_opportunities_identified'] = results['macro_opportunities']['total_opportunities']
        
        # Get most common patterns
        summary['most_common_errors'] = sorted(
            results['error_patterns']['statistics'].items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]
        
        summary['most_common_troubleshooting'] = sorted(
            results['troubleshooting_patterns']['statistics'].items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]
        
        summary['most_common_escalations'] = sorted(
            results['escalation_patterns']['statistics'].items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]
        
        summary['most_common_resolutions'] = sorted(
            results['resolution_patterns']['statistics'].items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]
        
        return summary

    def _extract_conversation_text(self, conversation: Dict[str, Any]) -> str:
        """Extract all text content from a conversation."""
        text_parts = []
        
        # Handle both dict and list formats
        if isinstance(conversation, dict):
            # Extract from conversation parts
            conversation_parts = conversation.get('conversation_parts', {})
            if isinstance(conversation_parts, dict):
                parts = conversation_parts.get('conversation_parts', [])
            else:
                parts = conversation_parts if isinstance(conversation_parts, list) else []
            
            for part in parts:
                if isinstance(part, dict) and part.get('body'):
                    text_parts.append(part['body'])
            
            # Extract from source
            source = conversation.get('source', {})
            if isinstance(source, dict) and source.get('body'):
                text_parts.append(source['body'])
            
            # Extract from full_text if available
            if conversation.get('full_text'):
                text_parts.append(conversation['full_text'])
        
        return ' '.join(text_parts)

    def get_pattern_definitions(self) -> Dict[str, Any]:
        """Get all pattern definitions for reference."""
        return {
            'error_patterns': self.error_patterns,
            'troubleshooting_steps': self.troubleshooting_steps,
            'escalation_patterns': self.escalation_patterns,
            'resolution_patterns': self.resolution_patterns
        }

    def add_custom_pattern(self, category: str, pattern_type: str, pattern: str):
        """Add a custom pattern to the detector."""
        if pattern_type == 'error':
            if category not in self.error_patterns:
                self.error_patterns[category] = []
            self.error_patterns[category].append(pattern)
        elif pattern_type == 'troubleshooting':
            if category not in self.troubleshooting_steps:
                self.troubleshooting_steps[category] = []
            self.troubleshooting_steps[category].append(pattern)
        elif pattern_type == 'escalation':
            if category not in self.escalation_patterns:
                self.escalation_patterns[category] = []
            self.escalation_patterns[category].append(pattern)
        elif pattern_type == 'resolution':
            if category not in self.resolution_patterns:
                self.resolution_patterns[category] = []
            self.resolution_patterns[category].append(pattern)
        
        # Recompile patterns
        self._compile_patterns()
        
        self.logger.info(f"Added custom {pattern_type} pattern for category {category}")

    def export_patterns(self, filepath: str):
        """Export all patterns to a JSON file."""
        patterns = self.get_pattern_definitions()
        with open(filepath, 'w') as f:
            json.dump(patterns, f, indent=2)
        
        self.logger.info(f"Patterns exported to {filepath}")

    def import_patterns(self, filepath: str):
        """Import patterns from a JSON file."""
        with open(filepath, 'r') as f:
            patterns = json.load(f)
        
        self.error_patterns.update(patterns.get('error_patterns', {}))
        self.troubleshooting_steps.update(patterns.get('troubleshooting_steps', {}))
        self.escalation_patterns.update(patterns.get('escalation_patterns', {}))
        self.resolution_patterns.update(patterns.get('resolution_patterns', {}))
        
        # Recompile patterns
        self._compile_patterns()
        
        self.logger.info(f"Patterns imported from {filepath}")
