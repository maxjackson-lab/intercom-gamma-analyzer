"""
Fin escalation analyzer service for analyzing AI agent interactions and escalations.

This service analyzes conversations involving Fin (the AI agent) to identify
escalation patterns, success rates, and opportunities for improvement.
"""

import logging
from typing import List, Dict, Any, Tuple, Set
from collections import Counter, defaultdict
from datetime import datetime
import re

logger = logging.getLogger(__name__)


class FinEscalationAnalyzer:
    """
    Analyzes Fin (AI agent) interactions and escalation patterns.
    
    This service identifies:
    - Fin interaction patterns
    - Escalation triggers
    - Success and failure rates
    - Improvement opportunities
    - Training needs
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Fin interaction patterns
        self.fin_patterns = {
            'fin_identification': [
                r'(?i)(fin|copilot|ai.*agent|bot)',
                r'(?i)(automated.*response|auto.*reply)',
                r'(?i)(i.*am.*fin|this.*is.*fin)'
            ],
            'fin_capabilities': [
                r'(?i)(i.*can.*help|i.*can.*assist)',
                r'(?i)(let.*me.*help|i.*ll.*help)',
                r'(?i)(i.*understand|i.*see)'
            ],
            'fin_limitations': [
                r'(?i)(i.*don.*t.*know|i.*can.*t.*help)',
                r'(?i)(i.*need.*to.*transfer|escalating)',
                r'(?i)(let.*me.*connect.*you|transferring)'
            ]
        }
        
        # Escalation triggers
        self.escalation_triggers = {
            'technical_complexity': [
                r'(?i)(complex|complicated|advanced)',
                r'(?i)(technical.*issue|engineering.*problem)',
                r'(?i)(bug|error|malfunction)',
                r'(?i)(integration|api|webhook)'
            ],
            'account_issues': [
                r'(?i)(account.*locked|account.*suspended)',
                r'(?i)(billing.*dispute|payment.*issue)',
                r'(?i)(security.*concern|unauthorized.*access)',
                r'(?i)(data.*breach|privacy.*issue)'
            ],
            'urgent_requests': [
                r'(?i)(urgent|asap|immediately)',
                r'(?i)(critical|emergency|down)',
                r'(?i)(business.*impact|production.*issue)',
                r'(?i)(customer.*facing|user.*impact)'
            ],
            'emotional_escalation': [
                r'(?i)(frustrated|angry|upset)',
                r'(?i)(disappointed|dissatisfied)',
                r'(?i)(unacceptable|unprofessional)',
                r'(?i)(manager|supervisor|escalate)'
            ]
        }
        
        # Success indicators
        self.success_indicators = {
            'resolution_achieved': [
                r'(?i)(resolved|fixed|solved)',
                r'(?i)(working.*now|it.*works)',
                r'(?i)(thank.*you|thanks|appreciate)',
                r'(?i)(perfect|exactly.*what.*i.*needed)'
            ],
            'information_provided': [
                r'(?i)(that.*helps|that.*makes.*sense)',
                r'(?i)(i.*understand.*now|got.*it)',
                r'(?i)(clear|helpful|useful)',
                r'(?i)(exactly.*what.*i.*was.*looking.*for)'
            ],
            'satisfaction_expressed': [
                r'(?i)(great|excellent|awesome)',
                r'(?i)(very.*helpful|very.*useful)',
                r'(?i)(satisfied|happy|pleased)',
                r'(?i)(would.*recommend|great.*service)'
            ]
        }
        
        # Failure indicators
        self.failure_indicators = {
            'confusion': [
                r'(?i)(confused|don.*t.*understand)',
                r'(?i)(that.*doesn.*t.*make.*sense)',
                r'(?i)(not.*what.*i.*asked|not.*helpful)',
                r'(?i)(still.*don.*t.*get.*it)'
            ],
            'frustration': [
                r'(?i)(frustrated|annoyed|irritated)',
                r'(?i)(this.*is.*taking.*too.*long)',
                r'(?i)(not.*getting.*anywhere)',
                r'(?i)(waste.*of.*time)'
            ],
            'escalation_request': [
                r'(?i)(speak.*to.*human|talk.*to.*person)',
                r'(?i)(escalate|transfer|supervisor)',
                r'(?i)(manager|higher.*up)',
                r'(?i)(real.*person|actual.*human)'
            ]
        }
        
        # Compile regex patterns
        self._compile_patterns()
        
        self.logger.info("FinEscalationAnalyzer initialized")

    def _compile_patterns(self):
        """Compile regex patterns for better performance."""
        self.compiled_fin_patterns = {}
        for category, patterns in self.fin_patterns.items():
            self.compiled_fin_patterns[category] = [
                re.compile(pattern) for pattern in patterns
            ]
        
        self.compiled_escalation_triggers = {}
        for category, patterns in self.escalation_triggers.items():
            self.compiled_escalation_triggers[category] = [
                re.compile(pattern) for pattern in patterns
            ]
        
        self.compiled_success_indicators = {}
        for category, patterns in self.success_indicators.items():
            self.compiled_success_indicators[category] = [
                re.compile(pattern) for pattern in patterns
            ]
        
        self.compiled_failure_indicators = {}
        for category, patterns in self.failure_indicators.items():
            self.compiled_failure_indicators[category] = [
                re.compile(pattern) for pattern in patterns
            ]

    def analyze_fin_escalations(self, conversations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze Fin escalations and interactions.
        
        Args:
            conversations: List of conversation dictionaries
            
        Returns:
            Dictionary containing escalation analysis and recommendations
        """
        self.logger.info(f"Analyzing Fin escalations in {len(conversations)} conversations")
        
        # Filter conversations that involve Fin
        fin_conversations = self._filter_fin_conversations(conversations)
        
        if not fin_conversations:
            return {
                'fin_conversations_found': 0,
                'message': 'No conversations involving Fin found',
                'summary': {}
            }
        
        results = {
            'fin_conversations_found': len(fin_conversations),
            'fin_interaction_analysis': self._analyze_fin_interactions(fin_conversations),
            'escalation_analysis': self._analyze_escalations(fin_conversations),
            'success_analysis': self._analyze_success_patterns(fin_conversations),
            'failure_analysis': self._analyze_failure_patterns(fin_conversations),
            'improvement_opportunities': self._identify_improvement_opportunities(fin_conversations),
            'training_recommendations': self._generate_training_recommendations(fin_conversations),
            'summary': {}
        }
        
        # Generate summary
        results['summary'] = self._generate_escalation_summary(results)
        
        self.logger.info("Fin escalation analysis completed")
        return results

    def _filter_fin_conversations(self, conversations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter conversations that involve Fin interactions."""
        fin_conversations = []
        
        for conv in conversations:
            text = self._extract_conversation_text(conv)
            
            # Check if conversation involves Fin
            for category, patterns in self.compiled_fin_patterns.items():
                for pattern in patterns:
                    if pattern.search(text):
                        fin_conversations.append(conv)
                        break
                else:
                    continue
                break
        
        return fin_conversations

    def _analyze_fin_interactions(self, conversations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze Fin interaction patterns."""
        interaction_stats = defaultdict(int)
        interaction_examples = defaultdict(list)
        conversation_interactions = defaultdict(list)
        
        for conv in conversations:
            conv_id = conv.get('id', 'unknown')
            text = self._extract_conversation_text(conv)
            
            for category, patterns in self.compiled_fin_patterns.items():
                for pattern in patterns:
                    matches = pattern.findall(text)
                    if matches:
                        interaction_stats[category] += len(matches)
                        interaction_examples[category].extend(matches[:3])
                        conversation_interactions[conv_id].append({
                            'category': category,
                            'matches': matches,
                            'pattern': pattern.pattern
                        })
        
        return {
            'statistics': dict(interaction_stats),
            'examples': {k: list(set(v)) for k, v in interaction_examples.items()},
            'conversation_details': dict(conversation_interactions)
        }

    def _analyze_escalations(self, conversations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze escalation patterns in Fin conversations."""
        escalation_stats = defaultdict(int)
        escalation_examples = defaultdict(list)
        escalation_contexts = defaultdict(list)
        
        for conv in conversations:
            conv_id = conv.get('id', 'unknown')
            text = self._extract_conversation_text(conv)
            
            for category, patterns in self.compiled_escalation_triggers.items():
                for pattern in patterns:
                    matches = pattern.findall(text)
                    if matches:
                        escalation_stats[category] += len(matches)
                        escalation_examples[category].extend(matches[:3])
                        escalation_contexts[category].append({
                            'conversation_id': conv_id,
                            'matches': matches,
                            'context': self._extract_context(text, matches[0]),
                            'escalation_trigger': category
                        })
        
        return {
            'statistics': dict(escalation_stats),
            'examples': {k: list(set(v)) for k, v in escalation_examples.items()},
            'contexts': dict(escalation_contexts),
            'escalation_rate': self._calculate_escalation_rate(conversations)
        }

    def _analyze_success_patterns(self, conversations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze success patterns in Fin conversations."""
        success_stats = defaultdict(int)
        success_examples = defaultdict(list)
        success_contexts = defaultdict(list)
        
        for conv in conversations:
            conv_id = conv.get('id', 'unknown')
            text = self._extract_conversation_text(conv)
            
            for category, patterns in self.compiled_success_indicators.items():
                for pattern in patterns:
                    matches = pattern.findall(text)
                    if matches:
                        success_stats[category] += len(matches)
                        success_examples[category].extend(matches[:3])
                        success_contexts[category].append({
                            'conversation_id': conv_id,
                            'matches': matches,
                            'context': self._extract_context(text, matches[0]),
                            'success_type': category
                        })
        
        return {
            'statistics': dict(success_stats),
            'examples': {k: list(set(v)) for k, v in success_examples.items()},
            'contexts': dict(success_contexts),
            'success_rate': self._calculate_success_rate(conversations)
        }

    def _analyze_failure_patterns(self, conversations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze failure patterns in Fin conversations."""
        failure_stats = defaultdict(int)
        failure_examples = defaultdict(list)
        failure_contexts = defaultdict(list)
        
        for conv in conversations:
            conv_id = conv.get('id', 'unknown')
            text = self._extract_conversation_text(conv)
            
            for category, patterns in self.compiled_failure_indicators.items():
                for pattern in patterns:
                    matches = pattern.findall(text)
                    if matches:
                        failure_stats[category] += len(matches)
                        failure_examples[category].extend(matches[:3])
                        failure_contexts[category].append({
                            'conversation_id': conv_id,
                            'matches': matches,
                            'context': self._extract_context(text, matches[0]),
                            'failure_type': category
                        })
        
        return {
            'statistics': dict(failure_stats),
            'examples': {k: list(set(v)) for k, v in failure_examples.items()},
            'contexts': dict(failure_contexts),
            'failure_rate': self._calculate_failure_rate(conversations)
        }

    def _identify_improvement_opportunities(self, conversations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Identify opportunities for improving Fin's performance."""
        opportunities = {
            'knowledge_gaps': defaultdict(int),
            'response_improvements': defaultdict(int),
            'escalation_optimization': defaultdict(int),
            'training_needs': defaultdict(int)
        }
        
        for conv in conversations:
            conv_id = conv.get('id', 'unknown')
            text = self._extract_conversation_text(conv)
            
            # Identify knowledge gaps
            knowledge_gap_patterns = [
                r'(?i)(i.*don.*t.*know|i.*can.*t.*help)',
                r'(?i)(not.*sure|unclear)',
                r'(?i)(need.*more.*information|require.*clarification)'
            ]
            
            for pattern in knowledge_gap_patterns:
                if re.search(pattern, text):
                    opportunities['knowledge_gaps']['missing_knowledge'] += 1
            
            # Identify response improvement opportunities
            response_patterns = [
                r'(?i)(that.*doesn.*t.*help|not.*helpful)',
                r'(?i)(confusing|unclear.*response)',
                r'(?i)(repetitive|same.*answer)'
            ]
            
            for pattern in response_patterns:
                if re.search(pattern, text):
                    opportunities['response_improvements']['response_quality'] += 1
            
            # Identify escalation optimization opportunities
            escalation_patterns = [
                r'(?i)(escalate.*too.*quickly|should.*have.*tried)',
                r'(?i)(could.*have.*solved|should.*have.*known)',
                r'(?i)(premature.*escalation|too.*early)'
            ]
            
            for pattern in escalation_patterns:
                if re.search(pattern, text):
                    opportunities['escalation_optimization']['timing_issues'] += 1
        
        return opportunities

    def _generate_training_recommendations(self, conversations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate training recommendations for Fin."""
        recommendations = []
        
        # Analyze common escalation triggers
        escalation_analysis = self._analyze_escalations(conversations)
        failure_analysis = self._analyze_failure_patterns(conversations)
        
        # Generate recommendations based on analysis
        for trigger_type, count in escalation_analysis['statistics'].items():
            if count >= 3:  # Threshold for training recommendation
                recommendation = {
                    'type': 'escalation_training',
                    'category': trigger_type,
                    'frequency': count,
                    'priority': 'high' if count >= 10 else 'medium',
                    'training_focus': self._get_training_focus(trigger_type),
                    'suggested_improvements': self._get_suggested_improvements(trigger_type)
                }
                recommendations.append(recommendation)
        
        for failure_type, count in failure_analysis['statistics'].items():
            if count >= 3:  # Threshold for training recommendation
                recommendation = {
                    'type': 'failure_training',
                    'category': failure_type,
                    'frequency': count,
                    'priority': 'high' if count >= 10 else 'medium',
                    'training_focus': self._get_training_focus(failure_type),
                    'suggested_improvements': self._get_suggested_improvements(failure_type)
                }
                recommendations.append(recommendation)
        
        return recommendations

    def _get_training_focus(self, category: str) -> str:
        """Get training focus for a category."""
        training_focus = {
            'technical_complexity': "Improve technical knowledge and troubleshooting capabilities",
            'account_issues': "Enhance account management and security knowledge",
            'urgent_requests': "Develop better urgency detection and response protocols",
            'emotional_escalation': "Improve emotional intelligence and de-escalation skills",
            'confusion': "Enhance clarity and explanation capabilities",
            'frustration': "Develop better empathy and problem-solving approaches",
            'escalation_request': "Improve resolution capabilities before escalation"
        }
        return training_focus.get(category, f"Training focus for {category}")

    def _get_suggested_improvements(self, category: str) -> List[str]:
        """Get suggested improvements for a category."""
        improvements = {
            'technical_complexity': [
                "Expand technical knowledge base",
                "Improve diagnostic capabilities",
                "Better integration with technical documentation"
            ],
            'account_issues': [
                "Enhance account security knowledge",
                "Improve billing and payment understanding",
                "Better access to account management tools"
            ],
            'urgent_requests': [
                "Implement urgency detection algorithms",
                "Create priority response protocols",
                "Improve escalation timing"
            ],
            'emotional_escalation': [
                "Develop emotional intelligence capabilities",
                "Improve de-escalation techniques",
                "Better empathy and understanding"
            ],
            'confusion': [
                "Improve explanation clarity",
                "Better step-by-step guidance",
                "Enhanced visual aids and examples"
            ],
            'frustration': [
                "Develop better problem-solving approaches",
                "Improve response efficiency",
                "Better understanding of user needs"
            ],
            'escalation_request': [
                "Expand resolution capabilities",
                "Improve self-service options",
                "Better knowledge base integration"
            ]
        }
        return improvements.get(category, [f"Improvements for {category}"])

    def _calculate_escalation_rate(self, conversations: List[Dict[str, Any]]) -> float:
        """Calculate the escalation rate for Fin conversations."""
        total_conversations = len(conversations)
        escalated_conversations = 0
        
        for conv in conversations:
            text = self._extract_conversation_text(conv)
            
            # Check for escalation indicators
            escalation_indicators = [
                r'(?i)(escalate|transfer|supervisor|manager)',
                r'(?i)(speak.*to.*human|talk.*to.*person)',
                r'(?i)(real.*person|actual.*human)'
            ]
            
            for indicator in escalation_indicators:
                if re.search(indicator, text):
                    escalated_conversations += 1
                    break
        
        return (escalated_conversations / total_conversations * 100) if total_conversations > 0 else 0

    def _calculate_success_rate(self, conversations: List[Dict[str, Any]]) -> float:
        """Calculate the success rate for Fin conversations."""
        total_conversations = len(conversations)
        successful_conversations = 0
        
        for conv in conversations:
            text = self._extract_conversation_text(conv)
            
            # Check for success indicators
            success_indicators = [
                r'(?i)(resolved|fixed|solved)',
                r'(?i)(thank.*you|thanks|appreciate)',
                r'(?i)(perfect|exactly.*what.*i.*needed)',
                r'(?i)(great|excellent|awesome)'
            ]
            
            for indicator in success_indicators:
                if re.search(indicator, text):
                    successful_conversations += 1
                    break
        
        return (successful_conversations / total_conversations * 100) if total_conversations > 0 else 0

    def _calculate_failure_rate(self, conversations: List[Dict[str, Any]]) -> float:
        """Calculate the failure rate for Fin conversations."""
        total_conversations = len(conversations)
        failed_conversations = 0
        
        for conv in conversations:
            text = self._extract_conversation_text(conv)
            
            # Check for failure indicators
            failure_indicators = [
                r'(?i)(frustrated|annoyed|irritated)',
                r'(?i)(not.*helpful|doesn.*t.*help)',
                r'(?i)(confused|don.*t.*understand)',
                r'(?i)(waste.*of.*time|not.*getting.*anywhere)'
            ]
            
            for indicator in failure_indicators:
                if re.search(indicator, text):
                    failed_conversations += 1
                    break
        
        return (failed_conversations / total_conversations * 100) if total_conversations > 0 else 0

    def _extract_context(self, text: str, match: str, context_length: int = 100) -> str:
        """Extract context around a match in the text."""
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

    def _generate_escalation_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate summary of escalation analysis."""
        summary = {
            'fin_conversations_analyzed': results['fin_conversations_found'],
            'escalation_rate': results['escalation_analysis']['escalation_rate'],
            'success_rate': results['success_analysis']['success_rate'],
            'failure_rate': results['failure_analysis']['failure_rate'],
            'top_escalation_triggers': sorted(
                results['escalation_analysis']['statistics'].items(),
                key=lambda x: x[1],
                reverse=True
            )[:5],
            'top_success_patterns': sorted(
                results['success_analysis']['statistics'].items(),
                key=lambda x: x[1],
                reverse=True
            )[:5],
            'top_failure_patterns': sorted(
                results['failure_analysis']['statistics'].items(),
                key=lambda x: x[1],
                reverse=True
            )[:5],
            'training_recommendations_count': len(results['training_recommendations']),
            'improvement_opportunities_count': sum(
                len(opps) for opps in results['improvement_opportunities'].values()
            )
        }
        
        return summary
