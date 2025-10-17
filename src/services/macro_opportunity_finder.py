"""
Macro opportunity finder service for identifying common support patterns.

This service analyzes support conversations to identify opportunities for
creating macros, training materials, and improving AI agent responses.
"""

import logging
from typing import List, Dict, Any, Tuple, Set
from collections import Counter, defaultdict
from datetime import datetime
import re

logger = logging.getLogger(__name__)


class MacroOpportunityFinder:
    """
    Identifies opportunities for creating macros based on conversation analysis.
    
    This service analyzes:
    - Common question patterns
    - Repeated troubleshooting steps
    - Standard responses
    - Escalation patterns
    - Resolution patterns
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Common question patterns that could become macros
        self.question_patterns = {
            'billing_questions': [
                r'(?i)(how.*do.*i.*cancel|how.*to.*cancel)',
                r'(?i)(how.*do.*i.*refund|how.*to.*refund)',
                r'(?i)(where.*is.*my.*invoice|invoice.*location)',
                r'(?i)(how.*do.*i.*change.*plan|upgrade.*plan)',
                r'(?i)(billing.*cycle|payment.*cycle)'
            ],
            'account_questions': [
                r'(?i)(how.*do.*i.*reset.*password|forgot.*password)',
                r'(?i)(how.*do.*i.*change.*email|change.*email.*address)',
                r'(?i)(how.*do.*i.*delete.*account|delete.*my.*account)',
                r'(?i)(how.*do.*i.*update.*profile|update.*my.*profile)',
                r'(?i)(two.*factor.*authentication|2fa)'
            ],
            'technical_questions': [
                r'(?i)(how.*do.*i.*export|export.*data)',
                r'(?i)(how.*do.*i.*import|import.*data)',
                r'(?i)(api.*documentation|api.*guide)',
                r'(?i)(integration.*help|how.*to.*integrate)',
                r'(?i)(webhook.*setup|webhook.*configuration)'
            ],
            'product_questions': [
                r'(?i)(how.*does.*this.*work|how.*to.*use)',
                r'(?i)(feature.*request|new.*feature)',
                r'(?i)(bug.*report|report.*bug)',
                r'(?i)(tutorial|how.*to.*tutorial)',
                r'(?i)(best.*practices|recommendations)'
            ]
        }
        
        # Common response patterns that could be standardized
        self.response_patterns = {
            'greeting_responses': [
                r'(?i)(hello|hi|hey).*(how.*can.*i.*help|what.*can.*i.*do)',
                r'(?i)(thank.*you.*for.*contacting|thanks.*for.*reaching.*out)',
                r'(?i)(i.*understand.*your.*concern|i.*hear.*your.*frustration)'
            ],
            'troubleshooting_responses': [
                r'(?i)(let.*me.*help.*you.*with.*that|i.*can.*help.*you)',
                r'(?i)(first.*try|let.*s.*start.*with)',
                r'(?i)(if.*that.*doesn.*t.*work|if.*the.*problem.*persists)',
                r'(?i)(please.*try.*this|can.*you.*try)'
            ],
            'escalation_responses': [
                r'(?i)(i.*ll.*escalate.*this|escalating.*to.*technical)',
                r'(?i)(let.*me.*connect.*you.*with|transferring.*you.*to)',
                r'(?i)(our.*technical.*team.*will|engineering.*team.*will)'
            ],
            'resolution_responses': [
                r'(?i)(is.*this.*resolved|does.*this.*solve.*your.*issue)',
                r'(?i)(let.*me.*know.*if.*you.*need|feel.*free.*to.*contact)',
                r'(?i)(is.*there.*anything.*else|anything.*else.*i.*can.*help)'
            ]
        }
        
        # Common troubleshooting sequences
        self.troubleshooting_sequences = {
            'browser_issues': [
                'clear_cache',
                'try_different_browser',
                'disable_extensions',
                'check_javascript'
            ],
            'login_issues': [
                'reset_password',
                'check_credentials',
                'clear_cookies',
                'try_incognito'
            ],
            'export_issues': [
                'check_file_format',
                'try_different_browser',
                'check_file_size',
                'contact_technical'
            ],
            'performance_issues': [
                'check_internet',
                'clear_cache',
                'restart_browser',
                'contact_technical'
            ]
        }
        
        # Compile regex patterns
        self._compile_patterns()
        
        self.logger.info("MacroOpportunityFinder initialized")

    def _compile_patterns(self):
        """Compile regex patterns for better performance."""
        self.compiled_question_patterns = {}
        for category, patterns in self.question_patterns.items():
            self.compiled_question_patterns[category] = [
                re.compile(pattern) for pattern in patterns
            ]
        
        self.compiled_response_patterns = {}
        for category, patterns in self.response_patterns.items():
            self.compiled_response_patterns[category] = [
                re.compile(pattern) for pattern in patterns
            ]

    def find_macro_opportunities(self, conversations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Find macro opportunities in conversations.
        
        Args:
            conversations: List of conversation dictionaries
            
        Returns:
            Dictionary containing macro opportunities and recommendations
        """
        self.logger.info(f"Finding macro opportunities in {len(conversations)} conversations")
        
        results = {
            'question_macros': self._find_question_macros(conversations),
            'response_macros': self._find_response_macros(conversations),
            'troubleshooting_macros': self._find_troubleshooting_macros(conversations),
            'escalation_macros': self._find_escalation_macros(conversations),
            'training_opportunities': self._find_training_opportunities(conversations),
            'ai_agent_improvements': self._find_ai_agent_improvements(conversations),
            'summary': {}
        }
        
        # Generate summary
        results['summary'] = self._generate_macro_summary(results)
        
        self.logger.info("Macro opportunity analysis completed")
        return results

    def _find_question_macros(self, conversations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Find opportunities for question-based macros."""
        question_stats = defaultdict(int)
        question_examples = defaultdict(list)
        question_contexts = defaultdict(list)
        
        for conv in conversations:
            conv_id = conv.get('id', 'unknown')
            text = self._extract_conversation_text(conv)
            
            for category, patterns in self.compiled_question_patterns.items():
                for pattern in patterns:
                    matches = pattern.findall(text)
                    if matches:
                        question_stats[category] += len(matches)
                        question_examples[category].extend(matches[:3])
                        question_contexts[category].append({
                            'conversation_id': conv_id,
                            'matches': matches,
                            'context': self._extract_context(text, matches[0])
                        })
        
        # Identify high-frequency questions for macro creation
        high_frequency_questions = {
            category: stats for category, stats in question_stats.items()
            if stats >= 3  # Threshold for macro creation
        }
        
        return {
            'statistics': dict(question_stats),
            'high_frequency_questions': high_frequency_questions,
            'examples': {k: list(set(v)) for k, v in question_examples.items()},
            'contexts': dict(question_contexts),
            'recommendations': self._generate_question_macro_recommendations(high_frequency_questions)
        }

    def _find_response_macros(self, conversations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Find opportunities for response-based macros."""
        response_stats = defaultdict(int)
        response_examples = defaultdict(list)
        response_contexts = defaultdict(list)
        
        for conv in conversations:
            conv_id = conv.get('id', 'unknown')
            text = self._extract_conversation_text(conv)
            
            for category, patterns in self.compiled_response_patterns.items():
                for pattern in patterns:
                    matches = pattern.findall(text)
                    if matches:
                        response_stats[category] += len(matches)
                        response_examples[category].extend(matches[:3])
                        response_contexts[category].append({
                            'conversation_id': conv_id,
                            'matches': matches,
                            'context': self._extract_context(text, matches[0])
                        })
        
        # Identify standardizable responses
        standardizable_responses = {
            category: stats for category, stats in response_stats.items()
            if stats >= 5  # Threshold for standardization
        }
        
        return {
            'statistics': dict(response_stats),
            'standardizable_responses': standardizable_responses,
            'examples': {k: list(set(v)) for k, v in response_examples.items()},
            'contexts': dict(response_contexts),
            'recommendations': self._generate_response_macro_recommendations(standardizable_responses)
        }

    def _find_troubleshooting_macros(self, conversations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Find opportunities for troubleshooting macros."""
        troubleshooting_sequences = defaultdict(int)
        troubleshooting_examples = defaultdict(list)
        
        for conv in conversations:
            conv_id = conv.get('id', 'unknown')
            text = self._extract_conversation_text(conv)
            
            # Check for common troubleshooting sequences
            for sequence_name, steps in self.troubleshooting_sequences.items():
                sequence_found = True
                found_steps = []
                
                for step in steps:
                    step_pattern = re.compile(rf'(?i).*{step.replace("_", ".*")}.*')
                    if step_pattern.search(text):
                        found_steps.append(step)
                    else:
                        sequence_found = False
                        break
                
                if sequence_found:
                    troubleshooting_sequences[sequence_name] += 1
                    troubleshooting_examples[sequence_name].append({
                        'conversation_id': conv_id,
                        'steps_found': found_steps,
                        'text_snippet': text[:300] + "..." if len(text) > 300 else text
                    })
        
        return {
            'statistics': dict(troubleshooting_sequences),
            'examples': dict(troubleshooting_examples),
            'recommendations': self._generate_troubleshooting_macro_recommendations(troubleshooting_sequences)
        }

    def _find_escalation_macros(self, conversations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Find opportunities for escalation macros."""
        escalation_patterns = defaultdict(int)
        escalation_examples = defaultdict(list)
        
        escalation_keywords = [
            'escalate', 'transfer', 'technical', 'manager', 'supervisor',
            'urgent', 'critical', 'complex', 'advanced'
        ]
        
        for conv in conversations:
            conv_id = conv.get('id', 'unknown')
            text = self._extract_conversation_text(conv)
            
            for keyword in escalation_keywords:
                if re.search(rf'(?i).*{keyword}.*', text):
                    escalation_patterns[keyword] += 1
                    escalation_examples[keyword].append({
                        'conversation_id': conv_id,
                        'context': self._extract_context(text, keyword)
                    })
        
        return {
            'statistics': dict(escalation_patterns),
            'examples': dict(escalation_examples),
            'recommendations': self._generate_escalation_macro_recommendations(escalation_patterns)
        }

    def _find_training_opportunities(self, conversations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Find opportunities for training materials."""
        training_opportunities = {
            'common_misconceptions': defaultdict(int),
            'knowledge_gaps': defaultdict(int),
            'best_practices': defaultdict(int),
            'case_studies': []
        }
        
        for conv in conversations:
            conv_id = conv.get('id', 'unknown')
            text = self._extract_conversation_text(conv)
            
            # Look for common misconceptions
            misconception_patterns = [
                r'(?i)(i.*thought.*it.*would|i.*expected.*it.*to)',
                r'(?i)(that.*s.*not.*how.*it.*works|that.*s.*not.*right)',
                r'(?i)(i.*didn.*t.*know.*that|i.*wasn.*t.*aware)'
            ]
            
            for pattern in misconception_patterns:
                if re.search(pattern, text):
                    training_opportunities['common_misconceptions']['misunderstanding'] += 1
            
            # Look for knowledge gaps
            knowledge_gap_patterns = [
                r'(?i)(how.*do.*i.*know|how.*can.*i.*tell)',
                r'(?i)(what.*does.*this.*mean|i.*don.*t.*understand)',
                r'(?i)(where.*can.*i.*find|where.*is.*the.*information)'
            ]
            
            for pattern in knowledge_gap_patterns:
                if re.search(pattern, text):
                    training_opportunities['knowledge_gaps']['information_needed'] += 1
        
        return training_opportunities

    def _find_ai_agent_improvements(self, conversations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Find opportunities for AI agent improvements."""
        ai_improvements = {
            'common_questions': defaultdict(int),
            'escalation_triggers': defaultdict(int),
            'response_patterns': defaultdict(int),
            'success_indicators': defaultdict(int)
        }
        
        for conv in conversations:
            conv_id = conv.get('id', 'unknown')
            text = self._extract_conversation_text(conv)
            
            # Look for AI agent interactions
            ai_patterns = [
                r'(?i)(fin|copilot|ai.*agent|bot)',
                r'(?i)(automated.*response|auto.*reply)'
            ]
            
            for pattern in ai_patterns:
                if re.search(pattern, text):
                    # Analyze what led to escalation or success
                    if re.search(r'(?i)(escalate|transfer|human)', text):
                        ai_improvements['escalation_triggers']['human_handoff'] += 1
                    elif re.search(r'(?i)(resolved|fixed|solved)', text):
                        ai_improvements['success_indicators']['ai_resolution'] += 1
        
        return ai_improvements

    def _generate_question_macro_recommendations(self, high_frequency_questions: Dict[str, int]) -> List[Dict[str, Any]]:
        """Generate recommendations for question-based macros."""
        recommendations = []
        
        for category, frequency in high_frequency_questions.items():
            recommendation = {
                'type': 'question_macro',
                'category': category,
                'frequency': frequency,
                'priority': 'high' if frequency >= 10 else 'medium',
                'suggested_macro': self._suggest_question_macro(category),
                'implementation_notes': self._get_implementation_notes(category, 'question')
            }
            recommendations.append(recommendation)
        
        return recommendations

    def _generate_response_macro_recommendations(self, standardizable_responses: Dict[str, int]) -> List[Dict[str, Any]]:
        """Generate recommendations for response-based macros."""
        recommendations = []
        
        for category, frequency in standardizable_responses.items():
            recommendation = {
                'type': 'response_macro',
                'category': category,
                'frequency': frequency,
                'priority': 'high' if frequency >= 15 else 'medium',
                'suggested_macro': self._suggest_response_macro(category),
                'implementation_notes': self._get_implementation_notes(category, 'response')
            }
            recommendations.append(recommendation)
        
        return recommendations

    def _generate_troubleshooting_macro_recommendations(self, troubleshooting_sequences: Dict[str, int]) -> List[Dict[str, Any]]:
        """Generate recommendations for troubleshooting macros."""
        recommendations = []
        
        for sequence_name, frequency in troubleshooting_sequences.items():
            recommendation = {
                'type': 'troubleshooting_macro',
                'category': sequence_name,
                'frequency': frequency,
                'priority': 'high' if frequency >= 5 else 'medium',
                'suggested_macro': self._suggest_troubleshooting_macro(sequence_name),
                'implementation_notes': self._get_implementation_notes(sequence_name, 'troubleshooting')
            }
            recommendations.append(recommendation)
        
        return recommendations

    def _generate_escalation_macro_recommendations(self, escalation_patterns: Dict[str, int]) -> List[Dict[str, Any]]:
        """Generate recommendations for escalation macros."""
        recommendations = []
        
        for pattern, frequency in escalation_patterns.items():
            recommendation = {
                'type': 'escalation_macro',
                'category': pattern,
                'frequency': frequency,
                'priority': 'high' if frequency >= 8 else 'medium',
                'suggested_macro': self._suggest_escalation_macro(pattern),
                'implementation_notes': self._get_implementation_notes(pattern, 'escalation')
            }
            recommendations.append(recommendation)
        
        return recommendations

    def _suggest_question_macro(self, category: str) -> str:
        """Suggest a macro for a question category."""
        macro_templates = {
            'billing_questions': "Billing FAQ: Common billing questions and answers",
            'account_questions': "Account Management: How to manage your account",
            'technical_questions': "Technical Support: Common technical questions",
            'product_questions': "Product Help: How to use our product"
        }
        return macro_templates.get(category, f"Macro for {category}")

    def _suggest_response_macro(self, category: str) -> str:
        """Suggest a macro for a response category."""
        macro_templates = {
            'greeting_responses': "Standard greeting and introduction",
            'troubleshooting_responses': "Troubleshooting assistance template",
            'escalation_responses': "Escalation process explanation",
            'resolution_responses': "Resolution confirmation template"
        }
        return macro_templates.get(category, f"Response macro for {category}")

    def _suggest_troubleshooting_macro(self, sequence_name: str) -> str:
        """Suggest a macro for a troubleshooting sequence."""
        macro_templates = {
            'browser_issues': "Browser troubleshooting step-by-step guide",
            'login_issues': "Login problem resolution guide",
            'export_issues': "Export problem troubleshooting guide",
            'performance_issues': "Performance issue resolution guide"
        }
        return macro_templates.get(sequence_name, f"Troubleshooting guide for {sequence_name}")

    def _suggest_escalation_macro(self, pattern: str) -> str:
        """Suggest a macro for an escalation pattern."""
        macro_templates = {
            'escalate': "When and how to escalate issues",
            'transfer': "Transfer process and guidelines",
            'technical': "Technical escalation procedures",
            'urgent': "Urgent issue handling procedures"
        }
        return macro_templates.get(pattern, f"Escalation macro for {pattern}")

    def _get_implementation_notes(self, category: str, macro_type: str) -> str:
        """Get implementation notes for a macro."""
        notes = {
            'question': "Create a comprehensive FAQ macro with common questions and detailed answers",
            'response': "Standardize response templates to ensure consistency and efficiency",
            'troubleshooting': "Create step-by-step troubleshooting guides with clear instructions",
            'escalation': "Define clear escalation criteria and procedures for different scenarios"
        }
        return notes.get(macro_type, "Implementation notes for macro creation")

    def _extract_context(self, text: str, match, context_length: int = 100) -> str:
        """Extract context around a match in the text."""
        # Handle tuple matches from regex groups
        if isinstance(match, tuple):
            match = match[0] if match else ""
        elif not isinstance(match, str):
            match = str(match)
            
        match_index = text.lower().find(match.lower())
        if match_index == -1:
            return text[:context_length] + "..." if len(text) > context_length else text
        
        start = max(0, match_index - context_length // 2)
        end = min(len(text), match_index + len(match) + context_length // 2)
        
        context = text[start:end]
        if start > 0:
            context = "..." + context
        if end < len(text):
            context = context + "..."
        
        return context

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

    def _generate_macro_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate summary of macro opportunities."""
        summary = {
            'total_opportunities': 0,
            'high_priority_macros': 0,
            'medium_priority_macros': 0,
            'question_macros': len(results['question_macros']['high_frequency_questions']),
            'response_macros': len(results['response_macros']['standardizable_responses']),
            'troubleshooting_macros': len(results['troubleshooting_macros']['statistics']),
            'escalation_macros': len(results['escalation_macros']['statistics']),
            'training_opportunities': len(results['training_opportunities']['common_misconceptions']),
            'ai_improvements': len(results['ai_agent_improvements']['common_questions'])
        }
        
        # Count total opportunities
        summary['total_opportunities'] = (
            summary['question_macros'] + 
            summary['response_macros'] + 
            summary['troubleshooting_macros'] + 
            summary['escalation_macros']
        )
        
        # Count priority levels
        all_recommendations = []
        all_recommendations.extend(results['question_macros']['recommendations'])
        all_recommendations.extend(results['response_macros']['recommendations'])
        all_recommendations.extend(results['troubleshooting_macros']['recommendations'])
        all_recommendations.extend(results['escalation_macros']['recommendations'])
        
        for rec in all_recommendations:
            if rec.get('priority') == 'high':
                summary['high_priority_macros'] += 1
            elif rec.get('priority') == 'medium':
                summary['medium_priority_macros'] += 1
        
        return summary
